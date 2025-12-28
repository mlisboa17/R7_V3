import asyncio
import json
from bots.monthly_stats import add_profit_by_strategy, get_monthly_accumulated_by_bot
from bots.estrategista import EstrategistaBot

async def rodar_teste_total():
    print("🔍 [TESTE] Carregando configurações...")
    with open('config/settings.json', 'r') as f:
        config = json.load(f)

    estrategista = EstrategistaBot(config)
    
    # 1. Simular Sinal de SCALPING
    sinal_scalping = {
        'symbol': 'SOL',
        'estrategia': 'scalping_v6',
        'rsi5': 25.0,
        'volume': 1000000
    }
    
    print("\n🛠️ Testando Validação do SCALPING...")
    if estrategista.analisar_tendencia(sinal_scalping):
        print(f"✅ Scalping Validado! Valor de entrada: ${sinal_scalping.get('entrada_usd')}")
        # Simula lucro no histórico
        add_profit_by_strategy(3.50, 'scalping_v6')
    
    # 2. Simular Sinal do OUTRO (Swing)
    sinal_swing = {
        'symbol': 'BTC',
        'estrategia': 'swing_rwa',
        'rsi5': 30.0,
        'volume': 5000000
    }
    
    print("\n🛠️ Testando Validação do SWING...")
    if estrategista.analisar_tendencia(sinal_swing):
        print(f"✅ Swing Validado! Valor de entrada: ${sinal_swing.get('entrada_usd')}")
        # Simula lucro no histórico
        add_profit_by_strategy(15.00, 'swing_rwa')

    # 3. Verificação Final do Banco de Dados
    print("\n📊 [RESULTADO FINAL] Verificando Potes de Lucro:")
    resumo = get_monthly_accumulated_by_bot()
    for bot, lucro in resumo.items():
        print(f"💰 Bot: {bot.upper()} | Lucro Registrado: ${lucro:.2f}")

if __name__ == "__main__":
    asyncio.run(rodar_teste_total())