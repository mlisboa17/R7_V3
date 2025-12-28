import streamlit as st
import pandas as pd
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger('dashboard')

# Optional: import Client lazily so the app starts even if dependency missing
try:
    from binance.client import Client
except Exception:
    Client = None

# Optional plotly and autorefresh
try:
    import plotly.express as px
except Exception:
    px = None
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

# Importar gestor financeiro
try:
    from bots.gestor_financeiro import GestorFinanceiro
    gestor_financeiro = GestorFinanceiro(banca_inicial_mes=1685.46)
except Exception as e:
    logger.warning(f"Não foi possível importar GestorFinanceiro: {e}")
    gestor_financeiro = None

# Configuração da Página
st.set_page_config(page_title="R7 V3 - Live Dashboard", layout="wide")
load_dotenv()

# Auto-refresh every 30s (if available)
if st_autorefresh:
    st_autorefresh(interval=30000, key="datarefresh")
else:
    st.write("⚠️ `streamlit-autorefresh` não instalado; atualizações manuais necessárias")

# Configurações de Banca
SALDO_INICIAL = 1743.12
META_DIARIA = 17.43

# Conexão Binance
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')

client = None
try:
    from tools.binance_wrapper import get_binance_client
    if api_key and api_secret:
        client = get_binance_client(api_key, api_secret)
except Exception:
    # fallback: keep previous behavior if wrapper/import not available
    if Client and api_key and api_secret:
        try:
            client = Client(api_key, api_secret)
        except Exception as e:
            client = None
            st.warning(f"Não foi possível conectar com Binance: {e}")


def buscar_dados_reais():
    """Busca saldo total da Binance (todos os ativos spot convertidos para USDT)."""
    if not client:
        raise RuntimeError("Cliente Binance não configurado. Verifique BINANCE_API_KEY/SECRET na .env")
    
    try:
        account = client.get_account()
        total_usdt = 0.0
        
        # Obter preços de uma vez para eficiência
        all_tickers = client.get_all_tickers()
        prices = {ticker['symbol']: float(ticker['price']) for ticker in all_tickers}
        
        for asset in account['balances']:
            free = float(asset['free'])
            locked = float(asset['locked'])
            amount = free + locked
            if amount > 0.0001:
                if asset['asset'] == 'USDT':
                    total_usdt += amount
                else:
                    symbol_usdt = f"{asset['asset']}USDT"
                    if symbol_usdt in prices:
                        price = prices[symbol_usdt]
                        valor_usdt = amount * price
                        total_usdt += valor_usdt
        
        return total_usdt
    except Exception as e:
        logger.error(f"Erro ao buscar saldo real: {e}")
        return SALDO_INICIAL

# Interface Streamlit
st.title("📊 R7 V3 - Monitoramento de Banca")

# Criar abas
tab_principal, tab_bots = st.tabs(["📈 Visão Geral", "🤖 Performance dos Bots"])

