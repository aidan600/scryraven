from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from core.evidence_ledger import (
    CandidateCustodyKind,
    CandidateCustodyRecord,
    CandidateDisposition,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import (
    AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE,
    AG96I3Q1_CITATION_ELIGIBILITY_MODE,
    execute_followup_citation_eligibility_action,
    execute_followup_final_answer_packet_prepare_action,
)
from core.followup_sufficiency_recheck_runtime import (
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    evidence_ledger_projection_digest,
)
from core.run_kernel import (
    FOLLOWUP_CITATION_ELIGIBILITY_STAGE,
    Observation,
    RunKernel,
    RunKernelTransitionError,
)
from tests.test_ag96i3p1_final_evidence_selection import (
    OFFICIAL_CANDIDATE_ID,
    OFFICIAL_REQUIREMENT_ID,
    _add_secondary_candidate,
    _assert_no_sensitive_payload,
    _consume_p1,
    _execute_o2,
    _execute_p1,
    _kernel_through_o1,
    _kernel_through_o2,
    _kernel_through_p1,
    _resequence_action_and_observation,
    _stale_legacy_i2e_action,
)

ROOT = Path(__file__).resolve().parents[1]


def test_q1_happy_path_rebuilds_packet_local_citation_eligibility() -> None:
    kernel = _kernel_through_p1()
    p1_packet = deepcopy(kernel.state.final_answer_packet)
    p1_state = deepcopy(kernel.state.followup_final_evidence_selection_state)
    ledger_before = kernel.state.evidence_ledger.to_projection().to_dict()
    sufficiency_before = deepcopy(kernel.state.sufficiency_judgment_projection)

    action = kernel.authorize_followup_citation_eligibility()
    assert action.stage == FOLLOWUP_CITATION_ELIGIBILITY_STAGE
    assert action.inputs["citation_eligibility_mode"] == (
        AG96I3Q1_CITATION_ELIGIBILITY_MODE
    )
    assert action.inputs["final_evidence_selection_mode"] == (
        AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
    )
    assert action.inputs["evidence_ledger_intake_mode"] == (
        "ag96i3m2_admission_review_followup_intake"
    )
    assert action.inputs["sufficiency_recheck_mode"] == (
        FOLLOWUP_SUFFICIENCY_RECHECK_MODE
    )

    result = _execute_q1(kernel, action=action)
    kernel.reduce(result.observation)

    packet = kernel.state.final_answer_packet
    q1_state = kernel.state.followup_citation_eligibility_state
    projection = kernel.state.followup_citation_eligibility_projection
    assert q1_state["owner"] == "RunKernel.FollowupCitationEligibility"
    assert q1_state["canonical_state"] is True
    assert projection["owner"] == "RunKernel.FollowupCitationEligibility"
    assert projection["canonical_state"] is True
    assert packet["owner"] == "RunKernel.FinalAnswerPacket"
    assert packet["canonical_state"] is True
    assert packet != p1_packet
    assert packet["packet_id"] == p1_packet["packet_id"]
    assert packet["evidence_allowed"] == p1_packet["evidence_allowed"]
    assert packet["evidence_excluded"] == p1_packet["evidence_excluded"]
    assert packet["readiness_status"] == "blocked"
    assert packet["final_answer_allowed"] is False
    assert packet["answer_ready"] is False
    assert packet["final_evidence_selected"] is True
    assert packet["citation_eligibility_deferred"] is False
    assert packet["citation_rendering_deferred"] is True
    assert packet["citation_eligible_flag"] is True
    assert "ag96i3q1_citation_eligibility_created" in packet["readiness_reasons"]
    assert "citation_rendering_deferred" in packet["readiness_reasons"]
    assert "role_handoffs_closed" in packet["readiness_reasons"]
    assert "citation_eligibility_deferred" not in packet["readiness_reasons"]

    assert len(packet["citation_eligible"]) == 1
    assert packet["citation_ineligible"] == []
    citation = packet["citation_eligible"][0]
    assert citation["packet_local"] is True
    assert citation["status"] == "citation_eligible"
    assert citation["candidate_id"] == OFFICIAL_CANDIDATE_ID
    assert citation["source_id"] == OFFICIAL_CANDIDATE_ID
    assert citation["url"].startswith("https://www.irs.gov/")
    assert citation["requirement_id"] == OFFICIAL_REQUIREMENT_ID
    assert citation["source_obligation_id"] == action.inputs["source_obligation_id"]

    assert packet["author_input_refs"] == {}
    assert kernel.state.final_answer_authority_projection == {}
    assert "author_payload_ref" not in packet
    assert packet["author_payload_created"] is False
    assert packet["author_activation_allowed"] is False
    assert packet["author_execution_deferred"] is True
    assert packet["citations_rendered"] is False
    assert packet["citation_rendering_changed"] is False
    assert packet["citation_behavior_changed"] is False
    assert packet["citation_formatter_invoked"] is False
    assert "citation_eligible_source_ids" not in packet
    assert "citation_eligibility_refs" not in packet
    assert packet["analyst_activation_allowed"] is False
    assert packet["analyst_handoff_created"] is False
    assert packet["economist_activation_allowed"] is False
    assert packet["economist_handoff_created"] is False
    assert packet["economist_code_execution_allowed"] is False
    assert packet["prompt_behavior_changed"] is False
    assert packet["product_answer_behavior_changed"] is False
    assert packet["live_validation_not_run"] is True
    assert packet["not_role_consumption_payload"] is True

    lineage = packet["citation_eligibility_lineage"]
    assert lineage["citation_eligibility_id"] == q1_state["citation_eligibility_id"]
    assert lineage["final_evidence_selection_id"] == (
        p1_state["final_evidence_selection_id"]
    )
    assert lineage["final_evidence_selection_observation_id"] == (
        p1_state["observation_id"]
    )
    assert lineage["followup_final_evidence_selection_digest"] == (
        action.inputs["followup_final_evidence_selection_digest"]
    )
    assert lineage["blocked_final_answer_packet_shell_digest"] == (
        action.inputs["blocked_final_answer_packet_shell_digest"]
    )
    assert lineage["followup_final_answer_packet_readiness_digest"] == (
        action.inputs["followup_final_answer_packet_readiness_digest"]
    )
    assert lineage["followup_sufficiency_recheck_digest"] == (
        action.inputs["followup_sufficiency_recheck_digest"]
    )
    assert lineage["intake_id"] == action.inputs["intake_id"]
    assert lineage["execution_id"] == action.inputs["execution_id"]
    assert lineage["provider_job_kind"] == action.inputs["provider_job_kind"]
    assert lineage["component_id"] == action.inputs["component_id"]
    assert lineage["source_obligation_id"] == action.inputs["source_obligation_id"]
    assert lineage["requirement_ids"] == action.inputs["requirement_ids"]
    assert lineage["expected_source_classes"] == action.inputs[
        "expected_source_classes"
    ]
    assert lineage["current_final_answer_packet_digest_before_q1"] == (
        action.inputs["current_final_answer_packet_digest"]
    )
    assert packet["citation_eligibility_summary"] == q1_state[
        "citation_eligibility_summary"
    ]
    assert kernel.state.followup_citation_eligibility_history == [projection]
    assert kernel.state.projections[FOLLOWUP_CITATION_ELIGIBILITY_STAGE] == (
        projection
    )
    assert kernel.state.followup_final_evidence_selection_state == p1_state
    assert kernel.state.evidence_ledger.to_projection().to_dict() == ledger_before
    assert kernel.state.sufficiency_judgment_projection == sufficiency_before

    with pytest.raises(RunKernelTransitionError, match="reduced follow-up FinalAnswerPacket"):
        kernel.authorize_followup_author_gate()
    _assert_no_sensitive_payload(packet)
    _assert_no_sensitive_payload(q1_state)


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (
            lambda packet: packet["evidence_allowed"][0].pop("source_id"),
            "source_id_missing",
        ),
        (
            lambda packet: packet["evidence_allowed"][0].update({"url": ""}),
            "source_url_missing",
        ),
        (
            lambda packet: packet["evidence_allowed"][0].update(
                {"candidate_id": "missing_ledger_candidate"}
            ),
            "missing_ledger_candidate",
        ),
    ],
)
def test_q1_marks_selected_evidence_ineligible_for_missing_prerequisites(
    mutator: Any,
    reason: str,
) -> None:
    kernel = _kernel_through_p1()
    mutator(kernel.state.final_answer_packet)

    _consume_q1(kernel)

    packet = kernel.state.final_answer_packet
    assert packet["citation_eligible"] == []
    assert len(packet["citation_ineligible"]) == 1
    assert packet["citation_ineligible"][0]["status"] == "citation_ineligible"
    assert packet["citation_ineligible"][0]["reason"] == reason
    assert "citation_eligible_source_ids" not in packet
    assert "citation_eligibility_refs" not in packet
    _assert_no_sensitive_payload(packet["citation_ineligible"][0])


