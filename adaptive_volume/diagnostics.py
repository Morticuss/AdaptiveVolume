"""Synthetic, local timing test. Never opens Discord or a microphone."""
import json
import os
import time
import wave
import numpy as np
import sounddevice as sd
from .config import data_dir
from .buffer import AudioBuffer
from .speech import SpeechDetector
from .process_audio import ProcessCapture


def synthetic_speech():
    from comtypes.client import CreateObject
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'synthetic-speech.wav'
    if not path.exists():
        voice = CreateObject('SAPI.SpVoice', dynamic=True)
        stream = CreateObject('SAPI.SpFileStream', dynamic=True)
        stream.Open(str(path), 3, False)
        voice.AudioOutputStream = stream
        voice.Speak('The music should become quiet while I am speaking. After a short pause it should return gently.', 0)
        stream.Close()
    with wave.open(str(path), 'rb') as f:
        if f.getsampwidth() != 2:
            raise ValueError('Synthetic voice fixture must be 16-bit PCM')
        rate, channels = f.getframerate(), f.getnchannels()
        raw = np.frombuffer(f.readframes(f.getnframes()), '<i2').reshape(-1, channels).astype(np.float32)/32768
    raw = raw.mean(axis=1)
    samples = np.interp(np.arange(round(len(raw)*48000/rate))*rate/48000, np.arange(len(raw)), raw)
    peak = max(.01, float(np.max(np.abs(samples))))
    samples = (samples * (.06/peak)).astype(np.float32)
    return np.repeat(samples[:, None], 2, axis=1)


def run_timing(output_device, delay_ms=50):
    """Measures generated samples → FIFO → render → own-process loopback.

    The virtual-cable capture path is deliberately outside this measurement.
    """
    fifo = AudioBuffer(delay_ms=delay_ms)
    detector = SpeechDetector()
    source = np.concatenate((np.zeros((24000, 2), np.float32), synthetic_speech(),
                             np.zeros((4800, 2), np.float32)))
    captured = []
    captured_start = [None]
    voice_detected_at = [None]
    voiced_offset = [None]
    processed = 0

    def observed(block, end):
        if captured_start[0] is None:
            captured_start[0] = end - len(block)/48000
        captured.append(block.copy())

    def output(out, frames, timing, status):
        out[:] = fifo.pop(frames)

    capture = ProcessCapture(os.getpid(), observed)
    capture.start()
    capture.ready.wait(6)
    if capture.error:
        capture.stop()
        raise RuntimeError(capture.error)
    stream = None
    try:
        stream = sd.OutputStream(device=output_device, samplerate=48000, channels=2,
                                 blocksize=480, latency='low', dtype='float32', callback=output)
        stream.start()
        start = scheduled = time.perf_counter()
        for offset in range(0, len(source), 480):
            wait = scheduled - time.perf_counter()
            if wait > 0:
                time.sleep(wait)
            block = source[offset:offset+480]
            now = time.perf_counter()
            fifo.push(block)
            if detector.feed(block) and voice_detected_at[0] is None:
                voice_detected_at[0] = now
                voiced_offset[0] = offset / 48000
            scheduled += len(block)/48000
        time.sleep(.25)
        reported = stream.latency
    finally:
        if stream:
            stream.stop()
            stream.close()
        capture.stop()
    if not captured:
        raise RuntimeError('No rendered samples captured')
    from numpy.fft import rfft, irfft
    a = source.mean(axis=1)
    b = np.concatenate(captured).mean(axis=1)
    size = 1 << (len(a)+len(b)-1).bit_length()
    correlation = irfft(rfft(b, size)*np.conj(rfft(a, size)), size)
    # Restrict lag to the plausible first 2 seconds rather than unrelated peaks.
    lag = int(np.argmax(correlation[:96000]))
    measured = lag/48000 + captured_start[0] - start
    speech_onset = int(np.argmax(np.max(np.abs(source), axis=1) > .003))/48000
    detection_delay = voice_detected_at[0] - (start+speech_onset) if voice_detected_at[0] else None
    margin = measured - detection_delay - .025 if detection_delay is not None else None
    report = {
        'configured_buffer_ms': delay_ms,
        'measured_added_ms': round(measured*1000, 2),
        'scope': 'Synthetic FIFO to own-process digital render; excludes VB-CABLE input, Discord and acoustic latency',
        'reported_render_ms': round(reported*1000, 2),
        'speech_detected': voice_detected_at[0] is not None,
        'speech_detection_ms_from_signal_onset': round(detection_delay*1000, 2) if detection_delay is not None else None,
        'estimated_25ms_fade_margin_ms': round(margin*1000, 2) if margin is not None else None,
        'fade_before_onset_in_this_test': margin >= 0 if margin is not None else False,
        'underruns': fifo.underruns, 'overruns': fifo.overruns,
        'note': 'One synthetic utterance; not a guarantee for other speakers. Windows volume ramp verified separately.'}
    data_dir().mkdir(parents=True, exist_ok=True)
    (data_dir() / 'latency-test.json').write_text(json.dumps(report, indent=2))
    return report


def run_comparison(output_device, delay_ms=50):
    baseline = run_timing(output_device, 0)
    buffered = run_timing(output_device, delay_ms)
    buffered['baseline_path_ms'] = baseline['measured_added_ms']
    buffered['buffered_path_ms'] = buffered['measured_added_ms']
    added = buffered['buffered_path_ms'] - buffered['baseline_path_ms']
    buffered['measured_added_ms'] = round(added, 2)
    buffered['scope'] = '0 ms versus configured FIFO, same output and own-process digital capture; excludes VB-CABLE and Discord'
    detection = buffered['speech_detection_ms_from_signal_onset']
    margin = added - detection - 25 if detection is not None else None
    buffered['estimated_25ms_fade_margin_ms'] = round(margin, 2) if margin is not None else None
    buffered['fade_before_onset_in_this_test'] = margin >= 0 if margin is not None else False
    buffered['note'] = 'Estimated margin uses the added buffer, not common output/capture latency. Not an acoustic or complete Discord-path measurement.'
    (data_dir() / 'latency-test.json').write_text(json.dumps(buffered, indent=2))
    return buffered
