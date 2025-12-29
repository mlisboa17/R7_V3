import streamlit as st
import pandas as pd
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()


# Importar funções e dados
try:
    from bots.gestor_financeiro import GestorFinanceiro
    from bots.monthly_stats import get_daily_breakdown, get_monthly_accumulated_by_bot, get_monthly_balance
    gestor = GestorFinanceiro()
except Exception as e:
    st.error(f"Erro ao importar módulos: {e}")
    st.stop()

# --- ABAS DO DASHBOARD ---
abas = [
    "Resumo Geral",
    "Performance dos Bots",
    "Resumo Diário",
    "Mais Informações"
]
tab_resumo, tab_bots, tab_diario, tab_info = st.tabs(abas)

# --- Aba Resumo Geral ---
with tab_resumo:
    # Autorefresh a cada 5 segundos
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5000, key="saldo_refresh")
    except ImportError:
        st.warning("streamlit-autorefresh não instalado. Atualize manualmente.")
    # Botão para atualizar saldo da Binance
    st.markdown("---")
    if st.button('🔄 Atualizar saldo da Binance'):
        with st.spinner('Atualizando saldo da Binance...'):
            import subprocess
            result = subprocess.run(['python', 'update_composition.py'], capture_output=True, text=True)
            if result.returncode == 0:
                st.success('Saldo atualizado com sucesso!')
            else:
                st.error(f'Erro ao atualizar saldo: {result.stderr}')
    st.markdown("---")
    import numpy as np
    stats = gestor.status_atual()
    saldo_inicial_mes = stats.get('saldo_inicial_mes', 0.0)
    saldo_final_mes = stats.get('saldo_final_mes', 0.0)
    lucro_mes = stats.get('lucro_mes', 0.0)
    trades_mes = stats.get('trades_mes', 0)
    win_rate_mes = stats.get('win_rate_mes', 0.0)
    drawdown_mes = stats.get('drawdown_mes', 0.0)

    hoje_str = datetime.now().strftime('%Y-%m-%d')
    dias = gestor.dados.get('dias', {})
    dia = dias.get(hoje_str, {})
    saldo_inicial_dia = dia.get('saldo_inicial', 0.0)
    saldo_final_dia = dia.get('saldo_final', saldo_inicial_dia + dia.get('lucro_do_dia', 0.0))
    lucro_dia = dia.get('lucro_do_dia', 0.0)
    trades_dia = dia.get('trades_realizados', 0)
    win_rate_dia = dia.get('win_rate', 0.0)
    drawdown_dia = dia.get('drawdown', 0.0)

    # Calcular retornos diários para Sharpe/Sortino
    retornos = []
    for d in dias.values():
        ini = d.get('saldo_inicial', 0.0)
        fim = d.get('saldo_final', ini + d.get('lucro_do_dia', 0.0))
        if ini > 0:
            retornos.append((fim - ini) / ini)

    # Sharpe Ratio (assume risk-free rate = 0)
    sharpe = np.nan
    if len(retornos) > 1:
        sharpe = (np.mean(retornos) / np.std(retornos, ddof=1)) * np.sqrt(252)

    # Sortino Ratio (downside risk)
    sortino = np.nan
    if len(retornos) > 1:
        downside = [r for r in retornos if r < 0]
        downside_std = np.std(downside, ddof=1) if downside else 0.0
        if downside_std > 0:
            sortino = (np.mean(retornos) / downside_std) * np.sqrt(252)

    # Profit Factor
    lucros = [d.get('lucro_do_dia', 0.0) for d in dias.values() if d.get('lucro_do_dia', 0.0) > 0]
    perdas = [-d.get('lucro_do_dia', 0.0) for d in dias.values() if d.get('lucro_do_dia', 0.0) < 0]
    profit_factor = (sum(lucros) / sum(perdas)) if sum(perdas) > 0 else float('inf')

    # Explicações para cada métrica
    explicacoes = {
        "Saldo Inicial Mês": "Valor do saldo no início do mês.",
        "Saldo Atual Mês": "Saldo atual considerando todas as operações do mês.",
        "Lucro Mês": "Diferença entre saldo inicial e saldo atual do mês.",
        "Trades no Mês": "Quantidade total de operações realizadas no mês.",
        "Win Rate Mês": "Percentual de operações vencedoras no mês.",
        "Qtd. Trades Mês": "Quantidade de trades executados no mês.",
        "Drawdown Mês": "Maior perda acumulada a partir de um topo no mês.",
        "Profit Factor": "Relação entre o total ganho e o total perdido (quanto ganha para cada dólar perdido)."
    }

    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    col1.metric("Saldo Inicial Mês", f"${saldo_inicial_mes:,.2f}")
    col1.caption(explicacoes["Saldo Inicial Mês"])
    col2.metric("Saldo Atual Mês", f"${saldo_final_mes:,.2f}", f"${lucro_mes:,.2f}")
    col2.caption(explicacoes["Saldo Atual Mês"])
    col3.metric("Trades no Mês", trades_mes)
    col3.caption(explicacoes["Trades no Mês"])
    col4.metric("Win Rate Mês", f"{win_rate_mes:.1%}")
    col4.caption(explicacoes["Win Rate Mês"])
    col5.metric("Drawdown Mês", f"{drawdown_mes:.2f}")
    col5.caption(explicacoes["Drawdown Mês"])
    col6.metric("Profit Factor", f"{profit_factor:.2f}")
    col6.caption("Relação entre o total ganho e o total perdido. Quanto maior, melhor. Acima de 1,5 é robusto.")
    col7.metric("Sharpe Ratio", f"{sharpe:.2f}" if not np.isnan(sharpe) else "N/A")
    col7.caption("Retorno ajustado ao risco. Acima de 1 é bom. Compara retorno médio e volatilidade.")
    col8.metric("Sortino Ratio", f"{sortino:.2f}" if not np.isnan(sortino) else "N/A")
    col8.caption("Versão do Sharpe que considera apenas volatilidade negativa (downside risk). Quanto maior, melhor.")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Saldo Inicial Hoje", f"${saldo_inicial_dia:,.2f}")
    col1.caption("Saldo no início do dia.")
    # Adiciona hora/minuto/segundo ao saldo do momento
    from datetime import datetime
    hora_atual = datetime.now().strftime('%H:%M:%S')
    col2.metric("Saldo Final Hoje", f"${saldo_final_dia:,.2f}", f"${lucro_dia:,.2f}")
    col2.caption(f"Saldo ao final do dia e lucro/prejuízo diário. (Atualizado às {hora_atual})")
    col3.metric("Trades Hoje", trades_dia)
    col3.caption("Quantidade de operações realizadas hoje.")
    col4.metric("Win Rate Hoje", f"{win_rate_dia:.1%}")
    col4.caption("Percentual de operações vencedoras hoje.")
    col5.metric("Drawdown Hoje", f"{drawdown_dia:.2f}")
    col5.caption("Maior perda acumulada a partir de um topo no dia.")

    # --- Saldo Real Consolidado e Composição Detalhada ---
    st.markdown("---")
    st.subheader("Saldo Real Consolidado e Composição de Ativos")
    import json
    try:
        with open('data/account_composition.json', 'r', encoding='utf-8') as f:
            comp = json.load(f)
        saldo_real = comp.get('_total_usdt', 0.0)
        st.metric("Saldo Real Total (USDT)", f"${saldo_real:,.2f}")
        st.write("**Composição detalhada:**")
        comp_table = {k: v for k, v in comp.items() if not k.startswith('_') and k != 'Earn/Staking'}
        st.dataframe(pd.DataFrame(list(comp_table.items()), columns=["Ativo", "Valor USDT"]).sort_values("Valor USDT", ascending=False), use_container_width=True)
        st.caption("Fonte: account_composition.json gerado via API Binance.")
    except Exception as e:
        st.warning(f"Não foi possível carregar composição detalhada: {e}")


