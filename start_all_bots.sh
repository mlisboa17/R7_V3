#!/bin/bash
# Script para iniciar todos os bots em background


nohup python3 bots/analista.py > analista.log 2>&1 &
nohup python3 bots/comunicador.py > comunicador.log 2>&1 &
nohup python3 bots/dashboard.py > dashboard.log 2>&1 &
nohup python3 bots/estrategista.py > estrategista.log 2>&1 &
nohup python3 bots/executor.py > executor.log 2>&1 &
nohup python3 bots/gestor_financeiro.py > gestor_financeiro.log 2>&1 &
nohup python3 bots/guardiao.py > guardiao.log 2>&1 &
nohup python3 bots/monthly_stats.py > monthly_stats.log 2>&1 &

# Atualiza saldo da Binance a cada 10 segundos
while true; do
	python3 update_composition.py > update_composition.log 2>&1
	sleep 10
done &
