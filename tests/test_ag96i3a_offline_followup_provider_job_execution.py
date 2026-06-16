import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.evidence_ledger import SourceRequirementStatus
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
from core.followup_provider_job_execution_runtime import (
    FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND,
    FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
    execute_followup_provider_job_action,
)
from core.followup_sufficiency_recheck_runtime import (
    execute_followup_sufficiency_recheck_action,
)
from core.run_kernel import (
    FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from tests.helpers.followup_fixture_spine import followup_fixture_gap

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "ag96i3a-offline-provider-job"


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
    gap_type: str = GapType.OFFICIAL_CURRENT_GAP.value,
    provider_query_ref: str | None = "query.ref.official.current",
    provider_query: str | None = None,
    budget_ledger: dict[str, int] | None = None,
) -> Any:
    gap = followup_fixture_gap(
        gap_type,
        authorized_query_ref=provider_query_ref,
        authorized_query=provider_query,
    )
    return build_followup_deliberation_checkpoint(
        {
            "run_id": RUN_ID,
            "checkpoint_id": "after-first-pass",
            "mode": "balanced",
            "components": [_component()],
            "budget_ledger": budget_ledger or _budget(),
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


def _official_candidate_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "result_status": "candidate_acquired",
        "adapter_result_id": "adapter-result-official-1",
        "url": "https://agency.example.gov/current-rule",
        "title": "Current Official Rule",
        "domain": "agency.example.gov",
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
        "readable_status": "readable",
        "fetchable_status": "fetchable",
        "provider_name": "offline_official_current_adapter",
        "eligible_for_stronger_obligation": True,
    }
    payload.update(overrides)
    return payload


def _authorized_kernel(
    *,
    checkpoint: Any | None = None,
) -> RunKernel:
    kernel = RunKernel.start(run_id=RUN_ID, request_id="request-1")
    action = kernel.authorize_followup_authorization_consumption(
        inputs={"checkpoint_id": "after-first-pass"}
    )
    result = execute_followup_authorization_consumption_action(
        action,
        checkpoint=checkpoint or _checkpoint(),
    )
    kernel.reduce(result.observation)
    return kernel


def _execute_provider_job(
    kernel: RunKernel,
    *,
    payload: dict[str, Any] | None = None,
) -> tuple[Any, Any]:
    action = kernel.authorize_followup_provider_job_execution(
        candidate_id="auth.candidate.001"
    )
    result = execute_followup_provider_job_action(
        action,
        adapter_result_payload=payload or _official_candidate_payload(),
    )
    kernel.reduce(result.observation)
    return action, result


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


def _requirement(projection: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] == requirement_id:
            return requirement
    raise AssertionError(f"missing requirement {requirement_id}")


def _mutated_observation(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type=ObservationType.FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED,
        status=RunStageStatus.COMPLETED,
        payload={"followup_execution_state": state},
    )


def test_positive_offline_live_shaped_execution_commits_canonical_state() -> None:
    kernel = _authorized_kernel()

    action, _result = _execute_provider_job(kernel)

    state = kernel.state.followup_execution_state
    projection = kernel.state.followup_execution_projection
    assert action.stage == FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE
    assert state["owner"] == "RunKernel.FollowupProviderJobExecution"
    assert state["canonical_state"] is True
    assert state["execution_mode"] == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
    assert state["provider_job_kind"] == FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND
    assert state["authorized_query_ref"] == "query.ref.official.current"
    assert state["live_provider_call_executed"] is False
    assert state["search_executed"] is False
    assert state["retrieval_executed"] is False
    assert state["fetch_executed"] is False
    assert state["model_called"] is False
    assert state["provider_execution_licensed"] is False
    assert state["offline_live_shaped_execution"] is True
    assert state["adapter_result_injected"] is True
    assert state["live_validation_not_run"] is True
    assert state["author_activation_allowed"] is False
    assert state["author_executor_invoked"] is False
    assert state["citation_eligible"] is False
    assert state["citation_rendering_changed"] is False
    assert state["product_answer_behavior_changed"] is False
    assert projection["execution_mode"] == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
    assert kernel.state.followup_execution_history == [projection]


def test_offline_execution_continues_through_same_ledger_sufficiency_and_packet_path() -> None:
    kernel = _authorized_kernel()
    _execute_provider_job(kernel)
    ledger_object = kernel.state.evidence_ledger

    _intake_provider_job(kernel)
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    assert kernel.state.evidence_ledger is ledger_object
    assert ledger["candidate_count"] == 1
    candidate = ledger["candidate_records"][0]
    assert candidate["provider_name"] == "offline_official_current_adapter"
    assert candidate["provider_role"] == FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND
    assert candidate["query_ref"] == "query.ref.official.current"
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value
    assert kernel.state.followup_evidence_intake_state["evidence_ledger_intake_mode"] == (
        FOLLOWUP_PROVIDER_JOB_EVIDENCE_INTAKE_MODE
    )
    assert (
        kernel.state.followup_evidence_intake_state["ledger_followup_provider_job_intake"][
            "offline_live_shaped_execution"
        ]
        is True
    )

    _recheck(kernel)
    assert kernel.state.sufficiency_judgment_projection["owner"] == (
        "RunKernel.RunAuthoritySufficiencyJudgment"
    )
    assert kernel.state.sufficiency_judgment_projection["canonical_state"] is True
    assert kernel.state.sufficiency_judgment_projection["final_answer_allowed"] is False

    _packet(kernel)
    assert kernel.state.followup_final_answer_packet_state["owner"] == (
        "RunKernel.FollowupFinalAnswerPacket"
    )
    assert kernel.state.final_answer_packet["packet_id"]
    assert kernel.state.final_answer_authority_projection["owner"] == (
        "RunKernel.FinalAnswerPacket"
    )
    assert kernel.state.final_answer_authority_projection["author_activation_allowed"] is False


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("sealed_candidate_id", "auth.candidate.002", "sealed_candidate_id"),
        ("followup_authorization_consumption_id", "other-auth", "authorization"),
        ("provider_job_kind", "semantic_recall", "provider_job_kind"),
        ("component_id", "component-other", "component_id"),
        ("source_obligation_id", "obligation-other", "source_obligation_id"),
        ("requirement_ids", ["requirement-other"], "requirement_ids"),
        ("expected_source_classes", ["reputable_secondary"], "expected_source_classes"),
        ("authorized_query_ref", "query.ref.other", "authorized_query_ref"),
    ],
)
def test_provider_job_execution_binding_guard_rejects_mismatched_observation(
    field: str,
    value: Any,
    match: str,
) -> None:
    kernel = _authorized_kernel()
    action = kernel.authorize_followup_provider_job_execution(
        candidate_id="auth.candidate.001"
    )
    result = execute_followup_provider_job_action(
        action,
        adapter_result_payload=_official_candidate_payload(),
    )
    state = deepcopy(result.record.to_dict())
    state[field] = value

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(_mutated_observation(action, state))


