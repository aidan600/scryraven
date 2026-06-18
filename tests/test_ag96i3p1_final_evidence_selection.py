from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from core.evidence_ledger import (
    CandidateCustodyKind,
    CandidateCustodyRecord,
    CandidateDisposition,
    EvidenceCandidate,
    SourceObligationLink,
    SourceRequirementStatus,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import (
    AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE,
    AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE,
    AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE,
    execute_followup_blocked_final_answer_packet_shell_action,
    execute_followup_final_answer_packet_prepare_action,
    execute_followup_final_answer_packet_readiness_action,
    execute_followup_final_evidence_selection_action,
)
from core.followup_sufficiency_recheck_runtime import (
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    evidence_ledger_projection_digest,
    execute_followup_sufficiency_recheck_action,
)
from core.run_kernel import (
    FOLLOWUP_FINAL_EVIDENCE_SELECTION_STAGE,
    Observation,
    RunKernel,
    RunKernelTransitionError,
)
from tests.ag96_static_guards import imported_modules
from tests.ag96i3_assertions import (
    assert_no_sensitive_payload,
    assert_p1_boundary_snapshot_unchanged,
    snapshot_p1_boundary_state,
)
from tests.helpers.followup_fixture_spine import run_followup_through_execution
from tests.test_ag96i3m2_followup_evidence_intake_activation import (
    _execute_m2_intake,
)

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "ag96i3p1-final-evidence-selection"
OFFICIAL_CANDIDATE_ID = "irs_current_rules_2026"
OFFICIAL_REQUIREMENT_ID = "source_requirement:requirement_official_current"


def test_p1_happy_path_mutates_o2_shell_to_evidence_selected_blocked_packet() -> None:
    kernel = _kernel_through_o2()
    o1_before = deepcopy(kernel.state.followup_final_answer_packet_readiness_state)
    o2_before = deepcopy(kernel.state.followup_blocked_final_answer_packet_shell_state)
    o2_projection_before = deepcopy(
        kernel.state.followup_blocked_final_answer_packet_shell_projection
    )
    ledger_before = kernel.state.evidence_ledger.to_projection().to_dict()
    sufficiency_before = deepcopy(kernel.state.sufficiency_judgment_projection)
    recheck_before = deepcopy(kernel.state.followup_sufficiency_recheck_state)
    blocked_packet_before = deepcopy(kernel.state.final_answer_packet)

    assert blocked_packet_before["evidence_allowed"] == []
    assert blocked_packet_before["final_evidence_selection_deferred"] is True

    action = kernel.authorize_followup_final_evidence_selection()
    assert action.stage == FOLLOWUP_FINAL_EVIDENCE_SELECTION_STAGE
    assert action.inputs["final_evidence_selection_mode"] == (
        AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
    )
    assert action.inputs["blocked_final_answer_packet_mode"] == (
        AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
    )
    assert action.inputs["packet_preparation_readiness_mode"] == (
        AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
    )
    assert action.inputs["evidence_ledger_intake_mode"] == (
        "ag96i3m2_admission_review_followup_intake"
    )
    assert action.inputs["sufficiency_recheck_mode"] == (
        FOLLOWUP_SUFFICIENCY_RECHECK_MODE
    )

    result = _execute_p1(kernel, action=action)
    kernel.reduce(result.observation)

    packet = kernel.state.final_answer_packet
    selection = kernel.state.followup_final_evidence_selection_state
    projection = kernel.state.followup_final_evidence_selection_projection
    selected = packet["evidence_allowed"]
    assert selection["owner"] == "RunKernel.FollowupFinalEvidenceSelection"
    assert selection["canonical_state"] is True
    assert projection["owner"] == "RunKernel.FollowupFinalEvidenceSelection"
    assert projection["canonical_state"] is True
    assert packet["owner"] == "RunKernel.FinalAnswerPacket"
    assert packet["canonical_state"] is True
    assert packet["packet_id"] == blocked_packet_before["packet_id"]
    assert packet != blocked_packet_before
    assert packet["readiness_status"] == "blocked"
    assert packet["final_answer_allowed"] is False
    assert packet["answer_ready"] is False
    assert packet["final_evidence_selected"] is True
    assert packet["final_evidence_selection_deferred"] is False
    assert packet["citation_eligibility_deferred"] is True
    assert packet["citation_eligible"] == []
    assert packet["citation_ineligible"] == []
    assert "citation_eligible_source_ids" not in packet
    assert "citation_eligibility_refs" not in packet
    assert packet["citations_rendered"] is False
    assert packet["citation_rendering_changed"] is False
    assert packet["citation_formatter_invoked"] is False
    assert packet["author_input_refs"] == {}
    assert "author_payload_ref" not in packet
    assert packet["author_payload_created"] is False
    assert packet["author_activation_allowed"] is False
    assert packet["author_execution_deferred"] is True
    assert packet["analyst_activation_allowed"] is False
    assert packet["analyst_handoff_created"] is False
    assert packet["economist_activation_allowed"] is False
    assert packet["economist_handoff_created"] is False
    assert packet["economist_code_execution_allowed"] is False
    assert packet["prompt_behavior_changed"] is False
    assert packet["product_answer_behavior_changed"] is False
    assert packet["live_validation_not_run"] is True
    assert packet["not_role_consumption_payload"] is True
    assert "ag96i3p1_final_evidence_selected" in packet["readiness_reasons"]
    assert "citation_eligibility_deferred" in packet["readiness_reasons"]
    assert "role_handoffs_closed" in packet["readiness_reasons"]

    assert len(selected) == 1
    evidence = selected[0]
    assert evidence == packet["selected_final_evidence_refs"][0]
    assert evidence["candidate_id"] == OFFICIAL_CANDIDATE_ID
    assert evidence["source_id"] == OFFICIAL_CANDIDATE_ID
    assert evidence["requirement_id"] == OFFICIAL_REQUIREMENT_ID
    assert evidence["source_class"] == "official_current_rules"
    assert evidence["source_tier"] == "official"
    assert evidence["status"] == "evidence_allowed"
    assert evidence["reason"] == (
        "ag96i3p1_selected_from_accepted_satisfied_evidence_ledger_custody"
    )
    assert_no_sensitive_payload(packet)
    assert_no_sensitive_payload(selection)

    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.followup_final_answer_packet_state == {}
    assert kernel.state.followup_author_gate_state == {}
    assert kernel.state.followup_author_observation_state == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert kernel.state.followup_final_answer_packet_readiness_state == o1_before
    assert kernel.state.followup_blocked_final_answer_packet_shell_state == o2_before
    assert kernel.state.followup_blocked_final_answer_packet_shell_projection == (
        o2_projection_before
    )
    assert kernel.state.evidence_ledger.to_projection().to_dict() == ledger_before
    assert kernel.state.sufficiency_judgment_projection == sufficiency_before
    assert kernel.state.followup_sufficiency_recheck_state == recheck_before
    assert kernel.state.projections[FOLLOWUP_FINAL_EVIDENCE_SELECTION_STAGE] == (
        projection
    )
    assert kernel.state.followup_final_evidence_selection_history == [projection]


def test_p1_selects_only_expected_official_candidate_and_excludes_secondary() -> None:
    kernel = _kernel_through_o2(mutator=_add_secondary_candidate)

    action = kernel.authorize_followup_final_evidence_selection()
    result = _execute_p1(kernel, action=action)
    kernel.reduce(result.observation)

    packet = kernel.state.final_answer_packet
    assert [item["candidate_id"] for item in packet["evidence_allowed"]] == [
        OFFICIAL_CANDIDATE_ID
    ]
    assert [item["candidate_id"] for item in packet["evidence_excluded"]] == [
        "secondary_context_2026"
    ]
    rejected = packet["evidence_excluded"][0]
    assert rejected["status"] == "evidence_excluded"
    assert rejected["reason"] == "source_class_outside_expected_source_classes"
    assert rejected["source_class"] == "reputable_secondary"
    assert packet["citation_eligible"] == []
    assert packet["citation_ineligible"] == []
    assert "citation_eligible_source_ids" not in packet
    assert "citation_eligibility_refs" not in packet
    assert_no_sensitive_payload(rejected)


def test_p1_excludes_stale_sibling_linked_to_satisfied_requirement() -> None:
    kernel = _kernel_through_o2(mutator=_add_stale_official_sibling_candidate)

    action = kernel.authorize_followup_final_evidence_selection()
    result = _execute_p1(kernel, action=action)
    kernel.reduce(result.observation)

    packet = kernel.state.final_answer_packet
    assert [item["candidate_id"] for item in packet["evidence_allowed"]] == [
        OFFICIAL_CANDIDATE_ID
    ]
    assert [item["candidate_id"] for item in packet["evidence_excluded"]] == [
        "stale_official_rules_2025"
    ]
    rejected = packet["evidence_excluded"][0]
    assert rejected["status"] == "evidence_excluded"
    assert rejected["source_class"] == "official_current_rules"
    assert rejected["source_tier"] == "official"
    assert rejected["currentness_signal"] == "stale"
    assert rejected["reason"] == "stale_currentness"
    assert packet["citation_eligible"] == []
    assert packet["citation_ineligible"] == []
    assert kernel.state.final_answer_authority_projection == {}
    assert packet["author_input_refs"] == {}
    assert "author_payload_ref" not in packet
    with pytest.raises(RunKernelTransitionError, match="reduced follow-up FinalAnswerPacket"):
        kernel.authorize_followup_author_gate()


@pytest.mark.parametrize(
    ("mutator_name", "label"),
    [
        ("unsatisfied_requirement", "unsatisfied"),
        ("rejected_custody", "rejected custody"),
        ("wrong_source_class", "wrong source class"),
        ("contextual_only", "contextual-only"),
        ("unreadable", "unreadable"),
        ("rejected_candidate_fact", "rejected disposition"),
    ],
)
def test_p1_does_not_select_noneligible_canonical_ledger_candidates(
    mutator_name: str,
    label: str,
) -> None:
    mutators = {
        "unsatisfied_requirement": lambda kernel: _set_requirement_status(
            kernel,
            SourceRequirementStatus.UNSATISFIED,
        ),
        "rejected_custody": _replace_custody_with_rejected_record,
        "wrong_source_class": _set_wrong_source_class,
        "contextual_only": _set_contextual_only,
        "unreadable": _set_unreadable,
        "rejected_candidate_fact": _set_rejected_candidate_fact,
    }
    mutator = mutators[mutator_name]
    kernel = _kernel_through_o2(mutator=mutator)
    action = kernel.authorize_followup_final_evidence_selection()
    snapshot = snapshot_p1_boundary_state(kernel)

    with pytest.raises(PermissionError, match="accepted satisfied EvidenceLedger custody"):
        _execute_p1(kernel, action=action)

    assert label
    assert_p1_boundary_snapshot_unchanged(kernel, snapshot)
    assert kernel.state.final_answer_packet["evidence_allowed"] == []
    assert kernel.state.final_answer_packet["final_evidence_selected"] is False


def test_p1_reduce_rejects_no_qualifying_candidate_before_bookkeeping() -> None:
    kernel = _kernel_through_o2(mutator=_set_unreadable)
    action = kernel.authorize_followup_final_evidence_selection()
    snapshot = snapshot_p1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="accepted satisfied EvidenceLedger custody"):
        kernel.reduce(_minimal_p1_observation(action))

    assert_p1_boundary_snapshot_unchanged(kernel, snapshot)
    assert kernel.state.final_answer_packet["evidence_allowed"] == []
    assert kernel.state.final_answer_packet["final_evidence_selected"] is False
    assert kernel.state.final_answer_authority_projection == {}


