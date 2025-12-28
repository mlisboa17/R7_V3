@echo off
REM start_bots.bat
REM Starts the R7_V3 bots with NO_DASH=1 (starts both bot and keep_alive in separate cmd windows)

cd /d %~dp0
set NO_DASH=1

echo NO_DASH=1 set; checking autostart guard...
if exist "%~dp0ENABLE_AUTOSTART" (
  echo Autostart enabled; starting start_real and keep_alive...
  start "R7_V3 - start_real" cmd /c "set NO_DASH=1 && python start_real.py"
  start "R7_V3 - keep_alive" cmd /c "set NO_DASH=1 && python tools/start_keep_alive.py"
) else (
  echo Autostart is disabled. To enable, create a file named "ENABLE_AUTOSTART" in this folder.
)

echo Done. Use Task Manager or logs to verify processes.
pause
 1


 