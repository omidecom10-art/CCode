"""Research agent: investigates the product, its reviews and competitor ads with tools, then returns a
ResearchReport where every insight cites evidence ids. It decides which tools to call and in what order."""
import json
import re

from ..data import BrandKit
from ..schemas import ResearchReport

SYSTEM = """You are the research agent for an e-commerce brand's creative team.
Investigate the product, its customer reviews and competitor ads with the tools, then report what the
creative team needs: the customer's own words, real benefits, objections, how competitors advertise, and
gaps we can own.

Rules:
- Use the tools. Look at the full review set (high and low ratings) and every competitor ad before concluding.
- Every insight, quote and angle must cite evidence ids exactly as the tools return them
  (reviews like R07, competitor ads like C03, product facts like P-desc or P-cold_retention, brand claims like B-claim-1).
- Quotes must be verbatim excerpts from reviews.
- Competitor ads are for angles and gaps only. Never treat a competitor's claim as true for our product.
- Flag anything the copy must avoid: unsupported claims, health or body claims, claims only competitors make,
  and wording that the brand guide forbids.
- Recommend exactly three distinct ad angles grounded in reviews and approved claims."""


def tools_spec():
    obj = lambda props, req: {"type": "object", "properties": props, "required": req, "additionalProperties": False}  # noqa: E731
    return [
        {"name": "get_product", "strict": True, "description": "Product title, price, description and specs, each with its evidence id.",
         "input_schema": obj({}, [])},
        {"name": "get_brand_guide", "strict": True, "description": "Brand voice, audience, approved claims (with ids), forbidden phrases, offer and CTA.",
         "input_schema": obj({}, [])},
        {"name": "search_reviews", "strict": True,
         "description": "Search customer reviews. Empty query returns all reviews in the rating range. Results include review ids.",
         "input_schema": obj({"query": {"type": "string"}, "min_rating": {"type": "integer"}, "max_rating": {"type": "integer"}},
                             ["query", "min_rating", "max_rating"])},
        {"name": "review_stats", "strict": True, "description": "Review count, average rating and rating distribution.",
         "input_schema": obj({}, [])},
        {"name": "get_competitor_ads", "strict": True, "description": "Competitor ads currently running, with ids, platform and days running.",
         "input_schema": obj({}, [])},
    ]


def tool_handler(kit: BrandKit):
    ev = kit.evidence()

    def handle(name: str, args: dict) -> str:
        if name == "get_product":
            facts = [{"id": k, "text": v.text} for k, v in ev.items() if v.source == "product"]
            return json.dumps({"title": kit.product["title"], "facts": facts})
        if name == "get_brand_guide":
            b = kit.brand
            return json.dumps({"voice": b["voice"], "audience": b["audience"], "offer": {"id": "B-offer", "text": b["offer"]},
                               "cta": b["cta"], "approved_claims": [{"id": k, "text": v.text} for k, v in ev.items() if k.startswith("B-claim")],
                               "do_not_say": b["do_not_say"]})
        if name == "search_reviews":
            words = [w for w in re.findall(r"[a-z0-9']+", args["query"].lower()) if len(w) > 2]
            hits = [r for r in kit.reviews if args["min_rating"] <= r["rating"] <= args["max_rating"]
                    and (not words or any(w in r["text"].lower() for w in words))]
            return json.dumps([{"id": r["id"], "rating": r["rating"], "verified": r["verified"], "text": r["text"]} for r in hits])
        if name == "review_stats":
            ratings = [r["rating"] for r in kit.reviews]
            return json.dumps({"count": len(ratings), "average": round(sum(ratings) / len(ratings), 2),
                               "distribution": {s: ratings.count(s) for s in range(5, 0, -1)}})
        if name == "get_competitor_ads":
            return json.dumps(kit.competitor_ads)
        raise ValueError(f"unknown tool {name}")

    return handle


def run(llm, settings, kit: BrandKit):
    prompt = (f"Research the product '{kit.product['title']}' for {kit.brand['name']} and prepare the creative brief. "
              "Start by calling the tools.")
    return llm.run_agent("research", settings.research_model, SYSTEM, prompt, ResearchReport,
                         tools=tools_spec(), tool_handler=tool_handler(kit))
