from __future__ import annotations

import json
import pickle
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from inspect import signature
from pathlib import Path

import pytest

from core.run_kernel import RunKernel, RunKernelTransitionError
from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_JUDGMENT_REQUEST_SCHEMA_VERSION,
    SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION,
    SEARCHOS_NAVIGATION_JUDGMENT_REQUEST_SCHEMA_VERSION,
    SearchOSJudgmentAction,
    SearchOSRuntimeError,
    SearchOSSlotPosture,
    begin_searchos_judgment_round,
    build_candidate_use_window_v1,
    build_searchos_initial_state,
    build_searchos_navigation_judgment_request_v1,
    build_searchos_policy_snapshot,
    build_searchos_read_custody_material_ref,
    charge_searchos_judgment_call,
    record_searchos_candidate_window,
    reduce_searchos_judgment_decision,
    searchos_policy_profile,
    searchos_policy_snapshot_ref,
    validate_searchos_judgment_model_output,
    validate_searchos_state,
)
from core.searchos_navigation_runtime import (
    NAVIGATION_BINDING_UNAVAILABLE,
    NAVIGATION_EXTRACTION_LIMIT,
    NAVIGATION_PENDING_EXECUTION,
    NAVIGATION_SELECTION_ADMITTED,
    NAVIGATION_SELECTION_AUTHORITY_REJECTED,
    NAVIGATION_SELECTION_UNAVAILABLE,
    EphemeralNavigationLocatorStore,
    NavigationOption,
    NavigationRuntimeError,
    admit_navigation_options_from_markdown,
    execute_navigation_selection,
    extract_bounded_navigation_links,
    navigation_candidate_ref,
    navigation_destination_eligibility,
    normalize_navigation_destination,
    project_navigation_window,
    reduce_navigation_selection_observation,
    sanitize_navigation_source_text,
    scrub_navigation_relationship_label,
)


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _ref(name: str, suffix: str) -> dict[str, str]:
    return {f"{name}_id": f"{name}:{suffix}", f"{name}_digest": _digest(suffix)}


def _refresh_state(state: dict[str, object]) -> dict[str, object]:
    core = {
        key: deepcopy(value)
        for key, value in state.items()
        if key not in {"state_id", "state_digest", "replay_identity"}
    }
    slots = dict(core["slots_by_id"])
    for slot_id, raw_slot in slots.items():
        slot = dict(raw_slot)
        slot.pop("slot_state_digest", None)
        slot["slot_state_digest"] = _digest(slot)
        slots[slot_id] = slot
    core["slots_by_id"] = slots
    digest = _digest(core)
    return {
        **core,
        "state_id": f"searchos-state:{digest[:24]}",
        "state_digest": digest,
        "replay_identity": f"searchos-state:{digest}",
    }


def _refresh_policy(policy: dict[str, object]) -> dict[str, object]:
    core = {
        key: deepcopy(value)
        for key, value in policy.items()
        if key not in {"policy_snapshot_id", "policy_snapshot_digest", "replay_identity"}
    }
    digest = _digest(core)
    return {
        **core,
        "policy_snapshot_id": f"searchos-policy:{digest[:24]}",
        "policy_snapshot_digest": digest,
        "replay_identity": f"searchos-policy:{digest}",
    }


def _redigest_option(value: dict[str, object]) -> dict[str, object]:
    identity = {
        key: deepcopy(value[key])
        for key in (
            "schema_version",
            "owner",
            "slot_id",
            "destination_binding_ref",
            "parent_read_custody_ref",
            "child_depth",
            "ancestor_physical_identity_digests",
            "bounded_relationship_context",
            "admission_ordinal",
        )
    }
    core = {
        **identity,
        "revision": value["revision"],
        "disposition": value["disposition"],
        "active_selection_ref": deepcopy(value["active_selection_ref"]),
    }
    return {
        **core,
        "navigation_option_id": f"searchos-navigation-option:{_digest(identity)[:24]}",
        "navigation_option_digest": _digest(core),
    }


def _candidate_ref_from_option(value: dict[str, object]) -> dict[str, object]:
    option_ref = {
        "navigation_option_id": value["navigation_option_id"],
        "navigation_option_digest": value["navigation_option_digest"],
        "revision": value["revision"],
    }
    digest = _digest({"navigation_option_ref": option_ref})
    return {
        "navigation_candidate_id": f"searchos-navigation-candidate:{digest[:24]}",
        "navigation_candidate_digest": digest,
        "navigation_option_ref": option_ref,
    }


def _state_with_parent(
    *,
    profile_name: str = "Balanced",
    navigation_open: bool = True,
    parent_url: str = "https://example.com/root",
) -> tuple[dict[str, object], dict[str, object]]:
    policy = build_searchos_policy_snapshot(
        run_id="run-1",
        request_id="request-1",
        profile_name=profile_name,
        navigation_runtime_open=navigation_open,
    )
    state = build_searchos_initial_state(
        run_id="run-1",
        request_id="request-1",
        answer_contract_ref=_ref("answer_contract", "current"),
        policy_snapshot=policy,
        active_slots=[
            {
                "slot_id": "slot-1",
                "component_ref": _ref("component", "one"),
                "source_obligation_ref": _ref("source_obligation", "one"),
                "requirement_posture": "required",
            }
        ],
        initial_candidate_state_ref=_ref("candidate_state", "revision-1"),
    )
    slot = dict(state["slots_by_id"]["slot-1"])
    candidate_ref = {
        **_ref("candidate_use_option", "parent"),
        "slot_id": "slot-1",
        "normalized_url": parent_url,
    }
    custody = build_searchos_read_custody_material_ref(
        slot_ref=slot["slot_ref"],
        candidate_use_option_ref=candidate_ref,
        custody_record={
            "normalized_url": parent_url,
            "fetch_read_content_packet_ref": _ref("fetch_read_content_packet", "parent"),
            "evidence_ledger_custody_ref": _ref("evidence_ledger_custody", "parent"),
            "evidence_ledger_candidate_id": "ledger-candidate:parent",
            "terminal_receipt_ref": _ref("terminal_receipt", "parent"),
            "custody_authorization_ref": _ref("custody_authorization", "parent"),
            "bounded_content_present": True,
        },
        same_normalized_url_reused=False,
    )
    slot["custody_refs"] = [custody]
    state = deepcopy(state)
    state["slots_by_id"]["slot-1"] = slot
    return _refresh_state(state), custody