def test_q1_marks_selected_evidence_ineligible_when_custody_no_longer_backs_it() -> None:
    kernel = _kernel_through_p1()
    kernel.state.evidence_ledger.custody_records = [
        CandidateCustodyRecord(
            candidate_id=OFFICIAL_CANDIDATE_ID,
            record_kind=CandidateCustodyKind.FACT,
            disposition=CandidateDisposition.REJECTED,
            reason="test rejected custody",
            source="test",
            requirement_id=OFFICIAL_REQUIREMENT_ID,
            observation_id="ag96i3q1:test-rejected-custody",
        )
    ]

    _consume_q1(kernel)

    packet = kernel.state.final_answer_packet
    assert packet["citation_eligible"] == []
    assert packet["citation_ineligible"][0]["reason"] == (
        "missing_accepted_fact_custody_record"
    )


def test_q1_does_not_promote_non_selected_excluded_evidence() -> None:
    kernel = _kernel_through_o2(mutator=_add_secondary_candidate)
    _consume_p1(kernel)

    _consume_q1(kernel)

    packet = kernel.state.final_answer_packet
    assert [item["candidate_id"] for item in packet["evidence_allowed"]] == [
        OFFICIAL_CANDIDATE_ID
    ]
    assert [item["candidate_id"] for item in packet["evidence_excluded"]] == [
        "secondary_context_2026"
    ]
    assert [item["candidate_id"] for item in packet["citation_eligible"]] == [
        OFFICIAL_CANDIDATE_ID
    ]


