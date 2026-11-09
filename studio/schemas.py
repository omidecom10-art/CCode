"""The contracts between agents. Every LLM call returns one of these, validated by Pydantic.

Length limits and evidence rules are enforced in studio/checks.py (deterministic), not in the schema,
so a slightly-too-long headline becomes a fixable review issue instead of a crashed run.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel


class Evidence(BaseModel):
    id: str            # R07 (review), C03 (competitor ad), P-spec, B-claim-1 (brand)
    source: Literal["review", "competitor", "product", "brand"]
    text: str


class Quote(BaseModel):
    text: str          # verbatim excerpt
    review_id: str


class Insight(BaseModel):
    point: str
    evidence_ids: List[str]


class CompetitorAngle(BaseModel):
    competitor: str
    angle: str
    risk_or_gap: str   # why we should not copy it, or what it leaves open
    evidence_ids: List[str]


class AdAngle(BaseModel):
    name: str
    hook_idea: str
    why_it_works: str
    evidence_ids: List[str]


class ResearchReport(BaseModel):
    product_summary: str
    audience: str
    customer_language: List[Quote]
    benefits: List[Insight]
    objections: List[Insight]
    competitor_angles: List[CompetitorAngle]
    gaps: List[str]
    recommended_angles: List[AdAngle]
    avoid: List[str]   # phrases or claims the copy must not use, with the reason


class Claim(BaseModel):
    text: str
    evidence_ids: List[str]


class StaticAd(BaseModel):
    id: str            # A1, A2, A3
    angle: str
    headline: str      # <= 40 characters
    subhead: str       # <= 90 characters
    offer_line: str    # must equal the brand offer
    cta: str           # must equal the brand CTA
    claims: List[Claim]
    testimonial: Optional[Quote] = None


class Beat(BaseModel):
    line: str          # what the voiceover says
    caption: str       # on-screen text, <= 32 characters
    broll_id: str      # id from the b-roll catalog
    evidence_ids: List[str]


class VideoScript(BaseModel):
    id: str            # V1
    angle: str
    beats: List[Beat]  # 3 to 6 beats, hook first
    end_card: str      # short line on the final card


class AdCopy(BaseModel):
    static_ads: List[StaticAd]
    video: VideoScript


class Issue(BaseModel):
    severity: Literal["blocker", "fix", "note"]
    quote: str
    problem: str
    fix: str


class AssetReview(BaseModel):
    asset_id: str
    verdict: Literal["pass", "fail"]
    issues: List[Issue]


class ReviewReport(BaseModel):
    summary: str
    assets: List[AssetReview]
