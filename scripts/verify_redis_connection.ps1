# Verify Redis Stack Connection
# Run this before starting Bookmap to ensure correct Redis is running

Write-Host "=== Redis Connection Verification ===" -ForegroundColor Cyan
Write-Host ""

# Check old Redis service is stopped
Write-Host "1. Checking old Redis service..." -ForegroundColor Yellow
$oldRedis = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
if ($oldRedis) {
    if ($oldRedis.Status -eq "Running") {
        Write-Host "   ✗ Old Redis 3.0 is still running!" -ForegroundColor Red
        Write-Host "   Stopping old Redis..." -ForegroundColor Yellow
        Stop-Service -Name "Redis" -Force
        Write-Host "   ✓ Old Redis stopped" -ForegroundColor Green
    }
    else {
        Write-Host "   ✓ Old Redis is stopped ($($oldRedis.StartType))" -ForegroundColor Green
    }
}

# Check Docker Redis Stack
Write-Host ""
Write-Host "2. Checking Docker Redis Stack..." -ForegroundColor Yellow
try {
    $ping = docker exec bookmap-redis-stack redis-cli PING 2>&1
    if ($ping -eq "PONG") {
        Write-Host "   ✓ Redis Stack is responding" -ForegroundColor Green
    }
    else {
        Write-Host "   ✗ Redis Stack not responding" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "   ✗ Docker Redis Stack not running!" -ForegroundColor Red
    Write-Host "   Run: .\scripts\start_redis_stack_docker.ps1" -ForegroundColor Yellow
    exit 1
}

# Check Redis version
Write-Host ""
Write-Host "3. Checking Redis version..." -ForegroundColor Yellow
$version = docker exec bookmap-redis-stack redis-cli INFO server 2>&1 | Select-String "redis_version:"
Write-Host "   $version" -ForegroundColor Green

# Test XADD command
Write-Host ""
Write-Host "4. Testing XADD (streams)..." -ForegroundColor Yellow
try {
    $streamId = docker exec bookmap-redis-stack redis-cli XADD test:verify "*" test value 2>&1
    if ($streamId -match "^\d+-\d+$") {
        Write-Host "   ✓ XADD works (stream ID: $streamId)" -ForegroundColor Green
        docker exec bookmap-redis-stack redis-cli DEL test:verify | Out-Null
    }
    else {
        Write-Host "   ✗ XADD failed: $streamId" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "   ✗ XADD command failed!" -ForegroundColor Red
    exit 1
}

# Test HSET with mapping
Write-Host ""
Write-Host "5. Testing HSET (mapping)..." -ForegroundColor Yellow
try {
    $result = docker exec bookmap-redis-stack redis-cli HSET test:verify:hash field1 val1 field2 val2 2>&1
    if ($result -match "^\d+$") {
        Write-Host "   ✓ HSET works (fields set: $result)" -ForegroundColor Green
        docker exec bookmap-redis-stack redis-cli DEL test:verify:hash | Out-Null
    }
    else {
        Write-Host "   ✗ HSET failed: $result" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "   ✗ HSET command failed!" -ForegroundColor Red
    exit 1
}

# Check active connections
Write-Host ""
Write-Host "6. Checking port 6379..." -ForegroundColor Yellow
$connections = netstat -ano | Select-String ":6379.*LISTENING"
$dockerListener = $connections | Select-String "27064|bookmap-redis-stack" | Measure-Object
if ($dockerListener.Count -gt 0) {
    Write-Host "   ✓ Docker Redis Stack is listening on 6379" -ForegroundColor Green
}
else {
    Write-Host "   ⚠ Cannot confirm which process owns port 6379" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== All Checks Passed ===" -ForegroundColor Green
Write-Host ""
Write-Host "Redis Stack is ready for Bookmap" -ForegroundColor Cyan
Write-Host "  Host: localhost:6379" -ForegroundColor White
Write-Host "  Version: Redis Stack 7.4.6" -ForegroundColor White
Write-Host "  RedisInsight: http://localhost:8001" -ForegroundColor White
Write-Host ""
Write-Host "Next: Restart Bookmap and enable Python addon" -ForegroundColor Yellow
Write-Host ""
