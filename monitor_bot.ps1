# Script de Monitoramento do Bot R7_V3
# Uso: .\monitor_bot.ps1

# Define o título da janela do PowerShell
$Host.UI.RawUI.WindowTitle = "R7_V3 - Monitor"

$ErrorActionPreference = "SilentlyContinue"

function Show-BotStatus {
    Clear-Host
    Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║        🤖 R7_V3 BOT - Monitor em Tempo Real             ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan
    
    # Verifica se bot está rodando
    $proc = Get-Process -Name python -ErrorAction SilentlyContinue
    
    if($proc) {
        Write-Host "✅ STATUS: ATIVO" -ForegroundColor Green
        Write-Host "   PID: $($proc[0].Id)" -ForegroundColor White
        Write-Host "   CPU: $([math]::Round($proc[0].CPU, 2))s" -ForegroundColor White
        Write-Host "   RAM: $([math]::Round($proc[0].WorkingSet64/1MB, 2))MB`n" -ForegroundColor White
    } else {
        Write-Host "❌ STATUS: PARADO`n" -ForegroundColor Red
        return
    }
    
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    Write-Host "📊 ATIVIDADES RECENTES (últimos 15 logs):`n" -ForegroundColor Yellow
    
    # Tenta ler do arquivo de log mais recente
    $logFile = Get-ChildItem -Path "logs" -Filter "*.log" -ErrorAction SilentlyContinue | 
               Sort-Object LastWriteTime -Descending | 
               Select-Object -First 1
    
    if($logFile) {
        Get-Content $logFile.FullName -Tail 15 | 
            Select-String -Pattern "EXAUSTÃO|FORÇA|MANTER|VENDER|Adicionado|Lucro|COMPRAR|APROVADA|Sniper Conectado" |
            Select-Object -Last 10 |
            ForEach-Object { Write-Host $_.Line -ForegroundColor White }
    } else {
        Write-Host "   (Aguardando logs...)" -ForegroundColor Gray
    }
    
    Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    Write-Host "🔄 Atualizando a cada 10 segundos... (Ctrl+C para sair)`n" -ForegroundColor Cyan
}

# Loop de monitoramento
while($true) {
    Show-BotStatus
    Start-Sleep -Seconds 10
}