def _admit(
    markdown: str,
    *,
    profile_name: str = "Balanced",
    parent_url: str = "https://example.com/root",
) -> tuple[dict[str, object], dict[str, object], EphemeralNavigationLocatorStore]:
    state, custody = _state_with_parent(
        profile_name=profile_name,
        parent_url=parent_url,
    )
    store = EphemeralNavigationLocatorStore(run_id="run-1", request_id="request-1")
    admitted, summary = admit_navigation_options_from_markdown(
        state,
        slot_id="slot-1",
        parent_read_custody_ref=custody,
        parent_url=parent_url,
        parent_depth=0,
        ancestor_physical_identity_digests=(),
        markdown_text=markdown,
        locator_store=store,
    )
    return admitted, summary, store


def _record_empty_candidate_window(state: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    slot = state["slots_by_id"]["slot-1"]
    window = build_candidate_use_window_v1(
        slot_ref=slot["slot_ref"],
        ordered_options=(),
        window_ordinal=1,
        policy_snapshot=state["policy_snapshot"],
    )
    return record_searchos_candidate_window(state, window=window), window


def _pending_navigation() -> tuple[
    dict[str, object],
    EphemeralNavigationLocatorStore,
    dict[str, object],
    dict[str, object],
]:
    state, _, store = _admit("[child](/child)")
    state, candidate_window = _record_empty_candidate_window(state)
    state, reservation = begin_searchos_judgment_round(state, slot_ids=["slot-1"])
    state, charge = charge_searchos_judgment_call(state, reservation_ref=reservation, slot_id="slot-1")
    navigation_window = project_navigation_window(state, slot_id="slot-1")
    custody = state["slots_by_id"]["slot-1"]["custody_refs"][0]
    request = build_searchos_navigation_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=candidate_window,
        navigation_window=navigation_window,
        read_custody_refs=[custody],
    )
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION,
            "action": SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value,
            "navigation_candidate_id": navigation_window[0]["navigation_candidate_ref"][
                "navigation_candidate_id"
            ],
            "reason": "The current source identifies a bounded next page.",
            "read_custody_assessments": [
                {
                    "read_custody_material_id": custody["read_custody_material_id"],
                    "reason_code": "needed_detail_absent",
                }
            ],
        },
    )
    pending = reduce_searchos_judgment_decision(state, decision=decision)
    return pending, store, decision, navigation_window[0]["navigation_candidate_ref"]


@pytest.mark.parametrize(
    ("value", "exact", "port_posture"),
    [
        ("https://EXAMPLE.com/a#section", "https://example.com/a", "implicit_default_443"),
        ("https://example.com:443/a", "https://example.com:443/a", "explicit_default_443"),
        ("https://example.com:444/a", "https://example.com:444/a", "explicit_nondefault_444"),
        ("https://[2001:0db8::1]:443/a/", "https://[2001:db8::1]:443/a/", "explicit_default_443"),
    ],
)
def test_normalization_preserves_port_fragment_and_trailing_slash_identity(
    value: str, exact: str, port_posture: str
) -> None:
    normalized = normalize_navigation_destination(value)
    assert normalized["exact_url"] == exact
    assert normalized["port_posture"] == port_posture
    assert "#" not in normalized["exact_url"]

    slash = normalize_navigation_destination("https://example.com/a/")
    no_slash = normalize_navigation_destination("https://example.com/a")
    assert slash["physical_identity_digest"] != no_slash["physical_identity_digest"]


@pytest.mark.parametrize(
    "value",
    [
        "ftp://example.com/a",
        "https://user:pass@example.com/a",  # pragma: allowlist secret
        "https://2001:db8::1/a",
        "https://[2001:db8::1%25eth0]/a",
        "https://[2001:db8::zz]/a",
        "https://example.com:bad/a",
        "https://exämple.com/a",
    ],
)
def test_normalization_rejects_unsupported_or_malformed_authority(value: str) -> None:
    with pytest.raises(NavigationRuntimeError):
        normalize_navigation_destination(value)


def test_navigation_eligibility_separates_lawful_normalization_from_policy() -> None:
    implicit = normalize_navigation_destination("http://example.com/root")
    implicit_upgrade = normalize_navigation_destination("https://example.com/child")
    explicit = normalize_navigation_destination("http://example.com:80/root")
    nondefault = normalize_navigation_destination("http://example.com:8080/root")
    downgrade = normalize_navigation_destination("http://example.com/child")

    assert navigation_destination_eligibility(implicit, implicit_upgrade)[0] is True
    assert navigation_destination_eligibility(explicit, downgrade)[0] is False
    assert navigation_destination_eligibility(nondefault, downgrade) == (
        False,
        "navigation_nondefault_port_ineligible",
    )
    assert (
        navigation_destination_eligibility(normalize_navigation_destination("https://example.com/root"), downgrade)[0]
        is False
    )
    assert (
        navigation_destination_eligibility(implicit, normalize_navigation_destination("https://www.example.com/child"))[
            0
        ]
        is False
    )


def test_extraction_is_supported_ordered_bounded_and_query_safe() -> None:
    text = " ".join(
        [
            "[absolute](https://example.com/a)",
            "[relative](../b)",
            "[balanced](../topic_(one))",
            "<https://example.com/c>",
            "[self](#fragment)",
            "[query](https://example.com/q?token=phase_unique_query_secret)",
            "[other](https://other.example/a)",
            "![image](https://example.com/image.png)",
            "[reference][id]",
            '<a href="https://example.com/html">html</a>',
            "naked https://example.com/naked",
        ]
    )
    extracted = extract_bounded_navigation_links(markdown_text=text, parent_url="https://example.com/root")
    assert [item["normalized_destination"]["path"] for item in extracted["occurrences"]] == [
        "/a",
        "/b",
        "/topic_(one)",
        "/c",
    ]
    assert extracted["rejection_counts"]["navigation_self_link"] == 1
    assert extracted["rejection_counts"]["navigation_query_not_supported"] == 1
    assert extracted["rejection_counts"]["navigation_hostname_changed"] == 1

    overflow = extract_bounded_navigation_links(
        markdown_text=" ".join(f"[item {index}](/item-{index})" for index in range(NAVIGATION_EXTRACTION_LIMIT + 1)),
        parent_url="https://example.com/root",
    )
    assert len(overflow["occurrences"]) == NAVIGATION_EXTRACTION_LIMIT
    assert overflow["overflow_count"] == 1
    sanitized = sanitize_navigation_source_text(text)
    assert "phase_unique_query_secret" not in sanitized
    assert "https://" not in sanitized
    assert "absolute" in sanitized and "relative" in sanitized


