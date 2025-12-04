

1. What this is

This is a small Python mini-project that:

- Loads an options chain from a CSV file
- Builds 1:-2:1 broken wing call butterflies for a single symbol/expiry
- Filters using DTE, credit, delta, and wing shape
- Calculates net credit, max profit, max loss
- Ranks trades by a basic risk/reward score: max_profit / max_loss

The point is to show how to reason about option structures and implement payoff math cleanly in Python.

2. Quick strategy recap

A 1:-2:1 Broken Wing Call Butterfly:

- Long 1 call at K1
- Short 2 calls at K2
- Long 1 call at K3
- All with the same expiry, and K1 < K2 < K3
- â€œBroken wingâ€ means the wings are not symmetric: (K2 - K1) != (K3 - K2)

Typical behavior:

- Often opened for a net credit
- Best outcome is usually if price finishes near K2
- Limited but asymmetric max loss on one side
- If the underlying finishes below K1, you usually just keep the credit

3. Files in this repo

- bwb_scanner.py: main module (reads CSV, builds BWBs, computes credit/max profit/max loss/score, CLI)
- sample_chain.csv: sample options chain for XYZ
- test_bwb_scanner.py: pytest tests for payoff math and filters

4. Requirements

- Python 3.11 (or recent 3.x)
- pandas
- pytest (for running tests)

5. CSV format / assumptions

Expected columns (case-insensitive):

- symbol
- expiry
- dte
- strike
- type
- bid
- ask
- mid (optional; computed as (bid + ask) / 2 if missing)
- delta
- iv

Assumptions:

- Only calls are used in this MVP.
- Scanner is designed for one symbol + one expiry at a time.
- All PnL numbers are per share (x100 for per-contract).

6. How to run the scanner

From the project folder:

    python bwb_scanner.py sample_chain.csv XYZ 2025-01-17

Arguments:
1) path to CSV file
2) symbol (e.g. XYZ)
3) expiry (e.g. 2025-01-17)

7. Using it from Python instead of CLI

Example:

    import bwb_scanner as b

    df = b.load_options_csv("sample_chain.csv")
    candidates = b.scan_broken_wing_butterflies(
        df,
        symbol="XYZ",
        expiry="2025-01-17",
        min_dte=1,
        max_dte=10,
        min_credit=0.50,
        short_delta_min=0.20,
        short_delta_max=0.35,
    )
    df_out = b.results_to_dataframe(candidates)
    print(df_out)

8. Filters and scoring

For each K1 < K2 < K3 (calls only, same symbol/expiry), the scanner enforces:

- DTE range: min_dte <= dte <= max_dte
- Broken wing shape: outer wing (K3 - K2) > inner wing (K2 - K1)
- Net credit >= min_credit
- abs(delta at K2) between short_delta_min and short_delta_max
- max_loss > 0

Payoff per share at expiry:

    payoff(S) = max(S-K1, 0) - 2*max(S-K2, 0) + max(S-K3, 0) + net_credit

Score:

    score = max_profit / max_loss

9. Tests

Tests are in test_bwb_scanner.py and use pytest.

Run with:

    python -m pytest -q test_bwb_scanner.py

Tests cover:

- payoff math for a known BWB configuration
- that the scanner finds BWBs and sorts by score
- that very strict delta/credit filters can remove all trades

10. Possible next steps

- Support put BWBs and vertical credit spreads.
- Plug into a live options data source.
- Add breakeven calculations and more detailed PnL stats.
- Add a simple probability layer using IV.
- Wrap this in a small API or UI.

11. Disclaimer

This is for educational purposes only and is not trading advice.