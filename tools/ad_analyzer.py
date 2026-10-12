from __future__ import annotations

import json

from models.schemas import AdAnalysis, ComparisonResult, HookAnalysis, IterationPlan
from utils.llm import call_cheap

ANALYST_SYSTEM = """You are an expert performance marketing analyst specializing in paid social ads.
You analyze ad creatives with a focus on what drives conversions, CTR, and ROAS.
Be specific and actionable — no generic advice. Reference concrete elements of the ad.
Consider: hook strength, visual hierarchy, copy clarity, CTA placement, audience targeting fit,
scroll-stopping power, emotional triggers, social proof, urgency, and platform best practices."""


def analyze_ad(ad_description: str, metrics: dict | None = None) -> AdAnalysis:
    """Analyze an ad creative and return structured scores + recommendations."""
    prompt = f"Analyze this ad creative:\n\n{ad_description}"
    if metrics:
        prompt += f"\n\nPerformance metrics:\n{json.dumps(metrics, indent=2)}"
    prompt += "\n\nProvide detailed, specific analysis with scores and actionable recommendations."

    return call_cheap(
        system=ANALYST_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_schema=AdAnalysis,
    )


def analyze_hook(hook_description: str) -> HookAnalysis:
    """Specialized analysis of the first 3 seconds / opening hook of an ad."""
    return call_cheap(
        system=ANALYST_SYSTEM + "\nFocus specifically on the opening hook — the first 3 seconds that determine if someone stops scrolling.",
        messages=[{"role": "user", "content": f"Analyze this ad hook:\n\n{hook_description}"}],
        output_schema=HookAnalysis,
    )


def compare_ads(ads: list[dict]) -> ComparisonResult:
    """Compare multiple ads and identify patterns in winners vs losers."""
    ads_text = "\n\n".join(
        f"--- Ad {i} ---\nDescription: {ad.get('description', 'N/A')}\nMetrics: {json.dumps(ad.get('metrics', {}))}"
        for i, ad in enumerate(ads)
    )
    return call_cheap(
        system=ANALYST_SYSTEM,
        messages=[{"role": "user", "content": f"Compare these ads and identify what makes the winners win:\n\n{ads_text}"}],
        output_schema=ComparisonResult,
    )


def suggest_iterations(analysis: AdAnalysis, num_variations: int = 5) -> IterationPlan:
    """Given an ad analysis, propose concrete iteration changes."""
    return call_cheap(
        system=ANALYST_SYSTEM + "\nYou are now proposing specific iterations on an existing ad to improve performance.",
        messages=[{"role": "user", "content": (
            f"Based on this analysis, propose {num_variations} specific changes to iterate on this ad.\n\n"
            f"Current analysis:\n{analysis.model_dump_json(indent=2)}\n\n"
            "For each change, explain what to modify, how, and why it should improve performance."
        )}],
        output_schema=IterationPlan,
    )


def explain_performance(
    ad_description: str,
    metrics: dict,
    benchmark_metrics: dict | None = None,
) -> str:
    """Explain why an ad is performing the way it is — plain text analysis."""
    prompt = f"Ad: {ad_description}\n\nMetrics: {json.dumps(metrics, indent=2)}"
    if benchmark_metrics:
        prompt += f"\n\nBenchmarks: {json.dumps(benchmark_metrics, indent=2)}"
    prompt += "\n\nExplain in detail why this ad is performing this way. What's working, what's not, and why?"

    return call_cheap(
        system=ANALYST_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
