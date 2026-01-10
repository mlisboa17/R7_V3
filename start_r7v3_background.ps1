# R7_V3 Trading Bot - Background Runner
$ErrorActionPreference = "Stop"

# Configurações
$ProjectPath = "c:\Users\mlisb\PROJETOS_Local\R7_V3"
$LogFile = "$ProjectPath\logs\bot_runner.log"

# Função para log
function Write-Log {
    param($Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
    Add-Content -Path $LogFile -Value $logMessage
}

# Cria diretório de logs se não existir
if (!(Test-Path "$ProjectPath\logs")) {
    New-Item -ItemType Directory -Path "$ProjectPath\logs" -Force
}

Write-Log "=== Iniciando R7_V3 Trading Bot ==="

# Mata processos anteriores
try {
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Log "Processos Python anteriores finalizados"
} catch {
    Write-Log "Nenhum processo Python anterior encontrado"
}

# Muda para o diretório do projeto
Set-Location $ProjectPath
Write-Log "Diretório alterado para: $ProjectPath"

# Inicia o bot
Write-Log "Iniciando bot principal..."
try {
    # Executa o bot e captura a saída
    $process = Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory $ProjectPath -PassThru -WindowStyle Normal
    Write-Log "Bot iniciado com PID: $($process.Id)"
    
    # Monitora o processo
    while (!$process.HasExited) {
        Start-Sleep -Seconds 30
        Write-Log "Bot rodando... PID: $($process.Id)"
    }
    
    Write-Log "Bot finalizado com código: $($process.ExitCode)"
} catch {
    Write-Log "ERRO ao iniciar bot: $($_.Exception.Message)"
}

Write-Log "=== Finalizando R7_V3 Trading Bot ==="