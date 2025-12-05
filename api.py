from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

import bwb_scanner as bwb


app = Flask(__name__)
# Allow requests from the React dev server (http://localhost:3000)
CORS(app)


@app.route("/api/scan", methods=["POST"])
def scan_bwb():
    """
    Accepts JSON payload with scan parameters, runs the BWB scanner,
    and returns results as JSON.
    """
    data = request.get_json(force=True) or {}

    symbol = data.get("symbol")
    expiry = data.get("expiry")

    if not symbol or not expiry:
        return jsonify({"error": "symbol and expiry are required"}), 400

    # CSV path defaults to sample_chain.csv in the same folder as this file
    csv_path = data.get("csv_path") or "sample_chain.csv"

    # Optional parameters with sensible defaults
    min_dte = int(data.get("min_dte", 1))
    max_dte = int(data.get("max_dte", 10))
    min_credit = float(data.get("min_credit", 0.50))
    short_delta_min = float(data.get("short_delta_min", 0.20))
    short_delta_max = float(data.get("short_delta_max", 0.35))

    try:
        # Make sure we resolve the CSV path relative to this file
        base_dir = Path(__file__).resolve().parent
        csv_full_path = base_dir / csv_path

        df_chain = bwb.load_options_csv(csv_full_path)
        bwbs = bwb.scan_broken_wing_butterflies(
            df_chain,
            symbol=symbol,
            expiry=expiry,
            min_dte=min_dte,
            max_dte=max_dte,
            min_credit=min_credit,
            short_delta_min=short_delta_min,
            short_delta_max=short_delta_max,
        )

        df_results = bwb.results_to_dataframe(bwbs)
        results_json = df_results.to_dict(orient="records")

        return jsonify({"results": results_json})

    except Exception as e:
        # In a real app you'd log this properly
        print("Error in /api/scan:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Flask dev server on http://localhost:5000
    app.run(host="127.0.0.1", port=5000, debug=True)
