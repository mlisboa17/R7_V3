<#
start_bots.ps1
Starts the R7_V3 bots with NO_DASH=1 so the dashboard is not launched.
Usage:
  - To start only the bot (recommended):  .\start_bots.ps1
  - To start bot + keep-alive/watchdog:      .\start_bots.ps1 -KeepAlive
#>

param(
    [switch]$KeepAlive
)

# Ensure script runs from project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Output "Setting NO_DASH=1 and starting bots..."
$env:NO_DASH = '1'

# Start start_real.py (it will spawn main in background)
try {
    Start-Process -FilePath "python" -ArgumentList "start_real.py" -WindowStyle Hidden -ErrorAction Stop
    Write-Output "✅ start_real.py started"
} catch {
    Write-Error "Failed to start start_real.py: $_"
}

$autostartFile = Join-Path $ScriptDir "ENABLE_AUTOSTART"
if ($KeepAlive) {
    if (-not (Test-Path $autostartFile)) {
        Write-Output '⚠️ Keep-alive not started because autostart is disabled. To enable, create "ENABLE_AUTOSTART" in the project root.'
    } else {
        try {
            Start-Process -FilePath "python" -ArgumentList "tools/start_keep_alive.py" -WindowStyle Hidden -ErrorAction Stop
            Write-Output "✅ keep_alive started"
        } catch {
            Write-Error "Failed to start keep_alive: $_"
        }
    }
} else {
    Write-Output "ℹ️ Keep-alive not started. Re-run with -KeepAlive to start it as well."
}
