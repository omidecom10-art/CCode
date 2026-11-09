"""Shared drawing helpers: font lookup (works on Windows, macOS, Linux/CI), cover-crop, text wrapping."""
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = {
    True: ["C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"],
    False: ["C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"],
}


@lru_cache(maxsize=64)
def font(size: int, bold: bool = False):
    for path in FONT_CANDIDATES[bold]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)  # Pillow's bundled font as a last resort


def hex_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cover(img: Image.Image, w: int, h: int, focus_y: float = 0.5) -> Image.Image:
    """Scale and crop to fill w x h (like CSS object-fit: cover)."""
    scale = max(w / img.width, h / img.height)
    im = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (im.width - w) // 2
    top = int((im.height - h) * focus_y)
    return im.crop((left, top, left + w, top + h))


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int):
    words, lines, line = text.split(), [], ""
    for word in words:
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=fnt) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit_text(draw, text, max_width, max_lines, start, minimum, bold=True):
    """Largest font size (start down to minimum) that fits text in max_lines."""
    for size in range(start, minimum - 1, -2):
        f = font(size, bold)
        lines = wrap(draw, text, f, max_width)
        if len(lines) <= max_lines:
            return f, lines
    f = font(minimum, bold)
    return f, wrap(draw, text, f, max_width)[:max_lines]
