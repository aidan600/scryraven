"""Compact semantic-state consumption for RunAuthority Sufficiency (AG-SEM-09).

Pure helpers derive sanitized ``semantic_state_facts`` from canonical AG-SEM-05/07/08
RunKernel state and evaluate deterministic semantic blockers for the real Sufficiency
judgment path. This module does not reduce state, authorize actions, call models,
or mutate accepted contracts, coverage, or amendments.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION = (
    "sufficiency_semantic_state_consumption_ag_sem_09_v1"
)

_MAX_LIST_ITEMS = 80
_MAX_BLOCKERS = 80

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db_row",
        "full_trace",
        "logs",
        "model_response",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_prompt",
        "raw_provider_payload",
        "raw_trace",
        "secret",
        "token",
        "unbounded_text",
    }
)

_REQUIRED_POSTURE = frozenset({"required"})
_SATISFIED_COVERAGE_STATES = frozenset({"satisfied"})
_DIRECT_BLOCKING_COVERAGE_STATES = frozenset(
    {
        "unassessed",
        "unsupported",
        "partial",
        "supported_with_caveats",
        "blocked",
    }
)
_FINALIZATION_BLOCKING_COVERAGE_STATES = frozenset({"conflicted", "stale", "blocked"})
_WEAK_ONLY_EVIDENCE_BASIS = frozenset(
    {
        "candidate_discovery",
        "evidence_ledger_custody",
        "search_result_snippet",
        "provider_answer_product",
        "work_attempted",
        "work_completed",
        "ids_or_digests_only",
    }
)
_STRONG_EVIDENCE_BASIS = frozenset(
    {
        "semantic_observation",
        "answer_bearing_content",
    }
)
_BLOCKING_SOURCE_OBLIGATION = frozenset(
    {"unsatisfied", "partial", "unknown", "stale"}
)
_BLOCKING_CONTENT_AVAILABILITY = frozenset(
    {"missing", "unreadable", "stale", "unknown", "partial"}
)
_BLOCKING_FOLLOWUP_NEED = frozenset({"required", "blocked"})
_BLOCKING_AMENDMENT_DISPOSITION = frozenset({"blocked"})
_CONFIRMATION_REQUIRED_DISPOSITION = frozenset(
    {"requires_user_confirmation", "proposed", "eligible_for_future_acceptance"}
)
_ALLOWED_USER_CONFIRMATION = frozenset(
    {
        "explicit_user_confirmation",
        "labeled_scenario_treatment",
        "explicit_user_authority",
    }
)
_WEAKENING_POSTURES_REQUIRING_AUTHORITY = frozenset(
    {
        "removes_requirement",
        "weakens_requirement",
        "weakens_source_obligation",
    }
)
_NON_BLOCKING_REJECTION_PREFIXES = (
    "ordinary_",
    "non_material_",
    "policy_",
)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if not clean_key or _is_sensitive_key(clean_key):
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items[:_MAX_LIST_ITEMS]]
    return _clean_text(value, limit=300)


def _digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _token_list(value: Any, *, limit: int = 160) -> list[str]:
    out: list[str] = []
    for item in _list(value):
        token = _clean_token(item, limit=limit)
        if token and token not in out:
            out.append(token)
    return out


def _normalized_token(value: Any) -> str | None:
    token = _clean_token(value)
    if not token:
        return None
    return token.casefold().replace("-", "_").replace(" ", "_")


def _latest_coverage_by_component(
    coverage_history: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for item in coverage_history:
        if not isinstance(item, Mapping):
            continue
        component_id = _clean_token(item.get("answer_component_id"))
        if not component_id:
            continue
        latest[component_id] = dict(item)
    return latest


def _invalidated_coverage_ids(
    amendment_history: Sequence[Mapping[str, Any]],
) -> dict[str, list[str]]:
    suspects: dict[str, list[str]] = {}
    for admission in amendment_history:
        if not isinstance(admission, Mapping):
            continue
        amendment_id = _clean_token(admission.get("amendment_record_id")) or "amendment"
        for candidate in _list(admission.get("candidate_invalidated_coverage_refs")):
            if not isinstance(candidate, Mapping):
                continue
            coverage_id = _clean_token(candidate.get("coverage_record_id"))
            component_id = _clean_token(candidate.get("answer_component_id"))
            if not coverage_id and not component_id:
                continue
            key = component_id or coverage_id or ""
            reasons = suspects.setdefault(key, [])
            reason = f"candidate_invalidated_coverage_ref:{amendment_id}"
            if reason not in reasons:
                reasons.append(reason)
    return suspects


def _is_weak_only_evidence_basis(evidence_basis: Sequence[Any]) -> bool:
    tokens = [_normalized_token(item) for item in evidence_basis]
    tokens = [token for token in tokens if token]
    if not tokens:
        return False
    if any(token in _STRONG_EVIDENCE_BASIS for token in tokens):
        return False
    return all(token in _WEAK_ONLY_EVIDENCE_BASIS for token in tokens)


def _append_blocker(
    blockers: list[dict[str, Any]],
    *,
    code: str,
    scope: str,
    ref_id: str | None = None,
    reason: str | None = None,
) -> None:
    if len(blockers) >= _MAX_BLOCKERS:
        return
    entry = {
        "code": _clean_token(code, limit=120),
        "scope": _clean_token(scope, limit=80),
    }
    if ref_id:
        entry["ref_id"] = _clean_token(ref_id, limit=160)
    if reason:
        entry["reason"] = _clean_text(reason, limit=260)
    blockers.append(entry)


@dataclass(frozen=True, slots=True)
class SemanticSufficiencyOverlay:
    """Deterministic semantic blocker overlay for Sufficiency judgment."""

    blockers: tuple[Mapping[str, Any], ...] = ()
    missing_assessments: tuple[Mapping[str, Any], ...] = ()
    mandatory_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()
    direct_answer_blocked: bool = False
    finalization_blocked: bool = False
    coverage_suspect_component_ids: tuple[str, ...] = ()
    candidate_new_contract_versions: tuple[str, ...] = ()


def build_semantic_state_facts_for_sufficiency(
    *,
    initial_answer_contract: Mapping[str, Any] | None,
    component_coverage_history: Sequence[Mapping[str, Any]],
    contract_amendment_admission_history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build compact semantic facts consumed by RunAuthority Sufficiency."""

    contract = _mapping(initial_answer_contract)
    if not contract.get("accepted_contract_digest"):
        return {
            "schema_version": SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION,
            "accepted_contract_version": None,
            "accepted_contract_digest": None,
            "required_component_count": 0,
            "covered_component_count": 0,
            "component_summaries": [],
            "amendment_summaries": [],
            "blockers": [],
            "required_caveats": [],
            "prohibited_upgrades": [],
            "direct_answer_blocked": False,
            "finalization_blocked": False,
        }

    latest_coverage = _latest_coverage_by_component(component_coverage_history)
    invalidation_suspects = _invalidated_coverage_ids(contract_amendment_admission_history)

    required_refs = [
        ref
        for ref in _list(contract.get("accepted_answer_component_refs"))
        if isinstance(ref, Mapping)
        and _normalized_token(ref.get("requirement_posture")) in _REQUIRED_POSTURE
    ]
    component_summaries: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    required_caveats: list[str] = []
    prohibited_upgrades: list[str] = []
    direct_answer_blocked = False
    finalization_blocked = False

    for ref in required_refs:
        component_id = _clean_token(ref.get("component_id")) or ""
        coverage = latest_coverage.get(component_id, {})
        suspect_reasons = list(invalidation_suspects.get(component_id, []))
        coverage_record_id = _clean_token(coverage.get("coverage_record_id"))
        if coverage_record_id:
            suspect_reasons.extend(invalidation_suspects.get(coverage_record_id, []))
        coverage_suspect = bool(suspect_reasons)

        summary = {
            "component_id": component_id,
            "requirement_posture": _clean_token(ref.get("requirement_posture")),
            "coverage_present": bool(coverage),
            "coverage_record_id": coverage_record_id,
            "coverage_state": _clean_token(coverage.get("coverage_state")),
            "semantic_support_status": _clean_token(
                coverage.get("semantic_support_status")
            ),
            "source_obligation_status": _clean_token(
                coverage.get("source_obligation_status")
            ),
            "content_availability_status": _clean_token(
                coverage.get("content_availability_status")
            ),
            "evidence_custody_status": _clean_token(
                coverage.get("evidence_custody_status")
            ),
            "evidence_basis": _token_list(coverage.get("evidence_basis")),
            "stale": bool(coverage.get("stale")),
            "remaining_unknowns": _token_list(coverage.get("remaining_unknowns")),
            "followup_need": _clean_token(coverage.get("followup_need")),
            "coverage_suspect": coverage_suspect,
            "coverage_suspect_reasons": suspect_reasons[:10],
            "blockers": [],
        }
        component_blockers: list[str] = []

        if not coverage:
            component_blockers.append("missing_required_component_coverage")
            _append_blocker(
                blockers,
                code="missing_required_component_coverage",
                scope="component",
                ref_id=component_id,
                reason="required_component_has_no_reduced_coverage",
            )
            direct_answer_blocked = True
        else:
            coverage_state = _normalized_token(coverage.get("coverage_state"))
            stale_flag = bool(coverage.get("stale"))
            conflict_posture = _normalized_token(coverage.get("conflict_posture"))

            if stale_flag or coverage_state == "stale":
                component_blockers.append("stale_coverage")
                _append_blocker(
                    blockers,
                    code="stale_coverage",
                    scope="component",
                    ref_id=component_id,
                )
                finalization_blocked = True
            if coverage_state == "conflicted" or conflict_posture == "present":
                component_blockers.append("conflicted_coverage")
                _append_blocker(
                    blockers,
                    code="conflicted_coverage",
                    scope="component",
                    ref_id=component_id,
                )
                finalization_blocked = True
            if coverage_state in _DIRECT_BLOCKING_COVERAGE_STATES:
                code = (
                    "partial_or_unsupported_coverage"
                    if coverage_state in {"partial", "supported_with_caveats", "unsupported"}
                    else "required_component_not_satisfied"
                )
                component_blockers.append(code)
                _append_blocker(
                    blockers,
                    code=code,
                    scope="component",
                    ref_id=component_id,
                    reason=f"coverage_state:{coverage_state}",
                )
                direct_answer_blocked = True
            elif coverage_state not in _SATISFIED_COVERAGE_STATES:
                component_blockers.append("required_component_not_satisfied")
                _append_blocker(
                    blockers,
                    code="required_component_not_satisfied",
                    scope="component",
                    ref_id=component_id,
                    reason=f"coverage_state:{coverage_state or 'unknown'}",
                )
                direct_answer_blocked = True

            remaining_unknowns = _token_list(coverage.get("remaining_unknowns"))
            if remaining_unknowns:
                component_blockers.append("remaining_unknowns")
                _append_blocker(
                    blockers,
                    code="remaining_unknowns",
                    scope="component",
                    ref_id=component_id,
                )
                direct_answer_blocked = True

            followup_need = _normalized_token(coverage.get("followup_need"))
            if followup_need in _BLOCKING_FOLLOWUP_NEED:
                component_blockers.append("followup_need_required_or_blocked")
                _append_blocker(
                    blockers,
                    code="followup_need_required_or_blocked",
                    scope="component",
                    ref_id=component_id,
                    reason=f"followup_need:{followup_need}",
                )
                finalization_blocked = True

            source_obligation = _normalized_token(
                coverage.get("source_obligation_status")
            )
            if source_obligation in _BLOCKING_SOURCE_OBLIGATION:
                component_blockers.append("source_obligation_unsatisfied")
                _append_blocker(
                    blockers,
                    code="source_obligation_unsatisfied",
                    scope="component",
                    ref_id=component_id,
                    reason=f"source_obligation_status:{source_obligation}",
                )
                direct_answer_blocked = True

            content_availability = _normalized_token(
                coverage.get("content_availability_status")
            )
            if content_availability in _BLOCKING_CONTENT_AVAILABILITY:
                component_blockers.append("content_unavailable")
                _append_blocker(
                    blockers,
                    code="content_unavailable",
                    scope="component",
                    ref_id=component_id,
                    reason=f"content_availability_status:{content_availability}",
                )
                direct_answer_blocked = True

            evidence_custody = _normalized_token(coverage.get("evidence_custody_status"))
            if evidence_custody and evidence_custody != "custodied":
                component_blockers.append("evidence_not_custodied")
                _append_blocker(
                    blockers,
                    code="evidence_not_custodied",
                    scope="component",
                    ref_id=component_id,
                    reason=f"evidence_custody_status:{evidence_custody}",
                )
                direct_answer_blocked = True

            if _is_weak_only_evidence_basis(_list(coverage.get("evidence_basis"))):
                component_blockers.append("weak_only_evidence_basis")
                _append_blocker(
                    blockers,
                    code="weak_only_evidence_basis",
                    scope="component",
                    ref_id=component_id,
                )
                direct_answer_blocked = True

            if coverage_suspect:
                component_blockers.append("coverage_suspect_from_amendment")
                _append_blocker(
                    blockers,
                    code="coverage_suspect_from_amendment",
                    scope="component",
                    ref_id=component_id,
                )
                direct_answer_blocked = True

            required_caveats.extend(_token_list(coverage.get("required_caveats")))
            prohibited_upgrades.extend(_token_list(coverage.get("prohibited_upgrades")))

        summary["blockers"] = component_blockers
        component_summaries.append(summary)

    amendment_summaries: list[dict[str, Any]] = []
    candidate_new_contract_versions: list[str] = []

    for admission in contract_amendment_admission_history:
        if not isinstance(admission, Mapping):
            continue
        amendment_id = _clean_token(admission.get("amendment_record_id")) or ""
        disposition = _normalized_token(admission.get("disposition"))
        materiality = _normalized_token(admission.get("materiality"))
        user_confirmation = _normalized_token(admission.get("user_confirmation_posture"))
        weakening = _normalized_token(admission.get("weakening_posture"))
        rejection_reasons = _token_list(admission.get("rejection_reasons"))
        blocking_reasons = _token_list(admission.get("blocking_reasons"))
        candidate_version = _clean_token(admission.get("candidate_new_contract_version"))
        candidate_digest = _clean_token(admission.get("candidate_new_contract_digest"))
        if candidate_version:
            candidate_new_contract_versions.append(candidate_version)

        amendment_blockers: list[str] = []
        summary = {
            "amendment_record_id": amendment_id,
            "disposition": _clean_token(admission.get("disposition")),
            "materiality": _clean_token(admission.get("materiality")),
            "user_confirmation_posture": _clean_token(
                admission.get("user_confirmation_posture")
            ),
            "weakening_posture": _clean_token(admission.get("weakening_posture")),
            "blocking_reasons": blocking_reasons,
            "rejection_reasons": rejection_reasons,
            "candidate_invalidated_coverage_refs": [
                {
                    "coverage_record_id": _clean_token(item.get("coverage_record_id")),
                    "answer_component_id": _clean_token(item.get("answer_component_id")),
                    "represented_only": bool(item.get("represented_only", True)),
                }
                for item in _list(admission.get("candidate_invalidated_coverage_refs"))
                if isinstance(item, Mapping)
            ][:20],
            "candidate_new_contract_version": candidate_version,
            "candidate_new_contract_digest": candidate_digest,
            "candidate_only": True,
            "blockers": [],
        }

        if disposition in _BLOCKING_AMENDMENT_DISPOSITION or blocking_reasons:
            amendment_blockers.append("amendment_blocked")
            _append_blocker(
                blockers,
                code="amendment_blocked",
                scope="amendment",
                ref_id=amendment_id,
            )
            finalization_blocked = True
        elif disposition == "rejected":
            ordinary_rejection = bool(rejection_reasons) and all(
                any(reason.casefold().startswith(prefix) for prefix in _NON_BLOCKING_REJECTION_PREFIXES)
                or reason.casefold().startswith("rejected_")
                for reason in rejection_reasons
            )
            if not ordinary_rejection and rejection_reasons:
                pass
        else:
            needs_confirmation = (
                disposition in _CONFIRMATION_REQUIRED_DISPOSITION
                or user_confirmation == "requires_user_confirmation"
                or (
                    materiality == "material"
                    and user_confirmation not in _ALLOWED_USER_CONFIRMATION
                    and disposition not in {"rejected", "blocked"}
                )
            )
            if needs_confirmation and user_confirmation not in _ALLOWED_USER_CONFIRMATION:
                amendment_blockers.append("amendment_requires_confirmation")
                _append_blocker(
                    blockers,
                    code="amendment_requires_confirmation",
                    scope="amendment",
                    ref_id=amendment_id,
                )
                finalization_blocked = True

            if (
                weakening in _WEAKENING_POSTURES_REQUIRING_AUTHORITY
                and user_confirmation != "explicit_user_authority"
            ):
                amendment_blockers.append("amendment_weakening_without_authority")
                _append_blocker(
                    blockers,
                    code="amendment_weakening_without_authority",
                    scope="amendment",
                    ref_id=amendment_id,
                    reason=f"weakening_posture:{weakening}",
                )
                finalization_blocked = True

        required_caveats.extend(_token_list(admission.get("required_caveats")))
        prohibited_upgrades.extend(_token_list(admission.get("prohibited_upgrades")))
        summary["blockers"] = amendment_blockers
        amendment_summaries.append(summary)

    facts_core = {
        "schema_version": SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION,
        "accepted_contract_version": _clean_token(contract.get("accepted_contract_version")),
        "accepted_contract_digest": _clean_token(contract.get("accepted_contract_digest")),
        "required_component_count": len(required_refs),
        "covered_component_count": sum(
            1 for ref in required_refs if latest_coverage.get(_clean_token(ref.get("component_id")) or "")
        ),
        "component_summaries": component_summaries,
        "amendment_summaries": amendment_summaries,
        "blockers": blockers,
        "required_caveats": list(dict.fromkeys(required_caveats))[:_MAX_LIST_ITEMS],
        "prohibited_upgrades": list(dict.fromkeys(prohibited_upgrades))[:_MAX_LIST_ITEMS],
        "direct_answer_blocked": bool(direct_answer_blocked),
        "finalization_blocked": bool(finalization_blocked),
        "candidate_new_contract_versions": list(
            dict.fromkeys(candidate_new_contract_versions)
        ),
    }
    facts_core["semantic_state_facts_digest"] = _digest_json(
        {
            key: facts_core[key]
            for key in (
                "accepted_contract_digest",
                "component_summaries",
                "amendment_summaries",
                "blockers",
                "direct_answer_blocked",
                "finalization_blocked",
            )
        }
    )
    return facts_core


