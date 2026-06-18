from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.followup_citation_rendering_runtime import (
    AG96I3T1_CITATION_RENDERING_MODE,
    execute_followup_citation_rendering_action,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import (
    execute_followup_final_answer_packet_prepare_action,
)
from core.run_kernel import (
    FOLLOWUP_CITATION_RENDERING_STAGE,
    Observation,
    RunKernel,
    RunKernelTransitionError,
)
from tests.ag96_static_guards import imported_modules
from tests.ag96i3_assertions import (
    assert_no_sensitive_payload,
    assert_t1_boundary_snapshot_unchanged,
    snapshot_t1_boundary_state,
)
from tests.test_ag96i3p1_final_evidence_selection import (
    OFFICIAL_CANDIDATE_ID,
    OFFICIAL_REQUIREMENT_ID,
    _add_secondary_candidate,
    _consume_p1,
    _execute_o2,
    _execute_p1,
    _kernel_through_o1,
    _kernel_through_o2,
    _resequence_action_and_observation,
    _stale_legacy_i2e_action,
)
from tests.test_ag96i3q1_citation_eligibility import (
    _consume_q1,
    _execute_q1,
    _inject_external_stale_action_and_observation,
    _kernel_through_q1,
)
from tests.test_ag96i3r1_citation_source_handoff import (
    _consume_r1,
    _execute_r1,
)

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_RENDERED_SOURCE_ENTRY_FIELDS = {
    "rendered_source_entry_id",
    "source_identity_position",
    "citation_id",
    "evidence_id",
    "candidate_id",
    "source_id",
    "requirement_id",
    "source_obligation_id",
    "stable_source_label",
    "title",
    "domain",
    "url",
    "source_class",
    "source_tier",
    "packet_local",
    "derived_from_r1",
    "rendering_mode",
    "rendering_policy",
}


def test_t1_happy_path_creates_r1_bound_rendering_state_only() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    r1_state = deepcopy(kernel.state.followup_citation_source_handoff_state)
    r1_projection = deepcopy(kernel.state.followup_citation_source_handoff_projection)
    q1_packet = deepcopy(kernel.state.final_answer_packet)

    action = kernel.authorize_followup_citation_rendering()
    assert action.stage == FOLLOWUP_CITATION_RENDERING_STAGE
    assert action.inputs["citation_rendering_mode"] == (
        AG96I3T1_CITATION_RENDERING_MODE
    )

    result = _execute_t1(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_citation_rendering_state
    projection = kernel.state.followup_citation_rendering_projection
    history = kernel.state.followup_citation_rendering_history
    assert state["owner"] == "RunKernel.FollowupCitationRendering"
    assert state["canonical_state"] is True
    assert state["trace_only"] is False
    assert state["storage_only"] is False
    assert projection["owner"] == "RunKernel.FollowupCitationRendering"
    assert projection["canonical_state"] is True
    assert history == [projection]
    assert kernel.state.projections[FOLLOWUP_CITATION_RENDERING_STAGE] == projection

    entries = state["rendered_source_entries"]
    identities = r1_state["source_identity_records"]
    assert len(entries) == len(identities)
    for position, (entry, identity) in enumerate(zip(entries, identities), start=1):
        assert set(entry) <= ALLOWED_RENDERED_SOURCE_ENTRY_FIELDS
        assert entry["rendered_source_entry_id"].endswith(f":source-entry:{position}")
        assert entry["source_identity_position"] == identity["source_identity_position"]
        assert entry["citation_id"] == identity["citation_id"]
        assert entry["evidence_id"] == identity["evidence_id"]
        assert entry["candidate_id"] == identity["candidate_id"]
        assert entry["source_id"] == identity["source_id"]
        assert entry["requirement_id"] == identity["requirement_id"]
        assert entry["source_obligation_id"] == identity["source_obligation_id"]
        assert entry["stable_source_label"] == f"S{position}"
        assert entry["title"] == identity["title"]
        assert entry["domain"] == identity["domain"]
        assert entry["url"] == identity["url"]
        assert entry["source_class"] == identity["source_class"]
        assert entry["source_tier"] == identity["source_tier"]
        assert entry["packet_local"] is True
        assert entry["derived_from_r1"] is True
        assert entry["rendering_mode"] == AG96I3T1_CITATION_RENDERING_MODE
        assert entry["rendering_policy"] == "machine_readable_source_entry_only"

    assert state["rendered_source_entry_count"] == len(identities)
    assert state["citation_source_handoff_id"] == r1_state["citation_source_handoff_id"]
    assert state["followup_citation_source_handoff_digest"] == (
        action.inputs["followup_citation_source_handoff_digest"]
    )
    assert state["source_identity_digest"] == r1_state["source_identity_digest"]
    lineage = state["citation_rendering_lineage"]
    assert lineage["citation_rendering_id"] == state["citation_rendering_id"]
    assert lineage["citation_source_handoff_id"] == (
        r1_state["citation_source_handoff_id"]
    )
    assert lineage["citation_eligibility_id"] == (
        kernel.state.followup_citation_eligibility_state["citation_eligibility_id"]
    )
    assert lineage["final_evidence_selection_id"] == (
        kernel.state.followup_final_evidence_selection_state[
            "final_evidence_selection_id"
        ]
    )
    assert lineage["source_identity_digest"] == r1_state["source_identity_digest"]

    assert kernel.state.final_answer_packet == q1_packet
    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.final_answer_packet["author_input_refs"] == {}
    assert "author_payload_ref" not in kernel.state.final_answer_packet
    assert kernel.state.final_answer_packet["readiness_status"] == "blocked"
    assert kernel.state.final_answer_packet["final_answer_allowed"] is False
    assert kernel.state.final_answer_packet["answer_ready"] is False
    assert kernel.state.followup_citation_source_handoff_state == r1_state
    assert kernel.state.followup_citation_source_handoff_projection == r1_projection
    assert state["canonical_final_answer_packet_mutated"] is False
    assert state["citations_rendered"] is False
    assert state["citation_formatter_invoked"] is False
    assert state["ordered_product_source_output_created"] is False
    assert state["author_payload_created"] is False
    assert state["author_activation_allowed"] is False
    assert state["analyst_activation_allowed"] is False
    assert state["economist_activation_allowed"] is False
    assert state["not_role_consumption_payload"] is True

    with pytest.raises(RunKernelTransitionError, match="FinalAnswerPacket"):
        kernel.authorize_followup_author_gate()
    assert_no_sensitive_payload(state)
    assert_no_sensitive_payload(projection)


def test_t1_rendering_uses_only_r1_source_identity_records() -> None:
    kernel = _kernel_through_o2(mutator=_add_secondary_candidate)
    _consume_p1(kernel)
    _consume_q1(kernel)
    _consume_r1(kernel)
    packet = deepcopy(kernel.state.final_answer_packet)
    r1_identities = deepcopy(
        kernel.state.followup_citation_source_handoff_state["source_identity_records"]
    )

    _consume_t1(kernel)

    entries = kernel.state.followup_citation_rendering_state[
        "rendered_source_entries"
    ]
    assert [item["candidate_id"] for item in packet["evidence_allowed"]] == [
        OFFICIAL_CANDIDATE_ID
    ]
    assert [item["candidate_id"] for item in packet["evidence_excluded"]] == [
        "secondary_context_2026"
    ]
    assert [item["candidate_id"] for item in r1_identities] == [
        OFFICIAL_CANDIDATE_ID
    ]
    assert [item["candidate_id"] for item in entries] == [OFFICIAL_CANDIDATE_ID]
    assert "secondary_context_2026" not in {item["candidate_id"] for item in entries}
    assert entries[0]["citation_id"] == r1_identities[0]["citation_id"]
    assert entries[0]["evidence_id"] == r1_identities[0]["evidence_id"]
    assert entries[0]["source_id"] == OFFICIAL_CANDIDATE_ID
    assert entries[0]["requirement_id"] == OFFICIAL_REQUIREMENT_ID
    assert entries[0]["stable_source_label"] == "S1"
    assert_no_sensitive_payload(entries)


def test_t1_product_output_prompt_and_role_surfaces_remain_closed() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)

    _consume_t1(kernel)

    packet = kernel.state.final_answer_packet
    state = kernel.state.followup_citation_rendering_state
    projection = kernel.state.followup_citation_rendering_projection
    forbidden_fields = {
        "inline_citation",
        "inline_citation_string",
        "final_answer_citation",
        "final_answer_citation_string",
        "rendered_citation",
        "rendered_citations",
        "formatted_citation",
        "formatted_citations",
        "source_list_prose",
        "markdown_source_list",
        "ordered_sources",
        "ordered_product_source_output",
        "final_answer_text",
        "prompt",
        "prompt_text",
        "author_authority_block",
        "author_payload_ref",
        "author_input_refs",
        "final_answer_authority_projection",
        "author_input_payload",
        "analyst_handoff_ref",
        "economist_handoff_ref",
    }
    for surface in (state, projection):
        _assert_forbidden_fields_absent(surface, forbidden_fields)
    for field in forbidden_fields - {"author_input_refs"}:
        assert field not in packet
    assert packet["author_input_refs"] == {}
    assert state["citations_rendered"] is False
    assert state["citation_formatter_invoked"] is False
    assert state["citation_rendering_deferred"] is True
    assert state["prompt_behavior_changed"] is False
    assert state["product_answer_behavior_changed"] is False
    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.followup_final_answer_packet_state == {}
    assert kernel.state.followup_author_gate_state == {}
    assert kernel.state.followup_author_observation_state == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert getattr(kernel.state, "analyst_author_handoff_state", {}) == {}
    assert getattr(kernel.state, "economist_handoff_state", {}) == {}


def test_t1_authorization_binds_required_ids_modes_and_digests() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)

    action = kernel.authorize_followup_citation_rendering()
    inputs = action.inputs

    for field in (
        "citation_rendering_id",
        "citation_source_handoff_id",
        "citation_source_handoff_observation_id",
        "followup_citation_source_handoff_digest",
        "source_identity_digest",
        "citation_eligibility_id",
        "citation_eligibility_observation_id",
        "followup_citation_eligibility_digest",
        "final_evidence_selection_id",
        "final_evidence_selection_observation_id",
        "followup_final_evidence_selection_digest",
        "blocked_final_answer_packet_shell_id",
        "blocked_final_answer_packet_shell_observation_id",
        "blocked_final_answer_packet_shell_digest",
        "blocked_final_answer_packet_digest",
        "packet_preparation_readiness_id",
        "readiness_observation_id",
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
    assert inputs["citation_rendering_mode"] == AG96I3T1_CITATION_RENDERING_MODE


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("ledger", "EvidenceLedger digest mismatch"),
        ("sufficiency", "SufficiencyJudgment digest mismatch"),
        ("recheck", "recheck digest mismatch"),
        ("readiness", "O1 readiness digest mismatch"),
        ("shell", "O2 shell digest mismatch"),
        ("p1", "P1 digest mismatch"),
        ("q1", "Q1 digest mismatch"),
        ("r1", "R1 digest mismatch"),
        ("packet", "FinalAnswerPacket digest mismatch"),
    ],
)
def test_t1_reducer_rejects_stale_digests(mutation: str, match: str) -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    action = kernel.authorize_followup_citation_rendering()
    result = _execute_t1(kernel, action=action)
    if mutation == "ledger":
        kernel.state.evidence_ledger.observation_refs.append(
            {"observation_id": "ag96i3t1:stale-ledger", "source": "test"}
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
    elif mutation == "q1":
        kernel.state.followup_citation_eligibility_state["digest_mutation"] = "test"
    elif mutation == "r1":
        kernel.state.followup_citation_source_handoff_state[
            "digest_mutation"
        ] = "test"
    else:
        kernel.state.final_answer_packet["digest_mutation"] = "test"
    snapshot = snapshot_t1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)

    assert_t1_boundary_snapshot_unchanged(kernel, snapshot)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("citation_rendering_id", "mutated-rendering"),
        ("citation_source_handoff_id", "mutated-handoff"),
        ("citation_source_handoff_observation_id", "mutated-r1-observation"),
        ("source_identity_digest", "mutated-source-digest"),
        ("citation_eligibility_id", "mutated-eligibility"),
        ("citation_eligibility_observation_id", "mutated-q1-observation"),
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
def test_t1_reducer_rejects_mutated_binding_fields(
    field: str,
    value: Any,
) -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    action = kernel.authorize_followup_citation_rendering()
    result = _execute_t1(kernel, action=action)
    bad_state = deepcopy(result.record.to_dict())
    bad_state[field] = value

    with pytest.raises(RunKernelTransitionError, match=field):
        kernel.reduce(_t1_observation_from_state(action, bad_state))

    assert kernel.state.followup_citation_rendering_state == {}


