# ============================================
# Database Setup Verification Script
# ============================================

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Database Setup Verification" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

$success = $true

# Load config
$configPath = "F:\Databases\database_config.properties"
if (Test-Path $configPath) {
    Write-Host "✓ Config file found: $configPath" -ForegroundColor Green
    $configContent = Get-Content $configPath | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '=' }
    $config = @{}
    foreach ($line in $configContent) {
        if ($line -match '^\s*([^=]+?)\s*=\s*(.+?)\s*$') {
            $config[$matches[1]] = $matches[2]
        }
    }
}
else {
    Write-Host "✗ Config file not found: $configPath" -ForegroundColor Red
    $success = $false
}

# Test Redis
Write-Host "`n--- Testing Redis ---" -ForegroundColor Yellow
try {
    $redisTest = redis-cli ping 2>&1
    if ($redisTest -match "PONG") {
        Write-Host "✓ Redis is running on localhost:6379" -ForegroundColor Green
        
        # Test basic operations
        redis-cli SET test_verify "testing_123" | Out-Null
        $value = redis-cli GET test_verify
        redis-cli DEL test_verify | Out-Null
        
        if ($value -eq "testing_123") {
            Write-Host "✓ Redis read/write operations successful" -ForegroundColor Green
        }
        else {
            Write-Host "⚠ Redis read/write test failed" -ForegroundColor Yellow
            $success = $false
        }
        
        # Check memory
        $memInfo = redis-cli INFO memory | Select-String "used_memory_human"
        if ($memInfo) {
            Write-Host "  Memory usage: $($memInfo -replace '.*:', '')" -ForegroundColor Gray
        }
    }
    else {
        Write-Host "✗ Redis not responding" -ForegroundColor Red
        $success = $false
    }
}
catch {
    Write-Host "✗ Redis connection failed: $_" -ForegroundColor Red
    $success = $false
}

# Test PostgreSQL/TimescaleDB
Write-Host "`n--- Testing PostgreSQL/TimescaleDB ---" -ForegroundColor Yellow
$env:PGPASSWORD = $config['timescaledb.password']
$pgHost = $config['timescaledb.host']
$pgPort = $config['timescaledb.port']
$pgDb = $config['timescaledb.database']
$pgUser = $config['timescaledb.user']

try {
    # Test connection
    $version = psql -U $pgUser -h $pgHost -p $pgPort -d $pgDb -t -c "SELECT version();" 2>&1
    if ($version -match "PostgreSQL") {
        Write-Host "✓ PostgreSQL connection successful" -ForegroundColor Green
        $versionShort = ($version -split '\r?\n')[0].Trim()
        if ($versionShort.Length -gt 80) {
            $versionShort = $versionShort.Substring(0, 77) + "..."
        }
        Write-Host "  $versionShort" -ForegroundColor Gray
    }
    else {
        Write-Host "✗ PostgreSQL connection failed" -ForegroundColor Red
        $success = $false
    }
    
    # Check TimescaleDB extension
    $tsdbVersion = psql -U $pgUser -h $pgHost -p $pgPort -d $pgDb -t -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';" 2>&1
    if ($tsdbVersion -and $tsdbVersion -match '\d+\.\d+') {
        Write-Host "✓ TimescaleDB extension enabled (v$($tsdbVersion.Trim()))" -ForegroundColor Green
    }
    else {
        Write-Host "✗ TimescaleDB extension not found" -ForegroundColor Red
        $success = $false
    }
    
    # Check tables
    $tableCount = psql -U $pgUser -h $pgHost -p $pgPort -d $pgDb -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" 2>&1
    if ($tableCount -gt 0) {
        Write-Host "✓ Found $($tableCount.Trim()) tables in database" -ForegroundColor Green
        
        # List tables
        $tables = psql -U $pgUser -h $pgHost -p $pgPort -d $pgDb -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" 2>&1
        $tableList = ($tables -split '\r?\n' | Where-Object { $_ -match '\S' } | ForEach-Object { $_.Trim() }) -join ', '
        Write-Host "  Tables: $tableList" -ForegroundColor Gray
    }
    else {
        Write-Host "⚠ No tables found (run init_timescaledb.sql)" -ForegroundColor Yellow
        $success = $false
    }
    
    # List hypertables
    $hypertables = psql -U $pgUser -h $pgHost -p $pgPort -d $pgDb -t -c "SELECT COUNT(*) FROM timescaledb_information.hypertables;" 2>&1
    if ($hypertables -gt 0) {
        Write-Host "✓ Found $($hypertables.Trim()) hypertable(s) configured" -ForegroundColor Green
        
        # Check compression
        $compressed = psql -U $pgUser -h $pgHost -p $pgPort -d $pgDb -t -c "SELECT COUNT(*) FROM timescaledb_information.hypertables WHERE compression_enabled=true;" 2>&1
        Write-Host "  Compression enabled: $($compressed.Trim())/$($hypertables.Trim())" -ForegroundColor Gray
        
        # List hypertables
        $htNames = psql -U $pgUser -h $pgHost -p $pgPort -d $pgDb -t -c "SELECT hypertable_name FROM timescaledb_information.hypertables ORDER BY hypertable_name;" 2>&1
        $htList = ($htNames -split '\r?\n' | Where-Object { $_ -match '\S' } | ForEach-Object { $_.Trim() }) -join ', '
        Write-Host "  Hypertables: $htList" -ForegroundColor Gray
    }
    else {
        Write-Host "⚠ No hypertables configured" -ForegroundColor Yellow
    }
    
    # Check retention/compression policies
    $policies = psql -U $pgUser -h $pgHost -p $pgPort -d $pgDb -t -c "SELECT COUNT(*) FROM timescaledb_information.jobs WHERE job_type IN ('compression_policy', 'retention_policy');" 2>&1
    if ($policies -gt 0) {
        Write-Host "✓ Found $($policies.Trim()) compression/retention policies" -ForegroundColor Green
    }
    
}
catch {
    Write-Host "✗ PostgreSQL connection failed: $_" -ForegroundColor Red
    $success = $false
}

