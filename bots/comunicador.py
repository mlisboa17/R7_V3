import os
import logging
import sqlite3
import asyncio
import telegram
from datetime import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters

logger = logging.getLogger('comunicador')

class ComunicadorBot:
    def __init__(self, token, chat_id, config, guardiao=None, executor=None, estrategista=None):
        self.token = token
        self.chat_id = chat_id
        self.config = config
        self.db_path = 'memoria_bot.db'
        
        # Injeção de dependências
        self.guardiao = guardiao
        self.executor = executor
        self.estrategista = estrategista
        
        self.bot = telegram.Bot(token=self.token)
        logger.info("[COMUNICADOR] Sistema Sniper Consolidado Ativado.")

    # --- 1. ALERTA DE TRADE (EXECUÇÃO) ---
    async def enviar_alerta_trade(self, par, acao, valor, estrategia, confianca=0.85):
        """Notifica entradas com a barra visual de confiança da IA."""
        emoji = "🎯" if acao.upper() in ["COMPRA", "BUY"] else "💰"
        num_verdes = int(confianca * 10)
        barra = "🟢" * num_verdes + "⚪" * (10 - num_verdes)
        
        msg = (
            f"{emoji} *SINAL SNIPER: {estrategia.upper()}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 *Ativo:* `{par}`\n"
            f"⚡ *Ação:* `{acao.upper()}`\n"
            f"💵 *Investido:* `${valor:.2f}`\n"
            f"📊 *Confiança IA:* `{confianca:.1%}`\n"
            f"[{barra}]\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ {datetime.now().strftime('%H:%M:%S')}"
        )
        await self._enviar(msg)

    # --- 2. RELATÓRIO DE PNL (FECHAMENTO) ---
    async def reportar_pnl(self, par, pnl_usdt, estrategia):
        """Relata o fechamento de posição e resultado."""
        emoji = "✅" if pnl_usdt > 0 else "❌"
        msg = (
            f"{emoji} *TRADE ENCERRADO*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 *Ativo:* `{par}`\n"
            f"💰 *Resultado:* `${pnl_usdt:.2f} USDT`\n"
            f"📂 *Estratégia:* `{estrategia}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        await self._enviar(msg)

    # --- 3. DASHBOARD CONSOLIDADO (/status) ---
    async def status_handler(self, update, context):
        """Dashboard que une Analista/Estrategista nas Estratégias Reais."""
        try:
            stats = self.estrategista.gestor.status_atual()
            detalhes_brutos = stats.get('detalhes_bots', {})

            # 1. Estrutura dos 4 Bots Operacionais
            consolidado = {
                "Scalping V6": {"pnl": 0.0, "trades": 0, "wins": 0},
                "Momentum Boost": {"pnl": 0.0, "trades": 0, "wins": 0},
                "Swing RWA": {"pnl": 0.0, "trades": 0, "wins": 0},
                "IA Sniper Pro": {"pnl": 0.0, "trades": 0, "wins": 0}
            }

            # 2. Lógica de Consolidação (Soma Analista/Estrategista nos grupos corretos)
            for nome_original, data in detalhes_brutos.items():
                pnl = data.get('pnl', 0.0)
                t = data.get('trades', 0)
                w = data.get('wins', 0)

                nome_low = nome_original.lower()
                if "scalping" in nome_low: target = "Scalping V6"
                elif "momentum" in nome_low: target = "Momentum Boost"
                elif "swing" in nome_low or "rwa" in nome_low: target = "Swing RWA"
                else: target = "IA Sniper Pro" # Analista/Estrategista/IA caem aqui

                consolidado[target]["pnl"] += pnl
                consolidado[target]["trades"] += t
                consolidado[target]["wins"] += w

            # 3. Construção da Tabela de Lucro Diário (SQL)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT strftime('%d/%m', data), lucro_liq FROM daily_states ORDER BY data DESC LIMIT 7")
            historico = cursor.fetchall()
            conn.close()

            # --- MONTAGEM DA MENSAGEM ---
            msg = "📊 *DASHBOARD R7_V3 CONSOLIDADO*\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━\n"
            
            # Parte 1: Performance por Estratégia
            for nome, info in consolidado.items():
                if info['trades'] > 0:
                    wr = (info['wins'] / info['trades']) * 100 if info['trades'] > 0 else 0
                    emoji = "🟢" if info['pnl'] >= 0 else "🔴"
                    msg += f"{emoji} *Bot:* `{nome}`\n"
                    msg += f"💰 *PnL:* `${info['pnl']:.2f}` | 🎯 *WR:* {wr:.1f}%\n\n"

            # Parte 2: Tabela de Datas (Como você pediu)
            msg += "📅 *HISTÓRICO RECENTE*\n"
            msg += "```\n"
            msg += f"{'DATA':<8} | {'LUCRO':<10}\n"
            msg += "---------|----------\n"
            soma_mes = 0.0
            for dia, lucro in reversed(historico):
                soma_mes += lucro
                e_status = "🟢" if lucro >= 0 else "🔴"
                msg += f"{dia:<8} | {e_status} {lucro:>7.2f}\n"
            msg += "---------|----------\n"
            msg += f"{'TOTAL':<8} | ${soma_mes:>8.2f}\n"
            msg += "```\n"
            msg += f"🕒 _Sincronizado: {datetime.now().strftime('%H:%M:%S')}_"

            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erro no dashboard: {e}")
            await update.message.reply_text("⚠️ Erro ao consolidar dados.")

    # --- 4. FUNÇÕES DE APOIO ---
    async def _enviar(self, texto):
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=texto, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Erro Telegram: {e}")

    def start_polling(self):
        try:
            app = Application.builder().token(self.token).build()
            app.add_handler(CommandHandler("status", self.status_handler))
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Falha no Polling: {e}")