import os
import sys
import logging
import asyncio
import json
import pandas as pd
from dotenv import load_dotenv
from binance import AsyncClient

# --- AJUSTE DE PATH (Evita erro 'No module named ia_engine') ---
diretorio_raiz = os.path.dirname(os.path.abspath(__file__))
if diretorio_raiz not in sys.path:
    sys.path.append(diretorio_raiz)

# --- Módulos R7_V3 ---
from bots.analista import AnalistaBot
from bots.executor import ExecutorBot
from bots.estrategista import EstrategistaBot
from bots.guardiao import GuardiaoBot
from bots.comunicador import ComunicadorBot
from tools.account_monitor import AccountMonitor
from sniper_monitor import SniperMonitor
from tools.lock_notifier import LockNotifier

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('R7_V3_MAIN')

def load_config():
    """Carrega as configurações do settings.json e injeta preços de custo."""
    path = os.path.join(os.path.dirname(__file__), 'config', 'settings.json')
    
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT', 
        'XRPUSDT', 'DOTUSDT', 'LINKUSDT', 'AVAXUSDT', 'POLUSDT',
        'LTCUSDT', 'NEARUSDT', 'ATOMUSDT', 'FETUSDT', 'RENDERUSDT'
    ]

    precos_manuais = {
        "SOLUSDT": 0.0,
        "BTCUSDT": 0.0,
        "ETHUSDT": 0.0,
        "GICLEUSDT": 68.35 
    }

    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Garante que os símbolos e preços manuais estejam sincronizados
            config['config_geral']['symbols_monitorados'] = symbols
            config['precos_custo'] = precos_manuais
            return config
            
    # Fallback caso o arquivo não exista
    return {
        "banca_referencia_usdt": 2152.00,
        "precos_custo": precos_manuais,
        "entrada_usd": 50.0,
        "config_geral": {
            "meta_diaria_total_usdt": 30.00,
            "exposicao_maxima_usdt": 2200.0,
            "symbols_monitorados": symbols
        }
    }

async def iniciar_sistema():
    logger.info("⚡ R7_V3: INICIANDO MODO SNIPER (ZERO LATÊNCIA)")
    
    load_dotenv()
    config = load_config()
    
    # 1. Conexão Binance com Retry
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET_KEY')
    
    client = None
    for i in range(3):
        try:
            client = await AsyncClient.create(api_key, api_secret)
            break
        except Exception as e:
            if i == 2: raise e
            logger.warning(f"⚠️ Falha na conexão (tentativa {i+1}/3). Reentando em 5s...")
            await asyncio.sleep(5)
    
    try:
        # 2. Inicialização do Monitor de Conta (Dinâmico)
        monitor = AccountMonitor(client)
        asyncio.create_task(monitor.monitor_loop())
        
        # 3. Módulos de Decisão e Execução
        estrategista = EstrategistaBot(config)
        executor = ExecutorBot(config, monitor=monitor)
        
        # 4. Treino da IA
        logger.info("🧠 IA: Sincronizando motor com padrões de mercado...")
        await asyncio.to_thread(executor.ia.train)
        
        # 5. Segurança e Analista
        analista = AnalistaBot(config, client=client, ia=executor.ia)
        estrategista.set_executor(executor)
        guardiao = GuardiaoBot(config, executor=executor)

        # Inicia o LockNotifier logo após o Guardião (apenas leitura/notificações)
        notifier = LockNotifier(guardiao, estrategista, executor)
        asyncio.create_task(notifier.monitor_loop())

        # 6. Gestão de Carteira Existente
        logger.info("🛡️ Assumindo carteira atual (Critério: Lucro 1.5%)...")
        await executor.assumir_e_gerenciar_carteira()

        # 7. Telegram
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if token and chat_id:
            comunicador = ComunicadorBot(token, chat_id, config, guardiao, executor, estrategista)
            asyncio.create_task(asyncio.to_thread(comunicador.start_polling))
            logger.info("📱 Telegram ativo.")

        # 8. Início do Ciclo e Sniper
        await estrategista.iniciar_dia_trading()
        
        sniper = SniperMonitor(
            symbols=config['config_geral']['symbols_monitorados'],
            ia=executor.ia,
            executor=executor,
            analista=analista,
            guardiao=guardiao,
            estrategista=estrategista
        )

        logger.info(f"🎯 Sniper R7_V3 ativo em {len(config['config_geral']['symbols_monitorados'])} moedas.")
        await sniper.iniciar_sniper(api_key, api_secret)

    except Exception as e:
        logger.error(f"🚨 Erro Crítico: {e}")
    finally:
        if client:
            await client.close_connection()
            logger.info("🔌 Conexão Binance encerrada.")

if __name__ == "__main__":
    try:
        asyncio.run(iniciar_sistema())
    except KeyboardInterrupt:
        logger.info("🛑 Sniper interrompido pelo usuário.")