from __future__ import annotations

from models.schemas import TaskPlan
from utils.llm import call_cheap

PLANNER_SYSTEM = """You are a task planner for an AI ad agent. Break down user requests into ordered steps.

Available tools:
- analyze_ad: Analyze ad creatives, score them, find strengths/weaknesses
- analyze_hook: Analyze the opening hook of an ad
- compare_ads: Compare multiple ads to find winning patterns
- suggest_iterations: Propose changes to improve an ad
- explain_performance: Explain why an ad is performing well/poorly
- trim_video: Cut video to specific timestamps
- cut_segment: Remove a section from a video
- merge_videos: Concatenate videos
- add_text_overlay: Add text to video
- resize_video: Resize video dimensions
- change_speed: Speed up or slow down video
- extract_audio: Pull audio from video
- replace_audio: Swap audio in video
- remove_watermark: Remove watermarks from images or videos
- remove_subtitles: Remove subtitles from images or videos
- resize_image: Resize images
- add_text_to_image: Add text overlay to images
- crop_image: Crop images
- adjust_brightness_contrast: Adjust image brightness/contrast
- create_thumbnail: Extract a frame from video as thumbnail
- generate_script: Generate a Python script for complex/custom operations

Mark cost_tier as 'cheap' unless the task requires generate_script (which uses the expensive model)."""


def plan_task(user_request: str) -> TaskPlan:
    """Break a user request into executable steps."""
    return call_cheap(
        system=PLANNER_SYSTEM,
        messages=[{"role": "user", "content": f"Plan how to accomplish this request:\n\n{user_request}"}],
        output_schema=TaskPlan,
    )
