# Service Dashboard - Quick Reference

## 🚀 Launch Commands

```bash
# Windows (Double-click)
start_dashboard.bat

# PowerShell
.\start_dashboard.ps1

# Python
python service_dashboard.py
```

**URL:** http://localhost:8000

## 📊 Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│                    🖥️ SERVICE DASHBOARD                      │
│                 Last Update: 2025-11-02 11:32:38            │
├─────────────────────────────────────────────────────────────┤
│  🔴 Redis           │  🐳 Redis Docker                       │
│  Status: Running    │  Status: Running                       │
│  Port: 6879         │  Container: bookmap-redis-stack       │
│  Keys: 1,234,567    │  Docker Status: Up 2 hours            │
├─────────────────────────────────────────────────────────────┤
│  🐘 TimescaleDB     │  ⚙️ PostgreSQL Service                │
│  Status: Running    │  Status: Running                       │
│  Port: 5432         │  Service: postgresql-x64-17           │
│  Size: 2.5 GB       │  Windows Status: Running              │
├─────────────────────────────────────────────────────────────┤
│              📊 Database Tables (trading_data)              │
│  ┌──────────────┬──────────────┬──────────────┬───────────┐│
│  │ mbo_data     │ stops_icebergs│ ohlc_candles│absorption ││
│  │ 12,732,544   │ 419          │ 0           │ 0         ││
│  └──────────────┴──────────────┴──────────────┴───────────┘│
├─────────────────────────────────────────────────────────────┤
│  📝 MBO Consumer Log        │  📝 Quarterly Theory Log      │
│  ┌──────────────────────┐   │  ┌──────────────────────┐    │
│  │ [2025-10-31 20:01]  │   │  │ [2025-10-31 15:30]  │    │
│  │ ✓ Inserted 2000     │   │  │ Session started      │    │
│  │ records             │   │  │ Monitoring cycles    │    │
│  └──────────────────────┘   │  └──────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  📝 PostgreSQL Log                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Database system ready to accept connections         │   │
│  │ Checkpoint complete                                 │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│           Dashboard will auto-refresh every 5 seconds       │
└─────────────────────────────────────────────────────────────┘
```

## 🎨 Status Badges

| Badge Color | Meaning           |
| ----------- | ----------------- |
| 🟢 Green    | Running (Healthy) |
| 🔴 Red      | Stopped (Down)    |
| 🟡 Yellow   | Error (Degraded)  |
| ⚪ Gray     | Unknown (No info) |

## 📈 What's Monitored

### Redis

- ✓ Connection health (PING test)
- ✓ Port status (6879)
- ✓ Memory usage
- ✓ Number of keys
- ✓ Connected clients
- ✓ Uptime in days
- ✓ Total commands processed

### TimescaleDB

- ✓ Connection health
- ✓ Port status (5432)
- ✓ Database size (trading_data)
- ✓ Active connections
- ✓ Table record counts
- ✓ PostgreSQL version

### Docker

- ✓ Container status (bookmap-redis-stack)
- ✓ Container uptime

### Windows Service

- ✓ Service status (postgresql-x64-17)
- ✓ Service state (Running/Stopped)

## 📝 Log Files

```
F:/Databases/Logs/
├── MBO_Consumer.log              (MBO data collection)
└── quarterly_theory_engine.log   (Trading strategy engine)

C:/Program Files/PostgreSQL/17/data/log/
└── postgresql-*.log              (Database server logs)
```

## 🔧 Configuration

Edit these values in `service_dashboard.py`:

```python
# Database connection
REDIS_PORT = 6879           # Your Redis port
TIMESCALE_PORT = 5432       # Your PostgreSQL port
TIMESCALE_DB = "trading_data"
TIMESCALE_PASSWORD = "your_password"

# Web server
run_server(port=8000)       # Dashboard port

# Auto-refresh (in HTML)
setTimeout(..., 5000)       # Refresh interval (ms)

# Log tail size
get_log_tail(log_file, lines=20)  # Lines to show
```

## 🛠️ Troubleshooting

### Service Shows "Stopped" But It's Running

- **Redis**: Check if container is running: `docker ps`
- **PostgreSQL**: Check service: `Get-Service postgresql-x64-17`
- **Port conflict**: Verify ports aren't blocked by firewall

### Connection Failed

```bash
# Test Redis manually
docker exec bookmap-redis-stack redis-cli PING

# Test PostgreSQL manually
psql -U postgres -d trading_data -c "SELECT 1;"
```

### Dashboard Won't Start

```bash
# Check port availability
netstat -an | findstr "8000"

# Try different port
python service_dashboard.py --port 9000
```

### Missing Dependencies

```bash
pip install redis psycopg2-binary
```

## 📊 API Endpoint

```bash
# Get JSON status
curl http://localhost:8000/api/status

# Use in scripts
$status = Invoke-RestMethod -Uri "http://localhost:8000/api/status"
Write-Host "Redis Status: $($status.services.redis.status)"
```

## 💡 Pro Tips

1. **Keep it open**: Run on second monitor during development
2. **Morning check**: First thing to verify after PC restart
3. **Before trading**: Verify all green before going live
4. **Debugging**: Watch logs update in real-time
5. **Integration**: Use `/api/status` endpoint in automation scripts

## 🔥 Quick Health Check

**All services healthy when:**

- ✅ Redis: Green badge, Port 6879, Keys > 0
- ✅ Redis Docker: Green badge, Container Up
- ✅ TimescaleDB: Green badge, Port 5432, Tables have records
- ✅ PostgreSQL Service: Green badge, Running status

## 🆘 Emergency Commands

```bash
# Restart Redis
docker restart bookmap-redis-stack

# Restart PostgreSQL
Restart-Service postgresql-x64-17

# Check all services quickly
Get-Service postgresql-x64-17; docker ps --filter "name=bookmap"
```

## 📱 Mobile View

Dashboard is responsive! Open on phone/tablet:

1. Find your computer's IP: `ipconfig`
2. Edit `service_dashboard.py`: Change `localhost` to `0.0.0.0`
3. Open `http://YOUR_IP:8000` on mobile

⚠️ **Security Warning**: Only use on trusted networks!

---

**Happy Monitoring! 📊🚀**
