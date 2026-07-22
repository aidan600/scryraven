"""Offline phase-focus proof for bounded SearchOS breadcrumb contracts.

Proof class: PRODUCT-supporting structural proof. Validation bucket:
phase_focus. Surface guarded: deterministic extraction, URL policy, safe refs,
lineage, failure scope, retained capacity, and RunKernel navigation authority.
High-custody or closed-this-phase surface: exact pre-custody URLs are transient;
Map, Crawl, Focused Extract, fallback, retry, browser, and live calls stay
closed. Runtime/product path guarded: canonical owners below the ordinary
SearchOS consumer. Expected cost: a bounded deterministic owner matrix in under
one second locally. Promotion posture: remain phase_focus; ordinary product
sentinels live in the product test module. Demotion/retirement condition:
replace only when the same exact contracts move to a successor SearchOS owner.
Why not fast_pr: this is exhaustive authority and capacity detail, not a cheap
broad PR sentinel.
"""

from __future__ import annotations

import json
from hashlib import sha256

import pytest

from core.evidence_ledger_candidate_custody import (
    admit_navigation_packet_commit_to_evidence_ledger,
)
from core.fetch_read_content_reference import (
    build_navigation_fetch_read_content_packet_v2,
    fetch_read_content_packet_ref_from_packet,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.searchos_iterative_judgment_runtime import (
    begin_searchos_judgment_round,
    build_candidate_use_window_v1,
    build_searchos_initial_state,
    build_searchos_judgment_request_v2,
    build_searchos_policy_snapshot,
    charge_searchos_judgment_call,
    record_searchos_candidate_window,
    reduce_searchos_judgment_decision,
    searchos_policy_profile,
    validate_searchos_state,
)
from core.searchos_navigation_runtime import (
    NAVIGATION_CANDIDATE_SET_CAPACITY_EXHAUSTED,
    NAVIGATION_DESTINATION_BINDING_UNAVAILABLE,
    NAVIGATION_EFFECTIVE_BASE_OUT_OF_SCOPE,
    NAVIGATION_EXTRACTED_OCCURRENCE_CEILING,
    NAVIGATION_MODEL_WINDOW_CEILING,
    NAVIGATION_QUERY_LOCATOR_NOT_SUPPORTED,
    SearchOSNavigationDestinationRegistry,
    SearchOSNavigationError,
    SearchOSNavigationExecutionOverlayV1,
    SearchOSNavigationPacketCommitRegistry,
    admit_searchos_navigation_candidate_set,
    admit_searchos_navigation_selection,
    build_searchos_navigation_candidate_set_v1,
    build_searchos_navigation_candidate_window_v1,
    build_searchos_navigation_physical_custody_record_v2,
    build_searchos_navigation_retained_state,
    build_searchos_navigation_use_custody_ref_v2,
    discard_navigation_extraction_draft,
    extract_searchos_navigation_draft_v1,
    mark_searchos_navigation_slot_structurally_terminal,
    navigation_physical_operation_identity,
    normalize_navigation_url,
    record_searchos_navigation_contributor_failure,
    record_searchos_navigation_destination_terminal,
    sanitize_searchos_navigation_source_text_v1,
    searchos_navigation_physical_custody_ref,
    validate_searchos_navigation_retained_state,
)


def _digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _digest(seed: str) -> str:
    return _digest_text(seed)


def _stable_json_digest(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _ref(kind: str, seed: str) -> dict[str, str]:
    return {
        f"{kind}_id": f"{kind}:{seed}",
        f"{kind}_digest": _digest(seed),
    }


def _slot(slot_id: str = "slot-1") -> dict[str, str]:
    return {"slot_id": slot_id, "slot_digest": _digest(slot_id)}


def _draft(
    text: str,
    *,
    attempted: str = "https://example.com/guides/start",
    final_url: str | None = None,
    resolved_url: str | None = None,
):
    return extract_searchos_navigation_draft_v1(
        run_id="run-1",
        request_id="request-1",
        operation_identity_key="read:parent",
        source_obligation_ref=_ref("source_obligation", "obligation-1"),
        component_ref=_ref("component", "component-1"),
        answer_contract_ref=_ref("answer_contract", "contract-1"),
        artifact_ref=_ref("artifact", "artifact-1"),
        physical_acquisition_ref=_ref("physical_acquisition", "physical-1"),
        retained_text=text,
        retained_digest=_digest_text(text),
        retained_character_count=len(text),
        attempted_parent_url=attempted,
        final_url=final_url,
        resolved_url=resolved_url,
    )


def _join_material(draft, *, slot_id: str = "slot-1"):
    packet = {
        "schema_version": "fetch_read_content_packet_v2",
        "fetch_read_content_packet_id": "fetch-read:parent",
        "fetch_read_content_packet_digest": _digest("packet"),
        "run_id": draft.run_id,
        "request_id": draft.request_id,
        "retained_digest": draft.retained_digest,
        "retained_character_count": draft.retained_character_count,
        "acquisition_artifact_ref": draft.artifact_ref,
        "physical_acquisition_ref": draft.physical_acquisition_ref,
        "source_obligation_ref": draft.source_obligation_ref,
        "component_ref": draft.component_ref,
        "answer_contract_ref": draft.answer_contract_ref,
        "attempted_source_full_digest": draft.attempted_parent_full_digest,
    }
    packet_ref = fetch_read_content_packet_ref_from_packet(packet)
    ledger = {
        "evidence_ledger_custody_id": "ledger-custody:parent",
        "evidence_ledger_custody_digest": _digest("ledger"),
        "fetch_read_content_packet_ref": packet_ref,
        "physical_acquisition_ref": draft.physical_acquisition_ref,
    }
    ledger_ref = {
        "evidence_ledger_custody_id": ledger["evidence_ledger_custody_id"],
        "evidence_ledger_custody_digest": ledger[
            "evidence_ledger_custody_digest"
        ],
    }
    parent = {
        "searchos_parent_use_custody_id": f"parent-use:{slot_id}",
        "searchos_parent_use_custody_digest": _digest(f"parent:{slot_id}"),
        "slot_ref": _slot(slot_id),
        "fetch_read_content_packet_ref": packet_ref,
        "evidence_ledger_custody_ref": ledger_ref,
        "physical_acquisition_ref": draft.physical_acquisition_ref,
        "source_obligation_ref": draft.source_obligation_ref,
        "component_ref": draft.component_ref,
        "attempted_source_full_digest": draft.attempted_parent_full_digest,
        "physical_identity_digest": draft.attempted_parent_physical_digest,
        "ancestor_physical_identity_digests": [],
    }
    return packet, ledger, parent


def _proposal(
    text: str,
    *,
    slot_id: str = "slot-1",
    parent_depth: int = 0,
):
    draft = _draft(text)
    packet, ledger, parent = _join_material(draft, slot_id=slot_id)
    registry = SearchOSNavigationDestinationRegistry(
        run_id="run-1", request_id="request-1"
    )
    proposal = build_searchos_navigation_candidate_set_v1(
        draft=draft,
        destination_registry=registry,
        fetch_read_packet=packet,
        evidence_ledger_custody=ledger,
        parent_custody_ref=parent,
        slot_ref=_slot(slot_id),
        parent_depth=parent_depth,
    )
    return draft, registry, proposal


def _prepare_pending_navigation_for_kernel(
    kernel: RunKernel,
    *,
    candidate_ref: dict[str, object],
    parent_custody_ref: dict[str, object],
    profile_name: str = "Deep",
    read_nomination_count: int = 0,
    navigation_selection_count: int = 0,
) -> dict[str, object]:
    candidate_state_ref = _ref("candidate_state", "current")
    policy = build_searchos_policy_snapshot(
        run_id="run-1",
        request_id="request-1",
        profile_name=profile_name,
        navigation_runtime_open=True,
    )
    state = build_searchos_initial_state(
        run_id="run-1",
        request_id="request-1",
        answer_contract_ref=_ref("answer_contract", "contract-1"),
        policy_snapshot=policy,
        active_slots=[
            {
                "slot_id": "slot-1",
                "component_ref": _ref("component", "component-1"),
                "source_obligation_ref": _ref("source_obligation", "obligation-1"),
                "requirement_posture": "required",
            }
        ],
        initial_candidate_state_ref=candidate_state_ref,
    )
    slot = state["slots_by_id"]["slot-1"]
    slot["slot_ref"] = dict(parent_custody_ref["slot_ref"])
    slot["read_nomination_count"] = read_nomination_count
    slot["navigation_selection_count"] = navigation_selection_count
    slot["custody_refs"] = [
        {
            "fetch_read_content_packet_ref": dict(
                parent_custody_ref["fetch_read_content_packet_ref"]
            ),
            "evidence_ledger_custody_ref": dict(
                parent_custody_ref["evidence_ledger_custody_ref"]
            ),
            "physical_identity_digest": parent_custody_ref["physical_identity_digest"],
        }
    ]
    slot.pop("slot_state_digest", None)
    slot["slot_state_digest"] = _stable_json_digest(slot)
    state_core = {
        key: value
        for key, value in state.items()
        if key not in {"state_id", "state_digest", "replay_identity"}
    }
    state_digest = _stable_json_digest(state_core)
    state = {
        **state_core,
        "state_id": f"searchos-state:{state_digest[:24]}",
        "state_digest": state_digest,
        "replay_identity": f"searchos-state:{state_digest}",
    }
    decision_core = {
        "schema_version": "searchos_judgment_decision_v2",
        "slot_ref": dict(slot["slot_ref"]),
        "candidate_state_ref": candidate_state_ref,
        "action": "REQUEST_NAVIGATE_BREADCRUMB",
        "navigation_candidate_ref": dict(candidate_ref),
        "read_custody_assessments": [],
    }
    decision_digest = _stable_json_digest(decision_core)
    decision = {
        **decision_core,
        "judgment_decision_id": f"searchos-decision:{decision_digest[:24]}",
        "judgment_decision_digest": decision_digest,
        "replay_identity": f"searchos-decision:{decision_digest}",
    }
    kernel.state.searchos_state = reduce_searchos_judgment_decision(
        state, decision=decision
    )
    return decision


def _atomic_navigation_kernel(
    text: str = "[child](/child)",
    *,
    parent_depth: int = 0,
    profile_name: str = "Deep",
    read_nomination_count: int = 0,
    navigation_selection_count: int = 0,
):
    _, registry, proposal = _proposal(text, parent_depth=parent_depth)
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    kernel.state.searchos_navigation_state = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=["slot-1"],
    )
    admission = kernel.authorize_searchos_navigation_candidate_admission(
        candidate_set=proposal
    )
    kernel.reduce(
        Observation.from_action(
            admission,
            observation_type=(ObservationType.SEARCHOS_NAVIGATION_CANDIDATES_ADMITTED),
            status=RunStageStatus.COMPLETED,
            payload={
                "admitted_navigation_candidate_set_ref": admission.inputs[
                    "predicted_admitted_candidate_set_ref"
                ]
            },
        )
    )
    candidate = build_searchos_navigation_candidate_window_v1(
        kernel.state.searchos_navigation_state,
        slot_id="slot-1",
    )["navigation_candidate_refs"][0]
    contributor = kernel.state.searchos_navigation_state["contributors_by_id"][
        candidate["representative_contributor_ref"]["navigation_contributor_id"]
    ]
    decision = _prepare_pending_navigation_for_kernel(
        kernel,
        candidate_ref=candidate,
        parent_custody_ref=contributor["parent_custody_ref"],
        profile_name=profile_name,
        read_nomination_count=read_nomination_count,
        navigation_selection_count=navigation_selection_count,
    )
    return kernel, registry, candidate, decision


def _same_destination_proposal(
    *,
    registry: SearchOSNavigationDestinationRegistry,
    ordinal: int,
    slot_id: str = "slot-1",
    parent_depth: int = 0,
):
    draft = _draft("[shared](/shared-destination)")
    packet, ledger, parent = _join_material(draft, slot_id=slot_id)
    parent["searchos_parent_use_custody_id"] = f"parent-use:{ordinal}"
    parent["searchos_parent_use_custody_digest"] = _digest(
        f"parent-use:{ordinal}"
    )
    return build_searchos_navigation_candidate_set_v1(
        draft=draft,
        destination_registry=registry,
        fetch_read_packet=packet,
        evidence_ledger_custody=ledger,
        parent_custody_ref=parent,
        slot_ref=_slot(slot_id),
        parent_depth=parent_depth,
        parent_custody_admission_ordinal=ordinal,
    )


def _navigation_judgment_request_at_limits(
    *,
    profile_name: str,
    navigation_selection_count: int,
    logical_edge_charges: int,
) -> dict[str, object]:
    _, _, proposal = _proposal("[child](/child)")
    navigation_state = admit_searchos_navigation_candidate_set(
        build_searchos_navigation_retained_state(
            run_id="run-1",
            request_id="request-1",
            required_slot_ids=["slot-1"],
        ),
        candidate_set=proposal,
    )
    navigation_window = build_searchos_navigation_candidate_window_v1(
        navigation_state,
        slot_id="slot-1",
    )
    policy = build_searchos_policy_snapshot(
        run_id="run-1",
        request_id="request-1",
        profile_name=profile_name,
        navigation_runtime_open=True,
    )
    state = build_searchos_initial_state(
        run_id="run-1",
        request_id="request-1",
        answer_contract_ref=_ref("answer_contract", "contract-1"),
        policy_snapshot=policy,
        active_slots=[
            {
                "slot_id": "slot-1",
                "component_ref": _ref("component", "component-1"),
                "source_obligation_ref": _ref("source_obligation", "obligation-1"),
                "requirement_posture": "required",
            }
        ],
    )
    slot = state["slots_by_id"]["slot-1"]
    slot["navigation_selection_count"] = navigation_selection_count
    slot.pop("slot_state_digest")
    slot["slot_state_digest"] = _stable_json_digest(slot)
    state_core = {
        key: value
        for key, value in state.items()
        if key not in {"state_id", "state_digest", "replay_identity"}
    }
    state_digest = _stable_json_digest(state_core)
    state = {
        **state_core,
        "state_id": f"searchos-state:{state_digest[:24]}",
        "state_digest": state_digest,
        "replay_identity": f"searchos-state:{state_digest}",
    }
    candidate_window = build_candidate_use_window_v1(
        slot_ref=slot["slot_ref"],
        ordered_options=[],
        window_ordinal=1,
        policy_snapshot=policy,
    )
    state = record_searchos_candidate_window(state, window=candidate_window)
    state, reservation = begin_searchos_judgment_round(state, slot_ids=["slot-1"])
    state, charge = charge_searchos_judgment_call(
        state,
        reservation_ref=reservation,
        slot_id="slot-1",
    )
    return build_searchos_judgment_request_v2(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=candidate_window,
        navigation_candidate_window=navigation_window,
        read_custody_refs=[],
        navigation_logical_edge_charges=logical_edge_charges,
    )


def test_bounded_supported_markdown_extraction_and_unsupported_forms() -> None:
    text = " ".join(
        [
            "[absolute](https://example.com/a)",
            "[relative](../b)",
            "[balanced](../topic_(one))",
            "<https://example.com/c>",
            "![image](https://example.com/image.png)",
            "[reference][id]",
            "[id]: https://example.com/definition",
            '<a href="https://example.com/html">html</a>',
            "naked https://example.com/naked",
        ]
    )
    draft = _draft(text)
    assert [item.normalized_destination.path for item in draft.occurrences] == [
        "/a",
        "/b",
        "/topic_(one)",
        "/c",
    ]
    assert draft.extraction_counters["retained_occurrences"] == 4
    assert all("image" not in item.relationship_label for item in draft.occurrences)
    sanitized = sanitize_searchos_navigation_source_text_v1(text)
    assert "https://example.com/a" not in sanitized
    assert "https://example.com/c" not in sanitized
    assert "https://example.com/image.png" not in sanitized
    assert "absolute" in sanitized and "relative" in sanitized
    assert "linked page" in sanitized
    assert "naked https://example.com/naked" in sanitized

    overflow_text = " ".join(
        f"[item {index}](https://example.com/{index})"
        for index in range(NAVIGATION_EXTRACTED_OCCURRENCE_CEILING + 1)
    )
    overflow = _draft(overflow_text)
    assert len(overflow.occurrences) == NAVIGATION_EXTRACTED_OCCURRENCE_CEILING
    assert overflow.extraction_counters["overflow_occurrences"] == 1


def test_origin_port_query_and_effective_base_policy_fail_closed() -> None:
    accepted = _draft(
        "[same](https://example.com/a) [upgrade](https://example.com/b)",
        attempted="http://example.com/start",
    )
    assert len(accepted.occurrences) == 2

    rejected = _draft(
        " ".join(
            [
                "[downgrade](http://example.com/a)",
                "[www](https://www.example.com/a)",
                "[sub](https://sub.example.com/a)",
                "[other](https://example.net/a)",
                "[port](https://example.com:444/a)",
                "[query](https://example.com/a?api_secret=never-retain)",
            ]
        )
    )
    assert rejected.occurrences == ()
    assert rejected.extraction_counters["rejected_query_occurrences"] == 1
    assert rejected.extraction_counters["rejected_origin_occurrences"] >= 4

    out_of_scope = _draft(
        "[relative](/a)", final_url="https://redirect.example.net/base"
    )
    assert out_of_scope.effective_base_status == NAVIGATION_EFFECTIVE_BASE_OUT_OF_SCOPE
    assert out_of_scope.occurrences == ()

    explicit_parent = _draft(
        "[implicit](https://example.com/a)",
        attempted="https://example.com:443/start",
    )
    assert explicit_parent.occurrences == ()

    unicode_host = _draft("[unicode](https://exämple.com/a)")
    assert unicode_host.occurrences == ()


def test_query_is_rejected_before_registry_and_never_stripped() -> None:
    secret = "phase_unique_query_secret_4f57"  # pragma: allowlist secret
    draft = _draft(f"[secret](https://example.com/path?token={secret})")
    registry = SearchOSNavigationDestinationRegistry(
        run_id="run-1", request_id="request-1"
    )
    packet, ledger, parent = _join_material(draft)
    proposal = build_searchos_navigation_candidate_set_v1(
        draft=draft,
        destination_registry=registry,
        fetch_read_packet=packet,
        evidence_ledger_custody=ledger,
        parent_custody_ref=parent,
        slot_ref=_slot(),
    )
    assert len(registry) == 0
    assert proposal["candidate_contributors"] == []
    assert secret not in json.dumps(proposal, sort_keys=True)
    assert secret not in sanitize_searchos_navigation_source_text_v1(
        f"[secret](https://example.com/path?token={secret})"
    )
    with pytest.raises(
        SearchOSNavigationError,
        match=NAVIGATION_QUERY_LOCATOR_NOT_SUPPORTED,
    ):
        registry.register(f"https://example.com/path?token={secret}")
    ordinary = _draft("[page two](https://example.com/path?page=2)")
    assert ordinary.occurrences == ()
    assert ordinary.extraction_counters["rejected_query_occurrences"] == 1
    with pytest.raises(
        SearchOSNavigationError,
        match=NAVIGATION_QUERY_LOCATOR_NOT_SUPPORTED,
    ):
        registry.register("https://example.com/path?page=2")


def test_trailing_slash_is_distinct_physical_identity() -> None:
    no_slash = normalize_navigation_url("https://EXAMPLE.com/a#fragment")
    slash = normalize_navigation_url("https://example.com/a/")
    assert no_slash.exact_url == "https://example.com/a"
    assert slash.exact_url == "https://example.com/a/"
    assert no_slash.full_digest != slash.full_digest
    assert no_slash.physical_digest != slash.physical_digest
    assert navigation_physical_operation_identity(no_slash.exact_url) != (
        navigation_physical_operation_identity(slash.exact_url)
    )


def test_exact_parent_custody_join_is_required_and_draft_can_be_destroyed() -> None:
    draft = _draft("[child](/child)")
    packet, ledger, parent = _join_material(draft)
    registry = SearchOSNavigationDestinationRegistry(
        run_id="run-1", request_id="request-1"
    )
    v1_packet = {**packet, "schema_version": "fetch_read_content_packet_v1"}
    with pytest.raises(
        SearchOSNavigationError,
        match="navigation_parent_packet_v2_required",
    ):
        build_searchos_navigation_candidate_set_v1(
            draft=draft,
            destination_registry=registry,
            fetch_read_packet=v1_packet,
            evidence_ledger_custody=ledger,
            parent_custody_ref=parent,
            slot_ref=_slot(),
        )
    with pytest.raises(
        SearchOSNavigationError,
        match="evidence_ledger_custody",
    ):
        build_searchos_navigation_candidate_set_v1(
            draft=draft,
            destination_registry=registry,
            fetch_read_packet=packet,
            evidence_ledger_custody={},
            parent_custody_ref=parent,
            slot_ref=_slot(),
        )
    altered_packet = dict(packet)
    altered_packet["retained_digest"] = _digest("altered")
    with pytest.raises(SearchOSNavigationError, match="retained_digest_mismatch"):
        build_searchos_navigation_candidate_set_v1(
            draft=draft,
            destination_registry=registry,
            fetch_read_packet=altered_packet,
            evidence_ledger_custody=ledger,
            parent_custody_ref=parent,
            slot_ref=_slot(),
        )
    altered_parent = dict(parent)
    altered_parent["evidence_ledger_custody_ref"] = _ref(
        "evidence_ledger_custody", "wrong"
    )
    with pytest.raises(SearchOSNavigationError, match="use_ledger_mismatch"):
        build_searchos_navigation_candidate_set_v1(
            draft=draft,
            destination_registry=registry,
            fetch_read_packet=packet,
            evidence_ledger_custody=ledger,
            parent_custody_ref=altered_parent,
            slot_ref=_slot(),
        )
    discard_navigation_extraction_draft(draft)
    assert draft.destroyed is True
    with pytest.raises(SearchOSNavigationError, match="draft_destroyed"):
        build_searchos_navigation_candidate_set_v1(
            draft=draft,
            destination_registry=registry,
            fetch_read_packet=packet,
            evidence_ledger_custody=ledger,
            parent_custody_ref=parent,
            slot_ref=_slot(),
        )


def test_registry_is_transient_exact_and_missing_binding_fails_before_edge() -> None:
    _, registry, proposal = _proposal("[child](/child)")
    state = build_searchos_navigation_retained_state(
        run_id="run-1", request_id="request-1", required_slot_ids=["slot-1"]
    )
    state = admit_searchos_navigation_candidate_set(
        state, candidate_set=proposal
    )
    window = build_searchos_navigation_candidate_window_v1(
        state, slot_id="slot-1"
    )
    assert window["visible_count"] == 1
    registry.discard()
    with pytest.raises(
        SearchOSNavigationError,
        match=NAVIGATION_DESTINATION_BINDING_UNAVAILABLE,
    ):
        admit_searchos_navigation_selection(
            state,
            navigation_candidate_ref=window["navigation_candidate_refs"][0],
            destination_registry=registry,
        )


def test_pending_navigation_does_not_charge_until_atomic_selection() -> None:
    kernel, registry, candidate, decision = _atomic_navigation_kernel()
    slot = kernel.state.searchos_state["slots_by_id"]["slot-1"]
    navigation = kernel.state.searchos_navigation_state
    assert slot["posture"] == "awaiting_navigation_admission"
    assert slot["read_nomination_count"] == 0
    assert navigation["logical_read_nomination_charges"] == 0
    assert navigation["logical_edge_charges"] == 0
    assert navigation["selection_leases_by_id"] == {}

    action = kernel.authorize_searchos_navigation_selection(
        navigation_candidate_ref=candidate,
        destination_registry=registry,
        judgment_decision_ref=decision,
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCHOS_NAVIGATION_SELECTED,
            status=RunStageStatus.COMPLETED,
            payload={
                "navigation_selection_ref": action.inputs[
                    "predicted_navigation_selection_ref"
                ],
                "navigation_edge_ref": action.inputs["predicted_navigation_edge_ref"],
            },
        )
    )
    slot = kernel.state.searchos_state["slots_by_id"]["slot-1"]
    navigation = kernel.state.searchos_navigation_state
    assert slot["posture"] == "awaiting_read"
    assert slot["read_nomination_count"] == 1
    assert slot["navigation_selection_count"] == 1
    assert slot["pending_navigation_decision_ref"] == {}
    assert slot["pending_navigation_candidate_ref"] == {}
    assert navigation["logical_read_nomination_charges"] == 1
    assert navigation["logical_edge_charges"] == 1
    assert len(navigation["selection_leases_by_id"]) == 1
    assert len(navigation["edges_by_id"]) == 1


