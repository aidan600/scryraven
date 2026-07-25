"""Canonical SearchOS authority for one bounded existing-obligation recovery cycle.

The records in this module are deliberately semantic-content-free.  They bind
only canonical RunKernel/SearchOS identities, coverage facts, compact Evidence
Ledger facts, policy, expenditure, and terminal disposition.
"""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_coverage_reduction_runtime import (
    ledger_qualification_blockers_for_satisfied_coverage,
)
from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_OWNER,
    SearchOSRequirementPosture,
    SearchOSSlotPosture,
    validate_searchos_state,
)

EXISTING_GAP_BASIS_SCHEMA_VERSION = "searchos_existing_gap_basis_v1"
RECOVERY_PURPOSE_SCHEMA_VERSION = "searchos_materially_novel_recovery_purpose_v1"
RECOVERY_LEASE_SCHEMA_VERSION = "searchos_existing_gap_recovery_lease_v1"
RECOVERY_CYCLE_SCHEMA_VERSION = "searchos_existing_gap_recovery_cycle_v1"
RECOVERY_TERMINAL_SCHEMA_VERSION = "searchos_existing_gap_recovery_terminal_aggregate_v1"
MAXIMUM_EXISTING_GAP_RECOVERY_CYCLES = 1
_GAP_KINDS = {
    "same_component_semantic_admission_not_supported",
    "same_component_source_obligation_not_covered",
}
_PURPOSE_KIND = "close_existing_same_component_source_obligation_gap"
_EVIDENCE_DELTA_KIND = "new_exact_obligation_support_assessment"


