import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bots.guardiao import GuardiaoBot
from bots.executor import ExecutorBot

cfg_path = os.path.join('config','settings.json')
if os.path.exists(cfg_path):
    with open(cfg_path,'r',encoding='utf-8') as f:
        cfg = json.load(f)
else:
    cfg = {'config_trade':{'meta_diaria_brl':99.09,'usdt_margin':294.0},'banca_total_brl':9909.25}

g = GuardiaoBot(cfg)
e = ExecutorBot(cfg)

# Reload state to pick up manual edits in logs/daily_state.json
g._load_state()
print('[INFO] state keys (month):', [k for k in g.state.keys() if k.startswith('month')])
# Persist friendly data file
g.salvar_progresso(e)
print('[OK] Saved data/daily_state.json via salvar_progresso')
print('--- data/daily_state.json ---')
print(open('data/daily_state.json','r',encoding='utf-8').read())