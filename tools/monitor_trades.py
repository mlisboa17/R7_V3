import time
import json
import os
import logging
from datetime import datetime

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
TRADES_FILE = os.path.join(BASE_DIR, 'data', 'trades_log.json')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'trades_tail.log')

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s %(message)s')


def load_trades():
    try:
        with open(TRADES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def main():
    last_count = len(load_trades())
    logging.info(f"monitor_trades started; file={TRADES_FILE}; initial_count={last_count}")
    print(f"monitor_trades started; watching {TRADES_FILE}; initial_count={last_count}")
    try:
        while True:
            try:
                trades = load_trades()
                if len(trades) > last_count:
                    new = trades[last_count:]
                    for t in new:
                        ts = t.get('timestamp') or t.get('date') or ''
                        msg = f"NEW_TRADE pair={t.get('pair')} strategy={t.get('estrategia')} pnl={t.get('pnl_usdt')} ts={ts}"
                        print(msg)
                        logging.info(msg)
                    last_count = len(trades)
                time.sleep(2)
            except Exception as e:
                logging.exception('Error while reading trades file')
                time.sleep(5)
    except KeyboardInterrupt:
        logging.info('monitor_trades stopped by KeyboardInterrupt')


if __name__ == '__main__':
    main()
