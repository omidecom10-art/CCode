"""Tests for watermark detection and removal."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest


@pytest.fixture
def sample_image_with_watermark(tmp_path):
    """Create a test image with a fake watermark in the corner."""
    img = np.full((480, 640, 3), 200, dtype=np.uint8)
    cv2.putText(img, "WATERMARK", (450, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    path = str(tmp_path / "watermarked.png")
    cv2.imwrite(path, img)
    return path


@pytest.fixture
def sample_image_with_subtitles(tmp_path):
    """Create a test image with fake subtitles at the bottom."""
    img = np.full((480, 640, 3), 100, dtype=np.uint8)
    cv2.putText(img, "This is a subtitle line", (50, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    path = str(tmp_path / "subtitled.png")
    cv2.imwrite(path, img)
    return path


def test_detect_watermark_regions(sample_image_with_watermark):
    from tools.watermark_remover import detect_watermark_regions
    regions = detect_watermark_regions(sample_image_with_watermark, search_area="corners")
    assert isinstance(regions, list)


def test_remove_watermark_inpaint(sample_image_with_watermark, tmp_path):
    from models.schemas import WatermarkRegion
    from tools.watermark_remover import remove_watermark_inpaint
    region = WatermarkRegion(x=440, y=5, width=190, height=35, confidence=0.9)
    out = str(tmp_path / "cleaned.png")
    result = remove_watermark_inpaint(sample_image_with_watermark, [region], out)
    assert Path(result).exists()


def test_detect_subtitles(sample_image_with_subtitles):
    from tools.watermark_remover import detect_subtitles
    regions = detect_subtitles(sample_image_with_subtitles)
    assert isinstance(regions, list)


def test_remove_subtitles_from_image(sample_image_with_subtitles, tmp_path):
    from tools.watermark_remover import remove_subtitles_from_image
    out = str(tmp_path / "no_subs.png")
    result = remove_subtitles_from_image(sample_image_with_subtitles, out)
    assert Path(result).exists()
