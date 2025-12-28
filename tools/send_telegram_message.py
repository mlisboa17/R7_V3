import os
import sys
import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def send(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
    r.raise_for_status()
    return r.json()

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print('MISSING')
        sys.exit(2)
    text = sys.argv[1] if len(sys.argv) > 1 else 'Teste: chat id configurado com sucesso.'
    try:
        res = send(token, chat_id, text)
        print('SENT', res.get('ok', False))
    except Exception as e:
        print('ERROR', e)
        sys.exit(3)
