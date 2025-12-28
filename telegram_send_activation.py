import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT = os.getenv('TELEGRAM_CHAT_ID')

async def send_activation():
    bot = Bot(token=TOKEN)
    msg = '⚠️ MODO REAL ATIVADO! R7_V3 operando com Banca Inicial: $1743.12 USDT. Saldo operacional: $1743.12 USDT. Meta do dia: $17.43 USDT. Digite /status para o relatório.'
    try:
        await bot.send_message(chat_id=CHAT, text=msg)
        print('Mensagem enviada com sucesso')
    except Exception as e:
        print('Falha ao enviar mensagem:', e)

if __name__ == '__main__':
    asyncio.run(send_activation())