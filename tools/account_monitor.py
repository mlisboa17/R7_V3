import asyncio
import json
import logging
from datetime import datetime
from binance.exceptions import BinanceAPIException

logger = logging.getLogger('account_monitor')

class AccountMonitor:
    def __init__(self, client, gestor=None, time_sync=None):
        self.client = client
        self.gestor = gestor
        self.time_sync = time_sync  # Referência ao TimeSyncManager para recuperação
        self.path = 'data/account_composition.json'
        self.timestamp_error_count = 0
        self.max_timestamp_errors = 3

    async def get_earn_balance(self):
        """Earn não está disponível via AsyncClient - retorna 0."""
        # As APIs get_simple_earn_flexible_product_position não existem no AsyncClient
        # Quando tiver acesso via API REST direta, implementar aqui
        return 0.0

    async def get_grid_bots_balance(self):
        """Grid Trading não está disponível via AsyncClient - retorna 0."""
        # As APIs get_spot_grid_strategies não existem no AsyncClient
        # Quando tiver acesso via API REST direta, implementar aqui
        return 0.0

    async def monitor_loop(self):
        logger.info("📡 Monitor de Saldo Dinâmico Iniciado.")
        erro_consecutivos = 0
        delay = 30
        
        while True:
            try:
                # 1. Busca saldo Spot (USDT livre) - ÚNICA FONTE DE VERDADE
                try:
                    res = await self.client.get_asset_balance(asset='USDT')
                    saldo_spot = float(res['free']) + float(res['locked'])
                    self.timestamp_error_count = 0  # Reset contador
                    
                except BinanceAPIException as e_spot:
                    # Verifica se é erro de timestamp
                    if e_spot.code == -1021:
                        self.timestamp_error_count += 1
                        logger.error(f"❌ Erro de Timestamp (#️⃣ {self.timestamp_error_count}): {e_spot}")
                        
                        # Tenta recuperar se TimeSyncManager está disponível
                        if self.time_sync and hasattr(self.time_sync, 'recover_from_timestamp_error'):
                            logger.warning(f"🔄 Tentando recuperar do erro de timestamp...")
                            try:
                                recovery_success = await self.time_sync.recover_from_timestamp_error()
                                if recovery_success:
                                    logger.info(f"✅ Recuperação bem-sucedida!")
                                    await asyncio.sleep(5)
                                    continue  # Tenta novamente
                                else:
                                    logger.error(f"❌ Recuperação falhou. Aguardando {delay}s...")
                            except Exception as recovery_error:
                                logger.error(f"❌ Erro durante recuperação: {recovery_error}")
                        
                        # Se muitos erros, aumenta delay
                        if self.timestamp_error_count >= self.max_timestamp_errors:
                            delay = 60
                            logger.warning(f"⚠️ Muitos erros de timestamp. Aumentando delay para {delay}s")
                        
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"❌ Erro ao buscar saldo Spot: [Code {e_spot.code}] {e_spot.message}")
                        await asyncio.sleep(10)
                        continue
                        
                except Exception as e_spot:
                    logger.error(f"❌ Erro ao buscar saldo Spot: {type(e_spot).__name__} - {e_spot}")
                    await asyncio.sleep(10)
                    continue

                # 2. Busca saldos dinâmicos (Earn e Grid)
                saldo_earn = await self.get_earn_balance()
                saldo_bots_grade = await self.get_grid_bots_balance()

                # 3. Busca saldo em outras criptos (via wallet_composition.json)
                saldo_cripto = 0.0
                try:
                    import json
                    with open('data/wallet_composition.json', 'r') as f:
                        wallet = json.load(f)
                        saldo_cripto = wallet.get('resumo', {}).get('criptos_altcoins', 0.0)
                except:
                    pass

                # 4. Cálculo da Equidade Total - INCLUI TUDO (SPOT + EARN + CRIPTO)
                saldo_total = saldo_spot + saldo_earn + saldo_cripto
                
                # 5. Registra no Gestor com campos separados
                try:
                    if self.gestor:
                        self.gestor.registrar_snapshot_momento(
                            saldo_total=saldo_total,
                            saldo_spot=saldo_spot,
                            saldo_earn=saldo_earn,
                            saldo_cripto=saldo_cripto
                        )
                except Exception as e_gestor:
                    logger.error(f"❌ Erro ao registrar snapshot no gestor: {type(e_gestor).__name__} - {e_gestor}")
                
                # Log detalhado com divisão
                logger.info(f"📸 Snapshot de banca atualizado: ${saldo_total:.2f}")
                erro_consecutivos = 0  # Reset contador de erros
                delay = 30  # Reset delay

            except Exception as e:
                erro_consecutivos += 1
                logger.error(f"⚠️ Erro no monitoramento (tentativa {erro_consecutivos}): {type(e).__name__} - {e}")
                if erro_consecutivos > 5:
                    logger.error(f"🚨 Muitos erros consecutivos! Aumentando delay para 60s...")
                    await asyncio.sleep(60)
                else:
                    await asyncio.sleep(10)
                continue
            
            await asyncio.sleep(delay)