with tab_principal:
    if client:
        st.markdown(f"**Status:** Conectado à Binance (API)")
    else:
        st.markdown(f"**Status:** Modo demo / sem conexão com Binance (verifique .env)")

    # Sidebar para métricas rápidas
    st.sidebar.header("Configurações do Ciclo")
    st.sidebar.write(f"Banca Inicial: ${SALDO_INICIAL:.2f}")
    st.sidebar.write(f"Meta Diária (1%): ${META_DIARIA:.2f}")

    def convert_asset_to_usdt(asset, amount):
        asset = asset.upper()
        if amount == 0:
            return 0.0
        if asset == 'USDT':
            return amount
        # try direct USDT pair
        symbols = [f"{asset}USDT", f"{asset}BUSD"]
        for sym in symbols:
            try:
                t = client.get_symbol_ticker(symbol=sym)
                price = float(t.get('price', 0))
                if price > 0:
                    # If pair is BUSD, convert BUSD to USDT
                    if sym.endswith('BUSD'):
                        busd_usdt = 1.0
                        try:
                            b = client.get_symbol_ticker(symbol='BUSDUSDT')
                            busd_usdt = float(b.get('price', 1.0)) or 1.0
                        except Exception:
                            busd_usdt = 1.0
                        return amount * price * busd_usdt
                    return amount * price
            except Exception:
                continue
        # fallback: try to find any symbol like TOKENBTC then convert BTC->USDT
        try:
            # common: assetBTC then BTCUSDT
            t = client.get_symbol_ticker(symbol=f"{asset}BTC")
            price_asset_btc = float(t.get('price', 0))
            if price_asset_btc > 0:
                btc_usdt = float(client.get_symbol_ticker(symbol='BTCUSDT').get('price', 0))
                return amount * price_asset_btc * btc_usdt
        except Exception:
            pass
        return 0.0

    # Main content da aba principal
    try:
        # --- CONSULTA FORÇADA: calcula saldo total convertido para USDT ---

        total_usdt = 0.0
        try:
            info = client.get_account()
            for bal in info.get('balances', []):
                free = float(bal.get('free') or 0)
                locked = float(bal.get('locked') or 0)
                amount = free + locked
                if amount <= 0:
                    continue
                asset = bal.get('asset')
                val = convert_asset_to_usdt(asset, amount)
                total_usdt += val
        except Exception as e:
            # fallback to USDT balance only
            try:
                total_usdt = buscar_dados_reais()
            except Exception:
                total_usdt = SALDO_INICIAL
    except Exception as e:
        st.error(f"Erro ao calcular saldo: {e}")
        total_usdt = SALDO_INICIAL

    saldo_agora = total_usdt
    lucro_abs = saldo_agora - SALDO_INICIAL
    progresso = (lucro_abs / META_DIARIA) if lucro_abs > 0 else 0.0

    # Métricas: Inicial (fixo), Saldo do Momento (calculado), Resultado
    col1, col2, col3 = st.columns(3)
    col1.metric("Banca Inicial", f"${SALDO_INICIAL:,.2f}")
    col2.metric("Saldo do Momento (USDT)", f"${saldo_agora:,.2f}", f"${lucro_abs:,.2f}")
    col3.metric("Resultado", f"${lucro_abs:,.2f}", f"{(lucro_abs/SALDO_INICIAL)*100:.2f}%")

    # Enviar relatório instantâneo via Telegram (controlado por session_state para evitar spam)
    try:
        import time
        from tools.send_telegram_message import send as send_telegram
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        now = int(time.time())
        last = st.session_state.get('last_sync', 0)
        # envia no máximo a cada 5 minutos
        if token and chat_id and (now - last) > 300:
            msg = f"📊 SINCRONIZAÇÃO: Minha banca inicial era ${SALDO_INICIAL:.2f}. Identifiquei agora na Binance o total de ${saldo_agora:,.2f}. Iniciando rastreio."
            try:
                send_telegram(token, chat_id, msg)
                st.session_state['last_sync'] = now
                st.success('Relatório de sincronização enviado ao Telegram')
            except Exception as e:
                st.warning(f"Falha ao enviar Telegram: {e}")
    except Exception:
        pass

    # Barra de Progresso Visual
    st.write("### Progresso da Meta")
    st.progress(min(max(progresso, 0.0), 1.0))

    # Relatório Financeiro do Gestor
    if gestor_financeiro:
        st.write("### 📊 Relatório Financeiro Diário")
        try:
            relatorio = gestor_financeiro.relatorio_diario()
            status_meta = gestor_financeiro.status_atual()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Saldo Inicial Hoje", f"${relatorio['saldo_inicial']:.2f}")
            with col2:
                st.metric("Lucro do Dia", f"${relatorio['lucro_do_dia']:.2f}")
            with col3:
                st.metric("Meta Diária", f"${relatorio['meta_diaria']:.2f}")
            with col4:
                progresso_meta = relatorio['progresso_percentual']
                st.metric("Progresso Meta", f"{progresso_meta:.1f}%", 
                         delta="✅ Meta Batida!" if relatorio['meta_batida'] else f"{progresso_meta:.1f}%")
            
            # Barra de progresso da meta financeira
            st.write("#### Progresso da Meta Diária (Gestor Financeiro)")
            st.progress(min(max(progresso_meta / 100, 0.0), 1.0))
            
            # Informações adicionais
            st.write(f"**Trades Realizados Hoje:** {relatorio['trades_realizados']}")
            st.write(f"**Lucro Acumulado Mês:** ${relatorio['lucro_acumulado_mes']:.2f}")
            
        except Exception as e:
            st.warning(f"Erro ao carregar relatório financeiro: {e}")
    else:
        st.info("Gestor financeiro não disponível")

    # Pizza 'Livre' vs 'Em Trade' — exemplo simples (assume 'em trade' = total - free)
    st.write("### Distribuição: Livre vs Em Trade")
    if client:
        info = client.get_account()
        balances = [d for d in info.get('balances', []) if float(d.get('free', 0) or 0) > 0 or float(d.get('locked', 0) or 0) > 0]
        # For simplicity compute total USDT free/locked
        free_usdt = sum(float(d.get('free') or 0) for d in balances if d.get('asset') == 'USDT')
        locked_usdt = sum(float(d.get('locked') or 0) for d in balances if d.get('asset') == 'USDT')
        livre = free_usdt
        em_trade = locked_usdt
    else:
        livre = saldo_agora * 0.9
        em_trade = saldo_agora * 0.1

    pie = pd.DataFrame({'quantidade': [livre, em_trade]}, index=['Livre', 'Em Trade'])
    # Prefer Plotly pie if available, otherwise show as dataframe
    if px:
        fig = px.pie(pie.reset_index().rename(columns={'index': 'tipo'}), names='tipo', values='quantidade', title='Livre vs Em Trade', hole=0.3)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(pie)

