@echo off
REM Launcher wrapper for Bookmap Python addon - prefer BOOKMAP_PYTHON env var, fallback to C:\Python314\python.exe
if defined BOOKMAP_PYTHON (
  "%BOOKMAP_PYTHON%" "%~dp0script.py" %*
) else (
  "C:\Python314\python.exe" "%~dp0script.py" %*
)

