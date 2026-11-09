"""Slack: run summaries and failure alerts through an incoming webhook (SLACK_WEBHOOK_URL)."""
import requests

from . import Integration


class Slack(Integration):
    name = "slack"

    @property
    def live(self) -> bool:
        return bool(self.creds.get("slack_webhook"))

    def post(self, text: str, blocks=None) -> dict:
        payload = {"text": text, **({"blocks": blocks} if blocks else {})}
        if not self.live:
            return self.dry_run(payload)
        r = requests.post(self.creds["slack_webhook"], json=payload, timeout=20)
        r.raise_for_status()
        return {"status": "sent"}

    def alert(self, text: str) -> dict:
        return self.post(f":rotating_light: {text}")

    def run_summary(self, report: dict) -> dict:
        lines = [f"*ecom-ai-studio run* for {report['brand']}: {report['approved']} approved, {report['blocked']} blocked",
                 f"Research: {report['research_tool_calls']} tool calls · Review rounds: {report['rounds']} · Cost: ${report['usd']}"]
        lines += [f"• {a['id']} {a['status']}: {a.get('headline', '')}" for a in report["assets"]]
        return self.post("\n".join(lines))
