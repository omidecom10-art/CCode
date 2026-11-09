"""The orchestrator: research -> write -> check + review (revise until approved) -> render -> verify -> publish.

An asset is approved only when the deterministic checks find nothing AND the reviewer agent passes it.
Anything still failing after the revision budget is blocked: it is reported, never rendered or published.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from .agents import copywriter, research, reviewer
from .checks import check_copy, check_video_file
from .config import Settings
from .data import load_brand
from .engines import static_ads, video
from .integrations.gdrive import Drive
from .integrations.meta_ads import MetaAds
from .integrations.notion import Notion
from .integrations.shopify import Shopify
from .integrations.slack import Slack
from .llm import LLM
from .monitor import RunMonitor
from .report import write_report


def _verdicts(copy, findings, review):
    by_id = {a.asset_id: a for a in review.assets}
    out = {}
    for asset_id, problems in findings.items():
        rv = by_id.get(asset_id)
        approved = not problems and rv is not None and rv.verdict == "pass"
        issues = [{"from": "checks", "problem": p} for p in problems]
        if rv:
            issues += [{"from": "reviewer", "severity": i.severity, "quote": i.quote, "problem": i.problem, "fix": i.fix}
                       for i in rv.issues if i.severity != "note"]
        out[asset_id] = {"approved": approved, "issues": issues,
                         "notes": [i.problem for i in (rv.issues if rv else []) if i.severity == "note"]}
    return out


def run(brand_dir: Path, out_dir: Path, mode: str = "live", tts_provider: str = None, skip_video: bool = False) -> dict:
    settings = Settings()
    out_dir = Path(out_dir)
    slack = Slack(out_dir, settings.integrations)
    monitor = RunMonitor(out_dir, alert_fn=slack.alert)
    llm = LLM(settings, monitor, out_dir / "llm_cassette.json", mode=mode)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    monitor.event("run_start", run_id=run_id, mode=mode, brand=str(brand_dir))
    save = lambda name, obj: (out_dir / name).write_text(  # noqa: E731
        json.dumps(obj, indent=2, ensure_ascii=False) if not hasattr(obj, "model_dump_json") else obj.model_dump_json(indent=2),
        encoding="utf-8")

    with monitor.step("load brand + product"):
        kit = load_brand(brand_dir)
        Shopify(out_dir, settings.integrations).product(kit.product["handle"])

    with monitor.step("research agent"):
        report, trace = research.run(llm, settings, kit)
        save("research.json", report)
        save("research_trace.json", trace)

    rounds, copy, issues = [], None, None
    for round_no in range(1, settings.max_revisions + 2):
        with monitor.step(f"copywriter round {round_no}"):
            copy = copywriter.run(llm, settings, kit, report, round_no, previous=copy, issues=issues)
            save(f"copy_round{round_no}.json", copy)
        with monitor.step(f"checks + reviewer round {round_no}"):
            findings = check_copy(copy, kit)
            review = reviewer.run(llm, settings, kit, copy, findings, round_no)
            verdicts = _verdicts(copy, findings, review)
            rounds.append({"round": round_no, "verdicts": verdicts, "reviewer_summary": review.summary})
            save(f"review_round{round_no}.json", rounds[-1])
        if all(v["approved"] for v in verdicts.values()):
            break
        issues = {k: v["issues"] for k, v in verdicts.items() if not v["approved"]}
    final = rounds[-1]["verdicts"]
    save("final_copy.json", copy)

    assets = []
    with monitor.step("static ad engine"):
        for ad in copy.static_ads:
            entry = {"id": ad.id, "kind": "static", "angle": ad.angle, "headline": ad.headline,
                     "status": "approved" if final[ad.id]["approved"] else "blocked", "files": []}
            if final[ad.id]["approved"]:
                entry["files"] = [str(p.relative_to(out_dir).as_posix()) for p in static_ads.render(ad, kit, out_dir / "ads")]
            assets.append(entry)

    v = copy.video
    ventry = {"id": v.id, "kind": "video", "angle": v.angle, "headline": v.beats[0].caption if v.beats else "",
              "status": "approved" if final[v.id]["approved"] else "blocked", "files": []}
    if ventry["status"] == "approved" and not skip_video:
        with monitor.step("video editor"):
            mp4, planned, probe = video.render(v, kit, out_dir / "video", tts_provider or settings.tts_provider, settings.tts_voice)
            problems = check_video_file(probe, planned)
            save("video/qa.json", {"planned_seconds": planned, "duration": float(probe["format"]["duration"]),
                                   "problems": problems, "probe": {"format": probe["format"], "streams": probe["streams"]}})
            ventry["files"] = [f"video/{mp4.name}", f"video/{v.id}_poster.jpg"]
            ventry["qa"] = problems
            if problems:
                ventry["status"] = "blocked"
                raise RuntimeError(f"Rendered video failed QA: {problems}")
    assets.append(ventry)

    with monitor.step("publish"):
        meta, drive, notion = MetaAds(out_dir, settings.integrations), Drive(out_dir, settings.integrations), Notion(out_dir, settings.integrations)
        for a in assets:
            notion.log_asset(a, run_id)
            for f in a["files"]:
                drive.upload(out_dir / f)
            if a["kind"] == "static" and a["status"] == "approved":
                ad = next(x for x in copy.static_ads if x.id == a["id"])
                meta.create_paused_ad(ad, out_dir / a["files"][0], link=f"https://example.com/products/{kit.product['handle']}")

    summary = {"run_id": run_id, "mode": mode, "brand": kit.brand["name"], "product": kit.product["title"],
               "models": {"research": settings.research_model, "writer": settings.writer_model, "reviewer": settings.reviewer_model},
               "research_tool_calls": len(trace), "rounds": len(rounds),
               "approved": sum(a["status"] == "approved" for a in assets), "blocked": sum(a["status"] == "blocked" for a in assets),
               "assets": assets, **monitor.summary()}
    slack.run_summary(summary)
    save("summary.json", summary)
    write_report(out_dir, kit, report, trace, rounds, copy, summary)
    monitor.event("run_done", approved=summary["approved"], blocked=summary["blocked"], usd=summary["usd"])
    return summary
