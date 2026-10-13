import os
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.environ['ADAPTIVE_VOLUME_DATA'] = str(root / 'data' / 'gui-test')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from adaptive_volume.gui import MainWindow, STYLE
from adaptive_volume.config import Settings

def main():
    app = QApplication([])
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    window = MainWindow(Settings(), smoke=True)
    window.show()

    def check():
        try:
            import ctypes
            assert ctypes.windll.user32.IsWindowVisible(int(window.winId()))
            window.tray_slider.setValue(32)
            assert window.slider.value() == 32
            assert window.settings.quiet_percent == 32
            window.slider.setValue(25)
            assert window.tray_slider.value() == 25
            root.joinpath('data').mkdir(exist_ok=True)
            window.grab().save(str(root / 'data' / 'gui-preview.png'))
            for page in range(1, window.tabs.count()):
                window.tabs.setCurrentIndex(page)
                app.processEvents()
                window.grab().save(str(root / 'data' / f'gui-page-{page}.png'))
            window.tabs.setCurrentIndex(0)
            assert window.tray.isVisible()
            window.tray.contextMenu().popup(window.pos())
            QTimer.singleShot(500, finish)
        except Exception:
            window.quit_app()
            raise

    def finish():
        import ctypes
        assert ctypes.windll.user32.IsWindowVisible(int(window.tray.contextMenu().winId()))
        window.tray.contextMenu().grab().save(str(root / 'data' / 'tray-preview.png'))
        window.tray.contextMenu().hide()
        from PySide6.QtWidgets import QSystemTrayIcon
        for reason in (QSystemTrayIcon.ActivationReason.Trigger,
                       QSystemTrayIcon.ActivationReason.DoubleClick):
            window.hide()
            window.tray.activated.emit(reason)
            app.processEvents()
            assert window.isVisible() and not window.isMinimized()
            assert ctypes.windll.user32.IsWindowVisible(int(window.winId()))
        window.showMinimized()
        window.show_window()
        app.processEvents()
        assert window.isVisible() and not window.isMinimized()
        print('GUI/native HWND, tray popup/native HWND and shared slider synchronization passed')
        window.quit_app()

    QTimer.singleShot(1500, check)
    app.exec()


if __name__ == "__main__":
    main()
