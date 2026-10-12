"""Short, reversible integration test on Spotify's Windows session only."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import time
import comtypes
from adaptive_volume.volume import SpotifyVolume, all_sessions
from adaptive_volume.envelope import Envelope

comtypes.CoInitialize()
before = {(endpoint, s.InstanceIdentifier): float(s.SimpleAudioVolume.GetMasterVolume())
          for endpoint, s in all_sessions()}
volume = SpotifyVolume()
volume.refresh()
if not volume.sessions:
    raise SystemExit('Spotify has no audio session')
e = Envelope()
e.enabled = True
start = time.perf_counter()
e.pulse('Synthetic voice trigger', start + .2)
samples = []
others_unchanged = True
try:
    while time.perf_counter() - start < 3.4:
        now = time.perf_counter()
        gain = e.value(now)
        volume.apply(gain)
        observed = next(iter(volume.sessions.values())).volume.GetMasterVolume()
        samples.append((round((now - start) * 1000, 2), gain, observed))
        if .1 < now - start < .105:
            during = {(endpoint, s.InstanceIdentifier): float(s.SimpleAudioVolume.GetMasterVolume())
                      for endpoint, s in all_sessions()}
            others_unchanged = all(abs(during[k] - v) < .002 for k, v in before.items()
                if k in during and k[0] + '|' + k[1] not in volume.sessions)
        time.sleep(.002)
finally:
    volume.restore()
after = {(endpoint, s.InstanceIdentifier): float(s.SimpleAudioVolume.GetMasterVolume())
         for endpoint, s in all_sessions()}
unchanged = all(abs(after[k] - v) < .002 for k, v in before.items() if k in after)
result = {'spotify_sessions': len(volume.sessions), 'all_original_levels_restored': unchanged,
          'other_sessions_unchanged_while_ducked': others_unchanged,
          'minimum_observed_volume': min(s[2] for s in samples),
          'fade_samples_first_40ms': [s for s in samples if s[0] < 40],
          'policy_hold_ms': 1100, 'policy_release_ms': 250}
Path('data').mkdir(exist_ok=True)
Path('data/spotify-test.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
assert unchanged
assert others_unchanged
assert abs(samples[-1][1] - 1) < .001
