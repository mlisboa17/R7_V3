import time
import logging
from binance.exceptions import BinanceAPIException
import httpx

logger = logging.getLogger('binance_wrapper')

def retry_api_call(func, max_retries=5, base_delay=1, exceptions=(BinanceAPIException, httpx.ConnectError, Exception)):
    """
    Wrapper para chamadas de API com retries exponenciais e logging.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except exceptions as e:
            logger.warning(f"[RETRY] Erro na chamada API ({type(e).__name__}): {e}. Tentativa {attempt}/{max_retries}")
            if attempt == max_retries:
                logger.error(f"[FAIL] Todas as tentativas falharam: {e}")
                raise
            time.sleep(base_delay * (2 ** (attempt - 1)))
