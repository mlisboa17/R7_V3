# Stop any running python -m http.server processes and start a new one on port 8530
$found = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'http.server' }
if ($found) {
    foreach ($p in $found) {
        Write-Output "Stopping PID $($p.ProcessId): $($p.CommandLine)"
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
    }
} else {
    Write-Output "No existing http.server processes found."
}
# Start http.server in background minimized
$python = 'python'
$arg = '-m http.server 8030'
Start-Process -FilePath $python -ArgumentList $arg -WorkingDirectory (Get-Location) -WindowStyle Minimized
Write-Output "Started http.server on port 8030"