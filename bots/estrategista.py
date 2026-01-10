import logging
import os
import asyncio
from datetime import datetime

# Importações de ferramentas e utilitários
from .gestor_financeiro import GestorFinanceiro
from utils.volatility import calculate_volatility
from tools.convert_to_stable import converter_lucro_para_stable

logger = logging.getLogger('estrategista')

class EstrategistaBot:
    def __init__(self, config):
        self.config = config
        self.open_positions = set()
        self.executor = None
        self.gestor = GestorFinanceiro()
        self.trava_dia_encerrado = False
        
        # --- NOVO: Configurações de Meta vindas do settings.json ---
        self.meta_target = config.get('config_geral', {}).get('meta_diaria_total_usdt', 25.0)
        self.banca_ref = config.get('banca_referencia_usdt', 1870.00)

    def set_executor(self, executor):
        """Conecta o executor para permitir vendas automáticas."""
        self.executor = executor

    async def iniciar_dia_trading(self):
        """Reset diário e snapshot da banca."""
        await asyncio.to_thread(self.gestor.registrar_inicio_dia, self.banca_ref)
        self.trava_dia_encerrado = False
        # Zera estado de lucro local para cálculo percentual
        self._lucro_hoje_cache = 0.0
        logger.info(f"🌅 Ciclo Iniciado | Meta: ${self.meta_target} | Banca Ref: ${self.banca_ref}")

    async def analisar_tendencia(self, symbol, preco_atual):
        """
        Analisa se o sistema ainda pode operar baseado no lucro do dia.
        Usa percentuais relativos à `banca_ref` para tomada de decisão.
        """
        if self.trava_dia_encerrado:
            return False

        # Consulta status real do gestor financeiro (retorna lucro em USDT)
        status = await asyncio.to_thread(self.gestor.status_atual)
        lucro_hoje = status.get('lucro_hoje', 0.0)
        self._lucro_hoje_cache = lucro_hoje
        
        # Log do status de meta para debug
        meta_batida = status.get('meta_batida', False)
        progresso = status.get('progresso_pct', 0.0)
        logger.info(f"📊 Status Meta | Lucro: ${lucro_hoje:.2f} | Meta: ${status.get('meta_diaria', 25.0):.2f} | Progresso: {progresso:.1f}% | Batida: {meta_batida}")

        # Calcula lucro em percentagem sobre a banca de referência
        try:
            lucro_pct = (lucro_hoje / float(self.banca_ref)) * 100.0
        except Exception:
            lucro_pct = 0.0

        # Limiares em percentuais - DESATIVADOS para bot nunca parar
        # meta_super_pct = 1.5   # 1.5%
        # meta_segura_pct = 1.0  # 1.0%
        # trava_recuo_pct = 0.8  # 0.8%

        # 1. BLOQUEIO: Meta Super Atingida - DESATIVADO
        # if lucro_pct >= meta_super_pct:
        #     await self.finalizar_e_converter(f"Super Meta Batida: {lucro_pct:.2f}% (${lucro_hoje:.2f})")
        #     return False

        # 2. PROTEÇÃO DE LUCRO - DESATIVADA
        # if lucro_pct >= trava_recuo_pct and lucro_pct < meta_segura_pct:
        #     await self.finalizar_e_converter(f"Proteção de Lucro Ativada: {lucro_pct:.2f}% (${lucro_hoje:.2f})")
        #     return False

        # 3. VERIFICAÇÃO DE DUPLICIDADE
        if symbol in self.open_positions:
            return False

        return True

    async def finalizar_e_converter(self, motivo):
        """Ação de encerramento total e proteção em Stablecoin."""
        if self.trava_dia_encerrado: return
        
        self.trava_dia_encerrado = True
        logger.info(f"🛑 [FINALIZANDO DIA] Motivo: {motivo}")
        
        try:
            # 1. Tenta converter via ferramenta externa
            api_key = os.getenv('BINANCE_API_KEY')
            secret = os.getenv('BINANCE_SECRET_KEY')
            await asyncio.to_thread(converter_lucro_para_stable, api_key, secret)
            
            # 2. Envia relatório para o Telegram
            if self.executor and self.executor.comunicador:
                msg = f"🏆 *R7_V3 Sniper Encerrado*\n🎯 Motivo: {motivo}\n💰 Saldo Protegido em USDT."
                await self.executor.comunicador._enviar(msg)
        except Exception as e:
            logger.error(f"Falha na conversão automática: {e}")

    # --- MÉTODOS DE APOIO AO SNIPER ---

    def registrar_pnl(self, pair, pnl_liquido, estrategia):
        """Callback do Executor: Registra PnL de cada trade fechado."""
        logger.info(f"📈 {pair} | PnL: ${pnl_liquido:.2f} | Estratégia: {estrategia}")
        # Delega para o gestor financeiro rastrear lucros por estratégia
        try:
            asyncio.create_task(self._registrar_pnl_async(pair, pnl_liquido, estrategia))
        except Exception as e:
            logger.error(f"Erro ao registrar PnL: {e}")

    async def _registrar_pnl_async(self, pair, pnl_liquido, estrategia):
        """Versão async para registrar PnL e rastrear por estratégia."""
        # 1. Atualiza PnL geral
        await asyncio.to_thread(
            self.gestor.atualizar_pnl_trade, 
            pnl_liquido
        )
        # 2. Rastreia PnL por estratégia (BOT)
        from bots.monthly_stats import add_profit_by_strategy
        await asyncio.to_thread(
            add_profit_by_strategy,
            pnl_liquido,
            estrategia
        )

    def mark_position_open(self, symbol):
        self.open_positions.add(symbol)

    async def mark_position_closed(self, symbol, pnl):
        """Libera a moeda para novos trades e atualiza o financeiro."""
        if symbol in self.open_positions:
            self.open_positions.remove(symbol)
        # Atualiza o gestor para que o próximo tick já leia o lucro novo
        await asyncio.to_thread(self.gestor.atualizar_pnl_trade, pnl)

    async def calcular_position_size(self, prices, saldo, risco_pct=0.01):
        """Calcula lote baseado na volatilidade real do ativo."""
        vol = await asyncio.to_thread(calculate_volatility, prices)
        if vol <= 0: return 0
        return max(0, (saldo * risco_pct) / vol)