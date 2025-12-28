@echo off
echo Stopping R7_V3 services...

powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'R7_V3' -or $_.CommandLine -match 'web_dash.py' -or $_.CommandLine -match 'dashboard_r7.py' -or $_.CommandLine -match 'start_real.py' -or $_.CommandLine -match 'streamlit' -or $_.CommandLine -match 'monitor_live.py' -or $_.CommandLine -match 'monitor_alerts.py') } | ForEach-Object { Write-Host ('Killing ' + $_.ProcessId + ' ' + $_.CommandLine); Stop-Process -Id $_.ProcessId -Force }"

if exist pid.txt (
  del pid.txt
  echo Removed pid.txt
)

echo Stop commands issued.