def test_t1_missing_noncanonical_prerequisites_reject() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    kernel.state.followup_citation_source_handoff_state["canonical_state"] = False
    with pytest.raises(RunKernelTransitionError, match="canonical R1 state"):
        kernel.authorize_followup_citation_rendering()

    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    kernel.state.followup_citation_source_handoff_projection = {}
    with pytest.raises(RunKernelTransitionError, match="R1 projection"):
        kernel.authorize_followup_citation_rendering()

    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    kernel.state.followup_citation_source_handoff_history = []
    with pytest.raises(RunKernelTransitionError, match="R1 history"):
        kernel.authorize_followup_citation_rendering()

    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    kernel.state.final_answer_packet["canonical_state"] = False
    with pytest.raises(RunKernelTransitionError, match="canonical FinalAnswerPacket"):
        kernel.authorize_followup_citation_rendering()


def test_t1_reducer_rebuilds_rendering_and_ignores_caller_entries() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    action = kernel.authorize_followup_citation_rendering()
    result = _execute_t1(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["rendered_source_entries"] = [
        {**spoofed["rendered_source_entries"][0], "source_id": "spoofed"}
    ]

    kernel.reduce(_t1_observation_from_state(action, spoofed))

    entry = kernel.state.followup_citation_rendering_state["rendered_source_entries"][
        0
    ]
    assert entry["source_id"] == OFFICIAL_CANDIDATE_ID


def test_t1_malformed_observation_rejects_before_bookkeeping_or_mutation() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    action = kernel.authorize_followup_citation_rendering()
    snapshot = snapshot_t1_boundary_state(kernel)
    bad_observation = Observation.from_action(
        action,
        observation_type="followup_citation_rendering_prepared",
        status="completed",
        payload={},
    )

    with pytest.raises(RunKernelTransitionError, match="requires followup"):
        kernel.reduce(bad_observation)

    assert_t1_boundary_snapshot_unchanged(kernel, snapshot)


def test_duplicate_t1_activation_for_same_r1_handoff_rejects() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    _consume_t1(kernel)

    with pytest.raises(RunKernelTransitionError, match="already activated"):
        kernel.authorize_followup_citation_rendering()


def test_pre_authorized_duplicate_t1_reduce_rejects_after_t1() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    first_action = kernel.authorize_followup_citation_rendering()
    first_result = _execute_t1(kernel, action=first_action)
    duplicate_action = kernel.authorize_followup_citation_rendering()
    duplicate_result = _execute_t1(kernel, action=duplicate_action)

    kernel.reduce(first_result.observation)
    snapshot = snapshot_t1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="duplicate|AG-96I3T1"):
        kernel.reduce(duplicate_result.observation)

    assert_t1_boundary_snapshot_unchanged(kernel, snapshot)


