import json
from pathlib import Path

import pytest
from PIL import Image

from conftest import HAS_FFMPEG
from studio.checks import check_video_file
from studio.engines import static_ads, video


def test_static_ad_renders_both_placements(kit, good_copy, tmp_path):
    paths = static_ads.render(good_copy.static_ads[0], kit, tmp_path)
    sizes = {p.name: Image.open(p).size for p in paths}
    assert sizes == {"A1_feed.png": (1080, 1350), "A1_story.png": (1080, 1920)}


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_video_editor_cuts_to_the_voiceover(kit, good_copy, tmp_path):
    mp4, planned, probe = video.render(good_copy.video, kit, tmp_path, tts_provider="silent")
    plan = json.loads((tmp_path / "edit_plan.json").read_text())
    assert len(plan["segments"]) == len(good_copy.video.beats) + 1  # beats + end card
    assert check_video_file(probe, planned) == []
    assert mp4.exists() and (tmp_path / "V1_poster.jpg").exists()


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_video_editor_works_with_a_relative_output_folder(kit, good_copy, tmp_path, monkeypatch):
    # Regression: ffmpeg's concat list resolves relative paths from its own folder.
    monkeypatch.chdir(tmp_path)
    mp4, planned, probe = video.render(good_copy.video, kit, Path("rel_out") / "video", tts_provider="silent")
    assert check_video_file(probe, planned) == []