def test_destination_failure_releases_lease_and_reopens_same_slot() -> None:
    kernel, registry, candidate, decision = _atomic_navigation_kernel()
    action = kernel.authorize_searchos_navigation_selection(
        navigation_candidate_ref=candidate,
        destination_registry=registry,
        judgment_decision_ref=decision,
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCHOS_NAVIGATION_SELECTED,
            status=RunStageStatus.COMPLETED,
            payload={
                "navigation_selection_ref": action.inputs[
                    "predicted_navigation_selection_ref"
                ],
                "navigation_edge_ref": action.inputs["predicted_navigation_edge_ref"],
            },
        )
    )
    navigation = kernel.state.searchos_navigation_state
    selection_ref = action.inputs["predicted_navigation_selection_ref"]
    selection = navigation["selection_leases_by_id"][
        selection_ref["navigation_selection_id"]
    ]
    terminal = kernel.authorize_searchos_navigation_terminal_record(
        outcome_scope="destination",
        stable_option_ref=selection["stable_option_ref"],
        operation_identity_key=(
            "read-navigation:" + selection["physical_identity_digest"]
        ),
        disposition="destination_failed",
        failure_code="navigation_transport_failed_no_retry",
    )
    kernel.reduce(
        Observation.from_action(
            terminal,
            observation_type=(ObservationType.SEARCHOS_NAVIGATION_TERMINAL_RECORDED),
            status=RunStageStatus.COMPLETED,
            payload={"navigation_terminal_outcome": dict(terminal.inputs)},
        )
    )
    slot = kernel.state.searchos_state["slots_by_id"]["slot-1"]
    navigation = kernel.state.searchos_navigation_state
    option = navigation["option_states_by_id"][
        selection["stable_option_ref"]["navigation_option_id"]
    ]
    assert slot["posture"] == "active_unjudged"
    assert slot["read_nomination_count"] == 1
    assert navigation["logical_read_nomination_charges"] == 1
    assert navigation["logical_edge_charges"] == 1
    assert option["disposition"] == "destination_failed"
    assert option["active_lease_ref"] == {}
    assert (
        selection_ref["navigation_selection_id"]
        in navigation["released_selection_leases_by_id"]
    )
    terminal_record = next(
        iter(navigation["terminal_physical_operations_by_key"].values())
    )
    assert terminal_record["retry_licensed"] is False


