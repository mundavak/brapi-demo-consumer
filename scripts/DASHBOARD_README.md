# Service Dashboard

A web-based monitoring dashboard for your trading infrastructure services.

## 📊 Features

- **Real-time Service Monitoring**

  - Redis (connection, memory, keys, clients)
  - TimescaleDB (connection, database size, table counts)
  - PostgreSQL Windows Service
  - Docker Container (bookmap-redis-stack)

- **Live Log Viewing**

  - MBO Consumer logs
  - Quarterly Theory Engine logs
  - PostgreSQL logs

- **Database Statistics**

  - Table record counts (mbo_data, stops_icebergs, ohlc_candles, absorption_events)
  - Database size
  - Active connections

- **Auto-Refresh**
  - Updates every 5 seconds
  - No manual refresh needed

## 🚀 Quick Start

### Option 1: Double-Click (Windows)

```bash
# Just double-click:
start_dashboard.bat
```

### Option 2: PowerShell

```powershell
.\start_dashboard.ps1
```

### Option 3: Python Direct

```bash
python service_dashboard.py
```

## 📖 Usage

1. Start the dashboard using one of the methods above
2. Open your browser to: **http://localhost:8000**
3. View real-time service status and logs
4. Press `Ctrl+C` in terminal to stop

## 🔧 Requirements

- Python 3.7+
- Redis Python client: `pip install redis`
- PostgreSQL Python client: `pip install psycopg2-binary`

**The launcher scripts will automatically install missing dependencies.**

## 📸 What You'll See

### Service Cards

- **Redis** - Connection status, memory usage, key count, uptime
- **Redis Docker** - Container status
- **TimescaleDB** - Database connection, size, active connections
- **PostgreSQL Service** - Windows service status

### Database Tables

- Real-time record counts for all tables
- See how many MBO records, stops/icebergs, OHLC candles, etc.

### Live Logs

- Last 15 lines from each log file
- MBO Consumer activity
- Quarterly Theory Engine activity
- PostgreSQL database logs

## 🎨 Dashboard Features

- **Status Badges**: Green (Running), Red (Stopped), Yellow (Error), Gray (Unknown)
- **Auto-Refresh**: Page refreshes every 5 seconds automatically
- **Responsive Design**: Works on any screen size
- **Dark Mode Logs**: Easy-to-read log viewer with monospace font

## 🔍 Monitored Services

| Service          | What It Monitors                                 |
| ---------------- | ------------------------------------------------ |
| **Redis**        | localhost:6879, PING test, memory, keys, clients |
| **Redis Docker** | bookmap-redis-stack container status             |
| **TimescaleDB**  | localhost:5432, trading_data database            |
| **PostgreSQL**   | postgresql-x64-17 Windows service                |

## 📁 Monitored Logs

| Log                  | Location                                      |
| -------------------- | --------------------------------------------- |
| **MBO Consumer**     | F:/Databases/Logs/MBO_Consumer.log            |
| **Quarterly Theory** | F:/Databases/Logs/quarterly_theory_engine.log |
| **PostgreSQL**       | C:/Program Files/PostgreSQL/17/data/log/      |

## 🛠️ Customization

Edit `service_dashboard.py` to customize:

```python
# Change port
run_server(port=9000)  # Default is 8000

# Change refresh interval (in HTML)
setTimeout(function() {
    location.reload();
}, 10000);  // 10 seconds instead of 5

# Add more log files
LOG_FILES = {
    "mbo_consumer": "F:/Databases/Logs/MBO_Consumer.log",
    "your_log": "path/to/your/log.log"
}
```

## 🆘 Troubleshooting

### "Port already in use"

Another service is using port 8000. Change the port in `service_dashboard.py`:

```python
run_server(port=9000)
```

### "Redis connection failed"

- Check if Redis Docker container is running: `docker ps`
- Verify Redis port: Should be 6879 (not 6379)

### "PostgreSQL connection failed"

- Check Windows service: `Get-Service postgresql-x64-17`
- Verify password in script matches your installation

### Missing Dependencies

Run the launcher scripts - they auto-install missing packages:

```bash
start_dashboard.bat
```

Or install manually:

```bash
pip install redis psycopg2-binary
```

## 🔐 Security Note

**This dashboard runs locally only (localhost:8000).** It's not accessible from other machines unless you change the server binding.

The PostgreSQL password is embedded in the script. Keep this file secure and do not commit to public repositories.

## 📊 API Endpoint

JSON API available at: **http://localhost:8000/api/status**

Returns:

```json
{
  "services": { ... },
  "logs": { ... },
  "stats": { ... }
}
```

Use this for programmatic monitoring or integration with other tools.

## 🎯 Use Cases

- **Morning Check**: Verify all services started after PC restart
- **Development**: Monitor services while coding
- **Production**: Quick health check before live trading
- **Debugging**: View real-time logs without opening log files
- **Monitoring**: Keep open on second monitor for continuous oversight

## 📝 Notes

- Dashboard updates every 5 seconds (configurable)
- Log files show last 15 lines (configurable)
- All timestamps are in your local timezone
- Database queries are non-blocking and cached
- Port checks timeout after 2 seconds to prevent hanging

## 🔄 Updates

To get the latest version:

```bash
git pull origin main
```

Or manually update `service_dashboard.py` from the repository.

---

**Made for Trading Agent Infrastructure**  
Monitor your databases like a pro! 📊🚀
