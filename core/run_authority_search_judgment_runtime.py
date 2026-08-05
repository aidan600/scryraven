"""RunKernel-authorized RunAuthority iterative search judgment executor."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from core.cap_enforcement import RunCapExceeded
from core.run_authority_search_judgment import (
    RunSearchJudgment,
    RunSearchJudgmentInput,
    SearchJudgmentValidationResult,
    safe_json,
)
from core.run_authority_search_judgment_prompt import (
    RUN_AUTHORITY_SEARCH_JUDGMENT_SYSTEM_PROMPT,
    build_run_authority_search_judgment_prompt,
    prompt_metadata,
)
from core.run_authority_search_judgment_validation import (
    build_deterministic_search_judgment,
    validate_or_repair_search_judgment,
)
from core.run_kernel import (
    SEARCH_JUDGMENT_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)


@dataclass(frozen=True, slots=True)
class RunSearchJudgmentResult:
    judgment: RunSearchJudgment
    deterministic_judgment: RunSearchJudgment
    validation: SearchJudgmentValidationResult
    observation: Observation
    prompt_hash: str | None = None
    prompt_length: int = 0


def _parse_model_judgment(
    raw: Any,
    *,
    clean_json_response: Callable[[str], str] | None,
) -> Mapping[str, Any]:
    text = str(raw or "")
    if clean_json_response is not None:
        text = clean_json_response(text)
    parsed = json.loads(text)
    if not isinstance(parsed, Mapping):
        raise ValueError("run search judgment model output must be a JSON object")
    return parsed


def execute_run_authority_search_judgment_action(
    action: AuthorizedAction,
    *,
    judgment_input: RunSearchJudgmentInput,
    ask_model: Callable[..., Any] | None = None,
    clean_json_response: Callable[[str], str] | None = None,
    smart_model_enabled: bool = False,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    effort: str = "high",
    use_reasoning: bool = True,
    measure_context_stage: Callable[..., Any] | None = None,
) -> RunSearchJudgmentResult:
    """Judge the next search action from canonical contract and ledger facts."""

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.SEARCH_JUDGMENT_DECIDE,
        stage=SEARCH_JUDGMENT_STAGE,
        expected_observation_type=ObservationType.SEARCH_JUDGMENT_DECIDED,
    )
    deterministic_judgment = build_deterministic_search_judgment(judgment_input)
    committed = deterministic_judgment
    prompt_hash = None
    prompt_length = 0
    model_attempted = False
    validation = SearchJudgmentValidationResult(
        status="valid",
        model_attempted=False,
        deterministic_decision=deterministic_judgment.decision.value,
    )

    if smart_model_enabled and ask_model is not None:
        prompt = build_run_authority_search_judgment_prompt(judgment_input)
        meta = prompt_metadata(prompt)
        prompt_hash = str(meta["prompt_hash"])
        prompt_length = int(meta["prompt_length"])
        model_attempted = True
        if measure_context_stage is not None:
            measure_context_stage(
                "run_authority_search_judgment",
                prompt=prompt,
                system_prompt=RUN_AUTHORITY_SEARCH_JUDGMENT_SYSTEM_PROMPT,
            )
        try:
            raw = ask_model(
                prompt,
                RUN_AUTHORITY_SEARCH_JUDGMENT_SYSTEM_PROMPT,
                provider=provider,
                model=model,
                effort=effort,
                base_url=base_url,
                api_key=api_key,
                require_json=True,
                use_reasoning=use_reasoning,
            )
            parsed = _parse_model_judgment(
                raw,
                clean_json_response=clean_json_response,
            )
            committed, validation = validate_or_repair_search_judgment(
                parsed,
                deterministic_judgment=deterministic_judgment,
                model_attempted=True,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
            )
        except RunCapExceeded:
            raise
        except Exception as exc:
            committed, validation = validate_or_repair_search_judgment(
                None,
                deterministic_judgment=deterministic_judgment,
                model_attempted=True,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
                fallback_reason=(f"model_search_judgment_parse_failed:{type(exc).__name__}"),
            )

    projection = committed.to_projection()
    validation_dict = validation.to_dict()
    projection["validation"] = validation_dict
    observation_payload = {
        "owner": "RunKernel.RunAuthoritySearchJudgment",
        "judgment_projection": projection,
        "validation": validation_dict,
        "decision": projection.get("decision"),
        "classifications": projection.get("classifications", []),
        "target_source_classes": projection.get("target_source_classes", []),
        "model_attempted": bool(model_attempted),
        "prompt_hash": prompt_hash,
        "prompt_length": prompt_length,
        "prompt_text_retained": False,
        "model_response_text_retained": False,
        "provider_payload_retained": False,
    }
    return RunSearchJudgmentResult(
        judgment=committed,
        deterministic_judgment=deterministic_judgment,
        validation=validation,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.SEARCH_JUDGMENT_DECIDED,
            status=RunStageStatus.COMPLETED,
            payload=safe_json(observation_payload),
        ),
        prompt_hash=prompt_hash,
        prompt_length=prompt_length,
    )


__all__ = [
    "RunSearchJudgmentResult",
    "execute_run_authority_search_judgment_action",
]
