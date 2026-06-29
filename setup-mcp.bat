@echo off
setlocal

echo ============================================================
echo  dcs-agentic MCP Setup
echo ============================================================
echo.

REM Install the mcp extra if not already present
echo [1/2] Installing dcs-agentic[mcp]...
pip install -e "%~dp0.[mcp]" --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python and pip are on PATH.
    pause
    exit /b 1
)
echo Done.
echo.

REM Run the setup command to register with Claude Desktop
echo [2/2] Registering MCP server with Claude Desktop...
python -m dcs_agentic setup --host claude-desktop
if errorlevel 1 (
    echo ERROR: Setup failed. See output above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup complete!
echo  Fully quit and relaunch Claude Desktop to activate.
echo ============================================================
echo.
pause
