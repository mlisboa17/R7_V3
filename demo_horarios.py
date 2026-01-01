#!/usr/bin/env python3
"""
Demonstração das funcionalidades de horário e mercados internacionais
do sistema R7_V3
"""

from main import is_market_hours, get_market_volatility_multiplier
from datetime import datetime, timezone, timedelta

def demo_market_hours():
    """Demonstra o controle de horário de operação"""
    print("🕐 DEMONSTRAÇÃO - CONTROLE DE HORÁRIO (BRASÍLIA)")
    print("=" * 50)

    now_utc = datetime.now(timezone.utc)
    now_brt = now_utc - timedelta(hours=3)  # UTC-3 para Brasília
    print(f"Horário atual (BRT): {now_brt.strftime('%H:%M:%S')}")
    print(f"Horário atual (UTC): {now_utc.strftime('%H:%M:%S')}")

    operating = is_market_hours()
    status = "✅ DENTRO do horário" if operating else "❌ FORA do horário"
    print(f"Status de operação: {status}")
    print(f"Horário de operação: 24/7 (Crypto nunca para)")
    print(f"Equivalente em UTC: Sempre ativo")
    print()

def demo_market_volatility():
    """Demonstra o multiplicador de volatilidade por mercado"""
    print("🌍 DEMONSTRAÇÃO - MERCADOS INTERNACIONAIS")
    print("=" * 50)

    current_hour = datetime.now(timezone.utc).hour
    multiplier = get_market_volatility_multiplier()

    print(f"Horário atual (UTC): {current_hour:02d}:00")
    print(f"Multiplicador de volatilidade: x{multiplier:.1f}")

    # Mostra os horários dos mercados
    markets = {
        "🌏 Ásia (Tóquio, Hong Kong)": "00:00-08:00 UTC / 21:00-05:00 BRT (x1.3)",
        "🌍 Europa (Londres, Frankfurt)": "08:00-16:00 UTC / 05:00-13:00 BRT (x1.4)",
        "🇺🇸 EUA (Nova York)": "14:30-21:00 UTC / 11:30-18:00 BRT (x1.5)",
        "🌎 Europa + EUA (sobreposição)": "14:00-16:00 UTC / 11:00-13:00 BRT (x1.6)",
        "🌙 Horário noturno": "22:00-08:00 UTC / 19:00-05:00 BRT (x0.7)"
    }

    print("\n📊 HORÁRIOS DOS MERCADOS:")
    for market, hours in markets.items():
        print(f"  {market}: {hours}")

    print("\n💡 IMPACTO NO TRADING:")
    print(f"  • Entradas ajustadas: base x {multiplier:.1f}")
    print(f"  • Frequência de varredura: {'mais rápida' if multiplier > 1.0 else 'mais lenta'}")
    if multiplier < 1.0:
        print("  • Estratégias filtradas: apenas conservadoras (swing, mean_reversion)")
    print()

def demo_strategy_adjustments():
    """Demonstra como as estratégias são ajustadas"""
    print("📈 DEMONSTRAÇÃO - AJUSTES DE ESTRATÉGIAS")
    print("=" * 50)

    multiplier = get_market_volatility_multiplier()

    strategies = {
        "scalping_v6": {"base": 25.0, "tp": 0.45, "sl": 0.50},
        "swing_rwa": {"base": 50.0, "tp": 3.20, "sl": 1.70},
        "momentum_boost": {"base": 35.0, "tp": 1.20, "sl": 0.80},
        "mean_reversion": {"base": 30.0, "tp": 2.20, "sl": 1.20}
    }

    print(f"Multiplicador de volatilidade atual: x{multiplier:.1f}")
    print("Estratégia       | Entrada Base | Entrada Ajustada | TP % | SL %")
    print("-" * 65)

    for strategy, config in strategies.items():
        base_entry = config["base"]
        adjusted_entry = min(base_entry * multiplier, base_entry * 1.5)  # Máximo 50% acima
        tp = config["tp"]
        sl = config["sl"]

        print(f"{strategy:<15} | ${base_entry:>11.0f} | ${adjusted_entry:>15.0f} | {tp:>4.2f} | {sl:>4.2f}")

    print()
    print("💰 CONSIDERAÇÕES:")
    print("  • Entradas nunca excedem 150% do valor base")
    print("  • Em baixa volatilidade: apenas estratégias conservadoras")
    print("  • Taxas da Binance já incluídas nos cálculos (0.2%)")
    print()

if __name__ == "__main__":
    print("🚀 R7_V3 - DEMONSTRAÇÃO DE HORÁRIO E MERCADOS INTERNACIONAIS")
    print("=" * 70)
    print()

    demo_market_hours()
    demo_market_volatility()
    demo_strategy_adjustments()

    print("✅ SISTEMA CONFIGURADO PARA:")
    print("  • Operar 24/7 (mercado crypto nunca para)")
    print("  • Ajustar entradas baseado na volatilidade dos mercados")
    print("  • Filtrar estratégias em períodos de baixa liquidez")
    print("  • Maximizar oportunidades quando mercados tradicionais estão ativos")