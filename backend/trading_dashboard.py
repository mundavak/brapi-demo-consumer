"""
Real-Time Trading Dashboard
===========================
Web-based dashboard for institutional order flow analysis.

Features:
- Real-time bias updates (auto-refresh)
- Support/resistance level visualization
- Price targets and reentry zones
- Historical session analysis
- Multi-symbol support

Usage:
    python trading_dashboard.py [port]

Example:
    python trading_dashboard.py 8080

Then open: http://localhost:8080
"""

import psycopg2
import json
import sys
from datetime import datetime, timedelta
import pytz
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import traceback

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

# Analysis parameters
LOOKBACK_HOURS = 1
MBO_SIZE_FILTER = 15
HIGH_SIGNIFICANCE_THRESHOLD = 0.7

# Scoring weights
WEIGHTS = {"mbo": 0.4, "absorption": 0.4, "icebergs": 0.2}

# Global cache for dashboard data
dashboard_cache = {"last_update": None, "data": None, "error": None}


def connect_database():
    """Connect to TimescaleDB."""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        return None


def fetch_all_data(lookback_time):
    """Fetch all data sources in one go."""
    conn = connect_database()
    if not conn:
        return None, None, None

    cursor = conn.cursor()

    try:
        # MBO data
        mbo_query = """
        SELECT timestamp, price, size, side, action
        FROM mbo_data
        WHERE timestamp >= %s 
          AND size > %s
          AND action IN ('ADD', 'DELETE', 'MODIFY')
        ORDER BY timestamp;
        """
        cursor.execute(mbo_query, (lookback_time, MBO_SIZE_FILTER))
        mbo_data = cursor.fetchall()

        # Absorption data
        abs_query = """
        SELECT timestamp, price, side, absorbed_volume, aggressor_volume, significance_score
        FROM absorption_events
        WHERE timestamp >= %s
        ORDER BY timestamp;
        """
        cursor.execute(abs_query, (lookback_time,))
        absorption_data = cursor.fetchall()

        # Iceberg data
        ice_query = """
        SELECT timestamp, price, side, detected_size, confidence_score, event_type
        FROM stops_icebergs
        WHERE timestamp >= %s
        ORDER BY timestamp;
        """
        cursor.execute(ice_query, (lookback_time,))
        iceberg_data = cursor.fetchall()

        cursor.close()
        conn.close()

        return mbo_data, absorption_data, iceberg_data
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return None, None, None


def calculate_bias(mbo_data, absorption_data, iceberg_data):
    """Calculate market bias from all data sources."""
    # MBO analysis
    buy_volume = sum(r[2] for r in mbo_data if r[3] == "BUY" and r[4] == "ADD")
    sell_volume = sum(r[2] for r in mbo_data if r[3] == "SELL" and r[4] == "ADD")
    mbo_delta = buy_volume - sell_volume
    mbo_score = mbo_delta * WEIGHTS["mbo"]

    # Absorption analysis
    buy_absorption = sum(r[3] for r in absorption_data if r[2] == "BUY")
    sell_absorption = sum(r[3] for r in absorption_data if r[2] == "SELL")
    abs_delta = buy_absorption - sell_absorption
    abs_score = abs_delta * WEIGHTS["absorption"]
    high_sig_buys = sum(
        1
        for r in absorption_data
        if r[2] == "BUY" and r[5] and r[5] > HIGH_SIGNIFICANCE_THRESHOLD
    )
    high_sig_sells = sum(
        1
        for r in absorption_data
        if r[2] == "SELL" and r[5] and r[5] > HIGH_SIGNIFICANCE_THRESHOLD
    )

    # Iceberg analysis
    buy_icebergs = len([r for r in iceberg_data if r[2] == "BUY"])
    sell_icebergs = len([r for r in iceberg_data if r[2] == "SELL"])
    ice_delta = buy_icebergs - sell_icebergs
    ice_score = ice_delta * WEIGHTS["icebergs"] * 100

    # Total score
    total_score = mbo_score + abs_score + ice_score
    normalized_score = max(-100, min(100, total_score / 100))

    if normalized_score > 50:
        bias = "STRONGLY BULLISH"
        color = "#00ff00"
    elif normalized_score > 20:
        bias = "BULLISH"
        color = "#7fff00"
    elif normalized_score > -20:
        bias = "NEUTRAL"
        color = "#ffff00"
    elif normalized_score > -50:
        bias = "BEARISH"
        color = "#ff7f00"
    else:
        bias = "STRONGLY BEARISH"
        color = "#ff0000"

    return {
        "bias": bias,
        "color": color,
        "score": round(total_score, 1),
        "normalized": round(normalized_score, 1),
        "mbo": {
            "buy": buy_volume,
            "sell": sell_volume,
            "delta": mbo_delta,
            "score": round(mbo_score, 1),
        },
        "absorption": {
            "buy": buy_absorption,
            "sell": sell_absorption,
            "delta": abs_delta,
            "score": round(abs_score, 1),
            "high_sig_buys": high_sig_buys,
            "high_sig_sells": high_sig_sells,
        },
        "icebergs": {
            "buy": buy_icebergs,
            "sell": sell_icebergs,
            "delta": ice_delta,
            "score": round(ice_score, 1),
        },
    }