@pytest.mark.parametrize(
    "label",
    [
        "https://example.com/private",
        "www.example.com",
        "example.com.",
        "(example.com)",
        "192.168.1.1",
        "host.example:8443",
        "/private/path",
        "private/path",
        "foo\\bar",
        "./relative",
        "../relative",
        "next?token=value",
        "person@example.com",
        "user:password@example.com",  # pragma: allowlist secret
        "api_key=credential",
        "%2Fprivate%2Fpath",
        "safe\x00control",
    ],
)
def test_relationship_labels_use_fixed_fallback_for_locator_like_text(label: str) -> None:
    assert scrub_navigation_relationship_label(label) == "linked page"


@pytest.mark.parametrize(
    "label",
    [
        "2001:db8::1",
        "[2001:db8::1]",
        "[2001:db8::1]:443",
        "2001:0db8:0000:0000:0000:0000:0000:0001",
        "See [2001:db8::1].",
        "Destination: [2001:db8::1]:443",
        "fd00::1",
        "fe80::1",
    ],
)
def test_ipv6_label_scrubber_uses_fixed_privacy_fallback(label: str) -> None:
    assert scrub_navigation_relationship_label(label) == "linked page"


@pytest.mark.parametrize(
    "label",
    [
        "Section 2: Results",
        "Status: complete",
        "Ratio 2:1",
        "Chapter 4: Methods",
    ],
)
def test_ipv6_label_scrubber_preserves_colon_bearing_prose(label: str) -> None:
    assert scrub_navigation_relationship_label(label) == label


def test_locator_store_is_exact_nonserializable_staged_and_run_bounded() -> None:
    store = EphemeralNavigationLocatorStore(run_id="run-1", request_id="request-1")
    normalized = normalize_navigation_destination("https://example.com/private")
    binding = store.stage(normalized)
    assert store.staged_count == 1 and store.committed_count == 0
    assert store.resolve(binding) is None
    with pytest.raises(TypeError):
        pickle.dumps(store)
    store.commit(binding)
    assert store.resolve(binding) == "https://example.com/private"
    altered = {**binding, "full_destination_digest": _digest("altered")}
    assert store.resolve(altered) is None
    second = store.stage(normalize_navigation_destination("https://example.com/discard"))
    store.discard_staged([second])
    assert store.staged_count == 0 and store.committed_count == 1
    assert store.consume_once_for_execution(binding) == ("https://example.com/private")
    with pytest.raises(NavigationRuntimeError, match="binding_unavailable"):
        store.consume_once_for_execution(binding)
    assert store.resolve(binding) is None
    store.discard_all()
    assert store.committed_count == 0
    with pytest.raises(NavigationRuntimeError, match="store_closed"):
        store.resolve(binding)


def test_options_live_under_searchos_and_new_destinations_remain_ephemeral() -> None:
    privacy_sentinel_path = "phase_unique_breadcrumb_destination_51af"
    exact = f"https://example.com/{privacy_sentinel_path}"
    state, summary, store = _admit(f"[safe label]({exact}) [query](/blocked?secret=value)")
    assert summary["admitted_option_count"] == 1
    assert summary["rejection_counts"] == {"navigation_query_not_supported": 1}
    assert store.committed_count == 1 and store.staged_count == 0
    assert "navigation" in state
    [option] = state["navigation"]["options_by_id"].values()
    assert NavigationOption.from_dict(option).disposition == "selectable"
    serialized = json.dumps(state, sort_keys=True)
    assert exact not in serialized
    assert privacy_sentinel_path not in serialized
    assert "destination_binding_ref" in serialized
    assert "searchos_navigation_state" not in serialized


@pytest.mark.parametrize(
    ("defect", "value"),
    [
        ("label", "https://example.com/private"),
        ("label", "private/path"),
        ("label", "(example.com)"),
        ("label", "192.168.1.1"),
        ("binding_id", "navigation-binding:https://example.com/private"),
        ("active_extra", "https://example.com/private"),
        ("selectable_active", "selection"),
        ("pending_empty", "selection"),
        ("context_extra", "selection"),
        ("depth", "selection"),
        ("cycle", "selection"),
    ],
)
def test_canonical_boundary_redigested_option_replays_fail_closed(defect: str, value: str) -> None:
    state, _, _ = _admit("[safe label](/child)")
    raw = deepcopy(next(iter(state["navigation"]["options_by_id"].values())))
    selection_digest = _digest("canonical-selection")
    selection_ref = {
        "navigation_selection_id": f"searchos-navigation-selection:{selection_digest[:24]}",
        "navigation_selection_digest": selection_digest,
    }
    if defect == "label":
        raw["bounded_relationship_context"]["relationship_label"] = value
    elif defect == "binding_id":
        raw["destination_binding_ref"]["destination_binding_id"] = value
    elif defect == "active_extra":
        raw["disposition"] = NAVIGATION_PENDING_EXECUTION
        raw["active_selection_ref"] = {**selection_ref, "destination_url": value}
    elif defect == "selectable_active":
        raw["active_selection_ref"] = selection_ref
    elif defect == "pending_empty":
        raw["disposition"] = NAVIGATION_PENDING_EXECUTION
        raw["active_selection_ref"] = {}
    elif defect == "context_extra":
        raw["bounded_relationship_context"]["unexpected"] = value
    elif defect == "depth":
        raw["bounded_relationship_context"]["child_depth"] = 7
    else:
        raw["ancestor_physical_identity_digests"] = [raw["destination_binding_ref"]["physical_identity_digest"]]
    with pytest.raises(NavigationRuntimeError):
        NavigationOption.from_dict(_redigest_option(raw))


def test_canonical_boundary_valid_pending_selection_ref_replays() -> None:
    state, _, _ = _admit("[safe label](/child)")
    option = NavigationOption.from_dict(next(iter(state["navigation"]["options_by_id"].values())))
    selection_digest = _digest("canonical-selection")
    pending = replace(
        option,
        disposition=NAVIGATION_PENDING_EXECUTION,
        active_selection_ref={
            "navigation_selection_id": f"searchos-navigation-selection:{selection_digest[:24]}",
            "navigation_selection_digest": selection_digest,
        },
    )
    assert NavigationOption.from_dict(pending.to_dict()) == pending
    binding_id = pending.destination_binding_ref["destination_binding_id"]
    assert "run-1" not in binding_id and "request-1" not in binding_id


