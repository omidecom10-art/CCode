"""Meta Ads: upload each approved static ad as a creative and create the ad PAUSED, so a person launches it.
Needs META_ACCESS_TOKEN, META_AD_ACCOUNT_ID, META_PAGE_ID (and an ad set id per call)."""
import base64
from pathlib import Path

import requests

from . import Integration

GRAPH = "https://graph.facebook.com/v23.0"


class MetaAds(Integration):
    name = "meta_ads"

    @property
    def live(self) -> bool:
        c = self.creds
        return bool(c.get("meta_token") and c.get("meta_ad_account") and c.get("meta_page_id"))

    def create_paused_ad(self, ad, image_path: Path, link: str, adset_id: str = "<ADSET_ID>") -> dict:
        creative = {
            "name": f"studio {ad.id} {ad.angle}",
            "object_story_spec": {"page_id": self.creds.get("meta_page_id") or "<PAGE_ID>", "link_data": {
                "message": f"{ad.subhead}\n\n{ad.offer_line}", "name": ad.headline, "link": link,
                "image_hash": "<from adimages upload>", "call_to_action": {"type": "SHOP_NOW", "value": {"link": link}}}},
        }
        ad_obj = {"name": f"studio {ad.id}", "adset_id": adset_id, "creative": {"creative_id": "<from adcreatives>"}, "status": "PAUSED"}
        if not self.live:
            return self.dry_run({"image": str(image_path.name), "adcreative": creative, "ad": ad_obj})
        act, token = f"act_{self.creds['meta_ad_account']}", self.creds["meta_token"]
        img = requests.post(f"{GRAPH}/{act}/adimages", timeout=60, data={
            "bytes": base64.b64encode(image_path.read_bytes()).decode(), "access_token": token}).json()
        image_hash = next(iter(img["images"].values()))["hash"]
        creative["object_story_spec"]["link_data"]["image_hash"] = image_hash
        cr = requests.post(f"{GRAPH}/{act}/adcreatives", timeout=60, json={**creative, "access_token": token}).json()
        ad_obj["creative"] = {"creative_id": cr["id"]}
        made = requests.post(f"{GRAPH}/{act}/ads", timeout=60, json={**ad_obj, "access_token": token}).json()
        return {"status": "created_paused", "ad_id": made.get("id")}
