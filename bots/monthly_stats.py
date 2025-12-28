import os
import json
from datetime import date

def get_monthly_stats_path():
    return os.path.join('data', 'monthly_stats.json')

def load_monthly_stats():
    path = get_monthly_stats_path()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_monthly_stats(stats):
    path = get_monthly_stats_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

def add_profit_by_strategy(profit, estrategia, report_date=None):
    """
    Registra o lucro separando por BOT/ESTRATÉGIA.
    Estrutura: stats[mes][data][estrategia] = valor
    """
    stats = load_monthly_stats()
    if report_date is None:
        report_date = date.today().isoformat()
    
    month_key = report_date[:7]
    
    if month_key not in stats:
        stats[month_key] = {}
    if report_date not in stats[month_key]:
        stats[month_key][report_date] = {}

    # Acumula o lucro caso o bot faça vários trades no mesmo dia
    valor_atual = stats[month_key][report_date].get(estrategia, 0.0)
    stats[month_key][report_date][estrategia] = round(valor_atual + profit, 2)
    
    save_monthly_stats(stats)

def get_daily_breakdown(report_date=None):
    """Retorna quanto cada bot ganhou no dia específico."""
    stats = load_monthly_stats()
    if report_date is None:
        report_date = date.today().isoformat()
    month_key = report_date[:7]
    return stats.get(month_key, {}).get(report_date, {})

def get_monthly_accumulated_by_bot(month=None):
    """Retorna o acumulado do mês separado por bot."""
    stats = load_monthly_stats()
    if month is None:
        month = date.today().isoformat()[:7]
    
    month_data = stats.get(month, {})
    total_por_bot = {}
    
    for dia_data in month_data.values():
        if isinstance(dia_data, dict):  # Apenas processar entradas que são dicionários (ignorar 'balance')
            for bot, lucro in dia_data.items():
                total_por_bot[bot] = round(total_por_bot.get(bot, 0.0) + lucro, 2)
            
    return total_por_bot

def set_monthly_balance(balance, report_date=None):
    """
    Salva o saldo mensal atual.
    Estrutura: stats[mes]['balance'] = valor
    """
    stats = load_monthly_stats()
    if report_date is None:
        report_date = date.today().isoformat()
    
    month_key = report_date[:7]
    
    if month_key not in stats:
        stats[month_key] = {}
    
    stats[month_key]['balance'] = round(balance, 2)
    
    save_monthly_stats(stats)

def get_monthly_balance(month=None):
    """Retorna o saldo mensal salvo."""
    stats = load_monthly_stats()
    if month is None:
        month = date.today().isoformat()[:7]
    
    return stats.get(month, {}).get('balance', 0.0)