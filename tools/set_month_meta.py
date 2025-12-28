import sys, os, json
if len(sys.argv) < 2:
    print('Usage: python tools/set_month_meta.py <amount_in_brl>')
    sys.exit(1)
amount = float(sys.argv[1])
os.makedirs('control', exist_ok=True)
with open(os.path.join('control', 'set_month_meta.json'), 'w', encoding='utf-8') as f:
    json.dump({'month_meta_total': amount}, f)
print(f'Wrote control/set_month_meta.json with month_meta_total={amount}')