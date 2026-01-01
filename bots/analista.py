import logging
import os
import asyncio
import pandas as pd  # Resolvendo definitivamente o erro de 'NameError: pd'
import pandas_ta as ta

logger = logging.getLogger('analista')

class AnalistaBot:
    def __init__(self, config, client=None, ia=None):
        """
        Inicializa o analista com acesso à API e ao motor de IA treinado.
        """
        self.config = config
        self.client = client
        self.ia = ia  # Objeto da IA com os 13.760 padrões carregados
        self.historico_df = {}
        
        # Configurações de alvos (Style Mapping)
        self.mapeamento_estilos = {
            'scalping_v6': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
            'momentum_boost': ['SOLUSDT', 'AVAXUSDT', 'NEARUSDT', 'FETUSDT', 'RNDRUSDT'],
            'swing_rwa': ['ADAUSDT', 'XRPUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT', 'LTCUSDT', 'ATOMUSDT']
        }

    def calculate_indicators(self, df):
        """
        Calcula indicadores técnicos necessários para validar o sinal da IA.
        """
        try:
            if df is None or len(df) < 25:
                return df
            
            # RSI para identificar exaustão
            df['rsi'] = ta.rsi(df['close'], length=14)
            
            # Médias Móveis para conferir tendência
            df['ema5'] = ta.ema(df['close'], length=5)
            df['ema20'] = ta.ema(df['close'], length=20)
            
            # Bandas de Bollinger para volatilidade de curto prazo
            bb = ta.bbands(df['close'], length=20, std=2)
            if bb is not None:
                df['bb_lower'] = bb['BBL_20_2.0']
                df['bb_upper'] = bb['BBU_20_2.0']

            return df
        except Exception as e:
            logger.error(f"Erro no cálculo de indicadores técnicos: {e}")
            return df

    async def analisar_tick(self, symbol, preco_atual):
        """
        MÉTODO CIRÚRGICO: Invocado pelo SniperMonitor em tempo real (Tick-by-Tick).
        Cruza a predição da IA com os filtros de segurança.
        """
        try:
            # 1. Determina a Estratégia Baseada no Ativo
            est_nome = 'swing_rwa' # Default
            for style, symbols in self.mapeamento_estilos.items():
                if symbol in symbols:
                    est_nome = style
                    break

            # Define força de entrada conforme o estilo
            forca_base = 1.5 if est_nome == 'scalping_v6' else 1.2 if est_nome == 'momentum_boost' else 1.0

            # 2. CONSULTA AO MOTOR DE IA (Predictive Analysis)
            decisao = "AGUARDAR"
            
            if self.ia:
                # O método predict da sua IA avalia o tick contra os 13k padrões
                predicao = self.ia.predict(symbol, preco_atual)
                
                # Filtro de Confiança Crítico: Mínimo 85% de acurácia técnica
                if predicao.get('sinal') == 'BUY' and predicao.get('confianca', 0) >= 0.85:
                    # Opcional: Adicionar conferência técnica extra aqui (ex: rsi < 70)
                    decisao = "COMPRAR"
                    logger.info(f"🎯 SINAL SNIPER CONFIRMADO: {symbol} | IA Confiança: {predicao['confianca']:.2%}")

            return {
                "decisao": decisao,
                "estrategia": est_nome,
                "forca": forca_base
            }

        except Exception as e:
            logger.error(f"Falha na análise técnica em tempo real para {symbol}: {e}")
            return {"decisao": "AGUARDAR", "estrategia": "none", "forca": 0}

    async def atualizar_historico_cache(self, symbol):
        """
        Mantém os últimos candles em memória para que os indicadores não sejam zerados.
        """
        # Implementação futura se desejar cálculos de indicadores mais complexos no Sniper
        pass