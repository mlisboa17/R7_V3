#!/usr/bin/env python3
"""Try to top-up USDT by selling minimal permitted quantities using MIN_NOTIONAL / LOT_SIZE filters."""
import os, sys
from dotenv import load_dotenv
load_dotenv()
from binance.client import Client
from tools.binance_wrapper import get_binance_client
from decimal import Decimal, ROUND_DOWN, getcontext

TARGET = 50.0
api = os.getenv('BINANCE_API_KEY')
secret = os.getenv('BINANCE_SECRET_KEY')
if not api or not secret:
    print('Binance credentials missing in .env')
    sys.exit(2)

c = get_binance_client(api, secret)
account = c.get_account()
balances = account.get('balances', [])

# compute current USDT available on account (free USDT)
usdt_free = 0.0
for b in balances:
    if b['asset'] == 'USDT':
        usdt_free = float(b['free'] or 0)
        break
print('Current free USDT:', usdt_free)

# read current generated from trades.log last sells (saves from previous runs)
gen = 0.0
try:
    with open('logs/trades.log','r',encoding='utf-8') as f:
        for line in f:
            if '| SELL' in line or '| SELL_MIN' in line:
                # parse received_usdt=
                if 'received_usdt=' in line:
                    try:
                        gen = max(gen, float(line.split('received_usdt=')[-1].strip()))
                    except Exception:
                        pass
except Exception:
    pass
print('Last recorded sell received (best guess):', gen)

need = max(0.0, TARGET - (usdt_free + gen))
print('Need additional USDT:', need)
if need <= 0:
    print('No top-up required')
    sys.exit(0)

candidates = []
for b in balances:
    asset = b['asset']
    free = float(b['free'] or 0)
    if free <= 0 or asset in ('USDT','BRL'):
        continue
    symbol = asset + 'USDT'
    try:
        ticker = c.get_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])
    except Exception:
        continue
    try:
        info = c.get_symbol_info(symbol)
    except Exception:
        continue
    lot = next((f for f in info.get('filters',[]) if f.get('filterType')=='LOT_SIZE'), None)
    min_not = next((f for f in info.get('filters',[]) if f.get('filterType') in ('MIN_NOTIONAL','NOTIONAL')), None)
    if not lot or not min_not:
        continue
    step = Decimal(str(lot.get('stepSize', '1'))) if lot else Decimal('1')
    min_qty = Decimal(str(lot.get('minQty', '0'))) if lot else Decimal('0')
    min_notional = Decimal(str((min_not.get('minNotional') if min_not else 0) or 0))
    # compute minimal qty that meets min_notional
    if price <= 0:
        continue
    if min_notional and min_notional > 0:
        required_qty = max(min_qty, (min_notional / Decimal(str(price))))
    else:
        required_qty = max(min_qty, Decimal('0'))
    # quantize to step (floor)
    getcontext().prec = 28
    multiplier = (required_qty / step).to_integral_value(rounding=ROUND_DOWN)
    qty = multiplier * step
    if qty <= Decimal(str(free)):
        expected = float(qty * Decimal(str(price)))
        candidates.append((asset, symbol, float(free), float(qty), expected))

# sort candidates by expected (smallest first)
candidates.sort(key=lambda x: x[4])
print('Candidate minimal sells:', candidates[:10])

collected = 0.0
    for asset, symbol, free, qty, expected in candidates:
    if collected >= need:
        break
    try:
        print('Trying sell', symbol, 'qty', qty)
            res = c.create_order(symbol=symbol, side='SELL', type='MARKET', quantity=str(qty))
            fills = res.get('fills') or []
            rec = 0.0
            if fills:
                for f in fills:
                    rec += float(f.get('qty', 0)) * float(f.get('price', 0)) if f.get('price') else 0
            if not rec:
                rec = float(res.get('cummulativeQuoteQty') or 0)
        collected += rec
        with open('logs/trades.log','a',encoding='utf-8') as f:
            f.write(f"{__import__('datetime').datetime.utcnow().isoformat()} | SELL_MIN_TOPUP | {symbol} | qty={qty} | received_usdt={rec}\n")
        print('Sold', symbol, 'received', rec)
    except Exception as e:
        print('Sell failed', symbol, type(e).__name__, e)

print('Collected additional USDT:', collected)
print('Total available now (free + collected):', usdt_free + collected + gen)

# If we reached target, write to data/daily_state.json usdt_operacional
if (usdt_free + collected + gen) >= TARGET:
    import json
    p='data/daily_state.json'
    try:
        d = json.load(open(p,'r',encoding='utf-8'))
    except Exception:
        d={}
    d['usdt_operacional']=round(usdt_free + collected + gen,6)
    json.dump(d, open(p,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
    print('Wrote data/daily_state.json usdt_operacional=', d['usdt_operacional'])
    # create control/go_live file to exit read-only
    os.makedirs('control', exist_ok=True)
    with open(os.path.join('control','go_live'),'w',encoding='utf-8') as f:
        f.write('go')
    print('Created control/go_live to trigger GO LIVE')
else:
    print('Top-up insufficient. Consider manual conversion or larger sells.')

sys.exit(0)
