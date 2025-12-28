import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bots.guardiao import GuardiaoBot

class DummyExec:
    def obter_saldo_real_spot(self, guardiao):
        # simulate closing balance
        return 10100.0

class DummyCom:
    def __init__(self):
        self.sent = []
    def send_text(self, text):
        print('[DUMMY COM] send_text:', text)
        self.sent.append(text)

if __name__ == '__main__':
    cfg = {'config_trade': {'meta_diaria_brl': 99.09, 'usdt_margin': 294.0, 'stop_diario_brl':10000.0}, 'banca_total_brl': 9909.25}
    g = GuardiaoBot(cfg, state_path='logs/daily_state_test.json')
    dcom = DummyCom()
    g.set_notify_callback(dcom.send_text)

    # set starting state
    g.state['saldo_inicial_brl'] = 9800.0
    g.state['lucro_do_dia_brl'] = 200.0
    g.state['usdt_operacional'] = 0.0
    g._write_state(g.state)

    print('Before report:', g.state)
    entry = g.generate_daily_report(executor=DummyExec())
    print('Report entry:', entry)
    print('After report state:', g.state)
