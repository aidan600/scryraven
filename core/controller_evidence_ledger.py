"""Controller-owned evidence ledger contract for authority custody.

The ledger consumes already-sanitized controller/projection facts and produces
pure state. It does not retrieve, route providers, rank/filter, classify, fit,
prompt, cite, synthesize, persist, or alter runtime answer behavior.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse, urlunparse

CONTROLLER_EVIDENCE_LEDGER_SCHEMA_VERSION = (
    "controller_evidence_ledger_ag74a_v1"
)
CONTROLLER_EVIDENCE_LEDGER_TRACE_SCHEMA_VERSION = (
    "controller_evidence_ledger_runtime_custody_ag74b_v1"
)
CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY = "controller_evidence_ledger"
CONTROLLER_EVIDENCE_LEDGER_COMPATIBILITY_STATUS = (
    "compatibility_only_subordinate_to_run_kernel_evidence_ledger_ag91j"
)

AUTHORITY_REQUIREMENT_DECLARED = "AuthorityRequirementDeclared"
RECOVERY_ACTION_AUTHORIZED = "RecoveryActionAuthorized"
PROVIDER_RESULT_OBSERVED = "ProviderResultObserved"
CANDIDATE_REPRESENTED = "CandidateRepresented"
CANDIDATE_READABLE = "CandidateReadable"
CANDIDATE_CLASSIFIED = "CandidateClassified"
CANDIDATE_FIT_EVALUATED = "CandidateFitEvaluated"
CANDIDATE_DISPOSITIONED = "CandidateDispositioned"
AUTHORITY_EVIDENCE_SELECTED = "AuthorityEvidenceSelected"
FINAL_EVIDENCE_OBSERVED = "FinalEvidenceObserved"
FINAL_CITATION_OBSERVED = "FinalCitationObserved"
ANSWER_CONTRACT_UPDATED = "AnswerContractUpdated"
CONTEXT_EXPOSURE_REQUIRED = "ContextExposureRequired"
CONTEXT_EXPOSURE_OBSERVED = "ContextExposureObserved"
LEGACY_CUSTODY_GAP_OBSERVED = "LegacyCustodyGapObserved"

LEDGER_EVENT_TYPES = (
    AUTHORITY_REQUIREMENT_DECLARED,
    RECOVERY_ACTION_AUTHORIZED,
    PROVIDER_RESULT_OBSERVED,
    CANDIDATE_REPRESENTED,
    CANDIDATE_READABLE,
    CANDIDATE_CLASSIFIED,
    CANDIDATE_FIT_EVALUATED,
    CANDIDATE_DISPOSITIONED,
    AUTHORITY_EVIDENCE_SELECTED,
    FINAL_EVIDENCE_OBSERVED,
    FINAL_CITATION_OBSERVED,
    ANSWER_CONTRACT_UPDATED,
    CONTEXT_EXPOSURE_REQUIRED,
    CONTEXT_EXPOSURE_OBSERVED,
    LEGACY_CUSTODY_GAP_OBSERVED,
)

UNKNOWN = "unknown"
NOT_OBSERVABLE = "not_observable"

_MAX_LIST_ITEMS = 40
_MAX_TEXT_CHARS = 240
_OFFICIAL_OR_CANONICAL_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    }
)
_OFFICIAL_OR_CANONICAL_TIERS = frozenset({"official", "primary", "canonical"})
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "cache",
    "credential",
    "db",
    "env",
    "full_trace",
    "key",
    "log",
    "output_packet",
    "password",
    "prompt",
    "provider_payload",
    "raw_",
    "secret",
    "snippet",
    "text",
    "token",
)
_PROTECTED_MARKERS = (
    "raw prompt",
    "raw_provider",
    "provider_payload",
    "secret",
    "token",
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(
        r"(?i)\b(api[_ -]?key|secret|token|password)\b\s*[:=]\s*[^,\s;]+"
    ),
)


def build_controller_evidence_ledger(
    *,
    runtime_trace: Mapping[str, Any] | None = None,
    provider_result_bridge: Mapping[str, Any] | None = None,
    passport_projection: Mapping[str, Any] | None = None,
    visibility_export: Mapping[str, Any] | None = None,
    final_top_evidence: Iterable[Mapping[str, Any]] | None = None,
    final_citations: Iterable[Mapping[str, Any] | str] | None = None,
    answer_contract_handoff: Mapping[str, Any] | None = None,
    surface_visibility: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Controller-owned evidence ledger state from sanitized facts."""

    trace = _safe_mapping(runtime_trace)
    bridge = _safe_mapping(provider_result_bridge) or _bridge_from_trace(trace)
    passports = _safe_mapping(passport_projection) or _passport_from_trace(trace)
    export = _safe_mapping(visibility_export)
    if not export:
        export = _visibility_export_from_trace(trace)
    handoff = _safe_mapping(answer_contract_handoff) or _handoff_from_trace(trace)
    surfaces = _safe_mapping(surface_visibility)

    events: list[dict[str, Any]] = []
    _append_requirement_event(events, trace=trace, passports=passports, export=export)
    _append_recovery_action_event(events, trace=trace)
    provider_events = _append_provider_events(events, bridge=bridge, trace=trace)
    candidate_events = _append_candidate_events(events, passports=passports, bridge=bridge)
    selected_events = _append_selected_evidence_events(
        events,
        passports=passports,
        export=export,
    )
    final_evidence_events = _append_final_evidence_events(
        events,
        final_top_evidence=final_top_evidence,
        export=export,
    )
    final_citation_events = _append_final_citation_events(
        events,
        final_citations=final_citations,
        export=export,
    )
    _append_answer_contract_event(events, handoff=handoff)
    _append_exposure_events(
        events,
        passports=passports,
        handoff=handoff,
        surfaces=surfaces,
    )
    gap_events = _append_legacy_gap_events(
        events,
        bridge=bridge,
        passports=passports,
        export=export,
        provider_event_count=len(provider_events),
        represented_candidate_count=len(candidate_events),
        selected_evidence_count=len(selected_events),
        final_evidence_count=len(final_evidence_events),
        final_citation_count=len(final_citation_events),
    )

    state = {
        "schema_version": CONTROLLER_EVIDENCE_LEDGER_SCHEMA_VERSION,
        "owner": "ControllerEvidenceLedger",
        "run_kernel_compatibility_status": (
            CONTROLLER_EVIDENCE_LEDGER_COMPATIBILITY_STATUS
        ),
        "controller_owned": True,
        "diagnostic_only": False,
        "sanitized": True,
        "behavior_changed": False,
        "runtime_behavior_changed": False,
        "event_types": list(LEDGER_EVENT_TYPES),
        "events": events,
        "requirements": _events_by_type(events, AUTHORITY_REQUIREMENT_DECLARED),
        "recovery_actions": _events_by_type(events, RECOVERY_ACTION_AUTHORIZED),
        "provider_results": _events_by_type(events, PROVIDER_RESULT_OBSERVED),
        "represented_candidates": _represented_candidate_states(events),
        "selected_evidence": _events_by_type(events, AUTHORITY_EVIDENCE_SELECTED),
        "final_evidence": _events_by_type(events, FINAL_EVIDENCE_OBSERVED),
        "final_citations": _events_by_type(events, FINAL_CITATION_OBSERVED),
        "final_evidence_citation_custody": _final_evidence_citation_custody(
            events
        ),
        "answer_contract": _first_event(events, ANSWER_CONTRACT_UPDATED),
        "context_exposure": {
            "required": _events_by_type(events, CONTEXT_EXPOSURE_REQUIRED),
            "observed": _events_by_type(events, CONTEXT_EXPOSURE_OBSERVED),
        },
        "legacy_custody_gaps": gap_events,
        "integrity": _integrity(events),
        "demolition_classification": _demolition_classification(),
        "decision_authority": {
            "controller_decides": True,
            "legacy_orchestrator_decides": False,
            "old_paths_can_still_make_decisions": (
                "only outside this ledger contract until follow-up demolition phases"
            ),
            "why_not_wrapper": (
                "The ledger owns the custody disposition vocabulary and records "
                "legacy bypasses as Controller-visible gaps instead of treating "
                "projection success as custody success."
            ),
        },
    }
    return _safe_value(state)