def test_missing_binding_rejects_pending_navigation_with_zero_deltas() -> None:
    kernel, registry, candidate, decision = _atomic_navigation_kernel()
    registry.discard()
    before_navigation = json.loads(json.dumps(kernel.state.searchos_navigation_state))
    action = kernel.authorize_searchos_navigation_selection(
        navigation_candidate_ref=candidate,
        destination_registry=registry,
        judgment_decision_ref=decision,
    )
    assert action.inputs["navigation_admission_outcome"] == "rejected"
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCHOS_NAVIGATION_SELECTED,
            status=RunStageStatus.FAILED,
            payload={
                "navigation_admission_outcome": "rejected",
                "failure_code": action.inputs["failure_code"],
            },
        )
    )
    slot = kernel.state.searchos_state["slots_by_id"]["slot-1"]
    navigation = kernel.state.searchos_navigation_state
    assert slot["posture"] == "active_unjudged"
    assert slot["read_nomination_count"] == 0
    assert slot["pending_navigation_decision_ref"] == {}
    assert slot["pending_navigation_candidate_ref"] == {}
    assert navigation["logical_read_nomination_charges"] == 0
    assert navigation["logical_edge_charges"] == 0
    assert navigation["selection_leases_by_id"] == {}
    assert navigation["edges_by_id"] == {}
    assert navigation["terminal_physical_operations_by_key"] == {}
    assert before_navigation["logical_edge_charges"] == 0
    option = next(iter(navigation["option_states_by_id"].values()))
    assert option["disposition"] == "binding_unavailable"


