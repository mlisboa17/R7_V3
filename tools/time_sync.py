"""
Sincronização de Relógio com Binance
Corrige erros APIError -1021 (timestamp mismatch) automaticamente
"""

import time
import logging
import subprocess
import platform
import asyncio
from binance.exceptions import BinanceAPIException

logger = logging.getLogger('time_sync')


class TimeSyncManager:
    """Gerencia sincronização de relógio com Binance e recuperação automática."""
    
    def __init__(self, client):
        self.client = client
        self.time_offset = 0
        self.last_sync = 0
        self.sync_interval = 300  # Re-sincronizar a cada 5 minutos
        self.max_retries = 3
        
    def get_local_time_ms(self):
        """Retorna tempo local em millisegundos."""
        return int(time.time() * 1000)
    
    async def sync_clock(self):
        """Sincroniza relógio com servidor Binance."""
        try:
            server_time = await self.client.get_server_time()
            local_time = self.get_local_time_ms()
            
            self.time_offset = server_time['serverTime'] - local_time
            self.last_sync = self.get_local_time_ms()
            
            if abs(self.time_offset) > 0:
                logger.info(f"⏰ Relógio Sincronizado. Offset: {self.time_offset}ms")
            
            return True
        except Exception as e:
            logger.warning(f"⚠️ Erro ao sincronizar relógio: {e}")
            return False
    
    def should_resync(self):
        """Verifica se deve fazer re-sincronização."""
        if self.last_sync == 0:
            return True
        elapsed = self.get_local_time_ms() - self.last_sync
        return elapsed > (self.sync_interval * 1000)
    
    def handle_timestamp_error(self, error: BinanceAPIException):
        """Detecta se erro é por timestamp e retorna True."""
        if error.code == -1021:
            logger.warning(f"🔴 Erro Timestamp Detectado: {error.message}")
            return True
        return False
    
    async def recover_from_timestamp_error(self):
        """Recuperação automática de erro de timestamp."""
        logger.warning("🔄 Iniciando procedimento de recuperação de timestamp...")
        
        # 1. Sincronizar relógio com Binance
        for attempt in range(self.max_retries):
            logger.info(f"   Tentativa {attempt + 1}/{self.max_retries} de sincronização...")
            if await self.sync_clock():
                logger.info("✅ Relógio sincronizado com sucesso!")
                await asyncio.sleep(5)  # Aguarda um pouco
                return True
            await asyncio.sleep(2)
        
        # 2. Se falhar, tenta sincronizar relógio do sistema (Windows)
        if platform.system() == "Windows":
            logger.warning("⚙️ Tentando sincronizar relógio do sistema (Windows)...")
            try:
                # Sincroniza via NTP usando comando do Windows
                result = subprocess.run(
                    ["w32tm", "/resync"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info("✅ Relógio do sistema sincronizado!")
                    await asyncio.sleep(5)
                    # Tenta sincronizar novamente com Binance
                    return await self.sync_clock()
                else:
                    logger.warning(f"⚠️ Sincronização w32tm falhou: {result.stderr.decode()}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao executar w32tm: {e}")
        
        logger.error("❌ Não foi possível recuperar do erro de timestamp")
        return False
    
    async def periodic_resync(self):
        """Task assíncrona para re-sincronizar periodicamente."""
        while True:
            try:
                if self.should_resync():
                    await self.sync_clock()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Erro em re-sincronização periódica: {e}")
                await asyncio.sleep(10)
