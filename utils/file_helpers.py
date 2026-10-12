from __future__ import annotations

import json
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from config.settings import get_settings


def detect_media_type(path: str | Path) -> str:
    path = Path(path)
    ext = path.suffix.lower()
    if ext in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"}:
        return "video"
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}:
        return "image"
    return "unknown"


def ensure_output_dir(subdir: str = "") -> Path:
    settings = get_settings()
    p = settings.output_path / subdir if subdir else settings.output_path
    p.mkdir(parents=True, exist_ok=True)
    return p


@contextmanager
def temp_dir():
    with tempfile.TemporaryDirectory(prefix="adagent_") as d:
        yield Path(d)


def validate_video(path: str | Path) -> bool:
    settings = get_settings()
    try:
        result = subprocess.run(
            [settings.ffmpeg_path.replace("ffmpeg", "ffprobe"), "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(result.stdout)
        return bool(data.get("streams"))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return False


def get_video_info(path: str | Path) -> dict:
    settings = get_settings()
    result = subprocess.run(
        [settings.ffmpeg_path.replace("ffmpeg", "ffprobe"), "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return json.loads(result.stdout)


def get_frame_at(video_path: str | Path, timestamp: str = "00:00:01") -> Path:
    """Extract a single frame from a video. Returns path to the extracted image."""
    out = ensure_output_dir("frames")
    output_path = out / f"frame_{Path(video_path).stem}_{timestamp.replace(':', '')}.png"
    settings = get_settings()
    subprocess.run(
        [settings.ffmpeg_path, "-y", "-ss", timestamp, "-i", str(video_path),
         "-frames:v", "1", "-q:v", "2", str(output_path)],
        capture_output=True, text=True, timeout=30,
    )
    return output_path
