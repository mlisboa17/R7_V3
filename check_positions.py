import os
from dotenv import load_dotenv
load_dotenv()
from tools.binance_wrapper import get_binance_client

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')

if api_key and api_secret:
    client = get_binance_client(api_key, api_secret)

    # Verificar posições futures
    try:
        positions = client.futures_position_information()
        print('Posições Futures:')
        total_futures = 0.0
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                print(f'{pos["symbol"]}: {pos["positionAmt"]} @ {pos["entryPrice"]}')
                # Calcular valor aproximado
                if pos['symbol'].endswith('USDT'):
                    valor = abs(float(pos['positionAmt'])) * float(pos['entryPrice'])
                    total_futures += valor
                    print(f'  -> ${valor:.2f} USDT')
        print(f'Total em Futures: ${total_futures:.2f}')
    except Exception as e:
        print(f'Erro ao verificar futures: {e}')

    # Verificar Earn products
    try:
        # Simple Earn
        simple_earn = client._get('sapi/v1/simple-earn/account', True)
        if simple_earn and 'totalAmountInUSDT' in simple_earn:
            print(f'Simple Earn: ${float(simple_earn["totalAmountInUSDT"]):.2f} USDT')
    except Exception as e:
        print(f'Erro ao verificar Simple Earn: {e}')

else:
    print('API keys não encontradas')