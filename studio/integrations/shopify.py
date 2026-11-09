"""Shopify: pull the product the ads are for. Admin GraphQL when SHOPIFY_ADMIN_TOKEN is set, otherwise the
store's public /products/<handle>.json. Returns the same shape as data/<brand>/product.json."""
import requests

from . import Integration

QUERY = """query($handle: String!) { productByHandle(handle: $handle) {
  id handle title descriptionHtml featuredImage { url }
  priceRangeV2 { minVariantPrice { amount currencyCode } } } }"""


class Shopify(Integration):
    name = "shopify"

    @property
    def live(self) -> bool:
        return bool(self.creds.get("shopify_domain"))

    def product(self, handle: str) -> dict:
        domain = self.creds.get("shopify_domain")
        if not domain:
            return self.dry_run({"would_fetch": f"https://<store>.myshopify.com/products/{handle}.json"},
                                "SHOPIFY_STORE_DOMAIN not set: using the product.json in the brand folder")
        token = self.creds.get("shopify_token")
        if token:
            r = requests.post(f"https://{domain}/admin/api/2026-07/graphql.json", timeout=30,
                              headers={"X-Shopify-Access-Token": token}, json={"query": QUERY, "variables": {"handle": handle}})
            r.raise_for_status()
            p = r.json()["data"]["productByHandle"]
            price = p["priceRangeV2"]["minVariantPrice"]
            return {"id": p["id"], "handle": p["handle"], "title": p["title"], "description": p["descriptionHtml"],
                    "price": price["amount"], "currency": price["currencyCode"], "image_url": (p.get("featuredImage") or {}).get("url")}
        r = requests.get(f"https://{domain}/products/{handle}.json", timeout=30)
        r.raise_for_status()
        p = r.json()["product"]
        return {"id": p["id"], "handle": p["handle"], "title": p["title"], "description": p["body_html"],
                "price": p["variants"][0]["price"], "currency": "", "image_url": (p.get("image") or {}).get("src")}
