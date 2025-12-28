import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bots.guardiao import GuardiaoBot
from bots.executor import ExecutorBot

# load config
cfg_path = os.path.join('config','settings.json')
if os.path.exists(cfg_path):
    with open(cfg_path,'r',encoding='utf-8') as f:
        cfg = json.load(f)
else:
    cfg = {'config_trade':{'meta_diaria_brl':99.09,'usdt_margin':294.0},'banca_total_brl':9909.25}

g = GuardiaoBot(cfg)
e = ExecutorBot(cfg)

# If control file for month meta exists, apply it
cm = os.path.join('control','set_month_meta.json')
if os.path.exists(cm):
    try:
        with open(cm,'r',encoding='utf-8') as f:
            m = json.load(f)
        v = m.get('month_meta_total')
        if v is not None:
            print('[SMOKE] Applying control month meta:', v)
            g.set_month_meta_total(float(v))
    except Exception as exc:
        print('[SMOKE] Failed to apply control month meta:', exc)
    finally:
        try:
            os.remove(cm)
        except Exception:
            pass

# Save progress with executor snapshot
try:
    g.salvar_progresso(e)
    print('[SMOKE] salvar_progresso(executor) completed')
except Exception as exc:
    print('[SMOKE] Error calling salvar_progresso:', exc)

# Print daily_state.json
p = os.path.join('data','daily_state.json')
if os.path.exists(p):
    print('\n---- data/daily_state.json ----')
    print(open(p,'r',encoding='utf-8').read())
else:
    print('[SMOKE] data/daily_state.json not found')

# Print a summary line
try:
    j = json.load(open(p,'r',encoding='utf-8'))
    print('\n[SMOKE SUMMARY] equity_brl:', j.get('equity_brl'), 'month_meta_total:', j.get('month_meta_total'), 'month_acumulado_brl:', j.get('month_acumulado_brl'))
except Exception:
    pass
