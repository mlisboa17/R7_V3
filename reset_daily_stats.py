#!/usr/bin/env python3
"""
Script de Reset Diário - Limpa estados travados e reseta para novo dia
NUNCA rode isso manualmente - é automático no inicializador
"""

import json
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('reset_stats')

def reset_stats():
    """Reseta os arquivos de estado para um novo dia limpo."""
    
    # 1. LIMPAR financeiro_stats.json (dados cumulativos)
    financeiro_file = 'data/financeiro_stats.json'
    if os.path.exists(financeiro_file):
        try:
            with open(financeiro_file, 'r') as f:
                dados = json.load(f)
            
            hoje = datetime.now().strftime("%Y-%m-%d")
            
            # Reseta o dia atual, mas mantém histórico anterior
            if "dias" not in dados:
                dados["dias"] = {}
            
            # Remove dia atual se existir com dados ruins
            if hoje in dados["dias"]:
                if dados["dias"][hoje].get("lucro_do_dia", 0) < -10:  # Se teve drawdown ruim
                    logger.info(f"🔄 Removendo dia {hoje} com drawdown negativo")
                    del dados["dias"][hoje]
            
            # Reseta totalizadores de hoje
            dados["lucro_acumulado_mes_hoje"] = 0.0
            dados["trades_realizados_mes_hoje"] = 0
            
            with open(financeiro_file, 'w') as f:
                json.dump(dados, f, indent=4)
            logger.info(f"✅ {financeiro_file} limpo")
        except Exception as e:
            logger.error(f"❌ Erro ao limpar {financeiro_file}: {e}")
    
    # 2. LIMPAR daily_state.json (estado operacional)
    daily_file = 'data/daily_state.json'
    data_reset_daily = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "lucro_acumulado_usdt": 0.0,
        "meta_objetivo": 30.0,
        "status": "caçando",
        "meta_batida": False,
        "stop_loss_atingido": False,
        "banca_inicial_dia": 2355.05
    }
    
    try:
        with open(daily_file, 'w') as f:
            json.dump(data_reset_daily, f, indent=2)
        logger.info(f"✅ {daily_file} resetado")
    except Exception as e:
        logger.error(f"❌ Erro ao limpar {daily_file}: {e}")
    
    # 3. LIMPAR locks_status.json
    locks_file = 'data/locks_status.json'
    data_reset_locks = {
        "timestamp": datetime.now().isoformat(),
        "guardiao": {
            "lucro_dia": 0.0,
            "meta_diaria": 30.0,
            "exposicao_max": 2200.0,
            "exposicao_atual": 0.0,
            "meta_batida": False,
            "limite_exposicao": False
        },
        "estrategista": {
            "trava_dia_encerrado": False,
            "trades_abertos": 0
        }
    }
    
    try:
        with open(locks_file, 'w') as f:
            json.dump(data_reset_locks, f, indent=2)
        logger.info(f"✅ {locks_file} resetado")
    except Exception as e:
        logger.error(f"❌ Erro ao limpar {locks_file}: {e}")
    
    logger.info("=" * 60)
    logger.info("🎯 SISTEMA RESETADO E PRONTO PARA NOVO DIA")
    logger.info("=" * 60)

if __name__ == "__main__":
    reset_stats()
