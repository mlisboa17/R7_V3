import os
import logging
import pandas as pd
from binance.client import Client
import sys
sys.path.append('..')
from utils.volatility import calculate_volatility

logger = logging.getLogger('analista')


class AnalistaBot:
    def __init__(self, config):
        self.config = config
        from tools.binance_wrapper import get_binance_client
        self.client = get_binance_client()

    def calculate_indicators(self, df):
        """Calcula RSI, Médias Móveis e MACD para precisão técnica."""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Médias e MACD
        df['ema5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['macd'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
        df['signal'] = df['macd'].ewm(span=9).mean()
        return df


    async def buscar_oportunidades(self, estrategista=None):
        """Varre as moedas definidas para cada uma das 4 estratégias, sugerindo sizing/stops dinâmicos se estrategista for fornecido."""
        oportunidades = []
        regras_moedas = {
            'scalping_v6': ['SOL', 'ADA', 'DOT', 'XRP'],
            'swing_rwa': ['BTC', 'ETH', 'LINK'],
            'momentum_boost': ['FET', 'RENDER', 'NEAR'],
            'mean_reversion': ['BNB', 'AVAX']
        }

        for nome_est, moedas in regras_moedas.items():
            config_est = self.config['estrategias'].get(nome_est)
            if not config_est or not config_est.get('ativo'): continue

            for symbol in moedas:
                try:
                    pair = f"{symbol}USDT"
                    klines = self.client.get_klines(symbol=pair, interval=config_est['tempo_grafico'], limit=50)
                    df = pd.DataFrame(klines, columns=['ts', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qv', 'nt', 'tb', 'tq', 'i'])
                    df['close'] = df['close'].astype(float)
                    df = self.calculate_indicators(df)
                    last = df.iloc[-1]

                    sinal = None
                    if nome_est == 'scalping_v6' and last['rsi'] < 42 and last['close'] > last['ema5']:
                        sinal = self._formatar_sinal(symbol, nome_est, last['close'], 0.45, 0.55)
                    elif nome_est == 'swing_rwa' and last['close'] > last['ema20'] and last['macd'] > last['signal']:
                        sinal = self._formatar_sinal(symbol, nome_est, last['close'], 2.50, 1.50)

                    # --- MELHORIA: Sizing e stops dinâmicos ---
                    if sinal and estrategista is not None:
                        saldo = self.config.get('banca_referencia_usdt', 2020.0)
                        prices = df['close'].tolist()
                        # Calcula tamanho da posição e stops dinâmicos
                        size = estrategista.calcular_position_size(prices, saldo)
                        stop, alvo = estrategista.definir_stops(last['close'], prices)
                        sinal['position_size'] = size
                        sinal['sl'] = stop
                        sinal['tp'] = alvo
                        sinal.pop('tp_pct', None)
                        sinal.pop('sl_pct', None)
                    if sinal:
                        oportunidades.append(sinal)
                except Exception as e:
                    logger.error(f"Erro analisando {symbol}: {e}")
        return oportunidades

    def _formatar_sinal(self, symbol, est, preco, tp, sl):
        return {
            'symbol': symbol, 'estrategia': est, 'price': preco,
            'entrada_usd': 100.0, 'tp_pct': tp, 'sl_pct': sl
        }