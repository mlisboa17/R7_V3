#!/usr/bin/env python3
"""
Script de sincronização de relógio com Binance
Útil para corrigir erros de timestamp fora de horário
"""

import subprocess
import platform
import time
import os
import sys
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

def sync_windows_clock():
    """Sincroniza relógio via w32tm (Windows)."""
    print("🖥️  Sistema: Windows")
    print("⏰ Sincronizando relógio do sistema via w32tm...")
    
    try:
        result = subprocess.run(
            ["w32tm", "/resync"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            print("✅ Relógio do sistema sincronizado com sucesso!")
            time.sleep(2)
            return True
        else:
            print(f"❌ Erro ao sincronizar: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Erro ao executar w32tm: {e}")
        return False

def sync_linux_clock():
    """Sincroniza relógio via ntpdate ou timedatectl (Linux)."""
    print("🖥️  Sistema: Linux")
    
    # Tenta timedatectl primeiro (systemd)
    try:
        print("⏰ Tentando sincronizar via timedatectl...")
        result = subprocess.run(
            ["sudo", "timedatectl", "set-ntp", "on"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            print("✅ Relógio sincronizado via timedatectl!")
            time.sleep(2)
            return True
    except:
        pass
    
    # Tenta ntpdate se timedatectl falhar
    try:
        print("⏰ Tentando sincronizar via ntpdate...")
        result = subprocess.run(
            ["sudo", "ntpdate", "-s", "pool.ntp.org"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            print("✅ Relógio sincronizado via ntpdate!")
            time.sleep(2)
            return True
    except:
        pass
    
    print("❌ Não foi possível sincronizar relógio Linux")
    return False

def sync_binance_time():
    """Verifica e sincroniza tempo com servidor Binance."""
    print("\n🔗 Verificando sincronização com Binance...")
    
    try:
        api_key = os.getenv('BINANCE_API_KEY')
        secret_key = os.getenv('BINANCE_SECRET_KEY')
        
        if not api_key or not secret_key:
            print("❌ API key e secret não configuradas em .env")
            return False
        
        client = Client(api_key, secret_key)
        server_time = client.get_server_time()
        local_time = int(time.time() * 1000)
        
        time_diff = server_time['serverTime'] - local_time
        
        print(f"📊 Hora Local: {local_time}ms")
        print(f"📊 Hora Binance: {server_time['serverTime']}ms")
        print(f"📊 Diferença: {time_diff}ms")
        
        if abs(time_diff) > 1000:
            print(f"⚠️  Diferença > 1000ms (Binance rejeitará operações)")
            return False
        elif abs(time_diff) > 500:
            print(f"⚠️  Diferença > 500ms (Pode causar erros ocasionais)")
            return False
        else:
            print(f"✅ Relógio sincronizado! Diferença aceitável.")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao conectar Binance: {e}")
        return False

def main():
    print("=" * 60)
    print("🔄 Sincronizador de Relógio para R7_V3")
    print("=" * 60)
    
    # 1. Sincroniza relógio do sistema
    system = platform.system()
    
    if system == "Windows":
        sync_windows_clock()
    elif system == "Linux":
        sync_linux_clock()
    elif system == "Darwin":
        print("🖥️  Sistema: macOS")
        print("⏰ Use 'System Preferences > Date & Time' para sincronizar manualmente")
    else:
        print(f"⚠️  Sistema desconhecido: {system}")
    
    # 2. Valida sincronização com Binance
    time.sleep(3)
    success = sync_binance_time()
    
    # 3. Resultado final
    print("\n" + "=" * 60)
    if success:
        print("✅ Sistema sincronizado com sucesso!")
        print("   Você pode reiniciar o R7_V3 agora.")
        sys.exit(0)
    else:
        print("❌ Sincronização incompleta")
        print("   Verifique sua conexão de internet e tente novamente.")
        sys.exit(1)

if __name__ == "__main__":
    main()
