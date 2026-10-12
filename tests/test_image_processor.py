"""Tests for image processor."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture
def sample_image(tmp_path):
    img = Image.fromarray(np.full((480, 640, 3), 150, dtype=np.uint8))
    path = str(tmp_path / "test.png")
    img.save(path)
    return path


def test_resize_image(sample_image, tmp_path):
    from tools.image_processor import resize_image
    out = str(tmp_path / "resized.png")
    result = resize_image(sample_image, out, 320, 240)
    assert Path(result).exists()
    img = Image.open(result)
    assert img.size == (320, 240)


def test_add_text_to_image(sample_image, tmp_path):
    from tools.image_processor import add_text_to_image
    out = str(tmp_path / "text.png")
    result = add_text_to_image(sample_image, out, "Hello World", "center")
    assert Path(result).exists()


def test_crop_image(sample_image, tmp_path):
    from tools.image_processor import crop_image
    out = str(tmp_path / "cropped.png")
    result = crop_image(sample_image, out, 10, 10, 300, 200)
    assert Path(result).exists()
    img = Image.open(result)
    assert img.size == (290, 190)


def test_adjust_brightness_contrast(sample_image, tmp_path):
    from tools.image_processor import adjust_brightness_contrast
    out = str(tmp_path / "adjusted.png")
    result = adjust_brightness_contrast(sample_image, out, brightness=1.5, contrast=1.2)
    assert Path(result).exists()
