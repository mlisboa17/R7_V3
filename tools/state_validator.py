"""
🛡️ Validador de Consistência de Estado
Detecta e previne corrupção de arquivos financeiros
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('state_validator')


class StateValidator:
    """Valida consistência entre arquivos de estado financeiro."""
    
    def __init__(self):
        self.path_financeiro = 'data/financeiro_stats.json'
        self.path_financial = 'data/financial_stats.json'
        self.path_daily = 'data/daily_state.json'
        self.path_locks = 'data/locks_status.json'
    
    def validar_consistencia(self):
        """Valida sincronização entre todos os arquivos de estado."""
        try:
            hoje = datetime.now().strftime("%Y-%m-%d")
            
            # Carregar todos os arquivos
            financeiro = self._carregar_json(self.path_financeiro)
            financial = self._carregar_json(self.path_financial)
            daily = self._carregar_json(self.path_daily)
            locks = self._carregar_json(self.path_locks)
            
            # Extrair valores
            lucro_financeiro = financeiro.get('dias', {}).get(hoje, {}).get('lucro_do_dia', 0.0)
            lucro_financial = financial.get('lucro_acumulado_dia', 0.0)
            lucro_daily = daily.get('lucro_acumulado_usdt', 0.0)
            
            # Verificar discrepâncias
            erros = []
            
            # 1. Verificar se lucro está dentro do esperado
            if lucro_financeiro < -10.0:  # Mais que -10 USD sem explicação
                erros.append(f"⚠️ Lucro negativamente anormal: ${lucro_financeiro:.2f}")
            
            # 2. Verificar inconsistência entre arquivos
            if abs(lucro_financeiro - lucro_financial) > 0.1:
                erros.append(
                    f"⚠️ Inconsistência entre financeiro_stats ({lucro_financeiro:.2f}) "
                    f"e financial_stats ({lucro_financial:.2f})"
                )
            
            if abs(lucro_financial - lucro_daily) > 0.1:
                erros.append(
                    f"⚠️ Inconsistência entre financial_stats ({lucro_financial:.2f}) "
                    f"e daily_state ({lucro_daily:.2f})"
                )
            
            # 3. Verificar se há lock anormal
            meta_batida = locks.get('guardiao', {}).get('meta_batida', False)
            trava_dia = locks.get('estrategista', {}).get('trava_dia_encerrado', False)
            
            if trava_dia and lucro_financeiro < 0:
                erros.append(
                    f"⚠️ Sistema travado com lucro negativo (${lucro_financeiro:.2f})"
                )
            
            if meta_batida and lucro_financeiro < 0:
                erros.append(
                    f"⚠️ Meta marcada como batida com lucro negativo (${lucro_financeiro:.2f})"
                )
            
            # 4. Verificar se há trades_realizados = 0 mas lucro != 0
            trades = financeiro.get('dias', {}).get(hoje, {}).get('trades_realizados', 0)
            if trades == 0 and abs(lucro_financeiro) > 0.5:
                erros.append(
                    f"🚨 ESTADO CORRUPTO: {trades} trades mas lucro = ${lucro_financeiro:.2f}"
                )
                return False, erros
            
            if erros:
                logger.warning("⚠️ Problemas de consistência detectados:")
                for erro in erros:
                    logger.warning(f"   {erro}")
                return False, erros
            
            logger.info("✅ Estado financeiro consistente")
            return True, []
            
        except Exception as e:
            logger.error(f"Erro ao validar consistência: {e}")
            return False, [str(e)]
    
    def detectar_estado_corrupto(self):
        """Detecta se estado está corrompido (precisa de cleanup)."""
        try:
            hoje = datetime.now().strftime("%Y-%m-%d")
            financeiro = self._carregar_json(self.path_financeiro)
            
            lucro = financeiro.get('dias', {}).get(hoje, {}).get('lucro_do_dia', 0.0)
            trades = financeiro.get('dias', {}).get(hoje, {}).get('trades_realizados', 0)
            
            # Se lucro muito negativo mas sem trades, está corrupto
            if lucro < -5.0 and trades == 0:
                logger.error(f"🚨 ESTADO CORRUPTO DETECTADO:")
                logger.error(f"   Lucro: ${lucro:.2f}")
                logger.error(f"   Trades: {trades}")
                logger.error(f"   Motivo: Lucro negativo sem trades executados")
                return True
            
            # Se lucro negativo E meta batida, está corrupto
            locks = self._carregar_json(self.path_locks)
            meta_batida = locks.get('guardiao', {}).get('meta_batida', False)
            
            if lucro < 0 and meta_batida:
                logger.error(f"🚨 ESTADO CORRUPTO DETECTADO:")
                logger.error(f"   Lucro: ${lucro:.2f} (negativo)")
                logger.error(f"   Meta batida: {meta_batida}")
                logger.error(f"   Motivo: Meta não pode ser batida com lucro negativo")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao detectar corrupção: {e}")
            return False
    
    def sincronizar_arquivos(self):
        """Força sincronização entre todos os arquivos."""
        try:
            hoje = datetime.now().strftime("%Y-%m-%d")
            
            # Carregar
            financeiro = self._carregar_json(self.path_financeiro)
            lucro = financeiro.get('dias', {}).get(hoje, {}).get('lucro_do_dia', 0.0)
            saldo_inicial = financeiro.get('dias', {}).get(hoje, {}).get('saldo_inicial', 0.0)
            
            # Sincronizar financial_stats
            financial = {
                'saldo_inicial_geral': saldo_inicial,
                'saldo_inicial_mes': saldo_inicial,
                'saldo_inicial_dia': saldo_inicial,
                'lucro_acumulado_dia': lucro,
                'ultima_atualizacao': hoje
            }
            self._salvar_json(self.path_financial, financial)
            
            # Sincronizar daily_state
            daily = {
                'date': hoje,
                'lucro_acumulado_usdt': lucro,
                'meta_objetivo': 30.0,
                'status': 'caçando'
            }
            self._salvar_json(self.path_daily, daily)
            
            logger.info("✅ Arquivos sincronizados")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar: {e}")
            return False
    
    def _carregar_json(self, path):
        """Carrega JSON com tratamento de erro."""
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao ler {path}: {e}")
        return {}
    
    def _salvar_json(self, path, dados):
        """Salva JSON com tratamento de erro."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar {path}: {e}")
            return False
    
    def relatorio_completo(self):
        """Gera relatório de saúde completo."""
        try:
            hoje = datetime.now().strftime("%Y-%m-%d")
            
            print("\n" + "=" * 70)
            print("📊 RELATÓRIO DE SAÚDE DO SISTEMA FINANCEIRO")
            print("=" * 70)
            
            # 1. Estado
            print("\n1️⃣ ESTADO FINANCEIRO:")
            financeiro = self._carregar_json(self.path_financeiro)
            dia_info = financeiro.get('dias', {}).get(hoje, {})
            
            print(f"   Saldo Inicial: ${dia_info.get('saldo_inicial', 0):.2f}")
            print(f"   Lucro do Dia: ${dia_info.get('lucro_do_dia', 0):.2f}")
            print(f"   Trades: {dia_info.get('trades_realizados', 0)}")
            
            # 2. Locks
            print("\n2️⃣ STATUS DE LOCKS:")
            locks = self._carregar_json(self.path_locks)
            print(f"   Meta Batida: {locks.get('guardiao', {}).get('meta_batida', False)}")
            print(f"   Trava Dia: {locks.get('estrategista', {}).get('trava_dia_encerrado', False)}")
            
            # 3. Validação
            print("\n3️⃣ VALIDAÇÃO:")
            consistente, erros = self.validar_consistencia()
            if consistente:
                print("   ✅ Arquivos consistentes")
            else:
                print("   ❌ Inconsistências encontradas:")
                for erro in erros:
                    print(f"      {erro}")
            
            # 4. Corrupção
            print("\n4️⃣ DETECÇÃO DE CORRUPÇÃO:")
            if self.detectar_estado_corrupto():
                print("   🚨 ESTADO CORRUPTO - Execute cleanup_trades.py")
            else:
                print("   ✅ Estado íntegro")
            
            print("\n" + "=" * 70 + "\n")
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {e}")
