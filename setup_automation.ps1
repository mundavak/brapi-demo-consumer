# Launcher script - automatically requests admin elevation
# Just double-click this file or run: .\setup_automation.ps1

Write-Host "Launching Task Scheduler setup with administrator privileges..." -ForegroundColor Cyan

$setupScript = Join-Path $PSScriptRoot "setup_task_admin.ps1"

if (-not (Test-Path $setupScript)) {
    Write-Host "Error: setup_task_admin.ps1 not found!" -ForegroundColor Red
    exit 1
}

# Launch with admin privileges
Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$setupScript`""

Write-Host "`nAdmin PowerShell window opened - follow the prompts there." -ForegroundColor Green
