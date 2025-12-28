import sys, os, json
sys.path.insert(0, os.getcwd())
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

print('Executor real_trading:', e.real_trading)
print('Executor has binance client:', bool(e.binance_client))
try:
    rate = e.get_usdt_brl_rate()
    print('USDTBRL rate:', rate)
except Exception as exc:
    print('Rate check failed:', exc)
try:
    saldo = e.obter_saldo_real_spot(g)
    print('Executor obter_saldo_real_spot:', saldo)
except Exception as exc:
    print('obter_saldo_real_spot failed:', exc)
print('Executor usdt_margin:', e.usdt_margin, 'usdt_available:', e.usdt_available)
# Guardiao may not expose `state`; try to read safely from object or daily_state.json
try:
    state = getattr(g, 'state', None)
    if not state:
        p = os.path.join('data', 'daily_state.json')
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as _f:
                    state = json.load(_f)
            except Exception:
                state = None
    month_start = state.get('month_start_balance_usd') if state else None
    month_meta = state.get('month_meta_total_usd') if state else None
    print('Guardiao month start (usd):', month_start, 'month_meta_usd:', month_meta)
except Exception as exc:
    print('Guardiao state check failed:', exc)
