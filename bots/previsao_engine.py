"""
🎯 PREVISÃO ENGINE - Sistema de Previsão Inteligente de Saída
Calcula 3 cenários (Conservador, Realista, Otimista) baseado em:
- Categoria do ativo (volatilidade esperada)
- Volume atual vs médio
- Horário de trading (Asia/Europa/US)
- Volatilidade histórica das últimas 24h
"""

import logging
import asyncio
from datetime import datetime, timedelta
import numpy as np
from bots.asset_classifier import AssetClassifier

logger = logging.getLogger('previsao')

class PrevisaoEngine:
    """Calcula previsões de preço e tempo para saída de posições"""
    
    # Velocidade média por categoria (% de lucro por hora)
    VELOCIDADE_BASE = {
        'LARGE_CAP': 0.4,   # 0.4% por hora (lento e estável)
        'MEME': 5.0,        # 5% por hora (explosivo)
        'DEFI': 1.2,        # 1.2% por hora
        'LAYER2': 1.0,      # 1% por hora
        'GAMING': 2.0,      # 2% por hora
        'AI': 1.5           # 1.5% por hora
    }
    
    # Multiplicadores por horário (UTC)
    HORARIO_MULTIPLIER = {
        'asia': (0, 8),      # 00:00-08:00 UTC - Mais lento (0.8x)
        'europa': (8, 16),   # 08:00-16:00 UTC - Normal (1.0x)
        'us': (16, 24)       # 16:00-00:00 UTC - Mais rápido (1.3x)
    }
    
    def __init__(self, client=None):
        self.client = client
        self.classifier = AssetClassifier()
    
    def get_horario_multiplier(self):
        """Retorna multiplicador baseado no horário atual"""
        hora_utc = datetime.utcnow().hour
        
        if 0 <= hora_utc < 8:
            return 0.8  # Asia - mais lento
        elif 8 <= hora_utc < 16:
            return 1.0  # Europa - normal
        else:
            return 1.3  # US - mais rápido
    
    async def calcular_volatilidade_24h(self, symbol):
        """
        Calcula volatilidade real das últimas 24h (desvio padrão dos retornos)
        Retorna % de movimento médio por hora
        """
        if not self.client:
            # Fallback: usa volatilidade estimada da categoria
            config = self.classifier.classify(symbol)
            return config.get('volatility', 'medium')
        
        try:
            # Busca klines de 1h das últimas 24h
            klines = await self.client.get_klines(symbol=symbol, interval='1h', limit=24)
            
            # Calcula retornos horários
            closes = [float(k[4]) for k in klines]  # índice 4 = close
            retornos = []
            for i in range(1, len(closes)):
                ret = (closes[i] / closes[i-1]) - 1
                retornos.append(abs(ret) * 100)  # Em percentual
            
            if not retornos:
                return 2.0  # Default
            
            # Volatilidade = movimento médio por hora
            vol_media = np.mean(retornos)
            return vol_media
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao calcular volatilidade de {symbol}: {e}")
            return 2.0  # Default seguro
    
    async def calcular_volume_ratio(self, symbol):
        """
        Calcula ratio do volume atual vs volume médio 24h
        > 1.5 = volume alto (movimento mais rápido)
        < 0.8 = volume baixo (movimento mais lento)
        """
        if not self.client:
            return 1.0  # Neutro
        
        try:
            ticker_24h = await self.client.get_ticker(symbol=symbol)
            volume_atual = float(ticker_24h['quoteVolume'])
            
            # Busca volume médio das últimas 24h
            klines = await self.client.get_klines(symbol=symbol, interval='1h', limit=24)
            volumes = [float(k[7]) for k in klines]  # índice 7 = quote asset volume
            volume_medio = np.mean(volumes) if volumes else volume_atual
            
            ratio = volume_atual / volume_medio if volume_medio > 0 else 1.0
            return min(ratio, 3.0)  # Cap em 3x para evitar outliers
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao calcular volume ratio de {symbol}: {e}")
            return 1.0
    
    async def gerar_previsao(self, symbol, entry_price, entry_time=None):
        """
        🎯 GERADOR PRINCIPAL DE PREVISÕES
        Retorna 3 cenários com preço, tempo estimado e probabilidade
        """
        if entry_time is None:
            entry_time = datetime.now()
        
        # 1. Classifica ativo e pega metas
        config = self.classifier.classify(symbol)
        categoria = config['category']
        tp_min = config['tp_min'] * 100  # Converte para %
        tp_ideal = config['tp_ideal'] * 100
        
        # 2. Calcula fatores de ajuste
        volatilidade_24h = await self.calcular_volatilidade_24h(symbol)
        volume_ratio = await self.calcular_volume_ratio(symbol)
        horario_mult = self.get_horario_multiplier()
        
        # 3. Velocidade ajustada (% por hora)
        velocidade_base = self.VELOCIDADE_BASE.get(categoria, 1.0)
        velocidade_ajustada = velocidade_base * horario_mult * volume_ratio
        
        # Aplica fator de volatilidade (alta vol = mais rápido)
        if volatilidade_24h > 3.0:
            velocidade_ajustada *= 1.3
        elif volatilidade_24h < 1.0:
            velocidade_ajustada *= 0.7
        
        logger.info(f"📊 {symbol} [{categoria}] | Vol: {volatilidade_24h:.2f}% | VolRatio: {volume_ratio:.2f}x | Horário: {horario_mult}x | Vel: {velocidade_ajustada:.2f}%/h")
        
        # 4. Calcula 3 cenários
        cenarios = {}
        
        # CONSERVADOR: TP mínimo da categoria
        pct_conservador = tp_min
        eta_conservador = pct_conservador / velocidade_ajustada if velocidade_ajustada > 0 else 24
        cenarios['conservador'] = {
            'preco_alvo': entry_price * (1 + pct_conservador/100),
            'lucro_pct': pct_conservador,
            'eta_horas': round(eta_conservador, 1),
            'eta_timestamp': (entry_time + timedelta(hours=eta_conservador)).isoformat(),
            'probabilidade': 85  # Alta chance de atingir mínimo
        }
        
        # REALISTA: TP ideal da categoria
        pct_realista = tp_ideal
        eta_realista = pct_realista / velocidade_ajustada if velocidade_ajustada > 0 else 48
        cenarios['realista'] = {
            'preco_alvo': entry_price * (1 + pct_realista/100),
            'lucro_pct': pct_realista,
            'eta_horas': round(eta_realista, 1),
            'eta_timestamp': (entry_time + timedelta(hours=eta_realista)).isoformat(),
            'probabilidade': 60  # Chance média
        }
        
        # OTIMISTA: 2x TP ideal (para memes) ou 1.5x (outros)
        multiplicador_otimista = 2.0 if categoria == 'MEME' else 1.5
        pct_otimista = tp_ideal * multiplicador_otimista
        eta_otimista = pct_otimista / (velocidade_ajustada * 1.5) if velocidade_ajustada > 0 else 72
        cenarios['otimista'] = {
            'preco_alvo': entry_price * (1 + pct_otimista/100),
            'lucro_pct': pct_otimista,
            'eta_horas': round(eta_otimista, 1),
            'eta_timestamp': (entry_time + timedelta(hours=eta_otimista)).isoformat(),
            'probabilidade': 30 if categoria in ['MEME', 'GAMING'] else 15  # Baixa chance
        }
        
        # 5. Monta previsão completa
        previsao = {
            'symbol': symbol,
            'categoria': categoria,
            'entry_price': entry_price,
            'entry_time': entry_time.isoformat(),
            'timestamp_previsao': datetime.now().isoformat(),
            'cenarios': cenarios,
            'fatores': {
                'volatilidade_24h': round(volatilidade_24h, 2),
                'volume_ratio': round(volume_ratio, 2),
                'horario_mult': horario_mult,
                'velocidade_ajustada': round(velocidade_ajustada, 2)
            }
        }
        
        # Log resumido
        logger.info(f"🎯 PREVISÃO GERADA: {symbol}")
        logger.info(f"   🔵 Conservador: {cenarios['conservador']['lucro_pct']:.1f}% em {cenarios['conservador']['eta_horas']:.1f}h ({cenarios['conservador']['probabilidade']}%)")
        logger.info(f"   🟡 Realista: {cenarios['realista']['lucro_pct']:.1f}% em {cenarios['realista']['eta_horas']:.1f}h ({cenarios['realista']['probabilidade']}%)")
        logger.info(f"   🟢 Otimista: {cenarios['otimista']['lucro_pct']:.1f}% em {cenarios['otimista']['eta_horas']:.1f}h ({cenarios['otimista']['probabilidade']}%)")
        
        return previsao
    
    def atualizar_divergencia(self, previsao_original, preco_atual):
        """
        Calcula divergência entre previsão e realidade
        Retorna status: ACIMA_PREVISTO, DENTRO_PREVISTO, ABAIXO_PREVISTO
        """
        entry_price = previsao_original['entry_price']
        lucro_atual = ((preco_atual / entry_price) - 1) * 100
        
        # Verifica qual cenário está mais próximo
        cenarios = previsao_original['cenarios']
        conservador_target = cenarios['conservador']['lucro_pct']
        realista_target = cenarios['realista']['lucro_pct']
        otimista_target = cenarios['otimista']['lucro_pct']
        
        # Calcula tempo decorrido
        entry_time = datetime.fromisoformat(previsao_original['entry_time'])
        tempo_decorrido = (datetime.now() - entry_time).total_seconds() / 3600  # horas
        
        # Determina status
        if lucro_atual >= realista_target:
            status = "ACIMA_PREVISTO"
            cenario_atual = "otimista"
        elif lucro_atual >= conservador_target:
            status = "DENTRO_PREVISTO"
            cenario_atual = "realista"
        elif lucro_atual > 0:
            status = "DENTRO_PREVISTO"
            cenario_atual = "conservador"
        else:
            status = "ABAIXO_PREVISTO"
            cenario_atual = "nenhum"
        
        # Calcula divergência temporal (esperado vs real)
        # Proteções: evita divisão por valores muito pequenos (tempo muito curto
        # ou velocidade prevista quase zero) que geram outliers enormes.
        epsilon_hours = 1.0 / 60.0  # mínimo 1 minuto em horas
        tempo_util = tempo_decorrido if tempo_decorrido >= epsilon_hours else epsilon_hours

        velocidade_real = lucro_atual / tempo_util

        velocidade_prevista = float(previsao_original['fatores'].get('velocidade_ajustada', 0) or 0)
        # Define um mínimo para velocidade prevista (0.01%/h) para evitar divisões por zero
        min_vel_prevista = 0.01
        vel_prev_util = velocidade_prevista if velocidade_prevista >= min_vel_prevista else min_vel_prevista

        divergencia_velocidade = ((velocidade_real / vel_prev_util) - 1) * 100
        # Corta outliers extremos para manter relatórios legíveis
        max_divergencia = 10000.0
        if divergencia_velocidade > max_divergencia:
            divergencia_velocidade = max_divergencia
        elif divergencia_velocidade < -max_divergencia:
            divergencia_velocidade = -max_divergencia
        
        return {
            'preco_atual': preco_atual,
            'lucro_atual_pct': round(lucro_atual, 2),
            'tempo_decorrido_horas': round(tempo_decorrido, 2),
            'status': status,
            'cenario_atual': cenario_atual,
            'divergencia_velocidade_pct': round(divergencia_velocidade, 1),
            'velocidade_real': round(velocidade_real, 2),
            'timestamp': datetime.now().isoformat()
        }
