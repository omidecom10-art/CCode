# AI Ad Agent + ecom-ai-studio

[![tests](https://github.com/omidecom10-art/ccode/actions/workflows/tests.yml/badge.svg)](https://github.com/omidecom10-art/ccode/actions/workflows/tests.yml)

Two complementary AI ad systems in one repo:

1. **Ad Agent CLI** — lightweight scriptwriting, ad analysis, hooks, video editing, watermark removal. Uses Claude Haiku (~$0.001/call).
2. **Studio Pipeline** — full research → copy → review → render → publish pipeline with evidence-checked ads, static ad rendering, video editing with TTS, and integrations (Shopify/Meta/Drive/Notion/Slack). Based on [ecom-ai-studio](https://github.com/cainticjohncarlo-pixel/ecom-ai-studio).

## Setup

```bash
pip install -r requirements.txt            # plus ffmpeg on PATH
cp .env.example .env                       # add ANTHROPIC_API_KEY
```

---

## Ad Agent CLI (cheap, fast)

| Function | Engine | Cost |
|----------|--------|------|
| Write script | Claude Haiku 5.5 | ~$0.001 |
| Generate hooks | Claude Haiku 5.5 | ~$0.001 |
| Iterate scripts | Claude Haiku 5.5 | ~$0.001 |
| Analyze ad | Claude Haiku 5.5 | ~$0.0007 |
| Compare ads | Claude Haiku 5.5 | ~$0.001 |
| Video editing | FFmpeg (local) | $0.00 |
| Watermark removal | OpenCV (local) | $0.00 |

### Usage

```bash
# Agent mode (auto-routes)
python -m cli.main agent "Write a 30s TikTok script for a skincare cream"

# Script writing
python -m cli.main write-script "Protein supplement for gym-goers" --platform instagram --duration 15

# Hooks for A/B testing
python -m cli.main hooks "Skincare cream 50% off" --num 15

# Video editing
python -m cli.main edit -op trim -i video.mp4 -o trimmed.mp4 -s 00:00:05 -e 00:00:20

# Watermark removal
python -m cli.main remove-watermark -i video.mp4 -o clean.mp4
```

---

## Studio Pipeline (full creative pipeline)

Research agent studies the product; copywriter agent writes ads and a video script; reviewer agent checks every claim against evidence; static ad engine renders PNGs; video editor cuts a vertical ad from voiceover and b-roll. Approved ads go to Meta as paused drafts, files to Drive, rows to Notion, alerts to Slack.

**One real run, committed:** [`output/sample_run/REPORT.md`](output/sample_run/REPORT.md) — 4 assets approved, 4 Claude calls, $0.25, 126s.

### Usage

```bash
# Live run (~$0.25 with claude-opus-5-5)
python -m studio run --brand data/sample_brand --out output/my_run

# Replay without API key (uses recorded cassette)
python -m studio run --out output/replay --replay --cassette output/sample_run/llm_cassette.json --tts silent

# Red-team the checkers
python -m studio redteam --out output/sample_run --replay
```

### How it works

| Stage | What happens | Code |
|---|---|---|
| Research agent | Tool-calling loop: product, brand guide, reviews, competitor ads. Returns a validated ResearchReport with cited evidence. | [`studio/agents/research.py`](studio/agents/research.py) |
| Copywriter agent | 3 static ads + video script with evidence ids and b-roll picks. | [`studio/agents/copywriter.py`](studio/agents/copywriter.py) |
| Deterministic checks | Length limits, exact offer/CTA, evidence ids, numbers, forbidden words, competitor names. | [`studio/checks.py`](studio/checks.py) |
| Reviewer agent | Reads copy against cited evidence, passes or fails each asset. | [`studio/agents/reviewer.py`](studio/agents/reviewer.py) |
| Static ad engine | Renders feed (1080x1350) and story (1080x1920) PNGs with auto-fitting text. | [`studio/engines/static_ads.py`](studio/engines/static_ads.py) |
| Video editor | TTS per beat, Ken Burns on b-roll, captions, end card, ffprobe QA. | [`studio/engines/video.py`](studio/engines/video.py) |
| Integrations | Shopify, Meta Ads (paused), Drive, Notion, Slack. Each runs live when env vars are set. | [`studio/integrations/`](studio/integrations) |

## Project layout

```
agent/               Ad Agent CLI agents (orchestrator, script writer, planner)
cli/                 Ad Agent CLI entry point
tools/               Video editor, watermark remover, image processor, ad analyzer
config/              Ad Agent settings
models/              Ad Agent Pydantic schemas
utils/               Shared helpers, LLM client

studio/              Studio pipeline (self-contained package)
  agents/            research.py, copywriter.py, reviewer.py
  engines/           static_ads.py, video.py, tts.py, graphics.py
  integrations/      shopify.py, meta_ads.py, gdrive.py, notion.py, slack.py
  checks.py          deterministic checks
  pipeline.py        orchestrator
  monitor.py         run log, cost, alerts
  report.py          REPORT.md writer
  redteam.py         planted-problem demo

data/sample_brand/   sample brand data (fictional)
output/sample_run/   committed live run (REPORT.md, ads/, video/, integrations/)
scripts/             site builder, asset fetcher
tests/               all tests (both systems)
```

## Tests

```bash
pytest -q    # runs all tests, including full pipeline replay (no API key needed)
```
