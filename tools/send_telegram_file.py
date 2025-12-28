import os
import sys
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def send_file(token, chat_id, file_path, caption=None):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': chat_id}
        if caption:
            data['caption'] = caption
        r = requests.post(url, data=data, files=files, timeout=30)
        r.raise_for_status()
        return r.json()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: send_telegram_file.py <file_path> [caption]')
        sys.exit(2)
    file_path = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else None
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print('NO_CREDENTIALS')
        sys.exit(3)
    if not os.path.exists(file_path):
        print('NO_FILE')
        sys.exit(4)
    try:
        res = send_file(token, chat_id, file_path, caption=caption)
        print('SENT', res.get('ok', False))
    except Exception as e:
        print('ERROR', e)
        sys.exit(1)
