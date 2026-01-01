import os
import logging
import asyncio
import json
import pandas as pd # Importado para evitar NameError global
from dotenv import load_dotenv
from binance import AsyncClient

# --- Módulos R7_V3 ---
from bots.analista import AnalistaBot
from bots.executor import ExecutorBot
from bots.estrategista import EstrategistaBot
from bots.guardiao import GuardiaoBot
from bots.comunicador import ComunicadorBot
from tools.account_monitor import AccountMonitor
from sniper_monitor import SniperMonitor

# Configuração de Logging Profissional
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('R7_V3_MAIN')

def load_config():
    path = os.path.join(os.path.dirname(__file__), 'config', 'settings.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "banca_referencia_usdt": 1827.00,
        "entrada_usd": 50.0,
        "config_geral": {
            "meta_diaria_total_usdt": 27.40,
            "exposicao_maxima_usdt": 600.0,
            "symbols_monitorados": [
                'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 
                'ADAUSDT', 'XRPUSDT', 'DOTUSDT', 'LINKUSDT', 
                'AVAXUSDT', 'MATICUSDT', 'LTCUSDT', 'NEARUSDT', 
                'ATOMUSDT', 'FETUSDT', 'RNDRUSDT'
            ]
        }
    }

async def iniciar_sistema():
    logger.info("⚡ R7_V3: INICIANDO MODO SNIPER (ZERO LATÊNCIA)")
    
    load_dotenv()
    config = load_config()
    
    # 1. Conexão Assíncrona
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET_KEY')
    client = await AsyncClient.create(api_key, api_secret)
    
    try:
        # 2. Inicialização dos Módulos Base
        monitor = AccountMonitor(client)
        estrategista = EstrategistaBot(config)
        executor = ExecutorBot(config, monitor=monitor)
        
        # 3. Inteligência Artificial: Carregamento Crítico
        logger.info("🧠 IA: Treinando motor com 13.760 padrões...")
        await asyncio.to_thread(executor.ia.train)
        logger.info("✅ IA pronta para predições.")

        # Registrar aporte inicial
        executor.ia.registrar_movimento('APORTE', 325.00, 'Aporte inicial do sistema')
        
        # Registrar realocação
        executor.ia.registrar_movimento("REALOCADA", 279.00, "Retirada de ADA para holding/Earn (3-12 meses)")

        # 4. Inicialização do Analista com a IA já treinada
        # PASSAGEM CIRÚRGICA: O Analista agora recebe o executor.ia
        analista = AnalistaBot(config, client=client, ia=executor.ia)

        # 5. Vínculos de Segurança
        estrategista.set_executor(executor)
        guardiao = GuardiaoBot(config, executor=executor)

        # 6. Telegram
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if token and chat_id:
            comunicador = ComunicadorBot(token, chat_id, config, guardiao, executor, estrategista)
            asyncio.create_task(asyncio.to_thread(comunicador.start_polling))
            logger.info("📱 Telegram ativo.")

        # 7. Ciclo Financeiro
        await estrategista.iniciar_dia_trading()
        
        # 8. DISPARO DO SNIPER MONITOR
        symbols = config['config_geral']['symbols_monitorados']
        sniper = SniperMonitor(
            symbols=symbols,
            ia=executor.ia,
            executor=executor,
            analista=analista, # Agora o Sniper recebe o Analista completo com o método analisar_tick
            guardiao=guardiao,
            estrategista=estrategista
        )

        logger.info(f"🎯 Sniper ativo em {len(symbols)} moedas. Em patrulha...")
        await sniper.iniciar_sniper(api_key, api_secret)

    except Exception as e:
        logger.error(f"🚨 Erro Crítico no Main: {e}")
    finally:
        await client.close_connection()
        logger.info("🔌 Conexão encerrada.")

if __name__ == "__main__":
    asyncio.run(iniciar_sistema())