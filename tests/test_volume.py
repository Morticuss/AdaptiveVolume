import pytest
from adaptive_volume.volume import SpotifyVolume, SessionState
from types import SimpleNamespace


class FakeVolume:
    def __init__(self, current):
        self.current = current
        self.writes = []

    def GetMasterVolume(self):
        return self.current

    def SetMasterVolume(self, value, context):
        self.current = value
        self.writes.append(value)


def test_cable_meter_acquires_owned_interface_instead_of_aliasing(monkeypatch):
    from adaptive_volume.volume import cable_peak
    from pycaw.utils import AudioUtilities
    from pycaw.api.endpointvolume import IAudioMeterInformation
    acquired = []
    class Pointer:
        def QueryInterface(self, interface):
            acquired.append(interface)
            return SimpleNamespace(GetPeakValue=lambda: .25)
    device = SimpleNamespace(FriendlyName='CABLE Input (VB-Audio Virtual Cable)',
        EndpointVolume=SimpleNamespace(GetMute=lambda: False,
                                       GetMasterVolumeLevelScalar=lambda: 1.),
        _dev=SimpleNamespace(Activate=lambda *args: Pointer()))
    monkeypatch.setattr(AudioUtilities, 'GetAllDevices', lambda **kwargs: [device])
    assert cable_peak() == .25
    assert acquired == [IAudioMeterInformation]


def test_manual_change_is_respected_and_never_boosted():
    control = SpotifyVolume(journal=False)
    fake = FakeVolume(.8)
    control.sessions = {'spotify': SessionState(fake, .8, .8)}
    control.apply(.25)
    assert fake.current == pytest.approx(.2)
    fake.current = .4  # User changes Windows mixer while ducked.
    control.apply(.25)
    assert fake.current == pytest.approx(.1)
    control.restore()
    assert fake.current == pytest.approx(.4)
    control.apply(3)
    assert fake.current == pytest.approx(.4)


def test_mute_is_preserved_and_multiple_sessions_share_same_gain():
    control = SpotifyVolume(journal=False)
    muted, other = FakeVolume(0), FakeVolume(.6)
    control.sessions = {'muted': SessionState(muted, 0, 0),
                        'other': SessionState(other, .6, .6)}
    control.apply(.25)
    assert muted.current == 0
    assert other.current == pytest.approx(.15)
    control.restore()
    assert muted.current == 0
    assert other.current == pytest.approx(.6)


def test_crash_journal_round_trip(tmp_path, monkeypatch):
    import adaptive_volume.volume as module
    monkeypatch.setattr(module, 'data_dir', lambda: tmp_path)
    control = SpotifyVolume()
    fake = FakeVolume(.8)
    control.sessions = {'session': SessionState(fake, .8, .8)}
    control.apply(.25)
    recovered = SpotifyVolume()
    assert recovered.recovery['session']['baseline'] == pytest.approx(.8)
    assert recovered.recovery['session']['last'] == pytest.approx(.2)


def test_matching_crash_volume_is_restored_but_manual_change_is_preserved(tmp_path, monkeypatch):
    import adaptive_volume.volume as module
    import json
    from types import SimpleNamespace
    monkeypatch.setattr(module, 'data_dir', lambda: tmp_path)
    fake = FakeVolume(.2)
    session = SimpleNamespace(Process=SimpleNamespace(name=lambda: 'Spotify.exe'),
                              State=0, InstanceIdentifier='id', SimpleAudioVolume=fake)
    monkeypatch.setattr(module, 'all_sessions', lambda: [('endpoint', session)])
    path = tmp_path / 'volume-recovery.json'
    path.write_text(json.dumps({'endpoint|id': {'baseline': .8, 'last': .2}}))
    matching = SpotifyVolume()
    matching.refresh()
    assert fake.current == pytest.approx(.8)
    fake.current = .15
    changed = SpotifyVolume()
    changed.refresh()
    assert fake.current == pytest.approx(.15)


def test_journal_tracks_each_changed_volume_and_does_not_write_when_idle(tmp_path, monkeypatch):
    import adaptive_volume.volume as module
    import json
    monkeypatch.setattr(module, 'data_dir', lambda: tmp_path)
    fake = FakeVolume(.8)
    control = SpotifyVolume()
    control.sessions = {'session': SessionState(fake, .8, .8)}
    control.apply(.9)
    control.apply(.8)
    path = tmp_path / 'volume-recovery.json'
    assert json.loads(path.read_text())['session']['last'] == pytest.approx(.64)
    stamp = path.stat().st_mtime_ns
    control.apply(.8)
    assert path.stat().st_mtime_ns == stamp


def test_new_session_during_duck_fades_instead_of_jumping(monkeypatch):
    import adaptive_volume.volume as module
    clock = [100.]
    monkeypatch.setattr(module.time, 'perf_counter', lambda: clock[0])
    fake = FakeVolume(.8)
    control = SpotifyVolume(journal=False)
    control.sessions = {'new': SessionState(fake, .8, .8, acquired_at=100.)}
    control.apply(.25)
    assert fake.current == pytest.approx(.8)
    clock[0] = 100.0125
    control.apply(.25)
    assert .2 < fake.current < .8
    clock[0] = 100.0251
    control.apply(.25)
    assert fake.current == pytest.approx(.2)