# --- Aba Performance dos Bots ---
with tab_bots:
    st.header("Performance dos Bots")
    try:
        hoje = get_daily_breakdown()  # {'bot1': valor, ...}
        mensal = get_monthly_accumulated_by_bot()  # {'bot1': valor, ...}
        total_hoje = sum(hoje.values())
        total_mensal = sum(mensal.values())
        bots = sorted(set(list(hoje.keys()) + list(mensal.keys())))
        df = pd.DataFrame({
            'Bot': bots,
            'Lucro Hoje (USDT)': [hoje.get(b, 0.0) for b in bots],
            '% Hoje': [100*hoje.get(b, 0.0)/total_hoje if total_hoje else 0 for b in bots],
            'Lucro Mês (USDT)': [mensal.get(b, 0.0) for b in bots],
            '% Mês': [100*mensal.get(b, 0.0)/total_mensal if total_mensal else 0 for b in bots],
        })
        st.dataframe(df.set_index('Bot'), use_container_width=True)

        # Histórico completo do mês
        import json
        st.subheader("Histórico Diário dos Bots no Mês")
        try:
            with open('data/monthly_stats.json', 'r', encoding='utf-8') as f:
                stats = json.load(f)
            from datetime import date
            mes_atual = date.today().isoformat()[:7]
            mes_data = stats.get(mes_atual, {})
            # Coletar todos os dias e bots
            dias = sorted([d for d in mes_data.keys() if d != 'balance'])
            todos_bots = set()
            for d in dias:
                for b in mes_data[d].keys():
                    todos_bots.add(b)
            todos_bots = sorted(todos_bots)
            # Montar tabela
            historico = []
            for d in dias:
                linha = {'Data': d}
                for b in todos_bots:
                    linha[b] = mes_data[d].get(b, 0.0)
                historico.append(linha)
            if historico:
                df_hist = pd.DataFrame(historico)
                st.dataframe(df_hist.set_index('Data'), use_container_width=True)
            else:
                st.info("Sem histórico disponível para o mês.")
        except Exception as e:
            st.warning(f"Erro ao carregar histórico mensal: {e}")
    except Exception as e:
        st.warning(f"Erro ao carregar performance dos bots: {e}")

