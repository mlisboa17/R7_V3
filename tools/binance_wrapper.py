import os
import asyncio
from binance import AsyncClient
from binance.exceptions import BinanceAPIException

DEFAULT_RETRIES = int(os.getenv('BINANCE_API_RETRIES', '5'))
DEFAULT_BACKOFF = float(os.getenv('BINANCE_API_BACKOFF', '1.0'))


class BinanceClientWrapper:
    def __init__(self, api_key=None, secret=None, retries=DEFAULT_RETRIES, backoff=DEFAULT_BACKOFF):
        # Forçar remoção de TESTNET
        os.environ.pop('TESTNET', None)
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.secret = secret or os.getenv('BINANCE_SECRET_KEY')
        self.retries = retries
        self.backoff = backoff
        
        # Calculate timestamp offset to sync with Binance server
        try:
            # Fixed offset since system time is ahead by ~28 seconds
            timestamp_offset = -30000  # 30 seconds behind to be safe
            self.client = AsyncClient(self.api_key, self.secret, testnet=False, timestamp_offset=timestamp_offset, requests_params={'timeout': 30})
        except Exception as e:
            # Fallback
            self.client = AsyncClient(self.api_key, self.secret, testnet=False, requests_params={'timeout': 30})
        
        # Override __del__ to prevent AttributeError
        self.client.__del__ = lambda: None
        # Override close_connection to prevent AttributeError
        self.client.close_connection = lambda: None

    async def _call_with_retries(self, fn, *a, **kw):
        delay = self.backoff
        last_exc = None
        for attempt in range(self.retries):
            try:
                return await fn(*a, **kw)
            except BinanceAPIException as e:
                last_exc = e
                await asyncio.sleep(delay)
                delay *= 2
            except Exception as e:
                # network/httpx errors, DNS, etc.
                last_exc = e
                await asyncio.sleep(delay)
                delay *= 2
        # final attempt
        return await fn(*a, **kw)

    def __getattr__(self, name):
        attr = getattr(self.client, name)
        if callable(attr):
            async def wrapper(*a, **kw):
                return await self._call_with_retries(attr, *a, **kw)
            return wrapper
        return attr


def get_binance_client(api_key=None, secret=None):
    return BinanceClientWrapper(api_key, secret)
