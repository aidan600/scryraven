"""Proposal-only Analyst Workbench scaffold for current-source records.

The workbench sits between candidate intake and D-prime review. It classifies
candidate roles, records analyst finding proposals, and prepares a compact
D-prime dossier without admitting evidence, satisfying source obligations,
creating citation eligibility, or claiming product correctness.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any, Mapping, Sequence

ANALYST_WORKBENCH_PHASE = (
    "CURRENT-SOURCE-RECORD-ANALYST-WORKBENCH-FULL-SLICE-SCAFFOLD-01"
)
CANDIDATE_EVIDENCE_TRIAGE_SCHEMA_VERSION = "candidate_evidence_triage_packet_v1"
EVIDENCE_ROLE_PROPOSAL_SCHEMA_VERSION = "evidence_role_proposal_v1"
ANALYST_WORKBENCH_SCHEMA_VERSION = "analyst_workbench_packet_v1"
ANALYST_FINDING_PROPOSAL_SCHEMA_VERSION = "analyst_finding_proposal_v1"
ANALYSIS_GAP_SEARCH_PROPOSAL_SCHEMA_VERSION = "analysis_gap_search_proposal_v1"
WORKBENCH_DPRIME_DOSSIER_SCHEMA_VERSION = "workbench_dprime_dossier_v1"
WORKBENCH_REDUCTION_PROJECTION_SCHEMA_VERSION = "workbench_reduction_projection_v1"

RUNTIME_CONSUMER = (
    "proplex.mvp_single_relation_live_dogfood_run."
    "build_generic_single_relation_live_dogfood_run_output"
)
DPRIME_CONSUMER = (
    "proplex.live_semantic_coverage_status."
    "build_live_semantic_coverage_status"
)

ROLE_STRICT_ANSWER_SUPPORT = "strict_answer_support_candidate"
ROLE_ANSWER_ADJACENT_CONTEXT = "answer_adjacent_context"
ROLE_QUALIFIER_EXCEPTION_CONTEXT = "qualifier_exception_context"
ROLE_OVERCLAIM_RISK = "overclaim_risk"
ROLE_CONFLICT_CANDIDATE = "conflict_candidate"
ROLE_SOURCE_OF_RECORD_LOOKING = "official_source_of_record_looking_candidate"
ROLE_UNREADABLE_HIGH_VALUE_OFFICIAL = "unreadable_high_value_official_artifact"
ROLE_DISCOVERY_ONLY = "discovery_only_candidate"
ROLE_REMEDIATION_NEEDED = "remediation_needed_candidate"

WORKBENCH_REDUCTION_ADMITTED = "admitted"
WORKBENCH_REDUCTION_CHALLENGED = "challenged"
WORKBENCH_REDUCTION_BLOCKED = "blocked"
WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED = "followup_not_licensed"
WORKBENCH_REDUCTION_NOT_REQUIRED = "not_required"

_RAW_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_source_content_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}
_NON_AUTHORITY_TRUE_FLAGS = {
    "proposal_only": True,
    "not_evidence_admission": True,
    "not_source_obligation_satisfaction": True,
    "not_citation_eligibility": True,
    "not_product_correctness": True,
    "not_answer_prose": True,
    "not_source_authority_finality": True,
}
_NON_AUTHORITY_FALSE_FLAGS = {
    "evidence_admitted": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "source_authority_finalized": False,
    "final_answer_packet_created": False,
    "author_answer_created": False,
    "product_correctness_claimed": False,
}
_CONTEXT_MARKERS = frozenset(
    {
        "discount",
        "discounted",
        "electronic",
        "eligible",
        "eligibility",
        "exception",
        "exemption",
        "extension",
        "grace",
        "late",
        "low income",
        "low-income",
        "online",
        "reduced",
        "reduction",
        "special",
        "temporary",
        "waiver",
    }
)
_STRICT_MARKERS = frozenset(
    {
        "base",
        "official",
        "paper",
        "regular",
        "required",
        "schedule",
        "standard",
    }
)
_CONTEXTUAL_STRICT_SUPPORT_MARKERS = frozenset(
    {
        "base",
        "paper",
        "regular",
        "required",
        "schedule",
        "standard",
    }
)
_CONFLICT_MARKERS = frozenset(
    {
        "but",
        "contradict",
        "different",
        "however",
        "instead",
        "not ",
        "rather",
    }
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def build_current_source_record_analyst_workbench(
    *,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any] | None,
    candidate_diagnostics: Sequence[Mapping[str, Any]],
    answer_bearing_candidate_window_diagnostics: Sequence[Mapping[str, Any]],
    provider_results: Sequence[Mapping[str, Any]],
    fetch_read_content_packet: Mapping[str, Any],
    entrypoint_kind: str,
) -> dict[str, Any]:
    """Build the sanitized proposal-only workbench bundle."""

    plan = _safe_mapping(relation_plan)
    acquisition = _safe_mapping(acquisition_plan)
    diagnostics = [_safe_mapping(item) for item in candidate_diagnostics]
    window_diagnostics = [
        _safe_mapping(item) for item in answer_bearing_candidate_window_diagnostics
    ]
    provider_by_url = _provider_results_by_url(provider_results)
    window_by_candidate_id = {
        _clean_text(item.get("candidate_id"), limit=320): item
        for item in window_diagnostics
        if _clean_text(item.get("candidate_id"), limit=320)
    }
    candidates = [
        _candidate_workbench_record(
            diagnostic,
            window_by_candidate_id=window_by_candidate_id,
            provider_result=provider_by_url.get(_clean_text(diagnostic.get("url"), limit=700) or ""),
            plan=plan,
            acquisition=acquisition,
        )
        for diagnostic in diagnostics
    ]
    role_proposals: list[dict[str, Any]] = []
    for candidate in candidates:
        role_proposals.extend(_role_proposals_for_candidate(candidate))
    triage_packet = _candidate_evidence_triage_packet(
        plan=plan,
        acquisition=acquisition,
        candidates=candidates,
        role_proposals=role_proposals,
        entrypoint_kind=entrypoint_kind,
    )
    analyst_findings = _analyst_finding_proposals(
        triage_packet=triage_packet,
        fetch_read_content_packet=fetch_read_content_packet,
    )
    gap_proposal = _analysis_gap_search_proposal(
        plan=plan,
        acquisition=acquisition,
        triage_packet=triage_packet,
    )
    workbench_packet = _analyst_workbench_packet(
        triage_packet=triage_packet,
        analyst_findings=analyst_findings,
        gap_proposal=gap_proposal,
        entrypoint_kind=entrypoint_kind,
    )
    dossier = _workbench_dprime_dossier(
        triage_packet=triage_packet,
        workbench_packet=workbench_packet,
        gap_proposal=gap_proposal,
    )
    projection = _workbench_reduction_projection(
        triage_packet=triage_packet,
        workbench_packet=workbench_packet,
        gap_proposal=gap_proposal,
        dossier=dossier,
    )
    bundle = {
        "candidate_evidence_triage_packet": triage_packet,
        "analyst_workbench_packet": workbench_packet,
        "analysis_gap_search_proposal": gap_proposal,
        "workbench_dprime_dossier": dossier,
        "workbench_reduction_projection": projection,
        "candidate_evidence_triage_ref": _triage_ref(triage_packet),
        "analyst_workbench_ref": _workbench_ref(workbench_packet),
        "analysis_gap_search_proposal_ref": _gap_ref(gap_proposal),
        "workbench_dprime_dossier_ref": workbench_dprime_dossier_ref(dossier),
        "workbench_reduction_projection_ref": _projection_ref(projection),
    }
    return validate_current_source_record_analyst_workbench_bundle(bundle)


def empty_current_source_record_analyst_workbench_bundle() -> dict[str, Any]:
    """Return an empty, explicit not-created bundle for pre-intake blockers."""

    empty_ref = {"status": "not_created", "phase": ANALYST_WORKBENCH_PHASE}
    projection = {
        "schema_version": WORKBENCH_REDUCTION_PROJECTION_SCHEMA_VERSION,
        "phase": ANALYST_WORKBENCH_PHASE,
        "owner": "AnalystWorkbenchRuntime",
        "status": WORKBENCH_REDUCTION_NOT_REQUIRED,
        "run_kernel_reduced": False,
        "run_kernel_reduction_pending": True,
        "proposed_for_runkernel_reduction": True,
        "ordinary_product_path_consumed": False,
        "blocked_before_answer": False,
        **_non_authority_posture(),
    }
    return {
        "candidate_evidence_triage_packet": {},
        "analyst_workbench_packet": {},
        "analysis_gap_search_proposal": {},
        "workbench_dprime_dossier": {},
        "workbench_reduction_projection": projection,
        "candidate_evidence_triage_ref": dict(empty_ref),
        "analyst_workbench_ref": dict(empty_ref),
        "analysis_gap_search_proposal_ref": dict(empty_ref),
        "workbench_dprime_dossier_ref": dict(empty_ref),
        "workbench_reduction_projection_ref": _projection_ref(projection),
    }


def workbench_dprime_dossier_ref(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Compact ref suitable for D-prime status and packet surfaces."""

    dossier = _safe_mapping(value)
    if not dossier:
        return {"status": "not_provided", "phase": ANALYST_WORKBENCH_PHASE}
    return _without_empty(
        {
            "schema_version": dossier.get("schema_version"),
            "phase": dossier.get("phase"),
            "dossier_id": dossier.get("dossier_id"),
            "dossier_digest": dossier.get("dossier_digest"),
            "runtime_consumer": dossier.get("runtime_consumer"),
            "dprime_consumer": dossier.get("dprime_consumer"),
            "strict_answer_support_candidate_count": _bounded_int(
                dossier.get("strict_answer_support_candidate_count")
            ),
            "contextual_candidate_count": _bounded_int(
                dossier.get("contextual_candidate_count")
            ),
            "overclaim_risk_candidate_count": _bounded_int(
                dossier.get("overclaim_risk_candidate_count")
            ),
            "gap_proposal_status": dossier.get("gap_proposal_status"),
            "raw_private_retention": False,
            "product_correctness_claimed": False,
        }
    )


