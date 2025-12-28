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

# Helpers
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

usdt_brl = exec_bot.get_usdt_brl_rate() or 1.0
rates_cache = {}

acct = client.get_account()
balances = acct.get('balances', [])
nonzero = [b for b in balances if float(b.get('free') or 0) + float(b.get('locked') or 0) > 0]

quotes = ['USDT','BUSD','BTC','ETH','BNB','USDC']
results = []
total_brl = 0.0

# prefetch common pairs to reduce calls
def pref(symbol):
    if symbol in rates_cache:
        return rates_cache[symbol]
    p = get_price(symbol)
    rates_cache[symbol] = p
    return p

# prefetch BTCUSDT, ETHUSDT, BNBUSDT, BUSDUSDT, USDCUSDT
pref('BTCUSDT'); pref('ETHUSDT'); pref('BNBUSDT'); pref('BUSDUSDT'); pref('USDCUSDT')

for b in nonzero:
    asset = b.get('asset')
    free = float(b.get('free') or 0)
    locked = float(b.get('locked') or 0)
    qty = free + locked
    brl_value = None
    method = None

    if qty <= 0:
        continue

    if asset == 'BRL':
        brl_value = qty
        method = 'BRL'
    elif asset == 'USDT':
        brl_value = qty * usdt_brl
        method = 'USDT'
    else:
        # try quotes
        for q in quotes:
            pair = f"{asset}{q}"
            price = pref(pair)
            if price and price > 0:
                # convert depending on quote
                if q == 'USDT':
                    brl_value = qty * price * usdt_brl
                    method = f"{asset}USDT"
                elif q == 'BUSD':
                    busd_usdt = pref('BUSDUSDT') or 1.0
                    brl_value = qty * price * busd_usdt * usdt_brl
                    method = f"{asset}BUSD->BUSDUSDT"
                elif q == 'USDC':
                    usdc_usdt = pref('USDCUSDT') or 1.0
                    brl_value = qty * price * usdc_usdt * usdt_brl
                    method = f"{asset}USDC->USDCUSDT"
                elif q == 'BTC':
                    btc_usdt = pref('BTCUSDT')
                    if btc_usdt:
                        brl_value = qty * price * btc_usdt * usdt_brl
                        method = f"{asset}BTC->BTCUSDT"
                elif q == 'ETH':
                    eth_usdt = pref('ETHUSDT')
                    if eth_usdt:
                        brl_value = qty * price * eth_usdt * usdt_brl
                        method = f"{asset}ETH->ETHUSDT"
                elif q == 'BNB':
                    bnb_usdt = pref('BNBUSDT')
                    if bnb_usdt:
                        brl_value = qty * price * bnb_usdt * usdt_brl
                        method = f"{asset}BNB->BNBUSDT"
                if brl_value is not None:
                    break
        # Try reverse pair (USDTASSET) - less common, but handle if exists
        if brl_value is None:
            for q in ['USDT','BTC','ETH','BNB','BUSD','USDC']:
                pair = f"{q}{asset}"
                price = pref(pair)
                if price and price > 0:
                    # price is quote asset per asset, so asset = quote/price
                    if q == 'USDT':
                        brl_value = qty * (1/price) * usdt_brl
                        method = f"USDT{asset} (inverted)"
                    elif q == 'BTC':
                        btc_usdt = pref('BTCUSDT')
                        if btc_usdt:
                            brl_value = qty * (1/price) * btc_usdt * usdt_brl
                            method = f"BTC{asset} (inverted)->BTCUSDT"
                    elif q == 'ETH':
                        eth_usdt = pref('ETHUSDT')
                        if eth_usdt:
                            brl_value = qty * (1/price) * eth_usdt * usdt_brl
                            method = f"ETH{asset} (inverted)->ETHUSDT"
                    elif q == 'BUSD':
                        busd_usdt = pref('BUSDUSDT') or 1.0
                        brl_value = qty * (1/price) * busd_usdt * usdt_brl
                        method = f"BUSD{asset} (inverted)"
                    if brl_value is not None:
                        break

    results.append({'asset': asset, 'qty': qty, 'brl': round(brl_value,2) if brl_value is not None else None, 'method': method})
    if brl_value is not None:
        total_brl += brl_value

# sort by brl desc, treat None as 0
results_sorted = sorted(results, key=lambda x: x['brl'] or 0, reverse=True)

# print top assets
print('Top assets by BRL value:')
for r in results_sorted[:10]:
    if r['brl'] is None:
        print(f" - {r['asset']}: qty={r['qty']} -> SEM_CONVERSAO (method={r['method']})")
    else:
        print(f" - {r['asset']}: qty={r['qty']} -> R$ {r['brl']:.2f} (via {r['method']})")

print('\nTotal estimated BRL (converted assets): R$ {:.2f}'.format(total_brl))

# Save results
out = {'total_brl': round(total_brl,2), 'rate_usdt_brl': usdt_brl, 'assets': results_sorted}
with open('data/nonzero_assets_brl_extended.json','w',encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print('Saved data/nonzero_assets_brl_extended.json')
