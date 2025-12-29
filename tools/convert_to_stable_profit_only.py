import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools')))
from binance_wrapper import get_binance_client

def converter_lucro_criptos_para_stable_somente_lucro(api_key=None, secret=None, min_usd=10):
    """
    Converte para USDT apenas as criptos que estão com lucro (preço atual > preço médio de compra).
    min_usd: valor mínimo em USD para converter cada ativo
    """
    client = get_binance_client(api_key, secret)
    balances = client.get_account()['balances']
    vendidos = []
    for asset in balances:
        symbol = asset['asset']
        free = float(asset['free'])
        if symbol in ['USDT', 'BUSD'] or free == 0:
            continue
        pair = symbol + 'USDT'
        try:
            price = float(client.get_symbol_ticker(symbol=pair)['price'])
            avg_price = None
            # Busca preço médio de compra
            trades = client.get_my_trades(symbol=pair)
            if not trades:
                continue
            total_qty = 0
            total_cost = 0
            total_fee = 0
            for t in trades:
                if t['isBuyer']:
                    qty = float(t['qty'])
                    price_trade = float(t['price'])
                    fee = float(t.get('commission', 0))
                    fee_asset = t.get('commissionAsset', symbol)
                    # Se a taxa foi paga na própria moeda, soma ao custo
                    if fee_asset == symbol:
                        total_fee += fee
                    total_qty += qty
                    total_cost += qty * price_trade
            if total_qty == 0:
                continue
            # Ajusta o preço médio incluindo as taxas pagas na moeda
            avg_price = (total_cost + (total_fee * price)) / total_qty
            if price > avg_price:
                usd_value = free * price
                if usd_value < min_usd:
                    continue
                client.order_market_sell(symbol=pair, quantity=free)
                vendidos.append(f"{symbol}: {free:.4f} vendidos a ${price:.2f} (lucro)")
        except Exception as e:
            continue

    # Envia mensagem no Telegram se houve vendas
    if vendidos:
        try:
            import os
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            if token and chat_id:
                from tools.send_telegram_message import send as send_telegram
                msg = "💰 Fechamento de lucros realizado:\n" + "\n".join(vendidos)
                send_telegram(token, chat_id, msg)
        except Exception as e:
            pass
