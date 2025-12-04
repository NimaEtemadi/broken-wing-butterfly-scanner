"""
Very small Broken Wing Butterfly (BWB) scanner.

- Reads an options chain from CSV
- Builds 1:-2:1 broken wing call butterflies on calls
- Applies a few sanity filters and ranks by simple R/R (max_profit / max_loss)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


@dataclass
class BrokenWingButterfly:
    """
    Simple container for a 1:-2:1 broken wing call butterfly.

    All values are per share (so multiply by 100 if you care about per-contract PnL).
    """
    symbol: str
    expiry: str
    dte: int
    k1: float
    k2: float
    k3: float
    credit: float      # net credit received per share
    max_profit: float  # best-case profit per share
    max_loss: float    # worst-case loss per share
    score: float       # e.g. max_profit / max_loss

    def as_dict(self) -> dict:
        """Convert to a plain dict so we can shove it into a DataFrame easily."""
        return {
            "symbol": self.symbol,
            "expiry": self.expiry,
            "dte": self.dte,
            "k1": self.k1,
            "k2": self.k2,
            "k3": self.k3,
            "credit": self.credit,
            "max_profit": self.max_profit,
            "max_loss": self.max_loss,
            "score": self.score,
        }


def load_options_csv(path: str | Path) -> pd.DataFrame:
    """
    Load an options chain CSV into a pandas DataFrame.

    Expected columns (case-insensitive):
        symbol, expiry, dte, strike, type, bid, ask, mid (optional), delta, iv

    If 'mid' is missing, it's computed as (bid + ask) / 2.
    """
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    required = {"symbol", "expiry", "dte", "strike", "type", "bid", "ask", "delta", "iv"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in CSV: {missing}")

    if "mid" not in df.columns:
        df["mid"] = (df["bid"] + df["ask"]) / 2.0

    numeric_cols = ["dte", "strike", "bid", "ask", "mid", "delta", "iv"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["symbol", "expiry", "dte", "strike", "type", "mid", "delta"])
    return df


def _normalise_type(option_type: str) -> str:
    """Normalise option type field into 'call' / 'put'."""
    t = option_type.strip().lower()
    if t in {"c", "call", "calls"}:
        return "call"
    if t in {"p", "put", "puts"}:
        return "put"
    return t


def filter_chain_for_bwb(
    df: pd.DataFrame,
    symbol: str,
    expiry: Optional[str] = None,
    min_dte: int = 1,
    max_dte: int = 10,
) -> pd.DataFrame:
    """
    Trim the full options chain down to:
    - one symbol
    - calls only
    - a DTE window
    - (optionally) a single expiry
    """
    df = df.copy()
    df["type"] = df["type"].apply(_normalise_type)

    mask = (df["symbol"] == symbol) & (df["type"] == "call")
    mask &= (df["dte"] >= min_dte) & (df["dte"] <= max_dte)

    if expiry is not None:
        mask &= (df["expiry"] == expiry)

    sub = df.loc[mask].copy()
    sub = sub.sort_values("strike").reset_index(drop=True)
    return sub


def bwb_payoff_per_share(S: float, k1: float, k2: float, k3: float, net_credit: float) -> float:
    """
    Profit at expiry per share for a 1:-2:1 call BWB with
    net_credit > 0 meaning credit received.
    """

    def call_payoff(s: float, k: float) -> float:
        return max(s - k, 0.0)

    payoff = call_payoff(S, k1) - 2 * call_payoff(S, k2) + call_payoff(S, k3)
    return payoff + net_credit


def bwb_max_profit_and_loss(
    k1: float,
    k2: float,
    k3: float,
    net_credit: float,
) -> tuple[float, float]:
    """
    Closed-form max profit and max loss per share for a 1:-2:1 broken wing call butterfly.

    Assumes k1 < k2 < k3.

    Option-only payoff (no premium):
        plateau for S >= k3 is: 2*k2 - k1 - k3
        maximum at S = k2 is:   k2 - k1
    """
    if not (k1 < k2 < k3):
        raise ValueError("Strikes must satisfy k1 < k2 < k3")

    plateau = 2 * k2 - k1 - k3      # can be negative for broken wings
    max_payoff = k2 - k1            # at S = k2

    max_profit = max_payoff + net_credit

    # Worst-case profit over all S:
    # - below k1: 0 + net_credit
    # - above k3: plateau + net_credit
    # the worst of those two drives the max loss
    worst_profit = min(0.0, plateau) + net_credit
    max_loss = max(0.0, -worst_profit)
    return max_profit, max_loss


def scan_broken_wing_butterflies(
    df: pd.DataFrame,
    symbol: str,
    expiry: Optional[str] = None,
    min_dte: int = 1,
    max_dte: int = 10,
    min_credit: float = 0.50,
    short_delta_min: float = 0.20,
    short_delta_max: float = 0.35,
) -> List[BrokenWingButterfly]:
    """
    Build and score candidate broken wing butterflies for a single symbol/expiry.

    Pattern:
        Long  1 call at K1
        Short 2 calls at K2
        Long  1 call at K3

    Constraints:
        - k1 < k2 < k3
        - "broken" wing: outer_wing > inner_wing
        - DTE between min_dte and max_dte
        - net credit >= min_credit
        - |delta(short strike)| between short_delta_min and short_delta_max

    All monetary outputs are per share.
    """
    chain = filter_chain_for_bwb(
        df,
        symbol=symbol,
        expiry=expiry,
        min_dte=min_dte,
        max_dte=max_dte,
    )

    if chain.empty:
        return []

    # assume a single expiry/DTE in the filtered chain; grab from first row
    expiry_value = chain["expiry"].iloc[0]
    dte_value = int(chain["dte"].iloc[0])

    strikes = chain["strike"].to_list()
    mids = chain["mid"].to_list()
    deltas = chain["delta"].to_list()

    n = len(chain)
    results: List[BrokenWingButterfly] = []

    for i in range(n):
        k1 = strikes[i]
        m1 = mids[i]

        for j in range(i + 1, n):
            k2 = strikes[j]
            m2 = mids[j]

            inner_wing = k2 - k1
            if inner_wing <= 0:
                continue

            short_delta = abs(deltas[j])
            if not (short_delta_min <= short_delta <= short_delta_max):
                continue

            for k in range(j + 1, n):
                k3 = strikes[k]
                m3 = mids[k]

                outer_wing = k3 - k2
                # for a broken wing, we want the outer wing wider than the inner one
                if outer_wing <= inner_wing:
                    continue

                net_credit = 2 * m2 - m1 - m3
                if net_credit < min_credit:
                    continue

                max_profit, max_loss = bwb_max_profit_and_loss(k1, k2, k3, net_credit)
                if max_loss <= 0:
                    # would be a free-lunch structure; skip for this scanner
                    continue

                score = max_profit / max_loss

                results.append(
                    BrokenWingButterfly(
                        symbol=symbol,
                        expiry=str(expiry_value),
                        dte=dte_value,
                        k1=float(k1),
                        k2=float(k2),
                        k3=float(k3),
                        credit=float(net_credit),
                        max_profit=float(max_profit),
                        max_loss=float(max_loss),
                        score=float(score),
                    )
                )

    results.sort(key=lambda r: r.score, reverse=True)
    return results


def results_to_dataframe(results: Iterable[BrokenWingButterfly]) -> pd.DataFrame:
    """
    Turn a list of BrokenWingButterfly objects into a pandas DataFrame.
    """
    rows = [r.as_dict() for r in results]
    if not rows:
        return pd.DataFrame(
            columns=[
                "symbol",
                "expiry",
                "dte",
                "k1",
                "k2",
                "k3",
                "credit",
                "max_profit",
                "max_loss",
                "score",
            ]
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    # Example: python bwb_scanner.py sample_chain.csv XYZ 2025-01-17
    import sys

    if len(sys.argv) != 4:
        print("Usage: python bwb_scanner.py <csv_path> <symbol> <expiry>")
        raise SystemExit(1)

    csv_path, symbol, expiry = sys.argv[1], sys.argv[2], sys.argv[3]
    chain_df = load_options_csv(csv_path)
    candidates = scan_broken_wing_butterflies(chain_df, symbol=symbol, expiry=expiry)
    out_df = results_to_dataframe(candidates)
    print(out_df.head(20).to_string(index=False))
