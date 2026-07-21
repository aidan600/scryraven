"""Offline phase-focus proof for bounded SearchOS breadcrumb contracts."""

from __future__ import annotations

import json
from hashlib import sha256

import pytest

from core.searchos_navigation_runtime import (
    NAVIGATION_CANDIDATE_SET_CAPACITY_EXHAUSTED,
    NAVIGATION_DESTINATION_BINDING_UNAVAILABLE,
    NAVIGATION_EFFECTIVE_BASE_OUT_OF_SCOPE,
    NAVIGATION_EXTRACTED_OCCURRENCE_CEILING,
    NAVIGATION_MODEL_WINDOW_CEILING,
    NAVIGATION_QUERY_LOCATOR_NOT_SUPPORTED,
    SearchOSNavigationDestinationRegistry,
    SearchOSNavigationError,
    admit_searchos_navigation_candidate_set,
    admit_searchos_navigation_selection,
    build_searchos_navigation_candidate_set_v1,
    build_searchos_navigation_candidate_window_v1,
    build_searchos_navigation_retained_state,
    discard_navigation_extraction_draft,
    extract_searchos_navigation_draft_v1,
    mark_searchos_navigation_slot_structurally_terminal,
    navigation_physical_operation_identity,
    normalize_navigation_url,
    record_searchos_navigation_contributor_failure,
    record_searchos_navigation_destination_terminal,
)


def _digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _digest(seed: str) -> str:
    return _digest_text(seed)


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
    packet_ref = {
        "fetch_read_content_packet_id": packet["fetch_read_content_packet_id"],
        "fetch_read_content_packet_digest": packet[
            "fetch_read_content_packet_digest"
        ],
    }
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
    secret = "phase_unique_query_secret_4f57"
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
    with pytest.raises(
        SearchOSNavigationError,
        match=NAVIGATION_QUERY_LOCATOR_NOT_SUPPORTED,
    ):
        registry.register(f"https://example.com/path?token={secret}")


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
            + current["destination_binding_ref"]["physical_identity_digest"]
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


def test_canonical_navigation_surfaces_are_url_free_before_custody() -> None:
    secret_path = "phase_unique_raw_path_96ad"
    raw_href = f"https://example.com/{secret_path}"
    _, _, proposal = _proposal(f"[destination]({raw_href})")
    serialized = json.dumps(proposal, sort_keys=True)
    assert raw_href not in serialized
    assert secret_path not in serialized
    assert "raw_href" not in serialized
    assert "selected_urls" not in serialized
    assert "available_urls" not in serialized

