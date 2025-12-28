"""Compute total account value in USDT using Binance API and notify via Telegram.
This script mirrors the dashboard's conversion rules and sends a report message.
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

try:
    from binance.client import Client
except Exception as e:
    print('python-binance not installed or import failed:', e)
    sys.exit(2)

try:
    from tools.send_telegram_message import send as send_telegram
except Exception:
    send_telegram = None

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')
if not api_key or not api_secret:
    print('Missing BINANCE_API_KEY/SECRET in environment')
    sys.exit(2)

from tools.binance_wrapper import get_binance_client
client = get_binance_client(api_key, api_secret)

SALDO_INICIAL = 1743.12


def convert_asset_to_usdt(asset, amount):
    asset = asset.upper()
    if amount == 0:
        return 0.0
    if asset == 'USDT':
        return amount
    symbols = [f"{asset}USDT", f"{asset}BUSD"]
    for sym in symbols:
        try:
            t = client.get_symbol_ticker(symbol=sym)
            price = float(t.get('price', 0))
            if price > 0:
                if sym.endswith('BUSD'):
                    busd_usdt = 1.0
                    try:
                        b = client.get_symbol_ticker(symbol='BUSDUSDT')
                        busd_usdt = float(b.get('price', 1.0)) or 1.0
                    except Exception:
                        busd_usdt = 1.0
                    return amount * price * busd_usdt
                return amount * price
        except Exception:
            continue
    # fallback via BTC
    try:
        t = client.get_symbol_ticker(symbol=f"{asset}BTC")
        price_asset_btc = float(t.get('price', 0))
        if price_asset_btc > 0:
            btc_usdt = float(client.get_symbol_ticker(symbol='BTCUSDT').get('price', 0))
            return amount * price_asset_btc * btc_usdt
    except Exception:
        pass
    return 0.0


def compute_total_usdt():
    total = 0.0
    info = client.get_account()
    for bal in info.get('balances', []):
        free = float(bal.get('free') or 0)
        locked = float(bal.get('locked') or 0)
        amount = free + locked
        if amount <= 0:
            continue
        asset = bal.get('asset')
        val = convert_asset_to_usdt(asset, amount)
        total += val
    return total


def main():
    try:
        total = compute_total_usdt()
    except Exception as e:
        print('Failed to compute total:', e)
        try:
            bal = client.get_asset_balance(asset='USDT')
            total = float(bal.get('free') or 0) + float(bal.get('locked') or 0)
        except Exception:
            total = SALDO_INICIAL

    print(f"Saldo do Momento (USDT): {total:.2f}")
    print(f"Banca Inicial (referência): {SALDO_INICIAL:.2f}")
    diff = total - SALDO_INICIAL
    print(f"Resultado: {diff:.2f} USDT")

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if send_telegram and token and chat_id:
        msg = f"📊 SINCRONIZAÇÃO: Minha banca inicial era ${SALDO_INICIAL:.2f}. Identifiquei agora na Binance o total de ${total:,.2f}. Iniciando rastreio."
        try:
            send_telegram(token, chat_id, msg)
            print('Telegram sent')
        except Exception as e:
            print('Failed to send Telegram:', e)
    else:
        print('Telegram not configured or send function not available')

if __name__ == '__main__':
    main()
