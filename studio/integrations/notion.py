"""Notion: one row per asset in a creative tracker database (NOTION_TOKEN, NOTION_DATABASE_ID)."""
import requests

from . import Integration


class Notion(Integration):
    name = "notion"

    @property
    def live(self) -> bool:
        return bool(self.creds.get("notion_token") and self.creds.get("notion_database"))

    def log_asset(self, asset: dict, run_id: str) -> dict:
        payload = {"parent": {"database_id": self.creds.get("notion_database") or "<DATABASE_ID>"}, "properties": {
            "Name": {"title": [{"text": {"content": f"{asset['id']}: {asset.get('headline', '')}"[:100]}}]},
            "Status": {"select": {"name": asset["status"]}},
            "Angle": {"rich_text": [{"text": {"content": asset.get("angle", "")[:200]}}]},
            "Run": {"rich_text": [{"text": {"content": run_id}}]}}}
        if not self.live:
            return self.dry_run(payload)
        r = requests.post("https://api.notion.com/v1/pages", json=payload, timeout=30, headers={
            "Authorization": f"Bearer {self.creds['notion_token']}", "Notion-Version": "2022-06-28"})
        r.raise_for_status()
        return {"status": "created", "page_id": r.json()["id"]}
