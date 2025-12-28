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
# Reload state from logs to pick up persisted month_config
g._load_state()
# Call salvar_progresso which now picks month_config.json
g.salvar_progresso(e)
print('[OK] salvar_progresso called; data/daily_state.json now:')
print(open('data/daily_state.json','r',encoding='utf-8').read())