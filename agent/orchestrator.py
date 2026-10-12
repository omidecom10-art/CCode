from __future__ import annotations

import json
from pathlib import Path

from models.schemas import WatermarkRegion
from utils.llm import call_with_tools

ORCHESTRATOR_SYSTEM = """You are an AI ad agent that helps create, analyze, and optimize ad creatives.
Respond in the same language the user writes in.

You have access to these tools:
1. analyze_ad - Analyze an ad creative (description + optional metrics)
2. compare_ads - Compare multiple ads to find patterns
3. suggest_iterations - Get iteration ideas for an ad
4. explain_performance - Explain why an ad performs the way it does
5. write_ad_script - Write a complete video ad script/manus with hooks, voiceover, visuals, CTA
6. write_hook_variations - Generate multiple hook variations for A/B testing
7. iterate_winning_script - Create variations on a winning ad script
8. edit_video - Edit videos (trim, cut, merge, overlay text, resize, speed change)
9. remove_watermark - Remove watermarks from images or videos
10. remove_subtitles - Remove subtitles from images or videos
11. process_image - Process images (resize, add text, crop, adjust)

Always think step by step. For multi-step tasks, chain operations in the right order.
Be specific about file paths and parameters. Ask for clarification if essential info is missing."""

TOOL_DEFINITIONS = [
    {
        "name": "analyze_ad",
        "description": "Analyze an ad creative and get scores, strengths, weaknesses, recommendations",
        "input_schema": {
            "type": "object",
            "properties": {
                "ad_description": {"type": "string", "description": "Description of the ad creative"},
                "metrics": {"type": "object", "description": "Performance metrics (CTR, ROAS, etc.)", "default": None},
            },
            "required": ["ad_description"],
        },
    },
    {
        "name": "compare_ads",
        "description": "Compare multiple ads to find winning patterns",
        "input_schema": {
            "type": "object",
            "properties": {
                "ads": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "metrics": {"type": "object"},
                        },
                    },
                },
            },
            "required": ["ads"],
        },
    },
    {
        "name": "suggest_iterations",
        "description": "Suggest specific iterations to improve an ad based on its analysis",
        "input_schema": {
            "type": "object",
            "properties": {
                "ad_description": {"type": "string"},
                "num_variations": {"type": "integer", "default": 5},
            },
            "required": ["ad_description"],
        },
    },
    {
        "name": "explain_performance",
        "description": "Explain why an ad is performing the way it is",
        "input_schema": {
            "type": "object",
            "properties": {
                "ad_description": {"type": "string"},
                "metrics": {"type": "object"},
                "benchmark_metrics": {"type": "object", "default": None},
            },
            "required": ["ad_description", "metrics"],
        },
    },
    {
        "name": "edit_video",
        "description": "Edit a video: trim, cut segment, merge, add text overlay, resize, change speed",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["trim", "cut", "merge", "overlay_text", "resize", "speed"]},
                "input_path": {"type": "string"},
                "output_path": {"type": "string"},
                "start": {"type": "string", "description": "Start timestamp for trim"},
                "end": {"type": "string", "description": "End timestamp for trim"},
                "cut_start": {"type": "string"},
                "cut_end": {"type": "string"},
                "input_paths": {"type": "array", "items": {"type": "string"}, "description": "For merge"},
                "text": {"type": "string", "description": "Text for overlay"},
                "position": {"type": "string", "default": "bottom"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
                "speed": {"type": "number", "description": "Speed multiplier"},
            },
            "required": ["operation"],
        },
    },
    {
        "name": "remove_watermark",
        "description": "Detect and remove watermarks from an image or video",
        "input_schema": {
            "type": "object",
            "properties": {
                "input_path": {"type": "string"},
                "output_path": {"type": "string"},
                "media_type": {"type": "string", "enum": ["image", "video", "auto"], "default": "auto"},
                "region": {
                    "type": "object",
                    "description": "Manual region: {x, y, width, height}. Auto-detect if omitted.",
                    "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "width": {"type": "integer"}, "height": {"type": "integer"}},
                },
            },
            "required": ["input_path", "output_path"],
        },
    },
    {
        "name": "remove_subtitles",
        "description": "Detect and remove subtitles from an image or video",
        "input_schema": {
            "type": "object",
            "properties": {
                "input_path": {"type": "string"},
                "output_path": {"type": "string"},
                "media_type": {"type": "string", "enum": ["image", "video", "auto"], "default": "auto"},
            },
            "required": ["input_path", "output_path"],
        },
    },
    {
        "name": "process_image",
        "description": "Process an image: resize, add text, crop, adjust brightness/contrast",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["resize", "add_text", "crop", "adjust", "platform_resize"]},
                "input_path": {"type": "string"},
                "output_path": {"type": "string"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
                "text": {"type": "string"},
                "position": {"type": "string", "default": "bottom"},
                "platform": {"type": "string", "description": "Platform name for platform_resize"},
                "left": {"type": "integer"}, "top": {"type": "integer"},
                "right": {"type": "integer"}, "bottom": {"type": "integer"},
                "brightness": {"type": "number", "default": 1.0},
                "contrast": {"type": "number", "default": 1.0},
            },
            "required": ["operation", "input_path", "output_path"],
        },
    },
    {
        "name": "write_ad_script",
        "description": "Write a complete video ad script/manus with hooks, voiceover text, visual directions, text overlays, and CTA",
        "input_schema": {
            "type": "object",
            "properties": {
                "brief": {"type": "string", "description": "What the ad is about: product, offer, target audience, key benefit"},
                "platform": {"type": "string", "enum": ["tiktok", "instagram", "facebook", "youtube"], "default": "tiktok"},
                "duration": {"type": "integer", "description": "Video length in seconds", "default": 30},
            },
            "required": ["brief"],
        },
    },
    {
        "name": "write_hook_variations",
        "description": "Generate multiple scroll-stopping hook variations (first 3 seconds) for A/B testing",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_or_offer": {"type": "string", "description": "What you're selling/promoting"},
                "num_hooks": {"type": "integer", "default": 10},
                "platform": {"type": "string", "default": "tiktok"},
            },
            "required": ["product_or_offer"],
        },
    },
    {
        "name": "iterate_winning_script",
        "description": "Create new variations of a winning ad script while keeping what works",
        "input_schema": {
            "type": "object",
            "properties": {
                "original_script": {"type": "string", "description": "The original winning script text"},
                "what_worked": {"type": "string", "description": "What elements performed well"},
                "num_variations": {"type": "integer", "default": 5},
            },
            "required": ["original_script", "what_worked"],
        },
    },
]


