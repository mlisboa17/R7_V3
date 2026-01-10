"""
Análise Completa de Todas as Posições
Verifica todas as moedas na carteira e recomenda ações
"""
import os
from dotenv import load_dotenv
from binance.client import Client
from datetime import datetime

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY') or os.getenv('API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY') or os.getenv('API_SECRET')

if not api_key or not api_secret:
    print("❌ Credenciais não encontradas")
    exit(1)

client = Client(api_key, api_secret)

# Moedas que NÃO devem ser vendidas (essenciais)
PROTEGIDAS = ['USDT', 'BNB', 'FDUSD', 'LDUSDT']

print("="*80)
print("📊 ANÁLISE COMPLETA DA CARTEIRA")
print("="*80)

account = client.get_account()
balances = [b for b in account['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]

print(f"\n💰 Total de ativos encontrados: {len(balances)}")

moedas_para_analisar = []
valor_total = 0

for balance in balances:
    asset = balance['asset']
    free = float(balance['free'])
    locked = float(balance['locked'])
    total = free + locked
    
    if total > 0 and asset not in PROTEGIDAS:
        moedas_para_analisar.append({
            'asset': asset,
            'quantidade': total,
            'free': free,
            'locked': locked
        })

print(f"🔍 Moedas para análise (excluindo protegidas): {len(moedas_para_analisar)}")
print(f"🛡️  Protegidas: {', '.join(PROTEGIDAS)}")

print("\n" + "="*80)
print("ANÁLISE DETALHADA POR MOEDA")
print("="*80)

recomendacoes_venda = []
recomendacoes_manter = []

for moeda in moedas_para_analisar:
    asset = moeda['asset']
    quantidade = moeda['quantidade']
    symbol = f"{asset}USDT"
    
    print(f"\n{'='*80}")
    print(f"🪙 {asset}USDT")
    print(f"{'='*80}")
    
    try:
        # Preço atual
        ticker = client.get_symbol_ticker(symbol=symbol)
        preco_atual = float(ticker['price'])
        valor_usdt = quantidade * preco_atual
        
        print(f"📊 Quantidade: {quantidade:.8f} {asset}")
        print(f"💵 Preço Atual: ${preco_atual:.6f}")
        print(f"💰 Valor Total: ${valor_usdt:.2f} USDT")
        
        valor_total += valor_usdt
        
        # Histórico de trades
        try:
            trades = client.get_my_trades(symbol=symbol, limit=50)
            
            if trades:
                # Filtra apenas compras
                compras = [t for t in trades if t['isBuyer']]
                
                if compras:
                    # Calcula preço médio ponderado
                    soma_custo = sum(float(t['price']) * float(t['qty']) for t in compras)
                    soma_qty = sum(float(t['qty']) for t in compras)
                    preco_medio = soma_custo / soma_qty if soma_qty > 0 else 0
                    
                    # Calcula lucro/prejuízo
                    lucro_pct = ((preco_atual - preco_medio) / preco_medio) * 100
                    lucro_usdt = (preco_atual - preco_medio) * quantidade
                    
                    print(f"📈 Preço Médio de Compra: ${preco_medio:.6f}")
                    print(f"{'='*80}")
                    
                    if lucro_pct > 0:
                        print(f"✅ LUCRO: {lucro_pct:+.2f}% (${lucro_usdt:+.2f} USDT)")
                    else:
                        print(f"❌ PREJUÍZO: {lucro_pct:+.2f}% (${lucro_usdt:+.2f} USDT)")
                    
                    # Última operação
                    ultimo = trades[-1]
                    dt_ultimo = datetime.fromtimestamp(ultimo['time']/1000)
                    dias_desde = (datetime.now() - dt_ultimo).days
                    
                    print(f"🕐 Última operação: {dt_ultimo.strftime('%d/%m/%Y %H:%M')} ({dias_desde} dias atrás)")
                    
                    # RECOMENDAÇÃO
                    print(f"\n{'='*80}")
                    print("🎯 RECOMENDAÇÃO:")
                    print(f"{'='*80}")
                    
                    if lucro_pct >= 2.0:
                        print(f"🟢 VENDER AGORA - Lucro satisfatório de {lucro_pct:.2f}%")
                        recomendacoes_venda.append({
                            'asset': asset,
                            'lucro_pct': lucro_pct,
                            'lucro_usdt': lucro_usdt,
                            'valor': valor_usdt,
                            'motivo': 'Lucro >= 2%'
                        })
                    elif lucro_pct > 0:
                        print(f"🟡 PODE VENDER - Pequeno lucro de {lucro_pct:.2f}% (aguardar mais ganho)")
                        recomendacoes_manter.append({
                            'asset': asset,
                            'lucro_pct': lucro_pct,
                            'valor': valor_usdt,
                            'motivo': 'Lucro pequeno, pode crescer'
                        })
                    elif lucro_pct > -5:
                        print(f"🟠 AGUARDAR - Prejuízo pequeno de {lucro_pct:.2f}% (aguardar recuperação)")
                        recomendacoes_manter.append({
                            'asset': asset,
                            'lucro_pct': lucro_pct,
                            'valor': valor_usdt,
                            'motivo': 'Prejuízo pequeno, aguardar'
                        })
                    else:
                        print(f"🔴 PREJUÍZO ALTO - {lucro_pct:.2f}% (decisão manual necessária)")
                        recomendacoes_manter.append({
                            'asset': asset,
                            'lucro_pct': lucro_pct,
                            'valor': valor_usdt,
                            'motivo': 'Prejuízo alto, avaliar'
                        })
                else:
                    print("ℹ️  Sem histórico de compras registrado")
            else:
                print("ℹ️  Nenhum trade encontrado")
                
        except Exception as e:
            print(f"⚠️  Erro ao buscar histórico: {e}")
            
    except Exception as e:
        print(f"❌ Erro ao processar {asset}: {e}")

# RESUMO FINAL
print("\n" + "="*80)
print("📋 RESUMO E RECOMENDAÇÕES")
print("="*80)

print(f"\n💰 Valor Total em Altcoins: ${valor_total:.2f} USDT")

if recomendacoes_venda:
    print(f"\n🟢 MOEDAS PARA VENDER ({len(recomendacoes_venda)}):")
    print("="*80)
    for rec in sorted(recomendacoes_venda, key=lambda x: x['lucro_pct'], reverse=True):
        print(f"  {rec['asset']:10s} | Lucro: {rec['lucro_pct']:+6.2f}% | ${rec['lucro_usdt']:+8.2f} | Valor: ${rec['valor']:.2f}")
        print(f"             └─ {rec['motivo']}")
else:
    print("\n🟢 Nenhuma moeda com lucro >= 2% para venda imediata")

if recomendacoes_manter:
    print(f"\n🟡 MOEDAS EM MONITORAMENTO ({len(recomendacoes_manter)}):")
    print("="*80)
    for rec in sorted(recomendacoes_manter, key=lambda x: x['lucro_pct'], reverse=True):
        print(f"  {rec['asset']:10s} | {rec['lucro_pct']:+6.2f}% | Valor: ${rec['valor']:.2f}")
        print(f"             └─ {rec['motivo']}")

print("\n" + "="*80)
print("✅ ANÁLISE CONCLUÍDA")
print("="*80)
