"""
🕯️ DETECTOR DE PADRÕES DE CANDLESTICK
Identifica padrões de reversão para evitar stops loss prematuros
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger('candlestick_patterns')

class CandlestickPatterns:
    """
    Detector de padrões de candlestick para identificar reversões
    """
    
    @staticmethod
    def is_hammer(candle):
        """
        Identifica Martelo (Hammer)
        - Pavio inferior longo (2x o corpo)
        - Corpo pequeno no topo
        - Indica reversão de alta após queda
        """
        try:
            body = abs(candle['close'] - candle['open'])
            lower_wick = min(candle['open'], candle['close']) - candle['low']
            upper_wick = candle['high'] - max(candle['open'], candle['close'])
            
            # Pavio inferior > 2x corpo E pavio superior pequeno
            is_pattern = (lower_wick > 2 * body) and (upper_wick < body * 0.3) and body > 0
            return is_pattern
        except:
            return False
    
    @staticmethod
    def is_inverted_hammer(candle):
        """
        Identifica Martelo Invertido
        - Pavio superior longo
        - Indica possível reversão de alta
        """
        try:
            body = abs(candle['close'] - candle['open'])
            lower_wick = min(candle['open'], candle['close']) - candle['low']
            upper_wick = candle['high'] - max(candle['open'], candle['close'])
            
            is_pattern = (upper_wick > 2 * body) and (lower_wick < body * 0.3) and body > 0
            return is_pattern
        except:
            return False
    
    @staticmethod
    def is_pin_bar(candle):
        """
        Identifica Pin Bar (rejeição de preço)
        - Pavio longo (superior ou inferior)
        - Corpo pequeno
        """
        try:
            body = abs(candle['close'] - candle['open'])
            lower_wick = min(candle['open'], candle['close']) - candle['low']
            upper_wick = candle['high'] - max(candle['open'], candle['close'])
            
            total_range = candle['high'] - candle['low']
            
            if total_range == 0:
                return False
            
            # Pavio > 66% do range total
            long_wick = max(lower_wick, upper_wick)
            is_pattern = (long_wick > total_range * 0.66) and (body < total_range * 0.25)
            return is_pattern
        except:
            return False
    
    @staticmethod
    def is_bullish_engulfing(prev_candle, curr_candle):
        """
        Identifica Engolfo de Alta
        - Vela anterior vermelha (queda)
        - Vela atual verde (alta) e maior
        """
        try:
            prev_red = prev_candle['close'] < prev_candle['open']
            curr_green = curr_candle['close'] > curr_candle['open']
            
            if not (prev_red and curr_green):
                return False
            
            # Vela atual engole a anterior
            engulfs = (curr_candle['open'] < prev_candle['close'] and 
                       curr_candle['close'] > prev_candle['open'])
            
            return engulfs
        except:
            return False
    
    @staticmethod
    def is_doji(candle):
        """
        Identifica Doji (indecisão)
        - Corpo muito pequeno
        - Open ≈ Close
        """
        try:
            body = abs(candle['close'] - candle['open'])
            total_range = candle['high'] - candle['low']
            
            if total_range == 0:
                return False
            
            # Corpo < 10% do range total
            is_pattern = body < total_range * 0.1
            return is_pattern
        except:
            return False
    
    @staticmethod
    def detect_all_patterns(df):
        """
        Detecta todos os padrões em um DataFrame de velas
        Retorna features binárias para treino da IA
        
        Args:
            df: DataFrame com colunas ['open', 'high', 'low', 'close']
        
        Returns:
            DataFrame com features de padrões detectados
        """
        patterns = {
            'hammer': [],
            'inverted_hammer': [],
            'pin_bar': [],
            'bullish_engulfing': [],
            'doji': []
        }
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            patterns['hammer'].append(1 if CandlestickPatterns.is_hammer(row) else 0)
            patterns['inverted_hammer'].append(1 if CandlestickPatterns.is_inverted_hammer(row) else 0)
            patterns['pin_bar'].append(1 if CandlestickPatterns.is_pin_bar(row) else 0)
            patterns['doji'].append(1 if CandlestickPatterns.is_doji(row) else 0)
            
            # Engulfing precisa da vela anterior
            if i > 0:
                prev = df.iloc[i-1]
                patterns['bullish_engulfing'].append(
                    1 if CandlestickPatterns.is_bullish_engulfing(prev, row) else 0
                )
            else:
                patterns['bullish_engulfing'].append(0)
        
        return pd.DataFrame(patterns)
    
    @staticmethod
    def has_reversal_signal(df, rsi=None):
        """
        Verifica se há sinal de reversão (martelo/pin bar em suporte)
        
        Args:
            df: DataFrame com dados OHLC
            rsi: Valor do RSI (se disponível)
        
        Returns:
            bool: True se detectou padrão de reversão
        """
        if len(df) < 2:
            return False
        
        try:
            last_candle = df.iloc[-1]
            
            # Martelo ou Pin Bar
            is_hammer = CandlestickPatterns.is_hammer(last_candle)
            is_pin = CandlestickPatterns.is_pin_bar(last_candle)
            
            # Se tem RSI, verificar se está em oversold
            if rsi is not None:
                in_oversold = rsi < 35
                return (is_hammer or is_pin) and in_oversold
            
            # Sem RSI, apenas verifica o padrão
            return is_hammer or is_pin
        except Exception as e:
            logger.error(f"Erro ao verificar sinal de reversão: {e}")
            return False
