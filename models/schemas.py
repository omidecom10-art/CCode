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


class ProductCandidate(BaseModel):
    name: str = Field(description="Product name")
    description: str = Field(description="Brief product description")
    niche: str = Field(description="Product niche/category")
    supplier_cost_usd: float = Field(description="Estimated supplier/AliExpress cost")
    selling_price_usd: float = Field(description="Recommended selling price")
    margin_percent: float = Field(description="Gross margin percentage")
    target_audience: str = Field(description="Who buys this product")
    best_platform: str = Field(description="Best ad platform: tiktok, instagram, facebook, youtube")
    trend_direction: str = Field(description="rising, stable, or declining")
    competition_level: str = Field(description="low, medium, or high")
    virality_score: int = Field(ge=1, le=10, description="Virality potential 1-10")
    wow_factor: str = Field(description="What makes this product stand out")
    ad_angle: str = Field(description="Suggested ad angle/hook")
    why_winner: str = Field(description="Why this could be a winning product")


class ProductSearchResult(BaseModel):
    products: list[ProductCandidate] = Field(description="List of product candidates")
    niche_summary: str = Field(description="Brief summary of the niche landscape")
    top_pick_index: int = Field(description="Index of the #1 recommended product (0-based)")


class DemandAnalysis(BaseModel):
    trend_direction: str = Field(description="rising, stable, declining")
    social_media_buzz: str = Field(description="Level and nature of social media activity")
    problem_solved: str = Field(description="What problem or desire it addresses")
    market_size: str = Field(description="Estimated market size/potential")


class ProfitAnalysis(BaseModel):
    supplier_cost_usd: float
    selling_price_usd: float
    margin_percent: float
    aov_potential: str = Field(description="Average order value potential with bundles/upsells")


class CompetitionAnalysis(BaseModel):
    seller_count: str = Field(description="How many competitors")
    brand_dominance: str = Field(description="Are big brands dominating?")
    ad_saturation: str = Field(description="How saturated are ads for this product")
    differentiation: str = Field(description="How to stand out")


class AdPotentialAnalysis(BaseModel):
    video_ad_potential: int = Field(ge=1, le=10, description="Can you make a compelling video? 1-10")
    best_ad_angles: list[str] = Field(description="Ad angles that work")
    ugc_potential: str = Field(description="UGC content potential")
    demo_possible: bool = Field(description="Can you do before/after or demo?")


class RiskAnalysis(BaseModel):
    shipping_risk: str
    quality_risk: str
    legal_risk: str
    seasonal_risk: str
    overall_risk: str = Field(description="low, medium, or high")


class ProductAnalysis(BaseModel):
    product_name: str
    verdict: str = Field(description="YES, MAYBE, or NO")
    overall_score: int = Field(ge=1, le=100, description="Overall score 1-100")
    demand: DemandAnalysis
    profit: ProfitAnalysis
    competition: CompetitionAnalysis
    ad_potential: AdPotentialAnalysis
    risks: RiskAnalysis
    hook_ideas: list[str] = Field(description="3 ad hook ideas")
    target_segments: list[str] = Field(description="Target audience segments")
    best_ad_format: str = Field(description="UGC, demo, testimonial, etc.")
    scaling_strategy: str = Field(description="How to scale this product")
    action_steps: list[str] = Field(description="Immediate next steps")