def build_controller_evidence_ledger_trace(
    runtime_trace: Mapping[str, Any] | None,
    *,
    final_top_evidence: Iterable[Mapping[str, Any]] | None = None,
    final_citations: Iterable[Mapping[str, Any] | str] | None = None,
    surface_visibility: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the runtime trace wrapper for Controller-owned custody state."""

    ledger = build_controller_evidence_ledger(
        runtime_trace=runtime_trace,
        final_top_evidence=final_top_evidence,
        final_citations=final_citations,
        surface_visibility=surface_visibility,
    )
    return {
        "schema_version": CONTROLLER_EVIDENCE_LEDGER_TRACE_SCHEMA_VERSION,
        "trace_key": CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY,
        "run_kernel_compatibility_status": (
            CONTROLLER_EVIDENCE_LEDGER_COMPATIBILITY_STATUS
        ),
        "trace_mode": "controller_owned_authority_custody",
        "diagnostic_only": False,
        "sanitized": True,
        "behavior_changed": False,
        "runtime_behavior_changed": False,
        "ControllerEvidenceLedger": ledger,
    }


def assert_controller_evidence_ledger_integrity(ledger: Mapping[str, Any]) -> None:
    """Raise when ledger-covered represented authority candidates lack disposition."""

    integrity = _safe_mapping(ledger).get("integrity")
    if not isinstance(integrity, Mapping):
        raise AssertionError("ControllerEvidenceLedger integrity missing")
    missing = integrity.get("represented_candidates_missing_disposition")
    if isinstance(missing, list) and missing:
        joined = ", ".join(str(item) for item in missing)
        raise AssertionError(
            "ControllerEvidenceLedger represented candidates missing disposition: "
            + joined
        )


def _append_requirement_event(
    events: list[dict[str, Any]],
    *,
    trace: Mapping[str, Any],
    passports: Mapping[str, Any],
    export: Mapping[str, Any],
) -> None:
    authority = _mapping(trace.get("authority_lifecycle"))
    action = _mapping(authority.get("recovery_action"))
    required_classes = _clean_list(
        action.get("required_source_classes")
        or trace.get("active_source_class_recovery_missing_classes")
        or trace.get("expected_source_classes_raw")
    )
    requirement_id = (
        _clean_text(authority.get("requirement_id"))
        or _clean_text(passports.get("requirement_id"))
        or (required_classes[0] if required_classes else "")
        or "authority_requirement"
    )
    required_authority = (
        _clean_text(authority.get("required_authority"))
        or _clean_text(passports.get("required_source_class"))
        or (required_classes[0] if required_classes else "")
        or UNKNOWN
    )
    _add_event(
        events,
        AUTHORITY_REQUIREMENT_DECLARED,
        {
            "requirement_id": requirement_id,
            "required_authority": required_authority,
            "required_source_classes": required_classes,
            "source_obligation_required": _source_obligation_required(
                required_classes=required_classes,
                export=export,
            ),
            "old_path_classification": "subordinated to Controller-owned ledger state",
        },
    )


def _append_recovery_action_event(
    events: list[dict[str, Any]],
    *,
    trace: Mapping[str, Any],
) -> None:
    authority = _mapping(trace.get("authority_lifecycle"))
    action = _mapping(authority.get("recovery_action"))
    action_type = _clean_text(action.get("action_type"))
    approved = action.get("approved")
    if not action_type and trace.get("active_source_class_recovery_used") is True:
        action_type = "recover_missing_source_class"
        approved = True
    if not action_type:
        return
    _add_event(
        events,
        RECOVERY_ACTION_AUTHORIZED,
        {
            "action_type": action_type,
            "approved": bool(approved),
            "required_source_classes": _clean_list(
                action.get("required_source_classes")
                or trace.get("active_source_class_recovery_missing_classes")
            ),
            "provider_role": _clean_text(
                action.get("provider_role")
                or trace.get("active_source_class_recovery_provider_role")
            )
            or UNKNOWN,
            "executor": "source-class recovery executor",
            "old_path_classification": "mechanical executor/helper only",
        },
    )


def _append_provider_events(
    events: list[dict[str, Any]],
    *,
    bridge: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    records = _record_list(bridge.get("bridge_records"))
    if not records:
        records = _provider_result_records_from_trace(trace)
    for record in records:
        payload = {
            "provider_result_id": _provider_result_id(record),
            "provider_name": _clean_text(
                record.get("provider_name") or record.get("provider")
            )
            or UNKNOWN,
            "provider_role": _clean_text(record.get("provider_role")) or UNKNOWN,
            "source_url": _clean_text(record.get("source_url") or record.get("url")),
            "normalized_domain": _clean_text(record.get("normalized_domain"))
            or _normalized_domain(record.get("source_url") or record.get("url")),
            "source_tier": _clean_token(record.get("source_tier")) or UNKNOWN,
            "source_class": _clean_token(record.get("source_class")) or UNKNOWN,
            "bridge_disposition": _clean_text(record.get("bridge_disposition"))
            or UNKNOWN,
            "old_path_classification": "replaced by Controller-owned ledger state",
        }
        event = _add_event(events, PROVIDER_RESULT_OBSERVED, payload)
        out.append(event)
    return out


def _append_candidate_events(
    events: list[dict[str, Any]],
    *,
    passports: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    passport_records = _record_list(passports.get("passports"))
    for passport in passport_records:
        candidate_id = _candidate_id(passport)
        represented = _add_event(
            events,
            CANDIDATE_REPRESENTED,
            {
                "candidate_id": candidate_id,
                "source_url": _clean_text(passport.get("source_url")),
                "source_tier": _clean_token(passport.get("source_tier")) or UNKNOWN,
                "source_class": _clean_token(passport.get("source_class")) or UNKNOWN,
                "passport_visible": True,
                "represented_by": "authority_candidate_passport",
                "old_path_classification": (
                    "subordinated to Controller-owned ledger state"
                ),
            },
        )
        out.append(represented)
        _add_event(
            events,
            CANDIDATE_READABLE,
            {
                "candidate_id": candidate_id,
                "readability_status": _clean_text(passport.get("readability_status"))
                or UNKNOWN,
                "readable_text_available": passport.get("readable_text_available"),
            },
        )
        _add_event(
            events,
            CANDIDATE_CLASSIFIED,
            {
                "candidate_id": candidate_id,
                "source_tier": _clean_token(passport.get("source_tier")) or UNKNOWN,
                "source_class": _clean_token(passport.get("source_class")) or UNKNOWN,
                "official_domain_signal": passport.get("official_domain_signal"),
                "currentness_signal": _clean_text(passport.get("currentness_signal"))
                or UNKNOWN,
            },
        )
        _add_event(
            events,
            CANDIDATE_FIT_EVALUATED,
            {
                "candidate_id": candidate_id,
                "fit_state": _clean_text(passport.get("fit_state")) or UNKNOWN,
                "satisfies_authority": passport.get("satisfies_authority"),
                "first_missing_stage": _clean_text(passport.get("first_missing_stage")),
            },
        )
        _add_event(
            events,
            CANDIDATE_DISPOSITIONED,
            {
                "candidate_id": candidate_id,
                "disposition": _clean_text(passport.get("final_disposition"))
                or UNKNOWN,
                "reason": _clean_text(
                    passport.get("rejection_reason")
                    or passport.get("mismatch_reason")
                    or passport.get("first_missing_stage")
                ),
                "controller_visible": passport.get("controller_visible"),
                "old_path_classification": (
                    "replaced by Controller-owned ledger state"
                ),
            },
        )

    for record in _record_list(bridge.get("bridge_records")):
        if record.get("represented_candidate_visible") is not True:
            continue
        candidate_id = _clean_text(
            record.get("represented_candidate_id")
            or record.get("passport_candidate_id")
        )
        if not candidate_id or _candidate_event_exists(events, candidate_id):
            continue
        represented = _add_event(
            events,
            CANDIDATE_REPRESENTED,
            {
                "candidate_id": candidate_id,
                "source_url": _clean_text(record.get("source_url")),
                "source_tier": _clean_token(record.get("source_tier")) or UNKNOWN,
                "source_class": _clean_token(record.get("source_class")) or UNKNOWN,
                "passport_visible": record.get("passport_visible"),
                "represented_by": "provider_result_bridge",
                "old_path_classification": (
                    "subordinated to Controller-owned ledger state"
                ),
            },
        )
        out.append(represented)
        disposition = (
            "represented_candidate_without_passport"
            if record.get("passport_visible") is not True
            else _clean_text(record.get("bridge_disposition")) or UNKNOWN
        )
        _add_event(
            events,
            CANDIDATE_DISPOSITIONED,
            {
                "candidate_id": candidate_id,
                "disposition": disposition,
                "reason": _clean_text(record.get("non_representation_reason"))
                or _clean_text(record.get("first_missing_stage")),
                "controller_visible": True,
                "old_path_classification": (
                    "replaced by Controller-owned ledger state"
                ),
            },
        )
    return out


def _append_selected_evidence_events(
    events: list[dict[str, Any]],
    *,
    passports: Mapping[str, Any],
    export: Mapping[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for passport in _record_list(passports.get("passports")):
        selected = passport.get("final_disposition") == "promoted_final_authority_evidence"
        if not selected and passport.get("fit_state") != "matched_selected":
            continue
        event = _add_event(
            events,
            AUTHORITY_EVIDENCE_SELECTED,
            {
                "candidate_id": _candidate_id(passport),
                "source_url": _clean_text(passport.get("source_url")),
                "source_class": _clean_token(passport.get("source_class")) or UNKNOWN,
                "selection_basis": _clean_text(passport.get("fit_state")) or UNKNOWN,
                "old_path_classification": (
                    "subordinated to Controller-owned ledger state"
                ),
            },
        )
        out.append(event)
    selected_count = _optional_int(export.get("final_selected_authority_evidence_count"))
    if selected_count > len(out):
        for index in range(len(out) + 1, selected_count + 1):
            event = _add_event(
                events,
                AUTHORITY_EVIDENCE_SELECTED,
                {
                    "evidence_id": f"legacy-final-selected-authority-evidence:{index}",
                    "selection_basis": "visibility_export_aggregate",
                    "old_path_classification": "still legacy authority and should be deleted/subordinated next",
                },
            )
            out.append(event)
    return out


def _append_final_evidence_events(
    events: list[dict[str, Any]],
    *,
    final_top_evidence: Iterable[Mapping[str, Any]] | None,
    export: Mapping[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for source in final_top_evidence or ():
        if not isinstance(source, Mapping):
            continue
        if not _official_or_canonical(source):
            continue
        event = _add_event(
            events,
            FINAL_EVIDENCE_OBSERVED,
            {
                "evidence_id": _source_identity(source),
                "source_url": _clean_text(source.get("url")),
                "source_tier": _clean_token(source.get("source_tier")) or UNKNOWN,
                "source_class": _clean_token(source.get("source_class")) or UNKNOWN,
                "observed_in": "final_top_evidence",
                "old_path_classification": "observer/export only",
            },
        )
        out.append(event)
    aggregate_count = _optional_int(export.get("final_evidence_official_or_canonical_count"))
    if aggregate_count > len(out):
        for index in range(len(out) + 1, aggregate_count + 1):
            event = _add_event(
                events,
                FINAL_EVIDENCE_OBSERVED,
                {
                    "evidence_id": f"legacy-final-evidence:{index}",
                    "observed_in": "visibility_export_aggregate",
                    "old_path_classification": (
                        "still legacy authority and should be deleted/subordinated next"
                    ),
                },
            )
            out.append(event)
    return out


def _append_final_citation_events(
    events: list[dict[str, Any]],
    *,
    final_citations: Iterable[Mapping[str, Any] | str] | None,
    export: Mapping[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for citation in final_citations or ():
        record = _citation_record(citation)
        if not record:
            continue
        event = _add_event(
            events,
            FINAL_CITATION_OBSERVED,
            {
                **record,
                "observed_in": "final_citations",
                "old_path_classification": "observer/export only",
            },
        )
        out.append(event)
    aggregate_count = _optional_int(export.get("final_citation_official_or_canonical_count"))
    if aggregate_count > len(out):
        for index in range(len(out) + 1, aggregate_count + 1):
            event = _add_event(
                events,
                FINAL_CITATION_OBSERVED,
                {
                    "citation_id": f"legacy-final-citation:{index}",
                    "observed_in": "visibility_export_aggregate",
                    "old_path_classification": (
                        "still legacy authority and should be deleted/subordinated next"
                    ),
                },
            )
            out.append(event)
    return out


def _append_answer_contract_event(
    events: list[dict[str, Any]],
    *,
    handoff: Mapping[str, Any],
) -> None:
    if not handoff:
        return
    _add_event(
        events,
        ANSWER_CONTRACT_UPDATED,
        {
            "schema_version": _clean_text(handoff.get("schema_version")) or UNKNOWN,
            "source_obligation_status": _clean_text(
                handoff.get("source_obligation_status")
            )
            or UNKNOWN,
            "fulfilled_items": _clean_list(handoff.get("fulfilled_items")),
            "partial_items": _clean_list(handoff.get("partial_items")),
            "unfulfilled_items": _clean_list(handoff.get("unfulfilled_items")),
            "unfulfilled_source_classes": _clean_list(
                handoff.get("unfulfilled_source_classes")
            ),
            "partial_source_classes": _clean_list(handoff.get("partial_source_classes")),
            "old_path_classification": "subordinated to Controller-owned ledger state",
        },
    )


def _append_exposure_events(
    events: list[dict[str, Any]],
    *,
    passports: Mapping[str, Any],
    handoff: Mapping[str, Any],
    surfaces: Mapping[str, Any],
) -> None:
    for selected in _events_by_type(events, AUTHORITY_EVIDENCE_SELECTED):
        candidate_id = _clean_text(selected.get("candidate_id"))
        _add_event(
            events,
            CONTEXT_EXPOSURE_REQUIRED,
            {
                "candidate_id": candidate_id,
                "requirement": "selected authority evidence must be visible to context/citation surfaces",
                "old_path_classification": "replaced by Controller-owned ledger state",
            },
        )
    if handoff:
        for reference in _record_list(handoff.get("evidence_used")):
            _add_event(
                events,
                CONTEXT_EXPOSURE_OBSERVED,
                {
                    "reference": _clean_text(reference.get("reference")) or UNKNOWN,
                    "source_class": _clean_text(reference.get("source_class"))
                    or UNKNOWN,
                    "observed_in": "answer_contract_handoff",
                },
            )
    for passport in _record_list(passports.get("passports")):
        candidate_id = _candidate_id(passport)
        for surface in (
            "context_packet_visible",
            "answer_contract_visible",
            "analyst_visible",
            "author_visible",
            "citation_eligible",
            "cited_in_final_answer",
        ):
            value = passport.get(surface)
            if value in {True, False}:
                _add_event(
                    events,
                    CONTEXT_EXPOSURE_OBSERVED,
                    {
                        "candidate_id": candidate_id,
                        "surface": surface,
                        "observed": value,
                        "observed_in": "authority_candidate_passport",
                    },
                )
    for key, values in surfaces.items():
        if not isinstance(values, (list, tuple, set)):
            continue
        _add_event(
            events,
            CONTEXT_EXPOSURE_OBSERVED,
            {
                "surface": _clean_text(key),
                "observed_identity_count": len(values),
                "observed_in": "surface_visibility",
            },
        )


def _append_legacy_gap_events(
    events: list[dict[str, Any]],
    *,
    bridge: Mapping[str, Any],
    passports: Mapping[str, Any],
    export: Mapping[str, Any],
    provider_event_count: int,
    represented_candidate_count: int,
    selected_evidence_count: int,
    final_evidence_count: int,
    final_citation_count: int,
) -> list[dict[str, Any]]:
    gap_events: list[dict[str, Any]] = []
    passport_count = _optional_int(passports.get("passport_count"))
    if passport_count == 0 and passports.get("passports") == []:
        passport_count = 0
    final_evidence_positive = final_evidence_count > 0 or _optional_int(
        export.get("final_evidence_official_or_canonical_count")
    ) > 0
    final_citation_positive = final_citation_count > 0 or _optional_int(
        export.get("final_citation_official_or_canonical_count")
    ) > 0
    final_selected_count = _optional_int(
        export.get("final_selected_authority_evidence_count")
    )
    if (final_evidence_positive or final_citation_positive) and (
        passport_count == 0 or represented_candidate_count == 0
    ):
        gap_events.append(
            _add_event(
                events,
                LEGACY_CUSTODY_GAP_OBSERVED,
                {
                    "gap_type": "final_evidence_or_citation_without_candidate_passport_custody",
                    "final_evidence_visible": final_evidence_positive,
                    "final_citation_visible": final_citation_positive,
                    "authority_candidate_passport_count": passport_count,
                    "represented_candidate_count": represented_candidate_count,
                    "old_path_classification": (
                        "still legacy authority and should be deleted/subordinated next"
                    ),
                    "demolition_target": (
                        "final evidence/citation survival path must become subordinate "
                        "to ControllerEvidenceLedger candidate/passport custody"
                    ),
                },
            )
        )
    if (
        final_evidence_positive or final_citation_positive
    ) and final_selected_count == 0 and selected_evidence_count == 0:
        gap_events.append(
            _add_event(
                events,
                LEGACY_CUSTODY_GAP_OBSERVED,
                {
                    "gap_type": "final_evidence_or_citation_without_final_selected_authority_evidence",
                    "final_selected_authority_evidence_count": final_selected_count,
                    "old_path_classification": (
                        "still legacy authority and should be deleted/subordinated next"
                    ),
                    "demolition_target": (
                        "legacy final_top_evidence/citation selection must no longer "
                        "bypass authority evidence selection custody"
                    ),
                },
            )
        )
    selected_events = _events_by_type(events, AUTHORITY_EVIDENCE_SELECTED)
    citation_events = _events_by_type(events, FINAL_CITATION_OBSERVED)
    missing_selected_citations = [
        event
        for event in selected_events
        if not _selected_authority_event_cited(event, citation_events)
    ]
    if (
        missing_selected_citations
        and (final_evidence_positive or _selected_authority_citation_eligible(export))
    ):
        gap_events.append(
            _add_event(
                events,
                LEGACY_CUSTODY_GAP_OBSERVED,
                {
                    "gap_type": (
                        "final_evidence_or_citation_selected_authority_evidence_not_cited"
                    ),
                    "selected_authority_evidence_count": len(selected_events),
                    "selected_authority_evidence_not_cited_count": len(
                        missing_selected_citations
                    ),
                    "final_citation_observed_count": len(citation_events),
                    "old_path_classification": (
                        "final citation surface must cite selected authority evidence"
                    ),
                    "demolition_target": (
                        "weak or aggregate final citations cannot satisfy selected "
                        "authority evidence citation custody"
                    ),
                },
            )
        )
    aggregate_status = _clean_text(bridge.get("aggregate_reconciliation_status"))
    if aggregate_status and aggregate_status not in {"reconciled", UNKNOWN}:
        gap_events.append(
            _add_event(
                events,
                LEGACY_CUSTODY_GAP_OBSERVED,
                {
                    "gap_type": "provider_result_bridge_aggregate_not_reconciled",
                    "provider_result_count": provider_event_count,
                    "bridge_aggregate_reconciliation_status": aggregate_status,
                    "old_path_classification": (
                        "subordinated to Controller-owned ledger state"
                    ),
                },
            )
        )
    if provider_event_count > 0 and selected_evidence_count == 0 and final_evidence_positive:
        gap_events.append(
            _add_event(
                events,
                LEGACY_CUSTODY_GAP_OBSERVED,
                {
                    "gap_type": "provider_result_to_final_evidence_custody_parallel_path",
                    "provider_result_count": provider_event_count,
                    "selected_evidence_count": selected_evidence_count,
                    "old_path_classification": (
                        "still legacy authority and should be deleted/subordinated next"
                    ),
                },
            )
        )
    return gap_events


def _final_evidence_citation_custody(
    events: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    event_list = [dict(event) for event in events]
    final_evidence = _events_by_type(event_list, FINAL_EVIDENCE_OBSERVED)
    final_citations = _events_by_type(event_list, FINAL_CITATION_OBSERVED)
    selected = _events_by_type(event_list, AUTHORITY_EVIDENCE_SELECTED)
    represented = [
        event
        for event in _events_by_type(event_list, CANDIDATE_REPRESENTED)
        if _is_authority_candidate(event)
    ]
    dispositions = _events_by_type(event_list, CANDIDATE_DISPOSITIONED)
    gaps = _events_by_type(event_list, LEGACY_CUSTODY_GAP_OBSERVED)
    final_gap_types = [
        gap_type
        for gap_type in (_clean_text(event.get("gap_type")) for event in gaps)
        if gap_type.startswith("final_evidence_or_citation_")
        or gap_type == "provider_result_to_final_evidence_custody_parallel_path"
    ]
    has_final_surface = bool(final_evidence or final_citations)
    integrity = _integrity(event_list)
    if not has_final_surface:
        status = "not_observed"
    elif integrity["represented_candidates_missing_disposition"]:
        status = "missing_controller_disposition"
    elif final_gap_types:
        status = "legacy_gap_observed"
    elif represented and dispositions and selected:
        status = "controller_complete"
    else:
        status = "legacy_gap_observed"
    return {
        "owner": "ControllerEvidenceLedger",
        "status": status,
        "custody_complete": status == "controller_complete",
        "final_evidence_observed_count": len(final_evidence),
        "final_citation_observed_count": len(final_citations),
        "represented_authority_candidate_count": len(represented),
        "candidate_disposition_count": len(dispositions),
        "selected_authority_evidence_count": len(selected),
        "legacy_gap_types": final_gap_types,
        "legacy_success_counts_are_authoritative": False,
        "old_path_classification": (
            "final evidence/citation counts are subordinate to ControllerEvidenceLedger custody"
        ),
    }


def _integrity(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    represented = _events_by_type(events, CANDIDATE_REPRESENTED)
    dispositions = {
        _clean_text(event.get("candidate_id"))
        for event in _events_by_type(events, CANDIDATE_DISPOSITIONED)
        if _clean_text(event.get("candidate_id"))
        and _clean_text(event.get("disposition")) not in {"", UNKNOWN}
    }
    missing = [
        str(event.get("candidate_id"))
        for event in represented
        if _is_authority_candidate(event)
        and _clean_text(event.get("candidate_id")) not in dispositions
    ]
    return {
        "represented_authority_candidate_count": len(
            [event for event in represented if _is_authority_candidate(event)]
        ),
        "represented_candidates_missing_disposition": missing,
        "status": "complete" if not missing else "missing_controller_disposition",
    }


def _demolition_classification() -> dict[str, Any]:
    return {
        "legacy_decision_path_targeted": (
            "pipeline_orchestrator.py final evidence/citation custody and AG-73 "
            "passive projection reconciliation"
        ),
        "new_controller_owned_owner": "ControllerEvidenceLedger",
        "executor_mechanical_helper": (
            "source-class recovery executor and recovered evidence visibility helper"
        ),
        "observer_projection_export": (
            "authority_candidate_passport, provider_result_represented_visibility, "
            "official_canonical_recovery_visibility_export"
        ),
        "old_code_deleted": [],
        "old_code_bypassed_or_subordinate": [
            "provider-result bridge facts become ledger ProviderResultObserved/CandidateRepresented events",
            "passport final_disposition becomes ledger CandidateDispositioned state",
            "final evidence/citation visibility becomes ledger observed state with explicit legacy gaps",
            "AnswerContract fulfillment becomes ledger AnswerContractUpdated state",
        ],
        "remaining_old_code_to_delete_next": [
            "pipeline_orchestrator.py local final_top_evidence selection/citation custody decisions",
            "parallel aggregate visibility success paths that do not require candidate/passport disposition",
        ],
        "net_complexity_impact": (
            "Adds a small pure contract so follow-up phases can delete or "
            "subordinate orchestrator-local evidence custody with fixtures in hand."
        ),
        "why_no_code_deleted_still_reduces_risk": (
            "Deletion is now keyed to ledger events and gap records rather than "
            "implicit agreement between passive projections."
        ),
    }


def _represented_candidate_states(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    dispositions = {
        _clean_text(event.get("candidate_id")): event
        for event in _events_by_type(events, CANDIDATE_DISPOSITIONED)
    }
    states: list[dict[str, Any]] = []
    for event in _events_by_type(events, CANDIDATE_REPRESENTED):
        candidate_id = _clean_text(event.get("candidate_id"))
        disposition = dispositions.get(candidate_id)
        states.append(
            {
                **dict(event),
                "ledger_disposition": (
                    None if disposition is None else dict(disposition)
                ),
            }
        )
    return states


def _add_event(
    events: list[dict[str, Any]],
    event_type: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    event = {
        "event_index": len(events),
        "event_type": event_type,
        **dict(payload),
    }
    events.append(event)
    return event


def _first_event(events: Iterable[Mapping[str, Any]], event_type: str) -> dict[str, Any] | None:
    for event in events:
        if event.get("event_type") == event_type:
            return dict(event)
    return None


def _events_by_type(
    events: Iterable[Mapping[str, Any]],
    event_type: str,
) -> list[dict[str, Any]]:
    return [dict(event) for event in events if event.get("event_type") == event_type]


def _bridge_from_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    for key in (
        "provider_result_represented_candidate_bridge",
        "provider_result_bridge",
    ):
        payload = trace.get(key)
        if isinstance(payload, Mapping):
            nested = payload.get("ProviderResultRepresentedCandidateBridge")
            if isinstance(nested, Mapping):
                return _safe_mapping(nested)
            return _safe_mapping(payload)
    return {}


def _passport_from_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    for key in ("authority_candidate_passport_projection",):
        payload = trace.get(key)
        if isinstance(payload, Mapping):
            nested = payload.get("AuthorityCandidatePassportProjection")
            if isinstance(nested, Mapping):
                return _safe_mapping(nested)
            return _safe_mapping(payload)
    return {}


def _visibility_export_from_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    payload = trace.get("official_canonical_recovery_visibility_export")
    if isinstance(payload, Mapping):
        nested = payload.get("OfficialCanonicalRecoveryVisibility")
        if isinstance(nested, Mapping):
            return _safe_mapping(nested)
        return _safe_mapping(payload)
    return {}


def _handoff_from_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    payload = trace.get("answer_contract_fulfillment_handoff")
    return _safe_mapping(payload) if isinstance(payload, Mapping) else {}


def _provider_result_records_from_trace(trace: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    diagnostics = trace.get("provider_diagnostics")
    if not isinstance(diagnostics, (list, tuple)):
        return records
    for attempt in diagnostics:
        if not isinstance(attempt, Mapping):
            continue
        for item in _record_list(attempt.get("provider_result_summaries")):
            records.append(
                {
                    "provider_name": attempt.get("provider"),
                    "provider_role": attempt.get("provider_role"),
                    "query_preview": attempt.get("query_preview"),
                    **item,
                }
            )
    return records


def _source_obligation_required(
    *,
    required_classes: list[str],
    export: Mapping[str, Any],
) -> bool | str:
    if required_classes:
        return True
    if _optional_int(export.get("final_evidence_official_or_canonical_count")) > 0:
        return True
    if _optional_int(export.get("final_citation_official_or_canonical_count")) > 0:
        return True
    return UNKNOWN


def _candidate_event_exists(events: Iterable[Mapping[str, Any]], candidate_id: str) -> bool:
    return any(
        event.get("event_type") == CANDIDATE_REPRESENTED
        and _clean_text(event.get("candidate_id")) == candidate_id
        for event in events
    )


def _candidate_id(record: Mapping[str, Any]) -> str:
    for key in ("candidate_id", "source_id", "evidence_id"):
        value = _clean_text(record.get(key))
        if value:
            return value
    source_url = _clean_text(record.get("source_url") or record.get("url"))
    if source_url:
        return f"candidate:{hashlib.sha1(source_url.encode('utf-8')).hexdigest()[:12]}"
    return "candidate:unidentified"


def _provider_result_id(record: Mapping[str, Any]) -> str:
    explicit = _clean_text(record.get("provider_result_id"))
    if explicit:
        return explicit
    basis = "|".join(
        (
            _clean_text(record.get("provider_name") or record.get("provider")),
            _clean_text(record.get("source_url") or record.get("url")),
            _clean_text(record.get("query_preview") or record.get("query")),
        )
    )
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
    return f"provider-result-{digest}"


def _source_identity(source: Mapping[str, Any]) -> str:
    for key in ("source_id", "evidence_id", "url", "title"):
        value = _clean_text(source.get(key))
        if value:
            return value
    return "final-evidence:unidentified"


def _citation_record(citation: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(citation, str):
        text = _clean_text(citation)
        if not text:
            return {}
        return {
            "citation_id": text,
            "source_id": text if "://" not in text else "",
            "source_url": text if "://" in text else "",
        }
    if not isinstance(citation, Mapping):
        return {}
    citation_id = _clean_text(
        citation.get("citation_id")
        or citation.get("source_id")
        or citation.get("url")
        or citation.get("title")
    )
    if not citation_id:
        return {}
    return {
        "citation_id": citation_id,
        "source_id": _clean_text(citation.get("source_id")),
        "source_url": _clean_text(citation.get("url") or citation.get("source_url")),
        "source_class": _clean_token(citation.get("source_class")) or UNKNOWN,
    }


def _selected_authority_event_cited(
    selected: Mapping[str, Any],
    citations: Iterable[Mapping[str, Any]],
) -> bool:
    selected_identities = _event_identities(
        selected,
        id_keys=("candidate_id", "source_id", "evidence_id"),
        url_keys=("source_url", "url"),
    )
    if not selected_identities:
        return False
    for citation in citations:
        citation_identities = _event_identities(
            citation,
            id_keys=("citation_id", "source_id", "evidence_id"),
            url_keys=("source_url", "url"),
        )
        if selected_identities & citation_identities:
            return True
    return False


def _selected_authority_citation_eligible(export: Mapping[str, Any]) -> bool:
    return _clean_token(export.get("citation_eligibility_state")) == "eligible"


def _event_identities(
    event: Mapping[str, Any],
    *,
    id_keys: Iterable[str],
    url_keys: Iterable[str],
) -> set[str]:
    identities: set[str] = set()
    for key in id_keys:
        value = _clean_text(event.get(key))
        if value:
            identities.add(f"id:{value.casefold()}")
    for key in url_keys:
        value = _normalize_url(event.get(key))
        if value:
            identities.add(f"url:{value}")
    return identities


def _official_or_canonical(source: Mapping[str, Any]) -> bool:
    return (
        _clean_token(source.get("source_class")) in _OFFICIAL_OR_CANONICAL_CLASSES
        or _clean_token(source.get("source_tier")) in _OFFICIAL_OR_CANONICAL_TIERS
        or _normalized_domain(source.get("url")).endswith(".gov")
    )


def _is_authority_candidate(event: Mapping[str, Any]) -> bool:
    return (
        _clean_token(event.get("source_class")) in _OFFICIAL_OR_CANONICAL_CLASSES
        or _clean_token(event.get("source_tier")) in _OFFICIAL_OR_CANONICAL_TIERS
        or _normalized_domain(event.get("source_url")).endswith(".gov")
    )


def _record_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(_safe_mapping(item))
        if len(out) >= _MAX_LIST_ITEMS:
            break
    return out


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        clean = _clean_text(item)
        key = clean.casefold()
        if clean and key not in seen:
            out.append(clean)
            seen.add(key)
        if len(out) >= _MAX_LIST_ITEMS:
            break
    return out


def _mapping(value: Any) -> dict[str, Any]:
    return _safe_mapping(value) if isinstance(value, Mapping) else {}


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key or "")
        if _is_sensitive_key(key_text):
            continue
        safe = _safe_value(item)
        if safe is not None:
            out[key_text] = safe
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:_MAX_LIST_ITEMS]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:_MAX_LIST_ITEMS]]
    return _clean_text(value)


def _is_sensitive_key(key: Any) -> bool:
    text = str(key or "").casefold()
    return any(marker in text for marker in _SENSITIVE_KEY_MARKERS)


def _clean_text(value: Any, *, limit: int = _MAX_TEXT_CHARS) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).strip().split())
    if not text:
        return ""
    lowered = text.casefold()
    if any(marker in lowered for marker in _PROTECTED_MARKERS):
        return "[redacted protected material]"
    for pattern in _SECRET_VALUE_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text[:limit]


def _clean_token(value: Any) -> str:
    return _clean_text(value, limit=80).casefold().replace("-", "_").replace(" ", "_")


def _optional_int(value: Any) -> int:
    if value is None or isinstance(value, bool) or value in {UNKNOWN, NOT_OBSERVABLE}:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _normalized_domain(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def _normalize_url(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return text.casefold().rstrip("/")
    return urlunparse(("https", host, (parsed.path or "").rstrip("/"), "", parsed.query, "")).casefold()


__all__ = [
    "ANSWER_CONTRACT_UPDATED",
    "AUTHORITY_EVIDENCE_SELECTED",
    "AUTHORITY_REQUIREMENT_DECLARED",
    "CANDIDATE_CLASSIFIED",
    "CANDIDATE_DISPOSITIONED",
    "CANDIDATE_FIT_EVALUATED",
    "CANDIDATE_READABLE",
    "CANDIDATE_REPRESENTED",
    "CONTEXT_EXPOSURE_OBSERVED",
    "CONTEXT_EXPOSURE_REQUIRED",
    "CONTROLLER_EVIDENCE_LEDGER_SCHEMA_VERSION",
    "CONTROLLER_EVIDENCE_LEDGER_COMPATIBILITY_STATUS",
    "CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY",
    "CONTROLLER_EVIDENCE_LEDGER_TRACE_SCHEMA_VERSION",
    "FINAL_CITATION_OBSERVED",
    "FINAL_EVIDENCE_OBSERVED",
    "LEDGER_EVENT_TYPES",
    "LEGACY_CUSTODY_GAP_OBSERVED",
    "PROVIDER_RESULT_OBSERVED",
    "RECOVERY_ACTION_AUTHORIZED",
    "assert_controller_evidence_ledger_integrity",
    "build_controller_evidence_ledger",
    "build_controller_evidence_ledger_trace",
]
