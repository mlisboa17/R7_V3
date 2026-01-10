#!/usr/bin/env python3
"""
Auto-Add Crypto System - Detecta e adiciona automaticamente novas altcoins
ao portfolio do R7_V3

Uso:
    python auto_add_crypto.py --symbol NEWUSDT
    python auto_add_crypto.py --watch-binance  # Monitora novas listings
"""

import json
import logging
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import argparse

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/crypto_additions.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('auto_add_crypto')

class CryptoPortfolioManager:
    def __init__(self, config_path: str = 'config/settings.json'):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = logger
        
    def _load_config(self) -> Dict:
        """Carrega configuração do settings.json"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"❌ Config não encontrada: {self.config_path}")
            sys.exit(1)
    
    def _save_config(self) -> bool:
        """Salva configuração atualizada"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"✅ Config salva: {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar config: {e}")
            return False
    
    def get_current_symbols(self) -> List[str]:
        """Retorna lista de símbolos monitorados"""
        try:
            return self.config['config_geral']['symbols_monitorados']
        except KeyError:
            self.logger.error("❌ symbols_monitorados não encontrado na config")
            return []
    
    def add_crypto(self, symbol: str, validate: bool = True) -> Tuple[bool, str]:
        """
        Adiciona nova cripto ao portfolio
        
        Args:
            symbol: Símbolo (ex: ZECUSDT, ETHEREUMETH)
            validate: Se True, valida formato e duplicatas
            
        Returns:
            (sucesso, mensagem)
        """
        
        # Normalizar símbolo
        symbol = symbol.upper().strip()
        
        # Validações
        if validate:
            # Verificar formato (deve terminar em USDT ou stablecoin)
            if not (symbol.endswith('USDT') or symbol.endswith('BUSD') or 
                    symbol.endswith('USDC') or symbol.endswith('TUSD')):
                return False, f"❌ Símbolo inválido: {symbol} (deve terminar em USDT/BUSD/USDC/TUSD)"
            
            # Verificar comprimento mínimo
            if len(symbol) < 6:  # Ex: BTCUSDT (mínimo 6 chars)
                return False, f"❌ Símbolo muito curto: {symbol}"
        
        # Verificar duplicata
        current = self.get_current_symbols()
        if symbol in current:
            return False, f"⚠️ {symbol} já existe no portfolio"
        
        try:
            # Adicionar ao config
            self.config['config_geral']['symbols_monitorados'].append(symbol)
            
            # Salvar
            if not self._save_config():
                return False, "❌ Erro ao salvar config"
            
            # Log
            total = len(self.config['config_geral']['symbols_monitorados'])
            msg = f"✅ {symbol} adicionado com sucesso! (Total: {total} moedas)"
            self.logger.info(msg)
            
            # Notificar
            self._notify_addition(symbol, total)
            
            return True, msg
            
        except Exception as e:
            return False, f"❌ Erro ao adicionar: {e}"
    
    def add_multiple_cryptos(self, symbols: List[str]) -> Dict[str, Tuple[bool, str]]:
        """Adiciona múltiplas criptos em batch"""
        results = {}
        for symbol in symbols:
            results[symbol] = self.add_crypto(symbol)
        return results
    
    def remove_crypto(self, symbol: str) -> Tuple[bool, str]:
        """Remove cripto do portfolio"""
        symbol = symbol.upper().strip()
        current = self.get_current_symbols()
        
        if symbol not in current:
            return False, f"❌ {symbol} não encontrado no portfolio"
        
        try:
            self.config['config_geral']['symbols_monitorados'].remove(symbol)
            
            if not self._save_config():
                return False, "❌ Erro ao salvar config"
            
            total = len(self.config['config_geral']['symbols_monitorados'])
            msg = f"✅ {symbol} removido. (Total: {total} moedas)"
            self.logger.info(msg)
            
            return True, msg
        except Exception as e:
            return False, f"❌ Erro ao remover: {e}"
    
    def list_portfolio(self) -> None:
        """Lista todas as criptos do portfolio"""
        symbols = self.get_current_symbols()
        
        print("\n" + "="*60)
        print(f"📊 PORTFOLIO ATUAL - {len(symbols)} MOEDAS")
        print("="*60)
        
        for i, symbol in enumerate(symbols, 1):
            print(f"  {i:2d}. {symbol}")
        
        print("="*60 + "\n")
    
    def validate_portfolio(self) -> bool:
        """Valida integridade do portfolio"""
        symbols = self.get_current_symbols()
        
        print(f"\n🔍 Validando {len(symbols)} moedas...\n")
        
        invalid = []
        for symbol in symbols:
            # Validar formato
            if not any(symbol.endswith(coin) for coin in ['USDT', 'BUSD', 'USDC', 'TUSD']):
                invalid.append(f"  ❌ {symbol} - formato inválido")
            elif len(symbol) < 6:
                invalid.append(f"  ❌ {symbol} - muito curto")
            else:
                print(f"  ✅ {symbol}")
        
        if invalid:
            print("\n⚠️ INVÁLIDOS:")
            for item in invalid:
                print(item)
            return False
        
        print(f"\n✅ Todas as {len(symbols)} moedas são válidas!\n")
        return True
    
    def _notify_addition(self, symbol: str, total: int) -> None:
        """Notifica sobre adição de nova cripto via Telegram"""
        try:
            from bots.comunicador import ComunicadorBot
            
            msg = f"""
🆕 NOVA CRIPTO ADICIONADA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Símbolo: {symbol}
Total de Moedas: {total}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            # ComunicadorBot.enviar(msg)  # Descomentar quando integrado
            self.logger.info(f"📱 Notificação: {msg}")
        except Exception as e:
            self.logger.debug(f"Notificação skipped: {e}")
    
    def export_portfolio(self, filepath: str = None) -> None:
        """Exporta portfolio em formato JSON"""
        if filepath is None:
            filepath = f"exports/portfolio_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'total_moedas': len(self.get_current_symbols()),
                'symbols': self.get_current_symbols()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"✅ Portfolio exportado: {filepath}")
        except Exception as e:
            self.logger.error(f"❌ Erro ao exportar: {e}")
    
    def import_portfolio(self, filepath: str) -> Tuple[bool, str]:
        """Importa portfolio de arquivo JSON"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            symbols = data.get('symbols', [])
            results = self.add_multiple_cryptos(symbols)
            
            added = sum(1 for success, _ in results.values() if success)
            msg = f"✅ {added} moedas importadas de {filepath}"
            self.logger.info(msg)
            
            return True, msg
        except Exception as e:
            return False, f"❌ Erro ao importar: {e}"

def main():
    parser = argparse.ArgumentParser(
        description='Auto-Add Crypto System para R7_V3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLOS:
  python auto_add_crypto.py --add ZECUSDT
  python auto_add_crypto.py --add ZEC ARB FET
  python auto_add_crypto.py --list
  python auto_add_crypto.py --validate
  python auto_add_crypto.py --remove ZECUSDT
  python auto_add_crypto.py --export
        """
    )
    
    parser.add_argument('--add', nargs='+', help='Adicionar símbolo(s)')
    parser.add_argument('--remove', help='Remover símbolo')
    parser.add_argument('--list', action='store_true', help='Listar portfolio')
    parser.add_argument('--validate', action='store_true', help='Validar portfolio')
    parser.add_argument('--export', nargs='?', const='auto', help='Exportar portfolio')
    parser.add_argument('--import', dest='import_file', help='Importar portfolio de arquivo')
    parser.add_argument('--config', default='config/settings.json', help='Caminho da config')
    
    args = parser.parse_args()
    
    manager = CryptoPortfolioManager(args.config)
    
    # Processar comandos
    if args.add:
        print(f"\n➕ Adicionando {len(args.add)} cripto(s)...\n")
        for symbol in args.add:
            success, msg = manager.add_crypto(symbol)
            print(msg)
    
    elif args.remove:
        print(f"\n➖ Removendo {args.remove}...\n")
        success, msg = manager.remove_crypto(args.remove)
        print(msg)
    
    elif args.list:
        manager.list_portfolio()
    
    elif args.validate:
        manager.validate_portfolio()
    
    elif args.export:
        filepath = None if args.export == 'auto' else args.export
        manager.export_portfolio(filepath)
    
    elif args.import_file:
        success, msg = manager.import_portfolio(args.import_file)
        print(msg)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
