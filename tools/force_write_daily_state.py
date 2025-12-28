#!/usr/bin/env python3
"""Forcefully write corrected daily_state.json with requested values.
"""
import json, os
from datetime import date

# compute historical sum
hist_path = os.path.join('data','history.json')
hist_sum = 0.0
if os.path.exists(hist_path):
    try:
        with open(hist_path,'r',encoding='utf-8') as f:
            hist = json.load(f) or []
        for e in hist:
            hist_sum += float(e.get('lucro_acumulado_dia_brl',0.0) or 0.0)
    except Exception:
        hist_sum = 0.0

payload = {
    'data': date.today().isoformat(),
    'saldo_inicial_brl': 9909.25,
    'meta_diaria_brl': round(9909.25 * 0.01, 2),
    'banca_inicial_brl': 9909.25,
    'lucro_acumulado_dia_brl': 86.31,
    'lucro_total_brl': round(86.31 + hist_sum, 2),
    'trades_today': 0,
    'usdt_operacional': 150.06691287,
    'lucro_acumulado_usdt': 0.0,
    'last_usdt_brl_rate': 5.5393,
    'status_meta': 'pendente'
}

os.makedirs('data', exist_ok=True)
with open('data/daily_state.json','w',encoding='utf-8') as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)

print('WROTE data/daily_state.json')
print(json.dumps(payload, indent=2, ensure_ascii=False))
