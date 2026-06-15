from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from core.followup_authorization_runtime import (
    FOLLOWUP_EXECUTION_GATE_REASON,
    consume_followup_deliberation_checkpoint,
    execute_followup_authorization_consumption_action,
    request_followup_provider_execution,
)
from core.followup_deliberation import (
    FollowupDecision,
    GapType,
    ReasoningHopType,
    build_followup_deliberation_checkpoint,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.run_kernel import (
    FOLLOWUP_AUTHORIZATION_STAGE,
    RUN_KERNEL_TRACE_KEY,
    RunKernel,
    RunKernelTransitionError,
)

ROOT = Path(__file__).resolve().parents[1]


def _budget(**overrides: int) -> dict[str, int]:
    base = {
        "cost_points_remaining": 8,
        "provider_calls_remaining": 3,
        "fetches_remaining": 3,
        "read_units_remaining": 3,
        "followup_rounds_remaining": 2,
        "meso_authorizations_remaining": 3,
        "macro_hops_remaining": 1,
    }
    base.update(overrides)
    return base


def _component(component_id: str, *, served: bool = True) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "central": True,
        "served_minimum": served,
        "minimum_provider_calls": 1,
        "minimum_fetches": 1,
        "minimum_read_units": 1,
    }


def _gap(
    gap_type: str,
    *,
    gap_id: str = "gap.official",
    component_id: str = "component-rule",
    obligation_id: str = "obligation-official-current",
    requirement_id: str = "requirement-official-current",
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "gap_id": gap_id,
        "gap_type": gap_type,
        "component_id": component_id,
        "source_obligation_id": obligation_id,
        "requirement_ids": [requirement_id],
        "severity": "central_required",
        "evidence_indicators": ["required_obligation_unsatisfied"],
    }
    payload.update(overrides)
    return payload


def _checkpoint(**overrides: Any) -> Any:
    fixture = {
        "run_id": "ag96i2a-fixture",
        "checkpoint_id": "after-first-pass",
        "mode": "balanced",
        "components": [_component("component-rule")],
        "budget_ledger": _budget(),
        "gaps": [_gap(GapType.OFFICIAL_CURRENT_GAP.value)],
        "sufficiency_handoff": {
            "satisfied_obligations": [],
            "missing_obligations": ["obligation-official-current"],
            "recommended_final_posture": "answer_with_caveats",
        },
    }
    fixture.update(overrides)
    return build_followup_deliberation_checkpoint(fixture)


def test_balanced_valid_official_current_candidate_becomes_sealed_non_executable() -> None:
    record = consume_followup_deliberation_checkpoint(_checkpoint()).to_dict()

    assert record["validation"]["status"] == "valid"
    assert record["status"] == "sealed_non_executable"
    assert record["selected_authorization_candidate_ids"] == ["auth.candidate.001"]
    seal = record["sealed_candidates"][0]
    assert seal["status"] == "sealed_non_executable"
    assert seal["provider_job_kind"] == "official_current_candidate_acquisition"
    assert seal["execution_gate"] == {
        "execution_permission": False,
        "executable_in_current_phase": False,
        "provider_execution_licensed": False,
        "reason": FOLLOWUP_EXECUTION_GATE_REASON,
    }
    assert record["behavior_boundary_flags"]["search_executed"] is False
    assert record["behavior_boundary_flags"]["provider_job_scheduled"] is False


def test_balanced_seal_preserves_candidate_custody_budget_and_fallback_posture() -> None:
    record = consume_followup_deliberation_checkpoint(_checkpoint()).to_dict()
    seal = record["sealed_candidates"][0]

    assert seal["component_id"] == "component_rule"
    assert seal["source_obligation_id"] == "obligation_official_current"
    assert seal["expected_evidence_ledger_custody_update"][
        "custody_update_expected"
    ] == [
        "candidate_identity",
        "source_class",
        "currentness_signal",
        "readable_answer_bearing_extract",
        "requirement_link",
    ]
    assert seal["budget_debit"]["provider_calls"] == 1
    assert seal["budget_semantics"]["debit_would_apply_in_future_execution_phase"]
    assert seal["budget_semantics"]["actual_provider_search_fetch_read_cost_incurred"] is False
    assert seal["fallback_stop_posture"] == "answer_with_caveats"
    assert seal["fallback_caveat_refuse_posture"] == "insufficient_evidence"


