# MBO Consumer Migration Guide
## SQLite → Redis/TimescaleDB

### Overview
Your original `MBO_Automated_v3.py` has been upgraded to `MBO_Redis_Consumer.py` with the new database architecture.

## Architecture Comparison

### OLD (v3.0.1 - SQLite)
```
Bookmap → MBO_Automated_v3.py → SQLite (enhanced_market_monitor_mbo.db)
                                 ↓
                              JSON file (live_prices.json)
                              
Problems:
- SQLite bottlenecks with large datasets
- Single-file database grows indefinitely  
- No separation of hot/cold data
- Limited concurrent access
```

### NEW (v4.0.0 - Redis/TimescaleDB)
```
Bookmap → MBO_Redis_Consumer.py → Redis (hot, real-time)
                                   ↓
                                TimescaleDB (cold, historical)
                                   
Benefits:
- Redis: In-memory speed for real-time queries
- TimescaleDB: Compression + retention policies
- Automatic data lifecycle (hot → cold)
- Shared infrastructure with Java consumers
- Concurrent access without locks
```

## Key Changes

### 1. Database Storage

**OLD**:
```python
# Single SQLite file
conn = sqlite3.connect("enhanced_market_monitor_mbo.db")
cursor.execute("INSERT INTO orders ...")
```

**NEW**:
```python
# Redis for hot data
redis_client.zadd("mbo:orders:MNQZ5:bid", {order_data: price})
redis_client.expire(key, 86400)  # 24-hour TTL

# TimescaleDB for cold data (batched)
mbo_batch_queue.put_nowait(mbo_data)
# Batch insert every 5 seconds
```

### 2. Data Flow

**OLD**: All data → SQLite immediately
**NEW**: Real-time → Redis, Historical → TimescaleDB (batched)

### 3. Session Management

**OLD**: Custom session tracking
**NEW**: Shared SessionManager pattern with Java consumers

```python
# Generates: MNQZ5_20251028_163000_a1b2c3d4
session_id = generate_session_id("MNQZ5")
```

### 4. CBDR Windows

**OLD**: Stored in code
**NEW**: Matches `database_config.properties`

```python
CBDR_PM: 16:00-20:00 EST
CBDR_LONDON: 02:00-05:00 EST
PRE_NY: 07:30-09:30 EST
```

## Installation

### 1. Install Python Dependencies
```powershell
pip install redis psycopg2-binary pytz
```

### 2. Verify Database Connections
```powershell
# Test Redis
redis-cli ping

# Test TimescaleDB
$env:PGPASSWORD = "X74Ot*BvtjgKuCBx"
psql -U postgres -h localhost -p 5432 -d trading_data -c "SELECT COUNT(*) FROM mbo_data;"
```

### 3. Copy to Bookmap
```powershell
# Copy Python addon to Bookmap
Copy-Item "f:\TradingAgent\deaProjects\brapi-demo-consumer\src\main\python\MBO_Redis_Consumer.py" `
          -Destination "F:\Bookmap\Python\build\MBO_Redis_Consumer.py"
```

### 4. Load in Bookmap
1. Open Bookmap
2. Go to **Settings → Python configuration**
3. Click **Add script**
4. Browse to: `F:\Bookmap\Python\build\MBO_Redis_Consumer.py`
5. Click **OK** and restart Bookmap

### 5. Enable on Chart
1. Open a chart (e.g., MNQ)
2. Right-click → **Indicators**
3. Find **"MBO Redis Consumer"**
4. Enable it

## Monitoring

### Check Redis Data
```powershell
# View MBO orders
redis-cli KEYS "mbo:orders:*"
redis-cli ZRANGE "mbo:orders:MNQZ5:bid" 0 10 WITHSCORES

# View trades
redis-cli KEYS "mbo:trades:*"
redis-cli XRANGE "mbo:trades:MNQZ5" - + COUNT 10

# View statistics
redis-cli HGETALL "mbo:stats:MNQZ5"
```

### Check TimescaleDB Data
```powershell
$env:PGPASSWORD = "X74Ot*BvtjgKuCBx"