def test_provider_job_execution_rejects_mismatched_action_id() -> None:
    kernel = _authorized_kernel()
    action = kernel.authorize_followup_provider_job_execution(
        candidate_id="auth.candidate.001"
    )
    result = execute_followup_provider_job_action(
        action,
        adapter_result_payload=_official_candidate_payload(),
    )
    bad = Observation(
        observation_id="bad-observation",
        run_id=kernel.state.run_id,
        action_id="missing-action-id",
        stage=action.stage,
        observation_type=ObservationType.FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED,
        status=RunStageStatus.COMPLETED,
        payload={"followup_execution_state": result.record.to_dict()},
        sequence=action.sequence,
    )

    with pytest.raises(RunKernelTransitionError, match="no matching issued action"):
        kernel.reduce(bad)


def test_caller_inputs_cannot_override_canonical_provider_job_authorization() -> None:
    kernel = _authorized_kernel()

    action = kernel.authorize_followup_provider_job_execution(
        candidate_id="auth.candidate.001",
        inputs={
            "sealed_candidate_id": "auth.candidate.999",
            "provider_job_kind": "semantic_recall",
            "component_id": "component-other",
            "source_obligation_id": "obligation-other",
            "requirement_ids": ["requirement-other"],
            "expected_source_classes": ["reputable_secondary"],
            "authorized_query_ref": "query.ref.malicious",
            "authorized_query": "malicious query",
            "budget_debit": {"provider_calls": 99},
            "provider_execution_licensed": True,
            "live_provider_call_executed": True,
            "search_executed": True,
            "retrieval_executed": True,
            "fetch_executed": True,
            "model_called": True,
            "author_activation_allowed": True,
            "citation_rendering_changed": True,
            "product_answer_behavior_changed": True,
            "live_validation_not_run": False,
            "caller_note": "preserved",
        },
    )

    assert action.inputs["sealed_candidate_id"] == "auth.candidate.001"
    assert action.inputs["provider_job_kind"] == FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND
    assert action.inputs["component_id"] == "component_rule"
    assert action.inputs["source_obligation_id"] == "obligation_official_current"
    assert action.inputs["requirement_ids"] == ["requirement_official_current"]
    assert action.inputs["expected_source_classes"] == [
        "official_government",
        "official_current_rules",
    ]
    assert action.inputs["authorized_query_ref"] == "query.ref.official.current"
    assert action.inputs["budget_debit"]["provider_calls"] == 1
    assert action.inputs["provider_execution_licensed"] is False
    assert action.inputs["live_provider_call_executed"] is False
    assert action.inputs["search_executed"] is False
    assert action.inputs["retrieval_executed"] is False
    assert action.inputs["fetch_executed"] is False
    assert action.inputs["model_called"] is False
    assert action.inputs["author_activation_allowed"] is False
    assert action.inputs["citation_rendering_changed"] is False
    assert action.inputs["product_answer_behavior_changed"] is False
    assert action.inputs["live_validation_not_run"] is True
    assert action.inputs["caller_note"] == "preserved"

    result = execute_followup_provider_job_action(
        action,
        adapter_result_payload=_official_candidate_payload(),
    )
    spoofed = deepcopy(result.record.to_dict())
    spoofed["budget_debit"] = {"provider_calls": 99}
    kernel.reduce(_mutated_observation(action, spoofed))
    assert kernel.state.followup_execution_state["budget_debit"]["provider_calls"] == 1


