import numpy as np
from adaptive_volume.envelope import Envelope
from adaptive_volume.buffer import AudioBuffer
from adaptive_volume.speech import SpeechDetector


def test_ramp_hold_and_release_follow_audible_speech():
    e = Envelope()
    e.enabled = True
    e.pulse('voice', 10.05)
    assert e.value(10) == 1
    assert .25 < e.value(10.0125) < 1
    assert abs(e.value(10.025) - .25) < 1e-8
    assert e.value(11.149) == .25
    assert e.value(11.151) == .25
    assert .25 < e.value(11.276) < 1
    assert e.value(11.402) == 1


def test_simultaneous_triggers_do_not_stack_and_new_speech_reverses():
    e = Envelope()
    e.enabled = True
    e.pulse('voice', 1)
    e.sustain('round', True)
    e.value(1)
    assert e.value(1.1) == .25
    e.sustain('round', False)
    e.value(3.1)
    mid = e.value(3.225)
    e.pulse('voice', 3.225)
    assert e.value(3.225) == mid
    assert e.value(3.255) == .25


def test_pause_clears_triggers_and_never_boosts():
    e = Envelope(quiet=2)
    e.enabled = True
    e.sustain('round', True)
    assert e.value(1) <= 1
    e.quiet = .1
    e.value(2)
    e.value(3)
    e.enabled = False
    assert abs(e.value(3) - .1) < 1e-8
    assert e.value(4) == 1


def test_buffer_delay_order_and_empty_output():
    b = AudioBuffer(rate=1000, delay_ms=50)
    for i in range(5):
        b.push(np.full((10, 2), i + 1, np.float32))
        assert not b.pop(10).any()
    b.push(np.full((10, 2), 6, np.float32))
    assert np.all(b.pop(10) == 1)
    # Clock correction can stretch the last few samples while draining.
    for i in range(20):
        if not b.pop(10).any():
            break
    else:
        raise AssertionError('An exhausted buffer replayed old audio')
    assert b.underruns == 1


def test_buffer_wraparound_preserves_samples():
    b = AudioBuffer(rate=1000, delay_ms=0)
    for i in range(200):
        block = np.full((13, 2), i, np.float32)
        b.push(block)
        assert np.array_equal(b.pop(13), block)


def test_silence_and_isolated_click_do_not_trigger():
    detector = SpeechDetector()
    assert not detector.feed(np.zeros((4800, 2), np.float32))
    block = np.zeros((480, 2), np.float32)
    block[0] = .5
    assert not detector.feed(block)
    assert not detector.feed(np.zeros((480, 2), np.float32))
