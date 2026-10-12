"""Bounded stereo FIFO. An empty queue never replays old audio."""
import threading
import numpy as np


class AudioBuffer:
    def __init__(self, rate=48000, delay_ms=50, channels=2):
        self.rate = rate
        self.delay = round(rate * delay_ms / 1000)
        self.channels = channels
        self.capacity = rate
        self.data = np.zeros((self.capacity, channels), np.float32)
        self.read = self.write = self.count = 0
        self.lock = threading.Lock()
        self.primed = False
        self.underruns = self.overruns = 0
        self.clock_adjustments = 0

    def push(self, block):
        with self.lock:
            if len(block) > self.capacity - self.count:
                self.overruns += 1
                self.read = self.write = self.count = 0
                self.primed = False
            block = block[-self.capacity:]
            n = len(block)
            split = min(n, self.capacity - self.write)
            self.data[self.write:self.write + split] = block[:split]
            self.data[:n - split] = block[split:]
            self.write = (self.write + n) % self.capacity
            self.count += n

    def pop(self, frames):
        out = np.zeros((frames, self.channels), np.float32)
        with self.lock:
            if not self.primed:
                if self.count < self.delay + frames:
                    return out
                self.primed = True
            consume = frames
            # Independent cable/headphone clocks drift. Gently interpolate a
            # few samples only outside a 20 ms jitter band, rather than letting
            # the queue grow indefinitely or periodically dropping voice blocks.
            if self.count > self.delay + frames + self.rate // 50:
                consume += min(4, self.count - self.delay - frames - self.rate // 50)
            elif self.count < self.delay + frames - self.rate // 50 and self.count >= frames:
                consume -= min(4, self.delay + frames - self.rate // 50 - self.count)
            n = min(consume, self.count)
            raw = np.zeros((n, self.channels), np.float32)
            split = min(n, self.capacity - self.read)
            raw[:split] = self.data[self.read:self.read + split]
            raw[split:n] = self.data[:n - split]
            if n == consume and consume != frames:
                positions = np.linspace(0, n - 1, frames)
                for channel in range(self.channels):
                    out[:, channel] = np.interp(positions, np.arange(n), raw[:, channel])
                self.clock_adjustments += consume - frames
            else:
                out[:min(n, frames)] = raw[:frames]
            self.read = (self.read + n) % self.capacity
            self.count -= n
            if n < consume:
                self.underruns += 1
                self.primed = False
        return out

    def queued_seconds(self):
        with self.lock:
            return self.count / self.rate
