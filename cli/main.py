#!/usr/bin/env python3
"""CLI entry point for the AI Ad Agent."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def cmd_agent(args):
    from agent.orchestrator import run
    request = " ".join(args.request)
    print(f"Agent processing: {request}\n")
    result = run(request, verbose=args.verbose)
    print(result)


def cmd_analyze(args):
    from tools.ad_analyzer import analyze_ad
    if args.input.endswith((".txt", ".md")):
        description = Path(args.input).read_text()
    else:
        description = args.input

    metrics = None
    if args.metrics:
        metrics = json.loads(Path(args.metrics).read_text())

    result = analyze_ad(description, metrics)
    print(result.model_dump_json(indent=2))


def cmd_compare(args):
    from tools.ad_analyzer import compare_ads
    ads = json.loads(Path(args.input).read_text())
    result = compare_ads(ads)
    print(result.model_dump_json(indent=2))


def cmd_iterate(args):
    from tools.ad_analyzer import analyze_ad, suggest_iterations
    if args.input.endswith((".txt", ".md")):
        description = Path(args.input).read_text()
    else:
        description = args.input

    print("Analyzing ad...")
    analysis = analyze_ad(description)
    print("Generating iterations...")
    plan = suggest_iterations(analysis, args.variations)
    print(plan.model_dump_json(indent=2))


def cmd_edit(args):
    from tools.video_editor import (
        add_text_overlay, change_speed, cut_segment,
        merge_videos, resize_video, trim_video,
    )
    op = args.operation
    if op == "trim":
        result = trim_video(args.input, args.output, args.start, args.end)
    elif op == "cut":
        result = cut_segment(args.input, args.output, args.start, args.end)
    elif op == "merge":
        result = merge_videos(args.inputs, args.output)
    elif op == "overlay-text":
        result = add_text_overlay(args.input, args.output, args.text, args.position or "bottom")
    elif op == "resize":
        result = resize_video(args.input, args.output, args.width, args.height)
    elif op == "speed":
        result = change_speed(args.input, args.output, args.speed)
    else:
        print(f"Unknown operation: {op}")
        return
    print(f"Done: {result}")


def cmd_remove_watermark(args):
    from utils.file_helpers import detect_media_type
    media = detect_media_type(args.input)
    if media == "image":
        from tools.watermark_remover import detect_watermark_regions, remove_watermark_inpaint
        regions = detect_watermark_regions(args.input, args.search_area or "corners")
        if not regions:
            print("No watermark regions detected. Use --region x,y,w,h to specify manually.")
            return
        print(f"Found {len(regions)} regions")
        result = remove_watermark_inpaint(args.input, regions, args.output)
    else:
        from tools.watermark_remover import remove_watermark_from_video
        result = remove_watermark_from_video(args.input, args.output)
    print(f"Done: {result}")


def cmd_remove_subtitles(args):
    from utils.file_helpers import detect_media_type
    media = detect_media_type(args.input)
    if media == "image":
        from tools.watermark_remover import remove_subtitles_from_image
        result = remove_subtitles_from_image(args.input, args.output)
    else:
        from tools.watermark_remover import remove_subtitles_from_video
        result = remove_subtitles_from_video(args.input, args.output)
    print(f"Done: {result}")


def cmd_generate_script(args):
    from agent.code_generator import generate_and_save
    description = " ".join(args.description)
    path = generate_and_save(description, args.filename)
    print(f"Script saved to: {path}")
    if args.show:
        print("\n" + Path(path).read_text())


def main():
    parser = argparse.ArgumentParser(description="AI Ad Agent — create, analyze, and optimize ad creatives")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    # agent (free-form)
    p = sub.add_parser("agent", help="Free-form request to the AI agent")
    p.add_argument("request", nargs="+")
    p.set_defaults(func=cmd_agent)

    # analyze
    p = sub.add_parser("analyze", help="Analyze an ad creative")
    p.add_argument("--input", "-i", required=True, help="Ad description text or .txt file")
    p.add_argument("--metrics", "-m", help="JSON file with performance metrics")
    p.set_defaults(func=cmd_analyze)

    # compare
    p = sub.add_parser("compare", help="Compare multiple ads")
    p.add_argument("--input", "-i", required=True, help="JSON file with array of ads")
    p.set_defaults(func=cmd_compare)

    # iterate
    p = sub.add_parser("iterate", help="Generate iteration ideas for an ad")
    p.add_argument("--input", "-i", required=True, help="Ad description text or .txt file")
    p.add_argument("--variations", "-n", type=int, default=5)
    p.set_defaults(func=cmd_iterate)

    # edit
    p = sub.add_parser("edit", help="Edit a video")
    p.add_argument("--operation", "-op", required=True,
                    choices=["trim", "cut", "merge", "overlay-text", "resize", "speed"])
    p.add_argument("--input", "-i")
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--inputs", nargs="+", help="Multiple input files for merge")
    p.add_argument("--start", "-s")
    p.add_argument("--end", "-e")
    p.add_argument("--text", "-t")
    p.add_argument("--position", "-p")
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--speed", type=float)
    p.set_defaults(func=cmd_edit)

    # remove-watermark
    p = sub.add_parser("remove-watermark", help="Remove watermarks from image or video")
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--search-area", choices=["corners", "bottom", "all"], default="corners")
    p.add_argument("--region", help="Manual region: x,y,w,h")
    p.set_defaults(func=cmd_remove_watermark)

    # remove-subtitles
    p = sub.add_parser("remove-subtitles", help="Remove subtitles from image or video")
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--output", "-o", required=True)
    p.set_defaults(func=cmd_remove_subtitles)

    # generate-script
    p = sub.add_parser("generate-script", help="Generate a custom Python script")
    p.add_argument("description", nargs="+")
    p.add_argument("--filename", "-f")
    p.add_argument("--show", action="store_true", help="Print generated script")
    p.set_defaults(func=cmd_generate_script)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
