# Service Monitoring Tools - Summary

## 🎯 What Was Created

### 1. **Web Dashboard** (`service_dashboard.py`)

A comprehensive web-based monitoring dashboard that shows:

- Real-time service status for Redis, TimescaleDB, PostgreSQL, Docker
- Live log tailing from MBO Consumer, Quarterly Theory Engine, PostgreSQL
- Database statistics (table record counts, database size, connections)
- Auto-refresh every 5 seconds

**URL:** http://localhost:8000

### 2. **Launcher Scripts**

#### **Windows Batch** (`start_dashboard.bat`)

- Double-click to launch
- Auto-installs missing dependencies
- Opens dashboard in browser

#### **PowerShell** (`start_dashboard.ps1`)

- More verbose output
- Dependency checking
- Clean error handling

### 3. **Quick Status Check** (`check_system_status.ps1`)

Fast command-line status report showing:

- Redis Docker status
- Redis connection (PING test)
- PostgreSQL service status
- TimescaleDB connection
- Recent data collection (MBO, Stops/Icebergs)

**No browser needed - pure console output**

## 🚀 Quick Start

### For Full Dashboard (Recommended)

```bash
# Just double-click:
start_dashboard.bat

# Then open: http://localhost:8000
```

### For Quick Console Check

```powershell
.\check_system_status.ps1
```

## 📊 What You'll Monitor

| Component            | Check Type         | Info Shown                               |
| -------------------- | ------------------ | ---------------------------------------- |
| **Redis**            | Connection + Stats | Port, keys, memory, clients, uptime      |
| **Redis Docker**     | Container Status   | Running/Stopped, uptime                  |
| **TimescaleDB**      | Connection + Stats | Port, DB size, connections, table counts |
| **PostgreSQL**       | Windows Service    | Running/Stopped status                   |
| **MBO Consumer**     | Live Logs          | Last 15 log lines, real-time updates     |
| **Quarterly Theory** | Live Logs          | Last 15 log lines, real-time updates     |
| **PostgreSQL**       | Server Logs        | Database server activity                 |

## 📁 Files Created

```
scripts/
├── service_dashboard.py              # Main dashboard server
├── start_dashboard.bat               # Windows launcher (double-click)
├── start_dashboard.ps1               # PowerShell launcher
├── check_system_status.ps1           # Quick console status
├── DASHBOARD_README.md               # Full documentation
└── DASHBOARD_QUICK_REFERENCE.md      # Quick reference guide
```

## 🎨 Dashboard Features

### Status Cards

Each service has a card showing:

- **Status badge** (Green/Red/Yellow/Gray)
- **Port number** and connection state
- **Version info** (for Redis, PostgreSQL)
- **Statistics** (memory, keys, database size, etc.)

### Database Tables Section

Shows real-time record counts:

- `mbo_data` - 12,732,544 records
- `stops_icebergs` - 419 events
- `ohlc_candles` - 0 records
- `absorption_events` - 0 records

### Live Log Viewers

Three log panels with:

- Dark mode styling (easy on eyes)
- Monospace font (readable formatting)
- Last 15 lines from each log
- Auto-scrolling updates

### Auto-Refresh

- Refreshes every 5 seconds automatically
- Shows last update timestamp
- Countdown to next refresh

## 🔧 Configuration

All settings in `service_dashboard.py`:

```python
# Ports
REDIS_PORT = 6879
TIMESCALE_PORT = 5432

# Database
TIMESCALE_DB = "trading_data"
TIMESCALE_PASSWORD = "X74Ot*BvtjgKuCBx"

# Log files
LOG_FILES = {
    "mbo_consumer": "F:/Databases/Logs/MBO_Consumer.log",
    "quarterly_theory": "F:/Databases/Logs/quarterly_theory_engine.log",
    "postgres": "C:/Program Files/PostgreSQL/17/data/log/postgresql-*.log"
}

# Server port
run_server(port=8000)
```

## 🎯 Use Cases

### 1. Morning Startup Check

