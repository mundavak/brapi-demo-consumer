<#
.SYNOPSIS
    Setup Windows Task Scheduler for daily automated candle import at 9:20 AM.

.DESCRIPTION
    Creates a scheduled task to run auto_import_candles.py daily at 9:20 AM EST.
    The task runs with highest privileges and uses the system Python environment.
#>

$TaskName = "Bookmap Candle Import"
$ScriptPath = "F:\TradingAgent\deaProjects\brapi-demo-consumer\backend\auto_import_candles.py"
$PythonPath = "python"  # Assumes Python is in PATH
$WorkingDir = "F:\TradingAgent\deaProjects\brapi-demo-consumer\backend"

Write-Host "Setting up daily candle import task..." -ForegroundColor Cyan

# Create the action (run Python script)
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkingDir

# Create the trigger (daily at 9:20 AM)
$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "9:20AM"

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Create principal (run with highest privileges)
$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

# Register the task
try {
    # Remove existing task if present
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($ExistingTask) {
        Write-Host "Removing existing task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    
    # Register new task
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Daily automated import of MNQ candle data from TradingView CSV exports at 9:20 AM EST" | Out-Null
    
    Write-Host "✓ Task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  Name: $TaskName"
    Write-Host "  Schedule: Daily at 9:20 AM"
    Write-Host "  Script: $ScriptPath"
    Write-Host "  Log: F:\TradingAgent\deaProjects\brapi-demo-consumer\outputs\logs\import_candles.log"
    Write-Host ""
    
    # Show task info
    $Task = Get-ScheduledTask -TaskName $TaskName
    Write-Host "Status: $($Task.State)" -ForegroundColor Green
    
    # Offer to run test
    Write-Host ""
    $Response = Read-Host "Run test import now? (y/n)"
    if ($Response -eq 'y') {
        Write-Host "Starting test import..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "✓ Test started! Check the log file for progress." -ForegroundColor Green
    }
    
}
catch {
    Write-Host "✗ Error creating task: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Management Commands:" -ForegroundColor Cyan
Write-Host "  View task:    Get-ScheduledTask -TaskName '$TaskName' | Format-List *"
Write-Host "  Run now:      Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Disable:      Disable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Enable:       Enable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Remove:       Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host "  View log:     Get-Content -Path 'F:\TradingAgent\deaProjects\brapi-demo-consumer\outputs\logs\import_candles.log' -Tail 50 -Wait"