class SearchOSExistingGapRecoveryError(ValueError):
    """Raised before any recovery authority or work can be created."""

    def __init__(
        self,
        message: str,
        *,
        blocker_interpretation: str = (
            "structural_or_validation_blocker"
        ),
    ) -> None:
        super().__init__(message)
        self.blocker_interpretation = blocker_interpretation


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _digest(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    except (TypeError, ValueError) as exc:
        raise SearchOSExistingGapRecoveryError("SearchOS existing-gap record is not JSON-safe") from exc
    return sha256(encoded.encode("utf-8")).hexdigest()


def _token(value: Any, label: str, *, limit: int = 320) -> str:
    token = str(value or "").strip()
    if not token or len(token) > limit:
        raise SearchOSExistingGapRecoveryError(f"SearchOS existing-gap record requires bounded {label}")
    return token


def _digest_token(value: Any, label: str) -> str:
    token = _token(value, label, limit=128)
    if len(token) != 64 or set(token) - set("0123456789abcdef"):
        raise SearchOSExistingGapRecoveryError(f"SearchOS existing-gap record requires canonical {label}")
    return token


def _envelope(
    core: Mapping[str, Any],
    *,
    id_field: str,
    digest_field: str,
    prefix: str,
) -> dict[str, Any]:
    safe = deepcopy(dict(core))
    digest = _digest(safe)
    return {
        **safe,
        id_field: f"{prefix}:{digest[:24]}",
        digest_field: digest,
        "replay_identity": f"{prefix}:{digest}",
    }


def _validate_envelope(
    value: Mapping[str, Any],
    *,
    schema_version: str,
    id_field: str,
    digest_field: str,
    prefix: str,
    label: str,
) -> dict[str, Any]:
    safe = _mapping(value)
    if safe.get("schema_version") != schema_version:
        raise SearchOSExistingGapRecoveryError(f"{label} schema mismatch")
    claimed = _digest_token(safe.get(digest_field), digest_field)
    core = {key: deepcopy(item) for key, item in safe.items() if key not in {id_field, digest_field, "replay_identity"}}
    if _digest(core) != claimed:
        raise SearchOSExistingGapRecoveryError(f"{label} digest mismatch")
    if safe.get(id_field) != f"{prefix}:{claimed[:24]}" or safe.get("replay_identity") != f"{prefix}:{claimed}":
        raise SearchOSExistingGapRecoveryError(f"{label} identity mismatch")
    return deepcopy(safe)


def _compact_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(value)
    ref = {
        key: deepcopy(item)
        for key, item in safe.items()
        if key.endswith("_id")
        or key.endswith("_digest")
        or key
        in {
            "schema_version",
            "component_id",
            "component_revision",
            "source_obligation_id",
            "accepted_contract_version",
            "answer_contract_ref",
            "slot_id",
            "requirement_posture",
            "admission_status",
            "coverage_state",
        }
    }
    if not any(key.endswith("_id") for key in ref):
        raise SearchOSExistingGapRecoveryError("canonical recovery reference lacks identity")
    return ref


def _refresh_state(state: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        key: deepcopy(value)
        for key, value in state.items()
        if key not in {"state_id", "state_digest", "replay_identity"}
    }
    digest = _digest(core)
    return {
        **core,
        "state_id": f"searchos-state:{digest[:24]}",
        "state_digest": digest,
        "replay_identity": f"searchos-state:{digest}",
    }


def _coverage_records_for_component(
    component_coverage_history: Sequence[Mapping[str, Any]],
    component_id: str,
) -> list[dict[str, Any]]:
    return [
        deepcopy(dict(item))
        for item in component_coverage_history
        if isinstance(item, Mapping) and item.get("answer_component_id") == component_id
    ]


def _matching_admissions(
    component_admission_projection: Mapping[str, Any],
    component_id: str,
) -> list[dict[str, Any]]:
    return [
        deepcopy(dict(item))
        for item in component_admission_projection.get("component_admission_refs") or ()
        if isinstance(item, Mapping) and item.get("component_id") == component_id
    ]


def _evidence_ledger_identity(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .casefold()
        .replace("-", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )


def _unique_tokens(value: Any) -> list[str]:
    tokens = [
        str(item or "").strip()
        for item in value or ()
        if str(item or "").strip()
    ]
    return tokens if len(tokens) == len(set(tokens)) else []


def _exact_recovery_coverage_chain_shape(
    *,
    coverage_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    answer_contract_ref: Mapping[str, Any],
    source_obligation_id: str,
    consumed_candidate_ids: Sequence[str],
    run_id: str,
    request_id: str,
) -> bool:
    coverage = _mapping(coverage_ref)
    requirement_ids = _unique_tokens(
        coverage.get("source_requirement_ids")
        or _mapping(
            coverage.get("evidence_ledger_binding")
        ).get("source_requirement_ids")
    )
    obligation_ids = _unique_tokens(
        coverage.get("source_obligation_ids")
    )
    coverage_candidate_ids = _unique_tokens(
        coverage.get("candidate_ids")
    )
    consumed_ids = _unique_tokens(consumed_candidate_ids)
    owned_links = [
        _mapping(item)
        for item in coverage.get(
            "owned_requirement_candidate_refs"
        )
        or ()
        if isinstance(item, Mapping)
    ]
    return bool(
        coverage.get("coverage_state") == "satisfied"
        and coverage.get("coverage_record_id")
        and coverage.get("coverage_record_digest")
        and coverage.get("run_id") == run_id
        and coverage.get("request_id") == request_id
        and coverage.get("answer_component_id")
        == component_ref.get("component_id")
        and coverage.get("component_revision")
        == component_ref.get("component_revision")
        and coverage.get("component_digest")
        == component_ref.get("component_digest")
        and coverage.get("accepted_contract_version")
        == answer_contract_ref.get("contract_version")
        and coverage.get("accepted_contract_digest")
        == answer_contract_ref.get("answer_contract_digest")
        and obligation_ids == [source_obligation_id]
        and len(requirement_ids) == 1
        and len(coverage_candidate_ids) == 1
        and consumed_ids == coverage_candidate_ids
        and len(owned_links) == 1
        and owned_links[0].get("requirement_id")
        == requirement_ids[0]
        and owned_links[0].get("source_obligation_id")
        == source_obligation_id
        and owned_links[0].get("candidate_id")
        == coverage_candidate_ids[0]
        and owned_links[0].get("link_status") == "accepted"
    )


def _exact_recovery_coverage_chain(
    *,
    coverage_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    answer_contract_ref: Mapping[str, Any],
    source_obligation_id: str,
    consumed_candidate_ids: Sequence[str],
    evidence_ledger_projection: Mapping[str, Any],
    run_id: str,
    request_id: str,
) -> bool:
    """Revalidate one exact coverage chain against current ledger truth."""

    coverage = _mapping(coverage_ref)
    if not _exact_recovery_coverage_chain_shape(
        coverage_ref=coverage,
        component_ref=component_ref,
        answer_contract_ref=answer_contract_ref,
        source_obligation_id=source_obligation_id,
        consumed_candidate_ids=consumed_candidate_ids,
        run_id=run_id,
        request_id=request_id,
    ):
        return False
    requirement_ids = _unique_tokens(
        coverage.get("source_requirement_ids")
        or _mapping(
            coverage.get("evidence_ledger_binding")
        ).get("source_requirement_ids")
    )
    candidate_ids = _unique_tokens(coverage.get("candidate_ids"))
    if len(requirement_ids) != 1 or len(candidate_ids) != 1:
        return False
    requirement_id = requirement_ids[0]
    candidate_id = candidate_ids[0]
    requirement_identity = _evidence_ledger_identity(
        requirement_id
    )
    candidate_identity = _evidence_ledger_identity(candidate_id)
    ledger = _mapping(evidence_ledger_projection)
    requirement_rows = [
        _mapping(item)
        for item in ledger.get("source_requirements") or ()
        if isinstance(item, Mapping)
        and _evidence_ledger_identity(
            item.get("requirement_id")
        )
        == requirement_identity
    ]
    candidate_rows = [
        _mapping(item)
        for item in ledger.get("candidate_records") or ()
        if isinstance(item, Mapping)
        and _evidence_ledger_identity(item.get("candidate_id"))
        == candidate_identity
    ]
    exact_links = [
        _mapping(item)
        for item in ledger.get("requirement_links") or ()
        if isinstance(item, Mapping)
        and _evidence_ledger_identity(
            item.get("requirement_id")
        )
        == requirement_identity
    ]
    if (
        len(requirement_rows) != 1
        or len(candidate_rows) != 1
        or len(exact_links) != 1
        or _evidence_ledger_identity(
            exact_links[0].get("candidate_id")
        )
        != candidate_identity
        or exact_links[0].get("link_status") != "accepted"
        or exact_links[0].get("link_reason")
        == "selected_candidate_matches_existing_requirement"
        or candidate_rows[0].get("stale") is True
    ):
        return False
    coverage_for_validation = {
        **coverage,
        "source_obligation_status": "satisfied",
        "source_obligation_ids": [source_obligation_id],
        "content_reference_bindings": [
            {"evidence_ref_id": candidate_id}
        ],
        "evidence_ledger_binding": {
            **_mapping(coverage.get("evidence_ledger_binding")),
            "source_requirement_ids": requirement_ids,
        },
    }
    return not ledger_qualification_blockers_for_satisfied_coverage(
        coverage=coverage_for_validation,
        evidence_ledger_projection=ledger,
        accepted_component={
            "component_id": component_ref.get("component_id"),
            "source_obligation_candidate_ids": [
                source_obligation_id
            ],
        },
        extra_evidence_refs=candidate_ids,
    )


def build_searchos_existing_gap_basis(
    *,
    state: Mapping[str, Any],
    slot_id: str,
    component_admission_projection: Mapping[str, Any],
    component_coverage_history: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive one exact post-analysis gap without inference or prompt content."""

    canonical = validate_searchos_state(state)
    slot_token = _token(slot_id, "slot_id")
    slot = _mapping(_mapping(canonical.get("slots_by_id")).get(slot_token))
    if not slot or slot_token not in canonical.get("active_slot_ids", ()):
        raise SearchOSExistingGapRecoveryError("existing-gap basis requires a current SearchOS slot")
    if slot.get("requirement_posture") != SearchOSRequirementPosture.REQUIRED.value:
        raise SearchOSExistingGapRecoveryError("optional SearchOS gaps are deferred by policy")
    if slot.get("posture") != SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value or not slot.get(
        "semantic_handoff_refs"
    ):
        raise SearchOSExistingGapRecoveryError(
            "existing-gap recovery requires a terminal post-analysis handoff",
            blocker_interpretation="lawful_recovery_ineligible",
        )
    slot_ref = _mapping(slot.get("slot_ref"))
    component_id = _token(slot_ref.get("component_id"), "component_id")
    obligation_id = _token(slot_ref.get("source_obligation_id"), "source_obligation_id")
    admissions = _matching_admissions(component_admission_projection, component_id)
    if not admissions:
        raise SearchOSExistingGapRecoveryError("existing-gap basis requires completed Component Analyst and D-prime")
    latest_admission = admissions[-1]
    latest_status = str(latest_admission.get("admission_status") or "")
    answer_contract_ref = _mapping(canonical.get("answer_contract_ref"))
    component_ref = _mapping(slot.get("component_ref"))
    if not (
        latest_admission.get("canonical_state") is True
        and latest_admission.get("current") is True
        and latest_admission.get("stale") is False
        and latest_status
        in {
            "admitted",
            "admitted_with_caveats",
            "blocked",
            "unsupported",
        }
        and latest_admission.get("component_id") == component_id
        and latest_admission.get("component_revision")
        == component_ref.get("component_revision")
        and latest_admission.get("component_digest")
        == component_ref.get("component_digest")
        and latest_admission.get("accepted_contract_version")
        == answer_contract_ref.get("contract_version")
        and latest_admission.get("accepted_contract_digest")
        == answer_contract_ref.get("answer_contract_digest")
        and _mapping(latest_admission.get("analyst_finding_ref"))
        and _mapping(latest_admission.get("dprime_validation_ref"))
    ):
        raise SearchOSExistingGapRecoveryError("existing-gap basis lacks exact same-component role provenance")
    coverage_records = _coverage_records_for_component(
        component_coverage_history, component_id
    )
    current_target_coverage_records = [
        record
        for record in coverage_records
        if record.get("canonical_state") is True
        and record.get("stale") is False
        and record.get("accepted_contract_version")
        == answer_contract_ref.get("contract_version")
        and record.get("accepted_contract_digest")
        == answer_contract_ref.get("answer_contract_digest")
        and record.get("component_revision")
        == component_ref.get("component_revision")
        and record.get("component_digest")
        == component_ref.get("component_digest")
        and obligation_id
        in {
            str(item)
            for item in record.get("source_obligation_ids") or ()
        }
    ]
    if len(current_target_coverage_records) > 1:
        raise SearchOSExistingGapRecoveryError(
            "existing-gap basis rejects competing current target coverage"
        )
    if current_target_coverage_records and not all(
        record.get("coverage_record_id")
        and record.get("coverage_record_digest")
        and record.get("coverage_state")
        and isinstance(record.get("evidence_ledger_binding"), Mapping)
        for record in current_target_coverage_records
    ):
        raise SearchOSExistingGapRecoveryError("existing-gap basis rejects ambiguous component coverage")
    coverage_requirement_ids = {
        str(requirement_id)
        for record in current_target_coverage_records
        for requirement_id in _mapping(
            record.get("evidence_ledger_binding")
        ).get("source_requirement_ids", ())
    }
    ledger_requirements = [
        {
            "requirement_id": item.get("requirement_id"),
            "requirement_kind": item.get("requirement_kind"),
            "source_obligation_id": item.get("source_obligation_id"),
            "component_id": item.get("component_id"),
            "status": item.get("status"),
        }
        for item in evidence_ledger_projection.get("source_requirements") or ()
        if isinstance(item, Mapping)
        and item.get("source_obligation_id") == obligation_id
        and _evidence_ledger_identity(item.get("component_id"))
        == _evidence_ledger_identity(component_id)
    ]
    ledger_requirement_ids = [
        str(item.get("requirement_id") or "")
        for item in ledger_requirements
        if item.get("requirement_id")
    ]
    if len(ledger_requirement_ids) != len(set(ledger_requirement_ids)):
        raise SearchOSExistingGapRecoveryError(
            "existing-gap basis rejects ambiguous exact requirements"
        )
    exact_requirement_ids = sorted(
        str(item["requirement_id"])
        for item in ledger_requirements
        if item.get("requirement_id") in coverage_requirement_ids
        and item.get("status") == "satisfied"
    )
    current_coverage = (
        current_target_coverage_records[0]
        if current_target_coverage_records
        else {}
    )
    exact_current_satisfied_chain = bool(
        current_coverage
        and _exact_recovery_coverage_chain(
            coverage_ref=current_coverage,
            component_ref=component_ref,
            answer_contract_ref=answer_contract_ref,
            source_obligation_id=obligation_id,
            consumed_candidate_ids=_unique_tokens(
                current_coverage.get("candidate_ids")
            ),
            evidence_ledger_projection=evidence_ledger_projection,
            run_id=canonical["run_id"],
            request_id=canonical["request_id"],
        )
    )
    if (
        latest_status in {"admitted", "admitted_with_caveats"}
        and exact_current_satisfied_chain
    ):
        raise SearchOSExistingGapRecoveryError(
            "existing-gap basis cannot reopen a satisfied source obligation",
            blocker_interpretation="lawful_recovery_ineligible",
        )
    coverage_basis = (
        {
            "basis_kind": "current_component_coverage",
            "current_coverage_ref": _compact_ref(
                current_target_coverage_records[0]
            ),
            "component_coverage_history_digest": _digest(
                current_target_coverage_records
            ),
            "component_coverage_record_count": 1,
        }
        if current_target_coverage_records
        else {
            "basis_kind": "explicit_canonical_absence",
            "component_id": component_id,
            "component_coverage_history_digest": _digest(
                [deepcopy(dict(item)) for item in component_coverage_history if isinstance(item, Mapping)]
            ),
            "component_coverage_record_count": 0,
        }
    )
    gap_kind = (
        "same_component_semantic_admission_not_supported"
        if latest_status not in {"admitted", "admitted_with_caveats"}
        else "same_component_source_obligation_not_covered"
    )
    core = {
        "schema_version": EXISTING_GAP_BASIS_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "answer_contract_ref": deepcopy(canonical["answer_contract_ref"]),
        "policy_snapshot_ref": deepcopy(canonical["policy_snapshot_ref"]),
        "searchos_state_ref": {
            "state_id": canonical["state_id"],
            "state_digest": canonical["state_digest"],
        },
        "prior_terminal_slot_ref": deepcopy(slot_ref),
        "prior_terminal_slot_state_digest": _digest_token(slot.get("slot_state_digest"), "slot_state_digest"),
        "prior_semantic_handoff_ref": _compact_ref(_mapping(slot["semantic_handoff_refs"][-1])),
        "component_ref": deepcopy(slot["component_ref"]),
        "source_obligation_ref": deepcopy(slot["source_obligation_ref"]),
        "requirement_posture": slot["requirement_posture"],
        "gap_kind": gap_kind,
        "component_admission_ref": _compact_ref(latest_admission),
        "component_analyst_proposal_ref": deepcopy(latest_admission["analyst_finding_ref"]),
        "component_dprime_validation_ref": deepcopy(latest_admission["dprime_validation_ref"]),
        "coverage_basis": coverage_basis,
        "exact_satisfied_requirement_ids": (
            exact_requirement_ids
            if exact_current_satisfied_chain
            else []
        ),
        "evidence_ledger_basis": {
            "projection_digest": _digest(evidence_ledger_projection),
            "matching_source_requirement_facts": ledger_requirements,
        },
        "prior_attempt_history_ref": {
            "existing_gap_recovery_cycle_count": len(
                canonical.get("existing_gap_recovery_cycles") or ()
            ),
            "existing_gap_recovery_purpose_refs_digest": _digest(
                canonical.get("existing_gap_recovery_purpose_refs") or ()
            ),
            "prior_slot_action_history_digest": _digest(
                slot.get("action_history") or ()
            ),
            "iteration_candidate_set_refs_digest": _digest(
                canonical.get("iteration_candidate_set_refs") or ()
            ),
        },
        "same_component_reassessment_required": True,
        "derived_component_recovery_authorized": False,
        "scrutineer_recovery_input_authorized": False,
        "specialist_recovery_input_authorized": False,
        "raw_content_retained": False,
        "canonical_state": True,
    }
    return _envelope(
        core,
        id_field="gap_basis_id",
        digest_field="gap_basis_digest",
        prefix="searchos-gap-basis",
    )


def validate_searchos_existing_gap_basis(
    basis: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _validate_envelope(
        basis,
        schema_version=EXISTING_GAP_BASIS_SCHEMA_VERSION,
        id_field="gap_basis_id",
        digest_field="gap_basis_digest",
        prefix="searchos-gap-basis",
        label="SearchOS existing-gap basis",
    )
    if (
        safe.get("owner") != SEARCHOS_OWNER
        or safe.get("canonical_state") is not True
        or not _mapping(safe.get("answer_contract_ref"))
        or not _mapping(safe.get("policy_snapshot_ref"))
        or not _mapping(safe.get("component_ref"))
        or not _mapping(safe.get("source_obligation_ref"))
        or not _mapping(safe.get("prior_attempt_history_ref"))
        or safe.get("requirement_posture")
        != SearchOSRequirementPosture.REQUIRED.value
        or safe.get("gap_kind") not in _GAP_KINDS
        or safe.get("same_component_reassessment_required") is not True
        or safe.get("derived_component_recovery_authorized") is not False
        or safe.get("scrutineer_recovery_input_authorized") is not False
        or safe.get("specialist_recovery_input_authorized") is not False
        or safe.get("raw_content_retained") is not False
    ):
        raise SearchOSExistingGapRecoveryError("SearchOS existing-gap basis broadens recovery authority")
    return safe


def build_searchos_materially_novel_recovery_purpose(
    gap_basis: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind novelty to the unsatisfied obligation and intended evidence delta."""

    basis = validate_searchos_existing_gap_basis(gap_basis)
    core = {
        "schema_version": RECOVERY_PURPOSE_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": basis["run_id"],
        "request_id": basis["request_id"],
        "gap_basis_ref": _compact_ref(basis),
        "answer_contract_ref": deepcopy(basis["answer_contract_ref"]),
        "policy_snapshot_ref": deepcopy(basis["policy_snapshot_ref"]),
        "component_ref": deepcopy(basis["component_ref"]),
        "source_obligation_ref": deepcopy(basis["source_obligation_ref"]),
        "prior_terminal_slot_ref": deepcopy(
            basis["prior_terminal_slot_ref"]
        ),
        "prior_attempt_history_ref": deepcopy(
            basis["prior_attempt_history_ref"]
        ),
        "purpose_kind": _PURPOSE_KIND,
        "intended_evidence_delta": {
            "delta_kind": _EVIDENCE_DELTA_KIND,
            "component_id": _mapping(basis["prior_terminal_slot_ref"]).get("component_id"),
            "source_obligation_id": _mapping(basis["prior_terminal_slot_ref"]).get("source_obligation_id"),
        },
        "query_wording_establishes_novelty": False,
        "physical_source_identity_establishes_novelty": False,
        "prompt_content_establishes_novelty": False,
        "canonical_state": True,
    }
    return _envelope(
        core,
        id_field="recovery_purpose_id",
        digest_field="recovery_purpose_digest",
        prefix="searchos-recovery-purpose",
    )


def validate_searchos_recovery_purpose(
    purpose: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _validate_envelope(
        purpose,
        schema_version=RECOVERY_PURPOSE_SCHEMA_VERSION,
        id_field="recovery_purpose_id",
        digest_field="recovery_purpose_digest",
        prefix="searchos-recovery-purpose",
        label="SearchOS recovery purpose",
    )
    if any(
        safe.get(field) is not False
        for field in (
            "query_wording_establishes_novelty",
            "physical_source_identity_establishes_novelty",
            "prompt_content_establishes_novelty",
        )
    ):
        raise SearchOSExistingGapRecoveryError("recovery purpose uses a non-semantic novelty basis")
    delta = _mapping(safe.get("intended_evidence_delta"))
    slot_component = _mapping(safe.get("component_ref")).get("component_id")
    source_obligation_ref = _mapping(safe.get("source_obligation_ref"))
    slot_obligation = source_obligation_ref.get("source_obligation_id") or source_obligation_ref.get("candidate_id")
    if (
        safe.get("owner") != SEARCHOS_OWNER
        or safe.get("canonical_state") is not True
        or not _mapping(safe.get("answer_contract_ref"))
        or not _mapping(safe.get("policy_snapshot_ref"))
        or not _mapping(safe.get("prior_terminal_slot_ref"))
        or not _mapping(safe.get("prior_attempt_history_ref"))
        or safe.get("purpose_kind") != _PURPOSE_KIND
        or delta.get("delta_kind") != _EVIDENCE_DELTA_KIND
        or delta.get("component_id") != slot_component
        or delta.get("source_obligation_id") != slot_obligation
    ):
        raise SearchOSExistingGapRecoveryError("recovery purpose lacks an exact materially novel evidence delta")
    return safe


def admit_searchos_existing_gap_recovery_cycle(
    *,
    state: Mapping[str, Any],
    gap_basis: Mapping[str, Any],
    recovery_purpose: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Admit or exactly replay the sole whole-run recovery lease."""

    canonical = validate_searchos_state(state)
    basis = validate_searchos_existing_gap_basis(gap_basis)
    purpose = validate_searchos_recovery_purpose(recovery_purpose)
    if (
        _mapping(purpose.get("gap_basis_ref")).get("gap_basis_digest") != basis["gap_basis_digest"]
        or basis.get("run_id") != canonical.get("run_id")
        or basis.get("request_id") != canonical.get("request_id")
        or _mapping(purpose.get("answer_contract_ref"))
        != _mapping(basis.get("answer_contract_ref"))
        or _mapping(purpose.get("policy_snapshot_ref"))
        != _mapping(basis.get("policy_snapshot_ref"))
        or _mapping(purpose.get("component_ref"))
        != _mapping(basis.get("component_ref"))
        or _mapping(purpose.get("source_obligation_ref"))
        != _mapping(basis.get("source_obligation_ref"))
        or _mapping(purpose.get("prior_terminal_slot_ref"))
        != _mapping(basis.get("prior_terminal_slot_ref"))
        or _mapping(purpose.get("prior_attempt_history_ref"))
        != _mapping(basis.get("prior_attempt_history_ref"))
    ):
        raise SearchOSExistingGapRecoveryError("recovery purpose/gap/run binding mismatch")
    policy = _mapping(canonical.get("policy_snapshot"))
    recovery_policy = _mapping(policy.get("existing_gap_recovery_policy"))
    if (
        canonical.get("existing_gap_recovery_runtime_open") is not True
        or recovery_policy.get("runtime_open") is not True
        or int(recovery_policy.get("maximum_cycles_per_run") or -1) != MAXIMUM_EXISTING_GAP_RECOVERY_CYCLES
        or recovery_policy.get("same_limits_for_all_profiles") is not True
        or recovery_policy.get("required_gaps_prioritized") is not True
        or recovery_policy.get("optional_gap_recovery_authorized") is not False
        or recovery_policy.get("whole_run_lease_required") is not True
    ):
        raise SearchOSExistingGapRecoveryError("SearchOS existing-gap recovery policy is closed or invalid")
    prior_purposes = [_mapping(item) for item in canonical.get("existing_gap_recovery_purpose_refs") or ()]
    exact_prior = next(
        (
            item
            for item in prior_purposes
            if item.get("recovery_purpose_id") == purpose["recovery_purpose_id"]
            and item.get("recovery_purpose_digest") == purpose["recovery_purpose_digest"]
        ),
        None,
    )
    if exact_prior is not None:
        cycle = next(
            (
                deepcopy(dict(item))
                for item in canonical.get("existing_gap_recovery_cycles") or ()
                if _mapping(item.get("recovery_purpose_ref")).get("recovery_purpose_digest")
                == purpose["recovery_purpose_digest"]
            ),
            None,
        )
        if cycle is None:
            raise SearchOSExistingGapRecoveryError("replayed recovery purpose lost its admitted cycle")
        return canonical, {
            "status": "already_admitted",
            "exact_replay": True,
            "work_authorized": False,
            "cycle": cycle,
            "cycle_ref": recovery_cycle_ref(cycle),
        }
    if _mapping(basis.get("searchos_state_ref")) != {
        "state_id": canonical.get("state_id"),
        "state_digest": canonical.get("state_digest"),
    }:
        raise SearchOSExistingGapRecoveryError("recovery gap basis is stale against canonical SearchOS state")
    if any(
        item.get("recovery_purpose_id") == purpose["recovery_purpose_id"]
        or _mapping(item.get("gap_basis_ref")).get("gap_basis_id")
        == _mapping(purpose.get("gap_basis_ref")).get("gap_basis_id")
        for item in prior_purposes
    ):
        raise SearchOSExistingGapRecoveryError("recovery purpose identity conflicts with prior canonical content")
    cycles = [deepcopy(dict(item)) for item in canonical.get("existing_gap_recovery_cycles") or ()]
    if len(cycles) >= MAXIMUM_EXISTING_GAP_RECOVERY_CYCLES:
        raise SearchOSExistingGapRecoveryError("whole-run existing-gap recovery cycle limit exhausted")
    prior_slot_ref = _mapping(basis["prior_terminal_slot_ref"])
    prior_slot_id = _token(prior_slot_ref.get("slot_id"), "prior slot_id")
    prior_slot = _mapping(_mapping(canonical.get("slots_by_id")).get(prior_slot_id))
    if (
        prior_slot.get("slot_state_digest") != basis["prior_terminal_slot_state_digest"]
        or prior_slot.get("posture") != SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value
    ):
        raise SearchOSExistingGapRecoveryError("recovery gap basis is stale against the prior terminal slot")
    purpose_ref = _compact_ref(purpose)
    cycle_seed = {
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "cycle_ordinal": len(cycles) + 1,
        "gap_basis_ref": _compact_ref(basis),
        "recovery_purpose_ref": purpose_ref,
        "prior_terminal_slot_ref": deepcopy(prior_slot_ref),
    }
    cycle_seed_digest = _digest(cycle_seed)
    cycle_id = f"searchos-recovery-cycle:{cycle_seed_digest[:24]}"
    lease_core = {
        "schema_version": RECOVERY_LEASE_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "cycle_id": cycle_id,
        "gap_basis_ref": _compact_ref(basis),
        "recovery_purpose_ref": purpose_ref,
        "answer_contract_ref": deepcopy(basis["answer_contract_ref"]),
        "policy_snapshot_ref": deepcopy(basis["policy_snapshot_ref"]),
        "component_ref": deepcopy(basis["component_ref"]),
        "source_obligation_ref": deepcopy(
            basis["source_obligation_ref"]
        ),
        "lease_scope": ("existing_component_source_obligation_search_read_and_same_component_reassessment"),
        "allowed_consumers": [
            "SearchOSJudgment",
            "QueryPlan",
            "SEARCH",
            "READ",
            "SearchOSNavigation",
            "ComponentAnalyst",
            "ComponentDprime",
            "ComponentCoverage",
        ],
        "scrutineer_input_authorized": False,
        "derived_component_authorized": False,
        "contract_amendment_authorized": False,
        "specialist_authorized": False,
        "status": "granted",
        "canonical_state": True,
    }
    lease = _envelope(
        lease_core,
        id_field="recovery_lease_id",
        digest_field="recovery_lease_digest",
        prefix="searchos-recovery-lease",
    )
    slot_identity = {
        "cycle_id": cycle_id,
        "component_ref": basis["component_ref"],
        "source_obligation_ref": basis["source_obligation_ref"],
        "recovery_purpose_ref": purpose_ref,
    }
    slot_identity_digest = _digest(slot_identity)
    recovery_slot_id = f"searchos-recovery-slot:{slot_identity_digest[:24]}"
    recovery_slot_core = {
        "slot_id": recovery_slot_id,
        "slot_ordinal": len(canonical["active_slot_ids"]) + 1,
        "component_ref": deepcopy(basis["component_ref"]),
        "source_obligation_ref": deepcopy(basis["source_obligation_ref"]),
        "requirement_posture": SearchOSRequirementPosture.REQUIRED.value,
        "posture": SearchOSSlotPosture.ACTIVE_UNJUDGED.value,
        "latest_reason": None,
        "current_candidate_state_ref": deepcopy(canonical["current_candidate_state_ref"]),
        "current_window_ref": {},
        "candidate_use_option_refs": [],
        "candidate_option_dispositions": {},
        "custody_refs": [],
        "semantic_handoff_refs": [],
        "action_history": [],
        "judgment_call_count": 0,
        "candidate_window_count": 0,
        "candidate_wave_count": 1,
        "read_nomination_count": 0,
        "followup_query_nomination_count": 0,
        "satisfaction_claimed": False,
        "coverage_upgrade_claimed": False,
        "pending_navigation_decision_ref": {},
        "pending_navigation_candidate_ref": {},
        "navigation_selection_count": 0,
        "navigation_availability_reason": None,
        "recovery_cycle_ref": {
            "cycle_id": cycle_id,
            "cycle_ordinal": len(cycles) + 1,
        },
        "recovery_gap_basis_ref": _compact_ref(basis),
        "recovery_purpose_ref": purpose_ref,
        "recovery_lease_ref": _compact_ref(lease),
        "prior_terminal_slot_ref": deepcopy(prior_slot_ref),
        "prior_terminal_slot_state_digest": prior_slot["slot_state_digest"],
    }
    recovery_slot_core["slot_ref"] = {
        "slot_id": recovery_slot_id,
        "slot_digest": _digest(slot_identity),
        "component_id": prior_slot_ref["component_id"],
        "source_obligation_id": prior_slot_ref["source_obligation_id"],
        "recovery_cycle_id": cycle_id,
    }
    recovery_slot_core["slot_state_digest"] = _digest(recovery_slot_core)
    budget = deepcopy(canonical["budget"])
    reserved = int(policy["minimum_reserved_judgment_calls_per_required_slot"])
    additional = int(policy["additional_judgment_call_pool_per_active_slot"])
    budget["judgment_call_ceiling"] = int(budget["judgment_call_ceiling"]) + reserved + additional
    budget["reserved_calls_remaining_by_required_slot"][recovery_slot_id] = reserved
    budget["shared_calls_remaining"] = int(budget["shared_calls_remaining"]) + additional
    cycle_core = {
        "schema_version": RECOVERY_CYCLE_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        **cycle_seed,
        "cycle_id": cycle_id,
        "recovery_lease_ref": _compact_ref(lease),
        "recovery_slot_ref": deepcopy(recovery_slot_core["slot_ref"]),
        "prior_terminal_slot_state_digest": prior_slot["slot_state_digest"],
        "answer_contract_ref": deepcopy(basis["answer_contract_ref"]),
        "policy_snapshot_ref": deepcopy(basis["policy_snapshot_ref"]),
        "component_ref": deepcopy(basis["component_ref"]),
        "source_obligation_ref": deepcopy(
            basis["source_obligation_ref"]
        ),
        "cumulative_history_baseline": {
            **deepcopy(basis["prior_attempt_history_ref"]),
            "active_slot_count": len(canonical["active_slot_ids"]),
            "required_slot_count": len(canonical["required_slot_ids"]),
            "semantic_handoff_ref_count": len(
                canonical.get("semantic_handoff_refs") or ()
            ),
            "searchos_state_digest_before_cycle": canonical[
                "state_digest"
            ],
        },
        "budget_baseline": {
            "judgment_call_ceiling": canonical["budget"]["judgment_call_ceiling"],
            "charged_logical_judgment_calls": canonical["budget"]["charged_logical_judgment_calls"],
            "failed_logical_judgment_calls": canonical["budget"]["failed_logical_judgment_calls"],
            "returned_pre_call_reservations": canonical["budget"]["returned_pre_call_reservations"],
            "iteration_candidate_set_count": len(canonical["iteration_candidate_set_refs"]),
        },
        "status": "active",
        "same_component_reassessment_required": True,
        "derived_component_recovery_authorized": False,
        "scrutineer_recovery_input_authorized": False,
        "canonical_state": True,
    }
    cycle = _envelope(
        cycle_core,
        id_field="cycle_record_id",
        digest_field="cycle_digest",
        prefix="searchos-recovery-cycle-record",
    )
    candidate = deepcopy(canonical)
    candidate["slots_by_id"][recovery_slot_id] = recovery_slot_core
    candidate["active_slot_ids"].append(recovery_slot_id)
    candidate["required_slot_ids"].append(recovery_slot_id)
    candidate["budget"] = budget
    candidate.setdefault("existing_gap_recovery_purpose_refs", []).append(purpose_ref)
    candidate.setdefault("existing_gap_recovery_lease_refs", []).append(_compact_ref(lease))
    candidate.setdefault("existing_gap_recovery_cycles", []).append(cycle)
    candidate["active_existing_gap_recovery_cycle_ref"] = recovery_cycle_ref(cycle)
    refreshed = _refresh_state(candidate)
    refreshed = validate_searchos_state(refreshed)
    return refreshed, {
        "status": "admitted",
        "exact_replay": False,
        "work_authorized": True,
        "cycle": cycle,
        "cycle_ref": recovery_cycle_ref(cycle),
        "lease": lease,
        "recovery_slot_ref": deepcopy(recovery_slot_core["slot_ref"]),
    }


def validate_searchos_recovery_cycle(
    cycle: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _validate_envelope(
        cycle,
        schema_version=RECOVERY_CYCLE_SCHEMA_VERSION,
        id_field="cycle_record_id",
        digest_field="cycle_digest",
        prefix="searchos-recovery-cycle-record",
        label="SearchOS recovery cycle",
    )
    if (
        safe.get("same_component_reassessment_required") is not True
        or safe.get("derived_component_recovery_authorized") is not False
        or safe.get("scrutineer_recovery_input_authorized") is not False
    ):
        raise SearchOSExistingGapRecoveryError("SearchOS recovery cycle broadens same-component authority")
    return safe


def recovery_cycle_ref(cycle: Mapping[str, Any]) -> dict[str, Any]:
    safe = validate_searchos_recovery_cycle(cycle)
    return {
        "schema_version": RECOVERY_CYCLE_SCHEMA_VERSION,
        "cycle_id": safe["cycle_id"],
        "cycle_record_id": safe["cycle_record_id"],
        "cycle_digest": safe["cycle_digest"],
        "cycle_ordinal": safe["cycle_ordinal"],
        "answer_contract_ref": deepcopy(
            safe["answer_contract_ref"]
        ),
        "component_ref": deepcopy(safe["component_ref"]),
        "source_obligation_ref": deepcopy(
            safe["source_obligation_ref"]
        ),
        "prior_terminal_slot_ref": deepcopy(
            safe["prior_terminal_slot_ref"]
        ),
        "recovery_slot_ref": deepcopy(safe["recovery_slot_ref"]),
        "recovery_purpose_ref": deepcopy(safe["recovery_purpose_ref"]),
        "recovery_lease_ref": deepcopy(safe["recovery_lease_ref"]),
    }


def validate_active_searchos_recovery_cycle_ref(
    state: Mapping[str, Any],
    cycle_ref: Mapping[str, Any],
) -> dict[str, Any]:
    canonical = validate_searchos_state(state)
    supplied = _mapping(cycle_ref)
    active = _mapping(canonical.get("active_existing_gap_recovery_cycle_ref"))
    if supplied != active:
        raise SearchOSExistingGapRecoveryError("same-component recovery requires the exact active cycle")
    matches = [
        validate_searchos_recovery_cycle(item)
        for item in canonical.get("existing_gap_recovery_cycles") or ()
        if isinstance(item, Mapping)
        and item.get("cycle_id") == supplied.get("cycle_id")
        and item.get("cycle_digest") == supplied.get("cycle_digest")
    ]
    if len(matches) != 1 or matches[0].get("status") != "active":
        raise SearchOSExistingGapRecoveryError("same-component recovery cycle is absent or terminal")
    return matches[0]


def finalize_searchos_existing_gap_recovery_cycle(
    *,
    state: Mapping[str, Any],
    cycle_ref: Mapping[str, Any],
    component_admission_ref: Mapping[str, Any] | None,
    evidence_ledger_projection: Mapping[str, Any],
    failure_reason: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Close the lease with exact expenditure and honest terminal disposition."""

    canonical = validate_searchos_state(state)
    cycle = validate_active_searchos_recovery_cycle_ref(canonical, cycle_ref)
    slot_ref = _mapping(cycle["recovery_slot_ref"])
    slot = _mapping(_mapping(canonical["slots_by_id"]).get(slot_ref["slot_id"]))
    admission = _mapping(component_admission_ref)
    coverage_ref = _mapping(admission.get("component_coverage_ref"))
    admission_candidate_ids = _unique_tokens(
        [
            _mapping(item).get("evidence_ref_id")
            for item in admission.get("evidence_refs") or ()
            if isinstance(item, Mapping)
        ]
    )
    admission_claimed = admission.get("admission_status") in {
        "admitted",
        "admitted_with_caveats",
    }
    exact_chain_current = _exact_recovery_coverage_chain(
        coverage_ref=coverage_ref,
        component_ref=_mapping(slot.get("component_ref")),
        answer_contract_ref=_mapping(
            cycle.get("answer_contract_ref")
        ),
        source_obligation_id=str(
            slot_ref.get("source_obligation_id") or ""
        ),
        consumed_candidate_ids=admission_candidate_ids,
        evidence_ledger_projection=evidence_ledger_projection,
        run_id=canonical["run_id"],
        request_id=canonical["request_id"],
    )
    admitted = (
        admission_claimed
        and admission.get("component_id") == slot_ref.get("component_id")
        and _mapping(admission.get("searchos_recovery_cycle_ref")).get("cycle_digest") == cycle["cycle_digest"]
        and admission.get("component_revision")
        == _mapping(slot.get("component_ref")).get(
            "component_revision"
        )
        and admission.get("component_digest")
        == _mapping(slot.get("component_ref")).get("component_digest")
        and admission.get("accepted_contract_version")
        == _mapping(cycle.get("answer_contract_ref")).get(
            "contract_version"
        )
        and admission.get("accepted_contract_digest")
        == _mapping(cycle.get("answer_contract_ref")).get(
            "answer_contract_digest"
        )
        and exact_chain_current
    )
    terminal_status = "recovered" if admitted else "exhausted_insufficient"
    reason = (
        None
        if admitted
        else _token(
            failure_reason
            or (
                "same_component_reassessment_failed:"
                "exact_ownership_chain_invalid"
                if admission_claimed
                else None
            )
            or slot.get("latest_reason")
            or "same_component_reassessment_not_admitted",
            "terminal failure reason",
            limit=240,
        )
    )
    baseline = _mapping(cycle["budget_baseline"])
    budget = _mapping(canonical["budget"])
    local_reserved_remaining = int(
        _mapping(budget.get("reserved_calls_remaining_by_required_slot")).get(
            slot_ref.get("slot_id")
        )
        or 0
    )
    blocker_class = (
        None
        if admitted
        else "validation"
        if str(reason).startswith("same_component_reassessment_failed:")
        else "provider_or_acquisition"
        if any(
            marker in str(reason)
            for marker in (
                "model",
                "provider",
                "acquisition",
                "fetch",
                "read",
                "navigation",
                "discover",
            )
        )
        else "recovery_exhaustion"
    )
    terminal_core = {
        "schema_version": RECOVERY_TERMINAL_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "cycle_ref": recovery_cycle_ref(cycle),
        "gap_basis_ref": deepcopy(cycle["gap_basis_ref"]),
        "recovery_purpose_ref": deepcopy(cycle["recovery_purpose_ref"]),
        "recovery_lease_ref": deepcopy(cycle["recovery_lease_ref"]),
        "recovery_slot_ref": deepcopy(slot_ref),
        "component_ref": deepcopy(slot["component_ref"]),
        "answer_contract_ref": deepcopy(
            cycle["answer_contract_ref"]
        ),
        "source_obligation_ref": deepcopy(
            slot["source_obligation_ref"]
        ),
        "terminal_status": terminal_status,
        "terminal_reason": reason,
        "whole_run_lease_status": (
            "settled_recovered"
            if admitted
            else "settled_exhausted_insufficient"
        ),
        "local_budget_status": {
            "slot_reserved_calls_remaining": local_reserved_remaining,
            "shared_calls_remaining": int(
                budget.get("shared_calls_remaining") or 0
            ),
            "slot_judgment_call_count": int(
                slot.get("judgment_call_count") or 0
            ),
            "terminal": True,
        },
        "terminal_blocker": (
            {
                "blocker_class": blocker_class,
                "reason_code": reason,
            }
            if reason
            else {}
        ),
        "novelty_exhausted": True,
        "lawful_materially_novel_recovery_purpose_remains": False,
        "component_admission_ref": (
            _compact_ref(admission) if admitted else {}
        ),
        "component_coverage_ref": (
            deepcopy(coverage_ref) if admitted else {}
        ),
        "consumed_candidate_ids": (
            admission_candidate_ids if admitted else []
        ),
        "expenditure": {
            "logical_judgment_calls": int(budget["charged_logical_judgment_calls"])
            - int(baseline["charged_logical_judgment_calls"]),
            "failed_logical_judgment_calls": int(budget["failed_logical_judgment_calls"])
            - int(baseline["failed_logical_judgment_calls"]),
            "returned_pre_call_reservations": int(budget["returned_pre_call_reservations"])
            - int(baseline["returned_pre_call_reservations"]),
            "iteration_candidate_sets": len(canonical["iteration_candidate_set_refs"])
            - int(baseline["iteration_candidate_set_count"]),
            "recovery_slot_action_count": len(slot.get("action_history") or ()),
        },
        "coverage_gained": admitted,
        "gap_remains": not admitted,
        "lease_terminal": True,
        "further_existing_gap_recovery_authorized": False,
        "final_sufficiency_decided": False,
        "final_answer_packet_decided": False,
        "author_execution_decided": False,
        "raw_content_retained": False,
        "canonical_state": True,
    }
    terminal = _envelope(
        terminal_core,
        id_field="terminal_aggregate_id",
        digest_field="terminal_aggregate_digest",
        prefix="searchos-recovery-terminal",
    )
    updated_cycle_core = {
        key: deepcopy(value)
        for key, value in cycle.items()
        if key
        not in {
            "cycle_record_id",
            "cycle_digest",
            "replay_identity",
            "status",
        }
    }
    updated_cycle_core["status"] = terminal_status
    updated_cycle_core["terminal_aggregate_ref"] = _compact_ref(terminal)
    updated_cycle = _envelope(
        updated_cycle_core,
        id_field="cycle_record_id",
        digest_field="cycle_digest",
        prefix="searchos-recovery-cycle-record",
    )
    candidate = deepcopy(canonical)
    candidate["existing_gap_recovery_cycles"] = [
        updated_cycle if _mapping(item).get("cycle_id") == cycle["cycle_id"] else deepcopy(dict(item))
        for item in canonical["existing_gap_recovery_cycles"]
    ]
    candidate["existing_gap_recovery_terminal_aggregate_ref"] = _compact_ref(terminal)
    candidate["existing_gap_recovery_terminal_aggregate"] = terminal
    candidate["active_existing_gap_recovery_cycle_ref"] = {}
    return validate_searchos_state(_refresh_state(candidate)), terminal


def validate_searchos_recovery_terminal_aggregate(
    terminal: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _validate_envelope(
        terminal,
        schema_version=RECOVERY_TERMINAL_SCHEMA_VERSION,
        id_field="terminal_aggregate_id",
        digest_field="terminal_aggregate_digest",
        prefix="searchos-recovery-terminal",
        label="SearchOS recovery terminal aggregate",
    )
    cycle_ref = _mapping(safe.get("cycle_ref"))
    slot_ref = _mapping(safe.get("recovery_slot_ref"))
    component_ref = _mapping(safe.get("component_ref"))
    source_obligation_ref = _mapping(safe.get("source_obligation_ref"))
    admission_ref = _mapping(safe.get("component_admission_ref"))
    coverage_ref = _mapping(safe.get("component_coverage_ref"))
    answer_contract_ref = _mapping(safe.get("answer_contract_ref"))
    consumed_candidate_ids = _unique_tokens(
        safe.get("consumed_candidate_ids")
    )
    terminal_status = safe.get("terminal_status")
    recovered = terminal_status == "recovered"
    exhausted = terminal_status == "exhausted_insufficient"
    expenditure = _mapping(safe.get("expenditure"))
    local_budget = _mapping(safe.get("local_budget_status"))
    blocker = _mapping(safe.get("terminal_blocker"))
    if (
        safe.get("lease_terminal") is not True
        or safe.get("further_existing_gap_recovery_authorized") is not False
        or safe.get("final_sufficiency_decided") is not False
        or safe.get("final_answer_packet_decided") is not False
        or safe.get("author_execution_decided") is not False
        or safe.get("raw_content_retained") is not False
        or safe.get("canonical_state") is not True
        or safe.get("owner") != SEARCHOS_OWNER
        or not (recovered or exhausted)
        or _mapping(cycle_ref.get("recovery_slot_ref")) != slot_ref
        or _mapping(cycle_ref.get("component_ref")) != component_ref
        or _mapping(cycle_ref.get("source_obligation_ref"))
        != source_obligation_ref
        or _mapping(cycle_ref.get("answer_contract_ref"))
        != answer_contract_ref
        or cycle_ref.get("cycle_id")
        != slot_ref.get("recovery_cycle_id")
        or _mapping(cycle_ref.get("recovery_purpose_ref"))
        != _mapping(safe.get("recovery_purpose_ref"))
        or _mapping(cycle_ref.get("recovery_lease_ref"))
        != _mapping(safe.get("recovery_lease_ref"))
        or not slot_ref.get("component_id")
        or not slot_ref.get("source_obligation_id")
        or component_ref.get("component_id")
        != slot_ref.get("component_id")
        or not component_ref.get("component_revision")
        or not component_ref.get("component_digest")
        or (
            source_obligation_ref.get("source_obligation_id")
            or source_obligation_ref.get("candidate_id")
        )
        != slot_ref.get("source_obligation_id")
        or safe.get("whole_run_lease_status")
        not in {
            "settled_recovered",
            "settled_exhausted_insufficient",
        }
        or local_budget.get("terminal") is not True
        or any(
            not isinstance(local_budget.get(key), int)
            or int(local_budget.get(key)) < 0
            for key in (
                "slot_reserved_calls_remaining",
                "shared_calls_remaining",
                "slot_judgment_call_count",
            )
        )
        or safe.get("novelty_exhausted") is not True
        or safe.get(
            "lawful_materially_novel_recovery_purpose_remains"
        )
        is not False
        or any(
            not isinstance(expenditure.get(key), int)
            or int(expenditure.get(key)) < 0
            for key in (
                "logical_judgment_calls",
                "failed_logical_judgment_calls",
                "returned_pre_call_reservations",
                "iteration_candidate_sets",
                "recovery_slot_action_count",
            )
        )
        or (
            recovered
            and (
                safe.get("coverage_gained") is not True
                or safe.get("gap_remains") is not False
                or safe.get("whole_run_lease_status") != "settled_recovered"
                or safe.get("terminal_reason") is not None
                or blocker
                or admission_ref.get("admission_status")
                not in {"admitted", "admitted_with_caveats"}
                or admission_ref.get("component_id") != slot_ref.get("component_id")
                or admission_ref.get("component_revision")
                != component_ref.get("component_revision")
                or admission_ref.get("component_digest")
                != component_ref.get("component_digest")
                or admission_ref.get("accepted_contract_version")
                != answer_contract_ref.get("contract_version")
                or admission_ref.get("accepted_contract_digest")
                != answer_contract_ref.get(
                    "answer_contract_digest"
                )
                or coverage_ref.get("coverage_state")
                != "satisfied"
                or not coverage_ref.get("coverage_record_id")
                or not coverage_ref.get("coverage_record_digest")
                or not _exact_recovery_coverage_chain_shape(
                    coverage_ref=coverage_ref,
                    component_ref=component_ref,
                    answer_contract_ref=answer_contract_ref,
                    source_obligation_id=str(
                        slot_ref.get("source_obligation_id") or ""
                    ),
                    consumed_candidate_ids=consumed_candidate_ids,
                    run_id=str(safe.get("run_id") or ""),
                    request_id=str(safe.get("request_id") or ""),
                )
            )
        )
        or (
            exhausted
            and (
                safe.get("coverage_gained") is not False
                or safe.get("gap_remains") is not True
                or safe.get("whole_run_lease_status")
                != "settled_exhausted_insufficient"
                or not safe.get("terminal_reason")
                or not blocker.get("blocker_class")
                or blocker.get("reason_code")
                != safe.get("terminal_reason")
                or admission_ref.get("admission_status")
                in {"admitted", "admitted_with_caveats"}
                or coverage_ref
                or consumed_candidate_ids
            )
        )
    ):
        raise SearchOSExistingGapRecoveryError("SearchOS recovery terminal broadens downstream authority")
    return safe


__all__ = [
    "EXISTING_GAP_BASIS_SCHEMA_VERSION",
    "MAXIMUM_EXISTING_GAP_RECOVERY_CYCLES",
    "RECOVERY_CYCLE_SCHEMA_VERSION",
    "RECOVERY_LEASE_SCHEMA_VERSION",
    "RECOVERY_PURPOSE_SCHEMA_VERSION",
    "RECOVERY_TERMINAL_SCHEMA_VERSION",
    "SearchOSExistingGapRecoveryError",
    "admit_searchos_existing_gap_recovery_cycle",
    "build_searchos_existing_gap_basis",
    "build_searchos_materially_novel_recovery_purpose",
    "finalize_searchos_existing_gap_recovery_cycle",
    "recovery_cycle_ref",
    "validate_active_searchos_recovery_cycle_ref",
    "validate_searchos_existing_gap_basis",
    "validate_searchos_recovery_cycle",
    "validate_searchos_recovery_purpose",
    "validate_searchos_recovery_terminal_aggregate",
]
