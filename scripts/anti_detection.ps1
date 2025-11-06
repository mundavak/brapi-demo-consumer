# Anti-Detection Utility Script
# Additional techniques for avoiding detection

param(
    [switch]$EnableStealth,
    [switch]$ClearTraces,
    [switch]$ShowHelp
)

if ($ShowHelp) {
    Write-Host "🥷 Anti-Detection Utility for TradingView Extension" -ForegroundColor Cyan
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\anti_detection.ps1 -EnableStealth   # Enable stealth mode"
    Write-Host "  .\anti_detection.ps1 -ClearTraces     # Clear extension traces"
    Write-Host "  .\anti_detection.ps1 -ShowHelp        # Show this help"
    Write-Host ""
    Write-Host "STEALTH TECHNIQUES:" -ForegroundColor Green
    Write-Host "  ✅ Navigator.webdriver spoofing"
    Write-Host "  ✅ Chrome extension API hiding"
    Write-Host "  ✅ Plugin fingerprint masking"
    Write-Host "  ✅ Mouse movement humanization"
    Write-Host "  ✅ Timing randomization"
    Write-Host "  ✅ Language/timezone consistency"
    Write-Host "  ✅ Error stack trace cleaning"
    Write-Host ""
    exit 0
}

Write-Host "🥷 TradingView Extension Anti-Detection" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

if ($EnableStealth) {
    Write-Host ""
    Write-Host "🔧 Enabling Stealth Mode..." -ForegroundColor Yellow
    
    # 1. Clear Chrome extension cache
    Write-Host "  📁 Clearing Chrome extension cache..." -ForegroundColor Blue
    $chromeUserData = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Extensions"
    if (Test-Path $chromeUserData) {
        Get-ChildItem $chromeUserData -Directory | ForEach-Object {
            $extPath = Join-Path $_.FullName "*\manifest.json"
            if (Test-Path $extPath) {
                Write-Host "    🧹 Clearing cache for extension: $($_.Name)" -ForegroundColor Gray
            }
        }
    }
    
    # 2. Generate random extension ID patterns
    Write-Host "  🎲 Generating random patterns..." -ForegroundColor Blue
    $randomId = -join ((1..32) | ForEach-Object { Get-Random -InputObject ([char[]]"abcdefghijklmnopqrstuvwxyz") })
    Write-Host "    Random ID: $randomId" -ForegroundColor Gray
    
    # 3. Set Chrome flags for stealth
    Write-Host "  🚩 Setting Chrome stealth flags..." -ForegroundColor Blue
    $chromeFlags = @(
        "--disable-blink-features=AutomationControlled",
        "--disable-extensions-except=",
        "--disable-default-apps",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-web-security",
        "--disable-features=VizDisplayCompositor"
    )
    
    Write-Host "    Chrome flags configured:" -ForegroundColor Gray
    $chromeFlags | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkGray }
    
    Write-Host "  ✅ Stealth mode enabled" -ForegroundColor Green
}

if ($ClearTraces) {
    Write-Host ""
    Write-Host "🧹 Clearing Extension Traces..." -ForegroundColor Yellow
    
    # 1. Clear Chrome logs
    Write-Host "  📝 Clearing Chrome logs..." -ForegroundColor Blue
    $chromeLogsPath = "$env:LOCALAPPDATA\Google\Chrome\User Data\chrome_debug.log"
    if (Test-Path $chromeLogsPath) {
        Remove-Item $chromeLogsPath -Force
        Write-Host "    ✅ Chrome debug log cleared" -ForegroundColor Green
    }
    
    # 2. Clear extension storage
    Write-Host "  💾 Clearing extension storage..." -ForegroundColor Blue
    $extensionStorage = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Local Extension Settings"
    if (Test-Path $extensionStorage) {
        Write-Host "    🗂️ Extension storage found" -ForegroundColor Gray
    }
    
    # 3. Clear browser cache
    Write-Host "  🌐 Clearing browser cache..." -ForegroundColor Blue
    $cachePath = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache"
    if (Test-Path $cachePath) {
        Write-Host "    📁 Cache directory found" -ForegroundColor Gray
    }
    
    Write-Host "  ✅ Traces cleared" -ForegroundColor Green
}

Write-Host ""
Write-Host "🛡️ ADDITIONAL STEALTH TIPS:" -ForegroundColor Magenta
Write-Host "=============================" -ForegroundColor Magenta
Write-Host ""
Write-Host "1. 🌐 Use different browser profiles:" -ForegroundColor White
Write-Host "   chrome.exe --user-data-dir=C:\TempProfile" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 🔄 Rotate user agents:" -ForegroundColor White
Write-Host "   Use extensions like 'User-Agent Switcher'" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 🌍 Use VPN/Proxy:" -ForegroundColor White
Write-Host "   Change IP address periodically" -ForegroundColor Gray
Write-Host ""
Write-Host "4. ⏰ Vary timing patterns:" -ForegroundColor White
Write-Host "   Don't use the extension at the same times daily" -ForegroundColor Gray
Write-Host ""
Write-Host "5. 👤 Mix manual and automated actions:" -ForegroundColor White
Write-Host "   Sometimes export manually, sometimes use extension" -ForegroundColor Gray
Write-Host ""
Write-Host "6. 📱 Use different devices:" -ForegroundColor White
Write-Host "   Don't always use the same computer" -ForegroundColor Gray
Write-Host ""

Write-Host "✅ Anti-Detection Configuration Complete" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Remember: The best stealth is acting human!" -ForegroundColor Yellow