def test_balanced_needs_deep_consumes_escalation_and_seals_no_candidate() -> None:
    checkpoint = _checkpoint(
        gaps=[
            _gap(
                GapType.CONFLICT_RECONCILIATION_GAP.value,
                gap_id="gap.conflict",
                obligation_id="obligation-currentness-conflict",
                requirement_id="requirement-currentness",
                evidence_indicators=["admitted_sources_conflict_on_currentness"],
            )
        ],
    )

    record = consume_followup_deliberation_checkpoint(checkpoint).to_dict()

    assert record["status"] == "denied"
    assert record["sealed_candidates"] == []
    assert record["needs_deep"] is True
    assert record["consumed_stop_decisions"][0]["final_answer_posture"] == "needs_deep"


def test_fast_micro_hop_checkpoint_consumes_validation_and_seals_no_candidate() -> None:
    checkpoint = _checkpoint(
        mode="fast",
        gaps=[
            _gap(
                GapType.CITATION_FINAL_ANSWER_POSTURE_GAP.value,
                gap_id="gap.citation",
                obligation_id="obligation-citation",
                requirement_id="requirement-citation",
                evidence_indicators=["candidate_missing_answer_bearing_extract"],
            )
        ],
    )

    record = consume_followup_deliberation_checkpoint(checkpoint).to_dict()

    assert record["validation"]["status"] == "valid"
    assert record["sealed_candidates"] == []
    assert record["micro_hop_validation"][0]["hop_type"] == "micro_verification"
    assert record["consumed_stop_decisions"][0]["decision"] == "stop"


def test_fast_official_current_gap_remains_micro_validation_caveat_only() -> None:
    record = consume_followup_deliberation_checkpoint(_checkpoint(mode="fast")).to_dict()

    assert record["sealed_candidates"] == []
    assert record["consumed_budget_decisions"][0]["decision"] == "caveat"
    assert record["consumed_budget_decisions"][0][
        "actual_provider_search_fetch_read_cost_incurred"
    ] is False
    assert record["micro_hop_validation"][0]["may_request_followup"] is False


def test_fast_conflict_gap_preserves_selected_mode_insufficient() -> None:
    checkpoint = _checkpoint(
        mode="fast",
        gaps=[
            _gap(
                GapType.CONTRACT_SHAPE_GAP.value,
                gap_id="gap.contract",
                obligation_id="obligation-contract",
                requirement_id="requirement-contract",
                evidence_indicators=["requires_reconciliation_or_contract_shape"],
            )
        ],
    )

    record = consume_followup_deliberation_checkpoint(checkpoint).to_dict()

    assert record["sealed_candidates"] == []
    assert record["selected_mode_insufficient"] is True
    assert record["needs_balanced_or_deep"] is True
    assert record["consumed_stop_decisions"][0]["final_answer_posture"] == (
        "needs_balanced_or_deep"
    )


def test_fast_malicious_candidate_is_rejected_fail_closed() -> None:
    checkpoint = _checkpoint(mode="fast")
    payload = checkpoint.to_dict()
    payload["records"]["followup_authorization_candidates"] = [
        {
            "authorization_id": "auth.fast.bad",
            "recommendation_id": "rec.001",
            "decision": "authorize_candidate",
            "mode": "fast",
            "hop_type": "meso_targeted_repair",
            "provider_job_kind": "official_current_candidate_acquisition",
            "component_id": "component-rule",
            "source_obligation_id": "obligation-official-current",
            "requirement_ids": ["requirement-official-current"],
            "budget_debit": {},
            "expected_evidence_ledger_custody_update": {"custody_update_expected": []},
            "fallback_stop_posture": "answer_with_caveats",
            "fallback_caveat_refuse_posture": "insufficient_evidence",
        }
    ]

    record = consume_followup_deliberation_checkpoint(payload).to_dict()

    assert record["status"] == "denied_invalid_checkpoint"
    assert record["selected_authorization_candidate_ids"] == []
    assert record["denied_candidate_ids"] == ["auth.fast.bad"]
    assert any("Fast may not contain authorization candidates" in e for e in record["validation"]["errors"])


def test_deep_macro_reconciliation_candidate_is_sealed_and_preserves_audit() -> None:
    checkpoint = _checkpoint(
        mode="deep",
        gaps=[
            _gap(
                GapType.CONFLICT_RECONCILIATION_GAP.value,
                gap_id="gap.conflict",
                obligation_id="obligation-conflict",
                requirement_id="requirement-conflict",
                evidence_indicators=["admitted_sources_conflict"],
            )
        ],
        deep_assumption_audit={
            "assumptions": [
                {
                    "assumption_id": "assumption.scope",
                    "statement": "The fixture scope is federal.",
                    "support": "Sanitized fixture.",
                    "fragility": "medium",
                    "what_would_change_answer": "A state-specific scope.",
                }
            ]
        },
    )

    record = consume_followup_deliberation_checkpoint(checkpoint).to_dict()

    assert record["sealed_candidates"][0]["provider_job_kind"] == "reconciliation_support"
    assert record["sealed_candidates"][0]["budget_debit"]["macro_hops"] == 1
    assert record["deep_assumption_audit"]["assumptions"][0]["fragility"] == "medium"
    assert record["execution_gate"]["provider_execution_licensed"] is False


