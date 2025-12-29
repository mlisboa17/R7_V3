import asyncio
import json, logging, os, sys, threading
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'tools')))
from convert_to_stable_profit_only import converter_lucro_criptos_para_stable_somente_lucro
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

    # Controle de exposição e diversificação
    exposicao_max_pct = 0.4  # Máximo 40% do saldo em um ativo/estratégia
    saldo_total = config.get('banca_referencia_usdt', 1710.36)
    saldo_ultimo_fechamento = saldo_total
    dia_atual = datetime.now().date()
    mes_atual = datetime.now().month
    ativos_expostos = {}
    estrategias_expostas = {}

    from utils.correlation import calcular_correlacao_ativos, ativos_correlacionados
    historico_precos = {}
    window_corr = 30
    threshold_corr = 0.85

    # Controle de venda de criptos lucrativas a cada 30 minutos caso não tenha rodado no horário padrão
    ultima_venda_lucro = None
    while True:
        try:
            agora = datetime.now()
            # Rollover diário: ao virar o dia, atualiza saldo_total para saldo final do dia anterior
            if agora.date() != dia_atual:
                dia_atual = agora.date()
                # Pega saldo real do momento (preferencialmente do arquivo account_composition.json)
                saldo_real = saldo_total
                try:
                    with open(os.path.join(BASE_DIR, 'data', 'account_composition.json'), 'r', encoding='utf-8') as f:
                        comp = json.load(f)
                        saldo_real = float(comp.get('_total_usdt', saldo_total))
                except Exception as e:
                    logger.warning(f"Não foi possível ler saldo real de account_composition.json: {e}")
                saldo_total = saldo_real
                saldo_ultimo_fechamento = saldo_total
                logger.info(f"Novo dia iniciado: {dia_atual}. Saldo inicial atualizado para {saldo_total}")
                # Atualiza saldo inicial do dia no gestor financeiro
                try:
                    estrategista.gestor.registrar_inicio_dia(saldo_total)
                except Exception as e:
                    logger.warning(f"Não foi possível registrar saldo inicial do dia: {e}")
                # Ao fechar o dia, converte apenas criptos com lucro para USDT
                try:
                    api_key = os.getenv('BINANCE_API_KEY')
                    secret = os.getenv('BINANCE_SECRET_KEY')
                    converter_lucro_criptos_para_stable_somente_lucro(api_key, secret)
                    logger.info('Criptos com lucro convertidas para USDT no fechamento do dia.')
                    ultima_venda_lucro = agora
                except Exception as e:
                    logger.error(f'Erro ao converter criptos com lucro para USDT: {e}')
                # Rollover mensal: se mudou o mês, reinicia banca_inicial_mes
                if agora.month != mes_atual:
                    mes_atual = agora.month
                    estrategista.gestor.dados['banca_inicial_mes'] = saldo_total
                    logger.info(f"Novo mês iniciado: {mes_atual}. Saldo inicial do mês: {saldo_total}")
                    estrategista.gestor._salvar()

            # Venda automática de criptos lucrativas às 23:55
            venda_realizada = False
            if agora.hour == 23 and agora.minute == 55:
                try:
                    api_key = os.getenv('BINANCE_API_KEY')
                    secret = os.getenv('BINANCE_SECRET_KEY')
                    from tools.convert_to_stable_profit_only import converter_lucro_criptos_para_stable_somente_lucro
                    converter_lucro_criptos_para_stable_somente_lucro(api_key, secret)
                    logger.info('Criptos lucrativas vendidas automaticamente às 23:55.')
                    ultima_venda_lucro = agora
                    venda_realizada = True
                    saldo_total = estrategista.gestor.status_atual().get('saldo_final', saldo_total)
                    logger.info(f"Saldo inicial do próximo dia atualizado para {saldo_total}")
                except Exception as e:
                    logger.error(f'Erro ao vender criptos lucrativas às 23:55: {e}')
                    try:
                        if hasattr(estrategista, 'executor') and estrategista.executor and hasattr(estrategista.executor, 'comunicador') and estrategista.executor.comunicador:
                            import asyncio
                            loop = asyncio.get_event_loop()
                            msg = 'Falha na venda automática das criptos lucrativas às 23:55. Favor realizar manualmente. As trades só serão retomadas amanhã.'
                            if loop.is_running():
                                asyncio.create_task(estrategista.executor.comunicador._enviar(msg))
                            else:
                                loop.run_until_complete(estrategista.executor.comunicador._enviar(msg))
                    except Exception as e2:
                        logger.error(f'Erro ao enviar aviso Telegram: {e2}')
                    await asyncio.sleep(3600)

            # Venda de criptos lucrativas a cada 30 minutos caso não tenha sido feita
            if (ultima_venda_lucro is None or (agora - ultima_venda_lucro).total_seconds() > 1800) and not venda_realizada:
                try:
                    api_key = os.getenv('BINANCE_API_KEY')
                    secret = os.getenv('BINANCE_SECRET_KEY')
                    from tools.convert_to_stable_profit_only import converter_lucro_criptos_para_stable_somente_lucro
                    converter_lucro_criptos_para_stable_somente_lucro(api_key, secret)
                    logger.info('Criptos lucrativas vendidas por rotina de 30 minutos.')
                    ultima_venda_lucro = agora
                except Exception as e:
                    logger.error(f'Erro na venda de rotina de 30 minutos: {e}')

            # Rotina de Tesouraria às 23:59 (mantida)
            if agora.hour == 23 and agora.minute == 59:
                await executor.fechar_lucros_preventivo()
                await asyncio.sleep(5)
                if guardiao.lucro_dia > 0:
                    await executor.mover_lucro_para_earn(guardiao.lucro_dia)
                await asyncio.sleep(60)

            oportunidades = await analista.buscar_oportunidades(estrategista=estrategista)
            # ...existing code...
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Erro: {e}"); await asyncio.sleep(30)

if __name__ == '__main__':
    asyncio.run(orchestrator(load_config()))