def test_p1_citation_and_role_surfaces_remain_closed() -> None:
    kernel = _kernel_through_p1()
    packet = kernel.state.final_answer_packet

    assert packet["citation_eligible"] == []
    assert packet["citation_ineligible"] == []
    assert "citation_eligible_source_ids" not in packet
    assert "citation_eligibility_refs" not in packet
    assert packet["citations_rendered"] is False
    assert packet["citation_rendering_changed"] is False
    assert packet["citation_behavior_changed"] is False
    assert packet["citation_formatter_invoked"] is False
    assert packet["author_input_refs"] == {}
    assert "author_payload_ref" not in packet
    assert packet["author_payload_created"] is False
    assert kernel.state.final_answer_authority_projection == {}
    with pytest.raises(RunKernelTransitionError, match="reduced follow-up FinalAnswerPacket"):
        kernel.authorize_followup_author_gate()
    assert kernel.state.followup_author_gate_state == {}
    assert kernel.state.followup_author_observation_state == {}
    assert packet["analyst_activation_allowed"] is False
    assert packet["analyst_handoff_created"] is False
    assert packet["economist_activation_allowed"] is False
    assert packet["economist_handoff_created"] is False
    assert packet["economist_code_execution_allowed"] is False


def test_p1_authorization_binds_all_required_identity_mode_and_digest_fields() -> None:
    kernel = _kernel_through_o2()
    action = kernel.authorize_followup_final_evidence_selection()
    inputs = action.inputs
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()

    for field in (
        "final_evidence_selection_id",
        "blocked_final_answer_packet_shell_id",
        "blocked_final_answer_packet_shell_observation_id",
        "blocked_final_answer_packet_shell_digest",
        "blocked_final_answer_packet_digest",
        "packet_preparation_readiness_id",
        "readiness_observation_id",
        "followup_final_answer_packet_readiness_digest",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "followup_sufficiency_recheck_observation_id",
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
    ):
        assert inputs[field] not in (None, "", [], {})
    assert inputs["requirement_ids"] == ["requirement_official_current"]
    assert inputs["expected_source_classes"] == [
        "official_government",
        "official_current_rules",
    ]
    assert inputs["evidence_ledger_intake_mode"] == (
        "ag96i3m2_admission_review_followup_intake"
    )
    assert inputs["sufficiency_recheck_mode"] == (
        FOLLOWUP_SUFFICIENCY_RECHECK_MODE
    )
    assert inputs["blocked_final_answer_packet_mode"] == (
        AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
    )
    assert inputs["final_evidence_selection_mode"] == (
        AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
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
        ("packet", "O2 packet digest mismatch"),
    ],
)
def test_p1_reducer_rejects_stale_digests(mutation: str, match: str) -> None:
    kernel = _kernel_through_o2()
    action = kernel.authorize_followup_final_evidence_selection()
    result = _execute_p1(kernel, action=action)
    snapshot = snapshot_p1_boundary_state(kernel)
    if mutation == "ledger":
        kernel.state.evidence_ledger.observation_refs.append(
            {"observation_id": "ag96i3p1:stale-ledger", "source": "test"}
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
    else:
        kernel.state.final_answer_packet["digest_mutation"] = "test"

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)

    assert kernel.state.followup_final_evidence_selection_state == {}
    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.reduced_action_ids == snapshot["reduced_action_ids"]
    assert kernel.state.observations == snapshot["observations"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("final_evidence_selection_id", "mutated-selection"),
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
def test_p1_reducer_rejects_mutated_binding_fields(field: str, value: Any) -> None:
    kernel = _kernel_through_o2()
    action = kernel.authorize_followup_final_evidence_selection()
    result = _execute_p1(kernel, action=action)
    bad_state = deepcopy(result.record.to_dict())
    bad_state[field] = value

    with pytest.raises(RunKernelTransitionError, match=field):
        kernel.reduce(_p1_observation_from_state(action, bad_state))

    assert kernel.state.followup_final_evidence_selection_state == {}


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (
            lambda kernel: kernel.state.followup_blocked_final_answer_packet_shell_state.update(
                {"canonical_state": False}
            ),
            "canonical O2 shell",
        ),
        (
            lambda kernel: kernel.state.followup_final_answer_packet_readiness_state.update(
                {"canonical_state": False}
            ),
            "canonical O1 readiness",
        ),
        (
            lambda kernel: kernel.state.sufficiency_judgment_projection.update(
                {"canonical_state": False}
            ),
            "canonical SufficiencyJudgment",
        ),
        (
            lambda kernel: kernel.state.followup_sufficiency_recheck_state.update(
                {"canonical_state": False}
            ),
            "canonical AG-96I3N recheck",
        ),
    ],
)
def test_p1_authorization_rejects_missing_or_noncanonical_prerequisites(
    mutator: Any,
    match: str,
) -> None:
    kernel = _kernel_through_o2()
    mutator(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.authorize_followup_final_evidence_selection()


def test_p1_runtime_rejects_missing_or_noncanonical_ledger_projection() -> None:
    kernel = _kernel_through_o2()
    action = kernel.authorize_followup_final_evidence_selection()

    with pytest.raises(PermissionError, match="EvidenceLedger owner"):
        execute_followup_final_evidence_selection_action(
            action,
            followup_blocked_final_answer_packet_shell_state=(
                kernel.state.followup_blocked_final_answer_packet_shell_state
            ),
            final_answer_packet=kernel.state.final_answer_packet,
            followup_final_answer_packet_readiness_state=(
                kernel.state.followup_final_answer_packet_readiness_state
            ),
            followup_sufficiency_recheck_state=(
                kernel.state.followup_sufficiency_recheck_state
            ),
            sufficiency_judgment_projection=(
                kernel.state.sufficiency_judgment_projection
            ),
            evidence_ledger_projection={},
            followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        )


def test_p1_reducer_rebuilds_packet_and_ignores_caller_projection_override() -> None:
    kernel = _kernel_through_o2()
    action = kernel.authorize_followup_final_evidence_selection()
    result = _execute_p1(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["packet_projection"]["evidence_allowed"][0]["candidate_id"] = "spoofed"
    spoofed["packet_projection"]["evidence_allowed"][0]["url"] = "https://bad.test"

    kernel.reduce(_p1_observation_from_state(action, spoofed))

    selected = kernel.state.final_answer_packet["evidence_allowed"]
    assert selected[0]["candidate_id"] == OFFICIAL_CANDIDATE_ID
    assert selected[0]["url"].startswith("https://www.irs.gov/")


def test_p1_malformed_observation_rejects_before_bookkeeping_or_mutation() -> None:
    kernel = _kernel_through_o2()
    action = kernel.authorize_followup_final_evidence_selection()
    snapshot = snapshot_p1_boundary_state(kernel)
    bad_observation = Observation.from_action(
        action,
        observation_type="followup_final_evidence_selection_prepared",
        status="completed",
        payload={},
    )

    with pytest.raises(RunKernelTransitionError, match="requires followup"):
        kernel.reduce(bad_observation)

    assert_p1_boundary_snapshot_unchanged(kernel, snapshot)


def test_duplicate_p1_activation_for_same_o2_shell_rejects() -> None:
    kernel = _kernel_through_p1()

    with pytest.raises(RunKernelTransitionError, match="already activated"):
        kernel.authorize_followup_final_evidence_selection()


def test_legacy_i2e_authorize_rejects_after_p1() -> None:
    kernel = _kernel_through_p1()

    with pytest.raises(RunKernelTransitionError, match="AG-96I3P1"):
        kernel.authorize_followup_final_answer_packet_prepare()

    assert kernel.state.final_answer_authority_projection == {}


def test_stale_legacy_i2e_reduce_rejects_after_p1_without_state_change() -> None:
    kernel = _kernel_through_p1()
    legacy_action = _stale_legacy_i2e_action(kernel)
    legacy_result = execute_followup_final_answer_packet_prepare_action(
        legacy_action,
        followup_sufficiency_recheck_state=(
            kernel.state.followup_sufficiency_recheck_state
        ),
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )
    snapshot = snapshot_p1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3P1"):
        kernel.reduce(legacy_result.observation)

    assert_p1_boundary_snapshot_unchanged(kernel, snapshot)


def test_stale_o2_reduce_rejects_after_p1_without_state_change() -> None:
    kernel = _kernel_through_o1()
    stale_o2_action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    stale_o2_result = _execute_o2(kernel, action=stale_o2_action)
    kernel.reduce(stale_o2_result.observation)
    _consume_p1(kernel)
    _stale_action, stale_observation = _resequence_action_and_observation(
        kernel,
        stale_o2_action,
        stale_o2_result.observation,
    )
    snapshot = snapshot_p1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="stale AG-96I3O2"):
        kernel.reduce(stale_observation)

    assert_p1_boundary_snapshot_unchanged(kernel, snapshot)


def test_static_guards_keep_p1_closed_to_live_roles_citations_and_legacy_builder() -> None:
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
        assert imported_modules(path).isdisjoint(forbidden_imports)
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
    p1_builder = runtime_source.split(
        "def build_followup_final_evidence_selection_record",
        1,
    )[1].split("def followup_projection_digest", 1)[0]
    assert "_eligible_final_evidence_refs" not in p1_builder
    assert "build_followup_final_answer_packet_record" not in p1_builder
    assert "build_final_answer_authority_projection" not in p1_builder
    assert "author_payload_ref" not in p1_builder
    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3p1" not in pipeline_source.casefold()
    assert "followup_final_evidence_selection" not in pipeline_source


def _kernel_through_p1() -> RunKernel:
    kernel = _kernel_through_o2()
    _consume_p1(kernel)
    return kernel


def _kernel_through_o2(*, mutator: Any | None = None) -> RunKernel:
    kernel = _kernel_through_o1(mutator=mutator)
    _consume_o2(kernel)
    return kernel


def _kernel_through_o1(*, mutator: Any | None = None) -> RunKernel:
    kernel = run_followup_through_execution(run_id=RUN_ID)
    _execute_m2_intake(kernel)
    if mutator is not None:
        mutator(kernel)
    recheck_action = kernel.authorize_followup_sufficiency_recheck()
    recheck_result = execute_followup_sufficiency_recheck_action(
        recheck_action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        prior_sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        sufficiency_handoff=kernel.state.followup_authorization_state.get(
            "sufficiency_handoff",
            {},
        ),
    )
    kernel.reduce(recheck_result.observation)
    readiness_action = kernel.authorize_followup_final_answer_packet_readiness()
    readiness_result = execute_followup_final_answer_packet_readiness_action(
        readiness_action,
        followup_sufficiency_recheck_state=(
            kernel.state.followup_sufficiency_recheck_state
        ),
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )
    kernel.reduce(readiness_result.observation)
    return kernel


def _execute_o2(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_blocked_final_answer_packet_shell_action(
        action,
        followup_final_answer_packet_readiness_state=(
            kernel.state.followup_final_answer_packet_readiness_state
        ),
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )


def _consume_o2(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _execute_p1(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_final_evidence_selection_action(
        action,
        followup_blocked_final_answer_packet_shell_state=(
            kernel.state.followup_blocked_final_answer_packet_shell_state
        ),
        final_answer_packet=kernel.state.final_answer_packet,
        followup_final_answer_packet_readiness_state=(
            kernel.state.followup_final_answer_packet_readiness_state
        ),
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )


def _consume_p1(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_final_evidence_selection()
    result = _execute_p1(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _p1_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_final_evidence_selection_prepared",
        status="completed",
        payload={"followup_final_evidence_selection_state": state},
    )


def _minimal_p1_observation(action: Any) -> Observation:
    state = {
        **dict(action.inputs),
        "observation_id": f"{action.action_id}:minimal-observation",
        "final_evidence_selected": True,
        "final_answer_allowed": False,
        "answer_ready": False,
        "citation_eligible": [],
        "citation_ineligible": [],
        "citations_rendered": False,
        "citation_rendering_changed": False,
        "citation_behavior_changed": False,
        "citation_formatter_invoked": False,
        "author_activation_allowed": False,
        "author_payload_created": False,
        "author_execution_deferred": True,
        "analyst_activation_allowed": False,
        "analyst_handoff_created": False,
        "economist_activation_allowed": False,
        "economist_handoff_created": False,
        "economist_code_execution_allowed": False,
        "prompt_behavior_changed": False,
        "product_answer_behavior_changed": False,
        "live_validation_not_run": True,
        "citation_eligibility_deferred": True,
        "not_role_consumption_payload": True,
        "author_input_refs": {},
    }
    return _p1_observation_from_state(action, state)


def _stale_legacy_i2e_action(kernel: RunKernel) -> Any:
    shell = deepcopy(kernel.state.followup_blocked_final_answer_packet_shell_state)
    shell_projection = deepcopy(
        kernel.state.followup_blocked_final_answer_packet_shell_projection
    )
    shell_history = deepcopy(
        kernel.state.followup_blocked_final_answer_packet_shell_history
    )
    selection_state = deepcopy(kernel.state.followup_final_evidence_selection_state)
    selection_projection = deepcopy(
        kernel.state.followup_final_evidence_selection_projection
    )
    selection_history = deepcopy(
        kernel.state.followup_final_evidence_selection_history
    )
    packet = deepcopy(kernel.state.final_answer_packet)
    kernel.state.followup_blocked_final_answer_packet_shell_state = {}
    kernel.state.followup_blocked_final_answer_packet_shell_projection = {}
    kernel.state.followup_blocked_final_answer_packet_shell_history = []
    kernel.state.followup_final_evidence_selection_state = {}
    kernel.state.followup_final_evidence_selection_projection = {}
    kernel.state.followup_final_evidence_selection_history = []
    kernel.state.final_answer_packet = {}
    action = kernel.authorize_followup_final_answer_packet_prepare()
    kernel.state.followup_blocked_final_answer_packet_shell_state = shell
    kernel.state.followup_blocked_final_answer_packet_shell_projection = shell_projection
    kernel.state.followup_blocked_final_answer_packet_shell_history = shell_history
    kernel.state.followup_final_evidence_selection_state = selection_state
    kernel.state.followup_final_evidence_selection_projection = selection_projection
    kernel.state.followup_final_evidence_selection_history = selection_history
    kernel.state.final_answer_packet = packet
    return action


def _resequence_action_and_observation(
    kernel: RunKernel,
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
    kernel.state.action_statuses[action_id] = kernel.state.action_statuses[
        action.action_id
    ]
    return stale_action, stale_observation


def _set_requirement_status(
    kernel: RunKernel,
    status: SourceRequirementStatus,
) -> None:
    kernel.state.evidence_ledger.requirements[OFFICIAL_REQUIREMENT_ID].status = status


def _replace_custody_with_rejected_record(kernel: RunKernel) -> None:
    kernel.state.evidence_ledger.custody_records = [
        CandidateCustodyRecord(
            candidate_id=OFFICIAL_CANDIDATE_ID,
            record_kind=CandidateCustodyKind.FACT,
            disposition=CandidateDisposition.REJECTED,
            reason="test rejected custody",
            source="test",
            requirement_id=OFFICIAL_REQUIREMENT_ID,
            observation_id="ag96i3p1:test-rejected-custody",
        )
    ]


def _set_wrong_source_class(kernel: RunKernel) -> None:
    candidate = kernel.state.evidence_ledger.candidates[OFFICIAL_CANDIDATE_ID]
    candidate.source_class = "reputable_secondary"
    candidate.source_tier = "secondary"


def _set_contextual_only(kernel: RunKernel) -> None:
    candidate = kernel.state.evidence_ledger.candidates[OFFICIAL_CANDIDATE_ID]
    candidate.contextual_only = True


def _set_unreadable(kernel: RunKernel) -> None:
    candidate = kernel.state.evidence_ledger.candidates[OFFICIAL_CANDIDATE_ID]
    candidate.readable_status = "unreadable"


def _set_rejected_candidate_fact(kernel: RunKernel) -> None:
    candidate = kernel.state.evidence_ledger.candidates[OFFICIAL_CANDIDATE_ID]
    candidate.fact_disposition = CandidateDisposition.REJECTED


def _add_secondary_candidate(kernel: RunKernel) -> None:
    candidate_id = "secondary_context_2026"
    kernel.state.evidence_ledger.candidates[candidate_id] = EvidenceCandidate(
        candidate_id=candidate_id,
        url="https://example.com/secondary-context",
        title="Secondary context",
        domain="example.com",
        source_tier="secondary",
        source_class="reputable_secondary",
        currentness_signal="current",
        readable_status="readable",
        fetchable_status="fetched",
        fact_disposition=CandidateDisposition.ACCEPTED,
        contextual_only=False,
        lower_tier=False,
        final_evidence_eligible=False,
    )
    kernel.state.evidence_ledger.custody_records.append(
        CandidateCustodyRecord(
            candidate_id=candidate_id,
            record_kind=CandidateCustodyKind.FACT,
            disposition=CandidateDisposition.ACCEPTED,
            reason="test secondary candidate",
            source="test",
            requirement_id=OFFICIAL_REQUIREMENT_ID,
            observation_id="ag96i3p1:test-secondary",
        )
    )
    requirement = kernel.state.evidence_ledger.requirements[OFFICIAL_REQUIREMENT_ID]
    if candidate_id not in requirement.linked_candidate_ids:
        requirement.linked_candidate_ids.append(candidate_id)
    kernel.state.evidence_ledger.links.append(
        SourceObligationLink(
            requirement_id=OFFICIAL_REQUIREMENT_ID,
            candidate_id=candidate_id,
            link_reason="test_secondary_candidate",
            link_status="accepted",
        )
    )


def _add_stale_official_sibling_candidate(kernel: RunKernel) -> None:
    candidate_id = "stale_official_rules_2025"
    kernel.state.evidence_ledger.candidates[candidate_id] = EvidenceCandidate(
        candidate_id=candidate_id,
        url="https://www.irs.gov/tax-professionals/stale-rates",
        title="Stale official rates",
        domain="irs.gov",
        source_tier="official",
        source_class="official_current_rules",
        currentness_signal="stale",
        readable_status="readable",
        fetchable_status="fetched",
        fact_disposition=CandidateDisposition.ACCEPTED,
        eligible_for_stronger_obligation=True,
        contextual_only=False,
        lower_tier=False,
        final_evidence_eligible=False,
    )
    kernel.state.evidence_ledger.custody_records.append(
        CandidateCustodyRecord(
            candidate_id=candidate_id,
            record_kind=CandidateCustodyKind.FACT,
            disposition=CandidateDisposition.ACCEPTED,
            reason="test stale official sibling",
            source="test",
            requirement_id=OFFICIAL_REQUIREMENT_ID,
            observation_id="ag96i3p1:test-stale-sibling",
        )
    )
    requirement = kernel.state.evidence_ledger.requirements[OFFICIAL_REQUIREMENT_ID]
    if candidate_id not in requirement.linked_candidate_ids:
        requirement.linked_candidate_ids.append(candidate_id)
    kernel.state.evidence_ledger.links.append(
        SourceObligationLink(
            requirement_id=OFFICIAL_REQUIREMENT_ID,
            candidate_id=candidate_id,
            link_reason="test_stale_official_sibling",
            link_status="accepted",
        )
    )
