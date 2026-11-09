"""One way to call Claude: an agent turn loop that ends in a validated Pydantic object.

- Structured output: `client.messages.parse(..., output_format=Schema)` returns `parsed_output`.
- Tool calling: when Claude asks for tools, we run them and send all results back in one message.
- Safety: refusals and truncation raise clear errors; the SDK retries 429/5xx itself (max_retries=3).
- Cassettes: every agent result is recorded, so tests/CI can replay a real run with no API key.
"""
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Type

import anthropic
from pydantic import BaseModel

from .config import Settings
from .monitor import RunMonitor

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AgentError(RuntimeError):
    pass


class LLM:
    def __init__(self, settings: Settings, monitor: RunMonitor, cassette: Path, mode: str = "live"):
        self.settings, self.monitor, self.mode = settings, monitor, mode
        self.cassette_path = Path(cassette)
        self.cassette: Dict[str, dict] = (
            json.loads(self.cassette_path.read_text(encoding="utf-8")) if self.cassette_path.exists() else {})
        self.client = anthropic.Anthropic(max_retries=3, timeout=300) if mode == "live" else None
        self._fallbacks = settings.use_fallbacks

    def run_agent(self, key: str, model: str, system: str, prompt: str, schema: Type[BaseModel],
                  tools: Optional[List[dict]] = None, tool_handler: Optional[Callable[[str, dict], str]] = None,
                  max_turns: int = 10):
        """Return (parsed schema instance, tool trace). `key` names the call in the cassette."""
        if self.mode == "replay":
            if key not in self.cassette:
                raise AgentError(f"No recorded output for '{key}' in {self.cassette_path.name}; run live once.")
            rec = self.cassette[key]
            self.monitor.event("llm_replay", agent=key)
            return schema.model_validate(rec["output"]), rec.get("trace", [])

        messages = [{"role": "user", "content": prompt}]
        trace: List[dict] = []
        for _ in range(max_turns):
            response = self._parse(model, system, messages, schema, tools)
            u = response.usage
            self.monitor.record_llm(key, model, {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens},
                                    getattr(response, "_request_id", "") or "")
            if response.stop_reason == "refusal":
                details = getattr(response, "stop_details", None)
                raise AgentError(f"{key}: model declined ({getattr(details, 'category', None)})")
            if response.stop_reason == "max_tokens":
                raise AgentError(f"{key}: output hit max_tokens; raise it or shorten the task")
            if response.stop_reason == "tool_use":
                calls = [b for b in response.content if b.type == "tool_use"]
                messages.append({"role": "assistant", "content": response.content})
                results = []
                for call in calls:
                    try:
                        out, is_error = tool_handler(call.name, call.input), False
                    except Exception as exc:  # a broken tool becomes an error result, not a crashed run
                        out, is_error = f"Error: {exc}", True
                    trace.append({"tool": call.name, "input": call.input, "result_preview": str(out)[:240]})
                    results.append({"type": "tool_result", "tool_use_id": call.id, "content": str(out), "is_error": is_error})
                messages.append({"role": "user", "content": results})
                continue
            parsed = getattr(response, "parsed_output", None)
            if parsed is None:
                raise AgentError(f"{key}: no structured output (stop_reason={response.stop_reason})")
            self.cassette[key] = {"model": model, "output": parsed.model_dump(), "trace": trace}
            self.cassette_path.write_text(json.dumps(self.cassette, indent=2, ensure_ascii=False), encoding="utf-8")
            return parsed, trace
        raise AgentError(f"{key}: still calling tools after {max_turns} turns")

    def _parse(self, model, system, messages, schema, tools):
        kwargs = dict(model=model, max_tokens=16000, system=system, messages=messages, output_format=schema)
        if tools:
            kwargs["tools"] = tools
        if self._fallbacks:
            kwargs["extra_headers"] = {"anthropic-beta": FALLBACK_BETA}
            kwargs["extra_body"] = {"fallbacks": "default"}
        try:
            return self.client.messages.parse(**kwargs)
        except anthropic.BadRequestError as exc:
            if self._fallbacks and "fallback" in str(exc).lower():  # account or model without the beta: retry plainly
                self._fallbacks = False
                kwargs.pop("extra_headers"), kwargs.pop("extra_body")
                return self.client.messages.parse(**kwargs)
            raise
