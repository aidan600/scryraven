"""One stateless OpenAI Responses transport; no provider routing or tools."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import requests


@dataclass(frozen=True)
class ModelRole:
    model: str
    reasoning: str


@dataclass(frozen=True)
class ModelConfig:
    fast: ModelRole = ModelRole("gpt-5.6-luna", "medium")
    smart: ModelRole = ModelRole("gpt-5.6-luna", "medium")

    @classmethod
    def from_environment(cls) -> ModelConfig:
        defaults = cls()
        return cls(**{
            name: ModelRole(
                os.getenv(f"SCRYRAVEN_{name.upper()}_MODEL", role.model),
                os.getenv(f"SCRYRAVEN_{name.upper()}_REASONING", role.reasoning),
            )
            for name, role in (("fast", defaults.fast), ("smart", defaults.smart))
        })


class ModelError(RuntimeError):
    """Only fixed, safe codes cross the transport boundary."""


@dataclass(frozen=True)
class ModelUsage:
    """Safe per-request counters. Missing/invalid counters remain unknown, not zero.

    Observers can aggregate these in-process and apply current prices in reporting.
    No prompt, response text, provider payload or credential is retained here.
    """

    stage: str
    phase: str
    cache_family: str
    model: str
    breakpoints: tuple[str, ...]
    input_tokens: int | None
    cached_input_tokens: int | None
    cache_write_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None

    @property
    def ordinary_uncached_tokens(self) -> int | None:
        values = self.input_tokens, self.cached_input_tokens, self.cache_write_tokens
        if any(value is None for value in values):
            return None
        ordinary = values[0] - values[1] - values[2]
        return ordinary if ordinary >= 0 else None


def _counter(data: Any, *path: str) -> int | None:
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data if type(data) is int and data >= 0 else None


def _json(value: Any) -> str:
    # Object ordering is mechanical; array order and every string remain intact.
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _input_blocks(instructions: str, material: dict, stage: str, phase: str) -> tuple[list[dict], tuple[str, ...]]:
    """One exact JSON object, split only at JSON boundaries; no semantic rewrite.

    Cache instructions across calls of the same contract, growing history across
    turns, and navigation's turn context across actions. Never write candidate,
    current evidence, decision or correction tails. Up to four explicit markers.
    See https://developers.openai.com/api/docs/guides/prompt-caching .
    """
    labels = ["instructions"]
    developer = {"type": "input_text", "text": instructions,
                 "prompt_cache_breakpoint": {"mode": "explicit"}}
    blocks: list[dict] = []
    pending = "{"
    history = "semantic_history" if material.get("semantic_history") else "conversation_context"
    stable = ("semantic_history", "conversation_context", "current_date", "phase", "question", "need", "answer_needs")
    corrections = ("selection_correction", "output_correction")
    order = [key for key in stable if key in material]
    boundary = len(order)
    order += sorted(key for key in material if key not in stable and key not in corrections)
    order += [key for key in corrections if key in material]

    def flush(label: str | None = None) -> None:
        nonlocal pending
        block = {"type": "input_text", "text": pending}
        if label:
            block["prompt_cache_breakpoint"] = {"mode": "explicit"}
            labels.append(label)
        blocks.append(block)
        pending = ""

    for index, key in enumerate(order):
        pending += (", " if index else "") + _json(key) + ": "
        value = material[key]
        if key == history and isinstance(value, list) and value:
            pending += "["
            for item_index, item in enumerate(value):
                pending += (", " if item_index else "") + _json(item)
                # Preserve every content boundary as history grows; only the last
                # two need markers to reuse the preceding turn's endpoint.
                flush("history" if item_index >= len(value) - 2 else None)
            pending += "]"
        else:
            pending += _json(value)
        if stage == "research" and phase == "navigation" and index + 1 == boundary:
            flush("navigation_context")
    pending += "}"
    flush()
    return [{"role": "developer", "content": [developer]}, {"role": "user", "content": blocks}], tuple(labels)


class OpenAIModel:
    def __init__(
        self,
        config: ModelConfig | None = None,
        *,
        post: Callable[..., Any] | None = None,
        usage_observer: Callable[[ModelUsage], None] | None = None,
        cache_namespace: str = "scryraven",
    ) -> None:
        self.config = config or ModelConfig.from_environment()
        self.post = post or requests.post
        self.usage_observer = usage_observer
        self.cache_namespace = cache_namespace

    def __call__(
        self, stage: str, instructions: str, material: dict, schema: dict,
    ) -> str:
        token = os.getenv("OPENAI_API_KEY", "").strip()
        if not token:
            raise ModelError("model_configuration_missing")
        role = self.config.smart if stage == "analyst" else self.config.fast
        instructions += "\nReturn only JSON matching the response schema, with no Markdown or commentary."
        phase = material.get("phase", stage)
        # Only fixed transport labels reach telemetry, never arbitrary material.
        safe_stage = stage if stage in {"research", "analyst", "author"} else "other"
        safe_phase = phase if phase in {"orientation", "navigation", "relevance", "analyst", "author"} else "other"
        family = sha256(_json(["layout-v1", self.cache_namespace, role.model, role.reasoning,
                              stage, phase, instructions, schema]).encode("utf-8")).hexdigest()[:32]
        cache_family = f"sr-v1:{safe_stage}:{safe_phase}:{family}"
        inputs, breakpoints = _input_blocks(instructions, material, stage, phase)
        payload = {
            "model": role.model,
            "input": inputs,
            "prompt_cache_key": cache_family,
            "prompt_cache_options": {"mode": "explicit", "ttl": "30m"},
            "store": False,
            "max_output_tokens": 12000,
            "text": {"format": {
                "type": "json_schema", "name": stage,
                "strict": True, "schema": schema,
            }},
        }
        if role.reasoning:
            payload["reasoning"] = {"effort": role.reasoning}
        data = None
        try:
            response = self.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            code = {
                400: "model_request_rejected", 401: "model_authentication_failed",
                403: "model_access_denied", 404: "model_unavailable",
                429: "model_rate_limited",
            }.get(status, "model_transport_failed")
            raise ModelError(code) from None
        except Exception:
            raise ModelError("model_transport_failed") from None
        finally:
            if self.usage_observer is not None:
                usage = ModelUsage(
                    safe_stage, safe_phase, cache_family, role.model, breakpoints,
                    _counter(data, "usage", "input_tokens"),
                    _counter(data, "usage", "input_tokens_details", "cached_tokens"),
                    _counter(data, "usage", "input_tokens_details", "cache_write_tokens"),
                    _counter(data, "usage", "output_tokens"),
                    _counter(data, "usage", "output_tokens_details", "reasoning_tokens"),
                )
                try:
                    self.usage_observer(usage)
                except Exception:
                    # Optional diagnostics cannot change normal product execution.
                    pass

        try:
            if data.get("status") != "completed":
                raise ModelError("model_response_incomplete")
            # Intermediate assistant updates are not part of a structured final
            # response. Never concatenate commentary with the final JSON object.
            messages = [item for item in data["output"] if item.get("type") == "message"]
            final = [item for item in messages if item.get("phase") == "final_answer"]
            if not final:
                final = [item for item in messages if item.get("phase") != "commentary"]
            parts = final[-1]["content"] if final else []
            if any(part.get("type") == "refusal" for part in parts):
                raise ModelError("model_refused")
            output = "".join(
                part["text"] for part in parts if part.get("type") == "output_text"
            )
            if not output.strip():
                raise ModelError("model_response_empty")
            return output
        except (KeyError, TypeError, AttributeError):
            raise ModelError("malformed_model_response") from None