def test_invalid_direct_browse_fetch_or_code_claim_is_rejected() -> None:
    payload = _checkpoint().to_dict()
    payload["capabilities"]["may_directly_browse"] = True
    payload["capabilities"]["may_directly_fetch"] = True
    payload["behavior_boundary_flags"]["arbitrary_code_execution_used"] = True

    record = consume_followup_deliberation_checkpoint(payload).to_dict()

    assert record["status"] == "denied_invalid_checkpoint"
    assert record["sealed_candidates"] == []
    assert any("may_directly_browse" in e for e in record["validation"]["errors"])
    assert any("may_directly_fetch" in e for e in record["validation"]["errors"])
    assert any("arbitrary_code_execution_used" in e for e in record["validation"]["errors"])


def test_bridge_only_provider_output_cannot_become_final_evidence_satisfaction() -> None:
    checkpoint = _checkpoint(
        gaps=[
            _gap(
                GapType.OFFICIAL_CURRENT_GAP.value,
                gap_id="gap.bridge",
                obligation_id="obligation-bridge",
                requirement_id="requirement-bridge",
                bridge_only_provider_output_present=True,
                evidence_indicators=["provider_answer_context_only"],
            )
        ],
        sufficiency_handoff={
            "missing_obligations": ["obligation-bridge"],
            "bridge_only_provider_outputs_satisfy_final_evidence": False,
        },
    )

    record = consume_followup_deliberation_checkpoint(checkpoint).to_dict()
    seal = record["sealed_candidates"][0]

    assert seal["bridge_only_provider_output"] is True
    assert seal["bridge_only_provider_output_satisfies_final_evidence"] is False
    assert seal["final_evidence_satisfaction_allowed"] is False
    assert record["sufficiency_handoff"][
        "bridge_only_provider_outputs_satisfy_final_evidence"
    ] is False


def test_budget_exhausted_consumes_denial_not_authorization() -> None:
    checkpoint = _checkpoint(budget_ledger=_budget(provider_calls_remaining=0))

    record = consume_followup_deliberation_checkpoint(checkpoint).to_dict()

    assert record["status"] == "denied"
    assert record["sealed_candidates"] == []
    assert record["denied_budget_debits"][0]["decision"] == "insufficient_budget"
    assert record["budget_semantics"]["denied_debits_preserved"]


def test_repeated_failed_recovery_consumes_stop_not_authorization() -> None:
    checkpoint = _checkpoint(
        prior_failed_followup_attempts=[
            {
                "gap_id": "gap.official",
                "source_obligation_id": "obligation-official-current",
            }
        ]
    )

    record = consume_followup_deliberation_checkpoint(checkpoint).to_dict()

    assert record["status"] == "denied"
    assert record["sealed_candidates"] == []
    assert record["consumed_stop_decisions"][0]["stop_reason"] == (
        "repeated_failed_recovery"
    )


def test_attempted_execution_from_ag96i2a_state_fails_closed() -> None:
    record = consume_followup_deliberation_checkpoint(_checkpoint())

    with pytest.raises(PermissionError, match=FOLLOWUP_EXECUTION_GATE_REASON):
        request_followup_provider_execution(record, candidate_id="auth.001")


def test_runkernel_consumes_followup_state_and_trace_is_derived_from_state() -> None:
    kernel = RunKernel.start(run_id="ag96i2a-fixture", request_id="request-1")
    action = kernel.authorize_followup_authorization_consumption(
        inputs={"checkpoint_id": "after-first-pass"}
    )
    result = execute_followup_authorization_consumption_action(
        action,
        checkpoint=_checkpoint(),
    )

    kernel.reduce(result.observation)

    assert kernel.state.followup_authorization_state["canonical_state"] is True
    assert kernel.state.followup_authorization_projection["trace_only"] is False
    assert kernel.state.projections[FOLLOWUP_AUTHORIZATION_STAGE] == (
        kernel.state.followup_authorization_projection
    )
    trace = kernel.to_trace_fragment()[RUN_KERNEL_TRACE_KEY]
    assert trace["followup_authorization_state"] == kernel.state.followup_authorization_state
    assert trace["followup_authorization_projection"] == (
        kernel.state.followup_authorization_projection
    )