def test_stale_legacy_i2e_reduce_rejects_after_t1_without_state_change() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    legacy_kernel = _kernel_through_o2()
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
    _consume_t1(kernel)
    _stale_action, stale_observation = _inject_external_stale_action_and_observation(
        kernel,
        legacy_kernel,
        legacy_action,
        legacy_result.observation,
    )
    snapshot = snapshot_t1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3T1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    assert_t1_boundary_snapshot_unchanged(kernel, snapshot)


def test_stale_o2_reduce_rejects_after_t1_without_state_change() -> None:
    kernel = _kernel_through_o1()
    stale_o2_action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    stale_o2_result = _execute_o2(kernel, action=stale_o2_action)
    kernel.reduce(stale_o2_result.observation)
    _consume_p1(kernel)
    _consume_q1(kernel)
    _consume_r1(kernel)
    _consume_t1(kernel)
    _stale_action, stale_observation = _resequence_action_and_observation(
        kernel,
        stale_o2_action,
        stale_o2_result.observation,
    )
    snapshot = snapshot_t1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3T1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    assert_t1_boundary_snapshot_unchanged(kernel, snapshot)


def test_stale_p1_reduce_rejects_after_t1_without_state_change() -> None:
    kernel = _kernel_through_o2()
    stale_p1_action = kernel.authorize_followup_final_evidence_selection()
    stale_p1_result = _execute_p1(kernel, action=stale_p1_action)
    kernel.reduce(stale_p1_result.observation)
    _consume_q1(kernel)
    _consume_r1(kernel)
    _consume_t1(kernel)
    _stale_action, stale_observation = _resequence_action_and_observation(
        kernel,
        stale_p1_action,
        stale_p1_result.observation,
    )
    snapshot = snapshot_t1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3T1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    assert_t1_boundary_snapshot_unchanged(kernel, snapshot)


