import logging
import json
import os
from datetime import date, datetime
# Removi a dependência direta se não for necessária, mas mantive o conceito
# from bots.monthly_stats import add_profit_by_strategy 

logger = logging.getLogger('guardiao')

class GuardiaoBot:
    def __init__(self, config, executor=None):
        self.config = config
        self.executor = executor
        
        # --- AJUSTE DE BANCA E METAS ---
        self.banca_inicial_mes = 2020.0 
        self.meta_diaria = 20.20 
        
        # Ajustado: Se entradas de $25 eram baixas, aumentamos a segurança da exposição
        # Permitindo que o robô tenha margem para gerenciar trades maiores
        self.exposicao_max = 950.0 
        
        # --- CONTROLE FINANCEIRO ---
        self.lucro_dia = 0.0
        
        # 🛡️ PROTEÇÃO ANTI-OVERTRADING
        self.last_trade_time = {}  # {symbol: timestamp}
        self.cooldown_seconds = 120  # 2 minutos entre trades da mesma moeda
        
        self.load_daily_state()

    def load_daily_state(self):
        os.makedirs('data', exist_ok=True)
        path = os.path.join('data', 'financial_master.json')
        hoje = date.today().isoformat()
        
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Lê do novo schema consolidado
                    ultima_atualizacao = data.get('_ultima_atualizacao', '')[:10]
                    if ultima_atualizacao == hoje:
                        self.lucro_dia = data.get('lucros', {}).get('lucro_acumulado_dia', 0.0)
                    else:
                        self.reset_dia(hoje)
            except Exception:
                self.reset_dia(hoje)
        else:
            self.reset_dia(hoje)

    def reset_dia(self, hoje):
        self.lucro_dia = 0.0
        path = os.path.join('data', 'financial_master.json')
        # Lê arquivo MASTER existente ou cria novo com estrutura completa
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        
        # Garante estrutura MASTER completa
        if 'lucros' not in data:
            data['lucros'] = {}
        if 'saldos' not in data:
            data['saldos'] = {
                'saldo_inicial_dia': 0.0,
                'saldo_atual': 0.0,
                'saldo_spot': 0.0,
                'saldo_earn': 0.0,
                'saldo_cripto': 0.0,
                'saldo_bloqueado_trades': 0.0
            }
        if 'metas' not in data:
            data['metas'] = {}
        if 'estatisticas_mes' not in data:
            data['estatisticas_mes'] = {}
        if 'historico_diario' not in data:
            data['historico_diario'] = {}
        
        # Atualiza campos relevantes
        data['_version'] = '1.0'
        data['_ultima_atualizacao'] = f"{hoje}T00:00:00"
        data['lucros']['lucro_acumulado_dia'] = 0.0
        data['metas']['status_meta_dia'] = 'caçando'
        data['metas']['meta_batida'] = False
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def update_lucro_usdt(self, pnl, estrategia):
        """Atualiza o lucro e persiste no JSON MASTER."""
        self.lucro_dia += pnl
        
        path = os.path.join('data', 'financial_master.json')
        try:
            # Lê arquivo MASTER
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            
            # Garante estrutura MASTER completa
            if 'lucros' not in data:
                data['lucros'] = {}
            if 'metas' not in data:
                data['metas'] = {}
            
            # Atualiza lucro do dia
            data['_version'] = '1.0'
            data['lucros']['lucro_acumulado_dia'] = round(self.lucro_dia, 2)
            data['_ultima_atualizacao'] = datetime.now().isoformat()
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"📊 PnL: ${pnl:.2f} | Total Dia: ${self.lucro_dia:.2f} / ${self.meta_diaria}")
        except Exception as e:
            logger.error(f"Erro ao salvar estado diário: {e}")

    def validar_operacao(self, symbol, confianca):
        """
        Validação Sniper Ultra-Segura: Duplicidade e Limite de Trades.
        """
        try:
            logger.info(f"🛡️ Guardião: Validando {symbol} (Conf: {confianca:.2f})")
            
            # 1. Recupera valor de entrada de forma segura
            entrada = 50.0
            if hasattr(self, 'executor') and self.executor:
                entrada = getattr(self.executor, 'entrada_usd', 50.0)
            
            # 🛡️ COOLDOWN: Evita trades muito rápidos da mesma moeda
            import time
            now = time.time()
            if symbol in self.last_trade_time:
                time_since_last = now - self.last_trade_time[symbol]
                if time_since_last < self.cooldown_seconds:
                    logger.warning(f"⏸️ {symbol}: Cooldown ativo ({time_since_last:.0f}s/{self.cooldown_seconds}s)")
                    return False, "COOLDOWN_ATIVO"
            
            # 2. Verifica se já existe trade aberto para a mesma moeda
            # (Isso evita a duplicação que vimos antes)
            if hasattr(self, 'executor') and self.executor and hasattr(self.executor, 'active_trades'):
                if symbol in self.executor.active_trades:
                    logger.warning(f"🚫 {symbol} já possui trade ativo. Abortando.")
                    return False, "MOEDA_JA_ATIVA"
                
                # 3. Regra de Ouro: Exposição Máxima - USO TOTAL DA EXPOSIÇÃO
                # Conta APENAS trades novos (não-legacy) no limite de 10 por bot (100% exposição)
                # ✅ NOVO: Ignora posições < $1
                trades_novos = [t for t in self.executor.active_trades.values() if not t.get('legacy', False)]
                posicoes_significativas = self.executor.contar_posicoes_abertas()  # Conta apenas >= $1
                max_trades_por_bot = self.config['config_geral'].get('max_trades_simultaneos', 10)
                if posicoes_significativas >= max_trades_por_bot:
                    logger.warning(f"🚫 Limite de {max_trades_por_bot} posições significativas atingido ({posicoes_significativas}/{max_trades_por_bot}). Total no dict: {len(self.executor.active_trades)}")
                    return False, "LIMITE_TRADES"
            
            # 🛡️ Registra timestamp para cooldown
            import time
            self.last_trade_time[symbol] = time.time()
            
            logger.info(f"✅ Guardião: Operação para {symbol} APROVADA.")
            return True, "APROVADO"

        except Exception as e:
            logger.error(f"🚨 Erro CRÍTICO dentro do Guardião: {e}")
            return False, "ERRO_GUARDIAO"