def evaluate_semantic_sufficiency_overlay(
    semantic_state_facts: Mapping[str, Any] | None,
) -> SemanticSufficiencyOverlay:
    """Evaluate deterministic semantic blockers from compact semantic facts."""

    facts = _mapping(semantic_state_facts)
    if not facts.get("accepted_contract_digest"):
        return SemanticSufficiencyOverlay()

    blockers = tuple(
        dict(item)
        for item in _list(facts.get("blockers"))
        if isinstance(item, Mapping)
    )[:_MAX_BLOCKERS]
    missing_assessments: list[dict[str, Any]] = []
    for blocker in blockers:
        code = _clean_token(blocker.get("code"))
        ref_id = _clean_token(blocker.get("ref_id"))
        scope = _normalized_token(blocker.get("scope"))
        if not code:
            continue
        requirement_kind = (
            "semantic_amendment" if scope == "amendment" else "semantic_component_coverage"
        )
        missing_assessments.append(
            {
                "requirement_id": f"semantic:{code}:{ref_id or 'global'}",
                "requirement_kind": requirement_kind,
                "component_id": ref_id if scope == "component" else None,
                "status": "missing",
                "reason": _clean_text(blocker.get("reason"), limit=260) or code,
            }
        )

    coverage_suspect_ids = tuple(
        dict.fromkeys(
            _clean_token(item.get("component_id"))
            for item in _list(facts.get("component_summaries"))
            if isinstance(item, Mapping) and item.get("coverage_suspect")
            and _clean_token(item.get("component_id"))
        )
    )
    candidate_versions = tuple(
        _clean_token(version)
        for version in _list(facts.get("candidate_new_contract_versions"))
        if _clean_token(version)
    )

    mandatory = tuple(_token_list(facts.get("required_caveats")))
    prohibited = tuple(_token_list(facts.get("prohibited_upgrades")))
    if facts.get("direct_answer_blocked"):
        prohibited = tuple(
            dict.fromkeys(
                (*prohibited, "do_not_upgrade_semantic_blocked_state_to_direct_answer")
            )
        )
    if facts.get("finalization_blocked"):
        prohibited = tuple(
            dict.fromkeys(
                (*prohibited, "do_not_finalize_while_semantic_amendment_or_coverage_blocks")
            )
        )

    return SemanticSufficiencyOverlay(
        blockers=blockers,
        missing_assessments=tuple(missing_assessments),
        mandatory_caveats=mandatory,
        prohibited_upgrades=prohibited,
        direct_answer_blocked=bool(facts.get("direct_answer_blocked")),
        finalization_blocked=bool(facts.get("finalization_blocked")),
        coverage_suspect_component_ids=coverage_suspect_ids,
        candidate_new_contract_versions=candidate_versions,
    )


