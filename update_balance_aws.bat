@echo off
REM Script para atualizar o saldo na AWS
ssh -i "C:\Users\mlisb\OneDrive\Desktop\r7_trade_key.pem" ubuntu@18.231.247.124 "source r7_env/bin/activate && python update_composition.py"
echo Saldo atualizado na AWS.