"""
Sistema de Classificação de Ativos e Metas Dinâmicas
Baseado em análise profissional de mercado
"""

class AssetClassifier:
    """Classifica criptomoedas por categoria e volatilidade"""
    
    CATEGORIES = {
        'LARGE_CAP': {
            'assets': ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'XRP', 'DOT', 'AVAX'],
            'tp_min': 0.02,      # 2%
            'tp_ideal': 0.035,   # 3.5%
            'trailing_pct': 0.015,   # 1.5%
            'max_days': 7,
            'volatility': 'LOW'
        },
        'MEME': {
            'assets': ['DOGE', 'PEPE', 'SHIB', 'WIF', 'BONK', 'FLOKI'],
            'tp_min': 0.05,      # 5%
            'tp_ideal': 0.15,    # 15%
            'trailing_pct': 0.05,    # 5%
            'max_days': 2,
            'volatility': 'EXTREME'
        },
        'DEFI': {
            'assets': ['LINK', 'UNI', 'AAVE', 'CRV', 'SUSHI', 'CAKE'],
            'tp_min': 0.03,      # 3%
            'tp_ideal': 0.06,    # 6%
            'trailing_pct': 0.02,    # 2%
            'max_days': 5,
            'volatility': 'MEDIUM'
        },
        'LAYER2': {
            'assets': ['ARB', 'POL', 'MATIC', 'OP', 'IMX'],
            'tp_min': 0.025,     # 2.5%
            'tp_ideal': 0.05,    # 5%
            'trailing_pct': 0.02,    # 2%
            'max_days': 5,
            'volatility': 'MEDIUM'
        },
        'GAMING': {
            'assets': ['MAGIC', 'AXS', 'GALA', 'SAND', 'MANA'],
            'tp_min': 0.04,      # 4%
            'tp_ideal': 0.10,    # 10%
            'trailing_pct': 0.03,    # 3%
            'max_days': 3,
            'volatility': 'HIGH'
        },
        'AI': {
            'assets': ['FET', 'RENDER', 'AGIX', 'OCEAN'],
            'tp_min': 0.035,     # 3.5%
            'tp_ideal': 0.08,    # 8%
            'trailing_pct': 0.025,   # 2.5%
            'max_days': 4,
            'volatility': 'HIGH'
        }
    }
    
    @classmethod
    def classify(cls, symbol: str) -> dict:
        """
        Classifica um ativo e retorna suas configurações.
        
        Args:
            symbol: Par de trading (ex: "BTCUSDT", "PEPEUSDT")
            
        Returns:
            dict com configurações da categoria
        """
        # Remove USDT do símbolo
        asset = symbol.replace('USDT', '').replace('BUSD', '')
        
        # Mapeamento de símbolos alternativos
        symbol_map = {
            'MATIC': 'POL',
            'RNDR': 'RENDER'
        }
        asset = symbol_map.get(asset, asset)
        
        # Busca em qual categoria está
        for category_name, config in cls.CATEGORIES.items():
            if asset in config['assets']:
                return {
                    'category': category_name,
                    'asset': asset,
                    **config
                }
        
        # Default: Trata como DEFI (média volatilidade)
        return {
            'category': 'DEFI',
            'asset': asset,
            **cls.CATEGORIES['DEFI']
        }
    
    @classmethod
    def get_exit_strategy(cls, symbol: str, lucro_pct: float, dias_posicao: float) -> dict:
        """
        Retorna estratégia de saída baseada em categoria e tempo.
        
        Args:
            symbol: Par de trading
            lucro_pct: Lucro atual em decimal (0.05 = 5%)
            dias_posicao: Dias desde a entrada
            
        Returns:
            dict com ação recomendada
        """
        config = cls.classify(symbol)
        
        # Ajuste de meta por tempo (decaimento temporal)
        if dias_posicao > config['max_days']:
            # Passou do tempo máximo: aceita 60% da meta mínima
            meta_ajustada = config['tp_min'] * 0.6
        elif dias_posicao > config['max_days'] * 0.7:
            # 70% do tempo: aceita 80% da meta
            meta_ajustada = config['tp_min'] * 0.8
        else:
            # Dentro do prazo: meta normal
            meta_ajustada = config['tp_min']
        
        # Decisão de saída
        if lucro_pct >= config['tp_ideal']:
            return {
                'action': 'SELL_75PCT',
                'reason': f"TP_IDEAL_{config['tp_ideal']*100:.1f}%",
                'trailing': config['trailing_pct'],
                'category': config['category']
            }
        elif lucro_pct >= meta_ajustada:
            return {
                'action': 'SELL_PARTIAL',
                'reason': f"TP_MIN_{meta_ajustada*100:.1f}%",
                'trailing': config['trailing_pct'],
                'category': config['category']
            }
        elif lucro_pct >= meta_ajustada * 0.7:
            return {
                'action': 'TRAILING_ACTIVE',
                'reason': 'APPROACHING_TARGET',
                'trailing': config['trailing_pct'],
                'category': config['category']
            }
        else:
            return {
                'action': 'HOLD',
                'reason': 'BELOW_TARGET',
                'trailing': config['trailing_pct'],
                'category': config['category']
            }


class ScaledExit:
    """Gerencia vendas escalonadas em múltiplas parcelas"""
    
    def __init__(self):
        self.partial_sales = {}  # {symbol: {'sold_25pct': False, 'sold_50pct': False, ...}}
    
    def reset_position(self, symbol: str):
        """Reseta rastreamento de vendas parciais"""
        if symbol in self.partial_sales:
            del self.partial_sales[symbol]
    
    def get_sell_percentage(self, symbol: str, lucro_pct: float, config: dict) -> float:
        """
        Calcula quanto vender baseado em lucro e vendas anteriores.
        
        Returns:
            float: Percentual da posição a vender (0.0 a 1.0)
        """
        if symbol not in self.partial_sales:
            self.partial_sales[symbol] = {
                'sold_25pct': False,
                'sold_50pct': False,
                'sold_75pct': False
            }
        
        sales = self.partial_sales[symbol]
        
        # Venda escalonada
        if lucro_pct >= config['tp_ideal'] and not sales['sold_75pct']:
            # Terceira venda: mais 25% (total 75% vendido)
            sales['sold_75pct'] = True
            return 0.25 / (1.0 if not sales['sold_25pct'] else 0.75 if not sales['sold_50pct'] else 0.5)
        
        elif lucro_pct >= config['tp_ideal'] * 0.7 and not sales['sold_50pct']:
            # Segunda venda: mais 25% (total 50% vendido)
            sales['sold_50pct'] = True
            return 0.25 / (1.0 if not sales['sold_25pct'] else 0.75)
        
        elif lucro_pct >= config['tp_min'] and not sales['sold_25pct']:
            # Primeira venda: 25% da posição
            sales['sold_25pct'] = True
            return 0.25
        
        return 0.0  # Não vende
    
    def should_sell_remaining(self, symbol: str, motivo: str) -> bool:
        """Verifica se deve vender o restante (stop loss, exaustão, etc)"""
        if symbol not in self.partial_sales:
            return True  # Vende 100% se nunca vendeu parcial
        
        # Se já vendeu parcialmente, vende o que restou
        sales = self.partial_sales[symbol]
        if sales['sold_75pct']:
            return True  # Vende os 25% restantes
        elif sales['sold_50pct']:
            return True  # Vende os 50% restantes
        elif sales['sold_25pct']:
            return True  # Vende os 75% restantes
        return True
