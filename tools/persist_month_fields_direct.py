import json, os
from datetime import date

# Desired values from user
month_start_usd = 9660.84
month_meta_usd = 1932.17
rate = None
# Try to read last rate from existing data/daily_state.json or logs/daily_state.json
try:
    p='data/daily_state.json'
    if os.path.exists(p):
        j=json.load(open(p,'r',encoding='utf-8'))
        rate = j.get('last_usdt_brl_rate')
except Exception:
    rate=None
if not rate:
    try:
        p='logs/daily_state.json'
        if os.path.exists(p):
            j=json.load(open(p,'r',encoding='utf-8'))
            rate = j.get('last_usdt_brl_rate')
    except Exception:
        rate=None
if not rate:
    rate = 5.5406

start_brl = round(month_start_usd * rate, 2)
meta_brl = round(month_meta_usd * rate, 2)
final_goal_usd = round(month_start_usd + month_meta_usd, 2)
final_goal_brl = round(start_brl + meta_brl, 2)

# Update logs/daily_state.json
logs_path = 'logs/daily_state.json'
os.makedirs(os.path.dirname(logs_path), exist_ok=True)
logs = {}
if os.path.exists(logs_path):
    try:
        logs = json.load(open(logs_path,'r',encoding='utf-8'))
    except Exception:
        logs = {}
logs.update({
    'month_start_balance': start_brl,
    'month_start_balance_usd': month_start_usd,
    'month_start_date': date.today().isoformat(),
    'month_meta_total': meta_brl,
    'month_meta_total_usd': month_meta_usd,
    'month_final_goal_brl': final_goal_brl,
    'month_final_goal_usd': final_goal_usd,
})
with open(logs_path,'w',encoding='utf-8') as f:
    json.dump(logs, f, indent=2)
print('[OK] updated', logs_path)

# Update data/daily_state.json friendly file
data_path = 'data/daily_state.json'
os.makedirs(os.path.dirname(data_path), exist_ok=True)
current = {}
if os.path.exists(data_path):
    try:
        current = json.load(open(data_path,'r',encoding='utf-8'))
    except Exception:
        current = {}
current.update({
    'data': date.today().isoformat(),
    'month_start_balance': start_brl,
    'month_start_balance_usd': month_start_usd,
    'month_meta_total': meta_brl,
    'month_meta_total_usd': month_meta_usd,
    'month_final_goal_brl': final_goal_brl,
    'month_final_goal_usd': final_goal_usd,
})
with open(data_path,'w',encoding='utf-8') as f:
    json.dump(current, f, indent=2)
print('[OK] updated', data_path)
print(json.dumps(current, indent=2))