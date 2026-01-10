#!/usr/bin/env python3
"""
Verificações rápidas para garantir que o sistema não está comprando ativos:
- Lista processos Python que possam estar rodando o projeto
- Procura por entradas de compra/venda nos últimos logs
- Mostra o timestamp do arquivo `data/account_composition.json`

Execute no diretório raiz do projeto:
python tools/check_system_state.py
"""

import os
import sys
import json
import glob
import re
from collections import deque
from datetime import datetime
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOG_DIR = os.path.join(ROOT, 'logs')
DATA_FILE = os.path.join(ROOT, 'data', 'account_composition.json')

BUY_KEYWORDS = [
    r"order_market_buy",
    r"Executando compra",
    r"executar.*compra",
    r"comprar_market",
    r"🎯 \[SNIPER",
    r"Executando ordem",
    r"Abrindo",
]

SELL_KEYWORDS = [
    r"order_market_sell",
    r"fechar_posicao",
    r"Fechado",
    r"VENDA",
]


def tail(filepath, lines=200):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return deque(f, maxlen=lines)
    except Exception:
        return []


def search_logs(keywords, files=None):
    pattern = re.compile('|'.join(keywords), re.IGNORECASE)
    matches = []
    if files is None:
        files = sorted(glob.glob(os.path.join(LOG_DIR, '*')), key=os.path.getmtime, reverse=True)[:10]
    for fp in files:
        lines = tail(fp, 1000)
        for i, line in enumerate(lines):
            if pattern.search(line):
                matches.append((os.path.basename(fp), i+1, line.strip()))
    return matches


def list_python_processes():
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            name = p.info.get('name') or ''
            cmd = ' '.join(p.info.get('cmdline') or [])
            if 'python' in name.lower() or 'python' in cmd.lower():
                procs.append((p.info['pid'], name, cmd))
        return procs
    except Exception:
        # Fallback to shell commands
        procs = []
        if os.name == 'nt':
            try:
                out = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq python.exe'], stderr=subprocess.DEVNULL).decode(errors='ignore')
                return [('tasklist', out.strip(), '')]
            except Exception:
                return []
        else:
            try:
                out = subprocess.check_output(['ps', 'aux'], stderr=subprocess.DEVNULL).decode(errors='ignore')
                lines = [l for l in out.splitlines() if 'python' in l]
                return [('ps', l, '') for l in lines]
            except Exception:
                return []


def check_data_file():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        stat = os.stat(DATA_FILE)
        ts = datetime.fromtimestamp(stat.st_mtime).isoformat()
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {'mtime': ts, 'total_usdt': data.get('_total_usdt'), 'timestamp_field': data.get('_timestamp')}
    except Exception as e:
        return {'error': str(e)}


def main():
    print('== Verificando processos Python ==')
    procs = list_python_processes()
    if not procs:
        print('Nenhum processo Python detectado (ou psutil não instalado).')
    else:
        for p in procs[:50]:
            print(p)

    print('\n== Verificando logs recentes por sinais de compra ==')
    buys = search_logs(BUY_KEYWORDS)
    sells = search_logs(SELL_KEYWORDS)

    if buys:
        print(f'Encontrado(s) {len(buys)} ocorrência(s) de palavras relacionadas a COMPRAS nos logs:')
        for f, lnum, line in buys[:50]:
            print(f'[{f}] {line}')
    else:
        print('Nenhuma indicação de ordens de compra encontrada nos últimos logs pesquisados.')

    if sells:
        print(f'Encontrado(s) {len(sells)} ocorrência(s) de palavras relacionadas a VENDAS nos logs:')
        for f, lnum, line in sells[:50]:
            print(f'[{f}] {line}')
    else:
        print('Nenhuma indicação de ordens de venda encontrada nos últimos logs pesquisados.')

    print('\n== Verificando data/account_composition.json ==')
    df = check_data_file()
    if df is None:
        print('Arquivo data/account_composition.json não existe.')
    else:
        if 'error' in df:
            print('Erro ao ler arquivo:', df['error'])
        else:
            print('Modificado em:', df['mtime'])
            print('Campo _total_usdt:', df.get('total_usdt'))
            print('Campo _timestamp interno:', df.get('timestamp_field'))

    print('\n== Sugestões ==')
    print('- Se houver processos Python do projeto rodando, encerre-os antes de parar o sistema.')
    print('- Para evitar compras acidentais, garanta que a variável de ambiente REAL_TRADING não esteja definida como 1 no ambiente em execução.')

if __name__ == '__main__':
    main()
