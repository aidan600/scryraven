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

from core.component_coverage_reduction_runtime import (
    ledger_qualification_blockers_for_satisfied_coverage,
)

SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION = (
    "sufficiency_semantic_state_consumption_ag_sem_09_v1"
)
SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION = (
    "sufficiency_semantic_ref_projection_ag_sem_proj_01_v1"
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
        "required_to_fulfill_existing_accepted_user_obligation",
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


def _append_unique_token(items: list[str], value: Any, *, limit: int = 160) -> None:
    token = _clean_token(value, limit=limit)
    if token and token not in items:
        items.append(token)


def _append_unique_mapping(items: list[dict[str, Any]], value: dict[str, Any]) -> None:
    if value and value not in items:
        items.append(value)


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


def _coverage_matches_accepted_component(
    coverage: Mapping[str, Any],
    *,
    accepted_contract_version: str | None,
    accepted_contract_digest: str | None,
    component_digest: str | None,
) -> bool:
    if not coverage:
        return False
    return (
        _clean_token(coverage.get("accepted_contract_version"))
        == accepted_contract_version
        and _clean_token(coverage.get("accepted_contract_digest"), limit=128)
        == accepted_contract_digest
        and _clean_token(coverage.get("component_digest"), limit=128)
        == component_digest
    )


def _coverage_safe_for_ref_projection(coverage: Mapping[str, Any]) -> bool:
    if coverage.get("canonical_state") is not True:
        return False
    if coverage.get("trace_only") is not False:
        return False
    if coverage.get("storage_only") is not False:
        return False
    if _normalized_token(coverage.get("coverage_state")) != "satisfied":
        return False
    if bool(coverage.get("stale")):
        return False
    if _normalized_token(coverage.get("conflict_posture")) not in {"none", "resolved"}:
        return False
    if _normalized_token(coverage.get("semantic_support_status")) != "supported":
        return False
    if _normalized_token(coverage.get("content_availability_status")) != "available":
        return False
    if _normalized_token(coverage.get("evidence_custody_status")) != "custodied":
        return False
    source_obligation = _normalized_token(coverage.get("source_obligation_status"))
    if source_obligation not in {"satisfied", "not_applicable"}:
        return False
    version_validity = _normalized_token(coverage.get("version_validity"))
    if version_validity and version_validity != "valid":
        return False
    if _token_list(coverage.get("remaining_unknowns")):
        return False
    if _normalized_token(coverage.get("followup_need")) in {"required", "blocked"}:
        return False
    if _is_weak_only_evidence_basis(_list(coverage.get("evidence_basis"))):
        return False
    if not _clean_token(coverage.get("coverage_record_id")):
        return False
    if not _clean_token(coverage.get("coverage_record_digest"), limit=128):
        return False

    content_bindings = [
        item for item in _list(coverage.get("content_reference_bindings")) if isinstance(item, Mapping)
    ]
    if not content_bindings:
        return False
    binding_ids: set[str] = set()
    for binding in content_bindings:
        content_ref_id = _clean_token(binding.get("content_ref_id"))
        if not content_ref_id:
            return False
        binding_ids.add(content_ref_id)
        if not _clean_token(binding.get("content_digest"), limit=128):
            return False
        if not _clean_token(binding.get("evidence_ref_id")):
            return False
        if binding.get("answer_bearing") is not True:
            return False
        if _normalized_token(binding.get("availability_status")) != "available":
            return False

    observation_refs = [
        item for item in _list(coverage.get("accepted_observation_refs")) if isinstance(item, Mapping)
    ]
    if not observation_refs:
        return False
    for observation in observation_refs:
        if observation.get("accepted") is False:
            return False
        if not _clean_token(observation.get("observation_id")):
            return False
        if not _clean_token(observation.get("observation_digest"), limit=128):
            return False
        observation_content_refs = _token_list(observation.get("content_refs"))
        if not observation_content_refs:
            return False
        for content_ref_id in observation_content_refs:
            if content_ref_id not in binding_ids:
                return False
    return True


def _build_semantic_ref_projection(
    *,
    accepted_contract: Mapping[str, Any],
    latest_coverage: Mapping[str, Mapping[str, Any]],
    required_component_ids: Sequence[str],
    semantic_state_facts_digest: str,
) -> dict[str, Any]:
    component_refs: list[dict[str, Any]] = []
    coverage_record_refs: list[dict[str, Any]] = []
    semantic_observation_refs: list[dict[str, Any]] = []
    sanitized_content_ref_ids: list[str] = []
    content_ref_digests: list[str] = []
    evidence_ids: list[str] = []
    semantic_source_ref_bindings: list[dict[str, Any]] = []
    source_obligation_refs: list[str] = []
    required_ids = [item for item in required_component_ids if item]
    safe_required_ids: set[str] = set()
    component_ref_index = {
        _clean_token(ref.get("component_id")): ref
        for ref in _list(accepted_contract.get("accepted_answer_component_refs"))
        if isinstance(ref, Mapping) and _clean_token(ref.get("component_id"))
    }

    for component_id in required_ids:
        coverage = _mapping(latest_coverage.get(component_id))
        component_ref = _mapping(component_ref_index.get(component_id))
        component_digest = _clean_token(component_ref.get("component_digest"), limit=128)
        if not (
            _coverage_matches_accepted_component(
                coverage,
                accepted_contract_version=_clean_token(
                    accepted_contract.get("accepted_contract_version")
                ),
                accepted_contract_digest=_clean_token(
                    accepted_contract.get("accepted_contract_digest"),
                    limit=128,
                ),
                component_digest=component_digest,
            )
            and _coverage_safe_for_ref_projection(coverage)
        ):
            continue
        safe_required_ids.add(component_id)
        if component_digest:
            _append_unique_mapping(
                component_refs,
                {
                    "component_id": component_id,
                    "component_digest": component_digest,
                },
            )

        coverage_record_id = _clean_token(coverage.get("coverage_record_id"))
        coverage_record_digest = _clean_token(
            coverage.get("coverage_record_digest"),
            limit=128,
        )
        _append_unique_mapping(
            coverage_record_refs,
            {
                "coverage_record_id": coverage_record_id,
                "coverage_record_digest": coverage_record_digest,
                "answer_component_id": component_id,
            },
        )

        for observation in _list(coverage.get("accepted_observation_refs")):
            if isinstance(observation, Mapping):
                _append_unique_mapping(
                    semantic_observation_refs,
                    {
                        "observation_id": _clean_token(observation.get("observation_id")),
                        "observation_digest": _clean_token(observation.get("observation_digest"), limit=128),
                    },
                )

        for binding in _list(coverage.get("content_reference_bindings")):
            if not isinstance(binding, Mapping):
                continue
            content_ref_id = _clean_token(binding.get("content_ref_id"))
            content_digest = _clean_token(binding.get("content_digest"), limit=128)
            evidence_ref_id = _clean_token(binding.get("evidence_ref_id"))
            _append_unique_token(sanitized_content_ref_ids, content_ref_id)
            _append_unique_token(content_ref_digests, content_digest, limit=128)
            _append_unique_token(evidence_ids, evidence_ref_id)
            if (
                evidence_ref_id
                and content_ref_id
                and content_digest
                and coverage_record_id
                and coverage_record_digest
                and component_digest
            ):
                _append_unique_mapping(
                    semantic_source_ref_bindings,
                    {
                        "origin_evidence_ref_id": evidence_ref_id,
                        "origin_evidence_ref_kind": "evidence_ledger_candidate",
                        "content_ref_id": content_ref_id,
                        "content_digest": content_digest,
                        "coverage_record_id": coverage_record_id,
                        "coverage_record_digest": coverage_record_digest,
                        "component_id": component_id,
                        "component_digest": component_digest,
                    },
                )

        ledger_binding = _mapping(coverage.get("evidence_ledger_binding"))
        for requirement_id in _token_list(ledger_binding.get("source_requirement_ids")):
            _append_unique_token(source_obligation_refs, requirement_id)

    available = bool(required_ids) and len(safe_required_ids) == len(set(required_ids))
    projection: dict[str, Any] = {
        "schema_version": SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
        "available": available,
        "semantic_state_facts_digest": _clean_token(semantic_state_facts_digest, limit=128),
        "accepted_contract_version": _clean_token(accepted_contract.get("accepted_contract_version")),
        "accepted_contract_digest": _clean_token(accepted_contract.get("accepted_contract_digest"), limit=128),
        "content_refs_available": bool(available and sanitized_content_ref_ids and content_ref_digests),
        "coverage_refs_available": bool(available and coverage_record_refs),
        "raw_content_included": False,
        "bounded_text_included": False,
        "prompt_visible": False,
        "author_payload_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
    }
    if component_refs:
        projection["component_refs"] = component_refs
    if coverage_record_refs:
        projection["coverage_record_refs"] = coverage_record_refs
    if semantic_observation_refs:
        projection["semantic_observation_refs"] = semantic_observation_refs
    if sanitized_content_ref_ids:
        projection["sanitized_content_ref_ids"] = sanitized_content_ref_ids
    if content_ref_digests:
        projection["content_ref_digests"] = content_ref_digests
    if evidence_ids:
        projection["evidence_ids"] = evidence_ids
    if semantic_source_ref_bindings:
        projection["semantic_source_ref_bindings"] = semantic_source_ref_bindings
    if source_obligation_refs:
        projection["source_obligation_refs"] = source_obligation_refs
    return projection


def _safe_semantic_ref_projection(value: Any) -> dict[str, Any]:
    projection = _mapping(value)
    if projection.get("schema_version") != SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION:
        return {}
    safe: dict[str, Any] = {
        "schema_version": SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
        "available": bool(projection.get("available")),
        "semantic_state_facts_digest": _clean_token(
            projection.get("semantic_state_facts_digest"),
            limit=128,
        ),
        "accepted_contract_version": _clean_token(projection.get("accepted_contract_version")),
        "accepted_contract_digest": _clean_token(projection.get("accepted_contract_digest"), limit=128),
        "content_refs_available": bool(projection.get("content_refs_available")),
        "coverage_refs_available": bool(projection.get("coverage_refs_available")),
        "raw_content_included": False,
        "bounded_text_included": False,
        "prompt_visible": False,
        "author_payload_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
    }

    component_refs = []
    for ref in _list(projection.get("component_refs")):
        if not isinstance(ref, Mapping):
            continue
        component_id = _clean_token(ref.get("component_id"))
        component_digest = _clean_token(ref.get("component_digest"), limit=128)
        if component_id and component_digest:
            component_refs.append({"component_id": component_id, "component_digest": component_digest})
    if component_refs:
        safe["component_refs"] = component_refs[:_MAX_LIST_ITEMS]

    coverage_refs = []
    for ref in _list(projection.get("coverage_record_refs")):
        if not isinstance(ref, Mapping):
            continue
        coverage_record_id = _clean_token(ref.get("coverage_record_id"))
        coverage_record_digest = _clean_token(ref.get("coverage_record_digest"), limit=128)
        answer_component_id = _clean_token(ref.get("answer_component_id"))
        if coverage_record_id and coverage_record_digest and answer_component_id:
            coverage_refs.append(
                {
                    "coverage_record_id": coverage_record_id,
                    "coverage_record_digest": coverage_record_digest,
                    "answer_component_id": answer_component_id,
                }
            )
    if coverage_refs:
        safe["coverage_record_refs"] = coverage_refs[:_MAX_LIST_ITEMS]

    observation_refs = []
    for ref in _list(projection.get("semantic_observation_refs")):
        if not isinstance(ref, Mapping):
            continue
        observation_id = _clean_token(ref.get("observation_id"))
        observation_digest = _clean_token(ref.get("observation_digest"), limit=128)
        if observation_id and observation_digest:
            observation_refs.append({"observation_id": observation_id, "observation_digest": observation_digest})
    if observation_refs:
        safe["semantic_observation_refs"] = observation_refs[:_MAX_LIST_ITEMS]

    for key in (
        "sanitized_content_ref_ids",
        "content_ref_digests",
        "evidence_ids",
        "source_obligation_refs",
    ):
        items = _token_list(projection.get(key), limit=128 if key.endswith("digests") else 160)
        if items:
            safe[key] = items[:_MAX_LIST_ITEMS]

    semantic_source_ref_bindings = []
    for ref in _list(projection.get("semantic_source_ref_bindings")):
        if not isinstance(ref, Mapping):
            continue
        origin_evidence_ref_id = _clean_token(ref.get("origin_evidence_ref_id"))
        origin_evidence_ref_kind = _clean_token(
            ref.get("origin_evidence_ref_kind")
            or "evidence_ledger_candidate",
            limit=120,
        )
        content_ref_id = _clean_token(ref.get("content_ref_id"))
        content_digest = _clean_token(ref.get("content_digest"), limit=128)
        coverage_record_id = _clean_token(ref.get("coverage_record_id"))
        coverage_record_digest = _clean_token(
            ref.get("coverage_record_digest"),
            limit=128,
        )
        component_id = _clean_token(ref.get("component_id"))
        component_digest = _clean_token(ref.get("component_digest"), limit=128)
        if (
            origin_evidence_ref_id
            and origin_evidence_ref_kind
            and content_ref_id
            and content_digest
            and coverage_record_id
            and coverage_record_digest
            and component_id
            and component_digest
        ):
            semantic_source_ref_bindings.append(
                {
                    "origin_evidence_ref_id": origin_evidence_ref_id,
                    "origin_evidence_ref_kind": origin_evidence_ref_kind,
                    "content_ref_id": content_ref_id,
                    "content_digest": content_digest,
                    "coverage_record_id": coverage_record_id,
                    "coverage_record_digest": coverage_record_digest,
                    "component_id": component_id,
                    "component_digest": component_digest,
                }
            )
    if semantic_source_ref_bindings:
        safe["semantic_source_ref_bindings"] = (
            semantic_source_ref_bindings[:_MAX_LIST_ITEMS]
        )
    return {key: value for key, value in safe.items() if value not in (None, "", [], {})}


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
    accepted_contract_version: str | None = None,
    accepted_contract_digest: str | None = None,
    component_digest: str | None = None,
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
    if accepted_contract_version:
        entry["accepted_contract_version"] = _clean_token(
            accepted_contract_version,
            limit=160,
        )
    if accepted_contract_digest:
        entry["accepted_contract_digest"] = _clean_token(
            accepted_contract_digest,
            limit=128,
        )
    if component_digest:
        entry["component_digest"] = _clean_token(component_digest, limit=128)
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
    current_answer_contract: Mapping[str, Any] | None = None,
    component_coverage_history: Sequence[Mapping[str, Any]],
    contract_amendment_admission_history: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any] | None = None,
    multicomponent_graph_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build compact semantic facts consumed by RunAuthority Sufficiency."""

    current_contract = _mapping(current_answer_contract)
    initial_contract = _mapping(initial_answer_contract)
    current_contract_consumed = bool(current_contract.get("accepted_contract_digest"))
    contract = current_contract if current_contract_consumed else initial_contract
    contract_source = (
        "current_answer_contract"
        if current_contract_consumed
        else "initial_answer_contract"
    )
    if not contract.get("accepted_contract_digest"):
        return {
            "schema_version": SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION,
            "accepted_contract_version": None,
            "accepted_contract_digest": None,
            "accepted_contract_source": None,
            "current_answer_contract_consumed": False,
            "required_component_count": 0,
            "covered_component_count": 0,
            "missing_component_count": 0,
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
    accepted_contract_version = _clean_token(contract.get("accepted_contract_version"))
    accepted_contract_digest = _clean_token(
        contract.get("accepted_contract_digest"),
        limit=128,
    )

    required_refs = [
        ref
        for ref in _list(contract.get("accepted_answer_component_refs"))
        if isinstance(ref, Mapping)
        and _normalized_token(ref.get("requirement_posture")) in _REQUIRED_POSTURE
    ]
    required_component_ids = [
        _clean_token(ref.get("component_id")) or ""
        for ref in required_refs
        if isinstance(ref, Mapping)
    ]
    accepted_required_component_refs = [
        {
            "answer_component_id": component_id,
            "component_digest": component_digest,
            "accepted_contract_version": accepted_contract_version,
            "accepted_contract_digest": accepted_contract_digest,
        }
        for ref in required_refs
        if (component_id := _clean_token(ref.get("component_id")))
        and (
            component_digest := _clean_token(ref.get("component_digest"), limit=128)
        )
    ]
    component_summaries: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    required_caveats: list[str] = []
    prohibited_upgrades: list[str] = []
    direct_answer_blocked = False
    finalization_blocked = False

    for ref in required_refs:
        component_id = _clean_token(ref.get("component_id")) or ""
        component_digest = _clean_token(ref.get("component_digest"), limit=128)
        raw_coverage = latest_coverage.get(component_id, {})
        coverage_identity_mismatch = bool(raw_coverage) and not (
            _coverage_matches_accepted_component(
                raw_coverage,
                accepted_contract_version=accepted_contract_version,
                accepted_contract_digest=accepted_contract_digest,
                component_digest=component_digest,
            )
        )
        coverage = {} if coverage_identity_mismatch else raw_coverage
        suspect_reasons = list(invalidation_suspects.get(component_id, []))
        coverage_record_id = _clean_token(
            (raw_coverage or {}).get("coverage_record_id")
            if coverage_identity_mismatch
            else coverage.get("coverage_record_id")
        )
        if coverage_record_id:
            suspect_reasons.extend(invalidation_suspects.get(coverage_record_id, []))
        if coverage_identity_mismatch:
            suspect_reasons.append("coverage_contract_identity_mismatch")
        coverage_suspect = bool(suspect_reasons)
        ledger_qualification_blockers: list[dict[str, str]] = []
        if coverage and isinstance(evidence_ledger_projection, Mapping):
            ledger_qualification_blockers = (
                ledger_qualification_blockers_for_satisfied_coverage(
                    coverage=coverage,
                    evidence_ledger_projection=evidence_ledger_projection,
                    accepted_component=ref,
                )
            )

        summary = {
            "component_id": component_id,
            "component_digest": component_digest,
            "accepted_contract_version": accepted_contract_version,
            "accepted_contract_digest": accepted_contract_digest,
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
            "ledger_qualification_status": (
                "blocked" if ledger_qualification_blockers else "qualified_or_not_applicable"
            ),
            "ledger_qualification_blockers": ledger_qualification_blockers[:10],
            "blockers": [],
        }
        component_blockers: list[str] = []

        if not coverage:
            if coverage_identity_mismatch:
                component_blockers.append("stale_or_orphan_component_coverage")
                _append_blocker(
                    blockers,
                    code="stale_or_orphan_component_coverage",
                    scope="component",
                    ref_id=component_id,
                    reason="coverage_identity_does_not_match_accepted_contract",
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
                )
            component_blockers.append("missing_required_component_coverage")
            _append_blocker(
                blockers,
                code="missing_required_component_coverage",
                scope="component",
                ref_id=component_id,
                reason="required_component_has_no_reduced_coverage",
                accepted_contract_version=accepted_contract_version,
                accepted_contract_digest=accepted_contract_digest,
                component_digest=component_digest,
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
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
                )
                finalization_blocked = True
            if coverage_state == "conflicted" or conflict_posture == "present":
                component_blockers.append("conflicted_coverage")
                _append_blocker(
                    blockers,
                    code="conflicted_coverage",
                    scope="component",
                    ref_id=component_id,
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
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
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
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
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
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
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
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
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
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
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
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
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
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
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
                )
                direct_answer_blocked = True

            if _is_weak_only_evidence_basis(_list(coverage.get("evidence_basis"))):
                component_blockers.append("weak_only_evidence_basis")
                _append_blocker(
                    blockers,
                    code="weak_only_evidence_basis",
                    scope="component",
                    ref_id=component_id,
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
                )
                direct_answer_blocked = True

            if coverage_suspect:
                component_blockers.append("coverage_suspect_from_amendment")
                _append_blocker(
                    blockers,
                    code="coverage_suspect_from_amendment",
                    scope="component",
                    ref_id=component_id,
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
                )
                direct_answer_blocked = True

            for ledger_blocker in ledger_qualification_blockers:
                code = _clean_token(ledger_blocker.get("code")) or (
                    "ledger_qualification_blocked"
                )
                component_blockers.append(code)
                _append_blocker(
                    blockers,
                    code=code,
                    scope="component",
                    ref_id=component_id,
                    reason=_clean_text(ledger_blocker.get("reason"), limit=260)
                    or "satisfied_coverage_lacks_current_ledger_qualification",
                    accepted_contract_version=accepted_contract_version,
                    accepted_contract_digest=accepted_contract_digest,
                    component_digest=component_digest,
                )
                direct_answer_blocked = True

            required_caveats.extend(_token_list(coverage.get("required_caveats")))
            prohibited_upgrades.extend(_token_list(coverage.get("prohibited_upgrades")))

        summary["blockers"] = component_blockers
        component_summaries.append(summary)

    # A ready, current ComponentWorkGraph V1 has independently revalidated the
    # exact admitted component set against the amended AnswerContract. Preserve
    # unchanged component findings across a monotonic add-component amendment
    # without pretending that their older coverage records were newly reduced.
    # This reconciliation is deliberately limited to the two identity-only
    # blockers; substantive coverage, custody, conflict, and source blockers
    # remain authoritative.
    graph = _mapping(multicomponent_graph_state)
    graph_contract_ref = _mapping(graph.get("accepted_contract_ref"))
    graph_current = (
        graph.get("owner") == "RunKernel.ComponentWorkGraphV1"
        and graph.get("canonical_state") is True
        and graph.get("graph_status") in {"ready", "ready_with_caveats"}
        and graph_contract_ref.get("accepted_contract_version")
        == accepted_contract_version
        and graph_contract_ref.get("accepted_contract_digest")
        == accepted_contract_digest
    )
    graph_admitted_components = {
        (
            _clean_token(node.get("component_id")),
            _clean_token(node.get("component_digest"), limit=128),
        )
        for node in _list(graph.get("component_nodes"))
        if isinstance(node, Mapping)
        and node.get("current") is True
        and node.get("stale") is not True
        and _normalized_token(node.get("admission_status"))
        in {"admitted", "admitted_with_caveats"}
    }
    reconciled_component_ids = {
        component_id
        for component_id, component_digest in graph_admitted_components
        if component_id
        and any(
            component_id == _clean_token(ref.get("component_id"))
            and component_digest
            == _clean_token(ref.get("component_digest"), limit=128)
            for ref in required_refs
        )
    } if graph_current else set()
    identity_only_blockers = {
        "stale_or_orphan_component_coverage",
        "missing_required_component_coverage",
    }
    if reconciled_component_ids:
        blockers = [
            blocker
            for blocker in blockers
            if not (
                _clean_token(blocker.get("ref_id")) in reconciled_component_ids
                and _clean_token(blocker.get("code")) in identity_only_blockers
            )
        ]
        for summary in component_summaries:
            if summary.get("component_id") not in reconciled_component_ids:
                continue
            remaining = [
                code
                for code in _token_list(summary.get("blockers"))
                if code not in identity_only_blockers
            ]
            if remaining:
                continue
            summary.update(
                {
                    "coverage_present": True,
                    "coverage_state": "satisfied",
                    "semantic_support_status": "supported",
                    "coverage_suspect": False,
                    "coverage_suspect_reasons": [],
                    "blockers": [],
                    "coverage_reconciliation_source": (
                        "current_ready_component_work_graph_v1"
                    ),
                }
            )
        direct_answer_blocked = any(
            _normalized_token(blocker.get("scope")) == "component"
            for blocker in blockers
        )

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

    covered_component_count = sum(
        1 for summary in component_summaries if summary.get("coverage_present")
    )
    facts_core = {
        "schema_version": SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION,
        "accepted_contract_version": _clean_token(contract.get("accepted_contract_version")),
        "accepted_contract_digest": _clean_token(contract.get("accepted_contract_digest")),
        "accepted_contract_source": contract_source,
        "current_answer_contract_consumed": current_contract_consumed,
        "required_component_count": len(required_refs),
        "covered_component_count": covered_component_count,
        "missing_component_count": max(0, len(required_refs) - covered_component_count),
        "accepted_required_component_refs": accepted_required_component_refs,
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
    facts_core["semantic_ref_projection"] = _build_semantic_ref_projection(
        accepted_contract=contract,
        latest_coverage=latest_coverage,
        required_component_ids=required_component_ids,
        semantic_state_facts_digest=facts_core["semantic_state_facts_digest"],
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
                "answer_component_id": ref_id if scope == "component" else None,
                "accepted_contract_version": _clean_token(
                    blocker.get("accepted_contract_version")
                    or facts.get("accepted_contract_version")
                ),
                "accepted_contract_digest": _clean_token(
                    blocker.get("accepted_contract_digest")
                    or facts.get("accepted_contract_digest"),
                    limit=128,
                ),
                "component_digest": _clean_token(
                    blocker.get("component_digest"),
                    limit=128,
                ),
                "semantic_gap_code": code,
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
    summary = {
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
        "missing_component_count": int(facts.get("missing_component_count") or 0),
        "amendment_admission_count": len(_list(facts.get("amendment_summaries"))),
    }
    semantic_ref_projection = _safe_semantic_ref_projection(facts.get("semantic_ref_projection"))
    if semantic_ref_projection:
        summary["semantic_ref_projection"] = semantic_ref_projection
    return summary


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
        "missing_component_count": int(facts.get("missing_component_count") or 0),
        "amendment_admission_count": len(_list(facts.get("amendment_summaries"))),
    }


__all__ = [
    "SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION",
    "SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION",
    "SemanticSufficiencyOverlay",
    "build_semantic_consumption_summary",
    "build_semantic_state_facts_for_sufficiency",
    "build_semantic_state_facts_summary",
    "evaluate_semantic_sufficiency_overlay",
]
