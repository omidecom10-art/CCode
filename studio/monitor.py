"""Run monitoring: every step is timed and logged to run.jsonl, LLM usage and cost are tracked,
and any failure triggers an alert (Slack when configured, otherwise a dry-run alert file)."""
import json
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import PRICES


class RunMonitor:
    def __init__(self, out_dir: Path, alert_fn=None):
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.log_path = self.out / "run.jsonl"
        self.log_path.write_text("", encoding="utf-8")
        self.alert_fn = alert_fn
        self.steps = []
        self.llm_calls = []
        self.started = time.time()

    def event(self, kind: str, **data):
        row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kind": kind, **data}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    @contextmanager
    def step(self, name: str):
        t0 = time.time()
        self.event("step_start", step=name)
        try:
            yield
        except Exception as exc:
            dur = round(time.time() - t0, 2)
            self.steps.append({"step": name, "status": "failed", "seconds": dur, "error": str(exc)[:500]})
            self.event("step_failed", step=name, seconds=dur, error=str(exc)[:500], trace=traceback.format_exc()[-1500:])
            if self.alert_fn:
                self.alert_fn(f"ecom-ai-studio run failed at '{name}': {str(exc)[:300]}")
            raise
        dur = round(time.time() - t0, 2)
        self.steps.append({"step": name, "status": "ok", "seconds": dur})
        self.event("step_ok", step=name, seconds=dur)

    def record_llm(self, agent: str, model: str, usage: dict, request_id: str = ""):
        price_in, price_out = PRICES.get(model, (0.0, 0.0))
        cost = (usage.get("input_tokens", 0) * price_in + usage.get("output_tokens", 0) * price_out) / 1_000_000
        row = {"agent": agent, "model": model, **usage, "usd": round(cost, 4), "request_id": request_id}
        self.llm_calls.append(row)
        self.event("llm_call", **row)

    def summary(self) -> dict:
        return {
            "seconds": round(time.time() - self.started, 1),
            "steps": self.steps,
            "llm_calls": len(self.llm_calls),
            "input_tokens": sum(c.get("input_tokens", 0) for c in self.llm_calls),
            "output_tokens": sum(c.get("output_tokens", 0) for c in self.llm_calls),
            "usd": round(sum(c["usd"] for c in self.llm_calls), 4),
        }
