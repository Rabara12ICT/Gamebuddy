@echo off
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH.
    echo Install Python 3.10+ from https://python.org and make sure "py" is available.
    pause
    exit /b 1
)

py -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo Pygame is not installed. Attempting to install it...
    py -m pip install --disable-pip-version-check pygame
    if errorlevel 1 (
        echo.
        echo Could not install Pygame. Check your internet connection and Python pip setup.
        pause
        exit /b 1
    )
)

py "%~dp0game.py"
if errorlevel 1 (
    echo.
    echo Game exited with an error. Review the traceback above.
    pause
    exit /b 1
)
