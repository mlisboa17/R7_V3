import logging
import asyncio

logger = logging.getLogger('estrategista')

class EstrategistaBot:
    def __init__(self, config):
        self.config = config
        self.executor = None
        self.kill_switch_ativado = False
        self.trava_dia_encerrado = False
        
        # Pega as configurações de risco do JSON
        gestao = config.get('gestao_risco', {})
        self.max_daily_loss = gestao.get('max_loss_pct', 2.5) / 100
        self.meta_diaria_pct = 0.015  # Sua Super Meta de 1.5%
        
        logger.info(f"🚀 Estrategista: Meta 1.5% | Kill Switch em {self.max_daily_loss*100}%")

    def set_executor(self, executor):
        self.executor = executor

    async def iniciar_dia_trading(self):
        """Prepara o bot para o ciclo de 24h (Chamado pelo main.py)."""
        self.kill_switch_ativado = False
        self.trava_dia_encerrado = False
        logger.info("🌅 Novo ciclo de trading iniciado. Metas resetadas.")

    def pode_operar(self):
        """Verifica se o bot está autorizado a abrir novos trades."""
        if self.kill_switch_ativado:
            logger.warning("🚫 Operação negada: Kill Switch ativo.")
            return False
        if self.trava_dia_encerrado:
            logger.warning("🚫 Operação negada: Meta do dia já atingida.")
            return False
        return True

    def verificar_kill_switch(self, banca_atual, saldo_inicial_dia):
        """Verifica prejuízo máximo (Kill Switch) e Lucro Máximo (Meta)."""
        if self.kill_switch_ativado or self.trava_dia_encerrado: 
            return True
            
        # 1. Checagem de Perda
        perda_real = (saldo_inicial_dia - banca_atual) / saldo_inicial_dia
        if perda_real >= self.max_daily_loss:
            logger.critical(f"🚨 LIMITE DE PERDA ATINGIDO ({perda_real:.2%}). PARANDO TUDO.")
            self.kill_switch_ativado = True
            return True
            
        # 2. Checagem de Meta Diária ($27.40 no seu caso)
        lucro_real = (banca_atual - saldo_inicial_dia) / saldo_inicial_dia
        if lucro_real >= self.meta_diaria_pct:
            logger.info(f"💰 META DIÁRIA ATINGIDA ({lucro_real:.2%}). Encerrando por hoje para proteger o lucro!")
            self.trava_dia_encerrado = True
            return True

        return False

    def definir_stops(self, preco_entrada, df, estrategia):
        """Calcula TP/SL usando ATR para evitar 'Stop de Agulhada'"""
        conf = self.config.get('estrategias', {}).get(estrategia, {})
        last = df.iloc[-1]
        
        # Tenta pegar o ATR do indicador, senão usa 1% como fallback
        atr = last.get('atr', preco_entrada * 0.01) 

        # --- LÓGICA DE STOP DINÂMICO ---
        # Stop Loss: 2x a volatilidade do ATR
        sl = round(preco_entrada - (atr * 2), 6)
        
        # Take Profit: Relação 1.5 : 1
        distancia_sl = preco_entrada - sl
        tp = round(preco_entrada + (distancia_sl * 1.5), 6)

        # Validação de segurança do JSON
        sl_minimo = preco_entrada * (1 - (conf.get('sl_pct', 1.0) / 100))
        if sl > sl_minimo: sl = round(sl_minimo, 6)

        return sl, tp

    def aplicar_breakeven(self, preco_entrada, preco_atual, sl_atual):
        """Move o Stop para o preço de entrada (mais taxas) para garantir lucro zero-zero."""
        lucro = (preco_atual - preco_entrada) / preco_entrada
        if lucro >= 0.0040: # +0.4% de lucro
            novo_sl = round(preco_entrada * 1.001, 6) # Entrada + 0.1%
            if novo_sl > sl_atual:
                logger.info(f"🛡️ Breakeven: Risco Zero em {novo_sl}")
                return novo_sl
        return sl_atual