@pytest.mark.parametrize(
    "label",
    [
        "2001:db8::1",
        "[2001:db8::1]",
        "[2001:db8::1]:443",
    ],
)
def test_ipv6_label_redigested_option_replay_fails_canonical_validation(label: str) -> None:
    state, _, _ = _admit("[safe label](/child)")
    raw = deepcopy(next(iter(state["navigation"]["options_by_id"].values())))
    raw["bounded_relationship_context"]["relationship_label"] = label
    with pytest.raises(
        NavigationRuntimeError,
        match="navigation_relationship_label_not_canonical",
    ):
        NavigationOption.from_dict(_redigest_option(raw))


def test_navigation_ineligible_parent_keeps_existing_read_custody_unchanged() -> None:
    state, custody = _state_with_parent(parent_url="https://example.com:444/root")
    original = deepcopy(state)
    store = EphemeralNavigationLocatorStore(run_id="run-1", request_id="request-1")
    admitted, summary = admit_navigation_options_from_markdown(
        state,
        slot_id="slot-1",
        parent_read_custody_ref=custody,
        parent_url="https://example.com:444/root",
        parent_depth=0,
        ancestor_physical_identity_digests=(),
        markdown_text="[child](https://example.com:444/child)",
        locator_store=store,
    )
    assert admitted["slots_by_id"]["slot-1"]["custody_refs"] == original["slots_by_id"]["slot-1"]["custody_refs"]
    assert summary["admitted_option_count"] == 0
    assert summary["rejection_counts"] == {"navigation_nondefault_port_ineligible": 1}
    assert store.committed_count == 0


def test_canonical_boundary_ancestor_cycle_is_rejected_before_locator_staging() -> None:
    state, custody = _state_with_parent(parent_url="https://example.com/b")
    parent_custody = deepcopy(state["slots_by_id"]["slot-1"]["custody_refs"])
    ancestor = normalize_navigation_destination("https://example.com/a")
    store = EphemeralNavigationLocatorStore(run_id="run-1", request_id="request-1")
    admitted, summary = admit_navigation_options_from_markdown(
        state,
        slot_id="slot-1",
        parent_read_custody_ref=custody,
        parent_url="https://example.com/b",
        parent_depth=1,
        ancestor_physical_identity_digests=(ancestor["physical_identity_digest"],),
        markdown_text="[ancestor](/a) [lawful sibling](/c)",
        locator_store=store,
    )
    assert summary == {
        "admitted_option_count": 1,
        "rejection_counts": {"navigation_ancestor_cycle": 1},
        "overflow_count": 0,
    }
    assert store.staged_count == 0 and store.committed_count == 1
    [option_value] = admitted["navigation"]["options_by_id"].values()
    option = NavigationOption.from_dict(option_value)
    assert option.destination_binding_ref["physical_identity_digest"] != ancestor["physical_identity_digest"]
    assert store.resolve(option.destination_binding_ref) == "https://example.com/c"
    window = project_navigation_window(admitted, slot_id="slot-1")
    assert len(window) == 1 and window[0]["relationship_label"] == "lawful sibling"
    assert admitted["slots_by_id"]["slot-1"]["custody_refs"] == parent_custody


def test_navigation_window_is_transient_deterministic_and_advances() -> None:
    state, _, _ = _admit(" ".join(f"[item {index}](/item-{index})" for index in range(13)))
    first = project_navigation_window(state, slot_id="slot-1")
    assert len(first) == 12
    assert [item["source_link_ordinal"] for item in first] == list(range(1, 13))
    assert "window" not in state["navigation"]

    first_id = first[0]["navigation_candidate_ref"]["navigation_option_ref"]["navigation_option_id"]
    current = NavigationOption.from_dict(state["navigation"]["options_by_id"][first_id])
    state = deepcopy(state)
    state["navigation"]["options_by_id"][first_id] = replace(
        current, disposition=NAVIGATION_BINDING_UNAVAILABLE
    ).to_dict()
    state = _refresh_state(state)
    advanced = project_navigation_window(state, slot_id="slot-1")
    assert len(advanced) == 12
    assert advanced[-1]["source_link_ordinal"] == 13


@pytest.mark.parametrize(
    ("profile", "depth", "selections", "edges"),
    [("Fast", 1, 1, 8), ("Balanced", 2, 2, 16), ("Deep", 3, 3, 24)],
)
def test_policy_snapshots_have_exact_immutable_navigation_leashes(
    profile: str, depth: int, selections: int, edges: int
) -> None:
    policy = searchos_policy_profile(profile)
    assert not hasattr(policy, "navigation_max_depth")
    closed = build_searchos_policy_snapshot(run_id="run-1", request_id="request-1", profile_name=profile)
    assert not {
        "navigation_max_depth",
        "navigation_selections_per_slot",
        "navigation_edges_per_run",
    }.intersection(closed)
    snapshot = build_searchos_policy_snapshot(
        run_id="run-1",
        request_id="request-1",
        profile_name=profile,
        navigation_runtime_open=True,
    )
    assert (
        snapshot["navigation_max_depth"],
        snapshot["navigation_selections_per_slot"],
        snapshot["navigation_edges_per_run"],
    ) == (depth, selections, edges)


