from __future__ import annotations

from typing import Type, TypeVar

import anthropic
from pydantic import BaseModel

from config.settings import get_settings

T = TypeVar("T", bound=BaseModel)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        settings = get_settings()
        _client = anthropic.Anthropic(api_key=settings.api_key, max_retries=2)
    return _client


def call_cheap(
    system: str,
    messages: list[dict],
    output_schema: Type[T] | None = None,
    max_tokens: int = 4096,
) -> T | str:
    """Call Claude Haiku 5.5 — use for analysis, planning, routing. ~$0.0005/call."""
    settings = get_settings()
    client = _get_client()

    kwargs: dict = dict(
        model=settings.default_model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )

    if output_schema is not None:
        resp = client.messages.parse(**kwargs, output_format=output_schema)
        return resp.parsed_output

    resp = client.messages.create(**kwargs)
    return resp.content[0].text


def call_complex(
    system: str,
    messages: list[dict],
    output_schema: Type[T] | None = None,
    max_tokens: int = 16000,
) -> T | str:
    """Call Claude Sonnet 5.5 — use ONLY for code generation. ~$0.03/call."""
    settings = get_settings()
    client = _get_client()

    kwargs: dict = dict(
        model=settings.complex_model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )

    if output_schema is not None:
        resp = client.messages.parse(**kwargs, output_format=output_schema)
        return resp.parsed_output

    resp = client.messages.create(**kwargs)
    return resp.content[0].text


def call_with_tools(
    system: str,
    messages: list[dict],
    tools: list[dict],
    model: str | None = None,
    max_tokens: int = 4096,
) -> anthropic.types.Message:
    """Call Claude with tool definitions for the agentic loop. Defaults to Haiku."""
    settings = get_settings()
    client = _get_client()
    return client.messages.create(
        model=model or settings.default_model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        tools=tools,
    )
