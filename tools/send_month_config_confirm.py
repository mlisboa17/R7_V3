import os
from tools.send_telegram_file import send_file
from dotenv import load_dotenv
load_dotenv()
TOK=os.getenv('TELEGRAM_BOT_TOKEN')
CHAT=os.getenv('TELEGRAM_CHAT_ID')
if not TOK or not CHAT:
    print('missing creds')
else:
    try:
        r = send_file(TOK, CHAT, 'data/month_config.json', caption='Projeto R7 - month_config (start balance & target)')
        print('SENT', r.get('ok', False))
        import json
        print(json.dumps(r, indent=2, ensure_ascii=False))
    except Exception as e:
        print('ERROR', e)
