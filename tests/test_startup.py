from types import SimpleNamespace
import time
from adaptive_volume.controller import Controller
from adaptive_volume import startup


def fake_controller(worker=None):
    controller = Controller.__new__(Controller)
    controller.want_enabled = True
    controller.error = ''
    controller.audio = SimpleNamespace(worker=worker, settings=SimpleNamespace(buffered=True),
        input=None, output=None, last_render=time.perf_counter(), last_capture=time.perf_counter())
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
