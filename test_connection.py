import os
import asyncio
from dotenv import load_dotenv
from tools.binance_wrapper import get_binance_client
from telegram import Bot

async def testar_conexao():
    load_dotenv()
    print("--- INICIANDO TESTE DE CONEXÃO R7_V3 ---")
    try:
        # Conexão Binance (usando wrapper com retries)
        client = get_binance_client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
        # Puxa cotação e saldo
        ticker = client.get_symbol_ticker(symbol="USDTBRL")
        preco_usdt = float(ticker['price'])
        
        conta = client.get_account()
        for asset in conta['balances']:
            free = float(asset['free']) if asset.get('free') else 0
            if free > 0:
                print(f"Detectado: {asset['asset']} - Saldo: {free}")
                # Simplificação para o teste: foca no saldo total estimado
        
        print(f"✅ Binance conectada! Cotação USDT: R$ {preco_usdt}")

        # Conexão Telegram
        bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        msg = f"🚀 R7_V3 Online!\nConexão Binance: OK\nCotação USDT: R$ {preco_usdt}\nPronto para iniciar monitoramento."
        await bot.send_message(chat_id=chat_id, text=msg)
        print("✅ Mensagem de teste enviada ao Telegram!")

    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")

if __name__ == '__main__':
    asyncio.run(testar_conexao())