def test_query_ref_is_required_before_adapter_execution() -> None:
    kernel = _authorized_kernel(
        checkpoint=_checkpoint(provider_query_ref=None, provider_query=None)
    )
    adapter_called = False

    with pytest.raises(RunKernelTransitionError, match="authorized query/ref"):
        action = kernel.authorize_followup_provider_job_execution(
            candidate_id="auth.candidate.001"
        )
        adapter_called = True
        execute_followup_provider_job_action(
            action,
            adapter_result_payload=_official_candidate_payload(),
        )

    assert adapter_called is False


@pytest.mark.parametrize(
    "job_kind",
    [
        ProviderJobKind.LEGAL_CURRENT_PRIMARY_ACQUISITION.value,
        ProviderJobKind.CANONICAL_DOC_ACQUISITION.value,
        ProviderJobKind.SOURCE_BOUND_NUMERIC_EXTRACTION_CALCULATION_SUPPORT.value,
        ProviderJobKind.CONFLICT_CURRENTNESS_CHECK.value,
        ProviderJobKind.FETCH_READ_EXTRACT.value,
        ProviderJobKind.SEMANTIC_RECALL.value,
        ProviderJobKind.DIRECT_CANDIDATE_SEARCH.value,
        ProviderJobKind.SCOUT_DISAMBIGUATION.value,
        ProviderJobKind.BRIDGE_HINT_DISCOVERY.value,
        ProviderJobKind.PROVIDER_ANSWER_CONTEXT.value,
    ],
)
def test_provider_job_allowlist_rejects_all_other_job_kinds(job_kind: str) -> None:
    kernel = _authorized_kernel()
    kernel.state.followup_authorization_state["sealed_candidates"][0][
        "provider_job_kind"
    ] = job_kind

    with pytest.raises(RunKernelTransitionError, match="only authorizes"):
        kernel.authorize_followup_provider_job_execution(
            candidate_id="auth.candidate.001"
        )


