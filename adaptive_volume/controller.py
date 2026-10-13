import threading
import time
import queue
import logging
from .envelope import Envelope
from .core_audio_worker import CoreAudioWorker
from .audio import AudioEngine

log = logging.getLogger(__name__)


class Controller:
    def __init__(self, settings):
        self.settings = settings
        self.envelope = Envelope(quiet=settings.quiet_percent / 100,
            attack=settings.attack_ms / 1000, hold=settings.hold_seconds,
            release=settings.release_seconds)
        self.commands = queue.Queue()
        self.stop_event = threading.Event()
        self.enabled = False
        self.want_enabled = False
        self.gain = 1.
        self.reasons = []
        self.spotify_count = 0
        self.error = ''
        self.routing_status = 'Discord output must be CABLE Input in buffered mode; headphones in unbuffered mode.'
        self.audio = AudioEngine(settings, self._speech)
        self.cable_signal_time = 0.
        self.silent_bridge_since = None
        self.last_health_log = 0.
        self.last_signal_recovery = float('-inf')
        self.volume_worker = None
        self.thread = threading.Thread(target=self._volume_loop, name='Spotify volume control', daemon=True)
        self.thread.start()

    def _speech(self, audible_end):
        if self.enabled:
            self.commands.put(('pulse', 'Discord speech', audible_end))

    def set_enabled(self, enabled):
        self.want_enabled = enabled
        if enabled and not self.audio.worker:
            if not self.audio.start():
                self.error = self.audio.status + (': ' + self.audio.fault if self.audio.fault else '')
                return False
        self.enabled = enabled
        if enabled:
            self.error = ''
        self.commands.put(('enabled', enabled))
        # Pausing ducking must keep the voice bridge audible.
        return True

    def maintain_audio(self):
        """Retry late devices at login and recover streams after disconnection."""
        if not self.want_enabled:
            return
        audio = self.audio
        failed = (audio.output is not None and not audio.output.active) or (
            audio.input is not None and not audio.input.active)
        if audio.worker and audio.settings.buffered:
            now = time.perf_counter()
            failed = failed or (audio.last_render > 0 and now - audio.last_render > 2) or (
                audio.last_capture > 0 and now - audio.last_capture > 2)
            # Active WASAPI callbacks can continue with zeros after device
            # initialization at login. Compare actual cable signal with both
            # ends of our bridge, independently of the speech threshold.
            missing_signal = self._silent_bridge(now)
            if missing_signal and now - self.last_signal_recovery >= 15:
                failed = True
                self.last_signal_recovery = now
                log.warning('Recovering silent bridge: cable_signal_age=%.2f capture_signal_age=%.2f render_signal_age=%.2f',
                            now - self.cable_signal_time, now - audio.last_capture_signal,
                            now - audio.last_render_signal)
            if now - self.last_health_log >= 30:
                self.last_health_log = now
                log.info('Bridge health: input_active=%s output_active=%s capture_age=%.2f render_age=%.2f cable_signal_age=%.2f metrics=%s fault=%s',
                         audio.input.active if audio.input else False,
                         audio.output.active if audio.output else False,
                         now - audio.last_capture, now - audio.last_render,
                         now - self.cable_signal_time, audio.metrics(), audio.fault)
        if failed:
            log.warning('Restarting audio bridge automatically')
            self.silent_bridge_since = None
            self.set_enabled(False)
            audio.stop()
            self.want_enabled = True
        if not audio.worker:
            # PortAudio caches the endpoint list. Refresh only with our streams
            # closed, so devices enabled/connected after login can be discovered.
            import sounddevice as sd
            try:
                sd._terminate()
                sd._initialize()
                self.set_enabled(True)
            except Exception as exc:
                log.exception('Audio device retry failed')
                self.error = f'Waiting for audio devices; retrying automatically: {exc}'

    def _silent_bridge(self, now):
        audio = self.audio
        # Give stream startup and the configured FIFO time to settle. A quiet
        # Discord channel alone must never trigger a restart.
        expected = self.cable_signal_time > 0 and now - self.cable_signal_time < 2
        missing = (now - audio.last_capture_signal > 2 or
                   now - audio.last_render_signal > 2)
        if now - audio.started_at < 3 or not expected or not missing:
            self.silent_bridge_since = None
            return False
        if self.silent_bridge_since is None:
            self.silent_bridge_since = now
        return now - self.silent_bridge_since >= 3


    def quiet(self, percent):
        self.settings.quiet_percent = percent
        self.commands.put(('quiet', percent / 100))

    def preview(self):
        self.commands.put(('preview',))

    def restart_audio(self):
        was_enabled = self.enabled
        self.set_enabled(False)
        self.audio.stop()
        return self.set_enabled(True) if was_enabled else True

    def _volume_loop(self):
        volume = CoreAudioWorker(self.settings)
        self.volume_worker = volume
        preview_until = 0
        try:
            while not self.stop_event.wait(.002):
                now = time.perf_counter()
                try:
                    while True:
                        command = self.commands.get_nowait()
                        match command:
                            case ('pulse', reason, end):
                                self.envelope.pulse(reason, end)
                            case ('sustain', reason, active):
                                self.envelope.sustain(reason, active)
                            case ('quiet', level):
                                self.envelope.quiet = level
                            case ('enabled', value):
                                self.envelope.enabled = value
                                if not value:
                                    self.envelope.clear()
                            case ('preview',):
                                preview_until = now + 2
                                self.envelope.sustain('Volume preview', True)
                except queue.Empty:
                    pass
                if preview_until and now >= preview_until:
                    self.envelope.sustain('Volume preview', False)
                    preview_until = 0
                self.envelope.enabled = self.enabled or now < preview_until
                if self.audio.fault and 'stopped' in self.audio.fault.lower():
                    self.envelope.clear()
                self.gain = self.envelope.value(now)
                self.reasons = self.envelope.reasons(now)
                snapshot = volume.update(self.gain)
                self.spotify_count = snapshot.get('spotify_count', self.spotify_count)
                self.routing_status = snapshot.get('routing_status', self.routing_status)
                self.cable_signal_time = snapshot.get('cable_signal_time', self.cable_signal_time)
                if snapshot.get('error'):
                    self.error = snapshot['error']
        except Exception as exc:
            log.exception('Volume control failed')
            self.error = f'Volume control failed: {exc}'
        finally:
            volume.close()

    def close(self):
        self.want_enabled = False
        self.enabled = False
        self.audio.stop()
        self.stop_event.set()
        self.thread.join(8)
