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
        
        # Buscar saldo REAL de Earn/Staking (API V2 atualizada)
        earn_usdt = 0.0
        try:
            # Simple Earn Flexible (novo endpoint)
            params = {'asset': 'USDT'}
            earn_response = client._request_margin_api('get', 'simple-earn/flexible/position', signed=True, data=params)
            
            if 'rows' in earn_response:
                for pos in earn_response['rows']:
                    asset = pos.get('asset', '')
                    total_amount = float(pos.get('totalAmount', 0))
                    
                    if asset in ['USDT', 'LDUSDT', 'FDUSD']:
                        earn_usdt += total_amount
                    else:
                        # Converter para USDT
                        symbol = f"{asset}USDT"
                        if symbol in prices:
                            earn_usdt += total_amount * prices[symbol]
            
            # Tentar buscar LDUSDT também (Launchpool)
            try:
                params_ld = {'asset': 'LDUSDT'}
                earn_ld = client._request_margin_api('get', 'simple-earn/flexible/position', signed=True, data=params_ld)
                if 'rows' in earn_ld:
                    for pos in earn_ld['rows']:
                        earn_usdt += float(pos.get('totalAmount', 0))
            except:
                pass
            
            print(f"✅ EARN encontrado: ${earn_usdt:.2f} USDT")
            composicao['Earn/Staking'] = earn_usdt
            total_usdt += earn_usdt
            
        except Exception as e:
            print(f"⚠️ Não foi possível buscar EARN: {e}")
            # Fallback: verificar se tem LDUSDT nos balances
            for asset in account['balances']:
                if asset['asset'] == 'LDUSDT':
                    ldusdt_total = float(asset['free']) + float(asset['locked'])
                    if ldusdt_total > 0:
                        earn_usdt = ldusdt_total
                        print(f"💡 LDUSDT detectado nos balances: ${earn_usdt:.2f}")
                        composicao['Earn/Staking'] = earn_usdt
                        total_usdt += earn_usdt
                        break
            
            if earn_usdt == 0:
                composicao['Earn/Staking'] = 0.0
        
        composicao['_total_usdt'] = total_usdt
        
        # Criar estrutura unificada para wallet_composition.json (usado pelo dashboard)
        from datetime import datetime
        wallet_data = {
            "_version": "1.0",
            "_description": "Arquivo MASTER unificado de composição da carteira",
            "_ultima_atualizacao": datetime.now().isoformat(),
            "_rate_usdt_brl": 5.5391,  # Fixo por enquanto
            "resumo": {
                "total_usdt": round(total_usdt, 2),
                "total_brl": round(total_usdt * 5.5391, 2),
                "usdt_spot": round(composicao.get('USDT', 0), 2),
                "earn_staking": round(earn_usdt, 2),
                "criptos_altcoins": round(total_usdt - composicao.get('USDT', 0) - earn_usdt, 2)
            },
            "holdings": {},
            "distribuicao_por_tipo": {
                "stable": round(composicao.get('USDT', 0), 2),
                "earn": round(earn_usdt, 2),
                "altcoin": 0.0,
                "meme": 0.0
            },
            "exposicao": {
                "spot_disponivel": round(composicao.get('USDT', 0), 2),
                "bloqueado_earn": round(earn_usdt, 2),
                "bloqueado_trades": 0.0,
                "total_disponivel_trading": round(composicao.get('USDT', 0), 2)
            }
        }
        
        # Adicionar holdings detalhados
        for asset, valor in composicao.items():
            if asset not in ['_total_usdt', 'Earn/Staking'] and valor > 0:
                if asset == 'USDT':
                    wallet_data['holdings'][asset] = {
                        "quantidade": round(valor, 8),
                        "valor_usdt": round(valor, 2),
                        "percentual": round((valor / total_usdt) * 100, 2),
                        "tipo": "stable"
                    }
                else:
                    wallet_data['holdings'][asset] = {
                        "quantidade": round(valor / prices.get(f"{asset}USDT", 1), 8),
                        "valor_usdt": round(valor, 2),
                        "percentual": round((valor / total_usdt) * 100, 2),
                        "tipo": "altcoin"
                    }
        
        # Adicionar EARN como holding separado
        if earn_usdt > 0:
            wallet_data['holdings']['LDUSDT'] = {
                "quantidade": round(earn_usdt, 8),
                "valor_usdt": round(earn_usdt, 2),
                "percentual": round((earn_usdt / total_usdt) * 100, 2),
                "tipo": "earn"
            }
        
        # Salvar em AMBOS os arquivos
        os.makedirs('data', exist_ok=True)
        
        # 1. wallet_composition.json (usado pelo dashboard)
        with open('data/wallet_composition.json', 'w', encoding='utf-8') as f:
            json.dump(wallet_data, f, indent=2)
        
        # 2. account_composition.json (legado)
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