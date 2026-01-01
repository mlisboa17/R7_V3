import pandas as pd
from datetime import datetime
import pytz

# Carregar dados
df = pd.read_csv('data/all_trades_history.csv')

# Filtrar apenas linhas com timestamp válido
df = df.dropna(subset=['timestamp'])

# Converter timestamp para datetime UTC
df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

# Converter para fuso de Brasília (UTC-3)
brasilia_tz = pytz.timezone('America/Sao_Paulo')
df['hora_brasilia'] = df['timestamp'].dt.tz_convert(brasilia_tz).dt.hour

# Agrupar por hora e calcular métricas
analise_hora = df.groupby('hora_brasilia').agg(
    total_pnl=('pnl_usdt', 'sum'),
    num_trades=('pnl_usdt', 'count'),
    pnl_medio=('pnl_usdt', 'mean'),
    win_rate=('pnl_usdt', lambda x: (x > 0).mean() * 100)
).reset_index()

# Ordenar por total_pnl descendente
analise_hora = analise_hora.sort_values('total_pnl', ascending=False)

print("Análise de Horários de Trading (Fuso Brasília)")
print("=" * 50)
print(analise_hora.to_string(index=False))

# Melhores horários (top 5 por pnl total)
print("\nMelhores Horários para Trading:")
melhores = analise_hora.head(5)
for _, row in melhores.iterrows():
    print(f"Hora {int(row['hora_brasilia']):02d}:00 - PnL Total: ${row['total_pnl']:.2f} | Trades: {int(row['num_trades'])} | Win Rate: {row['win_rate']:.1f}%")