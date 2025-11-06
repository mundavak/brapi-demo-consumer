# Trading Data Architecture Setup Script
# Creates all required folders and copies configuration files

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Trading Data Architecture Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Define paths
$paths = @{
    TradingAgentDashboard = "F:\TradingAgent\Dashboard"
    DatabaseRoot          = "F:\Databases"
    DatabaseLogs          = "F:\Databases\Logs"
    BookmapBuild          = "F:\Bookmap\Python\build"
}

# Create directories
Write-Host "Creating directory structure..." -ForegroundColor Yellow
foreach ($key in $paths.Keys) {
    $path = $paths[$key]
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "  [CREATED] $path" -ForegroundColor Green
    }
    else {
        Write-Host "  [EXISTS]  $path" -ForegroundColor Gray
    }
}

# Copy configuration files
Write-Host ""
Write-Host "Setting up configuration files..." -ForegroundColor Yellow

$configSource = ".\config\database_config.properties"
$configDest = "F:\Databases\database_config.properties"
if (Test-Path $configSource) {
    Copy-Item $configSource $configDest -Force
    Write-Host "  [COPIED] database_config.properties -> F:\Databases\" -ForegroundColor Green
}
else {
    Write-Host "  [WARNING] database_config.properties not found in .\config\" -ForegroundColor Yellow
}

$symbolConfigSource = ".\config\symbol_config.json"
$symbolConfigDest = "F:\TradingAgent\Dashboard\symbol_config.json"
if (Test-Path $symbolConfigSource) {
    Copy-Item $symbolConfigSource $symbolConfigDest -Force
    Write-Host "  [COPIED] symbol_config.json -> F:\TradingAgent\Dashboard\" -ForegroundColor Green
}
else {
    Write-Host "  [WARNING] symbol_config.json not found in .\config\" -ForegroundColor Yellow
}

# Create log file placeholders
Write-Host ""
Write-Host "Initializing log files..." -ForegroundColor Yellow
$logFiles = @(
    "StopsIcebergsConsumer.log",
    "OhlcCandleConsumer.log",
    "AbsorptionConsumer.log",
    "RedisManager.log",
    "TimescaleDBManager.log",
    "trading_system_summary.log"
)

foreach ($logFile in $logFiles) {
    $logPath = "F:\Databases\Logs\$logFile"
    if (-not (Test-Path $logPath)) {
        "# Log file initialized $(Get-Date)" | Out-File $logPath -Encoding UTF8
        Write-Host "  [CREATED] $logFile" -ForegroundColor Green
    }
}

# Verify Redis and TimescaleDB connectivity
Write-Host ""
Write-Host "Verifying database connectivity..." -ForegroundColor Yellow

# Test Redis
Write-Host "  Testing Redis connection..." -ForegroundColor Gray
try {
    $redisTest = & redis-cli ping 2>&1
    if ($redisTest -match "PONG") {
        Write-Host "  [OK] Redis is running and responding" -ForegroundColor Green
    }
    else {
        Write-Host "  [WARNING] Redis may not be running" -ForegroundColor Yellow
        Write-Host "            Please start Redis: redis-server" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  [ERROR] Redis CLI not found or not running" -ForegroundColor Red
    Write-Host "          Install Redis or add to PATH" -ForegroundColor Red
}

# Test TimescaleDB/PostgreSQL
Write-Host "  Testing PostgreSQL/TimescaleDB connection..." -ForegroundColor Gray
try {
    $pgTest = & psql -U postgres -d trading_data -c "SELECT 1;" 2>&1
    if ($pgTest -match "1 row") {
        Write-Host "  [OK] TimescaleDB is running and accessible" -ForegroundColor Green
    }
    else {
        Write-Host "  [WARNING] TimescaleDB/PostgreSQL may not be configured" -ForegroundColor Yellow
        Write-Host "            Run: psql -U postgres -f database\init_timescaledb.sql" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  [ERROR] PostgreSQL not found or database not created" -ForegroundColor Red
    Write-Host "          1. Install PostgreSQL with TimescaleDB extension" -ForegroundColor Red
    Write-Host "          2. CREATE DATABASE trading_data;" -ForegroundColor Red
    Write-Host "          3. Run: psql -U postgres -d trading_data -f database\init_timescaledb.sql" -ForegroundColor Red
}

# Display summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Folders created:" -ForegroundColor White
Write-Host "  - F:\TradingAgent\Dashboard\" -ForegroundColor Gray
Write-Host "  - F:\Databases\" -ForegroundColor Gray
Write-Host "  - F:\Databases\Logs\" -ForegroundColor Gray
Write-Host "  - F:\Bookmap\Python\build\" -ForegroundColor Gray
Write-Host ""
Write-Host "Configuration files:" -ForegroundColor White
Write-Host "  - F:\Databases\database_config.properties" -ForegroundColor Gray
Write-Host "  - F:\TradingAgent\Dashboard\symbol_config.json" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Verify Redis is running (redis-server)" -ForegroundColor Yellow
Write-Host "  2. Verify TimescaleDB is running (pg_ctl start)" -ForegroundColor Yellow
Write-Host "  3. Initialize TimescaleDB schema:" -ForegroundColor Yellow
Write-Host "     psql -U postgres -d trading_data -f database\init_timescaledb.sql" -ForegroundColor Cyan
Write-Host "  4. Build JARs: .\gradlew.bat clean build" -ForegroundColor Yellow
Write-Host "  5. Deploy to Bookmap: Copy from build\libs\ to F:\Bookmap\Python\build\" -ForegroundColor Yellow
Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
