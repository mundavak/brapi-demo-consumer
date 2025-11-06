# Quick System Status Check
# Run this for a fast command-line status report

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "  TRADING SYSTEM STATUS CHECK" -ForegroundColor White
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

# Redis Docker
Write-Host "Checking Redis Docker..." -ForegroundColor Yellow
$redisDocker = docker ps --filter "name=bookmap-redis-stack" --format "{{.Status}}" 2>$null
if ($redisDocker) {
    Write-Host "  ✓ Redis Docker: " -NoNewline -ForegroundColor Green
    Write-Host "Running ($redisDocker)" -ForegroundColor White
}
else {
    Write-Host "  ✗ Redis Docker: " -NoNewline -ForegroundColor Red
    Write-Host "Not running" -ForegroundColor White
}

# Redis Connection
Write-Host "Checking Redis connection..." -ForegroundColor Yellow
$redisPing = docker exec bookmap-redis-stack redis-cli PING 2>$null
if ($redisPing -eq "PONG") {
    Write-Host "  ✓ Redis Connection: " -NoNewline -ForegroundColor Green
    Write-Host "OK (PONG received)" -ForegroundColor White
}
else {
    Write-Host "  ✗ Redis Connection: " -NoNewline -ForegroundColor Red
    Write-Host "Failed" -ForegroundColor White
}

# PostgreSQL Service
Write-Host "Checking PostgreSQL service..." -ForegroundColor Yellow
$pgService = Get-Service -Name "postgresql-x64-17" -ErrorAction SilentlyContinue
if ($pgService -and $pgService.Status -eq "Running") {
    Write-Host "  ✓ PostgreSQL Service: " -NoNewline -ForegroundColor Green
    Write-Host "Running" -ForegroundColor White
}
else {
    Write-Host "  ✗ PostgreSQL Service: " -NoNewline -ForegroundColor Red
    Write-Host "Not running" -ForegroundColor White
}

# TimescaleDB Connection
Write-Host "Checking TimescaleDB connection..." -ForegroundColor Yellow
$env:PGPASSWORD = "X74Ot*BvtjgKuCBx"
$pgTest = psql -U postgres -d trading_data -c "SELECT 1;" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ TimescaleDB: " -NoNewline -ForegroundColor Green
    Write-Host "Connected" -ForegroundColor White
}
else {
    Write-Host "  ✗ TimescaleDB: " -NoNewline -ForegroundColor Red
    Write-Host "Connection failed" -ForegroundColor White
}

# MBO Data Check
Write-Host "Checking MBO data collection..." -ForegroundColor Yellow
$mboCount = psql -U postgres -d trading_data -t -c "SELECT COUNT(*) FROM mbo_data WHERE timestamp > NOW() - INTERVAL '5 minutes';" 2>$null
if ($LASTEXITCODE -eq 0) {
    $count = ($mboCount | Select-Object -First 1).Trim()
    try {
        $countInt = [int]$count
        if ($countInt -gt 0) {
            Write-Host "  ✓ MBO Data: " -NoNewline -ForegroundColor Green
            Write-Host "$countInt records in last 5 minutes" -ForegroundColor White
        }
        else {
            Write-Host "  ⚠ MBO Data: " -NoNewline -ForegroundColor Yellow
            Write-Host "No recent data (0 records in 5 minutes)" -ForegroundColor White
        }
    }
    catch {
        Write-Host "  ⚠ MBO Data: " -NoNewline -ForegroundColor Yellow
        Write-Host "Unable to parse count" -ForegroundColor White
    }
}

# Stops/Icebergs Data Check
Write-Host "Checking Stops/Icebergs collection..." -ForegroundColor Yellow
$stopsCount = psql -U postgres -d trading_data -t -c "SELECT COUNT(*) FROM stops_icebergs WHERE timestamp > NOW() - INTERVAL '5 minutes';" 2>$null
if ($LASTEXITCODE -eq 0) {
    $count = ($stopsCount | Select-Object -First 1).Trim()
    try {
        $countInt = [int]$count
        if ($countInt -gt 0) {
            Write-Host "  ✓ Stops/Icebergs: " -NoNewline -ForegroundColor Green
            Write-Host "$countInt events in last 5 minutes" -ForegroundColor White
        }
        else {
            Write-Host "  ⚠ Stops/Icebergs: " -NoNewline -ForegroundColor Yellow
            Write-Host "No recent data (0 events in 5 minutes)" -ForegroundColor White
        }
    }
    catch {
        Write-Host "  ⚠ Stops/Icebergs: " -NoNewline -ForegroundColor Yellow
        Write-Host "Unable to parse count" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "  STATUS CHECK COMPLETE" -ForegroundColor White
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""
Write-Host "For detailed monitoring, run: " -NoNewline -ForegroundColor White
Write-Host ".\start_dashboard.bat" -ForegroundColor Cyan
Write-Host ""
