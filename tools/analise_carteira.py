import os
from tools.binance_wrapper import get_binance_client

def analisar_carteira_e_sugerir(api_key=None, secret=None, min_usd=10):
    """
    Analisa todas as criptos da carteira e sugere:
    - Esperar até X% (maior potencial de alta)
    - Vender toda a carteira (se maioria estiver em lucro ou mercado negativo)
    - Outra sugestão baseada na distribuição
    """
    client = get_binance_client(api_key, secret)
    balances = client.get_account()['balances']
    sugestoes = []
    total_usdt = 0
    total_lucro = 0
    total_cripto = 0
    for asset in balances:
        symbol = asset['asset']
        free = float(asset['free'])
        if symbol in ['USDT', 'BUSD'] or free == 0:
            continue
        pair = symbol + 'USDT'
        try:
            price = float(client.get_symbol_ticker(symbol=pair)['price'])
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
                    if fee_asset == symbol:
                        total_fee += fee
                    total_qty += qty
                    total_cost += qty * price_trade
            if total_qty == 0:
                continue
            avg_price = (total_cost + (total_fee * price)) / total_qty
            usd_value = free * price
            lucro = (price - avg_price) * free
            total_usdt += usd_value
            total_cripto += usd_value
            if lucro > 0:
                total_lucro += lucro
                sugestoes.append(f"{symbol}: lucro de ${lucro:.2f} USDT")
            else:
                sugestoes.append(f"{symbol}: prejuízo de ${lucro:.2f} USDT")
        except Exception:
            continue
    if total_lucro > 0.7 * total_cripto:
        acao = "Sugestão: Vender toda a carteira, maioria em lucro."
    elif total_lucro < 0:
        acao = "Sugestão: Esperar recuperação, maioria em prejuízo."
    else:
        acao = "Sugestão: Avaliar individualmente ou esperar até 1,5%."
    return total_usdt, total_lucro, sugestoes, acao
