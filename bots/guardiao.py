import logging
import json
import os

logger = logging.getLogger('guardiao')

class GuardiaoBot:
    def __init__(self, config, executor=None):
        self.config = config
        self.executor = executor
        # Moedas ignoradas para o cálculo de risco (Holding/Earn)
        self.ativos_ignorar = ["ADA", "ICP", "GIGGLE"] 

    async def validar_operacao(self, simbolo, valor_entrada):
        """
        Valida a entrada ignorando moedas de holding e respeitando o novo limite.
        """
        try:
            path_composicao = 'data/account_composition.json'
            
            if not os.path.exists(path_composicao):
                logger.warning("⚠️ Aguardando dados do AccountMonitor para validar...")
                return "AGUARDANDO_DADOS"

            with open(path_composicao, 'r') as f:
                composicao = json.load(f)

            # 1. CÁLCULO DA EXPOSIÇÃO OPERACIONAL
            # Filtra moedas de holding para não sufocar o limite de trade
            exposicao_operacional = 0.0
            for asset, data in composicao.items():
                if asset.startswith("_") or asset in self.ativos_ignorar:
                    continue
                exposicao_operacional += data.get('usd_val', 0)

            # Busca limite do settings.json (Recomendado: 1500.00 ou 2200.00)
            limite_max = self.config['config_geral']['exposicao_maxima_usdt']
            
            # 2. TRAVA DE EXPOSIÇÃO CRÍTICA
            if (exposicao_operacional + valor_entrada) > limite_max:
                logger.warning(f"🚫 BLOQUEIO: Exposição Sniper (${exposicao_operacional:.2f}) atingiria limite de ${limite_max}")
                return "LIMITE_EXPOSICAO"

            # 3. VERIFICAÇÃO DE DUPLICIDADE
            # Evita comprar a mesma moeda duas vezes simultaneamente
            if self.executor and simbolo in self.executor.active_trades:
                logger.info(f"ℹ️ {simbolo} já está em operação ativa. Pulando.")
                return "MOEDA_JA_ATIVA"

            # 4. VERIFICAÇÃO DE CICLO ENCERRADO
            if self.executor and hasattr(self.executor, 'estrategista'):
                if self.executor.estrategista.trava_dia_encerrado:
                    logger.info("🚫 Sniper pausado: Meta diária já processada.")
                    return "META_BATIDA"

            logger.info(f"✅ Guardião: Exposição Sniper em ${exposicao_operacional:.2f}. {simbolo} LIBERADO.")
            return "OK"

        except Exception as e:
            logger.error(f"🚨 Erro na validação do Guardião: {e}")
            return "ERRO_SISTEMA"