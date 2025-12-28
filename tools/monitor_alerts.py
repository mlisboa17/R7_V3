#!/usr/bin/env python3
import os
import time
import pathlib
import asyncio
from dotenv import load_dotenv

load_dotenv()

LOG_DIR = pathlib.Path('logs')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT = os.getenv('TELEGRAM_CHAT_ID')
COOLDOWN_SEC = int(os.getenv('MONITOR_ALERT_COOLDOWN', '300'))  # 5 minutes default


def find_latest_log():
    if not LOG_DIR.exists():
        return None
    files = [f for f in LOG_DIR.iterdir() if f.is_file()]
    if not files:
        return None
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files[0]


async def send_telegram(text):
    try:
        from telegram import Bot
        b = Bot(TELEGRAM_TOKEN)
        await b.send_message(chat_id=TELEGRAM_CHAT, text=text)
        await b.close()
    except Exception as e:
        print('Telegram send failed:', e)


def tail_and_alert(path):
    print('Monitoring', path)
    last_sent = {}
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                line = line.strip()
                if not line:
                    continue
                # basic detection
                up = line.upper()
                is_crit = 'CRITICAL' in up or 'ERROR' in up or 'EXCEPTION' in up or 'FAIL' in up
                if is_crit:
                    key = line
                    now = time.time()
                    last = last_sent.get(key, 0)
                    if now - last > COOLDOWN_SEC:
                        last_sent[key] = now
                        text = f"[ALERTA] {time.strftime('%Y-%m-%d %H:%M:%S')}\n{line}"
                        print('Sending alert:', text)
                        asyncio.run(send_telegram(text))
    except KeyboardInterrupt:
        print('monitor_alerts stopped by user')
    except Exception as e:
        print('monitor_alerts error:', e)


def main():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print('Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in env; exiting')
        return
    latest = find_latest_log()
    if not latest:
        print('No log files found in logs/; exiting')
        return
    tail_and_alert(latest)


if __name__ == '__main__':
    main()
