#!/usr/bin/env python3
import asyncio
from dotenv import load_dotenv
import os
load_dotenv()
from telegram import Bot

MSG = '💰 Caixa gerado! 150.07 USDT disponíveis para trade. Saindo do modo leitura e iniciando operações reais.'

async def main():
    token=os.getenv('TELEGRAM_BOT_TOKEN')
    chat=os.getenv('TELEGRAM_CHAT_ID')
    b=Bot(token)
    try:
        c = await b.get_chat(chat)
        print('get_chat OK:', getattr(c,'id',None))
    except Exception as e:
        print('get_chat error:', type(e).__name__, e)
    try:
        await b.send_message(chat_id=chat, text=MSG)
        print('sent')
    except Exception as e:
        print('send error:', type(e).__name__, e)
    await b.close()

if __name__ == '__main__':
    asyncio.run(main())
