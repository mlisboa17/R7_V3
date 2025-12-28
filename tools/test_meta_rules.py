import sys, os
# ensure project root is on sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bots.guardiao import GuardiaoBot
from bots.executor import ExecutorBot
import time

class DummyCom:
    def send_text(self, text):
        print('[DUMMY COM] send_text:', text)

class DummyExec:
    def __init__(self):
        self.stopped = False
    def emergency_stop(self):
        print('[DUMMY EXEC] emergency_stop called')
        self.stopped = True

if __name__ == '__main__':
    cfg = {
        'config_trade': {
            'meta_diaria_brl': 99.09,
            'usdt_margin': 294.0,
            'stop_diario_brl': 10000.0
        },
        'banca_total_brl': 9909.25
    }
    g = GuardiaoBot(cfg, state_path='logs/daily_state_test.json')
    dcom = DummyCom()
    de = DummyExec()
    g.set_notify_callback(dcom.send_text)
    g.set_stop_callback(de.emergency_stop)

    print('Start state:', g.state)

    # Simulate incremental profits
    print('\n-- Sim: +50 (below meta)')
    g.update_lucro(50)
    time.sleep(0.1)
    print('state:', g.state)

    print('\n-- Sim: +50 (cross meta total 100.0)')
    g.update_lucro(50)
    time.sleep(0.1)
    print('state:', g.state)

    print('\n-- Sim: -6 (drop to 94.0 => below 95% of meta)')
    g.update_lucro(-6)
    time.sleep(0.1)
    print('state:', g.state)
    print('executor stopped?', de.stopped)

    print('\n-- Reset day and test super meta')
    g.start_new_day()
    print('state reset:', g.state)

    print('\n-- Sim: +150 (above 150% of meta)')
    g.update_lucro(150)
    time.sleep(0.1)
    print('state:', g.state)
    print('executor stopped?', de.stopped)
