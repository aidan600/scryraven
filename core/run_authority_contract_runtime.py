"""RunKernel-authorized RunAuthority contract synthesis executor."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from core.cap_enforcement import RunCapExceeded
from core.run_authority_contract import (
    ContractSynthesisStatus,
    RunAuthorityContract,
    RunContractValidationResult,
    safe_json,
)
from core.run_authority_contract_prompt import (
    RUN_AUTHORITY_CONTRACT_SYSTEM_PROMPT,
    build_run_authority_contract_prompt,
    prompt_metadata,
)
from core.run_authority_contract_templates import build_deterministic_contract
from core.run_authority_contract_validation import validate_or_fallback_contract
from core.run_kernel import (
    RUN_CONTRACT_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)


@dataclass(frozen=True, slots=True)
class RunContractSynthesisResult:
    contract: RunAuthorityContract
    deterministic_contract: RunAuthorityContract
    validation: RunContractValidationResult
    observation: Observation
    prompt_hash: str | None = None
    prompt_length: int = 0


def _route_facts(route_projection: Mapping[str, Any] | None) -> dict[str, Any]:
    projection = dict(route_projection or {})
    return {
        "intent": projection.get("intent"),
        "report_type": projection.get("report_type"),
        "query_type": projection.get("query_type"),
        "core_topic": projection.get("core_topic"),
        "primary_entity": projection.get("primary_entity"),
        "is_academic": bool(projection.get("is_academic")),
    }


def _parse_model_contract(
    raw: Any,
    *,
    clean_json_response: Callable[[str], str] | None,
) -> Mapping[str, Any]:
    text = str(raw or "")
    if clean_json_response is not None:
        text = clean_json_response(text)
    parsed = json.loads(text)
    if not isinstance(parsed, Mapping):
        raise ValueError("run contract model output must be a JSON object")
    return parsed


def execute_run_contract_synthesis_action(
    action: AuthorizedAction,
    *,
    query: str,
    mode: str | None,
    current_date: str | None,
    route_projection: Mapping[str, Any] | None = None,
    ask_model: Callable[..., Any] | None = None,
    clean_json_response: Callable[[str], str] | None = None,
    smart_model_enabled: bool = False,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    effort: str = "low",
    use_reasoning: bool = True,
    measure_context_stage: Callable[..., Any] | None = None,
) -> RunContractSynthesisResult:
    """Synthesize a contract from templates plus optional injected model output."""

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.RUN_CONTRACT_SYNTHESIZE,
        stage=RUN_CONTRACT_STAGE,
        expected_observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
    )
    facts = _route_facts(route_projection)
    deterministic_contract = build_deterministic_contract(
        query=query,
        mode=mode,
        route_facts=facts,
    )
    prompt_hash = None
    prompt_length = 0
    model_attempted = False
    committed = deterministic_contract
    validation = RunContractValidationResult(
        status=ContractSynthesisStatus.VALID,
        deterministic_template_ids=deterministic_contract.selected_template_ids,
        model_attempted=False,
    )

    if smart_model_enabled and ask_model is not None:
        prompt = build_run_authority_contract_prompt(
            query=query,
            mode=mode,
            current_date=current_date,
            route_facts=facts,
            deterministic_contract_projection=deterministic_contract.to_projection(),
            selected_template_ids=deterministic_contract.selected_template_ids,
        )
        meta = prompt_metadata(prompt)
        prompt_hash = str(meta["prompt_hash"])
        prompt_length = int(meta["prompt_length"])
        model_attempted = True
        if measure_context_stage is not None:
            measure_context_stage(
                "run_authority_contract_synthesis",
                prompt=prompt,
                system_prompt=RUN_AUTHORITY_CONTRACT_SYSTEM_PROMPT,
            )
        try:
            raw = ask_model(
                prompt,
                RUN_AUTHORITY_CONTRACT_SYSTEM_PROMPT,
                provider=provider,
                model=model,
                effort=effort,
                base_url=base_url,
                api_key=api_key,
                require_json=True,
                use_reasoning=use_reasoning,
            )
            parsed = _parse_model_contract(raw, clean_json_response=clean_json_response)
            committed, validation = validate_or_fallback_contract(
                parsed,
                deterministic_contract=deterministic_contract,
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
            committed, validation = validate_or_fallback_contract(
                None,
                deterministic_contract=deterministic_contract,
                model_attempted=True,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
                fallback_reason=f"model_contract_parse_failed:{type(exc).__name__}",
            )

    projection = committed.to_projection()
    observation_payload = {
        "owner": "RunKernel.RunAuthorityContract",
        "contract_projection": projection,
        "validation": validation.to_dict(),
        "synthesis_mode": projection.get("synthesis_mode"),
        "selected_template_ids": projection.get("selected_template_ids", []),
        "source_requirement_count": projection.get("source_requirement_count", 0),
        "required_source_requirement_count": projection.get(
            "required_source_requirement_count",
            0,
        ),
        "model_attempted": bool(model_attempted),
        "prompt_hash": prompt_hash,
        "prompt_length": prompt_length,
        "prompt_text_retained": False,
        "model_response_text_retained": False,
        "provider_payload_retained": False,
    }
    return RunContractSynthesisResult(
        contract=committed,
        deterministic_contract=deterministic_contract,
        validation=validation,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
            status=RunStageStatus.COMPLETED,
            payload=safe_json(observation_payload),
        ),
        prompt_hash=prompt_hash,
        prompt_length=prompt_length,
    )


__all__ = [
    "RunContractSynthesisResult",
    "execute_run_contract_synthesis_action",
]
