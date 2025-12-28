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

# get USDTBRL rate
try:
    usdt_brl = exec_bot.get_usdt_brl_rate()
except Exception:
    usdt_brl = 1.0

acct = client.get_account()
balances = acct.get('balances', [])
nonzero = [b for b in balances if float(b.get('free') or 0) > 0 or float(b.get('locked') or 0) > 0]
results = []
total_brl = 0.0

# helper to get ticker price
def get_price(symbol):
    try:
        t = client.get_symbol_ticker(symbol=symbol)
        return float(t.get('price') or 0)
    except Exception:
        try:
            a = client.get_avg_price(symbol=symbol)
            return float(a.get('price') or 0)
        except Exception:
            return None

# get BTCUSDT rate once
btc_usdt = get_price('BTCUSDT') or 0

for b in nonzero:
    asset = b.get('asset')
    free = float(b.get('free') or 0)
    locked = float(b.get('locked') or 0)
    qty = free + locked
    brl_value = None
    method = None

    if asset == 'BRL':
        brl_value = qty
        method = 'BRL'
    elif asset == 'USDT':
        brl_value = qty * usdt_brl
        method = 'USDT'
    else:
        # try ASSETUSDT
        price = get_price(f"{asset}USDT")
        if price:
            brl_value = qty * price * usdt_brl
            method = f'{asset}USDT'
        else:
            # try ASSETBUSD -> BUSD~USDT
            price = get_price(f"{asset}BUSD")
            busd_to_usdt = get_price('BUSDUSDT') or 1.0
            if price:
                brl_value = qty * price * busd_to_usdt * usdt_brl
                method = f'{asset}BUSD'
            else:
                # try ASSETBTC
                price = get_price(f"{asset}BTC")
                if price and btc_usdt:
                    brl_value = qty * price * btc_usdt * usdt_brl
                    method = f'{asset}BTC'
                else:
                    method = None

    results.append({'asset': asset, 'qty': qty, 'brl': round(brl_value, 2) if brl_value is not None else None, 'method': method})
    if brl_value is not None:
        total_brl += brl_value

# print compact list and total
import math
print('Ativos não-zero e estimativa BRL (quando possível):')
for r in results:
    if r['qty'] <= 0:
        continue
    if r['brl'] is None:
        print(f" - {r['asset']}: qty={r['qty']}  -> BRL=SEM_CONVERSAO (método={r['method']})")
    else:
        print(f" - {r['asset']}: qty={r['qty']}  -> BRL=R$ {r['brl']:.2f} (via {r['method']})")

print('\nTotal estimado (soma dos convertidos): R$ {:.2f}'.format(total_brl))
print('USDT->BRL rate used:', usdt_brl)

# Also save to data/nonzero_assets_brl.json
out = {'total_brl': round(total_brl,2), 'rate_usdt_brl': usdt_brl, 'assets': results}
with open('data/nonzero_assets_brl.json','w',encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print('Saved data/nonzero_assets_brl.json')
