import subprocess, sys, os
pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
if __name__ == '__main__':
    script_path = os.path.join(os.getcwd(), 'tools', 'keep_alive.py')
    # Start keep_alive.py in background without window
    subprocess.Popen([pythonw_path, script_path], creationflags=subprocess.CREATE_NO_WINDOW)
    print('Keep-alive watchdog started in background')
