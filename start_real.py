import subprocess
import sys
import os

# Caminho para o python que não abre janela (pythonw)
pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
if not os.path.exists(pythonw_path):
    pythonw_path = sys.executable

if __name__ == "__main__":
    # Ensure we run main.py from project root (absolute path) and set DASH_PORT=8530
    base_dir = os.path.abspath(os.path.dirname(__file__))
    script_path = os.path.join(base_dir, "main.py")
    env = os.environ.copy()
    env['DASH_PORT'] = env.get('DASH_PORT', '8530')

    creationflags = 0
    if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
        creationflags = subprocess.CREATE_NO_WINDOW

    subprocess.Popen([pythonw_path, script_path], creationflags=creationflags, env=env, cwd=base_dir)
    print("🚀 R7_V3 iniciado em background no MODO REAL! (DASH_PORT=%s)" % env['DASH_PORT'])