def test_stale_q1_reduce_rejects_after_t1_without_state_change() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    source_kernel = _kernel_through_o2()
    _consume_p1(source_kernel)
    stale_q1_action = source_kernel.authorize_followup_citation_eligibility()
    stale_q1_result = _execute_q1(source_kernel, action=stale_q1_action)

    _consume_t1(kernel)
    _stale_action, stale_observation = _inject_external_stale_action_and_observation(
        kernel,
        source_kernel,
        stale_q1_action,
        stale_q1_result.observation,
    )
    snapshot = snapshot_t1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3T1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    assert_t1_boundary_snapshot_unchanged(kernel, snapshot)


def test_stale_r1_reduce_rejects_after_t1_without_state_change() -> None:
    kernel = _kernel_through_q1()
    stale_r1_action = kernel.authorize_followup_citation_source_handoff()
    stale_r1_result = _execute_r1(kernel, action=stale_r1_action)
    kernel.reduce(stale_r1_result.observation)
    _consume_t1(kernel)
    _stale_action, stale_observation = _resequence_action_and_observation(
        kernel,
        stale_r1_action,
        stale_r1_result.observation,
    )
    snapshot = snapshot_t1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3T1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    assert_t1_boundary_snapshot_unchanged(kernel, snapshot)


def test_static_guards_keep_t1_closed_to_product_roles_provider_and_pipeline() -> None:
    runtime_path = ROOT / "core" / "followup_citation_rendering_runtime.py"
    reducer_path = ROOT / "core" / "followup_runkernel_reducers.py"
    run_kernel_path = ROOT / "core" / "run_kernel.py"
    for path in (runtime_path, reducer_path, run_kernel_path):
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()

    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.prompts",
        "core.author_execution_runtime",
        "core.final_answer_runtime_assembly",
        "core.final_evidence_bundle_builder",
        "core.runtime_prompt_assembly",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
        "subprocess",
        "os",
    }
    assert imported_modules(runtime_path).isdisjoint(forbidden_imports)
    runtime_source = runtime_path.read_text(encoding="utf-8")
    for forbidden in (
        "format_citation(",
        "render_citation(",
        "derive_author_input_payload(",
        "build_final_answer_authority_projection(",
        "build_ordered_sources(",
        "post_author_output_projection(",
        "runtime_prompt_assembly",
        "AuthorExecutor(",
        "AnalystExecutor",
        "EconomistExecutor",
    ):
        assert forbidden not in runtime_source

    reducer_source = reducer_path.read_text(encoding="utf-8")
    t1_reducer_section = reducer_source.split(
        "def validate_followup_citation_rendering_observation_binding",
        1,
    )[1].split("def validate_followup_author_gate_observation_binding", 1)[0]
    for forbidden in (
        "format_citation(",
        "render_citation(",
        "derive_author_input_payload(",
        "build_final_answer_authority_projection(",
        "build_ordered_sources(",
        "post_author_output_projection(",
        "AuthorExecutor(",
        "AnalystExecutor",
        "EconomistExecutor",
    ):
        assert forbidden not in t1_reducer_section

    run_kernel_source = run_kernel_path.read_text(encoding="utf-8")
    t1_authorize_section = run_kernel_source.split(
        "def authorize_followup_citation_rendering",
        1,
    )[1].split("def authorize_followup_final_answer_packet_prepare", 1)[0]
    t1_reduce_section = run_kernel_source.split(
        "elif action.action_type is ActionType.FOLLOWUP_CITATION_RENDERING:",
        1,
    )[1].split(
        "elif (",
        1,
    )[0]
    for forbidden in (
        "format_citation(",
        "render_citation(",
        "derive_author_input_payload(",
        "build_final_answer_authority_projection(",
        "build_ordered_sources(",
        "post_author_output_projection(",
        "AuthorExecutor(",
        "AnalystExecutor",
        "EconomistExecutor",
    ):
        assert forbidden not in t1_authorize_section
        assert forbidden not in t1_reduce_section

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3t1" not in pipeline_source.casefold()
    assert "followup_citation_rendering" not in pipeline_source


