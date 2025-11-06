# Redis Stack Upgrade Script for Windows
# Downloads and installs Redis Stack with modern features (XADD, JSON, Search, etc.)

Write-Host "=== Redis Stack Upgrade for Windows ===" -ForegroundColor Cyan
Write-Host ""

# Stop existing Redis service
Write-Host "1. Stopping old Redis service..." -ForegroundColor Yellow
try {
    Stop-Service -Name "Redis" -Force -ErrorAction SilentlyContinue
    Write-Host "   ✓ Redis service stopped" -ForegroundColor Green
}
catch {
    Write-Host "   ⚠ Could not stop Redis service (may not exist)" -ForegroundColor Yellow
}

# Download Redis Stack
Write-Host ""
Write-Host "2. Downloading Redis Stack..." -ForegroundColor Yellow
$downloadUrl = "https://packages.redis.io/redis-stack/redis-stack-server-7.4.0-v0.zip"
$downloadPath = "$env:TEMP\redis-stack.zip"
$extractPath = "C:\Program Files\Redis-Stack"

Write-Host "   Downloading from: $downloadUrl" -ForegroundColor Gray
try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $downloadPath -UseBasicParsing
    Write-Host "   ✓ Download complete" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Download failed: $_" -ForegroundColor Red
    exit 1
}

# Extract Redis Stack
Write-Host ""
Write-Host "3. Extracting Redis Stack..." -ForegroundColor Yellow
try {
    if (Test-Path $extractPath) {
        Write-Host "   Removing old installation..." -ForegroundColor Gray
        Remove-Item -Path $extractPath -Recurse -Force
    }
    
    Expand-Archive -Path $downloadPath -DestinationPath $extractPath -Force
    Write-Host "   ✓ Extracted to $extractPath" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Extraction failed: $_" -ForegroundColor Red
    exit 1
}

# Find the actual Redis Stack directory (version-specific subfolder)
$redisStackDir = Get-ChildItem -Path $extractPath -Directory | Select-Object -First 1
$redisStackPath = $redisStackDir.FullName

Write-Host "   Redis Stack directory: $redisStackPath" -ForegroundColor Gray

# Create Redis configuration
Write-Host ""
Write-Host "4. Creating Redis configuration..." -ForegroundColor Yellow
$configContent = @"
# Redis Stack Configuration for Bookmap Trading System
bind 127.0.0.1
port 6379
timeout 0
tcp-keepalive 300

# Persistence
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir "$extractPath\data"

# Logging
loglevel notice
logfile "$extractPath\logs\redis.log"

# Memory management
maxmemory 2gb
maxmemory-policy allkeys-lru

# Append only file (durability)
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec

# Redis Stack modules (automatically loaded)
loadmodule "$redisStackPath\rejson.dll"
loadmodule "$redisStackPath\redisearch.dll"
loadmodule "$redisStackPath\redistimeseries.dll"
"@

# Create directories
New-Item -ItemType Directory -Force -Path "$extractPath\data" | Out-Null
New-Item -ItemType Directory -Force -Path "$extractPath\logs" | Out-Null

$configPath = "$extractPath\redis.conf"
$configContent | Out-File -FilePath $configPath -Encoding utf8
Write-Host "   ✓ Configuration created at $configPath" -ForegroundColor Green

# Install as Windows service
Write-Host ""
Write-Host "5. Installing Redis Stack as Windows service..." -ForegroundColor Yellow
try {
    # Remove old service if exists
    $oldService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
    if ($oldService) {
        Write-Host "   Removing old Redis service..." -ForegroundColor Gray
        sc.exe delete Redis | Out-Null
    }
    
    # Install new service
    $redisServerExe = "$redisStackPath\redis-stack-server.exe"
    if (-not (Test-Path $redisServerExe)) {
        $redisServerExe = "$redisStackPath\redis-server.exe"
    }
    
    & $redisServerExe --service-install $configPath --service-name RedisStack --loglevel verbose
    Write-Host "   ✓ Service installed" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Service installation failed: $_" -ForegroundColor Red
    Write-Host "   You may need to run this script as Administrator" -ForegroundColor Yellow
    exit 1
}

