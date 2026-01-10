import os
import pandas as pd
import pandas_ta as ta
from binance.client import Client
from dotenv import load_dotenv
from tqdm import tqdm
import time

# --- SEU DICIONÁRIO DE MAPEAMENTO ---
MANUAL_MAPPING = {
    'HYPE': 'HYPEUSDT', 'TON': 'TONUSDT', 'ONDO': 'ONDOUSDT', 'ENA': 'ENAUSDT',
    'VIRTUAL': 'VIRTUALUSDT', 'IO': 'IOUSDT', 'SUI': 'SUIUSDT', 'APT': 'APTUSDT',
    'TIA': 'TIAUSDT', 'TAO': 'TAOUSDT', 'OM': 'OMUSDT', 'PENDLE': 'PENDLEUSDT',
    'MATIC': 'POLUSDT', 'RNDR': 'RENDERUSDT', 'AGIX': 'FETUSDT', 'OCEAN': 'FETUSDT',
    'BEAM': 'BEAMXUSDT', 'MC': 'BEAMXUSDT', 'WIF': 'WIFUSDT'
}

def gerar_historico_treino_avancado():
    load_dotenv()
    client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
    
    # Coletando todos os símbolos ativos na Binance para não deixar nada de fora
    exchange_info = client.get_exchange_info()
    ativos_binance = [s['symbol'] for s in exchange_info['symbols'] 
                      if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
    
    # Unindo suas moedas preferidas com o resto do mercado
    moedas_para_treino = list(set(list(MANUAL_MAPPING.values()) + ativos_binance))
    
    timeframes = ['1h', '4h']
    dados_finais = []

    print(f"🚀 Iniciando Mineração Inteligente em {len(moedas_para_treino)} pares...")

    for symbol in tqdm(moedas_para_treino):
        for tf in timeframes:
            try:
                # 60 dias é o ideal para capturar ciclos de queda e recuperação
                klines = client.get_historical_klines(symbol, tf, "60 days ago UTC")
                if not klines: continue
                
                df = pd.DataFrame(klines, columns=['ts','open','high','low','close','vol','ct','qv','nt','tb','tq','i'])
                
                for col in ['open', 'high', 'low', 'close', 'vol']:
                    df[col] = df[col].astype(float)

                # --- INDICADORES DE "SOBREVIVÊNCIA" (Essenciais para o Stop Loss) ---
                # 1. RSI: Sobrecompra/Sobrevenda
                df['rsi'] = ta.rsi(df['close'], length=14)
                
                # 2. EMA20: Tendência de curto prazo
                df['ema20'] = ta.ema(df['close'], length=20)
                
                # 3. ATR: Volatilidade (Diz se a queda é normal ou pânico)
                df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
                
                # 4. Volume Relativo: Identifica "Velas de Exaustão"
                df['vol_ema'] = ta.ema(df['vol'], length=20)
                df['rel_vol'] = df['vol'] / df['vol_ema'] 

                # --- LOGICA DE TARGET (O QUE QUEREMOS QUE A IA APRENDA) ---
                # Sucesso = Subiu 1.5% nas próximas 12 velas SEM cair mais de 2% antes (Drawdown)
                # Isso ensina a IA a ignorar "bull traps"
                future_max = df['high'].shift(-12).rolling(window=12).max()
                future_min = df['low'].shift(-12).rolling(window=12).min()
                
                df['sucesso'] = ((df['close'].shift(-12) > df['close'] * 1.015) & 
                                 (future_min > df['close'] * 0.98)).astype(int)

                df = df.dropna()

                for _, row in df.iterrows():
                    dados_finais.append({
                        'symbol': symbol,
                        'close': row['close'],
                        'rsi': row['rsi'],
                        'ema20': row['ema20'],
                        'atr_pct': (row['atr'] / row['close']) * 100, # Volatilidade em %
                        'rel_vol': row['rel_vol'], # Volume acima da média?
                        'sucesso': row['sucesso']
                    })
                
                # Evitar banimento por excesso de requisições (Rate Limit)
                time.sleep(0.1)

            except Exception as e:
                continue

    # Salvando Dataset
    os.makedirs('data', exist_ok=True)
    pd.DataFrame(dados_finais).to_csv('data/historico_ia_completo.csv', index=False)
    print(f"\n✅ Dataset Elite gerado: {len(dados_finais)} linhas.")

if __name__ == "__main__":
    gerar_historico_treino_avancado()