import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import comtypes
import sounddevice as sd
from adaptive_volume.volume import all_sessions

comtypes.CoInitialize()
out = {'devices': [], 'sessions': []}
for i, d in enumerate(sd.query_devices()):
    if sd.query_hostapis(d['hostapi'])['name'] == 'Windows WASAPI':
        out['devices'].append({'index': i, **dict(d)})
for endpoint, session in all_sessions():
    try:
        out['sessions'].append({'endpoint': endpoint, 'pid': session.ProcessId,
                               'name': session.Process.name() if session.Process else 'System',
                               'volume': session.SimpleAudioVolume.GetMasterVolume(),
                               'state': session.State})
    except Exception:
        pass
print(json.dumps(out, indent=2))
