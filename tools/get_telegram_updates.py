import os
from dotenv import load_dotenv
import requests
import json
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print('No token in env')
    raise SystemExit(2)
url = f'https://api.telegram.org/bot{TOKEN}/getUpdates'
resp = requests.get(url, timeout=10)
print('HTTP', resp.status_code)
try:
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception:
    print(resp.text)
