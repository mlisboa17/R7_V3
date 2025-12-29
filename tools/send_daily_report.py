import os
import sys
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from bots.gestor_financeiro import GestorFinanceiro
from tools.send_telegram_message import send as send_telegram

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

def main():
    gestor = GestorFinanceiro()
    stats = gestor.status_atual()
    hoje = datetime.now().strftime('%Y-%m-%d')
    # Carrega saldo real consolidado e composição detalhada
    try:
        import json
        with open('data/account_composition.json', 'r', encoding='utf-8') as f:
            comp = json.load(f)
        saldo_real = comp.get('_total_usdt', 0.0)
        comp_table = {k: v for k, v in comp.items() if not k.startswith('_') and k != 'Earn/Staking'}
        comp_str = '\n'.join([f"- {k}: ${v:,.2f}" for k, v in sorted(comp_table.items(), key=lambda x: -x[1])])
    except Exception as e:
        saldo_real = None
        comp_str = f"(Erro ao carregar composição: {e})"

    msg = (
        f"\U0001F4C8 *RELATÓRIO DIÁRIO - {hoje}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 *Saldo Inicial do Dia:* ${stats.get('saldo_inicial', 0.0):.2f}\n"
        f"💰 *Saldo Final do Dia:* ${stats.get('saldo_final', 0.0):.2f}\n"
        f"📈 *Lucro/Prejuízo do Dia:* ${stats.get('lucro_hoje', 0.0):.2f} USDT\n"
        f"⚔️ *Trades Hoje:* {stats.get('trades_hoje', 0)} | 🏆 Win Rate: {stats.get('win_rate_hoje', 0.0):.1%}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 *Saldo Inicial Mês:* ${stats.get('saldo_inicial_mes', 0.0):.2f}\n"
        f"💰 *Saldo Atual Mês:* ${stats.get('saldo_final_mes', 0.0):.2f}\n"
        f"📈 *Lucro/Prejuízo do Mês:* ${stats.get('lucro_mes', 0.0):.2f} USDT\n"
        f"⚔️ *Trades no Mês:* {stats.get('trades_mes', 0)} | 🏆 Win Rate: {stats.get('win_rate_mes', 0.0):.1%}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *Saldo Real Consolidado:* ${saldo_real:,.2f}\n"
        f"📊 *Composição Detalhada:*\n{comp_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 _Relatório automático enviado em {datetime.now().strftime('%H:%M:%S')}_"
    )
    if send_telegram and token and chat_id:
        try:
            send_telegram(token, chat_id, msg)
            print('Relatório diário enviado com sucesso.')
        except Exception as e:
            print('Falha ao enviar relatório diário:', e)
    else:
        print('Telegram não configurado ou função de envio indisponível.')

if __name__ == '__main__':
    main()
