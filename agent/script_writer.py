from __future__ import annotations

import json
from pathlib import Path

from models.schemas import AdScript, AdScriptBrief, ScriptVariation
from utils.file_helpers import ensure_output_dir
from utils.llm import call_cheap

SCRIPTWRITER_SYSTEM = """Du ar en varldsklass copywriter och kreativ director for performanceannonsering.
Du skriver videomanus/scripts for annonser pa TikTok, Instagram Reels, Facebook, YouTube Shorts etc.

Du foljer bevisade strukturer som:
- Hook (0-3s) -> Problem (3-7s) -> Solution (7-15s) -> Proof (15-22s) -> CTA (22-30s)
- Hook -> Agitate -> Solution -> CTA
- Hook -> Story -> Offer -> CTA
- Before/After
- UGC-style testimonial

Regler:
- Skriv ALLTID pa det sprak anvandaren skriver pa
- Varje script har tydliga tidsmarkeringar (t.ex. [0-3s])
- Inkludera VISUELLA anvisningar (vad som syns pa skarm)
- Inkludera LJUD/MUSIK-anvisningar
- Inkludera VOICEOVER-text (exakt vad som sags)
- Inkludera TEXT-OVERLAYS (vad som star pa skarm)
- Var specifik och konkret — inga generiska fraser
- Optimera for scroll-stopping hooks
- Anpassa langd och stil efter plattform"""


def write_ad_script(brief: str, platform: str = "tiktok", duration: int = 30) -> AdScript:
    """Write an ad video script from a brief. Uses Haiku — costs ~$0.001."""
    return call_cheap(
        system=SCRIPTWRITER_SYSTEM,
        messages=[{"role": "user", "content": (
            f"Skriv ett videomanus for en {duration}-sekunders annons.\n\n"
            f"Plattform: {platform}\n"
            f"Brief: {brief}\n\n"
            "Ge mig ett komplett manus med hook, visuella anvisningar, voiceover och CTA."
        )}],
        output_schema=AdScript,
    )


def write_hook_variations(product_or_offer: str, num_hooks: int = 10, platform: str = "tiktok") -> list[ScriptVariation]:
    """Generate multiple hook variations for A/B testing. ~$0.001."""
    prompt = (
        f"Skapa {num_hooks} olika hooks (oppningsrader, 0-3 sekunder) for en {platform}-annons.\n\n"
        f"Produkt/erbjudande: {product_or_offer}\n\n"
        "Varje hook ska vara scroll-stopping och anvanda en annorlunda vinkel:\n"
        "- Chock/overraskning\n- Fraga\n- Kontroversielt pastaende\n"
        "- Social proof\n- Direkt nytta\n- Smartpunkt/siffra\n"
        "- Storytelling\n- UGC-stil\n- Humor\n- FOMO\n\n"
        "Inkludera bade voiceover-text OCH visuell anvisning for varje hook."
    )

    class HookList(ScriptVariation.__class__.__bases__[0]):
        hooks: list[ScriptVariation]

    # Use a wrapper to get a list back
    from pydantic import BaseModel

    class HookListWrapper(BaseModel):
        hooks: list[ScriptVariation]

    result = call_cheap(
        system=SCRIPTWRITER_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_schema=HookListWrapper,
    )
    return result.hooks


def iterate_winning_script(
    original_script: str,
    what_worked: str,
    num_variations: int = 5,
) -> list[ScriptVariation]:
    """Create iterations on a winning ad script, keeping what works. ~$0.001."""
    from pydantic import BaseModel

    class VariationList(BaseModel):
        variations: list[ScriptVariation]

    result = call_cheap(
        system=SCRIPTWRITER_SYSTEM,
        messages=[{"role": "user", "content": (
            f"Har ar ett vinnande annonsmanus:\n\n{original_script}\n\n"
            f"Det har fungerade bra: {what_worked}\n\n"
            f"Skapa {num_variations} variationer som bevarar de vinnande elementen "
            "men testar nya vinklar, hooks eller CTA:er.\n\n"
            "Varje variation ska vara ett komplett manus med tidsmarkeringar."
        )}],
        output_schema=VariationList,
    )
    return result.variations


def script_from_analysis(
    analysis_json: str,
    product_info: str,
    platform: str = "tiktok",
    duration: int = 30,
) -> AdScript:
    """Write a new script based on ad analysis insights. ~$0.001."""
    return call_cheap(
        system=SCRIPTWRITER_SYSTEM,
        messages=[{"role": "user", "content": (
            f"Baserat pa denna analys av vad som funkar/inte funkar:\n\n{analysis_json}\n\n"
            f"Produkt/tjanst: {product_info}\n"
            f"Plattform: {platform}\n"
            f"Langd: {duration} sekunder\n\n"
            "Skriv ett nytt manus som tar tillvara pa styrkorna och undviker svagheterna."
        )}],
        output_schema=AdScript,
    )


def save_script(script: AdScript, filename: str | None = None) -> str:
    """Save a script to a readable text file."""
    scripts_dir = ensure_output_dir("scripts")
    if not filename:
        existing = list(scripts_dir.glob("script_*.txt"))
        num = len(existing) + 1
        filename = f"script_{num:03d}.txt"

    path = scripts_dir / filename
    lines = [
        f"ANNONSMANUS: {script.title}",
        f"Plattform: {script.platform} | Langd: {script.duration_seconds}s",
        f"Struktur: {script.structure}",
        "",
        "=" * 60,
        "",
    ]
    for section in script.sections:
        lines.append(f"[{section.timestamp}] — {section.section_name}")
        lines.append(f"  VOICEOVER: {section.voiceover}")
        lines.append(f"  VISUELLT: {section.visual_direction}")
        if section.text_overlay:
            lines.append(f"  TEXT PA SKARM: {section.text_overlay}")
        if section.music_direction:
            lines.append(f"  MUSIK/LJUD: {section.music_direction}")
        lines.append("")

    lines.append("=" * 60)
    lines.append(f"\nNYCKELBUDSKAP: {script.key_message}")
    if script.notes:
        lines.append(f"ANTECKNINGAR: {script.notes}")

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
