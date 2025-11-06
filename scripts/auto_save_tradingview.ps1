# TradingView Auto-Save PowerShell Script
# Automatically handles Windows save dialogs for TradingView exports
# 
# USAGE:
# .\scripts\auto_save_tradingview.ps1
# 
# Press Ctrl+C to stop

param(
    [int]$CheckInterval = 100,  # Check every 100ms
    [string]$TargetFolder = "F:\TradingAgent\deaProjects\brapi-demo-consumer\KnowledgeBase"
)

Write-Host "🤖 TradingView Auto-Save Monitor" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "✅ Monitoring for save dialogs..." -ForegroundColor Green
Write-Host "📁 Target folder: $TargetFolder" -ForegroundColor Yellow
Write-Host "🛑 Press Ctrl+C to stop" -ForegroundColor Red
Write-Host ""

# Add Windows API types for window manipulation
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public class WinAPI {
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindowEx(IntPtr hwndParent, IntPtr hwndChildAfter, string lpszClass, string lpszWindow);
    
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
    
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    
    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);
    
    // Constants
    public const uint WM_KEYDOWN = 0x0100;
    public const uint WM_CHAR = 0x0102;
    public const uint VK_RETURN = 0x0D;
    public const uint BM_CLICK = 0x00F5;
}
"@

function Send-EnterToWindow {
    param([IntPtr]$WindowHandle)
    
    if ($WindowHandle -ne [IntPtr]::Zero) {
        [WinAPI]::SetForegroundWindow($WindowHandle)
        Start-Sleep -Milliseconds 100
        [WinAPI]::PostMessage($WindowHandle, [WinAPI]::WM_KEYDOWN, [WinAPI]::VK_RETURN, [IntPtr]::Zero)
        return $true
    }
    return $false
}

function Get-WindowTitle {
    param([IntPtr]$WindowHandle)
    
    if ($WindowHandle -eq [IntPtr]::Zero) { return "" }
    
    $length = [WinAPI]::GetWindowTextLength($WindowHandle)
    if ($length -eq 0) { return "" }
    
    $builder = New-Object System.Text.StringBuilder($length + 1)
    [WinAPI]::GetWindowText($WindowHandle, $builder, $builder.Capacity)
    return $builder.ToString()
}

function Check-SaveDialogs {
    $found = $false
    
    # Method 1: Look for "Save As" dialogs
    $saveDialog = [WinAPI]::FindWindow($null, "Save As")
    if ($saveDialog -ne [IntPtr]::Zero) {
        Write-Host "🎯 Found 'Save As' dialog - sending Enter..." -ForegroundColor Green
        if (Send-EnterToWindow $saveDialog) {
            Write-Host "✅ Enter sent to Save As dialog" -ForegroundColor Green
            $found = $true
        }
    }
    
    # Method 2: Look for Chrome save dialogs
    $chromeDialog = [WinAPI]::FindWindow("Chrome_WidgetWin_1", $null)
    if ($chromeDialog -ne [IntPtr]::Zero) {
        $title = Get-WindowTitle $chromeDialog
        if ($title -like "*wants to save*" -or $title -like "*Save*") {
            Write-Host "🎯 Found Chrome save dialog: $title" -ForegroundColor Green
            if (Send-EnterToWindow $chromeDialog) {
                Write-Host "✅ Enter sent to Chrome dialog" -ForegroundColor Green
                $found = $true
            }
        }
    }
    
    # Method 3: Look for generic Windows dialogs with "Save" in title
    $dialogHandle = [WinAPI]::FindWindow("#32770", $null)  # Standard dialog class
    if ($dialogHandle -ne [IntPtr]::Zero) {
        $title = Get-WindowTitle $dialogHandle
        if ($title -like "*Save*") {
            Write-Host "🎯 Found Windows dialog: $title" -ForegroundColor Green
            if (Send-EnterToWindow $dialogHandle) {
                Write-Host "✅ Enter sent to Windows dialog" -ForegroundColor Green
                $found = $true
            }
        }
    }
    
    return $found
}

# Main monitoring loop
$lastAction = Get-Date
$actionCount = 0

try {
    while ($true) {
        if (Check-SaveDialogs) {
            $actionCount++
            $lastAction = Get-Date
            Write-Host "📊 Actions taken: $actionCount | Last: $($lastAction.ToString('HH:mm:ss'))" -ForegroundColor Blue
            Write-Host ""
            
            # Wait a bit longer after taking action to avoid spam
            Start-Sleep -Milliseconds 1000
        }
        
        Start-Sleep -Milliseconds $CheckInterval
        
        # Show periodic status (every 30 seconds)
        if ((Get-Date).Subtract($lastAction).TotalSeconds -gt 30 -and $actionCount -gt 0) {
            Write-Host "⏰ Still monitoring... (Actions: $actionCount)" -ForegroundColor DarkGray
            $lastAction = Get-Date
        }
    }
}
catch {
    Write-Host ""
    Write-Host "🛑 Auto-Save Monitor stopped" -ForegroundColor Yellow
    Write-Host "📊 Total actions taken: $actionCount" -ForegroundColor Blue
    
    if ($_.Exception.Message -like "*Operation was canceled*") {
        Write-Host "✅ Stopped by user (Ctrl+C)" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "🏁 TradingView Auto-Save Monitor finished" -ForegroundColor Cyan