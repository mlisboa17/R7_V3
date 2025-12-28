#!/usr/bin/env python3
import json
import sys, os
sys.path.insert(0, os.getcwd())
from bots.guardiao import GuardiaoBot
import json
config = json.load(open('config/settings.json'))

g = GuardiaoBot(config)
# Read amount from trades.log last sell
try:
    with open('logs/trades.log','r',encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
        last = lines[-1]
        # parse received_usdt= in last line
        if 'received_usdt=' in last:
            received = float(last.split('received_usdt=')[-1])
        else:
            received = 0.0
except Exception:
    received = 0.0

# set in internal state and save
g.state['usdt_operacional'] = round(received,6)
g._write_state(g.state)
# Now call salvar_progresso to propagate to data/daily_state.json
g.salvar_progresso()
print('Applied usdt_operacional=', received)
