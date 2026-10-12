from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

CHEAP_MODEL = "claude-haiku-5-5"
EXPENSIVE_MODEL = "claude-sonnet-5-5"


@dataclass
class Settings:
    api_key: str = ""
    default_model: str = CHEAP_MODEL
    complex_model: str = EXPENSIVE_MODEL
    ffmpeg_path: str = "ffmpeg"
    output_dir: str = "output"
    lama_model: str = "lama"

    @property
    def output_path(self) -> Path:
        p = Path(self.output_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        load_dotenv()
        _settings = Settings(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            default_model=os.getenv("DEFAULT_MODEL", CHEAP_MODEL),
            complex_model=os.getenv("COMPLEX_MODEL", EXPENSIVE_MODEL),
            ffmpeg_path=os.getenv("FFMPEG_PATH", "ffmpeg"),
            output_dir=os.getenv("OUTPUT_DIR", "output"),
        )
    return _settings
