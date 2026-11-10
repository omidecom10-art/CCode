from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter(prefix="/transcribe", tags=["transcribe"])

ModelSize = Literal["tiny", "base", "small", "medium", "large-v3"]
OutputFormat = Literal["json", "srt", "text"]


@router.post("")
async def transcribe_file(
    file: UploadFile,
    model_size: ModelSize = Query("base"),
    language: str | None = Query(None, description="Language code, e.g. 'sv', 'en'. Auto-detect if omitted."),
    format: OutputFormat = Query("json"),
):
    """Upload a video/audio file and get back the transcription."""
    if not file.filename:
        raise HTTPException(400, "No file uploaded")

    suffix = Path(file.filename).suffix or ".mp4"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        from tools.transcriber import transcribe, transcribe_to_srt

        if format == "srt":
            srt_path = tmp_path + ".srt"
            transcribe_to_srt(tmp_path, srt_path, model_size=model_size, language=language)
            srt_content = Path(srt_path).read_text(encoding="utf-8")
            Path(srt_path).unlink(missing_ok=True)
            return PlainTextResponse(srt_content, media_type="text/plain")

        result = transcribe(tmp_path, model_size=model_size, language=language)

        if format == "text":
            return PlainTextResponse(result.text)

        return JSONResponse(result.model_dump())

    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
