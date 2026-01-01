import os
import joblib
import pandas as pd
import pandas_ta as ta
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import logging
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import sqlite3
import json
from datetime import datetime
from transformers import pipeline
import warnings

# Limpa avisos de depreciação do Pandas para manter o terminal limpo
warnings.filterwarnings('ignore', category=FutureWarning)

logger = logging.getLogger('ia_engine')

class IAEngine:
    def __init__(self, model_path='cerebro_ia.joblib', db_path='memoria_bot.db'):
        self.model_path = model_path
        self.db_path = db_path
        self.analyzer = SentimentIntensityAnalyzer()
        
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
            print(f"\n⚠️ SOLICITAÇÃO DE REGISTRO FINANCEIRO:")
            print(f"   - TIPO: {tipo.upper()}")
            print(f"   - VALOR: ${valor:.2f}")
            print(f"   - DESCRIÇÃO: {descricao}")

            confirmacao = input("Confirmar este registro no banco de dados? (s/n): ").strip().lower()

            if confirmacao != 's':
                logger.info(f"🚫 Registro de {tipo.upper()} cancelado pelo usuário.")
                return False

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

    def predict(self, data, symbol=None):
        if self.model is None: return {"sinal": "WAIT", "confianca": 0.5}
        try:
            if isinstance(data, (int, float)):
                return {"sinal": "WAIT", "confianca": 0.5, "motivo": "Dados brutos"}

            df = pd.DataFrame([data])
            features_cols = ['close', 'rsi', 'volume', 'ema20', 'ema200', 'bb_upper', 'bb_lower', 
                             'price_above_ema', 'trend_4h', 'buy_pressure', 'volume_24h', 
                             'fear_greed', 'news_sentiment', 'whale_risk', 'price_change_percent', 'avg_price']
            
            for col in features_cols:
                if col not in df.columns: df[col] = 0
            
            X = df[features_cols]
            prob = self.model.predict_proba(X)[0][1]
            sinal = "BUY" if prob >= 0.85 else "WAIT"
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
            feat = {
                'close': preco_atual,
                'rsi': last['rsi'],
                'ema20': last['ema20'],
                'price_above_ema': 1 if preco_atual > last['ema20'] else 0
            }

            res = self.predict(feat)
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
                        'fear_greed', 'news_sentiment', 'whale_risk', 'price_change_percent', 'avg_price']
            
            df = df.dropna(subset=['sucesso'])
            X = df[features].fillna(0)
            
            # --- CORREÇÃO DO ERRO DE TARGET CONTÍNUO ---
            # Converte a coluna 'sucesso' (que pode vir como lucro real/contínuo) em 0 ou 1.
            y = df['sucesso']
            y_numeric = pd.to_numeric(y, errors='coerce').fillna(0)
            y_binary = (y_numeric > 0).astype(int) 
            
            self.model.fit(X, y_binary)
            self.save_model()
            logger.info(f"🧠 IA SNIPER TREINADA. Exemplos: {len(df)}")
            return True
        except Exception as e:
            logger.error(f"Erro no treino: {e}")
            return False