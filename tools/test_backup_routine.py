import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bots.guardiao import GuardiaoBot

def run_test():
    cfg = {'config_trade': {'meta_diaria_brl': 99.09, 'usdt_margin': 294.0, 'stop_diario_brl':10000.0}, 'banca_total_brl': 9909.25}
    g = GuardiaoBot(cfg, state_path='logs/daily_state_backup_test.json')
    # ensure data/history_log.json exists
    os.makedirs('data', exist_ok=True)
    sample = [{'date':'2025-12-22','start_brl':9800,'closing_brl':10000,'lucro_brl':200,'pct':2.04}]
    with open('data/history_log.json','w',encoding='utf-8') as f:
        json.dump(sample,f,indent=2)
    # remove any old backups
    for fn in os.listdir('logs') if os.path.exists('logs') else []:
        if fn.startswith('history_log_backup_'):
            try: os.remove(os.path.join('logs',fn))
            except: pass
    # create artificially old backups to test rotation (8 days old and 3 days old)
    import datetime
    os.makedirs('logs', exist_ok=True)
    old_date = (datetime.datetime.utcnow().date() - datetime.timedelta(days=8)).strftime('%Y%m%d')
    newer_date = (datetime.datetime.utcnow().date() - datetime.timedelta(days=3)).strftime('%Y%m%d')
    open(os.path.join('logs', f'history_log_backup_{old_date}.json'),'w',encoding='utf-8').write('{}')
    open(os.path.join('logs', f'history_log_backup_{newer_date}.json'),'w',encoding='utf-8').write('{}')

    ok = g.backup_history_log()
    print('Backup created (today):', ok)
    if ok:
        backs = sorted([fn for fn in os.listdir('logs') if fn.startswith('history_log_backup_')])
        print('Backup files after rotation:', backs)
        # check that old_date file was removed and newer_date + today exist
        assert f'history_log_backup_{old_date}.json' not in backs, 'Old backup not removed'
        assert f'history_log_backup_{newer_date}.json' in backs, 'Newer backup missing'
        today = datetime.datetime.utcnow().strftime('%Y%m%d')
        assert f'history_log_backup_{today}.json' in backs, 'Today backup missing'
        print('Rotation OK')

if __name__ == '__main__':
    run_test()
