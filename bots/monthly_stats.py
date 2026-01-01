import os
import json
from datetime import date

def mapear_estrategia(nome_bruto):
    """Consolida Analista/Estrategista no Sniper Pro."""
    n = str(nome_bruto).lower()
    if any(x in n for x in ["analista", "estrategista", "ia"]): return "IA Sniper Pro"
    if "scalping" in n: return "Scalping V6"
    if "momentum" in n: return "Momentum Boost"
    if "swing" in n or "rwa" in n: return "Swing RWA"
    return nome_bruto

def add_profit_by_strategy(profit, estrategia, report_date=None):
    path = os.path.join('data', 'monthly_stats.json')
    stats = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: stats = json.load(f)
    
    report_date = report_date or date.today().isoformat()
    month_key, est_limpa = report_date[:7], mapear_estrategia(estrategia)
    
    if month_key not in stats: stats[month_key] = {}
    if report_date not in stats[month_key]: stats[month_key][report_date] = {}
    
    stats[month_key][report_date][est_limpa] = round(stats[month_key][report_date].get(est_limpa, 0.0) + profit, 2)
    
    with open(path, 'w', encoding='utf-8') as f: json.dump(stats, f, indent=2)

def set_monthly_balance(balance, report_date=None):
    path = os.path.join('data', 'monthly_stats.json')
    stats = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: stats = json.load(f)
    
    report_date = report_date or date.today().isoformat()
    month_key = report_date[:7]
    if month_key not in stats: stats[month_key] = {}
    stats[month_key]['balance'] = round(balance, 2)
    
    with open(path, 'w', encoding='utf-8') as f: json.dump(stats, f, indent=2)

def get_daily_breakdown(report_date=None):
    """Retorna quanto cada bot ganhou no dia."""
    path = os.path.join('data', 'monthly_stats.json')
    stats = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: stats = json.load(f)
    
    report_date = report_date or date.today().isoformat()
    month_key = report_date[:7]
    return stats.get(month_key, {}).get(report_date, {})

def get_monthly_accumulated_by_bot(month=None):
    """Retorna o acumulado do mês separado por bot."""
    path = os.path.join('data', 'monthly_stats.json')
    stats = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: stats = json.load(f)
    
    month = month or date.today().isoformat()[:7]
    month_data = stats.get(month, {})
    total_por_bot = {}
    
    for dia_key, dia_data in month_data.items():
        if dia_key == 'balance': continue
        if isinstance(dia_data, dict):
            for bot, lucro in dia_data.items():
                bot_consolidado = mapear_estrategia(bot)
                total_por_bot[bot_consolidado] = round(total_por_bot.get(bot_consolidado, 0.0) + lucro, 2)
    
    return total_por_bot

def get_monthly_balance(month=None):
    """Retorna o saldo mensal."""
    path = os.path.join('data', 'monthly_stats.json')
    stats = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: stats = json.load(f)
    
    month = month or date.today().isoformat()[:7]
    return stats.get(month, {}).get('balance', 0.0)