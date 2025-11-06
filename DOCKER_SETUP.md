# Docker Setup for Bookmap Trading System

This project uses **Docker** to run Redis Stack and TimescaleDB, following the official Redis Stack installation guide for Windows.

## Prerequisites

1. **Docker Desktop for Windows**
   - Download: https://www.docker.com/products/docker-desktop/
   - Install and start Docker Desktop
   - Ensure WSL 2 backend is enabled (default)

## Quick Start

### Start All Services
```powershell
.\scripts\start_redis_stack_docker.ps1
```

This will:
- Pull latest Redis Stack and TimescaleDB images
- Start both containers with persistent volumes
- Initialize TimescaleDB schema
- Verify services are running

### Stop Services
```powershell
.\scripts\stop_redis_stack_docker.ps1
```

### Remove Everything (including data)
```powershell
docker-compose down -v
```

## Services

### Redis Stack (Port 6379)
- **Image**: `redis/redis-stack:latest`
- **Container**: `bookmap-redis-stack`
- **Features**:
  - Redis 7.x with all modern commands
  - RedisJSON for structured data
  - RediSearch for full-text search
  - RedisTimeSeries for time-series data
  - RedisInsight web UI (http://localhost:8001)
- **Data**: Persisted in Docker volume `redis-data`
- **Config**: `config/redis.conf`

### TimescaleDB (Port 5432)
- **Image**: `timescale/timescaledb:latest-pg17`
- **Container**: `bookmap-timescaledb`
- **Database**: `trading_data`
- **User**: `postgres`
- **Password**: `X74Ot*BvtjgKuCBx`
- **Data**: Persisted in Docker volume `timescale-data`
- **Init Script**: `database/init_timescaledb.sql` (runs on first start)

## Accessing Services

### Redis CLI
```powershell
# Interactive Redis CLI
docker exec -it bookmap-redis-stack redis-cli

# Run single command
docker exec bookmap-redis-stack redis-cli INFO server

# Test modern features
docker exec bookmap-redis-stack redis-cli XADD test:stream "*" field value
docker exec bookmap-redis-stack redis-cli HSET test:hash key1 val1 key2 val2
```

### RedisInsight Web UI
Open browser: http://localhost:8001
- Visual key browser
- Real-time monitoring
- Query builder
- Stream visualization

### PostgreSQL/TimescaleDB CLI
```powershell
# Interactive psql
docker exec -it bookmap-timescaledb psql -U postgres -d trading_data

# Run single query
docker exec bookmap-timescaledb psql -U postgres -d trading_data -c "SELECT COUNT(*) FROM mbo_data;"
```

## Troubleshooting

### Docker not found
Install Docker Desktop: https://www.docker.com/products/docker-desktop/

### Docker daemon not running
Start Docker Desktop application

### Port conflicts (6379 or 5432 already in use)
```powershell
# Check what's using the port
netstat -ano | findstr :6379
netstat -ano | findstr :5432

# Stop old Redis service
Stop-Service Redis

# Or edit docker-compose.yml to use different ports
```

### Container won't start
```powershell
# View logs
docker-compose logs redis-stack
docker-compose logs timescaledb

# Restart containers
docker-compose restart
```

### Data persistence issues
```powershell
# List volumes
docker volume ls

# Inspect volume
docker volume inspect brapi-demo-consumer_redis-data
docker volume inspect brapi-demo-consumer_timescale-data

# Backup volume
docker run --rm -v brapi-demo-consumer_redis-data:/data -v ${PWD}:/backup alpine tar czf /backup/redis-backup.tar.gz /data
```

## Migration from Windows Service Redis

If you have old Redis 3.0.504 installed as Windows service:

1. **Stop old service**:
   ```powershell
   Stop-Service Redis
   ```

2. **Export data** (optional):
   ```powershell
   redis-cli --rdb dump.rdb
   ```

3. **Start Docker Redis Stack**:
   ```powershell
   .\scripts\start_redis_stack_docker.ps1
   ```

4. **Import data** (optional):
   ```powershell
   docker cp dump.rdb bookmap-redis-stack:/data/
   docker exec bookmap-redis-stack redis-cli --rdb /data/dump.rdb
   ```

## Development Workflow

1. **Start services**: `.\scripts\start_redis_stack_docker.ps1`
2. **Verify running**: Check http://localhost:8001 (RedisInsight)
3. **Build addon**: `.\gradlew.bat clean pythonAddonJar`
4. **Run Bookmap**: Add MBO_Consumer_Python to chart
5. **Monitor data**: Use RedisInsight or psql

## Production Notes

- Docker volumes persist data across container restarts
- Backups should be automated (see TimescaleDB backup docs)
- Consider setting Redis password in production
- Monitor container resource usage
- Use `docker-compose logs -f` to monitor real-time logs

## References

- Redis Stack Docker: https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/docker/
- Redis Stack Windows: https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/windows/
- TimescaleDB Docker: https://docs.timescale.com/self-hosted/latest/install/installation-docker/
- Docker Compose: https://docs.docker.com/compose/
