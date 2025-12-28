#!/usr/bin/env python3
"""Rebalance script:
- Inspect spot balances and compute unrealized PnL for assets (using USDT pairs)
- Sell assets in profit until we accumulate $50 USDT
- If insufficient, convert BRL 294 to USDT
- Update data/daily_state.json and logs/trades.log
- Send Telegram notification with result
"""
import os
import sys
import json
import math
from dotenv import load_dotenv
load_dotenv()
from decimal import Decimal, ROUND_DOWN, getcontext

TARGET_USDT = 50.0
BRL_TO_CONVERT = 294.0

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
REAL_TRADING = os.getenv('REAL_TRADING', '0') == '1'


def log_trade(msg):
    with open('logs/trades.log', 'a', encoding='utf-8') as f:
        f.write(msg + "\n")


def update_daily_state(usdt_added):
    path = 'data/daily_state.json'
    try:
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
    except Exception:
        d = {'data': None, 'banca_inicial_brl': 0.0, 'lucro_acumulado_dia_brl': 0.0}

    d['usdt_operacional'] = round(d.get('usdt_operacional', 0.0) + usdt_added, 6)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print('Failed to write daily_state.json', e)
        return False


def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print('Telegram not configured; skipping send')
        return False
    try:
        from telegram import Bot
        import asyncio
        async def _send():
            bot = Bot(TELEGRAM_TOKEN)
            try:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
                await bot.close()
                return True
            except Exception as e:
                print('Telegram send failed', type(e).__name__, e)
                await bot.close()
                return False
        return asyncio.run(_send())
    except Exception as e:
        print('Telegram error', type(e).__name__, e)
        return False


