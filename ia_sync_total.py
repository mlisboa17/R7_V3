import os
import sqlite3
import logging
from binance.client import Client
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('IA_SYNC_TOTAL')

def sincronizar_e_adotar_tudo():
    load_dotenv()
    client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
    conn = sqlite3.connect('memoria_bot.db')
    cursor = conn.cursor()

    logger.info("🚀 IA: Iniciando varredura total de ativos para gestão Sniper...")

    # 1. Obter saldos da conta
    account = client.get_account()
    # Filtra apenas moedas que você realmente possui (valor > 0)
    ativos_reais = [b for b in account['balances'] if float(b['free']) + float(b['locked']) > 0.001]

    for item in ativos_reais:
        asset = item['asset']
        if asset in ['USDT', 'BNB', 'FDUSD']: continue  # Moedas de taxa e reserva

        symbol = f"{asset}USDT"
        
        try:
            # Busca as últimas ordens para calcular o preço médio de compra
            trades = client.get_my_trades(symbol=symbol, limit=10)
            if not trades: continue

            # Lógica para achar o preço médio real das compras
            compras = [float(t['price']) for t in trades if t['isBuyer']]
            if not compras: continue
            
            preco_medio = sum(compras) / len(compras)

            # 2. Registra na tabela de TRADES para o Estrategista assumir
            cursor.execute("""
                INSERT OR REPLACE INTO trades (symbol, entry_price, timestamp)
                VALUES (?, ?, DATETIME('now'))
            """, (asset, preco_medio))
            
            logger.info(f"✅ IA Assumiu: {asset} | Preço Médio: ${preco_medio:.4f}")

        except Exception as e:
            logger.debug(f"Pular {asset}: {e}")

    conn.commit()
    conn.close()
    logger.info("🎯 IA AGORA CONTROLA 100% DA CARTEIRA. Pode iniciar o main.py.")

if __name__ == "__main__":
    sincronizar_e_adotar_tudo()