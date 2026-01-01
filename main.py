import os
import logging
import asyncio
import json
import pandas as pd
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
    """Carrega configurações, corrige símbolos e permite informar preços de custo manuais."""
    path = os.path.join(os.path.dirname(__file__), 'config', 'settings.json')
    
    # Base de símbolos atualizada (POL e RENDER)
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 
        'ADAUSDT', 'XRPUSDT', 'DOTUSDT', 'LINKUSDT', 
        'AVAXUSDT', 'POLUSDT', 'LTCUSDT', 'NEARUSDT', 
        'ATOMUSDT', 'FETUSDT', 'RENDERUSDT'
    ]

    # --- ÁREA DE CONFIGURAÇÃO MANUAL ---
    # Informe aqui o preço que você pagou por moedas antigas que o bot deve gerenciar.
    # Se deixar vazio {}, o bot tentará buscar sozinho na Binance.
    precos_manuais = {
        "SOLUSDT": 0.0,  # Exemplo: coloque 180.50 se comprou nesse valor
        "BTCUSDT": 0.0,
        "ETHUSDT": 0.0,
        "GICLEUSDT": 68.35  # Preço de compra registrado
    }

    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            config['config_geral']['symbols_monitorados'] = symbols
            config['precos_custo'] = precos_manuais
            return config
            
    return {
        "banca_referencia_usdt": 1870.00, # Banca atualizada para 1870.00
        "precos_custo": precos_manuais,
        "entrada_usd": 50.0,
        "config_geral": {
            "meta_diaria_total_usdt": 27.40,
            "exposicao_maxima_usdt": 600.0,
            "symbols_monitorados": symbols
        }
    }

async def iniciar_sistema():
    logger.info("⚡ R7_V3: INICIANDO MODO SNIPER (ZERO LATÊNCIA)")
    
    load_dotenv()
    config = load_config()
    
    # 1. Conexão Assíncrona com a Binance (com retry)
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET_KEY')
    for i in range(3):
        try:
            client = await AsyncClient.create(api_key, api_secret)
            break
        except Exception as e:
            if i == 2: raise e
            logger.warning(f"⚠️ Falha na conexão (tentativa {i+1}/3). Reentando em 5s...")
            await asyncio.sleep(5)
    
    try:
        # 2. Inicialização dos Módulos Base
        monitor = AccountMonitor(client)
        estrategista = EstrategistaBot(config)
        executor = ExecutorBot(config, monitor=monitor)
        
        # Inicia a atualização contínua do saldo (a cada 30 segundos)
        asyncio.create_task(monitor.monitor_loop())
        
        # 3. Inteligência Artificial: Treino inicial
        logger.info("🧠 IA: Sincronizando motor com padrões de mercado...")
        await asyncio.to_thread(executor.ia.train)
        logger.info("✅ IA pronta para predições.")

        # 4. Inicialização do Analista
        analista = AnalistaBot(config, client=client, ia=executor.ia)

        # 5. Vínculos de Segurança
        estrategista.set_executor(executor)
        guardiao = GuardiaoBot(config, executor=executor)

        # 5.5. Gestão de Carteira Existente (SÓ VENDE COM LUCRO)
        # Este método usa o 'precos_custo' acima ou consulta a Binance.
        logger.info("🛡️ Assumindo carteira atual com critério de lucro de 1.5%...")
        await executor.assumir_e_gerenciar_carteira()

        # 6. Telegram (Comunicação)
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
            analista=analista,
            guardiao=guardiao,
            estrategista=estrategista
        )

        logger.info(f"🎯 Sniper ativo em {len(symbols)} moedas. Em patrulha...")
        await sniper.iniciar_sniper(api_key, api_secret)

    except Exception as e:
        logger.error(f"🚨 Erro Crítico no Main: {e}")
    finally:
        await client.close_connection()
        logger.info("🔌 Conexão Binance encerrada.")

if __name__ == "__main__":
    try:
        asyncio.run(iniciar_sistema())
    except KeyboardInterrupt:
        logger.info("🛑 Sniper interrompido pelo usuário.")