import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger('monitor')

class AccountMonitor:
    def __init__(self, client):
        self.client = client
        self.path = 'data/account_composition.json'

    async def monitor_loop(self):
        logger.info("📡 Monitor de Saldo Dinâmico Iniciado.")
        while True:
            try:
                account = await self.client.get_account()
                balances = [b for b in account['balances'] if float(b['free']) + float(b['locked']) > 0]
                
                composicao = {}
                total_usdt = 0.0
                for b in balances:
                    asset, qty = b['asset'], float(b['free']) + float(b['locked'])
                    try:
                        price = 1.0 if asset == 'USDT' else float((await self.client.get_symbol_ticker(symbol=f"{asset}USDT"))['price'])
                        val_usd = qty * price
                        if val_usd > 1.0:
                            composicao[asset] = {"qty": qty, "usd_val": round(val_usd, 2)}
                            total_usdt += val_usd
                    except: continue

                composicao.update({"_total_usdt": round(total_usdt, 2), "_timestamp": datetime.now().isoformat()})
                with open(self.path, 'w') as f:
                    json.dump(composicao, f, indent=2)
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Erro Monitor: {e}")
                await asyncio.sleep(10)