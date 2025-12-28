import sys, os, json
if len(sys.argv) < 2:
    print('Usage: python tools/set_trade_params.py params.json')
    sys.exit(1)
path = sys.argv[1]
if not os.path.exists(path):
    print('File not found:', path)
    sys.exit(1)
with open(path,'r',encoding='utf-8') as f:
    p = json.load(f)
# write to control file for main to pick up
os.makedirs('control', exist_ok=True)
with open(os.path.join('control','set_trade_params.json'),'w',encoding='utf-8') as cf:
    json.dump(p, cf)
print('Wrote control/set_trade_params.json')