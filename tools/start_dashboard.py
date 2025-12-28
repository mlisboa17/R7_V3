import subprocess
import sys
import os

# Prefer pythonw on Windows to avoid opening a console window
pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
if not os.path.exists(pythonw_path):
    pythonw_path = sys.executable

port = os.environ.get('DASH_PORT', '8530')
# Serve the project root (one level up from tools/)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

cmd = [pythonw_path, '-m', 'http.server', port]

creationflags = 0
if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
    creationflags = subprocess.CREATE_NO_WINDOW

subprocess.Popen(cmd, creationflags=creationflags, cwd=root_dir)
print(f'Dashboard server solicitado na porta {port} (background)')
