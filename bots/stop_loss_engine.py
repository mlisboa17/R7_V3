"""
🎯 STOP LOSS INTELIGENTE V2 - Sistema Híbrido com Valores em Dólares e Previsões
Implementa múltiplos tipos de stop loss:
1. Percentual dinâmico (atual)
2. Valor fixo em dólares 
3. Stop loss baseado em tempo + previsão
4. Stop loss adaptativo por volatilidade
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger('stop_loss_engine')

class StopLossEngine:
    """Sistema avançado de stop loss com múltiplas estratégias"""
    
    def __init__(self):
        # Configurações de stop loss por categoria
        self.config_sl = {
            'MEME': {
                'percentual_max': -3.5,      # -3.5% máximo para memes
                'valor_dolar_max': 15.0,     # $15 de perda máxima
                'tempo_max_horas': 24,       # 24h máximo sem lucro
                'volatilidade_factor': 1.5   # Mais flexível
            },
            'BLUE_CHIP': {
                'percentual_max': -6.0,      # -6.0% máximo para blue chips (aumentado para ADA - sofre mais volatilidade)
                'valor_dolar_max': 50.0,     # $50 de perda máxima
                'tempo_max_horas': 72,       # 72h máximo
                'volatilidade_factor': 0.8   # Mais rígido
            },
            'DEFI': {
                'percentual_max': -2.5,      # -2.5% máximo
                'valor_dolar_max': 20.0,     # $20 de perda máxima
                'tempo_max_horas': 36,       # 36h máximo
                'volatilidade_factor': 1.0   # Normal
            },
            'LAYER2': {
                'percentual_max': -2.0,      # -2.0% máximo
                'valor_dolar_max': 18.0,     # $18 de perda máxima
                'tempo_max_horas': 30,       # 30h máximo
                'volatilidade_factor': 1.1   # Pouco flexível
            }
        }
    
    def calcular_categoria(self, symbol: str) -> str:
        """Determina categoria da moeda para aplicar stop loss específico"""
        if not symbol:
            return 'DEFI'
            
        # Moedas MEME
        meme_coins = ['PEPE', 'DOGE', 'SHIB', 'WIF', 'BONK', 'FLOKI']
        if any(meme in symbol.upper() for meme in meme_coins):
            return 'MEME'
            
        # Blue Chips
        blue_chips = ['BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'XRP']
        if any(blue in symbol.upper() for blue in blue_chips):
            return 'BLUE_CHIP'
            
        # Layer 2
        layer2_coins = ['ARB', 'POL', 'MATIC', 'OP', 'METIS']
        if any(l2 in symbol.upper() for l2 in layer2_coins):
            return 'LAYER2'
            
        return 'DEFI'  # Default
    
    def calcular_stop_loss_hibrido(
        self, 
        symbol: str, 
        preco_entrada: float,
        quantidade: float,
        entry_time: datetime,
        previsao_tempo: Optional[int] = None  # horas até meta realista
    ) -> Dict[str, Any]:
        """
        Calcula stop loss híbrido considerando múltiplos fatores:
        1. Percentual por categoria
        2. Valor máximo em dólares
        3. Tempo baseado em previsão
        """
        categoria = self.calcular_categoria(symbol)
        config = self.config_sl[categoria]
        valor_posicao = preco_entrada * quantidade
        
        # 1. STOP LOSS PERCENTUAL (padrão atual)
        sl_percentual = preco_entrada * (1 + config['percentual_max'] / 100)
        perda_percentual = abs(config['percentual_max'])
        
        # 2. STOP LOSS POR VALOR EM DÓLARES
        perda_maxima_usd = min(config['valor_dolar_max'], valor_posicao * 0.15)  # Max 15% da posição
        sl_valor_dolar = preco_entrada - (perda_maxima_usd / quantidade)
        
        # 3. STOP LOSS POR TEMPO + PREVISÃO
        tempo_decorrido = (datetime.now() - entry_time).total_seconds() / 3600  # horas
        tempo_limite = config['tempo_max_horas']
        
        # Se há previsão, usa ela como base
        if previsao_tempo:
            # Permite 50% do tempo extra além da previsão
            tempo_limite = min(previsao_tempo * 1.5, config['tempo_max_horas'])
        
        tempo_esgotado = tempo_decorrido >= tempo_limite
        
        # 4. ESCOLHA DO STOP LOSS MAIS RESTRITIVO (PROTEÇÃO MÁXIMA)
        # Usa o stop loss que dá MENOR perda
        sl_final = max(sl_percentual, sl_valor_dolar)
        
        # Determina qual critério foi usado
        if sl_final == sl_percentual:
            criterio = f"percentual (-{perda_percentual:.1f}%)"
        else:
            criterio = f"valor ($-{perda_maxima_usd:.2f})"
        
        resultado = {
            'sl_price': sl_final,
            'sl_percentual': sl_percentual,
            'sl_valor_dolar': sl_valor_dolar,
            'criterio_usado': criterio,
            'categoria': categoria,
            'tempo_decorrido_horas': tempo_decorrido,
            'tempo_limite_horas': tempo_limite,
            'tempo_esgotado': tempo_esgotado,
            'perda_maxima_usd': perda_maxima_usd,
            'valor_posicao': valor_posicao,
            'deve_sair_por_tempo': tempo_esgotado
        }
        
        return resultado
    
    def should_exit_by_time_prediction(
        self, 
        symbol: str, 
        entry_time: datetime,
        previsao_realista_horas: Optional[float] = None,
        preco_atual: float = None,
        preco_entrada: float = None
    ) -> Tuple[bool, str]:
        """
        Verifica se deve sair por tempo + previsão:
        - Se passou do tempo previsto e está no prejuízo = SAIR
        - Se passou 2x o tempo previsto = SAIR sempre
        """
        if not previsao_realista_horas:
            return False, ""
        
        tempo_decorrido = (datetime.now() - entry_time).total_seconds() / 3600
        
        # Passou do tempo previsto?
        if tempo_decorrido > previsao_realista_horas:
            # Se está no prejuízo, sai imediatamente
            if preco_atual and preco_entrada and preco_atual < preco_entrada:
                return True, f"Tempo previsto esgotado ({previsao_realista_horas:.1f}h) + prejuízo"
            
            # Se passou 2x o tempo e ainda não bateu meta, sai
            if tempo_decorrido > (previsao_realista_horas * 2):
                return True, f"Tempo excedeu 2x a previsão ({previsao_realista_horas * 2:.1f}h)"
        
        return False, ""
    
    def get_stop_loss_description(self, sl_info: Dict[str, Any]) -> str:
        """Retorna descrição amigável do stop loss"""
        categoria = sl_info['categoria']
        criterio = sl_info['criterio_usado']
        
        desc = f"🛡️ Stop Loss {categoria}: {criterio}"
        
        if sl_info['deve_sair_por_tempo']:
            desc += f" + ⏰ Tempo esgotado ({sl_info['tempo_decorrido_horas']:.1f}h)"
        
        return desc