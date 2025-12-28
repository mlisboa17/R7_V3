import asyncio, json, logging, os, sys, threading
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(os.path.join(BASE_DIR, 'logs', 'main.log'))])
logger = logging.getLogger('orquestrador')

def load_config():
    with open(os.path.join(BASE_DIR, 'config', 'settings.json'), 'r', encoding='utf-8') as f:
        return json.load(f)

async def orchestrator(config: dict):
    from bots.analista import AnalistaBot
    from bots.estrategista import EstrategistaBot
    from bots.guardiao import GuardiaoBot
    from bots.executor import ExecutorBot
    from bots.comunicador import ComunicadorBot

    guardiao = GuardiaoBot(config); analista = AnalistaBot(config)
    estrategista = EstrategistaBot(config); executor = ExecutorBot(config)
    estrategista.set_executor(executor); estrategista.iniciar_dia_trading()

    comunicador = ComunicadorBot(token=os.getenv('TELEGRAM_BOT_TOKEN'), chat_id=os.getenv('TELEGRAM_CHAT_ID'),
                                config=config, guardiao=guardiao, executor=executor, estrategista=estrategista)

    async def handle_trade_completion(pair, pnl_usdt, estrategia):
        estrategista.mark_position_closed(pair, pnl_usdt)
        guardiao.update_lucro_usdt(pnl_usdt, estrategia)
        await comunicador.reportar_pnl(pair, pnl_usdt, estrategia)
        # Registrar trade no log com timestamp
        try:
            import json
            from datetime import datetime
            path = os.path.join(BASE_DIR, 'data', 'trades_log.json')
            entry = {
                'timestamp': datetime.now().isoformat(),
                'date': datetime.now().date().isoformat(),
                'pair': pair,
                'estrategia': estrategia,
                'pnl_usdt': round(pnl_usdt, 2)
            }
            # Ler existente
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        arr = json.load(f)
                    except Exception:
                        arr = []
            else:
                arr = []
            arr.append(entry)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(arr, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro salvando trade em trades_log: {e}")

    executor.callback_pnl = handle_trade_completion
    threading.Thread(target=comunicador.start_polling, daemon=True).start()

    logger.info("R7_V3 Online | Meta: $20.20 | Banca: $2020.00")

    while True:
        try:
            agora = datetime.now()
            # Rotina de Tesouraria às 23:55
            if agora.hour == 23 and agora.minute == 55:
                await executor.fechar_lucros_preventivo()
                await asyncio.sleep(5)
                if guardiao.lucro_dia > 0:
                    await executor.mover_lucro_para_earn(guardiao.lucro_dia)
                await asyncio.sleep(60)

            oportunidades = await analista.buscar_oportunidades()
            for op in oportunidades:
                if estrategista.analisar_tendencia(op):
                    aprovado, motivo = guardiao.validar_operacao(executor, op)
                    if aprovado:
                        estrategista.mark_position_open(op['symbol'])
                        if await executor.executar_ordem(op['symbol'], op):
                            await comunicador.enviar_alerta_trade(op['symbol'], "COMPRA", op['entrada_usd'], op['estrategia'])
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Erro: {e}"); await asyncio.sleep(30)

if __name__ == '__main__':
    asyncio.run(orchestrator(load_config()))