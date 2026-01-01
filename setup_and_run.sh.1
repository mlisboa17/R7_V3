#!/bin/bash

# Script para automatizar o setup e execução do bot R7_V3 no EC2
# Execute com: bash setup_and_run.sh

echo "Iniciando setup automático do R7_V3 no EC2..."

# 1. Atualizar sistema e instalar dependências básicas
echo "Atualizando sistema e instalando Git e Python..."
sudo apt update -y
sudo apt install -y git python3 python3-pip python3-venv

# 2. Clonar repositório (substitua pela sua URL)
REPO_URL="https://github.com/mlisboa17/R7_V3.git"  # URL atualizada com seu usuário
echo "Clonando repositório: $REPO_URL"
git clone $REPO_URL
cd R7_V3

# 3. Criar ambiente virtual e instalar dependências
echo "Criando ambiente virtual e instalando dependências..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Executar scripts em background (loop infinito)
echo "Iniciando scripts em background..."

# Função para rodar script em loop
run_in_loop() {
    while true; do
        echo "Iniciando $1..."
        python3 $1
        echo "$1 finalizado. Reiniciando em 5 segundos..."
        sleep 5
    done
}

# Iniciar main.py e start_real.py em background
run_in_loop main.py &
run_in_loop start_real.py &

# Iniciar dashboard Streamlit em background
while true; do
    echo "Iniciando dashboard..."
    streamlit run dashboard_r7.py --server.port 8501 --server.address 0.0.0.0
    echo "Dashboard finalizado. Reiniciando em 5 segundos..."
    sleep 5
done &

# Iniciar atualização de saldo a cada 10 segundos
while true; do
    echo "Atualizando saldo..."
    python3 update_composition.py
    sleep 10
done &

# Iniciar relatório diário (uma vez por dia)
while true; do
    python3 tools/send_daily_report.py
    sleep 86400  # 24h
done &

# Iniciar consolidação diária às 02:00
while true; do
    HORA=$(date +%H)
    MIN=$(date +%M)
    if [ "$HORA" -eq 2 ] && [ "$MIN" -eq 0 ]; then
        echo "Consolidando histórico..."
        python3 tools/consolidate_trades.py
        sleep 3600  # Evita rodar novamente na mesma hora
    else
        sleep 50
    fi
done &

echo "Setup completo! Todos os scripts estão rodando em background."
echo "Para verificar processos: ps aux | grep python"
echo "Para parar tudo: pkill -f python"