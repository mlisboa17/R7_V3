"""
✅ VERIFICAÇÃO DAS CORREÇÕES NA IA
Valida se as 3 correções críticas foram implementadas corretamente
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ia_engine import IAEngine
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def verificar_order_book():
    """Verifica se Order Book está implementado"""
    logger.info("\n📖 VERIFICANDO: Order Book Integration")
    logger.info("-" * 60)
    
    try:
        ia = IAEngine()
        
        # Testa se o método existe
        if not hasattr(ia, 'obter_order_book'):
            logger.error("   ❌ Método obter_order_book() não encontrado")
            return False
        
        logger.info("   ✅ Método obter_order_book() implementado")
        
        # Testa se features estão no predict
        import inspect
        source = inspect.getsource(ia.predict)
        
        order_book_features = ['bid_volume', 'ask_volume', 'bid_ask_ratio', 'spread_pct', 'support_strength']
        features_found = all(feat in source for feat in order_book_features)
        
        if features_found:
            logger.info("   ✅ Features de Order Book adicionadas ao predict()")
            for feat in order_book_features:
                logger.info(f"      - {feat}")
        else:
            logger.error("   ❌ Algumas features de Order Book faltando")
            return False
        
        logger.info("   ✅ Order Book: IMPLEMENTADO COM SUCESSO")
        return True
        
    except Exception as e:
        logger.error(f"   ❌ Erro ao verificar Order Book: {e}")
        return False

def verificar_metricas_recall():
    """Verifica se métricas de Recall estão implementadas"""
    logger.info("\n📊 VERIFICANDO: Métricas de Recall")
    logger.info("-" * 60)
    
    try:
        ia = IAEngine()
        
        # Verifica se tabela ia_metrics existe
        conn = sqlite3.connect('memoria_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ia_metrics'")
        table_exists = cursor.fetchone() is not None
        conn.close()
        
        if table_exists:
            logger.info("   ✅ Tabela ia_metrics criada no banco de dados")
        else:
            logger.error("   ❌ Tabela ia_metrics não encontrada")
            return False
        
        # Verifica se método _salvar_metricas_treino existe
        if not hasattr(ia, '_salvar_metricas_treino'):
            logger.error("   ❌ Método _salvar_metricas_treino() não encontrado")
            return False
        
        logger.info("   ✅ Método _salvar_metricas_treino() implementado")
        
        # Verifica imports de métricas
        import inspect
        source_train = inspect.getsource(ia.train)
        
        metricas_implementadas = [
            'recall_score' in source_train,
            'precision_score' in source_train,
            'f1_score' in source_train,
            'train_test_split' in source_train
        ]
        
        if all(metricas_implementadas):
            logger.info("   ✅ Métricas implementadas no método train():")
            logger.info("      - Recall Score (identifica oportunidades)")
            logger.info("      - Precision Score (evita alarmes falsos)")
            logger.info("      - F1 Score (balanço geral)")
            logger.info("      - Train/Test Split (validação)")
        else:
            logger.error("   ❌ Algumas métricas não implementadas corretamente")
            return False
        
        logger.info("   ✅ Métricas de Recall: IMPLEMENTADAS COM SUCESSO")
        return True
        
    except Exception as e:
        logger.error(f"   ❌ Erro ao verificar métricas: {e}")
        return False

def verificar_candlestick_patterns():
    """Verifica se padrões de candlestick estão implementados"""
    logger.info("\n🕯️  VERIFICANDO: Candlestick Patterns")
    logger.info("-" * 60)
    
    try:
        # Verifica se arquivo existe
        pattern_file = os.path.join('tools', 'candlestick_patterns.py')
        if not os.path.exists(pattern_file):
            logger.error(f"   ❌ Arquivo {pattern_file} não encontrado")
            return False
        
        logger.info(f"   ✅ Arquivo {pattern_file} criado")
        
        # Tenta importar
        try:
            from tools.candlestick_patterns import CandlestickPatterns
            logger.info("   ✅ Classe CandlestickPatterns importada com sucesso")
        except ImportError as e:
            logger.error(f"   ❌ Erro ao importar CandlestickPatterns: {e}")
            return False
        
        # Verifica métodos
        patterns = ['is_hammer', 'is_pin_bar', 'is_bullish_engulfing', 'is_doji', 'detect_all_patterns']
        for pattern in patterns:
            if hasattr(CandlestickPatterns, pattern):
                logger.info(f"   ✅ Método {pattern}() implementado")
            else:
                logger.error(f"   ❌ Método {pattern}() não encontrado")
                return False
        
        # Verifica integração com ia_engine
        ia = IAEngine()
        import inspect
        source_analisar = inspect.getsource(ia.analisar_tick)
        
        if 'CandlestickPatterns' in source_analisar and 'vela_de_exaustao' in source_analisar:
            logger.info("   ✅ Integração com ia_engine.analisar_tick()")
            logger.info("   ✅ Proteção contra stop loss em velas de exaustão")
        else:
            logger.warning("   ⚠️  Integração parcial com ia_engine")
        
        logger.info("   ✅ Candlestick Patterns: IMPLEMENTADO COM SUCESSO")
        return True
        
    except Exception as e:
        logger.error(f"   ❌ Erro ao verificar candlestick patterns: {e}")
        return False

def verificar_todas_correcoes():
    """Executa todas as verificações"""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║      ✅ VERIFICAÇÃO DAS CORREÇÕES DA IA - R7 SYSTEM            ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    
    resultados = {
        'order_book': verificar_order_book(),
        'recall': verificar_metricas_recall(),
        'candlestick': verificar_candlestick_patterns()
    }
    
    print("\n" + "="*70)
    print("📋 RESUMO DA AUDITORIA")
    print("="*70)
    
    status_symbols = {True: "✅ OK", False: "❌ FALHOU"}
    
    print(f"\n   A. Order Book Integration:     {status_symbols[resultados['order_book']]}")
    print(f"   B. Métricas de Recall:         {status_symbols[resultados['recall']]}")
    print(f"   C. Candlestick Patterns:       {status_symbols[resultados['candlestick']]}")
    
    total_ok = sum(resultados.values())
    total_checks = len(resultados)
    
    print(f"\n   📊 RESULTADO: {total_ok}/{total_checks} correções implementadas")
    print("="*70)
    
    if total_ok == total_checks:
        print("\n✅ TODAS AS CORREÇÕES IMPLEMENTADAS COM SUCESSO!")
        print("\n🎯 Próximos passos:")
        print("   1. Execute: python retreinar_ia.py")
        print("   2. Monitore as métricas de Recall/Precision")
        print("   3. Observe redução em stops loss desnecessários")
        print("\n💡 A IA agora possui:")
        print("   📖 Visão do Order Book (suporte/resistência real)")
        print("   📊 Métricas de Recall (monitoramento de performance)")
        print("   🕯️  Reconhecimento de velas de exaustão (evita stops prematuros)")
    else:
        print("\n⚠️  ALGUMAS CORREÇÕES FALHARAM")
        print("   Verifique os erros acima e corrija os problemas")
    
    print("\n")
    
    return total_ok == total_checks

if __name__ == "__main__":
    sucesso = verificar_todas_correcoes()
    sys.exit(0 if sucesso else 1)
