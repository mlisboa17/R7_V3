import os
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException

DEFAULT_RETRIES = int(os.getenv('BINANCE_API_RETRIES', '3'))
DEFAULT_BACKOFF = float(os.getenv('BINANCE_API_BACKOFF', '1.0'))


class BinanceClientWrapper:
    def __init__(self, api_key=None, secret=None, retries=DEFAULT_RETRIES, backoff=DEFAULT_BACKOFF):
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.secret = secret or os.getenv('BINANCE_SECRET_KEY')
        self.retries = retries
        self.backoff = backoff
        self.client = Client(self.api_key, self.secret)

    def _call_with_retries(self, fn, *a, **kw):
        delay = self.backoff
        last_exc = None
        for attempt in range(self.retries):
            try:
                return fn(*a, **kw)
            except BinanceAPIException as e:
                last_exc = e
                time.sleep(delay)
                delay *= 2
            except Exception as e:
                # network/httpx errors, DNS, etc.
                last_exc = e
                time.sleep(delay)
                delay *= 2
        # final attempt
        return fn(*a, **kw)

    def __getattr__(self, name):
        attr = getattr(self.client, name)
        if callable(attr):
            def wrapper(*a, **kw):
                return self._call_with_retries(attr, *a, **kw)
            return wrapper
        return attr


def get_binance_client(api_key=None, secret=None):
    return BinanceClientWrapper(api_key, secret)
