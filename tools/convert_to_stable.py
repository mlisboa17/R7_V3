import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools')))
from binance_wrapper import get_binance_client

def converter_lucro_para_stable(api_key=None, secret=None, min_usd=10):
    """
    Converte automaticamente todos os criptoativos (exceto USDT/BUSD) em USDT ao atingir a meta.
    min_usd: valor mínimo em USD para converter cada ativo
    """
    client = get_binance_client(api_key, secret)
    balances = client.get_account()['balances']
    for asset in balances:
        symbol = asset['asset']
        free = float(asset['free'])
        if symbol in ['USDT', 'BUSD'] or free == 0:
            continue
        # Busca par de conversão
        pair = symbol + 'USDT'
        try:
            price = float(client.get_symbol_ticker(symbol=pair)['price'])
            usd_value = free * price
            if usd_value < min_usd:
                continue
            # Vende tudo a mercado
            client.order_market_sell(symbol=pair, quantity=free)
        except Exception as e:
            # Se não existe par direto, ignora
            continue
