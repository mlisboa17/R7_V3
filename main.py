import os
import sys
import io
import logging
import asyncio
import json
from dotenv import load_dotenv
from binance import AsyncClient

# 🔧 FIX: Força UTF-8 no terminal Windows para suportar emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    # Define o título da janela do PowerShell/CMD
    os.system('title R7_V3')

# --- GARANTIA DE PATH ÚNICO ---
diretorio_raiz = os.path.dirname(os.path.abspath(__file__))
if diretorio_raiz not in sys.path:
    sys.path.append(diretorio_raiz)

from bots.analista import AnalistaBot
from bots.executor import ExecutorBot
from bots.estrategista import EstrategistaBot
from bots.guardiao import GuardiaoBot
from bots.monitor_previsoes import MonitorPrevisoes
from utils.notify import send_telegram_message
from tools.account_monitor import AccountMonitor
from tools.time_sync import TimeSyncManager
from tools.state_validator import StateValidator
from sniper_monitor import SniperMonitor

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('R7_V3_MAIN')

def load_config():
    path = os.path.join(diretorio_raiz, 'config', 'settings.json')
    if not os.path.exists(path):
        raise FileNotFoundError(f"🚨 Configuração não encontrada em: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

async def iniciar_sistema():
    logger.info("⚡ R7_V3: INICIANDO MODO SNIPER (ESTÁVEL)")
    load_dotenv()
    
    client = None
    time_sync = None
    
    try:
        # 🔍 VALIDAÇÃO PRÉVIA DE ESTADO
        logger.info("🔍 Validando integridade do sistema...")
        validator = StateValidator()
        
        # Gera relatório de saúde
        validator.relatorio_completo()
        
        # Detecta corrupção
        if validator.detectar_estado_corrupto():
            logger.error("🚨 Estado corrupto detectado! Sincronizando...")
            validator.sincronizar_arquivos()
            logger.info("✅ Sistema sincronizado e pronto")
        
        # Valida consistência
        consistente, erros = validator.validar_consistencia()
        if not consistente:
            logger.warning(f"⚠️ Inconsistências encontradas - Sincronizando...")
            validator.sincronizar_arquivos()
        
        config = load_config()
        
        # 1. CONEXÃO COM KEEPALIVE (Evita os timeouts vistos nos logs)
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET_KEY')
        
        # Criamos o cliente com suporte a reconexão automática
        client = await AsyncClient.create(api_key, api_secret)
        
        # 🔄 INICIALIZAR SINCRONIZAÇÃO DE RELÓGIO
        time_sync = TimeSyncManager(client)
        logger.info("⏰ Iniciando sincronização de relógio...")
        if await time_sync.sync_clock():
            logger.info("✅ Relógio sincronizado com sucesso!")
            # Inicia re-sincronização periódica em background
            asyncio.create_task(time_sync.periodic_resync())
        else:
            logger.warning("⚠️ Falha na sincronização inicial de relógio")

        # 2. INICIALIZAÇÃO DE MÓDULOS
        estrategista = EstrategistaBot(config)
        executor = ExecutorBot(config, monitor=None)
        
        # 3. MONITOR DE SALDO (Com os $2.355,05 de meta)
        monitor = AccountMonitor(client, gestor=estrategista.gestor, time_sync=time_sync)
        executor.monitor = monitor
        asyncio.create_task(monitor.monitor_loop())
        
        # --- TREINO DA IA ---
        # Opcional: executar treino em background para não bloquear startup.
        # Controle via .env: R7_TRAIN_ON_STARTUP=true|false
        train_on_startup = os.getenv('R7_TRAIN_ON_STARTUP', 'true').lower() in ('1', 'true', 'yes', 'y')
        logger.info("🧠 IA: Sincronizando motor de decisão... (train_on_startup=%s)", train_on_startup)
        if train_on_startup:
            # roda o treino em background sem aguardar (evita atrasar serviços críticos)
            asyncio.create_task(asyncio.to_thread(executor.ia.train))
        else:
            logger.info("🧠 Treino de IA ignorado no startup (R7_TRAIN_ON_STARTUP=false)")
        
        analista = AnalistaBot(config, client=client, ia=executor.ia)
        guardiao = GuardiaoBot(config, executor=executor)
        
        # 4. CONEXÃO DE DEPENDÊNCIAS (Fluxo de Dados)
        analista.set_executor(executor)
        estrategista.set_executor(executor)
        executor.analista = analista  # 🎯 Conecta analista ao executor para saída inteligente
        
        # 🎯 SISTEMA DE PREVISÕES - Roda em background a cada 15min
        monitor_previsoes = MonitorPrevisoes(client, executor)
        executor.monitor_previsoes = monitor_previsoes
        await monitor_previsoes.iniciar()
        logger.info("✅ Monitor de Previsões iniciado (atualização a cada 15 min)")
        
        # CONEXÃO DO MOTOR FINANCEIRO (Vital para o Dashboard)
        executor.callback_pnl = estrategista.registrar_pnl
        
        # Inicia ciclo diário
        await estrategista.iniciar_dia_trading()

        # 5. DISPARO DO SNIPER (Monitorando 22 Moedas)
        symbols = config['config_geral']['symbols_monitorados']
        sniper = SniperMonitor(
            symbols, executor.ia, executor, analista, guardiao, estrategista, 
            client=client, time_sync=time_sync
        )

        logger.info(f"🎯 Sniper R7_V3 ativo em {len(symbols)} moedas.")
        
        # 6. GESTÃO DE CARTEIRA (Em paralelo - não bloqueia)
        logger.info("🛡️ Assumindo posições abertas em background...")
        asyncio.create_task(executor.assumir_e_gerenciar_carteira())
        
        # 7. Loop principal do Sniper (PRIORIDADE - roda continuamente)
        await sniper.iniciar_sniper()

    except Exception as e:
        logger.error(f"🚨 Erro Fatal no Sistema: {e}")
        import traceback
        traceback.print_exc()
        try:
            send_telegram_message(f"🚨 Erro Fatal R7_V3: {e}")
        except Exception:
            logger.exception("Falha ao enviar alerta Telegram de erro fatal")
    finally:
        if client:
            await client.close_connection()
            logger.info("🔌 Conexão Binance encerrada.")

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    asyncio.run(iniciar_sistema())