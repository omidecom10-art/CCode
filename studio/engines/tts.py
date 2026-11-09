"""Voiceover. 'kokoro' runs the open Kokoro TTS model locally through the hyperframes CLI (no API key);
'silent' writes silence of the estimated length, for CI and tests. Swap in any TTS API by adding a provider."""
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 24000
WORDS_PER_SECOND = 2.6


def synthesize(text: str, out: Path, provider: str = "kokoro", voice: str = "am_michael", speed: float = 1.05) -> float:
    """Write a wav for one line and return its duration in seconds."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if provider == "kokoro" and shutil.which("npx"):
        safe = text.replace('"', "'")
        cmd = f'npx -y hyperframes tts "{safe}" --voice {voice} --speed {speed} -o "{out}"'
        subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=300)
        if out.exists():
            data, sr = sf.read(out, dtype="float32")
            return len(data) / sr
        raise RuntimeError(f"Kokoro TTS produced no audio for: {text[:60]}")
    seconds = max(1.2, len(text.split()) / WORDS_PER_SECOND)
    sf.write(out, np.zeros(int(seconds * SAMPLE_RATE), dtype="float32"), SAMPLE_RATE)
    return seconds
