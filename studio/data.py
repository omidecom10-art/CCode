"""Load a brand folder and build the evidence registry every claim must point back to."""
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .schemas import Evidence


@dataclass
class BrandKit:
    root: Path
    brand: dict
    product: dict
    reviews: List[dict]
    competitor_ads: List[dict]
    broll: List[dict]

    @property
    def product_image(self) -> Path:
        return self.root / self.product["image"]

    def evidence(self) -> Dict[str, Evidence]:
        """Every fact an agent may cite, keyed by id. Copy that cites anything else fails review."""
        ev: Dict[str, Evidence] = {}
        for r in self.reviews:
            ev[r["id"]] = Evidence(id=r["id"], source="review", text=f"({r['rating']} stars) {r['text']}")
        for a in self.competitor_ads:
            ev[a["id"]] = Evidence(id=a["id"], source="competitor", text=f"{a['competitor']}: {a['headline']}. {a['body']}")
        ev["P-desc"] = Evidence(id="P-desc", source="product", text=self.product["description"])
        for k, v in self.product.get("specs", {}).items():
            ev[f"P-{k}"] = Evidence(id=f"P-{k}", source="product", text=f"{k}: {v if isinstance(v, str) else ', '.join(v)}")
        ev["P-price"] = Evidence(id="P-price", source="product", text=f"price: ${self.product['price']}")
        for i, c in enumerate(self.brand["approved_claims"], 1):
            ev[f"B-claim-{i}"] = Evidence(id=f"B-claim-{i}", source="brand", text=c)
        ev["B-offer"] = Evidence(id="B-offer", source="brand", text=self.brand["offer"])
        return ev


def load_brand(folder: Path) -> BrandKit:
    folder = Path(folder)
    with open(folder / "reviews.csv", encoding="utf-8", newline="") as f:
        reviews = [dict(r, rating=int(r["rating"])) for r in csv.DictReader(f)]
    broll_catalog = folder / "assets" / "broll" / "catalog.json"
    return BrandKit(
        root=folder,
        brand=json.loads((folder / "brand.json").read_text(encoding="utf-8")),
        product=json.loads((folder / "product.json").read_text(encoding="utf-8")),
        reviews=reviews,
        competitor_ads=json.loads((folder / "competitor_ads.json").read_text(encoding="utf-8"))["ads"],
        broll=json.loads(broll_catalog.read_text(encoding="utf-8")) if broll_catalog.exists() else [],
    )
