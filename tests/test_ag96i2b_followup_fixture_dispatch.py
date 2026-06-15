from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from core.followup_authorization_runtime import (
    consume_followup_deliberation_checkpoint,
    execute_followup_authorization_consumption_action,
)
from core.followup_deliberation import (
    GapType,
    ReasoningHopType,
    build_followup_deliberation_checkpoint,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_execution_runtime import (
    FIXTURE_EXECUTION_MODE,
    FOLLOWUP_FIXTURE_GATE_REASON,
    execute_followup_fixture,
    execute_followup_fixture_action,
)
from core.run_kernel import (
    FOLLOWUP_AUTHORIZATION_STAGE,
    FOLLOWUP_EXECUTION_STAGE,
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
        "run_id": "ag96i2b-fixture",
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


def _fixture_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "result_status": "fixture_success",
        "summary": "Sanitized official current fixture candidate observed.",
        "source_class": "official_government",
        "currentness_signal": "fixture_current",
        "answer_bearing_extract_available": True,
    }
    payload.update(overrides)
    return payload


def _balanced_authorization_state() -> dict[str, Any]:
    return consume_followup_deliberation_checkpoint(_checkpoint()).to_dict()


def _execute_through_kernel(
    *,
    checkpoint: Any | None = None,
    fixture_payload: dict[str, Any] | None = None,
    candidate_id: str = "auth.candidate.001",
) -> RunKernel:
    checkpoint = checkpoint or _checkpoint()
    kernel = RunKernel.start(run_id="ag96i2b-fixture", request_id="request-1")
    auth_action = kernel.authorize_followup_authorization_consumption(
        inputs={"checkpoint_id": "after-first-pass"}
    )
    auth_result = execute_followup_authorization_consumption_action(
        auth_action,
        checkpoint=checkpoint,
    )
    kernel.reduce(auth_result.observation)

    exec_action = kernel.authorize_followup_fixture_execution(
        candidate_id=candidate_id,
        inputs={"fixture_execution_mode": FIXTURE_EXECUTION_MODE},
    )
    exec_result = execute_followup_fixture_action(
        exec_action,
        authorization_state=kernel.state.followup_authorization_state,
        sealed_candidate_id=candidate_id,
        fixture_result_payload=fixture_payload or _fixture_payload(),
        execution_mode=FIXTURE_EXECUTION_MODE,
    )
    kernel.reduce(exec_result.observation)
    return kernel


def test_balanced_sealed_official_current_candidate_fixture_executes_into_canonical_state() -> None:
    kernel = _execute_through_kernel()

    state = kernel.state.followup_execution_state
    assert state["canonical_state"] is True
    assert state["result_status"] == "fixture_success"
    assert state["provider_job_kind"] == "official_current_candidate_acquisition"
    assert state["component_id"] == "component_rule"
    assert state["source_obligation_id"] == "obligation_official_current"
    assert state["evidence_ledger_intake_deferred"] is True
    assert kernel.state.followup_authorization_state["status"] == "sealed_non_executable"


def test_runkernel_projection_is_derived_from_followup_execution_state() -> None:
    kernel = _execute_through_kernel()

    assert kernel.state.followup_execution_projection["trace_only"] is False
    assert kernel.state.projections[FOLLOWUP_EXECUTION_STAGE] == (
        kernel.state.followup_execution_projection
    )
    trace = kernel.to_trace_fragment()[RUN_KERNEL_TRACE_KEY]
    assert trace["followup_execution_state"] == kernel.state.followup_execution_state
    assert trace["followup_execution_projection"] == (
        kernel.state.followup_execution_projection
    )
    assert trace["followup_execution_projection"]["execution_id"] == (
        kernel.state.followup_execution_state["execution_id"]
    )


def test_fixture_execution_preserves_candidate_fields_budget_and_fallback_posture() -> None:
    record = execute_followup_fixture(
        _balanced_authorization_state(),
        sealed_candidate_id="auth.candidate.001",
        fixture_result_payload=_fixture_payload(),
        execution_mode=FIXTURE_EXECUTION_MODE,
    ).to_dict()

    assert record["provider_job_kind"] == "official_current_candidate_acquisition"
    assert record["component_id"] == "component_rule"
    assert record["source_obligation_id"] == "obligation_official_current"
    assert record["expected_evidence_ledger_custody_update"][
        "custody_update_expected"
    ] == [
        "candidate_identity",
        "source_class",
        "currentness_signal",
        "readable_answer_bearing_extract",
        "requirement_link",
    ]
    assert record["budget_debit"]["provider_calls"] == 1
    assert record["fallback_stop_posture"] == "answer_with_caveats"
    assert record["fallback_caveat_refuse_posture"] == "insufficient_evidence"


def test_fixture_execution_records_no_live_provider_search_retrieval_fetch_or_model_calls() -> None:
    record = execute_followup_fixture(
        _balanced_authorization_state(),
        sealed_candidate_id="auth.candidate.001",
        fixture_result_payload=_fixture_payload(),
        execution_mode=FIXTURE_EXECUTION_MODE,
    ).to_dict()
    flags = record["behavior_boundary_flags"]

    assert flags["live_provider_call_executed"] is False
    assert flags["search_executed"] is False
    assert flags["retrieval_executed"] is False
    assert flags["fetch_executed"] is False
    assert flags["model_called"] is False
    assert record["execution_gate"]["provider_execution_licensed"] is False


def test_fixture_execution_defers_evidence_ledger_and_does_not_mutate_it() -> None:
    kernel = RunKernel.start(run_id="ag96i2b-fixture", request_id="request-1")
    before = kernel.state.evidence_ledger.to_projection().to_dict()
    auth_action = kernel.authorize_followup_authorization_consumption()
    auth_result = execute_followup_authorization_consumption_action(
        auth_action,
        checkpoint=_checkpoint(),
    )
    kernel.reduce(auth_result.observation)
    after_auth = kernel.state.evidence_ledger.to_projection().to_dict()

    exec_action = kernel.authorize_followup_fixture_execution(
        candidate_id="auth.candidate.001",
        inputs={"fixture_execution_mode": FIXTURE_EXECUTION_MODE},
    )
    exec_result = execute_followup_fixture_action(
        exec_action,
        authorization_state=kernel.state.followup_authorization_state,
        sealed_candidate_id="auth.candidate.001",
        fixture_result_payload=_fixture_payload(),
        execution_mode=FIXTURE_EXECUTION_MODE,
    )
    kernel.reduce(exec_result.observation)
    after_exec = kernel.state.evidence_ledger.to_projection().to_dict()

    assert before == after_auth == after_exec
    assert kernel.state.followup_execution_state["evidence_ledger_intake_deferred"] is True
    assert kernel.state.followup_execution_state["evidence_ledger_evidence_admitted"] is False


@pytest.mark.parametrize(
    "mode",
    ["disabled", "live", "provider", "search", "retrieval", "fetch", "model"],
)
def test_attempted_non_fixture_execution_modes_fail_closed(mode: str) -> None:
    with pytest.raises(PermissionError, match=FOLLOWUP_FIXTURE_GATE_REASON):
        execute_followup_fixture(
            _balanced_authorization_state(),
            sealed_candidate_id="auth.candidate.001",
            fixture_result_payload=_fixture_payload(),
            execution_mode=mode,
        )


def test_missing_fixture_payload_fails_closed() -> None:
    with pytest.raises(ValueError, match="fixture_result_payload"):
        execute_followup_fixture(
            _balanced_authorization_state(),
            sealed_candidate_id="auth.candidate.001",
            execution_mode=FIXTURE_EXECUTION_MODE,
        )


def test_invalid_authorization_state_fails_closed() -> None:
    denied = consume_followup_deliberation_checkpoint(
        _checkpoint(budget_ledger=_budget(provider_calls_remaining=0))
    ).to_dict()

    with pytest.raises(PermissionError, match="sealed authorization state"):
        execute_followup_fixture(
            denied,
            sealed_candidate_id="auth.candidate.001",
            fixture_result_payload=_fixture_payload(),
            execution_mode=FIXTURE_EXECUTION_MODE,
        )


def test_unknown_sealed_candidate_id_fails_closed() -> None:
    with pytest.raises(KeyError, match="unknown sealed"):
        execute_followup_fixture(
            _balanced_authorization_state(),
            sealed_candidate_id="auth.unknown",
            fixture_result_payload=_fixture_payload(),
            execution_mode=FIXTURE_EXECUTION_MODE,
        )


def test_malicious_executable_gate_in_authorization_state_fails_closed() -> None:
    state = _balanced_authorization_state()
    state["sealed_candidates"][0]["execution_gate"]["provider_execution_licensed"] = True

    with pytest.raises(PermissionError, match="real provider execution permission"):
        execute_followup_fixture(
            state,
            sealed_candidate_id="auth.candidate.001",
            fixture_result_payload=_fixture_payload(),
            execution_mode=FIXTURE_EXECUTION_MODE,
        )


def test_fast_malicious_sealed_candidate_fails_closed() -> None:
    state = _balanced_authorization_state()
    state["mode"] = "fast"
    state["sealed_candidates"][0]["mode"] = "fast"

    with pytest.raises(PermissionError, match="Fast"):
        execute_followup_fixture(
            state,
            sealed_candidate_id="auth.candidate.001",
            fixture_result_payload=_fixture_payload(),
            execution_mode=FIXTURE_EXECUTION_MODE,
        )


def test_balanced_needs_deep_or_denied_authorization_state_does_not_fixture_execute() -> None:
    needs_deep = consume_followup_deliberation_checkpoint(
        _checkpoint(
            gaps=[
                _gap(
                    GapType.CONFLICT_RECONCILIATION_GAP.value,
                    gap_id="gap.conflict",
                    obligation_id="obligation-currentness-conflict",
                    requirement_id="requirement-currentness",
                    evidence_indicators=["admitted_sources_conflict_on_currentness"],
                )
            ]
        )
    ).to_dict()
    denied = consume_followup_deliberation_checkpoint(
        _checkpoint(budget_ledger=_budget(provider_calls_remaining=0))
    ).to_dict()

    for state in (needs_deep, denied):
        with pytest.raises(PermissionError):
            execute_followup_fixture(
                state,
                sealed_candidate_id="auth.candidate.001",
                fixture_result_payload=_fixture_payload(),
                execution_mode=FIXTURE_EXECUTION_MODE,
            )


def test_deep_reconciliation_candidate_fixture_executes_without_real_reconciliation() -> None:
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
    )
    state = consume_followup_deliberation_checkpoint(checkpoint).to_dict()
    candidate_id = state["sealed_candidates"][0]["candidate_id"]
    record = execute_followup_fixture(
        state,
        sealed_candidate_id=candidate_id,
        fixture_result_payload=_fixture_payload(summary="Sanitized conflict map only."),
        execution_mode=FIXTURE_EXECUTION_MODE,
    ).to_dict()

    assert record["provider_job_kind"] == "reconciliation_support"
    assert record["result_status"] == "fixture_success"
    assert record["behavior_boundary_flags"]["search_executed"] is False
    assert record["behavior_boundary_flags"]["evidence_ledger_mutated"] is False
    assert record["final_evidence_satisfied"] is False


