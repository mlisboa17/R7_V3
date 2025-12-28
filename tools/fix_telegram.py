#!/usr/bin/env python3
"""Script robusto para validar Telegram e Binance e enviar mensagem de ativação.
Uso: python tools/fix_telegram.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')

MSG = '🚀 R7_V3: Comunicação Estabelecida. Modo Real Pronto!'

async def check_telegram_and_send():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print('ERRO: TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados no .env')
        return False
    try:
        from telegram import Bot
        bot = Bot(TELEGRAM_TOKEN)
        # get_chat verifies the chat existence and permissions
        try:
            chat = await bot.get_chat(TELEGRAM_CHAT_ID)
            print('Telegram get_chat OK:', getattr(chat, 'title', getattr(chat, 'first_name', chat.id)))
        except Exception as e:
            print('Telegram get_chat falhou:', type(e).__name__, e)
            await bot.close()
            return False
        # Try to send the activation message with retries
        for attempt in range(1, 4):
            try:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=MSG)
                print('Mensagem de ativação enviada com sucesso!')
                await bot.close()
                return True
            except Exception as e:
                print(f'Tentativa {attempt} de envio falhou:', type(e).__name__, e)
                await asyncio.sleep(1 * attempt)
        await bot.close()
        return False
    except Exception as e:
        print('Erro ao inicializar Telegram Bot:', type(e).__name__, e)
        return False

def check_binance():
    if not BINANCE_API_KEY or not BINANCE_SECRET_KEY:
        print('Aviso: Chaves Binance não encontradas; pulando teste de Binance')
        return None
    try:
        from binance.client import Client
        from tools.binance_wrapper import get_binance_client
        client = get_binance_client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
        # Quick connectivity check
        try:
            ticker = client.get_symbol_ticker(symbol='USDTBRL')
            print('Binance OK: USDTBRL=', ticker.get('price'))
            return True
        except Exception as e:
            print('Binance API falhou (get_symbol_ticker):', type(e).__name__, e)
            return False
    except Exception as e:
        print('Erro ao inicializar Binance Client:', type(e).__name__, e)
        return False

async def main():
    print('--- Iniciando verificação de comunicação (Telegram + Binance) ---')
    bin_ok = check_binance()
    tg_ok = await check_telegram_and_send()
    print('\nResumo: Telegram OK=' + str(tg_ok) + ' | Binance OK=' + str(bin_ok))
    return 0 if tg_ok else 2

if __name__ == '__main__':
    rc = asyncio.run(main())
    sys.exit(rc)
