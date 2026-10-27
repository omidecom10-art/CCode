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


def cmd_write_script(args):
    from agent.script_writer import save_script, write_ad_script
    brief = " ".join(args.brief)
    print(f"Writing {args.duration}s ad script for {args.platform}...\n")
    script = write_ad_script(brief, args.platform, args.duration)
    path = save_script(script)
    print(Path(path).read_text())
    print(f"\nSaved to: {path}")


def cmd_hooks(args):
    from agent.script_writer import write_hook_variations
    product = " ".join(args.product)
    print(f"Generating {args.num} hooks for {args.platform}...\n")
    hooks = write_hook_variations(product, args.num, args.platform)
    for i, hook in enumerate(hooks, 1):
        print(f"--- Hook {i}: {hook.variation_name} ({hook.angle}) ---")
        print(f"  Text: {hook.script_text}")
        print(f"  Visuellt: {hook.visual_direction}")
        print(f"  Varfor: {hook.why_it_works}")
        print()


def cmd_iterate_script(args):
    from agent.script_writer import iterate_winning_script
    script = Path(args.script).read_text() if Path(args.script).exists() else args.script
    what_worked = " ".join(args.what_worked)
    print(f"Creating {args.variations} variations...\n")
    variations = iterate_winning_script(script, what_worked, args.variations)
    for i, var in enumerate(variations, 1):
        print(f"=== Variation {i}: {var.variation_name} ({var.angle}) ===")
        print(var.script_text)
        print(f"\nVisuellt: {var.visual_direction}")
        print(f"Varfor det funkar: {var.why_it_works}")
        print()


def cmd_find_products(args):
    from tools.product_researcher import search_trending_products
    niche = " ".join(args.niche)
    print(f"Soker vinnande produkter i: {niche}...\n")
    products = search_trending_products(niche, args.num)
    for i, p in enumerate(products, 1):
        margin_bar = "#" * int(p.margin_percent / 10)
        print(f"{'='*60}")
        print(f"  #{i} {p.name}")
        print(f"{'='*60}")
        print(f"  {p.description}")
        print(f"  Nisch: {p.niche}")
        print(f"  Kostnad: ${p.supplier_cost_usd:.2f} -> Pris: ${p.selling_price_usd:.2f} -> Marginal: {p.margin_percent:.0f}% [{margin_bar}]")
        print(f"  Malgrupp: {p.target_audience}")
        print(f"  Plattform: {p.best_platform} | Trend: {p.trend_direction} | Konkurrens: {p.competition_level}")
        print(f"  Viralpoang: {'*' * p.virality_score}{'.' * (10 - p.virality_score)} ({p.virality_score}/10)")
        print(f"  Wow-faktor: {p.wow_factor}")
        print(f"  Annonsvinkel: {p.ad_angle}")
        print(f"  Varfor vinnare: {p.why_winner}")
        print()


def cmd_analyze_product(args):
    from tools.product_researcher import analyze_product
    product = " ".join(args.product)
    print(f"Djupanalyserar: {product}...\n")
    analysis = analyze_product(product, args.url, args.niche)
    print(f"{'='*60}")
    print(f"  {analysis.product_name}")
    print(f"  Verdict: {analysis.verdict} | Score: {analysis.overall_score}/100")
    print(f"{'='*60}")
    print(f"\n--- Efterfragan ---")
    print(f"  Trend: {analysis.demand.trend_direction}")
    print(f"  Social media: {analysis.demand.social_media_buzz}")
    print(f"  Problem: {analysis.demand.problem_solved}")
    print(f"  Marknad: {analysis.demand.market_size}")
    print(f"\n--- Vinst ---")
    print(f"  Kostnad: ${analysis.profit.supplier_cost_usd:.2f}")
    print(f"  Pris: ${analysis.profit.selling_price_usd:.2f}")
    print(f"  Marginal: {analysis.profit.margin_percent:.0f}%")
    print(f"  AOV-potential: {analysis.profit.aov_potential}")
    print(f"\n--- Konkurrens ---")
    print(f"  Saljare: {analysis.competition.seller_count}")
    print(f"  Stormarken: {analysis.competition.brand_dominance}")
    print(f"  Annonsmattnnad: {analysis.competition.ad_saturation}")
    print(f"  Differentiering: {analysis.competition.differentiation}")
    print(f"\n--- Annonspotential ---")
    print(f"  Videopotential: {analysis.ad_potential.video_ad_potential}/10")
    print(f"  Basta vinklar: {', '.join(analysis.ad_potential.best_ad_angles)}")
    print(f"  UGC: {analysis.ad_potential.ugc_potential}")
    print(f"  Demo mojlig: {'Ja' if analysis.ad_potential.demo_possible else 'Nej'}")
    print(f"\n--- Risker ---")
    print(f"  Frakt: {analysis.risks.shipping_risk}")
    print(f"  Kvalitet: {analysis.risks.quality_risk}")
    print(f"  Juridiskt: {analysis.risks.legal_risk}")
    print(f"  Sasong: {analysis.risks.seasonal_risk}")
    print(f"  Total risk: {analysis.risks.overall_risk}")
    print(f"\n--- Hook-ideer ---")
    for i, hook in enumerate(analysis.hook_ideas, 1):
        print(f"  {i}. {hook}")
    print(f"\n--- Nasta steg ---")
    for i, step in enumerate(analysis.action_steps, 1):
        print(f"  {i}. {step}")
    print()


