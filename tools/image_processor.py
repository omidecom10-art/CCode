from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def resize_image(input_path: str, output_path: str, width: int, height: int) -> str:
    img = Image.open(input_path)
    img = img.resize((width, height), Image.LANCZOS)
    img.save(output_path)
    return output_path


def resize_for_platform(input_path: str, output_path: str, platform: str) -> str:
    """Resize image for common ad platforms."""
    sizes = {
        "instagram-story": (1080, 1920),
        "instagram-post": (1080, 1080),
        "facebook-feed": (1200, 628),
        "tiktok": (1080, 1920),
        "youtube-thumbnail": (1280, 720),
        "twitter": (1200, 675),
    }
    w, h = sizes.get(platform, (1080, 1080))
    return resize_image(input_path, output_path, w, h)


def add_text_to_image(
    input_path: str,
    output_path: str,
    text: str,
    position: str = "bottom",
    font_size: int = 48,
    color: str = "white",
    bg_color: str | None = None,
) -> str:
    img = Image.open(input_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    w, h = img.size
    positions = {
        "top": ((w - text_w) // 2, 30),
        "center": ((w - text_w) // 2, (h - text_h) // 2),
        "bottom": ((w - text_w) // 2, h - text_h - 30),
    }
    x, y = positions.get(position, positions["bottom"])

    if bg_color:
        padding = 10
        draw.rectangle([x - padding, y - padding, x + text_w + padding, y + text_h + padding], fill=bg_color)

    draw.text((x, y), text, font=font, fill=color)
    result = Image.alpha_composite(img, overlay).convert("RGB")
    result.save(output_path)
    return output_path


def crop_image(input_path: str, output_path: str, left: int, top: int, right: int, bottom: int) -> str:
    img = Image.open(input_path)
    img = img.crop((left, top, right, bottom))
    img.save(output_path)
    return output_path


def adjust_brightness_contrast(
    input_path: str, output_path: str,
    brightness: float = 1.0, contrast: float = 1.0,
) -> str:
    img = cv2.imread(input_path)
    result = cv2.convertScaleAbs(img, alpha=contrast, beta=(brightness - 1.0) * 127)
    cv2.imwrite(output_path, result)
    return output_path


def create_thumbnail(video_path: str, output_path: str, timestamp: str = "00:00:01") -> str:
    from utils.file_helpers import get_frame_at
    frame_path = get_frame_at(video_path, timestamp)
    Image.open(str(frame_path)).save(output_path)
    return output_path


def batch_process(
    input_dir: str,
    output_dir: str,
    operation: str,
    **kwargs,
) -> list[str]:
    """Apply the same operation to all images in a directory."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ops = {
        "resize": resize_image,
        "brightness_contrast": adjust_brightness_contrast,
        "add_text": add_text_to_image,
    }
    func = ops.get(operation)
    if not func:
        raise ValueError(f"Unknown operation: {operation}")

    results = []
    for p in sorted(Path(input_dir).iterdir()):
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            out = str(Path(output_dir) / p.name)
            func(str(p), out, **kwargs)
            results.append(out)
    return results
