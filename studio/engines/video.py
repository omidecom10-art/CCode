"""Video editor: cuts a vertical ad from a voiceover and a b-roll library.

1. Voiceover: one TTS clip per beat, so every line's exact length is known.
2. Edit plan (EDL): each beat gets its b-roll for exactly the length of its line (+ a short pad);
   an end card with the product, offer and CTA closes the ad.
3. Render with ffmpeg: Ken Burns motion on each still (alternating push-in / pull-out), caption overlay,
   segments concatenated, voiceover muxed in. Every segment shares one codec, so concat is lossless.
4. Probe the result with ffprobe; studio/checks.py verifies size, audio and duration against the plan.
Video clips in the catalog ('type': 'clip') are trimmed instead of animated.
"""
import json
import subprocess
from pathlib import Path
from typing import List

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

from ..data import BrandKit
from ..schemas import VideoScript
from . import tts
from .graphics import cover, fit_text, font, hex_rgb, wrap

W, H, FPS = 1080, 1920, 30
PAD = 0.25          # breath after each line
END_CARD = 2.6      # seconds


def _run(cmd: List[str]):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd[:6])}... {r.stderr[-600:]}")


def _caption_png(text: str, path: Path, colors: dict):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f, lines = fit_text(d, text, W - 200, 2, 76, 54)
    line_h = int(f.size * 1.18)
    box_h = line_h * len(lines) + 56
    top = int(H * 0.66)
    widest = max(d.textlength(line, font=f) for line in lines)
    d.rounded_rectangle(((W - widest) / 2 - 40, top, (W + widest) / 2 + 40, top + box_h), radius=26, fill=(20, 20, 20, 205))
    for i, line in enumerate(lines):
        d.text((W / 2, top + 28 + i * line_h + line_h / 2), line, font=f, fill=colors["light_text"], anchor="mm")
    img.save(path)


def _end_card(kit: BrandKit, script: VideoScript, path: Path):
    colors = {k: hex_rgb(v) for k, v in kit.brand["colors"].items()}
    img = Image.new("RGB", (W, H), colors["background"])
    product = Image.open(kit.product_image).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 1050), fill=colors["primary"])
    card = product.copy()
    card.thumbnail((W - 260, 900))  # whole product as a card, never cropped
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, card.width, card.height), radius=32, fill=255)
    img.paste(card, ((W - card.width) // 2, (1050 - card.height) // 2), mask)
    d.text((W / 2, 1160), kit.brand["wordmark"], font=font(44, True), fill=colors["primary"], anchor="mm")
    f, lines = fit_text(d, script.end_card, W - 160, 2, 72, 52)
    y = 1250
    for line in lines:
        d.text((W / 2, y), line, font=f, fill=colors["text"], anchor="mm")
        y += int(f.size * 1.2)
    ofont = font(36, True)
    for line in wrap(d, kit.brand["offer"], ofont, W - 220)[:2]:
        d.text((W / 2, y + 40), line, font=ofont, fill=colors["accent"], anchor="mm")
        y += 48
    cta_font = font(46, True)
    cw = d.textlength(kit.brand["cta"], font=cta_font) + 120
    d.rounded_rectangle(((W - cw) / 2, y + 100, (W + cw) / 2, y + 196), radius=18, fill=colors["primary"])
    d.text((W / 2, y + 148), kit.brand["cta"], font=cta_font, fill=colors["light_text"], anchor="mm")
    img.save(path, quality=92)


def _segment(still: Path, caption: Path, seconds: float, out: Path, push_in: bool):
    frames = max(1, round(seconds * FPS))
    step = 0.14 / frames
    z = f"min(1+{step}*on,1.14)" if push_in else f"max(1.14-{step}*on,1)"
    vf = (f"[0:v]scale={W * 3 // 2}:{H * 3 // 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}[bg];"
          f"[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(still), "-loop", "1", "-i", str(caption),
          "-filter_complex", vf, "-map", "[v]", "-frames:v", str(frames), "-r", str(FPS),
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)])


def _clip_segment(clip: Path, caption: Path, seconds: float, out: Path):
    """Real video b-roll: trim to the line's length, cover-crop to 9:16, overlay the caption."""
    vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}[bg];"
          f"[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-t", f"{seconds:.3f}", "-i", str(clip), "-loop", "1", "-i", str(caption),
          "-filter_complex", vf, "-map", "[v]", "-an", "-frames:v", str(max(1, round(seconds * FPS))),
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)])


def render(script: VideoScript, kit: BrandKit, out_dir: Path, tts_provider: str = "kokoro", voice: str = "am_michael"):
    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    colors = {k: hex_rgb(v) for k, v in kit.brand["colors"].items()}
    broll = {b["id"]: b for b in kit.broll}

    # 1. voiceover per beat
    plan, audio, sr = [], [], tts.SAMPLE_RATE
    for i, beat in enumerate(script.beats, 1):
        wav = work / f"vo_{i}.wav"
        speech = tts.synthesize(beat.line, wav, tts_provider, voice)
        data, sr = sf.read(wav, dtype="float32")
        data = data.mean(axis=1) if data.ndim > 1 else data
        audio.append(np.concatenate([data, np.zeros(int(PAD * sr), dtype="float32")]))
        plan.append({"beat": i, "line": beat.line, "caption": beat.caption, "broll_id": beat.broll_id,
                     "seconds": round(speech + PAD, 3)})
    audio.append(np.zeros(int(END_CARD * sr), dtype="float32"))
    vo = np.concatenate(audio)
    peak = float(np.abs(vo).max()) or 1.0
    sf.write(work / "voiceover.wav", vo * (0.9 / peak) if peak > 0.001 else vo, sr)

    # 2. render segments from the edit plan
    segs = []
    for p in plan:
        item = broll.get(p["broll_id"]) or kit.broll[0]
        cap = work / f"cap_{p['beat']}.png"
        _caption_png(p["caption"], cap, colors)
        seg = work / f"seg_{p['beat']}.mp4"
        if item.get("type") == "clip":
            _clip_segment(kit.root / "assets" / item["path"], cap, p["seconds"], seg)
        else:
            still = work / f"still_{p['beat']}.jpg"
            cover(Image.open(kit.root / "assets" / item["path"]).convert("RGB"), 1440, 2560).save(still, quality=92)
            _segment(still, cap, p["seconds"], seg, push_in=p["beat"] % 2 == 1)
        segs.append(seg)
    card = work / "end_card.jpg"
    _end_card(kit, script, card)
    blank = work / "blank.png"
    Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
    end_seg = work / "seg_end.mp4"
    _segment(card, blank, END_CARD, end_seg, push_in=True)
    segs.append(end_seg)
    plan.append({"beat": "end", "line": "", "caption": script.end_card, "broll_id": "end_card", "seconds": END_CARD})

    # 3. concat + mux (concat resolves relative paths from the list file's folder, so write absolute ones)
    (work / "concat.txt").write_text("".join(f"file '{s.resolve().as_posix()}'\n" for s in segs), encoding="utf-8")
    silent = work / "video_silent.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "concat.txt"), "-c", "copy", str(silent)])
    out = out_dir / f"{script.id}_9x16.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(work / "voiceover.wav"),
          "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out)])
    poster = out_dir / f"{script.id}_poster.jpg"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.0", "-i", str(out), "-frames:v", "1", "-q:v", "3", str(poster)])

    total = round(sum(p["seconds"] for p in plan), 2)
    (out_dir / "edit_plan.json").write_text(json.dumps({"total_seconds": total, "segments": plan}, indent=2), encoding="utf-8")
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(out)],
                                      capture_output=True, text=True).stdout)
    return out, total, probe
