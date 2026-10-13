"""Check native settings visibility when Windows launches the app hidden."""
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[1]
user = C.windll.user32
callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
user.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
user.IsWindowVisible.argtypes = [W.HWND]


def main():
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    executable = root / 'dist/release/AdaptiveVolume/AdaptiveVolume.exe'
    process = subprocess.Popen([str(executable), '--smoke'], startupinfo=startup)
    visible = False

    @callback_type
    def visit(handle, _):
        nonlocal visible
        pid = W.DWORD()
        user.GetWindowThreadProcessId(handle, C.byref(pid))
        if pid.value == process.pid:
            title = C.create_unicode_buffer(256)
            user.GetWindowTextW(handle, title, 256)
            if title.value == 'Adaptive Volume' and user.IsWindowVisible(handle):
                visible = True
        return True

    deadline = time.perf_counter() + 5
    while process.poll() is None and time.perf_counter() < deadline:
        user.EnumWindows(visit, 0)
        if visible:
            break
        time.sleep(.05)
    code = process.wait(timeout=30)
    assert visible, 'Hidden launch did not restore the actual native settings window'
    assert code == 0, code
    marker = json.loads((executable.parent / 'data/packaged-smoke.json').read_text())
    assert marker['event_loop_completed'] and marker['native_windows_destroyed']
    report = {'hidden_windows_launch': True, 'native_settings_window_visible': True,
              'clean_shutdown': True}
    (root / 'data/packaged-window-test.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
