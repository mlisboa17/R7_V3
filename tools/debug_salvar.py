import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bots.guardiao import GuardiaoBot
from bots.executor import ExecutorBot

cfg_path = os.path.join('config','settings.json')
if os.path.exists(cfg_path):
    cfg = json.load(open(cfg_path,'r',encoding='utf-8'))
else:
    cfg={'config_trade':{'meta_diaria_brl':99.09,'usdt_margin':294.0},'banca_total_brl':9909.25}

g = GuardiaoBot(cfg)
e = ExecutorBot(cfg)

print('month_config exists:', os.path.exists('data/month_config.json'))
if os.path.exists('data/month_config.json'):
    print('month_config:', json.dumps(json.load(open('data/month_config.json','r',encoding='utf-8')), indent=2))

print('state month keys:', {k:g.state.get(k) for k in g.state.keys() if k.startswith('month')})
print('calling salvar_progresso(executor)')
g.salvar_progresso(e)
print('wrote data/daily_state.json:')
print(open('data/daily_state.json','r',encoding='utf-8').read())
