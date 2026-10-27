"""Product research tool — finds and scores potential winning dropshipping products."""
from __future__ import annotations

import json
import re
import urllib.request
import urllib.parse
from datetime import datetime

from models.schemas import ProductCandidate, ProductAnalysis, ProductSearchResult
from utils.llm import call_cheap


def search_trending_products(niche: str, num_results: int = 10) -> list[ProductCandidate]:
    """Use AI to generate trending product ideas based on niche and current trends."""
    system = """You are a dropshipping product research expert. You analyze market trends,
social media virality, and consumer behavior to identify winning products.

A winning dropshipping product has:
- High perceived value vs low cost (3-5x markup minimum)
- Solves a clear problem or triggers impulse buys
- Hard to find in local stores (not on every shelf)
- Lightweight and cheap to ship
- Not dominated by big brands
- Has "wow factor" or is trending on social media
- Can be demonstrated in a short video ad

Respond in the same language the user writes in."""

    prompt = f"""Find {num_results} potential winning dropshipping products in the niche: "{niche}"

For each product, provide:
1. Product name and brief description
2. Why it could be a winner (problem it solves, wow factor, trend)
3. Estimated AliExpress/supplier cost in USD
4. Suggested selling price in USD
5. Target audience
6. Best platform to advertise on (TikTok, Instagram, Facebook)
7. Trend direction (rising, stable, declining)
8. Competition level (low, medium, high)
9. Virality potential (1-10)
10. A scroll-stopping ad angle

Base your analysis on current consumer trends, social media patterns, and proven dropshipping winners.
Think about seasonal trends, emerging niches, and products going viral."""

    result = call_cheap(
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_schema=ProductSearchResult,
    )

    return result.products


def analyze_product(product_name: str, product_url: str | None = None, niche: str | None = None) -> ProductAnalysis:
    """Deep analysis of a specific product's dropshipping potential."""
    system = """You are an expert dropshipping product analyst. You evaluate products based on:
- Market demand and trend trajectory
- Profit margins and pricing strategy
- Competition analysis
- Ad creative potential (can you make a viral ad?)
- Shipping and fulfillment complexity
- Return/refund risk
- Scalability potential
- Seasonal factors

Be brutally honest. Most products fail — only recommend truly promising ones.
Respond in the same language the user writes in."""

    context = f"Product: {product_name}"
    if product_url:
        context += f"\nURL: {product_url}"
    if niche:
        context += f"\nNiche: {niche}"

    prompt = f"""{context}

Perform a complete dropshipping potential analysis:

1. VERDICT: Is this a potential winner? (YES / MAYBE / NO)
2. OVERALL SCORE: 1-100

3. DEMAND ANALYSIS:
   - Search trend direction
   - Social media buzz
   - Problem/desire it addresses
   - Market size estimate

4. PROFIT ANALYSIS:
   - Estimated supplier cost
   - Recommended selling price
   - Expected profit margin %
   - Average order value potential (bundles, upsells)

5. COMPETITION:
   - How many sellers already sell this?
   - Are big brands dominating?
   - How saturated are ads for this product?
   - Can you differentiate?

6. AD POTENTIAL:
   - Can you make a compelling 15-30s video?
   - What ad angles work?
   - UGC potential
   - Before/after demonstration possible?

7. RISKS:
   - Shipping time concerns
   - Quality/return issues
   - Legal/trademark risks
   - Seasonal dependency

8. SCALING STRATEGY:
   - Best starting platform
   - Testing budget recommendation
   - Scaling approach
   - When to move to branding/private label

9. AD SCRIPT IDEAS:
   - 3 different hook ideas
   - Target audience segments
   - Best ad format (UGC, demo, testimonial, etc.)

10. FINAL RECOMMENDATION with action steps."""

    return call_cheap(
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_schema=ProductAnalysis,
    )


