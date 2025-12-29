import numpy as np

def calculate_volatility(prices, window=14, method='std'):
    """
    Calcula a volatilidade de uma série de preços.
    - method: 'std' para desvio padrão, 'atr' para Average True Range (ATR)
    - prices: lista ou array de preços de fechamento
    - window: janela de cálculo
    """
    prices = np.asarray(prices)
    if method == 'std':
        return np.std(prices[-window:])
    elif method == 'atr':
        # ATR requer high, low, close
        raise NotImplementedError('ATR requer high, low, close.')
    else:
        raise ValueError('Método de volatilidade não suportado.')
