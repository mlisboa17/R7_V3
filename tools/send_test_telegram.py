import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

print('Using token present:', bool(TOKEN))
print('Using chat_id present:', bool(CHAT_ID))
if not TOKEN or not CHAT_ID:
    print('Missing token or chat_id; aborting')
    raise SystemExit(2)

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {'chat_id': CHAT_ID, 'text': 'Teste automático de envio via send_test_telegram.py'}
try:
    r = requests.post(url, json=payload, timeout=10)
    print('HTTP', r.status_code)
    try:
        print('Response:', json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        print('Response text:', r.text)
except Exception as e:
    print('Request failed:', repr(e))
    raise