def validate_current_source_record_analyst_workbench_bundle(
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _safe_mapping(bundle)
    projection = _safe_mapping(safe.get("workbench_reduction_projection"))
    if projection.get("schema_version") != WORKBENCH_REDUCTION_PROJECTION_SCHEMA_VERSION:
        raise AnalystWorkbenchError("WorkbenchReductionProjection schema mismatch")
    if projection.get("owner") != "AnalystWorkbenchRuntime":
        raise AnalystWorkbenchError("WorkbenchReductionProjection owner mismatch")
    if projection.get("run_kernel_reduced") is not False:
        raise AnalystWorkbenchError("WorkbenchReductionProjection must not claim RunKernel reduction")
    if projection.get("run_kernel_reduction_pending") is not True:
        raise AnalystWorkbenchError("WorkbenchReductionProjection must mark RunKernel reduction pending")
    if projection.get("proposed_for_runkernel_reduction") is not True:
        raise AnalystWorkbenchError("WorkbenchReductionProjection must be proposed for RunKernel reduction")
    for key, expected in _NON_AUTHORITY_FALSE_FLAGS.items():
        if projection.get(key) is not expected:
            raise AnalystWorkbenchError(f"projection authority flag invalid: {key}")
    _reject_raw_private_or_authority_claims(safe)
    return _json_safe(safe)


class AnalystWorkbenchError(ValueError):
    """Raised when proposal-only workbench data violates its boundary."""


def _candidate_workbench_record(
    diagnostic: Mapping[str, Any],
    *,
    window_by_candidate_id: Mapping[str, Mapping[str, Any]],
    provider_result: Mapping[str, Any] | None,
    plan: Mapping[str, Any],
    acquisition: Mapping[str, Any],
) -> dict[str, Any]:
    provider = _safe_mapping(provider_result)
    candidate_id = _clean_text(diagnostic.get("candidate_id"), limit=320)
    window = window_by_candidate_id.get(candidate_id or "") or diagnostic
    text_features = _text_features(
        " ".join(
            item
            for item in (
                _clean_text(provider.get("provider_extracted_text"), limit=2_000),
            )
            if item
        )
    )
    features = _safe_mapping(diagnostic.get("candidate_selection_features"))
    official = bool(
        features.get("source_of_record_domain_signal") is True
        or features.get("official_domain_signal") is True
        or features.get("public_agency_domain_signal") is True
        or diagnostic.get("official_or_source_record_looking_http_candidate") is True
        or diagnostic.get("source_survival_candidate_signal")
        in {"source_of_record_looking", "official_looking"}
    )
    selected = bool(
        diagnostic.get("answer_bearing_candidate_window_selected") is True
        or window.get("answer_bearing_candidate_window_selected") is True
        or window.get("candidate_window_selected") is True
    )
    official_artifact = bool(
        official
        and (
            diagnostic.get("official_pdf_or_table_artifact_candidate") is True
            or window.get("official_pdf_or_table_artifact_candidate") is True
        )
    )
    read_support_status = (
        _clean_text(diagnostic.get("official_artifact_read_support_status"), limit=120)
        or _clean_text(window.get("official_artifact_read_support_status"), limit=120)
    )
    value_count = max(
        _bounded_int(window.get("matched_value_token_kind_count")),
        _bounded_int(diagnostic.get("matched_value_token_kind_count")),
        _value_token_count_from_text(provider.get("provider_extracted_text")),
    )
    anchor_count = max(
        _bounded_int(window.get("matched_anchor_count")),
        _bounded_int(diagnostic.get("matched_anchor_count")),
    )
    readable = bool(
        selected
        or diagnostic.get("readable_text_obtained") is True
        or diagnostic.get("provider_extracted_text_obtained") is True
        or _clean_text(window.get("selected_window_digest"), limit=128)
    )
    query_tokens = _query_tokens(plan, acquisition)
    candidate_tokens = set(text_features["tokens"])
    query_overlap = bool(query_tokens & candidate_tokens)
    contextual_markers = sorted(_CONTEXT_MARKERS & candidate_tokens)
    strict_markers = sorted(_STRICT_MARKERS & candidate_tokens)
    conflict_markers = sorted(
        marker for marker in _CONFLICT_MARKERS if marker in text_features["lowered"]
    )
    return _without_empty(
        {
            "candidate_ref": _candidate_ref(diagnostic, window),
            "candidate_id": candidate_id,
            "title": _clean_text(diagnostic.get("title"), limit=220),
            "domain": _clean_text(diagnostic.get("domain"), limit=260),
            "url": _clean_text(diagnostic.get("url"), limit=700),
            "provider_rank": _bounded_int(diagnostic.get("provider_rank")),
            "fetch_read_priority_rank": _bounded_int(
                diagnostic.get("fetch_read_priority_rank")
            ),
            "official_or_source_record_looking": official,
            "readable_or_bounded_window_available": readable,
            "selected_for_dprime_review": selected,
            "selected_window_digest": _clean_text(
                window.get("selected_window_digest")
                or diagnostic.get("selected_window_digest"),
                limit=128,
            ),
            "selected_window_char_count": _bounded_int(
                window.get("selected_window_char_count")
                or diagnostic.get("selected_window_char_count")
            ),
            "matched_anchor_count": anchor_count,
            "matched_value_token_kind_count": value_count,
            "official_pdf_or_table_artifact_candidate": official_artifact,
            "official_artifact_type": (
                _clean_text(diagnostic.get("official_artifact_type"), limit=80)
                or _clean_text(window.get("official_artifact_type"), limit=80)
            ),
            "official_artifact_read_support_status": read_support_status,
            "official_artifact_read_support_source": (
                _clean_text(
                    diagnostic.get("official_artifact_read_support_source"),
                    limit=120,
                )
                or _clean_text(
                    window.get("official_artifact_read_support_source"),
                    limit=120,
                )
            ),
            "official_artifact_read_support_raw_content_retained": False
            if official_artifact
            else None,
            "provider_snippet_used_as_extracted_source_text": False,
            "query_token_overlap": query_overlap,
            "context_marker_terms": contextual_markers,
            "strict_marker_terms": strict_markers,
            "conflict_marker_terms": conflict_markers,
            "provider_extracted_source_text_digest": _clean_text(
                provider.get("provider_extracted_source_text_digest")
                or provider.get("provider_extracted_text_digest")
                or diagnostic.get("provider_extracted_source_text_digest")
                or diagnostic.get("provider_extracted_text_digest"),
                limit=128,
            ),
            "provider_extracted_source_text_char_count": _bounded_int(
                provider.get("provider_extracted_text_char_count")
                or diagnostic.get("provider_extracted_source_text_char_count")
            ),
            **_non_authority_posture(),
        }
    )


def _role_proposals_for_candidate(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    roles: list[tuple[str, list[str]]] = []
    official = candidate.get("official_or_source_record_looking") is True
    readable = candidate.get("readable_or_bounded_window_available") is True
    selected = candidate.get("selected_for_dprime_review") is True
    value_count = _bounded_int(candidate.get("matched_value_token_kind_count"))
    anchor_count = _bounded_int(candidate.get("matched_anchor_count"))
    contextual = bool(_safe_sequence(candidate.get("context_marker_terms")))
    conflict = bool(_safe_sequence(candidate.get("conflict_marker_terms")))
    query_overlap = candidate.get("query_token_overlap") is True
    strict_terms = set(_safe_sequence(candidate.get("strict_marker_terms")))
    strict_basis = bool(anchor_count > 0 or query_overlap or strict_terms)
    contextual_strict_basis = bool(strict_terms & _CONTEXTUAL_STRICT_SUPPORT_MARKERS)
    strictish = bool(
        readable
        and value_count > 0
        and (contextual_strict_basis if contextual else strict_basis)
    )
    if official:
        roles.append(
            (
                ROLE_SOURCE_OF_RECORD_LOOKING,
                ["safe diagnostics indicate official or source-record-looking identity"],
            )
        )
    if strictish and not conflict:
        roles.append(
            (
                ROLE_STRICT_ANSWER_SUPPORT,
                ["bounded/readable candidate has strict value signal"],
            )
        )
    if contextual:
        roles.append(
            (
                ROLE_ANSWER_ADJACENT_CONTEXT,
                ["candidate contains contextual, exception, discount, or mode-specific markers"],
            )
        )
        roles.append(
            (
                ROLE_QUALIFIER_EXCEPTION_CONTEXT,
                ["candidate may describe a qualifier rather than the strict requested fact"],
            )
        )
    if contextual and value_count > 0:
        roles.append(
            (
                ROLE_OVERCLAIM_RISK,
                ["value-bearing contextual candidate could overstate strict answer support"],
            )
        )
    if conflict:
        roles.append(
            (
                ROLE_CONFLICT_CANDIDATE,
                ["candidate carries contrast or contradiction markers"],
            )
        )
    if official and not readable:
        roles.append(
            (
                ROLE_UNREADABLE_HIGH_VALUE_OFFICIAL,
                ["official-looking candidate did not provide readable bounded content"],
            )
        )
    if not roles:
        roles.append((ROLE_DISCOVERY_ONLY, ["candidate retained for discovery only"]))
    if not any(role == ROLE_STRICT_ANSWER_SUPPORT for role, _ in roles):
        roles.append(
            (
                ROLE_REMEDIATION_NEEDED,
                ["strict source-of-record support is not established by workbench triage"],
            )
        )
    return [
        _role_proposal(candidate, role=role, reasons=reasons, selected=selected)
        for role, reasons in roles
    ]


def _role_proposal(
    candidate: Mapping[str, Any],
    *,
    role: str,
    reasons: Sequence[str],
    selected: bool,
) -> dict[str, Any]:
    candidate_ref = _safe_mapping(candidate.get("candidate_ref"))
    role_id = (
        "evidence-role-proposal:"
        f"{candidate_ref.get('candidate_id') or 'candidate'}:{role}"
    )
    payload = {
        "schema_version": EVIDENCE_ROLE_PROPOSAL_SCHEMA_VERSION,
        "phase": ANALYST_WORKBENCH_PHASE,
        "proposal_id": role_id,
        "role": role,
        "candidate_ref": candidate_ref,
        "selected_for_dprime_review": bool(selected),
        "role_reason_codes": list(reasons),
        "classification_basis": "generic_metadata_and_bounded_window_diagnostics",
        "classifier_is_generic": True,
        **_non_authority_posture(),
    }
    payload["proposal_digest"] = _digest_json(payload)
    return payload


def _candidate_evidence_triage_packet(
    *,
    plan: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    role_proposals: Sequence[Mapping[str, Any]],
    entrypoint_kind: str,
) -> dict[str, Any]:
    roles_by_candidate = _roles_by_candidate(role_proposals)
    strict_refs = _candidate_refs_with_role(role_proposals, ROLE_STRICT_ANSWER_SUPPORT)
    contextual_refs = _candidate_refs_with_role(
        role_proposals, ROLE_ANSWER_ADJACENT_CONTEXT
    )
    overclaim_refs = _candidate_refs_with_role(role_proposals, ROLE_OVERCLAIM_RISK)
    selected_ref = _dprime_review_candidate_ref(
        candidates,
        strict_refs=strict_refs,
    )
    top_ref = _first_candidate_ref(candidates)
    packet = _without_empty(
        {
            "schema_version": CANDIDATE_EVIDENCE_TRIAGE_SCHEMA_VERSION,
            "phase": ANALYST_WORKBENCH_PHASE,
            "packet_kind": "CandidateEvidenceTriagePacket",
            "packet_id": (
                "candidate-evidence-triage:"
                f"{_clean_text(plan.get('plan_id'), limit=320) or 'unplanned'}"
            ),
            "runtime_consumer": RUNTIME_CONSUMER,
            "entrypoint_kind": _clean_text(entrypoint_kind, limit=120),
            "ordinary_product_path_consumed": True,
            "relation_plan_ref": _plan_ref(plan),
            "acquisition_plan_ref": _acquisition_ref(acquisition),
            "candidate_count": len(candidates),
            "role_proposal_count": len(role_proposals),
            "candidate_refs": [_safe_mapping(item.get("candidate_ref")) for item in candidates],
            "top_candidate_ref": top_ref,
            "selected_candidate_ref": selected_ref,
            "dprime_review_candidate_ref": selected_ref,
            "strict_answer_support_candidate_refs": strict_refs,
            "contextual_candidate_refs": contextual_refs,
            "overclaim_risk_candidate_refs": overclaim_refs,
            "roles_by_candidate": roles_by_candidate,
            "evidence_role_proposals": list(role_proposals),
            "generic_role_classification": True,
            "source_text_retained": False,
            **_non_authority_posture(),
        }
    )
    packet["packet_digest"] = _digest_json(packet)
    return packet


def _analyst_finding_proposals(
    *,
    triage_packet: Mapping[str, Any],
    fetch_read_content_packet: Mapping[str, Any],
) -> list[dict[str, Any]]:
    strict_refs = [
        _safe_mapping(item)
        for item in _safe_sequence(triage_packet.get("strict_answer_support_candidate_refs"))
    ]
    contextual_refs = [
        _safe_mapping(item)
        for item in _safe_sequence(triage_packet.get("contextual_candidate_refs"))
    ]
    overclaim_refs = [
        _safe_mapping(item)
        for item in _safe_sequence(triage_packet.get("overclaim_risk_candidate_refs"))
    ]
    selected_ref = _safe_mapping(triage_packet.get("selected_candidate_ref"))
    findings = [
        _finding_proposal(
            finding_kind="strict_support_present"
            if strict_refs
            else "strict_support_missing",
            selected_candidate_ref=selected_ref,
            supporting_candidate_refs=strict_refs,
            contextual_candidate_refs=contextual_refs,
            overclaim_risk_candidate_refs=overclaim_refs,
            fetch_read_content_packet=fetch_read_content_packet,
        )
    ]
    if overclaim_refs:
        findings.append(
            _finding_proposal(
                finding_kind="overclaim_risk_present",
                selected_candidate_ref=selected_ref,
                supporting_candidate_refs=[],
                contextual_candidate_refs=contextual_refs,
                overclaim_risk_candidate_refs=overclaim_refs,
                fetch_read_content_packet=fetch_read_content_packet,
            )
        )
    return findings


def _finding_proposal(
    *,
    finding_kind: str,
    selected_candidate_ref: Mapping[str, Any],
    supporting_candidate_refs: Sequence[Mapping[str, Any]],
    contextual_candidate_refs: Sequence[Mapping[str, Any]],
    overclaim_risk_candidate_refs: Sequence[Mapping[str, Any]],
    fetch_read_content_packet: Mapping[str, Any],
) -> dict[str, Any]:
    packet_digest = _clean_text(fetch_read_content_packet.get("packet_digest"), limit=128)
    finding = _without_empty(
        {
            "schema_version": ANALYST_FINDING_PROPOSAL_SCHEMA_VERSION,
            "phase": ANALYST_WORKBENCH_PHASE,
            "finding_kind": finding_kind,
            "finding_id": f"analyst-finding-proposal:{finding_kind}",
            "selected_candidate_ref": dict(selected_candidate_ref),
            "supporting_candidate_refs": [dict(item) for item in supporting_candidate_refs],
            "contextual_candidate_refs": [dict(item) for item in contextual_candidate_refs],
            "overclaim_risk_candidate_refs": [
                dict(item) for item in overclaim_risk_candidate_refs
            ],
            "fetch_read_content_packet_digest": packet_digest,
            "finding_basis": "candidate role proposals and bounded-window diagnostics",
            **_non_authority_posture(),
        }
    )
    finding["finding_digest"] = _digest_json(finding)
    return finding


def _analysis_gap_search_proposal(
    *,
    plan: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    triage_packet: Mapping[str, Any],
) -> dict[str, Any]:
    strict_refs = _safe_sequence(triage_packet.get("strict_answer_support_candidate_refs"))
    contextual_refs = _safe_sequence(triage_packet.get("contextual_candidate_refs"))
    overclaim_refs = _safe_sequence(triage_packet.get("overclaim_risk_candidate_refs"))
    role_map = _safe_mapping(triage_packet.get("roles_by_candidate"))
    unreadable_refs = [
        _safe_mapping(item.get("candidate_ref"))
        for item in _safe_sequence(triage_packet.get("evidence_role_proposals"))
        if _safe_mapping(item).get("role") == ROLE_UNREADABLE_HIGH_VALUE_OFFICIAL
    ]
    gap_needed = bool(unreadable_refs or not strict_refs)
    if not gap_needed:
        gap_kind = "not_required"
        reason = "strict support candidate proposed; contextual risks preserved"
    elif unreadable_refs:
        gap_kind = "unreadable_high_value_candidate"
        reason = "official-looking candidate needs readable strict support"
    elif not strict_refs and contextual_refs:
        gap_kind = "strict_support_missing"
        reason = "contextual material is insufficient for strict answer support"
    elif overclaim_refs:
        gap_kind = "overclaim_risk"
        reason = "value-bearing contextual material needs stricter source confirmation"
    elif not strict_refs:
        gap_kind = "strict_support_missing"
        reason = "strict answer support was not identified"
    else:
        gap_kind = "not_required"
        reason = "strict support candidate proposed"
    proposal = _without_empty(
        {
            "schema_version": ANALYSIS_GAP_SEARCH_PROPOSAL_SCHEMA_VERSION,
            "phase": ANALYST_WORKBENCH_PHASE,
            "proposal_kind": "AnalysisGapSearchProposal",
            "proposal_id": (
                "analysis-gap-search-proposal:"
                f"{_clean_text(plan.get('source_obligation_id'), limit=320) or 'source'}"
            ),
            "ordinary_product_path_consumed": True,
            "gap_status": "proposed" if gap_needed else "not_required",
            "gap_kind": gap_kind,
            "gap_reason": reason,
            "proposed_source_kind": "official or source-of-record strict support",
            "proposed_query_ref": _without_empty(
                {
                    "relation_plan_search_query_seed": _first_text(
                        plan.get("search_query_seeds")
                    ),
                    "acquisition_query": acquisition.get("acquisition_query"),
                    "component_id": plan.get("component_id"),
                    "source_obligation_id": plan.get("source_obligation_id"),
                }
            ),
            "contextual_candidate_refs": [
                _safe_mapping(item) for item in contextual_refs
            ],
            "overclaim_risk_candidate_refs": [
                _safe_mapping(item) for item in overclaim_refs
            ],
            "unreadable_candidate_refs": unreadable_refs,
            "roles_by_candidate": role_map,
            "live_followup_required": bool(gap_needed),
            "live_followup_licensed": False,
            "proposed_runkernel_reduction_status": (
                WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED
                if gap_needed
                else WORKBENCH_REDUCTION_NOT_REQUIRED
            ),
            **_non_authority_posture(),
        }
    )
    proposal["proposal_digest"] = _digest_json(proposal)
    return proposal


def _analyst_workbench_packet(
    *,
    triage_packet: Mapping[str, Any],
    analyst_findings: Sequence[Mapping[str, Any]],
    gap_proposal: Mapping[str, Any],
    entrypoint_kind: str,
) -> dict[str, Any]:
    overclaim = bool(_safe_sequence(triage_packet.get("overclaim_risk_candidate_refs")))
    strict_refs = _safe_sequence(triage_packet.get("strict_answer_support_candidate_refs"))
    gap_needed = gap_proposal.get("gap_status") == "proposed"
    packet = _without_empty(
        {
            "schema_version": ANALYST_WORKBENCH_SCHEMA_VERSION,
            "phase": ANALYST_WORKBENCH_PHASE,
            "packet_kind": "AnalystWorkbenchPacket",
            "packet_id": (
                "analyst-workbench:"
                f"{_clean_text(_safe_mapping(triage_packet.get('relation_plan_ref')).get('plan_id'), limit=320) or 'unplanned'}"
            ),
            "runtime_consumer": RUNTIME_CONSUMER,
            "entrypoint_kind": _clean_text(entrypoint_kind, limit=120),
            "ordinary_product_path_consumed": True,
            "candidate_evidence_triage_ref": _triage_ref(triage_packet),
            "evidence_role_proposal_refs": [
                _role_proposal_ref(item)
                for item in _safe_sequence(triage_packet.get("evidence_role_proposals"))
            ],
            "analyst_finding_proposals": list(analyst_findings),
            "analyst_finding_proposal_refs": [
                _finding_ref(item) for item in analyst_findings
            ],
            "specialist_lane_placeholder": _lane_placeholder("specialist"),
            "economist_lane_placeholder": _lane_placeholder("economist"),
            "scrutineer_lane_placeholder": _scrutineer_lane(
                challenge_recommended=bool(gap_needed or overclaim)
            ),
            "analysis_gap_search_proposal": dict(gap_proposal),
            "analysis_gap_search_proposal_ref": _gap_ref(gap_proposal),
            "strict_answer_support_candidate_count": len(strict_refs),
            "contextual_candidate_count": len(
                _safe_sequence(triage_packet.get("contextual_candidate_refs"))
            ),
            "overclaim_risk_candidate_count": len(
                _safe_sequence(triage_packet.get("overclaim_risk_candidate_refs"))
            ),
            "display_candidate_ref_status": "not_authorized_by_workbench",
            "dprime_review_candidate_ref": _safe_mapping(
                triage_packet.get("dprime_review_candidate_ref")
            ),
            **_non_authority_posture(),
        }
    )
    packet["packet_digest"] = _digest_json(packet)
    return packet


def _workbench_dprime_dossier(
    *,
    triage_packet: Mapping[str, Any],
    workbench_packet: Mapping[str, Any],
    gap_proposal: Mapping[str, Any],
) -> dict[str, Any]:
    dossier = _without_empty(
        {
            "schema_version": WORKBENCH_DPRIME_DOSSIER_SCHEMA_VERSION,
            "phase": ANALYST_WORKBENCH_PHASE,
            "dossier_kind": "WorkbenchDprimeDossier",
            "dossier_id": (
                "workbench-dprime-dossier:"
                f"{_clean_text(_safe_mapping(triage_packet.get('relation_plan_ref')).get('plan_id'), limit=320) or 'unplanned'}"
            ),
            "runtime_consumer": RUNTIME_CONSUMER,
            "dprime_consumer": DPRIME_CONSUMER,
            "ordinary_product_path_consumed": True,
            "candidate_evidence_triage_ref": _triage_ref(triage_packet),
            "analyst_workbench_ref": _workbench_ref(workbench_packet),
            "selected_candidate_ref": _safe_mapping(
                triage_packet.get("selected_candidate_ref")
            ),
            "top_candidate_ref": _safe_mapping(triage_packet.get("top_candidate_ref")),
            "dprime_review_candidate_ref": _safe_mapping(
                triage_packet.get("dprime_review_candidate_ref")
            ),
            "strict_answer_support_candidate_refs": [
                _safe_mapping(item)
                for item in _safe_sequence(
                    triage_packet.get("strict_answer_support_candidate_refs")
                )
            ],
            "contextual_candidate_refs": [
                _safe_mapping(item)
                for item in _safe_sequence(triage_packet.get("contextual_candidate_refs"))
            ],
            "overclaim_risk_candidate_refs": [
                _safe_mapping(item)
                for item in _safe_sequence(
                    triage_packet.get("overclaim_risk_candidate_refs")
                )
            ],
            "role_proposal_refs": [
                _role_proposal_ref(item)
                for item in _safe_sequence(triage_packet.get("evidence_role_proposals"))
            ],
            "analyst_finding_proposal_refs": [
                _finding_ref(item)
                for item in _safe_sequence(
                    workbench_packet.get("analyst_finding_proposals")
                )
            ],
            "scrutineer_lane_ref": _lane_ref(
                _safe_mapping(workbench_packet.get("scrutineer_lane_placeholder"))
            ),
            "specialist_lane_ref": _lane_ref(
                _safe_mapping(workbench_packet.get("specialist_lane_placeholder"))
            ),
            "economist_lane_ref": _lane_ref(
                _safe_mapping(workbench_packet.get("economist_lane_placeholder"))
            ),
            "analysis_gap_search_proposal_ref": _gap_ref(gap_proposal),
            "gap_proposal_status": gap_proposal.get("gap_status"),
            "strict_answer_support_candidate_count": len(
                _safe_sequence(triage_packet.get("strict_answer_support_candidate_refs"))
            ),
            "contextual_candidate_count": len(
                _safe_sequence(triage_packet.get("contextual_candidate_refs"))
            ),
            "overclaim_risk_candidate_count": len(
                _safe_sequence(triage_packet.get("overclaim_risk_candidate_refs"))
            ),
            "source_text_retained": False,
            **_non_authority_posture(),
        }
    )
    dossier["dossier_digest"] = _digest_json(dossier)
    return dossier


def _workbench_reduction_projection(
    *,
    triage_packet: Mapping[str, Any],
    workbench_packet: Mapping[str, Any],
    gap_proposal: Mapping[str, Any],
    dossier: Mapping[str, Any],
) -> dict[str, Any]:
    strict_count = len(_safe_sequence(triage_packet.get("strict_answer_support_candidate_refs")))
    overclaim_count = len(_safe_sequence(triage_packet.get("overclaim_risk_candidate_refs")))
    gap_needed = gap_proposal.get("gap_status") == "proposed"
    status = (
        WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED
        if gap_needed
        else WORKBENCH_REDUCTION_CHALLENGED
        if overclaim_count
        else WORKBENCH_REDUCTION_ADMITTED
        if strict_count
        else WORKBENCH_REDUCTION_NOT_REQUIRED
    )
    projection = _without_empty(
        {
            "schema_version": WORKBENCH_REDUCTION_PROJECTION_SCHEMA_VERSION,
            "phase": ANALYST_WORKBENCH_PHASE,
            "projection_kind": "WorkbenchReductionProjection",
            "owner": "AnalystWorkbenchRuntime",
            "runtime_consumer": RUNTIME_CONSUMER,
            "ordinary_product_path_consumed": True,
            "run_kernel_reduced": False,
            "run_kernel_reduction_pending": True,
            "proposed_for_runkernel_reduction": True,
            "status": status,
            "blocked_before_answer": status
            in {WORKBENCH_REDUCTION_BLOCKED, WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED},
            "candidate_evidence_triage_ref": _triage_ref(triage_packet),
            "analyst_workbench_ref": _workbench_ref(workbench_packet),
            "analysis_gap_search_proposal_ref": _gap_ref(gap_proposal),
            "workbench_dprime_dossier_ref": workbench_dprime_dossier_ref(dossier),
            "reduction_reason": (
                "strict support follow-up is needed but not licensed"
                if status == WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED
                else "local workbench projection prepared for D-prime dossier handoff"
            ),
            "strict_answer_support_candidate_count": strict_count,
            "overclaim_risk_candidate_count": overclaim_count,
            "workbench_proposals_are_not_support_admission": True,
            **_non_authority_posture(),
        }
    )
    projection["projection_digest"] = _digest_json(projection)
    return projection


def _lane_placeholder(lane: str) -> dict[str, Any]:
    lane_packet = {
        "lane": lane,
        "schema_version": "analyst_workbench_lane_placeholder_v1",
        "phase": ANALYST_WORKBENCH_PHASE,
        "owner": f"AnalystWorkbenchRuntime.{lane.title()}LanePlaceholder",
        "status": "not_required",
        "work_request_created": False,
        **_non_authority_posture(),
    }
    lane_packet["lane_digest"] = _digest_json(lane_packet)
    return lane_packet


def _scrutineer_lane(*, challenge_recommended: bool) -> dict[str, Any]:
    lane = _lane_placeholder("scrutineer")
    lane["owner"] = "AnalystWorkbenchRuntime.ScrutineerLanePlaceholder"
    lane["status"] = "challenge_recommended" if challenge_recommended else "cleared"
    lane["challenge_recommended"] = bool(challenge_recommended)
    lane["lane_digest"] = _digest_json(lane)
    return lane


def _provider_results_by_url(
    provider_results: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in provider_results:
        safe = _safe_mapping(item)
        url = _clean_text(safe.get("url") or safe.get("link"), limit=700)
        if url:
            out[url] = safe
    return out


def _candidate_ref(
    diagnostic: Mapping[str, Any],
    window: Mapping[str, Any],
) -> dict[str, Any]:
    return _without_empty(
        {
            "candidate_id": _clean_text(diagnostic.get("candidate_id"), limit=320),
            "candidate_digest": _clean_text(
                diagnostic.get("candidate_digest"), limit=128
            ),
            "title": _clean_text(diagnostic.get("title"), limit=220),
            "url": _clean_text(diagnostic.get("url"), limit=700),
            "domain": _clean_text(diagnostic.get("domain"), limit=260),
            "provider_rank": _bounded_int(diagnostic.get("provider_rank")),
            "fetch_read_priority_rank": _bounded_int(
                diagnostic.get("fetch_read_priority_rank")
            ),
            "selected_for_dprime_review": bool(
                diagnostic.get("answer_bearing_candidate_window_selected") is True
                or window.get("candidate_window_selected") is True
            ),
            "selected_window_digest": _clean_text(
                diagnostic.get("selected_window_digest")
                or window.get("selected_window_digest"),
                limit=128,
            ),
            "bounded_content_digest": _clean_text(
                diagnostic.get("bounded_content_digest")
                or window.get("bounded_content_digest"),
                limit=128,
            ),
            "official_pdf_or_table_artifact_candidate": (
                diagnostic.get("official_pdf_or_table_artifact_candidate") is True
                or window.get("official_pdf_or_table_artifact_candidate") is True
            ),
            "official_artifact_type": (
                _clean_text(diagnostic.get("official_artifact_type"), limit=80)
                or _clean_text(window.get("official_artifact_type"), limit=80)
            ),
            "official_artifact_read_support_status": (
                _clean_text(
                    diagnostic.get("official_artifact_read_support_status"),
                    limit=120,
                )
                or _clean_text(
                    window.get("official_artifact_read_support_status"),
                    limit=120,
                )
            ),
        }
    )


def _plan_ref(plan: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "plan_id": plan.get("plan_id"),
            "packet_digest": plan.get("packet_digest"),
            "component_id": plan.get("component_id"),
            "source_obligation_id": plan.get("source_obligation_id"),
            "search_requirement_id": plan.get("search_requirement_id"),
            "supported_query_class_id": plan.get("supported_query_class_id"),
        }
    )


def _acquisition_ref(acquisition: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "planner_kind": acquisition.get("planner_kind"),
            "acquisition_query": acquisition.get("acquisition_query"),
            "extraction_provider": acquisition.get("extraction_provider"),
            "expected_value_token_kinds": [
                _clean_text(item, limit=40)
                for item in _safe_sequence(acquisition.get("expected_value_token_kinds"))
                if _clean_text(item, limit=40)
            ],
        }
    )


def _triage_ref(packet: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "schema_version": packet.get("schema_version"),
            "phase": packet.get("phase"),
            "packet_id": packet.get("packet_id"),
            "packet_digest": packet.get("packet_digest"),
            "candidate_count": packet.get("candidate_count"),
            "role_proposal_count": packet.get("role_proposal_count"),
        }
    )


