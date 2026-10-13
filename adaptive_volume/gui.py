import ctypes
import json
import time
import logging
import subprocess
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QIcon, QDesktopServices
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QSlider, QComboBox, QSpinBox, QCheckBox,
    QTabWidget, QFormLayout, QSystemTrayIcon, QMenu, QWidgetAction, QMessageBox,
    QProgressBar, QTextEdit)
from .config import Settings, data_dir
from .controller import Controller
from .audio import devices
from . import startup

log = logging.getLogger(__name__)

STYLE = '''
QWidget { background: #10151e; color: #e7edf5; font-family: 'Segoe UI'; font-size: 14px; }
QMainWindow { background: #10151e; }
QLabel { background: transparent; }
QLabel#muted { color: #929fb3; }
QLabel#title { font-size: 29px; font-weight: 700; }
QLabel#hero { font-size: 38px; font-weight: 700; }
QLabel#eyebrow { color: #60d8c0; font-size: 12px; font-weight: 600; }
QFrame#card { background: #19212e; border: 1px solid #2a3547; border-radius: 16px; }
QPushButton { background: #263346; border: 1px solid #34435b; border-radius: 8px; padding: 10px 18px; }
QPushButton:hover { background: #344760; }
QPushButton#primary { background: #60d8c0; color: #0b2723; border: none; font-weight: 700; }
QPushButton#primary:hover { background: #88ead6; }
QTabWidget::pane { border: none; padding-top: 22px; }
QTabBar::tab { color: #929fb3; padding: 12px 24px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #60d8c0; border-bottom: 2px solid #60d8c0; }
QSlider::groove:horizontal { height: 6px; background: #334158; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #60d8c0; border-radius: 3px; }
QSlider::handle:horizontal { width: 18px; margin: -6px 0; background: #e7fff8; border-radius: 9px; }
QComboBox, QSpinBox { background: #19212e; border: 1px solid #34435b; border-radius: 7px; padding: 9px; }
QComboBox QAbstractItemView { background: #19212e; selection-background-color: #344760; }
QCheckBox { spacing: 10px; }
QProgressBar { border: none; background: #334158; border-radius: 5px; height: 10px; }
QProgressBar::chunk { background: #60d8c0; border-radius: 5px; }
QMenu { background: #19212e; border: 1px solid #34435b; padding: 10px; }
QMenu::item { padding: 9px 16px; }
QMenu::item:selected { background: #344760; border-radius: 5px; }
QTextEdit { background: #19212e; border: 1px solid #34435b; border-radius: 8px; padding: 12px; }
'''


