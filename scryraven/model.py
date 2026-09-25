"""One stateless OpenAI Responses transport with Answer-only local calculation."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
from typing import Any

import requests


@dataclass(frozen=True)
class ModelRole:
    model: str
    reasoning: str
    service_tier: str | None = None


@dataclass(frozen=True)
class ModelConfig:
    research: ModelRole = ModelRole("gpt-6-luna", "high", "fast")
    answer: ModelRole = ModelRole("gpt-6-sol", "medium", "fast")


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
    requested_service_tier: str | None = None
    returned_service_tier: str | None = None

    @property
    def ordinary_uncached_tokens(self) -> int | None:
        values = self.input_tokens, self.cached_input_tokens, self.cache_write_tokens
        if any(value is None for value in values):
            return None
        ordinary = values[0] - values[1] - values[2]
        return ordinary if ordinary >= 0 else None


_call_usage_observer: ContextVar[Callable[[ModelUsage], None] | None] = ContextVar(
    "scryraven_call_usage_observer", default=None,
)


@contextmanager
def capture_model_usage(observer: Callable[[ModelUsage], None]):
    """Observe one model invocation without changing a shared model's observer."""
    token = _call_usage_observer.set(observer)
    try:
        yield
    finally:
        _call_usage_observer.reset(token)


def _counter(data: Any, *path: str) -> int | None:
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data if type(data) is int and data >= 0 else None


def _json(value: Any) -> str:
    # Default object ordering is mechanical; array order and strings remain intact.
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


_RESEARCH_VOLATILE_ORDER = (
    "working_understanding", "catalog", "last_route", "evidence",
    "answer_missing_information", "pending_delivery", "budget",
)
_EVIDENCE_METADATA_ORDER = (
    "id", "source_id", "acquisition", "title", "url", "parent_id",
    "start_char", "end_char",
)
_CALCULATOR_TOOL = {
    "type": "function",
    "name": "calculate",
    "description": "Evaluate a bounded arithmetic expression using explicit numeric inputs.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
        "additionalProperties": False,
    },
}


def _evidence_json(value: Any) -> str:
    """Place each Evidence item's metadata before its exact content, without loss."""
    if not isinstance(value, list):
        return _json(value)
    items = []
    for item in value:
        if not isinstance(item, dict):
            items.append(_json(item))
            continue
        keys = [key for key in _EVIDENCE_METADATA_ORDER if key in item]
        keys += sorted(key for key in item if key not in _EVIDENCE_METADATA_ORDER and key != "content")
        if "content" in item:
            keys.append("content")
        items.append("{" + ", ".join(f"{_json(key)}: {_json(item[key])}" for key in keys) + "}")
    return "[" + ", ".join(items) + "]"


def _input_blocks(instructions: str, material: dict, stage: str, phase: str) -> tuple[list[dict], tuple[str, ...]]:
    """One exact JSON object, split only at JSON boundaries; no semantic rewrite.

    Cache instructions across calls of the same contract, growing history across
    turns, and Research's turn context across actions. Never write candidate,
    current evidence, decision or correction tails. Up to four explicit markers.
    See https://developers.openai.com/api/docs/guides/prompt-caching .
    """
    labels = ["instructions"]
    developer = {"type": "input_text", "text": instructions,
                 "prompt_cache_breakpoint": {"mode": "explicit"}}
    blocks: list[dict] = []
    pending = "{"
    history = "conversation_context"
    stable = ("conversation_context", "current_date", "phase", "question")
    corrections = ("output_correction",)
    order = [key for key in stable if key in material]
    boundary = len(order)
    if stage == "research" and phase == "research":
        order += [key for key in _RESEARCH_VOLATILE_ORDER if key in material]
        order += sorted(key for key in material
                        if key not in stable and key not in _RESEARCH_VOLATILE_ORDER
                        and key not in corrections)
    else:
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
            pending += (_evidence_json(value) if (stage, phase) in {
                ("research", "research"), ("answer", "answer"),
            } and key == "evidence" else _json(value))
        if stage == "research" and phase == "research" and index + 1 == boundary:
            flush("research_context")
    pending += "}"
    flush()
    return [{"role": "developer", "content": [developer]}, {"role": "user", "content": blocks}], tuple(labels)


def _calculation_output(
    call: dict, calculator: Callable[[str], dict],
    on_calculation: Callable[[int, str, dict], None] | None, sequence: int,
) -> dict:
    """Turn one Responses function call into a bounded, serializable tool result."""
    if (call.get("name") != "calculate" or not isinstance(call.get("call_id"), str)
            or not call["call_id"] or not isinstance(call.get("arguments"), str)):
        raise ModelError("malformed_model_response")
    raw_arguments = call["arguments"]
    try:
        arguments = json.loads(raw_arguments)
    except (ValueError, TypeError):
        arguments = None
    if (isinstance(arguments, dict) and set(arguments) == {"expression"}
            and isinstance(arguments["expression"], str)):
        expression = arguments["expression"]
        try:
            result = calculator(expression)
        except Exception:
            result = {"error": "calculator_failed"}
    else:
        expression = raw_arguments
        result = {"error": "invalid_tool_arguments"}
    try:
        if not isinstance(result, dict):
            raise TypeError("calculator result must be an object")
        output = json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError):
        result = {"error": "calculator_failed"}
        output = json.dumps(result, sort_keys=True)
    if on_calculation is not None:
        try:
            on_calculation(sequence, expression, result)
        except Exception:
            # Forensic observation cannot change the Answer result.
            pass
    return {"type": "function_call_output", "call_id": call["call_id"], "output": output}


