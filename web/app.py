"""Main FastAPI app. Each feature lives in its own router under web/routers/."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.routers import transcribe

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Ad Agent",
    description="AI-verktyg for videoannonser",
    version="0.1.0",
)

app.include_router(transcribe.router)


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
