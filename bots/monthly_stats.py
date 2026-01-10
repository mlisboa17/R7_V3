import json
import os
from datetime import datetime

PATH_STATS = os.path.join('data', 'monthly_stats.json')

def load_monthly_stats():
    """Carrega o histórico global de performance."""
    if os.path.exists(PATH_STATS):
        with open(PATH_STATS, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "total_trades": 0,
        "vitorias": 0,
        "derrotas": 0,
        "lucro_total_acumulado": 0.0,
        "historico_estrategias": {}
    }

def set_monthly_balance(balance_usdt):
    """Define o saldo mensal para rastreamento de composição."""
    stats = load_monthly_stats()
    stats["saldo_mensal_atual"] = balance_usdt
    stats["data_atualizacao"] = datetime.now().isoformat()
    
    os.makedirs('data', exist_ok=True)
    with open(PATH_STATS, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)

def add_profit_by_strategy(pnl, estrategia):
    """Registra o resultado de cada trade para mensuração."""
    stats = load_monthly_stats()
    
    stats["total_trades"] += 1
    if pnl > 0:
        stats["vitorias"] += 1
    else:
        stats["derrotas"] += 1
        
    stats["lucro_total_acumulado"] += pnl
    
    # Organiza por bot/estratégia
    if estrategia not in stats["historico_estrategias"]:
        stats["historico_estrategias"][estrategia] = {"trades": 0, "pnl": 0.0}
    
    stats["historico_estrategias"][estrategia]["trades"] += 1
    stats["historico_estrategias"][estrategia]["pnl"] += pnl
    
    os.makedirs('data', exist_ok=True)
    with open(PATH_STATS, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)