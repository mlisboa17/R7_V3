import os
import time
import logging
import asyncio
from binance.client import Client
from binance.exceptions import BinanceAPIException

logger = logging.getLogger('binance_wrapper')

DEFAULT_RETRIES = int(os.getenv('BINANCE_API_RETRIES', '5'))
DEFAULT_BACKOFF = float(os.getenv('BINANCE_API_BACKOFF', '1.0'))


class BinanceClientWrapper:
    def __init__(self, api_key=None, secret=None, retries=DEFAULT_RETRIES, backoff=DEFAULT_BACKOFF, time_sync=None):
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.secret = secret or os.getenv('BINANCE_SECRET_KEY')
        self.retries = retries
        self.backoff = backoff
        self.client = Client(self.api_key, self.secret)
        self.time_sync = time_sync  # Referência ao TimeSyncManager
        self.timestamp_error_count = 0

    def _call_with_retries(self, fn, *a, **kw):
        delay = self.backoff
        last_exc = None
        
        for attempt in range(self.retries):
            try:
                return fn(*a, **kw)
            except BinanceAPIException as e:
                # Se for erro de timestamp (-1021), tenta sincronizar
                if e.code == -1021:
                    self.timestamp_error_count += 1
                    logger.warning(f"[RETRY] Erro na chamada API (BinanceAPIException): {e}. Tentativa {attempt + 1}/{self.retries}")
                    
                    # Tenta sincronizar relógio se TimeSyncManager estiver disponível
                    if self.time_sync and hasattr(self.time_sync, 'sync_clock'):
                        try:
                            # Para chamadas síncronas, aguarda sincronização
                            server_time = self.client.get_server_time()
                            local_time = int(time.time() * 1000)
                            time_diff = server_time['serverTime'] - local_time
                            self.client.session.params['timestamp'] = lambda: int(time.time() * 1000) + time_diff
                            logger.info(f"⏰ Ajuste de timestamp aplicado: {time_diff}ms")
                        except Exception as sync_error:
                            logger.warning(f"⚠️ Erro ao sincronizar: {sync_error}")
                    
                    # Se muitos erros de timestamp, aguarda mais tempo
                    if self.timestamp_error_count > 2:
                        delay = self.backoff * 5
                        logger.warning(f"⚠️ Muitos erros de timestamp. Aumentando delay para {delay}s")
                else:
                    logger.warning(f"[RETRY] Erro na chamada API (BinanceAPIException): {e}. Tentativa {attempt + 1}/{self.retries}")
                
                last_exc = e
                time.sleep(delay)
                delay *= 2
                
            except Exception as e:
                # network/httpx errors, DNS, etc.
                logger.warning(f"[RETRY] Erro na chamada API ({type(e).__name__}): {e}. Tentativa {attempt + 1}/{self.retries}")
                last_exc = e
                time.sleep(delay)
                delay *= 2
        
        # final attempt
        logger.error(f"[FAIL] Todas as tentativas falharam: {last_exc}")
        return fn(*a, **kw)

    def __getattr__(self, name):
        attr = getattr(self.client, name)
        if callable(attr):
            def wrapper(*a, **kw):
                return self._call_with_retries(attr, *a, **kw)
            return wrapper
        return attr


def get_binance_client(api_key=None, secret=None, time_sync=None):
    return BinanceClientWrapper(api_key, secret, time_sync=time_sync)