# --- Aba Resumo Diário ---
with tab_diario:
    st.header("Resumo Diário")
    try:
        hoje = datetime.now().strftime('%Y-%m-%d')
        dias = gestor.dados.get('dias', {})
        dia = dias.get(hoje, {})
        saldo_inicial = dia.get('saldo_inicial', 0.0)
        saldo_final = dia.get('saldo_final', saldo_inicial + dia.get('lucro_do_dia', 0.0))
        lucro_dia = dia.get('lucro_do_dia', 0.0)
        trades_hoje = dia.get('trades_realizados', 0)
        win_rate_hoje = dia.get('win_rate', 0.0)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Saldo Inicial Hoje", f"${saldo_inicial:,.2f}")
        col2.metric("Saldo Final Hoje", f"${saldo_final:,.2f}", f"${lucro_dia:,.2f}")
        col3.metric("Trades Hoje", trades_hoje)
        col4.metric("Win Rate Hoje", f"{win_rate_hoje:.1%}")
    except Exception as e:
        st.warning(f"Erro ao carregar resumo diário: {e}")

# --- Aba Mais Informações ---
with tab_info:
    st.header("ℹ️ Mais Informações e Estatísticas Avançadas")
    import json
    import platform
    from collections import defaultdict

    # 1. Moedas em aberto por bot (baseado em trades_log.json)
    st.subheader("Moedas em Aberto por Bot")
    try:
        with open('data/trades_log.json', 'r', encoding='utf-8') as f:
            trades = json.load(f)
        open_by_bot = defaultdict(set)
        for trade in trades:
            bot = trade.get('estrategia', 'desconhecido')
            pair = trade.get('pair', '')
            if pair and bot:
                symbol = pair.replace('USDT', '').replace('BUSD', '')
                open_by_bot[bot].add(symbol)
        for bot, moedas in open_by_bot.items():
            st.write(f"**{bot.upper()}**: {', '.join(sorted(moedas)) if moedas else 'Nenhuma'}")
    except Exception as e:
        st.warning(f"Não foi possível carregar trades_log.json: {e}")

    # 2. Estatísticas rápidas dos ativos atuais
    st.subheader("Estatísticas dos Ativos Atuais")
    try:
        with open('data/account_composition.json', 'r', encoding='utf-8') as f:
            comp = json.load(f)
        ativos = {k: v for k, v in comp.items() if not k.startswith('_') and k != 'Earn/Staking' and v > 0}
        st.write(f"Total de ativos: {len(ativos)}")
        st.write(f"Ativos com saldo: {', '.join(ativos.keys())}")
        st.write(f"Saldo total estimado (USDT): {comp.get('_total_usdt', 0):,.2f}")
    except Exception as e:
        st.warning(f"Não foi possível carregar account_composition.json: {e}")

    # 3. Lucro por moeda e por bot
    st.subheader("Lucro por Moeda e por Bot")
    try:
        with open('data/trades_log.json', 'r', encoding='utf-8') as f:
            trades = json.load(f)
        lucro_por_moeda = defaultdict(float)
        lucro_por_bot = defaultdict(float)
        for trade in trades:
            pair = trade.get('pair', '')
            bot = trade.get('estrategia', 'desconhecido')
            pnl = float(trade.get('pnl_usdt', 0))
            if pair:
                symbol = pair.replace('USDT', '').replace('BUSD', '')
                lucro_por_moeda[symbol] += pnl
            if bot:
                lucro_por_bot[bot] += pnl
        if lucro_por_moeda:
            st.write("**Lucro por Moeda:**")
            df_lucro_moeda = pd.DataFrame(list(lucro_por_moeda.items()), columns=["Moeda", "Lucro USDT"])
            st.dataframe(df_lucro_moeda.sort_values("Lucro USDT", ascending=False), use_container_width=True)
        if lucro_por_bot:
            st.write("**Lucro por Bot:**")
            df_lucro_bot = pd.DataFrame(list(lucro_por_bot.items()), columns=["Bot", "Lucro USDT"])
            st.dataframe(df_lucro_bot.sort_values("Lucro USDT", ascending=False), use_container_width=True)
    except Exception as e:
        st.warning(f"Não foi possível calcular lucros por moeda/bot: {e}")

    # 4. Trades detalhados por dia
    st.subheader("Trades Detalhados por Dia")
    try:
        with open('data/trades_log.json', 'r', encoding='utf-8') as f:
            trades = json.load(f)
        if trades:
            df_trades = pd.DataFrame(trades)
            # Garante colunas principais
            for col in ['date', 'pair', 'estrategia', 'pnl_usdt']:
                if col not in df_trades.columns:
                    df_trades[col] = ''
            df_trades = df_trades.rename(columns={
                'date': 'Data',
                'pair': 'Par',
                'estrategia': 'Bot',
                'pnl_usdt': 'PnL (USDT)'
            })
            df_trades['Data'] = pd.to_datetime(df_trades['Data'], errors='coerce')

            # Filtros interativos
            datas_disponiveis = df_trades['Data'].dt.date.dropna().unique()
            bots_disponiveis = df_trades['Bot'].unique()
            pares_disponiveis = df_trades['Par'].unique()

            col1, col2, col3 = st.columns(3)
            with col1:
                data_filtro = st.date_input('Filtrar por Data', value=None, min_value=min(datas_disponiveis) if len(datas_disponiveis) else None, max_value=max(datas_disponiveis) if len(datas_disponiveis) else None)
            with col2:
                bot_filtro = st.multiselect('Filtrar por Bot', options=bots_disponiveis, default=list(bots_disponiveis))
            with col3:
                par_filtro = st.multiselect('Filtrar por Par', options=pares_disponiveis, default=list(pares_disponiveis))

            df_filtrado = df_trades.copy()
            if data_filtro:
                if isinstance(data_filtro, list):
                    # Suporte a múltiplas datas
                    df_filtrado = df_filtrado[df_filtrado['Data'].dt.date.isin(data_filtro)]
                else:
                    df_filtrado = df_filtrado[df_filtrado['Data'].dt.date == data_filtro]
            if bot_filtro:
                df_filtrado = df_filtrado[df_filtrado['Bot'].isin(bot_filtro)]
            if par_filtro:
                df_filtrado = df_filtrado[df_filtrado['Par'].isin(par_filtro)]

            # Ordena e exibe
            df_filtrado['Data'] = df_filtrado['Data'].dt.strftime('%Y-%m-%d')
            st.dataframe(df_filtrado.sort_values(['Data', 'Bot', 'Par']), use_container_width=True)
        else:
            st.info('Nenhum trade registrado.')
    except Exception as e:
        st.warning(f'Não foi possível carregar trades detalhados: {e}')

    # 5. Estatísticas do Sistema
    st.subheader("Estatísticas do Sistema")
    st.write(f"Sistema operacional: {platform.system()} {platform.release()}")
    st.write(f"Python: {platform.python_version()}")

    # 5. Resumo dos arquivos de dados

