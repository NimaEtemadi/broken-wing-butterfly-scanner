import pandas as pd
import pytest

from bwb_scanner import (
    bwb_payoff_per_share,
    bwb_max_profit_and_loss,
    scan_broken_wing_butterflies,
    results_to_dataframe,
)


def make_sample_chain() -> pd.DataFrame:
    """
    Small synthetic chain for XYZ, single expiry.
    Just enough strikes to build a few BWBs and poke the filters.
    """
    data = [
        # symbol, expiry, dte, strike, type, bid,  ask,  mid,  delta, iv
        ["XYZ", "2025-01-17", 5, 90,  "C", 10.0, 10.4, 10.2, 0.45, 0.25],
        ["XYZ", "2025-01-17", 5, 95,  "C",  7.0,  7.4,  7.2, 0.38, 0.24],
        ["XYZ", "2025-01-17", 5, 100, "C",  4.3,  4.7,  4.5, 0.30, 0.23],
        ["XYZ", "2025-01-17", 5, 110, "C",  1.0,  1.2,  1.1, 0.15, 0.22],
        ["XYZ", "2025-01-17", 5, 120, "C",  0.4,  0.6,  0.5, 0.08, 0.21],
    ]
    return pd.DataFrame(
        data,
        columns=[
            "symbol",
            "expiry",
            "dte",
            "strike",
            "type",
            "bid",
            "ask",
            "mid",
            "delta",
            "iv",
        ],
    )


def test_payoff_math_known_example():
    """
    Basic sanity check on the BWB payoff shape using a textbook example.
    """
    # Classic example: K1=95, K2=100, K3=110, net credit = 1.00
    k1, k2, k3 = 95.0, 100.0, 110.0
    net_credit = 1.0

    # Below lower strike: just keep the credit
    assert bwb_payoff_per_share(90, k1, k2, k3, net_credit) == pytest.approx(1.0)

    # At the body strike: peak profit = (K2-K1) + credit = 5 + 1
    assert bwb_payoff_per_share(100, k1, k2, k3, net_credit) == pytest.approx(6.0)

    # Far above the upper strike: plateau loss = (2*K2-K1-K3) + credit = -5 + 1 = -4
    assert bwb_payoff_per_share(200, k1, k2, k3, net_credit) == pytest.approx(-4.0)

    max_profit, max_loss = bwb_max_profit_and_loss(k1, k2, k3, net_credit)
    assert max_profit == pytest.approx(6.0)
    assert max_loss == pytest.approx(4.0)


def test_scanner_finds_bwb_and_sorts_by_score():
    """
    Make sure the scanner actually finds something and ranks it sensibly.
    """
    df = make_sample_chain()

    results = scan_broken_wing_butterflies(
        df,
        symbol="XYZ",
        expiry="2025-01-17",
        min_dte=1,
        max_dte=10,
        min_credit=0.5,
        short_delta_min=0.20,
        short_delta_max=0.35,
    )

    # With this sample chain we should get at least one BWB back
    assert len(results) >= 1

    # The "closest" broken wing we expect is built around 95/100/110
    top = results[0]
    assert top.k1 == pytest.approx(95.0)
    assert top.k2 == pytest.approx(100.0)
    assert top.k3 == pytest.approx(110.0)

    # Check that the DataFrame conversion works and is sorted by score
    df_results = results_to_dataframe(results)
    assert list(df_results.columns) == [
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

    scores = df_results["score"].to_list()
    # Scores should be in descending order
    assert scores == sorted(scores, reverse=True)


def test_filters_exclude_by_delta_and_credit():
    """
    Crank the filters so hard that nothing should get through.
    """
    df = make_sample_chain()

    # Delta filter that excludes all candidate short strikes -> no results
    results_delta = scan_broken_wing_butterflies(
        df,
        symbol="XYZ",
        expiry="2025-01-17",
        min_dte=1,
        max_dte=10,
        min_credit=0.5,
        short_delta_min=0.50,  # all deltas in sample are <= 0.45
        short_delta_max=0.80,
    )
    assert results_delta == []

    # Credit filter too strict -> no results
    results_credit = scan_broken_wing_butterflies(
        df,
        symbol="XYZ",
        expiry="2025-01-17",
        min_dte=1,
        max_dte=10,
        min_credit=5.0,  # way above any realistic BWB credit in the sample
        short_delta_min=0.20,
        short_delta_max=0.35,
    )
    assert results_credit == []
