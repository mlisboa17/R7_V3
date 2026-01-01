import os
import asyncio
from binance.exceptions import BinanceAPIException

# Compatibilidade com diferentes versões do SDK binance
AsyncClient = None
Client = None
try:
    # nova estrutura (quando disponível)
    from binance.async_client import AsyncClient as _AsyncClient
    AsyncClient = _AsyncClient
except Exception:
    try:
        # fallback antigo
        from binance import AsyncClient as _AsyncClient2
        AsyncClient = _AsyncClient2
    except Exception:
        try:
            # tentar o cliente síncrono
            from binance.client import Client as _Client
            Client = _Client
        except Exception:
            AsyncClient = None
            Client = None

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
        # Instancia o cliente async se disponível, caso contrário usa o cliente síncrono
        timestamp_offset = -30000  # 30 seconds behind to be safe
        if AsyncClient is not None:
            try:
                self.client = AsyncClient(self.api_key, self.secret, testnet=False, timestamp_offset=timestamp_offset, requests_params={'timeout': 30})
            except Exception:
                self.client = AsyncClient(self.api_key, self.secret, testnet=False, requests_params={'timeout': 30})
            self._is_async = True
            # Proteções para evitar __del__/close issues
            try: self.client.__del__ = lambda: None
            except Exception: pass
            try: self.client.close_connection = lambda: None
            except Exception: pass
        elif Client is not None:
            # Cliente síncrono: será executado em thread via asyncio.to_thread
            self.client = Client(self.api_key, self.secret)
            self._is_async = False
        else:
            raise RuntimeError("Nenhum cliente Binance disponível (instale python-binance ou binance-connector)")

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
            if getattr(self, '_is_async', True):
                async def wrapper(*a, **kw):
                    return await self._call_with_retries(attr, *a, **kw)
                return wrapper
            else:
                async def wrapper_sync(*a, **kw):
                    # Executa chamada síncrona em thread para não bloquear o loop
                    return await self._call_with_retries(lambda *aa, **kk: asyncio.to_thread(attr, *aa, **kk), *a, **kw)
                return wrapper_sync
        return attr


def get_binance_client(api_key=None, secret=None):
    return BinanceClientWrapper(api_key, secret)