def test_runkernel_rejects_executable_followup_authorization_state() -> None:
    kernel = RunKernel.start(run_id="ag96i2a-fixture", request_id="request-1")
    action = kernel.authorize_followup_authorization_consumption()
    result = execute_followup_authorization_consumption_action(
        action,
        checkpoint=_checkpoint(),
    )
    payload = result.observation.to_dict()["payload"]
    payload["followup_authorization_state"]["execution_gate"]["execution_permission"] = True
    bad_observation = result.observation.__class__(
        observation_id=result.observation.observation_id,
        run_id=result.observation.run_id,
        action_id=result.observation.action_id,
        stage=result.observation.stage,
        observation_type=result.observation.observation_type,
        status=result.observation.status,
        payload=payload,
        sequence=result.observation.sequence,
    )

    with pytest.raises(RunKernelTransitionError, match="closed execution gate"):
        kernel.reduce(bad_observation)


def test_redaction_sensitive_fields_absent_from_consumed_state() -> None:
    checkpoint = _checkpoint(
        input_state_refs={
            "raw_prompt": "RAW_PROMPT_SENTINEL",
            "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
            "raw_model_response": "RAW_MODEL_SENTINEL",
            "raw_text": "RAW_TEXT_SENTINEL",
            "full_text": "FULL_TEXT_SENTINEL",
            "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
            "token": "TOKEN_SENTINEL",
            "db_row": "DB_ROW_SENTINEL",
            "full_trace": "FULL_TRACE_SENTINEL",
        }
    )
    encoded = json.dumps(
        consume_followup_deliberation_checkpoint(checkpoint).to_dict(),
        sort_keys=True,
    )

    for forbidden in (
        "raw_prompt",
        "raw_provider_payload",
        "raw_model_response",
        "raw_text",
        "full_text",
        "secret",
        "token",
        "db_row",
        "full_trace",
        "RAW_PROMPT_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "RAW_MODEL_SENTINEL",
        "RAW_TEXT_SENTINEL",
        "FULL_TEXT_SENTINEL",
        "SECRET_SENTINEL",
        "TOKEN_SENTINEL",
        "DB_ROW_SENTINEL",
        "FULL_TRACE_SENTINEL",
    ):
        assert forbidden not in encoded


def test_static_guards_keep_followup_runtime_closed_to_provider_search_and_orchestrator() -> None:
    module_paths = [
        ROOT / "core" / "followup_authorization_runtime.py",
        ROOT / "core" / "followup_deliberation.py",
        ROOT / "core" / "followup_deliberation_validation.py",
    ]
    forbidden_imports = {
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.pipeline_orchestrator",
        "subprocess",
        "os",
    }

    for path in module_paths:
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()
        assert _imports(path).isdisjoint(forbidden_imports)
        for token in ("ask_model", "eval(", "exec(", "format_citation"):
            assert token not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "followup_authorization_runtime" not in pipeline_source
    assert "FOLLOWUP_AUTHORIZATION_STAGE" not in pipeline_source


def test_balanced_runtime_does_not_seal_macro_or_reconciliation_if_injected() -> None:
    checkpoint = _checkpoint()
    payload = checkpoint.to_dict()
    payload["records"]["followup_authorization_candidates"] = [
        {
            **payload["records"]["followup_authorization_candidates"][0],
            "authorization_id": "auth.macro.injected",
            "hop_type": ReasoningHopType.MACRO_RUN_DIAGNOSIS.value,
            "provider_job_kind": "reconciliation_support",
        }
    ]

    record = consume_followup_deliberation_checkpoint(payload).to_dict()

    assert record["status"] == "denied_invalid_checkpoint"
    assert record["sealed_candidates"] == []
    assert record["denied_candidate_ids"] == ["auth.macro.injected"]


def test_followup_decision_taxonomy_is_preserved_in_consumed_budget_records() -> None:
    checkpoint = _checkpoint(budget_ledger=_budget(fetches_remaining=0))
    record = consume_followup_deliberation_checkpoint(checkpoint).to_dict()

    assert record["consumed_budget_decisions"][0]["decision"] == (
        FollowupDecision.INSUFFICIENT_BUDGET.value
    )
    assert record["consumed_budget_decisions"][0]["debit_authorized_for_future_phase"] is False


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
