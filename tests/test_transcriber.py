from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from models.schemas import TranscriptionResult, TranscriptionSegment


class FakeSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


class FakeInfo:
    def __init__(self, language="en", duration=10.5):
        self.language = language
        self.duration = duration


@pytest.fixture
def tmp_video(tmp_path):
    p = tmp_path / "test.mp4"
    p.write_bytes(b"\x00" * 100)
    return str(p)


@pytest.fixture
def tmp_audio(tmp_path):
    p = tmp_path / "test.mp3"
    p.write_bytes(b"\x00" * 100)
    return str(p)


@patch("faster_whisper.WhisperModel")
def test_transcribe_audio(mock_model_cls, tmp_audio):
    from tools.transcriber import transcribe

    fake_segments = [
        FakeSegment(0.0, 2.5, "Hello world"),
        FakeSegment(2.5, 5.0, "This is a test"),
    ]
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter(fake_segments), FakeInfo())
    mock_model_cls.return_value = mock_model

    result = transcribe(tmp_audio)

    assert isinstance(result, TranscriptionResult)
    assert result.text == "Hello world This is a test"
    assert result.language == "en"
    assert len(result.segments) == 2
    assert result.segments[0].start == 0.0
    assert result.segments[0].text == "Hello world"
    mock_model_cls.assert_called_once_with("base", device="cpu", compute_type="int8")


@patch("tools.video_editor.extract_audio")
@patch("faster_whisper.WhisperModel")
def test_transcribe_video_extracts_audio(mock_model_cls, mock_extract, tmp_video):
    from tools.transcriber import transcribe

    mock_extract.return_value = "extracted.mp3"
    fake_segments = [FakeSegment(0.0, 1.0, "Video text")]
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter(fake_segments), FakeInfo(language="sv", duration=1.0))
    mock_model_cls.return_value = mock_model

    result = transcribe(tmp_video)

    mock_extract.assert_called_once()
    assert result.language == "sv"
    assert result.text == "Video text"


@patch("faster_whisper.WhisperModel")
def test_transcribe_with_language(mock_model_cls, tmp_audio):
    from tools.transcriber import transcribe

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([]), FakeInfo(language="sv", duration=0.0))
    mock_model_cls.return_value = mock_model

    result = transcribe(tmp_audio, language="sv")

    call_kwargs = mock_model.transcribe.call_args
    assert call_kwargs[1]["language"] == "sv"
    assert result.language == "sv"


@patch("faster_whisper.WhisperModel")
def test_transcribe_model_size(mock_model_cls, tmp_audio):
    from tools.transcriber import transcribe

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([]), FakeInfo(duration=0.0))
    mock_model_cls.return_value = mock_model

    transcribe(tmp_audio, model_size="small")
    mock_model_cls.assert_called_once_with("small", device="cpu", compute_type="int8")


def test_transcribe_file_not_found():
    from tools.transcriber import transcribe

    with pytest.raises(FileNotFoundError):
        transcribe("/nonexistent/file.mp3")


@patch("faster_whisper.WhisperModel")
def test_transcribe_to_srt(mock_model_cls, tmp_audio, tmp_path):
    from tools.transcriber import transcribe_to_srt

    fake_segments = [
        FakeSegment(0.0, 2.5, "First line"),
        FakeSegment(3.0, 5.5, "Second line"),
    ]
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter(fake_segments), FakeInfo())
    mock_model_cls.return_value = mock_model

    srt_path = str(tmp_path / "output.srt")
    result = transcribe_to_srt(tmp_audio, srt_path)

    assert result == srt_path
    content = Path(srt_path).read_text()
    assert "1\n00:00:00,000 --> 00:00:02,500\nFirst line" in content
    assert "2\n00:00:03,000 --> 00:00:05,500\nSecond line" in content


def test_seconds_to_srt_time():
    from tools.transcriber import _seconds_to_srt_time

    assert _seconds_to_srt_time(0.0) == "00:00:00,000"
    assert _seconds_to_srt_time(65.5) == "00:01:05,500"
    assert _seconds_to_srt_time(3661.123) == "01:01:01,123"
