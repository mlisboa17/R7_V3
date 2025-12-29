import os
import json
from glob import glob

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
LOGS_DIR = os.path.join(BASE_DIR, '..', 'logs')

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def main():
    # Carrega trades_log principal
    trades = load_json(os.path.join(DATA_DIR, 'trades_log.json'))
    if not isinstance(trades, list):
        trades = []

    # Adiciona outros logs relevantes (exemplo: logs/trades_tail.log)
    # Aqui só faz parse se for JSON válido, pode ser expandido para outros formatos
    # Exemplo: history_log.json (se for de trades)
    # Adicione aqui outros arquivos se necessário

    # Remove duplicatas por (date, pair, estrategia, pnl_usdt)
    seen = set()
    all_trades = []
    for t in trades:
        key = (t.get('date'), t.get('pair'), t.get('estrategia'), float(t.get('pnl_usdt', 0)))
        if key not in seen:
            seen.add(key)
            all_trades.append(t)


    # Salva consolidado em JSON
    out_path = os.path.join(DATA_DIR, 'all_trades_history.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_trades, f, indent=2, ensure_ascii=False)
    print(f"Consolidado salvo em {out_path} com {len(all_trades)} trades.")

    # Salva consolidado em CSV
    import csv
    csv_path = os.path.join(DATA_DIR, 'all_trades_history.csv')
    # Descobre todos os campos possíveis
    all_fields = set()
    for t in all_trades:
        all_fields.update(t.keys())
    all_fields = sorted(all_fields)
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        for t in all_trades:
            writer.writerow(t)
    print(f"Consolidado salvo em {csv_path}.")

if __name__ == '__main__':
    main()