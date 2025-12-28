import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import time
import subprocess
from bots.monthly_stats import get_monthly_balance
from bots.monthly_stats import get_daily_breakdown, get_monthly_accumulated_by_bot

# 1. Configuração Visual
st.set_page_config(page_title="R7_V3 Command Center", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    [data-testid="stSidebar"] { background-color: #0e1117; }
    </style>
    """, unsafe_allow_html=True)

def update_composition_data():
    """Executa o script de atualização da composição."""
    try:
        result = subprocess.run(['python', 'update_composition.py'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0:
            return True
        else:
            st.error(f"Erro ao atualizar composição: {result.stderr}")
            return False
    except Exception as e:
        st.error(f"Erro ao executar atualização: {e}")
        return False

def get_account_composition():
    """Consulta a composição do saldo (armazenada localmente para segurança)."""
    try:
        # Lê de um arquivo local atualizado periodicamente
        path = 'data/account_composition.json'
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Remover chaves que não são ativos
                return {k: v for k, v in data.items() if not k.startswith('_')}
        else:
            # Fallback: valores simulados
            return {"USDT": saldo_real, "BTC": 0, "ETH": 0, "Earn/Staking": 0}
    except Exception as e:
        st.error(f"Erro ao carregar composição: {e}")
        return {"USDT": saldo_real, "BTC": 0, "ETH": 0, "Earn/Staking": 0}
def load_stats():
    path = 'data/monthly_stats.json'
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def load_daily_state():
    path = 'data/daily_state.json'
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def load_trades_log():
    path = 'data/trades_log.json'
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return []
    return []

def get_last_logs():
    """Retorna as últimas 20 linhas do log do sistema."""
    log_path = 'logs/r7_v3.log'
    if not os.path.exists(log_path):
        return ["Log não encontrado."]
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return lines[-20:] if len(lines) > 20 else lines
    except Exception as e:
        return [f"Erro ao ler log: {e}"]

def calculate_metrics(trades):
    if not trades:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'total_profit': 0,
            'total_loss': 0
        }
    
    wins = [t['pnl_usdt'] for t in trades if t['pnl_usdt'] > 0]
    losses = [t['pnl_usdt'] for t in trades if t['pnl_usdt'] < 0]
    
    total_trades = len(trades)
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    total_profit = sum(wins)
    total_loss = abs(sum(losses))
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'total_profit': total_profit,
        'total_loss': total_loss
    }

# 3. Processamento de Dados
data = load_stats()
daily_state = load_daily_state()
hoje = datetime.now().strftime("%Y-%m-%d")
mes_atual = datetime.now().strftime("%Y-%m")

stats_mes = data.get(mes_atual, {})
stats_dia = stats_mes.get(hoje, {})

# Calcular totais
total_mes = sum(sum(strat.values()) for strat in stats_mes.values() if isinstance(strat, dict))
total_dia = sum(stats_dia.values()) if stats_dia else 0.0

# Estratégias do mês
strategies_mes = {}
for dia, strats in stats_mes.items():
    if isinstance(strats, dict):
        for strat, lucro in strats.items():
            strategies_mes[strat] = strategies_mes.get(strat, 0.0) + lucro

# Valores reais do daily_state
saldo_real = daily_state.get('spot_usdt', 1743.12)
lucro_dia_real = daily_state.get('lucro_acumulado_usdt', 0.0)
meta_diaria = daily_state.get('meta_diaria_usdt', 17.43)
trades_hoje = daily_state.get('trades_today', 0)

# Saldo mensal
saldo_mensal = get_monthly_balance(mes_atual)

# Métricas de performance
trades_log = load_trades_log()
metrics = calculate_metrics(trades_log)

# Agrupar trades por bot
trades_por_bot = {}
for trade in trades_log:
    bot = trade.get('estrategia', 'desconhecido')
    if bot not in trades_por_bot:
        trades_por_bot[bot] = []
    trades_por_bot[bot].append(trade)

# Calcular saldo total da composição
composicao = get_account_composition()
saldo_total = composicao.get('_total_usdt', sum(composicao.values()))

# 4. Interface - Sidebar
st.sidebar.title("🎮 R7_V3 Control")
st.sidebar.metric("Banca Base", f"$ {saldo_real:.2f}")
st.sidebar.write(f"🎯 Meta Diária: $ {meta_diaria:.2f}")
st.sidebar.divider()
if st.sidebar.button('🔄 ATUALIZAR AGORA'):
    st.rerun()

# 5. Interface - Dashboard Principal
st.title("📊 Painel de Performance Operacional")

# Linha 1: Métricas de Resumo
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("Saldo Total", f"$ {saldo_total:.2f}")
with c2:
    st.metric("Saldo Mensal", f"$ {saldo_mensal:.2f}")
with c3:
    st.metric("Lucro Hoje", f"$ {lucro_dia_real:.2f}")
with c4:
    st.metric("Lucro Mensal", f"$ {total_mes:.2f}")
with c5:
    progresso = (lucro_dia_real / meta_diaria) * 100 if lucro_dia_real > 0 else 0
    st.metric("Meta Diária %", f"{progresso:.1f}%")
with c6:
    st.metric("Trades Hoje", trades_hoje)

# Linha 2: Métricas de Performance
st.subheader("📊 Métricas de Performance")
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total Trades", metrics['total_trades'])
with col2:
    st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
with col3:
    st.metric("Avg Win", f"$ {metrics['avg_win']:.2f}")
with col4:
    st.metric("Avg Loss", f"$ {metrics['avg_loss']:.2f}")
with col5:
    st.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
with col6:
    st.metric("Sharpe Ratio", "N/A")  # Placeholder, precisa de dados históricos

st.divider()

# Linha 2: Gráfico e Estratégias
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📈 Evolução de Lucro Diário")
    if stats_mes:
        df_days = pd.DataFrame([{"Data": d, "Lucro": sum(v.values()) if isinstance(v, dict) else 0} for d, v in stats_mes.items()])
        st.line_chart(df_days.set_index("Data"))
    else:
        st.info("Aguardando dados históricos para gerar gráfico.")

with col_right:
    st.subheader("⚔️ Por Estratégia")
    if strategies_mes:
        df_strat = pd.DataFrame(list(strategies_mes.items()), columns=['Bot', 'Lucro'])
        st.table(df_strat)
    else:
        st.write("Sem dados por bot.")

# Seção: Performance individual dos bots (cards)
st.divider()
st.subheader("🤖 Performance Individual dos Bots")
try:
    # Carregar configurações
    with open('config/settings.json', 'r', encoding='utf-8') as f:
        settings = json.load(f)

    hoje_vals = get_daily_breakdown() or {}
    mensal_vals = get_monthly_accumulated_by_bot() or {}

    total_hoje = sum(hoje_vals.values()) if hoje_vals else 0.0
    total_mensal = sum(mensal_vals.values()) if mensal_vals else 0.0

    bots_config = {
        'scalping_v6': {'nome': 'Scalping V6', 'emoji': '⚡', 'cor': '#FF6B6B', 'desc': 'Scalping de curto prazo'},
        'swing_rwa': {'nome': 'Swing RWA', 'emoji': '📈', 'cor': '#4ECDC4', 'desc': 'Swing trading'},
        'momentum_boost': {'nome': 'Momentum Boost', 'emoji': '🚀', 'cor': '#45B7D1', 'desc': 'Momentum forte'},
        'mean_reversion': {'nome': 'Mean Reversion', 'emoji': '🔄', 'cor': '#96CEB4', 'desc': 'Reversão à média'}
    }

    moedas_por_estrategia = {
        'scalping_v6': ['SOL', 'ADA', 'DOT', 'LINK', 'AVAX', 'MATIC', 'ALGO'],
        'swing_rwa': ['BTC', 'ETH', 'BNB', 'LTC', 'XRP'],
        'momentum_boost': ['SOL', 'AVAX', 'MATIC', 'NEAR', 'FLOW'],
        'mean_reversion': ['TRX', 'XLM', 'VET', 'BAT', 'OMG']
    }

    cols = st.columns(2)
    for i, (bot_key, cfg) in enumerate(bots_config.items()):
        with cols[i % 2]:
            bot_settings = settings.get('estrategias', {}).get(bot_key, {})
            is_active = bot_settings.get('ativo', False)
            status_emoji = '🟢' if is_active else '🔴'

            lucro_hoje = hoje_vals.get(bot_key, 0.0)
            lucro_mes = mensal_vals.get(bot_key, 0.0)

            pct_hoje = (lucro_hoje / total_hoje * 100) if total_hoje > 0 else 0.0
            pct_mes = (lucro_mes / total_mensal * 100) if total_mensal > 0 else 0.0

            st.markdown(f"""
            <div style="border: 2px solid {cfg['cor']}; border-radius: 10px; padding: 12px; margin: 8px 0;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-weight:bold; color:{cfg['cor']};">{cfg['emoji']} {cfg['nome']}</div>
                    <div style="font-size:12px;">{status_emoji} {'ATIVO' if is_active else 'INATIVO'}</div>
                </div>
                <div style="font-size:12px; color:#666; margin-top:6px;">{bot_key.upper()} - {cfg['desc']}<br>
                {len(moedas_por_estrategia.get(bot_key, []))} moedas | Entrada: ${bot_settings.get('entrada_usd', 0):.0f} | TP: {bot_settings.get('tp_pct', 0):.1f}% | SL: {bot_settings.get('sl_pct', 0):.1f}%</div>
                <div style="display:flex; justify-content:space-between; margin-top:12px;">
                    <div style="text-align:center; flex:1;">
                        <div style="font-size:18px; font-weight:bold; color:{cfg['cor']};">${lucro_hoje:.2f}</div>
                        <div style="font-size:11px; color:#888;">Hoje</div>
                        <div style="font-size:12px; color:{cfg['cor']};">{pct_hoje:.1f}%</div>
                    </div>
                    <div style="text-align:center; flex:1;">
                        <div style="font-size:18px; font-weight:bold; color:{cfg['cor']};">${lucro_mes:.2f}</div>
                        <div style="font-size:11px; color:#888;">Mês</div>
                        <div style="font-size:12px; color:{cfg['cor']};">{pct_mes:.1f}%</div>
                    </div>
                </div>
                <div style="font-size:12px; color:#666; margin-top:8px;">Moedas: {', '.join(moedas_por_estrategia.get(bot_key, [])[:5])}{'...' if len(moedas_por_estrategia.get(bot_key, []))>5 else ''}</div>
            </div>
            """, unsafe_allow_html=True)
except Exception as e:
    st.error(f"Erro ao carregar performance dos bots: {e}")

st.divider()

# Linha 2.5: Trades por Bot
st.subheader("📊 Trades por Bot")
if trades_por_bot:
    for bot, trades in trades_por_bot.items():
        st.write(f"**{bot.capitalize()}**: {len(trades)} trades")
        df_trades = pd.DataFrame(trades)
        st.dataframe(df_trades)
else:
    st.write("Sem dados de trades.")

# Linha 3: Composição do Saldo
st.subheader("💰 Composição do Saldo (Binance)")
composicao = get_account_composition()
df_composicao = pd.DataFrame(list(composicao.items()), columns=['Ativo', 'Valor USDT'])
st.bar_chart(df_composicao, x='Ativo', y='Valor USDT')

# Linha 4: Logs em tempo real
st.subheader("📜 Atividade do Sistema (Terminal)")
logs = get_last_logs()
st.code("".join(logs), language='text')

# Rodapé
st.caption(f"R7_V3 v3.0 | Status: Online | Último Check: {datetime.now().strftime('%H:%M:%S')}")

# 6. Lógica de Atualização Automática (Autorefresh)
# Atualizar composição a cada 10 segundos
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()

current_time = time.time()
if current_time - st.session_state.last_update >= 10:
    update_composition_data()
    st.session_state.last_update = current_time

# Recarregar dados a cada 10 segundos
time.sleep(10)
st.rerun()