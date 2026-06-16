import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.followup_authorization_runtime import (
    execute_followup_authorization_consumption_action,
)
from core.followup_deliberation import (
    GapType,
    ProviderJobKind,
    build_followup_deliberation_checkpoint,
)
from core.followup_evidence_intake_runtime import (
    FOLLOWUP_PROVIDER_JOB_EVIDENCE_INTAKE_MODE,
    execute_followup_evidence_intake_action,
)
from core.followup_final_answer_packet_runtime import (
    execute_followup_final_answer_packet_prepare_action,
)
from core.followup_provider_job_live_validation_runtime import (
    AG96I3B_EXACT_VALIDATION_QUERY,
    execute_live_gated_followup_provider_job_validation_action,
)
from core.followup_sufficiency_recheck_runtime import (
    execute_followup_sufficiency_recheck_action,
)
from core.run_kernel import AuthorizedAction, RunKernel
from tests.helpers.followup_fixture_spine import followup_fixture_gap

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "ag96i3b-live-gated-provider-job"
ALLOWED_CANDIDATE_FACT_KEYS = {
    "url",
    "title",
    "domain",
    "source_tier",
    "source_class",
    "currentness_signal",
    "readable_status",
    "fetchable_status",
    "provider_name",
    "retrieval_pass_id",
    "adapter_result_id",
    "result_status",
    "bridge_only",
    "authorized_query_ref",
    "authorized_query",
}


def _budget(**overrides: int) -> dict[str, int]:
    budget = {
        "cost_points_remaining": 8,
        "provider_calls_remaining": 3,
        "fetches_remaining": 3,
        "read_units_remaining": 3,
        "followup_rounds_remaining": 2,
        "meso_authorizations_remaining": 3,
        "macro_hops_remaining": 1,
    }
    budget.update(overrides)
    return budget


def _component(component_id: str = "component-rule") -> dict[str, Any]:
    return {
        "component_id": component_id,
        "central": True,
        "served_minimum": True,
        "minimum_provider_calls": 1,
        "minimum_fetches": 1,
        "minimum_read_units": 1,
    }


def _checkpoint(
    *,
    provider_query_ref: str | None = "query.ref.ag96i3b.official.current",
    provider_query: str | None = AG96I3B_EXACT_VALIDATION_QUERY,
) -> Any:
    gap = followup_fixture_gap(
        GapType.OFFICIAL_CURRENT_GAP.value,
        authorized_query_ref=provider_query_ref,
        authorized_query=provider_query,
    )
    return build_followup_deliberation_checkpoint(
        {
            "run_id": RUN_ID,
            "checkpoint_id": "after-first-pass",
            "mode": "balanced",
            "components": [_component()],
            "budget_ledger": _budget(),
            "gaps": [gap],
            "sufficiency_handoff": {
                "satisfied_obligations": [],
                "missing_obligations": ["obligation-official-current"],
                "recommended_final_posture": "answer_with_caveats",
                "mandatory_caveats": ["prior_missing_official_current_caveat"],
                "prohibited_upgrades": ["prior_do_not_upgrade_fixture_gap"],
            },
        }
    )


def _authorized_kernel() -> RunKernel:
    kernel = RunKernel.start(run_id=RUN_ID, request_id="request-1")
    action = kernel.authorize_followup_authorization_consumption(
        inputs={"checkpoint_id": "after-first-pass"}
    )
    result = execute_followup_authorization_consumption_action(
        action,
        checkpoint=_checkpoint(),
    )
    kernel.reduce(result.observation)
    return kernel


def _provider_job_action(kernel: RunKernel) -> AuthorizedAction:
    return kernel.authorize_followup_provider_job_execution(
        candidate_id="auth.candidate.001"
    )


def _replace_action_inputs(
    action: AuthorizedAction,
    **overrides: Any,
) -> AuthorizedAction:
    inputs = dict(action.inputs)
    inputs.update(overrides)
    return AuthorizedAction(
        action_id=action.action_id,
        run_id=action.run_id,
        stage=action.stage,
        action_type=action.action_type,
        reason=action.reason,
        inputs=inputs,
        expected_observation_type=action.expected_observation_type,
        sequence=action.sequence,
    )


def _fake_official_search(_query: str) -> list[dict[str, Any]]:
    return [
        {
            "title": "IRS announces 2026 standard mileage rates",
            "url": "https://www.irs.gov/newsroom/irs-announces-2026-standard-mileage-rates",
            "domain": "irs.gov",
            "snippet": "raw provider snippet must not be retained",
            "raw_content": "raw provider body must not be retained",
            "text": "raw readable page text must not be retained",
            "payload": {"placeholder": "blocked_test_value"},
        }
    ]


