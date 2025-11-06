# Bookmap Startup Checklist

Run these checks **before starting Bookmap** to ensure everything is configured correctly.

## Quick Check (Run Every Time)

```powershell
.\scripts\verify_redis_connection.ps1
```

This verifies:
- ✓ Old Redis 3.0 service is stopped
- ✓ Docker Redis Stack 7.4.6 is running
- ✓ XADD (streams) command works
- ✓ HSET (mapping) command works
- ✓ Port 6379 is owned by Docker Redis Stack

## Full Startup Sequence

### 1. Start Docker Services

```powershell
.\scripts\start_redis_stack_docker.ps1
```

**Expected Output:**
```
✓ Docker daemon is running
✓ Images pulled
✓ Containers started
✓ Redis Stack is running
   redis_version:7.4.6
✓ TimescaleDB is running
   TimescaleDB version: 2.22.1
```

### 2. Verify Connections

```powershell
.\scripts\verify_redis_connection.ps1
```

**Expected Output:**
```
=== All Checks Passed ===
Redis Stack is ready for Bookmap
```

### 3. Start Bookmap

- Open Bookmap application
- Wait for connection to data feed (Rithmic, etc.)

### 4. Enable Python Addon

- Right-click chart → **Add Indicator**
- Find **"MBO_Automated_v3"** or **"MBO Consumer"**
- Enable for your instrument (e.g., MNQZ5.CME)

**Expected Log Messages:**
```
[2025-10-28 23:xx:xx] [INFO] ✓ Redis connected: localhost:6379
[2025-10-28 23:xx:xx] [INFO] ✓ TimescaleDB connected: PostgreSQL 17.6
[2025-10-28 23:xx:xx] [INFO] Session started: MNQZ5.CME_20251028_230000_abc123
```

**NO "unknown command 'XADD'" errors!**

### 5. Enable Java Consumers (Optional)

Add these indicators to chart:
- **"OHLC Candle Consumer"** - Real-time candle generation
- **"Absorption Consumer"** - Absorption/sweep detection
- **"Stops & Icebergs Consumer"** - Stop/iceberg detection

### 6. Monitor Data Flow

**RedisInsight (Web UI):**
```
http://localhost:8001
```

Look for keys:
- `mbo:trades:MNQZ5.CME` (stream)
- `mbo:orders:MNQZ5.CME:bid` (sorted set)
- `mbo:orders:MNQZ5.CME:ask` (sorted set)
- `mbo:stats:MNQZ5.CME` (hash)
- `candle:MNQZ5.CME:1m:current` (hash)

**TimescaleDB (PostgreSQL):**
```powershell
docker exec -it bookmap-timescaledb psql -U postgres -d trading_data
```

Check data:
```sql
-- Count MBO records
SELECT COUNT(*) FROM mbo_data;

-- Recent MBO events
SELECT * FROM mbo_data ORDER BY timestamp DESC LIMIT 10;

-- Recent candles
SELECT * FROM ohlc_candles ORDER BY timestamp DESC LIMIT 10;

-- Check CBDR window activity
SELECT cbdr_window, COUNT(*) 
FROM mbo_data 
WHERE cbdr_window IS NOT NULL 
GROUP BY cbdr_window;
```

## Troubleshooting

### Problem: "unknown command 'XADD'"

**Cause:** Old Redis 3.0 service is running instead of Docker Redis Stack

**Fix:**
```powershell
Stop-Service -Name "Redis" -Force
Set-Service -Name "Redis" -StartupType Disabled
.\scripts\verify_redis_connection.ps1
```

### Problem: Port 6379 already in use

**Check what's using it:**
```powershell
netstat -ano | findstr :6379
```

**If old Redis (PID 25608 or similar):**
```powershell
Stop-Service -Name "Redis" -Force
```

**If another Docker container:**
```powershell
docker ps -a | Select-String "6379"
docker stop <container_name>
```

### Problem: Docker Redis Stack not starting

**Check Docker Desktop is running:**
```powershell
docker info
```

**Restart Docker containers:**
```powershell
docker-compose restart
```

**View logs:**
```powershell
docker-compose logs -f redis-stack
```

### Problem: Bookmap can't connect to TimescaleDB

**Verify TimescaleDB is running:**
```powershell
docker exec bookmap-timescaledb psql -U postgres -d trading_data -c "SELECT version();"
```

**Check password in config:**
```
F:\Databases\database_config.properties
timescaledb.password=X74Ot*BvtjgKuCBx
```

### Problem: No data appearing in Redis

**Check Bookmap logs for errors**

**Verify addon is enabled:**
- Settings → Manage Addons → Check "MBO_Automated_v3" is enabled

**Check CBDR window:**
```powershell
# Current time in EST
Get-Date -Format "yyyy-MM-dd HH:mm:ss"
```

Data only stored during CBDR windows:
- PM/Asian: 16:00-20:00 EST
- London: 02:00-05:00 EST
- Pre-NY: 07:30-09:30 EST

Outside these windows, addon runs but doesn't store data to preserve resources.

## Daily Workflow

### Morning (Before Market)

```powershell
# 1. Start Docker services
.\scripts\start_redis_stack_docker.ps1

# 2. Verify connections
.\scripts\verify_redis_connection.ps1

# 3. Start Bookmap and enable addons
```

### During Trading

- Monitor RedisInsight for real-time data
- Check Bookmap logs for any errors
- Query TimescaleDB for historical analysis

### End of Day

```powershell
# Optional: Stop Docker to free resources
.\scripts\stop_redis_stack_docker.ps1
```

Data persists in Docker volumes, so you can restart anytime without data loss.

## Automated Startup Script

Create a shortcut to this script:

```powershell
# startup_bookmap_stack.ps1
.\scripts\start_redis_stack_docker.ps1
Start-Sleep -Seconds 5
.\scripts\verify_redis_connection.ps1
Write-Host ""
Write-Host "Ready to start Bookmap!" -ForegroundColor Green
```

Run before launching Bookmap each day.

## References

- Docker Setup: `DOCKER_SETUP.md`
- Redis Migration: `REDIS_MIGRATION_SUMMARY.md`
- Database Schema: `database/init_timescaledb.sql`
- Redis Keys: `database/REDIS_KEY_STRUCTURE.md`
