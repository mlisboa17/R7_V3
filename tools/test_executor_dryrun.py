import asyncio
import os
import sys
import logging

os.environ['REAL_TRADING'] = '0'
sys.path.insert(0, os.getcwd())

from bots.executor import ExecutorBot


class MockClient:
    def get_symbol_info(self, symbol):
        return {
            'symbol': symbol,
            'filters': [
                {'filterType': 'LOT_SIZE', 'stepSize': '0.000001', 'minQty': '0.0001'},
                {'filterType': 'PRICE_FILTER', 'tickSize': '0.01'}
            ]
        }

    def get_symbol_ticker(self, symbol):
        # return a fixed price for test
        return {'symbol': symbol, 'price': '30000'}

    def order_market_buy(self, symbol, quantity):
        # emulate an immediate fill
        return {'status': 'FILLED', 'fills': [{'price': '30000', 'qty': str(quantity)}], 'executedQty': str(quantity)}

    def order_market_sell(self, symbol, quantity):
        return {'status': 'FILLED', 'fills': [{'price': '30100', 'qty': str(quantity)}], 'executedQty': str(quantity)}

    def get_account(self):
        return {'balances': [{'asset': 'USDT', 'free': '1000', 'locked': '0'}]}


async def main():
    cfg = {}
    bot = ExecutorBot(cfg)
    # replace real client with mock
    bot.client = MockClient()

    # run a simulated buy
    ok = await bot.executar_ordem('BTC', {'entrada_usd': 50, 'tp_pct': 1, 'sl_pct': 0.5, 'estrategia': 'dryrun'})
    print('executar_ordem returned', ok)
    print('active_trades:', bot.active_trades)

    # cancel monitor tasks to exit cleanly
    for t in list(bot._monitor_tasks.values()):
        try:
            t.cancel()
        except Exception:
            pass


if __name__ == '__main__':
    asyncio.run(main())