# Check file paths and directories
Write-Host "`n--- Checking File Paths ---" -ForegroundColor Yellow
$logDir = $config['log.directory']
if (Test-Path $logDir) {
    Write-Host "✓ Log directory exists: $logDir" -ForegroundColor Green
}
else {
    Write-Host "⚠ Creating log directory: $logDir" -ForegroundColor Yellow
    New-Item -Path $logDir -ItemType Directory -Force | Out-Null
    Write-Host "✓ Log directory created" -ForegroundColor Green
}

$dashboardDir = $config['dashboard.output.path']
if (Test-Path $dashboardDir) {
    Write-Host "✓ Dashboard directory exists: $dashboardDir" -ForegroundColor Green
}
else {
    Write-Host "⚠ Creating dashboard directory: $dashboardDir" -ForegroundColor Yellow
    New-Item -Path $dashboardDir -ItemType Directory -Force | Out-Null
    Write-Host "✓ Dashboard directory created" -ForegroundColor Green
}

# Check JAR file
Write-Host "`n--- Checking Built JAR ---" -ForegroundColor Yellow
$jarPath = "F:\Bookmap\Python\build\Demo-Consumer-3.0.0.jar"
if (Test-Path $jarPath) {
    $jarInfo = Get-Item $jarPath
    Write-Host "✓ JAR file found: Demo-Consumer-3.0.0.jar" -ForegroundColor Green
    Write-Host "  Size: $([math]::Round($jarInfo.Length / 1MB, 2)) MB" -ForegroundColor Gray
    Write-Host "  Modified: $($jarInfo.LastWriteTime)" -ForegroundColor Gray
}
else {
    Write-Host "⚠ JAR file not found at $jarPath" -ForegroundColor Yellow
    Write-Host "  Run: .\gradlew.bat clean build" -ForegroundColor Gray
}

# Summary
Write-Host "`n===================================" -ForegroundColor Cyan
if ($success) {
    Write-Host "✓ All Systems Ready!" -ForegroundColor Green
}
else {
    Write-Host "⚠ Some Issues Found" -ForegroundColor Yellow
}
Write-Host "===================================" -ForegroundColor Cyan

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Load Demo-Consumer-3.0.0.jar into Bookmap" -ForegroundColor White
Write-Host "   Settings → API plugins configuration → Add" -ForegroundColor Gray
Write-Host "   Browse to: F:\Bookmap\Python\build\Demo-Consumer-3.0.0.jar" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Enable OhlcCandleConsumer on a chart" -ForegroundColor White
Write-Host "   Right-click chart → Indicators → OHLC Candle Consumer" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Monitor data collection" -ForegroundColor White
Write-Host "   Redis: redis-cli KEYS 'candle:*'" -ForegroundColor Gray
Write-Host "   Logs: Get-Content '$logDir\OhlcCandleConsumer.log' -Tail 50 -Wait" -ForegroundColor Gray
Write-Host "   DB: psql -U postgres -d trading_data -c 'SELECT COUNT(*) FROM ohlc_candles;'" -ForegroundColor Gray
Write-Host ""