def test_q1_authorization_binds_all_required_ids_modes_and_digests() -> None:
    kernel = _kernel_through_p1()
    action = kernel.authorize_followup_citation_eligibility()
    inputs = action.inputs
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()

    for field in (
        "citation_eligibility_id",
        "final_evidence_selection_id",
        "final_evidence_selection_observation_id",
        "followup_final_evidence_selection_digest",
        "blocked_final_answer_packet_shell_id",
        "blocked_final_answer_packet_shell_digest",
        "blocked_final_answer_packet_digest",
        "packet_preparation_readiness_id",
        "followup_final_answer_packet_readiness_digest",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "followup_sufficiency_recheck_digest",
        "followup_evidence_intake_id",
        "intake_id",
        "execution_id",
        "followup_execution_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "evidence_ledger_projection_digest",
        "sufficiency_judgment_digest",
        "current_final_answer_packet_digest",
    ):
        assert inputs[field] not in (None, "", [], {})
    assert inputs["requirement_ids"] == ["requirement_official_current"]
    assert inputs["expected_source_classes"] == [
        "official_government",
        "official_current_rules",
    ]
    assert inputs["citation_eligibility_mode"] == (
        AG96I3Q1_CITATION_ELIGIBILITY_MODE
    )
    assert inputs["evidence_ledger_projection_digest"] == (
        evidence_ledger_projection_digest(ledger)
    )


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("ledger", "EvidenceLedger digest mismatch"),
        ("sufficiency", "SufficiencyJudgment digest mismatch"),
        ("recheck", "recheck digest mismatch"),
        ("readiness", "readiness digest mismatch"),
        ("shell", "O2 shell digest mismatch"),
        ("p1", "P1 digest mismatch"),
        ("packet", "FinalAnswerPacket digest mismatch"),
    ],
)
def test_q1_reducer_rejects_stale_digests(mutation: str, match: str) -> None:
    kernel = _kernel_through_p1()
    action = kernel.authorize_followup_citation_eligibility()
    result = _execute_q1(kernel, action=action)
    if mutation == "ledger":
        kernel.state.evidence_ledger.observation_refs.append(
            {"observation_id": "ag96i3q1:stale-ledger", "source": "test"}
        )
    elif mutation == "sufficiency":
        kernel.state.sufficiency_judgment_projection["digest_mutation"] = "test"
    elif mutation == "recheck":
        kernel.state.followup_sufficiency_recheck_state["digest_mutation"] = "test"
    elif mutation == "readiness":
        kernel.state.followup_final_answer_packet_readiness_state[
            "digest_mutation"
        ] = "test"
    elif mutation == "shell":
        kernel.state.followup_blocked_final_answer_packet_shell_state[
            "digest_mutation"
        ] = "test"
    elif mutation == "p1":
        kernel.state.followup_final_evidence_selection_state[
            "digest_mutation"
        ] = "test"
    else:
        kernel.state.final_answer_packet["digest_mutation"] = "test"
    snapshot = _q1_state_snapshot(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)

    _assert_q1_snapshot_unchanged(kernel, snapshot)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("citation_eligibility_id", "mutated-eligibility"),
        ("final_evidence_selection_id", "mutated-selection"),
        ("final_evidence_selection_observation_id", "mutated-observation"),
        ("blocked_final_answer_packet_shell_id", "mutated-shell"),
        ("packet_preparation_readiness_id", "mutated-readiness"),
        ("recheck_id", "mutated-recheck"),
        ("intake_id", "mutated-intake"),
        ("execution_id", "mutated-execution"),
        ("sealed_candidate_id", "mutated-candidate"),
        ("requirement_ids", ["mutated-requirement"]),
        ("expected_source_classes", ["mutated-class"]),
        ("provider_job_kind", "mutated-provider"),
        ("component_id", "mutated-component"),
        ("source_obligation_id", "mutated-obligation"),
    ],
)
def test_q1_reducer_rejects_mutated_binding_fields(field: str, value: Any) -> None:
    kernel = _kernel_through_p1()
    action = kernel.authorize_followup_citation_eligibility()
    result = _execute_q1(kernel, action=action)
    bad_state = deepcopy(result.record.to_dict())
    bad_state[field] = value

    with pytest.raises(RunKernelTransitionError, match=field):
        kernel.reduce(_q1_observation_from_state(action, bad_state))

    assert kernel.state.followup_citation_eligibility_state == {}


