import asyncio
import os
import logging
import math
from binance.client import Client
from binance.exceptions import BinanceAPIException

logger = logging.getLogger('executor')

class ExecutorBot:
    def __init__(self, config):
        self.config = config
        from tools.binance_wrapper import get_binance_client
        self.client = get_binance_client()
        self.active_trades = {}
        self.callback_pnl = None
        self.real_trading = os.getenv('REAL_TRADING', '0') == '1'
        self._monitor_tasks = {}

    def get_symbol_precision(self, symbol):
        """Busca as regras de lot size e tick size da Binance."""
        try:
            info = self.client.get_symbol_info(symbol)
            lot_filter = next((f for f in info.get('filters', []) if f.get('filterType') == 'LOT_SIZE'), None)
            price_filter = next((f for f in info.get('filters', []) if f.get('filterType') == 'PRICE_FILTER'), None)
            def decimals_from_step(step):
                s = str(step)
                if '.' in s:
                    return max(0, len(s.split('.')[-1].rstrip('0')))
                return 0
            qty_precision = decimals_from_step(lot_filter.get('stepSize')) if lot_filter else 8
            price_precision = decimals_from_step(price_filter.get('tickSize')) if price_filter else 8
            return qty_precision, price_precision
        except Exception as e:
            logger.error(f"Erro ao obter precisão para {symbol}: {e}")
            return 2, 4

    # Small compatibility helpers used by tools/check_executor.py
    @property
    def binance_client(self):
        return self.client

    def get_usdt_brl_rate(self):
        try:
            t = self.client.get_symbol_ticker(symbol='USDTBRL')
            return float(t.get('price') or 0)
        except Exception as e:
            logger.error('Erro get_usdt_brl_rate: %s', e)
            raise

    def obter_saldo_real_spot(self, guardiao):
        try:
            acct = self.client.get_account()
            balances = acct.get('balances', [])
            usdt = next((float(b.get('free') or 0) for b in balances if b.get('asset') == 'USDT'), 0.0)
            return usdt
        except Exception as e:
            logger.error('Erro obter_saldo_real_spot: %s', e)
            raise

    @property
    def usdt_margin(self):
        return float(self.config.get('config_trade', {}).get('usdt_margin', 0))

    @property
    def usdt_available(self):
        try:
            return self.obter_saldo_real_spot(None)
        except Exception:
            return 0.0

    async def executar_ordem(self, symbol, dados_trade):
        pair = f"{symbol}USDT"
        try:
            info = self.client.get_symbol_info(pair)
            lot = next((f for f in info.get('filters', []) if f.get('filterType') == 'LOT_SIZE'), None)
            notional = next((f for f in info.get('filters', []) if f.get('filterType') in ('MIN_NOTIONAL', 'NOTIONAL')), None)
            step = float(lot.get('stepSize', '1')) if lot else 1
            min_qty = float(lot.get('minQty', '0')) if lot else 0
            min_notional = float(notional.get('minNotional') or 0) if notional else 0

            qty_prec, price_prec = self.get_symbol_precision(pair)
            ticker = self.client.get_symbol_ticker(symbol=pair)
            preco_atual = float(ticker['price'])
            entrada_usd = float(dados_trade.get('entrada_usd', 100.0))
            raw_qty = entrada_usd / preco_atual if preco_atual else 0

            # floor to step
            quant = math.floor(raw_qty / step) * step
            quantidade = round(quant, qty_prec)
            if quantidade < min_qty:
                logger.warning('Quantidade %s abaixo do min_qty %s para %s', quantidade, min_qty, pair)
                return False
            if min_notional and (quantidade * preco_atual) < min_notional:
                logger.warning('Ordem abaixo do min_notional para %s: qty=%s price=%s min_not=%s', pair, quantidade, preco_atual, min_notional)
                return False

            if self.real_trading:
                ordem = self.client.order_market_buy(symbol=pair, quantity=str(quantidade))
                fills = ordem.get('fills') or []
                filled_qty = sum(float(f.get('qty') or 0) for f in fills)
                if filled_qty <= 0:
                    filled_qty = float(ordem.get('executedQty') or 0)
                avg_price = 0.0
                if fills:
                    total = sum(float(f.get('qty') or 0) * float(f.get('price') or 0) for f in fills)
                    avg_price = (total / filled_qty) if filled_qty else 0.0
                else:
                    avg_price = float(ordem.get('fills', [{}])[0].get('price') or preco_atual)

                if filled_qty > 0:
                    preco_exec = avg_price or preco_atual
                    tp = round(preco_exec * (1 + float(dados_trade.get('tp_pct', 1))/100), price_prec)
                    sl = round(preco_exec * (1 - float(dados_trade.get('sl_pct', 1))/100), price_prec)
                    self.active_trades[pair] = {
                        'symbol': symbol,
                        'qty': filled_qty,
                        'entry': preco_exec,
                        'tp': tp,
                        'sl': sl,
                        'estrategia': dados_trade.get('estrategia')
                    }
                    # create and store monitor task
                    task = asyncio.create_task(self._monitorar_saida(pair))
                    self._monitor_tasks[pair] = task
                    return True
            else:
                # simulated mode: register fake trade using current price
                preco_exec = preco_atual
                tp = round(preco_exec * (1 + float(dados_trade.get('tp_pct', 1))/100), price_prec)
                sl = round(preco_exec * (1 - float(dados_trade.get('sl_pct', 1))/100), price_prec)
                self.active_trades[pair] = {
                    'symbol': symbol,
                    'qty': quantidade,
                    'entry': preco_exec,
                    'tp': tp,
                    'sl': sl,
                    'estrategia': dados_trade.get('estrategia')
                }
                task = asyncio.create_task(self._monitorar_saida(pair))
                self._monitor_tasks[pair] = task
                return True
            return False
        except Exception as e:
            logger.exception('Erro no Executor ao executar_ordem: %s', e)
            return False

    async def _monitorar_saida(self, pair):
        try:
            while pair in self.active_trades:
                trade = self.active_trades.get(pair)
                ticker = self.client.get_symbol_ticker(symbol=pair)
                preco_atual = float(ticker['price'])
                if preco_atual >= trade['tp'] or preco_atual <= trade['sl']:
                    await self.fechar_posicao(pair, "ALVO/STOP ATINGIDO")
                    break
                await asyncio.sleep(2)
        except Exception as e:
            logger.exception('Erro no monitorar_saida para %s: %s', pair, e)
            await asyncio.sleep(10)

    async def fechar_lucros_preventivo(self):
        """Vende apenas se o lucro cobrir as taxas (mínimo 0.25%)."""
        logger.info("[LIMPEZA] Analisando lucros reais após taxas...")
        copia_trades = list(self.active_trades.keys())
        for pair in copia_trades:
            trade = self.active_trades[pair]
            ticker = self.client.get_symbol_ticker(symbol=pair)
            preco_atual = float(ticker['price'])
            lucro_bruto_pct = ((preco_atual / trade['entry']) - 1) * 100
            
            if lucro_bruto_pct > 0.25: # Cobre 0.2% de taxas + margem
                await self.fechar_posicao(pair, "LIMPEZA DIÁRIA (LUCRO REAL)")

    async def fechar_posicao(self, pair, motivo):
        trade = self.active_trades.get(pair)
        if not trade:
            return
        try:
            venda = self.client.order_market_sell(symbol=pair, quantity=str(trade['qty']))
            fills = venda.get('fills') or []
            filled_qty = sum(float(f.get('qty') or 0) for f in fills)
            if filled_qty <= 0:
                filled_qty = float(venda.get('executedQty') or 0)
            avg_price = 0.0
            if fills and filled_qty:
                total = sum(float(f.get('qty') or 0) * float(f.get('price') or 0) for f in fills)
                avg_price = total / filled_qty
            else:
                avg_price = float(venda.get('fills', [{}])[0].get('price') or trade['entry'])

            pnl = (avg_price - trade['entry']) * filled_qty
            if self.callback_pnl:
                await self.callback_pnl(pair, pnl, trade.get('estrategia'))
            # cleanup
            try:
                del self.active_trades[pair]
            except KeyError:
                pass
            task = self._monitor_tasks.pop(pair, None)
            if task and not task.done():
                task.cancel()
        except Exception as e:
            logger.exception('Erro ao fechar %s: %s', pair, e)

    async def mover_lucro_para_earn(self, valor_usdt):
        """Envia o lucro líquido para o Binance Earn."""
        if not self.real_trading or valor_usdt < 1.0: return
        try:
            self.client._post('simple-earn/flexible/subscribe', True, data={'productId': 'USDT001', 'amount': round(valor_usdt, 2)})
            logger.info(f"Tesoureiro: ${valor_usdt:.2f} protegidos no Earn.")
        except Exception as e: logger.error(f"Erro no Tesoureiro: {e}")