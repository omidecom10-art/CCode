"""Deterministic checks that run before (and alongside) the reviewer agent. Cheap, explainable, and they
never get tired: length limits, exact offer/CTA, evidence ids that exist, numbers that match the evidence,
verbatim testimonials, forbidden phrases, competitor names, b-roll ids and video length."""
import re
from typing import Dict, List

from .data import BrandKit
from .schemas import AdCopy

WORDS_PER_SECOND = 2.6  # typical voiceover pace, used to estimate video length


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("’", "'").replace("“", '"').replace("”", '"')).strip()


def _numbers(s: str) -> List[str]:
    return re.findall(r"\d+(?:\.\d+)?", s.replace(",", ""))


def _phrase_hits(text: str, phrases: List[str]) -> List[str]:
    t = _norm(text)
    return [p for p in phrases if re.search(r"(?<![a-z])" + re.escape(p.lower()) + r"(?![a-z])", t)]


def check_copy(copy: AdCopy, kit: BrandKit) -> Dict[str, List[str]]:
    ev = kit.evidence()
    brand = kit.brand
    banned = [d["phrase"] for d in brand["do_not_say"]]
    competitors = brand["competitors"]
    evidence_numbers = set(_numbers(" ".join(e.text for e in ev.values() if e.source != "competitor")))
    broll_ids = {b["id"] for b in kit.broll}
    reviews = {r["id"]: r for r in kit.reviews}
    findings: Dict[str, List[str]] = {a.id: [] for a in copy.static_ads}
    findings[copy.video.id] = []

    def common(asset_id: str, text: str, ids: List[str]):
        f = findings[asset_id]
        for p in _phrase_hits(text, banned):
            f.append(f"Forbidden phrase: '{p}'")
        for c in _phrase_hits(text, competitors):
            f.append(f"Names a competitor: '{c}'")
        unknown = sorted({i for i in ids if i not in ev})
        if unknown:
            f.append(f"Cites evidence ids that do not exist: {', '.join(unknown)}")
        missing = sorted({n for n in _numbers(text) if n not in evidence_numbers})
        if missing:
            f.append(f"Numbers not found in our evidence: {', '.join(missing)}")

    for ad in copy.static_ads:
        f = findings[ad.id]
        if len(ad.headline) > 40:
            f.append(f"Headline is {len(ad.headline)} characters (max 40)")
        if len(ad.subhead) > 90:
            f.append(f"Subhead is {len(ad.subhead)} characters (max 90)")
        if ad.offer_line.strip() != brand["offer"]:
            f.append(f"Offer line must be exactly: {brand['offer']}")
        if ad.cta.strip() != brand["cta"]:
            f.append(f"CTA must be exactly: {brand['cta']}")
        ids = [i for c in ad.claims for i in c.evidence_ids]
        for c in ad.claims:
            if not c.evidence_ids:
                f.append(f"Claim has no evidence: '{c.text}'")
            elif all(ev.get(i) and ev[i].source == "competitor" for i in c.evidence_ids):
                f.append(f"Claim rests only on a competitor ad: '{c.text}'")
        text = " ".join([ad.headline, ad.subhead] + [c.text for c in ad.claims])
        if ad.testimonial:
            r = reviews.get(ad.testimonial.review_id)
            if not r:
                f.append(f"Testimonial cites unknown review {ad.testimonial.review_id}")
            else:
                if r["rating"] < 4:
                    f.append(f"Testimonial from a {r['rating']}-star review ({r['id']})")
                if _norm(ad.testimonial.text).strip('". ') not in _norm(r["text"]):
                    f.append(f"Testimonial is not verbatim from {r['id']}")
            text += " " + ad.testimonial.text
        common(ad.id, text, ids)

    v = copy.video
    f = findings[v.id]
    if not 3 <= len(v.beats) <= 6:
        f.append(f"Video has {len(v.beats)} beats (expected 3 to 6)")
    for i, b in enumerate(v.beats, 1):
        if len(b.caption) > 32:
            f.append(f"Beat {i} caption is {len(b.caption)} characters (max 32)")
        if b.broll_id not in broll_ids:
            f.append(f"Beat {i} uses unknown b-roll '{b.broll_id}'")
    words = sum(len(b.line.split()) for b in v.beats)
    est = words / WORDS_PER_SECOND
    if not 10 <= est <= 28:
        f.append(f"Voiceover is about {est:.0f}s ({words} words); aim for 15 to 25s")
    common(v.id, " ".join([b.line + " " + b.caption for b in v.beats] + [v.end_card]), [i for b in v.beats for i in b.evidence_ids])
    return findings


def check_video_file(probe: dict, expected_seconds: float) -> List[str]:
    """Checks on the rendered MP4 (from ffprobe)."""
    problems = []
    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(probe.get("format", {}).get("duration", 0))
    if not video or (video.get("width"), video.get("height")) != (1080, 1920):
        problems.append("Video is not 1080x1920")
    if not audio:
        problems.append("Video has no audio track")
    if abs(duration - expected_seconds) > 1.0:
        problems.append(f"Duration {duration:.1f}s differs from the edit plan ({expected_seconds:.1f}s)")
    if not 10 <= duration <= 30:
        problems.append(f"Duration {duration:.1f}s is outside 10 to 30s")
    return problems
