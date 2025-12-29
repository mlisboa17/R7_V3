import json
import os
from datetime import datetime

class GestorFinanceiro:
    def __init__(self, banca_inicial_mes=1710.36):
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
        # Salva também em data/saldos_diarios.json para consulta posterior
        try:
            path_saldos = os.path.join(os.path.dirname(self.path_stats), 'saldos_diarios.json')
            if os.path.exists(path_saldos):
                with open(path_saldos, 'r', encoding='utf-8') as f:
                    dados_saldos = json.load(f)
            else:
                dados_saldos = {"dias": {}}
            if hoje not in dados_saldos["dias"]:
                dados_saldos["dias"][hoje] = {"saldo_inicial": saldo_atual}
                with open(path_saldos, 'w', encoding='utf-8') as f:
                    json.dump(dados_saldos, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[AVISO] Não foi possível registrar saldo em saldos_diarios.json: {e}")

    def atualizar_lucro(self, pnl):
        hoje = datetime.now().strftime("%Y-%m-%d")
        self.dados["dias"][hoje]["lucro_do_dia"] += pnl
        self.dados["lucro_acumulado_mes"] += pnl
        self._salvar()

    def status_atual(self):
        hoje = datetime.now().strftime("%Y-%m-%d")
        mes = self.dados.get("mes_referencia", datetime.now().strftime("%Y-%m"))
        dias = self.dados.get("dias", {})
        dia = dias.get(hoje, {})
        # Dados do dia
        saldo_inicial = dia.get("saldo_inicial", 0.0)
        saldo_final = dia.get("saldo_final", saldo_inicial + dia.get("lucro_do_dia", 0.0))
        lucro_dia = dia.get("lucro_do_dia", 0.0)
        trades_hoje = dia.get("trades_realizados", 0)
        trades_vencedores_hoje = dia.get("trades_vencedores", 0)
        win_rate_hoje = (trades_vencedores_hoje / trades_hoje) if trades_hoje else 0.0
        drawdown_hoje = dia.get("drawdown", 0.0)
        # Dados do mês
        saldo_inicial_mes = self.dados.get("banca_inicial_mes", 0.0)
        saldo_final_mes = self.dados.get("saldo_final_mes", saldo_inicial_mes + self.dados.get("lucro_acumulado_mes", 0.0))
        lucro_mes = self.dados.get("lucro_acumulado_mes", 0.0)
        trades_mes = self.dados.get("trades_realizados_mes", 0)
        trades_vencedores_mes = 0
        for d in dias.values():
            trades_vencedores_mes += d.get("trades_vencedores", 0)
        win_rate_mes = (trades_vencedores_mes / trades_mes) if trades_mes else 0.0
        drawdown_mes = self.dados.get("drawdown_mes", 0.0)
        return {
            "meta_batida": lucro_dia >= self.meta_diaria_fixa,
            "lucro_hoje": lucro_dia,
            "saldo_inicial": saldo_inicial,
            "saldo_final": saldo_final,
            "trades_hoje": trades_hoje,
            "win_rate_hoje": win_rate_hoje,
            "drawdown_hoje": drawdown_hoje,
            "saldo_inicial_mes": saldo_inicial_mes,
            "saldo_final_mes": saldo_final_mes,
            "lucro_mes": lucro_mes,
            "trades_mes": trades_mes,
            "win_rate_mes": win_rate_mes,
            "drawdown_mes": drawdown_mes
        }

    def _salvar(self):
        with open(self.path_stats, 'w') as f:
            json.dump(self.dados, f, indent=4)