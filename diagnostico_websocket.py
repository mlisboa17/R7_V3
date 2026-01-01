#!/usr/bin/env python3
"""
Diagnóstico de Conectividade WebSocket para R7_V3
Testa a conexão com Binance WebSocket e identifica problemas
"""

import asyncio
import logging
import time
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_binance_connection(api_key, api_secret):
    """Testa conexão básica com Binance"""
    logger.info("🔌 Testando conexão básica com Binance...")
    try:
        client = await AsyncClient.create(api_key, api_secret)
        account = await client.get_account()
        logger.info("✅ Conexão básica OK")
        await client.close_connection()
        return True
    except Exception as e:
        logger.error(f"❌ Falha na conexão básica: {e}")
        return False

async def test_websocket_connection(api_key, api_secret, symbol="BTCUSDT"):
    """Testa conexão WebSocket com um símbolo específico"""
    logger.info(f"🔌 Testando WebSocket para {symbol}...")

    client = None
    try:
        client = await AsyncClient.create(api_key, api_secret)
        bsm = BinanceSocketManager(client)

        start_time = time.time()
        async with bsm.symbol_ticker_socket(symbol) as stream:
            logger.info(f"✅ WebSocket conectado para {symbol}")

            # Recebe algumas mensagens para testar
            messages_received = 0
            for _ in range(5):
                msg = await asyncio.wait_for(stream.recv(), timeout=10.0)
                if msg and 'c' in msg:
                    messages_received += 1
                    logger.info(f"📨 Mensagem recebida: {symbol} = ${msg['c']}")

            elapsed = time.time() - start_time
            logger.info(f"✅ WebSocket testado com sucesso: {messages_received} mensagens em {elapsed:.1f}s")

        await client.close_connection()
        return True

    except asyncio.TimeoutError:
        logger.error(f"❌ Timeout no WebSocket para {symbol}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro no WebSocket para {symbol}: {e}")
        return False
    finally:
        if client:
            try:
                await client.close_connection()
            except:
                pass

async def test_multiple_symbols(api_key, api_secret, symbols):
    """Testa WebSocket para múltiplos símbolos"""
    logger.info(f"🔌 Testando WebSocket para {len(symbols)} símbolos...")

    results = {}
    for symbol in symbols:
        logger.info(f"📊 Testando {symbol}...")
        success = await test_websocket_connection(api_key, api_secret, symbol)
        results[symbol] = success
        await asyncio.sleep(1)  # Pequena pausa entre testes

    successful = sum(1 for r in results.values() if r)
    logger.info(f"📊 Resultado: {successful}/{len(symbols)} símbolos conectados com sucesso")

    failed_symbols = [s for s, r in results.items() if not r]
    if failed_symbols:
        logger.warning(f"⚠️ Símbolos com falha: {failed_symbols}")

    return results

async def diagnose_network_issues():
    """Diagnóstico básico de problemas de rede"""
    logger.info("🔍 Diagnosticando possíveis problemas de rede...")

    import socket
    import platform

    # Testa conectividade básica
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        logger.info("✅ Conectividade básica com internet OK")
    except:
        logger.error("❌ Sem conectividade com internet")
        return False

    # Testa resolução DNS
    try:
        socket.gethostbyname("api.binance.com")
        logger.info("✅ Resolução DNS OK")
    except:
        logger.error("❌ Falha na resolução DNS para api.binance.com")
        return False

    # Testa conectividade com Binance
    try:
        sock = socket.create_connection(("stream.binance.com", 9443), timeout=5)
        sock.close()
        logger.info("✅ Conectividade com Binance WebSocket OK")
    except:
        logger.error("❌ Falha na conectividade com stream.binance.com:9443")
        return False

    logger.info("✅ Diagnóstico de rede concluído - sem problemas detectados")
    return True

async def main():
    """Função principal do diagnóstico"""
    logger.info("🎯 Iniciando diagnóstico de conectividade R7_V3")
    logger.info("=" * 50)

    # Carrega credenciais
    import os
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET_KEY')

    if not api_key or not api_secret:
        logger.error("❌ Credenciais da Binance não encontradas nas variáveis de ambiente")
        return

    # Testa conectividade de rede
    network_ok = await diagnose_network_issues()
    if not network_ok:
        logger.error("❌ Problemas de rede detectados. Verifique sua conexão.")
        return

    # Testa conexão básica
    basic_ok = await test_binance_connection(api_key, api_secret)
    if not basic_ok:
        logger.error("❌ Conexão básica com Binance falhou. Verifique suas credenciais.")
        return

    # Testa WebSocket
    symbols_to_test = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
    websocket_results = await test_multiple_symbols(api_key, api_secret, symbols_to_test)

    # Resumo final
    logger.info("=" * 50)
    logger.info("📋 RESUMO DO DIAGNÓSTICO:")

    successful_connections = sum(1 for r in websocket_results.values() if r)
    total_symbols = len(websocket_results)

    if successful_connections == total_symbols:
        logger.info("✅ TODOS os testes passaram! WebSocket funcionando perfeitamente.")
    else:
        logger.warning(f"⚠️ {successful_connections}/{total_symbols} conexões WebSocket bem-sucedidas.")
        logger.info("💡 Possíveis causas de problemas:")
        logger.info("   - Firewall bloqueando conexões WebSocket")
        logger.info("   - Proxy/VPN interferindo")
        logger.info("   - Limitações do provedor de internet")
        logger.info("   - Rate limiting da Binance")
        logger.info("   - Problemas temporários da Binance")

    logger.info("🎯 Diagnóstico concluído!")

if __name__ == "__main__":
    asyncio.run(main())