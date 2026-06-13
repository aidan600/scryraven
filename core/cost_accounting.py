from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any

# Prices are USD per 1M tokens unless otherwise noted. Unknown/local models are
# still counted, but default to zero USD rather than inventing prices.
MODEL_PRICING_USD_PER_1M: dict[str, dict[str, float]] = {
    "gpt-5.4": {"input": 10.0, "output": 30.0},
    "gpt-5.4-mini": {"input": 0.25, "output": 2.0},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}

PROVIDER_PRICING_USD_PER_CALL: dict[str, float] = {
    "tavily": 0.0,
    "linkup": 0.0,
    "exa": 0.0,
    "brave": 0.0,
}


def estimate_tokens(text_or_texts: Any) -> int:
    """Cheap deterministic token estimate used when provider usage is absent."""
    if text_or_texts is None:
        return 0
    if isinstance(text_or_texts, (list, tuple)):
        return sum(estimate_tokens(x) for x in text_or_texts)
    text = str(text_or_texts)
    if not text:
        return 0
    return max(1, int(len(text) / 4))


def extract_usage_tokens(response: Any) -> tuple[int | None, int | None]:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return None, None

    def _get(name: str) -> int | None:
        if isinstance(usage, dict):
            value = usage.get(name)
        else:
            value = getattr(usage, name, None)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    input_tokens = _get("prompt_tokens") or _get("input_tokens")
    output_tokens = _get("completion_tokens") or _get("output_tokens")
    return input_tokens, output_tokens


@dataclass
class CostAccumulator:
    cost_by_phase: dict[str, float] = field(default_factory=dict)
    cost_by_model: dict[str, float] = field(default_factory=dict)
    calls_by_phase: dict[str, int] = field(default_factory=dict)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    _lock: RLock = field(default_factory=RLock, repr=False, compare=False)

    def _add_cost(self, *, phase: str, model_or_provider: str, amount: float) -> None:
        with self._lock:
            phase_key = phase or "unknown"
            model_key = model_or_provider or "unknown"
            amount = float(amount or 0.0)
            self.cost_by_phase[phase_key] = self.cost_by_phase.get(phase_key, 0.0) + amount
            self.cost_by_model[model_key] = self.cost_by_model.get(model_key, 0.0) + amount
            self.calls_by_phase[phase_key] = self.calls_by_phase.get(phase_key, 0) + 1
            self.total_calls += 1

    def record_model_call(
        self,
        *,
        phase: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        with self._lock:
            pricing = MODEL_PRICING_USD_PER_1M.get((model or "").lower(), {})
            cost = (
                (max(0, int(input_tokens or 0)) / 1_000_000.0) * float(pricing.get("input", 0.0))
                + (max(0, int(output_tokens or 0)) / 1_000_000.0) * float(pricing.get("output", 0.0))
            )
            self.total_input_tokens += max(0, int(input_tokens or 0))
            self.total_output_tokens += max(0, int(output_tokens or 0))
            phase_key = phase or "unknown"
            model_key = model or "unknown_model"
            amount = float(cost or 0.0)
            self.cost_by_phase[phase_key] = self.cost_by_phase.get(phase_key, 0.0) + amount
            self.cost_by_model[model_key] = self.cost_by_model.get(model_key, 0.0) + amount
            self.calls_by_phase[phase_key] = self.calls_by_phase.get(phase_key, 0) + 1
            self.total_calls += 1

    def record_embedding_call(self, *, phase: str, model: str, input_tokens: int = 0) -> None:
        self.record_model_call(
            phase=phase or "embedding",
            model=model,
            input_tokens=input_tokens,
            output_tokens=0,
        )

    def record_search_call(self, *, phase: str, provider: str, calls: int = 1) -> None:
        for _ in range(max(1, int(calls or 1))):
            self._add_cost(
                phase=phase or "retrieval",
                model_or_provider=provider or "unknown_provider",
                amount=PROVIDER_PRICING_USD_PER_CALL.get((provider or "").lower(), 0.0),
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_cost_usd": round(sum(self.cost_by_phase.values()), 6),
                "cost_by_phase": {k: round(v, 6) for k, v in sorted(self.cost_by_phase.items())},
                "cost_by_model": {k: round(v, 6) for k, v in sorted(self.cost_by_model.items())},
                "calls_by_phase": {k: int(v) for k, v in sorted(self.calls_by_phase.items())},
                "total_input_tokens": int(self.total_input_tokens),
                "total_output_tokens": int(self.total_output_tokens),
                "total_calls": int(self.total_calls),
            }
