from dataclasses import asdict, dataclass
import json
from pathlib import Path
import os
import sys


def data_dir() -> Path:
    override = os.environ.get('ADAPTIVE_VOLUME_DATA')
    if override:
        return Path(override)
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / 'data'
    return Path(__file__).resolve().parent.parent / 'data'


@dataclass
class Settings:
    quiet_percent: int = 25
    buffer_ms: int = 50
    attack_ms: int = 25
    hold_seconds: float = 1.1
    release_seconds: float = .25
    vad_mode: int = 2
    min_voice_db: int = -40
    buffered: bool = False
    auto_enable: bool = True
    output_name: str = ''
    cable_name: str = ''
    discord_exe: str = 'discord.exe'

    @classmethod
    def load(cls):
        path = data_dir() / 'settings.json'
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
            obj = cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})
            obj.quiet_percent = max(0, min(100, int(obj.quiet_percent)))
            obj.buffer_ms = max(0, min(250, int(obj.buffer_ms)))
            obj.vad_mode = max(0, min(3, int(obj.vad_mode)))
            obj.min_voice_db = max(-70, min(-10, int(obj.min_voice_db)))
            # These timings are part of the agreed behaviour, not arbitrary JSON values.
            obj.attack_ms, obj.hold_seconds, obj.release_seconds = 25, 1.1, .25
            return obj
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self):
        path = data_dir() / 'settings.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(asdict(self), indent=2), encoding='utf-8')
        temp.replace(path)