def find_levels(mbo_data, absorption_data, iceberg_data, current_price=None):
    """Find key support and resistance levels."""
    support_levels = defaultdict(
        lambda: {"mbo": 0, "absorption": 0, "icebergs": 0, "score": 0}
    )
    resistance_levels = defaultdict(
        lambda: {"mbo": 0, "absorption": 0, "icebergs": 0, "score": 0}
    )

    # Process MBO
    for r in mbo_data:
        price = round(r[1], 2)
        volume = r[2]
        side = r[3]
        action = r[4]

        if action == "ADD":
            if side == "BUY":
                if current_price is None or price <= current_price:
                    support_levels[price]["mbo"] += volume
                    support_levels[price]["score"] += volume / 5
            elif side == "SELL":
                if current_price is None or price >= current_price:
                    resistance_levels[price]["mbo"] += volume
                    resistance_levels[price]["score"] += volume / 5

    # Process absorption
    for r in absorption_data:
        price = round(r[1], 2)
        side = r[2]
        volume = r[3]

        if side == "BUY":
            if current_price is None or price <= current_price:
                support_levels[price]["absorption"] += volume
                support_levels[price]["score"] += volume / 3
        elif side == "SELL":
            if current_price is None or price >= current_price:
                resistance_levels[price]["absorption"] += volume
                resistance_levels[price]["score"] += volume / 3

    # Process icebergs
    for r in iceberg_data:
        price = round(r[1], 2)
        side = r[2]
        size = r[3]

        if side == "BUY":
            if current_price is None or price <= current_price:
                support_levels[price]["icebergs"] += size
                support_levels[price]["score"] += 100
        elif side == "SELL":
            if current_price is None or price >= current_price:
                resistance_levels[price]["icebergs"] += size
                resistance_levels[price]["score"] += 100

    # Sort and format
    sorted_support = sorted(
        support_levels.items(), key=lambda x: x[1]["score"], reverse=True
    )[:10]
    sorted_resistance = sorted(
        resistance_levels.items(), key=lambda x: x[1]["score"], reverse=True
    )[:10]

    return [{"price": p, **data} for p, data in sorted_support], [
        {"price": p, **data} for p, data in sorted_resistance
    ]


def update_dashboard_data():
    """Update dashboard data cache."""
    global dashboard_cache

    try:
        lookback_time = datetime.now(pytz.UTC) - timedelta(hours=LOOKBACK_HOURS)

        mbo_data, absorption_data, iceberg_data = fetch_all_data(lookback_time)

        if mbo_data is None:
            dashboard_cache["error"] = "Database connection failed"
            return

        bias_analysis = calculate_bias(mbo_data, absorption_data, iceberg_data)
        support_levels, resistance_levels = find_levels(
            mbo_data, absorption_data, iceberg_data
        )

        dashboard_cache["data"] = {
            "timestamp": datetime.now(pytz.timezone("US/Eastern")).isoformat(),
            "data_counts": {
                "mbo": len(mbo_data),
                "absorption": len(absorption_data),
                "icebergs": len(iceberg_data),
            },
            "bias": bias_analysis,
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "lookback_hours": LOOKBACK_HOURS,
        }
        dashboard_cache["last_update"] = time.time()
        dashboard_cache["error"] = None

    except Exception as e:
        dashboard_cache["error"] = f"Error: {str(e)}\n{traceback.format_exc()}"


