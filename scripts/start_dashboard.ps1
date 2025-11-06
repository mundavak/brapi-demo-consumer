# Start Service Dashboard
# Quick launcher for the service monitoring dashboard

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "  SERVICE DASHBOARD LAUNCHER" -ForegroundColor White
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "✗ Python not found. Please install Python first." -ForegroundColor Red
    pause
    exit 1
}

# Check for required packages
Write-Host ""
Write-Host "Checking dependencies..." -ForegroundColor Yellow

$packages = @("redis", "psycopg2")
$missing = @()

foreach ($package in $packages) {
    $result = python -c "import $package" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missing += $package
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Missing packages: $($missing -join ', ')" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installing missing packages..." -ForegroundColor Yellow
    
    foreach ($package in $missing) {
        if ($package -eq "psycopg2") {
            pip install psycopg2-binary
        }
        else {
            pip install $package
        }
    }
}

Write-Host ""
Write-Host "Starting dashboard..." -ForegroundColor Green
Write-Host ""

# Start the dashboard
$scriptPath = Join-Path $PSScriptRoot "service_dashboard.py"
python $scriptPath

Write-Host ""
Write-Host "Dashboard stopped." -ForegroundColor Yellow
pause