def _workbench_ref(packet: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "schema_version": packet.get("schema_version"),
            "phase": packet.get("phase"),
            "packet_id": packet.get("packet_id"),
            "packet_digest": packet.get("packet_digest"),
            "strict_answer_support_candidate_count": packet.get(
                "strict_answer_support_candidate_count"
            ),
            "overclaim_risk_candidate_count": packet.get(
                "overclaim_risk_candidate_count"
            ),
        }
    )


def _role_proposal_ref(proposal: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "schema_version": proposal.get("schema_version"),
            "phase": proposal.get("phase"),
            "proposal_id": proposal.get("proposal_id"),
            "proposal_digest": proposal.get("proposal_digest"),
            "role": proposal.get("role"),
            "candidate_ref": _safe_mapping(proposal.get("candidate_ref")),
        }
    )


def _finding_ref(finding: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "schema_version": finding.get("schema_version"),
            "phase": finding.get("phase"),
            "finding_id": finding.get("finding_id"),
            "finding_digest": finding.get("finding_digest"),
            "finding_kind": finding.get("finding_kind"),
        }
    )


def _gap_ref(proposal: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "schema_version": proposal.get("schema_version"),
            "phase": proposal.get("phase"),
            "proposal_id": proposal.get("proposal_id"),
            "proposal_digest": proposal.get("proposal_digest"),
            "gap_status": proposal.get("gap_status"),
            "gap_kind": proposal.get("gap_kind"),
            "proposed_runkernel_reduction_status": proposal.get(
                "proposed_runkernel_reduction_status"
            ),
            "live_followup_required": proposal.get("live_followup_required"),
            "live_followup_licensed": proposal.get("live_followup_licensed"),
        }
    )


