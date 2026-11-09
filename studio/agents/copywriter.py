"""Copywriter agent: turns the research into three static ads and one short video script.
On a revision round it gets its previous copy plus every issue the checks and the reviewer found."""
import json

from ..data import BrandKit
from ..schemas import AdCopy, ResearchReport

SYSTEM = """You are the copywriter agent for an e-commerce brand. You write paid social ads from a research brief.

Write:
- Three static ads (ids A1, A2, A3), one per recommended angle:
  headline at most 40 characters, subhead at most 90 characters,
  offer_line exactly equal to the brand offer, cta exactly equal to the brand CTA,
  claims: every factual statement in the ad, each citing evidence ids from the registry.
  Optional testimonial: a verbatim excerpt from a review rated 4 or 5 stars, with its review id.
- One vertical video script (id V1) for a 15 to 25 second ad: 4 or 5 beats, hook first.
  Each beat: a voiceover line (short, spoken, 6 to 14 words), an on-screen caption of at most 32 characters,
  a broll_id chosen from the b-roll catalog that matches the line, and evidence ids for any fact in it.
  end_card: a short closing line (the offer and CTA are added to the card automatically).

Rules:
- Only state facts that the cited evidence supports. Numbers must match the evidence exactly.
- Never use the brand's forbidden phrases, never name competitors, never make health or body claims,
  and never borrow a competitor's claim.
- Write in the brand voice."""


def _context(kit: BrandKit, research: ResearchReport) -> str:
    ev = kit.evidence()
    return "\n\n".join([
        f"BRAND: {kit.brand['name']}\nVOICE: {kit.brand['voice']}\nAUDIENCE: {kit.brand['audience']}",
        f"OFFER (use exactly): {kit.brand['offer']}\nCTA (use exactly): {kit.brand['cta']}",
        "FORBIDDEN: " + "; ".join(f"{d['phrase']} ({d['reason']})" for d in kit.brand["do_not_say"]),
        "EVIDENCE REGISTRY (cite these ids):\n" + "\n".join(f"{k}: {v.text}" for k, v in ev.items() if v.source != "competitor"),
        "B-ROLL CATALOG (choose broll_id from these):\n" + "\n".join(f"{b['id']}: {b['description']} [tags: {', '.join(b['tags'])}]" for b in kit.broll),
        "RESEARCH BRIEF:\n" + research.model_dump_json(indent=1),
    ])


def run(llm, settings, kit: BrandKit, research: ResearchReport, round_no: int = 1, previous=None, issues=None):
    prompt = _context(kit, research)
    if previous is not None:
        prompt += ("\n\nYOUR PREVIOUS COPY:\n" + previous.model_dump_json(indent=1)
                   + "\n\nISSUES FOUND BY THE CHECKS AND THE REVIEWER (fix every one, keep what passed):\n"
                   + json.dumps(issues, indent=1, ensure_ascii=False))
    prompt += "\n\nWrite the ads now."
    copy, _ = llm.run_agent(f"copywriter_round{round_no}", settings.writer_model, SYSTEM, prompt, AdCopy)
    return copy
