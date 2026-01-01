@echo off
REM Script para parar o bot na AWS
ssh -i "C:\Users\mlisb\OneDrive\Desktop\r7_trade_key.pem" ubuntu@18.231.247.124 "pkill -f main.py"
echo Bot parado na AWS.