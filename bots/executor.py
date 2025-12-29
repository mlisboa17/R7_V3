import asyncio
import os
import logging
import math
from binance.client import Client
from binance.exceptions import BinanceAPIException
from utils.binance_retry import retry_api_call

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
            info = retry_api_call(lambda: self.client.get_symbol_info(symbol))
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
            t = retry_api_call(lambda: self.client.get_symbol_ticker(symbol='USDTBRL'))
            return float(t.get('price') or 0)
        except Exception as e:
            logger.error('Erro get_usdt_brl_rate: %s', e)
            raise

    def obter_saldo_real_spot(self, guardiao):
        try:
            acct = retry_api_call(lambda: self.client.get_account())
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
            info = retry_api_call(lambda: self.client.get_symbol_info(pair))
            lot = next((f for f in info.get('filters', []) if f.get('filterType') == 'LOT_SIZE'), None)
            notional = next((f for f in info.get('filters', []) if f.get('filterType') in ('MIN_NOTIONAL', 'NOTIONAL')), None)
            step = float(lot.get('stepSize', '1')) if lot else 1
            min_qty = float(lot.get('minQty', '0')) if lot else 0
            min_notional = float(notional.get('minNotional') or 0) if notional else 0

            qty_prec, price_prec = self.get_symbol_precision(pair)
            ticker = retry_api_call(lambda: self.client.get_symbol_ticker(symbol=pair))
            preco_atual = float(ticker['price'])

            # --- POSITION SIZING DINÂMICO ---
            if 'position_size' in dados_trade:
                raw_qty = float(dados_trade['position_size'])
            else:
                entrada_usd = float(dados_trade.get('entrada_usd', 100.0))
                raw_qty = entrada_usd / preco_atual if preco_atual else 0

            quant = math.floor(raw_qty / step) * step
            quantidade = round(quant, qty_prec)
            if quantidade < min_qty:
                logger.warning('Quantidade %s abaixo do min_qty %s para %s', quantidade, min_qty, pair)
                return False
            if min_notional and (quantidade * preco_atual) < min_notional:
                logger.warning('Ordem abaixo do min_notional para %s: qty=%s price=%s min_not=%s', pair, quantidade, preco_atual, min_notional)
                return False

            # --- EXECUÇÃO REAL OU SIMULADA ---
            if self.real_trading:
                ordem = retry_api_call(lambda: self.client.order_market_buy(symbol=pair, quantity=str(quantidade)))
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

                taxa = 0.001
                preco_compra_com_taxa = avg_price * (1 + taxa)

                if filled_qty > 0:
                    preco_exec = avg_price or preco_atual
                    # --- STOPS DINÂMICOS ---
                    if 'tp' in dados_trade and 'sl' in dados_trade:
                        tp = round(float(dados_trade['tp']), price_prec)
                        sl = round(float(dados_trade['sl']), price_prec)
                    else:
                        tp = round(preco_exec * (1 + float(dados_trade.get('tp_pct', 1))/100), price_prec)
                        sl = round(preco_exec * (1 - float(dados_trade.get('sl_pct', 1))/100), price_prec)
                    self.active_trades[pair] = {
                        'symbol': symbol,
                        'qty': filled_qty,
                        'entry': preco_exec,
                        'entry_with_fee': preco_compra_com_taxa,
                        'tp': tp,
                        'sl': sl,
                        'estrategia': dados_trade.get('estrategia')
                    }
                    task = asyncio.create_task(self._monitorar_saida(pair))
                    self._monitor_tasks[pair] = task
                    return True
            else:
                taxa = 0.001
                preco_exec = preco_atual
                preco_compra_com_taxa = preco_exec * (1 + taxa)
                if 'tp' in dados_trade and 'sl' in dados_trade:
                    tp = round(float(dados_trade['tp']), price_prec)
                    sl = round(float(dados_trade['sl']), price_prec)
                else:
                    tp = round(preco_exec * (1 + float(dados_trade.get('tp_pct', 1))/100), price_prec)
                    sl = round(preco_exec * (1 - float(dados_trade.get('sl_pct', 1))/100), price_prec)
                self.active_trades[pair] = {
                    'symbol': symbol,
                    'qty': quantidade,
                    'entry': preco_exec,
                    'entry_with_fee': preco_compra_com_taxa,
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
                ticker = retry_api_call(lambda: self.client.get_symbol_ticker(symbol=pair))
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
            ticker = retry_api_call(lambda: self.client.get_symbol_ticker(symbol=pair))
            preco_atual = float(ticker['price'])
            lucro_bruto_pct = ((preco_atual / trade['entry']) - 1) * 100
            
            if lucro_bruto_pct > 0.25: # Cobre 0.2% de taxas + margem
                await self.fechar_posicao(pair, "LIMPEZA DIÁRIA (LUCRO REAL)")

    async def fechar_posicao(self, pair, motivo):
        trade = self.active_trades.get(pair)
        if not trade:
            return
        try:
            venda = retry_api_call(lambda: self.client.order_market_sell(symbol=pair, quantity=str(trade['qty'])))
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

            # Captura taxas reais de cada fill
            total_commission = 0.0
            commission_assets = {}
            for f in fills:
                commission = float(f.get('commission', 0))
                asset = f.get('commissionAsset', '')
                total_commission += commission if asset == 'USDT' else 0.0
                if asset:
                    commission_assets[asset] = commission_assets.get(asset, 0.0) + commission

            # Se não houver info de commission nos fills, usa taxa padrão
            if not fills or not any('commission' in f for f in fills):
                taxa = 0.001
            else:
                taxa = total_commission / filled_qty if filled_qty else 0.001

            preco_venda_com_taxa = avg_price * (1 - taxa)
            preco_compra_com_taxa = trade.get('entry_with_fee', trade['entry'] * (1 + taxa))
            bruto = (preco_venda_com_taxa - preco_compra_com_taxa) * filled_qty
            from datetime import datetime
            import json
            import os
            log_path = os.path.join('data', 'trades_log.json')
            # Carrega histórico existente
            try:
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8') as f:
                        trades = json.load(f)
                else:
                    trades = []
            except Exception:
                trades = []
            # Captura saldo antes/depois e valores das moedas principais
            try:
                from datetime import datetime as dt
                import json
                comp_path = os.path.join('data', 'account_composition.json')
                comp = json.load(open(comp_path, 'r', encoding='utf-8')) if os.path.exists(comp_path) else {}
                saldo_antes = comp.get('_total_usdt', None)
                moedas_antes = {k: comp[k] for k in ['BTC', 'ETH', 'BNB', 'USDT', 'DOT', 'LTC', 'TRX', 'ICP'] if k in comp}
            except Exception:
                saldo_antes = None
                moedas_antes = {}

            # Após venda, atualizar comp para saldo depois
            try:
                import time
                time.sleep(1)  # Pequeno delay para garantir atualização
                comp = json.load(open(comp_path, 'r', encoding='utf-8')) if os.path.exists(comp_path) else {}
                saldo_depois = comp.get('_total_usdt', None)
                moedas_depois = {k: comp[k] for k in ['BTC', 'ETH', 'BNB', 'USDT', 'DOT', 'LTC', 'TRX', 'ICP'] if k in comp}
            except Exception:
                saldo_depois = None
                moedas_depois = {}

            trade_log = {
                'timestamp': datetime.now().isoformat(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'pair': pair,
                'estrategia': trade.get('estrategia'),
                'qty': filled_qty,
                'preco_compra_com_taxa': round(preco_compra_com_taxa, 6),
                'preco_venda_com_taxa': round(preco_venda_com_taxa, 6),
                'pnl_usdt': round(bruto, 4),
                'motivo': motivo,
                'taxa_binance': taxa,
                'taxa_binance_detalhe': commission_assets,
                'saldo_antes': saldo_antes,
                'saldo_depois': saldo_depois,
                'variacao_saldo': (saldo_depois - saldo_antes) if saldo_antes is not None and saldo_depois is not None else None,
                'moedas_antes': moedas_antes,
                'moedas_depois': moedas_depois
            }
            trades.append(trade_log)
            # Salva de volta
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    json.dump(trades, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Erro ao salvar trades_log.json: {e}")
            logger.info(f"Trade fechado: {pair} | Compra c/ taxa: {preco_compra_com_taxa:.6f} | Venda c/ taxa: {preco_venda_com_taxa:.6f} | Qtd: {filled_qty} | Lucro líquido: {bruto:.4f} | Taxas detalhadas: {commission_assets}")
            if self.callback_pnl:
                await self.callback_pnl(pair, bruto, trade.get('estrategia'))
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