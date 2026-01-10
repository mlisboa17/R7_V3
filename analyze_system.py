import json
import os

# Verificar configurações atuais
with open('config/settings.json', 'r') as f:
    config = json.load(f)

entrada_usd = config.get('entrada_usd', 10.0)
banca_ref = config.get('banca_referencia_usdt', 2355.05)

print('💰 ANÁLISE DOS VALORES DE ENTRADA:')
print('=' * 50)
print(f'Entrada por trade: ${entrada_usd:.2f}')
print(f'Banca de referência: ${banca_ref:.2f}')
print(f'Percentual da banca por trade: {(entrada_usd/banca_ref*100):.2f}%')
print()

# Verificar se o valor está baixo
if entrada_usd < 20:
    print('⚠️ VALOR BAIXO DETECTADO!')
    print('Sugestão: Aumentar para $20-50 por trade para melhor rentabilidade')
else:
    print('✅ Valor de entrada adequado')
    
print()
print('📊 CONFIGURAÇÕES DE STOP LOSS:')
print('=' * 50)
print(f"TP: {config.get('config_geral', {}).get('tp_pct', 1.0)}%")
print(f"SL: {config.get('config_geral', {}).get('sl_pct', 0.5)}%")
print()

# Verificar arquivo .env
print('🔧 CONFIGURAÇÕES AVANÇADAS (.env):')
print('=' * 50)
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    position_size = os.getenv('R7_POSITION_SIZE', '2%')
    max_loss = os.getenv('R7_MAX_LOSS_PCT', '5.0')
    safe_margin = os.getenv('R7_SAFE_MARGIN_PCT', '2.0')
    max_hold = os.getenv('R7_MAX_HOLD_HOURS', '48')
    
    print(f'Position Size: {position_size}')
    print(f'Max Loss PCT: {max_loss}%')
    print(f'Safe Margin: {safe_margin}%')
    print(f'Max Hold Hours: {max_hold}h')
    
except Exception as e:
    print(f'Erro carregando .env: {e}')

print()
print('💡 RECOMENDAÇÕES:')
print('=' * 50)
print('1. Para maior rentabilidade, considere aumentar entrada para $25-50')
print('2. Stop Loss atual está conservador (0.5%)')
print('3. Sistema tem proteção máxima de 5% de perda por posição')
print('4. Tempo máximo de 48h evita posições presas')