def app_icon():
    pix = QPixmap(128, 128)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor('#192b38'))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(4, 4, 120, 120, 30, 30)
    p.setPen(QPen(QColor('#60d8c0'), 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for x, height in [(30, 22), (47, 48), (64, 72), (81, 48), (98, 22)]:
        p.drawLine(x, 64-height//2, x, 64+height//2)
    p.end()
    return QIcon(pix)


def label(text, kind=None):
    result = QLabel(text)
    result.setWordWrap(len(text) > 65 and kind != 'hero')
    if kind:
        result.setObjectName(kind)
    return result


def card():
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(24, 22, 24, 22)
    layout.setSpacing(16)
    return frame, layout


class MainWindow(QMainWindow):
    def __init__(self, settings=None, smoke=False):
        super().__init__()
        self.settings = settings or Settings.load()
        self.controller = Controller(self.settings)
        self.smoke = smoke
        self.quitting = False
        self.setWindowTitle('Adaptive Volume')
        self.setWindowIcon(app_icon())
        self.resize(1030, 820)
        self.setMinimumSize(880, 760)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(32, 28, 32, 24)
        outer.setSpacing(20)
        heading = QHBoxLayout()
        heading.addWidget(label('Adaptive Volume', 'title'))
        heading.addStretch()
        heading.addWidget(label('LOCAL AUDIO  /  WINDOWS', 'eyebrow'))
        outer.addLayout(heading)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)
        self._home()
        self._audio()
        self._voice_detection()
        self._timing()
        outer.addWidget(label('Ctrl + Alt + M to enable or pause  ·  Closing this window keeps the tray running', 'muted'))
        self._tray()
        self.refresh_devices()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(150)
        self.update_status()
        if not smoke:
            ctypes.windll.user32.RegisterHotKey(int(self.winId()), 1, 0x0001 | 0x0002 | 0x4000, ord('M'))
            if self.settings.auto_enable:
                QTimer.singleShot(0, self.start_saved_audio)
            self.retry_timer = QTimer(self)
            self.retry_timer.timeout.connect(self.controller.maintain_audio)
            self.retry_timer.start(3000)

    def start_saved_audio(self):
        self.controller.set_enabled(True)
        self.update_status()

    def change_startup(self, checked):
        try:
            startup.set_enabled(checked)
        except OSError as exc:
            self.startup_check.blockSignals(True)
            self.startup_check.setChecked(startup.enabled())
            self.startup_check.blockSignals(False)
            QMessageBox.warning(self, 'Windows startup', str(exc))

    def change_auto_enable(self, checked):
        self.settings.auto_enable = checked
        if not self.smoke:
            self.settings.save()

    def _home(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)
        top, content = card()
        content.addWidget(label('LET THE MUSIC BREATHE', 'eyebrow'))
        hero = label('Your music.\nRoom for everything else.', 'hero')
        hero.setMinimumHeight(110)
        content.addWidget(hero)
        content.addWidget(label('A gentle fade that makes room for your friends on Discord.', 'muted'))
        row = QHBoxLayout()
        self.enable_button = QPushButton('Enable adaptive volume')
        self.enable_button.setObjectName('primary')
        self.enable_button.clicked.connect(self.toggle)
        row.addWidget(self.enable_button)
        self.state_label = label('Paused · normal music level', 'muted')
        row.addWidget(self.state_label, 1)
        content.addLayout(row)
        layout.addWidget(top)
        bottom, content = card()
        row = QHBoxLayout()
        row.addWidget(label('Lowered music level'))
        row.addStretch()
        self.percent_label = label('25% of normal', 'eyebrow')
        row.addWidget(self.percent_label)
        content.addLayout(row)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(self.settings.quiet_percent)
        self.slider.valueChanged.connect(self.set_quiet)
        content.addWidget(self.slider)
        row = QHBoxLayout()
        row.addWidget(label('Your chosen music level while friends speak on Discord.', 'muted'), 1)
        preview = QPushButton('Preview fade')
        preview.clicked.connect(self.controller.preview)
        row.addWidget(preview)
        content.addLayout(row)
        self.reason_label = label('Normal music level')
        content.addWidget(self.reason_label)
        self.level = QProgressBar()
        self.level.setRange(0, 100)
        self.level.setTextVisible(False)
        content.addWidget(self.level)
        layout.addWidget(bottom)
        self.home_status = label('', 'muted')
        layout.addWidget(self.home_status)
        layout.addStretch()
        self.tabs.addTab(page, 'Overview')

    def _audio(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(label('Voice audio', 'title'))
        layout.addWidget(label('Spotify stays on its current output. Only incoming Discord audio passes through the bridge.', 'muted'))
        self.startup_check = QCheckBox('Start with Windows · run quietly in the tray')
        self.startup_check.setChecked(startup.enabled())
        self.startup_check.toggled.connect(self.change_startup)
        layout.addWidget(self.startup_check)
        self.auto_check = QCheckBox('Enable automatically when the app opens')
        self.auto_check.setChecked(self.settings.auto_enable)
        self.auto_check.toggled.connect(self.change_auto_enable)
        layout.addWidget(self.auto_check)
        box, content = card()
        form = QFormLayout()
        form.setSpacing(16)
        self.mode = QComboBox()
        self.mode.addItems(['Buffered · virtual cable', 'Unbuffered · immediate Discord playback'])
        self.mode.setCurrentIndex(0 if self.settings.buffered else 1)
        form.addRow('Playback mode', self.mode)
        self.input_combo, self.output_combo = QComboBox(), QComboBox()
        form.addRow('Cable recording device', self.input_combo)
        form.addRow('Your headphones / speakers', self.output_combo)
        self.delay = QSpinBox()
        self.delay.setRange(0, 250)
        self.delay.setSuffix(' ms')
        self.delay.setValue(self.settings.buffer_ms)
        form.addRow('App buffer target', self.delay)
        self.sensitivity = QComboBox()
        self.sensitivity.addItems(['Most sensitive', 'Sensitive', 'Balanced', 'Noise resistant'])
        self.sensitivity.setCurrentIndex(self.settings.vad_mode)
        form.addRow('Speech detector', self.sensitivity)
        content.addLayout(form)
        content.addWidget(label('25 ms fade down  →  1.1 seconds of breathing room  →  250 ms fade up', 'eyebrow'))
        row = QHBoxLayout()
        refresh = QPushButton('Refresh devices')
        refresh.clicked.connect(self.refresh_devices)
        apply = QPushButton('Apply audio settings')
        apply.setObjectName('primary')
        apply.clicked.connect(self.apply_audio)
        row.addWidget(refresh)
        row.addWidget(apply)
        content.addLayout(row)
        layout.addWidget(box)
        self.routing_status = label('', 'muted')
        layout.addWidget(self.routing_status)
        row = QHBoxLayout()
        cable = QPushButton('Get VB-CABLE')
        cable.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://vb-audio.com/Cable/')))
        recovery = QPushButton('Recover direct voice audio')
        recovery.clicked.connect(self.recovery)
        row.addWidget(cable)
        row.addWidget(recovery)
        layout.addLayout(row)
        layout.addStretch()
        self.tabs.addTab(page, 'Audio setup')

    def _voice_detection(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)
        layout.addWidget(label('Voice detection', 'title'))
        layout.addWidget(label('Ignore quiet background sounds before checking for speech.', 'muted'))
        box, content = card()
        row = QHBoxLayout()
        row.addWidget(label('Minimum voice level'))
        row.addStretch()
        self.threshold_value = label(f'{self.settings.min_voice_db} dBFS', 'eyebrow')
        row.addWidget(self.threshold_value)
        content.addLayout(row)
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(-70, -10)
        self.threshold_slider.setValue(self.settings.min_voice_db)
        self.threshold_slider.valueChanged.connect(self.set_voice_threshold)
        content.addWidget(self.threshold_slider)
        content.addWidget(label('Left: picks up quieter voices. Right: rejects more background noise.', 'muted'))
        self.voice_level_label = label('Incoming audio: silence', 'eyebrow')
        content.addWidget(self.voice_level_label)
        self.voice_meter = QProgressBar()
        self.voice_meter.setRange(-90, 0)
        self.voice_meter.setTextVisible(False)
        content.addWidget(self.voice_meter)
        content.addWidget(label('Watch the level while nobody speaks, then put the minimum a little above that noise. Keep it below the level of your quietest friend. Changes apply immediately and are saved.', 'muted'))
        content.addWidget(label('dBFS measures digital audio level, not room loudness. For example, −30 dBFS requires louder audio than −40 dBFS. Sounds must also pass the speech detector; loud noise can still be mistaken for a voice.', 'muted'))
        layout.addWidget(box)
        layout.addStretch()
        self.tabs.addTab(page, 'Voice detection')

    def set_voice_threshold(self, value):
        self.settings.min_voice_db = value
        self.threshold_value.setText(f'{value} dBFS')
        if not self.smoke:
            self.settings.save()

    def _timing(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(label('Timing & diagnostics', 'title'))
        layout.addWidget(label('The 50 ms setting is a queue target, not a promise of total latency. Device latency is reported separately. A listening and loopback test are needed to measure the full path.', 'muted'))
        self.metrics = QTextEdit()
        self.metrics.setReadOnly(True)
        layout.addWidget(self.metrics, 1)
        layout.addWidget(label('Comparison: select Unbuffered in Audio setup, then return to Buffered at 50 ms. No buffer changes are made automatically.', 'muted'))
        self.timing_note = label('', 'muted')
        layout.addWidget(self.timing_note)
        self.test_button = QPushButton('Run local synthetic timing test')
        self.test_button.clicked.connect(self.run_timing_test)
        layout.addWidget(self.test_button)
        self.tabs.addTab(page, 'Diagnostics')

    def _tray(self):
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        menu = QMenu()
        widget = QWidget()
        widget.setMinimumWidth(270)
        layout = QVBoxLayout(widget)
        layout.addWidget(label('Lowered music level'))
        self.tray_percent = label('', 'eyebrow')
        layout.addWidget(self.tray_percent)
        self.tray_slider = QSlider(Qt.Orientation.Horizontal)
        self.tray_slider.setRange(0, 100)
        self.tray_slider.setValue(self.settings.quiet_percent)
        self.tray_slider.valueChanged.connect(self.set_quiet)
        layout.addWidget(self.tray_slider)
        action = QWidgetAction(menu)
        action.setDefaultWidget(widget)
        menu.addAction(action)
        menu.addSeparator()
        self.tray_toggle = menu.addAction('Enable adaptive volume', self.toggle)
        menu.addAction('Preview fade', self.controller.preview)
        menu.addAction('Open settings', self.show_window)
        menu.addAction('Recover direct voice audio', self.recovery)
        menu.addSeparator()
        menu.addAction('Quit', self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()
        self.set_quiet(self.settings.quiet_percent, save=False)

    def set_quiet(self, value, save=True):
        self.controller.quiet(value)
        for slider in (self.slider, self.tray_slider):
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
        self.percent_label.setText(f'{value}% of normal')
        self.tray_percent.setText(f'{value}% of normal')
        if save and not self.smoke:
            self.settings.save()

    def refresh_devices(self):
        try:
            available = devices()
        except Exception as exc:
            self.routing_status.setText(str(exc))
            return
        self.input_combo.clear()
        self.output_combo.clear()
        self.input_combo.addItem('Select cable recording device…', '')
        self.output_combo.addItem('Select headphones / speakers…', '')
        for device in available:
            name = device['name']
            if device['max_input_channels'] >= 2 and 'cable output' in name.lower():
                self.input_combo.addItem(name, name)
            if device['max_output_channels'] >= 2 and 'cable' not in name.lower():
                self.output_combo.addItem(name, name)
        for combo, selected in ((self.input_combo, self.settings.cable_name), (self.output_combo, self.settings.output_name)):
            if combo is self.output_combo and not selected:
                import sounddevice as sd
                wasapi = next((a for a in sd.query_hostapis() if a['name'] == 'Windows WASAPI'), None)
                if wasapi and wasapi['default_output_device'] >= 0:
                    selected = sd.query_devices(wasapi['default_output_device'])['name']
            index = combo.findData(selected)
            if index >= 0:
                combo.setCurrentIndex(index)
            elif combo.count() == 2:
                combo.setCurrentIndex(1)

    def apply_audio(self):
        self.settings.buffered = self.mode.currentIndex() == 0
        self.settings.buffer_ms = self.delay.value()
        self.settings.vad_mode = self.sensitivity.currentIndex()
        self.settings.cable_name = self.input_combo.currentData() or ''
        self.settings.output_name = self.output_combo.currentData() or ''
        if not self.smoke:
            self.settings.save()
        was_running = self.controller.audio.worker is not None
        was_enabled = self.controller.enabled
        self.controller.set_enabled(False)
        self.controller.audio.stop()
        if was_enabled:
            self.controller.set_enabled(True)
        elif was_running:
            self.controller.audio.start()
        self.update_status()

    def toggle(self):
        if not self.controller.enabled:
            self.apply_audio()
        if not self.controller.set_enabled(not self.controller.enabled):
            QMessageBox.information(self, 'Audio setup needed', self.controller.error)
        self.update_status()

    def update_status(self):
        c = self.controller
        self.enable_button.setText('Pause adaptive volume' if c.enabled else 'Enable adaptive volume')
        self.tray_toggle.setText('Pause adaptive volume' if c.enabled else 'Enable adaptive volume')
        self.state_label.setText('Listening locally' if c.enabled else 'Paused · normal music level')
        reason = ' + '.join(c.reasons) or 'Normal music level'
        self.reason_label.setText(reason)
        self.level.setValue(round(c.gain * 100))
        self.home_status.setText(f'Spotify: {c.spotify_count} session(s)  ·  {c.audio.status}')
        self.routing_status.setText(c.audio.fault or c.error or c.routing_status)
        self.tray.setToolTip(f'Adaptive Volume · {reason} · {round(c.gain*100)}%')
        info = c.audio.metrics()
        db = info['voice_level_dbfs']
        self.voice_meter.setValue(round(db))
        self.voice_level_label.setText('Incoming audio: silence' if db <= -90 else
            f'Incoming audio: {db:.1f} dBFS · ' + ('above minimum' if db >= self.settings.min_voice_db else 'below minimum'))
        info.update({'spotify_sessions': c.spotify_count, 'current_gain_percent': round(c.gain*100, 1),
                     'reasons': c.reasons, 'audio_status': c.audio.status,
                     'error': c.audio.fault or c.error})
        self.metrics.setPlainText(json.dumps(info, indent=2))
        report = data_dir() / 'latency-test.json'
        if report.exists():
            try:
                r = json.loads(report.read_text())
                self.timing_note.setText(f"Last synthetic cable test: {r.get('measured_added_ms', '?')} ms added · {r.get('scope', '')}")
            except (OSError, ValueError):
                pass

    def recovery(self):
        self.controller.set_enabled(False)
        QDesktopServices.openUrl(QUrl('ms-settings:apps-volume'))
        QMessageBox.information(self, 'Restore direct voice audio',
            'In Discord → User Settings → Voice & Video, set Output Device to your headphones.\n\n'
            'Leave the microphone unchanged. The bridge stays running while paused so voices remain audible. '
            'Windows Volume Mixer is open if an app-level output override also needs changing.')

    def run_timing_test(self):
        available = devices()
        selected = self.output_combo.currentData()
        target = next((d for d in available if d['name'] == selected and d['max_output_channels'] >= 2), None)
        if target is None:
            QMessageBox.information(self, 'Choose an output', 'Choose your headphones or speakers in Audio setup first.')
            return
        self.test_button.setEnabled(False)
        self.test_button.setText('Playing quiet synthetic speech…')
        command = [sys.executable]
        if not getattr(sys, 'frozen', False):
            command.append(str(Path(__file__).resolve().parents[1] / 'app.py'))
        command += ['--audio-test', '--device', str(target['index']), '--delay', str(self.delay.value())]
        self.test_process = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW)
        self.test_timer = QTimer(self)
        self.test_timer.timeout.connect(self.finish_timing_test)
        self.test_timer.start(300)

    def finish_timing_test(self):
        if self.test_process.poll() is None:
            return
        self.test_timer.stop()
        self.test_button.setEnabled(True)
        self.test_button.setText('Run local synthetic timing test')
        if self.test_process.returncode:
            QMessageBox.warning(self, 'Timing test', 'The test failed. See crash.txt in the app data folder for details.')
        self.update_status()

    def show_window(self):
        self.tray.contextMenu().hide()
        self.showNormal()
        from ctypes import wintypes
        user = ctypes.windll.user32
        user.IsWindowVisible.argtypes = [wintypes.HWND]
        user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        handle = int(self.winId())
        # Windows can honor STARTUPINFO(SW_HIDE) on the first native show,
        # although Qt has already marked the widget visible. A second Qt show
        # then does nothing. Restore the actual HWND when those states differ.
        if not user.IsWindowVisible(handle):
            user.ShowWindow(handle, 9)  # SW_RESTORE
        self.raise_()
        self.activateWindow()
        log.info('Settings window opened: visible=%s native_visible=%s minimized=%s', self.isVisible(), bool(user.IsWindowVisible(handle)), self.isMinimized())

    def tray_activated(self, reason):
        log.info('Tray activation: %s', reason)
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            # Restore after the native tray callback returns, so the shell
            # does not keep focus on a popup or notification-area window.
            QTimer.singleShot(0, self.show_window)

    def quit_app(self):
        if self.controller.audio.output and not self.smoke:
            reply = QMessageBox.question(self, 'Before quitting',
                'If Discord is routed through CABLE Input, change its output back to your headphones first. '
                'Quitting stops the voice bridge.\n\nQuit now?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.quitting = True
        self.timer.stop()
        if hasattr(self, 'retry_timer'):
            self.retry_timer.stop()
        if hasattr(self, 'test_process') and self.test_process.poll() is None:
            self.test_process.terminate()
            self.test_process.wait(timeout=5)
        self.controller.close()
        self.tray.hide()
        ctypes.windll.user32.UnregisterHotKey(int(self.winId()), 1)
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self.quitting:
            event.accept()
        else:
            self.hide()
            event.ignore()

    def nativeEvent(self, event_type, message):
        from ctypes import wintypes
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam == 1:
            self.toggle()
            return True, 0
        return super().nativeEvent(event_type, message)
