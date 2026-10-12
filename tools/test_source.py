"""Standalone audio source for capture tests; never uses Discord."""
import argparse
import numpy as np
import sounddevice as sd
import time

parser = argparse.ArgumentParser()
parser.add_argument('--device', type=int)
parser.add_argument('--seconds', type=float, default=8)
args = parser.parse_args()
rate = 48000
phase = 0

def callback(out, frames, timing, status):
    global phase
    t = (np.arange(frames) + phase) / rate
    phase += frames
    # Low-volume coded bursts for correlation, rather than loud test tones.
    gate = ((t % 1.0) < .15).astype(float)
    signal = (.015 * np.sin(2 * np.pi * 731 * t) * gate).astype(np.float32)
    out[:] = signal[:, None]

with sd.OutputStream(device=args.device, samplerate=rate, channels=2, blocksize=480,
                     dtype='float32', callback=callback):
    time.sleep(args.seconds)
