import os
import json
from dotenv import load_dotenv
from bots.estrategista import EstrategistaBot
from bots.executor import ExecutorBot

# Carregar variáveis de ambiente
load_dotenv()

# Carregar config
with open('config/settings.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Inicializar executor e estrategista
executor = ExecutorBot(config)
estrategista = EstrategistaBot(config)
estrategista.set_executor(executor)

print("=== VERIFICAÇÃO DE SALDO COMPLETA DA BINANCE ===")
print("Usando método atualizado do estrategista...")
print()

# Usar o método do estrategista
total_balance = estrategista.get_account_balance_usdt()

if total_balance is not None:
    print()
    print(f"✅ SALDO TOTAL ATUAL: ${total_balance:.2f} USDT")
    print()
    print("Este valor inclui:")
    print("- Saldos spot de todos os ativos")
    print("- Earn manual: $200.00 USDT")
    print("- Bot na Binance: $142.00 USDT")
    print("- Saldos adicionais de Earn (se detectados via API)")
else:
    print("❌ ERRO: Não foi possível obter o saldo da conta")