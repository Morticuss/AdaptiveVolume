"""Live WASAPI regression: late cable audio and active-but-silent capture.

Quit Adaptive Volume first. Uses a quiet generated tone, never a Discord call.
"""
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import sounddevice as sd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))


def source():
    device = next(i for i, d in enumerate(sd.query_devices())
                  if 'cable input' in d['name'].lower() and
                  sd.query_hostapis(d['hostapi'])['name'] == 'Windows WASAPI')
    samples = np.arange(48000 * 14)
    tone = (.01 * np.sin(2 * np.pi * 440 * samples / 48000)).astype('float32')
    sd.play(np.column_stack([tone, tone]), samplerate=48000, device=device, blocking=True)


def main():
    from adaptive_volume.config import Settings
    from adaptive_volume.controller import Controller
    from adaptive_volume.runtime_log import configure
    configure()
    settings = Settings(**json.loads((root / 'dist/AdaptiveVolume/data/settings.json').read_text()))
    assert settings.buffered
    controller = Controller(settings)
    audio = controller.audio
    capture = audio._capture
    broken_generation = [None]

    def silent_capture(data, frames, timing, flags):
        # Preserve callbacks and active flags while simulating a stale driver
        # capture session. Reopening creates a healthy stream generation.
        if audio.started_at == broken_generation[0]:
            data = np.zeros_like(data)
        capture(data, frames, timing, flags)

    audio._capture = silent_capture
    process = None
    try:
        assert controller.set_enabled(True), controller.error
        broken_generation[0] = audio.started_at
        time.sleep(4)  # App starts before the cable's render client.
        controller.maintain_audio()
        assert audio.started_at == broken_generation[0], 'Idle bridge restarted'
        process = subprocess.Popen([sys.executable, __file__, '--source'])
        deadline = time.perf_counter() + 12
        observed_silent_active = False
        while time.perf_counter() < deadline:
            controller.maintain_audio()
            if controller.cable_signal_time and audio.started_at == broken_generation[0]:
                assert audio.input.active and audio.output.active
                assert audio.last_capture_signal == audio.last_render_signal == 0
                observed_silent_active = True
            if audio.started_at != broken_generation[0] and audio.last_render_signal > audio.started_at:
                break
            time.sleep(.2)
        assert observed_silent_active, 'Did not exercise silent active streams with real cable signal'
        assert audio.started_at != broken_generation[0], 'Bridge did not automatically reopen'
        assert audio.last_capture_signal > audio.started_at
        assert audio.last_render_signal > audio.started_at
        report = {'late_source': True, 'active_silent_capture_injected': True,
                  'automatic_recovery': True, 'real_capture_and_render_signal_restored': True,
                  'metrics': audio.metrics(), 'scope': 'Synthetic tone; not a reboot or Discord call'}
        (root / 'data/bridge-recovery-test.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    finally:
        if process:
            process.wait(timeout=20)
        controller.close()


if __name__ == '__main__':
    source() if '--source' in sys.argv else main()
