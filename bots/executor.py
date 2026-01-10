import asyncio
import os
import logging
import math
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
import json
import sys
import requests
from datetime import datetime
from bots.stop_loss_engine import StopLossEngine
from bots.venda_inteligente import VendaInteligente

# Ajuste de Path para garantir que a IA Engine seja encontrada na raiz
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

# 🧠 Importa Cérebro de Decisão de Stop Loss
try:
    from tools.cerebro_stop_loss import CerebroStopLoss
    CEREBRO_DISPONIVEL = True
except ImportError:
    logger.warning("⚠️ Cérebro Stop Loss não encontrado - Decisões de renovação desabilitadas")
    CEREBRO_DISPONIVEL = False

try:
    from ia_engine import IAEngine
except ImportError:
    try:
        from ia_engine import IAEngine
    except Exception:
        raise

from bots.asset_classifier import AssetClassifier, ScaledExit
from bots.symbol_mapper import SymbolMapper

logger = logging.getLogger('executor')

class ExecutorBot:
    def __init__(self, config=None, monitor=None):
        self.config = config or {}
        self.monitor = monitor  
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_SECRET_KEY')
        self.client = None 
        self.active_trades = {}
        self.callback_pnl = None
        self.taxa_binance = 0.001 
        self.precisoes = {} # Cache para Lot Size
        self.analista = None  # Será injetado via main.py para saída inteligente
        self.ia = IAEngine() # Engine com os 13.760 padrões
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # 🎯 Sistema de Venda Dinâmica
        self.asset_classifier = AssetClassifier()
        self.scaled_exit = ScaledExit()
        
        # 🎯 Sistema de Previsões (será conectado pelo main.py)
        self.monitor_previsoes = None
        
        # 🛡️ Stop Loss Engine V2 (híbrido: percentual + dólar + tempo)
        self.stop_loss_engine = StopLossEngine()
        
        # 🧠 Cérebro de Decisão de Stop Loss (Renovar ou Vender)
        if CEREBRO_DISPONIVEL:
            try:
                self.cerebro_stop_loss = CerebroStopLoss()
                logger.info("🧠 Cérebro Stop Loss ativado - Decisões inteligentes habilitadas")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao carregar Cérebro: {e}")
                self.cerebro_stop_loss = None
        else:
            self.cerebro_stop_loss = None
        
        # 🎯 Sistema de Venda Inteligente V2 (baseado em previsões)
        self.venda_inteligente = VendaInteligente()
        
        # 🛡️ Controle de tentativas de venda (evita loop infinito)
        self._sell_attempts = {}  # {symbol: {'last_attempt': timestamp, 'error_count': int}}
        self._sell_cooldown = 10  # segundos entre tentativas após erro
        
        # 📊 Contador de verificações de trailing stop
        self._trailing_checks = {}  # {symbol: count}
    
    def enviar_telegram(self, mensagem):
        """Envia mensagem para o Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            requests.post(url, json={'chat_id': self.telegram_chat_id, 'text': mensagem, 'parse_mode': 'HTML'}, timeout=5)
        except Exception as e:
            logger.debug(f"Erro ao enviar Telegram: {e}")

    def contar_posicoes_abertas(self, preco_atual_dict=None):
        """
        Conta posições abertas considerando APENAS posições com valor >= $1.
        Ignora posições muito pequenas (dust).
        
        Args:
            preco_atual_dict: Dict com preços atuais {symbol: preco}
            
        Returns:
            int: Número de posições abertas com valor >= $1
        """
        count = 0
        for symbol, trade in self.active_trades.items():
            qty = trade.get('qty', 0)
            entry_price = trade.get('entry_price', 0)
            
            # Estima valor atual da posição
            if preco_atual_dict and symbol in preco_atual_dict:
                preco_atual = preco_atual_dict[symbol]
            else:
                preco_atual = entry_price  # Fallback para preço de entrada
            
            valor_posicao = qty * preco_atual
            
            # Só conta se valor >= $1
            if valor_posicao >= 1.0:
                count += 1
            else:
                logger.debug(f"⏭️ {symbol}: Ignorado na contagem (${valor_posicao:.4f} < $1.00)")
        
        return count


    def calcular_alvos(self, preco_compra, estrategia="scalping_v6", symbol=None, quantidade=None):
        """Calcula Take Profit e Stop Loss usando sistema híbrido V2."""
        # Stop Loss dinâmico baseado no tipo de moeda
        volatilidade_moeda = self.get_coin_volatility_profile(symbol)
        
        config_estrategias = {
            "scalping_v6": {"tp": 1.025, "sl": 0.985 + volatilidade_moeda},      # +2.5% / -1.5% SL dinâmico
            "meme_sniper": {"tp": 1.040, "sl": 0.975 + volatilidade_moeda},     # +4.0% / -2.5% SL dinâmico
            "momentum_boost": {"tp": 1.030, "sl": 0.982 + volatilidade_moeda},  # +3.0% / -1.8% SL dinâmico
            "layer2_defi": {"tp": 1.028, "sl": 0.985 + volatilidade_moeda},     # +2.8% / -1.5% SL dinâmico
            "swing_rwa": {"tp": 1.035, "sl": 0.980 + volatilidade_moeda}        # +3.5% / -2.0% SL dinâmico
        }
        config = config_estrategias.get(estrategia, {"tp": 1.025, "sl": 0.985})
        
        # Aplica margem segura configurável por .env (em pontos percentuais)
        try:
            safe_margin = float(os.getenv('R7_SAFE_MARGIN_PCT', '0.5'))  # Reduzido para ser menos conservador
        except Exception:
            safe_margin = 0.5

        # Converte tp multiplicador para pct, aplica margem (subtrai pontos percentuais)
        tp_pct = (config['tp'] - 1.0) * 100.0
        tp_pct_adj = max(tp_pct - safe_margin, 0.2)
        tp_multiplier_adj = 1.0 + (tp_pct_adj / 100.0)
        
        # 🆕 Stop Loss Híbrido V2 (se quantidade fornecida)
        if quantidade and symbol:
            sl_hibrido = self.stop_loss_engine.calcular_stop_loss_hibrido(
                symbol=symbol,
                preco_entrada=preco_compra,
                quantidade=quantidade,
                entry_time=datetime.now()
            )
            sl_price = sl_hibrido['sl_price']
            logger.info(f"🛡️ Stop Loss Híbrido {symbol}: {sl_hibrido['criterio_usado']} = ${sl_price:.6f}")
        else:
            # Fallback para método antigo
            sl_ajustado = self.ajustar_sl_inteligente(config['sl'], symbol, estrategia)
            sl_price = preco_compra * sl_ajustado

        return {
            'tp': preco_compra * tp_multiplier_adj,
            'sl': sl_price
        }

    async def _get_client(self):
        """Inicializa o cliente assíncrono (Singleton)."""
        if self.client is None:
            self.client = await AsyncClient.create(self.api_key, self.api_secret)
            await self.carregar_precisoes()
        return self.client
    
    def get_coin_volatility_profile(self, symbol):
        """Determina perfil de volatilidade da moeda para ajustar stop loss."""
        if not symbol:
            return 0.002  # Default conservador
            
        # Moedas MEME - alta volatilidade, stop loss mais controlado
        meme_coins = ['PEPE', 'DOGE', 'SHIB', 'WIF', 'BONK', 'FLOKI']
        if any(meme in symbol.upper() for meme in meme_coins):
            return 0.003  # +0.3% no stop loss (menos ansioso)
            
        # Blue Chips - menor volatilidade, stop loss mais rígido
        blue_chips = ['BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'XRP']
        if any(blue in symbol.upper() for blue in blue_chips):
            return 0.006  # +0.6% no stop loss (mais flexível para ADA)
            
        # Altcoins DeFi - volatilidade média
        defi_coins = ['UNI', 'LINK', 'AAVE', 'DOT', 'AVAX', 'ATOM']
        if any(defi in symbol.upper() for defi in defi_coins):
            return 0.003  # +0.3% no stop loss (média)
            
        # Outras moedas - padrão
        return 0.002  # +0.2% no stop loss
    
    def ajustar_sl_inteligente(self, sl_base, symbol, estrategia):
        """Ajusta stop loss inteligente para evitar saídas prematuras."""
        # Fator temporal - mais flexível nas primeiras horas
        tempo_flexibilidade = 0.003  # +0.3% nas primeiras horas
        
        # Fator de estratégia - meme coins mais controlados
        if estrategia == 'meme_sniper':
            fator_estrategia = 0.002  # +0.2% extra para memes (reduzido)
        elif estrategia == 'scalping_v6':
            fator_estrategia = 0.001  # +0.1% extra para scalping
        else:
            fator_estrategia = 0.002  # +0.2% padrão
            
        # Combina todos os fatores
        sl_ajustado = sl_base + tempo_flexibilidade + fator_estrategia
        
        # Limita o stop loss máximo para não ficar muito flexível
        sl_minimo = 0.975  # Nunca menos que -2.5%
        return max(sl_ajustado, sl_minimo)
    
    def get_coin_type_description(self, symbol):
        """Retorna emoji e descrição do tipo de moeda."""
        if not symbol:
            return "⚪"
            
        # Moedas MEME
        meme_coins = ['PEPE', 'DOGE', 'SHIB', 'WIF', 'BONK', 'FLOKI']
        if any(meme in symbol.upper() for meme in meme_coins):
            return "🎭 (MEME)"
            
        # Blue Chips
        blue_chips = ['BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'XRP']
        if any(blue in symbol.upper() for blue in blue_chips):
            return "🔷 (BLUE CHIP)"
            
        # DeFi
        defi_coins = ['UNI', 'LINK', 'AAVE', 'DOT', 'AVAX', 'ATOM']
        if any(defi in symbol.upper() for defi in defi_coins):
            return "🌐 (DEFI)"
            
        return "⚪ (ALT)"

    async def carregar_precisoes(self):
        """Busca as regras de arredondamento da Binance."""
        try:
            client = self.client  # Usa cliente já criado
            if not client:
                logger.warning("⚠️ Cliente não disponível para carregar precisões")
                return
            
            # 🗺️ Inicializa o mapeador de símbolos
            await SymbolMapper.initialize(client)
            
            info = await asyncio.wait_for(client.get_exchange_info(), timeout=10.0)
            for s in info['symbols']:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = f['stepSize'].rstrip('0').rstrip('.')
                        self.precisoes[s['symbol']] = len(step_size.split('.')[1]) if '.' in step_size else 0
            logger.info("✅ Filtros de precisão carregados para todas as moedas.")
        except asyncio.TimeoutError:
            logger.error("⏱️ Timeout ao carregar precisões da Binance")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar precisões: {e}")

    async def assumir_e_gerenciar_carteira(self):
        """
        Analisa ativos na carteira e ADICIONA ao active_trades para monitoramento contínuo.
        🔄 RODA EM LOOP: Re-scanneia a carteira a cada 60 segundos para detectar novas posições.
        """
        logger.info("🛡️ Assumindo controle de posições abertas e iniciando monitoramento CONTÍNUO...")
        
        while True:  # Loop infinito para monitoramento contínuo
            try:
                logger.debug("📡 Obtendo cliente Binance...")
                client = await self._get_client()
                
                logger.debug("📊 Re-scanneando carteira Binance...")
                account_info = await asyncio.wait_for(client.get_account(), timeout=10.0)
                balances = [b for b in account_info['balances'] if float(b['free']) > 0]
                logger.info(f"💰 Encontrados {len(balances)} ativos com saldo > 0")

                for asset_info in balances:
                    asset = asset_info['asset']
                    quantidade = float(asset_info['free'])

                    # Proteção APENAS para USDT e ativos bloqueados em Launchpool/Staking
                    # NUNCA ignorar ativos que representam dinheiro real!
                    ignored_assets = [
                        'USDT',          # Moeda base (não precisa monitorar)
                        'LDUSDT',        # USDT em Earn/Staking (não é tradável)
                        'LDBNB', 'LDBTC', 'LDETH', 'LDSOL', 'LDMATIC',  # Ativos em Launchpool (prefixo LD = Locked/Launchpool)
                    ]
                    
                    if asset in ignored_assets or quantidade <= 0:
                        logger.debug(f"⏭️ {asset}: Ignorado (staking/launchpool ou saldo zero)")
                        continue
                    
                    # 🗺️ USA O MAPEADOR DE SÍMBOLOS (resolve MATIC, etc)
                    # Primeiro tenta corrigir erros comuns
                    if asset.endswith('USDTT'):
                        symbol = SymbolMapper.fix_symbol_errors(asset)
                        logger.info(f"🔧 Corrigido: {asset} → {symbol}")
                    else:
                        symbol = SymbolMapper.map_asset_to_symbol(asset)
                    
                    if not symbol:
                        # 💰 ATENÇÃO: Asset na carteira mas não conseguimos mapear!
                        valor_estimado = quantidade * 0.01  # Estimativa mínima
                        logger.error(f"💰 {asset}: {quantidade:.4f} unidades (≈${valor_estimado:.2f}) - Não foi possível mapear para símbolo válido!")
                        logger.error(f"   ⚠️ TOKEN PODE ESTAR DESCONTINUADO OU RENOMEADO - Verifique manualmente!")
                        continue
                    
                    # Valida se símbolo existe
                    if not SymbolMapper.is_valid_symbol(symbol):
                        valor_estimado = quantidade * 0.01
                        logger.error(f"💰 {asset} → {symbol}: {quantidade:.4f} unidades (≈${valor_estimado:.2f})")
                        logger.error(f"   ⚠️ SÍMBOLO NÃO EXISTE NA BINANCE - Token possivelmente descontinuado/renomeado!")
                        logger.error(f"   📋 Ação necessária: Verificar na Binance se há migração/swap disponível")
                        continue
                    
                    logger.debug(f"🔍 Processando {asset} → {symbol}...")

                    try:
                        precos_manuais = self.config.get('precos_custo', {})
                        preco_compra = precos_manuais.get(symbol)

                        if not preco_compra or preco_compra == 0:
                            logger.debug(f"   Buscando histórico de trades para {symbol}...")
                            try:
                                trades = await asyncio.wait_for(
                                    client.get_my_trades(symbol=symbol, limit=1),
                                    timeout=3.0
                                )
                                if trades:
                                    preco_compra = float(trades[0]['price'])
                                    logger.debug(f"   ✓ Preço de compra encontrado: ${preco_compra:.4f}")
                                else:
                                    # � CRÍTICO: Sem histórico = NÃO MONITORAR
                                    # Usar preço atual como entrada é ERRO FATAL que causa perdas!
                                    ticker = await asyncio.wait_for(
                                        client.get_symbol_ticker(symbol=symbol),
                                        timeout=3.0
                                    )
                                    preco_atual_market = float(ticker['price'])
                                    valor_usdt = quantidade * preco_atual_market
                                    logger.error(f"🚨 {asset}: SEM HISTÓRICO DE COMPRA - NÃO SERÁ MONITORADO!")
                                    logger.error(f"   💰 Saldo: {quantidade:.4f} {asset} ≈ ${valor_usdt:.2f} USDT")
                                    logger.error(f"   ⚠️ SISTEMA NÃO SABE O PREÇO DE COMPRA REAL!")
                                    logger.error(f"   📋 AÇÃO NECESSÁRIA: Adicione manualmente em config/precos_custo.json:")
                                    logger.error(f"       \"{symbol}\": PRECO_QUE_VOCE_COMPROU")
                                    continue  # NÃO monitora sem preço real
                            except asyncio.TimeoutError:
                                logger.error(f"⏱️ {asset}: Timeout ao buscar informações - Verifique conexão")
                                continue
                            except Exception as e:
                                logger.error(f"❌ {asset}: Erro ao buscar dados: {e}")
                                logger.error(f"   💰 Saldo: {quantidade:.4f} {asset} - IMPOSSÍVEL MONITORAR")
                                continue

                        if not preco_compra:
                            logger.error(f"❌ {asset}: Sem dados válidos - NÃO SERÁ MONITORADO!")
                            logger.error(f"   💰 Você tem {quantidade:.4f} {asset} não monitorados!")
                            continue
                        
                        logger.debug(f"   Buscando preço atual para {symbol}...")
                        try:
                            ticker = await asyncio.wait_for(
                                client.get_symbol_ticker(symbol=symbol),
                                timeout=3.0
                            )
                            preco_atual = float(ticker['price'])
                            logger.debug(f"   ✓ Preço atual: ${preco_atual:.4f}")
                        except asyncio.TimeoutError:
                            logger.warning(f"⏱️ Timeout ao buscar preço de {asset}")
                            continue
                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao buscar preço de {asset}: {e}")
                            continue
                        
                        valor_total_posicao = quantidade * preco_atual
                        
                        # 🚫 NOVA REGRA: Ignora ativos com valor total abaixo de $1
                        if valor_total_posicao < 1.0:
                            logger.debug(f"⏭️ {asset}: Ignorado - Valor total ${valor_total_posicao:.4f} < $1.00")
                            continue
                        
                        lucro_atual_pct = ((preco_atual - preco_compra) / preco_compra) * 100
                        
                        # 🔄 ADICIONA ao active_trades para monitoramento contínuo
                        # IMPORTANTE: Marca como 'legacy' para não bloquear novas compras
                        if symbol not in self.active_trades:
                            alvos = self.calcular_alvos(preco_compra, "scalping_v6", symbol)
                            self.active_trades[symbol] = {
                                'qty': quantidade,
                                'entry_price': preco_compra,
                                'tp': alvos['tp'],
                                'sl': alvos['sl'],
                                'estrategia': 'manual_existing',
                                'confianca': 0.0,
                                'legacy': True,  # Marca como posição antiga
                                'entry_time': datetime.now()  # Estima tempo de entrada como agora
                            }
                            logger.info(f"✅ {asset}: Adicionado ao monitoramento | Lucro: {lucro_atual_pct:+.2f}%")
                        else:
                            logger.debug(f"⏭️ {asset}: Já está sendo monitorado")

                    except Exception as ex:
                        logger.warning(f"⚠️ Erro ao processar {asset}: {ex}")
                        continue
                
                logger.info(f"✅ Total de {len(self.active_trades)} posições sob monitoramento contínuo")
                
                # 🔄 Aguarda 60 segundos antes do próximo scan
                await asyncio.sleep(60)
                
            except asyncio.TimeoutError:
                logger.error("⏱️ Timeout ao buscar informações da conta Binance - Tentando novamente em 60s")
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"🚨 Erro crítico ao assumir carteira: {e} - Tentando novamente em 60s", exc_info=True)
                await asyncio.sleep(60)

    async def executar_ordem_sniper(self, symbol, preco_entrada_websocket, confianca_ia=0.70, estrategia="scalping_v6"):
        """
        MÉTODO RECALIBRADO: Executa compra com ESCALONAMENTO DE BANCA e STOP LOSS INTELIGENTE.
        """
        pair = f"{symbol}"
        if not pair.endswith("USDT"): pair += "USDT"
        
        try:
            client = await self._get_client()
            
            # 1. Usa sistema de alvos inteligente com stop loss dinâmico
            preco_atual = preco_entrada_websocket
            
            # 2. LÓGICA DE ESCALONAMENTO (O "Pulo do Gato") - OTIMIZADA
            # Banca Ref: $2.355,05 | Entrada Base: $35.00
            entrada_base = self.config.get('entrada_usd', 35.0)
            
            if confianca_ia >= 0.90:
                valor_entrada_final = entrada_base * 2.0  # $70.00 (Sniper Elite)
                peso_mao = "MÃO CHEIA (MAX)"
            elif confianca_ia >= 0.80:
                valor_entrada_final = entrada_base * 1.5  # $52.50 (Forte)
                peso_mao = "MÃO MÉDIA"
            else:
                valor_entrada_final = entrada_base        # $35.00 (Padrão)
                peso_mao = "MÃO CAUTELA"

            # 3. Cálculo de Quantidade com Precisão
            qty_prec = self.precisoes.get(pair, 4)
            quantidade = math.floor((valor_entrada_final / preco_entrada_websocket) * (10**qty_prec)) / (10**qty_prec)

            if quantidade <= 0: 
                logger.warning(f"🚫 Quantidade calculada insuficiente para {pair}")
                return False
            
            # 🆕 Calcula alvos com quantidade para Stop Loss Híbrido
            alvos = self.calcular_alvos(preco_atual, estrategia, symbol, quantidade)
            
            logger.info(f"🎯 Stop Loss Dinâmico: {symbol} | SL: {alvos['sl']:.6f} ({((alvos['sl']/preco_atual)-1)*100:+.2f}%)")

            logger.info(f"🎯 [SNIPER] {pair} | Confiança: {confianca_ia:.2%} | {peso_mao} | Inves: ${valor_entrada_final:.2f}")

            # 4. Envio da Ordem Real
            ordem = await client.order_market_buy(symbol=pair, quantity=quantidade)
            
            # Pega o preço médio de execução real dos fills
            precos_fills = [float(f['price']) for f in ordem.get('fills', [])]
            preco_exec = sum(precos_fills) / len(precos_fills) if precos_fills else preco_entrada_websocket

            # 🚫 NOVA REGRA: Só adiciona ao active_trades se valor >= $1 
            valor_final_posicao = quantidade * preco_exec
            if valor_final_posicao >= 1.0:
                self.active_trades[pair] = {
                    'qty': quantidade,
                    'entry_price': preco_exec,
                    'tp': preco_exec * alvos['tp'],
                    'sl': preco_exec * alvos['sl'],
                    'estrategia': estrategia,
                    'confianca': confianca_ia,
                    'entry_time': datetime.now()
                }
                logger.info(f"✅ {pair} adicionado ao monitoramento (${valor_final_posicao:.2f})")
            else:
                logger.info(f"⚪ {pair} executado mas NÃO monitorado (${valor_final_posicao:.4f} < $1.00)")

            # 📲 Notificação Telegram - COMPRA COM INFO DE STOP LOSS
            valor_investido = quantidade * preco_exec
            sl_pct = ((alvos['sl'] / preco_exec) - 1) * 100
            tp_pct = ((alvos['tp'] / preco_exec) - 1) * 100
            
            # Determina tipo de moeda para notificação
            tipo_moeda = self.get_coin_type_description(symbol)
            
            msg_compra = (
                f"🟢 <b>COMPRA EXECUTADA</b>\n"
                f"💎 Moeda: <b>{pair}</b> {tipo_moeda}\n"
                f"💵 Valor: <b>${valor_investido:.2f} USDT</b> ({peso_mao})\n"
                f"📊 Preço: <b>${preco_exec:.6f}</b>\n"
                f"🎯 Confiança IA: <b>{confianca_ia:.1%}</b>\n"
                f"🛡️ Stop Loss Dinâmico: <b>{sl_pct:+.2f}%</b>\n"
                f"🚀 Take Profit: <b>{tp_pct:+.2f}%</b>\n"
                f"📈 Estratégia: {estrategia}"
            )
            self.enviar_telegram(msg_compra)
            
            # 🎯 Registra no sistema de previsões (assíncrono, não bloqueia)
            if self.monitor_previsoes:
                try:
                    await self.monitor_previsoes.registrar_nova_posicao(pair, preco_exec, datetime.now())
                    logger.info(f"📡 Previsão iniciada para {pair}")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao registrar previsão para {pair}: {e}")

            # Monitor atualiza automaticamente via callback_pnl
            
            return True
            
        except BinanceAPIException as e:
            logger.error(f"❌ Erro Binance na execução {pair}: {e.message}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro geral na execução {pair}: {e}")
            return False

    async def fechar_posicao_parcial(self, pair, quantidade, motivo="VENDA_PARCIAL"):
        """Vende apenas uma parte da posição (venda escalonada)"""
        if pair not in self.active_trades:
            return False
        
        # 🛡️ COOLDOWN: Verifica se houve tentativa recente com erro
        now = datetime.now().timestamp()
        if pair in self._sell_attempts:
            last_attempt = self._sell_attempts[pair].get('last_attempt', 0)
            error_count = self._sell_attempts[pair].get('error_count', 0)
            
            # Se teve erro recente e está em cooldown, não tenta novamente
            if error_count > 0 and (now - last_attempt) < self._sell_cooldown:
                logger.debug(f"⏸️ {pair}: Em cooldown após erro (aguardando {self._sell_cooldown - (now - last_attempt):.1f}s)")
                return False
        
        trade = self.active_trades[pair]
        
        try:
            client = await self._get_client()
            
            # Ajusta quantidade para precisão
            qty_prec = self.precisoes.get(pair, 4)
            quantidade_ajustada = math.floor(quantidade * (10 ** qty_prec)) / (10 ** qty_prec)
            
            if quantidade_ajustada <= 0:
                logger.warning(f"⚠️ {pair}: Quantidade muito pequena para venda parcial ({quantidade})")
                return False
            
            logger.info(f"⚡ [VENDA PARCIAL] Executando {pair} | Qty: {quantidade_ajustada} | Motivo: {motivo}")
            venda = await client.order_market_sell(symbol=pair, quantity=quantidade_ajustada)
            
            # Calcula preço médio de venda
            precos_fills = [float(f['price']) for f in venda.get('fills', [])]
            preco_venda = sum(precos_fills) / len(precos_fills) if precos_fills else 0.0
            
            # Calcula PnL desta venda parcial
            custo = trade['entry_price'] * quantidade_ajustada
            receita = quantidade_ajustada * preco_venda
            lucro_usdt = receita - custo
            lucro_usdt -= (custo + receita) * self.taxa_binance  # Desconta taxas
            lucro_pct = (lucro_usdt / custo) * 100
            
            # 📱 Notifica no Telegram
            emoji = "💰" if lucro_usdt > 0 else "📉"
            pct_posicao = (quantidade_ajustada / trade['qty']) * 100
            msg = f"{emoji} <b>VENDA PARCIAL</b>\n"
            msg += f"🪙 {pair}\n"
            msg += f"📊 {pct_posicao:.0f}% da posição\n"
            msg += f"💵 Lucro: ${lucro_usdt:.2f} ({lucro_pct:+.2f}%)\n"
            msg += f"🎯 Motivo: {motivo}"
            
            await self.enviar_telegram(msg)
            
            logger.info(f"✅ {pair} venda parcial concluída: ${lucro_usdt:.2f} ({lucro_pct:+.2f}%)")
            
            # ✅ Sucesso: Reseta contador de erros
            if pair in self._sell_attempts:
                self._sell_attempts[pair]['error_count'] = 0
            
            return True
            
        except BinanceAPIException as e:
            # 🚨 Registra erro e ativa cooldown
            if pair not in self._sell_attempts:
                self._sell_attempts[pair] = {'last_attempt': 0, 'error_count': 0}
            
            self._sell_attempts[pair]['last_attempt'] = now
            self._sell_attempts[pair]['error_count'] += 1
            
            # Se é erro de saldo ou NOTIONAL, aumenta o cooldown
            if 'insufficient balance' in str(e).lower() or 'NOTIONAL' in str(e):
                logger.error(f"❌ Erro ao fechar parcial {pair}: {e.message} (cooldown de {self._sell_cooldown}s ativado)")
            else:
                logger.error(f"❌ Erro ao fechar parcial {pair}: {e}")
            
            return False
        except Exception as e:
            # 🚨 Registra erro genérico
            if pair not in self._sell_attempts:
                self._sell_attempts[pair] = {'last_attempt': 0, 'error_count': 0}
            
            self._sell_attempts[pair]['last_attempt'] = now
            self._sell_attempts[pair]['error_count'] += 1
            
            logger.error(f"❌ Erro ao fechar parcial {pair}: {e}")
            return False

    async def fechar_posicao(self, pair, motivo):
        """Fecha posição e reporta lucro líquido - com ajuste de LOT_SIZE."""
        if pair not in self.active_trades:
            return
        
        # 🛡️ COOLDOWN: Verifica se houve tentativa recente com erro
        now = datetime.now().timestamp()
        if pair in self._sell_attempts:
            last_attempt = self._sell_attempts[pair].get('last_attempt', 0)
            error_count = self._sell_attempts[pair].get('error_count', 0)
            
            # Se teve erro recente e está em cooldown, não tenta novamente
            if error_count > 0 and (now - last_attempt) < self._sell_cooldown:
                logger.debug(f"⏸️ {pair}: Em cooldown após erro (aguardando {self._sell_cooldown - (now - last_attempt):.1f}s)")
                return
        
        trade = self.active_trades[pair]
        
        try:
            client = await self._get_client()
            
            # 🔧 Ajusta quantidade para o LOT_SIZE mínimo da Binance
            quantidade_ajustada = trade['qty']
            qty_prec = self.precisoes.get(pair, 4)  # Pega precisão como int
            
            # Arredonda para a precisão correta
            quantidade_ajustada = math.floor(quantidade_ajustada * (10**qty_prec)) / (10**qty_prec)
            
            if quantidade_ajustada <= 0:
                logger.warning(f"⚠️ {pair}: Quantidade {quantidade_ajustada:.8f} insuficiente - Pulando venda")
                return
            
            venda = await client.order_market_sell(symbol=pair, quantity=quantidade_ajustada)
            
            precos_fills = [float(f['price']) for f in venda.get('fills', [])]
            preco_venda = sum(precos_fills) / len(precos_fills) if precos_fills else 0.0
            
            # Cálculo de PnL descontando taxas estimadas de ida e volta
            investido = trade['qty'] * trade['entry_price']
            retornado = trade['qty'] * preco_venda
            pnl_liquido = retornado - investido
            pnl_liquido -= (investido + retornado) * self.taxa_binance
            pnl_pct = (pnl_liquido / investido) * 100 if investido > 0 else 0

            logger.info(f"💰 {pair} fechado ({motivo}). PnL: ${pnl_liquido:.2f}")

            # 📲 Notificação Telegram - VENDA COMPLETA
            emoji = "💰" if pnl_liquido > 0 else "📉"
            msg_venda = (
                f"{emoji} <b>VENDA COMPLETA</b>\n"
                f"💎 Moeda: <b>{pair}</b>\n"
                f"💰 Lucro: <b>${pnl_liquido:+.2f} USDT ({pnl_pct:+.2f}%)</b>\n"
                f"📊 Preço Venda: <b>${preco_venda:.6f}</b>\n"
                f"📈 Preço Compra: ${trade['entry_price']:.6f}\n"
                f"🎯 Motivo: {motivo}"
            )
            self.enviar_telegram(msg_venda)

            if self.callback_pnl:
                await self.callback_pnl(pair, pnl_liquido, trade['estrategia'])
            
            # 🎯 Registra venda no histórico de previsões
            if self.monitor_previsoes:
                await self.monitor_previsoes.registrar_venda(pair, preco_venda, pnl_pct, motivo)

            # ✅ Sucesso: Reseta contador de erros e remove posição
            if pair in self._sell_attempts:
                del self._sell_attempts[pair]
            if pair in self._trailing_checks:
                logger.info(f"📊 {pair}: Finalizado após {self._trailing_checks[pair]} verificações de trailing")
                del self._trailing_checks[pair]
            
            del self.active_trades[pair]
            
        except BinanceAPIException as e:
            # 🚨 Registra erro e ativa cooldown
            if pair not in self._sell_attempts:
                self._sell_attempts[pair] = {'last_attempt': 0, 'error_count': 0}
            
            self._sell_attempts[pair]['last_attempt'] = now
            self._sell_attempts[pair]['error_count'] += 1
            
            # Se é erro de saldo, aumenta o cooldown e para de tentar
            if 'insufficient balance' in str(e).lower():
                logger.error(f"❌ Erro Binance ao fechar {pair}: {e.message} (posição possivelmente já vendida)")
                # Remove da lista para evitar tentativas futuras
                if pair in self.active_trades:
                    del self.active_trades[pair]
                if pair in self._sell_attempts:
                    del self._sell_attempts[pair]
                if pair in self._trailing_checks:
                    del self._trailing_checks[pair]
            else:
                logger.error(f"❌ Erro Binance ao fechar {pair}: {e.message} (cooldown de {self._sell_cooldown}s)")
                
        except Exception as e:
            # 🚨 Registra erro genérico
            if pair not in self._sell_attempts:
                self._sell_attempts[pair] = {'last_attempt': 0, 'error_count': 0}
            
            self._sell_attempts[pair]['last_attempt'] = now
            self._sell_attempts[pair]['error_count'] += 1
            
            logger.error(f"❌ Erro ao fechar {pair}: {e}")

    async def gerenciar_trailing_stop(self, pair, preco_atual):
        """
        🛡️ SAÍDA INTELIGENTE DINÂMICA - Sistema Híbrido Profissional
        
        NOVO: Adapta estratégia baseado em:
        1. Categoria do ativo (LARGE_CAP, MEME, DEFI, etc)
        2. Tempo na posição (custo de oportunidade)
        3. Venda escalonada (25% incremental)
        4. Análise de exaustão técnica
        """
        if pair not in self.active_trades: 
            return False
        
        trade = self.active_trades[pair]
        lucro_atual = (preco_atual / trade['entry_price']) - 1
        
        # ⏱️ Calcula tempo na posição em segundos e horas
        tempo_entrada = trade.get('entry_time', datetime.now())
        if isinstance(tempo_entrada, str):
            tempo_entrada = datetime.fromisoformat(tempo_entrada)
        segundos_posicao = (datetime.now() - tempo_entrada).total_seconds()
        horas_posicao = segundos_posicao / 3600
        
        # 🛡️ PROTEÇÃO: Tempo mínimo de holding (30 segundos)
        # Evita vender imediatamente após compra
        tempo_minimo_holding = 30  # segundos
        if segundos_posicao < tempo_minimo_holding:
            # Só permite venda se perda extrema (> 5%)
            if lucro_atual < -0.05:
                logger.warning(f"⚠️ {pair}: Venda antecipada por perda extrema {lucro_atual:.2%} em {segundos_posicao:.0f}s")
            else:
                logger.debug(f"⏸️ {pair}: Aguardando tempo mínimo ({segundos_posicao:.0f}s/{tempo_minimo_holding}s)")
                return False
        
        horas_posicao = segundos_posicao / 3600
        
        # 🛑 PROTEÇÃO 1: PERDA MÁXIMA PERMITIDA
        max_loss_pct = float(os.getenv('R7_MAX_LOSS_PCT', '8.0')) / 100  # Default: -8%
        if lucro_atual <= -max_loss_pct:
            logger.warning(f"🛑 [STOP LOSS MÁXIMO] {pair} | Perda: {lucro_atual:.2%} >= {max_loss_pct:.1%} | Fechando posição!")
            await self.fechar_posicao(pair, f"STOP_LOSS_MAX_{max_loss_pct*100:.1f}%")
            return True
        
        # ⏰ PROTEÇÃO 2: TEMPO MÁXIMO DE PERMANÊNCIA
        max_hold_hours = float(os.getenv('R7_MAX_HOLD_HOURS', '72'))  # Default: 72h (3 dias)
        if horas_posicao >= max_hold_hours:
            if lucro_atual >= 0:
                logger.info(f"⏰ [TIMEOUT LUCRATIVO] {pair} | {horas_posicao:.1f}h | Lucro: {lucro_atual:.2%} | Fechando!")
                await self.fechar_posicao(pair, f"TIMEOUT_PROFIT_{horas_posicao:.0f}h")
            else:
                logger.warning(f"⏰ [TIMEOUT PREJUÍZO] {pair} | {horas_posicao:.1f}h | Perda: {lucro_atual:.2%} | Fechando!")
                await self.fechar_posicao(pair, f"TIMEOUT_LOSS_{horas_posicao:.0f}h")
            return True
        
        # 🚀 PROTEÇÃO 3: LUCRO RÁPIDO (Se configurado)
        quick_profit_pct = float(os.getenv('R7_QUICK_PROFIT_PCT', '0')) / 100  # Default: desabilitado
        if quick_profit_pct > 0 and lucro_atual >= quick_profit_pct and horas_posicao <= 4:
            logger.info(f"🚀 [LUCRO RÁPIDO] {pair} | {horas_posicao:.1f}h | Lucro: {lucro_atual:.2%} | Fechando!")
            await self.fechar_posicao(pair, f"QUICK_PROFIT_{lucro_atual*100:.1f}%")
            return True
        
        # 📊 Contador de verificações
        if pair not in self._trailing_checks:
            self._trailing_checks[pair] = 0
        self._trailing_checks[pair] += 1
        
        # Log a cada 100 verificações
        if self._trailing_checks[pair] % 100 == 0:
            logger.info(f"📊 {pair}: {self._trailing_checks[pair]} verificações | {horas_posicao:.1f}h | Lucro: {lucro_atual:.2%}")
        
        # 📊 Classifica ativo e obtém configurações dinâmicas
        asset_config = self.asset_classifier.classify(pair)
        
        # ⏱️ Converte horas para dias para compatibilidade
        dias_posicao = horas_posicao / 24.0
        
        # 🎯 Obtém estratégia de saída dinâmica
        exit_strategy = self.asset_classifier.get_exit_strategy(pair, lucro_atual, dias_posicao)
        
        logger.info(f"📊 [{asset_config['category']}] {pair} | Lucro: {lucro_atual:.2%} | Dias: {dias_posicao:.1f} | Ação: {exit_strategy['action']}")
        
        # 🎯 NÍVEL 1: VENDA ESCALONADA (Sistema Profissional)
        if exit_strategy['action'] in ['SELL_75PCT', 'SELL_PARTIAL']:
            # Calcula quanto vender (25%, 50%, 75% ou 100%)
            pct_to_sell = self.scaled_exit.get_sell_percentage(pair, lucro_atual, asset_config)
            
            if pct_to_sell > 0:
                # Venda parcial
                quantidade_vender = trade['qty'] * pct_to_sell
                logger.info(f"💰 [VENDA ESCALONADA] {pair} | Vendendo {pct_to_sell*100:.0f}% | Lucro: {lucro_atual:.2%}")
                
                # Executa venda parcial
                success = await self.fechar_posicao_parcial(pair, quantidade_vender, exit_strategy['reason'])
                
                if success:
                    # Atualiza quantidade restante
                    trade['qty'] -= quantidade_vender
                    
                    # Se vendeu tudo, remove da lista
                    if trade['qty'] <= 0.01:  # Margem de segurança
                        logger.info(f"✅ {pair} vendido completamente via escalonamento")
                        self.scaled_exit.reset_position(pair)
                        del self.active_trades[pair]
                        return True
                
                return success
        
        # 🎯 NÍVEL 2: ANÁLISE DE EXAUSTÃO (Se lucro >= tp_min)
        # 🎯 NÍVEL 2: ANÁLISE DE EXAUSTÃO (Se lucro >= tp_min)
        if lucro_atual >= asset_config['tp_min']:
            # Verifica se deve manter ou vender baseado em indicadores
            if self.analista:
                decisao = await asyncio.to_thread(
                    self.analista.avaliar_exaustao, pair, preco_atual
                )
                
                if decisao == "VENDER":
                    logger.info(f"💰 [EXAUSTÃO DETECTADA] {pair} | Lucro: {lucro_atual:.2%} | Vendendo restante!")
                    await self.fechar_posicao(pair, "TP_EXAUSTAO")
                    self.scaled_exit.reset_position(pair)
                    return True
                elif decisao == "MANTER":
                    logger.info(f"🚀 [FORÇA DETECTADA] {pair} | Lucro: {lucro_atual:.2%} | Mantendo (RSI<70, EMA5↑)")
                    # Ativa trailing agressivo para proteger
                    novo_sl = preco_atual * (1 - asset_config['trailing_pct'])
                    if novo_sl > trade['sl']:
                        trade['sl'] = novo_sl
            else:
                # Fallback: Sem analista, vende no TP
                logger.info(f"💰 [TAKE PROFIT] {pair} | Lucro: {lucro_atual:.2%}")
                await self.fechar_posicao(pair, f"TP_{asset_config['tp_min']*100:.1f}%")
                self.scaled_exit.reset_position(pair)
                return True
        
        # 🛡️ NÍVEL 3: TRAILING STOP DINÂMICO (baseado em categoria)
        elif exit_strategy['action'] == 'TRAILING_ACTIVE':
            trailing_distance = asset_config['trailing_pct']
            novo_sl = preco_atual * (1 - trailing_distance)
            if novo_sl > trade['sl']:
                trade['sl'] = novo_sl
                logger.debug(f"📈 [TRAILING {asset_config['category']}] {pair} | Lucro: {lucro_atual:.2%} | Novo SL: {novo_sl:.4f} (-{trailing_distance*100:.1f}%)")
        
        # 🛑 Verifica se atingiu Stop Loss
        if preco_atual <= trade['sl']:
            logger.warning(f"🛑 [STOP LOSS ATINGIDO] {pair} | Preço: ${preco_atual:.4f} <= SL: ${trade['sl']:.4f}")
            
            # 🧠 DECISÃO INTELIGENTE: Vender ou Renovar?
            if self.cerebro_stop_loss:
                try:
                    # Busca buffer de preços (se disponível)
                    buffer_precos = []
                    if self.monitor and hasattr(self.monitor, 'buffers'):
                        buffer_precos = self.monitor.buffers.get(pair, [])
                    
                    # Consulta o cérebro
                    decisao_cerebro = self.cerebro_stop_loss.decidir_venda_ou_renovacao(
                        symbol=pair,
                        preco_atual=preco_atual,
                        preco_entrada=trade['entry_price'],
                        buffer_precos=buffer_precos if buffer_precos else [preco_atual],
                        tempo_posicao_horas=horas_posicao
                    )
                    
                    if decisao_cerebro['decisao'] == 'RENOVAR':
                        # 🔄 RENOVAÇÃO: Ajusta Stop Loss e mantém posição
                        # Calcula novo stop loss 3% abaixo do atual
                        novo_sl = preco_atual * 0.97
                        perda_atual = ((preco_atual - trade['entry_price']) / trade['entry_price']) * 100
                        
                        logger.info(f"🔄 [RENOVAÇÃO] {pair} | Cérebro detectou reversão provável!")
                        logger.info(f"   📊 RSI: {decisao_cerebro['features'].get('rsi', 0):.1f}")
                        logger.info(f"   💡 Motivo: {decisao_cerebro['motivo']}")
                        logger.info(f"   🎯 Confiança: {decisao_cerebro['confianca']:.1%}")
                        logger.info(f"   📉 Perda atual: {perda_atual:.2f}%")
                        logger.info(f"   🛡️ Novo SL: ${novo_sl:.4f} (-3.0%)")
                        
                        # Atualiza stop loss
                        trade['sl'] = novo_sl
                        
                        # Marca que renovação foi feita (evita renovar múltiplas vezes)
                        if 'renovacoes' not in trade:
                            trade['renovacoes'] = 0
                        trade['renovacoes'] += 1
                        
                        # Limite de renovações (máximo 2x por posição)
                        if trade['renovacoes'] >= 2:
                            logger.warning(f"⚠️ {pair}: Limite de renovações atingido (2x) - Próximo stop será final")
                            trade['renovacao_desabilitada'] = True
                        
                        # 📲 Notifica no Telegram
                        msg_renovacao = (
                            f"🔄 <b>STOP LOSS RENOVADO</b>\n"
                            f"💎 {pair}\n"
                            f"📊 RSI: {decisao_cerebro['features'].get('rsi', 0):.1f}\n"
                            f"💡 {decisao_cerebro['motivo']}\n"
                            f"🎯 Confiança: {decisao_cerebro['confianca']:.1%}\n"
                            f"📉 Perda atual: {perda_atual:.2f}%\n"
                            f"🛡️ Novo SL: ${novo_sl:.4f}"
                        )
                        self.enviar_telegram(msg_renovacao)
                        
                        return False  # Não fecha posição
                        
                    else:
                        # ❌ VENDER: Cérebro confirma a queda
                        logger.warning(f"❌ [VENDA CONFIRMADA] {pair} | Cérebro confirmou tendência de queda")
                        logger.warning(f"   💡 Motivo: {decisao_cerebro['motivo']}")
                        logger.warning(f"   🎯 Confiança: {decisao_cerebro['confianca']:.1%}")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao consultar Cérebro para {pair}: {e}")
                    # Em caso de erro, vende por segurança
                    pass
            
            # Vende posição (ou se cérebro não disponível, ou se decidiu vender)
            await self.fechar_posicao(pair, "STOP_LOSS")
            self.scaled_exit.reset_position(pair)
            return True
        
        return False

    async def fechar_todos_clientes(self):
        if self.client:
            await self.client.close_connection()
            self.client = None