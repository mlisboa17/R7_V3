import logging
import pandas as pd
# import pandas_ta as ta  # Removido - usando cálculos manuais
import asyncio

logger = logging.getLogger('analista')

class AnalistaBot:
    def __init__(self, config, client=None, ia=None):
        self.config = config
        self.client = client
        self.ia = ia
        self.executor = None # Injetado via main.py
        self.historico_df = {}

    def set_executor(self, executor):
        self.executor = executor

    def avaliar_exaustao(self, symbol, preco_atual):
        """
        🎯 SAÍDA INTELIGENTE - Verifica se a tendência ainda é de alta ou se há reversão iminente.
        Retorna "MANTER" se ainda há força de alta, "VENDER" se sinais de exaustão.
        """
        try:
            df = self.historico_df.get(symbol)
            if df is None or len(df) < 20:
                logger.debug(f"⚠️ {symbol}: Sem dados suficientes para avaliar exaustão - VENDER por segurança")
                return "VENDER"

            # 1. RSI (Acima de 70 indica sobrecomprado - Perigo de reversão)
            rsi_atual = df['rsi'].iloc[-1] if 'rsi' in df.columns else 50
            
            # 2. Tendência de Curto Prazo (Inclinação da EMA5)
            ema5_atual = df['ema5'].iloc[-1] if 'ema5' in df.columns else preco_atual
            ema5_anterior = df['ema5'].iloc[-2] if 'ema5' in df.columns and len(df) >= 2 else ema5_atual
            
            # 🔍 Lógica de Decisão:
            # Se RSI < 70, preço acima EMA5 E EMA5 subindo = Ainda tem força!
            if rsi_atual < 70 and preco_atual > ema5_atual and ema5_atual > ema5_anterior:
                logger.info(f"🚀 {symbol}: FORÇA DE ALTA (RSI:{rsi_atual:.1f} < 70 | EMA5↑) - MANTER")
                return "MANTER"
            
            # Se RSI > 70 ou EMA5 virando para baixo: hora de realizar o lucro
            if rsi_atual >= 70:
                logger.warning(f"⚠️ {symbol}: RSI sobrecomprado ({rsi_atual:.1f} >= 70) - VENDER")
                return "VENDER"
            elif ema5_atual <= ema5_anterior:
                logger.warning(f"📉 {symbol}: EMA5 inclinando para baixo - VENDER")
                return "VENDER"
            elif ema5_atual <= ema5_anterior:
                logger.warning(f"📉 {symbol}: EMA5 inclinando para baixo - VENDER")
            else:
                logger.info(f"🎯 {symbol}: Preço abaixo da EMA5 - VENDER")
                
            return "VENDER"
            
        except Exception as e:
            logger.error(f"❌ Erro ao avaliar exaustão de {symbol}: {e}")
            return "VENDER"  # Na dúvida, realiza o lucro

    def check_btc_panic(self):
        """
        🛑 FILTRO BTC PANIC - Melhoria #7 (OTIMIZADO)
        Detecta se o BTC está em queda livre nos últimos 15 minutos.
        Usa histórico em cache (mais rápido que API call).
        Retorna True se BTC caiu > 0.5% em 15min.
        """
        try:
            if "BTCUSDT" not in self.historico_df:
                return False
            
            btc_df = self.historico_df["BTCUSDT"]
            
            if len(btc_df) < 3:
                return False
            
            # Compara preço atual com o preço de 15 min atrás (3 velas de 5min)
            preco_agora = btc_df['close'].iloc[-1]
            preco_antes = btc_df['close'].iloc[-3]
            variacao = (preco_agora / preco_antes) - 1
            
            # Se cair mais de 0.5% em 15min, é pânico
            if variacao < -0.005:
                logger.warning(f"🚨 [BTC PANIC] BTC caiu {variacao*100:.2f}% nos últimos 15min - BLOQUEANDO ALTS")
                return True
            
            logger.debug(f"✅ [BTC CHECK] BTC variou {variacao*100:.2f}% - Normal")
            return False
            
        except Exception as e:
            logger.error(f"Erro no check BTC panic: {e}")
            return False  # Em caso de erro, não bloqueia

    def calculate_indicators(self, df):
        try:
            if len(df) < 30: return df
            # Cálculo manual do RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Cálculo manual das EMAs
            df['ema5'] = df['close'].ewm(span=5).mean()
            df['ema20'] = df['close'].ewm(span=20).mean()
            return df
        except Exception as e:
            logger.error(f"Erro nos indicadores: {e}")
            return df

    async def atualizar_historico(self, symbol):
        try:
            if not self.client: return
            # Busca 100 velas de 5min para dar contexto à IA
            klines = await self.client.get_klines(symbol=symbol, interval='5m', limit=100)
            df = pd.DataFrame(klines, columns=['ts', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qv', 'nt', 'tb', 'tq', 'i'])
            for col in ['open', 'high', 'low', 'close', 'vol']:
                df[col] = df[col].astype(float)
            self.historico_df[symbol] = df
        except Exception as e:
            logger.error(f"Erro ao carregar histórico de {symbol}: {e}")

    async def analisar_tick(self, symbol, preco_atual):
        """
        MOTOR DE DECISÃO V5: Com Trailing Stop, Limite Adaptativo e Filtro BTC.
        Se IA >= 85%, ignora RSI/EMA e atira.
        """
        try:
            # 🛑 FILTRO BTC PANIC - Bloqueia alts se BTC em queda livre (método síncrono otimizado)
            if symbol != "BTCUSDT":
                btc_panic = self.check_btc_panic()
                if btc_panic:
                    return {"decisao": "VETADO", "motivo": "BTC_PANIC", "confianca": 0}
            
            # 1. Definição de Estratégia por Perfil de Moeda (5 Estratégias Otimizadas)
            
            # 🔷 BLUE CHIPS - Scalping conservador em grandes caps
            if any(x in symbol for x in ['BTC', 'ETH', 'BNB']):
                est_nome = 'scalping_v6'
            
            # 🎭 MEME SNIPER - Agressivo para memes de alta volatilidade
            elif any(x in symbol for x in ['PEPE', 'WIF', 'DOGE']):
                est_nome = 'meme_sniper'
            
            # 🚀 MOMENTUM BOOST - Layer 1 + AI com força de momentum
            elif any(x in symbol for x in ['SOL', 'AVAX', 'NEAR', 'FET', 'RENDER', 'ATOM']):
                est_nome = 'momentum_boost'
            
            # 🌐 LAYER2 DEFI - Layer 2 e DeFi com volatilidade média
            elif any(x in symbol for x in ['ARB', 'POL', 'JUP']):
                est_nome = 'layer2_defi'
            
            # 🎮 GAMING - Gaming/Metaverse com alta volatilidade
            elif any(x in symbol for x in ['MAGIC', 'AXS', 'GALA', 'SAND', 'MANA']):
                est_nome = 'gaming'
            
            # 📊 SWING RWA - Old School Alts para swing trading
            else:  # ADA, XRP, DOT, LINK, LTC, ZEC
                est_nome = 'swing_rwa'

            # 2. Contexto de Dados
            if symbol not in self.historico_df:
                await self.atualizar_historico(symbol)
            
            df = self.historico_df[symbol]
            df.loc[df.index[-1], 'close'] = preco_atual 
            df = self.calculate_indicators(df)
            last = df.iloc[-1]

            # DEBUG: Mostra indicadores a cada tick
            rsi = last.get('rsi', 50)
            ema5 = last.get('ema5', 0)
            ema20 = last.get('ema20', 0)
            logger.debug(f"🔍 {symbol} | Preço: ${preco_atual:.4f} | RSI: {rsi:.2f} | EMA5: {ema5:.4f} | EMA20: {ema20:.4f}")
            # 3. Predição Antecipada da IA (Para checar Prioridade)
            feat = {
                'close': preco_atual, 
                'rsi': rsi, 
                'ema20': ema20,
                'price_above_ema': 1 if preco_atual > ema20 else 0
            }
            
            res_ia = self.ia.predict(feat, symbol=symbol)
            confianca_ia = res_ia.get('confianca', 0)
            sinal_ia = res_ia.get('sinal', 'HOLD')

            # Log SEMPRE para diagnosticar (não apenas debug)
            logger.info(f"⚡ IA {symbol}: Sinal={sinal_ia} | Conf={confianca_ia:.2%} | RSI={rsi:.1f} | P={preco_atual:.4f}")

            # 4. Lógica de Gatilho (Técnico vs Prioridade IA)
            # 🎯 LIMITE ADAPTATIVO DINÂMICO - Ajusta conforme lucro do dia
            # Se lucro diário > $15 (metade da meta), fica mais exigente (75%)
            # Se lucro < $15, mantém agressivo (50% ou config)
            try:
                from datetime import datetime
                hoje_str = datetime.now().strftime('%Y-%m-%d')
                
                # Usa self.executor.gestor se disponível (dados atualizados em tempo real)
                if self.executor and hasattr(self.executor, 'gestor'):
                    dia_atual = self.executor.gestor.dados.get('dias', {}).get(hoje_str, {})
                    lucro_hoje = dia_atual.get('lucro_do_dia', 0.0)
                else:
                    # Fallback: carrega do arquivo
                    from bots.gestor_financeiro import GestorFinanceiro
                    gestor = GestorFinanceiro()
                    dia_atual = gestor.dados.get('dias', {}).get(hoje_str, {})
                    lucro_hoje = dia_atual.get('lucro_do_dia', 0.0)
                
                # Ajuste de limite conforme performance do dia - MAIS AGRESSIVO
                # Limite base reduzido: 50% para comprar, 60% se lucro > $15
                base_limit = 0.55 if est_nome == 'meme_sniper' else 0.50  # Reduzido de 65%/60%
                limite_gatilho = 0.60 if lucro_hoje > 15.0 else self.config.get('confianca_minima', base_limit)
                logger.debug(f"🎯 [LIMITE ADAPTATIVO] Data: {hoje_str} | Lucro Hoje: ${lucro_hoje:.2f} | Limite: {limite_gatilho:.0%} | Est: {est_nome}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao calcular limite adaptativo: {e}")
                limite_gatilho = self.config.get('confianca_minima', 0.50)  # Fallback 50% - MAIS AGRESSIVO
            
            # --- LÓGICA SIMPLIFICADA: CONFIANÇA NA IA ---
            # Se IA aprovareom com confiança >= 50% (ou 60% se muito lucro hoje), COMPRA!
            # Não precisa mais de "gatilho técnico" separado
            
            # 🔍 DEBUG CRÍTICO: Verificar decisão
            logger.info(f"🔍 DEBUG {symbol}: sinal_ia={sinal_ia} | confianca={confianca_ia:.2%} | limite={limite_gatilho:.2%}")
            
            # Decisão: IA diz BUY e confiança >= limite?
            if sinal_ia == "BUY" and confianca_ia >= limite_gatilho:
                logger.info(f"🎯 SINAL GERADO: {symbol} | IA: {confianca_ia:.2%} | Limite: {limite_gatilho:.0%}")
                
                # Retorna dados para o SniperMonitor executar
                return {
                    "decisao": "COMPRAR", 
                    "confianca": confianca_ia,
                    "estrategia": est_nome,
                    "preco": preco_atual
                }
            else:
                # Log de debug para entender por que não comprou
                if sinal_ia != "BUY":
                    logger.debug(f"⏸️ {symbol}: IA não recomenda compra (sinal={sinal_ia})")
                elif confianca_ia < limite_gatilho:
                    logger.debug(f"⏸️ {symbol}: Confiança baixa ({confianca_ia:.2%} < {limite_gatilho:.2%})")

            return {"decisao": "AGUARDAR", "confianca": confianca_ia}

        except Exception as e:
            logger.error(f"Erro no Analista para {symbol}: {e}")
            return {"decisao": "ERRO", "confianca": 0}