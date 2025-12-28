import sys, os, json, calendar
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bots.guardiao import GuardiaoBot
from bots.executor import ExecutorBot
from datetime import date

# Defaults from user's instruction
AMOUNT_USD = 9660.84
META_PERCENT = 0.20

# Allow overrides via CLI
amount = float(sys.argv[1]) if len(sys.argv) > 1 else AMOUNT_USD
meta_percent = float(sys.argv[2]) if len(sys.argv) > 2 else META_PERCENT
currency = (sys.argv[3] if len(sys.argv) > 3 else 'USD').upper()

# load config
cfg_path = os.path.join('config','settings.json')
if os.path.exists(cfg_path):
    with open(cfg_path,'r',encoding='utf-8') as f:
        cfg = json.load(f)
else:
    cfg = {'config_trade':{'meta_diaria_brl':99.09,'usdt_margin':294.0},'banca_total_brl':9909.25}

g = GuardiaoBot(cfg)
e = ExecutorBot(cfg)

# Determine rate
rate = g.state.get('last_usdt_brl_rate') or 1.0
try:
    if getattr(e, 'binance_client', None):
        r2 = e.get_usdt_brl_rate()
        if r2:
            rate = r2
except Exception:
    pass

if currency == 'USD':
    start_usd = amount
    start_brl = round(amount * rate, 2)
else:
    start_brl = amount
    start_usd = round(amount / rate if rate else 0.0, 2)

# compute monthly meta (full month) as percent of start balance (in USD-space if currency USD)
if currency == 'USD':
    month_meta_usd = round(start_usd * meta_percent, 2)
    month_meta_brl = round(month_meta_usd * rate, 2)
else:
    month_meta_brl = round(start_brl * meta_percent, 2)
    month_meta_usd = round(month_meta_brl / rate if rate else 0.0, 2)

# final goal
final_goal_usd = round(start_usd + month_meta_usd, 2)
final_goal_brl = round(start_brl + month_meta_brl, 2)

# Apply to guardiao state
try:
    g.state['month_start_balance'] = round(start_brl, 2)
    g.state['month_start_balance_usd'] = round(start_usd, 2)
    g.state['month_start_date'] = date.today().isoformat()
    days_in_month = calendar.monthrange(date.today().year, date.today().month)[1]
    g.state['month_days'] = days_in_month
    g.state['month_meta_total'] = round(month_meta_brl, 2)
    g.state['month_meta_total_usd'] = round(month_meta_usd, 2)
    g.state['month_final_goal_brl'] = final_goal_brl
    g.state['month_final_goal_usd'] = final_goal_usd
    # persist
    g._write_state(g.state)
    # Ensure non-decreasing rule via set_month_meta_total (it will not lower existing if larger)
    g.set_month_meta_total(round(month_meta_brl, 2))
    # Save friendly progress file using executor snapshot when available
    g.salvar_progresso(e)
    print('[OK] Month start applied:')
    print(json.dumps({
        'month_start_balance_usd': g.state.get('month_start_balance_usd'),
        'month_start_balance_brl': g.state.get('month_start_balance'),
        'month_meta_total_usd': g.state.get('month_meta_total_usd'),
        'month_meta_total_brl': g.state.get('month_meta_total'),
        'month_final_goal_usd': g.state.get('month_final_goal_usd'),
        'month_final_goal_brl': g.state.get('month_final_goal_brl'),
        'rate_used': rate
    }, indent=2))
except Exception as exc:
    print('Error applying month start:', exc)
    raise
