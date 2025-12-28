import os
import json
from tools.send_telegram_message import send
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT = os.getenv('TELEGRAM_CHAT_ID')
if not TOKEN or not CHAT:
    print('MISSING_TOKEN_OR_CHAT')
else:
    text = 'Projeto R7 calibrado — saldo inicial $9,660.84 (USD), meta mensal 20% = $1,932.17, objetivo final $11,593.01. Projeto R7 em modo automático.'
    try:
        r = send(TOKEN, CHAT, text)
        print('SENT', r.get('ok', False))
        print(json.dumps(r, indent=2, ensure_ascii=False))
    except Exception as e:
        print('ERROR', e)
