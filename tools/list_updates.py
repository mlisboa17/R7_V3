#!/usr/bin/env python3
import asyncio
from dotenv import load_dotenv
import os
load_dotenv()
from telegram import Bot

async def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print('TELEGRAM_BOT_TOKEN not set')
        return
    bot = Bot(token)
    try:
        updates = await bot.get_updates(timeout=3)
        if not updates:
            print('No updates available (bot may not have received messages from users)')
            return
        for u in updates:
            print('Update:', u)
            if u.message:
                print('From chat id:', u.message.chat.id, 'user:', u.message.from_user)
    except Exception as e:
        print('get_updates error:', type(e).__name__, e)
    finally:
        await bot.close()

if __name__ == '__main__':
    asyncio.run(main())
