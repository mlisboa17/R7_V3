import sys, os
sys.path.insert(0, os.getcwd())
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo('America/Sao_Paulo')
    prev = (datetime.now(tz).date() - timedelta(days=1)).isoformat()
except Exception:
    prev = (datetime.utcnow().date() - timedelta(days=1)).isoformat()

print('Sending summary for', prev)
from tools.daily_summary_daemon import send_summary_once
ok = send_summary_once(prev)
print('send_summary_once returned', ok)
