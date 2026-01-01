import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv
import time
import requests

# Configurações de Interface
load_dotenv()
st.set_page_config(
    layout="wide",
    page_title="R7_V3 Sniper Dashboard",
    page_icon="🎯",
    initial_sidebar_state="collapsed"
)

# --- SISTEMA DE AUTO-REFRESH E MEMÓRIA DE SESSÃO ---
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()
    st.session_state.refresh_count = 0
    st.session_state.memo_total = 0.0 # Memória para evitar saldo zero no refresh

# Lógica de Auto-refresh (10 segundos)
if time.time() - st.session_state.last_refresh > 10:
    st.session_state.last_refresh = time.time()
    st.session_state.refresh_count += 1
    st.rerun()

# --- FUNÇÃO DE LEITURA REAL-TIME (SEM CACHE) ---
def load_data(path):
    """Lê dados brutos do disco. Sem cache para garantir atualização real."""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content: return {}
                return json.loads(content)
        except: 
            return {}
    return {}

# --- CARREGAMENTO DOS DADOS ---
account = load_data('data/account_composition.json')
trades = load_data('data/trades_log.json')
settings = load_data('config/settings.json')
hoje_str = datetime.now().strftime('%Y-%m-%d')
hoje_dd_mm_aaaa = datetime.now().strftime('%d_%m_%Y')

# Carregar saldo inicial do dia
day_file = f'data/{hoje_dd_mm_aaaa}.json'
initial_data = load_data(day_file)
saldo_inicial_dia = initial_data.get('saldo_inicial', 0.0)

# Ajuste manual do saldo (do settings.json)
manual_adjust = settings.get('manual_balance_adjustment', 0.0)

# --- PROCESSAMENTO DO SALDO REAL ---
total_vido_da_binance = account.get('_total_usdt', 0.0)

# Lógica Anti-Flash: Se a leitura falhar (bot escrevendo), usa o último valor da memória
if total_vido_da_binance > 0:
    total_atual = total_vido_da_binance + manual_adjust
    st.session_state.memo_total = total_atual
else:
    total_atual = st.session_state.memo_total

# Cálculo do Lucro do Dia (Trades)
lucro_hoje_trades = 0.0
trades_list = trades if isinstance(trades, list) else []
for t in trades_list:
    if str(t.get('date')).startswith(hoje_str):
        lucro_hoje_trades += float(t.get('pnl_usdt', 0))

# Se o saldo inicial do arquivo for zero, tenta estimar para não quebrar a métrica
if saldo_inicial_dia == 0:
    saldo_inicial_dia = total_atual - lucro_hoje_trades - manual_adjust

# Mudança Real e Progressão
mudanca_real = total_atual - (saldo_inicial_dia + manual_adjust)
progressao_dia = (mudanca_real / (saldo_inicial_dia + manual_adjust) * 100) if (saldo_inicial_dia + manual_adjust) > 0 else 0.0

# --- INTERFACE ---
col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.title("🎯 R7_V3 SNIPER - Dashboard")
with col_t2:
    if st.button("🔄 Refresh Manual"):
        st.rerun()

st.markdown(f"**Status:** Online | **Atualização:** {datetime.now().strftime('%H:%M:%S')} | **Ciclos:** {st.session_state.refresh_count}")

# --- MÉTRICAS PRINCIPAIS ---
tab1, tab2 = st.tabs(["📊 Visão Geral", "🤖 Performance dos Bots"])

with tab1:
    st.subheader("📈 Monitor de Saldo e Progressão")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Saldo Inicial (00:00)", f"${saldo_inicial_dia + manual_adjust:,.2f}")
    m2.metric("Saldo Real Binance", f"${total_atual:,.2f}", f"{mudanca_real:+.2f}")
    m3.metric("Lucro Hoje", f"${mudanca_real:+,.2f}")
    m4.metric("Crescimento %", f"{progressao_dia:+.2f}%")

    st.progress(min(max(progressao_dia / 2.0, 0.0), 1.0)) # Meta 2%

    st.divider()

    # --- PORTFÓLIO ---
    st.subheader("💰 Composição em Tempo Real")
    portfolio = []
    prices = {}
    
    # Criamos uma lista de ativos para buscar preços via API (apenas para exibição no dash)
    for asset, data in account.items():
        if asset != '_total_usdt' and isinstance(data, dict):
            # Fallback rápido para evitar travar o dashboard com muitas requests
            try:
                val_usd = data.get('usd_val', 0)
                qty = data.get('qty', 0)
                preco_estimado = val_usd / qty if qty > 0 else 0
                
                portfolio.append({
                    'Ativo': asset,
                    'Quantidade': f"{qty:,.6f}",
                    'Valor em USDT': f"${val_usd:,.2f}",
                    'Preço Médio Estimado': f"${preco_estimado:,.4f}"
                })
            except: continue

    if portfolio:
        df_p = pd.DataFrame(portfolio)
        st.dataframe(df_p, use_container_width=True)
        # Mini gráfico de alocação
        st.bar_chart(df_p.set_index('Ativo')['Valor em USDT'].str.replace('$', '').str.replace(',', '').astype(float))
    else:
        st.info("Aguardando atualização de ativos do bot...")

with tab2:
    st.subheader("🤖 Estratégias Sniper")
    if trades_list:
        df_trades = pd.DataFrame(trades_list)
        bot_col = 'estrategia' if 'estrategia' in df_trades.columns else 'bot'
        
        if bot_col in df_trades.columns:
            bots = df_trades[bot_col].unique()
            cols = st.columns(len(bots) if len(bots) > 0 else 1)
            for i, b_name in enumerate(bots):
                df_b = df_trades[df_trades[bot_col] == b_name]
                pnl_b = df_b['pnl_usdt'].sum()
                wr_b = (len(df_b[df_b['pnl_usdt'] > 0]) / len(df_b)) * 100
                cols[i].metric(f"Bot {b_name}", f"${pnl_b:,.2f}", f"WR: {wr_b:.1f}%")
        else:
            st.info("Aguardando o primeiro trade para analisar estratégias.")
    else:
        st.info("Nenhum trade realizado no log.")

# --- LOGS ---
with st.expander("📜 Ver Histórico de Operações"):
    if trades_list:
        st.dataframe(pd.DataFrame(trades_list).iloc[::-1], use_container_width=True)