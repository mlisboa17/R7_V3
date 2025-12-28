"""Keep-alive watchdog for R7_V3
- Checks every 5 minutes whether the bot is running (checks for pythonw/python processes containing main.py or start_real.py)
- If not running, launches `start_real.py` using pythonw
- Prevents Windows sleep using SetThreadExecutionState
- Sends Telegram alerts on restart and critical failure
- Logs activity to logs/keep_alive.log and records restart timestamps in logs/keep_alive_restarts.json
- Ensures dashboard server (http.server) is running
"""
import os
import sys
import time
import subprocess
import datetime
import json
import requests
from threading import Thread
from dotenv import load_dotenv
load_dotenv()

LOG = os.path.join(os.getcwd(), 'logs', 'keep_alive.log')
RESTARTS = os.path.join(os.getcwd(), 'logs', 'keep_alive_restarts.json')
CHECK_INTERVAL = 5 * 60  # 5 minutes
RESTART_LIMIT = 5
RESTART_WINDOW = 60 * 60  # seconds (1 hour)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT = os.getenv('TELEGRAM_CHAT_ID')
DASHBOARD_PORT = int(os.environ.get('DASH_PORT', '8530'))


def log(msg):
    ts = datetime.datetime.now().isoformat()
    line = f"{ts} | {msg}\n"
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass


def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        log('Telegram not configured; skipping send')
        return False
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        r = requests.post(url, json={'chat_id': TELEGRAM_CHAT, 'text': text}, timeout=5)
        if r.ok:
            log(f'Telegram sent: {text}')
            return True
        else:
            log(f'Telegram send failed: {r.status_code} {r.text}')
            return False
    except Exception as e:
        log(f'Telegram send error: {e}')
        return False


def prevent_sleep():
    if os.name != 'nt':
        return
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_AWAYMODE = 0x00000040
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(flags | ES_AWAYMODE)
        except Exception:
            ctypes.windll.kernel32.SetThreadExecutionState(flags)
        log('Requested system execution state (prevent sleep)')
    except Exception as e:
        log(f'Prevent sleep not available: {e}')


# Restart counting utilities
def _read_restarts():
    try:
        if os.path.exists(RESTARTS):
            with open(RESTARTS, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _write_restarts(lst):
    try:
        with open(RESTARTS, 'w', encoding='utf-8') as f:
            json.dump(lst, f)
    except Exception:
        pass


def record_restart():
    now = time.time()
    lst = _read_restarts()
    lst.append(now)
    # prune older than window
    lst = [t for t in lst if now - t <= RESTART_WINDOW]
    _write_restarts(lst)
    return len(lst)


def restart_count_last_hour():
    now = time.time()
    lst = _read_restarts()
    lst = [t for t in lst if now - t <= RESTART_WINDOW]
    return len(lst)


# Check if bot is running
def is_bot_running():
    try:
        out = subprocess.check_output(['wmic', 'process', 'where', "name='pythonw.exe' or name='python.exe'", 'get', 'ProcessId,CommandLine'], stderr=subprocess.STDOUT, text=True)
        lines = out.splitlines()
        for ln in lines:
            ln_lower = ln.lower()
            if 'main.py' in ln_lower or 'start_real.py' in ln_lower or 'r7_v3' in ln_lower:
                return True
    except Exception:
        try:
            out = subprocess.check_output(['tasklist', '/fi', 'imagename eq pythonw.exe'], text=True)
            if 'pythonw.exe' in out or 'python.exe' in out:
                return True
        except Exception:
            pass
    return False


def start_bot():
    try:
        pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
        start_script = os.path.join(os.getcwd(), 'start_real.py')
        if not os.path.exists(start_script):
            start_script = os.path.join(os.getcwd(), 'main.py')
        subprocess.Popen([pythonw, start_script], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        log(f'Started bot via {start_script} using {pythonw}')
        # notify via telegram
        send_telegram('⚠️ R7_V3 caiu, mas eu já o reiniciei automaticamente.')
    except Exception as e:
        log(f'Failed to start bot: {e}')
        send_telegram(f'❌ Watchdog falhou ao tentar reiniciar o bot: {e}')


def is_dashboard_running():
    try:
        import requests
        r = requests.get(f'http://127.0.0.1:{DASHBOARD_PORT}/dashboard.html', timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def start_dashboard():
    if is_dashboard_running():
        log('Dashboard already running')
        return
    try:
        pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
        subprocess.Popen([pythonw, '-m', 'http.server', str(DASHBOARD_PORT)], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        log('Started dashboard server on port %s' % DASHBOARD_PORT)
    except Exception as e:
        log(f'Failed to start dashboard: {e}')


def main():
    log('Watchdog started')
    prevent_sleep()
    # Respect NO_DASH env var: when set to 1/true/yes, do not start dashboard
    no_dash = os.environ.get('NO_DASH', '0').lower()
    if no_dash not in ('1', 'true', 'yes'):
        start_dashboard()
    else:
        log('NO_DASH set; skipping dashboard start')
        try:
            send_telegram('⚠️ keep_alive: NO_DASH enabled — dashboard will not be started by watchdog.')
        except Exception:
            pass

    while True:
        try:
            if not is_bot_running():
                log('Bot not running; need to attempt restart')
                count = restart_count_last_hour()
                if count >= RESTART_LIMIT:
                    msg = f'🚨 R7_V3 foi reiniciado mais de {RESTART_LIMIT} vezes na última hora; watchdog irá pausar e notificar.'
                    log(msg)
                    send_telegram(msg)
                    # do not attempt further restarts automatically
                    break
                # record restart and attempt
                rec = record_restart()
                log(f'Restart count in window: {rec}')
                start_bot()
            else:
                log('Bot running')
            prevent_sleep()
        except Exception as e:
            log(f'Watchdog error: {e}')
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