def main():
    if not REAL_TRADING:
        print('REAL_TRADING is not enabled; aborting per safety.')
        return 2

    try:
        from binance.client import Client
    except Exception as e:
        print('Binance client missing:', e)
        return 3

    api = os.getenv('BINANCE_API_KEY')
    secret = os.getenv('BINANCE_SECRET_KEY')
    if not api or not secret:
        print('Binance keys missing in .env')
        return 4

    from tools.binance_wrapper import get_binance_client
    client = get_binance_client(api, secret)

    account = client.get_account()
    balances = account.get('balances', [])

    brl_balance = 0.0
    for bal in balances:
        if bal.get('asset') == 'BRL':
            brl_balance = float(bal.get('free') or 0)
    print('BRL balance:', brl_balance)

    winners = []  # (asset, free_qty, avg_buy_price, cur_price, usd_value, profit_usd)

    for bal in balances:
        asset = bal.get('asset')
        free = float(bal.get('free') or 0)
        locked = float(bal.get('locked') or 0)
        total_qty = free + locked
        if total_qty <= 0 or asset in ('USDT', 'BRL'):
            continue
        symbol = asset + 'USDT'
        try:
            # check symbol exists
            cur = client.get_symbol_ticker(symbol=symbol)
            cur_price = float(cur['price'])
        except Exception:
            # skip non-USDT pairs
            continue
        # get recent trades for this symbol to compute average buy price
        try:
            trades = client.get_my_trades(symbol=symbol, limit=1000)
            buy_qty = 0.0
            buy_cost = 0.0
            for t in trades:
                if t.get('isBuyer'):
                    q = float(t.get('qty') or 0)
                    p = float(t.get('price') or 0)
                    buy_qty += q
                    buy_cost += q * p
            avg_buy = (buy_cost / buy_qty) if buy_qty > 0 else None
        except Exception:
            avg_buy = None
        if avg_buy:
            # compute unrealized profit for total_qty
            profit_usd = (cur_price - avg_buy) * total_qty
            usd_value = cur_price * total_qty
            if profit_usd > 0:
                winners.append((asset, free, avg_buy, cur_price, usd_value, profit_usd))

    # Sort winners by profit descending
    winners.sort(key=lambda x: x[5], reverse=True)

    total_usdt_generated = 0.0
    sell_records = []

    for w in winners:
        if total_usdt_generated >= TARGET_USDT:
            break
        asset, free, avg_buy, cur_price, usd_value, profit = w
        # how much USDT we still need
        need = TARGET_USDT - total_usdt_generated
        raw_qty = Decimal(str(need)) / Decimal(str(cur_price)) if cur_price else Decimal('0')
        # get LOT_SIZE filters to compute valid quantity increment and minQty
        symbol = asset + 'USDT'
        try:
            info = client.get_symbol_info(symbol)
            lot = next((f for f in info.get('filters', []) if f.get('filterType') == 'LOT_SIZE'), None)
            if lot:
                step = Decimal(str(lot.get('stepSize', '1')))
                min_qty = Decimal(str(lot.get('minQty', '0')))
                getcontext().prec = 28
                quant = (raw_qty / step).to_integral_value(rounding=ROUND_DOWN) * step
                qty_to_sell = min(Decimal(str(free)), quant)
                qty_to_sell = float(qty_to_sell)
            else:
                qty_to_sell = min(free, float(raw_qty))
        except Exception:
            qty_to_sell = min(free, round(raw_qty, 8))

        try:
            # ensure qty meets min_qty if provided
            if 'min_qty' in locals() and Decimal(str(qty_to_sell)) < min_qty:
                print(f'Skipping {asset}: computed qty {qty_to_sell} below min qty {min_qty}')
                continue
            if qty_to_sell <= 0:
                continue

            print(f'Selling {qty_to_sell} {asset} (symbol={symbol}) to generate USDT')
            res = client.create_order(symbol=symbol, side='SELL', type='MARKET', quantity=str(qty_to_sell))
            fills = res.get('fills') or []
            received = 0.0
            if fills:
                for f in fills:
                    received += float(f.get('qty', 0)) * float(f.get('price', 0)) if f.get('price') else 0
            if not received:
                received = float(res.get('cummulativeQuoteQty') or 0)
            total_usdt_generated += received
            sell_records.append({'asset': asset, 'qty': qty_to_sell, 'received_usdt': received, 'symbol': symbol})
            log_trade(f"{__import__('datetime').datetime.utcnow().isoformat()} | SELL | {symbol} | qty={qty_to_sell} | received_usdt={received}")
        except Exception as e:
            print('Sell failed for', asset, type(e).__name__, e)

    # Secondary attempt: if still short, try selling minQty of winners (small fractional sells) to collect tiny amounts
    if total_usdt_generated < TARGET_USDT:
        print('Secondary pass: attempting minQty sells to top up remaining USDT')
        for w in winners:
            if total_usdt_generated >= TARGET_USDT:
                break
            asset, free, avg_buy, cur_price, usd_value, profit = w
            symbol = asset + 'USDT'
            try:
                info = client.get_symbol_info(symbol)
                lot = next((f for f in info.get('filters', []) if f.get('filterType') == 'LOT_SIZE'), None)
                if not lot:
                    continue
                min_qty = float(lot.get('minQty', '0'))
                step = float(lot.get('stepSize', '1'))
                if free < min_qty:
                    continue
                qty_to_sell = min(Decimal(str(free)), Decimal(str(min_qty)))
                qty_to_sell = float(qty_to_sell)
                if qty_to_sell <= 0:
                    continue
                print(f'Secondary sell: selling minQty {qty_to_sell} {asset} (symbol={symbol})')
                res = client.create_order(symbol=symbol, side='SELL', type='MARKET', quantity=str(qty_to_sell))
                fills = res.get('fills') or []
                received = 0.0
                if fills:
                    for f in fills:
                        received += float(f.get('qty', 0)) * float(f.get('price', 0)) if f.get('price') else 0
                if not received:
                    received = float(res.get('cummulativeQuoteQty') or 0)
                total_usdt_generated += received
                log_trade(f"{__import__('datetime').datetime.utcnow().isoformat()} | SELL_MIN | {symbol} | qty={qty_to_sell} | received_usdt={received}")
            except Exception as e:
                print('Secondary sell failed for', asset, type(e).__name__, e)

    # If still short, try converting BRL_TO_CONVERT to USDT
    brl_converted = 0.0
    if total_usdt_generated < TARGET_USDT:
        try:
            # attempt market buy of USDTBRL using quoteOrderQty=BRL_TO_CONVERT
            print('Converting BRL to USDT for remaining margin...')
            res = client.create_order(symbol='USDTBRL', side='BUY', type='MARKET', quoteOrderQty=str(BRL_TO_CONVERT))
            received = float(res.get('cummulativeQuoteQty') or 0)
            # For BUY on USDTBRL, cummulativeQuoteQty is BRL spent; we need bought qty: check fills qty
            bought_qty = 0.0
            for f in res.get('fills', []) or []:
                bought_qty += float(f.get('qty') or 0)
            if not bought_qty:
                # fallback: approximate by BRL/price
                ticker = client.get_symbol_ticker(symbol='USDTBRL')
                price = float(ticker['price'])
                bought_qty = BRL_TO_CONVERT / price if price else 0
            total_usdt_generated += bought_qty
            brl_converted = BRL_TO_CONVERT
            log_trade(f"{__import__('datetime').datetime.utcnow().isoformat()} | CONVERT BRL->USDT | brl={BRL_TO_CONVERT} | received_usdt={bought_qty}")
        except Exception as e:
            print('BRL->USDT conversion failed:', type(e).__name__, e)

    # Update daily_state.json with USDT operational balance
    update_daily_state(round(total_usdt_generated, 6))

    # Prepare Telegram message
    msg = f"💰 Caixa gerado! {total_usdt_generated:.6f} USDT disponíveis para trade. Iniciando operações reais."
    send_ok = send_telegram(msg)

    print('Done. total_usdt_generated=', total_usdt_generated, 'telegram_sent=', send_ok)
    return 0


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
