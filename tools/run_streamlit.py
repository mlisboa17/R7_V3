#!/usr/bin/env python3
"""
Inicia o Streamlit em uma porta fixa ou escolhida automaticamente
- Se --port for informado, valida que a porta esteja livre e a usa (sai com código 1 se ocupada)
- Se não, escolhe a primeira porta livre a partir de 8501
- Imprime a porta usada e a URL antes de executar o Streamlit
"""

import socket
import subprocess
import os
import sys
import argparse


def find_free_port(start=8501, end=8600):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found in range")


def check_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', type=int, help='Porta desejada (ex: 8501)')
    parser.add_argument('--script', '-s', default='dashboard_r7_v2.py', help='Arquivo streamlit a executar')
    args = parser.parse_args()

    if args.port:
        if not check_port_free(args.port):
            print(f"ERRO: Porta {args.port} está ocupada.", file=sys.stderr)
            sys.exit(1)
        port = args.port
    else:
        port = find_free_port()

    url = f"http://localhost:{port}"
    print(f"Iniciando Streamlit em: {url}")

    # Define variável de ambiente para garantir que o streamlit use a porta
    os.environ['STREAMLIT_SERVER_PORT'] = str(port)

    cmd = ['streamlit', 'run', args.script, '--server.port', str(port)]

    # Substitui o processo atual para que os sinais (Ctrl+C) funcionem normalmente
    try:
        return_code = subprocess.call(cmd)
        sys.exit(return_code)
    except FileNotFoundError:
        print('Erro: comando `streamlit` não encontrado. Ative o ambiente correto.', file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
