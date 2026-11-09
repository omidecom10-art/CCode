"""Writes REPORT.md for a run: a readable walkthrough of what every agent did, with the finished assets."""
import json
from pathlib import Path


def _esc(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def write_report(out: Path, kit, research, trace, rounds, copy, summary):
    ev = kit.evidence()
    L = [f"# Sample run: {summary['product']}", "",
         f"Brand: **{summary['brand']}** (fictional sample brand) · run `{summary['run_id']}` · mode `{summary['mode']}`  ",
         f"Models: research `{summary['models']['research']}`, writer `{summary['models']['writer']}`, reviewer `{summary['models']['reviewer']}`  ",
         f"Result: **{summary['approved']} approved, {summary['blocked']} blocked** after {summary['rounds']} review round(s) · "
         f"{summary['llm_calls']} LLM calls · {summary['input_tokens']:,} in / {summary['output_tokens']:,} out tokens · "
         f"**${summary['usd']}** · {summary['seconds']}s", ""]

    L += ["## Finished assets", ""]
    for a in summary["assets"]:
        if a["kind"] == "static" and a["files"]:
            feed, story = a["files"]
            L += [f"### {a['id']} · {a['angle']} ({a['status']})", "",
                  f'<img src="{feed}" width="360" alt="{a["id"]} feed 4:5"> <img src="{story}" width="203" alt="{a["id"]} story 9:16">', ""]
        elif a["kind"] == "video" and a["files"]:
            L += [f"### {a['id']} · video · {a['angle']} ({a['status']})", "",
                  f'<a href="{a["files"][0]}"><img src="{a["files"][1]}" width="240" alt="video poster"></a>  ',
                  f"[Watch {a['files'][0]}]({a['files'][0]}) · edit plan: [video/edit_plan.json](video/edit_plan.json) · QA: [video/qa.json](video/qa.json)", ""]
        else:
            L += [f"### {a['id']} ({a['status']})", "", "Blocked by review, so it was not rendered or published.", ""]

    L += ["## 1. Research agent", "", f"> {research.product_summary}", "",
          f"**Tool calls ({len(trace)}), chosen by the agent:**", "", "| # | Tool | Input | Result (preview) |", "|---|---|---|---|"]
    L += [f"| {i} | `{t['tool']}` | `{_esc(json.dumps(t['input']))}` | {_esc(t['result_preview'][:110])}… |" for i, t in enumerate(trace, 1)]
    L += ["", "**Customer language (verbatim, cited):**", ""]
    L += [f"- \"{q.text}\" ({q.review_id})" for q in research.customer_language[:6]]
    L += ["", "**Recommended angles:**", ""]
    L += [f"- **{a.name}**: {a.hook_idea} *({', '.join(a.evidence_ids)})*" for a in research.recommended_angles]
    L += ["", "**Competitor angles and gaps:**", ""]
    L += [f"- {c.competitor}: {c.angle}. {c.risk_or_gap} *({', '.join(c.evidence_ids)})*" for c in research.competitor_angles]
    L += [f"- Gap: {g}" for g in research.gaps]
    L += ["", "**Avoid:**", ""] + [f"- {x}" for x in research.avoid] + [""]

    L += ["## 2. Copywriter and reviewer (agents checking agents)", "",
          "Each round: the copywriter writes, deterministic checks run, then the reviewer agent reads the copy against the "
          "evidence it cites. Failing assets go back to the copywriter with every issue.", "",
          "| Round | Asset | Checks | Reviewer | Approved | Main issue |", "|---|---|---|---|---|---|"]
    for r in rounds:
        for aid, v in r["verdicts"].items():
            checks = [i for i in v["issues"] if i["from"] == "checks"]
            rev = [i for i in v["issues"] if i["from"] == "reviewer"]
            main = (checks or rev or [{"problem": "-"}])[0]["problem"]
            L.append(f"| {r['round']} | {aid} | {len(checks)} issue(s) | {len(rev)} issue(s) | {'yes' if v['approved'] else 'no'} | {_esc(main)[:140]} |")
    L += ["", f"Reviewer's last summary: {rounds[-1]['reviewer_summary']}", ""]

    L += ["## 3. Final copy and the evidence behind every claim", ""]
    for ad in copy.static_ads:
        L += [f"**{ad.id} · {ad.angle}**  ", f"Headline: {ad.headline}  ", f"Subhead: {ad.subhead}  ",
              f"Offer: {ad.offer_line} · CTA: {ad.cta}"]
        if ad.testimonial:
            L.append(f"Testimonial: \"{ad.testimonial.text}\" ({ad.testimonial.review_id})")
        L += ["", "| Claim | Evidence |", "|---|---|"]
        L += [f"| {_esc(c.text)} | " + "<br>".join(f"`{i}` {_esc(ev[i].text)[:120]}" for i in c.evidence_ids if i in ev) + " |" for c in ad.claims]
        L.append("")
    v = copy.video
    L += [f"**{v.id} · video script · {v.angle}**", "", "| Beat | Voiceover | Caption | B-roll | Evidence |", "|---|---|---|---|---|"]
    L += [f"| {i} | {_esc(b.line)} | {_esc(b.caption)} | `{b.broll_id}` | {', '.join(b.evidence_ids) or '-'} |" for i, b in enumerate(v.beats, 1)]
    L += [f"| end | | {_esc(v.end_card)} + offer + CTA | `end_card` | |", ""]

    L += ["## 4. Integrations", "", "Dry-run payloads (no credentials set for this sample run) are in [integrations/](integrations/): "
          "Shopify product fetch, Meta Ads (each approved ad created **PAUSED**), Google Drive uploads, Notion tracker rows, Slack summary.", ""]
    L += ["## 5. Monitoring", "", "Every step is timed and logged to [run.jsonl](run.jsonl); a failure posts a Slack alert.", "",
          "| Step | Status | Seconds |", "|---|---|---|"]
    L += [f"| {s['step']} | {s['status']} | {s['seconds']} |" for s in summary["steps"]]
    (Path(out) / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