def _execute_tool(name: str, params: dict) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        if name == "analyze_ad":
            from tools.ad_analyzer import analyze_ad
            result = analyze_ad(params["ad_description"], params.get("metrics"))
            return result.model_dump_json(indent=2)

        elif name == "compare_ads":
            from tools.ad_analyzer import compare_ads
            result = compare_ads(params["ads"])
            return result.model_dump_json(indent=2)

        elif name == "suggest_iterations":
            from tools.ad_analyzer import analyze_ad, suggest_iterations
            analysis = analyze_ad(params["ad_description"])
            result = suggest_iterations(analysis, params.get("num_variations", 5))
            return result.model_dump_json(indent=2)

        elif name == "explain_performance":
            from tools.ad_analyzer import explain_performance
            return explain_performance(
                params["ad_description"], params["metrics"], params.get("benchmark_metrics")
            )

        elif name == "edit_video":
            from tools.video_editor import (
                add_text_overlay, change_speed, cut_segment,
                merge_videos, resize_video, trim_video,
            )
            op = params["operation"]
            if op == "trim":
                return trim_video(params["input_path"], params["output_path"], params["start"], params["end"])
            elif op == "cut":
                return cut_segment(params["input_path"], params["output_path"], params["cut_start"], params["cut_end"])
            elif op == "merge":
                return merge_videos(params["input_paths"], params["output_path"])
            elif op == "overlay_text":
                return add_text_overlay(
                    params["input_path"], params["output_path"], params["text"],
                    params.get("position", "bottom"),
                )
            elif op == "resize":
                return resize_video(params["input_path"], params["output_path"], params["width"], params["height"])
            elif op == "speed":
                return change_speed(params["input_path"], params["output_path"], params["speed"])
            return f"Unknown video operation: {op}"

        elif name == "remove_watermark":
            from utils.file_helpers import detect_media_type
            input_path = params["input_path"]
            output_path = params["output_path"]
            media = params.get("media_type", "auto")
            if media == "auto":
                media = detect_media_type(input_path)

            if media == "image":
                region = params.get("region")
                if region:
                    from tools.watermark_remover import remove_watermark_from_region
                    return remove_watermark_from_region(input_path, output_path, **region)
                else:
                    from tools.watermark_remover import detect_watermark_regions, remove_watermark_inpaint
                    regions = detect_watermark_regions(input_path)
                    if not regions:
                        return "No watermark regions detected. Try specifying a region manually."
                    return remove_watermark_inpaint(input_path, regions, output_path)
            else:
                region = params.get("region")
                regions = [WatermarkRegion(**region, confidence=1.0)] if region else None
                from tools.watermark_remover import remove_watermark_from_video
                return remove_watermark_from_video(input_path, output_path, regions)

        elif name == "remove_subtitles":
            from utils.file_helpers import detect_media_type
            input_path = params["input_path"]
            output_path = params["output_path"]
            media = params.get("media_type", "auto")
            if media == "auto":
                media = detect_media_type(input_path)

            if media == "image":
                from tools.watermark_remover import remove_subtitles_from_image
                return remove_subtitles_from_image(input_path, output_path)
            else:
                from tools.watermark_remover import remove_subtitles_from_video
                return remove_subtitles_from_video(input_path, output_path)

        elif name == "process_image":
            from tools.image_processor import (
                add_text_to_image, adjust_brightness_contrast,
                crop_image, resize_for_platform, resize_image,
            )
            op = params["operation"]
            if op == "resize":
                return resize_image(params["input_path"], params["output_path"], params["width"], params["height"])
            elif op == "platform_resize":
                return resize_for_platform(params["input_path"], params["output_path"], params["platform"])
            elif op == "add_text":
                return add_text_to_image(
                    params["input_path"], params["output_path"], params["text"],
                    params.get("position", "bottom"),
                )
            elif op == "crop":
                return crop_image(
                    params["input_path"], params["output_path"],
                    params["left"], params["top"], params["right"], params["bottom"],
                )
            elif op == "adjust":
                return adjust_brightness_contrast(
                    params["input_path"], params["output_path"],
                    params.get("brightness", 1.0), params.get("contrast", 1.0),
                )
            return f"Unknown image operation: {op}"

        elif name == "write_ad_script":
            from agent.script_writer import save_script, write_ad_script
            script = write_ad_script(params["brief"], params.get("platform", "tiktok"), params.get("duration", 30))
            path = save_script(script)
            return f"Script saved to: {path}\n\n{script.model_dump_json(indent=2)}"

        elif name == "write_hook_variations":
            from agent.script_writer import write_hook_variations
            hooks = write_hook_variations(
                params["product_or_offer"], params.get("num_hooks", 10), params.get("platform", "tiktok"),
            )
            return json.dumps([h.model_dump() for h in hooks], indent=2, ensure_ascii=False)

        elif name == "iterate_winning_script":
            from agent.script_writer import iterate_winning_script
            variations = iterate_winning_script(
                params["original_script"], params["what_worked"], params.get("num_variations", 5),
            )
            return json.dumps([v.model_dump() for v in variations], indent=2, ensure_ascii=False)

        return f"Unknown tool: {name}"

    except Exception as e:
        return f"Error executing {name}: {e}"


def run(user_request: str, verbose: bool = False) -> str:
    """Run the agent orchestrator loop. Routes 90%+ through Haiku (cheap)."""
    messages = [{"role": "user", "content": user_request}]
    final_text_parts = []

    for _ in range(10):
        response = call_with_tools(
            system=ORCHESTRATOR_SYSTEM,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )

        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "end_turn":
            for block in assistant_content:
                if hasattr(block, "text"):
                    final_text_parts.append(block.text)
            break

        tool_results = []
        for block in assistant_content:
            if block.type == "tool_use":
                if verbose:
                    print(f"  [tool] {block.name}({json.dumps(block.input)[:200]})")
                result = _execute_tool(block.name, block.input)
                if verbose:
                    print(f"  [result] {str(result)[:200]}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return "\n".join(final_text_parts) if final_text_parts else "Agent completed without text output."
