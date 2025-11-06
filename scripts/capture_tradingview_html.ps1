# TradingView HTML Capture Script
# Captures HTML from browser for debugging extension

param(
    [string]$Url = "https://www.tradingview.com/chart/",
    [string]$OutputPath = ".\captured_html"
)

Write-Host "🌐 TradingView HTML Capture Tool" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Create output directory
if (!(Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
    Write-Host "📁 Created output directory: $OutputPath" -ForegroundColor Green
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$filename = "tradingview_$timestamp.html"
$fullPath = Join-Path $OutputPath $filename

Write-Host "🎯 Target URL: $Url" -ForegroundColor Yellow
Write-Host "📄 Output file: $fullPath" -ForegroundColor Yellow
Write-Host ""

# Method 1: Using Invoke-WebRequest (basic HTML structure)
Write-Host "📡 Fetching HTML with PowerShell..." -ForegroundColor Blue
try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing
    $response.Content | Out-File -FilePath $fullPath -Encoding UTF8
    Write-Host "✅ Basic HTML captured" -ForegroundColor Green
}
catch {
    Write-Host "❌ PowerShell method failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "🔧 BETTER METHODS FOR DYNAMIC CONTENT:" -ForegroundColor Magenta
Write-Host "=======================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "1. 🌐 Browser Developer Tools:" -ForegroundColor Cyan
Write-Host "   • Open TradingView chart" -ForegroundColor White
Write-Host "   • Press F12 → Elements tab" -ForegroundColor White
Write-Host "   • Right-click <html> → Copy → Copy outerHTML" -ForegroundColor White
Write-Host "   • Paste into text file" -ForegroundColor White
Write-Host ""
Write-Host "2. 🧩 Browser Extension Console:" -ForegroundColor Cyan
Write-Host "   • Open TradingView chart" -ForegroundColor White
Write-Host "   • Press F12 → Console tab" -ForegroundColor White
Write-Host "   • Run: document.documentElement.outerHTML" -ForegroundColor Yellow
Write-Host "   • Copy the output" -ForegroundColor White
Write-Host ""
Write-Host "3. 💾 Browser Save As:" -ForegroundColor Cyan
Write-Host "   • Right-click page → Save as..." -ForegroundColor White
Write-Host "   • Choose 'Webpage, Complete'" -ForegroundColor White
Write-Host "   • Gets HTML + all resources" -ForegroundColor White
Write-Host ""
Write-Host "4. 🎯 Context Menu Specific:" -ForegroundColor Cyan
Write-Host "   • Right-click chart to open menu" -ForegroundColor White
Write-Host "   • F12 → Elements → Inspect the menu" -ForegroundColor White
Write-Host "   • Right-click menu element → Copy outerHTML" -ForegroundColor White
Write-Host ""

Write-Host "📁 Basic HTML saved to: $fullPath" -ForegroundColor Green
Write-Host "💡 For dynamic content (menus, dialogs), use browser dev tools!" -ForegroundColor Yellow

# Open the output directory
if (Test-Path $fullPath) {
    Write-Host ""
    Write-Host "🚀 Opening output directory..." -ForegroundColor Blue
    Start-Process explorer.exe -ArgumentList $OutputPath
}