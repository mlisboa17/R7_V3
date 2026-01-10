import asyncio
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger('lock_notifier')

class LockNotifier:
    def __init__(self, guardiao, estrategista, executor, path=None, interval=15):
        self.guardiao = guardiao
        self.estrategista = estrategista
        self.executor = executor
        self.interval = interval
        self.path = path or os.path.join('data', 'locks_status.json')
        os.makedirs('data', exist_ok=True)

    async def monitor_loop(self):
        logger.info('🔎 Iniciando verificador de travas/flags (apenas leitura)')
        while True:
            try:
                status = self._gather_status()
                # Grava status para inspeção externa
                try:
                    with open(self.path, 'w', encoding='utf-8') as f:
                        json.dump(status, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.debug(f'Erro ao gravar locks_status: {e}')

                # Loga avisos concisos quando alguma trava estiver ativa
                if status.get('estrategista', {}).get('trava_dia_encerrado'):
                    logger.warning('⚠️ Estrategista: trava_dia_encerrado ATIVADA')
                if status.get('guardiao', {}).get('meta_batida'):
                    logger.warning('⚠️ Guardião: meta diária batida (bloqueio de operações)')
                if status.get('guardiao', {}).get('limite_exposicao'):
                    # Ponto crítico: avisa se o limite de $2200 for atingido
                    logger.warning(f"⚠️ Guardião: Limite atingido! Exp. Atual: ${status['guardiao']['exposicao_atual']:.2f}")

                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                logger.info('🔒 LockNotifier cancelado')
                return
            except Exception as e:
                logger.error(f'Erro no LockNotifier: {e}')
                await asyncio.sleep(5)

    def _gather_status(self):
        # Guardião - Pega as metas do settings.json
        try:
            lucro_dia = getattr(self.guardiao, 'lucro_dia', 0.0)
            meta = self.guardiao.config['config_geral'].get('meta_diaria_total_usdt', 30.0)
            exposicao_max = self.guardiao.config['config_geral'].get('exposicao_maxima_usdt', 2200.0)
        except Exception:
            lucro_dia = meta = exposicao_max = None

        # Cálculo de Exposição Real (Sincronizado com a lógica de ignorar ADA)
        exposicao_atual = 0.0
        try:
            # Tenta ler do arquivo de composição que o AccountMonitor gera
            path_comp = os.path.join('data', 'account_composition.json')
            if os.path.exists(path_comp):
                with open(path_comp, 'r') as f:
                    comp = json.load(f)
                    # Soma tudo exceto os ativos ignorados pelo guardião
                    for asset, data in comp.items():
                        if asset.startswith("_") or asset in getattr(self.guardiao, 'ativos_ignorar', []):
                            continue
                        exposicao_atual += data.get('usd_val', 0)
        except Exception:
            exposicao_atual = 0.0

        guardiao_status = {
            'lucro_dia': lucro_dia,
            'meta_diaria': meta,
            'exposicao_max': exposicao_max,
            'exposicao_atual': round(exposicao_atual, 2),
            'meta_batida': (lucro_dia >= meta if lucro_dia and meta else False),
            'limite_exposicao': (exposicao_atual + 50.0 > exposicao_max if exposicao_max else False)
        }

        # Estrategista
        trava = getattr(self.estrategista, 'trava_dia_encerrado', False)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'guardiao': guardiao_status,
            'estrategista': {'trava_dia_encerrado': trava}
        }