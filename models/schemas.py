from __future__ import annotations

from pydantic import BaseModel, Field


class AdAnalysis(BaseModel):
    hook_score: int = Field(ge=1, le=10, description="Hook effectiveness 1-10")
    visual_score: int = Field(ge=1, le=10, description="Visual quality 1-10")
    copy_score: int = Field(ge=1, le=10, description="Copywriting quality 1-10")
    cta_score: int = Field(ge=1, le=10, description="Call-to-action strength 1-10")
    overall_score: int = Field(ge=1, le=10, description="Overall ad effectiveness 1-10")
    strengths: list[str] = Field(description="What works well in this ad")
    weaknesses: list[str] = Field(description="What needs improvement")
    recommendations: list[str] = Field(description="Specific actionable improvements")
    winning_elements: list[str] = Field(description="Elements worth keeping in iterations")
    target_audience_fit: str = Field(description="How well the ad matches its target audience")


class HookAnalysis(BaseModel):
    attention_grab: int = Field(ge=1, le=10)
    curiosity_factor: int = Field(ge=1, le=10)
    relevance: int = Field(ge=1, le=10)
    emotional_trigger: str
    improvement_suggestions: list[str]


class ChangeItem(BaseModel):
    element: str = Field(description="Element to change: hook, cta, visual, copy, pacing")
    current_state: str
    proposed_change: str
    rationale: str


class IterationPlan(BaseModel):
    original_analysis: AdAnalysis
    changes: list[ChangeItem]
    expected_improvement: str
    priority_order: list[int] = Field(description="Order to apply changes, by index")


class ComparisonResult(BaseModel):
    winner: int = Field(description="Index of the best ad (0-based)")
    ranking: list[int] = Field(description="Indices ranked best to worst")
    common_strengths: list[str]
    common_weaknesses: list[str]
    key_differentiators: list[str]
    pattern_insights: str = Field(description="What patterns emerge from the winning ads")


class TaskStep(BaseModel):
    action: str
    tool: str
    parameters: dict
    depends_on: list[int] = Field(default_factory=list)


class TaskPlan(BaseModel):
    task_type: str = Field(description="analyze, edit_video, remove_watermark, iterate_ad, generate_script")
    steps: list[TaskStep]
    estimated_cost_tier: str = Field(description="cheap or expensive")


class VideoEditSpec(BaseModel):
    operation: str = Field(description="trim, cut, merge, overlay_text, resize")
    input_files: list[str]
    output_file: str
    parameters: dict


class WatermarkRegion(BaseModel):
    x: int
    y: int
    width: int
    height: int
    confidence: float = Field(ge=0.0, le=1.0)


class ScriptSection(BaseModel):
    timestamp: str = Field(description="Time range, e.g. '0-3s'")
    section_name: str = Field(description="e.g. Hook, Problem, Solution, CTA")
    voiceover: str = Field(description="Exact words spoken")
    visual_direction: str = Field(description="What the viewer sees on screen")
    text_overlay: str = Field(default="", description="Text shown on screen")
    music_direction: str = Field(default="", description="Music/sound cues")


class AdScript(BaseModel):
    title: str = Field(description="Short title for this script")
    platform: str = Field(description="Target platform: tiktok, instagram, facebook, youtube")
    duration_seconds: int = Field(description="Total video length in seconds")
    structure: str = Field(description="Script structure used, e.g. Hook-Problem-Solution-CTA")
    sections: list[ScriptSection] = Field(description="Ordered sections of the script")
    key_message: str = Field(description="The core message/selling point")
    notes: str = Field(default="", description="Production notes or tips")


class ScriptVariation(BaseModel):
    variation_name: str = Field(description="Short name for this variation")
    angle: str = Field(description="The approach/angle used, e.g. 'social proof', 'FOMO'")
    script_text: str = Field(description="The full script or hook text")
    visual_direction: str = Field(description="Visual instructions")
    why_it_works: str = Field(description="Why this variation should perform well")


class AdScriptBrief(BaseModel):
    product_or_service: str
    target_audience: str
    key_benefit: str
    platform: str = "tiktok"
    duration_seconds: int = 30
    tone: str = Field(default="engaging", description="e.g. urgent, friendly, edgy, luxurious")
