#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.getcwd())
from bots.guardiao import GuardiaoBot
config = json.load(open('config/settings.json'))

g = GuardiaoBot(config)
# enforce values
g.state['saldo_inicial_brl'] = 9909.25
g.state['meta_diaria_brl'] = round(9909.25 * 0.01,2)
g.state['lucro_do_dia_brl'] = 86.31
g.state['usdt_operacional'] = 150.06691287
# update storico (if needed) - keep history as-is
g._write_state(g.state)
print('WROTE guardiao state; calling salvar_progresso')
g.salvar_progresso()
print('Done; reading data/daily_state.json:')
print(open('data/daily_state.json','r',encoding='utf-8').read())
