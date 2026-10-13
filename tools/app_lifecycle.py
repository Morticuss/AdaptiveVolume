"""Gracefully quit the local packaged app for updates and audio checks."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import psutil


def quit_local():
    expected = (Path(__file__).resolve().parents[1] / 'dist/AdaptiveVolume/AdaptiveVolume.exe').resolve()
    source = Path(__file__).resolve().parents[1] / 'app.py'
    user = C.windll.user32
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.PostThreadMessageW.argtypes = [W.DWORD, W.UINT, W.WPARAM, W.LPARAM]
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    for process in psutil.process_iter(['exe', 'cmdline']):
        if '--multiprocessing-fork' in (process.info['cmdline'] or []):
            continue
        executable = Path(process.info['exe']) if process.info['exe'] else None
        source_app = (executable and executable.name.lower() in ('python.exe', 'pythonw.exe')
                      and str(source) in (process.info['cmdline'] or []))
        if not executable or (executable.resolve() != expected and not source_app):
            continue
        threads = set()

        @callback_type
        def visit(hwnd, data):
            pid = W.DWORD()
            thread = user.GetWindowThreadProcessId(hwnd, C.byref(pid))
            if pid.value == process.pid:
                threads.add(thread)
            return True

        user.EnumWindows(visit, 0)
        if not threads:
            # Virtualenv launchers and spawned helpers can have the same
            # command line while owning no Qt window. Quit the window owner.
            continue
        for thread in threads:
            user.PostThreadMessageW(thread, 0x0012, 0, 0)
        code = process.wait(timeout=15)
        if code != 0:
            raise RuntimeError(f'App exited with code {code}')
        print('Adaptive Volume stopped cleanly')


if __name__ == '__main__':
    quit_local()
