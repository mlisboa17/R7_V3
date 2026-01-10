import json
from datetime import datetime
from collections import defaultdict
import statistics


DEF_REALISTA_PCT = 5.0


def load_history(path='previsoes_historico.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_iso(ts):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def analyze(history, realista_pct=DEF_REALISTA_PCT):
    records = []
    by_month = defaultdict(int)
    for key, rec in history.items():
        entry_time = parse_iso(rec.get('entry_time') or rec.get('previsao_inicial', {}).get('entry_time'))
        if not entry_time:
            continue
        venda = rec.get('venda')
        # skip open positions
        if not venda:
            continue
        lucro = venda.get('lucro_pct')
        if lucro is None:
            continue
        # check if sold within ETA of realista scenario when possible
        eta_horas = None
        try:
            eta_horas = rec.get('previsao_inicial', {}).get('cenarios', {}).get('realista', {}).get('eta_horas')
        except Exception:
            eta_horas = None
        venda_time = parse_iso(venda.get('timestamp'))
        within_eta = None
        if venda_time and eta_horas is not None:
            delta = (venda_time - entry_time).total_seconds() / 3600.0
            within_eta = delta <= eta_horas

        records.append({
            'key': key,
            'entry_time': entry_time,
            'venda_time': venda_time,
            'realized_pct': float(lucro),
            'within_eta': within_eta,
            'target_pct': realista_pct,
        })
        by_month[(entry_time.year, entry_time.month)] += 1

    return records, by_month


def compute_metrics(records, realista_pct=DEF_REALISTA_PCT):
    closed = records
    if not closed:
        return None
    n = len(closed)
    successes = [r for r in closed if r['realized_pct'] >= realista_pct]
    p_emp = len(successes) / n
    realized = [r['realized_pct']/100.0 for r in closed]
    mean = statistics.mean(realized)
    median = statistics.median(realized)
    losses = [r['realized_pct']/100.0 for r in closed if r['realized_pct'] < realista_pct]
    avg_loss_when_fail = statistics.mean(losses) if losses else 0.0
    trades_per_month = None
    # estimate trades/month from distribution
    return {
        'n_trades': n,
        'p_empirical': p_emp,
        'mean_realized_pct': mean*100.0,
        'median_realized_pct': median*100.0,
        'avg_loss_when_fail_pct': avg_loss_when_fail*100.0,
    }


def simulate_month(metrics, trades_month_options=[12,16,20]):
    # simple compounding using mean_realized_pct per trade
    res = {}
    mean_per_trade = metrics['mean_realized_pct']/100.0
    for t in trades_month_options:
        total = (1.0 + mean_per_trade) ** t - 1.0
        res[t] = total
    return res


def main():
    hist = load_history()
    records, by_month = analyze(hist, realista_pct=DEF_REALISTA_PCT)
    metrics = compute_metrics(records, realista_pct=DEF_REALISTA_PCT)
    if not metrics:
        print('Nenhum trade fechado encontrado em previsoes_historico.json')
        return

    print(f"Trades analisados: {metrics['n_trades']}")
    print(f"Taxa empírica de sucesso (>= {DEF_REALISTA_PCT}%): {metrics['p_empirical']*100:.2f}%")
    print(f"Realizado médio por trade: {metrics['mean_realized_pct']:.2f}%  Mediana: {metrics['median_realized_pct']:.2f}%")
    print(f"Perda média quando falha (real < target): {metrics['avg_loss_when_fail_pct']:.2f}%")
    print()
    sims = simulate_month(metrics)
    for t, val in sims.items():
        print(f"Simulação (composto) com {t} trades/mês → {val*100:.2f}%/m")


if __name__ == '__main__':
    main()
