import asyncio
import os
import logging
import math
from binance.exceptions import BinanceAPIException
from utils.binance_retry import retry_api_call
from ia_engine import IAEngine
from bots.monthly_stats import add_profit_by_strategy
import pandas as pd

logger = logging.getLogger('executor')

class ExecutorBot:
    def __init__(self, config, monitor=None, estrategista=None):
        self.config = config
        self.monitor = monitor
        self.estrategista = estrategista
        from tools.binance_wrapper import get_binance_client
        self.client = get_binance_client()
        self.active_trades = {}
        self.callback_pnl = None
        self.real_trading = os.getenv('REAL_TRADING', '0') == '1'
        self.ia = IAEngine()
        self.ia_threshold = 0.65 
        self._sell_checker_task = None

    def start_sell_checker(self):
        if self._sell_checker_task is None or self._sell_checker_task.done():
            self._sell_checker_task = asyncio.create_task(self._global_sell_checker())

    async def _global_sell_checker(self):
        while True:
            try:
                if not self.active_trades:
                    await asyncio.sleep(5)
                    continue
                for pair in list(self.active_trades.keys()):
                    await self._check_sell_conditions(pair)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Erro no verificador de vendas: {e}")
                await asyncio.sleep(5)

    async def _check_sell_conditions(self, pair):
        trade = self.active_trades.get(pair)
        if not trade: return
        try:
            ticker = await retry_api_call(lambda: self.client.get_symbol_ticker(symbol=pair))
            preco_atual = float(ticker['price'])
            
            # Trava de Breakeven (+0.05% para pagar taxas)
            lucro_atual_perc = (preco_atual - trade['entry']) / trade['entry']
            if lucro_atual_perc >= 0.0025 and not trade['breakeven_ativo']:
                self.active_trades[pair]['sl'] = trade['entry'] * 1.0005
                self.active_trades[pair]['breakeven_ativo'] = True
                logger.info(f"🛡️ {pair}: Breakeven ativado.")

            # Saída por Stop ou Take Profit
            if preco_atual >= trade['tp']:
                await self.fechar_posicao(pair, "TAKE PROFIT")
            elif preco_atual <= trade['sl']:
                await self.fechar_posicao(pair, "STOP LOSS")
        except Exception as e:
            logger.error(f"Erro ao verificar {pair}: {e}")

    async def executar_ordem(self, symbol, dados_trade):
        pair = f"{symbol}USDT"
        try:
            qty_prec, price_prec = await self.get_symbol_precision(pair)
            ticker = await retry_api_call(lambda: self.client.get_symbol_ticker(symbol=pair))
            preco_atual = float(ticker['price'])

            # IA Check (Rigor 0.65)
            if 'ia_features' in dados_trade:
                prob = self.ia.predict(dados_trade['ia_features'])
                if prob < self.ia_threshold: return False

            # Posicionamento Fixo $25.00
            pos_size_usd = 25.00 
            quantidade = math.floor((pos_size_usd / preco_atual) * (10**qty_prec)) / (10**qty_prec)

            if self.real_trading:
                ordem = await retry_api_call(lambda: self.client.order_market_buy(symbol=pair, quantity=f"{quantidade:.{qty_prec}f}"))
                avg_price = float(ordem['fills'][0]['price']) if ordem.get('fills') else preco_atual
                filled_qty = float(ordem.get('executedQty', quantidade))
            else:
                avg_price, filled_qty = preco_atual, quantidade

            self.active_trades[pair] = {
                'symbol': symbol, 'qty': filled_qty, 'entry': avg_price,
                'tp': round(dados_trade['tp'], price_prec), 'sl': round(dados_trade['sl'], price_prec),
                'estrategia': dados_trade.get('estrategia'), 'breakeven_ativo': False, 'qty_prec': qty_prec
            }
            self.start_sell_checker()
            return True
        except Exception as e:
            logger.error(f"Erro ao abrir {pair}: {e}")
            return False

    async def fechar_posicao(self, pair, motivo):
        trade = self.active_trades.get(pair)
        if not trade: return
        try:
            if self.real_trading:
                await retry_api_call(lambda: self.client.order_market_sell(symbol=pair, quantity=f"{trade['qty']:.{trade['qty_prec']}f}"))
            
            ticker = await retry_api_call(lambda: self.client.get_symbol_ticker(symbol=pair))
            preco_venda = float(ticker['price'])
            # Cálculo de PnL Real (Descontando 0.1% de taxa de compra e venda)
            pnl_bruto = (preco_venda - trade['entry']) * trade['qty']
            taxas = (trade['entry'] * trade['qty'] * 0.001) + (preco_venda * trade['qty'] * 0.001)
            pnl_liquido = pnl_bruto - taxas
            
            add_profit_by_strategy(pnl_liquido, trade['estrategia'])
            if self.callback_pnl: await self.callback_pnl(pair, pnl_liquido, trade['estrategia'])
            del self.active_trades[pair]
            logger.info(f"💰 {pair} Fechado | PnL Líquido: ${pnl_liquido:.2f} | Motivo: {motivo}")
        except Exception as e:
            logger.error(f"Erro ao fechar {pair}: {e}")

    async def get_symbol_precision(self, symbol):
        try:
            info = await retry_api_call(lambda: self.client.get_symbol_info(symbol))
            step_size = next(f['stepSize'] for f in info['filters'] if f['filterType'] == 'LOT_SIZE')
            tick_size = next(f['tickSize'] for f in info['filters'] if f['filterType'] == 'PRICE_FILTER')
            return abs(len(str(float(step_size)).split('.')[-1].rstrip('0'))), abs(len(str(float(tick_size)).split('.')[-1].rstrip('0')))
        except: return 2, 4

    async def executar_compra_sniper(self, symbol, preco_atual):
        """
        Executa compra em modo sniper baseada no WebSocket.
        """
        # Lógica para executar compra imediata
        dados_trade = {
            'tp': preco_atual * 1.012,  # 1.2% take profit
            'sl': preco_atual * 0.992,  # 0.8% stop loss
            'estrategia': 'sniper_websocket'
        }
        await self.executar_ordem(symbol, dados_trade)

    async def executar_venda_sniper(self, symbol, preco_atual):
        """
        Executa venda em modo sniper baseada no WebSocket.
        """
        pair = f"{symbol}USDT"
        if pair in self.active_trades:
            await self.fechar_posicao(pair, "SNIPER_VENDA")

    async def comprar_market(self, symbol):
        """
        Compra market order para sniper.
        """
        dados_trade = {
            'tp': None,  # Definir TP dinâmico se necessário
            'sl': None,  # Definir SL dinâmico
            'estrategia': 'sniper_market'
        }
        await self.executar_ordem(symbol, dados_trade)

    async def vender_market(self, symbol):
        """
        Vende market order para sniper.
        """
        pair = f"{symbol}USDT"
        if pair in self.active_trades:
            await self.fechar_posicao(pair, "SNIPER_VENDA_MARKET")

    async def executar_ordem_sniper(self, symbol, preco_entrada_websocket, forca_sinal=1.0, estrategia="scalping_v6"):
        """
        preco_entrada_websocket: Preço atual
        forca_sinal: Multiplicador vindo da IA (ex: 1.0 a 2.0)
        estrategia: Estratégia escolhida ('scalping_v6', 'momentum_boost', 'swing_rwa')
        """
        pair = f"{symbol}"
        if not pair.endswith("USDT"): pair += "USDT"
        
        try:
            qty_prec, price_prec = await self.get_symbol_precision(pair)
            
            # LÓGICA DINÂMICA:
            # Se o sinal for forte, ele sobe a entrada. 
            # Se for normal, usa o mínimo seguro (ex: $50) para evitar o prejuízo que você teve com $25.
            base_entrada = self.config.get('entrada_usd', 50.0)
            valor_entrada_final = base_entrada * forca_sinal
            
            # Garante que não ultrapasse um teto de segurança (ex: $150 por trade)
            valor_entrada_final = min(valor_entrada_final, 150.0)

            quantidade = math.floor((valor_entrada_final / preco_entrada_websocket) * (10**qty_prec)) / (10**qty_prec)

            logger.info(f"🎯 [SNIPER DINÂMICO] {pair} | Entrada: ${valor_entrada_final:.2f} | Sinal: {forca_sinal} | Estratégia: {estrategia}")

            # Execução
            if self.real_trading:
                ordem = await retry_api_call(lambda: self.client.order_market_buy(symbol=pair, quantity=f"{quantidade:.{qty_prec}f}"))
                avg_price = float(ordem['fills'][0]['price']) if ordem.get('fills') else preco_entrada_websocket
                filled_qty = float(ordem.get('executedQty', quantidade))
            else:
                avg_price, filled_qty = preco_entrada_websocket, quantidade

            # TP/SL baseados na estratégia
            config_estat = {
                "scalping_v6": {"tp": 1.012, "sl": 0.992},  # 1.2% TP, 0.8% SL
                "momentum_boost": {"tp": 1.020, "sl": 0.990},  # 2.0% TP, 1.0% SL
                "swing_rwa": {"tp": 1.045, "sl": 0.980}  # 4.5% TP, 2.0% SL
            }
            niveis = config_estat.get(estrategia, {"tp": 1.012, "sl": 0.992})  # Fallback

            self.active_trades[pair] = {
                'symbol': symbol, 'qty': filled_qty, 'entry': avg_price,
                'tp': round(avg_price * niveis['tp'], price_prec), 
                'sl': round(avg_price * niveis['sl'], price_prec),
                'estrategia': estrategia, 'breakeven_ativo': False, 'qty_prec': qty_prec
            }
            self.start_sell_checker()
            return True
        except Exception as e:
            logger.error(f"Erro ao executar sniper {pair}: {e}")
            return False