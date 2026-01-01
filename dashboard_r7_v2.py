import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh
import requests    

# Tenta importar o componente de refresh
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st.error("Por favor, instale: pip install streamlit-autorefresh")
    st.stop()

# Configurações de Interface
load_dotenv()
st.set_page_config(layout="wide", page_title="R7_V3 Sniper Dashboard", page_icon="🎯")

# --- AUTO-REFRESH CONFIGURADO PARA 1 MINUTO ---
# 60000 milissegundos = 1 minuto

st_autorefresh(interval=60000, key="datarefresh")  # Atualiza a cada 1 minuto

# Botão de Refresh Manual
if st.button("🔄 Atualizar Dados Agora"):
    st.rerun()
# --- FUNÇÃO DE LEITURA SEGURA ---
@st.cache_data(ttl=60)  # Cache por 60 segundos
def load_data(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

# --- CARREGAMENTO DOS DADOS ---
account = load_data('data/account_composition.json')
trades = load_data('data/trades_log.json')
hoje_str = datetime.now().strftime('%Y-%m-%d')
hoje_dd_mm_aaaa = datetime.now().strftime('%d_%m_%Y')

# Carregar saldo inicial do dia
day_file = f'data/{hoje_dd_mm_aaaa}.json'
initial_data = load_data(day_file)
saldo_inicial_dia = initial_data.get('saldo_inicial', None)

# --- PROCESSAMENTO DE DADOS ---
total_atual = account.get('_total_usdt', 0.0)

# Cálculo do Lucro do Dia (Soma de todos os trades feitos hoje)
lucro_hoje = 0.0
trades_list = trades if isinstance(trades, list) else []
for t in trades_list:
    if str(t.get('date')).startswith(hoje_str):
        lucro_hoje += float(t.get('pnl_usdt', 0))

# Se não há saldo inicial salvo, calcular aproximado
if saldo_inicial_dia is None:
    saldo_inicial_dia = total_atual - lucro_hoje

# Cálculo da mudança real do saldo
mudanca_real = total_atual - saldo_inicial_dia if saldo_inicial_dia is not None else 0.0
progressao_dia = (mudanca_real / saldo_inicial_dia * 100) if saldo_inicial_dia and saldo_inicial_dia > 0 else 0.0

# --- CABEÇALHO ---
st.title("🎯 R7_V3 SNIPER - Dashboard de Performance")
st.markdown(f"**Refresh:** 1 min | **Status:** Online | **Última Atualização:** {datetime.now().strftime('%H:%M:%S')}")

# --- ABAS ---
tab1, tab2 = st.tabs(["📊 Visão Geral", "🤖 Performance dos Bots"])

with tab1:
    # --- SEÇÃO 1: PROGRESSÃO DIÁRIA ---
    st.subheader("📈 Monitor de Saldo e Progressão")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)

    with col_s1:
        st.metric("Saldo Inicial (00:00)", f"${saldo_inicial_dia:,.2f}")
        st.caption("Valor salvo no início do dia")

    with col_s2:
        st.metric("Saldo do Momento", f"${total_atual:,.2f}", f"{mudanca_real:+.2f}")
        st.caption("Valor real em USDT na Binance")

    with col_s3:
        cor_pnl = "normal" if mudanca_real >= 0 else "inverse"
        st.metric("Lucro Financeiro Hoje", f"${mudanca_real:+,.2f}")
        st.caption("Variação total do saldo hoje (incluindo trades e outras operações)")

    with col_s4:
        st.metric("Progressão Diária", f"{progressao_dia:+.2f}%")
        st.caption("Percentual de crescimento do patrimônio hoje")

    # Barra de Progresso Visual
    st.write(f"**Crescimento do Patrimônio Hoje:**")
    st.progress(min(max(progressao_dia / 2.0, 0.0), 1.0))  # Baseado em meta de 2%

    st.divider()

    # --- CARTÃO CONSOLIDADO DE PERFORMANCE ---
    st.subheader("🎯 Performance Consolidada dos Bots")
    if trades_list:
        total_trades = len(trades_list)
        wins = sum(1 for t in trades_list if float(t.get('pnl_usdt', 0)) > 0)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        lucro_total = sum(float(t.get('pnl_usdt', 0)) for t in trades_list)

        # Cálculo do Fator Gasto/Ganho
        gross_profit = sum(float(t.get('pnl_usdt', 0)) for t in trades_list if float(t.get('pnl_usdt', 0)) > 0)
        gross_loss = abs(sum(float(t.get('pnl_usdt', 0)) for t in trades_list if float(t.get('pnl_usdt', 0)) < 0))
        if gross_profit > 0:
            factor_gasto_ganho = gross_loss / gross_profit
        else:
            factor_gasto_ganho = float('inf') if gross_loss > 0 else 0

        # Cálculos adicionais
        melhor_trade = max((float(t.get('pnl_usdt', 0)) for t in trades_list), default=0)
        pior_trade = min((float(t.get('pnl_usdt', 0)) for t in trades_list), default=0)
        media_trade = lucro_total / total_trades if total_trades > 0 else 0

        col_cons1, col_cons2, col_cons3, col_cons4, col_cons5, col_cons6 = st.columns(6)
        with col_cons1:
            st.metric("Total de Trades", total_trades)
            st.caption("Número total de operações realizadas")
        with col_cons2:
            st.metric("Win Rate Geral", f"{win_rate:.1f}%")
            st.caption("Percentual de trades com lucro")
        with col_cons3:
            st.metric("Lucro Total", f"${lucro_total:+,.2f}")
            st.caption("Soma de todos os PnL dos trades")
        with col_cons4:
            if factor_gasto_ganho == float('inf'):
                st.metric("Fator Gasto/Ganho", "∞")
            elif factor_gasto_ganho == 0:
                st.metric("Fator Gasto/Ganho", "0.00")
            else:
                st.metric("Fator Gasto/Ganho", f"{factor_gasto_ganho:.2f}")
            st.caption("Razão entre perdas e ganhos totais")
        with col_cons5:
            st.metric("Melhor Trade", f"${melhor_trade:+,.2f}")
            st.caption("Maior lucro em um único trade")
        with col_cons6:
            st.metric("Pior Trade", f"${pior_trade:+,.2f}")
            st.caption("Maior perda em um único trade")
    else:
        st.info("Nenhum trade realizado ainda.")

