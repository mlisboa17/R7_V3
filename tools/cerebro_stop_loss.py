"""
🧠 DECISOR DE STOP LOSS INTELIGENTE
Decide entre VENDER no stop loss ou RENOVAR posição (aguardar reversão)
"""
import joblib
import os
import logging
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger('cerebro_stop_loss')

class CerebroStopLoss:
    """
    🧠 Cérebro de Decisão para Stop Loss
    Carrega modelo treinado e decide se deve vender ou aguardar reversão
    """
    
    def __init__(self, model_path='models/cerebro_r7_v3.pkl'):
        self.model_path = model_path
        self.modelo = None
        self.carregar_modelo()
    
    def carregar_modelo(self):
        """Carrega o modelo treinado"""
        try:
            if os.path.exists(self.model_path):
                self.modelo = joblib.load(self.model_path)
                logger.info(f"🧠 Cérebro Stop Loss carregado: {self.model_path}")
            else:
                logger.warning(f"⚠️ Modelo não encontrado: {self.model_path}")
                self.modelo = None
        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo: {e}")
            self.modelo = None
    
    def calcular_features(self, symbol, preco_atual, buffer_precos, volume_atual=None):
        """
        Calcula features necessárias para o modelo
        
        Args:
            symbol: Par de trading (ex: BTCUSDT)
            preco_atual: Preço atual do ativo
            buffer_precos: Lista de preços históricos recentes
            volume_atual: Volume atual (opcional)
        
        Returns:
            dict com features calculadas ou None se houver erro
        """
        try:
            if len(buffer_precos) < 20:
                logger.warning(f"⚠️ Buffer insuficiente para {symbol}: {len(buffer_precos)} velas")
                return None
            
            # Converte para DataFrame
            df = pd.DataFrame(list(buffer_precos), columns=['close'])
            df['close'] = df['close'].astype(float)
            
            # Calcula indicadores técnicos
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema20'] = ta.ema(df['close'], length=20)
            df['atr'] = ta.atr(df['high'] if 'high' in df else df['close'], 
                              df['low'] if 'low' in df else df['close'], 
                              df['close'], length=14)
            
            # Última linha (valores atuais)
            last = df.iloc[-1]
            
            # Features esperadas pelo modelo: [rsi, ema20, atr_pct, rel_vol]
            features = {
                'rsi': last['rsi'] if not pd.isna(last['rsi']) else 50.0,
                'ema20': last['ema20'] if not pd.isna(last['ema20']) else preco_atual,
                'atr_pct': (last['atr'] / preco_atual * 100) if not pd.isna(last['atr']) and preco_atual > 0 else 1.0,
                'rel_vol': volume_atual / df['close'].mean() if volume_atual else 1.0
            }
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular features para {symbol}: {e}")
            return None
    
    def decidir_venda_ou_renovacao(self, symbol, preco_atual, preco_entrada, buffer_precos, 
                                    tempo_posicao_horas=0, volume_atual=None):
        """
        🎯 DECISÃO INTELIGENTE: Vender ou Renovar?
        
        Args:
            symbol: Par de trading
            preco_atual: Preço atual
            preco_entrada: Preço de entrada da posição
            buffer_precos: Histórico de preços
            tempo_posicao_horas: Há quanto tempo está na posição
            volume_atual: Volume atual
        
        Returns:
            dict com decisão e informações
        """
        try:
            # Se modelo não está carregado, vende por segurança
            if self.modelo is None:
                return {
                    'decisao': 'VENDER',
                    'motivo': 'modelo_nao_disponivel',
                    'confianca': 0.0,
                    'features': None
                }
            
            # Calcula features
            features = self.calcular_features(symbol, preco_atual, buffer_precos, volume_atual)
            
            if features is None:
                return {
                    'decisao': 'VENDER',
                    'motivo': 'features_invalidas',
                    'confianca': 0.0,
                    'features': None
                }
            
            # Prepara dados para predição (ordem: rsi, ema20, atr_pct, rel_vol)
            dados_modelo = [[
                features['rsi'],
                features['ema20'],
                features['atr_pct'],
                features['rel_vol']
            ]]
            
            # 🧠 PREDIÇÃO
            previsao = self.modelo.predict(dados_modelo)[0]
            
            # Tenta obter probabilidade (se modelo suportar)
            try:
                proba = self.modelo.predict_proba(dados_modelo)[0]
                confianca = max(proba)  # Confiança na predição
            except:
                confianca = 0.75  # Confiança padrão se não tiver predict_proba
            
            # 📊 ANÁLISE ADICIONAL
            perda_atual = ((preco_atual - preco_entrada) / preco_entrada) * 100
            rsi = features['rsi']
            
            # LÓGICA DE DECISÃO
            if previsao == 1:
                # Modelo prevê ALTA (reversão)
                
                # Regras de segurança
                if perda_atual < -5.0 and tempo_posicao_horas > 24:
                    # Perda muito grande e muito tempo na posição -> VENDA por segurança
                    decisao = 'VENDER'
                    motivo = 'perda_excessiva_tempo_longo'
                elif rsi < 25 and confianca > 0.60:
                    # RSI muito baixo + alta confiança -> RENOVAR (provável reversão)
                    decisao = 'RENOVAR'
                    motivo = 'reversao_provavel_rsi_baixo'
                elif rsi < 35 and confianca > 0.70:
                    # RSI baixo + confiança alta -> RENOVAR
                    decisao = 'RENOVAR'
                    motivo = 'modelo_previu_alta'
                else:
                    # Confiança moderada -> RENOVAR com cautela
                    decisao = 'RENOVAR'
                    motivo = 'modelo_previu_alta_confianca_moderada'
            else:
                # Modelo prevê QUEDA (continuar caindo)
                decisao = 'VENDER'
                motivo = 'modelo_confirmou_queda'
            
            # Log da decisão
            logger.info(f"🧠 {symbol} | Decisão: {decisao}")
            logger.info(f"   📊 RSI: {rsi:.1f} | Perda: {perda_atual:.2f}% | Confiança: {confianca:.1%}")
            logger.info(f"   💡 Motivo: {motivo}")
            
            return {
                'decisao': decisao,
                'motivo': motivo,
                'confianca': confianca,
                'features': features,
                'previsao_modelo': int(previsao),
                'perda_atual': perda_atual
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na decisão para {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Em caso de erro, vende por segurança
            return {
                'decisao': 'VENDER',
                'motivo': f'erro_decisao: {str(e)}',
                'confianca': 0.0,
                'features': None
            }
    
    def analise_rapida(self, rsi, ema20_vs_preco, atr_pct, rel_vol):
        """
        Análise rápida quando já tem as features calculadas
        
        Args:
            rsi: RSI atual (0-100)
            ema20_vs_preco: EMA20 dividido pelo preço atual
            atr_pct: ATR em percentual do preço
            rel_vol: Volume relativo (volume_atual / média)
        
        Returns:
            'RENOVAR' ou 'VENDER'
        """
        if self.modelo is None:
            return 'VENDER'
        
        try:
            dados = [[rsi, ema20_vs_preco, atr_pct, rel_vol]]
            previsao = self.modelo.predict(dados)[0]
            
            return 'RENOVAR' if previsao == 1 else 'VENDER'
        except Exception as e:
            logger.error(f"Erro na análise rápida: {e}")
            return 'VENDER'


# 🎯 FUNÇÃO HELPER PARA USO RÁPIDO
def consultar_cerebro(symbol, preco_atual, preco_entrada, buffer_precos, tempo_horas=0):
    """
    Função helper para consulta rápida do cérebro
    
    Returns:
        'RENOVAR' ou 'VENDER'
    """
    cerebro = CerebroStopLoss()
    resultado = cerebro.decidir_venda_ou_renovacao(
        symbol, preco_atual, preco_entrada, buffer_precos, tempo_horas
    )
    return resultado['decisao']
