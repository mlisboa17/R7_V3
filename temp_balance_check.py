import os
from dotenv import load_dotenv
load_dotenv()
from tools.binance_wrapper import get_binance_client

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')

if api_key and api_secret:
    client = get_binance_client(api_key, api_secret)
    account = client.get_account()
    print('Saldos da conta:')
    total_usdt = 0.0
    for asset in account['balances']:
        free = float(asset['free'])
        locked = float(asset['locked'])
        total = free + locked
        if total > 0.0001:
            print(f'{asset["asset"]}: {total:.6f} (free: {free:.6f}, locked: {locked:.6f})')
            if asset['asset'] == 'USDT':
                total_usdt += total
            else:
                try:
                    ticker = client.get_symbol_ticker(symbol=f'{asset["asset"]}USDT')
                    price = float(ticker['price'])
                    valor_usdt = total * price
                    total_usdt += valor_usdt
                    print(f'  -> ${valor_usdt:.2f} USDT')
                except:
                    print(f'  -> Não conseguiu converter para USDT')
    print(f'Total em USDT (spot): ${total_usdt:.2f}')
else:
    print('API keys não encontradas')