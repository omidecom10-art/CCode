"""CLI.

  python -m studio run --brand data/sample_brand --out output/sample_run            # live (needs ANTHROPIC_API_KEY)
  python -m studio run --brand data/sample_brand --out output/replay --replay \\
         --cassette output/sample_run/llm_cassette.json --tts silent                 # no key: replays the recorded run
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from . import pipeline


def main(argv=None):
    ap = argparse.ArgumentParser(prog="studio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="research -> copy -> review -> render -> publish")
    r.add_argument("--brand", default="data/sample_brand")
    r.add_argument("--out", default="output/run")
    r.add_argument("--replay", action="store_true", help="replay recorded LLM outputs instead of calling the API")
    r.add_argument("--cassette", help="recorded outputs to replay (copied into --out)")
    r.add_argument("--tts", choices=["kokoro", "silent"], help="voiceover provider (default from STUDIO_TTS)")
    r.add_argument("--skip-video", action="store_true")
    t = sub.add_parser("redteam", help="plant problems in a run's approved copy and see what the checkers catch")
    t.add_argument("--out", default="output/sample_run")
    t.add_argument("--brand", default="data/sample_brand")
    t.add_argument("--replay", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "redteam":
        from . import redteam
        print("Wrote", redteam.run(Path(a.out), Path(a.brand), mode="replay" if a.replay else "live"))
        return 0
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.replay and a.cassette and Path(a.cassette).resolve() != (out / "llm_cassette.json").resolve():
        shutil.copy(a.cassette, out / "llm_cassette.json")
    try:
        summary = pipeline.run(Path(a.brand), out, mode="replay" if a.replay else "live", tts_provider=a.tts, skip_video=a.skip_video)
    except Exception as exc:
        print(f"Run failed: {exc}\nSee {out / 'run.jsonl'} (an alert was sent or written to integrations/slack.json).", file=sys.stderr)
        return 1
    print(json.dumps({k: summary[k] for k in ("approved", "blocked", "rounds", "llm_calls", "usd", "seconds")}, indent=2))
    print(f"Report: {out / 'REPORT.md'}")
    return 0 if summary["blocked"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
