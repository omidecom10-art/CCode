"""Download the openly licensed stand-in images used by the sample brand (run once).

Images come from the Wikimedia Commons API (no key needed), public domain / CC0 / CC BY / CC BY-SA only.
Each file's source, author and licence are written to data/sample_brand/assets/SOURCES.md, and the
b-roll catalog (id, path, tags, description) to assets/broll/catalog.json. They stand in for a real
brand's own product photos and b-roll library.

Usage: python scripts/fetch_sample_assets.py
"""
import io
import json
import re
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "data" / "sample_brand" / "assets"
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "ecom-ai-studio/0.1 (portfolio demo; contact via github.com/cainticjohncarlo-pixel)"}
OK_LICENCE = re.compile(r"^(cc0|public domain|pd|cc by( |-)?(sa )?\d|cc-by(-sa)?-\d)", re.I)

WANTED = [  # (file stem, search query, b-roll tags)
    ("product", "stainless steel water bottle", ["product", "bottle", "close-up"]),
    ("broll_trail", "hiking trail mountains hiker", ["outdoors", "hiking", "adventure"]),
    ("broll_gym", "dumbbells rack weights", ["gym", "workout", "fitness"]),
    ("broll_desk", "laptop desk workspace", ["work", "desk", "office", "daily"]),
    ("broll_ice", "glass of water with ice", ["cold", "ice", "refreshing"]),
    ("broll_camp", "tent camping morning", ["camping", "outdoors", "morning"]),
    ("broll_road", "road trip car highway", ["travel", "commute", "car"]),
]


def candidates(query):
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {query}",
              "gsrnamespace": 6, "gsrlimit": 25, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1920}
    r = requests.get(API, params=params, headers=UA, timeout=60)
    r.raise_for_status()
    pages = sorted(r.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        lic = (meta.get("LicenseShortName", {}).get("value") or "").strip()
        if ii.get("width", 0) >= 1200 and ii.get("height", 0) >= 800 and OK_LICENCE.match(lic) and ii.get("mime", "image/jpeg") != "image/svg+xml":
            author = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value") or "unknown").strip()
            yield {"title": p["title"].replace("File:", ""), "url": ii.get("thumburl") or ii["url"],
                   "page": ii.get("descriptionurl"), "licence": lic, "author": author[:80]}


def main():
    (ASSETS / "broll").mkdir(parents=True, exist_ok=True)
    sources, catalog = [], []
    for stem, query, tags in WANTED:
        for c in candidates(query):
            try:
                img = requests.get(c["url"], headers=UA, timeout=60)
                img.raise_for_status()
                im = Image.open(io.BytesIO(img.content)).convert("RGB")
            except Exception as e:
                print("  skip", c["title"][:50], str(e)[:60])
                continue
            im.thumbnail((1920, 1920))
            rel = "product.jpg" if stem == "product" else f"broll/{stem}.jpg"
            im.save(ASSETS / rel, quality=88)
            sources.append(f"| `{rel}` | {c['title']} | {c['author']} | {c['licence']} | {c['page']} |")
            if stem != "product":
                catalog.append({"id": stem, "path": rel, "type": "still", "tags": tags, "description": c["title"][:120]})
            print("saved", rel, im.size, c["licence"])
            break
        else:
            print("NO MATCH for", query)
        time.sleep(1.0)
    (ASSETS / "SOURCES.md").write_text(
        "# Stand-in assets (openly licensed)\n\nThe sample brand is fictional. These images stand in for a real brand's product "
        "photos and b-roll library. Fetched from Wikimedia Commons by `scripts/fetch_sample_assets.py`.\n\n"
        "| File | Title | Author | Licence | Source |\n|---|---|---|---|---|\n" + "\n".join(sources) + "\n", encoding="utf-8")
    (ASSETS / "broll" / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
