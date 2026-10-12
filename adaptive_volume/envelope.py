"""Deterministic ducking policy; no Windows or GUI dependencies."""
from dataclasses import dataclass
import math


@dataclass
class Envelope:
    quiet: float = .25
    attack: float = .025
    hold: float = 1.1
    release: float = .25
    gain: float = 1.0

    def __post_init__(self):
        self.deadlines = {}
        self.enabled = False
        self._target = 1.0
        self._start_gain = 1.0
        self._start_time = 0.0
        self._duration = self.release

    def pulse(self, reason: str, audible_end: float):
        self.deadlines[reason] = max(self.deadlines.get(reason, 0), audible_end + self.hold)

    def sustain(self, reason: str, active: bool):
        if active:
            self.deadlines[reason] = math.inf
        else:
            self.deadlines.pop(reason, None)

    def clear(self):
        self.deadlines.clear()

    def reasons(self, now):
        self.deadlines = {k: v for k, v in self.deadlines.items() if v > now}
        return sorted(self.deadlines) if self.enabled else []

    def value(self, now):
        reasons = self.reasons(now)
        target = max(0., min(1., self.quiet)) if reasons else 1.0
        if target != self._target:
            # Finish evaluating the old ramp before changing direction.
            self.gain = self._evaluate(now)
            self._start_gain = self.gain
            self._start_time = now
            self._duration = self.attack if target < self.gain else self.release
            self._target = target
        self.gain = self._evaluate(now)
        return self.gain

    def _evaluate(self, now):
        t = min(1., max(0., (now - self._start_time) / self._duration))
        if t == 1.:
            return self._target
        t = t * t * (3 - 2 * t)
        return self._start_gain + (self._target - self._start_gain) * t
