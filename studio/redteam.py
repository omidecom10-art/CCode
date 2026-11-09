"""Red-team demo for "agents that check other agents' work".

Takes the approved copy from a run, plants six realistic problems, and shows which ones the deterministic
checks catch and which ones only the reviewer agent catches. Writes REDTEAM.md next to the run.

  python -m studio redteam --out output/sample_run            # live (one reviewer call)
  python -m studio redteam --out output/sample_run --replay   # no key: uses the recorded review
"""
import json
from pathlib import Path

from .agents import reviewer
from .checks import check_copy
from .config import Settings
from .data import load_brand
from .llm import LLM
from .monitor import RunMonitor
from .schemas import AdCopy, Quote

PLANTED = [
    # (asset, what we plant, what a correct reviewer should say)
    ("A1", "Subhead claims 'leak-proof' and a competitor's 36-hour figure", "forbidden phrase + number not in our evidence"),
    ("A1", "Testimonial swapped to R09, the 5-star 'I've lost 10 pounds' review", "health/body claim from a verbatim 5-star review"),
    ("A2", "Headline says the bottle is lighter than a named competitor", "competitor name + contradicts R08 (heavier than plastic)"),
    ("A3", "Subhead borrows SummitSip's 'The last bottle you'll ever buy' line", "competitor's claim (C01) presented as ours"),
    ("V1", "Caption says 'Drink more, lose weight'", "forbidden phrase / health claim"),
    ("V1", "Voiceover says the bottle 'boosts your energy all day'", "AquaCore's health claim (C03) borrowed"),
]


def plant(copy: AdCopy) -> AdCopy:
    a1, a2, a3 = copy.static_ads[:3]
    a1 = a1.model_copy(update={"subhead": "Leak-proof lid. Cold for up to 36 hours, wherever you go.",
                               "testimonial": Quote(text="I've lost 10 pounds since I started carrying this everywhere and drinking more water.", review_id="R09")})
    a2 = a2.model_copy(update={"headline": "Lighter than SummitSip. Same grip."})
    a3 = a3.model_copy(update={"subhead": "The last bottle you'll ever buy. Hot up to 12 hours in our lab test."})
    beats = list(copy.video.beats)
    beats[1] = beats[1].model_copy(update={"caption": "Drink more, lose weight"})
    beats[2] = beats[2].model_copy(update={"line": "Coffee still hot at lunch, and it boosts your energy all day."})
    return copy.model_copy(update={"static_ads": [a1, a2, a3] + copy.static_ads[3:], "video": copy.video.model_copy(update={"beats": beats})})


def run(out_dir: Path, brand_dir: Path, mode: str = "live") -> Path:
    out_dir = Path(out_dir)
    settings = Settings()
    kit = load_brand(brand_dir)
    copy = AdCopy.model_validate_json((out_dir / "final_copy.json").read_text(encoding="utf-8"))
    bad = plant(copy)
    findings = check_copy(bad, kit)
    monitor = RunMonitor(out_dir / "redteam")
    llm = LLM(settings, monitor, out_dir / "llm_cassette.json", mode=mode)
    review = reviewer.run(llm, settings, kit, bad, findings, round_no="redteam")
    by_id = {a.asset_id: a for a in review.assets}
    (out_dir / "redteam").mkdir(exist_ok=True)
    (out_dir / "redteam" / "planted_copy.json").write_text(bad.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "redteam" / "result.json").write_text(json.dumps(
        {"checks": findings, "review": review.model_dump(), "usd": monitor.summary()["usd"]}, indent=2), encoding="utf-8")

    L = ["# Red-team: do the checkers catch planted problems?", "",
         "Six problems were planted in the approved copy from this run. Deterministic checks run first; the reviewer agent "
         "then reads the copy against the evidence it cites. An asset ships only if both pass.", "",
         "| Asset | Planted problem | Expected catch |", "|---|---|---|"]
    L += [f"| {a} | {p} | {e} |" for a, p, e in PLANTED]
    L += ["", "## Deterministic checks", ""]
    for aid, f in findings.items():
        L += [f"**{aid}**: " + ("; ".join(f) if f else "nothing found")]
    L += ["", "## Reviewer agent", "", f"> {review.summary}", ""]
    for aid in findings:
        rv = by_id.get(aid)
        if not rv:
            continue
        L += [f"**{aid}: {rv.verdict.upper()}**", ""]
        L += [f"- [{i.severity}] \"{i.quote}\": {i.problem} Fix: {i.fix}" for i in rv.issues]
        L.append("")
    blocked = [a for a in findings if findings[a] or (by_id.get(a) and by_id[a].verdict == "fail")]
    L += ["## Outcome", "", f"Blocked: **{', '.join(blocked) or 'none'}** of {', '.join(findings)}. "
          "Nothing blocked is rendered or published; in a normal run each issue goes back to the copywriter agent.", "",
          "Note the split: rules catch exact things (forbidden words, a competitor's name, a number we never claimed). "
          "Only the reviewer catches meaning: a verbatim 5-star review that is still a weight-loss claim, or a competitor's "
          "slogan and health claim reworded into our copy."]
    path = out_dir / "REDTEAM.md"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path
