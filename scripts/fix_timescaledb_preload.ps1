# ============================================
# Fix TimescaleDB Preload Configuration
# ============================================

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Fixing TimescaleDB Preload" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

$configPath = "F:\TradingAgent\Databases\postgresql.conf"

# Check if config exists at custom location
if (-not (Test-Path $configPath)) {
    Write-Host "Config not found at custom path, searching for PostgreSQL installation..." -ForegroundColor Yellow
    
    $pgConfig = Get-ChildItem -Path "C:\Program Files\PostgreSQL" -Recurse -Filter "postgresql.conf" -ErrorAction SilentlyContinue | Select-Object -First 1
    
    if ($pgConfig) {
        $configPath = $pgConfig.FullName
        Write-Host "Found config at: $configPath" -ForegroundColor Green
    }
    else {
        Write-Host "ERROR: Could not find postgresql.conf" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Using config: $configPath" -ForegroundColor Cyan

# Backup config
$backupPath = "$configPath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $configPath $backupPath
Write-Host "✓ Backed up config to: $backupPath" -ForegroundColor Green

# Read config
$config = Get-Content $configPath

# Find shared_preload_libraries line
$preloadLineIndex = -1
$preloadLine = $null

for ($i = 0; $i -lt $config.Count; $i++) {
    if ($config[$i] -match "^\s*shared_preload_libraries\s*=") {
        $preloadLineIndex = $i
        $preloadLine = $config[$i]
        break
    }
}

if ($preloadLineIndex -ge 0) {
    Write-Host "Found existing shared_preload_libraries at line $($preloadLineIndex + 1)" -ForegroundColor Yellow
    Write-Host "  Current: $preloadLine" -ForegroundColor Gray
    
    # Check if timescaledb already present
    if ($preloadLine -match "timescaledb") {
        Write-Host "✓ TimescaleDB already in shared_preload_libraries" -ForegroundColor Green
    }
    else {
        # Add timescaledb to existing line
        if ($preloadLine -match "shared_preload_libraries\s*=\s*'([^']*)'") {
            $existingLibs = $matches[1]
            if ($existingLibs) {
                $newLine = "shared_preload_libraries = 'timescaledb,$existingLibs'"
            }
            else {
                $newLine = "shared_preload_libraries = 'timescaledb'"
            }
        }
        else {
            # Handle case without quotes
            $newLine = "shared_preload_libraries = 'timescaledb'"
        }
        
        $config[$preloadLineIndex] = $newLine
        Write-Host "✓ Updated: $newLine" -ForegroundColor Green
    }
}
else {
    Write-Host "No existing shared_preload_libraries found, adding new line" -ForegroundColor Yellow
    
    # Find a good place to add it (after # - Shared Library Preloading if exists)
    $insertIndex = -1
    for ($i = 0; $i -lt $config.Count; $i++) {
        if ($config[$i] -match "Shared Library Preloading" -or $config[$i] -match "CUSTOMIZED OPTIONS") {
            $insertIndex = $i + 1
            break
        }
    }
    
    if ($insertIndex -lt 0) {
        # Add at end
        $config += ""
        $config += "# TimescaleDB Extension"
        $config += "shared_preload_libraries = 'timescaledb'"
    }
    else {
        # Insert after the comment
        $newLines = @()
        $newLines += ""
        $newLines += "# TimescaleDB Extension"
        $newLines += "shared_preload_libraries = 'timescaledb'"
        
        $config = $config[0..($insertIndex)] + $newLines + $config[($insertIndex + 1)..($config.Count - 1)]
    }
    
    Write-Host "✓ Added shared_preload_libraries = 'timescaledb'" -ForegroundColor Green
}

# Write updated config
Set-Content -Path $configPath -Value $config

Write-Host "`n✓ Configuration updated successfully!" -ForegroundColor Green

# Find and restart PostgreSQL service
Write-Host "`n--- Restarting PostgreSQL Service ---" -ForegroundColor Yellow
$pgServices = Get-Service -Name "*postgres*" -ErrorAction SilentlyContinue

if ($pgServices) {
    if ($pgServices -is [array]) {
        $pgService = $pgServices[0]
    }
    else {
        $pgService = $pgServices
    }
    
    Write-Host "Found service: $($pgService.Name)" -ForegroundColor Cyan
    Write-Host "Current status: $($pgService.Status)" -ForegroundColor Cyan
    
    try {
        if ($pgService.Status -eq "Running") {
            Write-Host "Stopping service..." -ForegroundColor Yellow
            Stop-Service $pgService.Name -Force
            Start-Sleep -Seconds 3
        }
        
        Write-Host "Starting service..." -ForegroundColor Yellow
        Start-Service $pgService.Name
        Start-Sleep -Seconds 5
        
        $newStatus = Get-Service $pgService.Name
        if ($newStatus.Status -eq "Running") {
            Write-Host "✓ PostgreSQL service restarted successfully!" -ForegroundColor Green
        }
        else {
            Write-Host "⚠ Service status: $($newStatus.Status)" -ForegroundColor Yellow
            Write-Host "You may need to restart manually" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "ERROR restarting service: $_" -ForegroundColor Red
        Write-Host "`nPlease restart manually using one of these commands:" -ForegroundColor Yellow
        Write-Host "  Restart-Service $($pgService.Name)" -ForegroundColor White
        Write-Host "  or" -ForegroundColor Gray
        Write-Host "  net stop $($pgService.Name) && net start $($pgService.Name)" -ForegroundColor White
    }
}
else {
    Write-Host "⚠ Could not find PostgreSQL service" -ForegroundColor Yellow
    Write-Host "Please restart PostgreSQL manually via Services or:" -ForegroundColor White
    Write-Host "  net stop postgresql-x64-17 && net start postgresql-x64-17" -ForegroundColor White
}

Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "1. Verify PostgreSQL is running:" -ForegroundColor Yellow
Write-Host "   Get-Service *postgres*" -ForegroundColor White
Write-Host "`n2. Set password and create extension:" -ForegroundColor Yellow
Write-Host "   `$env:PGPASSWORD = 'X74Ot*BvtjgKuCBx'" -ForegroundColor White
Write-Host "   psql -U postgres -h localhost -p 5432 -d trading_data -c `"CREATE EXTENSION IF NOT EXISTS timescaledb;`"" -ForegroundColor White
Write-Host "`n3. Verify TimescaleDB loaded:" -ForegroundColor Yellow
Write-Host "   psql -U postgres -h localhost -p 5432 -d trading_data -c `"\dx`"" -ForegroundColor White
Write-Host "`n4. Initialize schema:" -ForegroundColor Yellow
Write-Host "   psql -U postgres -h localhost -p 5432 -d trading_data -f `"F:\TradingAgent\deaProjects\brapi-demo-consumer\database\init_timescaledb.sql`"" -ForegroundColor White
Write-Host ""
