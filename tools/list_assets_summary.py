import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bots.executor import ExecutorBot

# Load config
cfg_path = os.path.join('config', 'settings.json')
if os.path.exists(cfg_path):
    with open(cfg_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
else:
    config = {'config_trade': {'meta_diaria_brl': 99.09, 'usdt_margin': 294.0}}

exec_bot = ExecutorBot(config)
client = getattr(exec_bot, 'binance_client', None)
if not client:
    print('NO_BINANCE_CLIENT')
    sys.exit(2)

acct = client.get_account()
balances = acct.get('balances', [])
all_count = len(balances)
nonzero = [b for b in balances if float(b.get('free') or 0) > 0 or float(b.get('locked') or 0) > 0]
nonzero_count = len(nonzero)
print(f'Total assets: {all_count}')
print(f'Non-zero assets: {nonzero_count}')
if nonzero_count:
    print('\nNon-zero assets:')
    for b in nonzero:
        asset = b.get('asset')
        free = float(b.get('free') or 0)
        locked = float(b.get('locked') or 0)
        print(f' - {asset}: free={free}, locked={locked}')
