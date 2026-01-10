import sys, json, os
sys.path.insert(0, 'R7_V3')
sys.path.insert(0, '.')
from bots.guardiao import GuardiaoBot
from bots.estrategista import EstrategistaBot
from tools.lock_notifier import LockNotifier

cfg = json.load(open('config/settings.json'))
guard = GuardiaoBot(cfg)
estr = EstrategistaBot(cfg)
class DummyExec:
    def __init__(self):
        self.active_trades = {}
executor = DummyExec()
ln = LockNotifier(guard, estr, executor)
status = ln._gather_status()
import pprint
pprint.pprint(status)

os.makedirs('data', exist_ok=True)
with open('data/locks_status.json','w',encoding='utf-8') as f:
    json.dump(status,f,indent=2,ensure_ascii=False)
print('\nWrote data/locks_status.json')
