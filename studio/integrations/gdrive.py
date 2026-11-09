"""Google Drive: upload finished files to a shared folder (GOOGLE_DRIVE_TOKEN = OAuth access token,
GOOGLE_DRIVE_FOLDER_ID). Uses the multipart upload endpoint; swap in a service account for production."""
import json
import mimetypes
from pathlib import Path

import requests

from . import Integration


class Drive(Integration):
    name = "gdrive"

    @property
    def live(self) -> bool:
        return bool(self.creds.get("drive_token") and self.creds.get("drive_folder"))

    def upload(self, path: Path) -> dict:
        meta = {"name": path.name, "parents": [self.creds.get("drive_folder") or "<FOLDER_ID>"]}
        if not self.live:
            return self.dry_run({"metadata": meta, "file": path.name, "bytes": path.stat().st_size})
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        files = {"metadata": ("metadata", json.dumps(meta), "application/json"), "file": (path.name, path.read_bytes(), mime)}
        r = requests.post("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart", files=files, timeout=120,
                          headers={"Authorization": f"Bearer {self.creds['drive_token']}"})
        r.raise_for_status()
        return {"status": "uploaded", "file_id": r.json()["id"]}
