"""Tests for video editor (FFmpeg wrapper). These tests need actual video files."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_video(tmp_path):
    """Create a minimal test video using FFmpeg."""
    out = tmp_path / "test.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(out),
    ], capture_output=True)
    if not out.exists():
        pytest.skip("FFmpeg not available")
    return str(out)


def test_trim_video(sample_video, tmp_path):
    from tools.video_editor import trim_video
    out = str(tmp_path / "trimmed.mp4")
    result = trim_video(sample_video, out, "00:00:01", "00:00:03")
    assert Path(result).exists()


def test_add_text_overlay(sample_video, tmp_path):
    from tools.video_editor import add_text_overlay
    out = str(tmp_path / "overlay.mp4")
    result = add_text_overlay(sample_video, out, "TEST TEXT", "center")
    assert Path(result).exists()


def test_resize_video(sample_video, tmp_path):
    from tools.video_editor import resize_video
    out = str(tmp_path / "resized.mp4")
    result = resize_video(sample_video, out, 640, 480)
    assert Path(result).exists()


def test_extract_frames(sample_video, tmp_path):
    from tools.video_editor import extract_frames
    frames_dir = str(tmp_path / "frames")
    frames = extract_frames(sample_video, frames_dir, fps=1)
    assert len(frames) >= 4
