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
        """Responde ao comando /status com os dados financeiros reais."""
        try:
            # Puxa dados do Gestor Financeiro via Estrategista
            stats = self.estrategista.gestor.status_atual()
            lucro_dia = stats['lucro_hoje']
            meta_fixa = self.estrategista.gestor.meta_diaria_fixa
            
            # Cálculo de progresso
            progresso = (lucro_dia / meta_fixa) * 100
            status_meta = "✅ META BATIDA!" if stats['meta_batida'] else f"Faltam ${ (meta_fixa - lucro_dia):.2f}"

            msg = (
                f"📊 *STATUS R7_V3 SNIPER*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📈 *Lucro Hoje:* ${lucro_dia:.2f}\n"
                f"🎯 *Meta Fixa:* ${meta_fixa:.2f} ({progresso:.1f}%)\n"
                f"🛡️ *Status:* {status_meta}\n"
                f"⚔️ *Trades Ativos:* {len(self.estrategista.open_positions)}\n"
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
        """Roda em background ouvindo seus comandos."""
        try:
            # Cria a aplicação para o polling
            app = Application.builder().token(self.token).build()
            
            # Adiciona os comandos
            app.add_handler(CommandHandler("status", self.status_handler))
            
            logger.info('[COMUNICADOR] Polling do Telegram iniciado.')
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Falha crítica no polling do Telegram: {e}")