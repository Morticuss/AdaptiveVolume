import queue
import threading
import time
import logging
import numpy as np
import psutil
import sounddevice as sd
from .buffer import AudioBuffer
from .speech import SpeechDetector
from .process_audio import ProcessCapture

log = logging.getLogger(__name__)


def devices():
    return [{'index': i, **dict(d)} for i, d in enumerate(sd.query_devices())
            if sd.query_hostapis(d['hostapi'])['name'] == 'Windows WASAPI']


def root_pid(executable):
    candidates = []
    for proc in psutil.process_iter(['pid', 'ppid', 'name']):
        if (proc.info['name'] or '').lower() == executable.lower():
            candidates.append(proc.info)
    ids = {p['pid'] for p in candidates}
    roots = [p['pid'] for p in candidates if p['ppid'] not in ids]
    return min(roots) if roots else None


class AudioEngine:
    def __init__(self, settings, on_speech):
        self.settings = settings
        self.on_speech = on_speech
        self.status = 'Audio not started'
        self.fault = ''
        self.capture_latency = self.render_latency = 0.
        self.buffer = None
        self.input = self.output = None
        self.analysis = queue.Queue(maxsize=100)
        self.stop_event = threading.Event()
        self.worker = None
        self.discord = None
        self.last_render = 0
        self.last_capture = 0
        self.rms = 0.
        self.last_level_time = 0.
        self.dropped_analysis = 0
        self.last_capture_signal = self.last_render_signal = 0.
        self.started_at = 0.

    def start(self):
        self.stop_event.clear()
        self.fault = ''
        self.last_capture = self.last_render = time.perf_counter()
        self.started_at = self.last_capture
        self.last_capture_signal = self.last_render_signal = 0.
        if self.settings.buffered:
            available = devices()
            inputs = [d for d in available if d['max_input_channels'] >= 2 and
                      'cable output' in d['name'].lower()]
            outputs = [d for d in available if d['max_output_channels'] >= 2 and
                       'cable' not in d['name'].lower()]
            source = next((d for d in inputs if d['name'] == self.settings.cable_name), None)
            if source is None and not self.settings.cable_name and len(inputs) == 1:
                source = inputs[0]
            target = next((d for d in outputs if d['name'] == self.settings.output_name), None)
            if not source or not target:
                self.status = 'Choose CABLE Output and your headphones in Audio settings'
                log.warning('Bridge devices unavailable: cable=%r output=%r', self.settings.cable_name, self.settings.output_name)
                return False
            try:
                self.buffer = AudioBuffer(delay_ms=self.settings.buffer_ms)
                self.input = sd.InputStream(device=source['index'], samplerate=48000,
                    channels=2, dtype='float32', blocksize=480, latency='low',
                    extra_settings=sd.WasapiSettings(auto_convert=True), callback=self._capture)
                self.output = sd.OutputStream(device=target['index'], samplerate=48000,
                    channels=2, dtype='float32', blocksize=480, latency='low',
                    extra_settings=sd.WasapiSettings(auto_convert=True), callback=self._render)
                self.capture_latency, self.render_latency = self.input.latency, self.output.latency
                self.input.start()
                self.output.start()
                self.status = 'Buffered audio bridge running · check Discord output is CABLE Input'
                log.info('Bridge started: cable=%r output=%r capture_ms=%.1f render_ms=%.1f', source['name'], target['name'], self.capture_latency * 1000, self.render_latency * 1000)
            except Exception as exc:
                log.exception('Bridge startup failed')
                self.fault = str(exc)
                self.stop()
                self.status = 'Audio bridge failed · use Recovery'
                return False
        else:
            self.status = 'Unbuffered · waiting for Discord desktop'
        self.worker = threading.Thread(target=self._analyse, name='Speech analysis', daemon=True)
        self.worker.start()
        return True

    def _capture(self, data, frames, timing, flags):
        now = time.perf_counter()
        self.last_capture = now
        if np.max(np.abs(data), initial=0.) > .000001:
            self.last_capture_signal = now
        if flags:
            self.fault = f'Input stream: {flags}'
        self.buffer.push(data)
        if self.buffer.overruns:
            self.fault = 'Audio queue overflowed; check the selected output device or restart the bridge.'
        predicted_delay = self.buffer.queued_seconds() + self.render_latency
        self._enqueue('discord', data.copy(), now + predicted_delay)

    def _render(self, out, frames, timing, flags):
        self.last_render = time.perf_counter()
        if flags:
            self.fault = f'Output stream: {flags}'
        out[:] = self.buffer.pop(frames)
        if np.max(np.abs(out), initial=0.) > .000001:
            self.last_render_signal = self.last_render

    def _enqueue(self, source, data, audible_end):
        try:
            self.analysis.put_nowait((source, data, audible_end))
        except queue.Full:
            self.dropped_analysis += 1

    def _fault(self, msg):
        self.fault = msg

    def _analyse(self):
        detector = SpeechDetector(self.settings.vad_mode)
        next_scan = 0
        while not self.stop_event.is_set():
            now = time.perf_counter()
            if now >= next_scan:
                self._maintain_processes()
                next_scan = now + 2
                if self.output and (not self.output.active or now - self.last_render > 1):
                    self.fault = 'Headphone playback stopped. Use Recovery to restore direct voice output.'
                    self.status = 'Playback unavailable'
                if self.input and (not self.input.active or now - self.last_capture > 1):
                    self.fault = 'Cable capture stopped. Use Recovery to restore direct voice output.'
            try:
                source, data, end = self.analysis.get(timeout=.05)
            except queue.Empty:
                continue
            # Backlogged analysis must not cause delayed, apparently random ducking.
            if time.perf_counter() - end > .15:
                continue
            if source == 'discord':
                self.rms = float(np.sqrt(np.mean(data * data)))
                self.last_level_time = time.perf_counter()
            detector.set_floor(10 ** (self.settings.min_voice_db / 20))
            if detector.feed(data):
                self.on_speech(end)

    def _maintain_processes(self):
        if self.settings.buffered:
            return
        pid = root_pid(self.settings.discord_exe)
        if self.discord and (self.discord.pid != pid or self.discord.error):
            self.discord.stop()
            self.discord = None
        if pid and not self.discord:
            self.discord = ProcessCapture(pid,
                lambda block, end: self._enqueue('discord', block, end), self._fault)
            self.discord.start()
        self.status = 'Unbuffered · Discord captured' if pid else 'Unbuffered · waiting for Discord desktop'

    def stop(self):
        log.info('Stopping audio: status=%s fault=%s', self.status, self.fault)
        self.stop_event.set()
        for stream in (self.input, self.output):
            if stream:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass
        self.input = self.output = None
        if self.discord:
            self.discord.stop()
        self.discord = None
        if self.worker and self.worker is not threading.current_thread():
            self.worker.join(3)
        self.worker = None
        while not self.analysis.empty():
            try:
                self.analysis.get_nowait()
            except queue.Empty:
                break

    def metrics(self):
        rms = self.rms if time.perf_counter() - self.last_level_time < .5 else 0.
        return {'voice_level_dbfs': round(max(-90., 20 * float(np.log10(max(rms, 1e-9)))) , 1),
                'minimum_voice_dbfs': self.settings.min_voice_db,
                'configured_buffer_ms': self.settings.buffer_ms if self.settings.buffered else 0,
                'reported_capture_ms': round(self.capture_latency * 1000, 1),
                'reported_render_ms': round(self.render_latency * 1000, 1),
                'queued_ms': round(self.buffer.queued_seconds() * 1000, 1) if self.buffer else 0,
                'underruns': self.buffer.underruns if self.buffer else 0,
                'overruns': self.buffer.overruns if self.buffer else 0,
                'clock_adjustment_samples': self.buffer.clock_adjustments if self.buffer else 0,
                'analysis_drops': self.dropped_analysis}
