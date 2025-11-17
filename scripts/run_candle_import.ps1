<#
.SYNOPSIS
    Manually run the candle import process.
    
.DESCRIPTION
    Executes auto_import_candles.py and displays results.
#>

$ScriptPath = "F:\TradingAgent\deaProjects\brapi-demo-consumer\backend\auto_import_candles.py"
$LogPath = "F:\TradingAgent\deaProjects\brapi-demo-consumer\outputs\logs\import_candles.log"

Write-Host "Running candle import..." -ForegroundColor Cyan
Write-Host "Log: $LogPath" -ForegroundColor Gray
Write-Host ""

# Change to backend directory
Push-Location "F:\TradingAgent\deaProjects\brapi-demo-consumer\backend"

try {
    # Run the import
    python auto_import_candles.py
    
    Write-Host ""
    Write-Host "Import complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "View logs:" -ForegroundColor Cyan
    Write-Host "  Get-Content -Path '$LogPath' -Tail 50"
    Write-Host ""
    Write-Host "View recent imports in database:" -ForegroundColor Cyan
    Write-Host "  `$env:PGPASSWORD='X74Ot*BvtjgKuCBx'; psql -h localhost -U postgres -d trading_data -c `"SELECT timeframe, COUNT(*) FROM ohlc_candles WHERE session_id LIKE 'auto_import_%' GROUP BY timeframe;`""
    
} catch {
    Write-Host "Error running import: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
