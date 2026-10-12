import numpy as np
from adaptive_volume.speech import SpeechDetector
from adaptive_volume.config import Settings


class MisclassifyingVad:
    def is_speech(self, pcm, rate):
        return True


def test_level_gate_blocks_noise_even_if_vad_calls_it_speech():
    detector = SpeechDetector(floor=10 ** (-40 / 20))
    detector.vad = MisclassifyingVad()
    assert not detector.feed(np.full((960, 2), .005, np.float32))  # -46 dBFS
    assert detector.feed(np.full((960, 2), .02, np.float32))  # -34 dBFS


def test_live_threshold_change_requires_two_fresh_frames():
    detector = SpeechDetector(floor=.01)
    detector.vad = MisclassifyingVad()
    frame = np.full((480, 2), .02, np.float32)
    assert not detector.feed(frame)
    detector.set_floor(.03)
    assert not detector.feed(frame)
    assert not detector.feed(frame)
    detector.set_floor(.01)
    assert not detector.feed(frame)
    assert detector.feed(frame)
    detector.set_floor(.01)  # Reapplying the unchanged threshold preserves detection.
    assert detector.feed(frame)


def test_threshold_persists_and_invalid_values_are_clamped(tmp_path, monkeypatch):
    monkeypatch.setenv('ADAPTIVE_VOLUME_DATA', str(tmp_path))
    settings = Settings(min_voice_db=-32)
    settings.save()
    assert Settings.load().min_voice_db == -32
    settings.min_voice_db = 4
    settings.save()
    assert Settings.load().min_voice_db == -10


def test_legacy_settings_keep_user_choices_and_adopt_discord_only_timings(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv('ADAPTIVE_VOLUME_DATA', str(tmp_path))
    (tmp_path / 'settings.json').write_text(json.dumps({'quiet_percent': 45,
        'min_voice_db': -30, 'buffered': True, 'output_name': 'Chosen headphones',
        'hold_seconds': 2, 'release_seconds': 1, 'game_profiles': {'Valorant': {}},
        'aion_exe': 'oldgame.exe'}))
    settings = Settings.load()
    assert (settings.quiet_percent, settings.min_voice_db, settings.output_name,
            settings.buffered) == (45, -30, 'Chosen headphones', True)
    assert (settings.hold_seconds, settings.release_seconds) == (1.1, .25)
    settings.save()
    saved = json.loads((tmp_path / 'settings.json').read_text())
    assert 'game_profiles' not in saved and 'aion_exe' not in saved
