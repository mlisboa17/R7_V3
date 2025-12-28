import time
import pathlib
import json
import os
import sys

sys.path.insert(0, os.getcwd())

LOG_DIR = pathlib.Path('logs')
TRADE_LOG = pathlib.Path('data/trades_log.json')

def find_latest_log():
    files = [f for f in LOG_DIR.iterdir() if f.is_file()]
    if not files:
        return None
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files[0]

def print_summary():
    # short account/trades summary
    try:
        if TRADE_LOG.exists():
            t = json.load(open(TRADE_LOG, 'r', encoding='utf-8'))
            recent = t[-5:] if isinstance(t, list) else []
            print('\n=== Últimos trades ===')
            for tr in recent:
                print(tr)
        else:
            print('\n=== trades_log not found ===')
    except Exception as e:
        print('\n=== erro lendo trades_log:', e)

def tail_log(path):
    print(f"Tailing {path} (Ctrl+C to stop).")
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            # seek to end
            f.seek(0, os.SEEK_END)
            last_summary = time.time()
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                else:
                    line = line.rstrip('\n')
                    if 'ERROR' in line or 'CRITICAL' in line or 'FAIL' in line:
                        print('\x1b[31m' + line + '\x1b[0m')
                    elif 'WARN' in line or 'WARNING' in line:
                        print('\x1b[33m' + line + '\x1b[0m')
                    else:
                        print(line)

                # periodic summary
                if time.time() - last_summary > 30:
                    print_summary()
                    last_summary = time.time()
    except KeyboardInterrupt:
        print('\nMonitor stopped by user')
    except Exception as e:
        print('Monitor error:', e)

def main():
    latest = find_latest_log()
    if not latest:
        print('No log files found in logs/ directory')
        return
    tail_log(latest)

if __name__ == '__main__':
    main()
