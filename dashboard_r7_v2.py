# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime
from dotenv import load_dotenv
import plotly.graph_objects as go

# Força o reconhecimento da pasta raiz para evitar erros de importação
diretorio_raiz = os.path.dirname(os.path.abspath(__file__))
if diretorio_raiz not in sys.path:
    sys.path.append(diretorio_raiz)

# Componente de refresh (Instale via: pip install streamlit-autorefresh)
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st.error("Por favor, instale: pip install streamlit-autorefresh")
    st.stop()

# Configuração da Página
st.set_page_config(page_title="R7_V3 Sniper V2", layout="wide", page_icon="📈")

# 🔄 AUTO-REFRESH GLOBAL (30 SEGUNDOS) - Atualiza saldos mais frequentemente
st_autorefresh(interval=30000, key="global_refresh")

# FORÇA LIMPEZA DE CACHE A CADA REFRESH PARA SALDOS DINÂMICOS
st.cache_data.clear()

load_dotenv()

# Configuração de categorias
CATEGORIA_CONFIG = {
    'MEME': {'cor': '#ff6b6b', 'nome': 'Meme Coins'},
    'BLUE_CHIP': {'cor': '#4ecdc4', 'nome': 'Blue Chips'},
    'DEFI': {'cor': '#45b7d1', 'nome': 'DeFi'},
    'LAYER2': {'cor': '#96ceb4', 'nome': 'Layer 2'},
    'DEFAULT': {'cor': '#666666', 'nome': 'Outros'}
}

# Force rerun para evitar cache
if "refresh_count" not in st.session_state:
    st.session_state.refresh_count = 0
st.session_state.refresh_count += 1

# --- IMPORTAÇÃO DE MÓDULOS ---
try:
    from bots.gestor_financeiro import GestorFinanceiro
    from bots.stop_loss_engine import StopLossEngine
    from bots.venda_inteligente import VendaInteligente
    gestor = GestorFinanceiro()
    stop_loss_engine = StopLossEngine()
    venda_inteligente = VendaInteligente()
except Exception as e:
    st.error(f"Erro ao carregar módulos: {e}")
    st.stop()

# --- FUNÇÃO PARA ANÁLISE DE PERDAS ---
@st.cache_data(ttl=45, show_spinner="🔍 Analisando perdas...")  
def get_analise_perdas(df_trades):
    """Analisa padrões de perdas para identificar problemas."""
    if df_trades.empty or 'pnl' not in df_trades.columns:
        return {}
    
    trades_negativas = df_trades[df_trades['pnl'] < 0]
    
    if trades_negativas.empty:
        return {"sem_perdas": True, "mensagem": "🎉 Nenhuma trade com prejuízo!"}
    
    analise = {
        "sem_perdas": False,
        "total_perdas": len(trades_negativas),
        "valor_total_perdido": trades_negativas['pnl'].sum(),
        "maior_perda": trades_negativas['pnl'].min(),
        "perda_media": trades_negativas['pnl'].mean()
    }
    
    # Análise por estratégia/bot
    if 'estrategia' in trades_negativas.columns:
        perdas_por_bot = trades_negativas.groupby('estrategia')['pnl'].agg(['count', 'sum', 'mean']).round(2)
        analise["perdas_por_bot"] = perdas_por_bot.to_dict('index')
    
    # Análise por moeda
    coluna_moeda = 'symbol' if 'symbol' in trades_negativas.columns else 'pair'
    if coluna_moeda in trades_negativas.columns:
        perdas_por_moeda = trades_negativas.groupby(coluna_moeda)['pnl'].agg(['count', 'sum']).round(2)
        # Identifica moedas mais problemáticas (mais de 1 perda)
        moedas_problematicas = perdas_por_moeda[perdas_por_moeda['count'] > 1].sort_values('sum')
        analise["moedas_problematicas"] = moedas_problematicas.to_dict('index')
    
    # Padrão temporal (se há timestamp)
    if 'timestamp' in trades_negativas.columns:
        trades_negativas_copy = trades_negativas.copy()
        trades_negativas_copy['hora'] = trades_negativas_copy['timestamp'].dt.hour
        perdas_por_hora = trades_negativas_copy.groupby('hora')['pnl'].count()
        if not perdas_por_hora.empty:
            hora_mais_perdas = perdas_por_hora.idxmax()
            analise["hora_mais_perdas"] = hora_mais_perdas
            analise["perdas_na_hora_pico"] = perdas_por_hora.max()
    
    return analise

