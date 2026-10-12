import numpy as np
import webrtcvad


class SpeechDetector:
    """Two consecutive 10 ms voiced frames plus an RMS noise floor."""
    def __init__(self, mode=2, floor=.003):
        self.vad = webrtcvad.Vad(mode)
        self.floor = floor
        self.pending = np.empty(0, np.float32)
        self.run = 0

    def set_floor(self, floor):
        if floor != self.floor:
            self.floor = floor
            self.run = 0
            self.pending = np.empty(0, np.float32)

    def feed(self, samples, rate=48000):
        mono = np.mean(samples, axis=1) if samples.ndim == 2 else samples
        # Capture is explicitly 48 kHz; WebRTC supports these additional rates.
        if rate not in (8000, 16000, 32000, 48000):
            raise ValueError('Speech input must use a supported WebRTC sample rate')
        self.pending = np.concatenate((self.pending, mono.astype(np.float32)))
        size = rate // 100
        detected = False
        while len(self.pending) >= size:
            frame, self.pending = self.pending[:size], self.pending[size:]
            pcm = (np.clip(frame, -1, 1) * 32767).astype('<i2').tobytes()
            voiced = np.sqrt(np.mean(frame * frame)) >= self.floor and self.vad.is_speech(pcm, rate)
            self.run = self.run + 1 if voiced else 0
            detected |= self.run >= 2
        return detected