# --- COMPOSIÇÃO DO PORTFÓLIO ---
st.subheader("💰 Composição do Portfólio")

if account:
    # Buscar preços atuais
    prices = {}
    for asset in account.keys():
        if asset != '_total_usdt':
            if asset == 'USDT':
                prices[asset] = 1.0
            else:
                try:
                    response = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={asset}USDT', timeout=5)
                    if response.status_code == 200:
                        prices[asset] = float(response.json()['price'])
                    else:
                        prices[asset] = None
                except:
                    prices[asset] = None

    portfolio = []
    for asset, data in account.items():
        if asset != '_total_usdt' and isinstance(data, dict):
            preco_atual = prices.get(asset, None)
            portfolio.append({
                'Ativo': asset,
                'Quantidade': f"{data.get('qty', 0):,.8f}",
                'Valor USD': f"${data.get('usd_val', 0):,.2f}",
                'Preço Atual': f"${preco_atual:,.4f}" if preco_atual else 'N/A'
            })
    if portfolio:
        df_portfolio = pd.DataFrame(portfolio)
        df_portfolio['Valor USD Num'] = df_portfolio['Valor USD'].str.replace('$', '').str.replace(',', '').astype(float)
        df_portfolio = df_portfolio.sort_values('Valor USD Num', ascending=False).drop('Valor USD Num', axis=1)
        st.dataframe(df_portfolio, use_container_width=True)
        # Gráfico de barras
        valores = df_portfolio['Valor USD'].str.replace('$', '').str.replace(',', '').astype(float)
        st.bar_chart(pd.DataFrame({'Valor USD': valores}, index=df_portfolio['Ativo']))
    else:
        st.info("Nenhuma composição de conta disponível.")
else:
    st.info("Dados de composição da conta não carregados.")

with tab2:
    # --- SEÇÃO 2: MÉTRICAS POR BOT ---
    st.subheader("🤖 Performance por Estratégia")

    if trades_list:
        df_trades = pd.DataFrame(trades_list)
        # Garante que a coluna estratégia existe
        bot_column = 'estrategia' if 'estrategia' in df_trades.columns else 'bot'
        if bot_column in df_trades.columns:
            bots = df_trades[bot_column].unique()
            cols_bots = st.columns(len(bots))
            
            for i, bot in enumerate(bots):
                with cols_bots[i]:
                    df_bot = df_trades[df_trades[bot_column] == bot]
                    lucro_bot = df_bot['pnl_usdt'].sum()
                    num_trades = len(df_bot)
                    # Cálculo de Win Rate
                    wins = len(df_bot[df_bot['pnl_usdt'] > 0])
                    wr = (wins / num_trades * 100) if num_trades > 0 else 0
                    
                    with st.container(border=True):
                        st.markdown(f"### Bot: {bot}")
                        st.metric("PnL Acumulado", f"${lucro_bot:,.2f}")
                        st.write(f"📊 Trades: {num_trades} | 🎯 Win Rate: {wr:.1f}%")
                        
                        if lucro_bot > 0: st.success("Perfil Lucrativo")
                        else: st.warning("Aguardando Performance")
        else:
            st.info("Coluna de estratégia não encontrada no log.")
    else:
        st.info("Nenhum trade realizado ainda para análise.")

st.divider()

# --- SEÇÃO 3: HISTÓRICO ---
with st.expander("📜 Ver Logs de Operações Completos"):
    if trades_list:
        st.dataframe(pd.DataFrame(trades_list).iloc[::-1], use_container_width=True)