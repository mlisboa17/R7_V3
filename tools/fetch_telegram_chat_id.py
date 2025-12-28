import os
import sys
import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def get_updates(token):
    url = f"https://api.telegram.org/bot{token}/getUpdates?limit=100"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print('NO_TOKEN')
        sys.exit(2)
    try:
        j = get_updates(token)
    except Exception as e:
        print('ERROR', str(e))
        sys.exit(3)
    res = j.get('result', [])
    if not res:
        print('NO_UPDATES')
        sys.exit(4)

    # Find the last update that contains a user message (not from a bot)
    candidate = None
    for u in sorted(res, key=lambda x: x.get('update_id', 0)):
        # possible fields: message, edited_message, callback_query
        msg = u.get('message') or u.get('edited_message') or (u.get('callback_query') and u['callback_query'].get('message'))
        if not msg:
            continue
        frm = msg.get('from') or {}
        if frm.get('is_bot'):
            continue
        # Use private/group/channels too; accept first non-bot message
        candidate = msg
    if not candidate:
        print('NO_USER_MESSAGES')
        sys.exit(5)
    chat = candidate.get('chat', {})
    chat_id = chat.get('id')
    # Try to show human-friendly context: username/name/title
    username = candidate.get('from', {}).get('username')
    fname = candidate.get('from', {}).get('first_name')
    lname = candidate.get('from', {}).get('last_name')
    title = chat.get('title')

    info = {
        'chat_id': chat_id,
        'username': username,
        'first_name': fname,
        'last_name': lname,
        'chat_title': title
    }
    # Print a short single-line JSON-like output (not exposing token)
    print(info['chat_id'], info['username'] or '', info['first_name'] or '', info['chat_title'] or '')
    sys.exit(0)