def find_products_by_criteria(criteria: dict) -> list[ProductCandidate]:
    """Find products matching specific criteria (price range, margin, trend, etc.)."""
    system = """You are a dropshipping product research expert.
Find products that match the given criteria exactly.
Respond in the same language the user writes in."""

    criteria_text = "\n".join(f"- {k}: {v}" for k, v in criteria.items())

    prompt = f"""Find 10 dropshipping products matching these criteria:
{criteria_text}

For each product, analyze its winning potential. Focus on products that are
currently trending or have untapped potential. Avoid oversaturated products."""

    result = call_cheap(
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_schema=ProductSearchResult,
    )

    return result.products


def compare_products(products: list[str]) -> str:
    """Compare multiple products and rank them by dropshipping potential."""
    system = """You are a dropshipping product analyst. Compare products objectively
and rank them by their potential to be profitable dropshipping products.
Respond in the same language the user writes in."""

    products_text = "\n".join(f"{i+1}. {p}" for i, p in enumerate(products))

    prompt = f"""Compare these products for dropshipping potential and rank them:

{products_text}

For each product, score:
- Demand (1-10)
- Margins (1-10)
- Competition (1-10, higher = less competition = better)
- Ad potential (1-10)
- Scalability (1-10)

Then rank them overall with a clear recommendation on which to test first and why."""

    return call_cheap(
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )


def generate_product_report(niche: str, budget: float | None = None) -> str:
    """Generate a comprehensive product research report for a niche."""
    system = """You are a senior dropshipping consultant writing a product research report.
Be data-driven, specific, and actionable. No fluff.
Respond in the same language the user writes in."""

    budget_text = f"\nTesting budget: ${budget}" if budget else ""

    prompt = f"""Write a comprehensive dropshipping product research report for the niche: "{niche}"{budget_text}

Include:

## NICHE OVERVIEW
- Market size and growth
- Key trends driving demand
- Seasonal patterns
- Competition landscape

## TOP 5 PRODUCT PICKS
For each:
- Product name and description
- Supplier cost → Selling price → Margin
- Why it's a winner NOW
- Risk level (low/medium/high)
- Ad angle that works

## TESTING STRATEGY
- Which product to test first and why
- Recommended ad budget per product
- Testing framework (how many creatives, audiences)
- Success metrics (target CPA, ROAS, CTR)

## SUPPLIER STRATEGY
- Where to source (AliExpress, CJ, etc.)
- What to look for in suppliers
- Shipping optimization tips

## AD STRATEGY
- Platform recommendation
- Creative types that work in this niche
- Targeting suggestions
- Scaling triggers

## QUICK ACTION PLAN
- Day 1-3: What to do
- Day 4-7: Testing phase
- Day 8-14: Analysis and scaling decisions"""

    return call_cheap(
        system=system,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8192,
    )


def get_google_trends_interest(keyword: str) -> dict:
    """Fetch basic trend data for a keyword via Google Trends RSS."""
    try:
        encoded = urllib.parse.quote(keyword)
        url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode()
            mentions = data.lower().count(keyword.lower())
            return {"keyword": keyword, "trending_mentions": mentions, "source": "google_trends_rss"}
    except Exception:
        return {"keyword": keyword, "trending_mentions": 0, "source": "unavailable"}


def validate_product_idea(product_name: str, selling_price: float, cost_price: float) -> str:
    """Quick validation of a product idea with margin and feasibility check."""
    margin = ((selling_price - cost_price) / selling_price) * 100 if selling_price > 0 else 0
    ad_budget_per_sale = selling_price * 0.3

    system = """You are a dropshipping product validator. Give a quick, honest assessment.
Respond in the same language the user writes in."""

    prompt = f"""Quick validation for this dropshipping product:

Product: {product_name}
Cost price: ${cost_price:.2f}
Selling price: ${selling_price:.2f}
Gross margin: {margin:.1f}%
Max ad spend per sale (30% of price): ${ad_budget_per_sale:.2f}

Is this viable? Consider:
1. Is the margin enough after ads, shipping, refunds?
2. Can you profitably acquire customers at ${ad_budget_per_sale:.2f} per sale?
3. Is the price point impulse-buy friendly?
4. Quick verdict: GO / TWEAK PRICING / SKIP

Keep it short and actionable."""

    return call_cheap(
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