def _projection_ref(projection: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "schema_version": projection.get("schema_version"),
            "phase": projection.get("phase"),
            "owner": projection.get("owner"),
            "status": projection.get("status"),
            "run_kernel_reduced": projection.get("run_kernel_reduced"),
            "run_kernel_reduction_pending": projection.get(
                "run_kernel_reduction_pending"
            ),
            "proposed_for_runkernel_reduction": projection.get(
                "proposed_for_runkernel_reduction"
            ),
            "projection_digest": projection.get("projection_digest"),
            "blocked_before_answer": projection.get("blocked_before_answer"),
        }
    )


def _lane_ref(lane: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "lane": lane.get("lane"),
            "phase": lane.get("phase"),
            "owner": lane.get("owner"),
            "status": lane.get("status"),
            "lane_digest": lane.get("lane_digest"),
        }
    )


def _candidate_refs_with_role(
    role_proposals: Sequence[Mapping[str, Any]],
    role: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for proposal in role_proposals:
        safe = _safe_mapping(proposal)
        if safe.get("role") != role:
            continue
        ref = _safe_mapping(safe.get("candidate_ref"))
        identity = _clean_text(ref.get("candidate_id"), limit=320) or _digest_json(ref)
        if identity in seen:
            continue
        seen.add(identity)
        refs.append(ref)
    return refs


def _roles_by_candidate(
    role_proposals: Sequence[Mapping[str, Any]],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for proposal in role_proposals:
        safe = _safe_mapping(proposal)
        ref = _safe_mapping(safe.get("candidate_ref"))
        candidate_id = _clean_text(ref.get("candidate_id"), limit=320)
        role = _clean_text(safe.get("role"), limit=120)
        if candidate_id and role:
            out.setdefault(candidate_id, []).append(role)
    return out


def _first_candidate_ref(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {}
    first = sorted(
        candidates,
        key=lambda item: (
            _bounded_int(item.get("provider_rank"), default=999),
            _bounded_int(item.get("fetch_read_priority_rank"), default=999),
        ),
    )[0]
    return _safe_mapping(first.get("candidate_ref"))


def _first_selected_candidate_ref(
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    for candidate in candidates:
        if candidate.get("selected_for_dprime_review") is True:
            return _safe_mapping(candidate.get("candidate_ref"))
    return _first_candidate_ref(candidates)


def _dprime_review_candidate_ref(
    candidates: Sequence[Mapping[str, Any]],
    *,
    strict_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    strict_ids = {
        _clean_text(_safe_mapping(item).get("candidate_id"), limit=320)
        for item in strict_refs
    }
    official_artifact_strict = [
        candidate
        for candidate in candidates
        if _clean_text(candidate.get("candidate_id"), limit=320) in strict_ids
        and candidate.get("official_pdf_or_table_artifact_candidate") is True
        and candidate.get("readable_or_bounded_window_available") is True
    ]
    if official_artifact_strict:
        return _safe_mapping(
            sorted(
                official_artifact_strict,
                key=lambda item: (
                    _bounded_int(item.get("fetch_read_priority_rank"), default=999),
                    _bounded_int(item.get("provider_rank"), default=999),
                ),
            )[0].get("candidate_ref")
        )
    return _first_selected_candidate_ref(candidates)


def _query_tokens(plan: Mapping[str, Any], acquisition: Mapping[str, Any]) -> set[str]:
    parts = [
        _clean_text(plan.get("component_text"), limit=400),
        _clean_text(plan.get("source_obligation_text"), limit=400),
        _clean_text(plan.get("claim_under_test"), limit=500),
        _clean_text(acquisition.get("acquisition_query"), limit=500),
    ]
    parts.extend(
        _clean_text(item, limit=160)
        for item in _safe_sequence(plan.get("search_query_seeds"))
    )
    return {
        token
        for token in _TOKEN_RE.findall(" ".join(item for item in parts if item).casefold())
        if len(token) >= 4
    }


def _text_features(value: str) -> dict[str, Any]:
    lowered = value.casefold()
    compact = re.sub(r"(?<=[a-z0-9])[-_/](?=[a-z0-9])", "", lowered)
    tokens = set(_TOKEN_RE.findall(lowered))
    tokens.update(_TOKEN_RE.findall(compact))
    return {"lowered": lowered, "tokens": sorted(tokens)}


def _value_token_count_from_text(value: Any) -> int:
    text = _clean_text(value, limit=2_000) or ""
    patterns = (
        r"\$\s?\d{1,6}(?:\.\d{2})?",
        r"\b(?:19|20)\d{2}(?:-\d{1,2}(?:-\d{1,2})?)?\b",
        (
            r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
            r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
            r"nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}\b"
        ),
        r"\b\d+(?:\.\d+)?\b",
    )
    values: set[str] = set()
    lowered = text.casefold()
    for pattern in patterns:
        values.update(re.findall(pattern, lowered, flags=re.IGNORECASE))
    return len(values)


def _non_authority_posture() -> dict[str, Any]:
    return {
        **_NON_AUTHORITY_TRUE_FLAGS,
        **_NON_AUTHORITY_FALSE_FLAGS,
        "raw_private_retention_flags": dict(_RAW_FALSE_FLAGS),
        **_RAW_FALSE_FLAGS,
    }


def _reject_raw_private_or_authority_claims(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key or "").strip().casefold()
            if normalized in _NON_AUTHORITY_FALSE_FLAGS and item is not False:
                raise AnalystWorkbenchError(f"forbidden authority claim: {key}")
            if normalized == "raw_private_retention_flags":
                flags = _safe_mapping(item)
                if not flags or any(flag_value is not False for flag_value in flags.values()):
                    raise AnalystWorkbenchError(
                        "raw/private retention flags must stay false"
                    )
                continue
            if normalized.startswith("raw_") and item is not False:
                raise AnalystWorkbenchError(f"raw/private retention claim: {key}")
            _reject_raw_private_or_authority_claims(item)
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            _reject_raw_private_or_authority_claims(item)


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {}, ())
    }


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _first_text(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_text(value, limit=500)
    for item in _safe_sequence(value):
        text = _clean_text(item, limit=500)
        if text:
            return text
    return None


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, parsed)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ANALYST_WORKBENCH_PHASE",
    "ANALYST_WORKBENCH_SCHEMA_VERSION",
    "ANALYST_FINDING_PROPOSAL_SCHEMA_VERSION",
    "ANALYSIS_GAP_SEARCH_PROPOSAL_SCHEMA_VERSION",
    "AnalystWorkbenchError",
    "CANDIDATE_EVIDENCE_TRIAGE_SCHEMA_VERSION",
    "EVIDENCE_ROLE_PROPOSAL_SCHEMA_VERSION",
    "ROLE_ANSWER_ADJACENT_CONTEXT",
    "ROLE_OVERCLAIM_RISK",
    "ROLE_QUALIFIER_EXCEPTION_CONTEXT",
    "ROLE_STRICT_ANSWER_SUPPORT",
    "ROLE_UNREADABLE_HIGH_VALUE_OFFICIAL",
    "WORKBENCH_DPRIME_DOSSIER_SCHEMA_VERSION",
    "WORKBENCH_REDUCTION_PROJECTION_SCHEMA_VERSION",
    "WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED",
    "build_current_source_record_analyst_workbench",
    "empty_current_source_record_analyst_workbench_bundle",
    "validate_current_source_record_analyst_workbench_bundle",
    "workbench_dprime_dossier_ref",
]