# --- FUNÇÃO PARA LER ÚLTIMAS TRADES VIA REST API ---
# IMPLEMENTAÇÃO DIRETA VIA BINANCE API
def get_ultimas_trades():
    """Busca histórico de trades real da Binance via REST API"""
    import requests
    import hmac
    import hashlib
    import time
    from urllib.parse import urlencode
    
    try:
        # 0. TESTE DE CONECTIVIDADE PRIMEIRO
        if not test_binance_connectivity():
            st.info("📡 API Binance indisponível - usando dados locais")
            return get_trades_fallback()
        
        # 1. CARREGA CREDENCIAIS
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET_KEY')
        
        if not api_key or not api_secret:
            st.info("🔑 Credenciais não encontradas - usando dados locais")
            return get_trades_fallback()
        
        # 2. BUSCA TRADES DOS Últimos 7 DIAS
        base_url = "https://api.binance.com"
        endpoint = "/api/v3/myTrades"
        
        # Calcula timestamp de 7 dias atrás
        sete_dias_atras = int((time.time() - (7 * 24 * 60 * 60)) * 1000)
        
        # 3. BUSCA SÍMBOLOS ATIVOS APENAS SE HOUVER TRADES REAIS
        # Em vez de buscar todos os símbolos, vamos usar uma abordagem mais eficiente
        try:
            # Primeiro, busca os símbolos que realmente têm trades recentes
            symbols_response = requests.get(
                f"{base_url}/api/v3/ticker/24hr",
                timeout=5
            )
            
            if symbols_response.status_code == 200:
                tickers = symbols_response.json()
                # Filtra apenas símbolos USDT com volume > 0
                symbols_com_volume = []
                for ticker in tickers:
                    if (ticker['symbol'].endswith('USDT') and 
                        float(ticker['volume']) > 0 and
                        ticker['symbol'] in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT']):
                        symbols_com_volume.append(ticker['symbol'])
                
                # Usa apenas os primeiros 3 símbolos para evitar rate limit
                symbols_para_buscar = symbols_com_volume[:3] if symbols_com_volume else ['BTCUSDT']
            else:
                # Fallback para símbolos seguros
                symbols_para_buscar = ['BTCUSDT']
                
        except Exception:
            symbols_para_buscar = ['BTCUSDT']  # Só BTC como fallback seguro
        
        all_trades = []
        timestamp_atual = int(time.time() * 1000)
        
        for symbol in symbols_para_buscar:
            try:
                # Usar parâmetros mais conservadores para evitar erros 400
                current_timestamp = int(time.time() * 1000)
                params = {
                    'symbol': symbol,
                    'limit': 10,  # Limite menor para evitar sobrecarga
                    'timestamp': current_timestamp,
                    'recvWindow': 60000  # Janela maior para evitar problemas de timing
                }
                
                # Remove startTime e endTime que podem causar erro 400
                # A API retornaá os trades mais recentes por padrão
                
                # Cria assinatura
                query_string = urlencode(params)
                signature = hmac.new(
                    api_secret.encode('utf-8'),
                    query_string.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                
                params['signature'] = signature
                
                headers = {
                    'X-MBX-APIKEY': api_key,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                # Faz requisição
                response = requests.get(
                    base_url + endpoint,
                    params=params,
                    headers=headers,
                    timeout=5
                )
                
                if response.status_code == 200:
                    trades_data = response.json()
                    
                    for trade in trades_data:
                        # Converte para formato padrão
                        trade_formatado = {
                            'timestamp': pd.to_datetime(int(trade['time']), unit='ms'),
                            'symbol': trade['symbol'],
                            'side': 'BUY' if trade['isBuyer'] else 'SELL',
                            'quantity': float(trade['qty']),
                            'price': float(trade['price']),
                            'commission': float(trade['commission']),
                            'commissionAsset': trade['commissionAsset'],
                            'realizedPnl': 0.0,  # Será calculado depois
                            'orderId': trade['orderId']
                        }
                        
                        # Calcula valor em USDT
                        if trade['symbol'].endswith('USDT'):
                            trade_formatado['value_usdt'] = float(trade['qty']) * float(trade['price'])
                        else:
                            trade_formatado['value_usdt'] = 0.0
                        
                        all_trades.append(trade_formatado)
                        
                elif response.status_code == 400:
                    # Não mostra erro para cada símbolo, apenas registra
                    continue
                elif response.status_code == 403:
                    st.warning("⚠️ Problema de permissão na API Binance")
                    break  # Para de tentar outros símbolos
                elif response.status_code == 429:
                    st.warning("⚠️ Rate limit atingido - aguarde")
                    break
                else:
                    # Para outros erros, não exibe para não poluir a tela
                    continue
                    
            except Exception as e:
                # Não mostra erro para cada símbolo
                continue
        
        # 4. PROCESSA DADOS
        if all_trades:
            df = pd.DataFrame(all_trades)
            
            # Ordena por timestamp
            df = df.sort_values('timestamp', ascending=False)
            
            # Calcula PnL simples (diferença entre compra/venda)
            df['pnl'] = 0.0
            
            # Agrupa por símbolo para calcular PnL
            for symbol in df['symbol'].unique():
                symbol_trades = df[df['symbol'] == symbol].sort_values('timestamp')
                
                buy_price = None
                buy_qty = 0
                
                for idx, trade in symbol_trades.iterrows():
                    if trade['side'] == 'BUY':
                        if buy_price is None:
                            buy_price = trade['price']
                            buy_qty = trade['quantity']
                        else:
                            # Média ponderada
                            total_cost = (buy_price * buy_qty) + (trade['price'] * trade['quantity'])
                            buy_qty += trade['quantity']
                            buy_price = total_cost / buy_qty
                            
                    elif trade['side'] == 'SELL' and buy_price is not None:
                        # Calcula PnL da venda
                        sell_value = trade['price'] * trade['quantity']
                        buy_value = buy_price * trade['quantity']
                        pnl = sell_value - buy_value - trade['commission']
                        
                        df.at[idx, 'pnl'] = pnl
                        
                        # Ajusta quantidade comprada
                        buy_qty -= trade['quantity']
                        if buy_qty <= 0:
                            buy_price = None
                            buy_qty = 0
            
            # Adiciona metadados
            timestamp = datetime.now().strftime('%H:%M:%S')
            total_trades = len(df)
            periodo = "7 dias" if total_trades > 0 else "sem dados"
            
            st.success(f"✅ [{timestamp}] {total_trades} trades API Binance ({periodo})")
            
            return df.head(50)  # Limita a 50 trades mais recentes
            
        else:
            st.info("📊 Nenhum trade encontrado nos últimos 7 dias")
            return get_trades_fallback()
            
    except Exception as e:
        st.error(f"❌ Erro buscando histórico: {e}")
        return get_trades_fallback()

def get_trades_fallback():
    """Função fallback para trades armazenados localmente"""
    try:
        # PRIORIDADE: Dados reais do sistema
        path_master = os.path.join(diretorio_raiz, 'data', 'trades_master.json')
        if os.path.exists(path_master):
            with open(path_master, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            trades_historico = data.get('trades_historico', [])
            if trades_historico:
                df = pd.DataFrame(trades_historico[-30:])  # Últimas 30 trades
                
                # Corrige estrutura inconsistente de timestamp/date
                for idx, row in df.iterrows():
                    if pd.isna(row.get('timestamp')) or row.get('timestamp') is None:
                        # Se não tem timestamp, cria um baseado na data
                        if 'date' in row and row['date']:
                            df.at[idx, 'timestamp'] = f"{row['date']}T23:59:59"
                        else:
                            df.at[idx, 'timestamp'] = datetime.now().isoformat()
                
                # Converte timestamp para datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                
                # Padroniza colunas
                if 'pair' in df.columns and 'symbol' not in df.columns:
                    df['symbol'] = df['pair']
                
                # Padroniza PnL
                if 'pnl_usdt' in df.columns and 'pnl' not in df.columns:
                    df['pnl'] = df['pnl_usdt'].astype(float)
                elif 'lucro_brl' in df.columns and 'pnl' not in df.columns:
                    df['pnl'] = df['lucro_brl'].astype(float)
                
                # Remove entradas inválidas
                df = df.dropna(subset=['timestamp'])
                    
                timestamp = datetime.now().strftime('%H:%M:%S')
                st.info(f"📂 [{timestamp}] Dados locais: {len(df)} trades")
                    
                return df.sort_values('timestamp', ascending=False) if not df.empty else df
        
        # Fallback para history_log.json
        path_legacy = os.path.join(diretorio_raiz, 'data', 'history_log.json')
        if os.path.exists(path_legacy):
            with open(path_legacy, 'r', encoding='utf-8') as f:
                trades = json.load(f)
            
            if trades:
                df = pd.DataFrame(trades[-20:])
                
                if 'date' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['date'] + 'T12:00:00')
                else:
                    df['timestamp'] = pd.to_datetime(datetime.now())
                
                if 'lucro_brl' in df.columns:
                    df['pnl'] = df['lucro_brl'].astype(float)
                    
                return df.sort_values('timestamp', ascending=False) if not df.empty else df
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar trades: {e}")
        return pd.DataFrame()

# --- FUNÇÃO PARA BUSCAR ORDENS ATIVAS VIA REST API ---
def get_ordens_ativas_api():
    """Busca ordens abertas diretamente da Binance via REST API"""
    import requests
    import hmac
    import hashlib
    import time
    from urllib.parse import urlencode
    
    try:
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET_KEY')
        
        if not api_key or not api_secret:
            return []
        
        # Busca ordens abertas
        base_url = "https://api.binance.com"
        endpoint = "/api/v3/openOrders"
        timestamp = int(time.time() * 1000)
        
        params = {
            'timestamp': timestamp,
            'recvWindow': 5000
        }
        
        query_string = urlencode(params)
        signature = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        params['signature'] = signature
        
        headers = {
            'X-MBX-APIKEY': api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.get(
            base_url + endpoint,
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            ordens = response.json()
            
            posicoes_ativas = []
            for ordem in ordens:
                posicao = {
                    'symbol': ordem['symbol'],
                    'side': ordem['side'],
                    'quantity': float(ordem['origQty']),
                    'price': float(ordem['price']),
                    'value_usdt': float(ordem['origQty']) * float(ordem['price']),
                    'status': ordem['status'],
                    'timestamp': pd.to_datetime(int(ordem['time']), unit='ms'),
                    'orderId': ordem['orderId']
                }
                posicoes_ativas.append(posicao)
            
            timestamp_fmt = datetime.now().strftime('%H:%M:%S')
            if posicoes_ativas:
                st.success(f"✅ [{timestamp_fmt}] {len(posicoes_ativas)} ordens ativas da API")
            
            return posicoes_ativas
            
    except Exception as e:
        st.warning(f"⚠️ Erro buscando ordens ativas: {e}")
        return []

# --- FUNÇÃO PARA HISTÓRICO COM FILTROS DE PERÍODO ---
def get_historico_filtrado_api(dias=7, symbols_filtro=None):
    """Busca histórico filtrado por período e símbolos específicos"""
    import requests
    import hmac
    import hashlib
    import time
    from urllib.parse import urlencode
    
    try:
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET_KEY')
        
        if not api_key or not api_secret:
            return pd.DataFrame()
        
        base_url = "https://api.binance.com"
        endpoint = "/api/v3/myTrades"
        
        # Calcula período
        periodo_ms = int((time.time() - (dias * 24 * 60 * 60)) * 1000)
        timestamp_atual = int(time.time() * 1000)
        
        # Símbolos para buscar - abordagem mais conservadora
        if symbols_filtro:
            symbols_busca = symbols_filtro[:5]  # Limita a 5 símbolos
        else:
            # Apenas símbolos principais para evitar erros
            symbols_busca = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        all_trades = []
        simbolos_com_trades = 0
        
        for symbol in symbols_busca:
            try:
                current_timestamp = int(time.time() * 1000)
                params = {
                    'symbol': symbol,
                    'limit': 50,  # Limite menor
                    'timestamp': current_timestamp,
                    'recvWindow': 60000  # Janela maior
                }
                
                # Não usar startTime/endTime para evitar erros 400
                
                query_string = urlencode(params)
                signature = hmac.new(
                    api_secret.encode('utf-8'),
                    query_string.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                
                params['signature'] = signature
                
                headers = {
                    'X-MBX-APIKEY': api_key,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                response = requests.get(
                    base_url + endpoint,
                    params=params,
                    headers=headers,
                    timeout=8
                )
                
                if response.status_code == 200:
                    trades_data = response.json()
                    
                    if trades_data:  # Se há trades
                        simbolos_com_trades += 1
                        
                        for trade in trades_data:
                            trade_formatado = {
                                'timestamp': pd.to_datetime(int(trade['time']), unit='ms'),
                                'symbol': trade['symbol'],
                                'side': 'BUY' if trade['isBuyer'] else 'SELL',
                                'quantity': float(trade['qty']),
                                'price': float(trade['price']),
                                'commission': float(trade['commission']),
                                'commissionAsset': trade['commissionAsset'],
                                'value_usdt': float(trade['qty']) * float(trade['price']),
                                'orderId': trade['orderId'],
                                'isMaker': trade['isMaker']
                            }
                            all_trades.append(trade_formatado)
                            
            except Exception:
                continue  # Ignora erros individuais
        
        if all_trades:
            df = pd.DataFrame(all_trades)
            df = df.sort_values('timestamp', ascending=False)
            
            # Calcula estatísticas
            total_compras = len(df[df['side'] == 'BUY'])
            total_vendas = len(df[df['side'] == 'SELL'])
            volume_total = df['value_usdt'].sum()
            
            timestamp_fmt = datetime.now().strftime('%H:%M:%S')
            st.success(f"✅ [{timestamp_fmt}] {len(df)} trades de {simbolos_com_trades} símbolos | {dias}d | Vol: ${volume_total:,.0f}")
            
            return df
        else:
            st.info(f"📊 Nenhum trade encontrado nos últimos {dias} dias")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"❌ Erro histórico filtrado: {e}")
        return pd.DataFrame()

# --- FUNÇÃO DE BUSCA DE DECISÕES DA IA ---
# --- FUNÇÃO PARA POSIÇÕES ATIVAS COM TIMING ---
@st.cache_data(ttl=45)
def get_posicoes_ativas_com_timing():
    """Busca posições ativas com informações de timing de compra e provável venda"""
    posicoes = []
    try:
        # Busca do executor (arquivo em data/active_trades.json)
        path_active = os.path.join(diretorio_raiz, 'data', 'active_trades.json')
        if os.path.exists(path_active):
            with open(path_active, 'r', encoding='utf-8') as f:
                trades_ativos = json.load(f)
                
            for symbol, trade in trades_ativos.items():
                if isinstance(trade, dict):
                    # Calcula tempo de posição
                    entry_time = trade.get('entry_time', datetime.now().isoformat())
                    entry_dt = pd.to_datetime(entry_time)
                    agora = datetime.now()
                    tempo_posicao = (agora - entry_dt).total_seconds() / 3600
                    
                    # Busca previsão se disponível
                    previsao_path = os.path.join(diretorio_raiz, 'data', 'previsoes_historico.json')
                    data_venda_provavel = None
                    cenario_alvo = None
                    
                    if os.path.exists(previsao_path):
                        try:
                            with open(previsao_path, 'r', encoding='utf-8') as f:
                                previsoes = json.load(f)
                            
                            # Busca previsão para esta posição
                            for chave, dados in previsoes.items():
                                if symbol in chave and abs((pd.to_datetime(dados.get('timestamp', '')) - entry_dt).total_seconds()) < 7200:  # 2h tolerância
                                    previsao = dados.get('previsao_inicial', {})
                                    if 'cenarios' in previsao:
                                        # Estima data de venda baseada no cenário realista
                                        realista = previsao['cenarios'].get('realista', {})
                                        eta_horas = realista.get('eta_horas', 4)
                                        data_venda_provavel = entry_dt + pd.Timedelta(hours=eta_horas)
                                        cenario_alvo = f"Realista ({realista.get('lucro_pct', 0):.1f}%)"
                                        break
                        except:
                            pass
                    
                    # Se não tem previsão, estima baseado na categoria
                    if not data_venda_provavel:
                        # Estimativa por categoria (horas médias)
                        if any(meme in symbol.upper() for meme in ['PEPE', 'DOGE', 'SHIB', 'WIF', 'BONK']):
                            eta_horas = 6  # Memes: 6h
                        elif any(blue in symbol.upper() for blue in ['BTC', 'ETH', 'BNB', 'SOL']):
                            eta_horas = 12  # Blue chips: 12h
                        else:
                            eta_horas = 8  # Outros: 8h
                        
                        data_venda_provavel = entry_dt + pd.Timedelta(hours=eta_horas)
                        cenario_alvo = "Estimativa"
                    
                    posicao = {
                        'symbol': symbol,
                        'data_compra': entry_dt.strftime('%d/%m/%y %H:%M'),
                        'data_venda_provavel': data_venda_provavel.strftime('%d/%m/%y %H:%M') if data_venda_provavel else 'N/A',
                        'tempo_posicao': f"{tempo_posicao:.1f}h",
                        'cenario_alvo': cenario_alvo,
                        'preco_entrada': trade.get('entry_price', 0),
                        'quantidade': trade.get('qty', 0),
                        'valor_investido': trade.get('entry_price', 0) * trade.get('qty', 0)
                    }
                    posicoes.append(posicao)
                    
        return pd.DataFrame(posicoes)
    except Exception as e:
        st.error(f"Erro ao carregar posições ativas: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=45)  # Limpa o cache a cada 45 segundos
def get_ia_decisions():
    try:
        db_path = os.path.join(diretorio_raiz, 'memoria_bot.db')
        if not os.path.exists(db_path): return pd.DataFrame()
        # Use o modo 'uri' para permitir leitura enquanto o bot escreve
        conn = sqlite3.connect(f"file:{db_path}?                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                ZZde=ro", uri=True)
        query = "SELECT timestamp, symbol, confianca, decisao, motivo FROM logs_decisao ORDER BY id DESC LIMIT 15"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

# --- FUNÇÃO PARA LER SALDO DIVIDIDO (USDT, EARN, SPOTS) ---
# IMPLEMENTAÇÃO DIRETA VIA REST API BINANCE
def test_binance_connectivity():
    """Testa se a API da Binance está acessível"""
    try:
        import requests
        response = requests.get("https://api.binance.com/api/v3/ping", timeout=3)
        return response.status_code == 200
    except:
        return False

def get_saldo_dividido():
    """Busca saldo real da Binance via REST API de forma eficiente"""
    import requests
    import hmac
    import hashlib
    import time
    from urllib.parse import urlencode
    
    try:
        # 1. CARREGA CREDENCIAIS DA BINANCE
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET_KEY')
        
        if not api_key or not api_secret:
            st.warning("⚠️ Credenciais Binance não encontradas no .env")
            return get_saldo_fallback()
        
        # 2. PREPARA REQUISIÇÃO PARA GET /api/v3/account
        base_url = "https://api.binance.com"
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)
        
        # Parâmetros da requisição
        params = {
            'timestamp': timestamp,
            'recvWindow': 5000
        }
        
        # 3. CRIA ASSINATURA HMAC SHA256
        query_string = urlencode(params)
        signature = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        params['signature'] = signature
        
        # 4. EXECUTA REQUISIÇÃO
        headers = {
            'X-MBX-APIKEY': api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.get(
            base_url + endpoint,
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            st.error(f"❌ Erro API Binance: {response.status_code} - {response.text}")
            return get_saldo_fallback()
        
        # 5. PROCESSA DADOS DA CONTA
        account_data = response.json()
        
        usdt_spot = 0.0
        earn_staking = 0.0  # Para simplificar, vamos focar no Spot
        cripto_total_usdt = 0.0
        
        # Busca preços atuais dos assets que temos
        assets_para_converter = []
        
        for balance in account_data.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total_balance = free + locked
            
            if total_balance > 0.001:  # Ignora valores insignificantes
                if asset in ['USDT', 'BUSD', 'USDC', 'TUSD']:  # Stablecoins
                    usdt_spot += total_balance
                elif asset not in ['BNB']:  # Ignora BNB (taxa)
                    # ✅ CORREÇÃO: Só adiciona se realmente tem saldo
                    assets_para_converter.append({'asset': f'{asset}USDT', 'quantidade': total_balance})
        
        # 6. BUSCA PREÇOS ATUAIS PARA CONVERSÃO
        if assets_para_converter:
            try:
                # Requisição individual para cada preço (mais confiável)
                for asset_info in assets_para_converter:
                    symbol = asset_info['asset']
                    quantidade = asset_info['quantidade']
                    
                    try:
                        price_response = requests.get(
                            f"{base_url}/api/v3/ticker/price",
                            params={'symbol': symbol},
                            timeout=3
                        )
                        
                        if price_response.status_code == 200:
                            price_data = price_response.json()
                            price = float(price_data['price'])
                            valor_usdt = quantidade * price
                            cripto_total_usdt += valor_usdt
                            
                        else:
                            st.warning(f"⚠️ Preço não encontrado para {symbol}")
                            
                    except Exception as e:
                        st.warning(f"⚠️ Erro buscando preço {symbol}: {str(e)[:30]}")
                        continue
                
            except Exception as e:
                st.warning(f"⚠️ Erro geral buscando preços: {str(e)[:50]}...")
        
        # 7. CALCULA TOTAIS
        total_usdt = usdt_spot + earn_staking + cripto_total_usdt
        
        # 8. RETORNA RESULTADO
        timestamp = datetime.now().strftime('%H:%M:%S')
        st.success(f"✅ [{timestamp}] API REST Binance - TOTAL: ${total_usdt:,.2f}")
        
        return {
            "USDT": usdt_spot,
            "EARN": earn_staking,
            "CRIPTO": cripto_total_usdt,
            "TOTAL": total_usdt
        }
        
    except requests.RequestException as e:
        st.error(f"❌ Erro de conexão: {e}")
        return get_saldo_fallback()
    except Exception as e:
        st.error(f"❌ Erro inesperado: {e}")
        return get_saldo_fallback()

# --- FUNÇÃO FALLBACK PARA SALDO LOCAL ---
def get_saldo_fallback():
    """Função fallback que lê saldo de arquivos locais"""
    try:
        # 2. FALLBACK: Lê do arquivo local
        path = os.path.join(diretorio_raiz, 'data', 'wallet_composition.json')
        if not os.path.exists(path):
            st.warning("📂 Fallback: wallet_composition.json não encontrado")
            return {"USDT": 0.0, "EARN": 0.0, "CRIPTO": 0.0, "TOTAL": 0.0}
        
        with open(path, 'r', encoding='utf-8') as f:
            wallet = json.load(f)
        
        # Extrai do schema consolidado
        resumo = wallet.get('resumo', {})
        resultado = {
            "USDT": resumo.get('usdt_spot', 0.0),
            "EARN": resumo.get('earn_staking', 0.0),
            "CRIPTO": resumo.get('criptos_altcoins', 0.0),
            "TOTAL": resumo.get('total_usdt', 0.0)
        }
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        st.info(f"📂 [{timestamp}] Dados locais: ${resultado['TOTAL']:,.2f}")
        return resultado
    except Exception as e:
        st.error(f"❌ Erro no fallback: {e}")
        return {"USDT": 0.0, "EARN": 0.0, "CRIPTO": 0.0, "TOTAL": 0.0}

# --- FUNÇÃO PARA LER CARTEIRA DE CRIPTOS ---
@st.cache_data(ttl=10)
def get_carteira_criptos():
    try:
        # Lê do arquivo MASTER unificado
        path = os.path.join(diretorio_raiz, 'data', 'wallet_composition.json')
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            wallet = json.load(f)
        # Retorna holdings convertido para formato compatível
        holdings = wallet.get('holdings', {})
        return {k: v.get('quantidade', 0) for k, v in holdings.items()}
    except:
        return {}

# --- FUNÇÃO PARA LER PREVISÕES ATIVAS ---
@st.cache_data(ttl=10)
def get_previsoes_ativas():
    try:
        path = os.path.join(diretorio_raiz, 'previsoes_historico.json')
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            historico = json.load(f)
        # Filtra apenas posições abertas
        abertas = {k: v for k, v in historico.items() if v.get('status') == 'ABERTA'}
        return abertas
    except:
        return {}

# --- FUNÇÕES PARA ANÁLISE AVANÇADA ---
@st.cache_data(ttl=10)
def get_analise_previsoes_vendas():
    """Retorna análise detalhada das previsões e estratégias de venda."""
    try:
        previsoes = get_previsoes_ativas()
        if not previsoes:
            return {}
            
        analises = {}
        
        for symbol, dados in previsoes.items():
            if dados.get('status') != 'ABERTA':
                continue
                
            try:
                # Simula análise de venda inteligente
                situacao = venda_inteligente.analisar_situacao_venda(
                    symbol=symbol,
                    preco_atual=float(dados.get('preco_entrada', 0)),
                    preco_entrada=float(dados.get('preco_entrada', 0)),
                    tempo_posicao_horas=24,  # Simula 24h
                    categoria='MEME'  # Default para demo
                )
                
                analises[symbol] = {
                    'previsao': dados,
                    'analise_venda': situacao,
                    'recomendacao': situacao.get('acao_recomendada', 'AGUARDAR'),
                    'percentual_venda': situacao.get('percentual_para_vender', 0),
                    'motivo': situacao.get('motivo', '')
                }
            except Exception as e:
                # Se falhar análise individual, usa valores padrão
                analises[symbol] = {
                    'previsao': dados,
                    'analise_venda': {},
                    'recomendacao': 'AGUARDAR',
                    'percentual_venda': 0,
                    'motivo': f'Análise indisponível: {str(e)[:50]}...'
                }
        
        return analises
    except Exception as e:
        return {}

@st.cache_data(ttl=45)
def get_stop_loss_analysis():
    """Análise do sistema de stop loss híbrido."""
    try:
        previsoes = get_previsoes_ativas()
        if not previsoes:
            return {}
            
        analises = {}
        
        for symbol, dados in previsoes.items():
            try:
                preco_entrada = float(dados.get('preco_entrada', 0))
                quantidade = float(dados.get('quantidade', 0))
                
                # Calcula stop loss híbrido
                stop_loss = stop_loss_engine.calcular_stop_loss_hibrido(
                    symbol=symbol,
                    preco_entrada=preco_entrada,
                    quantidade=quantidade,
                    categoria='MEME',  # Default
                    tempo_posicao_horas=12
                )
                
                analises[symbol] = {
                    'stop_loss_pct': stop_loss.get('stop_loss_pct', 0),
                    'stop_loss_usd': stop_loss.get('stop_loss_usd', 0),
                    'limite_tempo': stop_loss.get('limite_tempo_horas', 0),
                    'criterio_ativo': stop_loss.get('criterio_dominante', 'N/A'),
                    'nivel_risco': stop_loss.get('nivel_risco', 'MEDIO')
                }
            except Exception as e:
                # Valores padrão se análise falhar
                analises[symbol] = {
                    'stop_loss_pct': 5.0,
                    'stop_loss_usd': 10.0,
                    'limite_tempo': 24,
                    'criterio_ativo': 'Percentual',
                    'nivel_risco': 'MEDIO'
                }
        
        return analises
    except Exception as e:
        return {}

@st.cache_data(ttl=45)
def get_bot_stats():
    """Retorna estatísticas dos bots por categoria."""
    try:
        # Simula estatísticas baseadas nos dados disponíveis
        trades = get_ultimas_trades()
        if trades.empty:
            return {}
        
        stats = {}
        if 'estrategia' in trades.columns:
            stats = trades['estrategia'].value_counts().to_dict()
        elif 'type' in trades.columns:
            stats = trades['type'].value_counts().to_dict()
        else:
            # Fallback: estatísticas simuladas
            stats = {
                'MEME': 5,
                'BLUE_CHIP': 3,
                'DEFI': 2,
                'LAYER2': 1
            }
        
        return stats
    except Exception as e:
        return {}

@st.cache_data(ttl=45, show_spinner="🎯 Carregando previsões...")
def get_previsoes_acuracia():
    """Carrega dados de previsões com tracking de acurácia."""
    try:
        path = os.path.join(diretorio_raiz, 'data', 'previsoes_acuracia.json')
        if not os.path.exists(path):
            return {'cards_previsoes': [], 'estatisticas_consolidadas': {}}
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        return {'cards_previsoes': [], 'estatisticas_consolidadas': {}}

# --- LÓGICA DE DADOS FINANCEIROS DINÂMICOS ---
try:
    with open(os.path.join(diretorio_raiz, 'config', 'settings.json'), 'r') as f:
        config_file = json.load(f)
    meta_diaria = config_file.get('config_geral', {}).get('meta_diaria_total_usdt', 30.0)
    banca_referencia = config_file.get('banca_referencia_usdt', 2355.05)
except:
    meta_diaria = 30.0
    banca_referencia = 2355.05

# --- CARREGAMENTO DE SALDOS DINÂMICOS ---
# Força atualização automática baseada no session state
if "force_saldo_refresh" not in st.session_state:
    st.session_state.force_saldo_refresh = False

# Se o usuário forçou atualização, limpa cache
if st.session_state.force_saldo_refresh:
    st.cache_data.clear()
    st.session_state.force_saldo_refresh = False

# FORÇA ATUALIZAÇÃO CONSTANTE DOS SALDOS
if "refresh_count" not in st.session_state:
    st.session_state.refresh_count = 0
    
st.session_state.refresh_count += 1

# SEMPRE limpa cache e força nova busca de saldo para dados em tempo real
st.cache_data.clear()
saldo_dividido_atual = get_saldo_dividido()

# SALDO INICIAL DO DIA - Busca ou atualiza dinamicamente
try:
    financial_path = os.path.join(diretorio_raiz, 'data', 'financial_master.json')
    if os.path.exists(financial_path):
        with open(financial_path, 'r', encoding='utf-8') as f:
            fin = json.load(f)
        
        # Verifica se o saldo inicial é de hoje
        hoje = datetime.now().strftime('%Y-%m-%d')
        data_saldo_inicial = fin.get('saldos', {}).get('data_referencia', '')
        
        if data_saldo_inicial == hoje:
            # Usa saldo inicial do dia registrado
            saldo_inicial_dia = fin.get('saldos', {}).get('saldo_inicial_dia', banca_referencia)
        else:
            # Se é de outro dia, atualiza com saldo atual como novo inicial
            saldo_inicial_dia = saldo_dividido_atual.get('TOTAL', banca_referencia)
            st.info(f"🔄 Saldo inicial atualizado para hoje: ${saldo_inicial_dia:,.2f}")
        
        # Não usa o lucro_hoje do arquivo, será calculado dinamicamente
    else:
        # Se não existe arquivo, usa saldo atual como inicial
        saldo_inicial_dia = saldo_dividido_atual.get('TOTAL', banca_referencia)
        st.warning("📂 financial_master.json não encontrado - usando saldo atual como inicial")
        
except Exception as e:
    # Se corrompido, usa saldo atual como inicial
    saldo_inicial_dia = saldo_dividido_atual.get('TOTAL', banca_referencia)
    st.warning(f"⚠️ Erro no arquivo financeiro. Usando saldo atual como inicial")

# Extrai componentes do saldo atual
saldo_spot_atual = saldo_dividido_atual.get('USDT', 0.0)
saldo_earn_atual = saldo_dividido_atual.get('EARN', 0.0)
saldo_cripto_atual = saldo_dividido_atual.get('CRIPTO', 0.0)
# Saldo total DINÂMICO = soma de todos os componentes
saldo_total = saldo_spot_atual + saldo_earn_atual + saldo_cripto_atual

# LUCRO/PREJUÍZO REAL = diferença entre saldo atual e inicial
lucro_hoje = saldo_total - saldo_inicial_dia

stats = gestor.status_atual()

# --- BARRA LATERAL ---
st.sidebar.title("🎯 R7_V3 Sniper V2")

# BOTÃO DE ATUALIZAÇÃO FORÇADA
if st.sidebar.button("🔄 Atualizar Dashboard", help="Força atualização completa dos dados"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# 🔒 SALDO INICIAL (REFERÊNCIA FIXA)
st.sidebar.markdown("### 🔒 Base do Dia")
st.sidebar.markdown(f"<p style='font-size: 11px; color: #888;'>📌 Referência 00:00h</p>", unsafe_allow_html=True)
st.sidebar.metric("Inicial", f"${saldo_inicial_dia:,.2f}")

# 💰 SALDO ATUAL (DINÂMICO)
st.sidebar.markdown("### 💰 Atual")
delta_sidebar = saldo_total - saldo_inicial_dia
delta_color = "normal" if delta_sidebar >= 0 else "inverse"
st.sidebar.metric("Total", f"${saldo_total:,.2f}", delta=f"${delta_sidebar:+.2f}")
st.sidebar.caption(f"🔄 Sincronizado: {datetime.now().strftime('%H:%M:%S')} | #{st.session_state.refresh_count}")

with st.sidebar.expander("📊 Componentes"):
    st.write(f"💵 **Spot:** ${saldo_spot_atual:,.2f}")
    st.write(f"🔄 **Earn:** ${saldo_earn_atual:,.2f}")
    st.write(f"🪙 **Criptos:** ${saldo_cripto_atual:,.2f}")

st.sidebar.markdown("---")
st.sidebar.markdown(f"<p style='font-size: 10px; color: #666;'>🔄 Dashboard: {datetime.now().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)

# --- 🏆 ÁREA DE PROGRESSO DIÁRIO (SUPORTA NEGATIVO) ---
st.markdown(f"### 🎯 Meta Diária: ${meta_diaria:.2f} | Atual: ${lucro_hoje:+.2f}")

# Calcula progresso permitindo valores negativos
if meta_diaria > 0:
    progresso_pct = lucro_hoje / meta_diaria
    # Limita entre -1 (100% negativo) e 2 (200% positivo para metas superadas)
    progresso_visual = max(-1.0, min(2.0, progresso_pct))
    
    # Converte para 0-1 para a barra visual
    if progresso_visual < 0:
        barra_valor = (progresso_visual + 1) / 2  # -1 vira 0, 0 vira 0.5
    else:
        barra_valor = min(1.0, (progresso_visual + 1) / 2)  # 0 vira 0.5, 1 vira 1.0
    
    col_bar, col_text = st.columns([3, 1])
    with col_bar:
        st.progress(barra_valor)
    with col_text:
        pct_display = progresso_pct * 100
        if lucro_hoje >= meta_diaria:
            cor = "#FFD700"  # Dourado para meta atingida
            emoji = "🏆"
        elif lucro_hoje >= 0:
            cor = "#32CD32"  # Verde
            emoji = "📈"
        else:
            cor = "#FF4500"  # Vermelho
            emoji = "📉"
        st.markdown(f"<p style='color: {cor}; font-size: 16px; font-weight: bold; text-align: center;'>{emoji} {pct_display:+.1f}%</p>", unsafe_allow_html=True)
else:
    st.warning("⚠️ Meta não definida")

# Alertas de status com mais informações
if lucro_hoje >= meta_diaria:
    faltam_para_dobrar = meta_diaria * 2 - lucro_hoje
    if faltam_para_dobrar <= 0:
        st.success(f"🎉 META DUPLA! Lucro: ${lucro_hoje:+.2f} | +{(lucro_hoje/meta_diaria*100):+.0f}%")
    else:
        st.success(f"✅ META ATINGIDA! Lucro: ${lucro_hoje:+.2f} | Faltam ${faltam_para_dobrar:.2f} para dobrar")
elif lucro_hoje >= 0:
    faltam = meta_diaria - lucro_hoje
    st.info(f"📈 NO LUCRO: ${lucro_hoje:+.2f} | Faltam ${faltam:.2f} para a meta ({(lucro_hoje/meta_diaria*100):.1f}%)")
else:
    recuperar_total = meta_diaria - lucro_hoje
    st.error(f"📉 PREJUÍZO: ${lucro_hoje:+.2f} | Precisa recuperar ${recuperar_total:.2f} para atingir a meta")

# --- ABAS ---
tab_resumo, tab_posicoes, tab_ia, tab_analises, tab_diario = st.tabs(["📊 Resumo Financeiro", "🎯 Posições Ativas", "🤖 Decisões IA", "🔬 Análises Avançadas", "📅 Histórico"])

with tab_resumo:
    # 🔄 CONTROLE DE ATUALIZAÇÃO
    col_titulo, col_refresh = st.columns([3, 1])
    with col_titulo:
        st.subheader("📊 Resumo Financeiro")
    with col_refresh:
        if st.button("🔄 Atualizar Saldos", help="Força atualização dos saldos em tempo real"):
            # Limpa TODOS os caches
            st.cache_data.clear()
            # Força nova busca dos saldos
            saldo_dividido_atual = get_saldo_dividido()
            # Recalcula totais
            saldo_spot_atual = saldo_dividido_atual.get('USDT', 0.0)
            saldo_earn_atual = saldo_dividido_atual.get('EARN', 0.0)
            saldo_cripto_atual = saldo_dividido_atual.get('CRIPTO', 0.0)
            saldo_total = saldo_spot_atual + saldo_earn_atual + saldo_cripto_atual
            lucro_hoje = saldo_total - saldo_inicial_dia
            # Mostra resultado
            timestamp = datetime.now().strftime('%H:%M:%S')
            st.success(f"✅ [{timestamp}] Saldos atualizados! Total: ${saldo_total:,.2f} | Lucro: ${lucro_hoje:+.2f}")
    # Calcula período dos dados
    try:
        df_trades = get_ultimas_trades()
        # Se get_ultimas_trades() falhar, usa dados locais como fallback
        if df_trades.empty:
            df_trades = get_trades_fallback()
    except Exception as e:
        st.warning("⚠️ Usando dados locais (API temporariamente indisponível)")
        df_trades = get_trades_fallback()
    periodo_info = ""
    data_inicio_fmt = ""
    data_fim_fmt = ""
    
    if not df_trades.empty and 'timestamp' in df_trades.columns:
        try:
            data_inicio = df_trades['timestamp'].min()
            data_fim = df_trades['timestamp'].max()
            
            if pd.notna(data_inicio) and pd.notna(data_fim):
                data_inicio_fmt = data_inicio.strftime('%d/%m/%Y')
                data_fim_fmt = data_fim.strftime('%d/%m/%Y')
                
                if data_inicio_fmt == data_fim_fmt:
                    periodo_info = f"Dia {data_inicio_fmt}"
                else:
                    periodo_info = f"{data_inicio_fmt} até {data_fim_fmt}"
            else:
                periodo_info = "Período indeterminado"
        except:
            periodo_info = "Calculando..."
    else:
        periodo_info = "Sem dados"
    
    # 📊 MÉTRICAS PRINCIPAIS CONSOLIDADAS
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_saldo = saldo_total - saldo_inicial_dia
        delta_color = "normal" if delta_saldo >= 0 else "inverse"
        st.metric("💰 Saldo Total", f"${saldo_total:,.2f}", delta=f"${delta_saldo:+.2f}", delta_color=delta_color)
        st.caption(f"📊 Base: ${saldo_inicial_dia:,.2f} | 🔄 {datetime.now().strftime('%H:%M:%S')} | Refresh #{st.session_state.refresh_count}")
    
    with col2:
        emoji_lucro = "📈" if lucro_hoje >= 0 else "📉"
        delta_color = "normal" if lucro_hoje >= 0 else "inverse"
        st.metric(f"{emoji_lucro} Performance", f"${lucro_hoje:+.2f}", delta=f"{(lucro_hoje/saldo_inicial_dia*100):+.2f}%", delta_color=delta_color)
        if periodo_info != "Sem dados":
            st.caption(f"📅 {periodo_info}")
    
    with col3:
        win_rate = stats.get('win_rate_mes', 0.0)
        trades_mes = stats.get('trades_mes', 0)
        st.metric("🎯 Taxa Sucesso", f"{win_rate:.1%}")
        st.caption(f"📊 {trades_mes} trades no mês")
    
    with col4:
        decisoes_ia = get_ia_decisions()
        st.metric("🤖 Sinais IA", len(decisoes_ia))
        st.caption("🔄 Atualizado há 45s")

    st.markdown("---")
    
    # 🔄 PERFORMANCE POR BOT (Estratégias)
    st.subheader("🤖 Performance por BOT (Estratégias)")
    try:
        with open(os.path.join(diretorio_raiz, 'data', 'monthly_stats.json'), 'r') as f:
            monthly = json.load(f)
        
        estrategias_info = monthly.get('historico_estrategias', {})
        
        if estrategias_info:
            # Mapeamento de nomes e emojis
            bot_config = {
                'scalping_v6': {'nome': '🔷 Blue Chips', 'cor': '#4169E1'},
                'meme_sniper': {'nome': '🎭 Meme Sniper', 'cor': '#FF1493'},
                'momentum_boost': {'nome': '🚀 Momentum', 'cor': '#32CD32'},
                'layer2_defi': {'nome': '🌐 Layer2 DeFi', 'cor': '#FF8C00'},
                'swing_rwa': {'nome': '📊 Swing RWA', 'cor': '#9370DB'}
            }
            
            # Cria 5 colunas para os 5 bots
            cols = st.columns(5)
            
            for idx, (estrategia_key, config) in enumerate(bot_config.items()):
                with cols[idx]:
                    dados = estrategias_info.get(estrategia_key, {'trades': 0, 'pnl': 0.0})
                    trades = dados.get('trades', 0)
                    pnl = dados.get('pnl', 0.0)
                    
                    # Card com cor
                    st.markdown(f"""
                    <div style="background: {config['cor']}20; padding: 15px; border-radius: 10px; border-left: 4px solid {config['cor']}">
                        <h4 style="margin: 0; color: {config['cor']}">{config['nome']}</h4>
                        <p style="margin: 5px 0; font-size: 24px; font-weight: bold;">${pnl:.2f}</p>
                        <p style="margin: 0; font-size: 14px; color: #888;">{trades} trades</p>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("📊 Aguardando dados de estratégias...")
    except:
        st.info("📊 Carregando dados dos bots...")

with tab_posicoes:
    st.header("🎯 Posições Ativas em Monitoramento")
    
    # Carrega previsões
    previsoes = get_previsoes_ativas()
    num_posicoes = len(previsoes)
    
    if num_posicoes > 0:
        # Métricas gerais
        col1, col2, col3 = st.columns(3)
        
        total_investido = 0
        total_atual = 0
        
        for chave, posicao in previsoes.items():
            entry_price = posicao.get('entry_price', 0)
            # Pega última atualização se existir
            atualizacoes = posicao.get('atualizacoes', [])
            if atualizacoes:
                preco_atual = atualizacoes[-1].get('preco_atual', entry_price)
            else:
                preco_atual = entry_price
            
            # Estimativa de quantidade (assumindo $50 por posição)
            qtd_estimada = 50 / entry_price
            total_investido += 50
            total_atual += qtd_estimada * preco_atual
        
        lucro_total = total_atual - total_investido
        
        col1.metric("📊 Posições Ativas", num_posicoes)
        col2.metric("💰 Investido", f"${total_investido:.2f}")
        col3.metric("📈 Lucro Atual", f"${lucro_total:.2f}", delta=f"{(lucro_total/total_investido*100):+.2f}%")
        
        st.markdown("---")
        
        # Exibe cada posição
        for chave, posicao in previsoes.items():
            symbol = posicao.get('symbol', 'DESCONHECIDO')
            categoria = posicao.get('categoria', 'UNKNOWN')
            entry_price = posicao.get('entry_price', 0)
            entry_time = posicao.get('entry_time', '')
            
            # Pega previsão inicial
            previsao_inicial = posicao.get('previsao_inicial', {})
            cenarios = previsao_inicial.get('cenarios', {})
            
            # Pega última atualização
            atualizacoes = posicao.get('atualizacoes', [])
            if atualizacoes:
                ultima_att = atualizacoes[-1]
                preco_atual = ultima_att.get('preco_atual', entry_price)
                lucro_pct = ultima_att.get('lucro_atual_pct', 0)
                status = ultima_att.get('status', 'AGUARDANDO')
                tempo_decorrido = ultima_att.get('tempo_decorrido_horas', 0)
            else:
                preco_atual = entry_price
                lucro_pct = 0
                status = 'AGUARDANDO'
                tempo_decorrido = 0
            
            # Emoji por categoria
            cat_emoji = {
                'LARGE_CAP': '🔷',
                'MEME': '🎭',
                'DEFI': '🌐',
                'LAYER2': '🔗',
                'GAMING': '🎮',
                'AI': '🤖'
            }
            emoji = cat_emoji.get(categoria, '💎')
            
            # Status emoji
            status_emoji = {
                'ACIMA_PREVISTO': '🚀',
                'DENTRO_PREVISTO': '✅',
                'ABAIXO_PREVISTO': '⚠️',
                'AGUARDANDO': '⏳'
            }
            status_icon = status_emoji.get(status, '📊')
            
            # Calcula estimativa de venda baseada nos cenários
            data_compra = pd.to_datetime(entry_time) if entry_time else pd.to_datetime('now')
            data_compra_str = data_compra.strftime('%d/%m/%y %H:%M')
            
            # Estima venda baseada no cenário realista
            if cenarios.get('realista'):
                eta_horas = cenarios['realista'].get('eta_horas', 4)
                data_venda_est = data_compra + pd.Timedelta(hours=eta_horas)
                cenario_meta = f"Realista {cenarios['realista'].get('lucro_pct', 0):.1f}%"
            else:
                # Fallback por categoria
                eta_map = {'MEME': 6, 'LARGE_CAP': 12, 'DEFI': 8, 'LAYER2': 8}
                eta_horas = eta_map.get(categoria, 8)
                data_venda_est = data_compra + pd.Timedelta(hours=eta_horas)
                cenario_meta = f"Estimado ({categoria})"
            
            data_venda_str = data_venda_est.strftime('%d/%m/%y %H:%M')
            
            # Card da posição com timing
            with st.expander(f"{emoji} {symbol} | {lucro_pct:+.2f}% | {status_icon} {status} | 📅 {data_compra_str} → {data_venda_str}", expanded=False):
                # Timing da posição
                col_time1, col_time2 = st.columns(2)
                with col_time1:
                    st.markdown(f"**📅 Compra:** {data_compra_str}")
                    st.markdown(f"**⏰ Tempo:** {tempo_decorrido:.1f}h")
                with col_time2:
                    st.markdown(f"**🎯 Venda Estimada:** {data_venda_str}")
                    st.markdown(f"**📊 Meta:** {cenario_meta}")
                
                st.markdown("---")
                # Informações básicas
                col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                col_info1.metric("Entrada", f"${entry_price:.6f}")
                col_info2.metric("Atual", f"${preco_atual:.6f}")
                col_info3.metric("Lucro", f"{lucro_pct:+.2f}%")
                col_info4.metric("Tempo", f"{tempo_decorrido:.1f}h")
                
                st.markdown("---")
                
                # Previsões
                st.markdown("**🎯 Previsões Iniciais:**")
                col_prev1, col_prev2, col_prev3 = st.columns(3)
                
                conservador = cenarios.get('conservador', {})
                realista = cenarios.get('realista', {})
                otimista = cenarios.get('otimista', {})
                
                with col_prev1:
                    st.markdown("**🔵 Conservador**")
                    st.metric(
                        label="Lucro Previsto", 
                        value=f"{conservador.get('lucro_pct', 0):.1f}%",
                        delta=f"{conservador.get('probabilidade', 0)}% probabilidade"
                    )
                    st.caption(f"ETA: {conservador.get('eta_horas', 0):.1f}h")
                
                with col_prev2:
                    st.markdown("**🟡 Realista**")
                    st.metric(
                        label="Lucro Previsto",
                        value=f"{realista.get('lucro_pct', 0):.1f}%",
                        delta=f"{realista.get('probabilidade', 0)}% probabilidade"
                    )
                    st.caption(f"ETA: {realista.get('eta_horas', 0):.1f}h")
                
                with col_prev3:
                    st.markdown("**🟢 Otimista**")
                    st.metric(
                        label="Lucro Previsto",
                        value=f"{otimista.get('lucro_pct', 0):.1f}%",
                        delta=f"{otimista.get('probabilidade', 0)}% probabilidade"
                    )
                    st.caption(f"ETA: {otimista.get('eta_horas', 0):.1f}h")
                
                # Análises Avançadas
                st.markdown("---")
                st.markdown("**🔬 Análise Sistema Avançado:**")
                
                try:
                    # Análise de venda inteligente para esta posição
                    analise_venda = venda_inteligente.analisar_situacao_venda(
                        symbol=symbol,
                        preco_atual=preco_atual,
                        preco_entrada=entry_price,
                        tempo_posicao_horas=tempo_decorrido,
                        categoria=categoria
                    )
                    
                    # Stop loss híbrido
                    stop_loss_info = stop_loss_engine.calcular_stop_loss_hibrido(
                        symbol=symbol,
                        preco_entrada=entry_price,
                        quantidade=posicao.get('quantidade', 0),
                        categoria=categoria,
                        tempo_posicao_horas=tempo_decorrido
                    )
                    
                    col_adv1, col_adv2 = st.columns(2)
                    
                    with col_adv1:
                        st.markdown("**🧠 Venda Inteligente:**")
                        acao = analise_venda.get('acao_recomendada', 'AGUARDAR')
                        st.write(f"• Recomendação: **{acao}**")
                        
                        if analise_venda.get('percentual_para_vender', 0) > 0:
                            st.write(f"• Vender: **{analise_venda.get('percentual_para_vender', 0):.0f}%**")
                        
                        motivo = analise_venda.get('motivo', '')
                        if motivo:
                            st.caption(f"💡 {motivo}")
                    
                    with col_adv2:
                        st.markdown("**🛡️ Stop Loss Híbrido:**")
                        st.write(f"• Percentual: **{stop_loss_info.get('stop_loss_pct', 0):.2f}%**")
                        st.write(f"• USD: **${stop_loss_info.get('stop_loss_usd', 0):.2f}**")
                        
                        criterio = stop_loss_info.get('criterio_dominante', 'N/A')
                        st.caption(f"🎯 Critério: {criterio}")
                        
                except Exception as e:
                    st.info("🔧 Análise avançada temporariamente indisponível")
                
                # Timeline de atualizações
                if atualizacoes and len(atualizacoes) > 1:
                    st.markdown("---")
                    st.markdown("**📊 Histórico de Atualizações:**")
                    
                    df_att = pd.DataFrame(atualizacoes[-10:])  # Últimas 10
                    if not df_att.empty:
                        df_att['timestamp'] = pd.to_datetime(df_att['timestamp'])
                        df_att = df_att.sort_values('timestamp', ascending=False)
                        
                        # Formata para exibição
                        df_display = df_att[['timestamp', 'lucro_atual_pct', 'status', 'tempo_decorrido_horas']].copy()
                        df_display.columns = ['Data/Hora', 'Lucro %', 'Status', 'Tempo (h)']
                        df_display['Data/Hora'] = df_display['Data/Hora'].dt.strftime('%d/%m %H:%M')
                        
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    else:
        st.info("📭 Nenhuma posição ativa no momento")
        st.markdown("O sistema adiciona automaticamente ao monitoramento quando:")
        st.markdown("- ✅ Executar compra via Sniper")
        st.markdown("- ✅ Detectar moeda na carteira (scan a cada 60s)")
        st.markdown("- ✅ Compra externa via Binance")

    st.markdown("---")
    st.info("📊 Estatísticas dos bots disponíveis na aba 'Resumo Financeiro'")

with tab_ia:
    st.subheader("🧠 Log de Seletividade da IA")
    df_decisoes = get_ia_decisions()
    if not df_decisoes.empty:
        df_display = df_decisoes.rename(columns={
            'timestamp': 'Hora', 'symbol': 'Moeda', 'confianca': 'Confiança', 'decisao': 'Resultado', 'motivo': 'Motivo'
        })
        df_display['Confiança'] = df_display['Confiança'].apply(lambda x: f"{x:.2%}")

        def style_rows(row):
            if row['Resultado'] == 'COMPRAR': return ['background-color: #004d00']*len(row)
            if row['Resultado'] == 'VETADO': return ['color: #ff4b4b']*len(row)
            return ['']*len(row)

        st.dataframe(df_display.style.apply(style_rows, axis=1), use_container_width=True, height=450)
    else:
        st.info("Aguardando sinais... A IA está analisando o mercado.")

with tab_analises:
    st.subheader("🔬 Sistema de Análises Avançadas")
    
    # Cards de Acurácia de Previsões
    st.markdown("### 🎯 Cards de Previsões & Acurácia")
    
    dados_acuracia = get_previsoes_acuracia()
    cards_previsoes = dados_acuracia.get('cards_previsoes', [])
    stats_consolidadas = dados_acuracia.get('estatisticas_consolidadas', {})
    
    if cards_previsoes:
        # Cards das últimas 6 previsões
        st.markdown("**📊 Últimas 6 Previsões:**")
        
        for i in range(0, len(cards_previsoes[:6]), 2):
            cols = st.columns(2)
            
            for j, col in enumerate(cols):
                if i + j < len(cards_previsoes):
                    card = cards_previsoes[i + j]
                    
                    with col:
                        # Status do card
                        status = card['resultado']['status']
                        status_icon = "🟢" if status == "VENDIDO" else "🟡" if status == "ATIVA" else "🔴"
                        
                        # Determina acerto
                        acuracia = card['acuracia']
                        if acuracia['conservador_atingido']:
                            acerto_icon = "✅"
                            acerto_texto = "Conservador OK"
                        elif acuracia['realista_atingido']:
                            acerto_icon = "✅"
                            acerto_texto = "Realista OK"
                        elif acuracia['otimista_atingido']:
                            acerto_icon = "✅" 
                            acerto_texto = "Otimista OK"
                        else:
                            acerto_icon = "⏳" if status == "ATIVA" else "❌"
                            acerto_texto = "Aguardando" if status == "ATIVA" else "Não atingiu metas"
                        
                        # Status de execução da trade
                        compra_realizada = "✅ COMPRA" if status != "PENDENTE" else "⏳ AGUARDANDO"
                        venda_realizada = "✅ VENDA" if status == "FINALIZADA" else "⏳ EM ABERTO"
                        
                        # Horários formatados
                        if 'timestamp_entrada' in card['entrada']:
                            try:
                                dt_entrada = pd.to_datetime(card['entrada']['timestamp_entrada'])
                                momento_compra = dt_entrada.strftime('%H:%M/%d/%m/%y')
                            except:
                                momento_compra = "N/A"
                        else:
                            momento_compra = "N/A"
                        
                        if status == "FINALIZADA" and 'timestamp_saida' in card.get('resultado', {}):
                            try:
                                dt_saida = pd.to_datetime(card['resultado']['timestamp_saida'])
                                momento_venda = dt_saida.strftime('%H:%M/%d/%m/%y')
                            except:
                                momento_venda = "N/A"
                        else:
                            # Estima momento da venda baseado na estratégia
                            if 'timestamp_entrada' in card['entrada']:
                                try:
                                    dt_entrada = pd.to_datetime(card['entrada']['timestamp_entrada'])
                                    symbol = card['symbol']
                                    
                                    # Duração estimada por categoria
                                    if any(meme in symbol.upper() for meme in ['PEPE', 'DOGE', 'SHIB']):
                                        duracao_h = 4
                                        categoria = "MEME"
                                    elif any(blue in symbol.upper() for blue in ['BTC', 'ETH', 'BNB', 'SOL']):
                                        duracao_h = 12
                                        categoria = "BLUE"
                                    else:
                                        duracao_h = 8
                                        categoria = "DEFI"
                                    
                                    dt_venda_est = dt_entrada + pd.Timedelta(hours=duracao_h)
                                    momento_venda = f"{dt_venda_est.strftime('%H:%M/%d/%m/%y')} (est.{categoria})"
                                except:
                                    momento_venda = "Estimando..."
                            else:
                                momento_venda = "Estimando..."
                        
                        with st.container():
                            st.markdown(f"""
                            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin-bottom: 10px; background: linear-gradient(145deg, #f8f9fa, #e9ecef);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <span style="font-weight: bold; font-size: 14px;">{status_icon} {card['symbol']}</span>
                                    <span style="font-size: 12px; color: #666;">{card['entrada']['estrategia']}</span>
                                </div>
                                <div style="margin-bottom: 8px;">
                                    <span style="font-size: 13px; color: #333;">💰 Lucro: <strong>{card['resultado']['lucro_pct']:+.1f}%</strong></span><br>
                                    <span style="font-size: 12px; color: #666;">⏱️ {card['resultado']['tempo_decorrido_h']:.1f}h</span>
                                </div>
                                <div style="margin-bottom: 8px;">
                                    <span style="font-size: 12px; color: #444;">🔄 Status Execução:</span><br>
                                    <span style="font-size: 11px;">{compra_realizada} | {venda_realizada}</span>
                                </div>
                                <div style="margin-bottom: 8px;">
                                    <span style="font-size: 12px; color: #444;">⏰ Timing:</span><br>
                                    <span style="font-size: 11px;">📥 Compra: {momento_compra}</span><br>
                                    <span style="font-size: 11px;">📤 Venda: {momento_venda}</span>
                                </div>
                                <div style="margin-bottom: 8px;">
                                    <span style="font-size: 12px; color: #444;">🎯 Previsão:</span><br>
                                    <span style="font-size: 11px;">📈 C: {card['previsao']['conservador']['meta']:.1f}% • R: {card['previsao']['realista']['meta']:.1f}% • O: {card['previsao']['otimista']['meta']:.1f}%</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-size: 12px;">{acerto_icon} {acerto_texto}</span>
                                    <span style="font-size: 11px; color: #888;">Score: {acuracia['score_previsao']:.1f}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
        
        # Card Consolidado - GANHOS E PERDAS REALISTAS
        st.markdown("---")
        st.markdown("**📊 REALIDADE CONSOLIDADA - GANHOS vs PERDAS**")
        
        # Calcula estatísticas REAIS de todos os cards
        total_cards = len(cards_previsoes)
        ganhos_count = 0
        perdas_count = 0
        valor_total_ganho = 0.0
        valor_total_perdido = 0.0
        trades_finalizadas = 0
        trades_em_aberto = 0
        
        for card in cards_previsoes:
            lucro_pct = card['resultado']['lucro_pct']
            status = card['resultado']['status']  # Status está dentro de resultado
            
            if status == "FINALIZADA":
                trades_finalizadas += 1
                if lucro_pct > 0:
                    ganhos_count += 1
                    valor_total_ganho += lucro_pct
                else:
                    perdas_count += 1
                    valor_total_perdido += abs(lucro_pct)
            else:
                trades_em_aberto += 1
                # Para trades em aberto, considera tendência atual
                if lucro_pct > 0:
                    valor_total_ganho += lucro_pct  # Ganho não realizado
                else:
                    valor_total_perdido += abs(lucro_pct)  # Perda não realizada
        
        # Resultado final
        resultado_final = valor_total_ganho - valor_total_perdido
        taxa_sucesso_real = (ganhos_count / trades_finalizadas * 100) if trades_finalizadas > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div style="border: 2px solid #28a745; border-radius: 12px; padding: 16px; background: linear-gradient(145deg, #d4edda, #c3e6cb);">
                <h4 style="margin: 0 0 12px 0; color: #155724;">💚 GANHOS</h4>
                <div style="margin-bottom: 8px;">
                    <span style="font-weight: bold; font-size: 24px; color: #155724;">
                        {ganhos_count}
                    </span>
                    <span style="font-size: 14px; color: #155724;"> trades</span>
                </div>
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 16px; color: #155724;">
                        💰 Total: <strong>+{valor_total_ganho:.2f}%</strong>
                    </span>
                </div>
                <div>
                    <span style="font-size: 14px; color: #155724;">
                        📊 Média: <strong>+{(valor_total_ganho/ganhos_count if ganhos_count > 0 else 0):.2f}%</strong>
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="border: 2px solid #dc3545; border-radius: 12px; padding: 16px; background: linear-gradient(145deg, #f8d7da, #f5c6cb);">
                <h4 style="margin: 0 0 12px 0; color: #721c24;">💔 PERDAS</h4>
                <div style="margin-bottom: 8px;">
                    <span style="font-weight: bold; font-size: 24px; color: #721c24;">
                        {perdas_count}
                    </span>
                    <span style="font-size: 14px; color: #721c24;"> trades</span>
                </div>
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 16px; color: #721c24;">
                        💸 Total: <strong>-{valor_total_perdido:.2f}%</strong>
                    </span>
                </div>
                <div>
                    <span style="font-size: 14px; color: #721c24;">
                        📉 Média: <strong>-{(valor_total_perdido/perdas_count if perdas_count > 0 else 0):.2f}%</strong>
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            resultado_cor = "#155724" if resultado_final > 0 else "#721c24"
            resultado_bg = "linear-gradient(145deg, #d4edda, #c3e6cb)" if resultado_final > 0 else "linear-gradient(145deg, #f8d7da, #f5c6cb)"
            resultado_icon = "🏆" if resultado_final > 0 else "⚠️"
            
            st.markdown(f"""
            <div style="border: 2px solid {resultado_cor}; border-radius: 12px; padding: 16px; background: {resultado_bg};">
                <h4 style="margin: 0 0 12px 0; color: {resultado_cor};">{resultado_icon} RESULTADO</h4>
                <div style="margin-bottom: 8px;">
                    <span style="font-weight: bold; font-size: 20px; color: {resultado_cor};">
                        {'LUCRO' if resultado_final > 0 else 'PREJUÍZO'}
                    </span>
                </div>
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 18px; color: {resultado_cor};">
                        🎯 <strong>{resultado_final:+.2f}%</strong>
                    </span>
                </div>
                <div style="margin-bottom: 6px;">
                    <span style="font-size: 14px; color: {resultado_cor};">
                        ✅ Taxa: <strong>{taxa_sucesso_real:.1f}%</strong>
                    </span>
                </div>
                <div>
                    <span style="font-size: 12px; color: {resultado_cor};">
                        📊 {trades_finalizadas} finalizadas | {trades_em_aberto} ativas
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📭 Nenhuma previsão registrada ainda.")
    
    st.markdown("---")
    
    # Análise de Previsões e Vendas Inteligentes
    st.markdown("### 🎯 Previsões & Venda Inteligente")
    analises_vendas = get_analise_previsoes_vendas()
    
    if analises_vendas:
        for symbol, analise in analises_vendas.items():
            with st.expander(f"📊 {symbol} - {analise['recomendacao']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🔮 Previsão Ativa:**")
                    previsao = analise['previsao']
                    st.write(f"• Entrada: ${previsao.get('preco_entrada', 0):.6f}")
                    st.write(f"• Tempo: {previsao.get('timestamp', 'N/A')}")
                    st.write(f"• Categoria: {previsao.get('categoria', 'N/A')}")
                    
                    # Cenários de Previsão
                    if 'cenarios' in previsao:
                        st.markdown("**📈 Cenários:**")
                        for tipo, cenario in previsao['cenarios'].items():
                            st.write(f"• {tipo}: +{cenario.get('variacao_pct', 0):.1f}% em {cenario.get('tempo_estimado_horas', 0):.1f}h")
                
                with col2:
                    st.markdown("**🧠 Análise Inteligente:**")
                    venda_info = analise['analise_venda']
                    st.write(f"• Ação: **{analise['recomendacao']}**")
                    
                    if analise['percentual_venda'] > 0:
                        st.write(f"• Vender: **{analise['percentual_venda']:.0f}%**")
                    
                    if analise['motivo']:
                        st.info(f"💡 {analise['motivo']}")
                    
                    # Indicadores de Performance
                    if 'performance' in venda_info:
                        perf = venda_info['performance']
                        st.metric("📊 Score Situação", f"{perf.get('score', 0):.1f}/10")
    else:
        st.info("📭 Nenhuma posição ativa para análise no momento.")
    
    # Análise de Stop Loss Híbrido
    st.markdown("### 🛡️ Sistema Stop Loss Híbrido")
    analises_stop = get_stop_loss_analysis()
    
    if analises_stop:
        for symbol, analise in analises_stop.items():
            with st.expander(f"🛡️ {symbol} - Stop Loss Avançado"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("📉 Stop Loss %", f"{analise.get('stop_loss_pct', 0):.2f}%")
                    st.metric("💰 Stop Loss USD", f"${analise.get('stop_loss_usd', 0):.2f}")
                
                with col2:
                    st.metric("⏱️ Limite Tempo", f"{analise.get('limite_tempo', 0):.0f}h")
                    st.metric("🎯 Critério Ativo", analise.get('criterio_ativo', 'N/A'))
                
                with col3:
                    risco = analise.get('nivel_risco', 'MEDIO')
                    cor_risco = "🟢" if risco == "BAIXO" else "🟡" if risco == "MEDIO" else "🔴"
                    st.metric("⚠️ Nível Risco", f"{cor_risco} {risco}")
    else:
        st.info("🔒 Nenhuma posição ativa para análise de stop loss.")
    
    # Estatísticas do Sistema
    st.markdown("### 📊 Estatísticas do Sistema Avançado")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🎯 Posições c/ Previsão", len(analises_vendas))
    with col2:
        vendas_recomendadas = sum(1 for a in analises_vendas.values() if a['recomendacao'] != 'AGUARDAR')
        st.metric("💡 Vendas Recomendadas", vendas_recomendadas)
    with col3:
        stops_ativos = len(analises_stop)
        st.metric("🛡️ Stops Híbridos", stops_ativos)

with tab_diario:
    st.subheader("📅 Histórico de Trades - Análise por Período")
    
    # 🔍 FILTROS DE PERÍODO
    st.markdown("### 🔍 Filtros de Período")
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    with col_filtro1:
        # Data de início
        data_inicio_filter = st.date_input(
            "📅 Data Início",
            value=datetime.now().date() - pd.Timedelta(days=7),  # Últimos 7 dias por padrão
            help="Selecione a data de início do período"
        )
    
    with col_filtro2:
        # Data de fim
        data_fim_filter = st.date_input(
            "📅 Data Fim",
            value=datetime.now().date(),
            help="Selecione a data de fim do período"
        )
    
    with col_filtro3:
        # Botão de aplicar filtro
        aplicar_filtro = st.button("🔍 Filtrar Período", type="primary")
    
    # 📊 ANÁLISE DO PERÍODO SELECIONADO
    if aplicar_filtro or data_inicio_filter or data_fim_filter:
        st.markdown("---")
        st.markdown("### 📊 Resultados do Período")
        
        # Carrega trades do período
        df_trades_historico = get_ultimas_trades()
        
        if not df_trades_historico.empty and 'timestamp' in df_trades_historico.columns:
            # Filtra por período
            df_trades_historico['data'] = pd.to_datetime(df_trades_historico['timestamp']).dt.date
            
            df_filtrado = df_trades_historico[
                (df_trades_historico['data'] >= data_inicio_filter) & 
                (df_trades_historico['data'] <= data_fim_filter)
            ]
            
            if not df_filtrado.empty:
                # 💰 CONSOLIDAÇÃO DE RESULTADOS
                col_res1, col_res2, col_res3, col_res4 = st.columns(4)
                
                # Calcula métricas do período
                total_trades = len(df_filtrado)
                trades_lucro = len(df_filtrado[df_filtrado['pnl'] > 0]) if 'pnl' in df_filtrado.columns else 0
                trades_prejuizo = len(df_filtrado[df_filtrado['pnl'] < 0]) if 'pnl' in df_filtrado.columns else 0
                
                if 'pnl' in df_filtrado.columns:
                    lucro_total = df_filtrado[df_filtrado['pnl'] > 0]['pnl'].sum()
                    prejuizo_total = df_filtrado[df_filtrado['pnl'] < 0]['pnl'].sum()
                    resultado_liquido = df_filtrado['pnl'].sum()
                    win_rate = (trades_lucro / total_trades * 100) if total_trades > 0 else 0
                else:
                    lucro_total = prejuizo_total = resultado_liquido = win_rate = 0
                
                with col_res1:
                    st.metric("📊 Total Trades", total_trades)
                    st.metric("✅ Trades Lucro", trades_lucro)
                
                with col_res2:
                    st.metric("💚 Total Ganhos", f"${lucro_total:+.2f}")
                    st.metric("🎯 Win Rate", f"{win_rate:.1f}%")
                
                with col_res3:
                    st.metric("💔 Total Perdas", f"${prejuizo_total:+.2f}", delta_color="inverse")
                    st.metric("❌ Trades Prejuízo", trades_prejuizo)
                
                with col_res4:
                    # RESULTADO REAL FINAL
                    cor_resultado = "normal" if resultado_liquido >= 0 else "inverse"
                    emoji_resultado = "🎉" if resultado_liquido >= 0 else "😰"
                    st.metric(f"{emoji_resultado} RESULTADO REAL", f"${resultado_liquido:+.2f}", 
                             delta=f"{resultado_liquido:+.2f}", delta_color=cor_resultado)
                    
                    # Percentual sobre capital inicial
                    if resultado_liquido != 0:
                        pct_resultado = (resultado_liquido / saldo_inicial_dia * 100)
                        st.caption(f"📊 {pct_resultado:+.2f}% do capital")
                
                st.markdown("---")
                
                # 🏆 RESUMO EXECUTIVO
                st.markdown("### 🏆 Resumo Executivo do Período")
                col_resumo1, col_resumo2 = st.columns(2)
                
                with col_resumo1:
                    st.markdown("**📈 Performance:**")
                    if resultado_liquido > 0:
                        st.success(f"✅ Período LUCRATIVO com ${resultado_liquido:+.2f}")
                    elif resultado_liquido < 0:
                        st.error(f"❌ Período com PREJUÍZO de ${resultado_liquido:+.2f}")
                    else:
                        st.info("➖ Período neutro (sem lucro/prejuízo)")
                    
                    # Análise da eficiência
                    if total_trades > 0:
                        st.markdown("**🎯 Eficiência:**")
                        if win_rate >= 70:
                            st.success(f"🌟 Excelente taxa de sucesso: {win_rate:.1f}%")
                        elif win_rate >= 60:
                            st.info(f"👍 Boa taxa de sucesso: {win_rate:.1f}%")
                        elif win_rate >= 50:
                            st.warning(f"⚠️ Taxa moderada: {win_rate:.1f}%")
                        else:
                            st.error(f"🔻 Taxa baixa de sucesso: {win_rate:.1f}%")
                
                with col_resumo2:
                    st.markdown("**💡 Insights:**")
                    
                    # Análise risk/reward
                    if trades_lucro > 0 and trades_prejuizo > 0:
                        lucro_medio = lucro_total / trades_lucro
                        prejuizo_medio = abs(prejuizo_total / trades_prejuizo)
                        ratio_risk_reward = lucro_medio / prejuizo_medio
                        
                        st.write(f"💰 Lucro médio por trade: ${lucro_medio:.2f}")
                        st.write(f"💔 Perda média por trade: ${prejuizo_medio:.2f}")
                        st.write(f"⚖️ Ratio R/R: {ratio_risk_reward:.2f}")
                        
                        if ratio_risk_reward >= 2:
                            st.success("🎯 Excelente gestão de risco!")
                        elif ratio_risk_reward >= 1.5:
                            st.info("👍 Boa gestão de risco")
                        else:
                            st.warning("⚠️ Melhorar gestão de risco")
                    
                    # Frequência de trading
                    periodo_dias = (data_fim_filter - data_inicio_filter).days + 1
                    trades_por_dia = total_trades / periodo_dias if periodo_dias > 0 else 0
                    st.write(f"📊 Período analisado: {periodo_dias} dias")
                    st.write(f"🔄 Trades por dia: {trades_por_dia:.1f}")
                
                st.markdown("---")
                
                # 📋 TABELA DETALHADA DAS TRADES
                st.markdown("### 📋 Trades Detalhadas do Período")
                
                # Prepara dados para exibição
                df_display_historico = df_filtrado.copy()
                
                if 'timestamp' in df_display_historico.columns:
                    df_display_historico['📅 Data/Hora'] = df_display_historico['timestamp'].dt.strftime('%d/%m/%Y %H:%M')
                
                if 'symbol' in df_display_historico.columns:
                    df_display_historico['🪙 Moeda'] = df_display_historico['symbol']
                elif 'pair' in df_display_historico.columns:
                    df_display_historico['🪙 Moeda'] = df_display_historico['pair']
                
                if 'pnl' in df_display_historico.columns:
                    def format_pnl_historico(value):
                        if value > 0:
                            return f"💚 ${value:+.2f}"
                        elif value < 0:
                            return f"💔 ${value:+.2f}"
                        else:
                            return f"➖ ${value:+.2f}"
                    
                    df_display_historico['💰 Resultado'] = df_display_historico['pnl'].apply(format_pnl_historico)
                
                if 'estrategia' in df_display_historico.columns:
                    df_display_historico['🤖 Estratégia'] = df_display_historico['estrategia']
                
                # Seleciona colunas para exibir
                colunas_exibir_hist = []
                for col in ['📅 Data/Hora', '🪙 Moeda', '💰 Resultado', '🤖 Estratégia']:
                    if col in df_display_historico.columns:
                        colunas_exibir_hist.append(col)
                
                if colunas_exibir_hist:
                    st.dataframe(
                        df_display_historico[colunas_exibir_hist].sort_values('📅 Data/Hora', ascending=False),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.dataframe(df_filtrado[['timestamp', 'symbol', 'pnl']].head(20), use_container_width=True)
                
                # 📈 GRÁFICO DE EVOLUÇÃO DO PERÍODO
                st.markdown("### 📈 Evolução dos Resultados")
                
                if 'pnl' in df_filtrado.columns and 'timestamp' in df_filtrado.columns:
                    df_grafico = df_filtrado.sort_values('timestamp').copy()
                    df_grafico['lucro_acumulado'] = df_grafico['pnl'].cumsum()
                    df_grafico['data_grafico'] = df_grafico['timestamp'].dt.strftime('%d/%m %H:%M')
                    
                    # Gráfico de linha da evolução
                    st.line_chart(df_grafico.set_index('data_grafico')['lucro_acumulado'])
                    
                    # Estatísticas do gráfico
                    maior_alta = df_grafico['lucro_acumulado'].max()
                    maior_baixa = df_grafico['lucro_acumulado'].min()
                    
                    col_graf1, col_graf2, col_graf3 = st.columns(3)
                    with col_graf1:
                        st.metric("🚀 Maior Alta", f"${maior_alta:+.2f}")
                    with col_graf2:
                        st.metric("📉 Maior Baixa", f"${maior_baixa:+.2f}")
                    with col_graf3:
                        volatilidade = maior_alta - maior_baixa
                        st.metric("🌊 Volatilidade", f"${volatilidade:.2f}")
            
            else:
                st.warning(f"❌ Nenhuma trade encontrada no período de {data_inicio_filter} até {data_fim_filter}")
        
        else:
            st.error("❌ Dados de trades não disponíveis")
    
    else:
        # Mostra histórico padrão quando não há filtro aplicado
        st.markdown("### 📊 Curva de Lucro Diário")
        dias = gestor.dados.get('dias', {})
        if dias:
            df_h = pd.DataFrame([{"Data": d, "Lucro": v.get('lucro_do_dia', 0.0)} for d, v in dias.items()])
            st.line_chart(df_h.set_index("Data"))
        else:
            st.info("📊 Selecione um período acima para ver análise detalhada ou aguarde dados do sistema.")

# Rodapé com informações do sistema
st.markdown("---")
col_foot1, col_foot2, col_foot3 = st.columns(3)
with col_foot1:
    st.caption(f"🤖 R7_V3 Sniper V2 | Build 2026.01.09")
with col_foot2:
    st.caption(f"🔄 Auto-refresh: 45s | ⏰ {datetime.now().strftime('%H:%M:%S')}")
with col_foot3:
    uptime_info = f"⚡ Refresh #{st.session_state.refresh_count}"
    st.caption(uptime_info)
