import asyncio
import collections
import logging
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException

logger = logging.getLogger('sniper_monitor')

class SniperMonitor:
    def __init__(self, symbols, ia, executor, analista, guardiao, estrategista):
        self.symbols = symbols
        self.ia_engine = ia
        self.executor_bot = executor
        self.analista = analista
        self.guardiao = guardiao
        self.estrategista = estrategista

        # Buffer de preços para dar contexto aos indicadores (RSI, Médias, etc)
        self.precos_buffer = {s: collections.deque(maxlen=100) for s in symbols}
        self.is_running = True

    async def monitorar_moeda(self, symbol, client):
        """Monitora uma moeda específica via WebSocket com latência zero e retry robusto."""
        retry_count = 0
        max_retries = 10
        base_delay = 5

        while self.is_running and retry_count < max_retries:
            try:
                bsm = BinanceSocketManager(client)

                # Usamos ticker_socket para ter o preço atualizado a cada 1000ms ou menos
                async with bsm.symbol_ticker_socket(symbol) as stream:
                    logger.info(f"✅ Sniper Conectado: {symbol} (tentativa {retry_count + 1})")
                    retry_count = 0  # Reset retry count on successful connection

                    while self.is_running:
                        try:
                            msg = await asyncio.wait_for(stream.recv(), timeout=30.0)
                            if not msg or 'c' not in msg:
                                continue

                            preco_atual = float(msg['c']) # Preço de fechamento atual
                            self.precos_buffer[symbol].append(preco_atual)

                            # 1. MONITORAMENTO DE SAÍDA (TP/SL)
                            # Checa se temos uma posição aberta nesta moeda para fechar no alvo
                            if symbol in self.executor_bot.active_trades:
                                trade = self.executor_bot.active_trades[symbol]

                                if preco_atual >= trade['tp']:
                                    await self.executor_bot.fechar_posicao(symbol, "🎯 Sniper Take Profit")
                                elif preco_atual <= trade['sl']:
                                    await self.executor_bot.fechar_posicao(symbol, "🛡️ Sniper Stop Loss")

                            # 2. ANÁLISE DE ENTRADA (IA + TÉCNICO)
                            # Chamamos o Analista que agora é assíncrono e usa a IA
                            resultado = await self.analista.analisar_tick(symbol, preco_atual)

                            if resultado["decisao"] == "COMPRAR":
                                # 3. VALIDAÇÃO DE SEGURANÇA (Guardião + Estrategista)
                                # O Guardião checa exposição máxima e o Estrategista checa meta diária
                                aprovado, motivo = self.guardiao.validar_operacao(self.executor_bot, resultado)
                                pode_operar = await self.estrategista.analisar_tendencia(symbol, preco_atual)

                                if aprovado and pode_operar:
                                    logger.info(f"🚀 GATILHO SNIPER: {symbol} | Força: {resultado['forca']}")
                                    await self.executor_bot.executar_ordem_sniper(
                                        symbol=symbol,
                                        preco_atual=preco_atual,
                                        forca_sinal=resultado.get("forca", 1.0),
                                        estrategia=resultado.get("estrategia", "scalping_v6")
                                    )
                                else:
                                    if not pode_operar:
                                        logger.debug(f"🛑 Estrategista bloqueou entrada em {symbol} (Meta/Proteção).")

                        except asyncio.TimeoutError:
                            logger.warning(f"⏰ Timeout no WebSocket de {symbol}. Verificando conexão...")
                            break  # Sai do loop interno para reconectar
                        except Exception as e:
                            logger.error(f"⚠️ Erro no processamento de {symbol}: {e}")
                            break  # Sai do loop interno para reconectar

            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout na conexão WebSocket de {symbol}")
            except Exception as e:
                retry_count += 1
                delay = min(base_delay * (2 ** retry_count), 300)  # Exponential backoff, max 5min
                logger.error(f"🔌 Erro no WebSocket de {symbol} (tentativa {retry_count}/{max_retries}): {e}")
                logger.info(f"⏳ Aguardando {delay}s antes de reconectar...")

                if retry_count >= max_retries:
                    logger.critical(f"🚨 Máximo de tentativas atingido para {symbol}. Parando monitoramento.")
                    break

                await asyncio.sleep(delay)

        if retry_count >= max_retries:
            logger.error(f"❌ Monitoramento de {symbol} finalizado após {max_retries} tentativas falhadas")

    async def iniciar_sniper(self, api_key, api_secret):
        """Dispara todas as moedas monitoradas em paralelo (Async) com retry robusto."""
        client = None
        for attempt in range(3):
            try:
                logger.info(f"🔌 Conectando à Binance (tentativa {attempt + 1}/3)...")
                client = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
                logger.info("✅ Cliente Binance conectado com sucesso!")
                break
            except Exception as e:
                logger.warning(f"⚠️ Falha na conexão Binance (tentativa {attempt + 1}/3): {e}")
                if attempt < 2:
                    await asyncio.sleep(5)
                else:
                    logger.error("❌ Não foi possível conectar à Binance após 3 tentativas")
                    return

        if not client:
            logger.error("❌ Cliente Binance não disponível. Abortando sniper.")
            return

        # Cria uma tarefa assíncrona para cada símbolo
        tasks = [self.monitorar_moeda(s, client) for s in self.symbols]

        logger.info(f"🎯 Sniper R7_V3 iniciado para: {self.symbols}")
        logger.info(f"📊 Monitorando {len(self.symbols)} símbolos em paralelo")

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"❌ Erro geral no sniper: {e}")
        finally:
            logger.info("🔌 Finalizando conexões WebSocket...")
            await client.close_connection()
        
        try:
            # Executa todas as moedas simultaneamente
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.critical(f"🚨 Sniper Monitor parou abruptamente: {e}")
        finally:
            await client.close_connection()