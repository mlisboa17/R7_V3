import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bots.guardiao import GuardiaoBot
from bots.executor import ExecutorBot

cfg_path = os.path.join('config','settings.json')
if os.path.exists(cfg_path):
    with open(cfg_path,'r',encoding='utf-8') as f:
        cfg=json.load(f)
else:
    cfg={'config_trade':{'meta_diaria_brl':99.09,'usdt_margin':294.0},'banca_total_brl':9909.25}

g = GuardiaoBot(cfg)
e = ExecutorBot(cfg)

# Read month_config.json
mc_path = os.path.join('data','month_config.json')
if not os.path.exists(mc_path):
    print('NO_MONTH_CONFIG')
    sys.exit(2)
mc = json.load(open(mc_path,'r',encoding='utf-8'))

# Validate types
if not isinstance(mc.get('initial_balance'), (int,float)):
    print('initial_balance not numeric')
    sys.exit(3)
if not isinstance(mc.get('monthly_target_percent'), (int,float)):
    print('monthly_target_percent not numeric')
    sys.exit(4)

# Apply values
rate = g.state.get('last_usdt_brl_rate') or 1.0
g.state['month_start_balance_usd'] = float(mc['initial_balance'])
g.state['month_start_balance'] = round(float(mc['initial_balance']) * rate, 2)
# monthly target: if provided in USD use that, otherwise compute from percent
if mc.get('monthly_target_usd'):
    g.state['month_meta_total_usd'] = float(mc['monthly_target_usd'])
    g.state['month_meta_total'] = round(float(mc['monthly_target_usd']) * rate,2)
else:
    g.state['month_meta_total_usd'] = round(float(mc['initial_balance']) * float(mc['monthly_target_percent']),2)
    g.state['month_meta_total'] = round(g.state['month_meta_total_usd'] * rate,2)

g.state['month_start_date'] = mc.get('month_start_date')
g.state['month_days'] = mc.get('month_days', 31)
# persist
g._write_state(g.state)
print('[OK] Guardiao state updated with month config')
# Force a friendly progress save
try:
    g.salvar_progresso(e)
    print('[OK] salvar_progresso executed; data/daily_state.json updated')
except Exception as exc:
    print('ERROR saving progress:', exc)
    sys.exit(5)

# Print a concise check
d = json.load(open('data/daily_state.json','r',encoding='utf-8'))
print(json.dumps({
    'month_start_balance_usd': g.state.get('month_start_balance_usd'),
    'month_start_balance_brl': g.state.get('month_start_balance'),
    'month_meta_total_usd': g.state.get('month_meta_total_usd'),
    'month_meta_total_brl': g.state.get('month_meta_total'),
    'data_daily_keys': list(d.keys())
}, indent=2))
