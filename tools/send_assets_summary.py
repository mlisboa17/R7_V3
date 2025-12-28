import os, json, sys
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# load results
p = 'data/nonzero_assets_brl_extended.json'
if not os.path.exists(p):
    print('NO_DATA')
    sys.exit(2)
with open(p,'r',encoding='utf-8') as f:
    j = json.load(f)

total = j.get('total_brl',0)
assets = j.get('assets',[])[:6]
lines = [f"📊 RESUMO DE ATIVOS — TOTAL ESTIMADO: R$ {total:,.2f}"]
for a in assets:
    brl = a.get('brl')
    if brl is None:
        lines.append(f" - {a['asset']}: {a['qty']} -> SEM_CONVERSAO")
    else:
        lines.append(f" - {a['asset']}: {a['qty']} -> R$ {brl:,.2f}")
msg = '\n'.join(lines)

# send via tools/send_telegram_message.py
import subprocess
token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')
if not token or not chat:
    print('NO_TELEGRAM')
    print(msg)
    sys.exit(0)
res = subprocess.run(['python','tools/send_telegram_message.py', msg], capture_output=True, text=True)
print('SEND OUTPUT:', res.stdout, res.stderr)
if res.returncode == 0:
    # attempt to send the extended JSON file as attachment
    json_path = 'data/nonzero_assets_brl_extended.json'
    if os.path.exists(json_path):
        sendf = subprocess.run(['python','tools/send_telegram_file.py', json_path, 'Relatório completo de ativos (JSON)'], capture_output=True, text=True)
        print('SEND FILE OUTPUT:', sendf.stdout, sendf.stderr)
        if sendf.returncode == 0:
            print('FILE SENT')
        else:
            print('FILE SEND FAILED')
    print('SENT')
else:
    print('FAILED')
