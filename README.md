# AI Ad Agent

AI-powered agent for creating, analyzing, and optimizing ad creatives. Built to be as cheap as possible.

## Cost Breakdown

| Operation | Engine | Cost per Call |
|-----------|--------|--------------|
| Ad Analysis | Claude Haiku 5.5 | ~$0.0007 |
| Ad Comparison | Claude Haiku 5.5 | ~$0.001 |
| Iteration Planning | Claude Haiku 5.5 | ~$0.001 |
| Performance Explanation | Claude Haiku 5.5 | ~$0.0005 |
| Script Generation | Claude Sonnet 5.5 | ~$0.03 |
| Video Editing | FFmpeg (local) | $0.00 |
| Watermark Removal | OpenCV (local) | $0.00 |
| Image Processing | Pillow (local) | $0.00 |

**Typical workflow:** Analyze + iterate = ~$0.002 (two tenths of a cent).

## Requirements

- Python 3.10+
- FFmpeg (system install)
- Anthropic API key

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Usage

### Free-form Agent (routes automatically)

```bash
python -m cli.main agent "Analyze this ad and suggest 5 iterations: [description]"
python -m cli.main agent "Remove the watermark from video.mp4 and trim to 15 seconds"
```

### Direct Commands

```bash
# Analyze an ad
python -m cli.main analyze -i "30s TikTok ad showing product demo with upbeat music"
python -m cli.main analyze -i ad_description.txt -m metrics.json

# Compare ads
python -m cli.main compare -i ads.json

# Generate iterations
python -m cli.main iterate -i "winning ad description" -n 5

# Video editing
python -m cli.main edit -op trim -i video.mp4 -o trimmed.mp4 -s 00:00:05 -e 00:00:20
python -m cli.main edit -op merge --inputs v1.mp4 v2.mp4 -o merged.mp4
python -m cli.main edit -op overlay-text -i video.mp4 -o output.mp4 -t "Buy Now!" -p bottom
python -m cli.main edit -op resize -i video.mp4 -o output.mp4 --width 1080 --height 1920
python -m cli.main edit -op speed -i video.mp4 -o output.mp4 --speed 1.5

# Remove watermarks
python -m cli.main remove-watermark -i image.png -o clean.png
python -m cli.main remove-watermark -i video.mp4 -o clean.mp4

# Remove subtitles
python -m cli.main remove-subtitles -i video.mp4 -o clean.mp4

# Generate custom scripts
python -m cli.main generate-script "Create 10 variations of a winning ad by swapping hooks" --show
```

### As Python Library

```python
from tools.ad_analyzer import analyze_ad, suggest_iterations
from tools.video_editor import trim_video, add_text_overlay
from tools.watermark_remover import remove_watermark_from_video
from agent.orchestrator import run

# Analyze
analysis = analyze_ad("30s product demo ad with social proof hook")
print(analysis.overall_score, analysis.recommendations)

# Iterate
plan = suggest_iterations(analysis, num_variations=5)

# Edit
trim_video("input.mp4", "output.mp4", "00:00:03", "00:00:18")

# Agent mode
result = run("Remove watermark, trim to 15s, add CTA overlay")
```

## Architecture

```
agent/
  orchestrator.py  - Main agent loop (Haiku for routing, ~$0.0004/call)
  planner.py       - Task decomposition (Haiku)
  code_generator.py - Script generation (Sonnet, only when needed)
tools/
  video_editor.py      - FFmpeg wrapper (free)
  watermark_remover.py - OpenCV inpainting (free)
  image_processor.py   - Pillow/OpenCV (free)
  ad_analyzer.py       - Ad analysis (Haiku)
```

90%+ of LLM calls go through Haiku (~20x cheaper than Sonnet). Sonnet is only used for code generation.

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```
