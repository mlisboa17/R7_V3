import os
import sqlite3
import logging
from binance.client import Client
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Sincronizador_R7')

def sincronizar_posicoes_reais():
    load_dotenv()
    client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
    conn = sqlite3.connect('memoria_bot.db')
    cursor = conn.cursor()

    logger.info("🔍 Analisando carteira para adoção de ativos...")

    # 1. Busca todos os saldos da conta
    account = client.get_account()
    saldos = [d for d in account['balances'] if float(d['free']) > 0 or float(d['locked']) > 0]

    for saldo in saldos:
        asset = saldo['asset']
        if asset in ['USDT', 'BNB', 'FDUSD']: continue # Ignora moedas de taxa/estáveis

        qty = float(saldo['free']) + float(saldo['locked'])
        symbol = f"{asset}USDT"

        try:
            # 2. Busca o histórico de ordens para achar o preço médio
            trades = client.get_my_trades(symbol=symbol, limit=5)
            if not trades: continue

            # Calcula o preço médio das últimas compras
            soma_preco = sum(float(t['price']) for t in trades if t['isBuyer'])
            contagem = sum(1 for t in trades if t['isBuyer'])
            
            if contagem == 0: continue
            preco_medio = soma_preco / contagem

            # 3. Injeta na memória da IA como uma posição aberta
            cursor.execute("""
                INSERT OR IGNORE INTO trades (symbol, entry_price, timestamp)
                VALUES (?, ?, DATETIME('now'))
            """, (asset, preco_medio))
            
            logger.info(f"✅ Ativo {asset} adotado! Preço Médio: ${preco_medio:.4f} | Qtd: {qty}")

        except Exception as e:
            logger.error(f"⚠️ Não foi possível sincronizar {asset}: {e}")

    conn.commit()
    conn.close()
    logger.info("🚀 Sincronização concluída. A IA agora monitora toda a sua banca.")

if __name__ == "__main__":
    sincronizar_posicoes_reais()