def _fake_lower_then_official_search(_query: str) -> list[dict[str, Any]]:
    return [
        {
            "title": "Mileage rate explainer from a fleet vendor",
            "url": "https://cardata.co/blog/mileage-rate",
            "domain": "cardata.co",
            "snippet": "raw rank 1 snippet must not be retained",
            "text": "raw rank 1 text must not be retained",
            "payload": {"placeholder": "blocked_rank_1"},
        },
        {
            "title": "IRS announces 2026 standard mileage rates",
            "url": "https://www.irs.gov/newsroom/irs-announces-2026-standard-mileage-rates",
            "domain": "irs.gov",
            "snippet": "raw rank 2 snippet must not be retained",
            "raw_content": "raw rank 2 content must not be retained",
            "payload": {"placeholder": "blocked_rank_2"},
        },
    ]


def _fake_lower_only_search(_query: str) -> list[dict[str, Any]]:
    return [
        {
            "title": "Mileage rate explainer from a fleet vendor",
            "url": "https://cardata.co/blog/mileage-rate",
            "domain": "cardata.co",
            "snippet": "raw lower-tier snippet must not be retained",
            "text": "raw lower-tier text must not be retained",
            "payload": {"placeholder": "blocked_lower_only"},
        }
    ]


def _execute_live_gate(
    action: AuthorizedAction,
    *,
    provider_search: Any = _fake_official_search,
    config_available: bool = True,
    provider_name: str = "fake_live_search",
) -> Any:
    return execute_live_gated_followup_provider_job_validation_action(
        action,
        live_validation_authorized=True,
        provider_search=provider_search,
        provider_config_available=lambda: config_available,
        provider_name=provider_name,
    )


def _intake_provider_job(kernel: RunKernel) -> Any:
    action = kernel.authorize_followup_evidence_intake()
    result = execute_followup_evidence_intake_action(
        action,
        followup_execution_state=kernel.state.followup_execution_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    kernel.reduce(result.observation)
    return result


def _recheck(kernel: RunKernel) -> Any:
    action = kernel.authorize_followup_sufficiency_recheck()
    result = execute_followup_sufficiency_recheck_action(
        action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        prior_sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        sufficiency_handoff=kernel.state.followup_authorization_state.get(
            "sufficiency_handoff",
            {},
        ),
    )
    kernel.reduce(result.observation)
    return result


def _packet(kernel: RunKernel) -> Any:
    action = kernel.authorize_followup_final_answer_packet_prepare()
    result = execute_followup_final_answer_packet_prepare_action(
        action,
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )
    kernel.reduce(result.observation)
    return result


def test_live_gate_refuses_without_explicit_authorization() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)
    calls = 0

    def search(_query: str) -> list[dict[str, Any]]:
        nonlocal calls
        calls += 1
        return _fake_official_search(_query)

    with pytest.raises(PermissionError, match="explicit authorization"):
        execute_live_gated_followup_provider_job_validation_action(
            action,
            live_validation_authorized=False,
            provider_search=search,
            provider_config_available=lambda: True,
        )

    assert calls == 0


def test_live_gate_refuses_wrong_provider_job_kind() -> None:
    kernel = _authorized_kernel()
    action = _replace_action_inputs(
        _provider_job_action(kernel),
        provider_job_kind=ProviderJobKind.SEMANTIC_RECALL.value,
    )

    with pytest.raises(PermissionError, match="official/current"):
        _execute_live_gate(action)


def test_live_gate_refuses_without_authorized_query_ref_or_query() -> None:
    kernel = _authorized_kernel()
    action = _replace_action_inputs(
        _provider_job_action(kernel),
        authorized_query_ref=None,
        authorized_query=None,
    )

    with pytest.raises(PermissionError, match="authorized query/ref"):
        _execute_live_gate(action)


def test_live_gate_enforces_one_provider_search_call_and_no_retries() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)
    calls = 0

    def failing_search(_query: str) -> list[dict[str, Any]]:
        nonlocal calls
        calls += 1
        raise RuntimeError("simulated provider failure")

    result = _execute_live_gate(action, provider_search=failing_search)

    record = result.validation_record.to_dict()
    assert calls == 1
    assert record["provider_search_call_count"] == 1
    assert record["live_budget"]["max_provider_search_calls"] == 1
    assert record["live_budget"]["no_retries"] is True
    assert record["result_status"] == "provider_search_error"
    assert result.provider_job_action_result is not None


def test_live_gate_redacts_raw_payload_text_and_snippet_fields() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)

    result = _execute_live_gate(action)

    candidate = result.validation_record.to_dict()["sanitized_candidate_facts"]
    serialized = json.dumps(candidate, sort_keys=True)
    assert set(candidate) == ALLOWED_CANDIDATE_FACT_KEYS
    for forbidden in (
        "snippet",
        "raw_content",
        "raw provider",
        "raw readable",
        "payload",
        "blocked_test_value",
    ):
        assert forbidden not in serialized


