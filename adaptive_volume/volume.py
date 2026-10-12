import json
import time
from dataclasses import dataclass
from .config import data_dir


def all_sessions():
    from pycaw.utils import AudioUtilities, AudioSession
    from pycaw.api.audiopolicy import IAudioSessionControl2
    from pycaw.constants import EDataFlow, DEVICE_STATE
    sessions = []
    for device in AudioUtilities.GetAllDevices(data_flow=EDataFlow.eRender.value,
                                              device_state=DEVICE_STATE.ACTIVE.value):
        try:
            enum = device.AudioSessionManager.GetSessionEnumerator()
            for i in range(enum.GetCount()):
                session = AudioSession(enum.GetSession(i).QueryInterface(IAudioSessionControl2))
                sessions.append((device.id, session))
        except Exception:
            continue
    return sessions


@dataclass
class SessionState:
    volume: object
    baseline: float
    last: float
    acquired_at: float = 0.


class SpotifyVolume:
    def __init__(self, executable='spotify.exe', journal=True):
        self.executable = executable.lower()
        self.sessions = {}
        self.error = ''
        self.journal = data_dir() / 'volume-recovery.json' if journal else None
        self.recovery = {}
        if self.journal:
            try:
                self.recovery = json.loads(self.journal.read_text())
            except (OSError, ValueError):
                pass
        self.last_save = 0

    def refresh(self):
        found = set()
        for endpoint, session in all_sessions():
            try:
                process = session.Process
                if not process or process.name().lower() != self.executable or session.State == 2:
                    continue
                key = endpoint + '|' + session.InstanceIdentifier
                found.add(key)
                volume = session.SimpleAudioVolume
                if key not in self.sessions:
                    current = float(volume.GetMasterVolume())
                    previous = self.recovery.get(key)
                    if previous and abs(current - previous['last']) < .002:
                        current = previous['baseline']
                        volume.SetMasterVolume(current, None)
                    self.sessions[key] = SessionState(volume, current, current, time.perf_counter())
                else:
                    self.sessions[key].volume = volume
            except Exception as exc:
                self.error = str(exc)
        self.sessions = {k: v for k, v in self.sessions.items() if k in found}

    def apply(self, gain):
        gain = max(0., min(1., gain))
        dirty = False
        now = time.perf_counter()
        for state in self.sessions.values():
            try:
                observed = float(state.volume.GetMasterVolume())
                if abs(observed - state.last) > .002:
                    # A user's mixer adjustment becomes the new normal level.
                    state.baseline = observed
                    dirty = True
                # A Spotify session discovered during an existing duck must
                # also fade in, rather than jump straight to the quiet level.
                age = max(0., min(1., (now - state.acquired_at) / .025))
                blend = age * age * (3 - 2 * age)
                session_gain = 1 + (gain - 1) * blend
                desired = min(state.baseline, state.baseline * session_gain)
                if abs(desired - observed) > .0001:
                    state.volume.SetMasterVolume(desired, None)
                    dirty = True
                state.last = desired
            except Exception as exc:
                self.error = str(exc)
        if self.journal and dirty:
            self._save()

    def _save(self):
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        temp = self.journal.with_suffix('.tmp')
        temp.write_text(json.dumps({k: {'baseline': v.baseline, 'last': v.last}
                                    for k, v in self.sessions.items()}))
        temp.replace(self.journal)

    def restore(self):
        self.apply(1.0)
        if self.journal:
            self._save()
