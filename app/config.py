from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from environs import Env

@dataclass()
class AiGuard:
    action: str
    chunk_chars: int
    buffer_tokens: int
    window_chars: int
    ttfb_deadline_ms: float

@dataclass
class Config:
    aiguard: AiGuard


def load_config(path: Optional[str|Path] = Path(__file__).parent / '.env') -> Config:
    env = Env()
    env.read_env(path)
    return Config(aiguard=AiGuard(
        action=env.str("AIGUARD_ACTION"),
        chunk_chars=env.int("AIGUARD_CHUNK_CHARS"),
        buffer_tokens=env.int("AIGUARD_BUFFER_TOKENS"),
        window_chars=env.int("AIGUARD_WINDOW_CHARS"),
        ttfb_deadline_ms=env.float("AIGUARD_TTFB_DEADLINE_MS")
    ))