def test_live_gate_returns_sanitized_candidate_facts_only() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)

    result = _execute_live_gate(action)

    candidate = result.validation_record.to_dict()["sanitized_candidate_facts"]
    assert set(candidate) == ALLOWED_CANDIDATE_FACT_KEYS
    assert candidate["url"].startswith("https://www.irs.gov/")
    assert candidate["domain"] == "irs.gov"
    assert candidate["source_tier"] == "official"
    assert candidate["source_class"] == "official_government"
    assert candidate["authorized_query"] == AG96I3B_EXACT_VALIDATION_QUERY


def test_official_current_selector_chooses_lower_rank_official_candidate() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)

    result = _execute_live_gate(
        action,
        provider_search=_fake_lower_then_official_search,
    )

    record = result.validation_record.to_dict()
    candidate = record["sanitized_candidate_facts"]
    diagnostics = record["provider_result_set_diagnostics"]
    assert candidate["domain"] == "irs.gov"
    assert candidate["url"].startswith("https://www.irs.gov/")
    assert candidate["result_status"] == "candidate_acquired"
    assert candidate["bridge_only"] is False
    assert diagnostics["provider_result_count"] == 2
    assert diagnostics["sanitized_result_count"] == 2
    assert diagnostics["selected_candidate_rank"] == 2
    assert diagnostics["selected_candidate_reason"] == (
        "official_current_candidate_selected"
    )
    assert diagnostics["first_failure_layer"] == "none"
    assert [item["domain"] for item in diagnostics["sanitized_results"]] == [
        "cardata.co",
        "irs.gov",
    ]


def test_no_official_result_records_bridge_hint_and_ledger_does_not_admit() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)

    result = _execute_live_gate(action, provider_search=_fake_lower_only_search)
    kernel.reduce(result.provider_job_action_result.observation)
    _intake_provider_job(kernel)

    record = result.validation_record.to_dict()
    candidate = record["sanitized_candidate_facts"]
    diagnostics = record["provider_result_set_diagnostics"]
    intake = kernel.state.followup_evidence_intake_state
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()

    assert record["stop_reason"] == "no_satisfying_official_current_candidate"
    assert candidate["domain"] == "cardata.co"
    assert candidate["result_status"] == "bridge_only"
    assert candidate["bridge_only"] is True
    assert diagnostics["selected_candidate_rank"] == 1
    assert diagnostics["selected_candidate_reason"] == (
        "no_satisfying_official_current_candidate_bridge_hint_recorded"
    )
    assert diagnostics["first_failure_layer"] == "official_current_selection"
    assert intake["evidence_ledger_candidate_admitted"] is False
    assert intake["source_obligation_satisfied"] is False
    assert ledger["candidate_records"][0]["final_evidence_eligible"] is False


def test_scout_bridge_hint_mode_records_hints_without_official_satisfaction() -> None:
    kernel = _authorized_kernel()
    action = _replace_action_inputs(
        _provider_job_action(kernel),
        provider_job_kind=ProviderJobKind.SCOUT_DISAMBIGUATION.value,
    )

    result = _execute_live_gate(
        action,
        provider_search=_fake_lower_then_official_search,
    )

    record = result.validation_record.to_dict()
    candidate = record["sanitized_candidate_facts"]
    diagnostics = record["provider_result_set_diagnostics"]
    assert result.provider_job_action_result is None
    assert record["stop_reason"] == "provider_hints_recorded"
    assert candidate["domain"] == "cardata.co"
    assert candidate["result_status"] == "bridge_only"
    assert candidate["bridge_only"] is True
    assert diagnostics["provider_job_kind"] == "scout_disambiguation"
    assert diagnostics["selected_candidate_reason"] == (
        "scout_bridge_hint_recorded_not_official_current_satisfaction"
    )
    assert diagnostics["first_failure_layer"] == "official_current_selection"


def test_scout_only_provider_surface_records_alignment_mismatch() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)

    result = _execute_live_gate(
        action,
        provider_search=_fake_lower_then_official_search,
        provider_name="brave_reconnaissance",
    )

    record = result.validation_record.to_dict()
    candidate = record["sanitized_candidate_facts"]
    diagnostics = record["provider_result_set_diagnostics"]
    assert candidate["domain"] == "irs.gov"
    assert candidate["result_status"] == "bridge_only"
    assert candidate["bridge_only"] is True
    assert diagnostics["selected_candidate_rank"] == 2
    assert diagnostics["provider_surface_role"] == "scout_bridge_hint"
    assert diagnostics["provider_job_surface_alignment_status"] == (
        "provider_surface_mismatch"
    )
    assert diagnostics["selected_candidate_reason"] == (
        "official_current_candidate_visible_on_scout_bridge_surface"
    )
    assert diagnostics["first_failure_layer"] == "provider_job_surface_alignment"


