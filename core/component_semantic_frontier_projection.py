"""Bounded, zero-authority component semantic frontier projection.

The projector reads existing canonical runtime state and emits only booleans,
counts, closed tokens, and already-canonical opaque component identifiers.  It
does not mutate the supplied state and no runtime decision may consume it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from core.multicomponent_component_admission import (
    component_analyst_input_binding_mismatch_from_exception,
    project_component_analyst_input_binding_mismatch_v1,
)
from core.multicomponent_role_runtime import COMPONENT_ANALYST_CASE_POSTURES

COMPONENT_SEMANTIC_FRONTIER_SCHEMA_VERSION = "component_semantic_frontier_v1"
COMPONENT_SEMANTIC_FRONTIER_TRACE_KEY = "component_semantic_frontier_v1"
COMPONENT_SEMANTIC_FRONTIER_EXCEPTION_ATTRIBUTE = (
    "component_semantic_frontier_v1"
)

_ADMISSION_STATUSES = frozenset(
    {"admitted", "admitted_with_caveats", "unsupported", "blocked"}
)
_SEARCHOS_POSTURES = frozenset(
    {
        "active_unjudged",
        "awaiting_interpretation_binding",
        "awaiting_followup_discover",
        "awaiting_navigation_admission",
        "awaiting_navigation_execution",
        "awaiting_read",
        "budget_exhausted",
        "clarification_required",
        "judgment_failed",
        "ready_for_semantic_evaluation",
        "semantically_handed_off",
        "stale_or_invalid",
        "unresolved_handoff",
    }
)
_SOURCE_CLASSES = frozenset(
    {
        "current_primary_or_official",
        "official",
        "official_current_rules",
        "official_docs",
        "official_government",
        "primary",
        "primary_source_documents",
        "supporting_fact",
        "unknown",
    }
)
_SOURCE_TIERS = frozenset(
    {
        "canonical",
        "official",
        "primary",
        "secondary",
        "unknown",
    }
)
_CURRENTNESS_POSTURES = frozenset(
    {
        "current",
        "currentness_not_verified_by_diagnostic",
        "not_evaluated",
        "stale",
        "unknown",
    }
)
_READABLE_STATUSES = frozenset(
    {
        "not_evaluated",
        "not_read",
        "read_not_authorized_by_validation_gate",
        "readable",
        "unknown",
        "unreadable",
    }
)
_ADMISSION_EXCEPTION_CLASSES = frozenset(
    {
        "ComponentCoverageReductionError",
        "MulticomponentComponentAdmissionError",
        "RunKernelTransitionError",
        "SemanticObservationAdmissionError",
    }
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    return []


def _token(value: Any, allowed: frozenset[str]) -> str:
    token = str(value or "").strip().casefold()
    return token if token in allowed else "not_observable"


def _bounded_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return min(value, 100)


def _opaque_digest(value: Any) -> str | None:
    token = str(value or "").strip().casefold()
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
        return None
    return token


def _component_slots(
    searchos_state: Mapping[str, Any], component_id: str
) -> list[dict[str, Any]]:
    return [
        _mapping(slot)
        for slot in _mapping(searchos_state.get("slots_by_id")).values()
        if _mapping(_mapping(slot).get("slot_ref")).get("component_id")
        == component_id
    ]


def _component_handoffs(
    semantic_handoffs: Sequence[Mapping[str, Any]], component_id: str
) -> list[dict[str, Any]]:
    return [
        _mapping(handoff)
        for handoff in semantic_handoffs
        if _mapping(_mapping(handoff).get("slot_ref")).get("component_id")
        == component_id
    ]


def _current_posture(slots: Sequence[Mapping[str, Any]]) -> str:
    postures = {
        _token(_mapping(slot).get("posture"), _SEARCHOS_POSTURES)
        for slot in slots
    }
    postures.discard("not_observable")
    return next(iter(postures)) if len(postures) == 1 else "not_observable"


def _latest_admission(
    admissions: Sequence[Mapping[str, Any]], component_id: str
) -> dict[str, Any]:
    matches = [
        _mapping(item)
        for item in admissions
        if _mapping(item).get("component_id") == component_id
    ]
    return matches[-1] if matches else {}


def _matching_analyst_artifact(
    role_artifacts: Mapping[str, Any],
    component_id: str,
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    expected_ref = _mapping(admission.get("component_analyst_case_ref"))
    candidates = [
        _mapping(value)
        for key, value in role_artifacts.items()
        if str(key).startswith("multicomponent_role:component_analyst")
        and str(key).endswith(f":{component_id}")
    ]
    if expected_ref:
        exact = [
            artifact
            for artifact in candidates
            if artifact.get("artifact_digest")
            == expected_ref.get("artifact_digest")
            and artifact.get("input_packet_digest")
            == expected_ref.get("input_packet_digest")
        ]
        if exact:
            return exact[-1]
    return candidates[-1] if candidates else {}


def _content_reference_count(evidence: Mapping[str, Any]) -> int | None:
    for key in ("content_references", "content_refs"):
        if key in evidence:
            return _bounded_count(len(_sequence(evidence.get(key))))
    return None


def _source_fact(
    evidence: Mapping[str, Any],
    *,
    keys: Sequence[str],
    allowed: frozenset[str],
) -> str:
    custody = _mapping(evidence.get("candidate_custody_ref"))
    for owner in (evidence, custody):
        for key in keys:
            if key in owner:
                projected = _token(owner.get(key), allowed)
                if projected != "not_observable":
                    return projected
    return "not_observable"


def _project_component(
    *,
    component: Mapping[str, Any],
    ordinal: int,
    searchos_state: Mapping[str, Any],
    semantic_handoffs: Sequence[Mapping[str, Any]],
    analyst_packets: Mapping[str, Any],
    role_artifacts: Mapping[str, Any],
    admissions: Sequence[Mapping[str, Any]],
    mismatch: Mapping[str, Any],
    admission_exception_class: str | None,
) -> dict[str, Any]:
    component_id = str(component.get("component_id") or "")
    slots = _component_slots(searchos_state, component_id)
    handoffs = _component_handoffs(semantic_handoffs, component_id)
    packet = _mapping(analyst_packets.get(component_id))
    evidence = _mapping(packet.get("component_evidence"))
    admission = _latest_admission(admissions, component_id)
    analyst = _matching_analyst_artifact(
        role_artifacts, component_id, admission
    )
    semantic_output = _mapping(analyst.get("semantic_output"))
    mismatch_for_component = bool(
        mismatch
        and mismatch.get("accepted_component_id") == component_id
    )
    admission_exception_present = bool(
        mismatch_for_component
        and admission_exception_class in _ADMISSION_EXCEPTION_CLASSES
    )
    custody_ids = {
        str(_mapping(item).get("read_custody_material_id") or "")
        for slot in slots
        for item in _sequence(_mapping(slot).get("custody_refs"))
        if _mapping(item).get("read_custody_material_id")
    }
    handoff_materials = [
        _mapping(item)
        for handoff in handoffs
        for item in _sequence(handoff.get("read_custody_material_refs"))
    ]
    source_obligation_present = any(
        bool(
            _mapping(_mapping(slot).get("slot_ref")).get(
                "source_obligation_id"
            )
            or _mapping(slot).get("source_obligation_ref")
        )
        for slot in slots
    )
    return {
        "component_id": component_id,
        "component_digest": _opaque_digest(component.get("component_digest")),
        "component_ordinal": ordinal,
        "searchos_final_posture": _current_posture(slots),
        "semantic_handoff_present": bool(
            handoffs
            or any(_sequence(slot.get("semantic_handoff_refs")) for slot in slots)
        ),
        "read_custody_count": len(custody_ids),
        "semantic_handoff_material_count": (
            len(handoff_materials) if handoffs else None
        ),
        "evidence_ref_present": bool(
            evidence.get("evidence_ref_id")
            or any(
                item.get("read_custody_material_id") for item in handoff_materials
            )
        ),
        "source_obligation_ref_present": source_obligation_present,
        "source_class": _source_fact(
            evidence, keys=("source_class",), allowed=_SOURCE_CLASSES
        ),
        "source_tier": _source_fact(
            evidence, keys=("source_tier",), allowed=_SOURCE_TIERS
        ),
        "currentness_posture": _source_fact(
            evidence,
            keys=("currentness", "currentness_signal"),
            allowed=_CURRENTNESS_POSTURES,
        ),
        "readable_status": _source_fact(
            evidence,
            keys=(
                "readability_posture",
                "readable_status",
                "readability_status",
            ),
            allowed=_READABLE_STATUSES,
        ),
        "analyst_input_packet_present": bool(packet),
        "analyst_input_component_evidence_present": bool(evidence),
        "analyst_input_evidence_ref_present": bool(
            evidence.get("evidence_ref_id")
        ),
        "analyst_input_content_reference_count": _content_reference_count(
            evidence
        ),
        "analyst_executed": bool(analyst),
        "case_posture": _token(
            semantic_output.get("case_posture"),
            frozenset(COMPONENT_ANALYST_CASE_POSTURES),
        ),
        "claim_present": bool(semantic_output.get("claim_text")),
        "caveat_count": min(len(_sequence(semantic_output.get("caveats"))), 100),
        "blocker_count": min(len(_sequence(semantic_output.get("blockers"))), 100),
        "unresolved_need_present": bool(semantic_output.get("unresolved_need")),
        "missing_evidentiary_premise_present": bool(
            semantic_output.get("missing_evidentiary_premise")
        ),
        "calculation_need_present": bool(
            semantic_output.get("calculation_need")
        ),
        "component_admission_ref_present": bool(admission),
        "admission_status": _token(
            admission.get("admission_status"), _ADMISSION_STATUSES
        ),
        "semantic_observation_ref_present": bool(
            _mapping(admission.get("semantic_observation_ref"))
        ),
        "component_coverage_ref_present": bool(
            _mapping(admission.get("component_coverage_ref"))
        ),
        "admission_exception_present": admission_exception_present,
        "admission_exception_class": (
            admission_exception_class
            if admission_exception_present
            else None
        ),
        "input_binding_mismatch_projection_present": mismatch_for_component,
    }


def build_component_semantic_frontier_v1(
    *,
    accepted_contract: Mapping[str, Any] | None,
    searchos_state: Mapping[str, Any] | None,
    scheduler_context: Mapping[str, Any] | None,
    role_artifacts: Mapping[str, Any] | None,
    component_admission_projection: Mapping[str, Any] | None,
    semantic_handoffs: Sequence[Mapping[str, Any]] = (),
    input_binding_mismatch_projection: Mapping[str, Any] | None = None,
    admission_exception_class: str | None = None,
) -> dict[str, Any]:
    """Build the pure bounded projection from already-existing authorities."""

    accepted = _mapping(accepted_contract)
    components = [
        _mapping(item)
        for item in _sequence(accepted.get("accepted_answer_component_refs"))
        if _mapping(item).get("component_id")
    ]
    scheduler = _mapping(scheduler_context)
    analyst_packets = _mapping(
        scheduler.get("component_analyst_input_packets")
    )
    admission_projection = _mapping(component_admission_projection)
    admissions = [
        _mapping(item)
        for item in _sequence(
            admission_projection.get("component_admission_refs")
        )
    ]
    mismatch = project_component_analyst_input_binding_mismatch_v1(
        input_binding_mismatch_projection
    )
    projected_components = [
        _project_component(
            component=component,
            ordinal=ordinal,
            searchos_state=_mapping(searchos_state),
            semantic_handoffs=semantic_handoffs,
            analyst_packets=analyst_packets,
            role_artifacts=_mapping(role_artifacts),
            admissions=admissions,
            mismatch=mismatch,
            admission_exception_class=admission_exception_class,
        )
        for ordinal, component in enumerate(components, start=1)
    ]
    return {
        "schema_version": COMPONENT_SEMANTIC_FRONTIER_SCHEMA_VERSION,
        "available": bool(projected_components),
        "component_count": len(projected_components),
        "components": projected_components,
    }


def build_component_semantic_frontier_from_run_kernel(
    run_kernel: Any,
    *,
    searchos_result: Any | None = None,
    exc: BaseException | None = None,
) -> dict[str, Any]:
    """Read the installed canonical owners without retaining another copy."""

    state = getattr(run_kernel, "state", None)
    projections = getattr(state, "projections", {})
    accepted = (
        getattr(state, "current_answer_contract", None)
        or getattr(state, "initial_answer_contract", None)
        or {}
    )
    mismatch = (
        component_analyst_input_binding_mismatch_from_exception(exc)
        if exc is not None
        else {}
    )
    exception_class = type(exc).__name__ if exc is not None else None
    semantic_handoffs = getattr(searchos_result, "semantic_handoffs", ()) or ()
    return build_component_semantic_frontier_v1(
        accepted_contract=accepted,
        searchos_state=getattr(state, "searchos_state", None),
        scheduler_context=getattr(
            state, "multicomponent_scheduler_context", None
        ),
        role_artifacts=projections,
        component_admission_projection=_mapping(projections).get(
            "multicomponent_component_admission"
        ),
        semantic_handoffs=semantic_handoffs,
        input_binding_mismatch_projection=mismatch,
        admission_exception_class=exception_class,
    )


def safely_build_component_semantic_frontier_from_run_kernel(
    run_kernel: Any,
    *,
    searchos_result: Any | None = None,
    exc: BaseException | None = None,
) -> dict[str, Any]:
    """Fail observationally closed without changing product execution."""

    try:
        return build_component_semantic_frontier_from_run_kernel(
            run_kernel,
            searchos_result=searchos_result,
            exc=exc,
        )
    except Exception:
        return {}


def attach_component_semantic_frontier_to_exception(
    exc: BaseException, projection: Mapping[str, Any]
) -> None:
    """Attach one completed safe projection to the existing exception object."""

    try:
        setattr(
            exc,
            COMPONENT_SEMANTIC_FRONTIER_EXCEPTION_ATTRIBUTE,
            sanitize_component_semantic_frontier_v1(projection),
        )
    except (AttributeError, TypeError):
        return


def component_semantic_frontier_from_exception(
    exc: BaseException,
) -> dict[str, Any]:
    """Resolve the first valid bounded projection from an exception chain."""

    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        projected = sanitize_component_semantic_frontier_v1(
            getattr(
                current,
                COMPONENT_SEMANTIC_FRONTIER_EXCEPTION_ATTRIBUTE,
                None,
            )
        )
        if projected.get("available") is True:
            return projected
        current = current.__cause__ or current.__context__
    return {}


def sanitize_component_semantic_frontier_v1(value: Any) -> dict[str, Any]:
    """Allowlist an already-built frontier for trace/packet publication."""

    raw = _mapping(value)
    if raw.get("schema_version") != COMPONENT_SEMANTIC_FRONTIER_SCHEMA_VERSION:
        return {}
    raw_components = _sequence(raw.get("components"))[:5]
    components: list[dict[str, Any]] = []
    for ordinal, item in enumerate(raw_components, start=1):
        component = _mapping(item)
        component_id = str(component.get("component_id") or "").strip()[:160]
        if not component_id:
            continue
        projected = {
            "component_id": component_id,
            "component_digest": _opaque_digest(component.get("component_digest")),
            "component_ordinal": _bounded_count(
                component.get("component_ordinal")
            )
            or ordinal,
            "searchos_final_posture": _token(
                component.get("searchos_final_posture"), _SEARCHOS_POSTURES
            ),
            "semantic_handoff_present": component.get(
                "semantic_handoff_present"
            )
            is True,
            "read_custody_count": _bounded_count(
                component.get("read_custody_count")
            ),
            "semantic_handoff_material_count": _bounded_count(
                component.get("semantic_handoff_material_count")
            ),
            "evidence_ref_present": component.get("evidence_ref_present")
            is True,
            "source_obligation_ref_present": component.get(
                "source_obligation_ref_present"
            )
            is True,
            "source_class": _token(
                component.get("source_class"), _SOURCE_CLASSES
            ),
            "source_tier": _token(
                component.get("source_tier"), _SOURCE_TIERS
            ),
            "currentness_posture": _token(
                component.get("currentness_posture"), _CURRENTNESS_POSTURES
            ),
            "readable_status": _token(
                component.get("readable_status"), _READABLE_STATUSES
            ),
            "analyst_input_packet_present": component.get(
                "analyst_input_packet_present"
            )
            is True,
            "analyst_input_component_evidence_present": component.get(
                "analyst_input_component_evidence_present"
            )
            is True,
            "analyst_input_evidence_ref_present": component.get(
                "analyst_input_evidence_ref_present"
            )
            is True,
            "analyst_input_content_reference_count": _bounded_count(
                component.get("analyst_input_content_reference_count")
            ),
            "analyst_executed": component.get("analyst_executed") is True,
            "case_posture": _token(
                component.get("case_posture"),
                frozenset(COMPONENT_ANALYST_CASE_POSTURES),
            ),
            "claim_present": component.get("claim_present") is True,
            "caveat_count": _bounded_count(component.get("caveat_count")),
            "blocker_count": _bounded_count(component.get("blocker_count")),
            "unresolved_need_present": component.get(
                "unresolved_need_present"
            )
            is True,
            "missing_evidentiary_premise_present": component.get(
                "missing_evidentiary_premise_present"
            )
            is True,
            "calculation_need_present": component.get(
                "calculation_need_present"
            )
            is True,
            "component_admission_ref_present": component.get(
                "component_admission_ref_present"
            )
            is True,
            "admission_status": _token(
                component.get("admission_status"), _ADMISSION_STATUSES
            ),
            "semantic_observation_ref_present": component.get(
                "semantic_observation_ref_present"
            )
            is True,
            "component_coverage_ref_present": component.get(
                "component_coverage_ref_present"
            )
            is True,
            "admission_exception_present": component.get(
                "admission_exception_present"
            )
            is True,
            "admission_exception_class": (
                component.get("admission_exception_class")
                if component.get("admission_exception_class")
                in _ADMISSION_EXCEPTION_CLASSES
                else None
            ),
            "input_binding_mismatch_projection_present": component.get(
                "input_binding_mismatch_projection_present"
            )
            is True,
        }
        components.append(projected)
    return {
        "schema_version": COMPONENT_SEMANTIC_FRONTIER_SCHEMA_VERSION,
        "available": bool(components),
        "component_count": len(components),
        "components": deepcopy(components),
    }


__all__ = [
    "COMPONENT_SEMANTIC_FRONTIER_EXCEPTION_ATTRIBUTE",
    "COMPONENT_SEMANTIC_FRONTIER_SCHEMA_VERSION",
    "COMPONENT_SEMANTIC_FRONTIER_TRACE_KEY",
    "attach_component_semantic_frontier_to_exception",
    "build_component_semantic_frontier_from_run_kernel",
    "build_component_semantic_frontier_v1",
    "component_semantic_frontier_from_exception",
    "safely_build_component_semantic_frontier_from_run_kernel",
    "sanitize_component_semantic_frontier_v1",
]
