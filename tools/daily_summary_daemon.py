#!/usr/bin/env python3
import time
import os
import json
import pathlib
from datetime import datetime, timedelta, time as dtime
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from dotenv import load_dotenv

load_dotenv()

from tools.send_telegram_message import send as send_telegram

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT = os.getenv('TELEGRAM_CHAT_ID')
HOUR = int(os.getenv('DAILY_SUMMARY_HOUR', '0'))
MINUTE = int(os.getenv('DAILY_SUMMARY_MINUTE', '5'))
TZ = os.getenv('DAILY_SUMMARY_TZ', 'America/Sao_Paulo')

DATA_DIR = pathlib.Path('data')
LOGS_DIR = pathlib.Path('logs')


def load_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def compose_summary(target_date=None):
    # target_date should be a date string YYYY-MM-DD representing the day to summarize
    daily = load_json(DATA_DIR / 'daily_state.json', {}) or {}
    month_cfg = load_json(DATA_DIR / 'month_config.json', {}) or {}
    trades = load_json(DATA_DIR / 'trades_log.json', []) or []
    acc = load_json(DATA_DIR / 'account_composition.json', {}) or {}

    if not target_date:
        # default to previous day in configured TZ
        if ZoneInfo:
            local_now = datetime.now(ZoneInfo(TZ))
        else:
            local_now = datetime.utcnow()
        target = (local_now.date() - timedelta(days=1)).isoformat()
    else:
        target = target_date

    # filter trades by target date (either 'date' field or timestamp prefix)
    target_trades = [t for t in trades if t.get('date') == target or t.get('timestamp', '').startswith(target)]
    total_day = sum(float(t.get('pnl_usdt', 0) or 0) for t in target_trades)
    open_positions = len([t for t in trades if t.get('status') == 'open']) if isinstance(trades, list) else 0

    msg = []
    msg.append('📊 Resumo Diário R7_V3')
    msg.append(f'Dia (Brasília): {target}')
    msg.append('')
    # try to get daily PnL from daily_state.json if available for that date
    reported_daily = daily.get('lucro_acumulado_usdt') if daily.get('date') == target else None
    if reported_daily is not None:
        msg.append(f'Lucro do dia (USDT) [reportado]: {float(reported_daily):.2f}')
    msg.append(f'Operações do dia: {len(target_trades)} | PnL do dia (USDT) [calc]: {total_day:.2f}')
    msg.append(f'Posições abertas estimadas: {open_positions}')
    msg.append('')
    msg.append('Composição (resumo):')
    if acc:
        top = sorted(((k, v) for k, v in acc.items() if k != '_total_usdt'), key=lambda x: -float(x[1]) if isinstance(x[1], (int, float)) else 0)[:6]
        for k, v in top:
            msg.append(f'- {k}: {v}')
        msg.append(f"Total USDT (estimado): {acc.get('_total_usdt', 0):.2f}")
    else:
        msg.append(' - Nenhuma composição disponível')

    msg.append('')
    msg.append('Últimos trades do dia:')
    for t in target_trades[-5:]:
        msg.append(str(t))

    return '\n'.join(msg)


def send_summary_once(target_date=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print('Missing Telegram config; skipping send')
        return False
    text = compose_summary(target_date)
    try:
        send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT, text)
        print('Daily summary sent')
        return True
    except Exception as e:
        print('Failed to send summary:', e)
        return False


def seconds_until_next(hour=HOUR, minute=MINUTE, tz_name=TZ):
    # compute next occurrence of hour:minute in the given timezone
    if ZoneInfo:
        tz = ZoneInfo(tz_name)
        now_local = datetime.now(tz)
        target_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_local <= now_local:
            target_local = target_local + timedelta(days=1)
        # convert target_local to UTC seconds from now
        target_utc = target_local.astimezone(ZoneInfo('UTC'))
        now_utc = datetime.now(ZoneInfo('UTC'))
        return (target_utc - now_utc).total_seconds()
    else:
        # fallback to UTC-based scheduling
        now = datetime.utcnow()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return (target - now).total_seconds()


def main():
    print(f'Daily summary daemon starting; scheduled at {HOUR:02d}:{MINUTE:02d} (TZ={TZ})')
    # send one immediately on start for verification: send summary for previous day in TZ
    # compute previous day in TZ
    if ZoneInfo:
        local_now = datetime.now(ZoneInfo(TZ))
        prev = (local_now.date() - timedelta(days=1)).isoformat()
    else:
        prev = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
    send_summary_once(prev)
    while True:
        secs = seconds_until_next()
        print(f'Next summary in {int(secs)} seconds')
        time.sleep(secs)
        # send for previous day in TZ (the day that just finished locally)
        if ZoneInfo:
            local_now = datetime.now(ZoneInfo(TZ))
            prev = (local_now.date() - timedelta(days=1)).isoformat()
        else:
            prev = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
        send_summary_once(prev)


if __name__ == '__main__':
    main()
