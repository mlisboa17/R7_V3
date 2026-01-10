import json
import os
import logging
from datetime import datetime

logger = logging.getLogger('gestor')

class GestorFinanceiro:
    def __init__(self):
        self.path_config = 'config/settings.json'
        self.path_stats = 'data/financial_master.json'  # ✅ Usando arquivo MASTER consolidado
        
        # 1. Carrega configurações para meta e banca base
        config = self._carregar_config_raiz()
        self.banca_referencia_config = config.get('banca_referencia_usdt', 2152.00)
        self.meta_diaria_alvo = config.get('config_geral', {}).get('meta_diaria_total_usdt', 30.00)
        
        # Garante estrutura de pastas
        os.makedirs('data', exist_ok=True)
        self.dados = self._carregar_dados()

    def _carregar_config_raiz(self):
        """Lê o settings.json para alinhar metas e banca."""
        try:
            if os.path.exists(self.path_config):
                with open(self.path_config, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler settings.json: {e}")
        return {}

    def _carregar_dados(self):
        """Carrega o histórico de lucros e saldos iniciais do arquivo MASTER."""
        if os.path.exists(self.path_stats):
            try:
                with open(self.path_stats, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Adapta schema do MASTER para compatibilidade
                    return {
                        "lucro_acumulado_mes": data.get('lucros', {}).get('lucro_acumulado_mes', 0.0),
                        "trades_realizados_mes": data.get('estatisticas_mes', {}).get('total_trades', 0),
                        "dias": data.get('historico_diario', {})
                    }
            except Exception as e:
                logger.error(f"Erro ao ler financial_master.json: {e}")
        
        return {
            "lucro_acumulado_mes": 0.0,
            "trades_realizados_mes": 0,
            "dias": {}
        }

    def registrar_inicio_dia(self, saldo_inicial_banca):
        """
        Registra o início do dia usando APENAS o saldo Spot confirmado.
        Ignora o parâmetro banca_ref se a data já foi inicializada.
        """
        hoje = datetime.now().strftime("%Y-%m-%d")
        
        if hoje not in self.dados["dias"]:
            self.dados["dias"][hoje] = {
                "saldo_inicial": saldo_inicial_banca,
                "lucro_do_dia": 0.0,
                "trades": 0
            }
            logger.info(f"🌅 Dia Iniciado (Spot Only) | Saldo Inicial: ${saldo_inicial_banca:.2f}")
            self._salvar()

    def registrar_snapshot_momento(self, saldo_total, saldo_spot=0.0, saldo_earn=0.0, saldo_cripto=0.0):
        """
        LÓGICA SNIPER: Calcula o lucro real por Delta de Saldo.
        saldo_total: SPOT + EARN + CRIPTO
        saldo_spot: USDT disponível para trading
        saldo_earn: USDT em Earn/Staking
        saldo_cripto: Valor em outras criptomoedas
        """
        hoje = datetime.now().strftime("%Y-%m-%d")
        
        # Se for o primeiro registro do dia, define o Saldo Inicial Real com campos separados
        if hoje not in self.dados["dias"]:
            self.dados["dias"][hoje] = {
                "saldo_inicial": saldo_total,
                "saldo_spot": saldo_spot,
                "saldo_earn": saldo_earn,
                "saldo_cripto": saldo_cripto,
                "lucro_do_dia": 0.0,
                "trades": 0
            }
            logger.info(f"🌅 Saldo Inicial do Dia Registrado: ${saldo_total:.2f} (Spot: ${saldo_spot:.2f}, Earn: ${saldo_earn:.2f}, Cripto: ${saldo_cripto:.2f})")

        # Cálculo Dinâmico: Diferença absoluta de patrimônio
        saldo_inicial = self.dados["dias"][hoje]["saldo_inicial"]
        lucro_real_hoje = saldo_total - saldo_inicial
        
        # Atualiza com campos atualizados
        self.dados["dias"][hoje]["lucro_do_dia"] = round(lucro_real_hoje, 2)
        self.dados["dias"][hoje]["saldo_spot"] = saldo_spot
        self.dados["dias"][hoje]["saldo_earn"] = saldo_earn
        self.dados["dias"][hoje]["saldo_cripto"] = saldo_cripto
        self._salvar()
        
        return lucro_real_hoje

    def status_atual(self, saldo_total_agora=None):
        """
        Retorna o cockpit financeiro para o Dashboard e para o Estrategista.
        """
        hoje = datetime.now().strftime("%Y-%m-%d")
        dia = self.dados.get("dias", {}).get(hoje, {})
        
        # Se não passarmos o saldo atual, ele usa o último registrado
        saldo_ref = saldo_total_agora if saldo_total_agora else (dia.get('saldo_inicial', self.banca_referencia_config) + dia.get('lucro_do_dia', 0.0))
        
        lucro_dia = dia.get("lucro_do_dia", 0.0)
        
        return {
            "saldo_final_mes": saldo_ref,
            "lucro_hoje": lucro_dia,
            "meta_diaria": self.meta_diaria_alvo,
            "meta_batida": lucro_dia >= self.meta_diaria_alvo,
            "progresso_pct": round((lucro_dia / self.meta_diaria_alvo) * 100, 1) if lucro_dia > 0 else 0.0,
            "lucro_mes": self.dados.get("lucro_acumulado_mes", 0.0),
            "trades_mes": self.dados.get("trades_realizados_mes", 0)
        }

    def atualizar_pnl_trade(self, pnl):
        """Registra o PnL vindo especificamente de um trade do Sniper."""
        hoje = datetime.now().strftime("%Y-%m-%d")
        if hoje not in self.dados["dias"]:
            # Caso o snapshot ainda não tenha rodado, usamos a banca do config como base
            self.registrar_snapshot_momento(self.banca_referencia_config)

        self.dados["lucro_acumulado_mes"] += pnl
        self.dados["trades_realizados_mes"] += 1
        self._salvar()

    def _salvar(self):
        """Persiste os dados em disco MANTENDO estrutura MASTER."""
        try:
            # Lê estrutura existente para preservar campos MASTER
            if os.path.exists(self.path_stats):
                with open(self.path_stats, 'r', encoding='utf-8') as f:
                    data_completo = json.load(f)
            else:
                data_completo = {}
            
            # Atualiza apenas os campos compatíveis (dias, lucro_acumulado_mes, trades_realizados_mes)
            data_completo["dias"] = self.dados.get("dias", {})
            data_completo["lucro_acumulado_mes"] = self.dados.get("lucro_acumulado_mes", 0.0)
            data_completo["trades_realizados_mes"] = self.dados.get("trades_realizados_mes", 0)
            
            # Mantém estrutura MASTER se existir
            if "saldos" not in data_completo:
                data_completo["saldos"] = {
                    "saldo_inicial_dia": 0.0,
                    "saldo_spot": 0.0,
                    "saldo_earn": 0.0,
                    "saldo_cripto": 0.0,
                    "saldo_atual": 0.0
                }
            
            with open(self.path_stats, 'w', encoding='utf-8') as f:
                json.dump(data_completo, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar financial_master.json: {e}")