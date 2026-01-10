#!/usr/bin/env python3
"""
Sistema de Verificação Consolidado - R7_V3
Consolidação de todas as funções de check_ em um único arquivo
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from binance.client import Client
from binance.exceptions import BinanceAPIException
import sqlite3
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('SystemChecker')

class SystemChecker:
    def __init__(self):
        self.client = None
        self.load_config()
    
    def load_config(self):
        """Carrega configurações do .env e settings.json"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            self.api_key = os.getenv('BINANCE_API_KEY')
            self.api_secret = os.getenv('BINANCE_SECRET_KEY')
            
            if self.api_key and self.api_secret:
                self.client = Client(self.api_key, self.api_secret)
                logger.info("✅ Cliente Binance inicializado")
            else:
                logger.warning("⚠️ Credenciais Binance não encontradas")
                
        except Exception as e:
            logger.error(f"❌ Erro ao carregar configurações: {e}")
    
    async def check_balance_quick(self):
        """Verificação rápida do saldo atual"""
        try:
            if not self.client:
                return {"error": "Cliente Binance não inicializado"}
            
            account = self.client.get_account()
            balances = [b for b in account['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
            
            total_usdt = 0
            assets = []
            
            for balance in balances[:20]:  # Top 20 assets
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    try:
                        if asset == 'USDT':
                            price_usdt = 1.0
                        else:
                            ticker = self.client.get_symbol_ticker(symbol=f"{asset}USDT")
                            price_usdt = float(ticker['price'])
                        
                        value_usdt = total * price_usdt
                        total_usdt += value_usdt
                        
                        assets.append({
                            'asset': asset,
                            'balance': total,
                            'value_usdt': value_usdt,
                            'price': price_usdt
                        })
                    except:
                        continue
            
            return {
                'timestamp': datetime.now().isoformat(),
                'total_usdt': total_usdt,
                'total_assets': len(assets),
                'assets': sorted(assets, key=lambda x: x['value_usdt'], reverse=True)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na verificação de saldo: {e}")
            return {"error": str(e)}
    
    async def check_positions(self):
        """Verifica posições abertas no sistema"""
        try:
            # Verifica active_trades
            active_trades_path = os.path.join('data', 'active_trades.json')
            positions = {}
            
            if os.path.exists(active_trades_path):
                with open(active_trades_path, 'r') as f:
                    positions = json.load(f)
            
            # Verifica banco de dados
            db_positions = []
            if os.path.exists('memoria_bot.db'):
                conn = sqlite3.connect('memoria_bot.db')
                cursor = conn.execute("SELECT symbol, entry_price, timestamp FROM trades WHERE exit_price IS NULL")
                db_positions = cursor.fetchall()
                conn.close()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'active_trades_count': len(positions),
                'active_trades': positions,
                'db_positions_count': len(db_positions),
                'db_positions': db_positions
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na verificação de posições: {e}")
            return {"error": str(e)}
    
    async def check_trades_now(self):
        """Verifica trades das últimas 24h"""
        try:
            if not self.client:
                return {"error": "Cliente Binance não inicializado"}
            
            # Data de 24h atrás
            start_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
            
            all_trades = []
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT']
            
            for symbol in symbols:
                try:
                    trades = self.client.get_my_trades(symbol=symbol, startTime=start_time)
                    all_trades.extend(trades)
                except:
                    continue
            
            # Processa trades
            buy_trades = [t for t in all_trades if t['isBuyer']]
            sell_trades = [t for t in all_trades if not t['isBuyer']]
            
            total_buy_volume = sum(float(t['quoteQty']) for t in buy_trades)
            total_sell_volume = sum(float(t['quoteQty']) for t in sell_trades)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'period': '24h',
                'total_trades': len(all_trades),
                'buy_trades': len(buy_trades),
                'sell_trades': len(sell_trades),
                'buy_volume_usdt': total_buy_volume,
                'sell_volume_usdt': total_sell_volume,
                'net_volume': total_buy_volume - total_sell_volume
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na verificação de trades: {e}")
            return {"error": str(e)}
    
    async def check_binance_history(self, symbol="BTCUSDT", days=7):
        """Verifica histórico de ordens para um symbol"""
        try:
            if not self.client:
                return {"error": "Cliente Binance não inicializado"}
            
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            # Busca ordens
            orders = self.client.get_all_orders(symbol=symbol, startTime=start_time)
            
            filled_orders = [o for o in orders if o['status'] == 'FILLED']
            buy_orders = [o for o in filled_orders if o['side'] == 'BUY']
            sell_orders = [o for o in filled_orders if o['side'] == 'SELL']
            
            return {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'period_days': days,
                'total_orders': len(orders),
                'filled_orders': len(filled_orders),
                'buy_orders': len(buy_orders),
                'sell_orders': len(sell_orders),
                'recent_orders': filled_orders[-5:]  # 5 mais recentes
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na verificação de histórico: {e}")
            return {"error": str(e)}
    
    async def check_ada_magic_history(self):
        """Verificação específica para histórico ADA (se necessário)"""
        return await self.check_binance_history("ADAUSDT", days=30)
    
    def save_check_report(self, check_type, data):
        """Salva relatório de verificação"""
        try:
            reports_dir = os.path.join('data', 'check_reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{check_type}_{timestamp}.json"
            filepath = os.path.join(reports_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Relatório salvo: {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar relatório: {e}")
    
    async def run_all_checks(self):
        """Executa todas as verificações"""
        logger.info("🔍 Iniciando verificação completa do sistema...")
        
        checks = {
            'balance_quick': await self.check_balance_quick(),
            'positions': await self.check_positions(),
            'trades_24h': await self.check_trades_now(),
            'btc_history': await self.check_binance_history("BTCUSDT", 7),
            'ada_history': await self.check_ada_magic_history()
        }
        
        # Salva relatório consolidado
        self.save_check_report('full_system_check', checks)
        
        # Exibe resumo
        print("\n" + "="*60)
        print("📊 RELATÓRIO COMPLETO DE VERIFICAÇÃO")
        print("="*60)
        
        if 'error' not in checks['balance_quick']:
            balance_data = checks['balance_quick']
            print(f"💰 Saldo Total: ${balance_data['total_usdt']:,.2f}")
            print(f"📊 Total de Ativos: {balance_data['total_assets']}")
        
        if 'error' not in checks['positions']:
            pos_data = checks['positions']
            print(f"🎯 Posições Ativas: {pos_data['active_trades_count']}")
            print(f"💾 Posições no DB: {pos_data['db_positions_count']}")
        
        if 'error' not in checks['trades_24h']:
            trade_data = checks['trades_24h']
            print(f"📈 Trades 24h: {trade_data['total_trades']}")
            print(f"💵 Volume Líquido: ${trade_data['net_volume']:,.2f}")
        
        print("="*60)
        
        return checks

# Funções de compatibilidade (mantém interface antiga)
async def check_balance_quick():
    checker = SystemChecker()
    return await checker.check_balance_quick()

async def check_positions():
    checker = SystemChecker()
    return await checker.check_positions()

async def check_trades_now():
    checker = SystemChecker()
    return await checker.check_trades_now()

async def check_binance_history(symbol="BTCUSDT", days=7):
    checker = SystemChecker()
    return await checker.check_binance_history(symbol, days)

async def check_ada_magic_history():
    checker = SystemChecker()
    return await checker.check_ada_magic_history()

if __name__ == "__main__":
    checker = SystemChecker()
    asyncio.run(checker.run_all_checks())