def background_updater():
    """Background thread to update data every 10 seconds."""
    while True:
        try:
            update_dashboard_data()
        except Exception as e:
            print(f"Background update error: {e}")
        time.sleep(10)


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/":
            self.serve_html()
        elif self.path == "/api/data":
            self.serve_json()
        else:
            self.send_error(404)

    def serve_html(self):
        """Serve the dashboard HTML."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header .timestamp { color: #aaa; font-size: 0.9em; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h2 {
            font-size: 1.3em;
            margin-bottom: 15px;
            border-bottom: 2px solid rgba(255,255,255,0.2);
            padding-bottom: 10px;
        }
        .bias-display {
            text-align: center;
            padding: 30px;
            font-size: 2em;
            font-weight: bold;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        .score { font-size: 0.6em; color: #ddd; display: block; margin-top: 10px; }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            margin: 5px 0;
            background: rgba(255,255,255,0.03);
            border-radius: 5px;
        }
        .metric-label { color: #aaa; }
        .metric-value { font-weight: bold; }
        .positive { color: #00ff00; }
        .negative { color: #ff4444; }
        .neutral { color: #ffff00; }
        .level-list { max-height: 300px; overflow-y: auto; }
        .level-item {
            display: flex;
            justify-content: space-between;
            padding: 8px;
            margin: 3px 0;
            background: rgba(255,255,255,0.03);
            border-radius: 5px;
            font-size: 0.9em;
        }
        .level-price { font-weight: bold; color: #00aaff; }
        .level-score { color: #ffaa00; }
        .error {
            background: rgba(255,0,0,0.2);
            border: 1px solid #ff0000;
            padding: 15px;
            border-radius: 5px;
            color: #ffaaaa;
        }
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2em;
            color: #aaa;
        }
        .component-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 10px;
            margin-top: 10px;
        }
        .component {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 5px;
        }
        .component h3 {
            font-size: 1em;
            margin-bottom: 10px;
            color: #00aaff;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .updating { animation: pulse 1s infinite; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Trading Dashboard</h1>
            <div class="timestamp" id="timestamp">Loading...</div>
        </div>
        
        <div id="content" class="loading">
            <div>⏳ Loading market data...</div>
        </div>
    </div>

    <script>
        let updateInterval;
        
        function formatNumber(num) {
            return num.toLocaleString('en-US');
        }
        
        function renderDashboard(data) {
            const bias = data.bias;
            const support = data.support_levels;
            const resistance = data.resistance_levels;
            
            const html = `
                <div class="grid">
                    <div class="card" style="grid-column: span 2;">
                        <h2>🎯 Institutional Bias</h2>
                        <div class="bias-display" style="background-color: ${bias.color}20; border: 2px solid ${bias.color};">
                            ${bias.bias}
                            <span class="score">Score: ${bias.score} / Normalized: ${bias.normalized}/100</span>
                        </div>
                        
                        <div class="component-grid">
                            <div class="component">
                                <h3>MBO Order Flow (${(WEIGHTS.mbo * 100).toFixed(0)}%)</h3>
                                <div class="metric">
                                    <span class="metric-label">Buy Volume:</span>
                                    <span class="metric-value positive">${formatNumber(bias.mbo.buy)}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Sell Volume:</span>
                                    <span class="metric-value negative">${formatNumber(bias.mbo.sell)}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Delta:</span>
                                    <span class="metric-value ${bias.mbo.delta >= 0 ? 'positive' : 'negative'}">${bias.mbo.delta >= 0 ? '+' : ''}${formatNumber(bias.mbo.delta)}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Score:</span>
                                    <span class="metric-value">${bias.mbo.score}</span>
                                </div>
                            </div>
                            
                            <div class="component">
                                <h3>Absorption (${(WEIGHTS.absorption * 100).toFixed(0)}%)</h3>
                                <div class="metric">
                                    <span class="metric-label">Buy Absorption:</span>
                                    <span class="metric-value positive">${formatNumber(bias.absorption.buy)}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Sell Absorption:</span>
                                    <span class="metric-value negative">${formatNumber(bias.absorption.sell)}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Delta:</span>
                                    <span class="metric-value ${bias.absorption.delta >= 0 ? 'positive' : 'negative'}">${bias.absorption.delta >= 0 ? '+' : ''}${formatNumber(bias.absorption.delta)}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">High-Sig Buys:</span>
                                    <span class="metric-value positive">${bias.absorption.high_sig_buys}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">High-Sig Sells:</span>
                                    <span class="metric-value negative">${bias.absorption.high_sig_sells}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Score:</span>
                                    <span class="metric-value">${bias.absorption.score}</span>
                                </div>
                            </div>
                            
                            <div class="component">
                                <h3>Icebergs & Stops (${(WEIGHTS.icebergs * 100).toFixed(0)}%)</h3>
                                <div class="metric">
                                    <span class="metric-label">Buy Icebergs:</span>
                                    <span class="metric-value positive">${bias.icebergs.buy}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Sell Icebergs:</span>
                                    <span class="metric-value negative">${bias.icebergs.sell}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Delta:</span>
                                    <span class="metric-value ${bias.icebergs.delta >= 0 ? 'positive' : 'negative'}">${bias.icebergs.delta >= 0 ? '+' : ''}${bias.icebergs.delta}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Score:</span>
                                    <span class="metric-value">${bias.icebergs.score}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>🟢 Support Levels</h2>
                        <div class="level-list">
                            ${support.length > 0 ? support.map(level => `
                                <div class="level-item">
                                    <span class="level-price">${level.price.toFixed(2)}</span>
                                    <span class="level-score">Score: ${level.score.toFixed(0)}</span>
                                </div>
                                <div style="font-size: 0.8em; color: #888; padding-left: 10px;">
                                    MBO: ${formatNumber(level.mbo)} | Abs: ${formatNumber(level.absorption)} | Ice: ${level.icebergs}
                                </div>
                            `).join('') : '<div style="padding: 20px; text-align: center; color: #888;">No support levels detected</div>'}
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>🔴 Resistance Levels</h2>
                        <div class="level-list">
                            ${resistance.length > 0 ? resistance.map(level => `
                                <div class="level-item">
                                    <span class="level-price">${level.price.toFixed(2)}</span>
                                    <span class="level-score">Score: ${level.score.toFixed(0)}</span>
                                </div>
                                <div style="font-size: 0.8em; color: #888; padding-left: 10px;">
                                    MBO: ${formatNumber(level.mbo)} | Abs: ${formatNumber(level.absorption)} | Ice: ${level.icebergs}
                                </div>
                            `).join('') : '<div style="padding: 20px; text-align: center; color: #888;">⚠️ No resistance - Path of least resistance is UP!</div>'}
                        </div>
                    </div>
                    
                    <div class="card" style="grid-column: span 2;">
                        <h2>📈 Data Summary</h2>
                        <div class="metric">
                            <span class="metric-label">MBO Orders (size > ${MBO_SIZE_FILTER}):</span>
                            <span class="metric-value">${formatNumber(data.data_counts.mbo)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Absorption Events:</span>
                            <span class="metric-value">${formatNumber(data.data_counts.absorption)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Icebergs/Stops:</span>
                            <span class="metric-value">${formatNumber(data.data_counts.icebergs)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Lookback Period:</span>
                            <span class="metric-value">${data.lookback_hours} hour(s)</span>
                        </div>
                    </div>
                </div>
            `;
            
            document.getElementById('content').innerHTML = html;
            document.getElementById('timestamp').textContent = `Last updated: ${new Date(data.timestamp).toLocaleString()}`;
        }
        
        function renderError(error) {
            document.getElementById('content').innerHTML = `
                <div class="error">
                    <h2>❌ Error</h2>
                    <p>${error}</p>
                </div>
            `;
        }
        
        async function updateData() {
            try {
                const response = await fetch('/api/data');
                const result = await response.json();
                
                if (result.error) {
                    renderError(result.error);
                } else if (result.data) {
                    renderDashboard(result.data);
                } else {
                    renderError('No data available');
                }
            } catch (error) {
                renderError('Failed to fetch data: ' + error.message);
            }
        }
        
        // Initial load
        updateData();
        
        // Auto-refresh every 10 seconds
        updateInterval = setInterval(updateData, 10000);
        
        // Constants for JavaScript
        const WEIGHTS = { mbo: 0.4, absorption: 0.4, icebergs: 0.2 };
        const MBO_SIZE_FILTER = 15;
    </script>
</body>
</html>
        """

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def serve_json(self):
        """Serve the dashboard data as JSON."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        response = {
            "error": dashboard_cache.get("error"),
            "data": dashboard_cache.get("data"),
            "last_update": dashboard_cache.get("last_update"),
        }

        self.wfile.write(json.dumps(response).encode("utf-8"))


def main():
    """Main entry point."""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    print(f"{'='*60}")
    print(f"  Trading Dashboard Server")
    print(f"{'='*60}")
    print(f"  Port: {port}")
    print(f"  URL: http://localhost:{port}")
    print(
        f"  Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}"
    )
    print(f"  Lookback: {LOOKBACK_HOURS} hour(s)")
    print(f"  Auto-refresh: Every 10 seconds")
    print(f"{'='*60}\n")

    # Initial data load
    print("⏳ Loading initial data...")
    update_dashboard_data()

    if dashboard_cache.get("error"):
        print(f"❌ Error: {dashboard_cache['error']}")
        print("\n⚠️  Server will start but data may not be available.")
    else:
        print("✅ Initial data loaded successfully")

    # Start background updater thread
    updater_thread = threading.Thread(target=background_updater, daemon=True)
    updater_thread.start()
    print("✅ Background updater started")

    # Start HTTP server
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"\n🚀 Server running at http://localhost:{port}")
    print("   Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down server...")
        server.shutdown()
        print("✅ Server stopped")


if __name__ == "__main__":
    main()
