"""Topology-neutral, transient Sufficiency consumption of direct semantic state.

This module does not decide readiness and does not create semantic authority.  It
mechanically validates already-current Phase-1 component admission refs and an
already-bound Cross-Component Analyst artifact, then packages their exact
material for the existing Sufficiency owner.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from core.multicomponent_graph_scheduling import (
    canonical_multicomponent_contract_ref,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_ANALYST_RESUME,
    ROLE_CROSS_COMPONENT_ANALYST,
    role_artifact_ref,
    safe_packet_digest,
    validate_multicomponent_role_artifact,
)

DIRECT_SEMANTIC_SUFFICIENCY_CONSUMPTION_SCHEMA_VERSION = "direct_semantic_sufficiency_consumption_v1"
DIRECT_SEMANTIC_PROVENANCE_ENVELOPE_SCHEMA_VERSION = "direct_semantic_sufficiency_provenance_envelope_v1"

_CANONICAL_TERMINAL_ADMISSION_STATUSES = frozenset(
    {
        "admitted",
        "admitted_with_caveats",
        "unsupported",
        "blocked",
    }
)
_MULTICOMPONENT_COMPONENT_ADMISSION_OWNER = "RunKernel.MulticomponentComponentAdmission"
_MULTICOMPONENT_COMPONENT_ADMISSION_PROJECTION_FIELDS = frozenset(
    {
        "schema_version",
        "owner",
        "canonical_state",
        "trace_only",
        "storage_only",
        "run_id",
        "request_id",
        "accepted_contract_version",
        "accepted_contract_digest",
        "component_admission_refs",
        "component_count",
        "admitted_component_count",
        "blocked_component_count",
        "logical_component_analyst_evaluations",
        "physical_component_analyst_calls",
        "latest_action_id",
        "projection_digest",
    }
)
_SUPPORTING_ADMISSION_STATUSES = frozenset({"admitted", "admitted_with_caveats"})
_SUPPORT_REF_FIELDS = (
    "admitted_claim_ref",
    "semantic_observation_ref",
    "component_coverage_ref",
)
_LOCAL_SYNTHESIS_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,39}\Z")


class DirectSemanticSufficiencyConsumptionError(ValueError):
    """Raised when direct semantic state loses exact mechanical binding."""


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: Any, *, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    return text[:limit] if text else None


def _mapping_list(value: Any, *, field: str) -> list[dict[str, Any]]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise DirectSemanticSufficiencyConsumptionError(f"{field} must be an exact ordered array")
    items = list(value)
    if any(not isinstance(item, Mapping) for item in items):
        raise DirectSemanticSufficiencyConsumptionError(f"{field} must contain only mappings")
    return [deepcopy(dict(item)) for item in items]


def _text_list(value: Any, *, field: str, limit: int = 1000) -> list[str]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise DirectSemanticSufficiencyConsumptionError(f"{field} must be an exact text array")
    out: list[str] = []
    for raw in value:
        text = _clean_text(raw, limit=limit)
        if not text or text != raw:
            raise DirectSemanticSufficiencyConsumptionError(f"{field} contains invalid bounded text")
        out.append(text)
    if len(out) != len(set(out)):
        raise DirectSemanticSufficiencyConsumptionError(f"{field} cannot contain duplicate values")
    return out


def _digest_list(field: str, values: Sequence[Mapping[str, Any]]) -> str:
    return safe_packet_digest({field: [deepcopy(dict(item)) for item in values]})


def direct_component_admission_refs_digest(
    component_admission_refs: Sequence[Mapping[str, Any]],
) -> str:
    """Digest an exact ordered canonical component-admission ref list."""

    return _digest_list("component_admission_refs", component_admission_refs)


def cross_relationship_proposal_digest(proposal: Mapping[str, Any]) -> str:
    """Digest the exact bounded semantic fields of one Cross proposal."""

    return safe_packet_digest(deepcopy(dict(proposal)))


def cross_relationship_entries_digest(
    cross_relationship_entries: Sequence[Mapping[str, Any]],
) -> str:
    """Digest an exact ordered topology-neutral Cross relationship list."""

    return _digest_list(
        "cross_relationship_entries",
        cross_relationship_entries,
    )


def direct_semantic_relationship_entries_digest(
    cross_relationship_entries: Sequence[Mapping[str, Any]],
) -> str:
    """Stable public name used by Sufficiency, FAP, and quantitative reproof."""

    return cross_relationship_entries_digest(cross_relationship_entries)


def direct_semantic_provenance_envelope_digest(
    provenance_envelope: Mapping[str, Any],
) -> str:
    """Digest a provenance envelope without its declared digest field."""

    core = deepcopy(dict(provenance_envelope))
    core.pop("provenance_digest", None)
    return safe_packet_digest(core)


def direct_semantic_sufficiency_consumption_digest(
    consumption: Mapping[str, Any],
) -> str:
    """Digest direct Sufficiency consumption without its declared digest."""

    core = deepcopy(dict(consumption))
    core.pop("consumption_digest", None)
    return safe_packet_digest(core)


def _validate_contract(
    accepted_contract: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    contract = deepcopy(dict(accepted_contract))
    contract_ref = canonical_multicomponent_contract_ref(contract)
    component_refs = _mapping_list(
        contract.get("accepted_answer_component_refs"),
        field="accepted_answer_component_refs",
    )
    component_ids = [_clean_text(item.get("component_id"), limit=160) or "" for item in component_refs]
    if (
        contract.get("canonical_state") is not True
        or not _clean_text(contract.get("owner"), limit=180)
        or not _clean_text(contract.get("run_id"), limit=180)
        or not _clean_text(contract.get("request_id"), limit=180)
        or not _clean_text(contract.get("accepted_contract_version"), limit=180)
        or not _clean_text(contract.get("accepted_contract_digest"), limit=180)
        or not 1 <= len(component_refs) <= 5
        or contract.get("accepted_answer_component_count") != len(component_refs)
        or any(not item for item in component_ids)
        or len(component_ids) != len(set(component_ids))
        or any(
            not _clean_text(item.get("component_revision"), limit=180)
            or not _clean_text(item.get("component_digest"), limit=180)
            for item in component_refs
        )
    ):
        raise DirectSemanticSufficiencyConsumptionError(
            "direct Sufficiency consumption requires one exact accepted contract"
        )
    return contract, component_refs, contract_ref


def _validate_analyst_case_ref(
    case_ref: Mapping[str, Any],
    *,
    run_id: str,
    request_id: str,
    logical_evaluation_key: str,
) -> None:
    action_ref = _mapping(case_ref.get("authorized_action_ref"))
    if (
        case_ref.get("schema_version") != "multicomponent_semantic_role_artifact_v1"
        or case_ref.get("role") not in {ROLE_COMPONENT_ANALYST, ROLE_COMPONENT_ANALYST_RESUME}
        or case_ref.get("run_id") != run_id
        or case_ref.get("request_id") != request_id
        or case_ref.get("logical_evaluation_key") != logical_evaluation_key
        or case_ref.get("logical_evaluations") != 1
        or case_ref.get("physical_calls") != 1
        or not _clean_text(case_ref.get("artifact_id"), limit=180)
        or not _clean_text(case_ref.get("artifact_digest"), limit=180)
        or not _clean_text(case_ref.get("input_packet_digest"), limit=180)
        or not _clean_text(action_ref.get("action_id"), limit=180)
        or not _clean_text(action_ref.get("observation_type"), limit=180)
    ):
        raise DirectSemanticSufficiencyConsumptionError("component admission has an invalid Component Analyst case ref")


def validate_direct_component_admission_refs(
    *,
    accepted_contract: Mapping[str, Any],
    component_admission_refs: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Validate exact order and terminal mechanics of canonical admission refs."""

    contract, component_refs, _contract_ref = _validate_contract(accepted_contract)
    admissions = _mapping_list(
        component_admission_refs,
        field="component_admission_refs",
    )
    if len(admissions) != len(component_refs):
        raise DirectSemanticSufficiencyConsumptionError(
            "component admissions do not match accepted component cardinality"
        )

    run_id = str(contract["run_id"])
    request_id = str(contract["request_id"])
    for component, admission in zip(component_refs, admissions, strict=True):
        component_id = str(component["component_id"])
        status = admission.get("admission_status")
        case_ref = _mapping(admission.get("component_analyst_case_ref"))
        support_refs_are_mappings = all(
            field in admission and isinstance(admission.get(field), Mapping) for field in _SUPPORT_REF_FIELDS
        )
        support_refs = tuple(_mapping(admission.get(field)) for field in _SUPPORT_REF_FIELDS)
        if (
            admission.get("schema_version") != "multicomponent_component_admission_ref_v1"
            or admission.get("owner") != _MULTICOMPONENT_COMPONENT_ADMISSION_OWNER
            or admission.get("canonical_state") is not True
            or admission.get("run_id") != run_id
            or admission.get("request_id") != request_id
            or admission.get("accepted_contract_version") != contract.get("accepted_contract_version")
            or admission.get("accepted_contract_digest") != contract.get("accepted_contract_digest")
            or admission.get("component_id") != component_id
            or admission.get("logical_evaluation_key") != component_id
            or admission.get("component_revision") != component.get("component_revision")
            or admission.get("component_digest") != component.get("component_digest")
            or status not in _CANONICAL_TERMINAL_ADMISSION_STATUSES
            or admission.get("current") is not True
            or admission.get("stale") is not False
            or not case_ref
            or not support_refs_are_mappings
            or (status in _SUPPORTING_ADMISSION_STATUSES and not all(support_refs))
            or (status not in _SUPPORTING_ADMISSION_STATUSES and any(support_refs))
        ):
            raise DirectSemanticSufficiencyConsumptionError(
                f"component admission is not exact current canonical state: {component_id}"
            )
        _validate_analyst_case_ref(
            case_ref,
            run_id=run_id,
            request_id=request_id,
            logical_evaluation_key=component_id,
        )
        analyst_alias = admission.get("analyst_finding_ref")
        if analyst_alias is not None and _mapping(analyst_alias) != case_ref:
            raise DirectSemanticSufficiencyConsumptionError("component admission Analyst compatibility ref diverged")

        claim_ref, observation_ref, coverage_ref = support_refs
        evidence_refs = _mapping_list(
            admission.get("evidence_refs", ()),
            field=f"component_admission_refs[{component_id}].evidence_refs",
        )
        if status in _SUPPORTING_ADMISSION_STATUSES:
            claim_text = _clean_text(claim_ref.get("claim_text"), limit=1200)
            if (
                not _clean_text(claim_ref.get("claim_id"), limit=180)
                or not claim_text
                or not _clean_text(claim_ref.get("claim_digest"), limit=180)
                or not _clean_text(observation_ref.get("observation_id"), limit=180)
                or not _clean_text(observation_ref.get("observation_digest"), limit=180)
                or not _clean_text(coverage_ref.get("coverage_record_id"), limit=180)
                or not _clean_text(coverage_ref.get("coverage_record_digest"), limit=180)
            ):
                raise DirectSemanticSufficiencyConsumptionError(
                    "supporting component admission has malformed support refs"
                )
            coverage_bindings = {
                "run_id": run_id,
                "request_id": request_id,
                "answer_component_id": component_id,
                "component_revision": component.get("component_revision"),
                "component_digest": component.get("component_digest"),
                "accepted_contract_version": contract.get("accepted_contract_version"),
                "accepted_contract_digest": contract.get("accepted_contract_digest"),
            }
            if any(
                key in coverage_ref and coverage_ref.get(key) != expected for key, expected in coverage_bindings.items()
            ):
                raise DirectSemanticSufficiencyConsumptionError(
                    "component coverage ref is bound to foreign canonical state"
                )
        elif evidence_refs:
            raise DirectSemanticSufficiencyConsumptionError(
                "non-supporting component admission cannot carry evidence refs"
            )

    return tuple(admissions)


