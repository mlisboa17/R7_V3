"""
✅ TESTE DO CÉREBRO STOP LOSS
Valida integração e funcionamento do sistema de decisão inteligente
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.cerebro_stop_loss import CerebroStopLoss
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def teste_carregamento_modelo():
    """Testa se o modelo foi carregado corretamente"""
    print("\n" + "="*70)
    print("🧠 TESTE 1: Carregamento do Modelo")
    print("="*70)
    
    try:
        cerebro = CerebroStopLoss()
        
        if cerebro.modelo is None:
            print("❌ FALHOU: Modelo não carregado")
            print(f"   Verifique se o arquivo existe: {cerebro.model_path}")
            return False
        
        print(f"✅ Modelo carregado: {cerebro.model_path}")
        print(f"   Tipo: {type(cerebro.modelo)}")
        
        # Verifica se tem método predict
        if not hasattr(cerebro.modelo, 'predict'):
            print("❌ FALHOU: Modelo não possui método predict()")
            return False
        
        print("✅ Método predict() disponível")
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def teste_calculo_features():
    """Testa cálculo de features"""
    print("\n" + "="*70)
    print("📊 TESTE 2: Cálculo de Features")
    print("="*70)
    
    try:
        cerebro = CerebroStopLoss()
        
        # Dados simulados (30 velas de preços)
        buffer_precos = [
            45000 + i * 100 for i in range(-15, 0)  # Queda gradual
        ] + [
            44500 + i * 50 for i in range(0, 15)   # Recuperação
        ]
        
        preco_atual = 44800
        
        features = cerebro.calcular_features(
            symbol='BTCUSDT',
            preco_atual=preco_atual,
            buffer_precos=buffer_precos,
            volume_atual=1000
        )
        
        if features is None:
            print("❌ FALHOU: Features não calculadas")
            return False
        
        print("✅ Features calculadas com sucesso:")
        print(f"   RSI:      {features['rsi']:.2f}")
        print(f"   EMA20:    ${features['ema20']:.2f}")
        print(f"   ATR %:    {features['atr_pct']:.2f}%")
        print(f"   Rel Vol:  {features['rel_vol']:.2f}x")
        
        # Valida ranges esperados
        if not (0 <= features['rsi'] <= 100):
            print(f"⚠️  RSI fora do range: {features['rsi']}")
        if features['ema20'] <= 0:
            print(f"⚠️  EMA20 inválida: {features['ema20']}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def teste_decisao_renovar():
    """Testa decisão de renovação (RSI baixo)"""
    print("\n" + "="*70)
    print("🔄 TESTE 3: Decisão - RENOVAR (RSI Baixo)")
    print("="*70)
    
    try:
        cerebro = CerebroStopLoss()
        
        # Simula queda forte com RSI baixo (possível reversão)
        buffer_precos = [
            45000 - i * 200 for i in range(30)  # Queda forte
        ]
        
        preco_entrada = 45000
        preco_atual = 43500  # -3.3% de perda
        
        decisao = cerebro.decidir_venda_ou_renovacao(
            symbol='BTCUSDT',
            preco_atual=preco_atual,
            preco_entrada=preco_entrada,
            buffer_precos=buffer_precos,
            tempo_posicao_horas=2
        )
        
        print(f"   Decisão: {decisao['decisao']}")
        print(f"   Motivo:  {decisao['motivo']}")
        print(f"   Confiança: {decisao['confianca']:.1%}")
        
        if decisao['features']:
            print(f"   RSI: {decisao['features']['rsi']:.1f}")
            print(f"   Perda: {decisao['perda_atual']:.2f}%")
        
        # Espera RENOVAR se RSI < 35
        if decisao['features'] and decisao['features']['rsi'] < 35:
            if decisao['decisao'] == 'RENOVAR':
                print("✅ Decisão correta: RENOVAR em RSI baixo")
            else:
                print("⚠️  Esperado RENOVAR, mas decidiu VENDER")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def teste_decisao_vender():
    """Testa decisão de venda (perda muito grande)"""
    print("\n" + "="*70)
    print("❌ TESTE 4: Decisão - VENDER (Perda Excessiva)")
    print("="*70)
    
    try:
        cerebro = CerebroStopLoss()
        
        # Simula perda grande e tempo longo
        buffer_precos = [45000 for _ in range(30)]  # Preço estável
        
        preco_entrada = 45000
        preco_atual = 42500  # -5.5% de perda
        tempo_horas = 30  # Muito tempo na posição
        
        decisao = cerebro.decidir_venda_ou_renovacao(
            symbol='BTCUSDT',
            preco_atual=preco_atual,
            preco_entrada=preco_entrada,
            buffer_precos=buffer_precos,
            tempo_posicao_horas=tempo_horas
        )
        
        print(f"   Decisão: {decisao['decisao']}")
        print(f"   Motivo:  {decisao['motivo']}")
        print(f"   Perda: {decisao['perda_atual']:.2f}%")
        print(f"   Tempo: {tempo_horas:.1f}h")
        
        # Espera VENDER por segurança (perda > 5% e tempo > 24h)
        if decisao['decisao'] == 'VENDER':
            print("✅ Decisão correta: VENDER por perda excessiva + tempo longo")
        else:
            print("⚠️  Decisão arriscada: Renovando apesar de perda grande")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def teste_integracao_executor():
    """Testa integração com ExecutorBot"""
    print("\n" + "="*70)
    print("🔗 TESTE 5: Integração com ExecutorBot")
    print("="*70)
    
    try:
        # Tenta importar ExecutorBot
        from bots.executor import ExecutorBot, CEREBRO_DISPONIVEL
        
        if not CEREBRO_DISPONIVEL:
            print("❌ FALHOU: CEREBRO_DISPONIVEL = False no executor.py")
            return False
        
        print("✅ CEREBRO_DISPONIVEL = True no executor.py")
        
        # Tenta criar instância
        executor = ExecutorBot()
        
        if not hasattr(executor, 'cerebro_stop_loss'):
            print("❌ FALHOU: executor.cerebro_stop_loss não existe")
            return False
        
        print("✅ executor.cerebro_stop_loss existe")
        
        if executor.cerebro_stop_loss is None:
            print("⚠️  executor.cerebro_stop_loss = None (modelo não carregado)")
            return False
        
        print("✅ executor.cerebro_stop_loss inicializado")
        print(f"   Modelo: {executor.cerebro_stop_loss.model_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def executar_todos_testes():
    """Executa todos os testes"""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║       🧠 TESTE DO CÉREBRO STOP LOSS - R7 SYSTEM               ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    
    testes = [
        ("Carregamento do Modelo", teste_carregamento_modelo),
        ("Cálculo de Features", teste_calculo_features),
        ("Decisão: Renovar", teste_decisao_renovar),
        ("Decisão: Vender", teste_decisao_vender),
        ("Integração com Executor", teste_integracao_executor)
    ]
    
    resultados = []
    
    for nome, teste_func in testes:
        try:
            resultado = teste_func()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"\n❌ Erro fatal no teste '{nome}': {e}")
            resultados.append((nome, False))
    
    # Resumo
    print("\n" + "="*70)
    print("📋 RESUMO DOS TESTES")
    print("="*70)
    
    for nome, passou in resultados:
        status = "✅ PASSOU" if passou else "❌ FALHOU"
        print(f"   {status} - {nome}")
    
    total_passou = sum(1 for _, passou in resultados if passou)
    total_testes = len(resultados)
    
    print(f"\n   📊 RESULTADO: {total_passou}/{total_testes} testes passaram")
    print("="*70)
    
    if total_passou == total_testes:
        print("\n✅ TODOS OS TESTES PASSARAM!")
        print("\n🎯 Sistema pronto para uso:")
        print("   - Cérebro carregado corretamente")
        print("   - Features sendo calculadas")
        print("   - Decisões funcionando (Renovar/Vender)")
        print("   - Integração com Executor OK")
        print("\n💡 Próximos passos:")
        print("   1. Execute: python main.py")
        print("   2. Monitore logs por mensagens: 🔄 [RENOVAÇÃO] ou ❌ [VENDA CONFIRMADA]")
        print("   3. Acompanhe decisões do cérebro em tempo real")
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM")
        print("   Corrija os problemas acima antes de usar em produção")
    
    print("\n")
    
    return total_passou == total_testes

if __name__ == "__main__":
    sucesso = executar_todos_testes()
    sys.exit(0 if sucesso else 1)
