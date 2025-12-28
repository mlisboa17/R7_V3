#!/usr/bin/env python3
"""Apply critical corrections to today's daily_state.json as requested:
- Force Saldo Inicial = 9909.25
- Set Lucro Hoje = 86.31
- Set USDT available = 150.06691287
- Recompute and save daily_state.json via Guardiao.salvar_progresso
"""
import sys, os, json
sys.path.insert(0, os.getcwd())
from bots.guardiao import GuardiaoBot

config = json.load(open('config/settings.json'))

g = GuardiaoBot(config)

# Set values
g.state['saldo_inicial_brl'] = 9909.25
g.state['meta_diaria_brl'] = round(9909.25 * 0.01, 2)
# set today's profit
g.state['lucro_do_dia_brl'] = 86.31
# usdt available
g.state['usdt_operacional'] = 150.06691287
# ensure lucro_acumulado_usdt exists (leave as-is if present)
if 'lucro_acumulado_usdt' not in g.state:
    g.state['lucro_acumulado_usdt'] = 0.0
# write and persist via salvar_progresso
g._write_state(g.state)
print('State written to guardiao; calling salvar_progresso()')
g.salvar_progresso()
print('Saved progress; check data/daily_state.json')
