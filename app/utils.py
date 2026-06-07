import os
import subprocess
import sys


def reopen_window(app):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py = os.path.join(root, "main.py")
    subprocess.Popen([sys.executable, main_py], cwd=root)
    app.destroy()
