import logging
import json
import os
from datetime import date
from bots.monthly_stats import add_profit_by_strategy

logger = logging.getLogger('guardiao')

class GuardiaoBot:
    def __init__(self, config):
        self.config = config
        # Meta Fixa baseada no início do mês ($2020)
        self.banca_inicial_mes = 2020.0 
        self.meta_diaria = 20.20 
        self.exposicao_max = 900.0 # Usando a folga dos seus $1000 líquidos
        
        self.lucro_dia = 0.0
        self.load_daily_state()

    def load_daily_state(self):
        path = os.path.join('data', 'daily_state.json')
        hoje = date.today().isoformat()
        
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('date') == hoje:
                    self.lucro_dia = data.get('lucro_acumulado_usdt', 0.0)
                else:
                    self.lucro_dia = 0.0
                    self.reset_dia(hoje)

    def reset_dia(self, hoje):
        data = {
            "date": hoje,
            "lucro_acumulado_usdt": 0.0,
            "meta_objetivo": self.meta_diaria,
            "status": "caçando"
        }
        with open(os.path.join('data', 'daily_state.json'), 'w') as f:
            json.dump(data, f, indent=2)

    def update_lucro_usdt(self, pnl, estrategia):
        self.lucro_dia += pnl
        add_profit_by_strategy(pnl, estrategia) # Salva no histórico mensal
        
        # Atualiza o arquivo diário
        path = os.path.join('data', 'daily_state.json')
        with open(path, 'r') as f:
            data = json.load(f)
        data['lucro_acumulado_usdt'] = self.lucro_dia
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"PnL: ${pnl:.2f} | Total Dia: ${self.lucro_dia:.2f}")

    def validar_operacao(self, executor, estrategia_config=None):
        # 1. Bloqueia se a meta de $20.20 foi batida
        if self.lucro_dia >= self.meta_diaria:
            return False, "Meta diária batida"

        # 2. Bloqueia se a exposição passar de $900
        exposicao_atual = sum(t.get('entrada_usd', 0) for t in executor.active_trades.values())
        if (exposicao_atual + 100) > self.exposicao_max:
            return False, "Limite de exposição atingido"

        return True, "Aprovado"