def build_semantic_consumption_summary(
    semantic_state_facts: Mapping[str, Any] | None,
    *,
    overlay: SemanticSufficiencyOverlay | None = None,
) -> dict[str, Any]:
    """Build a compact semantic consumption summary for Sufficiency projection."""

    facts = _mapping(semantic_state_facts)
    evaluated = overlay or evaluate_semantic_sufficiency_overlay(facts)
    blocker_codes = tuple(
        dict.fromkeys(
            _clean_token(item.get("code"))
            for item in evaluated.blockers
            if isinstance(item, Mapping) and _clean_token(item.get("code"))
        )
    )
    return {
        "schema_version": SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION,
        "semantic_state_facts_digest": facts.get("semantic_state_facts_digest")
        or _digest_json(facts),
        "blocker_count": len(evaluated.blockers),
        "blocker_codes": list(blocker_codes),
        "direct_answer_blocked": bool(evaluated.direct_answer_blocked),
        "finalization_blocked": bool(evaluated.finalization_blocked),
        "required_caveats_merged_count": len(evaluated.mandatory_caveats),
        "prohibited_upgrades_merged_count": len(evaluated.prohibited_upgrades),
        "coverage_suspect_component_ids": list(evaluated.coverage_suspect_component_ids),
        "candidate_new_contract_versions": list(evaluated.candidate_new_contract_versions),
        "required_component_count": int(facts.get("required_component_count") or 0),
        "covered_component_count": int(facts.get("covered_component_count") or 0),
        "amendment_admission_count": len(_list(facts.get("amendment_summaries"))),
    }


def build_semantic_state_facts_summary(
    semantic_state_facts: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Compact summary of semantic facts for Sufficiency projection."""

    facts = _mapping(semantic_state_facts)
    blocker_codes = tuple(
        dict.fromkeys(
            _clean_token(item.get("code"))
            for item in _list(facts.get("blockers"))
            if isinstance(item, Mapping) and _clean_token(item.get("code"))
        )
    )
    return {
        "schema_version": SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION,
        "semantic_state_facts_digest": facts.get("semantic_state_facts_digest")
        or _digest_json(facts),
        "direct_answer_blocked": bool(facts.get("direct_answer_blocked")),
        "finalization_blocked": bool(facts.get("finalization_blocked")),
        "blocker_codes": list(blocker_codes),
        "required_component_count": int(facts.get("required_component_count") or 0),
        "covered_component_count": int(facts.get("covered_component_count") or 0),
        "amendment_admission_count": len(_list(facts.get("amendment_summaries"))),
    }


__all__ = [
    "SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION",
    "SemanticSufficiencyOverlay",
    "build_semantic_consumption_summary",
    "build_semantic_state_facts_for_sufficiency",
    "build_semantic_state_facts_summary",
    "evaluate_semantic_sufficiency_overlay",
]
