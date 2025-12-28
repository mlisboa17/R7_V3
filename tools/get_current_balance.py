import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from bots.guardiao import GuardiaoBot
from bots.executor import ExecutorBot

# Load config
cfg_path = os.path.join('config', 'settings.json')
if os.path.exists(cfg_path):
    with open(cfg_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
else:
    config = {'config_trade': {'meta_diaria_brl': 99.09, 'usdt_margin': 294.0}, 'banca_total_brl': 9909.25}

guardiao = GuardiaoBot(config)
executor = ExecutorBot(config)

output = {}
output['executor_has_client'] = bool(getattr(executor, 'binance_client', None))

# Try to get USDTBRL rate
try:
    rate = executor.get_usdt_brl_rate()
except Exception:
    rate = guardiao.state.get('last_usdt_brl_rate', 1.0) or 1.0
output['usdt_brl_rate'] = rate

# Try active snapshot via executor
try:
    closing = executor.obter_saldo_real_spot(guardiao)
    output['source'] = 'executor_snapshot'
    output['total_brl'] = float(closing)
except Exception as e:
    # fallback calculation
    spot = guardiao.get_spot()
    usdt_oper = guardiao.state.get('usdt_operacional', 0.0)
    total = spot + usdt_oper * rate
    output['source'] = 'fallback_local'
    output['total_brl'] = round(total, 2)
    output['fallback_details'] = {'spot_brl': spot, 'usdt_operacional': usdt_oper, 'rate_used': rate}

# Also include some state
output['spot_brl'] = guardiao.get_spot()
output['usdt_operacional'] = guardiao.state.get('usdt_operacional', 0.0)
output['lucro_do_dia_brl'] = guardiao.get_lucro()

print(json.dumps(output, indent=2, ensure_ascii=False))
