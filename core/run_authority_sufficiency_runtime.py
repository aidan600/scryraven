"""RunKernel-authorized RunAuthority final sufficiency executor."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from core.cap_enforcement import RunCapExceeded
from core.run_authority_sufficiency import (
    RunSufficiencyJudgment,
    RunSufficiencyJudgmentInput,
    SufficiencyValidationResult,
    safe_json,
)
from core.run_authority_sufficiency_prompt import (
    RUN_AUTHORITY_SUFFICIENCY_SYSTEM_PROMPT,
    build_run_authority_sufficiency_prompt,
    prompt_metadata,
)
from core.run_authority_sufficiency_validation import (
    build_deterministic_sufficiency_judgment,
    preserve_multicomponent_sufficiency_authority,
    validate_or_repair_sufficiency_judgment,
)
from core.run_kernel import (
    ANSWER_CONTRACT_AUTHORITY_MAP_STAGE,
    SUFFICIENCY_JUDGMENT_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)


@dataclass(frozen=True, slots=True)
class RunSufficiencyJudgmentResult:
    judgment: RunSufficiencyJudgment
    deterministic_judgment: RunSufficiencyJudgment
    validation: SufficiencyValidationResult
    observation: Observation
    prompt_hash: str | None = None
    prompt_length: int = 0


@dataclass(frozen=True, slots=True)
class RunSufficiencyJudgmentHandoff:
    """RunKernel-reduced sufficiency judgment projection."""

    result: RunSufficiencyJudgmentResult
    projection: dict[str, Any]


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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
        raise ValueError("run sufficiency model output must be a JSON object")
    return parsed


def execute_run_authority_sufficiency_judgment_action(
    action: AuthorizedAction,
    *,
    judgment_input: RunSufficiencyJudgmentInput,
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
) -> RunSufficiencyJudgmentResult:
    """Judge final answer sufficiency from canonical state and compatibility facts."""

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.SUFFICIENCY_JUDGMENT_DECIDE,
        stage=SUFFICIENCY_JUDGMENT_STAGE,
        expected_observation_type=ObservationType.SUFFICIENCY_JUDGMENT_DECIDED,
    )
    deterministic_judgment = build_deterministic_sufficiency_judgment(judgment_input)
    committed = deterministic_judgment
    prompt_hash = None
    prompt_length = 0
    model_attempted = False
    validation = SufficiencyValidationResult(
        status="valid",
        model_attempted=False,
        deterministic_decision=deterministic_judgment.decision.value,
    )

    if smart_model_enabled and ask_model is not None:
        prompt = build_run_authority_sufficiency_prompt(judgment_input)
        meta = prompt_metadata(prompt)
        prompt_hash = str(meta["prompt_hash"])
        prompt_length = int(meta["prompt_length"])
        model_attempted = True
        if measure_context_stage is not None:
            measure_context_stage(
                "run_authority_sufficiency_judgment",
                prompt=prompt,
                system_prompt=RUN_AUTHORITY_SUFFICIENCY_SYSTEM_PROMPT,
            )
        try:
            raw = ask_model(
                prompt,
                RUN_AUTHORITY_SUFFICIENCY_SYSTEM_PROMPT,
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
            committed, validation = validate_or_repair_sufficiency_judgment(
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
            committed, validation = validate_or_repair_sufficiency_judgment(
                None,
                deterministic_judgment=deterministic_judgment,
                model_attempted=True,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
                fallback_reason=(
                    f"model_sufficiency_judgment_parse_failed:{type(exc).__name__}"
                ),
            )

    committed = preserve_multicomponent_sufficiency_authority(
        committed,
        deterministic_judgment=deterministic_judgment,
    )
    projection = committed.to_projection()
    validation_dict = validation.to_dict()
    projection["validation"] = validation_dict
    observation_payload = {
        "owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "judgment_projection": projection,
        "validation": validation_dict,
        "decision": projection.get("decision"),
        "final_answer_posture": projection.get("final_answer_posture"),
        "final_answer_allowed": projection.get("final_answer_allowed"),
        "missing_required_obligation_count": len(
            projection.get("missing_required_obligations") or []
        ),
        "mandatory_caveat_count": len(projection.get("mandatory_caveats") or []),
        "prohibited_upgrade_count": len(
            projection.get("prohibited_upgrades") or []
        ),
        "model_attempted": bool(model_attempted),
        "prompt_hash": prompt_hash,
        "prompt_length": prompt_length,
        "prompt_text_retained": False,
        "model_response_text_retained": False,
        "provider_payload_retained": False,
    }
    safe_observation_payload = safe_json(observation_payload)
    if not isinstance(safe_observation_payload, Mapping):
        safe_observation_payload = {}
    else:
        safe_observation_payload = dict(safe_observation_payload)
    safe_observation_payload["judgment_projection"] = projection
    safe_observation_payload["validation"] = validation_dict
    return RunSufficiencyJudgmentResult(
        judgment=committed,
        deterministic_judgment=deterministic_judgment,
        validation=validation,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.SUFFICIENCY_JUDGMENT_DECIDED,
            status=RunStageStatus.COMPLETED,
            payload=safe_observation_payload,
        ),
        prompt_hash=prompt_hash,
        prompt_length=prompt_length,
    )


def execute_sufficiency_judgment_handoff_from_scope(
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    *,
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
) -> RunSufficiencyJudgmentHandoff:
    """Build, authorize, execute, and reduce final-answer sufficiency judgment."""

    from core.run_authority_sufficiency_adapter import (
        build_sufficiency_judgment_input_from_runtime,
    )

    evidence_ledger_projection = runtime_scope["evidence_ledger_projection"]
    search_judgment_projection = runtime_scope["search_judgment_projection"]
    run_contract_projection = runtime_scope["run_contract_projection"]
    final_top_evidence = runtime_scope["final_top_evidence"]
    scrutineer_flags = runtime_scope["scrutineer_flags"]
    corpus_weak = bool(runtime_scope["corpus_weak"])
    judgment_input = build_sufficiency_judgment_input_from_runtime(
        contract_projection=run_contract_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        search_judgment_projection=search_judgment_projection,
        search_judgment_history=run_kernel.state.search_judgment_history,
        answer_contract_projection=runtime_scope["answer_contract_projection"],
        final_evidence_count=len(final_top_evidence),
        author_evidence_count=len(runtime_scope["author_evidence"]),
        citation_eligible_candidate_count=len(runtime_scope["unique_source_urls"]),
        conflicts_present=bool(scrutineer_flags),
        scrutineer_flag_count=len(scrutineer_flags),
        corpus_weak=corpus_weak,
        weak_corpus_reason=(
            runtime_scope["weak_corpus_recovery_skip_reason"]
            or runtime_scope["corpus_state"]
            if corpus_weak
            else None
        ),
        synth_was_insufficient=bool(runtime_scope["synth_was_insufficient"]),
        failure_card_show=runtime_scope["_pre_gate_failure_card_show"],
        failure_card_reason=runtime_scope["_pre_gate_failure_card_reason"],
        iterations_run=runtime_scope["iterations_run"],
        max_iterations=runtime_scope["max_iterations"],
        recovery_attempt_count=(
            runtime_scope["_run_controller_mirror"].state.active_source_class_recovery_attempt_count
        ),
        initial_answer_contract=run_kernel.state.initial_answer_contract,
        current_answer_contract=run_kernel.state.current_answer_contract,
        component_coverage_history=run_kernel.state.component_coverage_history,
        contract_amendment_admission_history=(
            run_kernel.state.contract_amendment_admission_history
        ),
        answer_contract_authority_map_projection=run_kernel.state.projections.get(
            ANSWER_CONTRACT_AUTHORITY_MAP_STAGE,
        ),
        multicomponent_graph_state=run_kernel.state.projections.get(
            "multicomponent_component_work_graph_v1"
        ),
        multicomponent_scheduler_state=run_kernel.state.projections.get(
            "multicomponent_graph_scheduler"
        ),
        searchos_existing_gap_recovery_terminal_state=(
            run_kernel.state.searchos_state.get("recovery_terminal_aggregate")
            or run_kernel.state.projections.get("searchos_existing_gap_recovery_terminal")
        ),
        searchos_required_needs_block_state=(
            run_kernel.state.projections.get("searchos_required_needs_block")
        ),
        searchos_state=run_kernel.state.searchos_state,
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
    )
    action = run_kernel.authorize_sufficiency_judgment(
        inputs={
            "contract_id": run_contract_projection.get("contract_id"),
            "candidate_count": evidence_ledger_projection.get("candidate_count"),
            "requirement_count": evidence_ledger_projection.get(
                "requirement_count"
            ),
            "search_judgment_decision": search_judgment_projection.get("decision"),
            "final_evidence_count": len(final_top_evidence),
            "smart_model_enabled": bool(smart_model_enabled),
            "multicomponent_graph_digest": _safe_mapping(
                run_kernel.state.projections.get(
                    "multicomponent_component_work_graph_v1"
                )
            ).get("graph_digest"),
        }
    )
    result = execute_run_authority_sufficiency_judgment_action(
        action,
        judgment_input=judgment_input,
        ask_model=ask_model if smart_model_enabled else None,
        clean_json_response=clean_json_response,
        smart_model_enabled=smart_model_enabled,
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        effort=effort,
        use_reasoning=use_reasoning,
        measure_context_stage=measure_context_stage,
    )
    run_kernel.reduce(result.observation)
    return RunSufficiencyJudgmentHandoff(
        result=result,
        projection=dict(run_kernel.state.sufficiency_judgment_projection),
    )


__all__ = [
    "RunSufficiencyJudgmentHandoff",
    "RunSufficiencyJudgmentResult",
    "execute_run_authority_sufficiency_judgment_action",
    "execute_sufficiency_judgment_handoff_from_scope",
]