```powershell
# Quick check all services
.\check_system_status.ps1

# If issues found, launch dashboard for details
.\start_dashboard.bat
```

### 2. Development Monitoring

- Launch dashboard: `start_dashboard.bat`
- Open in browser: http://localhost:8000
- Keep open on second monitor
- Watch logs update in real-time as you develop

### 3. Production Health Check

- Quick verification before live trading
- All services show green badges
- Database tables have recent data
- Logs show no errors

### 4. Debugging Issues

- Dashboard shows which service failed
- View live logs to see error messages
- Check database connections
- Verify data collection

## 📊 API Endpoint

JSON endpoint available for automation:

```powershell
# Get status as JSON
Invoke-RestMethod -Uri "http://localhost:8000/api/status"

# Use in scripts
$status = Invoke-RestMethod -Uri "http://localhost:8000/api/status"
if ($status.services.redis.status -ne "Running") {
    Write-Host "Redis is down!" -ForegroundColor Red
}
```

## 🛠️ Dependencies

```bash
# Auto-installed by launchers, or manually:
pip install redis psycopg2-binary
```

## 🆘 Troubleshooting

### Dashboard Won't Start

```bash
# Check if port 8000 is in use
netstat -an | findstr "8000"

# Try different port
python service_dashboard.py --port 9000
```

### Service Shows "Stopped"

```bash
# Restart Redis
docker restart bookmap-redis-stack

# Restart PostgreSQL
Restart-Service postgresql-x64-17
```

### Connection Failed

```bash
# Test manually
docker exec bookmap-redis-stack redis-cli PING
psql -U postgres -d trading_data -c "SELECT 1;"
```

## 💡 Pro Tips

1. **Bookmark it**: Add http://localhost:8000 to browser bookmarks
2. **Startup script**: Add launcher to Windows startup folder
3. **Second monitor**: Keep dashboard open during development
4. **Mobile access**: Edit to bind `0.0.0.0` instead of `localhost` (on trusted network only)
5. **Custom logs**: Add your own log files to `LOG_FILES` dict
6. **Alert scripts**: Use API endpoint to trigger alerts when services fail

## 📸 Expected Output

### Console (Quick Check)

```
======================================================================
  TRADING SYSTEM STATUS CHECK
======================================================================

Checking Redis Docker...
  ✓ Redis Docker: Running (Up 2 hours)
Checking Redis connection...
  ✓ Redis Connection: OK (PONG received)
Checking PostgreSQL service...
  ✓ PostgreSQL Service: Running
Checking TimescaleDB connection...
  ✓ TimescaleDB: Connected
Checking MBO data collection...
  ✓ MBO Data: 1234 records in last 5 minutes
Checking Stops/Icebergs collection...
  ✓ Stops/Icebergs: 419 events in last 5 minutes

======================================================================
  STATUS CHECK COMPLETE
======================================================================

For detailed monitoring, run: .\start_dashboard.bat
```

### Browser (Dashboard)

- Modern gradient background (purple/blue)
- White cards with rounded corners
- Green/Red status badges
- Dark terminal-style log viewers
- Auto-updating every 5 seconds

## 🔒 Security

- Dashboard runs locally only (localhost:8000)
- PostgreSQL password in script (keep file secure)
- No external network access required
- All data stays on your machine

## 📚 Documentation

| File                           | Purpose                              |
| ------------------------------ | ------------------------------------ |
| `DASHBOARD_README.md`          | Full documentation with all features |
| `DASHBOARD_QUICK_REFERENCE.md` | Quick lookup guide                   |
| This file                      | Overview and quick start             |

## 🎉 What's Next?

Now you can:

1. ✅ Monitor all services from one dashboard
2. ✅ View live logs without opening log files
3. ✅ Check database health at a glance
4. ✅ Verify data collection in real-time
5. ✅ Quickly diagnose issues

**Your trading infrastructure monitoring is complete!** 🚀📊

---

**Happy Trading! May your services stay green! 💚**