@pytest.mark.parametrize(
    ("profile_name", "parent_depth", "read_count", "selection_count", "reason"),
    (
        ("Fast", 1, 0, 0, "navigation_depth_limit_exhausted"),
        ("Fast", 0, 0, 1, "navigation_selection_limit_exhausted"),
        ("Fast", 0, 2, 0, "navigation_read_nomination_limit_exhausted"),
    ),
)
def test_policy_rejections_clear_pending_without_charges(
    profile_name: str,
    parent_depth: int,
    read_count: int,
    selection_count: int,
    reason: str,
) -> None:
    kernel, registry, candidate, decision = _atomic_navigation_kernel(
        parent_depth=parent_depth,
        profile_name=profile_name,
        read_nomination_count=read_count,
        navigation_selection_count=selection_count,
    )
    action = kernel.authorize_searchos_navigation_selection(
        navigation_candidate_ref=candidate,
        destination_registry=registry,
        judgment_decision_ref=decision,
    )
    assert action.inputs["navigation_admission_outcome"] == "rejected"
    assert action.inputs["failure_code"] == reason
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCHOS_NAVIGATION_SELECTED,
            status=RunStageStatus.FAILED,
            payload={
                "navigation_admission_outcome": "rejected",
                "failure_code": reason,
            },
        )
    )
    slot = kernel.state.searchos_state["slots_by_id"]["slot-1"]
    assert slot["posture"] == "active_unjudged"
    assert slot["read_nomination_count"] == read_count
    assert kernel.state.searchos_navigation_state["logical_edge_charges"] == 0
    assert (
        kernel.state.searchos_navigation_state["logical_read_nomination_charges"] == 0
    )


@pytest.mark.parametrize(
    "failure_kind",
    ("stale_lineage", "stale_representative", "lease_conflict"),
)
def test_current_authority_rejections_have_zero_incremental_charges(
    failure_kind: str,
) -> None:
    kernel, registry, candidate, decision = _atomic_navigation_kernel(
        "[child](/child) [other](/other)"
    )
    if failure_kind == "stale_lineage":
        second_draft = _draft("[same child](/child)")
        packet, ledger, parent = _join_material(second_draft)
        parent["searchos_parent_use_custody_id"] = "parent-use:second"
        parent["searchos_parent_use_custody_digest"] = _digest("parent-use:second")
        proposal = build_searchos_navigation_candidate_set_v1(
            draft=second_draft,
            destination_registry=registry,
            fetch_read_packet=packet,
            evidence_ledger_custody=ledger,
            parent_custody_ref=parent,
            slot_ref=_slot(),
            parent_custody_admission_ordinal=2,
        )
        kernel.state.searchos_navigation_state = (
            admit_searchos_navigation_candidate_set(
                kernel.state.searchos_navigation_state,
                candidate_set=proposal,
            )
        )
    elif failure_kind == "stale_representative":
        option_id = candidate["stable_option_ref"]["navigation_option_id"]
        kernel.state.searchos_navigation_state["option_states_by_id"][option_id][
            "representative_contributor_ref"
        ] = _ref("navigation_contributor", "stale")
    else:
        kernel.state.searchos_navigation_state, _, _ = (
            admit_searchos_navigation_selection(
                kernel.state.searchos_navigation_state,
                navigation_candidate_ref=candidate,
                destination_registry=registry,
            )
        )
    before_edge = kernel.state.searchos_navigation_state["logical_edge_charges"]
    before_read = kernel.state.searchos_navigation_state[
        "logical_read_nomination_charges"
    ]
    action = kernel.authorize_searchos_navigation_selection(
        navigation_candidate_ref=candidate,
        destination_registry=registry,
        judgment_decision_ref=decision,
    )
    assert action.inputs["navigation_admission_outcome"] == "rejected"
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCHOS_NAVIGATION_SELECTED,
            status=RunStageStatus.FAILED,
            payload={
                "navigation_admission_outcome": "rejected",
                "failure_code": action.inputs["failure_code"],
            },
        )
    )
    assert kernel.state.searchos_navigation_state["logical_edge_charges"] == before_edge
    assert (
        kernel.state.searchos_navigation_state["logical_read_nomination_charges"]
        == before_read
    )
    assert (
        kernel.state.searchos_state["slots_by_id"]["slot-1"]["read_nomination_count"]
        == 0
    )
    assert (
        kernel.state.searchos_state["slots_by_id"]["slot-1"]["posture"]
        == "active_unjudged"
    )


def test_stable_lineage_staleness_contributor_failure_and_terminal_scope() -> None:
    _, registry, first = _proposal("[child](/child)")
    state = build_searchos_navigation_retained_state(
        run_id="run-1", request_id="request-1", required_slot_ids=["slot-1"]
    )
    state = admit_searchos_navigation_candidate_set(state, candidate_set=first)
    old_candidate = build_searchos_navigation_candidate_window_v1(
        state, slot_id="slot-1"
    )["navigation_candidate_refs"][0]

    second_draft = _draft("[same child from second occurrence](/child)")
    packet, ledger, parent = _join_material(second_draft)
    parent["searchos_parent_use_custody_id"] = "parent-use:second"
    parent["searchos_parent_use_custody_digest"] = _digest("parent:second")
    second = build_searchos_navigation_candidate_set_v1(
        draft=second_draft,
        destination_registry=registry,
        fetch_read_packet=packet,
        evidence_ledger_custody=ledger,
        parent_custody_ref=parent,
        slot_ref=_slot(),
        parent_custody_admission_ordinal=2,
    )
    state = admit_searchos_navigation_candidate_set(state, candidate_set=second)
    with pytest.raises(SearchOSNavigationError, match="stale_lineage"):
        admit_searchos_navigation_selection(
            state,
            navigation_candidate_ref=old_candidate,
            destination_registry=registry,
        )
    current = build_searchos_navigation_candidate_window_v1(
        state, slot_id="slot-1"
    )["navigation_candidate_refs"][0]
    option_id = current["stable_option_ref"]["navigation_option_id"]
    refs = state["option_states_by_id"][option_id]["feasible_contributor_refs"]
    state = record_searchos_navigation_contributor_failure(
        state,
        contributor_ref=refs[0],
        failure_code="navigation_ancestor_cycle",
    )
    assert state["option_states_by_id"][option_id]["disposition"] == "selectable"
    assert len(state["option_states_by_id"][option_id]["feasible_contributor_refs"]) == 1

    current = build_searchos_navigation_candidate_window_v1(
        state, slot_id="slot-1"
    )["navigation_candidate_refs"][0]
    state, selection, _ = admit_searchos_navigation_selection(
        state,
        navigation_candidate_ref=current,
        destination_registry=registry,
    )
    assert selection["lease_posture"] == "active_immutable_selection"
    assert state["logical_edge_charges"] == 1
    assert state["logical_read_nomination_charges"] == 1
    with pytest.raises(SearchOSNavigationError, match="active_lease_conflict"):
        admit_searchos_navigation_selection(
            state,
            navigation_candidate_ref=current,
            destination_registry=registry,
        )

    state = record_searchos_navigation_destination_terminal(
        state,
        stable_option_ref=current["stable_option_ref"],
        operation_identity_key=(
            "read-navigation:"
            + selection["physical_identity_digest"]
        ),
        disposition="destination_failed",
        failure_code="navigation_transport_failed_no_retry",
    )
    assert state["option_states_by_id"][option_id]["disposition"] == (
        "destination_failed"
    )
    assert next(iter(state["terminal_physical_operations_by_key"].values()))[
        "retry_licensed"
    ] is False


