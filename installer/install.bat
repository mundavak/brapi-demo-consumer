@echo off
echo MCP PDF Reader Quick Installer
echo ==============================
echo.
echo This will install MCP PDF Reader for VS Code AI assistants
echo.
echo Requirements:
echo - Python 3.8+ installed and in PATH
echo - VS Code installed  
echo - PowerShell execution policy allows scripts
echo.
pause

REM Check if PowerShell can run scripts
powershell -Command "Get-ExecutionPolicy" | findstr /i "restricted" >nul
if %errorlevel%==0 (
    echo ERROR: PowerShell execution policy is Restricted
    echo Please run this command as Administrator:
    echo Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    pause
    exit /b 1
)

REM Run the PowerShell installer
powershell -ExecutionPolicy Bypass -File "%~dp0Install-MCP-PDFReader.ps1"

pause