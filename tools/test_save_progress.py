import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bots.guardiao import GuardiaoBot
from bots.executor import ExecutorBot
cfg_path = 'config/settings.json'
try:
    with open(cfg_path,'r',encoding='utf-8') as f:
        cfg=json.load(f)
except Exception:
    cfg={'config_trade':{'meta_diaria_brl':99.09,'usdt_margin':294.0},'banca_total_brl':9909.25}

g=GuardiaoBot(cfg)
e=ExecutorBot(cfg)
# Save progress using executor snapshot
try:
    g.salvar_progresso(e)
    print('[OK] salvar_progresso(executor) called')
except Exception as exc:
    print('Error calling salvar_progresso:', exc)
# Print daily_state.json
try:
    with open('data/daily_state.json','r',encoding='utf-8') as f:
        print('\n---- data/daily_state.json ----')
        print(f.read())
except Exception as exc:
    print('Error reading daily_state.json:', exc)