def test_capacity_prefix_window_and_required_slot_reservations() -> None:
    links = " ".join(f"[item {index}](/item-{index})" for index in range(5))
    _, _, proposal = _proposal(links)
    state = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=[],
        ceilings={
            "stable_options": 4,
            "contributors": 4,
            "lineages": 4,
            "candidate_sets": 1,
            "deep_edges": 4,
        },
    )
    state = admit_searchos_navigation_candidate_set(state, candidate_set=proposal)
    assert state["retained_counts"]["stable_options"] == 4
    assert state["retained_counts"]["contributors"] == 4
    assert state["retained_counts"]["lineages"] == 4
    assert state["overflow_totals"]["contributors"] == 1
    with pytest.raises(
        SearchOSNavigationError,
        match=NAVIGATION_CANDIDATE_SET_CAPACITY_EXHAUSTED,
    ):
        admit_searchos_navigation_candidate_set(state, candidate_set=proposal)

    _, _, many = _proposal(
        " ".join(f"[item {index}](/visible-{index})" for index in range(20))
    )
    roomy = build_searchos_navigation_retained_state(
        run_id="run-1", request_id="request-1", required_slot_ids=[]
    )
    roomy = admit_searchos_navigation_candidate_set(roomy, candidate_set=many)
    window = build_searchos_navigation_candidate_window_v1(
        roomy, slot_id="slot-1"
    )
    assert window["visible_count"] == NAVIGATION_MODEL_WINDOW_CEILING
    assert window["hidden_count"] == 8

    _, _, slot_one = _proposal("[one](/one)", slot_id="slot-1")
    reserved = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=["slot-1", "slot-2"],
        ceilings={
            "stable_options": 4,
            "contributors": 4,
            "lineages": 4,
            "candidate_sets": 4,
            "deep_edges": 4,
        },
    )
    reserved = admit_searchos_navigation_candidate_set(
        reserved, candidate_set=slot_one
    )
    assert reserved["retained_counts"]["stable_options"] == 1
    _, _, slot_one_more = _proposal("[two](/two) [three](/three)", slot_id="slot-1")
    reserved = admit_searchos_navigation_candidate_set(
        reserved, candidate_set=slot_one_more
    )
    assert reserved["retained_counts"]["stable_options"] == 2
    assert reserved["overflow_totals"]["contributors"] == 1
    released = mark_searchos_navigation_slot_structurally_terminal(
        reserved, slot_id="slot-2"
    )
    assert released["slot_reservation_status"]["slot-2"] == (
        "terminal_or_depth_two_unreachable"
    )


@pytest.mark.parametrize(
    ("category", "occurrence_count", "expected_count"),
    [
        (category, occurrence_count, min(occurrence_count, 2))
        for category in ("stable_options", "contributors", "lineages")
        for occurrence_count in (1, 2, 3)
    ],
)
def test_retained_category_limit_minus_one_limit_and_plus_one(
    category: str,
    occurrence_count: int,
    expected_count: int,
) -> None:
    _, _, proposal = _proposal(
        " ".join(
            f"[item {index}](/capacity-{category}-{index})"
            for index in range(occurrence_count)
        )
    )
    ceilings = {
        "stable_options": 16,
        "contributors": 16,
        "lineages": 16,
        "candidate_sets": 16,
        "deep_edges": 16,
    }
    ceilings[category] = 2
    state = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=[],
        ceilings=ceilings,
    )
    state = admit_searchos_navigation_candidate_set(
        state, candidate_set=proposal
    )
    assert state["retained_counts"][category] == expected_count
    admitted = next(iter(state["candidate_sets_by_id"].values()))
    assert admitted["admission_excluded_count"] == max(
        0, occurrence_count - 2
    )
    if occurrence_count == 3:
        assert state["overflow_totals"][category] == 1


def test_candidate_set_and_deep_edge_limit_boundaries() -> None:
    state = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=[],
        ceilings={
            "stable_options": 16,
            "contributors": 16,
            "lineages": 16,
            "candidate_sets": 2,
            "deep_edges": 2,
        },
    )
    proposals = [
        _proposal(f"[set {index}](/set-{index})")[2]
        for index in range(3)
    ]
    state = admit_searchos_navigation_candidate_set(
        state, candidate_set=proposals[0]
    )
    assert state["retained_counts"]["candidate_sets"] == 1
    state = admit_searchos_navigation_candidate_set(
        state, candidate_set=proposals[1]
    )
    assert state["retained_counts"]["candidate_sets"] == 2
    with pytest.raises(
        SearchOSNavigationError,
        match=NAVIGATION_CANDIDATE_SET_CAPACITY_EXHAUSTED,
    ):
        admit_searchos_navigation_candidate_set(
            state, candidate_set=proposals[2]
        )

    _, registry, three_options = _proposal(
        "[a](/edge-a) [b](/edge-b) [c](/edge-c)"
    )
    edge_state = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=[],
        ceilings={
            "stable_options": 16,
            "contributors": 16,
            "lineages": 16,
            "candidate_sets": 16,
            "deep_edges": 2,
        },
    )
    edge_state = admit_searchos_navigation_candidate_set(
        edge_state, candidate_set=three_options
    )
    for expected_edge_count in (1, 2):
        candidate = build_searchos_navigation_candidate_window_v1(
            edge_state, slot_id="slot-1"
        )["navigation_candidate_refs"][0]
        edge_state, _, _ = admit_searchos_navigation_selection(
            edge_state,
            navigation_candidate_ref=candidate,
            destination_registry=registry,
        )
        assert edge_state["retained_counts"]["deep_edges"] == (
            expected_edge_count
        )
    third = build_searchos_navigation_candidate_window_v1(
        edge_state, slot_id="slot-1"
    )["navigation_candidate_refs"][0]
    with pytest.raises(
        SearchOSNavigationError,
        match="navigation_deep_edge_capacity_exhausted",
    ):
        admit_searchos_navigation_selection(
            edge_state,
            navigation_candidate_ref=third,
            destination_registry=registry,
        )


