# Redis Stack Migration Summary

## ✅ Migration Complete

### What Changed

**From:** Redis 3.0.504 (Windows Service, 2015 release)
**To:** Redis Stack 7.4.6 (Docker, latest with modern features)

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Docker Compose (docker-compose.yml)                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────┐  ┌───────────────────┐   │
│  │ Redis Stack 7.4.6    │  │ TimescaleDB 2.22  │   │
│  │ Port: 6379           │  │ Port: 5432        │   │
│  │ RedisInsight: 8001   │  │ DB: trading_data  │   │
│  └──────────────────────┘  └───────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Code Updates

### Python (MBO_Redis_Consumer.py) - UPDATED ✅

**Changed from Redis 3.0 compatibility to modern syntax:**

```python
# OLD (Redis 3.0)
redis_client.zadd(key, price, order_data)  # Positional args
redis_client.lpush(key, trade_data)  # Lists instead of streams
redis_client.hset(key, "field1", val1)  # Individual calls
redis_client.hset(key, "field2", val2)

# NEW (Redis Stack 7.4)
redis_client.zadd(key, {order_data: price})  # Dict mapping
redis_client.xadd(key, trade_data, maxlen=10000)  # Streams
redis_client.hset(key, mapping={
    "field1": val1,
    "field2": val2
})  # Single mapping call
```

### Java Consumers - NO CHANGES NEEDED ✅

**Already compatible** because:
- Using **Jedis 5.1.0** (modern Redis client)
- Jedis automatically uses correct syntax for Redis version
- All commands work with both Redis 3.0 and Redis Stack

**Verified working:**
```java
// These all work with Redis Stack out of the box
jedis.hset(key, Map)  // Modern HSET
jedis.xadd(streamKey, streamData, XAddParams)  // Streams
jedis.zadd(key, score, member)  // Modern ZADD
```

## New Features Available

### Redis Stack Modules

1. **RedisJSON** - Store/query JSON directly
   ```bash
   JSON.SET user:1 $ '{"name":"trader","balance":10000}'
   JSON.GET user:1 $.balance
   ```

2. **RediSearch** - Full-text search
   ```bash
   FT.CREATE idx:trades SCHEMA symbol TAG price NUMERIC
   FT.SEARCH idx:trades "@symbol:{MNQZ5}"
   ```

3. **RedisTimeSeries** - Built-in time-series
   ```bash
   TS.ADD price:MNQ 1635724800 19500.25
   TS.RANGE price:MNQ 1635724800 1635811200
   ```

4. **RedisGraph** - Graph database (if needed for relationships)

### Redis Streams (Now Available)

**Python addon uses streams for trades:**
```python
# Store trade as stream entry
redis_client.xadd("mbo:trades:MNQZ5.CME", {
    "trade_id": "12345",
    "price": "19500.25",
    "size": "10",
    "timestamp": "2025-10-28T19:00:00Z"
}, maxlen=10000)

# Read recent trades
trades = redis_client.xrevrange("mbo:trades:MNQZ5.CME", count=100)
```

## Management

### Start/Stop Services

```powershell
# Start everything
.\scripts\start_redis_stack_docker.ps1

# Stop everything
.\scripts\stop_redis_stack_docker.ps1

# Remove all data
docker-compose down -v
```

### Access Tools

**RedisInsight Web UI:**
- URL: http://localhost:8001
- Visual key browser, real-time monitoring, query builder

**Redis CLI:**
```powershell
docker exec -it bookmap-redis-stack redis-cli
```

**TimescaleDB CLI:**
```powershell
docker exec -it bookmap-timescaledb psql -U postgres -d trading_data
```

### View Logs

```powershell
# All services
docker-compose logs -f

# Redis only
docker-compose logs -f redis-stack

# TimescaleDB only
docker-compose logs -f timescaledb
```

## Data Storage

### Redis (Hot Storage)

**Current candles** (real-time):
```
candle:MNQZ5.CME:1m:current -> Hash
candle:MNQZ5.CME:5m:current -> Hash
```

**MBO orders** (bid/ask sorted by price):
```
mbo:orders:MNQZ5.CME:bid -> Sorted Set
mbo:orders:MNQZ5.CME:ask -> Sorted Set
```

**Trade stream** (chronological):
```
mbo:trades:MNQZ5.CME -> Stream (XADD)
```

**Session stats**:
```
mbo:stats:MNQZ5.CME -> Hash
```

### TimescaleDB (Cold Storage)

