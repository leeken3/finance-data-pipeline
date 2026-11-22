@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

if "%~1"=="" goto usage_error
if /I "%~1"=="help" goto usage_ok
if /I "%~1"=="run" goto run

echo Unknown command: %~1
echo.
goto usage_error

:run
set "URL=http://127.0.0.1:8000/"
set "CHROME_EXE="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%LocalAppData%\Google\Chrome\Application\chrome.exe"

if defined CHROME_EXE (
    start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process -FilePath '%CHROME_EXE%' -ArgumentList '%URL%'"
) else (
    start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process '%URL%'"
)
"%PYTHON_EXE%" "%PROJECT_DIR%\app.py"
exit /b %errorlevel%

:usage_ok
echo Usage: expenses run
echo.
echo run   Start Ledger and open http://127.0.0.1:8000
exit /b 0

:usage_error
echo Usage: expenses run
echo.
echo run   Start Ledger and open http://127.0.0.1:8000
exit /b 1
