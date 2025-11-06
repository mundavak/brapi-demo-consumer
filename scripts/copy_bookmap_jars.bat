@echo off
setlocal EnableDelayedExpansion
echo -------------------------------
echo Copy Bookmap JARs into project mavenLib/providers/modules
echo Project root: %~dp0..\
set PROJECT_ROOT=%~dp0..
set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%
set PROVIDERS_DIR=%PROJECT_ROOT%\providers\modules
set MAVENLIB_DIR=%PROJECT_ROOT%\mavenLib
mkdir "%PROVIDERS_DIR%" 2>nul
mkdir "%MAVENLIB_DIR%" 2>nul
echo Providers target: "%PROVIDERS_DIR%"
echo mavenLib target: "%MAVENLIB_DIR%"

rem Common Bookmap install path
set BOOKMAP_LIB="%ProgramFiles%\Bookmap\lib"
if not exist %BOOKMAP_LIB% (
  echo Bookmap lib folder not found at %ProgramFiles%\Bookmap\lib
  echo Please update this script or copy jars manually.
  exit /b 2
)

echo Searching for broadcasting-api JAR in %ProgramFiles%\Bookmap\lib ...
set BROADCAST_JAR=
for /f "delims=" %%F in ('dir /b /a-d "%ProgramFiles%\Bookmap\lib\broadcasting-api*.jar" 2^>nul') do (
  set "BROADCAST_JAR=%%~fF"
)
if defined BROADCAST_JAR (
  echo Found: "%BROADCAST_JAR%"
  echo Copying broadcasting JAR to providers/modules ...
  copy "%BROADCAST_JAR%" "%PROVIDERS_DIR%" /Y >nul && echo Copied broadcasting JAR to providers/modules\
) else (
  echo broadcasting-api JAR not found in %ProgramFiles%\Bookmap\lib .
)

echo Searching for api-core JAR in %ProgramFiles%\Bookmap\lib ...
set API_CORE_JAR=
for /f "delims=" %%F in ('dir /b /a-d "%ProgramFiles%\Bookmap\lib\api-core*.jar" 2^>nul') do (
  set "API_CORE_JAR=%%~fF"
)
if defined API_CORE_JAR (
  echo Found: "%API_CORE_JAR%"
  rem Extract version from filename (api-core-<version>.jar)
  for %%G in ("%API_CORE_JAR%") do set "API_NAME=%%~nxG"
  set "API_VER=!API_NAME:api-core-=!"
  set "API_VER=!API_VER:.jar=!"
  echo Detected api-core version: !API_VER!
  set DEST_API_DIR=%MAVENLIB_DIR%\com\bookmap\api\api-core\!API_VER!
  mkdir "!DEST_API_DIR!" 2>nul
  echo Copying api-core into "!DEST_API_DIR!" ...
  copy "!API_CORE_JAR!" "!DEST_API_DIR!\" /Y >nul && echo Copied api-core to !DEST_API_DIR!\
) else (
  echo api-core JAR not found in %ProgramFiles%\Bookmap\lib .
)

echo Done. Review messages above. If files were copied, run: .\gradlew.bat clean build --refresh-dependencies
endlocal