def test_canonical_boundary_closed_policy_and_state_include_boundary_a_recovery() -> None:
    expected_policy = {
        "schema_version": "searchos_policy_profile_v1",
        "owner": "RunKernel.SearchOSIterativeJudgment",
        "profile_name": "Balanced",
        "maximum_active_slots": 8,
        "candidate_use_window_size": 12,
        "minimum_reserved_judgment_calls_per_required_slot": 3,
        "additional_judgment_call_pool_per_active_slot": 2,
        "candidate_windows_per_slot": 3,
        "candidate_waves_per_slot": 3,
        "read_nominations_per_slot": 3,
        "followup_query_nominations_per_slot": 2,
        "interpretation_bindings_per_semantic_obligation": 1,
        "orientation_refinements_per_slot": 1,
        "navigation_runtime_open": False,
        "post_analyst_reentry_runtime_open": False,
        "existing_gap_recovery_policy": {
            "schema_version": "searchos_existing_gap_recovery_policy_v1",
            "runtime_open": False,
            "maximum_cycles_per_run": 1,
            "same_limits_for_all_profiles": True,
            "required_gaps_prioritized": True,
            "optional_gap_recovery_authorized": False,
            "whole_run_lease_required": True,
        },
        "recovery_policy": {
            "schema_version": "searchos_recovery_policy_v2",
            "runtime_open": False,
            "maximum_total_cycles_per_run": 2,
            "maximum_existing_component_cycles_per_run": 1,
            "maximum_searched_premise_cycles_per_run": 1,
            "maximum_searched_generation": 2,
            "one_linear_active_cycle": True,
            "one_searched_premise_per_generation": True,
            "generation_three_rejected_before_work": True,
            "whole_run_lease_required": True,
        },
        "provisional_maximum_leash": True,
        "consumption_target": False,
        "permanently_calibrated": False,
        "run_id": "run-baseline-identity",
        "request_id": "request-baseline-identity",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "prompt_can_override": False,
        "adapter_can_override": False,
        "environment_can_override": False,
        "policy_snapshot_id": "searchos-policy:9e644053264baac7c6a0c8d7",
        "policy_snapshot_digest": "9e644053264baac7c6a0c8d7603f9d8f1934ac2e2e6e1a2ea7f3126f0e24d4a2",  # pragma: allowlist secret
        "replay_identity": "searchos-policy:9e644053264baac7c6a0c8d7603f9d8f1934ac2e2e6e1a2ea7f3126f0e24d4a2",  # pragma: allowlist secret
    }
    policy = build_searchos_policy_snapshot(
        run_id="run-baseline-identity",
        request_id="request-baseline-identity",
        profile_name="Balanced",
    )
    assert policy == expected_policy
    assert (
        searchos_policy_snapshot_ref(expected_policy)["policy_snapshot_digest"]
        == expected_policy["policy_snapshot_digest"]
    )
    state = build_searchos_initial_state(
        run_id="run-baseline-identity",
        request_id="request-baseline-identity",
        answer_contract_ref=_ref("answer_contract", "baseline"),
        policy_snapshot=policy,
        active_slots=[
            {
                "slot_id": "slot-baseline",
                "component_ref": _ref("component", "baseline"),
                "source_obligation_ref": _ref("source_obligation", "baseline"),
                "requirement_posture": "required",
            }
        ],
        initial_candidate_state_ref=_ref("candidate_state", "baseline"),
    )
    assert (
        state["state_digest"]
        == "e3394f10c8a9694e78a461b94648bf4b7a7503a7055f63fb9250d9d1b3591a98"  # pragma: allowlist secret
    )
    assert state["state_id"] == "searchos-state:e3394f10c8a9694e78a461b9"
    assert state["replay_identity"] == (
        "searchos-state:e3394f10c8a9694e78a461b94648bf4b7a7503a7055f63fb9250d9d1b3591a98"  # pragma: allowlist secret
    )
    assert set(state) == {
        "schema_version",
        "owner",
        "run_id",
        "request_id",
        "answer_contract_ref",
        "policy_snapshot_ref",
        "policy_snapshot",
        "initial_candidate_state_ref",
        "current_candidate_state_ref",
        "iteration_candidate_set_refs",
        "active_slot_ids",
        "required_slot_ids",
        "judgment_eligible_required_slot_ids",
        "optional_slot_ids",
        "slots_by_id",
        "semantic_obligations_by_id",
        "semantic_obligation_ids_by_component",
        "budget",
        "semantic_handoff_refs",
        "interpretation_binding_history",
        "existing_gap_recovery_runtime_open",
        "existing_gap_recovery_purpose_refs",
        "existing_gap_recovery_lease_refs",
        "existing_gap_recovery_cycles",
        "active_existing_gap_recovery_cycle_ref",
        "existing_gap_recovery_terminal_aggregate",
        "existing_gap_recovery_terminal_aggregate_ref",
        "recovery_lease",
        "recovery_lease_history",
        "recovery_cycle_admission_history",
        "recovery_cycle_terminal_history",
        "recovery_expenditure_history",
        "active_recovery_cycle_ref",
        "recovery_terminal_aggregate",
        "readiness_projection_ref",
        "required_needs_block_ref",
        "required_needs_block",
        "comprehensive_recovery_runtime_open",
        "known_url_read_runtime_open",
        "search_attached_content_custody_runtime_open",
        "whole_run_stopping_runtime_open",
        "canonical_state",
        "trace_only",
        "storage_only",
        "state_id",
        "state_digest",
        "replay_identity",
    }
    assert validate_searchos_state(state) == state
    assert "navigation" not in state
    assert not any("navigation" in key for key in state["slots_by_id"]["slot-baseline"])


def test_canonical_boundary_policy_validator_rejects_partial_or_contradictory_limits() -> None:
    closed = build_searchos_policy_snapshot(run_id="run-1", request_id="request-1", profile_name="Balanced")
    with pytest.raises(SearchOSRuntimeError, match="closed navigation policy"):
        searchos_policy_snapshot_ref(_refresh_policy({**closed, "navigation_max_depth": 2}))
    opened = build_searchos_policy_snapshot(
        run_id="run-1",
        request_id="request-1",
        profile_name="Balanced",
        navigation_runtime_open=True,
    )
    partial = deepcopy(opened)
    partial.pop("navigation_edges_per_run")
    with pytest.raises(SearchOSRuntimeError, match="opened navigation policy"):
        searchos_policy_snapshot_ref(_refresh_policy(partial))
    with pytest.raises(SearchOSRuntimeError, match="opened navigation policy"):
        searchos_policy_snapshot_ref(_refresh_policy({**opened, "navigation_max_depth": 99}))