def _proposal_payload_from_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "synthesis_key": entry.get("synthesis_key"),
        "claim_text": entry.get("claim_text"),
        "relationship_type": entry.get("relationship_type"),
        "component_inputs": list(entry.get("component_inputs") or ()),
        "synthesis_inputs": list(entry.get("synthesis_inputs") or ()),
        "caveats": list(entry.get("caveats") or ()),
        "nonclaims": list(entry.get("nonclaims") or ()),
        "blockers": list(entry.get("blockers") or ()),
    }


def validate_cross_relationship_entries(
    cross_relationship_entries: Sequence[Mapping[str, Any]],
    *,
    component_ids: Sequence[str],
    cross_component_artifact_ref: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Validate exact Cross proposal fields and their topology-neutral DAG."""

    entries = _mapping_list(
        cross_relationship_entries,
        field="cross_relationship_entries",
    )
    if len(entries) > 4:
        raise DirectSemanticSufficiencyConsumptionError("Cross relationship entry count exceeds the installed bound")
    known_components = [str(item) for item in component_ids]
    if any(not item for item in known_components) or len(known_components) != len(set(known_components)):
        raise DirectSemanticSufficiencyConsumptionError("Cross relationship validation requires unique component IDs")
    expected_artifact_ref = _mapping(cross_component_artifact_ref)
    required_fields = {
        "entry_kind",
        "synthesis_key",
        "claim_text",
        "relationship_type",
        "component_inputs",
        "synthesis_inputs",
        "caveats",
        "nonclaims",
        "blockers",
        "proposal_digest",
        "cross_component_artifact_ref",
    }
    keys: list[str] = []
    dependencies: dict[str, list[str]] = {}
    for entry in entries:
        key = _clean_text(entry.get("synthesis_key"), limit=40)
        claim_text = _clean_text(entry.get("claim_text"), limit=1200)
        relationship_type = _clean_text(entry.get("relationship_type"), limit=160)
        component_inputs = _text_list(
            entry.get("component_inputs"),
            field="cross relationship component_inputs",
            limit=160,
        )
        synthesis_inputs = _text_list(
            entry.get("synthesis_inputs"),
            field="cross relationship synthesis_inputs",
            limit=40,
        )
        _text_list(entry.get("caveats"), field="cross relationship caveats")
        _text_list(entry.get("nonclaims"), field="cross relationship nonclaims")
        _text_list(entry.get("blockers"), field="cross relationship blockers")
        proposal_payload = _proposal_payload_from_entry(entry)
        if (
            set(entry) != required_fields
            or entry.get("entry_kind") != "cross_relationship"
            or not key
            or not _LOCAL_SYNTHESIS_KEY.fullmatch(key)
            or not claim_text
            or claim_text != entry.get("claim_text")
            or not relationship_type
            or relationship_type != entry.get("relationship_type")
            or not (component_inputs or synthesis_inputs)
            or any(item not in known_components for item in component_inputs)
            or entry.get("proposal_digest") != cross_relationship_proposal_digest(proposal_payload)
            or not _mapping(entry.get("cross_component_artifact_ref"))
            or (expected_artifact_ref and _mapping(entry.get("cross_component_artifact_ref")) != expected_artifact_ref)
        ):
            raise DirectSemanticSufficiencyConsumptionError("Cross relationship entry lost exact proposal binding")
        keys.append(key)
        dependencies[key] = synthesis_inputs

    if len(keys) != len(set(keys)):
        raise DirectSemanticSufficiencyConsumptionError("Cross relationship entries cannot repeat a synthesis key")
    known_keys = set(keys)
    if any(
        dependency not in known_keys or dependency == key
        for key, dependency_keys in dependencies.items()
        for dependency in dependency_keys
    ):
        raise DirectSemanticSufficiencyConsumptionError("Cross relationship entry has an unknown or self dependency")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visiting:
            raise DirectSemanticSufficiencyConsumptionError("Cross relationship dependencies contain a cycle")
        if key in visited:
            return
        visiting.add(key)
        for dependency in dependencies.get(key, ()):
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in keys:
        visit(key)
    return tuple(entries)


def _direct_component_entry(
    *,
    component_ref: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
) -> dict[str, Any]:
    claim_ref = _mapping(admission_ref.get("admitted_claim_ref"))
    analyst_ref = _mapping(admission_ref.get("component_analyst_case_ref"))
    return {
        "entry_kind": "direct_component",
        "component_id": admission_ref.get("component_id"),
        "component_label": component_ref.get("user_facing_label"),
        "component_question": component_ref.get("user_facing_question"),
        "component_purpose": component_ref.get("component_purpose"),
        "accepted_component_ref": deepcopy(dict(component_ref)),
        "support_kind": "direct",
        "semantic_inference_depth": 0,
        "claim_id": claim_ref.get("claim_id"),
        "claim_text": claim_ref.get("claim_text"),
        "claim_digest": claim_ref.get("claim_digest"),
        "admission_status": admission_ref.get("admission_status"),
        "current": True,
        "stale": False,
        "semantic_observation_ref": deepcopy(_mapping(admission_ref.get("semantic_observation_ref"))),
        "component_analyst_case_ref": deepcopy(analyst_ref),
        "analyst_finding_ref": deepcopy(analyst_ref),
        "specialist_quantitative_authority_ref": deepcopy(
            _mapping(admission_ref.get("specialist_quantitative_authority_ref"))
        ),
        "component_coverage_ref": deepcopy(_mapping(admission_ref.get("component_coverage_ref"))),
        "evidence_refs": [
            deepcopy(dict(item)) for item in admission_ref.get("evidence_refs") or () if isinstance(item, Mapping)
        ],
        "required_caveats": list(admission_ref.get("required_caveats") or ()),
        "preserved_nonclaims": list(admission_ref.get("preserved_nonclaims") or ()),
    }


def _cross_relationship_entry(
    proposal: Mapping[str, Any],
    *,
    cross_component_artifact_ref: Mapping[str, Any],
) -> dict[str, Any]:
    proposal_payload = {
        "synthesis_key": proposal.get("synthesis_key"),
        "claim_text": proposal.get("claim_text"),
        "relationship_type": proposal.get("relationship_type"),
        "component_inputs": list(proposal.get("component_inputs") or ()),
        "synthesis_inputs": list(proposal.get("synthesis_inputs") or ()),
        "caveats": list(proposal.get("caveats") or ()),
        "nonclaims": list(proposal.get("nonclaims") or ()),
        "blockers": list(proposal.get("blockers") or ()),
    }
    return {
        "entry_kind": "cross_relationship",
        **deepcopy(proposal_payload),
        "proposal_digest": cross_relationship_proposal_digest(proposal_payload),
        "cross_component_artifact_ref": deepcopy(dict(cross_component_artifact_ref)),
    }


def validate_direct_semantic_provenance_envelope(
    provenance_envelope: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the exact transient provenance envelope and declared digest."""

    envelope = deepcopy(dict(provenance_envelope))
    required_fields = {
        "schema_version",
        "accepted_contract_ref",
        "accepted_component_refs",
        "requested_synthesis_directive",
        "component_admission_refs",
        "component_count",
        "component_admission_refs_digest",
        "cross_component_artifact_ref",
        "cross_relationship_entry_count",
        "cross_relationship_entries_digest",
        "cross_relationship_proposal_digests",
        "self_audit",
        "provenance_digest",
    }
    contract_ref = _mapping(envelope.get("accepted_contract_ref"))
    accepted_component_refs = _mapping_list(
        envelope.get("accepted_component_refs"),
        field="provenance accepted_component_refs",
    )
    admissions = _mapping_list(
        envelope.get("component_admission_refs"),
        field="provenance component_admission_refs",
    )
    artifact_ref = _mapping(envelope.get("cross_component_artifact_ref"))
    proposal_digests = envelope.get("cross_relationship_proposal_digests")
    if isinstance(proposal_digests, str | bytes) or not isinstance(proposal_digests, Sequence):
        raise DirectSemanticSufficiencyConsumptionError("Cross proposal digests must be an exact ordered array")
    proposal_digests = list(proposal_digests)
    relationship_count = envelope.get("cross_relationship_entry_count")
    directive = envelope.get("requested_synthesis_directive")
    self_audit = envelope.get("self_audit")
    if (
        set(envelope) != required_fields
        or envelope.get("schema_version") != DIRECT_SEMANTIC_PROVENANCE_ENVELOPE_SCHEMA_VERSION
        or not contract_ref
        or contract_ref.get("canonical_state") is not True
        or not _clean_text(contract_ref.get("run_id"), limit=180)
        or not _clean_text(contract_ref.get("request_id"), limit=180)
        or not _clean_text(contract_ref.get("accepted_contract_version"), limit=180)
        or not _clean_text(contract_ref.get("accepted_contract_digest"), limit=180)
        or len(accepted_component_refs) != len(admissions)
        or [item.get("component_id") for item in accepted_component_refs]
        != [item.get("component_id") for item in admissions]
        or any(
            component.get("component_revision") != admission.get("component_revision")
            or component.get("component_digest") != admission.get("component_digest")
            for component, admission in zip(
                accepted_component_refs,
                admissions,
                strict=True,
            )
        )
        or (directive is not None and _clean_text(directive, limit=360) != directive)
        or not admissions
        or envelope.get("component_count") != len(admissions)
        or envelope.get("component_admission_refs_digest") != direct_component_admission_refs_digest(admissions)
        or not isinstance(relationship_count, int)
        or isinstance(relationship_count, bool)
        or not 0 <= relationship_count <= 4
        or len(proposal_digests) != relationship_count
        or any(not _clean_text(item, limit=180) for item in proposal_digests)
        or envelope.get("provenance_digest") != direct_semantic_provenance_envelope_digest(envelope)
    ):
        raise DirectSemanticSufficiencyConsumptionError("direct semantic provenance envelope lost exact binding")
    if artifact_ref:
        if (
            artifact_ref.get("role") != ROLE_CROSS_COMPONENT_ANALYST
            or artifact_ref.get("run_id") != contract_ref.get("run_id")
            or artifact_ref.get("request_id") != contract_ref.get("request_id")
            or not _clean_text(self_audit, limit=1200)
            or self_audit != _clean_text(self_audit, limit=1200)
        ):
            raise DirectSemanticSufficiencyConsumptionError("Cross provenance ref or self-audit is invalid")
    elif relationship_count or proposal_digests or self_audit is not None:
        raise DirectSemanticSufficiencyConsumptionError("Cross-free provenance cannot carry relationship material")
    return envelope


def validate_direct_semantic_provenance_and_relationship_entries(
    *,
    direct_semantic_provenance: Mapping[str, Any],
    cross_relationship_entries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Rebind one provenance envelope to its exact Cross relationship list.

    Empty provenance with an empty relationship list is the ordinary non-direct
    FAP case. Any Cross relationship material requires complete provenance.
    """

    provenance = _mapping(direct_semantic_provenance)
    entries_supplied = _mapping_list(
        cross_relationship_entries,
        field="cross_relationship_entries",
    )
    if not provenance:
        if entries_supplied:
            raise DirectSemanticSufficiencyConsumptionError(
                "Cross relationship entries require direct semantic provenance"
            )
        return {}
    envelope = validate_direct_semantic_provenance_envelope(provenance)
    component_ids = [
        str(item.get("component_id") or "")
        for item in envelope.get("component_admission_refs") or ()
        if isinstance(item, Mapping)
    ]
    entries = validate_cross_relationship_entries(
        entries_supplied,
        component_ids=component_ids,
        cross_component_artifact_ref=_mapping(envelope.get("cross_component_artifact_ref")),
    )
    if (
        envelope.get("cross_relationship_entry_count") != len(entries)
        or envelope.get("cross_relationship_entries_digest") != direct_semantic_relationship_entries_digest(entries)
        or envelope.get("cross_relationship_proposal_digests") != [item["proposal_digest"] for item in entries]
    ):
        raise DirectSemanticSufficiencyConsumptionError(
            "Cross relationship entries do not match direct semantic provenance"
        )
    return {
        "direct_semantic_provenance": envelope,
        "cross_relationship_entries": [deepcopy(dict(item)) for item in entries],
    }


def _validate_direct_component_entries(
    entries: Sequence[Mapping[str, Any]],
    *,
    component_admission_refs: Sequence[Mapping[str, Any]],
    accepted_component_refs: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    direct_entries = _mapping_list(entries, field="direct_component_entries")
    supporting_refs = [
        deepcopy(dict(item))
        for item in component_admission_refs
        if item.get("admission_status") in _SUPPORTING_ADMISSION_STATUSES
    ]
    component_by_id = {
        str(item.get("component_id") or ""): deepcopy(dict(item))
        for item in accepted_component_refs
        if isinstance(item, Mapping)
    }
    if [item.get("component_id") for item in direct_entries] != [item.get("component_id") for item in supporting_refs]:
        raise DirectSemanticSufficiencyConsumptionError(
            "direct component entries do not preserve supporting admission order"
        )
    for entry, admission in zip(direct_entries, supporting_refs, strict=True):
        component = _mapping(entry.get("accepted_component_ref"))
        canonical_component = component_by_id.get(
            str(admission.get("component_id") or ""),
            {},
        )
        expected = _direct_component_entry(
            component_ref=canonical_component,
            admission_ref=admission,
        )
        if component != canonical_component or entry != expected:
            raise DirectSemanticSufficiencyConsumptionError(
                "direct component entry lost exact canonical admission binding"
            )
    return tuple(direct_entries)


def validate_direct_semantic_sufficiency_consumption(
    consumption: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebind one full transient direct-consumption packet mechanically."""

    value = deepcopy(dict(consumption))
    required_fields = {
        "schema_version",
        "direct_semantic_provenance",
        "component_admission_refs",
        "component_count",
        "direct_component_entries",
        "direct_component_entry_count",
        "cross_relationship_entries",
        "cross_relationship_entry_count",
        "query_resolution_proposals",
        "consumption_digest",
    }
    envelope = validate_direct_semantic_provenance_envelope(_mapping(value.get("direct_semantic_provenance")))
    admissions = _mapping_list(
        value.get("component_admission_refs"),
        field="component_admission_refs",
    )
    direct_entries = _validate_direct_component_entries(
        value.get("direct_component_entries", ()),
        component_admission_refs=admissions,
        accepted_component_refs=_mapping_list(
            envelope.get("accepted_component_refs"),
            field="provenance accepted_component_refs",
        ),
    )
    component_ids = [str(item.get("component_id") or "") for item in admissions]
    artifact_ref = _mapping(envelope.get("cross_component_artifact_ref"))
    relationship_entries = validate_cross_relationship_entries(
        value.get("cross_relationship_entries", ()),
        component_ids=component_ids,
        cross_component_artifact_ref=artifact_ref,
    )
    validate_direct_semantic_provenance_and_relationship_entries(
        direct_semantic_provenance=envelope,
        cross_relationship_entries=relationship_entries,
    )
    query_resolution_proposals = _mapping_list(
        value.get("query_resolution_proposals", ()),
        field="query_resolution_proposals",
    )
    if (
        set(value) != required_fields
        or value.get("schema_version") != DIRECT_SEMANTIC_SUFFICIENCY_CONSUMPTION_SCHEMA_VERSION
        or admissions != envelope.get("component_admission_refs")
        or value.get("component_count") != len(admissions)
        or value.get("direct_component_entry_count") != len(direct_entries)
        or value.get("cross_relationship_entry_count") != len(relationship_entries)
        or envelope.get("cross_relationship_entry_count") != len(relationship_entries)
        or envelope.get("cross_relationship_entries_digest") != cross_relationship_entries_digest(relationship_entries)
        or envelope.get("cross_relationship_proposal_digests")
        != [item["proposal_digest"] for item in relationship_entries]
        or len(query_resolution_proposals) > 5
        or (query_resolution_proposals and not artifact_ref)
        or value.get("consumption_digest") != direct_semantic_sufficiency_consumption_digest(value)
    ):
        raise DirectSemanticSufficiencyConsumptionError("direct semantic Sufficiency consumption lost exact binding")
    return value


def build_direct_semantic_sufficiency_consumption(
    *,
    accepted_contract: Mapping[str, Any],
    component_admission_refs: Sequence[Mapping[str, Any]],
    cross_component_artifact: Mapping[str, Any] | None,
    requested_synthesis_directive: str,
) -> dict[str, Any]:
    """Build transient direct semantic material for the existing Sufficiency owner."""

    contract, component_refs, contract_ref = _validate_contract(accepted_contract)
    admissions = validate_direct_component_admission_refs(
        accepted_contract=contract,
        component_admission_refs=component_admission_refs,
    )
    component_ids = [str(item["component_id"]) for item in component_refs]
    directive = _clean_text(requested_synthesis_directive, limit=360)
    contract_directive = _clean_text(
        _mapping(contract.get("question_meaning_metadata")).get("requested_synthesis_directive"),
        limit=360,
    )
    if len(component_refs) >= 2 and (not directive or directive != contract_directive):
        raise DirectSemanticSufficiencyConsumptionError(
            "requested synthesis directive is not exact accepted-contract meaning"
        )

    all_components_supporting = all(
        item.get("admission_status") in _SUPPORTING_ADMISSION_STATUSES for item in admissions
    )
    if cross_component_artifact is None:
        if len(component_refs) >= 2 and all_components_supporting:
            raise DirectSemanticSufficiencyConsumptionError(
                "supporting multicomponent direct state requires its exact Cross artifact"
            )
        cross_artifact_ref: dict[str, Any] = {}
        cross_entries: tuple[dict[str, Any], ...] = ()
        self_audit: str | None = None
        query_resolution_proposals: list[dict[str, Any]] = []
    else:
        if len(component_refs) < 2 or not all_components_supporting:
            raise DirectSemanticSufficiencyConsumptionError(
                "Cross artifact cannot consume non-supporting direct component state"
            )
        artifact = validate_multicomponent_role_artifact(
            cross_component_artifact,
            expected_role=ROLE_CROSS_COMPONENT_ANALYST,
        )
        if (
            artifact.get("run_id") != contract.get("run_id")
            or artifact.get("request_id") != contract.get("request_id")
            or artifact.get("accepted_contract_ref") != contract_ref
            or _mapping(artifact.get("graph_ref"))
        ):
            raise DirectSemanticSufficiencyConsumptionError(
                "Cross artifact is not bound to the exact direct accepted contract"
            )
        cross_artifact_ref = role_artifact_ref(artifact)
        semantic_output = _mapping(artifact.get("semantic_output"))
        self_audit = _clean_text(semantic_output.get("self_audit"), limit=1200)
        if not self_audit or self_audit != semantic_output.get("self_audit"):
            raise DirectSemanticSufficiencyConsumptionError("Cross artifact requires an exact bounded self-audit")
        cross_entries = tuple(
            _cross_relationship_entry(
                proposal,
                cross_component_artifact_ref=cross_artifact_ref,
            )
            for proposal in _mapping_list(
                semantic_output.get("synthesis_proposals"),
                field="Cross synthesis_proposals",
            )
        )
        cross_entries = validate_cross_relationship_entries(
            cross_entries,
            component_ids=component_ids,
            cross_component_artifact_ref=cross_artifact_ref,
        )
        query_resolution_proposals = _mapping_list(
            semantic_output.get("query_resolution_proposals", ()),
            field="Cross query_resolution_proposals",
        )

    direct_entries = tuple(
        _direct_component_entry(
            component_ref=component,
            admission_ref=admission,
        )
        for component, admission in zip(component_refs, admissions, strict=True)
        if admission.get("admission_status") in _SUPPORTING_ADMISSION_STATUSES
    )
    relationship_entries_digest = cross_relationship_entries_digest(cross_entries)
    envelope_core = {
        "schema_version": DIRECT_SEMANTIC_PROVENANCE_ENVELOPE_SCHEMA_VERSION,
        "accepted_contract_ref": deepcopy(contract_ref),
        "accepted_component_refs": [deepcopy(dict(item)) for item in component_refs],
        "requested_synthesis_directive": directive,
        "component_admission_refs": [deepcopy(dict(item)) for item in admissions],
        "component_count": len(admissions),
        "component_admission_refs_digest": (direct_component_admission_refs_digest(admissions)),
        "cross_component_artifact_ref": deepcopy(cross_artifact_ref),
        "cross_relationship_entry_count": len(cross_entries),
        "cross_relationship_entries_digest": relationship_entries_digest,
        "cross_relationship_proposal_digests": [item["proposal_digest"] for item in cross_entries],
        "self_audit": self_audit,
    }
    envelope = {
        **envelope_core,
        "provenance_digest": safe_packet_digest(envelope_core),
    }
    consumption_core = {
        "schema_version": DIRECT_SEMANTIC_SUFFICIENCY_CONSUMPTION_SCHEMA_VERSION,
        "direct_semantic_provenance": envelope,
        "component_admission_refs": [deepcopy(dict(item)) for item in admissions],
        "component_count": len(admissions),
        "direct_component_entries": [deepcopy(dict(item)) for item in direct_entries],
        "direct_component_entry_count": len(direct_entries),
        "cross_relationship_entries": [deepcopy(dict(item)) for item in cross_entries],
        "cross_relationship_entry_count": len(cross_entries),
        "query_resolution_proposals": deepcopy(query_resolution_proposals),
    }
    consumption = {
        **consumption_core,
        "consumption_digest": safe_packet_digest(consumption_core),
    }
    return validate_direct_semantic_sufficiency_consumption(consumption)


def rebind_direct_semantic_sufficiency_consumption_to_current_state(
    supplied_consumption: Mapping[str, Any],
    *,
    accepted_contract: Mapping[str, Any],
    component_admission_projection: Mapping[str, Any],
    role_projections: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild one supplied packet solely from existing current owners."""

    supplied = validate_direct_semantic_sufficiency_consumption(supplied_consumption)
    contract = deepcopy(dict(accepted_contract))
    admission_projection = _mapping(component_admission_projection)
    admission_refs = _mapping_list(
        admission_projection.get("component_admission_refs"),
        field="current component_admission_refs",
    )
    projection_core = {
        key: deepcopy(value) for key, value in admission_projection.items() if key != "projection_digest"
    }
    if (
        set(admission_projection) != _MULTICOMPONENT_COMPONENT_ADMISSION_PROJECTION_FIELDS
        or admission_projection.get("schema_version") != "multicomponent_component_admission_projection_v1"
        or admission_projection.get("owner") != _MULTICOMPONENT_COMPONENT_ADMISSION_OWNER
        or admission_projection.get("canonical_state") is not True
        or admission_projection.get("trace_only") is not False
        or admission_projection.get("storage_only") is not False
        or admission_projection.get("run_id") != contract.get("run_id")
        or admission_projection.get("request_id") != contract.get("request_id")
        or admission_projection.get("accepted_contract_version") != contract.get("accepted_contract_version")
        or admission_projection.get("accepted_contract_digest") != contract.get("accepted_contract_digest")
        or admission_projection.get("component_count") != len(admission_refs)
        or admission_projection.get("projection_digest") != safe_packet_digest(projection_core)
        or admission_projection.get("admitted_component_count")
        != sum(item.get("admission_status") in _SUPPORTING_ADMISSION_STATUSES for item in admission_refs)
        or admission_projection.get("blocked_component_count")
        != sum(item.get("admission_status") not in _SUPPORTING_ADMISSION_STATUSES for item in admission_refs)
        or admission_projection.get("logical_component_analyst_evaluations")
        != sum(int(item.get("logical_component_analyst_evaluations") or 0) for item in admission_refs)
        or admission_projection.get("physical_component_analyst_calls")
        != sum(int(item.get("physical_component_analyst_calls") or 0) for item in admission_refs)
        or (admission_refs and admission_projection.get("latest_action_id") != admission_refs[-1].get("action_id"))
    ):
        raise DirectSemanticSufficiencyConsumptionError(
            "direct semantic consumption requires current component admission authority"
        )

    provenance = _mapping(supplied.get("direct_semantic_provenance"))
    artifact_ref = _mapping(provenance.get("cross_component_artifact_ref"))
    cross_artifact: dict[str, Any] | None = None
    if artifact_ref:
        role = str(artifact_ref.get("role") or "")
        logical_key = str(artifact_ref.get("logical_evaluation_key") or "")
        current_artifact = _mapping(role_projections.get(f"multicomponent_role:{role}:{logical_key}"))
        if (
            role != ROLE_CROSS_COMPONENT_ANALYST
            or not current_artifact
            or role_artifact_ref(current_artifact) != artifact_ref
        ):
            raise DirectSemanticSufficiencyConsumptionError(
                "direct semantic consumption Cross ref is not current RunKernel authority"
            )
        cross_artifact = current_artifact

    directive = (
        _clean_text(
            _mapping(contract.get("question_meaning_metadata")).get("requested_synthesis_directive"),
            limit=360,
        )
        or ""
    )
    expected = build_direct_semantic_sufficiency_consumption(
        accepted_contract=contract,
        component_admission_refs=admission_refs,
        cross_component_artifact=cross_artifact,
        requested_synthesis_directive=directive,
    )
    if supplied != expected:
        raise DirectSemanticSufficiencyConsumptionError(
            "direct semantic consumption is not the exact current owner-derived packet"
        )
    return expected


__all__ = [
    "DIRECT_SEMANTIC_PROVENANCE_ENVELOPE_SCHEMA_VERSION",
    "DIRECT_SEMANTIC_SUFFICIENCY_CONSUMPTION_SCHEMA_VERSION",
    "DirectSemanticSufficiencyConsumptionError",
    "build_direct_semantic_sufficiency_consumption",
    "cross_relationship_entries_digest",
    "cross_relationship_proposal_digest",
    "direct_component_admission_refs_digest",
    "direct_semantic_provenance_envelope_digest",
    "direct_semantic_relationship_entries_digest",
    "direct_semantic_sufficiency_consumption_digest",
    "rebind_direct_semantic_sufficiency_consumption_to_current_state",
    "validate_cross_relationship_entries",
    "validate_direct_component_admission_refs",
    "validate_direct_semantic_provenance_and_relationship_entries",
    "validate_direct_semantic_provenance_envelope",
    "validate_direct_semantic_sufficiency_consumption",
]
