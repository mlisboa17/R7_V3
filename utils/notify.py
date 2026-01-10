import os
import logging
import requests

logger = logging.getLogger('notify')

def send_telegram_message(text: str) -> bool:
    """Send a message to Telegram if credentials are present in .env.
    Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
    Returns True on success, False otherwise."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        logger.debug('[notify] Telegram not configured.')
        return False
    try:
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        payload = {'chat_id': chat_id, 'text': text}
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info('[notify] Telegram message sent.')
            return True
        else:
            logger.warning('[notify] Telegram failed: %s', resp.text)
            return False
    except Exception as e:
        logger.exception('[notify] Exception sending telegram: %s', e)
        return False
