import os
from dotenv import load_dotenv
load_dotenv()
from tools.send_telegram_message import send

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
print('token present:', bool(token))
print('chat_id present:', bool(chat_id))
try:
    r = send(token, chat_id, 'Teste automático de envio via tools/test_send_telegram.py')
    print('SENT OK:', r)
except Exception as e:
    print('SEND FAIL:', e)
    raise
