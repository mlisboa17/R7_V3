import os
import pandas as pd
import pandas_ta as ta
from binance.client import Client
from dotenv import load_dotenv
from tqdm import tqdm
import time

def gerar_historico_treino():
    load_dotenv()
    client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
    
    moedas = ['BTC', 'ETH', 'SOL', 'ADA', 'XRP', 'DOT', 'AVAX', 'FET', 'NEAR', 'LINK']
    timeframes = ['1h', '4h'] # Alinhado com a sua IAEngine
    dados_finais = []

    print(f"🚀 Minerando dados para IA Robusta ($1827)...")

    for symbol in tqdm(moedas):
        for tf in timeframes:
            try:
                klines = client.get_historical_klines(f"{symbol}USDT", tf, "60 days ago UTC")
                df = pd.DataFrame(klines, columns=['ts','open','high','low','close','vol','ct','qv','nt','tb','tq','i'])
                
                for col in ['open', 'high', 'low', 'close', 'vol']:
                    df[col] = df[col].astype(float)

                # --- INDICADORES REQUERIDOS PELA SUA IAENGINE ---
                df.ta.rsi(length=14, append=True)
                df.ta.ema(length=20, append=True)
                df.ta.ema(length=200, append=True)
                df.ta.bbands(length=20, std=2, append=True)
                
                df['price_above_ema'] = (df['close'] > df['EMA_20']).astype(int)
                df['trend_4h'] = df['close'].pct_change(periods=4) * 100
                df['price_change_percent'] = df['close'].pct_change() * 100
                df['avg_price'] = df['close'].rolling(window=5).mean()
                
                # TARGET: Sucesso se o preço subir 1.5% em 12 horas
                df['sucesso'] = (df['close'].shift(-12) > df['close'] * 1.015).astype(int)

                # Remover linhas iniciais (para EMA_200) e finais (para target)
                df = df.iloc[200:-12]
                
                for _, row in df.iterrows():
                    dados_finais.append({
                        'close': row['close'], 'rsi': row['RSI_14'], 'volume': row['vol'],
                        'ema20': row['EMA_20'], 'ema200': row['EMA_200'], 
                        'bb_upper': row['BBU_20_2.0_2.0'], 'bb_lower': row['BBL_20_2.0_2.0'],
                        'price_above_ema': row['price_above_ema'], 'trend_4h': row['trend_4h'],
                        'buy_pressure': 0.5, 'volume_24h': row['vol'] * 24, # Estimativa
                        'fear_greed': 50, 'news_sentiment': 0, 'whale_risk': 0,
                        'price_change_percent': row['price_change_percent'], 
                        'avg_price': row['avg_price'], 'sucesso': row['sucesso']
                    })
            except Exception as e:
                continue

    os.makedirs('data', exist_ok=True)
    pd.DataFrame(dados_finais).to_csv('data/historico_ia.csv', index=False)
    print(f"✅ Dataset criado com {len(dados_finais)} linhas.")

if __name__ == "__main__":
    gerar_historico_treino()