def test_navigation_judgment_is_exact_ref_only_and_pending_is_zero_charge() -> None:
    state, _, _ = _admit("[child](/child)")
    state, candidate_window = _record_empty_candidate_window(state)
    state, reservation = begin_searchos_judgment_round(state, slot_ids=["slot-1"])
    state, charge = charge_searchos_judgment_call(state, reservation_ref=reservation, slot_id="slot-1")
    navigation_window = project_navigation_window(state, slot_id="slot-1")
    custody = state["slots_by_id"]["slot-1"]["custody_refs"][0]
    request = build_searchos_navigation_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=candidate_window,
        navigation_window=navigation_window,
        read_custody_refs=[custody],
    )
    assert request["schema_version"] == SEARCHOS_NAVIGATION_JUDGMENT_REQUEST_SCHEMA_VERSION
    assert SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value in request["legal_actions"]
    assert "https://example.com/child" not in json.dumps(request, sort_keys=True)
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION,
            "action": SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value,
            "navigation_candidate_id": navigation_window[0]["navigation_candidate_ref"][
                "navigation_candidate_id"
            ],
            "reason": "The current source identifies a bounded next page.",
            "read_custody_assessments": [
                {
                    "read_custody_material_id": custody["read_custody_material_id"],
                    "reason_code": "needed_detail_absent",
                }
            ],
        },
    )
    before = state["slots_by_id"]["slot-1"]
    reduced = reduce_searchos_judgment_decision(state, decision=decision)
    after = reduced["slots_by_id"]["slot-1"]
    assert after["posture"] == SearchOSSlotPosture.AWAITING_NAVIGATION_ADMISSION.value
    assert after["read_nomination_count"] == before["read_nomination_count"]
    assert after["navigation_selection_count"] == 0
    assert reduced["navigation"]["edges"] == []
    assert after["pending_navigation_candidate_ref"] == navigation_window[0]["navigation_candidate_ref"]


def test_ipv6_label_is_private_across_navigation_foundation_surfaces() -> None:
    literal = "2001:db8::1"
    parent_url = "https://[2001:db8::1]/root"
    exact_destination = "https://[2001:db8::1]/child"
    forbidden_navigation_values = (literal, exact_destination, "/child")
    state, summary, store = _admit(
        "[2001:db8::1](/child)",
        parent_url=parent_url,
    )
    assert summary["admitted_option_count"] == 1
    option_value = next(iter(state["navigation"]["options_by_id"].values()))
    option = NavigationOption.from_dict(option_value)
    context = option.bounded_relationship_context
    assert context["relationship_label"] == "linked page"
    assert literal not in json.dumps(context, sort_keys=True)
    serialized_option = json.dumps(option.to_dict(), sort_keys=True)
    assert all(value not in serialized_option for value in forbidden_navigation_values)
    serialized_navigation = json.dumps(state["navigation"], sort_keys=True)
    assert all(value not in serialized_navigation for value in forbidden_navigation_values)

    state, candidate_window = _record_empty_candidate_window(state)
    state, reservation = begin_searchos_judgment_round(state, slot_ids=["slot-1"])
    state, charge = charge_searchos_judgment_call(
        state,
        reservation_ref=reservation,
        slot_id="slot-1",
    )
    navigation_window = project_navigation_window(state, slot_id="slot-1")
    assert navigation_window[0]["relationship_label"] == "linked page"
    serialized_window = json.dumps(navigation_window, sort_keys=True)
    assert all(value not in serialized_window for value in forbidden_navigation_values)
    custody = state["slots_by_id"]["slot-1"]["custody_refs"][0]
    request = build_searchos_navigation_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=candidate_window,
        navigation_window=navigation_window,
        read_custody_refs=[custody],
    )
    assert any(item["normalized_url"] == parent_url for item in request["read_custody_refs"])
    serialized_request_navigation = json.dumps(request["navigation_options"], sort_keys=True)
    assert all(value not in serialized_request_navigation for value in forbidden_navigation_values)
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION,
            "action": SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value,
            "navigation_candidate_id": navigation_window[0]["navigation_candidate_ref"][
                "navigation_candidate_id"
            ],
            "reason": "The current source identifies a bounded next page.",
            "read_custody_assessments": [
                {
                    "read_custody_material_id": custody["read_custody_material_id"],
                    "reason_code": "needed_detail_absent",
                }
            ],
        },
    )
    pending = reduce_searchos_judgment_decision(state, decision=decision)
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    kernel.state.searchos_state = pending
    action = kernel.authorize_searchos_navigation_selection(
        judgment_decision_ref=decision,
        navigation_candidate=navigation_window[0]["navigation_candidate_ref"],
    )
    serialized_action = json.dumps(action.to_dict(), sort_keys=True)
    assert all(value not in serialized_action for value in forbidden_navigation_values)
    observation = execute_navigation_selection(
        action=action,
        authorized_state_snapshot=deepcopy(pending),
        locator_store=store,
    )
    assert observation.payload["outcome"] == NAVIGATION_SELECTION_ADMITTED
    serialized_observation = json.dumps(observation.to_dict(), sort_keys=True)
    assert all(value not in serialized_observation for value in forbidden_navigation_values)
    assert store.resolve(option.destination_binding_ref) == exact_destination


def test_closed_slice_a_shape_and_judgment_contract_remain_navigation_free() -> None:
    state, _ = _state_with_parent(navigation_open=False)
    assert "navigation" not in state
    slot = state["slots_by_id"]["slot-1"]
    assert not any(key.startswith("navigation_") for key in slot)
    assert not any(key.startswith("pending_navigation_") for key in slot)
    state, window = _record_empty_candidate_window(state)
    state, reservation = begin_searchos_judgment_round(state, slot_ids=["slot-1"])
    state, charge = charge_searchos_judgment_call(state, reservation_ref=reservation, slot_id="slot-1")
    from core.searchos_iterative_judgment_runtime import (
        build_searchos_judgment_request_v1,
    )

    request = build_searchos_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=window,
        read_custody_refs=state["slots_by_id"]["slot-1"]["custody_refs"],
    )
    assert request["schema_version"] == SEARCHOS_JUDGMENT_REQUEST_SCHEMA_VERSION
    assert "navigation_options" not in request
    assert SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value not in request["legal_actions"]


