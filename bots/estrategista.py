import logging
from .gestor_financeiro import GestorFinanceiro

logger = logging.getLogger('estrategista')


class EstrategistaBot:
    def __init__(self, config):
        self.config = config
        self.open_positions = set()
        self.executor = None
        # Sabedoria: Meta fixa diária de 1% sobre os $2020
        # `GestorFinanceiro` aceita opcionalmente o saldo inicial do mês; usa meta interna fixa
        self.gestor = GestorFinanceiro()

    def set_executor(self, executor):
        self.executor = executor

    def iniciar_dia_trading(self):
        """Snapshot para o Dashboard e reset de metas diárias."""
        # Usa a banca de referência do config se disponível
        banca = self.config.get('banca_referencia_usdt', 2020.00) if isinstance(self.config, dict) else 2020.00
        self.gestor.registrar_inicio_dia(banca)
        logger.info(f"Dia iniciado. Meta: ${self.gestor.meta_diaria_fixa}")

    def analisar_tendencia(self, sinal):
        """Valida se o trade deve ser aberto com base na meta batida ou duplicidade."""
        status = self.gestor.status_atual()
        
        # 1. Se a meta de $20.20 já foi batida, não abre mais nada
        if status.get('meta_batida'):
            return False

        # 2. Se já estiver posicionado na mesma moeda, ignora
        if sinal.get('symbol') in self.open_positions:
            return False

        return True

    def mark_position_open(self, symbol):
        self.open_positions.add(symbol)

    def mark_position_closed(self, symbol, pnl):
        if symbol in self.open_positions:
            self.open_positions.remove(symbol)
            # Atualiza o lucro no gestor para controle de meta
            self.gestor.atualizar_lucro(pnl)