def test_q1_reducer_rebuilds_packet_and_ignores_caller_citation_arrays() -> None:
    kernel = _kernel_through_p1()
    action = kernel.authorize_followup_citation_eligibility()
    result = _execute_q1(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["citation_eligible"] = [
        {
            "citation_id": "spoofed",
            "evidence_id": "spoofed",
            "status": "citation_eligible",
            "source_id": "spoofed",
            "packet_local": True,
        }
    ]
    spoofed["packet_projection"]["citation_eligible"] = spoofed[
        "citation_eligible"
    ]

    kernel.reduce(_q1_observation_from_state(action, spoofed))

    citation = kernel.state.final_answer_packet["citation_eligible"][0]
    assert citation["candidate_id"] == OFFICIAL_CANDIDATE_ID
    assert citation["source_id"] == OFFICIAL_CANDIDATE_ID
    assert citation["citation_id"] != "spoofed"


def test_q1_malformed_observation_rejects_before_bookkeeping_or_mutation() -> None:
    kernel = _kernel_through_p1()
    action = kernel.authorize_followup_citation_eligibility()
    snapshot = _q1_state_snapshot(kernel)
    bad_observation = Observation.from_action(
        action,
        observation_type="followup_citation_eligibility_prepared",
        status="completed",
        payload={},
    )

    with pytest.raises(RunKernelTransitionError, match="requires followup"):
        kernel.reduce(bad_observation)

    _assert_q1_snapshot_unchanged(kernel, snapshot)


def test_duplicate_q1_activation_for_same_p1_packet_rejects() -> None:
    kernel = _kernel_through_q1()

    with pytest.raises(RunKernelTransitionError, match="already activated"):
        kernel.authorize_followup_citation_eligibility()


def test_legacy_i2e_authorize_rejects_after_q1() -> None:
    kernel = _kernel_through_q1()

    with pytest.raises(RunKernelTransitionError, match="AG-96I3Q1"):
        kernel.authorize_followup_final_answer_packet_prepare()

    assert kernel.state.final_answer_authority_projection == {}


def test_stale_legacy_i2e_reduce_rejects_after_q1_without_state_change() -> None:
    kernel = _kernel_through_p1()
    legacy_kernel = _kernel_through_p1()
    legacy_action = _stale_legacy_i2e_action(legacy_kernel)
    legacy_result = execute_followup_final_answer_packet_prepare_action(
        legacy_action,
        followup_sufficiency_recheck_state=(
            legacy_kernel.state.followup_sufficiency_recheck_state
        ),
        sufficiency_judgment_projection=(
            legacy_kernel.state.sufficiency_judgment_projection
        ),
        evidence_ledger_projection=(
            legacy_kernel.state.evidence_ledger.to_projection().to_dict()
        ),
        followup_evidence_intake_state=(
            legacy_kernel.state.followup_evidence_intake_state
        ),
    )
    _consume_q1(kernel)
    _stale_action, stale_observation = _inject_external_stale_action_and_observation(
        kernel,
        legacy_kernel,
        legacy_action,
        legacy_result.observation,
    )
    snapshot = _q1_state_snapshot(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3Q1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    _assert_q1_snapshot_unchanged(kernel, snapshot)


def test_stale_o2_reduce_rejects_after_q1_without_state_change() -> None:
    kernel = _kernel_through_o1()
    stale_o2_action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    stale_o2_result = _execute_o2(kernel, action=stale_o2_action)
    kernel.reduce(stale_o2_result.observation)
    _consume_p1(kernel)
    _consume_q1(kernel)
    _stale_action, stale_observation = _resequence_action_and_observation(
        kernel,
        stale_o2_action,
        stale_o2_result.observation,
    )
    snapshot = _q1_state_snapshot(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3Q1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    _assert_q1_snapshot_unchanged(kernel, snapshot)


def test_stale_p1_reduce_rejects_after_q1_without_state_change() -> None:
    kernel = _kernel_through_o2()
    stale_p1_action = kernel.authorize_followup_final_evidence_selection()
    stale_p1_result = _execute_p1(kernel, action=stale_p1_action)
    kernel.reduce(stale_p1_result.observation)
    _consume_q1(kernel)
    _stale_action, stale_observation = _resequence_action_and_observation(
        kernel,
        stale_p1_action,
        stale_p1_result.observation,
    )
    snapshot = _q1_state_snapshot(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3Q1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    _assert_q1_snapshot_unchanged(kernel, snapshot)


def test_static_guards_keep_q1_closed_to_rendering_handoffs_roles_and_pipeline() -> None:
    runtime_path = ROOT / "core" / "followup_final_answer_packet_runtime.py"
    reducer_path = ROOT / "core" / "followup_runkernel_reducers.py"
    run_kernel_path = ROOT / "core" / "run_kernel.py"
    module_paths = [runtime_path, reducer_path, run_kernel_path]
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.prompts",
        "core.author_execution_runtime",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
        "subprocess",
        "os",
    }
    for path in module_paths:
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()
        assert _imports(path).isdisjoint(forbidden_imports)
        for forbidden in (
            "AuthorExecutor(",
            "AnalystExecutor",
            "EconomistExecutor",
            "execute_author_action",
            "execute_analyst",
            "execute_economist",
            "select_author_system_prompt",
            "format_citation",
            "render_citation",
        ):
            assert forbidden not in source

    runtime_source = runtime_path.read_text(encoding="utf-8")
    q1_builder = runtime_source.split(
        "def build_followup_citation_eligibility_record",
        1,
    )[1].split("def followup_projection_digest", 1)[0]
    assert "build_followup_final_answer_packet_record" not in q1_builder
    assert "build_final_answer_packet(" not in q1_builder
    assert "build_final_answer_authority_projection" not in q1_builder
    assert "build_citation_source_handoff_state" not in q1_builder
    assert "author_payload_ref" not in q1_builder
    assert "rendered_citation" not in q1_builder
    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3q1" not in pipeline_source.casefold()
    assert "followup_citation_eligibility" not in pipeline_source


def _execute_q1(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_citation_eligibility_action(
        action,
        followup_final_evidence_selection_state=(
            kernel.state.followup_final_evidence_selection_state
        ),
        final_answer_packet=kernel.state.final_answer_packet,
        followup_blocked_final_answer_packet_shell_state=(
            kernel.state.followup_blocked_final_answer_packet_shell_state
        ),
        followup_final_answer_packet_readiness_state=(
            kernel.state.followup_final_answer_packet_readiness_state
        ),
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )


def _consume_q1(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_citation_eligibility()
    result = _execute_q1(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _kernel_through_q1() -> RunKernel:
    kernel = _kernel_through_p1()
    _consume_q1(kernel)
    return kernel


def _q1_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_citation_eligibility_prepared",
        status="completed",
        payload={"followup_citation_eligibility_state": state},
    )


def _inject_external_stale_action_and_observation(
    kernel: RunKernel,
    source_kernel: RunKernel,
    action: Any,
    observation: Observation,
) -> tuple[Any, Observation]:
    sequence = kernel.state.next_observation_sequence
    action_id = f"{action.action_id}:stale:{sequence}"
    stale_action = replace(action, action_id=action_id, sequence=sequence)
    stale_observation = replace(
        observation,
        observation_id=f"{observation.observation_id}:stale:{sequence}",
        action_id=action_id,
        sequence=sequence,
    )
    kernel.state.issued_actions[action_id] = stale_action
    kernel.state.action_statuses[action_id] = source_kernel.state.action_statuses[
        action.action_id
    ]
    return stale_action, stale_observation


def _q1_state_snapshot(kernel: RunKernel) -> dict[str, Any]:
    return {
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "followup_citation_eligibility_state": deepcopy(
            kernel.state.followup_citation_eligibility_state
        ),
        "followup_citation_eligibility_projection": deepcopy(
            kernel.state.followup_citation_eligibility_projection
        ),
        "followup_citation_eligibility_history": deepcopy(
            kernel.state.followup_citation_eligibility_history
        ),
        "followup_final_evidence_selection_state": deepcopy(
            kernel.state.followup_final_evidence_selection_state
        ),
        "followup_final_answer_packet_state": deepcopy(
            kernel.state.followup_final_answer_packet_state
        ),
        "followup_blocked_final_answer_packet_shell_state": deepcopy(
            kernel.state.followup_blocked_final_answer_packet_shell_state
        ),
        "projections": deepcopy(kernel.state.projections),
        "action_statuses": deepcopy(kernel.state.action_statuses),
        "stage_statuses": deepcopy(kernel.state.stage_statuses),
        "reduced_action_ids": deepcopy(kernel.state.reduced_action_ids),
        "observations": deepcopy(kernel.state.observations),
        "next_observation_sequence": kernel.state.next_observation_sequence,
    }


def _assert_q1_snapshot_unchanged(
    kernel: RunKernel,
    snapshot: dict[str, Any],
) -> None:
    assert kernel.state.final_answer_packet == snapshot["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == snapshot[
        "final_answer_authority_projection"
    ]
    assert kernel.state.followup_citation_eligibility_state == snapshot[
        "followup_citation_eligibility_state"
    ]
    assert kernel.state.followup_citation_eligibility_projection == snapshot[
        "followup_citation_eligibility_projection"
    ]
    assert kernel.state.followup_citation_eligibility_history == snapshot[
        "followup_citation_eligibility_history"
    ]
    assert kernel.state.followup_final_evidence_selection_state == snapshot[
        "followup_final_evidence_selection_state"
    ]
    assert kernel.state.followup_final_answer_packet_state == snapshot[
        "followup_final_answer_packet_state"
    ]
    assert kernel.state.followup_blocked_final_answer_packet_shell_state == snapshot[
        "followup_blocked_final_answer_packet_shell_state"
    ]
    assert kernel.state.projections == snapshot["projections"]
    assert kernel.state.action_statuses == snapshot["action_statuses"]
    assert kernel.state.stage_statuses == snapshot["stage_statuses"]
    assert kernel.state.reduced_action_ids == snapshot["reduced_action_ids"]
    assert kernel.state.observations == snapshot["observations"]
    assert kernel.state.next_observation_sequence == snapshot[
        "next_observation_sequence"
    ]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
