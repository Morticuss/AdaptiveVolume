"""Stress main-thread GC and kill the COM helper while VB-CABLE plays.

Uses a quiet tone. Quit the packaged app before running this check.
"""
import json
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))


def main():
    import gc
    from adaptive_volume.config import Settings
    from adaptive_volume.controller import Controller
    from adaptive_volume.runtime_log import configure
    configure()
    settings = Settings(**json.loads((root / 'dist/AdaptiveVolume/data/settings.json').read_text()))
    assert settings.buffered
    controller = Controller(settings)
    tone = None
    try:
        assert controller.set_enabled(True), controller.error
        tone = subprocess.Popen([sys.executable, str(root / 'tools/test_bridge_recovery.py'), '--source'])
        deadline = time.perf_counter() + 5
        while controller.audio.last_render_signal == 0 and time.perf_counter() < deadline:
            time.sleep(.05)
        assert controller.audio.last_render_signal > 0
        assert 'comtypes' not in sys.modules, 'COM objects leaked into the audio/UI process'
        worker = controller.volume_worker
        deadline = time.perf_counter() + 4
        while (not worker.process or not controller.routing_status.startswith('Discord')) and time.perf_counter() < deadline:
            time.sleep(.05)
        assert worker.process and worker.process.is_alive()
        pid = worker.process.pid
        count = 0
        deadline = time.perf_counter() + 3
        while time.perf_counter() < deadline:
            cycle = []
            cycle.append(cycle)
            del cycle
            gc.collect()
            count += 1
            time.sleep(.01)
        audio = controller.audio
        input_stream, output_stream = audio.input, audio.output
        worker.process.terminate()  # Controlled simulation of a native COM crash.
        deadline = time.perf_counter() + 4
        maximum_callback_age = 0.
        while time.perf_counter() < deadline:
            now = time.perf_counter()
            maximum_callback_age = max(maximum_callback_age, now - audio.last_capture, now - audio.last_render)
            assert audio.input is input_stream and audio.output is output_stream
            assert audio.input.active and audio.output.active
            assert now - audio.last_render_signal < .5
            if worker.process and worker.process.pid != pid and worker.process.is_alive():
                break
            time.sleep(.01)
        assert worker.process and worker.process.pid != pid and worker.process.is_alive()
        assert maximum_callback_age < .5
        report = {'forced_main_thread_collections': count, 'helper_restarted': True,
                  'voice_streams_not_reopened': True, 'render_signal_continued': True,
                  'maximum_callback_age_seconds': maximum_callback_age,
                  'scope': 'Real VB-CABLE tone; forcibly terminated isolated Windows audio helper'}
        (root / 'data/worker-isolation-test.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    finally:
        if tone:
            tone.wait(timeout=20)
        controller.close()


if __name__ == '__main__':
    main()