def test_one_authorized_selection_admits_exactly_one_edge_and_read_nomination() -> None:
    pending, store, decision, candidate = _pending_navigation()
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    kernel.state.searchos_state = pending
    before = deepcopy(pending)
    action = kernel.authorize_searchos_navigation_selection(
        judgment_decision_ref=decision,
        navigation_candidate=candidate,
    )
    assert "locator_store" not in signature(kernel.authorize_searchos_navigation_selection).parameters
    assert "locator_store" not in signature(reduce_navigation_selection_observation).parameters
    assert kernel.state.searchos_state == before
    snapshot = deepcopy(kernel.state.searchos_state)
    observation = execute_navigation_selection(
        action=action,
        authorized_state_snapshot=snapshot,
        locator_store=store,
    )
    assert snapshot == kernel.state.searchos_state
    assert observation.payload["outcome"] == NAVIGATION_SELECTION_ADMITTED
    assert "https://" not in json.dumps(action.to_dict(), sort_keys=True)
    assert "https://" not in json.dumps(observation.to_dict(), sort_keys=True)
    kernel.reduce(observation)

    after = kernel.state.searchos_state
    before_slot = before["slots_by_id"]["slot-1"]
    after_slot = after["slots_by_id"]["slot-1"]
    assert after_slot["read_nomination_count"] == before_slot["read_nomination_count"] + 1
    assert after_slot["navigation_selection_count"] == 1
    assert after_slot["posture"] == SearchOSSlotPosture.AWAITING_NAVIGATION_EXECUTION.value
    assert len(after["navigation"]["edges"]) == 1
    option = NavigationOption.from_dict(next(iter(after["navigation"]["options_by_id"].values())))
    assert option.disposition == NAVIGATION_PENDING_EXECUTION
    assert option.active_selection_ref == observation.payload["proposed_navigation_selection_ref"]
    assert store.resolve(option.destination_binding_ref) == "https://example.com/child"


def test_authority_integrity_rejection_is_zero_charge_and_marks_slot_stale() -> None:
    pending, store, decision, candidate = _pending_navigation()
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    kernel.state.searchos_state = pending
    action = kernel.authorize_searchos_navigation_selection(
        judgment_decision_ref=decision,
        navigation_candidate=candidate,
    )
    altered_snapshot = deepcopy(pending)
    altered_snapshot["slots_by_id"]["slot-1"]["latest_reason"] = "altered_after_authorization"
    altered_snapshot = _refresh_state(altered_snapshot)
    observation = execute_navigation_selection(
        action=action,
        authorized_state_snapshot=altered_snapshot,
        locator_store=store,
    )
    assert observation.payload["outcome"] == NAVIGATION_SELECTION_AUTHORITY_REJECTED
    before_slot = deepcopy(pending["slots_by_id"]["slot-1"])
    kernel.reduce(observation)
    after = kernel.state.searchos_state
    after_slot = after["slots_by_id"]["slot-1"]
    assert after_slot["read_nomination_count"] == before_slot["read_nomination_count"]
    assert after_slot["navigation_selection_count"] == 0
    assert after["navigation"]["edges"] == []
    assert after_slot["posture"] == SearchOSSlotPosture.STALE_OR_INVALID.value


def test_missing_ephemeral_binding_is_recoverable_and_advances_the_window() -> None:
    pending, _, decision, candidate = _pending_navigation()
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    kernel.state.searchos_state = pending
    action = kernel.authorize_searchos_navigation_selection(
        judgment_decision_ref=decision,
        navigation_candidate=candidate,
    )
    unavailable_store = EphemeralNavigationLocatorStore(run_id="run-1", request_id="request-1")
    observation = execute_navigation_selection(
        action=action,
        authorized_state_snapshot=deepcopy(pending),
        locator_store=unavailable_store,
    )
    assert observation.payload["outcome"] == NAVIGATION_SELECTION_UNAVAILABLE
    assert observation.payload["reason"] == "navigation_destination_binding_missing"
    kernel.reduce(observation)
    after = kernel.state.searchos_state
    slot = after["slots_by_id"]["slot-1"]
    assert slot["read_nomination_count"] == 0
    assert slot["navigation_selection_count"] == 0
    assert slot["posture"] == SearchOSSlotPosture.ACTIVE_UNJUDGED.value
    assert after["navigation"]["edges"] == []
    assert project_navigation_window(after, slot_id="slot-1") == []
    option = NavigationOption.from_dict(next(iter(after["navigation"]["options_by_id"].values())))
    assert option.disposition == NAVIGATION_BINDING_UNAVAILABLE
    window = build_candidate_use_window_v1(
        slot_ref=after["slots_by_id"]["slot-1"]["slot_ref"],
        ordered_options=(),
        window_ordinal=2,
        policy_snapshot=after["policy_snapshot"],
    )
    after = record_searchos_candidate_window(after, window=window)
    after, reservation = begin_searchos_judgment_round(after, slot_ids=["slot-1"])
    after, charge = charge_searchos_judgment_call(after, reservation_ref=reservation, slot_id="slot-1")
    request = build_searchos_navigation_judgment_request_v1(
        state=after,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=window,
        navigation_window=[],
        read_custody_refs=after["slots_by_id"]["slot-1"]["custody_refs"],
    )
    assert SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY.value in request["legal_actions"]


@pytest.mark.parametrize(
    ("exhaustion", "reason"),
    [
        ("depth", "navigation_depth_limit_exhausted"),
        ("selection", "navigation_selection_limit_exhausted"),
        ("edge", "navigation_run_edge_limit_exhausted"),
        ("read", "navigation_read_nomination_limit_exhausted"),
        ("parent", "navigation_parent_relationship_unavailable"),
    ],
)
def test_executor_fails_closed_at_every_policy_and_relationship_boundary(exhaustion: str, reason: str) -> None:
    pending, store, decision, candidate = _pending_navigation()
    state = deepcopy(pending)
    slot = state["slots_by_id"]["slot-1"]
    option_id = candidate["navigation_option_ref"]["navigation_option_id"]
    option = NavigationOption.from_dict(state["navigation"]["options_by_id"][option_id])
    policy = state["policy_snapshot"]
    if exhaustion == "depth":
        option = replace(
            option,
            child_depth=policy["navigation_max_depth"] + 1,
            bounded_relationship_context={
                **option.bounded_relationship_context,
                "parent_depth": policy["navigation_max_depth"],
                "child_depth": policy["navigation_max_depth"] + 1,
            },
        )
    elif exhaustion == "selection":
        slot["navigation_selection_count"] = policy["navigation_selections_per_slot"]
    elif exhaustion == "edge":
        state["navigation"]["edges"] = [
            {"bounded_existing_edge": index} for index in range(policy["navigation_edges_per_run"])
        ]
    elif exhaustion == "read":
        slot["read_nomination_count"] = policy["read_nominations_per_slot"]
    else:
        slot["custody_refs"] = []
    if exhaustion == "depth":
        option_value = option.to_dict()
        del state["navigation"]["options_by_id"][option_id]
        state["navigation"]["options_by_id"][option_value["navigation_option_id"]] = option_value
        candidate = navigation_candidate_ref(option_value)
        slot["pending_navigation_candidate_ref"] = candidate
    state = _refresh_state(state)
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    kernel.state.searchos_state = state
    action = kernel.authorize_searchos_navigation_selection(
        judgment_decision_ref=decision,
        navigation_candidate=candidate,
    )
    observation = execute_navigation_selection(
        action=action,
        authorized_state_snapshot=deepcopy(state),
        locator_store=store,
    )
    assert observation.payload["outcome"] == NAVIGATION_SELECTION_UNAVAILABLE
    assert observation.payload["reason"] == reason
    before_slot = deepcopy(state["slots_by_id"]["slot-1"])
    before_edges = len(state["navigation"]["edges"])
    kernel.reduce(observation)
    after = kernel.state.searchos_state
    assert after["slots_by_id"]["slot-1"]["read_nomination_count"] == before_slot["read_nomination_count"]
    assert after["slots_by_id"]["slot-1"]["navigation_selection_count"] == before_slot["navigation_selection_count"]
    assert len(after["navigation"]["edges"]) == before_edges


