import asyncio
import logging
from binance import BinanceSocketManager
from bots.venda_inteligente import VendaInteligente

logger = logging.getLogger('sniper_resiliente')

class ResilientSniper:
    def __init__(self, symbols, ia_engine, executor_bot, guardiao):
        self.symbols = symbols
        self.ia_engine = ia_engine
        self.executor_bot = executor_bot
        self.guardiao = guardiao
        self.running = True

    async def monitorar_moeda(self, symbol):
        """Monitora cada moeda e aplica a estratégia específica decidida pela IA."""
        retry_delay = 5
        while self.running:
            try:
                client = await self.executor_bot._get_client()
                bsm = BinanceSocketManager(client)
                
                # Abre o canal de preço em tempo real
                async with bsm.symbol_ticker_socket(symbol) as stream:
                    logger.info(f"✅ Stream Ativa: {symbol}")
                    retry_delay = 5
                    
                    while self.running:
                        msg = await stream.recv()
                        if not msg: continue
                        
                        preco = float(msg['c'])
                        pair = f"{symbol}USDT" if "USDT" not in symbol else symbol

                        # 1. GESTÃO DE SAÍDA INTELIGENTE V2 (TP/SL + Previsões)
                        if pair in self.executor_bot.active_trades:
                            trade = self.executor_bot.active_trades[pair]
                            entry_time = trade.get('entry_time', datetime.now())
                            
                            # 🆕 Busca previsão se disponível
                            previsao = None
                            if hasattr(self.executor_bot, 'monitor_previsoes') and self.executor_bot.monitor_previsoes:
                                try:
                                    chave_posicao = f"{pair}_{entry_time.strftime('%Y%m%d_%H%M%S')}"
                                    historico = self.executor_bot.monitor_previsoes.historico
                                    previsao = historico.get(chave_posicao, {}).get('previsao_inicial')
                                except Exception as e:
                                    logger.debug(f"Erro ao buscar previsão para {pair}: {e}")
                            
                            # 🎯 Análise inteligente de venda
                            if hasattr(self.executor_bot, 'venda_inteligente'):
                                categoria = self.executor_bot.venda_inteligente._get_categoria(pair)
                                
                                # Calcula tempo de posição em horas
                                agora = datetime.now()
                                tempo_posicao_horas = (agora - entry_time).total_seconds() / 3600
                                
                                analise = self.executor_bot.venda_inteligente.analisar_situacao_venda(
                                    symbol=pair,
                                    preco_atual=preco,
                                    preco_entrada=trade['entry_price'],
                                    tempo_posicao_horas=tempo_posicao_horas,
                                    previsao=previsao,
                                    categoria=categoria
                                )
                                
                                # Log da decisão
                                relatorio = self.executor_bot.venda_inteligente.gerar_relatorio_decisao(analise)
                                logger.info(f"📊 {pair}: {relatorio}")
                                
                                # Executa venda se recomendado
                                if analise['deve_vender']:
                                    if analise['percentual_venda'] >= 100:
                                        # Venda total
                                        await self.executor_bot.fechar_posicao(pair, analise['motivo'])
                                    else:
                                        # Venda parcial
                                        quantidade_venda = trade['qty'] * (analise['percentual_venda'] / 100)
                                        await self.executor_bot.fechar_posicao_parcial(pair, quantidade_venda, analise['motivo'])
                                
                            # Fallback: sistema tradicional de TP/SL
                            else:
                                if preco >= trade['tp']:
                                    await self.executor_bot.fechar_posicao(pair, f"TP_{trade['estrategia']}")
                                elif preco <= trade['sl']:
                                    await self.executor_bot.fechar_posicao(pair, f"SL_{trade['estrategia']}")
                        
                        # 2. GESTÃO DE ENTRADA (Lógica Multi-Bot)
                        else:
                            pode_operar, motivo = self.guardiao.validar_operacao(self.executor_bot.active_trades, symbol)
                            if pode_operar:
                                # A IA agora retorna o dicionário completo: {decisao, estrategia, forca}
                                analise = await self.ia_engine.analisar_tick(symbol, preco)
                                
                                if analise and analise.get('decisao') == "COMPRAR":
                                    estrategia = analise.get('estrategia', 'default')
                                    forca = analise.get('forca', 1.0)
                                    
                                    logger.info(f"🎯 Sinal Detectado: {symbol} | Estratégia: {estrategia} | Força: {forca}")
                                    
                                    # Dispara a ordem com os parâmetros dinâmicos
                                    await self.executor_bot.executar_ordem_sniper(
                                        symbol=symbol, 
                                        preco_entrada_websocket=preco,
                                        forca_sinal=forca,
                                        estrategia=estrategia
                                    )
            except Exception as e:
                logger.error(f"⚠️ Erro no socket {symbol}: {e}. Reconectando...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)

    async def iniciar(self):
        """Dispara todas as 15 moedas em paralelo."""
        tasks = [self.monitorar_moeda(s) for s in self.symbols]
        await asyncio.gather(*tasks)