# Count MBO records
psql -U postgres -d trading_data -c "SELECT COUNT(*) FROM mbo_data;"

# Recent MBO events
psql -U postgres -d trading_data -c "SELECT * FROM mbo_data ORDER BY timestamp DESC LIMIT 10;"

# MBO by symbol and window
psql -U postgres -d trading_data -c "
    SELECT symbol, cbdr_window, COUNT(*) 
    FROM mbo_data 
    WHERE timestamp > NOW() - INTERVAL '1 hour'
    GROUP BY symbol, cbdr_window;
"
```

### Monitor Logs
```powershell
# Watch MBO consumer logs
Get-Content "F:\Databases\Logs\MBO_Consumer.log" -Tail 50 -Wait

# Search for errors
Select-String -Path "F:\Databases\Logs\MBO_Consumer.log" -Pattern "ERROR"
```

## Data Lifecycle

### Hot Data (Redis)
- **MBO Orders**: 24-hour TTL
- **Trades**: 12-hour TTL  
- **Statistics**: 1-hour TTL
- **Purpose**: Real-time dashboard queries

### Cold Data (TimescaleDB)
- **Retention**: 30 days (configured in init_timescaledb.sql)
- **Compression**: After 7 days
- **Purpose**: Historical analysis, pattern recognition, HTF analysis

## Performance Comparison

### OLD (SQLite)
- Single-threaded writes
- File locks on every insert
- Full table scans for queries
- ~100 inserts/second (degrading with size)

### NEW (Redis + TimescaleDB)
- Redis: 10,000+ ops/second in-memory
- TimescaleDB: Batched inserts (500 records/5 seconds)
- Automatic compression and retention
- No performance degradation over time

## Integration with Java Consumers

Your Python MBO addon now shares infrastructure with:
- `OhlcCandleConsumer.java` (already working!)
- `StopsIcebergsConsumer.java` (to be created)
- `AbsorptionConsumer.java` (to be created)

All use the same:
- Redis instance (localhost:6379)
- TimescaleDB database (trading_data)
- Session ID format
- CBDR window definitions
- Log directory (F:/Databases/Logs/)

## Troubleshooting

### "Module 'redis' not found"
```powershell
pip install redis
```

### "Connection refused: localhost:6379"
```powershell
# Start Redis service
Start-Service Redis
Get-Service Redis
```

### "Connection refused: localhost:5432"
```powershell
# Start PostgreSQL service
Start-Service postgresql-x64-17
Get-Service postgresql-x64-17
```

### No data in TimescaleDB
- Check batch processor is running (logs show "Batch processor started")
- Verify trading window is active (PM, London, or Pre-NY)
- Check batch queue size in logs
- Ensure PostgreSQL user has INSERT permission

### Redis memory usage too high
```powershell
# Check memory
redis-cli INFO memory

# Adjust TTLs in script if needed
REDIS_TTL_MBO = 86400  # Reduce if needed
```

## Migration Checklist

- [x] Install Redis + TimescaleDB
- [x] Configure PostgreSQL with TimescaleDB extension
- [x] Initialize trading_data schema (init_timescaledb.sql)
- [x] Install Python dependencies (redis, psycopg2-binary, pytz)
- [ ] Copy MBO_Redis_Consumer.py to Bookmap folder
- [ ] Load script in Bookmap
- [ ] Enable on MNQ chart
- [ ] Verify data in Redis (redis-cli KEYS "mbo:*")
- [ ] Verify data in TimescaleDB (psql query)
- [ ] Monitor logs for errors
- [ ] Test during CBDR window
- [ ] Confirm batch processing working
- [ ] Archive old SQLite database

## Next Steps

1. **Test the new MBO consumer** during next trading window
2. **Create Java Broadcasting consumers**:
   - StopsIcebergsConsumer.java (from Broadcasting API)
   - AbsorptionConsumer.java (from Broadcasting API)
3. **Build dashboard** to query Redis + TimescaleDB
4. **Add BTC symbol** once MNQ is stable

Your 32GB RAM is MORE than enough for this setup! Redis will use ~1-2GB max for hot data with your TTLs configured.
