"""Static ad engine: renders approved copy into finished PNGs in the brand's colours.
Two placements per ad: feed 1080x1350 (4:5) and story 1080x1920 (9:16)."""
import math
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFilter

from ..data import BrandKit
from ..schemas import StaticAd
from .graphics import fit_text, font, hex_rgb, wrap

SIZES = {"feed": (1080, 1350), "story": (1080, 1920)}


def _shadowed(base: Image.Image, xy, text, fnt, fill):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((xy[0] + 2, xy[1] + 3), text, font=fnt, fill=(0, 0, 0, 140))
    layer = layer.filter(ImageFilter.GaussianBlur(3))
    base.alpha_composite(layer)
    ImageDraw.Draw(base).text(xy, text, font=fnt, fill=fill)


def _star(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill):
    pts = []
    for k in range(10):
        ang = math.pi / 2 + k * math.pi / 5
        rad = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy - rad * math.sin(ang)))
    d.polygon(pts, fill=fill)


def _text_block(d, ad, x, y, maxw, scale, placement, colors, draw=True) -> int:
    """Headline, subhead and optional testimonial. Returns the y where the block ends."""
    s = lambda n: max(12, int(n * scale))  # noqa: E731
    hfont, hlines = fit_text(d, ad.headline, maxw, 2, s(92), s(60))
    for line in hlines:
        if draw:
            d.text((x, y), line, font=hfont, fill=colors["primary"])
        y += int(hfont.size * 1.1)
    y += s(14)
    sfont = font(s(38 if placement == "feed" else 42))
    for line in wrap(d, ad.subhead, sfont, maxw)[:3]:
        if draw:
            d.text((x, y), line, font=sfont, fill=colors["text"])
        y += int(sfont.size * 1.32)
    if ad.testimonial:
        y += s(18)
        qfont = font(s(30 if placement == "feed" else 36))
        quote = f"“{ad.testimonial.text.strip(chr(34))}”"
        if draw:
            for i in range(5):  # stars drawn as shapes: not every font has a star glyph
                _star(d, x + s(16) + i * s(38), y + s(16), s(16), colors["accent"])
        y += s(44)
        for line in wrap(d, quote, qfont, maxw)[:3]:
            if draw:
                d.text((x, y), line, font=qfont, fill=colors["text"])
            y += int(qfont.size * 1.3)
        if draw:
            d.text((x, y), "Verified buyer", font=font(s(24)), fill=colors["primary"])
        y += s(30)
    return y


def render(ad: StaticAd, kit: BrandKit, out_dir: Path) -> List[Path]:
    colors = {k: hex_rgb(v) for k, v in kit.brand["colors"].items()}
    product = Image.open(kit.product_image).convert("RGB")
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for placement, (W, H) in SIZES.items():
        photo_h = int(H * (0.52 if placement == "feed" else 0.55))
        canvas = Image.new("RGBA", (W, H), colors["background"] + (255,))
        # brand-colour panel with the whole product photo as a card (a tall product never gets its top cut off)
        ImageDraw.Draw(canvas).rectangle((0, 0, W, photo_h), fill=colors["primary"])
        card = product.copy()
        card.thumbnail((W - 200, photo_h - 150))
        mask = Image.new("L", card.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, card.width, card.height), radius=28, fill=255)
        cx, cy = (W - card.width) // 2, (photo_h - card.height) // 2 + 30
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((cx + 8, cy + 14, cx + card.width + 8, cy + card.height + 14), radius=28, fill=(0, 0, 0, 110))
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
        canvas.paste(card, (cx, cy), mask)
        _shadowed(canvas, (64, 48), kit.brand["wordmark"], font(34, True), colors["light_text"] + (255,))

        d = ImageDraw.Draw(canvas)
        x, maxw = 64, W - 128
        bar_y = H - (150 if placement == "feed" else 230)
        # shrink the text block until it clears the bottom bar (long quotes must never hit the offer pill)
        for scale in (1.0, 0.92, 0.85, 0.78, 0.72, 0.66):
            if _text_block(d, ad, x, photo_h + 24, maxw, scale, placement, colors, draw=False) <= bar_y - 28:
                break
        _text_block(d, ad, x, photo_h + 24, maxw, scale, placement, colors, draw=True)

        # bottom bar: offer pill (left) and CTA button (right)
        ofont = font(28, True)
        offer = kit.brand["offer"]
        ow = d.textlength(offer, font=ofont)
        if ow > W - 128 - 280:  # long offer wraps above the button
            ofont = font(25, True)
            ow = d.textlength(offer, font=ofont)
        d.rounded_rectangle((x, bar_y, x + ow + 44, bar_y + 64), radius=32, fill=colors["accent"])
        d.text((x + 22, bar_y + 32), offer, font=ofont, fill=colors["light_text"], anchor="lm")
        cfont = font(34, True)
        cw = d.textlength(ad.cta, font=cfont) + 72
        d.rounded_rectangle((W - 64 - cw, bar_y - 8, W - 64, bar_y + 72), radius=14, fill=colors["primary"])
        d.text((W - 64 - cw / 2, bar_y + 32), ad.cta, font=cfont, fill=colors["light_text"], anchor="mm")

        path = out_dir / f"{ad.id}_{placement}.png"
        canvas.convert("RGB").save(path, optimize=True)
        paths.append(path)
    return paths
