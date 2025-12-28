@echo off
REM Start Streamlit dashboard (Windows) using DASH_PORT if provided
cd /d %~dp0
REM Default port if DASH_PORT not set
if "%DASH_PORT%"=="" (
	set DASH_PORT=8501
)
echo Starting Streamlit on port %DASH_PORT%
start "R7 V3 Dashboard" cmd /c "streamlit run dashboard_r7.py --server.port %DASH_PORT%"
