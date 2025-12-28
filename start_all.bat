@echo off
setlocal
if "%DASH_PORT%"=="" set DASH_PORT=8530
echo Starting R7_V3 services...

echo 1) Starting orchestrator (start_real.py)
start "R7 Orchestrator" cmd /c "python start_real.py"
ping -n 2 127.0.0.1 >nul

echo 2) Starting Streamlit dashboard (web_dash.py) on port %DASH_PORT%
start "R7 Streamlit" cmd /c "set DASH_PORT=%DASH_PORT% && streamlit run web_dash.py --server.port %DASH_PORT%"
ping -n 1 127.0.0.1 >nul

echo 3) Starting monitors
start "R7 Monitor Live" cmd /c "python -u tools\monitor_live.py"
start "R7 Monitor Alerts" cmd /c "python -u tools\monitor_alerts.py"

echo All start commands issued. Use start_all.bat to restart or stop_all.bat to stop.
endlocal