def test_result_set_diagnostics_include_multiple_sanitized_ranks_only() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)

    result = _execute_live_gate(
        action,
        provider_search=_fake_lower_then_official_search,
    )

    diagnostics = result.validation_record.to_dict()[
        "provider_result_set_diagnostics"
    ]
    serialized = json.dumps(diagnostics, sort_keys=True)
    assert diagnostics["provider_result_count"] == 2
    assert diagnostics["sanitized_result_count"] == 2
    assert [item["rank"] for item in diagnostics["sanitized_results"]] == [1, 2]
    assert {
        "rank",
        "url",
        "title",
        "domain",
        "source_class",
        "source_tier",
        "currentness_signal",
        "candidate_fit_status",
    } == set(diagnostics["sanitized_results"][0])
    for forbidden in (
        "snippet",
        "raw_content",
        "raw rank",
        "payload",
        "blocked_rank_1",
        "blocked_rank_2",
    ):
        assert forbidden not in serialized


def test_live_gate_preserves_runkernel_state_and_same_evidence_ledger_path() -> None:
    kernel = _authorized_kernel()
    ledger_object = kernel.state.evidence_ledger
    action = _provider_job_action(kernel)
    result = _execute_live_gate(action)

    kernel.reduce(result.provider_job_action_result.observation)
    assert kernel.state.followup_execution_state["owner"] == (
        "RunKernel.FollowupProviderJobExecution"
    )
    assert kernel.state.followup_execution_state["canonical_state"] is True
    assert kernel.state.followup_execution_state["provider_job_kind"] == (
        ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value
    )
    assert result.validation_record.to_dict()["provider_search_call_count"] == 1

    _intake_provider_job(kernel)

    assert kernel.state.evidence_ledger is ledger_object
    assert kernel.state.followup_evidence_intake_state["evidence_ledger_intake_mode"] == (
        FOLLOWUP_PROVIDER_JOB_EVIDENCE_INTAKE_MODE
    )
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    assert ledger["candidate_records"][0]["provider_name"] == "fake_live_search"
    assert ledger["candidate_records"][0]["query_ref"] == (
        "query.ref.ag96i3b.official.current"
    )


def test_live_gate_keeps_author_citation_and_product_flags_closed() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)
    result = _execute_live_gate(action)

    kernel.reduce(result.provider_job_action_result.observation)
    state = kernel.state.followup_execution_state
    for field in (
        "model_called",
        "author_activation_allowed",
        "author_executor_invoked",
        "citation_eligible",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
    ):
        assert state[field] is False

    _intake_provider_job(kernel)
    _recheck(kernel)
    _packet(kernel)
    assert kernel.state.final_answer_authority_projection[
        "author_activation_allowed"
    ] is False
    assert kernel.state.followup_final_answer_packet_state[
        "author_execution_deferred"
    ] is True


def test_live_gate_stops_cleanly_when_provider_config_is_missing() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)
    calls = 0

    def search(_query: str) -> list[dict[str, Any]]:
        nonlocal calls
        calls += 1
        return _fake_official_search(_query)

    result = _execute_live_gate(
        action,
        provider_search=search,
        config_available=False,
    )

    record = result.validation_record.to_dict()
    assert record["result_status"] == "config_missing_not_run"
    assert record["stop_reason"] == "provider_config_missing"
    assert record["provider_config_available"] is False
    assert record["provider_search_call_count"] == 0
    assert result.provider_job_action_result is None
    assert calls == 0


def test_static_closed_surface_guard_for_live_gate_adapter() -> None:
    module_path = ROOT / "core" / "followup_provider_job_live_validation_runtime.py"
    source = module_path.read_text(encoding="utf-8")
    imports = _imports(module_path)
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.author_execution_runtime",
        "core.followup_author_gate_runtime",
        "core.followup_author_observation_runtime",
        "core.followup_final_answer_packet_runtime",
        "core.citation_source_handoff_contract",
        "core.provider_search_final_assembly_authority_boundary",
    }
    assert imports.isdisjoint(forbidden_imports)
    for token in (
        "AuthorExecutor",
        "FinalAnswerPacket",
        "format_citation",
    ):
        assert token not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "followup_provider_job_live_validation_runtime" not in pipeline_source


def test_live_gate_does_not_mutate_action_inputs() -> None:
    kernel = _authorized_kernel()
    action = _provider_job_action(kernel)
    original_inputs = deepcopy(action.inputs)

    _execute_live_gate(action)

    assert action.inputs == original_inputs


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
