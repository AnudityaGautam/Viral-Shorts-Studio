@echo off
title Viral Shorts Studio - Long to 9:16 Shorts Clipper
color 0b
cd /d "%~dp0"

echo ================================================================
echo           VIRAL SHORTS STUDIO (LONG TO 9:16 SHORTS)
echo ================================================================
echo Starting local studio server...
echo.

:: Detect Python executable
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :found_python
)

py -c "exit(0)" >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=py"
    goto :found_python
)

python -c "exit(0)" >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :found_python
)

echo [ERROR] Neither 'py' nor 'python' was found in your PATH or AppData!
echo Please make sure Python is installed and added to PATH.
pause
exit /b 1

:found_python
echo Using Python runtime: %PY_CMD%
echo Studio will automatically open in your default browser at: http://localhost:5000
echo (Keep this window open while using the Studio)
echo.

%PY_CMD% server.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The server stopped unexpectedly.
    pause
)

