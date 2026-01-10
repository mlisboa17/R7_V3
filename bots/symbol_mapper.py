"""
🗺️ MAPEADOR DE SÍMBOLOS - Resolve problemas de símbolos inválidos
Converte ativos da carteira para símbolos corretos da Binance
Atualizado automaticamente com dados da exchange
"""

import logging
from binance import AsyncClient

logger = logging.getLogger('symbol_mapper')

class SymbolMapper:
    """Mapeia símbolos de ativos para pares válidos da Binance"""
    
    # Mapeamento manual de casos conhecidos
    MANUAL_MAPPING = {
        # Casos especiais
        'MATIC': 'POLUSDT',      # Polygon mudou de MATIC para POL
        'RNDR': 'RENDERUSDT',    # Render token
        'BETH': 'ETHUSDT',       # Binance Staked ETH
        'WBETH': 'ETHUSDT',      # Wrapped Beacon ETH
        
        # Staking tokens (mapeiam para o ativo original)
        'LDBNB': 'BNBUSDT',
        'LDBTC': 'BTCUSDT',
        'LDETH': 'ETHUSDT',
        'LDMATIC': 'POLUSDT',
        'LDSOL': 'SOLUSDT',
        
        # Wrapped tokens
        'WBTC': 'BTCUSDT',
        'WETH': 'ETHUSDT',
        'WBNB': 'BNBUSDT',
        
        # Outros casos
        'BUSD': 'USDTUSDT',  # BUSD foi descontinuado
        'TUSD': 'USDTUSDT',
        'USDC': 'USDCUSDT',
        'DAI': 'DAIUSDT',
    }
    
    # Cache de símbolos válidos da Binance
    _valid_symbols_cache = None
    
    @classmethod
    async def initialize(cls, client: AsyncClient):
        """
        Inicializa o mapeador carregando todos os símbolos válidos da Binance
        Deve ser chamado uma vez ao iniciar o sistema
        """
        try:
            exchange_info = await client.get_exchange_info()
            cls._valid_symbols_cache = {
                s['symbol'] for s in exchange_info['symbols']
                if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING'
            }
            logger.info(f"✅ Carregados {len(cls._valid_symbols_cache)} símbolos válidos da Binance")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao carregar símbolos da Binance: {e}")
            cls._valid_symbols_cache = set()
            return False
    
    @classmethod
    def map_asset_to_symbol(cls, asset: str) -> str:
        """
        Converte um ativo para símbolo USDT válido
        
        Args:
            asset: Nome do ativo (ex: 'BTC', 'MATIC', 'LDOG')
        
        Returns:
            Símbolo válido para trading (ex: 'BTCUSDT', 'POLUSDT', 'LDOGUSDT')
        """
        # Remove espaços e converte para maiúsculas
        asset = asset.strip().upper()
        
        # Ignora USDT
        if asset == 'USDT':
            return None
        
        # 1. Verifica mapeamento manual primeiro (prioridade)
        if asset in cls.MANUAL_MAPPING:
            mapped = cls.MANUAL_MAPPING[asset]
            logger.debug(f"🗺️ Mapeamento manual: {asset} → {mapped}")
            return mapped
        
        # 2. Tenta padrão: ASSET + USDT
        standard_symbol = f"{asset}USDT"
        
        # Verifica se está no cache de símbolos válidos
        if cls._valid_symbols_cache:
            if standard_symbol in cls._valid_symbols_cache:
                return standard_symbol
            else:
                # Procura alternativas similares
                alternatives = [
                    s for s in cls._valid_symbols_cache
                    if asset in s and s.endswith('USDT')
                ]
                
                if alternatives:
                    # Retorna a primeira alternativa encontrada
                    logger.warning(f"⚠️ {asset}: Usando alternativa {alternatives[0]}")
                    return alternatives[0]
                else:
                    logger.error(f"❌ {asset}: Nenhum símbolo válido encontrado na Binance")
                    return None
        else:
            # Cache não inicializado, tenta padrão
            logger.debug(f"⚠️ Cache não inicializado, usando padrão: {standard_symbol}")
            return standard_symbol
    
    @classmethod
    def add_manual_mapping(cls, asset: str, symbol: str):
        """
        Adiciona um mapeamento manual personalizado
        Útil para casos descobertos durante execução
        """
        cls.MANUAL_MAPPING[asset.upper()] = symbol.upper()
        logger.info(f"✅ Mapeamento adicionado: {asset} → {symbol}")
    
    @classmethod
    def get_all_valid_symbols(cls):
        """Retorna todos os símbolos válidos carregados"""
        return cls._valid_symbols_cache or set()
    
    @classmethod
    def is_valid_symbol(cls, symbol: str) -> bool:
        """Verifica se um símbolo é válido"""
        if not cls._valid_symbols_cache:
            logger.warning("⚠️ Cache de símbolos não inicializado")
            return True  # Permite por segurança
        return symbol.upper() in cls._valid_symbols_cache
    
    @classmethod
    def fix_symbol_errors(cls, asset: str) -> str:
        """
        Corrige erros comuns de digitação/duplicação
        
        Args:
            asset: Símbolo com possível erro (ex: 'LDUSDTT', 'BTCUSDTT')
        
        Returns:
            Símbolo corrigido
        """
        asset = asset.upper()
        
        # Remove USDT duplicado (LDUSDTT → LDOG → LDOGUSDT)
        if asset.endswith('USDTT'):
            base = asset[:-5]  # Remove 'USDTT'
            logger.warning(f"🔧 Corrigindo símbolo duplicado: {asset} → {base}")
            return cls.map_asset_to_symbol(base)
        
        # Remove USDT se já está no nome
        if asset.endswith('USDT') and len(asset) > 4:
            base = asset[:-4]
            return cls.map_asset_to_symbol(base)
        
        return cls.map_asset_to_symbol(asset)
