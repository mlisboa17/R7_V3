import os, json, sys
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv
load_dotenv()
import requests

out = {}
# Env keys
out['REAL_TRADING'] = os.getenv('REAL_TRADING')
out['BINANCE_API_KEY_present'] = bool(os.getenv('BINANCE_API_KEY'))
out['BINANCE_SECRET_KEY_present'] = bool(os.getenv('BINANCE_SECRET_KEY'))

# Public connectivity: ping Binance API
try:
    r = requests.get('https://api.binance.com/api/v3/ping', timeout=5)
    out['public_ping_ok'] = (r.status_code == 200)
except Exception as e:
    out['public_ping_ok'] = False
    out['public_ping_error'] = str(e)

# Public ticker
try:
    r = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=USDTBRL', timeout=5)
    out['public_ticker_ok'] = r.status_code == 200
    out['ticker'] = r.json() if r.status_code==200 else None
except Exception as e:
    out['public_ticker_ok'] = False
    out['ticker_error'] = str(e)

# Try using python-binance client if available
try:
    from binance.client import Client
    api = os.getenv('BINANCE_API_KEY') or None
    sec = os.getenv('BINANCE_SECRET_KEY') or None
    if api and sec:
        try:
            from tools.binance_wrapper import get_binance_client
            client = get_binance_client(api, sec)
            # attempt account info
            try:
                acct = client.get_account()
                out['account_ok'] = True
                out['balances_count'] = len(acct.get('balances', []))
            except Exception as e:
                out['account_ok'] = False
                out['account_error'] = str(e)
        except Exception as e:
            out['client_init_error'] = str(e)
    else:
        out['account_ok'] = False
        out['account_error'] = 'No API keys in env/config'
except Exception as e:
    out['binance_client_available'] = False
    out['binance_client_error'] = str(e)

print(json.dumps(out, indent=2, ensure_ascii=False))