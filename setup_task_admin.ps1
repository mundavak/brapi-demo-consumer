# Run this script as Administrator
# Right-click PowerShell → Run as Administrator, then execute this script

$ErrorActionPreference = 'Stop'

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setting up Bookmap Candle Import Task" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

try {
    # Remove existing task if present
    Write-Host "Checking for existing task..."
    Unregister-ScheduledTask -TaskName "Bookmap Candle Import" -Confirm:$false -ErrorAction SilentlyContinue
    
    # Define paths
    $ProjectRoot = "F:\TradingAgent\deaProjects\brapi-demo-consumer"
    $PythonScript = "$ProjectRoot\backend\auto_import_candles.py"
    $WorkingDir = "$ProjectRoot\backend"
    $LogFile = "$ProjectRoot\outputs\logs\import_candles.log"
    
    Write-Host "Script location: $PythonScript"
    Write-Host "Working directory: $WorkingDir"
    Write-Host "Log file: $LogFile`n"
    
    # Verify files exist
    if (-not (Test-Path $PythonScript)) {
        throw "Python script not found: $PythonScript"
    }
    
    # Create action
    $Action = New-ScheduledTaskAction `
        -Execute "python" `
        -Argument "`"$PythonScript`"" `
        -WorkingDirectory $WorkingDir
    
    # Create trigger (daily at 9:20 AM)
    $Trigger = New-ScheduledTaskTrigger -Daily -At "9:20AM"
    
    # Create settings
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1)
    
    # Create principal (run with highest privileges)
    $Principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -RunLevel Highest
    
    # Register task
    Write-Host "Creating scheduled task..."
    Register-ScheduledTask `
        -TaskName "Bookmap Candle Import" `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Automatically imports MNQ candles from TradingView CSVs daily at 9:20 AM" | Out-Null
    
    Write-Host "`n✓ Task created successfully!" -ForegroundColor Green
    Write-Host "`nTask Details:" -ForegroundColor Cyan
    Write-Host "  Name: Bookmap Candle Import"
    Write-Host "  Schedule: Daily at 9:20 AM EST"
    Write-Host "  Script: $PythonScript"
    Write-Host "  Log: $LogFile"
    
    # Get task info
    $Task = Get-ScheduledTask -TaskName "Bookmap Candle Import"
    $TaskInfo = Get-ScheduledTaskInfo $Task
    
    Write-Host "`nTask Status:" -ForegroundColor Cyan
    Write-Host "  State: $($Task.State)"
    Write-Host "  Next Run: $($TaskInfo.NextRunTime)"
    
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "Would you like to run a test now? (Y/N): " -ForegroundColor Yellow -NoNewline
    $response = Read-Host
    
    if ($response -eq 'Y' -or $response -eq 'y') {
        Write-Host "`nRunning test import..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName "Bookmap Candle Import"
        Start-Sleep -Seconds 2
        
        Write-Host "`nChecking log file..."
        if (Test-Path $LogFile) {
            Write-Host "`nLast 10 lines of log:" -ForegroundColor Cyan
            Get-Content $LogFile -Tail 10
        }
    }
    
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "Management Commands:" -ForegroundColor Cyan
    Write-Host "  View task:    Get-ScheduledTask -TaskName 'Bookmap Candle Import' | Format-List *"
    Write-Host "  Run now:      Start-ScheduledTask -TaskName 'Bookmap Candle Import'"
    Write-Host "  Disable:      Disable-ScheduledTask -TaskName 'Bookmap Candle Import'"
    Write-Host "  Enable:       Enable-ScheduledTask -TaskName 'Bookmap Candle Import'"
    Write-Host "  Remove:       Unregister-ScheduledTask -TaskName 'Bookmap Candle Import' -Confirm:`$false"
    Write-Host "  View log:     Get-Content '$LogFile' -Tail 50 -Wait"
    Write-Host "========================================`n" -ForegroundColor Green
    
} catch {
    Write-Host "`n✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`nMake sure you're running PowerShell as Administrator!" -ForegroundColor Yellow
    Write-Host "Right-click PowerShell icon → Run as Administrator`n" -ForegroundColor Yellow
    exit 1
}
