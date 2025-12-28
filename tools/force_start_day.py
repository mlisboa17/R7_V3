#!/usr/bin/env python3
import json
import sys, os
sys.path.insert(0, os.getcwd())
from bots.guardiao import GuardiaoBot
config = json.load(open('config/settings.json'))

g = GuardiaoBot(config)
# Force today's start balance to 9909.25 as requested
ok = g.start_new_day(executor=None, force_saldo_brl=9909.25)
print('start_new_day ok=', ok)
print('state snapshot:', g.state)