**Hypertables** (time-series optimized):
```sql
mbo_data          -- Market by order events
ohlc_candles      -- OHLC candles (all timeframes)
stops_icebergs    -- Stop/iceberg detections
absorption_events -- Absorption/sweep events
trading_sessions  -- Session metadata
market_bias       -- Trading bias signals
```

## Deployment Workflow

1. **Start Docker services** (if not running):
   ```powershell
   .\scripts\start_redis_stack_docker.ps1
   ```

2. **Build addons** (if code changed):
   ```powershell
   .\gradlew.bat clean build
   ```

3. **Restart Bookmap**:
   - Close Bookmap completely
   - Start Bookmap
   - Add addons to chart

4. **Monitor data**:
   - RedisInsight: http://localhost:8001
   - Bookmap logs: Watch for connection messages
   - Database queries: Use psql or Redis CLI

## Verification

### Check Redis is working

```powershell
# Ping Redis
docker exec bookmap-redis-stack redis-cli PING

# Check version
docker exec bookmap-redis-stack redis-cli INFO server | Select-String "redis_version"

# List all keys
docker exec bookmap-redis-stack redis-cli KEYS "*"

# Watch real-time commands
docker exec bookmap-redis-stack redis-cli MONITOR
```

### Check TimescaleDB is working

```powershell
# Check version
docker exec bookmap-timescaledb psql -U postgres -d trading_data -c "SELECT version();"

# List tables
docker exec bookmap-timescaledb psql -U postgres -d trading_data -c "\dt"

# Count MBO records
docker exec bookmap-timescaledb psql -U postgres -d trading_data -c "SELECT COUNT(*) FROM mbo_data;"

# Check recent data
docker exec bookmap-timescaledb psql -U postgres -d trading_data -c "SELECT * FROM mbo_data ORDER BY timestamp DESC LIMIT 5;"
```

## Troubleshooting

### Port conflicts

If ports 6379 or 5432 are in use:

```powershell
# Check what's using the port
netstat -ano | findstr :6379
netstat -ano | findstr :5432

# Stop old Redis service
Stop-Service Redis

# Kill process by PID
taskkill /PID <PID> /F
```

### Container issues

```powershell
# Restart containers
docker-compose restart

# Rebuild containers
docker-compose up -d --force-recreate

# Check container status
docker ps -a

# View container logs
docker logs bookmap-redis-stack
docker logs bookmap-timescaledb
```

### Data persistence

Data is stored in Docker volumes and persists across restarts:
```powershell
# List volumes
docker volume ls

# Backup Redis data
docker exec bookmap-redis-stack redis-cli SAVE
docker cp bookmap-redis-stack:/data/dump.rdb ./backup/

# Backup TimescaleDB
docker exec bookmap-timescaledb pg_dump -U postgres trading_data > backup/trading_data.sql
```

## Performance Notes

### Redis Stack

- **Max Memory**: 2GB (configured in docker-compose.yml)
- **Eviction Policy**: allkeys-lru (least recently used)
- **Persistence**: RDB snapshots + AOF (append-only file)
- **Connection Pool**: 50 max connections (Java), Python uses single connection

### Expected Throughput

- **MBO events**: 1000-5000 events/second
- **Candle updates**: 60+ updates/second (1m timeframe)
- **Batch inserts**: 500 records/5 seconds to TimescaleDB

## Migration Checklist

- [x] Install Docker Desktop
- [x] Create docker-compose.yml
- [x] Start Redis Stack container
- [x] Start TimescaleDB container
- [x] Update Python addon for modern Redis syntax
- [x] Verify Java consumers (no changes needed)
- [x] Rebuild Python addon JAR
- [x] Test Redis connections
- [x] Test TimescaleDB connections
- [x] Open RedisInsight UI
- [x] Verify database schema
- [ ] Deploy to Bookmap (user's next step)
- [ ] Monitor real-time data capture
- [ ] Build dashboard for signals

## Next Steps

1. **Restart Bookmap** with new Redis Stack connection
2. **Add Python addon** to chart (MBO_Consumer_Python)
3. **Add Java consumers** to chart:
   - OHLC Candle Consumer
   - Absorption Consumer
   - Stops & Icebergs Consumer
4. **Monitor RedisInsight** for real-time keys
5. **Query TimescaleDB** for historical data
6. **Build trading dashboard** using Redis queries

## References

- Docker Setup: `DOCKER_SETUP.md`
- Redis Stack Docs: https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/docker/
- Jedis Documentation: https://github.com/redis/jedis
- TimescaleDB Docs: https://docs.timescale.com/
