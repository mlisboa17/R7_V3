import asyncio
import collections
import logging
from binance import AsyncClient, BinanceSocketManager

logger = logging.getLogger('sniper_monitor')

class SniperMonitor:
    def __init__(self, symbols, ia, executor, analista, guardiao, estrategista, client=None, time_sync=None):
        self.symbols = symbols
        self.ia_engine = ia
        self.executor_bot = executor
        self.analista = analista
        self.guardiao = guardiao
        self.estrategista = estrategista
        self.client = client  # 🔄 Reutiliza cliente do main.py
        self.time_sync = time_sync  # ⏰ Gerenciador de sincronização de tempo
        
        # Buffer para dar contexto aos indicadores se necessário
        self.precos_buffer = {s: collections.deque(maxlen=100) for s in symbols}
        self.is_running = True
        
        # 📊 Contador de ciclos para monitoramento
        self.ciclos_contador = {s: 0 for s in symbols}
        self.ciclos_ultima_atualizacao = {s: 0 for s in symbols}
        
        # ⏰ Controle de sincronização de relógio
        self.last_time_sync = 0  # timestamp da última sincronização
        
        # 🎭 COOLDOWN para memes (evita ansiedade excessiva)
        import time
        self.last_meme_attempt = {s: 0 for s in symbols}
        self.meme_cooldown_seconds = 30  # 30 segundos entre tentativas para memes

    async def monitorar_moeda(self, symbol, client):
        """Monitora cada moeda individualmente com reconexão automática + Exponential Backoff."""
        retry_count = 0
        max_retries = 10  # Limite de tentativas antes de desistir
        
        while self.is_running and retry_count < max_retries:
            try:
                bsm = BinanceSocketManager(client)
                # Ticker socket fornece o preço atualizado (close) em tempo real
                ts = bsm.symbol_ticker_socket(symbol)
                
                async with ts as stream:
                    logger.info(f"✅ Sniper Conectado: {symbol}")
                    retry_count = 0  # Reset após conexão bem-sucedida

                    while self.is_running:
                        # Se a meta do dia foi batida, o sniper entra em pausa técnica
                        if self.estrategista.trava_dia_encerrado:
                            await asyncio.sleep(30)
                            continue

                        try:
                            msg = await stream.recv()
                            if not msg or 'c' not in msg:
                                continue
                            
                            preco_atual = float(msg['c'])
                            self.precos_buffer[symbol].append(preco_atual)
                            
                            # 📊 Incrementa contador de ciclos
                            self.ciclos_contador[symbol] += 1
                            
                            # ⏰ SINCRONIZAÇÃO DE RELÓGIO a cada 500 ciclos (ou ~5-10 minutos)
                            if self.time_sync and self.ciclos_contador[symbol] % 500 == 0:
                                import time
                                now = time.time()
                                # Sincroniza apenas se passou mais de 5 minutos desde a última vez
                                if now - self.last_time_sync > 300:
                                    asyncio.create_task(self.time_sync.sync_clock())
                                    self.last_time_sync = now
                                    logger.info(f"⏰ {symbol}: Sincronização de relógio iniciada no ciclo #{self.ciclos_contador[symbol]}")
                            
                            # 📊 Log de contador a cada 100 ciclos
                            if self.ciclos_contador[symbol] % 100 == 0:
                                logger.info(f"📈 {symbol}: {self.ciclos_contador[symbol]} ciclos executados")
                            
                            # 📊 RESUMO ESTATÍSTICO a cada 1000 ciclos
                            if self.ciclos_contador[symbol] % 1000 == 0:
                                total_ciclos = sum(self.ciclos_contador.values())
                                posicoes_abertas = len(self.executor_bot.active_trades)
                                logger.info(f"📊 RESUMO DO SISTEMA - Ciclo #{self.ciclos_contador[symbol]}")
                                logger.info(f"   Total de ciclos (todas moedas): {total_ciclos:,}")
                                logger.info(f"   Posições abertas: {posicoes_abertas}")
                                logger.info(f"   Moedas monitoradas: {len(self.symbols)}")

                            # 1. GESTÃO DE SAÍDA (Trailing Stop + TP/SL)
                            if symbol in self.executor_bot.active_trades:
                                # Log apenas a cada 50 ciclos para não poluir
                                if self.ciclos_contador[symbol] % 50 == 0:
                                    trade = self.executor_bot.active_trades[symbol]
                                    lucro = ((preco_atual / trade['entry_price']) - 1) * 100
                                    logger.info(f"🔄 {symbol}: Ciclo #{self.ciclos_contador[symbol]} | Preço: ${preco_atual:.4f} | Lucro: {lucro:+.2f}%")
                                
                                # 🛡️ TRAILING STOP DINÂMICO - Protege lucros
                                fechou = await self.executor_bot.gerenciar_trailing_stop(symbol, preco_atual)
                                
                                # Se o trailing já fechou, não precisa verificar TP/SL fixos
                                if fechou:
                                    logger.info(f"✅ {symbol}: Posição fechada no ciclo #{self.ciclos_contador[symbol]}")
                                    continue
                            else:
                                # 🎯 SEM POSIÇÃO ABERTA: Reduz carga do sistema
                                # Só analisa a cada 5 ticks para evitar overtrading
                                if self.ciclos_contador[symbol] % 5 != 0:
                                    continue

                            # 2. ANÁLISE DE ENTRADA (Analista + IA)
                            # 🎭 COOLDOWN para memes - evita ansiedade excessiva
                            if any(meme in symbol for meme in ['PEPE', 'DOGE', 'WIF']):
                                import time
                                now = time.time()
                                if now - self.last_meme_attempt[symbol] < self.meme_cooldown_seconds:
                                    # logger.debug(f"🕐 {symbol}: Cooldown ativo - aguardando...")
                                    continue
                                    
                            logger.debug(f"🔎 {symbol}: Chamando analista.analisar_tick com preço={preco_atual}")
                            resultado = await self.analista.analisar_tick(symbol, preco_atual)

                            # 🔍 DEBUG: Log para verificar retorno do analista
                            logger.info(f"📊 {symbol}: Retorno analista = {resultado}")
                            
                            if resultado and resultado.get("decisao") == "COMPRAR":
                                confianca = resultado.get('confianca', 0.60)
                                logger.info(f"✅ {symbol}: ENTROU no IF de COMPRAR! Chamando Guardião... (Conf: {confianca:.2%})")
                                
                                # Atualiza timestamp para memes
                                if any(meme in symbol for meme in ['PEPE', 'DOGE', 'WIF']):
                                    import time
                                    self.last_meme_attempt[symbol] = time.time()
                                # 3. VALIDAÇÃO DE SEGURANÇA (Guardião NÃO é async)
                                try:
                                    validado, motivo = self.guardiao.validar_operacao(symbol, confianca)
                                    logger.info(f"🔍 {symbol}: Guardião retornou validado={validado}, motivo={motivo}")
                                except Exception as e:
                                    logger.error(f"❌ {symbol}: ERRO ao chamar Guardião: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    continue
                                
                                if validado:
                                    logger.info(f"🚀 EXECUÇÃO APROVADA: {symbol} | IA: {resultado.get('confianca', 0.60):.2%}")
                                    # Execução Única e Controlada
                                    asyncio.create_task(
                                        self.executor_bot.executar_ordem_sniper(
                                            symbol=symbol,
                                            preco_entrada_websocket=resultado.get("preco", preco_atual),
                                            confianca_ia=resultado.get('confianca', 0.60),
                                            estrategia=resultado.get("estrategia", "scalping_v6")
                                        )
                                    )
                                else:
                                    logger.warning(f"🛑 Guardião bloqueou {symbol}: {motivo}")
                        
                        except Exception as e:
                            # Se stream morreu, sai do inner loop para reconectar
                            if "Connection" in str(e) or "closed" in str(e):
                                logger.warning(f"⚠️ Conexão perdida em {symbol}. Reconectando...")
                                break
                            continue

            except asyncio.CancelledError:
                logger.info(f"⚠️ Stream {symbol} cancelado. Finalizando...")
                break
            except AttributeError as e:
                # Erro específico de 'fail_connection' ao reconectar
                if 'fail_connection' in str(e):
                    retry_count += 1
                    # 🔄 EXPONENTIAL BACKOFF: 2s, 4s, 8s, 16s, 32s, 60s (máx)
                    espera = min(60, 2 ** retry_count)
                    logger.warning(f"🔄 {symbol}: Erro de reconexão WebSocket. Tentativa {retry_count}/{max_retries}. Aguardando {espera}s...")
                    
                    if retry_count >= max_retries:
                        logger.error(f"❌ {symbol}: Limite de tentativas atingido ({max_retries}). Parando moeda.")
                        break
                    
                    await asyncio.sleep(espera)
                else:
                    raise
            except Exception as e:
                # Captura qualquer erro de WebSocket/conexão
                error_msg = str(e)
                retry_count += 1
                # 🔄 EXPONENTIAL BACKOFF
                espera = min(60, 2 ** retry_count)
                logger.error(f"⚠️ Erro no WebSocket {symbol}: {error_msg[:100]}. Tentativa {retry_count}/{max_retries}. Reconectando em {espera}s...")
                
                if retry_count >= max_retries:
                    logger.error(f"❌ {symbol}: Muitas tentativas falhadas ({max_retries}). Parando...")
                    self.is_running = False
                    break
                
                await asyncio.sleep(espera)

    async def iniciar_sniper(self, api_key=None, api_secret=None):
        """Dispara todas as moedas do settings.json em paralelo.
        
        Nota: Usa o cliente passado em __init__. Os parâmetros api_key/api_secret
        são ignorados para manter compatibilidade com main.py.
        """
        if not self.client:
            logger.error("❌ Cliente Binance não foi inicializado!")
            return
        
        try:
            tasks = [self.monitorar_moeda(s, self.client) for s in self.symbols]
            logger.info(f"🎯 Sniper R7_V3 operando em {len(self.symbols)} moedas.")
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"🚨 Erro no loop global do Sniper: {e}")