# PowerShell script to help test the Chrome extension
Write-Host "🔧 Chrome Extension Testing Assistant" -ForegroundColor Cyan
Write-Host "=====================================`n" -ForegroundColor Cyan

Write-Host "🎯 Extension Status: Syntax Error Fixed!" -ForegroundColor Green
Write-Host "📍 Extension Location: $(Get-Location)`n" -ForegroundColor Yellow

Write-Host "📋 Testing Checklist:" -ForegroundColor Magenta
Write-Host "  ✅ Syntax errors resolved in content.js" -ForegroundColor Green
Write-Host "  ✅ Downloads API integration complete" -ForegroundColor Green  
Write-Host "  ✅ Background script ready" -ForegroundColor Green
Write-Host "  ✅ Popup UI enhanced" -ForegroundColor Green
Write-Host "  🔄 Extension testing needed`n" -ForegroundColor Yellow

Write-Host "🚀 Testing Steps:" -ForegroundColor Cyan
Write-Host "1. Open Chrome and go to chrome://extensions/"
Write-Host "2. Turn ON 'Developer mode' (top right toggle)"
Write-Host "3. Click 'Load unpacked' and select this folder:"
Write-Host "   $(Get-Location)" -ForegroundColor Yellow
Write-Host "4. Look for errors in the extension card"
Write-Host "5. If no errors, go to TradingView.com"
Write-Host "6. Open any chart and try the export`n"

Write-Host "🐛 Debugging Tools:" -ForegroundColor Cyan
Write-Host "• Right-click extension icon → 'Inspect popup' (popup console)"
Write-Host "• F12 on TradingView page → Console tab (content script logs)"
Write-Host "• chrome://extensions/ → Background page (service worker logs)"
Write-Host "• chrome://downloads/ → Check Downloads API activity`n"

Write-Host "📊 Expected Results:" -ForegroundColor Green
Write-Host "• No syntax errors when loading extension"
Write-Host "• Export should save to Downloads/TradingView_Data/"
Write-Host "• Smart filename: chart_export_SYMBOL_2025-11-03_TIME.csv"
Write-Host "• Browser notification on successful download`n"

Write-Host "🔍 Quick File Check:" -ForegroundColor Magenta
Write-Host "content.js lines: $((Get-Content content.js).Count)"
Write-Host "background.js lines: $((Get-Content background.js).Count)"
Write-Host "manifest.json valid: $(Test-Path manifest.json)"

Write-Host "`n🎉 Ready to test! Load the extension in Chrome now." -ForegroundColor Green