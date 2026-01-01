import json
import os
import logging
import sqlite3
from datetime import date, datetime, timedelta
from bots.monthly_stats import add_profit_by_strategy, mapear_estrategia, set_monthly_balance

logger = logging.getLogger('gestor_financeiro')

class GestorFinanceiro:
    def __init__(self, meta_diaria=25.0, ia=None):
        self.caminho_stats = os.path.join('data', 'financial_stats.json')
        self.caminho_estado = os.path.join('data', 'daily_state.json')
        self.db_path = 'memoria_bot.db'
        self.meta_diaria = meta_diaria
        self.ia = ia  # Referência para a IAEngine
        self.dados = {}
        self._inicializar_estatisticas()

    def _inicializar_estatisticas(self):
        """Carrega dados e verifica se o dia mudou para processar o fechamento."""
        hoje = date.today().isoformat()
        default_stats = {
            "saldo_inicial_geral": 1870.00,
            "saldo_inicial_mes": 1870.00,
            "saldo_inicial_dia": 1870.00,
            "lucro_acumulado_dia": 0.0,
            "trades_hoje": 0,
            "wins_hoje": 0,
            "ultima_atualizacao": hoje,
            "detalhes_bots": {}
        }

        if os.path.exists(self.caminho_stats):
            try:
                with open(self.caminho_stats, 'r', encoding='utf-8') as f:
                    self.dados = json.load(f)
                
                if self.dados.get("ultima_atualizacao") != hoje:
                    # O fechamento de ontem vira o inicial de hoje
                    saldo_ontem = self.dados["saldo_inicial_dia"] + self.dados["lucro_acumulado_dia"]
                    self.registrar_virada_dia(saldo_ontem)
            except Exception as e:
                logger.error(f"Erro ao carregar financial_stats: {e}")
                self.dados = default_stats
        else:
            self.dados = default_stats
            self._salvar_dados()

    def registrar_virada_dia(self, saldo_fechamento_real):
        """Executa o fechamento contábil de ontem e salva no SQL e JSON."""
        ontem = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        hoje = date.today().isoformat()
        
        lucro_final_ontem = round(self.dados.get("lucro_acumulado_dia", 0.0), 2)
        saldo_ini_ontem = self.dados.get("saldo_inicial_dia", 1870.00)

        # 1. Salva no Histórico Mensal (JSON)
        set_monthly_balance(saldo_fechamento_real, report_date=ontem)
        
        # 2. Salva no Banco de Dados SQL (Permanente)
        self._salvar_no_sql(ontem, saldo_ini_ontem, lucro_final_ontem, saldo_fechamento_real)

        # 3. Reset de Variáveis para o novo dia
        self.dados["saldo_inicial_dia"] = round(saldo_fechamento_real, 2)
        self.dados["lucro_acumulado_dia"] = 0.0
        self.dados["trades_hoje"] = 0
        self.dados["wins_hoje"] = 0
        self.dados["detalhes_bots"] = {}
        self.dados["ultima_atualizacao"] = hoje
        
        if hoje.endswith("-01"): # Virada de mês
            self.dados["saldo_inicial_mes"] = round(saldo_fechamento_real, 2)

        self._salvar_dados()
        logger.info(f"🌅 Dia finalizado: {ontem} | PnL: ${lucro_final_ontem} | Saldo: ${saldo_fechamento_real}")

    def atualizar_lucro(self, pnl_liquido, estrategia="IA Sniper Pro"):
        """Registra cada trade e atualiza o estado atual."""
        estrategia_limpa = mapear_estrategia(estrategia)
        
        self.dados["lucro_acumulado_dia"] = round(self.dados["lucro_acumulado_dia"] + pnl_liquido, 2)
        self.dados["trades_hoje"] += 1
        if pnl_liquido > 0: self.dados["wins_hoje"] += 1

        # Detalhes para o Dashboard Consolidado
        if estrategia_limpa not in self.dados["detalhes_bots"]:
            self.dados["detalhes_bots"][estrategia_limpa] = {"pnl": 0.0, "trades": 0, "wins": 0}
        
        bot = self.dados["detalhes_bots"][estrategia_limpa]
        bot["pnl"] = round(bot["pnl"] + pnl_liquido, 2)
        bot["trades"] += 1
        if pnl_liquido > 0: bot["wins"] += 1

        # Registra no monthly_stats.json para tabelas
        add_profit_by_strategy(pnl_liquido, estrategia_limpa)

        self._salvar_dados()
        self._atualizar_estado_diario_json()

    def _salvar_no_sql(self, data_ref, saldo_ini, lucro, saldo_fim):
        """Gravação direta no SQLite para garantir o histórico do Telegram."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO daily_states (data, saldo_ini, lucro_liq, saldo_final)
                VALUES (?, ?, ?, ?)
            """, (data_ref, saldo_ini, lucro, saldo_fim))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erro SQL ao salvar virada de dia: {e}")

    def status_atual(self):
        """Retorna snapshot para o Dashboard e Telegram."""
        lucro = self.dados["lucro_acumulado_dia"]
        wr = (self.dados["wins_hoje"] / self.dados["trades_hoje"]) if self.dados["trades_hoje"] > 0 else 0
        return {
            "saldo_inicial": self.dados["saldo_inicial_dia"],
            "saldo_final": round(self.dados["saldo_inicial_dia"] + lucro, 2),
            "lucro_hoje": round(lucro, 2),
            "trades_hoje": self.dados["trades_hoje"],
            "win_rate_hoje": wr,
            "detalhes_bots": self.dados.get("detalhes_bots", {}),
            "saldo_inicial_mes": self.dados["saldo_inicial_mes"]
        }

    def _salvar_dados(self):
        with open(self.caminho_stats, 'w', encoding='utf-8') as f:
            json.dump(self.dados, f, indent=4)

    def _atualizar_estado_diario_json(self):
        estado = {"date": date.today().isoformat(), "lucro_acumulado_usdt": self.dados["lucro_acumulado_dia"], "meta_diaria": self.meta_diaria}
        with open(self.caminho_estado, 'w', encoding='utf-8') as f:
            json.dump(estado, f, indent=4)