from types import SimpleNamespace
import time
from adaptive_volume.controller import Controller
from adaptive_volume import startup


def fake_controller(worker=None):
    controller = Controller.__new__(Controller)
    controller.want_enabled = True
    controller.error = ''
    controller.cable_signal_time = 0.
    controller.silent_bridge_since = None
    controller.last_signal_recovery = float('-inf')
    controller.last_health_log = time.perf_counter()
    controller.audio = SimpleNamespace(worker=worker, settings=SimpleNamespace(buffered=True),
        input=None, output=None, last_render=time.perf_counter(), last_capture=time.perf_counter(),
        started_at=time.perf_counter(), last_capture_signal=0., last_render_signal=0.)
    calls = []
    controller.set_enabled = lambda value: calls.append(('enabled', value))
    controller.audio.stop = lambda: calls.append(('stop',))
    return controller, calls


def test_waiting_devices_retry_but_paused_does_not(monkeypatch):
    import sounddevice as sd
    calls = []
    monkeypatch.setattr(sd, '_terminate', lambda: calls.append('close'))
    monkeypatch.setattr(sd, '_initialize', lambda: calls.append('refresh'))
    controller, enabled = fake_controller()
    controller.maintain_audio()
    assert calls == ['close', 'refresh']
    assert enabled == [('enabled', True)]
    controller.want_enabled = False
    controller.maintain_audio()
    assert len(calls) == 2


def test_running_bridge_is_not_restarted_and_stalled_one_is(monkeypatch):
    import sounddevice as sd
    monkeypatch.setattr(sd, '_terminate', lambda: None)
    monkeypatch.setattr(sd, '_initialize', lambda: None)
    controller, calls = fake_controller(worker=object())
    controller.audio.input = controller.audio.output = SimpleNamespace(active=True)
    controller.maintain_audio()
    assert calls == []
    controller.audio.last_render -= 5
    def stop():
        calls.append(('stop',))
        controller.audio.worker = None
    controller.audio.stop = stop
    controller.maintain_audio()
    assert calls == [('enabled', False), ('stop',), ('enabled', True)]


def test_packaged_startup_quotes_paths_and_runs_in_tray(monkeypatch):
    monkeypatch.setattr(startup.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(startup.sys, 'executable', r'E:\A Folder\AdaptiveVolume.exe')
    assert startup.command() == '"E:\\A Folder\\AdaptiveVolume.exe" --tray'


def test_silent_active_bridge_recovers_when_cable_has_signal(monkeypatch):
    import sounddevice as sd
    monkeypatch.setattr(sd, '_terminate', lambda: None)
    monkeypatch.setattr(sd, '_initialize', lambda: None)
    controller, calls = fake_controller(worker=object())
    audio = controller.audio
    audio.input = audio.output = SimpleNamespace(active=True)
    audio.started_at = 90.
    controller.last_health_log = 100.
    clock = [100.]
    monkeypatch.setattr(time, 'perf_counter', lambda: clock[0])
    def tick(now):
        clock[0] = now
        audio.last_capture = audio.last_render = now
        controller.cable_signal_time = now
        controller.maintain_audio()
    def stop():
        calls.append(('stop',))
        audio.worker = None
    audio.stop = stop
    tick(100.)
    tick(102.)
    assert calls == []
    tick(103.)
    assert calls == [('enabled', False), ('stop',), ('enabled', True)]


def test_silence_and_forwarded_quiet_audio_do_not_restart():
    controller, _ = fake_controller(worker=object())
    controller.audio.started_at = 90.
    for now in range(100, 110):
        assert not controller._silent_bridge(now)
        controller.cable_signal_time = now
        controller.audio.last_capture_signal = controller.audio.last_render_signal = now
        assert not controller._silent_bridge(now)
    controller.cable_signal_time = 111.
    assert not controller._silent_bridge(111.)
    assert not controller._silent_bridge(115.)


def test_capture_working_but_render_silent_is_detected():
    controller, _ = fake_controller(worker=object())
    controller.audio.started_at = 90.
    for now in range(100, 104):
        controller.cable_signal_time = controller.audio.last_capture_signal = now
        assert controller._silent_bridge(now) == (now == 103)


def test_repeated_silent_recoveries_are_spaced_apart(monkeypatch):
    import sounddevice as sd
    monkeypatch.setattr(sd, '_terminate', lambda: None)
    monkeypatch.setattr(sd, '_initialize', lambda: None)
    controller, calls = fake_controller(worker=object())
    audio = controller.audio
    audio.input = audio.output = SimpleNamespace(active=True)
    audio.started_at = 90.
    controller.last_health_log = controller.last_signal_recovery = 100.
    controller.silent_bridge_since = 101.
    for now in (110., 115.):
        monkeypatch.setattr(time, 'perf_counter', lambda: now)
        audio.last_capture = audio.last_render = controller.cable_signal_time = now
        def stop():
            calls.append(('stop',))
            audio.worker = None
        audio.stop = stop
        controller.maintain_audio()
        if now == 110.:
            assert calls == []
    assert calls == [('enabled', False), ('stop',), ('enabled', True)]


def test_routing_ignores_old_inactive_discord_sessions(monkeypatch):
    from adaptive_volume import controller as module, volume
    from pycaw.utils import AudioUtilities
    controller, _ = fake_controller()
    controller.settings = SimpleNamespace(buffered=True, discord_exe='discord.exe')
    controller.routing_status = ''
    monkeypatch.setattr(AudioUtilities, 'GetAllDevices', lambda: [
        SimpleNamespace(id='cable', FriendlyName='CABLE Input'),
        SimpleNamespace(id='headphones', FriendlyName='Headphones')])
    process = SimpleNamespace(name=lambda: 'Discord.exe')
    monkeypatch.setattr(module, 'all_sessions', lambda: [
        ('headphones', SimpleNamespace(State=0, Process=process)),
        ('cable', SimpleNamespace(State=1, Process=process))])
    monkeypatch.setattr(volume, 'cable_peak', lambda: 0.)
    controller._check_routing()
    assert controller.routing_status == 'Discord cable routing detected'