def test_bridge_only_fixture_result_cannot_satisfy_final_evidence_or_citation() -> None:
    record = execute_followup_fixture(
        _balanced_authorization_state(),
        sealed_candidate_id="auth.candidate.001",
        fixture_result_payload=_fixture_payload(
            result_status="fixture_success",
            bridge_only=True,
            final_evidence_satisfied=True,
            citation_eligible=True,
        ),
        execution_mode=FIXTURE_EXECUTION_MODE,
    ).to_dict()

    assert record["result_status"] == "fixture_bridge_only"
    assert record["bridge_only"] is True
    assert record["final_evidence_satisfied"] is False
    assert record["citation_eligible"] is False
    assert record["evidence_ledger_evidence_admitted"] is False


def test_budget_semantics_preserve_planned_debit_but_record_no_actual_cost() -> None:
    record = execute_followup_fixture(
        _balanced_authorization_state(),
        sealed_candidate_id="auth.candidate.001",
        fixture_result_payload=_fixture_payload(),
        execution_mode=FIXTURE_EXECUTION_MODE,
    ).to_dict()
    budget = record["budget_semantics"]

    assert budget["planned_debit_preserved"]["provider_calls"] == 1
    assert budget["fixture_execution_did_not_incur_provider_search_fetch_read_cost"] is True
    assert budget["actual_provider_search_fetch_read_cost_incurred"] is False
    assert budget["actual_provider_account_debited"] is False
    assert budget["provider_cost_accounting_deferred"] is True


