import asyncio
from dotenv import load_dotenv
import os
load_dotenv()
from telegram import Bot

async def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    print('Token present:', bool(token))
    print('Chat id:', chat_id)
    b = Bot(token)
    try:
        c = await b.get_chat(chat_id)
        print('get_chat OK:', c)
    except Exception as e:
        print('get_chat error:', type(e).__name__, e)
    finally:
        await b.close()

if __name__ == '__main__':
    asyncio.run(main())
