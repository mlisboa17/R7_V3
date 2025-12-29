# Consolida histórico de trades diariamente às 02:00
Start-Job -ScriptBlock {
    $python = "python"
    while ($true) {
        $agora = Get-Date
        if ($agora.Hour -eq 2 -and $agora.Minute -eq 0) {
            Write-Host "Consolidando histórico de trades..."
            & $python tools\consolidate_trades.py
            Write-Host "Histórico consolidado. Próxima execução em 24h."
            Start-Sleep -Seconds 3600  # Evita rodar mais de uma vez na mesma hora
        } else {
            Start-Sleep -Seconds 50
        }
    }
}
# start_all_loop.ps1
# Executa scripts principais em loop infinito para rodar 24/7
# Adapte a lista de scripts conforme necessário


$python = "python"  # Ou caminho completo para python.exe se necessário
$scripts = @(
    "main.py",
    "start_real.py"
    # Adicione outros scripts que precisam rodar 24/7
)

# Inicia scripts Python em loop
foreach ($script in $scripts) {
    Start-Job -ScriptBlock {
        param($python, $script)
        while ($true) {
            Write-Host "Iniciando $script..."
            & $python $script
            Write-Host "$script finalizado. Reiniciando em 5 segundos..."
            Start-Sleep -Seconds 5
        }
    } -ArgumentList $python, $script
}

# Inicia o dashboard Streamlit em background
Start-Job -ScriptBlock {
    while ($true) {
        Write-Host "Iniciando dashboard_r7.py via Streamlit..."
        streamlit run dashboard_r7.py
        Write-Host "Dashboard finalizado. Reiniciando em 5 segundos..."
        Start-Sleep -Seconds 5
    }
}

# Inicia o relatório diário automático (ajuste o horário no script)
Start-Job -ScriptBlock {
    while ($true) {
        & $python tools\send_daily_report.py
        Start-Sleep -Seconds 86400  # Executa uma vez a cada 24h
    }
}


# Atualiza saldo da Binance a cada 10 segundos
Start-Job -ScriptBlock {
    $python = "python"
    while ($true) {
        Write-Host "Atualizando saldo da Binance..."
        & $python update_composition.py
        Start-Sleep -Seconds 10
    }
}

Write-Host "Todos os scripts foram iniciados em background."
Write-Host "Use 'Get-Job' para ver os jobs e 'Stop-Job' para parar."
