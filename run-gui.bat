@echo off
REM run-gui.bat - Launch the DCS Agentic Mission Editor PySide6 GUI.
REM Double-click this file to open the chat GUI directly.

setlocal
cd /d "%~dp0"

REM Use the project venv if present, otherwise fall back to whatever python is on PATH.
if exist ".venv\Scripts\python.exe" (
    set "PY=%~dp0.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

REM Make sure the package and PySide6 are importable.
"%PY%" -c "import PySide6" 1>nul 2>nul
if errorlevel 1 (
    echo [setup] Installing PySide6...
    "%PY%" -m pip install PySide6
    if errorlevel 1 (
        echo ERROR: Failed to install PySide6.
        pause
        exit /b 1
    )
)

"%PY%" -c "import dcs_agentic" 1>nul 2>nul
if errorlevel 1 (
    echo [setup] Installing dcs-agentic with agent extras...
    "%PY%" -m pip install -e ".[agents]"
    if errorlevel 1 (
        echo ERROR: Failed to install dcs-agentic. Run: pip install -e .[dev,agents]
        pause
        exit /b 1
    )
)

"%PY%" "%~dp0start-mission-gui.py"
endlocal
