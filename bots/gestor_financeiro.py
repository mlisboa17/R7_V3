import json
import os
from datetime import datetime

class GestorFinanceiro:
    def __init__(self, banca_inicial_mes=2020.00):
        self.path_stats = 'data/financeiro_stats.json'
        self.meta_diaria_fixa = 20.20 # 1% fixo do mês
        self.dados = self._carregar_dados()

    def _carregar_dados(self):
        if os.path.exists(self.path_stats):
            with open(self.path_stats, 'r') as f:
                return json.load(f)
        return {"lucro_acumulado_mes": 0.0, "dias": {}}

    def registrar_inicio_dia(self, saldo_atual):
        hoje = datetime.now().strftime("%Y-%m-%d")
        if hoje not in self.dados["dias"]:
            self.dados["dias"][hoje] = {"saldo_inicial": saldo_atual, "lucro_do_dia": 0.0}
            self._salvar()

    def atualizar_lucro(self, pnl):
        hoje = datetime.now().strftime("%Y-%m-%d")
        self.dados["dias"][hoje]["lucro_do_dia"] += pnl
        self.dados["lucro_acumulado_mes"] += pnl
        self._salvar()

    def status_atual(self):
        hoje = datetime.now().strftime("%Y-%m-%d")
        dia = self.dados["dias"].get(hoje, {"lucro_do_dia": 0.0})
        return {
            "meta_batida": dia["lucro_do_dia"] >= self.meta_diaria_fixa,
            "lucro_hoje": dia["lucro_do_dia"]
        }

    def _salvar(self):
        with open(self.path_stats, 'w') as f:
            json.dump(self.dados, f, indent=4)