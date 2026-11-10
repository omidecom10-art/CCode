from __future__ import annotations

import tempfile
from pathlib import Path

from models.schemas import TranscriptionResult, TranscriptionSegment
from utils.file_helpers import detect_media_type


def transcribe(
    input_path: str,
    model_size: str = "base",
    language: str | None = None,
) -> TranscriptionResult:
    """Transcribe audio/video using faster-whisper (local, free)."""
    from faster_whisper import WhisperModel

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    audio_path = input_path
    tmp_audio = None

    if detect_media_type(input_path) == "video":
        from tools.video_editor import extract_audio
        tmp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_audio.close()
        extract_audio(input_path, tmp_audio.name)
        audio_path = tmp_audio.name

    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments_iter, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
        )

        segments = []
        text_parts = []
        for seg in segments_iter:
            segments.append(TranscriptionSegment(
                start=round(seg.start, 2),
                end=round(seg.end, 2),
                text=seg.text.strip(),
            ))
            text_parts.append(seg.text.strip())

        return TranscriptionResult(
            text=" ".join(text_parts),
            language=info.language,
            duration=round(info.duration, 2),
            segments=segments,
        )
    finally:
        if tmp_audio:
            Path(tmp_audio.name).unlink(missing_ok=True)


def transcribe_to_srt(input_path: str, output_path: str, **kwargs) -> str:
    """Transcribe and save as SRT subtitle file."""
    result = transcribe(input_path, **kwargs)

    lines = []
    for i, seg in enumerate(result.segments, 1):
        start_srt = _seconds_to_srt_time(seg.start)
        end_srt = _seconds_to_srt_time(seg.end)
        lines.append(f"{i}")
        lines.append(f"{start_srt} --> {end_srt}")
        lines.append(seg.text)
        lines.append("")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _seconds_to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
