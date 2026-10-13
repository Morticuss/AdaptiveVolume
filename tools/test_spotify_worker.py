"""Verify the isolated helper lowers and restores live Spotify volume."""
from pathlib import Path
import sys
import time
import json

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))


def main():
    from adaptive_volume.config import Settings
    from adaptive_volume.core_audio_worker import CoreAudioWorker
    from adaptive_volume.volume import all_sessions

    def levels():
        result = {}
        for endpoint, session in all_sessions():
            if session.Process and session.Process.name().lower() == 'spotify.exe':
                result[endpoint + '|' + session.InstanceIdentifier] = float(session.SimpleAudioVolume.GetMasterVolume())
        return result

    baseline = levels()
    assert baseline and any(value > .01 for value in baseline.values()), 'Spotify must have an audible session'
    worker = CoreAudioWorker(Settings())
    try:
        deadline = time.perf_counter() + 5
        while time.perf_counter() < deadline:
            snapshot = worker.update(1.)
            if snapshot.get('spotify_count'):
                break
            time.sleep(.01)
        assert snapshot.get('spotify_count'), snapshot
        for _ in range(40):
            worker.update(.5)
            time.sleep(.01)
        lowered = levels()
        assert all(abs(lowered[key] - value * .5) < .005 for key, value in baseline.items() if key in lowered)
    finally:
        worker.close()
    restored = levels()
    assert all(abs(restored[key] - value) < .005 for key, value in baseline.items() if key in restored)
    report = {'isolated_helper_lowered_spotify': True, 'shutdown_restored_original_volume': True,
              'sessions': len(baseline)}
    (root / 'data/spotify-worker-test.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
