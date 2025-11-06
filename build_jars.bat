@echo off
REM ============================================
REM Trading Data Architecture - JAR Build Script
REM ============================================

echo ========================================
echo Building Trading Consumer JAR Files
echo ========================================
echo.

cd /d F:\TradingAgent\deaProjects\brapi-demo-consumer

echo [1/5] Cleaning previous builds...
call gradlew.bat clean
if errorlevel 1 (
    echo ERROR: Clean failed
    pause
    exit /b 1
)
echo ... Done
echo.

echo [2/5] Resolving dependencies...
call gradlew.bat dependencies
echo ... Done
echo.

echo [3/5] Building JAR files...
call gradlew.bat build -x test
if errorlevel 1 (
    echo ERROR: Build failed
    echo.
    echo Common issues:
    echo - Missing Bookmap API JAR in mavenLib folder
    echo - Check that api-core-7.5.0.4.jar is present
    echo - Verify Java 11+ is installed
    pause
    exit /b 1
)
echo ... Done
echo.

echo [4/5] Creating output directory...
if not exist "F:\Bookmap\Python\build" mkdir "F:\Bookmap\Python\build"
echo ... Done
echo.

echo [5/5] Copying JARs to Bookmap directory...
copy /Y build\libs\*.jar F:\Bookmap\Python\build\
if errorlevel 1 (
    echo WARNING: Could not copy to F:\Bookmap\Python\build\
    echo Trying alternate location...
    if not exist "F:\TradingAgent\Build" mkdir "F:\TradingAgent\Build"
    copy /Y build\libs\*.jar F:\TradingAgent\Build\
)
echo ... Done
echo.

echo ========================================
echo Build Complete!
echo ========================================
echo.
echo JAR files created:
dir /B build\libs\*.jar
echo.
echo Location: F:\Bookmap\Python\build\
echo.
echo Next steps:
echo 1. Open Bookmap
echo 2. Go to Settings -^> Manage Addons
echo 3. Click "Add custom addon"
echo 4. Navigate to F:\Bookmap\Python\build\
echo 5. Select Demo-Consumer-3.0.0.jar
echo 6. Enable the addon
echo 7. Restart Bookmap
echo.
echo ========================================

pause