def test_redaction_sensitive_fixture_fields_absent_from_execution_state() -> None:
    record = execute_followup_fixture(
        _balanced_authorization_state(),
        sealed_candidate_id="auth.candidate.001",
        fixture_result_payload=_fixture_payload(
            raw_prompt="RAW_PROMPT_SENTINEL",
            raw_provider_payload="RAW_PROVIDER_SENTINEL",
            raw_model_response="RAW_MODEL_SENTINEL",
            raw_text="RAW_TEXT_SENTINEL",
            full_text="FULL_TEXT_SENTINEL",
            secret="SECRET_SENTINEL",  # pragma: allowlist secret
            token="TOKEN_SENTINEL",
            db_row="DB_ROW_SENTINEL",
            full_trace="FULL_TRACE_SENTINEL",
        ),
        execution_mode=FIXTURE_EXECUTION_MODE,
    ).to_dict()
    encoded = json.dumps(record, sort_keys=True)

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


def test_runkernel_rejects_execution_observation_with_live_or_ledger_flags() -> None:
    kernel = _execute_through_kernel()
    action = kernel.authorize_followup_fixture_execution(
        candidate_id="auth.candidate.001",
        inputs={"fixture_execution_mode": FIXTURE_EXECUTION_MODE},
    )
    record = execute_followup_fixture(
        kernel.state.followup_authorization_state,
        sealed_candidate_id="auth.candidate.001",
        fixture_result_payload=_fixture_payload(),
        execution_mode=FIXTURE_EXECUTION_MODE,
    ).to_dict()
    record["behavior_boundary_flags"]["search_executed"] = True

    bad_observation = kernel.state.observations[-1].__class__.from_action(
        action,
        observation_type="followup_execution_observed",
        status="completed",
        payload={"followup_execution_state": record},
    )

    with pytest.raises(RunKernelTransitionError, match="search_executed=False"):
        kernel.reduce(bad_observation)


