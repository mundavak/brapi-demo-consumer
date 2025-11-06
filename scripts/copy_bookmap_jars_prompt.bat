@echo off
setlocal EnableDelayedExpansion

echo ==================================================
echo Copy Bookmap JARs into project mavenLib/providers/modules
echo ==================================================
echo Enter full path to your Bookmap lib folder (e.g. C:\Program Files\Bookmap\lib)
set /p BOOKMAP_LIB=Bookmap lib path (leave empty for default):
if "%BOOKMAP_LIB%"=="" set "BOOKMAP_LIB=%ProgramFiles%\Bookmap\lib"
if not exist "%BOOKMAP_LIB%" (
  echo Path "%BOOKMAP_LIB%" does not exist.
  pause
  exit /b 2
)

set PROJECT_ROOT=%~dp0..
set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%
set PROVIDERS_DIR=%PROJECT_ROOT%\providers\modules
set MAVENLIB_DIR=%PROJECT_ROOT%\mavenLib
mkdir "%PROVIDERS_DIR%" 2>nul
mkdir "%MAVENLIB_DIR%" 2>nul

echo Providers target: "%PROVIDERS_DIR%"
echo mavenLib target: "%MAVENLIB_DIR%"
echo Using Bookmap lib: "%BOOKMAP_LIB%"

rem find broadcasting-api jar(s)
set FOUND=0
nfor %%F in ("%BOOKMAP_LIB%\broadcasting-api*.jar") do (
  if exist "%%~fF" (
    set FOUND=1
    echo Copying broadcasting JAR: %%~nxF to providers/modules
    copy "%%~fF" "%PROVIDERS_DIR%\" /Y >nul && echo Copied %%~nxF
    rem Also copy to mavenLib coordinate layout if possible (place under com/bookmap/addons/broadcasting-api/<ver>)
    for /f "tokens=2 delims=-" %%V in ("%%~nxF") do set NAME_PART=%%V
  )
)
if %FOUND%==0 echo No broadcasting-api JARs found in "%BOOKMAP_LIB%".

rem find api-core jar(s)
set FOUND_CORE=0
nfor %%F in ("%BOOKMAP_LIB%\api-core*.jar") do (
  if exist "%%~fF" (
    set FOUND_CORE=1
    echo Found api-core: %%~nxF
    rem extract version roughly from filename api-core-<version>.jar
    set "FNAME=%%~nxF"
    for /f "tokens=2 delims=-" %%A in ("!FNAME!") do set "VERPART=%%A"
    set "VERPART=!VERPART:.jar=!"
    set DEST_API_DIR=%MAVENLIB_DIR%\com\bookmap\api\api-core\!VERPART!
    mkdir "!DEST_API_DIR!" 2>nul
    echo Copying api-core into "!DEST_API_DIR!" ...
    copy "%%~fF" "!DEST_API_DIR!\" /Y >nul && echo Copied api-core to !DEST_API_DIR!\
  )
)
if %FOUND_CORE%==0 echo No api-core JARs found in "%BOOKMAP_LIB%".

echo --------------------------------------------------
echo Optional: install jars to local maven repo (~/.m2) (requires 'mvn' on PATH)
set /p INSTALL_MVN=Run 'mvn install' for found jars? (y/N):
if /i "%INSTALL_MVN%"=="y" (
  echo Installing broadcasting JARs to local maven repo...
  for %%F in ("%BOOKMAP_LIB%\broadcasting-api*.jar") do (
    if exist "%%~fF" (
      echo Installing %%~nxF ...
      mvn install:install-file -Dfile="%%~fF" -DgroupId=com.bookmap.addons -DartifactId=broadcasting-api -Dversion=local -Dpackaging=jar
    )
  )
  for %%F in ("%BOOKMAP_LIB%\api-core*.jar") do (
    if exist "%%~fF" (
      echo Installing %%~nxF ...
      mvn install:install-file -Dfile="%%~fF" -DgroupId=com.bookmap.api -DartifactId=api-core -Dversion=local -Dpackaging=jar
    )
  )
)

echo Done. If jar files were copied, run: .\gradlew.bat clean build --refresh-dependencies
pause
endlocal

