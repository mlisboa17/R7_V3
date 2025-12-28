import json, os
from datetime import date
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from tools.send_telegram_message import send

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT = os.getenv('TELEGRAM_CHAT_ID')

# Load month config
mc = {}
if os.path.exists('data/month_config.json'):
    try:
        mc = json.load(open('data/month_config.json','r',encoding='utf-8'))
    except Exception:
        mc = {}

# Load history to compute month accumulated
hist = []
if os.path.exists('data/history.json'):
    try:
        hist = json.load(open('data/history.json','r',encoding='utf-8')) or []
    except Exception:
        hist = []

ym = date.today().isoformat()[:7]
month_acum = 0.0
for e in hist:
    if e.get('date','').startswith(ym):
        month_acum += float(e.get('lucro_acumulado_dia_brl',0.0) or 0.0)
# add today's profit if present
today_profit = 0.0
if os.path.exists('logs/daily_state.json'):
    try:
        ld = json.load(open('logs/daily_state.json','r',encoding='utf-8'))
        today_profit = float(ld.get('lucro_do_dia_brl', ld.get('lucro_acumulado_dia_brl', 0.0)) or 0.0)
    except Exception:
        today_profit = 0.0
else:
    try:
        dd = json.load(open('data/daily_state.json','r',encoding='utf-8'))
        today_profit = float(dd.get('lucro_acumulado_dia_brl', dd.get('lucro_do_dia_brl', 0.0)) or 0.0)
    except Exception:
        today_profit = 0.0

month_acum += today_profit

# Compose message
start_usd = mc.get('month_start_balance_usd')
start_brl = mc.get('month_start_balance')
meta_usd = mc.get('month_meta_total_usd')
meta_brl = mc.get('month_meta_total')
final_usd = mc.get('month_final_goal_usd')
final_brl = mc.get('month_final_goal_brl')
start_date = mc.get('month_start_date')

month_falta_brl = max(0.0, (meta_brl or 0.0) - month_acum)
month_falta_usd = round(month_falta_brl / ( ( (json.load(open('logs/daily_state.json','r')).get('last_usdt_brl_rate')) if os.path.exists('logs/daily_state.json') else 1.0) or 1.0),2)

msg = (
    f"📣 RESUMO R7_V3 — Calibração concluída\n\n"
    f"🔹 Saldo início do mês: ${start_usd:,.2f} (BRL R$ {start_brl:,.2f})\n"
    f"🎯 Meta mensal (20%): ${meta_usd:,.2f} (BRL R$ {meta_brl:,.2f})\n"
    f"🏁 Objetivo final: ${final_usd:,.2f} (BRL R$ {final_brl:,.2f})\n\n"
    f"📅 Data de início oficial: {start_date}\n"
    f"📈 Progresso mês-to-date: BRL R$ {month_acum:,.2f} (Falta BRL R$ {month_falta_brl:,.2f} / USD ${month_falta_usd:,.2f})\n\n"
    f"💾 Arquivos: `data/month_config.json` e `data/daily_state.json` anexados para auditoria.\n\n"
    f"✅ O Projeto R7 está calibrado e em modo automático — meta fixa até o fim do mês (não decrescente)."
)

if not TOKEN or not CHAT:
    print('Missing Telegram credentials. Here is the message:')
    print(msg)
else:
    try:
        res = send(TOKEN, CHAT, msg)
        print('SENT', res.get('ok', False))
    except Exception as e:
        print('ERROR', e)
        print('Message:')
        print(msg)
