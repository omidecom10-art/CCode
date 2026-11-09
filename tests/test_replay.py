"""End to end without an API key: replay the recorded sample run through the whole pipeline."""
import json
import shutil

import pytest

from conftest import HAS_FFMPEG, ROOT
from studio import pipeline

CASSETTE = ROOT / "output" / "sample_run" / "llm_cassette.json"


@pytest.mark.skipif(not CASSETTE.exists(), reason="no recorded sample run yet")
def test_full_pipeline_replays_the_recorded_run(tmp_path):
    shutil.copy(CASSETTE, tmp_path / "llm_cassette.json")
    summary = pipeline.run(ROOT / "data" / "sample_brand", tmp_path, mode="replay", tts_provider="silent", skip_video=not HAS_FFMPEG)
    recorded = json.loads((ROOT / "output" / "sample_run" / "summary.json").read_text(encoding="utf-8"))
    assert summary["approved"] == recorded["approved"]
    assert summary["rounds"] == recorded["rounds"]
    assert (tmp_path / "REPORT.md").exists()
    for a in summary["assets"]:
        for f in a["files"]:
            assert (tmp_path / f).exists(), f
    # integrations had no credentials, so each wrote its dry-run payload
    assert (tmp_path / "integrations" / "slack.json").exists()
