import json
import os
import logging
import asyncio
from datetime import datetime
from utils.binance_retry import retry_api_call

logger = logging.getLogger('account_monitor')

class AccountMonitor:
    def __init__(self, client):
        """
        Recebe o cliente da Binance já instanciado no Executor.
        """
        self.client = client
        self.path = os.path.join('data', 'account_composition.json')
        # Moedas que o R7_V3 monitora ativamente
        self.assets_of_interest = ['BTC', 'ETH', 'BNB', 'USDT', 'SOL', 'ADA', 'DOT', 'LINK', 'FET', 'RENDER', 'NEAR', 'AVAX', 'XRP']

    async def monitor_loop(self):
        """
        Loop contínuo que atualiza a composição da conta a cada 30 segundos.
        """
        logger.info("🔄 Iniciando monitor contínuo de saldo (30s interval)")
        while True:
            try:
                await self.atualizar_composicao()
                await asyncio.sleep(30)  # Atualiza a cada 30 segundos
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
                await asyncio.sleep(10)  # Espera 10 segundos em caso de erro

    async def atualizar_composicao(self):
        try:
            account_info = await self.client.get_account()
            balances = account_info['balances']
            nova_composicao = {}
            total_geral_usdt = 0.0

            for b in balances:
                qty = float(b['free']) + float(b['locked'])
                if qty <= 0: continue
                
                asset = b['asset']
                if asset == 'USDT':
                    valor_usd = qty
                else:
                    try:
                        # Tenta pegar o preço atual da Binance
                        ticker = await self.client.get_symbol_ticker(symbol=f"{asset}USDT")
                        valor_usd = qty * float(ticker['price'])
                    except:
                        continue # Ignora moedas que não têm par USDT (como GIGGLE)

                if valor_usd > 1.0: # Só registra o que vale mais de 1 dólar
                    nova_composicao[asset] = {"qty": qty, "usd_val": round(valor_usd, 2)}
                    total_geral_usdt += valor_usd

            nova_composicao['_total_usdt'] = round(total_geral_usdt, 2)
            nova_composicao['_timestamp'] = datetime.now().isoformat()

            # GRAVAÇÃO DINÂMICA
            with open('data/account_composition.json', 'w') as f:
                json.dump(nova_composicao, f, indent=2)
                
        except Exception as e:
            logger.error(f"Erro ao atualizar saldo dinâmico: {e}")