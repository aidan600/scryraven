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
from core.query_plan import DiscoveryJobClass
from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_OWNER,
    SEARCHOS_SEMANTIC_OBLIGATION_SCHEMA_VERSION,
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
SEARCHOS_RECOVERY_LEASE_SCHEMA_VERSION = "searchos_whole_run_recovery_lease_v2"
SEARCHOS_RECOVERY_CYCLE_ADMISSION_SCHEMA_VERSION = "searchos_recovery_cycle_admission_v2"
SEARCHOS_RECOVERY_CYCLE_TERMINAL_SCHEMA_VERSION = "searchos_recovery_cycle_terminal_v2"
SEARCHOS_RECOVERY_TERMINAL_AGGREGATE_SCHEMA_VERSION = "searchos_recovery_terminal_aggregate_v2"
RECOVERY_TERMINAL_BLOCKER_CLASS_BY_INTERPRETATION = {
    "structural_or_validation_blocker": "structural_or_validation",
    "provider_or_acquisition_blocker": "provider_or_acquisition",
    "lawful_recovery_exhaustion": "recovery_exhaustion",
    "lawful_recovery_ineligible": "recovery_ineligible",
}
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


def _recovery_slot_uncertainty_lineage(
    *,
    state: Mapping[str, Any],
    slot_id: str,
    component_ref: Mapping[str, Any],
    prior_slot: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Project one recovery slot into the unified acquisition lineage."""

    canonical = _mapping(state)
    prior = _mapping(prior_slot)
    component = deepcopy(_mapping(component_ref))
    component_id = _token(
        component.get("component_id"),
        "component_id",
    )
    obligations_by_id = _mapping(
        canonical.get("semantic_obligations_by_id")
    )
    semantic_obligation_ids = [
        str(item)
        for item in prior.get("semantic_obligation_ids") or ()
        if str(item or "").strip()
    ]
    legacy_lineage_defaulted = not bool(prior)
    semantic_obligations_to_admit: dict[str, dict[str, Any]] = {}
    if semantic_obligation_ids:
        for semantic_obligation_id in semantic_obligation_ids:
            semantic_obligation = deepcopy(
                _mapping(
                    obligations_by_id.get(semantic_obligation_id)
                )
            )
            if not semantic_obligation:
                raise SearchOSExistingGapRecoveryError(
                    "recovery slot inherits an orphaned semantic obligation"
                )
            if (
                semantic_obligation.get("binding_posture")
                == "unbound_required"
                or _mapping(
                    semantic_obligation.get(
                        "clarification_posture"
                    )
                ).get("clarification_required")
                is True
            ):
                raise SearchOSExistingGapRecoveryError(
                    "recovery slot cannot inherit unresolved semantic obligations"
                )
            semantic_obligations_to_admit[
                semantic_obligation_id
            ] = semantic_obligation
        legacy_lineage_defaulted = bool(
            prior.get("legacy_semantic_obligations_defaulted")
        )
    elif prior:
        raise SearchOSExistingGapRecoveryError(
            "recovery slot lacks canonical semantic obligations"
        )
    else:
        semantic_slot_ref = {
            "slot_id": f"{slot_id}:legacy-semantic",
            "slot_kind": "unknown_or_other",
            "status": "explicit",
            "materiality": "material",
            "candidate_values": [],
            "selected_value": None,
            "user_confirmation_required": False,
            "unresolved_material": False,
        }
        semantic_obligation_id = (
            "searchos-semantic-obligation:"
            f"{component_id}:{semantic_slot_ref['slot_id']}"
        )
        semantic_obligation_core = {
            "schema_version": (
                SEARCHOS_SEMANTIC_OBLIGATION_SCHEMA_VERSION
            ),
            "owner": SEARCHOS_OWNER,
            "semantic_obligation_id": semantic_obligation_id,
            "component_ref": component,
            "semantic_slot_ref": semantic_slot_ref,
            "acquisition_driving": True,
            "initial_discovery_job_class": (
                DiscoveryJobClass.STANDARD_DISCOVERY.value
            ),
            "binding_posture": "not_required",
            "interpretation_binding_ref": {},
            "interpretation_binding_count": 0,
            "clarification_posture": {
                "clarification_required": False,
                "component_ref": component,
                "semantic_slot_ref": semantic_slot_ref,
                "declared_candidates": [],
                "reason": None,
                "provider_dispatch_allowed": False,
            },
            "base_answer_contract_mutated": False,
            "satisfaction_claimed": False,
        }
        semantic_obligations_to_admit[semantic_obligation_id] = {
            **semantic_obligation_core,
            "semantic_obligation_digest": _digest(
                semantic_obligation_core
            ),
        }
        semantic_obligation_ids = [semantic_obligation_id]
    try:
        discovery_job_class = DiscoveryJobClass(
            str(
                prior.get("current_discovery_job_class")
                or DiscoveryJobClass.STANDARD_DISCOVERY.value
            )
        )
    except ValueError as exc:
        raise SearchOSExistingGapRecoveryError(
            "recovery slot has invalid provider-neutral discovery job lineage"
        ) from exc
    return {
        "semantic_obligation_ids": list(
            semantic_obligation_ids
        ),
        "current_discovery_semantic_obligation_ids": list(
            semantic_obligation_ids
        ),
        "current_query_plan_item_refs": [
            deepcopy(_mapping(item))
            for item in prior.get("current_query_plan_item_refs") or ()
            if _mapping(item)
        ],
        "current_discovery_job_class": discovery_job_class.value,
        "orientation_refinement_count": 0,
        "current_candidate_zero_useful_result": False,
        "legacy_semantic_obligations_defaulted": (
            legacy_lineage_defaulted
        ),
    }, semantic_obligations_to_admit


def _admit_recovery_semantic_obligations(
    *,
    state: dict[str, Any],
    component_id: str,
    semantic_obligation_ids: Sequence[str],
    semantic_obligations: Mapping[str, Mapping[str, Any]],
) -> None:
    obligations_by_id = state.setdefault(
        "semantic_obligations_by_id",
        {},
    )
    for semantic_obligation_id in semantic_obligation_ids:
        incoming = deepcopy(
            _mapping(
                semantic_obligations.get(semantic_obligation_id)
            )
        )
        existing = _mapping(
            obligations_by_id.get(semantic_obligation_id)
        )
        if existing and existing != incoming:
            raise SearchOSExistingGapRecoveryError(
                "recovery semantic obligation conflicts with canonical state"
            )
        obligations_by_id[semantic_obligation_id] = incoming
    ids_by_component = state.setdefault(
        "semantic_obligation_ids_by_component",
        {},
    )
    existing_ids = list(ids_by_component.get(component_id) or ())
    if existing_ids and existing_ids != list(semantic_obligation_ids):
        raise SearchOSExistingGapRecoveryError(
            "recovery component semantic cardinality conflicts with canonical state"
        )
    ids_by_component[component_id] = list(
        semantic_obligation_ids
    )


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
        raise SearchOSExistingGapRecoveryError("existing-gap basis requires completed Component Analyst case and RunKernel admission")
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
        and _mapping(latest_admission.get("component_analyst_case_ref"))
        and str(_mapping(latest_admission.get("component_analyst_case_ref")).get("role") or "")
        in {"component_analyst", "component_analyst_resume"}
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
        "component_analyst_case_ref": deepcopy(latest_admission["component_analyst_case_ref"]),
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
        or not _mapping(safe.get("component_admission_ref"))
        or not _mapping(safe.get("component_analyst_case_ref"))
        or str(_mapping(safe.get("component_analyst_case_ref")).get("role") or "")
        not in {"component_analyst", "component_analyst_resume"}
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
    (
        uncertainty_lineage,
        semantic_obligations_to_admit,
    ) = _recovery_slot_uncertainty_lineage(
        state=canonical,
        slot_id=recovery_slot_id,
        component_ref=basis["component_ref"],
        prior_slot=prior_slot,
    )
    recovery_slot_core = {
        "slot_id": recovery_slot_id,
        "slot_ordinal": len(canonical["active_slot_ids"]) + 1,
        "component_ref": deepcopy(basis["component_ref"]),
        "source_obligation_ref": deepcopy(basis["source_obligation_ref"]),
        "requirement_posture": SearchOSRequirementPosture.REQUIRED.value,
        **uncertainty_lineage,
        "posture": SearchOSSlotPosture.ACTIVE_UNJUDGED.value,
        "latest_reason": None,
        "current_candidate_state_ref": deepcopy(
            prior_slot.get("current_candidate_state_ref")
            or canonical["initial_candidate_state_ref"]
        ),
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
    recovery_slot_ref_identity = {
        "slot_id": recovery_slot_id,
        "component_id": prior_slot_ref["component_id"],
        "source_obligation_id": prior_slot_ref["source_obligation_id"],
        "component_ref": deepcopy(basis["component_ref"]),
        "source_obligation_ref": deepcopy(basis["source_obligation_ref"]),
        "semantic_obligation_ids": deepcopy(
            uncertainty_lineage["semantic_obligation_ids"]
        ),
        "query_plan_item_refs": deepcopy(
            uncertainty_lineage["current_query_plan_item_refs"]
        ),
        "discovery_job_class": uncertainty_lineage[
            "current_discovery_job_class"
        ],
        "recovery_cycle_id": cycle_id,
    }
    recovery_slot_core["slot_ref"] = {
        **recovery_slot_ref_identity,
        "slot_digest": _digest(recovery_slot_ref_identity),
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
    _admit_recovery_semantic_obligations(
        state=candidate,
        component_id=prior_slot_ref["component_id"],
        semantic_obligation_ids=uncertainty_lineage[
            "semantic_obligation_ids"
        ],
        semantic_obligations=semantic_obligations_to_admit,
    )
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
    cycle = validate_active_searchos_recovery_cycle_ref(
        canonical,
        cycle_ref,
    )
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


def _whole_run_recovery_lease_ref(lease: Mapping[str, Any]) -> dict[str, Any]:
    safe = _validate_envelope(
        lease,
        schema_version=SEARCHOS_RECOVERY_LEASE_SCHEMA_VERSION,
        id_field="recovery_lease_id",
        digest_field="recovery_lease_digest",
        prefix="searchos-whole-run-recovery-lease",
        label="SearchOS whole-run recovery lease",
    )
    return {
        "schema_version": SEARCHOS_RECOVERY_LEASE_SCHEMA_VERSION,
        "recovery_lease_id": safe["recovery_lease_id"],
        "recovery_lease_digest": safe["recovery_lease_digest"],
        "run_id": safe["run_id"],
        "request_id": safe["request_id"],
    }


def ensure_searchos_whole_run_recovery_lease(
    *,
    state: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Create or exactly reuse the one immutable whole-run recovery lease."""

    canonical = validate_searchos_state(state)
    existing = _mapping(canonical.get("recovery_lease"))
    if existing:
        lease_ref = _whole_run_recovery_lease_ref(existing)
        history = [
            _mapping(item)
            for item in canonical.get("recovery_lease_history") or ()
        ]
        if history != [lease_ref]:
            raise SearchOSExistingGapRecoveryError(
                "whole-run recovery lease history is not immutable"
            )
        return canonical, existing, True
    policy = _mapping(
        _mapping(canonical.get("policy_snapshot")).get("recovery_policy")
    )
    if (
        canonical.get("existing_gap_recovery_runtime_open") is not True
        or policy.get("runtime_open") is not True
        or policy.get("whole_run_lease_required") is not True
    ):
        raise SearchOSExistingGapRecoveryError(
            "whole-run SearchOS recovery lease policy is closed"
        )
    lease_core = {
        "schema_version": SEARCHOS_RECOVERY_LEASE_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "policy_snapshot_ref": deepcopy(canonical["policy_snapshot_ref"]),
        "lease_scope": (
            "whole_run_existing_component_and_searched_premise_recovery"
        ),
        "shared_across_recovery_classifications": True,
        "immutable": True,
        "allowed_consumers": [
            "SearchOSJudgment",
            "QueryPlan",
            "SEARCH",
            "READ",
            "SearchOSNavigation",
            "Acquisition",
            "EvidenceLedger",
            "ComponentAnalyst",
            "CrossComponentAnalyst",
            "ComponentCoverage",
        ],
        "search_planner_rerun_authorized": False,
        "new_acquisition_lane_authorized": False,
        "canonical_state": True,
    }
    lease = _envelope(
        lease_core,
        id_field="recovery_lease_id",
        digest_field="recovery_lease_digest",
        prefix="searchos-whole-run-recovery-lease",
    )
    candidate = deepcopy(canonical)
    candidate["recovery_lease"] = lease
    candidate["recovery_lease_history"] = [
        _whole_run_recovery_lease_ref(lease)
    ]
    return validate_searchos_state(_refresh_state(candidate)), lease, False


def _recovery_cycle_admission_ref(
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _validate_envelope(
        admission,
        schema_version=SEARCHOS_RECOVERY_CYCLE_ADMISSION_SCHEMA_VERSION,
        id_field="cycle_admission_id",
        digest_field="cycle_admission_digest",
        prefix="searchos-recovery-cycle-admission",
        label="SearchOS recovery cycle admission",
    )
    return {
        "schema_version": SEARCHOS_RECOVERY_CYCLE_ADMISSION_SCHEMA_VERSION,
        "cycle_id": safe["cycle_id"],
        "cycle_admission_id": safe["cycle_admission_id"],
        "cycle_admission_digest": safe["cycle_admission_digest"],
        "stable_replay_key": safe["stable_replay_key"],
        "recovery_classification": safe["recovery_classification"],
        "generation_depth": safe["generation_depth"],
    }


def validate_active_searchos_generalized_recovery_cycle_ref(
    state: Mapping[str, Any],
    cycle_admission_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the exact active generalized recovery-cycle admission ref."""

    canonical = validate_searchos_state(state)
    supplied = _mapping(cycle_admission_ref)
    active = _mapping(canonical.get("active_recovery_cycle_ref"))
    if supplied != active or not active:
        raise SearchOSExistingGapRecoveryError(
            "SearchOS recovery execution requires the exact active cycle"
        )
    admission = next(
        (
            _mapping(item)
            for item in canonical.get(
                "recovery_cycle_admission_history"
            )
            or ()
            if _recovery_cycle_admission_ref(_mapping(item)) == active
        ),
        None,
    )
    if admission is None:
        raise SearchOSExistingGapRecoveryError(
            "active SearchOS recovery admission is absent"
        )
    return admission


def _recovery_cycle_terminal_ref(
    terminal: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _validate_envelope(
        terminal,
        schema_version=SEARCHOS_RECOVERY_CYCLE_TERMINAL_SCHEMA_VERSION,
        id_field="cycle_terminal_id",
        digest_field="cycle_terminal_digest",
        prefix="searchos-recovery-cycle-terminal",
        label="SearchOS recovery cycle terminal",
    )
    return {
        "schema_version": SEARCHOS_RECOVERY_CYCLE_TERMINAL_SCHEMA_VERSION,
        "cycle_id": safe["cycle_id"],
        "cycle_terminal_id": safe["cycle_terminal_id"],
        "cycle_terminal_digest": safe["cycle_terminal_digest"],
        "terminal_status": safe["terminal_status"],
    }


def _recovery_policy(state: Mapping[str, Any]) -> dict[str, Any]:
    policy = _mapping(
        _mapping(state.get("policy_snapshot")).get("recovery_policy")
    )
    if policy.get("schema_version") != "searchos_recovery_policy_v2":
        raise SearchOSExistingGapRecoveryError(
            "generalized SearchOS recovery policy is absent"
        )
    return policy


def validate_searched_premise_generation_prework(
    state: Mapping[str, Any],
    *,
    generation_depth: int,
) -> dict[str, Any]:
    """Reject an ineligible searched generation before amendment mutation."""

    canonical = validate_searchos_state(state)
    policy = _recovery_policy(canonical)
    admissions = [_mapping(item) for item in canonical.get("recovery_cycle_admission_history") or ()]
    searched = [item for item in admissions if item.get("recovery_classification") == "searched_premise"]
    if _mapping(canonical.get("recovery_terminal_aggregate")).get("posture") == "settled":
        raise SearchOSExistingGapRecoveryError(
            "settled whole-run recovery aggregate rejects amendment mutation or work"
        )
    depth = int(generation_depth)
    maximum_generation = int(policy["maximum_searched_generation"])
    if depth > maximum_generation:
        raise SearchOSExistingGapRecoveryError(
            f"searched recovery generation {depth} is rejected before amendment mutation or work"
        )
    if depth != len(searched) + 1:
        raise SearchOSExistingGapRecoveryError("searched recovery generations must be contiguous and linear")
    if len(searched) >= int(policy["maximum_searched_premise_cycles_per_run"]):
        raise SearchOSExistingGapRecoveryError(
            "searched-premise recovery cycle budget is exhausted before amendment mutation or work"
        )
    if len(admissions) >= int(policy["maximum_total_cycles_per_run"]):
        raise SearchOSExistingGapRecoveryError(
            "whole-run SearchOS recovery cycle budget is exhausted before amendment mutation or work"
        )
    return {
        "status": "eligible_before_amendment_mutation",
        "generation_depth": depth,
        "expected_generation_depth": len(searched) + 1,
        "maximum_searched_generation": maximum_generation,
        "searched_cycle_count": len(searched),
        "total_cycle_count": len(admissions),
    }


def admit_searchos_recovery_cycle(
    *,
    state: Mapping[str, Any],
    lease: Mapping[str, Any],
    stable_replay_key: str,
    recovery_classification: str,
    proposal_ref: Mapping[str, Any],
    current_contract_ref: Mapping[str, Any],
    current_graph_ref: Mapping[str, Any] | None,
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    answer_target_refs: Sequence[Mapping[str, Any]],
    dependency_component_refs: Sequence[Mapping[str, Any]],
    generation_parent_ref: Mapping[str, Any],
    generation_depth: int,
    prior_terminal_slot_ref: Mapping[str, Any] | None = None,
    contract_amendment_record_ref: Mapping[str, Any] | None = None,
    contract_amendment_admission_ref: Mapping[str, Any] | None = None,
    contract_amendment_application_ref: Mapping[str, Any] | None = None,
    expected_parent_state_ref: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Admit one immutable recovery cycle under the shared whole-run lease."""

    canonical = validate_searchos_state(state)
    lease_ref = _whole_run_recovery_lease_ref(lease)
    if lease_ref != _whole_run_recovery_lease_ref(
        _mapping(canonical.get("recovery_lease"))
    ):
        raise SearchOSExistingGapRecoveryError(
            "recovery cycle does not use the whole-run lease"
        )
    if recovery_classification not in {
        "existing_component_gap",
        "searched_premise",
    }:
        raise SearchOSExistingGapRecoveryError(
            "SearchOS recovery classification is invalid"
        )
    replay_key = _token(stable_replay_key, "stable replay key")
    targets = [deepcopy(_mapping(item)) for item in answer_target_refs]
    dependencies = [
        deepcopy(_mapping(item)) for item in dependency_component_refs
    ]
    prior_slot_ref = deepcopy(_mapping(prior_terminal_slot_ref))
    if len({_digest(item) for item in targets}) != len(targets):
        raise SearchOSExistingGapRecoveryError(
            "recovery answer-target refs must be unique"
        )
    if targets != sorted(targets, key=_digest):
        raise SearchOSExistingGapRecoveryError(
            "recovery answer-target refs must use canonical sorted order"
        )
    if len({_digest(item) for item in dependencies}) != len(dependencies):
        raise SearchOSExistingGapRecoveryError(
            "recovery dependency refs must be unique"
        )
    if recovery_classification == "searched_premise" and not targets:
        raise SearchOSExistingGapRecoveryError(
            "searched-premise recovery requires answer targets"
        )
    if recovery_classification == "searched_premise" and prior_slot_ref:
        raise SearchOSExistingGapRecoveryError(
            "searched-premise recovery cannot fabricate a prior slot"
        )
    prior_slot: dict[str, Any] = {}
    if recovery_classification == "existing_component_gap":
        prior_slot_id = _token(
            prior_slot_ref.get("slot_id"),
            "existing-gap prior terminal slot id",
        )
        prior_slot = _mapping(
            _mapping(canonical.get("slots_by_id")).get(prior_slot_id)
        )
        if (
            not prior_slot
            or _mapping(prior_slot.get("slot_ref")) != prior_slot_ref
            or _mapping(prior_slot.get("component_ref"))
            != _mapping(component_ref)
            or _mapping(prior_slot.get("source_obligation_ref"))
            != _mapping(source_obligation_ref)
            or prior_slot.get("posture")
            not in {
                SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value,
                SearchOSSlotPosture.UNRESOLVED_HANDOFF.value,
                SearchOSSlotPosture.STALE_OR_INVALID.value,
            }
        ):
            raise SearchOSExistingGapRecoveryError(
                "existing-gap recovery prior terminal slot is stale"
            )
    admission_input = {
        "stable_replay_key": replay_key,
        "recovery_classification": recovery_classification,
        "proposal_ref": deepcopy(_mapping(proposal_ref)),
        "current_contract_ref": deepcopy(_mapping(current_contract_ref)),
        "current_graph_ref": deepcopy(_mapping(current_graph_ref)),
        "component_ref": deepcopy(_mapping(component_ref)),
        "source_obligation_ref": deepcopy(_mapping(source_obligation_ref)),
        "prior_terminal_slot_ref": prior_slot_ref,
        "answer_target_refs": targets,
        "dependency_component_refs": dependencies,
        "generation_parent_ref": deepcopy(_mapping(generation_parent_ref)),
        "generation_depth": int(generation_depth),
        "contract_amendment_record_ref": deepcopy(
            _mapping(contract_amendment_record_ref)
        ),
        "contract_amendment_admission_ref": deepcopy(
            _mapping(contract_amendment_admission_ref)
        ),
        "contract_amendment_application_ref": deepcopy(
            _mapping(contract_amendment_application_ref)
        ),
    }
    admission_input_digest = _digest(admission_input)

    # Exact replay is resolved before currentness or active-cycle checks.
    for prior in canonical.get("recovery_cycle_admission_history") or ():
        prior_map = _mapping(prior)
        if prior_map.get("stable_replay_key") != replay_key:
            continue
        if prior_map.get("admission_input_digest") != admission_input_digest:
            raise SearchOSExistingGapRecoveryError(
                "SearchOS recovery cycle stable replay identity conflict"
            )
        return canonical, {
            "status": "exact_replay",
            "work_authorized": False,
            "cycle_admission": deepcopy(prior_map),
            "cycle_admission_ref": _recovery_cycle_admission_ref(prior_map),
            "terminal_ref": next(
                (
                    _recovery_cycle_terminal_ref(item)
                    for item in canonical.get(
                        "recovery_cycle_terminal_history"
                    )
                    or ()
                    if _mapping(item).get("cycle_id")
                    == prior_map.get("cycle_id")
                ),
                {},
            ),
        }

    expected_state = _mapping(expected_parent_state_ref)
    if expected_state and expected_state != {
        "state_id": canonical.get("state_id"),
        "state_digest": canonical.get("state_digest"),
    }:
        raise SearchOSExistingGapRecoveryError(
            "unknown recovery cycle proposal is stale against SearchOS state"
        )
    if _mapping(canonical.get("active_recovery_cycle_ref")):
        raise SearchOSExistingGapRecoveryError(
            "SearchOS permits only one linear active recovery cycle"
        )
    policy = _recovery_policy(canonical)
    admissions = [
        _mapping(item)
        for item in canonical.get("recovery_cycle_admission_history") or ()
    ]
    existing_count = sum(
        item.get("recovery_classification") == "existing_component_gap"
        for item in admissions
    )
    searched = [
        item
        for item in admissions
        if item.get("recovery_classification") == "searched_premise"
    ]
    if len(admissions) >= int(policy["maximum_total_cycles_per_run"]):
        raise SearchOSExistingGapRecoveryError(
            "whole-run SearchOS recovery cycle budget is exhausted"
        )
    if (
        recovery_classification == "existing_component_gap"
        and existing_count
        >= int(policy["maximum_existing_component_cycles_per_run"])
    ):
        raise SearchOSExistingGapRecoveryError(
            "existing-component recovery cycle budget is exhausted"
        )
    if (
        recovery_classification == "searched_premise"
        and len(searched)
        >= int(policy["maximum_searched_premise_cycles_per_run"])
    ):
        raise SearchOSExistingGapRecoveryError(
            "searched-premise recovery cycle budget is exhausted"
        )

    depth = int(generation_depth)
    if recovery_classification == "searched_premise":
        if depth > int(policy["maximum_searched_generation"]):
            raise SearchOSExistingGapRecoveryError(f"searched recovery generation {depth} is rejected before work")
        if depth != len(searched) + 1:
            raise SearchOSExistingGapRecoveryError(
                "searched recovery generations must be contiguous and linear"
            )
        if any(int(item.get("generation_depth") or 0) == depth for item in searched):
            raise SearchOSExistingGapRecoveryError(
                "only one searched premise is allowed per generation"
            )
        if depth > 1:
            prior_cycle_id = searched[-1]["cycle_id"]
            prior_terminal = next(
                (
                    item
                    for item in canonical.get(
                        "recovery_cycle_terminal_history"
                    )
                    or ()
                    if _mapping(item).get("cycle_id") == prior_cycle_id
                ),
                None,
            )
            if prior_terminal is None or _mapping(
                generation_parent_ref
            ) != _recovery_cycle_terminal_ref(_mapping(prior_terminal)):
                raise SearchOSExistingGapRecoveryError(
                    "searched recovery generation parent is stale or branches"
                )
        if not all(
            (
                _mapping(contract_amendment_record_ref),
                _mapping(contract_amendment_admission_ref),
                _mapping(contract_amendment_application_ref),
            )
        ):
            raise SearchOSExistingGapRecoveryError(
                "searched-premise recovery requires the exact applied amendment chain"
            )
    elif depth != 0:
        raise SearchOSExistingGapRecoveryError("existing-component recovery generation depth must be 0")
    if _mapping(canonical.get("recovery_terminal_aggregate")).get("posture") == "settled":
        raise SearchOSExistingGapRecoveryError("settled whole-run recovery aggregate cannot admit new work")

    cycle_seed = {
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "admission_input_digest": admission_input_digest,
        "ordinal": len(admissions) + 1,
    }
    cycle_id = "searchos-recovery-cycle:" + _digest(cycle_seed)[:24]
    slot_seed = {
        "cycle_id": cycle_id,
        "component_ref": component_ref,
        "source_obligation_ref": source_obligation_ref,
    }
    slot_id = "searchos-recovery-slot:" + _digest(slot_seed)[:24]
    (
        uncertainty_lineage,
        semantic_obligations_to_admit,
    ) = _recovery_slot_uncertainty_lineage(
        state=canonical,
        slot_id=slot_id,
        component_ref=component_ref,
        prior_slot=prior_slot,
    )
    slot_core = {
        "slot_id": slot_id,
        "slot_ordinal": len(canonical.get("slots_by_id") or {}) + 1,
        "component_ref": deepcopy(_mapping(component_ref)),
        "source_obligation_ref": deepcopy(_mapping(source_obligation_ref)),
        "requirement_posture": SearchOSRequirementPosture.REQUIRED.value,
        **uncertainty_lineage,
        "posture": SearchOSSlotPosture.ACTIVE_UNJUDGED.value,
        "latest_reason": None,
        "current_candidate_state_ref": {},
        "current_window_ref": {},
        "candidate_use_option_refs": [],
        "candidate_option_dispositions": {},
        "custody_refs": [],
        "semantic_handoff_refs": [],
        "action_history": [],
        "judgment_call_count": 0,
        "candidate_window_count": 0,
        "candidate_wave_count": 0,
        "read_nomination_count": 0,
        "followup_query_nomination_count": 0,
        "satisfaction_claimed": False,
        "coverage_upgrade_claimed": False,
        "pending_navigation_decision_ref": {},
        "pending_navigation_candidate_ref": {},
        "navigation_selection_count": 0,
        "navigation_availability_reason": None,
        "recovery_cycle_ref": {"cycle_id": cycle_id},
        "recovery_lease_ref": lease_ref,
        "prior_slot_absent": recovery_classification == "searched_premise",
        "prior_terminal_slot_ref": prior_slot_ref,
    }
    slot_ref_identity = {
        "slot_id": slot_id,
        "component_id": _token(
            _mapping(component_ref).get("component_id"),
            "component_id",
        ),
        "source_obligation_id": _token(
            _mapping(source_obligation_ref).get("source_obligation_id")
            or _mapping(source_obligation_ref).get("candidate_id"),
            "source_obligation_id",
        ),
        "component_ref": deepcopy(_mapping(component_ref)),
        "source_obligation_ref": deepcopy(
            _mapping(source_obligation_ref)
        ),
        "semantic_obligation_ids": deepcopy(
            uncertainty_lineage["semantic_obligation_ids"]
        ),
        "query_plan_item_refs": deepcopy(
            uncertainty_lineage["current_query_plan_item_refs"]
        ),
        "discovery_job_class": uncertainty_lineage[
            "current_discovery_job_class"
        ],
        "recovery_cycle_id": cycle_id,
    }
    slot_core["slot_ref"] = {
        **slot_ref_identity,
        "slot_digest": _digest(slot_ref_identity),
    }
    slot_core["slot_state_digest"] = _digest(slot_core)
    admission_core = {
        "schema_version": SEARCHOS_RECOVERY_CYCLE_ADMISSION_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "cycle_id": cycle_id,
        "cycle_ordinal": len(admissions) + 1,
        **admission_input,
        "admission_input_digest": admission_input_digest,
        "whole_run_lease_ref": lease_ref,
        "recovery_slot_ref": deepcopy(slot_core["slot_ref"]),
        "prior_slot_absent": recovery_classification == "searched_premise",
        "prior_terminal_slot_ref": prior_slot_ref,
        "initial_candidate_window_empty": True,
        "search_planner_rerun": False,
        "new_acquisition_lane": False,
        "status": "admitted",
        "immutable_admission_record": True,
        "canonical_state": True,
    }
    admission = _envelope(
        admission_core,
        id_field="cycle_admission_id",
        digest_field="cycle_admission_digest",
        prefix="searchos-recovery-cycle-admission",
    )
    slot_core["current_candidate_state_ref"] = deepcopy(
        _mapping(prior_slot.get("current_candidate_state_ref"))
        or _mapping(canonical.get("initial_candidate_state_ref"))
        or _recovery_cycle_admission_ref(admission)
    )
    slot_core.pop("slot_state_digest", None)
    slot_core["slot_state_digest"] = _digest(slot_core)
    candidate = deepcopy(canonical)
    _admit_recovery_semantic_obligations(
        state=candidate,
        component_id=_token(
            _mapping(component_ref).get("component_id"),
            "component_id",
        ),
        semantic_obligation_ids=uncertainty_lineage[
            "semantic_obligation_ids"
        ],
        semantic_obligations=semantic_obligations_to_admit,
    )
    candidate["answer_contract_ref"] = deepcopy(
        _mapping(current_contract_ref)
    )
    candidate["slots_by_id"][slot_id] = slot_core
    candidate["active_slot_ids"].append(slot_id)
    candidate["required_slot_ids"].append(slot_id)
    candidate["recovery_cycle_admission_history"].append(admission)
    candidate["active_recovery_cycle_ref"] = (
        _recovery_cycle_admission_ref(admission)
    )
    budget = candidate["budget"]
    reserved = int(
        _mapping(candidate["policy_snapshot"]).get(
            "minimum_reserved_judgment_calls_per_required_slot"
        )
        or 0
    )
    additional = int(
        _mapping(candidate["policy_snapshot"]).get(
            "additional_judgment_call_pool_per_active_slot"
        )
        or 0
    )
    budget["judgment_call_ceiling"] += reserved + additional
    budget["reserved_calls_remaining_by_required_slot"][slot_id] = reserved
    budget["shared_calls_remaining"] += additional
    candidate["recovery_terminal_aggregate"] = _build_generalized_recovery_terminal_aggregate(
        candidate,
        lawful_selected_recovery_work_remains=True,
    )
    return validate_searchos_state(_refresh_state(candidate)), {
        "status": "admitted",
        "work_authorized": True,
        "cycle_admission": admission,
        "cycle_admission_ref": _recovery_cycle_admission_ref(admission),
        "recovery_slot_ref": deepcopy(slot_core["slot_ref"]),
    }


def terminalize_searchos_recovery_cycle(
    *,
    state: Mapping[str, Any],
    cycle_admission_ref: Mapping[str, Any],
    terminal_status: str,
    terminal_reason: str | None,
    terminal_interpretation: str | None,
    lawful_selected_recovery_work_remains: bool,
    expenditure: Mapping[str, Any],
    component_admission_ref: Mapping[str, Any] | None = None,
    component_coverage_ref: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Append one immutable terminal record without rewriting its admission."""

    canonical = validate_searchos_state(state)
    supplied = _mapping(cycle_admission_ref)
    cycle_id = _token(supplied.get("cycle_id"), "cycle_id")
    prior_terminals = [
        _mapping(item)
        for item in canonical.get("recovery_cycle_terminal_history") or ()
        if _mapping(item).get("cycle_id") == cycle_id
    ]
    if prior_terminals:
        prior = prior_terminals[0]
        normalized_terminal_reason = _clean_terminal_reason(terminal_reason)
        requested_terminal_input = {
            "terminal_status": terminal_status,
            "terminal_reason": normalized_terminal_reason,
            "terminal_interpretation": terminal_interpretation,
            "lawful_selected_recovery_work_remains": bool(lawful_selected_recovery_work_remains),
            "terminal_blocker": (
                {
                    "blocker_class": (RECOVERY_TERMINAL_BLOCKER_CLASS_BY_INTERPRETATION[str(terminal_interpretation)]),
                    "interpretation": terminal_interpretation,
                    "reason_code": normalized_terminal_reason,
                }
                if terminal_status != "recovered"
                and terminal_interpretation in RECOVERY_TERMINAL_BLOCKER_CLASS_BY_INTERPRETATION
                else {}
            ),
            "expenditure": deepcopy(_mapping(expenditure)),
            "component_admission_ref": deepcopy(
                _mapping(component_admission_ref)
            ),
            "component_coverage_ref": deepcopy(
                _mapping(component_coverage_ref)
            ),
        }
        if prior.get("terminal_input_digest") != _digest(
            requested_terminal_input
        ):
            raise SearchOSExistingGapRecoveryError(
                "SearchOS recovery terminal replay identity conflict"
            )
        return canonical, deepcopy(prior)
    if supplied != _mapping(canonical.get("active_recovery_cycle_ref")):
        raise SearchOSExistingGapRecoveryError(
            "unknown SearchOS recovery terminal request is stale"
        )
    admission = next(
        (
            _mapping(item)
            for item in canonical.get("recovery_cycle_admission_history") or ()
            if _mapping(item).get("cycle_id") == cycle_id
        ),
        None,
    )
    if admission is None:
        raise SearchOSExistingGapRecoveryError(
            "SearchOS recovery cycle admission is absent"
        )
    if terminal_status not in {"recovered", "exhausted_insufficient", "failed"}:
        raise SearchOSExistingGapRecoveryError("SearchOS recovery terminal status is invalid")
    if terminal_status != "recovered" and not _clean_terminal_reason(terminal_reason):
        raise SearchOSExistingGapRecoveryError("unsuccessful SearchOS recovery terminal requires a reason")
    if terminal_status == "recovered":
        if terminal_interpretation is not None:
            raise SearchOSExistingGapRecoveryError("recovered SearchOS terminal cannot carry a blocker interpretation")
    elif terminal_interpretation not in RECOVERY_TERMINAL_BLOCKER_CLASS_BY_INTERPRETATION:
        raise SearchOSExistingGapRecoveryError("unsuccessful SearchOS terminal requires a typed interpretation")
    expected_status = (
        "failed"
        if terminal_interpretation
        in {
            "structural_or_validation_blocker",
            "provider_or_acquisition_blocker",
        }
        else "exhausted_insufficient"
    )
    if terminal_status != "recovered" and terminal_status != expected_status:
        raise SearchOSExistingGapRecoveryError("SearchOS terminal status and typed interpretation conflict")
    expenditure_safe = deepcopy(_mapping(expenditure))
    if any(
        not isinstance(expenditure_safe.get(key), int)
        or int(expenditure_safe.get(key)) < 0
        for key in (
            "logical_judgment_calls",
            "search_queries",
            "read_operations",
            "navigation_operations",
            "acquisition_operations",
        )
    ):
        raise SearchOSExistingGapRecoveryError(
            "SearchOS recovery expenditure is incomplete or negative"
        )
    terminal_input = {
        "terminal_status": terminal_status,
        "terminal_reason": _clean_terminal_reason(terminal_reason),
        "terminal_interpretation": terminal_interpretation,
        "lawful_selected_recovery_work_remains": bool(lawful_selected_recovery_work_remains),
        "terminal_blocker": (
            {
                "blocker_class": (RECOVERY_TERMINAL_BLOCKER_CLASS_BY_INTERPRETATION[str(terminal_interpretation)]),
                "interpretation": terminal_interpretation,
                "reason_code": _clean_terminal_reason(terminal_reason),
            }
            if terminal_status != "recovered"
            else {}
        ),
        "expenditure": expenditure_safe,
        "component_admission_ref": deepcopy(
            _mapping(component_admission_ref)
        ),
        "component_coverage_ref": deepcopy(_mapping(component_coverage_ref)),
    }
    terminal_core = {
        "schema_version": SEARCHOS_RECOVERY_CYCLE_TERMINAL_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "cycle_id": cycle_id,
        "cycle_admission_ref": deepcopy(supplied),
        "terminal_input_digest": _digest(terminal_input),
        **terminal_input,
        "admission_record_rewritten": False,
        "lease_terminal": False,
        "canonical_state": True,
    }
    terminal = _envelope(
        terminal_core,
        id_field="cycle_terminal_id",
        digest_field="cycle_terminal_digest",
        prefix="searchos-recovery-cycle-terminal",
    )
    candidate = deepcopy(canonical)
    candidate["recovery_cycle_terminal_history"].append(terminal)
    candidate["recovery_expenditure_history"].append(
        {
            "cycle_id": cycle_id,
            "cycle_admission_ref": deepcopy(supplied),
            "cycle_terminal_ref": _recovery_cycle_terminal_ref(terminal),
            "expenditure": expenditure_safe,
        }
    )
    candidate["active_recovery_cycle_ref"] = {}
    slot_ref = _mapping(admission.get("recovery_slot_ref"))
    slot_id = slot_ref.get("slot_id")
    if slot_id in candidate["slots_by_id"]:
        slot = deepcopy(candidate["slots_by_id"][slot_id])
        slot["posture"] = (
            SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value
            if terminal_status == "recovered"
            else SearchOSSlotPosture.UNRESOLVED_HANDOFF.value
        )
        slot["latest_reason"] = _clean_terminal_reason(terminal_reason)
        slot["slot_state_digest"] = _digest(
            {
                key: value
                for key, value in slot.items()
                if key != "slot_state_digest"
            }
        )
        candidate["slots_by_id"][slot_id] = slot
    candidate["recovery_terminal_aggregate"] = _build_generalized_recovery_terminal_aggregate(
        candidate,
        lawful_selected_recovery_work_remains=(lawful_selected_recovery_work_remains),
        settled_interpretation=(
            None
            if lawful_selected_recovery_work_remains
            else ("recovery_completed" if terminal_status == "recovered" else str(terminal_interpretation))
        ),
    )
    return validate_searchos_state(_refresh_state(candidate)), terminal


def _build_generalized_recovery_terminal_aggregate(
    state: Mapping[str, Any],
    *,
    lawful_selected_recovery_work_remains: bool,
    settled_interpretation: str | None = None,
) -> dict[str, Any]:
    """Project cumulative recovery posture under the one immutable lease."""

    candidate = _mapping(state)
    admissions = [_mapping(item) for item in candidate.get("recovery_cycle_admission_history") or ()]
    terminals = [_mapping(item) for item in candidate.get("recovery_cycle_terminal_history") or ()]
    active_cycle_ref = _mapping(candidate.get("active_recovery_cycle_ref"))
    policy = _recovery_policy(candidate)
    cumulative_expenditure = {
        key: sum(
            int(_mapping(_mapping(item).get("expenditure")).get(key) or 0)
            for item in candidate.get("recovery_expenditure_history") or ()
        )
        for key in (
            "logical_judgment_calls",
            "search_queries",
            "read_operations",
            "navigation_operations",
            "acquisition_operations",
        )
    }
    settled = bool(not active_cycle_ref and not lawful_selected_recovery_work_remains)
    if settled and settled_interpretation is None:
        raise SearchOSExistingGapRecoveryError("settled recovery aggregate requires a typed interpretation")
    aggregate_core = {
        "schema_version": SEARCHOS_RECOVERY_TERMINAL_AGGREGATE_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": candidate["run_id"],
        "request_id": candidate["request_id"],
        "whole_run_lease_ref": _whole_run_recovery_lease_ref(candidate["recovery_lease"]),
        "cycle_admission_refs": [_recovery_cycle_admission_ref(item) for item in admissions],
        "cycle_terminal_refs": [_recovery_cycle_terminal_ref(item) for item in terminals],
        "active_cycle_ref": active_cycle_ref,
        "expenditure_history_digest": _digest(candidate["recovery_expenditure_history"]),
        "cumulative_expenditure": cumulative_expenditure,
        "mode_cycle_generation_caps": {
            "maximum_existing_component_cycles_per_run": int(policy["maximum_existing_component_cycles_per_run"]),
            "maximum_searched_premise_cycles_per_run": int(policy["maximum_searched_premise_cycles_per_run"]),
            "maximum_total_cycles_per_run": int(policy["maximum_total_cycles_per_run"]),
            "maximum_searched_generation": int(policy["maximum_searched_generation"]),
        },
        "admission_count": len(admissions),
        "terminal_count": len(terminals),
        "posture": "settled" if settled else "open",
        "lawful_selected_recovery_work_remains": bool(lawful_selected_recovery_work_remains),
        "settled_interpretation": (settled_interpretation if settled else None),
        "canonical_state": True,
    }
    return _envelope(
        aggregate_core,
        id_field="terminal_aggregate_id",
        digest_field="terminal_aggregate_digest",
        prefix="searchos-recovery-terminal-aggregate",
    )


def validate_searchos_generalized_recovery_terminal_aggregate(
    aggregate: Mapping[str, Any],
    *,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the typed cumulative whole-run recovery projection."""

    safe = _validate_envelope(
        aggregate,
        schema_version=(SEARCHOS_RECOVERY_TERMINAL_AGGREGATE_SCHEMA_VERSION),
        id_field="terminal_aggregate_id",
        digest_field="terminal_aggregate_digest",
        prefix="searchos-recovery-terminal-aggregate",
        label="generalized SearchOS recovery terminal aggregate",
    )
    admission_refs = [_mapping(item) for item in safe.get("cycle_admission_refs") or ()]
    terminal_refs = [_mapping(item) for item in safe.get("cycle_terminal_refs") or ()]
    active_ref = _mapping(safe.get("active_cycle_ref"))
    cumulative = _mapping(safe.get("cumulative_expenditure"))
    caps = _mapping(safe.get("mode_cycle_generation_caps"))
    posture = safe.get("posture")
    settled_interpretation = safe.get("settled_interpretation")
    allowed_settled = {
        *RECOVERY_TERMINAL_BLOCKER_CLASS_BY_INTERPRETATION,
        "recovery_completed",
    }
    cumulative_keys = {
        "logical_judgment_calls",
        "search_queries",
        "read_operations",
        "navigation_operations",
        "acquisition_operations",
    }
    cap_keys = {
        "maximum_existing_component_cycles_per_run",
        "maximum_searched_premise_cycles_per_run",
        "maximum_total_cycles_per_run",
        "maximum_searched_generation",
    }
    if (
        safe.get("owner") != SEARCHOS_OWNER
        or safe.get("canonical_state") is not True
        or not _mapping(safe.get("whole_run_lease_ref"))
        or int(safe.get("admission_count") or 0) != len(admission_refs)
        or int(safe.get("terminal_count") or 0) != len(terminal_refs)
        or len(terminal_refs) > len(admission_refs)
        or set(cumulative) != cumulative_keys
        or any(not isinstance(cumulative.get(key), int) or int(cumulative.get(key)) < 0 for key in cumulative_keys)
        or set(caps) != cap_keys
        or any(not isinstance(caps.get(key), int) or int(caps.get(key)) < 0 for key in cap_keys)
        or (
            posture == "open"
            and (
                settled_interpretation is not None
                or (not active_ref and safe.get("lawful_selected_recovery_work_remains") is not True)
            )
        )
        or (
            posture == "settled"
            and (
                active_ref
                or safe.get("lawful_selected_recovery_work_remains") is not False
                or settled_interpretation not in allowed_settled
            )
        )
        or posture not in {"open", "settled"}
    ):
        raise SearchOSExistingGapRecoveryError("generalized SearchOS recovery aggregate is invalid")
    if state is not None:
        canonical = validate_searchos_state(state)
        policy = _recovery_policy(canonical)
        expected_caps = {
            key: int(policy[key])
            for key in (
                "maximum_existing_component_cycles_per_run",
                "maximum_searched_premise_cycles_per_run",
                "maximum_total_cycles_per_run",
                "maximum_searched_generation",
            )
        }
        expected_cumulative = {
            key: sum(
                int(_mapping(_mapping(item).get("expenditure")).get(key) or 0)
                for item in canonical.get("recovery_expenditure_history") or ()
            )
            for key in cumulative
        }
        if (
            _mapping(canonical.get("recovery_terminal_aggregate")) != safe
            or safe.get("run_id") != canonical.get("run_id")
            or safe.get("request_id") != canonical.get("request_id")
            or admission_refs
            != [_recovery_cycle_admission_ref(item) for item in canonical.get("recovery_cycle_admission_history") or ()]
            or terminal_refs
            != [_recovery_cycle_terminal_ref(item) for item in canonical.get("recovery_cycle_terminal_history") or ()]
            or active_ref != _mapping(canonical.get("active_recovery_cycle_ref"))
            or caps != expected_caps
            or cumulative != expected_cumulative
            or safe.get("expenditure_history_digest") != _digest(canonical.get("recovery_expenditure_history") or ())
        ):
            raise SearchOSExistingGapRecoveryError("generalized recovery aggregate is stale against SearchOS state")
    return safe


def settle_searchos_recovery_terminal_aggregate(
    *,
    state: Mapping[str, Any],
    settled_interpretation: str,
) -> dict[str, Any]:
    """Settle the whole-run aggregate once no lawful selected work remains."""

    if settled_interpretation not in {
        *RECOVERY_TERMINAL_BLOCKER_CLASS_BY_INTERPRETATION,
        "recovery_completed",
    }:
        raise SearchOSExistingGapRecoveryError("recovery aggregate settlement requires a typed interpretation")
    canonical = validate_searchos_state(state)
    existing = _mapping(canonical.get("recovery_terminal_aggregate"))
    if existing.get("posture") == "settled":
        if existing.get("settled_interpretation") != (settled_interpretation):
            raise SearchOSExistingGapRecoveryError("settled recovery aggregate cannot be reinterpreted")
        return canonical
    if _mapping(canonical.get("active_recovery_cycle_ref")):
        raise SearchOSExistingGapRecoveryError("active recovery cycle prevents whole-run settlement")
    candidate = deepcopy(canonical)
    candidate["recovery_terminal_aggregate"] = _build_generalized_recovery_terminal_aggregate(
        candidate,
        lawful_selected_recovery_work_remains=False,
        settled_interpretation=settled_interpretation,
    )
    return validate_searchos_state(_refresh_state(candidate))


def _clean_terminal_reason(value: Any) -> str | None:
    if value is None:
        return None
    reason = " ".join(str(value).strip().split())
    return reason[:240] or None


__all__ = [
    "EXISTING_GAP_BASIS_SCHEMA_VERSION",
    "MAXIMUM_EXISTING_GAP_RECOVERY_CYCLES",
    "RECOVERY_CYCLE_SCHEMA_VERSION",
    "RECOVERY_LEASE_SCHEMA_VERSION",
    "RECOVERY_PURPOSE_SCHEMA_VERSION",
    "RECOVERY_TERMINAL_BLOCKER_CLASS_BY_INTERPRETATION",
    "RECOVERY_TERMINAL_SCHEMA_VERSION",
    "SEARCHOS_RECOVERY_CYCLE_ADMISSION_SCHEMA_VERSION",
    "SEARCHOS_RECOVERY_CYCLE_TERMINAL_SCHEMA_VERSION",
    "SEARCHOS_RECOVERY_LEASE_SCHEMA_VERSION",
    "SEARCHOS_RECOVERY_TERMINAL_AGGREGATE_SCHEMA_VERSION",
    "SearchOSExistingGapRecoveryError",
    "admit_searchos_recovery_cycle",
    "admit_searchos_existing_gap_recovery_cycle",
    "build_searchos_existing_gap_basis",
    "build_searchos_materially_novel_recovery_purpose",
    "finalize_searchos_existing_gap_recovery_cycle",
    "ensure_searchos_whole_run_recovery_lease",
    "recovery_cycle_ref",
    "validate_active_searchos_generalized_recovery_cycle_ref",
    "validate_active_searchos_recovery_cycle_ref",
    "validate_searchos_existing_gap_basis",
    "validate_searchos_recovery_cycle",
    "validate_searchos_recovery_purpose",
    "validate_searchos_generalized_recovery_terminal_aggregate",
    "validate_searchos_recovery_terminal_aggregate",
    "validate_searched_premise_generation_prework",
    "settle_searchos_recovery_terminal_aggregate",
    "terminalize_searchos_recovery_cycle",
]
