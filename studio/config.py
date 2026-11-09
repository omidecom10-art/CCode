"""Settings from the environment (and a local, gitignored .env). Nothing secret is ever logged."""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Tiny .env loader so the project has no extra dependency. Existing env vars win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_dotenv()


@dataclass
class Settings:
    # One model for every agent by default; each agent can be pointed elsewhere.
    research_model: str = os.getenv("STUDIO_RESEARCH_MODEL", "claude-opus-5-5")
    writer_model: str = os.getenv("STUDIO_WRITER_MODEL", "claude-opus-5-5")
    reviewer_model: str = os.getenv("STUDIO_REVIEWER_MODEL", "claude-opus-5-5")
    max_revisions: int = int(os.getenv("STUDIO_MAX_REVISIONS", "2"))
    # Opus 5.5 server-side refusal fallback (beta). Set STUDIO_FALLBACKS=0 to turn off.
    use_fallbacks: bool = os.getenv("STUDIO_FALLBACKS", "1") == "1"
    tts_provider: str = os.getenv("STUDIO_TTS", "kokoro")  # kokoro (local) | silent (CI)
    tts_voice: str = os.getenv("STUDIO_TTS_VOICE", "am_michael")
    # Integrations run live only when their credentials exist; otherwise they write a dry-run payload.
    integrations: dict = field(default_factory=lambda: {
        "slack_webhook": os.getenv("SLACK_WEBHOOK_URL", ""),
        "shopify_domain": os.getenv("SHOPIFY_STORE_DOMAIN", ""),
        "shopify_token": os.getenv("SHOPIFY_ADMIN_TOKEN", ""),
        "meta_token": os.getenv("META_ACCESS_TOKEN", ""),
        "meta_ad_account": os.getenv("META_AD_ACCOUNT_ID", ""),
        "meta_page_id": os.getenv("META_PAGE_ID", ""),
        "notion_token": os.getenv("NOTION_TOKEN", ""),
        "notion_database": os.getenv("NOTION_DATABASE_ID", ""),
        "drive_token": os.getenv("GOOGLE_DRIVE_TOKEN", ""),
        "drive_folder": os.getenv("GOOGLE_DRIVE_FOLDER_ID", ""),
    })


# USD per million tokens, for the cost line in the run summary.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
