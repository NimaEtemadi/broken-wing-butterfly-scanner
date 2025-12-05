
1. What this is
This repo is a small end-to-end project that:

- Loads an options chain from a CSV file
- Builds 1:-2:1 broken wing call butterflies for a single symbol / expiry
- Filters candidates using DTE, credit, delta, and wing shape
- Calculates net credit, max profit, max loss
- Ranks trades by a basic risk/reward score: max_profit / max_loss
- Exposes the scanner via:
  - a Python CLI,
  - a small Flask API (/api/scan),
  - and a React frontend that calls the API and displays the results

The focus is on:
- clean payoff math,
- clear code structure,
- and a simple but realistic full-stack flow (Python → API → React).
2. Strategy recap (short)
A 1:-2:1 Broken Wing Call Butterfly:

- Long 1 call at K1
- Short 2 calls at K2
- Long 1 call at K3
- All with the same expiry, and K1 < K2 < K3
- “Broken wing” means the wings are not symmetric: (K2 - K1) != (K3 - K2)
  and in this implementation we enforce: outer_wing = (K3 - K2) > inner_wing = (K2 - K1)

Typical behavior:

- Often opened for a net credit
- Best outcome is usually if price finishes near K2
- Limited but asymmetric max loss on one side
- If the underlying finishes below K1, you usually just keep the credit

This scanner builds those structures programmatically and evaluates them.
3. Project structure
Backend (Python)

- bwb_scanner.py
  Core module:
  - loads CSV (load_options_csv),
  - filters the chain (filter_chain_for_bwb),
  - constructs BWBs (scan_broken_wing_butterflies),
  - computes credit / max profit / max loss / score,
  - provides a small CLI entry point.

- api.py
  Flask API that exposes a POST /api/scan endpoint which:
  - accepts JSON parameters (symbol, expiry, filters),
  - calls the scanner in bwb_scanner.py,
  - returns the results as JSON.

- sample_chain.csv
  Sample options chain for a single symbol (XYZ) and a single expiry.
  Used by the scanner, tests, and API.

- test_bwb_scanner.py
  pytest tests for:
  - payoff math of a known BWB configuration,
  - scanner ranking behavior,
  - filter behavior (delta and credit).

Frontend (React)

- bwb-ui/ – React application (created with Create React App)
  - bwb-ui/src/App.js
    React component that:
    - calls http://localhost:5000/api/scan (Flask),
    - sends symbol / expiry / filter settings,
    - renders the results table,
    - and explains the strategy & backend flow.
  - bwb-ui/src/App.css
    Styling for a dark, card-style UI.
4. Requirements
Python (backend)

- Python 3.11 (or any recent 3.x)
- Packages:
  - pandas
  - pytest (for tests)
  - flask
  - flask-cors

Install (example):

    pip install pandas pytest flask flask-cors

Node / React (frontend)

- Node.js + npm (or yarn)

Inside bwb-ui:

    cd bwb-ui
    npm install
5. CSV format and assumptions
The scanner expects an options chain CSV with columns (case-insensitive):

- symbol
- expiry (e.g. 2025-01-17)
- dte (days to expiry, integer)
- strike
- type (C / P / call / put)
- bid
- ask
- mid (optional; if missing it is computed as (bid + ask) / 2)
- delta
- iv

Key assumptions:

- This MVP only scans call BWBs.
- Scanner is designed for one symbol + one expiry at a time.
- All PnL numbers are per share (multiply by 100 for per-contract numbers).
- Data is assumed to be a snapshot (no intraday updating).
6. Running the backend scanner (CLI)
From the project root (where bwb_scanner.py and sample_chain.csv live):

    python bwb_scanner.py sample_chain.csv XYZ 2025-01-17

Arguments:

1) csv_path – path to the options CSV file
2) symbol – e.g. XYZ
3) expiry – e.g. 2025-01-17

This will:

- load the CSV,
- scan for BWBs on XYZ with that expiry,
- print the top candidates as a table (strikes, credit, max profit, max loss, score).
7. Running the backend API (Flask)
From the project root:

    python api.py

This starts a Flask dev server on http://localhost:5000.

API: POST /api/scan

URL:

    http://localhost:5000/api/scan

JSON body example:

    {
      "csv_path": "sample_chain.csv",
      "symbol": "XYZ",
      "expiry": "2025-01-17",
      "min_dte": 1,
      "max_dte": 10,
      "min_credit": 0.5,
      "short_delta_min": 0.2,
      "short_delta_max": 0.35
    }

Response shape:

    {
      "results": [
        {
          "symbol": "XYZ",
          "expiry": "2025-01-17",
          "dte": 5,
          "k1": 95.0,
          "k2": 100.0,
          "k3": 110.0,
          "credit": 0.7,
          "max_profit": 5.7,
          "max_loss": 4.3,
          "score": 1.3255813953
        },
        ...
      ]
    }

If something goes wrong, the API returns:

    { "error": "error message here" }
8. Running the frontend (React UI)
From the React app folder:

    cd bwb-ui
    npm start

This starts the React dev server on http://localhost:3000.

The UI:

- Calls http://localhost:5000/api/scan on initial load,
- Uses the sample CSV and default filters to fetch BWB candidates,
- Displays:
  - an overview of the strategy and filters,
  - a description of the backend flow,
  - and a table of scan results (strikes, credit, max profit, max loss, score),
- Includes a small form for changing symbol and expiry and re-running the scan.

Make sure the Flask backend (python api.py) is running before loading the UI, otherwise you’ll see an error in the frontend when it tries to call /api/scan.
9. Using the scanner directly from Python
Example usage from a Python shell:

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
10. Filters and scoring (details)
For each triple K1 < K2 < K3 (calls only, same symbol, same expiry), the scanner enforces:

- DTE range: min_dte <= dte <= max_dte
- Broken wing shape: outer_wing = (K3 - K2) > inner_wing = (K2 - K1)
- Minimum credit: net_credit >= min_credit
- Short strike delta band: short_delta_min <= abs(delta_at_K2) <= short_delta_max
- Risk sanity: max_loss > 0 (skip degenerate/no-risk structures)

Payoff per share at expiry:

    payoff(S) = max(S - K1, 0)
                - 2 * max(S - K2, 0)
                + max(S - K3, 0)
                + net_credit

Score:

    score = max_profit / max_loss

This is intentionally simple for the MVP, but captures a basic risk/reward ranking.
11. Tests
Tests are in test_bwb_scanner.py and use pytest.

Run tests from the project root:

    python -m pytest -q test_bwb_scanner.py

They cover:

- Payoff math for a known BWB configuration.
- That the scanner finds BWBs and sorts them by score.
- That very strict delta / credit filters can remove all trades.
12. Possible next steps
A few natural extensions:

- Support put BWBs and other structures (e.g. vertical credit spreads).
- Plug into a live options data source instead of a static CSV.
- Add:
  - breakeven price calculations,
  - more detailed PnL stats,
  - per-contract PnL.
- Add a simple probability layer derived from IV (e.g. probability of finishing in the “sweet spot”).
- Extend the API to multiple strategies and symbols, and add more controls to the UI.
13. Disclaimer
This code is for educational / demonstration purposes only and is not financial advice or a recommendation to trade any instrument or strategy.
