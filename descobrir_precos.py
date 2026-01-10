"""
🔍 SCRIPT DE DESCOBERTA AUTOMÁTICA DE PREÇOS
Busca na Binance os preços reais de compra para MAGIC, POLU e outras moedas.
"""
import asyncio
import json
import os
from binance import AsyncClient
from dotenv import load_dotenv

async def descobrir_precos():
    load_dotenv()
    
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET_KEY')
    
    print("🔍 Conectando na Binance...")
    client = await AsyncClient.create(api_key, api_secret)
    
    # Moedas para verificar
    symbols = ['MAGICUSDT', 'POLUSDT', 'POLOUSDT', 'MATICUSDT']
    
    precos_encontrados = {}
    
    print("\n📊 Buscando histórico de trades...\n")
    
    for symbol in symbols:
        try:
            print(f"🔎 Verificando {symbol}...")
            
            # Busca os últimos 50 trades (mais profundo)
            trades = await client.get_my_trades(symbol=symbol, limit=50)
            
            if trades:
                # Pega o último trade de COMPRA (side = BUY)
                buy_trades = [t for t in trades if t['isBuyer']]
                
                if buy_trades:
                    last_buy = buy_trades[-1]  # Último trade de compra
                    preco = float(last_buy['price'])
                    qty = float(last_buy['qty'])
                    time = last_buy['time']
                    
                    # Converte timestamp para data
                    from datetime import datetime
                    data = datetime.fromtimestamp(time / 1000).strftime('%Y-%m-%d %H:%M')
                    
                    precos_encontrados[symbol] = preco
                    
                    print(f"✅ {symbol}: ${preco:.6f}")
                    print(f"   📅 Data: {data}")
                    print(f"   📦 Quantidade: {qty:.4f}")
                    print(f"   💰 Valor: ${preco * qty:.2f}\n")
                else:
                    print(f"⚠️  {symbol}: Sem trades de COMPRA no histórico\n")
            else:
                print(f"⚠️  {symbol}: Sem histórico de trades\n")
                
        except Exception as e:
            if "Invalid symbol" in str(e):
                print(f"❌ {symbol}: Símbolo não existe na Binance\n")
            else:
                print(f"❌ {symbol}: Erro - {e}\n")
    
    await client.close_connection()
    
    # Salva os preços encontrados
    if precos_encontrados:
        config_path = 'config/precos_custo.json'
        
        # Lê arquivo existente se houver
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Atualiza com preços encontrados (sem sobrescrever manualmente configurados)
        for symbol, preco in precos_encontrados.items():
            if symbol not in config or config.get(symbol, 0) == 0.0:
                config[symbol] = preco
        
        # Remove comentários se existirem
        config = {k: v for k, v in config.items() if not k.startswith('_')}
        
        # Salva
        os.makedirs('config', exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("="*60)
        print("✅ ARQUIVO ATUALIZADO: config/precos_custo.json")
        print("="*60)
        print(json.dumps(config, indent=2))
        print("\n🚀 Agora você pode reiniciar o sistema: python .\\main.py")
    else:
        print("⚠️  Nenhum preço foi encontrado. Verifique se você tem trades dessas moedas.")

if __name__ == "__main__":
    print("="*60)
    print("🔍 DESCOBRIDOR AUTOMÁTICO DE PREÇOS DE COMPRA")
    print("="*60)
    asyncio.run(descobrir_precos())
