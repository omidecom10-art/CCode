"""Integrations. Each one runs live when its credentials are set and otherwise writes the exact payload
it would send to output/<run>/integrations/<name>.json, so a run is always inspectable."""
import json
from pathlib import Path


class Integration:
    name = "base"

    def __init__(self, out_dir: Path, creds: dict):
        self.out = Path(out_dir) / "integrations"
        self.creds = creds

    @property
    def live(self) -> bool:
        return False

    def dry_run(self, payload: dict, note: str = "") -> dict:
        self.out.mkdir(parents=True, exist_ok=True)
        path = self.out / f"{self.name}.json"
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        existing.append({"note": note or "dry run: credentials not set, nothing was sent", "payload": payload})
        path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"status": "dry-run", "file": str(path)}
