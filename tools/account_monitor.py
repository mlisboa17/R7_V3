import json
import os
import logging
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

    async def atualizar_composicao(self):
        try:
            # Busca dados da conta com sistema de re-tentativa
            acct = await retry_api_call(lambda: self.client.get_account())
            balances = acct.get('balances', [])
            
            composition = {}
            total_geral_usdt = 0.0
            
            # Busca preços de mercado para conversão
            tickers = await retry_api_call(lambda: self.client.get_all_tickers())
            price_map = {t['symbol']: float(t['price']) for t in tickers}

            for b in balances:
                asset = b['asset']
                free = float(b['free'])
                locked = float(b['locked'])
                total_qty = free + locked

                if total_qty > 0:
                    # Converte o valor da moeda para USDT
                    if asset == 'USDT':
                        valor_usdt = total_qty
                    else:
                        pair = f"{asset}USDT"
                        valor_usdt = total_qty * price_map.get(pair, 0.0)

                    # Salva apenas o que tem valor relevante (> $0.10)
                    if valor_usdt > 0.10 or asset in self.assets_of_interest:
                        composition[asset] = {
                            'qty': total_qty,
                            'usd_val': round(valor_usdt, 2)
                        }
                        total_geral_usdt += valor_usdt

            # Adiciona Simple Earn Flexible
            # try:
            #     earn_data = self.client.get_simple_earn_flexible_product_list()
            #     for product in earn_data:
            #         if product.get('status') == 'PURCHASING':
            #             asset = product.get('asset')
            #             totalAmount = float(product.get('totalAmount', 0))
            #             if asset == 'USDT':
            #                 total_geral_usdt += totalAmount
            #                 composition['Earn/Staking'] = composition.get('Earn/Staking', 0) + totalAmount
            #             else:
            #                 pair = f"{asset}USDT"
            #                 valor_usdt = totalAmount * price_map.get(pair, 0.0)
            #                 total_geral_usdt += valor_usdt
            #                 composition['Earn/Staking'] = composition.get('Earn/Staking', 0) + valor_usdt
            # except Exception as e:
            #     logger.warning(f"Não foi possível buscar dados de Simple Earn: {e}")

            # Adiciona Metadados
            composition['_total_usdt'] = round(total_geral_usdt, 2)
            composition['_timestamp'] = datetime.now().isoformat()

            # Garante que a pasta data existe e salva
            os.makedirs('data', exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(composition, f, indent=2)
            
            logger.info(f"📸 Snapshot de banca atualizado: ${total_geral_usdt:.2f}")
            return composition

        except Exception as e:
            logger.error(f"Erro ao atualizar monitor de ativos: {e}")
            return None