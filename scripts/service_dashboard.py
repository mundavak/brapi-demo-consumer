"""
Service Dashboard - Monitor TimescaleDB, PostgreSQL, and Redis
================================================================

A web-based dashboard to monitor database services, logs, and health status.

Usage:
    python service_dashboard.py

Then open: http://localhost:8000

Features:
- Real-time service status (Running/Stopped)
- Connection health checks
- Recent log entries
- Database statistics
- Auto-refresh every 5 seconds
"""

import os
import sys
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import socket

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379  # Redis in Docker uses standard port 6379
TIMESCALE_HOST = "localhost"
TIMESCALE_PORT = 5432
TIMESCALE_DB = "trading_data"
TIMESCALE_USER = "postgres"
TIMESCALE_PASSWORD = "X74Ot*BvtjgKuCBx"

LOG_FILES = {
    "mbo_consumer": "F:/Databases/Logs/MBO_Consumer.log",
    "quarterly_theory": "F:/Databases/Logs/quarterly_theory_engine.log",
    "postgres": "C:/Program Files/PostgreSQL/17/data/log/postgresql-*.log"
}

# Global cache for dashboard data
dashboard_data = {
    "last_update": None,
    "services": {},
    "logs": {},
    "stats": {}
}


def check_port(host, port, timeout=2):
    """Check if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False


def check_redis_status():
    """Check Redis service status"""
    try:
        # Check if port is open
        if not check_port(REDIS_HOST, REDIS_PORT):
            return {
                "status": "Stopped",
                "port": REDIS_PORT,
                "connection": "Failed",
                "error": "Port not reachable"
            }
        
        # Try to ping Redis
        import redis
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=2)
        ping_result = client.ping()
        
        # Get info
        info = client.info()
        
        return {
            "status": "Running",
            "port": REDIS_PORT,
            "connection": "Connected",
            "version": info.get("redis_version", "Unknown"),
            "uptime_days": info.get("uptime_in_days", 0),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "Unknown"),
            "total_commands": info.get("total_commands_processed", 0),
            "keys": client.dbsize()
        }
    except ImportError:
        return {
            "status": "Unknown",
            "error": "redis-py not installed"
        }
    except Exception as e:
        return {
            "status": "Error",
            "error": str(e)
        }


def check_postgres_status():
    """Check PostgreSQL/TimescaleDB service status"""
    try:
        # Check if port is open
        if not check_port(TIMESCALE_HOST, TIMESCALE_PORT):
            return {
                "status": "Stopped",
                "port": TIMESCALE_PORT,
                "connection": "Failed",
                "error": "Port not reachable"
            }
        
        # Try to connect
        import psycopg2
        conn = psycopg2.connect(
            host=TIMESCALE_HOST,
            port=TIMESCALE_PORT,
            database=TIMESCALE_DB,
            user=TIMESCALE_USER,
            password=TIMESCALE_PASSWORD,
            connect_timeout=3
        )
        
        cursor = conn.cursor()
        
        # Get version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        # Get database size
        cursor.execute(f"SELECT pg_size_pretty(pg_database_size('{TIMESCALE_DB}'));")
        db_size = cursor.fetchone()[0]
        
        # Get connection count
        cursor.execute("SELECT count(*) FROM pg_stat_activity;")
        connections = cursor.fetchone()[0]
        
        # Get table counts
        tables_info = {}
        for table in ["mbo_data", "stops_icebergs", "ohlc_candles", "absorption_events"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                tables_info[table] = cursor.fetchone()[0]
            except:
                tables_info[table] = "N/A"
        
        cursor.close()
        conn.close()
        
        return {
            "status": "Running",
            "port": TIMESCALE_PORT,
            "connection": "Connected",
            "version": version[:80],
            "database": TIMESCALE_DB,
            "size": db_size,
            "connections": connections,
            "tables": tables_info
        }
    except ImportError:
        return {
            "status": "Unknown",
            "error": "psycopg2 not installed"
        }
    except Exception as e:
        return {
            "status": "Error",
            "error": str(e)
        }


def check_docker_service(container_name):
    """Check Docker container status"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            status = result.stdout.strip()
            return {
                "status": "Running",
                "container": container_name,
                "docker_status": status
            }
        else:
            return {
                "status": "Stopped",
                "container": container_name
            }
    except Exception as e:
        return {
            "status": "Unknown",
            "error": str(e)
        }


