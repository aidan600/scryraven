"""One stateless OpenAI Responses transport; no provider routing or tools."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class ModelRole:
    model: str
    reasoning: str


@dataclass(frozen=True)
class ModelConfig:
    fast: ModelRole = ModelRole("gpt-4.1-mini", "")
    smart: ModelRole = ModelRole("gpt-5.4", "medium")

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


class OpenAIModel:
    def __init__(
        self,
        config: ModelConfig | None = None,
        *,
        post: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config or ModelConfig.from_environment()
        self.post = post or requests.post

    def __call__(
        self, stage: str, instructions: str, material: dict, schema: dict,
    ) -> str:
        token = os.getenv("OPENAI_API_KEY", "").strip()
        if not token:
            raise ModelError("model_configuration_missing")
        role = self.config.smart if stage == "analyst" else self.config.fast
        payload = {
            "model": role.model,
            "instructions": instructions + "\nReturn only JSON matching the response schema, with no Markdown or commentary.",
            "input": json.dumps(material, ensure_ascii=False),
            "store": False,
            "max_output_tokens": 12000,
            "text": {"format": {
                "type": "json_schema", "name": stage,
                "strict": True, "schema": schema,
            }},
        }
        if role.reasoning:
            payload["reasoning"] = {"effort": role.reasoning}
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