def _execute_t1(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_citation_rendering_action(
        action,
        followup_citation_source_handoff_state=(
            kernel.state.followup_citation_source_handoff_state
        ),
        followup_citation_source_handoff_projection=(
            kernel.state.followup_citation_source_handoff_projection
        ),
        followup_citation_source_handoff_history=(
            kernel.state.followup_citation_source_handoff_history
        ),
        followup_citation_eligibility_state=(
            kernel.state.followup_citation_eligibility_state
        ),
        followup_citation_eligibility_projection=(
            kernel.state.followup_citation_eligibility_projection
        ),
        followup_citation_eligibility_history=(
            kernel.state.followup_citation_eligibility_history
        ),
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=(
            kernel.state.final_answer_authority_projection
        ),
        followup_final_evidence_selection_state=(
            kernel.state.followup_final_evidence_selection_state
        ),
        followup_final_evidence_selection_projection=(
            kernel.state.followup_final_evidence_selection_projection
        ),
        followup_final_evidence_selection_history=(
            kernel.state.followup_final_evidence_selection_history
        ),
        followup_blocked_final_answer_packet_shell_state=(
            kernel.state.followup_blocked_final_answer_packet_shell_state
        ),
        followup_blocked_final_answer_packet_shell_projection=(
            kernel.state.followup_blocked_final_answer_packet_shell_projection
        ),
        followup_blocked_final_answer_packet_shell_history=(
            kernel.state.followup_blocked_final_answer_packet_shell_history
        ),
        followup_final_answer_packet_readiness_state=(
            kernel.state.followup_final_answer_packet_readiness_state
        ),
        followup_final_answer_packet_readiness_projection=(
            kernel.state.followup_final_answer_packet_readiness_projection
        ),
        followup_final_answer_packet_readiness_history=(
            kernel.state.followup_final_answer_packet_readiness_history
        ),
        followup_sufficiency_recheck_state=(
            kernel.state.followup_sufficiency_recheck_state
        ),
        sufficiency_judgment_projection=(
            kernel.state.sufficiency_judgment_projection
        ),
        evidence_ledger_projection=(
            kernel.state.evidence_ledger.to_projection().to_dict()
        ),
        followup_evidence_intake_state=(
            kernel.state.followup_evidence_intake_state
        ),
    )


def _consume_t1(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_citation_rendering()
    result = _execute_t1(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _t1_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_citation_rendering_prepared",
        status="completed",
        payload={"followup_citation_rendering_state": state},
    )


def _assert_forbidden_fields_absent(
    value: Any,
    forbidden_fields: set[str],
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden_fields
            _assert_forbidden_fields_absent(child, forbidden_fields)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_forbidden_fields_absent(child, forbidden_fields)
