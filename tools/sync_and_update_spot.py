import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
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

if not executor.binance_client:
    print('No Binance client available. Cannot fetch on-chain balances.')
    sys.exit(2)

print('Fetching account balances from Binance...')
client = executor.binance_client
rate = executor.get_usdt_brl_rate() or guardiao.state.get('last_usdt_brl_rate', 1.0)
print(f'Using USDT->BRL rate: {rate}')
try:
    acct = client.get_account()
except Exception as e:
    print('Failed to get account:', e)
    sys.exit(3)

balances = acct.get('balances', [])
asset_breakdown = []
total_brl = 0.0
for asset in balances:
    try:
        free = float(asset.get('free', 0) or 0)
    except Exception:
        free = 0.0
    if free <= 0:
        continue
    symbol = asset.get('asset')
    entry = {'asset': symbol, 'free': free, 'brl_value': None, 'note': ''}
    if symbol == 'BRL':
        entry['brl_value'] = round(free, 2)
        total_brl += entry['brl_value']
    elif symbol == 'USDT':
        entry['brl_value'] = round(free * rate, 2)
        total_brl += entry['brl_value']
    else:
        # try assetUSDT
        pair = f"{symbol}USDT"
        try:
            tick = client.get_symbol_ticker(symbol=pair)
            price = float(tick.get('price') or 0)
            brl_val = free * price * rate
            entry['brl_value'] = round(brl_val, 2)
            total_brl += entry['brl_value']
        except Exception:
            entry['note'] = 'no pair to USDT; not converted'
    asset_breakdown.append(entry)

# Show result
print('\nAsset breakdown:')
for e in asset_breakdown:
    print(f" - {e['asset']}: free={e['free']} -> BRL={e['brl_value']} {e['note']}")
print(f'Computed total BRL: R$ {total_brl:.2f}')

# Confirm and update state
confirm = os.getenv('AUTO_CONFIRM_UPDATE', '1')  # default to auto-confirm
if confirm == '1':
    old_spot = guardiao.get_spot()
    guardiao.state['spot_brl'] = round(total_brl, 2)
    guardiao._write_state(guardiao.state)
    guardiao.salvar_progresso()
    print(f"Updated guardiao.state['spot_brl']: {old_spot} -> {guardiao.state['spot_brl']}")
    print('State and progress file updated.')
else:
    print('AUTO_CONFIRM_UPDATE not set; did not update state.')

print('Done.')
