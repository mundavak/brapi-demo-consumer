# Start Redis Stack and TimescaleDB using Docker
# Requires Docker Desktop for Windows

Write-Host "=== Starting Bookmap Trading Stack (Docker) ===" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
Write-Host "1. Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "   ✓ $dockerVersion" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Docker not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Docker Desktop from:" -ForegroundColor Yellow
    Write-Host "https://www.docker.com/products/docker-desktop/" -ForegroundColor Cyan
    exit 1
}

# Check if Docker daemon is running
Write-Host ""
Write-Host "2. Checking Docker daemon..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "   ✓ Docker daemon is running" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Docker daemon is not running!" -ForegroundColor Red
    Write-Host "   Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# Navigate to project directory
$projectRoot = "F:\TradingAgent\deaProjects\brapi-demo-consumer"
Set-Location $projectRoot

# Stop existing containers
Write-Host ""
Write-Host "3. Stopping existing containers..." -ForegroundColor Yellow
try {
    docker-compose down 2>&1 | Out-Null
    Write-Host "   ✓ Old containers stopped" -ForegroundColor Green
}
catch {
    Write-Host "   ⚠ No existing containers" -ForegroundColor Gray
}

# Pull latest images
Write-Host ""
Write-Host "4. Pulling latest images..." -ForegroundColor Yellow
Write-Host "   (This may take a few minutes on first run)" -ForegroundColor Gray
try {
    docker-compose pull
    Write-Host "   ✓ Images pulled" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Failed to pull images: $_" -ForegroundColor Red
    exit 1
}

# Start containers
Write-Host ""
Write-Host "5. Starting containers..." -ForegroundColor Yellow
try {
    docker-compose up -d
    Write-Host "   ✓ Containers started" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Failed to start containers: $_" -ForegroundColor Red
    exit 1
}

# Wait for services to be ready
Write-Host ""
Write-Host "6. Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check Redis Stack
Write-Host ""
Write-Host "7. Verifying Redis Stack..." -ForegroundColor Yellow
try {
    $redisInfo = docker exec bookmap-redis-stack redis-cli INFO server | Select-String "redis_version"
    Write-Host "   $redisInfo" -ForegroundColor Green
    
    # Test modern commands
    Write-Host "   Testing XADD (streams)..." -ForegroundColor Gray
    docker exec bookmap-redis-stack redis-cli XADD test:stream "*" field value | Out-Null
    Write-Host "   ✓ Redis Streams working" -ForegroundColor Green
    
    Write-Host "   Testing HSET (modern syntax)..." -ForegroundColor Gray
    docker exec bookmap-redis-stack redis-cli HSET test:hash field1 val1 field2 val2 | Out-Null
    Write-Host "   ✓ Modern HSET working" -ForegroundColor Green
    
    # Cleanup test keys
    docker exec bookmap-redis-stack redis-cli DEL test:stream test:hash | Out-Null
}
catch {
    Write-Host "   ✗ Redis Stack verification failed: $_" -ForegroundColor Red
}

# Check TimescaleDB
Write-Host ""
Write-Host "8. Verifying TimescaleDB..." -ForegroundColor Yellow
try {
    $pgVersion = docker exec bookmap-timescaledb psql -U postgres -d trading_data -c "SELECT version();" -t
    Write-Host "   ✓ PostgreSQL connected" -ForegroundColor Green
    
    $tsVersion = docker exec bookmap-timescaledb psql -U postgres -d trading_data -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';" -t
    Write-Host "   ✓ TimescaleDB version: $tsVersion" -ForegroundColor Green
}
catch {
    Write-Host "   ⚠ TimescaleDB verification failed (may still be initializing)" -ForegroundColor Yellow
}

# Display connection info
Write-Host ""
Write-Host "=== Services Running ===" -ForegroundColor Green
Write-Host ""
Write-Host "Redis Stack:" -ForegroundColor Cyan
Write-Host "  Host: localhost:6379" -ForegroundColor White
Write-Host "  RedisInsight UI: http://localhost:8001" -ForegroundColor White
Write-Host "  Container: bookmap-redis-stack" -ForegroundColor Gray
Write-Host ""
Write-Host "TimescaleDB:" -ForegroundColor Cyan
Write-Host "  Host: localhost:5432" -ForegroundColor White
Write-Host "  Database: trading_data" -ForegroundColor White
Write-Host "  User: postgres" -ForegroundColor White
Write-Host "  Container: bookmap-timescaledb" -ForegroundColor Gray
Write-Host ""
Write-Host "Management Commands:" -ForegroundColor Cyan
Write-Host "  View logs:    docker-compose logs -f" -ForegroundColor White
Write-Host "  Stop:         docker-compose stop" -ForegroundColor White
Write-Host "  Restart:      docker-compose restart" -ForegroundColor White
Write-Host "  Remove:       docker-compose down -v" -ForegroundColor White
Write-Host ""
Write-Host "Redis CLI:" -ForegroundColor Cyan
Write-Host "  docker exec -it bookmap-redis-stack redis-cli" -ForegroundColor White
Write-Host ""
Write-Host "PostgreSQL CLI:" -ForegroundColor Cyan
Write-Host "  docker exec -it bookmap-timescaledb psql -U postgres -d trading_data" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Open RedisInsight: http://localhost:8001" -ForegroundColor White
Write-Host "  2. Rebuild addon: .\gradlew.bat clean pythonAddonJar" -ForegroundColor White
Write-Host "  3. Restart Bookmap and verify no Redis errors" -ForegroundColor White
Write-Host ""
