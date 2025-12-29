import numpy as np
import pandas as pd

def calcular_correlacao_ativos(historico_precos, ativos=None, window=30):
    """
    Calcula a matriz de correlação entre ativos usando preços de fechamento.
    historico_precos: dict {symbol: [precos]}
    ativos: lista de ativos a considerar (opcional)
    window: janela de cálculo
    """
    if ativos is None:
        ativos = list(historico_precos.keys())
    data = {a: historico_precos[a][-window:] for a in ativos if len(historico_precos[a]) >= window}
    df = pd.DataFrame(data)
    return df.corr()

def ativos_correlacionados(corr_matrix, threshold=0.85):
    """
    Retorna pares de ativos com correlação acima do threshold.
    """
    correlated = set()
    for a in corr_matrix.columns:
        for b in corr_matrix.columns:
            if a != b and corr_matrix.loc[a, b] >= threshold:
                correlated.add(tuple(sorted((a, b))))
    return list(correlated)