with tab_bots:
    st.header("🤖 Performance Individual dos Bots")
    st.write("Análise detalhada do desempenho de cada estratégia de trading")

    try:
        # Importar funções de estatísticas e configurações
        from bots.monthly_stats import get_daily_breakdown, get_monthly_accumulated_by_bot
        import json

        # Carregar configurações
        with open('config/settings.json', 'r') as f:
            settings = json.load(f)

        # Obter dados diários e mensais
        hoje = get_daily_breakdown()  # Ex: {'scalping_v6': 5.40, 'swing_rwa': 0.0}
        mensal = get_monthly_accumulated_by_bot()  # Ex: {'scalping_v6': 125.30, 'swing_rwa': 89.20}

        # Calcular totais para percentuais
        total_hoje = sum(hoje.values())
        total_mensal = sum(mensal.values())

        # --- Banca inicial e saldo mensal ---
        from bots.monthly_stats import get_monthly_balance
        banca_inicial = settings.get('banca_referencia_usdt', 0.0)
        saldo_atual = get_monthly_balance() or 0.0
        variacao = saldo_atual - banca_inicial
        variacao_pct = (variacao / banca_inicial * 100) if banca_inicial else 0.0

        # Cor condicional para variação
        cor_variacao = '#2ECC71' if variacao >= 0 else '#FF6B6B'

        # Card resumo da banca
        st.markdown(f"""
        <div style="border: 2px solid #222; border-radius: 10px; padding: 15px; margin: 10px 0; background-color: rgba(0,0,0,0.03);">
            <div style="display:flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size:12px; color:#888;">Banca Inicial (referência)</div>
                    <div style="font-size:20px; font-weight:bold;">${banca_inicial:.2f}</div>
                </div>
                <div>
                    <div style="font-size:12px; color:#888;">Saldo Atual (mês)</div>
                    <div style="font-size:20px; font-weight:bold;">${saldo_atual:.2f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size:12px; color:#888;">Variação</div>
                    <div style="font-size:18px; font-weight:bold; color:{cor_variacao};">{variacao:+.2f} USD</div>
                    <div style="font-size:12px; color:{cor_variacao};">{variacao_pct:+.1f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Configurações dos bots com informações detalhadas
        moedas_por_estrategia = {
            'scalping_v6': ['SOL', 'ADA', 'DOT', 'LINK', 'AVAX', 'MATIC', 'ALGO', 'VET', 'ICP', 'FIL', 'TRX', 'ETC', 'XLM', 'THETA'],
            'swing_rwa': ['BTC', 'ETH', 'BNB', 'LTC', 'XRP', 'ADA', 'DOT', 'LINK', 'AVAX', 'MATIC', 'ICP', 'NEAR'],
            'momentum_boost': ['SOL', 'AVAX', 'MATIC', 'NEAR', 'FLOW', 'MANA', 'SAND', 'AXS', 'CHZ', 'ENJ', 'FTM', 'THETA'],
            'mean_reversion': ['TRX', 'XLM', 'VET', 'BAT', 'OMG', 'LSK', 'QTUM', 'XEM', 'WAVES', 'STRAT', 'ARK', 'BTG']
        }

        bots_config = {
            'scalping_v6': {'nome': 'Scalping V6', 'emoji': '⚡', 'cor': '#FF6B6B', 'desc': 'Scalping de curto prazo'},
            'swing_rwa': {'nome': 'Swing RWA', 'emoji': '📈', 'cor': '#4ECDC4', 'desc': 'Swing trading'},
            'momentum_boost': {'nome': 'Momentum Boost', 'emoji': '🚀', 'cor': '#45B7D1', 'desc': 'Momentum forte'},
            'mean_reversion': {'nome': 'Mean Reversion', 'emoji': '🔄', 'cor': '#96CEB4', 'desc': 'Reversão à média'}
        }

        # Cards em grid - 2 colunas
        cols = st.columns(2)

        for i, (bot_key, config) in enumerate(bots_config.items()):
            with cols[i % 2]:
                # Obter configurações do bot
                bot_settings = settings.get('estrategias', {}).get(bot_key, {})
                is_active = bot_settings.get('ativo', False)
                moedas = moedas_por_estrategia.get(bot_key, [])
                
                # Status do bot
                status_emoji = "🟢" if is_active else "🔴"
                status_text = "ATIVO" if is_active else "INATIVO"

                # Dados do bot
                lucro_hoje = hoje.get(bot_key, 0.0)
                lucro_mensal = mensal.get(bot_key, 0.0)

                # Percentuais
                pct_hoje = (lucro_hoje / total_hoje * 100) if total_hoje > 0 else 0
                pct_mensal = (lucro_mensal / total_mensal * 100) if total_mensal > 0 else 0

                # Card com métricas expandidas
                st.markdown(f"""
                <div style="border: 2px solid {config['cor']}; border-radius: 10px; padding: 20px; margin: 10px 0; background-color: rgba(255,255,255,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="color: {config['cor']}; margin: 0;">{config['emoji']} {config['nome']}</h3>
                        <span style="background-color: {config['cor']}20; color: {config['cor']}; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">{status_emoji} {status_text}</span>
                    </div>
                    
                    <div style="font-size: 14px; color: #888; margin-bottom: 15px;">
                        <strong>{bot_key.upper()}</strong> - {config['desc']}<br>
                        {len(moedas)} moedas | Entrada: ${bot_settings.get('entrada_usd', 0):.0f} | TP: {bot_settings.get('tp_pct', 0):.1f}% | SL: {bot_settings.get('sl_pct', 0):.1f}%
                    </div>

                    <div style="display: flex; justify-content: space-between; margin: 15px 0;">
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 24px; font-weight: bold; color: {config['cor']};">${lucro_hoje:.2f}</div>
                            <div style="font-size: 12px; color: #888;">Hoje</div>
                            <div style="font-size: 14px; color: {config['cor']}; font-weight: bold;">{pct_hoje:.1f}%</div>
                        </div>
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 24px; font-weight: bold; color: {config['cor']};">${lucro_mensal:.2f}</div>
                            <div style="font-size: 12px; color: #888;">Mês</div>
                            <div style="font-size: 14px; color: {config['cor']}; font-weight: bold;">{pct_mensal:.1f}%</div>
                        </div>
                    </div>

                    <div style="font-size: 12px; color: #666; margin-top: 10px;">
                        Moedas: {', '.join(moedas[:5])}{'...' if len(moedas) > 5 else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Tabela detalhada de performance mensal
        if mensal and total_mensal > 0:
            st.write("### 📋 Detalhes por Bot - Performance Mensal")
            
            # Preparar dados para a tabela
            dados_tabela = []
            for bot_key, valor in mensal.items():
                if valor > 0:
                    config = bots_config.get(bot_key, {'nome': bot_key, 'emoji': '🤖'})
                    percentual = (valor / total_mensal) * 100
                    dados_tabela.append({
                        'Bot': f"{config['emoji']} {config['nome']}",
                        'Lucro': f"${valor:.2f}",
                        'Percentual': f"{percentual:.1f}%"
                    })

            if dados_tabela:
                df_detalhes = pd.DataFrame(dados_tabela)
                st.dataframe(df_detalhes.set_index('Bot'), use_container_width=True)
            else:
                st.info("Nenhum lucro registrado ainda este mês.")
        else:
            st.info("Aguardando dados de performance dos bots...")

    except Exception as e:
        st.error(f"Erro ao carregar dados dos bots: {e}")
        st.info("Verifique se o sistema está rodando e gerando estatísticas.")

    # Voltar para a aba principal para adicionar mais conteúdo
    st.write("### Ativos na Carteira")
    if client:
        try:
            info = client.get_account()

            # Filtra apenas o que você realmente tem saldo
            df_balances = pd.DataFrame(info['balances'])
            df_balances[['free', 'locked']] = df_balances[['free', 'locked']].apply(pd.to_numeric)
            df_portfolio = df_balances[(df_balances['free'] > 0) | (df_balances['locked'] > 0)].copy()

            # Adicionar coluna de valor em USDT
            df_portfolio['valor_usdt'] = df_portfolio.apply(
                lambda row: convert_asset_to_usdt(row['asset'], row['free'] + row['locked']), axis=1
            )

            st.write(df_portfolio)
            # Garante que os dados existam
            if 'valor_usdt' in df_portfolio.columns and not df_portfolio.empty:
                fig = px.pie(df_portfolio, values='valor_usdt', names='asset', hole=0.3)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Aguardando dados da Binance para gerar o gráfico...")
        except Exception as e:
            st.error(f"Erro ao conectar com a Binance ou processar dados: {e}")
    else:
        st.warning("Cliente Binance não disponível para mostrar carteira.")

# Nota: o Streamlit detecta mudanças e atualiza automaticamente quando a página é recarregada.
