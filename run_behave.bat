@echo off
setlocal enabledelayedexpansion

REM ====== Paths ======
set "PROJECT_DIR=E:\shayan\tests"
set "PYTHON_EXE=C:\Python312\python.exe"
set "SCRIPT=%PROJECT_DIR%\run_behave.py"
set "LOG_DIR=%PROJECT_DIR%\logs"
set "SCREENSHOT_DIR=%PROJECT_DIR%\screenshots"

REM ====== Date-Time Stamp ======
for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set ldt=%%a
set "dt=!ldt:~0,8!"
set "tm=!ldt:~8,6!"
set "TIMESTAMP=!dt!_!tm!"

REM ====== Make Folders ======
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%SCREENSHOT_DIR%" mkdir "%SCREENSHOT_DIR%"

REM ====== Log Header ======
echo ========================================= >> "%LOG_DIR%\behave_%TIMESTAMP%.log"
echo Behave Run Started at %date% %time% >> "%LOG_DIR%\behave_%TIMESTAMP%.log"
echo ========================================= >> "%LOG_DIR%\behave_%TIMESTAMP%.log"

REM ====== Run Python Script ======
"%PYTHON_EXE%" "%SCRIPT%" >> "%LOG_DIR%\behave_%TIMESTAMP%.log" 2>&1

REM ====== Error Handling ======
if %ERRORLEVEL% NEQ 0 (
    echo Error found >> "%LOG_DIR%\behave_%TIMESTAMP%.log"
)

REM ====== Kill leftover processes (VERY IMPORTANT for Selenium) ======
taskkill /f /im chrome.exe >nul 2>&1
taskkill /f /im chromedriver.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1

echo Finished at %date% %time% >> "%LOG_DIR%\behave_%TIMESTAMP%.log"
echo ========================================= >> "%LOG_DIR%\behave_%TIMESTAMP%.log"

endlocal
exit /b 0