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
        
        # Buffer de preços para dar contexto aos indicadores (RSI, Médias, etc)
        self.precos_buffer = {s: collections.deque(maxlen=100) for s in symbols}
        self.is_running = True

    async def monitorar_moeda(self, symbol, client):
        """Monitora uma moeda específica via WebSocket com latência zero."""
        bsm = BinanceSocketManager(client)
        
        while self.is_running:
            try:
                # Usamos ticker_socket para ter o preço atualizado a cada 1000ms ou menos
                async with bsm.symbol_ticker_socket(symbol) as stream:
                    logger.info(f"✅ Sniper Conectado: {symbol}")
                    
                    while self.is_running:
                        msg = await stream.recv()
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

            except Exception as e:
                logger.error(f"⚠️ Erro no socket de {symbol}: {e}. Reconectando...")
                await asyncio.sleep(5)

    async def iniciar_sniper(self, api_key, api_secret):
        """Dispara todas as moedas monitoradas em paralelo (Async)."""
        client = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
        
        # Cria uma tarefa assíncrona para cada símbolo
        tasks = [self.monitorar_moeda(s, client) for s in self.symbols]
        
        logger.info(f"🎯 Sniper R7_V3 iniciado para: {self.symbols}")
        
        try:
            # Executa todas as moedas simultaneamente
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.critical(f"🚨 Sniper Monitor parou abruptamente: {e}")
        finally:
            await client.close_connection()