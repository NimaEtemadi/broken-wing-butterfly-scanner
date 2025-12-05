import React, { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [symbol, setSymbol] = useState("XYZ");
  const [expiry, setExpiry] = useState("2025-01-17");

  const runScan = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("http://localhost:5000/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          csv_path: "sample_chain.csv",
          symbol,
          expiry,
          min_dte: 1,
          max_dte: 10,
          min_credit: 0.5,
          short_delta_min: 0.2,
          short_delta_max: 0.35,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Request failed");
      }

      setResults(data.results || []);
    } catch (err) {
      setError(err.message || "Something went wrong");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runScan();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo-circle">BWB</div>
        <div>
          <h1>Broken Wing Butterfly Scanner</h1>
          <p className="subtitle">
            Python backend + React UI for scanning 1:-2:1 broken wing call
            butterflies and ranking them by risk / reward.
          </p>
        </div>
      </header>

      <main className="app-main">
        <section className="card overview-card">
          <h2>Project Overview</h2>
          <p>
            The backend is a small Python module (
            <code>bwb_scanner.py</code>) which reads an options chain from CSV,
            constructs broken wing call butterflies, filters them by DTE, credit,
            delta and wing shape, and computes max profit, max loss and a
            <code> max_profit / max_loss</code> score.
          </p>
          <p>
            This React frontend calls a Flask API on{" "}
            <code>http://localhost:5000/api/scan</code> and renders the results
            as a table.
          </p>

          <div className="tags">
            <span className="tag">Python</span>
            <span className="tag">Flask</span>
            <span className="tag">React</span>
            <span className="tag">Options</span>
          </div>
        </section>

        <section className="card layout-grid">
          <div className="card-inner">
            <h2>Strategy &amp; Filters</h2>

            <h3>Strategy structure</h3>
            <ul className="bullet-list">
              <li>Long 1 call at K1</li>
              <li>Short 2 calls at K2</li>
              <li>Long 1 call at K3</li>
              <li>All with the same expiry, K1 &lt; K2 &lt; K3</li>
              <li>
                Broken wing condition: <code>(K3 - K2) &gt; (K2 - K1)</code>
              </li>
            </ul>

            <h3>Filter logic</h3>
            <ul className="bullet-list">
              <li>DTE between 1 and 10 days</li>
              <li>Minimum net credit ≥ 0.50 per share</li>
              <li>Short strike |delta| between 0.20 and 0.35</li>
              <li>Outer wing wider than inner wing</li>
              <li>Skip structures with max_loss ≤ 0</li>
            </ul>
          </div>

          <div className="card-inner">
            <h2>Backend Flow (Flask + Python)</h2>
            <ol className="bullet-list numbered">
              <li>
                React sends a JSON POST request to{" "}
                <code>/api/scan</code> with symbol, expiry and filter settings.
              </li>
              <li>
                Flask endpoint <code>/api/scan</code> loads{" "}
                <code>sample_chain.csv</code> through{" "}
                <code>load_options_csv</code>.
              </li>
              <li>
                It calls <code>scan_broken_wing_butterflies</code> with the
                given filters.
              </li>
              <li>
                The results are converted to a DataFrame and then to JSON
                (list of dicts).
              </li>
              <li>
                Flask returns <code>{"{ results: [...] }"}</code>, which this UI
                renders in the table below.
              </li>
            </ol>
          </div>
        </section>

        <section className="card results-card">
          <div className="results-header">
            <div>
              <h2>Scan results</h2>
              <p className="muted">
                Data is coming from the Python scanner through the Flask API.
              </p>
            </div>
            <div className="results-filters">
              <div>
                <span className="filter-label">Symbol</span>
                <span className="filter-value">{symbol}</span>
              </div>
              <div>
                <span className="filter-label">Expiry</span>
                <span className="filter-value">{expiry}</span>
              </div>
              <div>
                <span className="filter-label">DTE</span>
                <span className="filter-value">1–10</span>
              </div>
              <div>
                <span className="filter-label">Min credit</span>
                <span className="filter-value">&ge; 0.50</span>
              </div>
            </div>
          </div>

          <div className="controls-row">
            <div className="controls-group">
              <label>
                Symbol
                <input
                  type="text"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                />
              </label>
              <label>
                Expiry
                <input
                  type="text"
                  value={expiry}
                  onChange={(e) => setExpiry(e.target.value)}
                  placeholder="YYYY-MM-DD"
                />
              </label>
            </div>
            <button
              className="primary-btn"
              onClick={runScan}
              disabled={loading}
            >
              {loading ? "Scanning..." : "Run scan"}
            </button>
          </div>

          {error && (
            <p className="muted" style={{ color: "#f97373" }}>
              {error}
            </p>
          )}

          <div className="table-wrapper">
            <table className="results-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Expiry</th>
                  <th>DTE</th>
                  <th>K1</th>
                  <th>K2</th>
                  <th>K3</th>
                  <th>Credit</th>
                  <th>Max Profit</th>
                  <th>Max Loss</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {results.length === 0 && !loading && !error && (
                  <tr>
                    <td colSpan="10" style={{ textAlign: "center" }}>
                      No candidates found with current filters.
                    </td>
                  </tr>
                )}
                {results.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.symbol}</td>
                    <td>{row.expiry}</td>
                    <td>{row.dte}</td>
                    <td>{row.k1.toFixed(1)}</td>
                    <td>{row.k2.toFixed(1)}</td>
                    <td>{row.k3.toFixed(1)}</td>
                    <td>{row.credit.toFixed(2)}</td>
                    <td>{row.max_profit.toFixed(2)}</td>
                    <td>{row.max_loss.toFixed(2)}</td>
                    <td>{row.score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card">
          <h2>Next steps</h2>
          <p>
            This setup keeps the heavier options math and payoff logic in Python,
            and uses React just for presentation and user input. The same pattern
            can be extended to other strategies (vertical spreads, etc.) or to
            live market data instead of a static CSV.
          </p>
        </section>
      </main>

      <footer className="app-footer">
        <span>Broken Wing Butterfly Scanner • Python (Flask) + React</span>
      </footer>
    </div>
  );
}

export default App;
