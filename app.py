import ctypes
import os
import sys
import traceback
from pathlib import Path
import faulthandler

# Capture native DLL failures as well as Python exceptions in packaged builds.
# This file contains stack traces only, never audio or screenshots.
if getattr(sys, 'frozen', False):
    _fault_dir = Path(sys.executable).parent / 'data'
    _fault_dir.mkdir(parents=True, exist_ok=True)
    _fault_stream = (_fault_dir / 'native-crash.log').open('a', encoding='utf-8')
    faulthandler.enable(_fault_stream, all_threads=True)
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, QCoreApplication, QEvent
from adaptive_volume.config import data_dir
from adaptive_volume.gui import MainWindow, STYLE


def main():
    if '--audio-test' in sys.argv:
        import json
        from adaptive_volume.diagnostics import run_comparison
        output = int(sys.argv[sys.argv.index('--device')+1])
        delay = int(sys.argv[sys.argv.index('--delay')+1])
        result = run_comparison(output, delay)
        print(json.dumps(result, indent=2))
        return 0
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Mort.AdaptiveVolume.1')
    kernel = ctypes.windll.kernel32
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    mutex_name = 'Local\\MortAdaptiveVolume' + ('.Smoke' if '--smoke' in sys.argv else '')
    mutex = kernel.CreateMutexW(None, False, mutex_name)
    duplicate = kernel.GetLastError() == 183
    app = QApplication(sys.argv)
    app.setApplicationName('Adaptive Volume')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    app.setQuitOnLastWindowClosed(False)
    if duplicate:
        QMessageBox.information(None, 'Adaptive Volume', 'Adaptive Volume is already running. Open it from the tray icon.')
        return 0
    window = MainWindow(smoke='--smoke' in sys.argv)
    app.aboutToQuit.connect(window.controller.close)
    if '--tray' not in sys.argv or '--smoke' in sys.argv:
        window.show()
    if '--smoke' in sys.argv:
        QTimer.singleShot(2500, window.quit_app)
    completed = False
    result = 0
    try:
        result = app.exec()
        completed = True
        return result
    finally:
        window.controller.close()
        # Tear down native tray/window handles before Qt's platform plugin is
        # unloaded by the frozen runtime, not during interpreter finalization.
        window.tray.hide()
        window.tray.setContextMenu(None)
        window.tray.deleteLater()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        if '--smoke' in sys.argv:
            data_dir().mkdir(parents=True, exist_ok=True)
            (data_dir() / 'packaged-smoke.json').write_text('{"event_loop_completed": true, "native_windows_destroyed": true}')
        kernel.CloseHandle(ctypes.c_void_p(mutex))
        if completed and getattr(sys, 'frozen', False):
            # PyInstaller/Python 3.14 unloads qwindows during interpreter
            # finalization, where Qt's native TLS destructor crashes on this
            # host. All application resources have already been explicitly
            # stopped/restored/deleted above. Avoid only that final DLL unload.
            faulthandler.disable()
            _fault_stream.close()
            os._exit(result)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        data_dir().mkdir(parents=True, exist_ok=True)
        (data_dir() / 'crash.txt').write_text(traceback.format_exc(), encoding='utf-8')
        raise