class OpenAIModel:
    def __init__(
        self,
        config: ModelConfig | None = None,
        *,
        post: Callable[..., Any] | None = None,
        usage_observer: Callable[[ModelUsage], None] | None = None,
        cache_namespace: str = "scryraven",
        timeout_seconds: float = 120,
    ) -> None:
        self.config = config if config is not None else ModelConfig()
        self.post = post or requests.post
        self.usage_observer = usage_observer
        self.cache_namespace = cache_namespace
        self.timeout_seconds = timeout_seconds

    def __call__(
        self, stage: str, instructions: str, material: dict, schema: dict,
        *, calculator: Callable[[str], dict] | None = None,
        on_calculation: Callable[[int, str, dict], None] | None = None,
        remaining_seconds: Callable[[], float] | None = None,
    ) -> str:
        token = os.getenv("OPENAI_API_KEY", "").strip()
        if not token:
            raise ModelError("model_configuration_missing")
        role = self.config.answer if stage == "answer" else self.config.research
        use_calculator = stage == "answer" and calculator is not None
        if stage == "answer":
            instructions += ("\nWhen finished, return only JSON matching the response schema, "
                             "without an outer code fence or commentary. The answer string "
                             "may contain task-appropriate Markdown.")
        else:
            instructions += "\nReturn only JSON matching the response schema, with no Markdown or commentary."
        phase = material.get("phase", stage)
        # Only fixed transport labels reach telemetry, never arbitrary material.
        safe_stage = stage if stage in {"research", "answer"} else "other"
        safe_phase = phase if phase in {"research", "answer"} else "other"
        family_parts = ["layout-v1", self.cache_namespace, role.model, role.reasoning,
                        stage, phase, instructions, schema]
        if use_calculator:
            family_parts.append(_CALCULATOR_TOOL)
        family = sha256(_json(family_parts).encode("utf-8")).hexdigest()[:32]
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
        if role.service_tier is not None:
            if role.service_tier not in {"default", "fast"}:
                raise ValueError("invalid_service_tier")
            payload["service_tier"] = role.service_tier
        if use_calculator:
            payload["tools"] = [_CALCULATOR_TOOL]
            payload["include"] = ["reasoning.encrypted_content"]
        # Runtime gives this call at most the remaining Answer-stage and whole-run
        # time. The configured transport timeout remains a per-request ceiling;
        # for direct calls without a runtime deadline, bound the entire attempt.
        deadline = (monotonic() + self.timeout_seconds
                    if use_calculator and remaining_seconds is None else None)
        sequence = 0
        while True:
            timeout = self.timeout_seconds
            if use_calculator:
                if deadline is not None:
                    timeout = min(timeout, deadline - monotonic())
                if remaining_seconds is not None:
                    timeout = min(timeout, remaining_seconds())
                if timeout <= 0:
                    raise ModelError("model_request_timed_out")
            data = None
            try:
                response = self.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()
            except requests.Timeout:
                raise ModelError("model_request_timed_out") from None
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
                observers = (self.usage_observer, _call_usage_observer.get())
                if any(observer is not None for observer in observers):
                    usage = ModelUsage(
                        safe_stage, safe_phase, cache_family, role.model, breakpoints,
                        _counter(data, "usage", "input_tokens"),
                        _counter(data, "usage", "input_tokens_details", "cached_tokens"),
                        _counter(data, "usage", "input_tokens_details", "cache_write_tokens"),
                        _counter(data, "usage", "output_tokens"),
                        _counter(data, "usage", "output_tokens_details", "reasoning_tokens"),
                        role.service_tier,
                        (data.get("service_tier") if isinstance(data, dict)
                         and data.get("service_tier") in {"default", "fast", "priority"} else None),
                    )
                    for observer in observers:
                        if observer is not None:
                            try:
                                observer(usage)
                            except Exception:
                                # Optional diagnostics cannot change normal product execution.
                                pass

            try:
                if data.get("status") != "completed":
                    details = data.get("incomplete_details")
                    reason = details.get("reason") if isinstance(details, dict) else None
                    code = {
                        "content_filter": "model_response_incomplete_content_filter",
                        "max_output_tokens": "model_response_incomplete_max_output_tokens",
                    }.get(reason) if isinstance(reason, str) else None
                    raise ModelError(code or "model_response_incomplete")
                items = data["output"]
                if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                    raise ModelError("malformed_model_response")
                calls = [item for item in items if item.get("type") == "function_call"]
                if calls and use_calculator:
                    # Replaying every output item also preserves encrypted reasoning
                    # for stateless reasoning-model continuation with store=False.
                    outputs = []
                    for call in calls:
                        sequence += 1
                        outputs.append(_calculation_output(call, calculator, on_calculation, sequence))
                    payload = {**payload, "input": [*payload["input"], *items, *outputs]}
                    continue
                # Intermediate assistant updates are not part of a structured final
                # response. Never concatenate commentary with the final JSON object.
                messages = [item for item in items if item.get("type") == "message"]
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