def cmd_product_report(args):
    from tools.product_researcher import generate_product_report
    niche = " ".join(args.niche)
    print(f"Genererar produktrapport for: {niche}...\n")
    report = generate_product_report(niche, args.budget)
    print(report)
    if args.output:
        Path(args.output).write_text(report)
        print(f"\nRapporten sparad till: {args.output}")


def cmd_validate_product(args):
    from tools.product_researcher import validate_product_idea
    product = " ".join(args.product)
    print(f"Validerar: {product}...\n")
    result = validate_product_idea(product, args.price, args.cost)
    print(result)


def cmd_compare_products(args):
    from tools.product_researcher import compare_products
    print(f"Jamfor {len(args.products)} produkter...\n")
    result = compare_products(args.products)
    print(result)


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

    # write-script (ad video script/manus)
    p = sub.add_parser("write-script", help="Write a video ad script/manus")
    p.add_argument("brief", nargs="+", help="What the ad is about")
    p.add_argument("--platform", default="tiktok", choices=["tiktok", "instagram", "facebook", "youtube"])
    p.add_argument("--duration", "-d", type=int, default=30, help="Video length in seconds")
    p.set_defaults(func=cmd_write_script)

    # hooks (generate hook variations)
    p = sub.add_parser("hooks", help="Generate scroll-stopping hook variations for A/B testing")
    p.add_argument("product", nargs="+", help="Product or offer description")
    p.add_argument("--num", "-n", type=int, default=10, help="Number of hooks to generate")
    p.add_argument("--platform", default="tiktok", choices=["tiktok", "instagram", "facebook", "youtube"])
    p.set_defaults(func=cmd_hooks)

    # iterate-script (iterate on a winning script)
    p = sub.add_parser("iterate-script", help="Create variations of a winning ad script")
    p.add_argument("--script", "-s", required=True, help="Winning script text or .txt file")
    p.add_argument("what_worked", nargs="+", help="What elements performed well")
    p.add_argument("--variations", "-n", type=int, default=5)
    p.set_defaults(func=cmd_iterate_script)

    # find-products
    p = sub.add_parser("find-products", help="Find winning dropshipping products in a niche")
    p.add_argument("niche", nargs="+", help="Niche to search in")
    p.add_argument("--num", "-n", type=int, default=10, help="Number of products to find")
    p.set_defaults(func=cmd_find_products)

    # analyze-product
    p = sub.add_parser("analyze-product", help="Deep analysis of a product's dropshipping potential")
    p.add_argument("product", nargs="+", help="Product name")
    p.add_argument("--url", "-u", help="Product URL for reference")
    p.add_argument("--niche", help="Product niche for context")
    p.set_defaults(func=cmd_analyze_product)

    # product-report
    p = sub.add_parser("product-report", help="Generate a full product research report for a niche")
    p.add_argument("niche", nargs="+", help="Niche to research")
    p.add_argument("--budget", "-b", type=float, help="Testing budget in USD")
    p.add_argument("--output", "-o", help="Save report to file")
    p.set_defaults(func=cmd_product_report)

    # validate-product
    p = sub.add_parser("validate-product", help="Quick validation of a product idea")
    p.add_argument("product", nargs="+", help="Product name")
    p.add_argument("--price", "-p", type=float, required=True, help="Selling price in USD")
    p.add_argument("--cost", "-c", type=float, required=True, help="Supplier cost in USD")
    p.set_defaults(func=cmd_validate_product)

    # compare-products
    p = sub.add_parser("compare-products", help="Compare products for dropshipping potential")
    p.add_argument("products", nargs="+", help="Product names to compare")
    p.set_defaults(func=cmd_compare_products)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
