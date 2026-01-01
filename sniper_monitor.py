import asyncio
import collections
import logging
from binance import AsyncClient, BinanceSocketManager

logger = logging.getLogger('sniper_monitor')

class SniperMonitor:
    def __init__(self, symbols, ia, executor, analista, guardiao, estrategista):
        self.symbols = symbols
        self.ia_engine = ia
        self.executor_bot = executor
        self.analista = analista
        self.guardiao = guardiao
        self.estrategista = estrategista
        
        # Buffer para dar contexto aos indicadores se necessário
        self.precos_buffer = {s: collections.deque(maxlen=100) for s in symbols}
        self.is_running = True

    async def monitorar_moeda(self, symbol, client):
        """Monitora cada moeda individualmente com reconexão automática."""
        retry_count = 0
        while self.is_running:
            try:
                bsm = BinanceSocketManager(client)
                # Ticker socket fornece o preço atualizado (close) em tempo real
                async with bsm.symbol_ticker_socket(symbol) as stream:
                    logger.info(f"✅ Sniper Conectado: {symbol}")
                    retry_count = 0 

                    while self.is_running:
                        # Se a meta do dia foi batida, o sniper entra em pausa técnica
                        if self.estrategista.trava_dia_encerrado:
                            await asyncio.sleep(30)
                            continue

                        try:
                            # Aguarda o próximo tick de preço
                            msg = await asyncio.wait_for(stream.recv(), timeout=45.0)
                            if not msg or 'c' not in msg: continue

                            preco_atual = float(msg['c'])
                            self.precos_buffer[symbol].append(preco_atual)

                            # 1. GESTÃO DE SAÍDA (Monitora TP/SL de ordens abertas)
                            if symbol in self.executor_bot.active_trades:
                                trade = self.executor_bot.active_trades[symbol]
                                if preco_atual >= trade['tp']:
                                    await self.executor_bot.fechar_posicao(symbol, "🎯 Sniper Take Profit")
                                elif preco_atual <= trade['sl']:
                                    await self.executor_bot.fechar_posicao(symbol, "🛡️ Sniper Stop Loss")

                            # 2. ANÁLISE DE ENTRADA (Analista + IA)
                            resultado = await self.analista.analisar_tick(symbol, preco_atual)

                            if resultado.get("decisao") == "COMPRAR":
                                # 3. VALIDAÇÃO DE SEGURANÇA (Ignora ADA e checa limite de $2200)
                                status_guardiao = await self.guardiao.validar_operacao(symbol, self.executor_bot.entrada_usd)
                                
                                if status_guardiao == "OK":
                                    logger.info(f"🚀 GATILHO: {symbol} | Força: {resultado.get('forca', 1.0)}")
                                    await self.executor_bot.executar_ordem_sniper(
                                        symbol=symbol,
                                        preco_entrada_websocket=preco_atual,
                                        forca_sinal=resultado.get("forca", 1.0),
                                        estrategia=resultado.get("estrategia", "scalping_v6")
                                    )
                                else:
                                    logger.debug(f"🛑 Guardião: {symbol} bloqueado por {status_guardiao}")

                        except asyncio.TimeoutError:
                            logger.warning(f"⏰ Timeout em {symbol}. Reiniciando stream...")
                            break 

            except Exception as e:
                # CORREÇÃO: Removido fail_connection() que causava erro de atributo
                logger.error(f"⚠️ Erro no WebSocket {symbol}: {e}. Reconectando...")
                await asyncio.sleep(10)

    async def iniciar_sniper(self, api_key, api_secret):
        """Dispara todas as moedas do settings.json em paralelo."""
        client = await AsyncClient.create(api_key, api_secret)
        try:
            tasks = [self.monitorar_moeda(s, client) for s in self.symbols]
            logger.info(f"🎯 Sniper R7_V3 operando em {len(self.symbols)} moedas.")
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"🚨 Erro no loop global do Sniper: {e}")
        finally:
            await client.close_connection()