def test_static_guards_keep_fixture_dispatch_closed_to_provider_search_and_orchestrator() -> None:
    module_paths = [
        ROOT / "core" / "followup_execution_runtime.py",
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

    run_kernel_source = (ROOT / "core" / "run_kernel.py").read_text(encoding="utf-8")
    assert "followup_execution_runtime" not in run_kernel_source
    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "followup_execution_runtime" not in pipeline_source
    assert "FOLLOWUP_EXECUTION_STAGE" not in pipeline_source
    assert FOLLOWUP_AUTHORIZATION_STAGE in run_kernel_source
    assert FOLLOWUP_EXECUTION_STAGE == "followup_fixture_execution"


def test_run_kernel_authorization_rejects_non_fixture_mode() -> None:
    kernel = RunKernel.start(run_id="ag96i2b-fixture", request_id="request-1")
    auth_action = kernel.authorize_followup_authorization_consumption()
    auth_result = execute_followup_authorization_consumption_action(
        auth_action,
        checkpoint=_checkpoint(),
    )
    kernel.reduce(auth_result.observation)

    with pytest.raises(RunKernelTransitionError, match="fixture_only"):
        kernel.authorize_followup_fixture_execution(
            candidate_id="auth.candidate.001",
            inputs={"fixture_execution_mode": "live"},
        )


def test_balanced_injected_macro_or_denied_candidate_remains_unexecutable() -> None:
    checkpoint = _checkpoint()
    payload = checkpoint.to_dict()
    payload["records"]["followup_authorization_candidates"] = [
        {
            **payload["records"]["followup_authorization_candidates"][0],
            "authorization_id": "auth.macro.injected",
            "hop_type": ReasoningHopType.MACRO_RUN_DIAGNOSIS.value,
        }
    ]
    state = consume_followup_deliberation_checkpoint(payload).to_dict()

    assert state["status"] == "denied_invalid_checkpoint"
    with pytest.raises(PermissionError):
        execute_followup_fixture(
            state,
            sealed_candidate_id="auth.macro.injected",
            fixture_result_payload=_fixture_payload(),
            execution_mode=FIXTURE_EXECUTION_MODE,
        )


def test_fixture_status_taxonomy_accepts_no_result_wrong_source_class_and_error() -> None:
    cases = {
        "fixture_no_result": {"no_result": True},
        "fixture_wrong_source_class": {"wrong_source_class": True},
        "fixture_error": {"error": "sanitized error"},
    }
    for expected, payload in cases.items():
        record = execute_followup_fixture(
            _balanced_authorization_state(),
            sealed_candidate_id="auth.candidate.001",
            fixture_result_payload=_fixture_payload(**payload),
            execution_mode=FIXTURE_EXECUTION_MODE,
        ).to_dict()
        assert record["result_status"] == expected


def test_followup_execution_does_not_change_final_answer_or_author_surfaces() -> None:
    kernel = _execute_through_kernel()

    assert kernel.state.final_answer_packet == {}
    assert kernel.state.final_answer_outcome == {}
    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.followup_execution_state["behavior_boundary_flags"][
        "final_answer_behavior_changed"
    ] is False


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
