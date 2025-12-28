import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

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

try:
    acct = client.get_account()
except Exception as e:
    print('ERROR', str(e))
    sys.exit(3)

balances = acct.get('balances', [])
# Print all assets (including zero balances) as JSON
out = []
for b in balances:
    symbol = b.get('asset')
    free = float(b.get('free') or 0)
    locked = float(b.get('locked') or 0)
    out.append({'asset': symbol, 'free': free, 'locked': locked})

# Sort by asset name
out = sorted(out, key=lambda x: x['asset'])
print(json.dumps(out, indent=2, ensure_ascii=False))
