import os
import logging
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
        
        # Injeção de dependências para relatórios em tempo real
        self.guardiao = guardiao
        self.executor = executor
        self.estrategista = estrategista
        
        # Inicialização do Bot
        self.bot = telegram.Bot(token=self.token)
        logger.info("[COMUNICADOR] Sistema de notificações ativo.")

    async def enviar_alerta_trade(self, par, acao, valor, estrategia):
        """Notifica cada entrada do Sniper no Telegram."""
        emoji = "🚀" if acao.upper() == "COMPRA" else "💰"
        msg = (
            f"{emoji} *[SINAL: {estrategia.upper()}]*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔹 *Ação:* {acao}\n"
            f"💎 *Ativo:* {par}\n"
            f"💵 *Investido:* ${valor:.2f} USDT\n"
            f"⏰ *Horário:* {datetime.now().strftime('%H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        await self._enviar(msg)

    async def reportar_pnl(self, par, pnl_usdt, estrategia):
        """Relata o fechamento de uma posição e o lucro/prejuízo."""
        emoji = "✅" if pnl_usdt > 0 else "❌"
        msg = (
            f"{emoji} *[FECHAMENTO: {estrategia.upper()}]*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 *Ativo:* {par}\n"
            f"💰 *Resultado:* ${pnl_usdt:.2f} USDT\n"
            f"📅 *Data:* {datetime.now().strftime('%d/%m %H:%M')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        await self._enviar(msg)

    async def status_handler(self, update, context):
        """Responde ao comando /status com dados financeiros completos e visuais."""
        try:
            # Puxa dados do Gestor Financeiro via Estrategista
            stats = self.estrategista.gestor.status_atual()
            lucro_dia = stats.get('lucro_hoje', 0.0)
            meta_fixa = self.estrategista.gestor.meta_diaria_fixa
            saldo_inicial = stats.get('saldo_inicial', 0.0)
            saldo_final = stats.get('saldo_final', 0.0)
            lucro_mes = stats.get('lucro_mes', 0.0)
            saldo_inicial_mes = stats.get('saldo_inicial_mes', 0.0)
            saldo_final_mes = stats.get('saldo_final_mes', 0.0)
            trades_hoje = stats.get('trades_hoje', 0)
            trades_mes = stats.get('trades_mes', 0)
            win_rate_hoje = stats.get('win_rate_hoje', 0.0)
            win_rate_mes = stats.get('win_rate_mes', 0.0)
            drawdown_hoje = stats.get('drawdown_hoje', 0.0)
            drawdown_mes = stats.get('drawdown_mes', 0.0)
            progresso = (lucro_dia / meta_fixa) * 100 if meta_fixa else 0.0
            status_meta = "✅ META BATIDA!" if stats.get('meta_batida') else f"Faltam ${ (meta_fixa - lucro_dia):.2f}"

            saldo_earn = 200.02
            saldo_bots = 142.42
            saldo_total = saldo_final + saldo_earn + saldo_bots
            lucro_total = saldo_total - saldo_inicial
            msg = (
                f"📊 *STATUS R7_V3 SNIPER*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💵 *Saldo Inicial do Dia:* ${saldo_inicial:.2f}\n"
                f"💰 *Saldo Final do Dia:* ${saldo_final:.2f}\n"
                f"💸 *Earn (USDT):* ${saldo_earn:.2f}\n"
                f"🤖 *Bots Binance (USDT):* ${saldo_bots:.2f}\n"
                f"💼 *Saldo Total Consolidado:* ${saldo_total:.2f}\n"
                f"📈 *Lucro/Prejuízo do Dia:* ${lucro_dia:.2f} USDT\n"
                f"💹 *Lucro/Prejuízo Consolidado:* ${lucro_total:.2f} USDT\n"
                f"🎯 *Meta Diária:* ${meta_fixa:.2f} ({progresso:.1f}%)\n"
                f"🛡️ *Status:* {status_meta}\n"
                f"⚔️ *Trades Hoje:* {trades_hoje} | 🏆 Win Rate: {win_rate_hoje:.1%}\n"
                f"📉 *Drawdown Hoje:* {drawdown_hoje:.2f}%\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 *Resumo Mensal*\n"
                f"💵 *Saldo Inicial Mês:* ${saldo_inicial_mes:.2f}\n"
                f"💰 *Saldo Atual Mês:* ${saldo_final_mes:.2f}\n"
                f"📈 *Lucro/Prejuízo do Mês:* ${lucro_mes:.2f} USDT\n"
                f"⚔️ *Trades no Mês:* {trades_mes} | 🏆 Win Rate: {win_rate_mes:.1%}\n"
                f"📉 *Drawdown Mês:* {drawdown_mes:.2f}%\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🕒 _Dados atualizados em tempo real_"
            )
            await update.message.reply_text(msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Erro no status_handler: {e}")
            await update.message.reply_text("⚠️ Erro ao acessar dados financeiros.")

    async def _enviar(self, texto):
        """Entrega as mensagens garantindo o parse_mode."""
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=texto, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"[COMUNICADOR] Erro de envio: {e}")

    def start_polling(self):
        """Roda em background ouvindo seus comandos e respostas."""
        try:
            app = Application.builder().token(self.token).build()
            app.add_handler(CommandHandler("status", self.status_handler))

            # Handler para respostas de texto (SIM/NÃO) para meta
            async def resposta_meta_handler(update, context):
                texto = update.message.text.strip().upper()
                if texto in ["SIM", "NÃO", "NAO"]:
                    if self.estrategista:
                        self.estrategista._resposta_meta = texto
                        await update.message.reply_text(f"Recebido: {texto}. Obrigado!", parse_mode='Markdown')

            app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), resposta_meta_handler))

            logger.info('[COMUNICADOR] Polling do Telegram iniciado.')
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Falha crítica no polling do Telegram: {e}")