@pytest.mark.parametrize(("profile_name", "max_depth", "selection_limit", "edge_limit"),
    (
        ("Fast", 1, 1, 8),
        ("Balanced", 2, 2, 16),
        ("Deep", 3, 3, 24),
    ),
)
def test_mode_specific_navigation_limits_and_boundaries(
    profile_name: str,
    max_depth: int,
    selection_limit: int,
    edge_limit: int,
) -> None:
    profile = searchos_policy_profile(profile_name)
    assert profile.navigation_max_depth == max_depth
    assert profile.navigation_selections_per_slot == selection_limit
    assert profile.navigation_edges_per_run == edge_limit

    draft = _draft("[tempting next link](/next)")
    packet, ledger, parent = _join_material(draft)
    registry = SearchOSNavigationDestinationRegistry(
        run_id="run-1", request_id="request-1"
    )
    at_max = build_searchos_navigation_candidate_set_v1
    with pytest.raises(SearchOSNavigationError, match="depth_violation"):
        at_max(
            draft=draft,
            destination_registry=registry,
            fetch_read_packet=packet,
            evidence_ledger_custody=ledger,
            parent_custody_ref=parent,
            slot_ref=_slot(),
            parent_depth=max_depth,
            navigation_max_depth=max_depth,
        )
    allowed = build_searchos_navigation_candidate_set_v1(
        draft=draft,
        destination_registry=registry,
        fetch_read_packet=packet,
        evidence_ledger_custody=ledger,
        parent_custody_ref=parent,
        slot_ref=_slot(),
        parent_depth=max_depth - 1,
        navigation_max_depth=max_depth,
    )
    assert allowed["candidate_contributors"][0]["child_depth"] == max_depth

    links = " ".join(
        f"[item {index}](/edge-{index})" for index in range(edge_limit + 1)
    )
    _, edge_registry, edge_proposal = _proposal(links)
    state = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=[],
    )
    state = admit_searchos_navigation_candidate_set(state, candidate_set=edge_proposal)
    for expected in range(1, edge_limit + 1):
        candidate = build_searchos_navigation_candidate_window_v1(
            state, slot_id="slot-1"
        )["navigation_candidate_refs"][0]
        state, _, _ = admit_searchos_navigation_selection(
            state,
            navigation_candidate_ref=candidate,
            destination_registry=edge_registry,
            navigation_max_depth=max_depth,
            navigation_selections_per_slot=edge_limit + 1,
            navigation_edges_per_run=edge_limit,
        )
        assert state["logical_edge_charges"] == expected
    next_candidate = build_searchos_navigation_candidate_window_v1(
        state, slot_id="slot-1"
    )["navigation_candidate_refs"][0]
    with pytest.raises(SearchOSNavigationError, match="run_edge_limit"):
        admit_searchos_navigation_selection(
            state,
            navigation_candidate_ref=next_candidate,
            destination_registry=edge_registry,
            navigation_max_depth=max_depth,
            navigation_selections_per_slot=edge_limit + 1,
            navigation_edges_per_run=edge_limit,
        )
    assert state["logical_edge_charges"] == edge_limit
    assert state["logical_read_nomination_charges"] == edge_limit

    selection_links = " ".join(
        f"[selection {index}](/selection-{index})"
        for index in range(selection_limit + 1)
    )
    _, selection_registry, selection_proposal = _proposal(selection_links)
    selection_state = admit_searchos_navigation_candidate_set(
        build_searchos_navigation_retained_state(
            run_id="run-1",
            request_id="request-1",
            required_slot_ids=[],
        ),
        candidate_set=selection_proposal,
    )
    assert selection_state["logical_edge_charges"] == 0
    for expected in range(1, selection_limit + 1):
        candidate = build_searchos_navigation_candidate_window_v1(
            selection_state, slot_id="slot-1"
        )["navigation_candidate_refs"][0]
        selection_state, _, _ = admit_searchos_navigation_selection(
            selection_state,
            navigation_candidate_ref=candidate,
            destination_registry=selection_registry,
            navigation_max_depth=max_depth,
            navigation_selections_per_slot=selection_limit,
            navigation_edges_per_run=edge_limit,
        )
        assert selection_state["logical_edge_charges"] == expected
    rejected_candidate = build_searchos_navigation_candidate_window_v1(
        selection_state, slot_id="slot-1"
    )["navigation_candidate_refs"][0]
    with pytest.raises(SearchOSNavigationError, match="selection_limit_exhausted"):
        admit_searchos_navigation_selection(
            selection_state,
            navigation_candidate_ref=rejected_candidate,
            destination_registry=selection_registry,
            navigation_max_depth=max_depth,
            navigation_selections_per_slot=selection_limit,
            navigation_edges_per_run=edge_limit,
        )
    assert selection_state["logical_edge_charges"] == selection_limit
    assert selection_state["logical_read_nomination_charges"] == (selection_limit)


@pytest.mark.parametrize(
    ("profile_name", "selection_limit", "edge_limit"),
    (("Fast", 1, 8), ("Balanced", 2, 16), ("Deep", 3, 24)),
)
def test_navigation_legal_action_is_omitted_at_mode_limits(
    profile_name: str,
    selection_limit: int,
    edge_limit: int,
) -> None:
    available = _navigation_judgment_request_at_limits(
        profile_name=profile_name,
        navigation_selection_count=selection_limit - 1,
        logical_edge_charges=edge_limit - 1,
    )
    assert available["navigation_availability_reason"] == ("navigation_available")
    assert "REQUEST_NAVIGATE_BREADCRUMB" in available["legal_actions"]

    for attempted_count in (selection_limit, selection_limit + 1):
        exhausted = _navigation_judgment_request_at_limits(
            profile_name=profile_name,
            navigation_selection_count=attempted_count,
            logical_edge_charges=edge_limit - 1,
        )
        assert exhausted["navigation_availability_reason"] == (
            "navigation_selection_limit_exhausted"
        )
        assert exhausted["navigation_candidate_refs"] == []
        assert "REQUEST_NAVIGATE_BREADCRUMB" not in exhausted["legal_actions"]
        assert {
            "PROPOSE_FOLLOWUP_QUERY",
            "HANDOFF_UNRESOLVED",
        }.issubset(exhausted["legal_actions"])

    for attempted_count in (edge_limit, edge_limit + 1):
        exhausted = _navigation_judgment_request_at_limits(
            profile_name=profile_name,
            navigation_selection_count=selection_limit - 1,
            logical_edge_charges=attempted_count,
        )
        assert exhausted["navigation_availability_reason"] == (
            "navigation_run_edge_limit_exhausted"
        )
        assert exhausted["navigation_candidate_refs"] == []
        assert "REQUEST_NAVIGATE_BREADCRUMB" not in exhausted["legal_actions"]
        assert {
            "PROPOSE_FOLLOWUP_QUERY",
            "HANDOFF_UNRESOLVED",
        }.issubset(exhausted["legal_actions"])


def test_v1_policy_and_navigation_state_replay_remain_parseable() -> None:
    policy = build_searchos_policy_snapshot(
        run_id="run-1",
        request_id="request-1",
        profile_name="Balanced",
        navigation_runtime_open=True,
    )
    v1_policy_core = {
        key: value
        for key, value in policy.items()
        if key
        not in {
            "policy_snapshot_id",
            "policy_snapshot_digest",
            "replay_identity",
            "navigation_max_depth",
            "navigation_selections_per_slot",
            "navigation_edges_per_run",
        }
    }
    v1_policy_core["schema_version"] = "searchos_policy_profile_v1"
    v1_policy_digest = _stable_json_digest(v1_policy_core)
    v1_policy = {
        **v1_policy_core,
        "policy_snapshot_id": f"searchos-policy:{v1_policy_digest[:24]}",
        "policy_snapshot_digest": v1_policy_digest,
        "replay_identity": f"searchos-policy:{v1_policy_digest}",
    }
    v1_state = build_searchos_initial_state(
        run_id="run-1",
        request_id="request-1",
        answer_contract_ref=_ref("answer_contract", "contract-1"),
        policy_snapshot=v1_policy,
        active_slots=[
            {
                "slot_id": "slot-1",
                "component_ref": _ref("component", "component-1"),
                "source_obligation_ref": _ref("source_obligation", "obligation-1"),
                "requirement_posture": "required",
            }
        ],
    )
    slot = v1_state["slots_by_id"]["slot-1"]
    for field in (
        "navigation_selection_count",
        "pending_navigation_decision_ref",
        "pending_navigation_candidate_ref",
        "navigation_availability_reason",
        "navigation_admission_history",
    ):
        slot.pop(field)
    slot.pop("slot_state_digest")
    slot["slot_state_digest"] = _stable_json_digest(slot)
    state_core = {
        key: value
        for key, value in v1_state.items()
        if key not in {"state_id", "state_digest", "replay_identity"}
    }
    state_core["schema_version"] = "searchos_iterative_judgment_state_v1"
    state_digest = _stable_json_digest(state_core)
    replay_state = {
        **state_core,
        "state_id": f"searchos-state:{state_digest[:24]}",
        "state_digest": state_digest,
        "replay_identity": f"searchos-state:{state_digest}",
    }
    assert validate_searchos_state(replay_state) == replay_state

    navigation_v1 = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=["slot-1"],
    )
    navigation_v1["schema_version"] = "searchos_navigation_retained_state_v1"
    for field in (
        "released_selection_leases_by_id",
        "selection_counts_by_slot",
        "selection_admission_facts_by_id",
        "expansion_outcomes_by_parent_custody_id",
    ):
        navigation_v1.pop(field)
    assert validate_searchos_navigation_retained_state(navigation_v1) == (navigation_v1)