def test_canonical_boundary_executor_rejects_corrupted_cycle_material() -> None:
    pending, store, decision, candidate = _pending_navigation()
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    kernel.state.searchos_state = pending
    action = kernel.authorize_searchos_navigation_selection(
        judgment_decision_ref=decision,
        navigation_candidate=candidate,
    )
    corrupted = deepcopy(pending)
    original = deepcopy(next(iter(corrupted["navigation"]["options_by_id"].values())))
    original["ancestor_physical_identity_digests"] = [original["destination_binding_ref"]["physical_identity_digest"]]
    impossible = _redigest_option(original)
    corrupt_candidate = _candidate_ref_from_option(impossible)
    corrupted["navigation"]["options_by_id"] = {impossible["navigation_option_id"]: impossible}
    corrupted["slots_by_id"]["slot-1"]["pending_navigation_candidate_ref"] = corrupt_candidate
    corrupted = _refresh_state(corrupted)
    corrupt_action = replace(
        action,
        inputs={
            **action.inputs,
            "expected_searchos_state_ref": {
                "state_id": corrupted["state_id"],
                "state_digest": corrupted["state_digest"],
            },
            "navigation_candidate_ref": corrupt_candidate,
            "navigation_option_ref": corrupt_candidate["navigation_option_ref"],
        },
    )
    observation = execute_navigation_selection(
        action=corrupt_action,
        authorized_state_snapshot=corrupted,
        locator_store=store,
    )
    assert observation.payload["outcome"] == NAVIGATION_SELECTION_AUTHORITY_REJECTED
    assert observation.payload["reason"] == "navigation_option_not_current"


def test_revision_binding_and_current_state_tampering_fail_closed() -> None:
    pending, store, decision, candidate = _pending_navigation()
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    kernel.state.searchos_state = pending
    action = kernel.authorize_searchos_navigation_selection(
        judgment_decision_ref=decision,
        navigation_candidate=candidate,
    )
    stale_option_ref = {
        **action.inputs["navigation_option_ref"],
        "revision": int(action.inputs["navigation_option_ref"]["revision"]) + 1,
    }
    stale_action = replace(
        action,
        inputs={**action.inputs, "navigation_option_ref": stale_option_ref},
    )
    revision_observation = execute_navigation_selection(
        action=stale_action,
        authorized_state_snapshot=deepcopy(pending),
        locator_store=store,
    )
    assert revision_observation.payload["outcome"] == NAVIGATION_SELECTION_AUTHORITY_REJECTED
    assert revision_observation.payload["reason"] == "navigation_option_revision_mismatch"

    altered_candidate = {
        **action.inputs["navigation_candidate_ref"],
        "navigation_candidate_digest": _digest("altered-candidate"),
    }
    candidate_action = replace(
        action,
        inputs={**action.inputs, "navigation_candidate_ref": altered_candidate},
    )
    candidate_observation = execute_navigation_selection(
        action=candidate_action,
        authorized_state_snapshot=deepcopy(pending),
        locator_store=store,
    )
    assert candidate_observation.payload["outcome"] == NAVIGATION_SELECTION_AUTHORITY_REJECTED
    assert candidate_observation.payload["reason"] == "navigation_pending_candidate_mismatch"

    class MismatchedLocatorStore:
        @staticmethod
        def resolve(binding_ref: object) -> str:
            del binding_ref
            return "https://example.com/tampered"

    binding_observation = execute_navigation_selection(
        action=action,
        authorized_state_snapshot=deepcopy(pending),
        locator_store=MismatchedLocatorStore(),  # type: ignore[arg-type]
    )
    assert binding_observation.payload["outcome"] == NAVIGATION_SELECTION_UNAVAILABLE
    assert binding_observation.payload["reason"] == "navigation_destination_binding_mismatch"

    admitted_store = _pending_navigation()[1]
    admitted_observation = execute_navigation_selection(
        action=action,
        authorized_state_snapshot=deepcopy(pending),
        locator_store=admitted_store,
    )
    changed = deepcopy(pending)
    changed["slots_by_id"]["slot-1"]["latest_reason"] = "state_changed_before_reduction"
    kernel.state.searchos_state = _refresh_state(changed)
    before = deepcopy(kernel.state.searchos_state)
    with pytest.raises(RunKernelTransitionError, match="navigation_observation_stale"):
        kernel.reduce(admitted_observation)
    assert kernel.state.searchos_state == before

    wrong_scope = RunKernel.start(run_id="other-run", request_id="request-1")
    wrong_scope.state.searchos_state = pending
    with pytest.raises(RunKernelTransitionError, match="scope differs"):
        wrong_scope.authorize_searchos_navigation_selection(
            judgment_decision_ref=decision,
            navigation_candidate=candidate,
        )


def test_ordinary_slice_a_product_runtime_activates_the_installed_one_hop_path() -> None:
    source = Path("core/searchos_slice_a_product_runtime.py").read_text(encoding="utf-8")
    assert SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value in source
    assert "navigation_runtime_open=True" in source
    assert "parent_depth=0" in source
    assert "execute_searchos_navigation_read_to_custody" in source
