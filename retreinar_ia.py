"""
🧠 RETREINAMENTO DA IA COM NOVAS FEATURES
Treina a IA com Order Book e Candlestick patterns e exibe métricas
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ia_engine import IAEngine
import sqlite3
import pandas as pd
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def exibir_metricas_historicas():
    """Exibe histórico de métricas da IA"""
    try:
        conn = sqlite3.connect('memoria_bot.db')
        df = pd.read_sql_query('SELECT * FROM ia_metrics ORDER BY timestamp DESC LIMIT 10', conn)
        conn.close()
        
        if df.empty:
            logger.info("📊 Nenhuma métrica registrada ainda.")
            return
        
        logger.info("\n" + "="*70)
        logger.info("📊 HISTÓRICO DE MÉTRICAS DA IA (últimos 10 treinos)")
        logger.info("="*70)
        
        for idx, row in df.iterrows():
            timestamp = row['timestamp']
            recall = row['recall'] * 100
            precision = row['precision'] * 100
            f1 = row['f1_score'] * 100
            accuracy = row['accuracy'] * 100
            n_samples = int(row['n_samples'])
            
            logger.info(f"\n🗓️  Data: {timestamp}")
            logger.info(f"   📈 Recall:    {recall:.1f}% (identifica {recall:.1f}% das oportunidades)")
            logger.info(f"   🎯 Precision: {precision:.1f}% (acurácia quando prevê)")
            logger.info(f"   ⚖️  F1-Score:  {f1:.1f}% (balanço geral)")
            logger.info(f"   ✅ Accuracy:  {accuracy:.1f}% (acurácia total)")
            logger.info(f"   📚 Amostras:  {n_samples} exemplos")
            
            # Análise qualitativa
            if recall < 60:
                logger.warning(f"   ⚠️  RECALL BAIXO - IA perdendo muitas oportunidades!")
            elif recall >= 70:
                logger.info(f"   ✅ RECALL BOM - IA identificando bem as oportunidades")
            
            if precision < 50:
                logger.warning(f"   ⚠️  PRECISION BAIXA - Muitos alarmes falsos!")
            elif precision >= 65:
                logger.info(f"   ✅ PRECISION BOA - Predições confiáveis")
        
        logger.info("\n" + "="*70 + "\n")
        
    except Exception as e:
        logger.error(f"Erro ao buscar métricas: {e}")

def verificar_dados_treino():
    """Verifica quantidade de dados disponíveis para treino"""
    try:
        conn = sqlite3.connect('memoria_bot.db')
        
        # Dados do banco
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM analises WHERE sucesso IS NOT NULL')
        count_db = cursor.fetchone()[0]
        
        # Dados do CSV
        count_csv = 0
        if os.path.exists('data/historico_ia.csv'):
            df_csv = pd.read_csv('data/historico_ia.csv')
            count_csv = len(df_csv[df_csv['sucesso'].notna()])
        
        total = count_db + count_csv
        
        logger.info("\n" + "="*70)
        logger.info("📚 DADOS DISPONÍVEIS PARA TREINO")
        logger.info("="*70)
        logger.info(f"   💾 Banco de dados: {count_db} registros")
        logger.info(f"   📄 Arquivo CSV:    {count_csv} registros")
        logger.info(f"   📊 TOTAL:          {total} registros")
        
        if total < 50:
            logger.warning(f"\n   ⚠️  POUCOS DADOS! Recomendado: mínimo 100 registros")
            logger.warning(f"   📈 Deixe o bot operar por mais tempo para coletar dados")
        elif total < 100:
            logger.info(f"\n   ⚠️  Dados suficientes, mas mais seria melhor")
        else:
            logger.info(f"\n   ✅ Quantidade boa de dados para treino!")
        
        logger.info("="*70 + "\n")
        
        conn.close()
        return total
        
    except Exception as e:
        logger.error(f"Erro ao verificar dados: {e}")
        return 0

def retreinar_ia():
    """Retreina a IA com as novas features"""
    logger.info("\n" + "="*70)
    logger.info("🧠 INICIANDO RETREINAMENTO DA IA")
    logger.info("="*70)
    logger.info("🆕 Novas features incluídas:")
    logger.info("   📖 Order Book (bid_volume, ask_volume, spread, etc)")
    logger.info("   🕯️  Candlestick Patterns (martelo, pin bar, engulfing, etc)")
    logger.info("="*70 + "\n")
    
    try:
        # Verifica dados disponíveis
        total_dados = verificar_dados_treino()
        
        if total_dados < 10:
            logger.error("❌ ERRO: Dados insuficientes para treino (mínimo 10 registros)")
            return False
        
        # Inicializa IA
        logger.info("🔧 Inicializando IA Engine...")
        ia = IAEngine()
        
        # Treina
        logger.info("🏋️  Treinando modelo...")
        sucesso = ia.train()
        
        if sucesso:
            logger.info("\n" + "="*70)
            logger.info("✅ IA RETREINADA COM SUCESSO!")
            logger.info("="*70)
            logger.info("🎯 Próximos passos:")
            logger.info("   1. Verifique as métricas acima")
            logger.info("   2. Se Recall < 60%, colete mais dados")
            logger.info("   3. Execute o sistema e monitore performance")
            logger.info("="*70 + "\n")
            
            # Exibe métricas históricas
            exibir_metricas_historicas()
            
            return True
        else:
            logger.error("❌ Erro ao treinar IA")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro durante retreinamento: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║         🧠 RETREINAMENTO DA IA - R7 SNIPER SYSTEM               ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print("\n")
    
    # Primeiro exibe métricas antigas (se existirem)
    exibir_metricas_historicas()
    
    # Pergunta se quer retreinar
    resposta = input("🤔 Deseja retreinar a IA agora? (s/n): ").strip().lower()
    
    if resposta == 's':
        sucesso = retreinar_ia()
        
        if sucesso:
            print("\n✅ Processo concluído com sucesso!")
            print("💡 A IA agora possui:")
            print("   - Visão do Order Book (suporte/resistência)")
            print("   - Reconhecimento de padrões de candlestick")
            print("   - Métricas de Recall para monitoramento\n")
        else:
            print("\n❌ Erro durante o retreinamento. Verifique os logs acima.\n")
    else:
        print("\n⏭️  Retreinamento cancelado.\n")