def test_registry_transaction_commits_only_canonical_prefix_and_rolls_back_new() -> (
    None
):
    draft = _draft("[one](/one) [two](/two)")
    packet, ledger, parent = _join_material(draft)
    registry = SearchOSNavigationDestinationRegistry(
        run_id="run-1", request_id="request-1", capacity=2
    )
    transaction = registry.begin_transaction()
    proposal = build_searchos_navigation_candidate_set_v1(
        draft=draft,
        destination_registry=transaction,
        fetch_read_packet=packet,
        evidence_ledger_custody=ledger,
        parent_custody_ref=parent,
        slot_ref=_slot(),
    )
    state = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=[],
        ceilings={
            "stable_options": 1,
            "contributors": 2,
            "lineages": 2,
            "candidate_sets": 2,
            "deep_edges": 2,
        },
    )
    admitted = admit_searchos_navigation_candidate_set(state, candidate_set=proposal)
    candidate_set = next(iter(admitted["candidate_sets_by_id"].values()))
    admitted_bindings = [
        admitted["options_by_id"][ref["stable_option_ref"]["navigation_option_id"]][
            "destination_binding_ref"
        ]
        for ref in candidate_set["navigation_candidate_refs"]
    ]
    assert len(admitted_bindings) == 1
    transaction.commit_admitted_bindings(admitted_bindings)
    transaction.finalize()
    assert len(registry) == 1
    assert registry.resolve(admitted_bindings[0]).endswith("/one") or registry.resolve(
        admitted_bindings[0]
    ).endswith("/two")

    existing_ref = admitted_bindings[0]
    rollback = registry.begin_transaction()
    assert rollback.register(registry.resolve(existing_ref)) == existing_ref
    new_ref = rollback.register("https://example.com/new")
    rollback.commit_admitted_bindings([existing_ref, new_ref])
    assert len(registry) == 2
    rollback.rollback()
    assert len(registry) == 1
    assert registry.resolve(existing_ref)
    with pytest.raises(SearchOSNavigationError, match="binding_unavailable"):
        registry.resolve(new_ref)


def test_registry_transaction_mid_proposal_and_capacity_failure_leave_no_entries() -> (
    None
):
    registry = SearchOSNavigationDestinationRegistry(
        run_id="run-1", request_id="request-1", capacity=1
    )
    transaction = registry.begin_transaction()
    transaction.register("https://example.com/valid")
    with pytest.raises(SearchOSNavigationError):
        transaction.register("https://example.com:444/invalid")
    transaction.rollback()
    assert len(registry) == 0

    transaction = registry.begin_transaction()
    first = transaction.register("https://example.com/first")
    second = transaction.register("https://example.com/second")
    with pytest.raises(SearchOSNavigationError, match="capacity_exhausted"):
        transaction.commit_admitted_bindings([first, second])
    transaction.rollback()
    assert len(registry) == 0


def test_bracketed_ipv6_normalizes_registers_and_overlays_without_network() -> None:
    exact = "https://[2001:0db8:0:0::1]:443/path/"
    normalized = normalize_navigation_url(exact)
    assert normalized.exact_url == "https://[2001:db8::1]:443/path/"
    assert normalized.hostname == "2001:db8::1"
    assert normalized.path == "/path/"
    assert normalized.port_posture == "explicit_default_443"
    registry = SearchOSNavigationDestinationRegistry(
        run_id="run-1", request_id="request-1"
    )
    binding = registry.register(exact)
    assert registry.resolve(binding) == normalized.exact_url
    overlay = SearchOSNavigationExecutionOverlayV1.create(
        run_id="run-1",
        request_id="request-1",
        destination_binding_ref=binding,
        navigation_edge_ref=_ref("navigation_edge", "ipv6"),
        navigation_selection_ref=_ref("navigation_selection", "ipv6"),
        work_order_ref=_ref("work_order", "ipv6"),
        route_observation_ref=_ref("route_observation", "ipv6"),
        destination_registry=registry,
    )
    overlay.require_active()
    assert overlay.exact_execution_url == normalized.exact_url
    assert normalize_navigation_url("https://127.0.0.1/path").hostname == "127.0.0.1"
    assert (
        normalize_navigation_url("https://EXAMPLE.com/path").hostname == "example.com"
    )
    for invalid in (
        "https://2001:db8::1/path",
        "https://[2001:db8::1%25eth0]/path",
        "https://[2001:db8::zz]/path",
        "https://[2001:db8::1]:444/path",
        "https://user@[2001:db8::1]/path",
        "https://[2001:db8::1]/path?query=blocked",
    ):
        with pytest.raises(SearchOSNavigationError):
            registry.register(invalid)


@pytest.mark.parametrize("contributor_count", [7, 8, 9])
def test_per_option_contributor_limit_boundaries(
    contributor_count: int,
) -> None:
    registry = SearchOSNavigationDestinationRegistry(
        run_id="run-1", request_id="request-1"
    )
    state = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=[],
    )
    for ordinal in range(1, contributor_count + 1):
        state = admit_searchos_navigation_candidate_set(
            state,
            candidate_set=_same_destination_proposal(
                registry=registry,
                ordinal=ordinal,
            ),
        )
    option_state = next(iter(state["option_states_by_id"].values()))
    assert len(option_state["feasible_contributor_refs"]) == min(
        contributor_count, 8
    )
    assert state["overflow_totals"]["contributors"] == max(
        0, contributor_count - 8
    )


@pytest.mark.parametrize("occurrence_count", [47, 48, 49])
def test_extraction_occurrence_limit_boundaries(
    occurrence_count: int,
) -> None:
    draft = _draft(
        " ".join(
            f"[item {index}](/extract-{index})"
            for index in range(occurrence_count)
        )
    )
    assert len(draft.occurrences) == min(occurrence_count, 48)
    assert draft.extraction_counters["overflow_occurrences"] == max(
        0, occurrence_count - 48
    )


def test_eight_required_slots_can_each_represent_depth_two() -> None:
    required_slots = [f"slot-{index}" for index in range(1, 9)]
    state = build_searchos_navigation_retained_state(
        run_id="run-1",
        request_id="request-1",
        required_slot_ids=required_slots,
    )
    for index, slot_id in enumerate(required_slots, start=1):
        registry = SearchOSNavigationDestinationRegistry(
            run_id="run-1", request_id="request-1"
        )
        state = admit_searchos_navigation_candidate_set(
            state,
            candidate_set=_same_destination_proposal(
                registry=registry,
                ordinal=index,
                slot_id=slot_id,
                parent_depth=1,
            ),
        )
    assert state["retained_counts"] == {
        "stable_options": 8,
        "contributors": 8,
        "lineages": 8,
        "candidate_sets": 8,
        "deep_edges": 0,
    }
    assert set(state["slot_reservation_status"].values()) == {
        "lawful_depth_two_represented"
    }


def test_canonical_navigation_surfaces_are_url_free_before_custody() -> None:
    secret_path = "phase_unique_raw_path_96ad"  # pragma: allowlist secret
    raw_href = f"https://example.com/{secret_path}"
    _, _, proposal = _proposal(f"[destination]({raw_href})")
    serialized = json.dumps(proposal, sort_keys=True)
    assert raw_href not in serialized
    assert secret_path not in serialized
    assert "raw_href" not in serialized
    assert "selected_urls" not in serialized
    assert "available_urls" not in serialized


def test_runkernel_owns_candidate_admission_selection_and_logical_charges() -> None:
    exact_url = "https://example.com/runkernel-owned-destination-8d1f"
    _, registry, proposal = _proposal(f"[destination]({exact_url})")
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    kernel.state.searchos_navigation_state = (
        build_searchos_navigation_retained_state(
            run_id="run-1",
            request_id="request-1",
            required_slot_ids=["slot-1"],
        )
    )

    admission = kernel.authorize_searchos_navigation_candidate_admission(
        candidate_set=proposal
    )
    assert exact_url not in json.dumps(admission.to_dict(), sort_keys=True)
    kernel.reduce(
        Observation.from_action(
            admission,
            observation_type=(
                ObservationType.SEARCHOS_NAVIGATION_CANDIDATES_ADMITTED
            ),
            status=RunStageStatus.COMPLETED,
            payload={
                "admitted_navigation_candidate_set_ref": admission.inputs[
                    "predicted_admitted_candidate_set_ref"
                ]
            },
        )
    )
    window = build_searchos_navigation_candidate_window_v1(
        kernel.state.searchos_navigation_state,
        slot_id="slot-1",
    )
    candidate_ref = window["navigation_candidate_refs"][0]
    contributor = kernel.state.searchos_navigation_state["contributors_by_id"][
        candidate_ref["representative_contributor_ref"]["navigation_contributor_id"]
    ]
    decision = _prepare_pending_navigation_for_kernel(
        kernel,
        candidate_ref=candidate_ref,
        parent_custody_ref=contributor["parent_custody_ref"],
    )
    selection = kernel.authorize_searchos_navigation_selection(
        navigation_candidate_ref=candidate_ref,
        destination_registry=registry,
        judgment_decision_ref=decision,
    )
    assert exact_url not in json.dumps(selection.to_dict(), sort_keys=True)
    kernel.reduce(
        Observation.from_action(
            selection,
            observation_type=ObservationType.SEARCHOS_NAVIGATION_SELECTED,
            status=RunStageStatus.COMPLETED,
            payload={
                "navigation_selection_ref": selection.inputs[
                    "predicted_navigation_selection_ref"
                ],
                "navigation_edge_ref": selection.inputs[
                    "predicted_navigation_edge_ref"
                ],
            },
        )
    )
    state = kernel.state.searchos_navigation_state
    assert state["logical_edge_charges"] == 1
    assert state["logical_read_nomination_charges"] == 1
    assert len(state["selection_leases_by_id"]) == 1
    assert len(state["edges_by_id"]) == 1
    assert exact_url not in json.dumps(
        kernel.state.to_trace_projection().to_dict(), sort_keys=True
    )


