"""Current-user Windows login startup, with no administrator requirement."""
from pathlib import Path
import subprocess
import sys
import winreg

KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'Adaptive Volume'


def command():
    if getattr(sys, 'frozen', False):
        args = [sys.executable, '--tray']
    else:
        interpreter = Path(sys.executable).with_name('pythonw.exe')
        args = [str(interpreter), str(Path(__file__).resolve().parents[1] / 'app.py'), '--tray']
    return subprocess.list2cmdline(args)


def enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as key:
            return winreg.QueryValueEx(key, NAME)[0] == command()
    except FileNotFoundError:
        return False


def set_enabled(value):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as key:
        if value:
            winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, command())
        else:
            try:
                winreg.DeleteValue(key, NAME)
            except FileNotFoundError:
                pass
