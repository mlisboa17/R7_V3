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

# Limpa avisos de depreciação do Pandas para manter o terminal profissional
warnings.filterwarnings('ignore', category=FutureWarning)

logger = logging.getLogger('ia_engine')

class IAEngine:
    def __init__(self, model_path='cerebro_ia.joblib', db_path='memoria_bot.db'):
        self.model_path = model_path
        self.db_path = db_path
        self.analyzer = SentimentIntensityAnalyzer()
        
        # Carregamento do FinBERT (Otimizado: apenas se necessário ou disponível)
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
        Registra movimentos financeiros: REALOCADA, APORTE ou RETIRADA.
        Estes valores NÃO entram no cálculo de lucro/prejuízo diário (PnL).
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insere o registro detalhado
            cursor.execute('''
                INSERT INTO movimentacoes (tipo, valor, descricao)
                VALUES (?, ?, ?)
            ''', (tipo.upper(), valor, descricao))
            
            # Se for APORTE ou RETIRADA/REALOCADA, atualizamos o saldo_final do dia 
            # apenas para controle de banca, mas SEM mexer no lucro_liq.
            hoje = datetime.now().date().isoformat()
            ajuste = valor if tipo.upper() == 'APORTE' else -valor
            
            cursor.execute('''
                UPDATE daily_states 
                SET saldo_final = saldo_final + ? 
                WHERE data = ?
            ''', (ajuste, hoje))
            
            conn.commit()
            conn.close()
            logger.info(f"💾 Registrado: {tipo.upper()} - {valor} - {descricao}")
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
        # Tabela de estados diários (resumo diário) - Adicionando campos novos
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
        
        # Garantir que as colunas existam caso a tabela já tenha sido criada antes
        try:
            cursor.execute('ALTER TABLE daily_states ADD COLUMN aporte REAL DEFAULT 0;')
            cursor.execute('ALTER TABLE daily_states ADD COLUMN saque REAL DEFAULT 0;')
        except sqlite3.OperationalError:
            pass  # As colunas já existem
            
        # Tabela específica para Movimentações (Aporte, Retirada, Realocação)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,        -- REALOCADA, APORTE, RETIRADA
                valor REAL,
                descricao TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def predict(self, data, symbol=None):
        """
        ASSINATURA UNIVERSAL: Aceita dicionário de features ou valor unitário.
        Resolve o erro de 'positional arguments'.
        """
        if self.model is None: return {"sinal": "WAIT", "confianca": 0.5}

        try:
            # Se receber apenas o preço, cria um DF simplificado
            if isinstance(data, (int, float)):
                # Fallback: Se não temos todas as features, simulamos com o preço
                # Para maior acurácia, o Analista deve enviar o dicionário completo
                return {"sinal": "WAIT", "confianca": 0.5, "motivo": "Dados insuficientes"}

            # Se receber o dicionário completo (comportamento padrão do AnalistaBot)
            df = pd.DataFrame([data])
            
            # Garante que as colunas estão na ordem correta do treino
            features_cols = ['close', 'rsi', 'volume', 'ema20', 'ema200', 'bb_upper', 'bb_lower', 
                             'price_above_ema', 'trend_4h', 'buy_pressure', 'volume_24h', 
                             'fear_greed', 'news_sentiment', 'whale_risk', 'price_change_percent', 'avg_price']
            
            # Preenche colunas faltantes com 0 para não quebrar o modelo
            for col in features_cols:
                if col not in df.columns: df[col] = 0
            
            X = df[features_cols]
            prob = self.model.predict_proba(X)[0][1]
            sinal = "BUY" if prob >= 0.85 else "WAIT"

            return {"sinal": sinal, "confianca": prob}
            
        except Exception as e:
            logger.error(f"Erro na predição IA: {e}")
            return {"sinal": "WAIT", "confianca": 0.0}

    async def analisar_tick(self, symbol, preco_atual, buffer_precos):
        """
        MOTOR SNIPER: Integrado com o WebSocket.
        """
        try:
            if len(buffer_precos) < 20:
                return {"decisao": "AGUARDAR", "estrategia": "none", "forca": 0}

            # Prepara dados rápidos do buffer
            df = pd.DataFrame(list(buffer_precos), columns=['close'])
            df['close'] = df['close'].astype(float)
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema20'] = ta.ema(df['close'], length=20)
            
            last = df.iloc[-1]
            
            # Dicionário de features para o predict
            feat = {
                'close': preco_atual,
                'rsi': last['rsi'],
                'ema20': last['ema20'],
                'price_above_ema': 1 if preco_atual > last['ema20'] else 0,
                # Outras features podem ser zeradas se não disponíveis no tick
            }

            res = self.predict(feat)

            if res['sinal'] == "BUY":
                # Lógica de moedas
                if any(x in symbol for x in ['BTC', 'ETH', 'BNB']):
                    est, forca = "scalping_v6", 1.5
                elif any(x in symbol for x in ['SOL', 'AVAX', 'NEAR', 'FET', 'RNDR']):
                    est, forca = "momentum_boost", 1.2
                else:
                    est, forca = "swing_rwa", 1.0
                
                return {"decisao": "COMPRAR", "estrategia": est, "forca": forca, "confianca": res['confianca']}
            
            return {"decisao": "AGUARDAR", "estrategia": "none", "forca": 0}

        except Exception as e:
            logger.error(f"Erro no Analisar Tick IA: {e}")
            return {"decisao": "AGUARDAR", "estrategia": "none", "forca": 0}

    def train(self):
        """Treino blindado contra colunas vazias."""
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
            y = df['sucesso']

            self.model.fit(X, y)
            self.save_model()
            logger.info(f"🧠 IA SNIPER TREINADA. Exemplos: {len(df)}")
            return True
        except Exception as e:
            logger.error(f"Erro no treino: {e}")
            return False