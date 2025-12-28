# Stop any running process whose command line contains main.py and start a new one
$found = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'main.py' }
if ($found) {
    foreach ($p in $found) {
        Write-Output "Stopping PID $($p.ProcessId): $($p.CommandLine)"
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
    }
} else {
    Write-Output "No existing main.py processes found."
}
# Start orchestrator in a new minimized window
$python = 'python'
$arg = 'main.py'
Start-Process -FilePath $python -ArgumentList $arg -WorkingDirectory (Get-Location) -WindowStyle Minimized
Write-Output "Started python main.py"