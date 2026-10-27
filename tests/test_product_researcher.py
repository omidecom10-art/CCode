"""Tests for the product researcher module."""
from __future__ import annotations

from unittest.mock import patch

from models.schemas import (
    AdPotentialAnalysis,
    CompetitionAnalysis,
    DemandAnalysis,
    ProductAnalysis,
    ProductCandidate,
    ProductSearchResult,
    ProfitAnalysis,
    RiskAnalysis,
)


def _make_candidate(**overrides) -> ProductCandidate:
    defaults = dict(
        name="LED Sunset Lamp",
        description="Aesthetic room lamp",
        niche="Home decor",
        supplier_cost_usd=5.0,
        selling_price_usd=29.99,
        margin_percent=83.3,
        target_audience="18-30 women",
        best_platform="tiktok",
        trend_direction="rising",
        competition_level="medium",
        virality_score=8,
        wow_factor="Creates viral sunset aesthetic",
        ad_angle="Transform your room in seconds",
        why_winner="High perceived value, low cost, very visual",
    )
    defaults.update(overrides)
    return ProductCandidate(**defaults)


def _make_analysis(**overrides) -> ProductAnalysis:
    defaults = dict(
        product_name="LED Sunset Lamp",
        verdict="YES",
        overall_score=82,
        demand=DemandAnalysis(
            trend_direction="rising",
            social_media_buzz="High on TikTok",
            problem_solved="Room aesthetics",
            market_size="Large",
        ),
        profit=ProfitAnalysis(
            supplier_cost_usd=5.0,
            selling_price_usd=29.99,
            margin_percent=83.3,
            aov_potential="Bundle with RGB strip for $49.99",
        ),
        competition=CompetitionAnalysis(
            seller_count="50-100",
            brand_dominance="No",
            ad_saturation="Medium",
            differentiation="Unique color options",
        ),
        ad_potential=AdPotentialAnalysis(
            video_ad_potential=9,
            best_ad_angles=["Room transformation", "Aesthetic setup"],
            ugc_potential="Very high",
            demo_possible=True,
        ),
        risks=RiskAnalysis(
            shipping_risk="Low - lightweight",
            quality_risk="Medium - LED lifespan varies",
            legal_risk="Low",
            seasonal_risk="Low - year round",
            overall_risk="low",
        ),
        hook_ideas=["Watch this room transform", "POV: you found the viral lamp", "This $30 lamp > $200 lighting"],
        target_segments=["College students", "Content creators", "Young women"],
        best_ad_format="UGC room transformation",
        scaling_strategy="Start TikTok, expand to IG/FB",
        action_steps=["Order sample", "Create UGC ad", "Test $50/day"],
    )
    defaults.update(overrides)
    return ProductAnalysis(**defaults)


def test_product_candidate_model():
    p = _make_candidate()
    assert p.name == "LED Sunset Lamp"
    assert p.margin_percent == 83.3
    assert p.virality_score == 8
    assert 1 <= p.virality_score <= 10


def test_product_analysis_model():
    a = _make_analysis()
    assert a.verdict == "YES"
    assert a.overall_score == 82
    assert a.demand.trend_direction == "rising"
    assert a.profit.margin_percent > 50
    assert len(a.hook_ideas) == 3
    assert len(a.action_steps) == 3


def test_product_search_result_model():
    products = [_make_candidate(), _make_candidate(name="Phone Holder")]
    result = ProductSearchResult(
        products=products,
        niche_summary="Home decor is trending",
        top_pick_index=0,
    )
    assert len(result.products) == 2
    assert result.top_pick_index == 0


@patch("tools.product_researcher.call_cheap")
def test_search_trending_products(mock_call):
    mock_call.return_value = ProductSearchResult(
        products=[_make_candidate()],
        niche_summary="Good niche",
        top_pick_index=0,
    )
    from tools.product_researcher import search_trending_products
    results = search_trending_products("home decor", 5)
    assert len(results) == 1
    assert results[0].name == "LED Sunset Lamp"
    mock_call.assert_called_once()


@patch("tools.product_researcher.call_cheap")
def test_analyze_product(mock_call):
    mock_call.return_value = _make_analysis()
    from tools.product_researcher import analyze_product
    result = analyze_product("LED Sunset Lamp")
    assert result.verdict == "YES"
    assert result.overall_score > 0
    mock_call.assert_called_once()


@patch("tools.product_researcher.call_cheap")
def test_validate_product_idea(mock_call):
    mock_call.return_value = "GO - Margins are healthy at 83%"
    from tools.product_researcher import validate_product_idea
    result = validate_product_idea("LED Lamp", 29.99, 5.0)
    assert "GO" in result


@patch("tools.product_researcher.call_cheap")
def test_compare_products(mock_call):
    mock_call.return_value = "Product 1 wins because..."
    from tools.product_researcher import compare_products
    result = compare_products(["LED Lamp", "Phone Holder"])
    assert isinstance(result, str)
    assert len(result) > 0


@patch("tools.product_researcher.call_cheap")
def test_generate_product_report(mock_call):
    mock_call.return_value = "# Product Report\n\nGreat niche..."
    from tools.product_researcher import generate_product_report
    result = generate_product_report("home decor", budget=500.0)
    assert "Product Report" in result


def test_margin_calculation():
    from tools.product_researcher import validate_product_idea
    with patch("tools.product_researcher.call_cheap") as mock_call:
        mock_call.return_value = "GO"
        validate_product_idea("Test Product", 30.0, 10.0)
        call_args = mock_call.call_args
        prompt = call_args[1]["messages"][0]["content"] if "messages" in call_args[1] else call_args[0][1][0]["content"]
        assert "66.7%" in prompt
