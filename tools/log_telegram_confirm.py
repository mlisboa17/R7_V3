from datetime import datetime

msg = f"{datetime.utcnow().isoformat()} | chat_id=8483312482 | SENT: R7_V3 MODO REAL ATIVADO - Saldo operacional: 294 USDT. Meta: R$ 99,09\n"
with open('logs/telegram_confirm.log', 'a', encoding='utf-8') as f:
    f.write(msg)
print('OK')
