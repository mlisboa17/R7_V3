import logging
import json
import os
from datetime import date
from bots.gestor_financeiro import GestorFinanceiro

logger = logging.getLogger('guardiao')

class GuardiaoBot:
    def __init__(self, config, executor=None):
        """
        Guardião Sniper R7_V3.
        Monitora metas de $20, stops de $25 e exposição de $120.
        """
        self.config = config
        self.executor = executor
        
        # Sincronização com os saldos hierárquicos
        self.gestor = GestorFinanceiro(meta_diaria=config['config_geral'].get('meta_diaria_total_usdt', 23.11))
        
        # Parâmetros de Segurança
        self.banca_referencia = config.get('banca_referencia_usdt', 1870.00)
        self.exposicao_max = config['config_geral'].get('exposicao_maxima_usdt', 120.0)
        self.stop_loss_diario = -config['config_geral'].get('stop_loss_diario_usdt', 25.0)
        self.meta_diaria = self.gestor.meta_diaria
        
        # Lucro do dia carregado do Gestor
        self.lucro_dia = self.gestor.dados.get("lucro_acumulado_dia", 0.0)

    def update_lucro_usdt(self, pnl, estrategia):
        """Atualiza o lucro e ajusta o rigor da IA se bater a meta de segurança ($10)."""
        self.gestor.atualizar_lucro(pnl, estrategia)
        self.lucro_dia = self.gestor.dados["lucro_acumulado_dia"]
        
        # Meta de Segurança atingida: Aumenta threshold da IA para 0.85 (Sniper Ultra)
        if self.lucro_dia >= 10.0 and self.executor:
            if hasattr(self.executor, 'ia_threshold'):
                self.executor.ia_threshold = 0.85
                logger.info("🛡️ Meta de Segurança ($10) atingida. IA em modo SNIPER (0.85).")

    def validar_operacao(self, active_trades, symbol_ou_sistema="SISTEMA"):
        """A última barreira antes da ordem ser enviada."""
        
        # 1. Trava de Lucro Máximo (Meta batida)
        if self.lucro_dia >= self.meta_diaria:
            return False, f"Meta de ${self.meta_diaria} atingida. Dia encerrado."
        
        # 2. Trava de Stop Loss Diário
        if self.lucro_dia <= self.stop_loss_diario:
            return False, f"Stop Loss Diário de ${abs(self.stop_loss_diario)} atingido."

        # 3. Trava de Exposição Financeira ($120)
        exposicao_atual = sum(t.get('qty', 0) * t.get('entry', 0) for t in active_trades.values())
        if (exposicao_atual + 25.0) > self.exposicao_max:
            return False, f"Exposição máxima de ${self.exposicao_max} atingida."

        # 4. Verificação por Moeda (Evita repetição)
        if symbol_ou_sistema != "SISTEMA":
            pair = f"{symbol_ou_sistema}USDT"
            if pair in active_trades:
                return False, f"Já posicionado em {symbol_ou_sistema}."

        return True, "Aprovado"