def check_windows_service(service_name):
    """Check Windows service status"""
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"Get-Service -Name '{service_name}' | Select-Object -ExpandProperty Status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            status = result.stdout.strip()
            return {
                "status": "Running" if status == "Running" else "Stopped",
                "service": service_name,
                "windows_status": status
            }
        else:
            return {
                "status": "Not Found",
                "service": service_name
            }
    except Exception as e:
        return {
            "status": "Unknown",
            "error": str(e)
        }


def get_log_tail(log_file, lines=20):
    """Get last N lines from log file"""
    try:
        if "*" in log_file:
            # Handle wildcard (get most recent file)
            import glob
            files = glob.glob(log_file)
            if files:
                log_file = max(files, key=os.path.getmtime)
            else:
                return ["No log files found"]
        
        if not os.path.exists(log_file):
            return [f"Log file not found: {log_file}"]
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            return f.readlines()[-lines:]
    except Exception as e:
        return [f"Error reading log: {str(e)}"]


def update_dashboard_data():
    """Update all dashboard data"""
    global dashboard_data
    
    # Services
    dashboard_data["services"] = {
        "redis": check_redis_status(),
        "redis_docker": check_docker_service("bookmap-redis-stack"),
        "timescaledb": check_postgres_status(),
        "postgres_service": check_windows_service("postgresql-x64-17")
    }
    
    # Logs
    dashboard_data["logs"] = {}
    for log_name, log_path in LOG_FILES.items():
        dashboard_data["logs"][log_name] = get_log_tail(log_path, 15)
    
    # Stats
    dashboard_data["stats"] = {
        "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    dashboard_data["last_update"] = datetime.now()


def generate_html():
    """Generate dashboard HTML"""
    update_dashboard_data()
    
    services = dashboard_data["services"]
    logs = dashboard_data["logs"]
    stats = dashboard_data["stats"]
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Service Dashboard - Trading Agent</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 32px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .header-info {{
            text-align: center;
            color: rgba(255,255,255,0.9);
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .card-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-left: auto;
        }}
        .status-running {{ background: #4ade80; color: white; }}
        .status-stopped {{ background: #ef4444; color: white; }}
        .status-error {{ background: #f59e0b; color: white; }}
        .status-unknown {{ background: #9ca3af; color: white; }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .info-row:last-child {{ border-bottom: none; }}
        .info-label {{
            color: #666;
            font-size: 13px;
        }}
        .info-value {{
            font-weight: 600;
            font-size: 13px;
        }}
        .log-container {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            max-height: 300px;
            overflow-y: auto;
            line-height: 1.5;
        }}
        .log-line {{
            margin-bottom: 2px;
            word-wrap: break-word;
        }}
        .table-stats {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-top: 10px;
        }}
        .table-stat {{
            background: #f8fafc;
            padding: 10px;
            border-radius: 6px;
        }}
        .table-name {{
            font-size: 12px;
            color: #666;
            margin-bottom: 4px;
        }}
        .table-count {{
            font-size: 18px;
            font-weight: 700;
            color: #667eea;
        }}
        .refresh-notice {{
            text-align: center;
            color: rgba(255,255,255,0.8);
            font-size: 12px;
            margin-top: 20px;
        }}
        .full-width {{
            grid-column: 1 / -1;
        }}
    </style>
    <script>
        // Auto-refresh every 5 seconds
        setTimeout(function() {{
            location.reload();
        }}, 5000);
    </script>
</head>
<body>
    <div class="container">
        <h1>🖥️ Service Dashboard</h1>
        <div class="header-info">
            Last Update: {stats.get('last_check', 'N/A')}<br>
            Auto-refresh in 5 seconds
        </div>
        
        <div class="grid">
            <!-- Redis Service -->
            <div class="card">
                <div class="card-title">
                    🔴 Redis
                    <span class="status-badge status-{services['redis']['status'].lower()}">{services['redis']['status']}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Port:</span>
                    <span class="info-value">{services['redis'].get('port', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Connection:</span>
                    <span class="info-value">{services['redis'].get('connection', 'N/A')}</span>
                </div>
                {f'''<div class="info-row">
                    <span class="info-label">Version:</span>
                    <span class="info-value">{services['redis'].get('version', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Uptime:</span>
                    <span class="info-value">{services['redis'].get('uptime_days', 0)} days</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Memory:</span>
                    <span class="info-value">{services['redis'].get('used_memory_human', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Keys:</span>
                    <span class="info-value">{services['redis'].get('keys', 0):,}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Clients:</span>
                    <span class="info-value">{services['redis'].get('connected_clients', 0)}</span>
                </div>''' if services['redis']['status'] == 'Running' else f'''<div class="info-row">
                    <span class="info-label">Error:</span>
                    <span class="info-value" style="color: #ef4444;">{services['redis'].get('error', 'Unknown')}</span>
                </div>'''}
            </div>
            
            <!-- Redis Docker -->
            <div class="card">
                <div class="card-title">
                    🐳 Redis Docker
                    <span class="status-badge status-{services['redis_docker']['status'].lower()}">{services['redis_docker']['status']}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Container:</span>
                    <span class="info-value">{services['redis_docker'].get('container', 'N/A')}</span>
                </div>
                {f'''<div class="info-row">
                    <span class="info-label">Docker Status:</span>
                    <span class="info-value">{services['redis_docker'].get('docker_status', 'N/A')}</span>
                </div>''' if 'docker_status' in services['redis_docker'] else ''}
            </div>
            
            <!-- TimescaleDB -->
            <div class="card">
                <div class="card-title">
                    🐘 TimescaleDB
                    <span class="status-badge status-{services['timescaledb']['status'].lower()}">{services['timescaledb']['status']}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Port:</span>
                    <span class="info-value">{services['timescaledb'].get('port', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Connection:</span>
                    <span class="info-value">{services['timescaledb'].get('connection', 'N/A')}</span>
                </div>
                {f'''<div class="info-row">
                    <span class="info-label">Database:</span>
                    <span class="info-value">{services['timescaledb'].get('database', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Size:</span>
                    <span class="info-value">{services['timescaledb'].get('size', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Connections:</span>
                    <span class="info-value">{services['timescaledb'].get('connections', 'N/A')}</span>
                </div>''' if services['timescaledb']['status'] == 'Running' else f'''<div class="info-row">
                    <span class="info-label">Error:</span>
                    <span class="info-value" style="color: #ef4444;">{services['timescaledb'].get('error', 'Unknown')}</span>
                </div>'''}
            </div>
            
            <!-- PostgreSQL Service -->
            <div class="card">
                <div class="card-title">
                    ⚙️ PostgreSQL Service
                    <span class="status-badge status-{services['postgres_service']['status'].lower()}">{services['postgres_service']['status']}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Service Name:</span>
                    <span class="info-value">{services['postgres_service'].get('service', 'N/A')}</span>
                </div>
                {f'''<div class="info-row">
                    <span class="info-label">Windows Status:</span>
                    <span class="info-value">{services['postgres_service'].get('windows_status', 'N/A')}</span>
                </div>''' if 'windows_status' in services['postgres_service'] else ''}
            </div>
        </div>
        
        <!-- Database Tables -->
        {f'''<div class="card" style="margin-bottom: 20px;">
            <div class="card-title">📊 Database Tables (trading_data)</div>
            <div class="table-stats">
                {chr(10).join([f'''<div class="table-stat">
                    <div class="table-name">{table}</div>
                    <div class="table-count">{count:,}</div>
                </div>''' for table, count in services['timescaledb'].get('tables', {}).items()])}
            </div>
        </div>''' if services['timescaledb']['status'] == 'Running' and 'tables' in services['timescaledb'] else ''}
        
        <!-- Logs -->
        <div class="grid">
            {chr(10).join([f'''<div class="card">
                <div class="card-title">📝 {log_name.replace('_', ' ').title()}</div>
                <div class="log-container">
                    {chr(10).join([f'<div class="log-line">{line.strip()}</div>' for line in log_lines[-15:]])}
                </div>
            </div>''' for log_name, log_lines in logs.items()])}
        </div>
        
        <div class="refresh-notice">
            Dashboard will auto-refresh every 5 seconds
        </div>
    </div>
</body>
</html>"""
    
    return html


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = generate_html()
            self.wfile.write(html.encode())
        elif self.path == "/api/status":
            # JSON API endpoint
            update_dashboard_data()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(dashboard_data, default=str).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress request logging
        pass


def run_server(port=8000):
    """Run the dashboard server"""
    server = HTTPServer(("localhost", port), DashboardHandler)
    print(f"🚀 Service Dashboard starting on http://localhost:{port}")
    print(f"📊 Monitoring:")
    print(f"   - Redis ({REDIS_HOST}:{REDIS_PORT})")
    print(f"   - TimescaleDB ({TIMESCALE_HOST}:{TIMESCALE_PORT})")
    print(f"   - PostgreSQL Service (postgresql-x64-17)")
    print(f"   - Docker Container (bookmap-redis-stack)")
    print()
    print(f"🔄 Auto-refresh: Every 5 seconds")
    print(f"⏹️  Press Ctrl+C to stop")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✅ Dashboard stopped")
        server.shutdown()


if __name__ == "__main__":
    run_server()
