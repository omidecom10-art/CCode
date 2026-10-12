from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from config.settings import get_settings
from utils.file_helpers import ensure_output_dir


class VideoEditError(Exception):
    pass


def _run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    settings = get_settings()
    cmd = [settings.ffmpeg_path] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise VideoEditError(f"FFmpeg failed: {result.stderr[:500]}")
    return result


def trim_video(input_path: str, output_path: str, start: str, end: str) -> str:
    """Trim video between start and end timestamps (HH:MM:SS or seconds)."""
    _run_ffmpeg(["-y", "-i", input_path, "-ss", start, "-to", end, "-c", "copy", output_path])
    return output_path


def cut_segment(input_path: str, output_path: str, cut_start: str, cut_end: str) -> str:
    """Remove a segment from the middle of a video."""
    out_dir = ensure_output_dir("temp")
    part1 = str(out_dir / "part1.mp4")
    part2 = str(out_dir / "part2.mp4")

    _run_ffmpeg(["-y", "-i", input_path, "-to", cut_start, "-c", "copy", part1])
    _run_ffmpeg(["-y", "-i", input_path, "-ss", cut_end, "-c", "copy", part2])

    concat_file = out_dir / "concat.txt"
    concat_file.write_text(f"file '{part1}'\nfile '{part2}'\n")

    _run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", output_path])
    return output_path


def merge_videos(input_paths: list[str], output_path: str) -> str:
    """Concatenate multiple videos into one."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in input_paths:
            f.write(f"file '{p}'\n")
        concat_file = f.name

    _run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_path])
    Path(concat_file).unlink(missing_ok=True)
    return output_path


def add_text_overlay(
    input_path: str,
    output_path: str,
    text: str,
    position: str = "bottom",
    font_size: int = 48,
    color: str = "white",
    bg_color: str = "black@0.5",
    start_time: float = 0,
    duration: float | None = None,
) -> str:
    """Add text overlay to video."""
    pos_map = {
        "top": "x=(w-text_w)/2:y=50",
        "center": "x=(w-text_w)/2:y=(h-text_h)/2",
        "bottom": "x=(w-text_w)/2:y=h-text_h-50",
        "top-left": "x=50:y=50",
        "top-right": "x=w-text_w-50:y=50",
        "bottom-left": "x=50:y=h-text_h-50",
        "bottom-right": "x=w-text_w-50:y=h-text_h-50",
    }
    pos_expr = pos_map.get(position, pos_map["bottom"])
    escaped_text = text.replace("'", "\\'").replace(":", "\\:")

    enable = f":enable='between(t,{start_time},{start_time + duration})'" if duration else ""
    drawtext = (
        f"drawtext=text='{escaped_text}':{pos_expr}:fontsize={font_size}"
        f":fontcolor={color}:box=1:boxcolor={bg_color}:boxborderw=10{enable}"
    )

    _run_ffmpeg(["-y", "-i", input_path, "-vf", drawtext, "-codec:a", "copy", output_path])
    return output_path


def extract_audio(input_path: str, output_path: str) -> str:
    _run_ffmpeg(["-y", "-i", input_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", output_path])
    return output_path


def replace_audio(video_path: str, audio_path: str, output_path: str) -> str:
    _run_ffmpeg([
        "-y", "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0", "-shortest", output_path,
    ])
    return output_path


def resize_video(input_path: str, output_path: str, width: int, height: int) -> str:
    _run_ffmpeg([
        "-y", "-i", input_path,
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "copy", output_path,
    ])
    return output_path


def change_speed(input_path: str, output_path: str, speed: float) -> str:
    """Change video speed. speed=2.0 means 2x faster, 0.5 means half speed."""
    video_filter = f"setpts={1/speed}*PTS"
    audio_filter = f"atempo={speed}"
    if speed > 2.0:
        audio_filter = f"atempo=2.0,atempo={speed/2.0}"
    elif speed < 0.5:
        audio_filter = f"atempo=0.5,atempo={speed/0.5}"

    _run_ffmpeg([
        "-y", "-i", input_path,
        "-filter:v", video_filter, "-filter:a", audio_filter, output_path,
    ])
    return output_path


def extract_frames(input_path: str, output_dir: str, fps: int = 1) -> list[str]:
    """Extract frames from video at given fps rate."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    pattern = str(Path(output_dir) / "frame_%04d.png")
    _run_ffmpeg(["-y", "-i", input_path, "-vf", f"fps={fps}", pattern])
    return sorted(str(p) for p in Path(output_dir).glob("frame_*.png"))


def frames_to_video(frame_dir: str, output_path: str, fps: int = 30, audio_source: str | None = None) -> str:
    """Reassemble frames into a video, optionally with audio from the original."""
    pattern = str(Path(frame_dir) / "frame_%04d.png")
    args = ["-y", "-framerate", str(fps), "-i", pattern]
    if audio_source:
        args += ["-i", audio_source, "-map", "0:v", "-map", "1:a", "-shortest"]
    args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", output_path]
    _run_ffmpeg(args)
    return output_path
