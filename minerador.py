import os
import pandas as pd
import pandas_ta as ta
from binance.client import Client
from dotenv import load_dotenv
from tqdm import tqdm

def gerar_historico_treino():
    load_dotenv()
    client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
    
    # 🎯 Seleção Estratégica: Misturando BLUE, FUN e IA para a IA aprender as diferenças
    moedas = [
        ('BTC', 'LARGE_CAP'), ('ETH', 'LARGE_CAP'), 
        ('SOL', 'DEFI'), ('LINK', 'DEFI'),
        ('FET', 'AI'), ('NEAR', 'AI'),
        ('PEPE', 'MEME'), ('DOGE', 'MEME')
    ]
    
    timeframes = ['1h', '4h']
    dados_finais = []

    print(f"🚀 Minerando 60 dias de histórico para alimentar o Cérebro IA...")

    for symbol, categoria in tqdm(moedas):
        for tf in timeframes:
            try:
                # Busca 60 dias para ter volume de dados (aprox 1440 velas por par)
                klines = client.get_historical_klines(f"{symbol}USDT", tf, "60 days ago UTC")
                df = pd.DataFrame(klines, columns=['ts','open','high','low','close','vol','ct','qv','nt','tb','tq','i'])
                
                for col in ['open', 'high', 'low', 'close', 'vol']:
                    df[col] = df[col].astype(float)

                # --- INDICADORES ---
                df['rsi'] = ta.rsi(df['close'], length=14)
                df['ema20'] = ta.ema(df['close'], length=20)
                
                # TARGET: Sucesso se o preço subir 1.5% nas próximas 12 velas
                df['sucesso'] = (df['close'].shift(-12) > df['close'] * 1.015).astype(int)

                # Limpeza de NaNs gerados pelos indicadores
                df = df.dropna(subset=['rsi', 'ema20', 'sucesso'])
                
                for _, row in df.iterrows():
                    dados_finais.append({
                        'close': row['close'],
                        'rsi': row['rsi'],
                        'ema20': row['ema20'],
                        'categoria': categoria, # 👈 VITAL: Para a IA diferenciar os setores
                        'sucesso': row['sucesso']
                    })
            except Exception as e:
                print(f"Erro em {symbol}: {e}")
                continue

    os.makedirs('data', exist_ok=True)
    pd.DataFrame(dados_finais).to_csv('data/historico_ia.csv', index=False)
    print(f"✅ Dataset Elite criado com {len(dados_finais)} linhas em 'data/historico_ia.csv'.")

if __name__ == "__main__":
    gerar_historico_treino()