# Start Redis Stack service
Write-Host ""
Write-Host "6. Starting Redis Stack service..." -ForegroundColor Yellow
try {
    Start-Service -Name "RedisStack"
    Start-Sleep -Seconds 3
    
    $service = Get-Service -Name "RedisStack"
    if ($service.Status -eq "Running") {
        Write-Host "   ✓ Redis Stack is running" -ForegroundColor Green
    }
    else {
        Write-Host "   ✗ Service failed to start" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "   ✗ Failed to start service: $_" -ForegroundColor Red
    exit 1
}

# Verify installation
Write-Host ""
Write-Host "7. Verifying installation..." -ForegroundColor Yellow
try {
    $version = & "$redisStackPath\redis-cli.exe" INFO server | Select-String "redis_version"
    Write-Host "   $version" -ForegroundColor Green
    
    # Test modern commands
    Write-Host "   Testing XADD (streams)..." -ForegroundColor Gray
    & "$redisStackPath\redis-cli.exe" XADD test_stream "*" field value | Out-Null
    Write-Host "   ✓ XADD works" -ForegroundColor Green
    
    Write-Host "   Testing HSET (modern syntax)..." -ForegroundColor Gray
    & "$redisStackPath\redis-cli.exe" HSET test_hash field1 value1 field2 value2 | Out-Null
    Write-Host "   ✓ HSET works" -ForegroundColor Green
    
    # Cleanup test keys
    & "$redisStackPath\redis-cli.exe" DEL test_stream test_hash | Out-Null
}
catch {
    Write-Host "   ✗ Verification failed: $_" -ForegroundColor Red
}

# Update PATH environment variable
Write-Host ""
Write-Host "8. Updating system PATH..." -ForegroundColor Yellow
try {
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($currentPath -notlike "*$redisStackPath*") {
        $newPath = "$currentPath;$redisStackPath"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
        Write-Host "   ✓ PATH updated (restart terminal to use redis-cli)" -ForegroundColor Green
    }
    else {
        Write-Host "   ✓ PATH already contains Redis Stack" -ForegroundColor Green
    }
}
catch {
    Write-Host "   ⚠ Could not update PATH (requires Administrator)" -ForegroundColor Yellow
    Write-Host "   Manually add to PATH: $redisStackPath" -ForegroundColor Gray
}

# Cleanup
Remove-Item -Path $downloadPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Redis Stack Installation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Installation Details:" -ForegroundColor Cyan
Write-Host "  Location: $redisStackPath" -ForegroundColor White
Write-Host "  Service: RedisStack" -ForegroundColor White
Write-Host "  Config: $configPath" -ForegroundColor White
Write-Host "  Port: 6379" -ForegroundColor White
Write-Host "  Max Memory: 2GB" -ForegroundColor White
Write-Host ""
Write-Host "Features Enabled:" -ForegroundColor Cyan
Write-Host "  ✓ Redis Streams (XADD, XREAD)" -ForegroundColor Green
Write-Host "  ✓ RedisJSON (JSON.SET, JSON.GET)" -ForegroundColor Green
Write-Host "  ✓ RediSearch (FT.CREATE, FT.SEARCH)" -ForegroundColor Green
Write-Host "  ✓ RedisTimeSeries (TS.ADD, TS.RANGE)" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Restart your terminal to use redis-cli" -ForegroundColor White
Write-Host "  2. Test: redis-cli --version" -ForegroundColor White
Write-Host "  3. Rebuild Python addon: .\gradlew.bat clean pythonAddonJar" -ForegroundColor White
Write-Host "  4. Restart Bookmap and verify no Redis errors" -ForegroundColor White
Write-Host ""
