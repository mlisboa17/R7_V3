import json
import os
import time
from binance.client import Client
from dotenv import load_dotenv
from bots.monthly_stats import set_monthly_balance

def update_account_composition():
    """Atualiza a composição do saldo da Binance e salva localmente."""
    try:
        load_dotenv()
        api_key = os.getenv('BINANCE_API_KEY')
        secret_key = os.getenv('BINANCE_SECRET_KEY')
        
        from tools.binance_wrapper import get_binance_client
        client = get_binance_client(api_key, secret_key)
        
        # Sincronizar tempo com o servidor
        server_time = client.get_server_time()
        local_time = int(time.time() * 1000)
        time_diff = server_time['serverTime'] - local_time
        if abs(time_diff) > 500:
            print(f"Ajustando diferença de tempo: {time_diff}ms")
            # O python-binance lida com isso automaticamente, mas para garantir
            client.session.params['timestamp'] = lambda: int(time.time() * 1000) + time_diff
        
        account = client.get_account()
        
        # Obter todos os preços de uma vez
        all_tickers = client.get_all_tickers()
        prices = {ticker['symbol']: float(ticker['price']) for ticker in all_tickers}
        
        composicao = {}
        total_usdt = 0.0
        
        for asset in account['balances']:
            free = float(asset['free'])
            locked = float(asset['locked'])
            total = free + locked
            if total > 0.0001:  # Ignorar saldos muito pequenos
                if asset['asset'] == 'USDT':
                    composicao['USDT'] = total
                    total_usdt += total
                else:
                    # Tentar converter para USDT
                    symbol_usdt = f"{asset['asset']}USDT"
                    if symbol_usdt in prices:
                        price = prices[symbol_usdt]
                        valor_usdt = total * price
                        composicao[asset['asset']] = valor_usdt
                        total_usdt += valor_usdt
                    else:
                        # Tentar BUSD
                        symbol_busd = f"{asset['asset']}BUSD"
                        if symbol_busd in prices:
                            price_busd = prices[symbol_busd]
                            # Assumir BUSD = USDT (aprox)
                            valor_usdt = total * price_busd
                            composicao[asset['asset']] = valor_usdt
                            total_usdt += valor_usdt
                        else:
                            # Se não conseguir, manter como cripto (não adicionar ao total)
                            composicao[asset['asset']] = total
        
        # Adicionar Earn/Staking (placeholder por enquanto)
        earn_usdt = 0.0  # Ajustado para 0
        composicao['Earn/Staking'] = earn_usdt
        total_usdt += earn_usdt
        
        composicao['_total_usdt'] = total_usdt
        
        # Salvar localmente
        os.makedirs('data', exist_ok=True)
        with open('data/account_composition.json', 'w', encoding='utf-8') as f:
            json.dump(composicao, f, indent=2)
        
        # Salvar saldo mensal
        set_monthly_balance(total_usdt)
        
        # Corrigir erro de Unicode no Windows removendo emoji
        print(f"Composição da conta atualizada com sucesso! Total: ${total_usdt:.2f} USDT")
        return composicao
    
    except Exception as e:
        # Corrigir erro de Unicode no Windows removendo emoji
        print(f"Erro ao atualizar composição: {e}")
        return None

if __name__ == "__main__":
    update_account_composition()