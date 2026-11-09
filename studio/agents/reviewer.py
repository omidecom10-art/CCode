"""Reviewer agent: checks the copywriter's work. It sees the copy, the evidence the copy cites, the brand
rules and the deterministic check results, and returns a pass/fail verdict per asset with fixable issues."""
import json

from ..data import BrandKit
from ..schemas import AdCopy, ReviewReport

SYSTEM = """You are the reviewer agent. Another agent wrote these ads; your job is to catch problems before
anything is rendered or published. Be strict about facts and fair about style.

For each asset (A1, A2, A3, V1) return pass or fail with issues.
Fail an asset if any of these is true:
- a claim is not supported by the evidence it cites (read the cited evidence text), or a number does not match;
- it uses a forbidden phrase, names a competitor, borrows a competitor's claim, or makes a health or body claim;
- a testimonial is not verbatim, comes from a review under 4 stars, or implies something the brand cannot claim;
- the deterministic checks reported a problem for it;
- for the video: a caption contradicts its line, or a b-roll choice clearly does not fit the line.
Style problems that do not mislead are "note" severity and do not fail an asset.
For every issue give the exact quote, the problem and a concrete fix."""


def run(llm, settings, kit: BrandKit, copy: AdCopy, findings: dict, round_no: int = 1):
    ev = kit.evidence()
    cited = sorted({i for a in copy.static_ads for c in a.claims for i in c.evidence_ids}
                   | {a.testimonial.review_id for a in copy.static_ads if a.testimonial}
                   | {i for b in copy.video.beats for i in b.evidence_ids})
    prompt = "\n\n".join([
        "COPY TO REVIEW:\n" + copy.model_dump_json(indent=1),
        "EVIDENCE CITED (id: text):\n" + "\n".join(f"{i}: {ev[i].text}" if i in ev else f"{i}: (NOT IN REGISTRY)" for i in cited),
        f"BRAND OFFER: {kit.brand['offer']}\nBRAND CTA: {kit.brand['cta']}",
        "FORBIDDEN PHRASES: " + "; ".join(f"{d['phrase']} ({d['reason']})" for d in kit.brand["do_not_say"]),
        "COMPETITORS (must never appear): " + ", ".join(kit.brand["competitors"]),
        "B-ROLL CATALOG: " + "; ".join(f"{b['id']} = {b['description']}" for b in kit.broll),
        "DETERMINISTIC CHECK RESULTS:\n" + json.dumps(findings, indent=1),
        "Review every asset now.",
    ])
    report, _ = llm.run_agent(f"reviewer_round{round_no}", settings.reviewer_model, SYSTEM, prompt, ReviewReport)
    return report
