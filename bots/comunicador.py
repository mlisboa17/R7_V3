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
        
        # Injeção de dependências
        self.guardiao = guardiao
        self.executor = executor
        self.estrategista = estrategista
        
        # Inicialização do Bot
        self.bot = telegram.Bot(token=self.token)
        logger.info("[COMUNICADOR] Sistema Sniper Visual ativado.")

    async def enviar_alerta_trade(self, par, acao, valor, estrategia, confianca=0.85):
        """Notifica entradas com foco na Confiança da IA e Gestão de Lote."""
        emoji = "🎯" if acao.upper() in ["COMPRA", "BUY"] else "💰"
        
        # Barra visual de confiança (85% = 8 bolinhas verdes)
        num_verdes = int(confianca * 10)
        barra = "🟢" * num_verdes + "⚪" * (10 - num_verdes)
        
        msg = (
            f"{emoji} <b>SINAL DETECTADO: {estrategia.upper()}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>Ativo:</b> {par}\n"
            f"⚡ <b>Ação:</b> {acao.upper()}\n"
            f"💵 <b>Investido:</b> ${valor:.2f} USDT\n"
            f"📊 <b>Confiança IA:</b> {confianca:.1%}\n"
            f"[{barra}]\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ {datetime.now().strftime('%H:%M:%S')} | R7_V3 Sniper"
        )
        await self._enviar(msg)

    async def reportar_pnl(self, par, pnl_usdt, estrategia):
        """Relata o fechamento de posição com destaque visual no resultado."""
        lucro = pnl_usdt > 0
        emoji = "✅" if lucro else "❌"
        status = "LUCRO" if lucro else "PREJUÍZO"
        
        msg = (
            f"{emoji} <b>OPERAÇÃO ENCERRADA: {status}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>Ativo:</b> {par}\n"
            f"💰 <b>Resultado:</b> ${pnl_usdt:+.2f} USDT\n"
            f"📂 <b>Estratégia:</b> {estrategia}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 {datetime.now().strftime('%d/%m %H:%M')}"
        )
        await self._enviar(msg)

    async def alertar_kill_switch(self, motivo, perda_atual=0):
        """Alerta crítico de segurança."""
        msg = (
            f"🛑 <b>PROTEÇÃO ATIVADA: KILL SWITCH</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>Motivo:</b> {motivo}\n"
            f"📉 <b>Drawdown:</b> {perda_atual:.2f}%\n"
            f"📢 <b>Ação:</b> Operações suspensas para proteger capital.\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <i>Monitorização R7_V3 Ativa</i>"
        )
        await self._enviar(msg)

    async def status_handler(self, update, context):
        """Responde ao comando /status com o dashboard financeiro consolidado."""
        try:
            stats = self.estrategista.gestor.status_atual()
            lucro_dia = stats.get('lucro_hoje', 0.0)
            meta_fixa = self.estrategista.gestor.meta_diaria_fixa
            
            progresso = (lucro_dia / meta_fixa) * 100 if meta_fixa else 0.0
            status_meta = "✅ META BATIDA!" if stats.get('meta_batida') else f"Faltam `${ (meta_fixa - lucro_dia):.2f}`"

            msg = (
                f"📊 *DASHBOARD R7_V3 SNIPER*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💵 *Saldo Inicial:* `${stats.get('saldo_inicial', 0.0):.2f}`\n"
                f"💰 *Saldo Atual:* `${stats.get('saldo_final', 0.0):.2f}`\n"
                f"📈 *Lucro Hoje:* `${lucro_dia:.2f} USDT`\n"
                f"🎯 *Meta:* `${meta_fixa:.2f}` (`{progresso:.1f}%`)\n"
                f"🛡️ *Status:* {status_meta}\n\n"
                f"⚔️ *Trades Hoje:* `{stats.get('trades_hoje', 0)}` | 🏆 WR: `{stats.get('win_rate_hoje', 0.0):.1%}`\n"
                f"📉 *Drawdown:* `{stats.get('drawdown_hoje', 0.0):.2f}%`\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🕒 _Atualizado em:_ `{datetime.now().strftime('%H:%M:%S')}`"
            )
            await update.message.reply_text(msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Erro no status_handler: {e}")
            await update.message.reply_text("⚠️ Erro ao aceder aos dados financeiros.")

    async def _enviar(self, texto):
        """Entrega as mensagens garantindo o parse_mode HTML."""
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=texto, parse_mode='HTML')
        except Exception as e:
            logger.error(f"[COMUNICADOR] Erro de envio: {e}")
            # Fallback: Tenta enviar sem formatação
            try:
                await self.bot.send_message(chat_id=self.chat_id, text=texto)
            except:
                pass

    def start_polling(self):
        """Inicia a escuta de comandos (Roda em thread separada no main)."""
        try:
            app = Application.builder().token(self.token).build()
            
            # Comandos
            app.add_handler(CommandHandler("status", self.status_handler))
            
            # Handler para respostas rápidas
            async def resposta_meta_handler(update, context):
                texto = update.message.text.strip().upper()
                if texto in ["SIM", "NÃO", "NAO"]:
                    if self.estrategista:
                        self.estrategista._resposta_meta = texto
                        await update.message.reply_text(f"✅ Confirmado: {texto}")

            app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), resposta_meta_handler))

            logger.info('[COMUNICADOR] Polling do Telegram iniciado.')
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Falha no Telegram Polling: {e}")