def test_runkernel_successful_custody_is_first_canonical_exact_url_commit() -> None:
    exact_url = "https://example.com/first-canonical-commit-e1b7/"
    draft, registry, proposal = _proposal(f"[destination]({exact_url})")
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    kernel.state.searchos_navigation_state = (
        build_searchos_navigation_retained_state(
            run_id="run-1",
            request_id="request-1",
            required_slot_ids=["slot-1"],
        )
    )
    admission = kernel.authorize_searchos_navigation_candidate_admission(
        candidate_set=proposal
    )
    kernel.reduce(
        Observation.from_action(
            admission,
            observation_type=(
                ObservationType.SEARCHOS_NAVIGATION_CANDIDATES_ADMITTED
            ),
            status=RunStageStatus.COMPLETED,
            payload={
                "admitted_navigation_candidate_set_ref": admission.inputs[
                    "predicted_admitted_candidate_set_ref"
                ]
            },
        )
    )
    candidate_ref = build_searchos_navigation_candidate_window_v1(
        kernel.state.searchos_navigation_state,
        slot_id="slot-1",
    )["navigation_candidate_refs"][0]
    contributor = kernel.state.searchos_navigation_state["contributors_by_id"][
        candidate_ref["representative_contributor_ref"]["navigation_contributor_id"]
    ]
    decision = _prepare_pending_navigation_for_kernel(
        kernel,
        candidate_ref=candidate_ref,
        parent_custody_ref=contributor["parent_custody_ref"],
    )
    selection_action = kernel.authorize_searchos_navigation_selection(
        navigation_candidate_ref=candidate_ref,
        destination_registry=registry,
        judgment_decision_ref=decision,
    )
    kernel.reduce(
        Observation.from_action(
            selection_action,
            observation_type=ObservationType.SEARCHOS_NAVIGATION_SELECTED,
            status=RunStageStatus.COMPLETED,
            payload={
                "navigation_selection_ref": selection_action.inputs[
                    "predicted_navigation_selection_ref"
                ],
                "navigation_edge_ref": selection_action.inputs[
                    "predicted_navigation_edge_ref"
                ],
            },
        )
    )
    navigation_state = kernel.state.searchos_navigation_state
    selection = next(iter(navigation_state["selection_leases_by_id"].values()))
    edge = next(iter(navigation_state["edges_by_id"].values()))
    contributor = navigation_state["contributors_by_id"][
        edge["representative_contributor_ref"]["navigation_contributor_id"]
    ]
    binding = edge["destination_binding_ref"]
    bounded_text = "Durable bounded destination content"
    packet = build_navigation_fetch_read_content_packet_v2(
        run_id="run-1",
        request_id="request-1",
        answer_contract_ref=draft.answer_contract_ref,
        source_obligation_ref=draft.source_obligation_ref,
        component_ref=draft.component_ref,
        acquisition_work_order_ref=_ref("work_order", "destination"),
        route_observation_ref=_ref("route_observation", "destination"),
        execution_action_ref=_ref("action", "destination"),
        acquisition_artifact_ref=_ref("artifact", "destination"),
        physical_acquisition_ref=_ref(
            "physical_acquisition", "destination"
        ),
        navigation_destination_binding_ref=binding,
        navigation_edge_ref={
            "navigation_edge_id": edge["navigation_edge_id"],
            "navigation_edge_digest": edge["navigation_edge_digest"],
        },
        navigation_selection_ref={
            "navigation_selection_id": selection[
                "navigation_selection_id"
            ],
            "navigation_selection_digest": selection[
                "navigation_selection_digest"
            ],
        },
        navigation_lineage_snapshot_ref=edge[
            "navigation_lineage_snapshot_ref"
        ],
        representative_contributor_ref=edge[
            "representative_contributor_ref"
        ],
        parent_custody_ref=edge["parent_custody_ref"],
        operation_identity_key=(
            f"read-navigation:{binding['physical_identity_digest']}"
        ),
        attempted_url=exact_url,
        durable_source_url=exact_url,
        provider="linkup",
        operation="fetch",
        bounded_text=bounded_text,
        retained_digest=_digest_text(bounded_text),
        retained_character_count=len(bounded_text),
        content_type="text/markdown",
        http_status=200,
        content_title="Destination",
    )
    packet_registry = SearchOSNavigationPacketCommitRegistry(
        run_id="run-1", request_id="request-1"
    )
    packet_commit_ref = packet_registry.register(packet)
    packet_ref = fetch_read_content_packet_ref_from_packet(packet)
    commit_action = (
        kernel.authorize_searchos_navigation_physical_custody_commit(
            packet_commit_ref=packet_commit_ref,
            fetch_read_content_packet_ref=packet_ref,
            navigation_selection_ref=selection_action.inputs[
                "predicted_navigation_selection_ref"
            ],
            navigation_edge_ref=selection_action.inputs[
                "predicted_navigation_edge_ref"
            ],
            destination_binding_ref=binding,
            physical_identity_digest=binding[
                "physical_identity_digest"
            ],
            operation_identity_key=(
                f"read-navigation:{binding['physical_identity_digest']}"
            ),
        )
    )
    precommit_trace = json.dumps(
        kernel.state.to_trace_projection().to_dict(), sort_keys=True
    )
    assert exact_url not in precommit_trace

    committed = admit_navigation_packet_commit_to_evidence_ledger(
        evidence_ledger=kernel.state.evidence_ledger,
        packet_registry=packet_registry,
        packet_commit_ref=packet_commit_ref,
    )
    physical = build_searchos_navigation_physical_custody_record_v2(
        fetch_read_content_packet=committed.committed_fetch_read_packet,
        evidence_ledger_custody_ref=(
            committed.evidence_ledger_custody_ref
        ),
    )
    use_custody = build_searchos_navigation_use_custody_ref_v2(
        slot_ref=contributor["slot_ref"],
        selection_ref=selection_action.inputs[
            "predicted_navigation_selection_ref"
        ],
        edge_ref=selection_action.inputs[
            "predicted_navigation_edge_ref"
        ],
        physical_custody_ref=searchos_navigation_physical_custody_ref(
            physical
        ),
        fetch_read_content_packet_ref=packet_ref,
        evidence_ledger_custody_ref=(
            committed.evidence_ledger_custody_ref
        ),
        destination_binding_ref=binding,
        physical_acquisition_origin="navigation_candidate",
        navigation_depth=edge["child_depth"],
        ancestor_physical_identity_digests=[
            contributor["parent_custody_ref"][
                "physical_identity_digest"
            ]
        ],
    )
    kernel.reduce(
        Observation.from_action(
            commit_action,
            observation_type=(
                ObservationType.ACQUISITION_NAVIGATION_PHYSICAL_CUSTODY_COMMITTED
            ),
            status=RunStageStatus.COMPLETED,
            payload={
                "packet_commit_ref": packet_commit_ref,
                "committed_fetch_read_content_packet": (
                    committed.committed_fetch_read_packet
                ),
                "evidence_ledger_observation": committed.observation.to_dict(),
                "evidence_ledger_custody_ref": (
                    committed.evidence_ledger_custody_ref
                ),
                "navigation_physical_custody_record": physical,
                "navigation_use_custody_ref": use_custody,
            },
        )
    )
    retained = kernel.state.searchos_navigation_state[
        "physical_custody_by_digest"
    ][binding["physical_identity_digest"]]
    assert retained["attempted_url"] == exact_url
    assert retained["durable_source_url"] == exact_url
    assert len(
        kernel.state.searchos_navigation_state["use_custody_refs_by_id"]
    ) == 1
    assert exact_url in json.dumps(
        kernel.state.evidence_ledger.to_projection().to_dict(),
        sort_keys=True,
    )