@pytest.mark.parametrize(
    "budget_override",
    [
        {"provider_calls_remaining": 0},
        {"fetches_remaining": 0},
        {"read_units_remaining": 0},
        {"cost_points_remaining": 0},
        {"followup_rounds_remaining": 0},
    ],
)
def test_exhausted_budget_denies_authorization_without_adapter_invocation(
    budget_override: dict[str, int],
) -> None:
    kernel = _authorized_kernel(
        checkpoint=_checkpoint(budget_ledger=_budget(**budget_override))
    )
    adapter_called = False

    with pytest.raises(RunKernelTransitionError, match="not sealed"):
        action = kernel.authorize_followup_provider_job_execution(
            candidate_id="auth.candidate.001"
        )
        adapter_called = True
        execute_followup_provider_job_action(
            action,
            adapter_result_payload=_official_candidate_payload(),
        )

    assert kernel.state.followup_authorization_state["sealed_candidates"] == []
    assert adapter_called is False


@pytest.mark.parametrize(
    "payload",
    [
        {"source_tier": "secondary", "source_class": "reputable_secondary"},
        {"source_tier": "social_or_forum", "source_class": "social_or_forum"},
        {"source_class": "official_current_rules", "aggregate_only": True},
        {"source_class": "official_current_rules", "currentness_signal": "stale"},
        {"source_class": "official_current_rules", "readable_status": "unreadable"},
        {"wrong_source_class": True, "source_class": "reputable_secondary"},
        {"no_result": True},
        {"adapter_error": True, "adapter_error_code": "sanitized_error"},
    ],
)
def test_non_satisfying_provider_job_results_do_not_satisfy_official_current(
    payload: dict[str, Any],
) -> None:
    kernel = _authorized_kernel()
    _execute_provider_job(
        kernel,
        payload=_official_candidate_payload(**payload),
    )

    _intake_provider_job(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    custody = ledger["custody_records"][0]
    assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert custody["disposition"] in {"rejected", "contextual"}
    assert ledger["candidate_records"][0]["final_evidence_eligible"] is False
    assert kernel.state.followup_evidence_intake_state["final_evidence_satisfied"] is False
    assert kernel.state.followup_evidence_intake_state["citation_eligible"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_obligation_satisfied", True),
        ("final_evidence_satisfied", True),
        ("citation_eligible", True),
        ("sufficiency_ready", True),
        ("final_answer_packet_ready", True),
        ("author_activation_allowed", True),
        ("citation_rendering_changed", True),
        ("product_answer_behavior_changed", True),
        ("query_generation_changed", True),
        ("provider_routing_changed", True),
        ("live_validation_not_run", False),
        ("raw_text", "raw should never be retained"),
        ("raw_payload", {"placeholder": "blocked_test_value"}),
    ],
)
def test_observation_spoofing_is_rejected(field: str, value: Any) -> None:
    kernel = _authorized_kernel()
    action = kernel.authorize_followup_provider_job_execution(
        candidate_id="auth.candidate.001"
    )
    result = execute_followup_provider_job_action(
        action,
        adapter_result_payload=_official_candidate_payload(),
    )
    spoofed = deepcopy(result.record.to_dict())
    spoofed[field] = value

    with pytest.raises(RunKernelTransitionError):
        kernel.reduce(_mutated_observation(action, spoofed))


def test_static_closed_surface_guard_for_offline_provider_job_module() -> None:
    module_path = ROOT / "core" / "followup_provider_job_execution_runtime.py"
    source = module_path.read_text(encoding="utf-8")
    imports = _imports(module_path)
    forbidden_imports = {
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.pipeline_orchestrator",
        "core.source_class_recovery_executor",
        "subprocess",
        "os",
        "requests",
        "openai",
        "dotenv",
        "sqlite3",
    }
    assert imports.isdisjoint(forbidden_imports)
    for token in (
        "process_search_queries",
        "execute_recorded_retrieval_dispatch",
        "source_class_recovery",
        "AuthorExecutor",
        "format_citation",
        "FinalAnswerPacket",
        "SufficiencyJudgment",
        ".env",
        "raw_provider_payload",
    ):
        assert token not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "followup_provider_job_execution_runtime" not in pipeline_source
    assert "FOLLOWUP_PROVIDER_JOB_EXECUTE" not in pipeline_source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
