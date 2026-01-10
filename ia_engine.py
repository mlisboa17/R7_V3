import os
import joblib
import pandas as pd
import pandas_ta as ta
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, recall_score, precision_score, f1_score
import logging
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import sqlite3
import json
from datetime import datetime
from transformers import pipeline
import warnings
import asyncio

# Limpa avisos de depreciação do Pandas para manter o terminal limpo
warnings.filterwarnings('ignore', category=FutureWarning)

logger = logging.getLogger('ia_engine')

class IAEngine:
    def __init__(self, model_path='cerebro_ia.joblib', db_path='memoria_bot.db'):
        self.model_path = model_path
        self.db_path = db_path
        self.analyzer = SentimentIntensityAnalyzer()
        
        # API Keys para Order Book
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_SECRET_KEY')
        
        # Carregamento do FinBERT (Otimizado)
        try:
            self.finbert = pipeline("sentiment-analysis", model="ProsusAI/finbert", device=-1)
        except Exception as e:
            logger.warning(f"⚠️ FinBERT não carregado: {e}. Usando fallback Vader.")
            self.finbert = None

        self.create_tables()
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            logger.info("🧠 IA carregada do arquivo.")
        else:
            self.model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
            logger.info("🧠 Nova IA criada.")

    def save_model(self):
        joblib.dump(self.model, self.model_path)
        logger.info("🧠 IA salva.")

    def registrar_movimento(self, tipo, valor, descricao):
        """
        Registra movimentos financeiros apenas após confirmação manual no console.
        """
        try:
            # Em ambientes de produção queremos evitar bloqueios por input().
            # Controle via .env: R7_INTERACTIVE_REGISTRAR=true|false
            import os
            interactive = os.getenv('R7_INTERACTIVE_REGISTRAR', 'false').lower() in ('1', 'true', 'yes', 'y')

            if interactive:
                print(f"\n⚠️ SOLICITAÇÃO DE REGISTRO FINANCEIRO:")
                print(f"   - TIPO: {tipo.upper()}")
                print(f"   - VALOR: ${valor:.2f}")
                print(f"   - DESCRIÇÃO: {descricao}")

                confirmacao = input("Confirmar este registro no banco de dados? (s/n): ").strip().lower()

                if confirmacao != 's':
                    logger.info(f"🚫 Registro de {tipo.upper()} cancelado pelo usuário.")
                    return False
            else:
                logger.info("[IAEngine] Registro automático (modo não-interativo). Verifique R7_INTERACTIVE_REGISTRAR se desejar confirmação manual.")

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO movimentacoes (tipo, valor, descricao)
                VALUES (?, ?, ?)
            ''', (tipo.upper(), valor, descricao))

            hoje = datetime.now().date().isoformat()
            ajuste = valor if tipo.upper() == 'APORTE' else -valor

            cursor.execute('''
                UPDATE daily_states
                SET saldo_final = saldo_final + ?
                WHERE data = ?
            ''', (ajuste, hoje))

            conn.commit()
            conn.close()
            logger.info(f"💾 Confirmado e Registrado: {tipo.upper()} - {valor}")
            return True

        except Exception as e:
            logger.error(f"Erro ao registrar movimento: {e}")
            return False

    def create_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                close REAL, rsi REAL, volume REAL, ema20 REAL, ema200 REAL,
                bb_upper REAL, bb_lower REAL, price_above_ema INTEGER,
                trend_4h REAL, buy_pressure REAL, volume_24h REAL,
                fear_greed REAL, news_sentiment REAL, whale_risk REAL,
                price_change_percent REAL, avg_price REAL, decision INTEGER, sucesso INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data DATE UNIQUE,
                saldo_ini REAL,
                lucro_bruto REAL,
                taxas REAL,
                lucro_liq REAL,
                win_rate REAL,
                meta REAL,
                exposicao REAL,
                saldo_final REAL,
                aporte REAL DEFAULT 0,
                saque REAL DEFAULT 0
            )
        ''')
        
        try:
            cursor.execute('ALTER TABLE daily_states ADD COLUMN aporte REAL DEFAULT 0;')
            cursor.execute('ALTER TABLE daily_states ADD COLUMN saque REAL DEFAULT 0;')
        except sqlite3.OperationalError:
            pass 
            
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                valor REAL,
                descricao TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 📊 NOVA TABELA: Métricas de treino da IA
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ia_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                recall REAL,
                precision REAL,
                f1_score REAL,
                n_samples INTEGER,
                accuracy REAL
            )
        ''')
        
        conn.commit()
        conn.close()

    def get_historico_for_train(self):
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query('SELECT * FROM analises WHERE sucesso IS NOT NULL', conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar histórico no DB: {e}")
            return pd.DataFrame()
    
    async def obter_order_book(self, symbol):
        """📖 Busca profundidade de mercado (Order Book) da Binance"""
        try:
            # Usa API REST da Binance (não precisa de autenticação)
            url = f"https://api.binance.com/api/v3/depth"
            params = {'symbol': symbol, 'limit': 20}
            
            response = requests.get(url, params=params, timeout=3)
            
            if response.status_code == 200:
                depth = response.json()
                
                # Analisa bids (compra) e asks (venda)
                bids = depth.get('bids', [])[:5]  # 5 primeiros níveis
                asks = depth.get('asks', [])[:5]
                
                if not bids or not asks:
                    return None
                
                # Calcula força do suporte/resistência
                bid_volume = sum([float(b[1]) for b in bids])
                ask_volume = sum([float(a[1]) for a in asks])
                
                # Spread bid-ask (liquidez)
                bid_price = float(bids[0][0])
                ask_price = float(asks[0][0])
                spread = (ask_price - bid_price) / bid_price if bid_price > 0 else 0
                
                return {
                    'bid_volume': bid_volume,
                    'ask_volume': ask_volume,
                    'bid_ask_ratio': bid_volume / ask_volume if ask_volume > 0 else 0,
                    'spread_pct': spread * 100,
                    'support_strength': bid_volume  # Força do suporte
                }
            else:
                logger.warning(f"⚠️ Erro ao buscar order book: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar order book: {e}")
            return None

    def predict(self, data, symbol=None):
        if self.model is None: return {"sinal": "WAIT", "confianca": 0.5}
        try:
            if isinstance(data, (int, float)):
                return {"sinal": "WAIT", "confianca": 0.5, "motivo": "Dados brutos"}

            df = pd.DataFrame([data])
            features_cols = ['close', 'rsi', 'volume', 'ema20', 'ema200', 'bb_upper', 'bb_lower', 
                             'price_above_ema', 'trend_4h', 'buy_pressure', 'volume_24h', 
                             'fear_greed', 'news_sentiment', 'whale_risk', 'price_change_percent', 'avg_price',
                             # 📖 Order Book features
                             'bid_volume', 'ask_volume', 'bid_ask_ratio', 'spread_pct', 'support_strength',
                             # 🕯️ Candlestick features
                             'hammer', 'inverted_hammer', 'pin_bar', 'bullish_engulfing', 'doji']
            
            for col in features_cols:
                if col not in df.columns: df[col] = 0
            
            X = df[features_cols]
            prob = self.model.predict_proba(X)[0][1]
            
            # THRESHOLD REDUZIDO: 45% (mais agressivo, alinhado com analista 50%)
            sinal = "BUY" if prob >= 0.45 else "WAIT"
            
            # Log detalhado para debug
            if symbol:  # Se symbol foi passado
                if prob >= 0.40:  # Log se estiver próximo de comprar
                    logger.info(f"🧠 IA {symbol}: prob={prob:.2%} -> sinal={sinal} (threshold=45%)")
            
            return {"sinal": sinal, "confianca": prob}
        except Exception as e:
            logger.error(f"Erro na predição: {e}")
            return {"sinal": "WAIT", "confianca": 0.0}

    async def analisar_tick(self, symbol, preco_atual, buffer_precos):
        try:
            if len(buffer_precos) < 20:
                return {"decisao": "AGUARDAR", "estrategia": "none", "forca": 0}

            df = pd.DataFrame(list(buffer_precos), columns=['close'])
            df['close'] = df['close'].astype(float)
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema20'] = ta.ema(df['close'], length=20)
            
            last = df.iloc[-1]
            
            # 🕯️ VERIFICA PADRÕES DE CANDLESTICK (se tiver dados OHLC)
            candlestick_features = {
                'hammer': 0, 'inverted_hammer': 0, 'pin_bar': 0, 
                'bullish_engulfing': 0, 'doji': 0
            }
            
            try:
                from tools.candlestick_patterns import CandlestickPatterns
                
                # Se buffer_precos tem dados OHLC completos
                if isinstance(buffer_precos[0], dict) and 'high' in buffer_precos[0]:
                    df_ohlc = pd.DataFrame(list(buffer_precos))
                    patterns = CandlestickPatterns.detect_all_patterns(df_ohlc)
                    if not patterns.empty:
                        last_pattern = patterns.iloc[-1]
                        candlestick_features = {
                            'hammer': int(last_pattern['hammer']),
                            'inverted_hammer': int(last_pattern['inverted_hammer']),
                            'pin_bar': int(last_pattern['pin_bar']),
                            'bullish_engulfing': int(last_pattern['bullish_engulfing']),
                            'doji': int(last_pattern['doji'])
                        }
                        
                        # 🔨 PROTEÇÃO: Se detectou martelo/pin bar em RSI baixo, NÃO VENDA!
                        if (candlestick_features['hammer'] or candlestick_features['pin_bar']) and last['rsi'] < 35:
                            logger.info(f"🔨 {symbol}: MARTELO/PIN BAR em RSI {last['rsi']:.1f} - AGUARDANDO REVERSÃO")
                            return {"decisao": "AGUARDAR", "estrategia": "none", "forca": 0, "motivo": "vela_de_exaustao"}
            except ImportError:
                pass  # Candlestick patterns não disponível
            except Exception as e:
                logger.debug(f"Não foi possível analisar candlesticks: {e}")
            
            # 📖 BUSCA ORDER BOOK
            order_book_features = {
                'bid_volume': 0, 'ask_volume': 0, 'bid_ask_ratio': 0,
                'spread_pct': 0, 'support_strength': 0
            }
            
            try:
                order_book = await self.obter_order_book(symbol)
                if order_book:
                    order_book_features = order_book
            except Exception as e:
                logger.debug(f"Não foi possível buscar order book: {e}")
            
            # Monta features completas
            feat = {
                'close': preco_atual,
                'rsi': last['rsi'],
                'ema20': last['ema20'],
                'price_above_ema': 1 if preco_atual > last['ema20'] else 0,
                **order_book_features,
                **candlestick_features
            }

            res = self.predict(feat, symbol=symbol)
            if res['sinal'] == "BUY":
                if any(x in symbol for x in ['BTC', 'ETH', 'BNB']):
                    est, forca = "scalping_v6", 1.5
                elif any(x in symbol for x in ['SOL', 'AVAX', 'NEAR', 'FET', 'RENDER']):
                    est, forca = "momentum_boost", 1.2
                else:
                    est, forca = "swing_rwa", 1.0
                return {"decisao": "COMPRAR", "estrategia": est, "forca": forca, "confianca": res['confianca']}
            
            return {"decisao": "AGUARDAR", "estrategia": "none", "forca": 0}
        except Exception as e:
            logger.error(f"Erro no analisar_tick: {e}")
            return {"decisao": "AGUARDAR", "estrategia": "none", "forca": 0}

    def train(self):
        """Treina a IA garantindo que os targets sejam binários/discretos."""
        try:
            df_db = self.get_historico_for_train()
            df_csv = pd.read_csv('data/historico_ia.csv') if os.path.exists('data/historico_ia.csv') else pd.DataFrame()
            
            df = pd.concat([df_db, df_csv], ignore_index=True)
            if df.empty or 'sucesso' not in df.columns:
                logger.warning("📄 Sem dados suficientes para treino.")
                return False

            features = ['close', 'rsi', 'volume', 'ema20', 'ema200', 'bb_upper', 'bb_lower', 
                        'price_above_ema', 'trend_4h', 'buy_pressure', 'volume_24h', 
                        'fear_greed', 'news_sentiment', 'whale_risk', 'price_change_percent', 'avg_price',
                        # 📖 Order Book features (podem estar vazias em dados antigos)
                        'bid_volume', 'ask_volume', 'bid_ask_ratio', 'spread_pct', 'support_strength',
                        # 🕯️ Candlestick features (podem estar vazias em dados antigos)
                        'hammer', 'inverted_hammer', 'pin_bar', 'bullish_engulfing', 'doji']
            
            df = df.dropna(subset=['sucesso'])
            
            # Adiciona features que podem não existir em dados antigos
            for feat in features:
                if feat not in df.columns:
                    df[feat] = 0
            
            X = df[features].fillna(0)
            
            # --- CORREÇÃO DO ERRO DE TARGET CONTÍNUO ---
            # Converte a coluna 'sucesso' (que pode vir como lucro real/contínuo) em 0 ou 1.
            y = df['sucesso']
            y_numeric = pd.to_numeric(y, errors='coerce').fillna(0)
            y_binary = (y_numeric > 0).astype(int)
            
            # 📊 DIVIDE EM TREINO E TESTE (70/30)
            if len(df) >= 10:  # Só divide se tiver dados suficientes
                X_train, X_test, y_train, y_test = train_test_split(X, y_binary, test_size=0.3, random_state=42)
            else:
                X_train, X_test, y_train, y_test = X, X, y_binary, y_binary  # Usa todos os dados
            
            # Treina
            self.model.fit(X_train, y_train)
            
            # 📈 CALCULA MÉTRICAS DE PERFORMANCE
            try:
                y_pred = self.model.predict(X_test)
                
                recall = recall_score(y_test, y_pred, zero_division=0)
                precision = precision_score(y_test, y_pred, zero_division=0)
                f1 = f1_score(y_test, y_pred, zero_division=0)
                accuracy = accuracy_score(y_test, y_pred)
                
                # Log detalhado
                logger.info(f"🧠 IA SNIPER TREINADA. Exemplos: {len(df)}")
                logger.info(f"📊 MÉTRICAS DE PERFORMANCE:")
                logger.info(f"   ✅ RECALL:    {recall:.1%} (identifica {recall:.1%} das oportunidades reais)")
                logger.info(f"   ✅ PRECISION: {precision:.1%} (acurácia quando prevê compra)")
                logger.info(f"   ✅ F1-SCORE:  {f1:.1%} (balanço geral)")
                logger.info(f"   ✅ ACCURACY:  {accuracy:.1%} (acurácia geral)")
                
                # ⚠️ ALERTAS
                if recall < 0.60:
                    logger.warning(f"⚠️ RECALL BAIXO ({recall:.1%})! IA está perdendo muitas oportunidades!")
                    logger.warning(f"   → Considere aumentar o dataset de treino")
                    logger.warning(f"   → Verifique se features de Order Book estão sendo coletadas")
                
                if precision < 0.50:
                    logger.warning(f"⚠️ PRECISION BAIXA ({precision:.1%})! Muitos alarmes falsos!")
                    logger.warning(f"   → Considere ajustar threshold de confiança")
                
                # 💾 Salva métricas no banco
                self._salvar_metricas_treino(recall, precision, f1, len(df), accuracy)
                
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível calcular métricas: {e}")
            
            self.save_model()
            return True
        except Exception as e:
            logger.error(f"Erro no treino: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _salvar_metricas_treino(self, recall, precision, f1, n_samples, accuracy):
        """💾 Salva métricas de treino para auditoria"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ia_metrics (recall, precision, f1_score, n_samples, accuracy)
                VALUES (?, ?, ?, ?, ?)
            ''', (recall, precision, f1, n_samples, accuracy))
            
            conn.commit()
            conn.close()
            
            logger.info(f"💾 Métricas salvas no DB para auditoria")
        except Exception as e:
            logger.error(f"Erro ao salvar métricas: {e}")