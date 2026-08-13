"""Version-bound component-gap authorization for existing QueryPlan queries.

This helper tags one already-existing query from one SearchJudgment component
gap. It does not construct SearchWorkPlan, allocate queries across a planning
carrier, or create new executable query text.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

SEARCH_WORK_QUERY_PLAN_CONSUMPTION_SCHEMA_VERSION = "search_work_query_plan_consumption_ag96e2_v1"

_COMPONENT_GAP_AUTHORIZING_DECISIONS = frozenset(
    {
        "continue_targeted_search",
        "recover_missing_canonical",
        "recover_missing_legal_primary",
        "recover_missing_official_current",
        "recover_missing_source_bound_numeric",
    }
)


def authorize_existing_query_by_version_bound_component_gap(
    *,
    existing_queries: Sequence[str],
    query_metadata: Mapping[str, Mapping[str, Any]],
    search_judgment_projection: Mapping[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], bool, str | None, str | None]:
    """Tag one already-existing query from one version-bound semantic gap."""

    queries = tuple(_clean_query(query) for query in existing_queries if _clean_query(query))
    return _apply_version_bound_component_gap_authority(
        queries,
        query_metadata,
        search_judgment_projection=search_judgment_projection,
    )


def _apply_version_bound_component_gap_authority(
    queries: Sequence[str],
    query_metadata: Mapping[str, Mapping[str, Any]],
    *,
    search_judgment_projection: Mapping[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], bool, str | None, str | None]:
    metadata = {
        _clean_query(query): dict(value)
        for query, value in query_metadata.items()
        if _clean_query(query) and isinstance(value, Mapping)
    }
    if not search_judgment_projection:
        return metadata, False, None, None
    gap, reason = _version_bound_component_gap(search_judgment_projection)
    if reason or not gap:
        return metadata, False, None, reason
    target_component = _normalize_component_id(gap["answer_component_id"])
    matches = [
        query
        for query in queries
        if _component_id_from_query_metadata(metadata.get(query, {}))
        == target_component
    ]
    if not matches:
        return metadata, False, None, "zero_existing_candidate_query_matches_component_gap"
    if len(matches) > 1:
        return metadata, False, None, "multiple_existing_candidate_queries_match_component_gap"
    query = matches[0]
    existing = metadata.setdefault(query, {})
    existing["version_bound_component_gap_authorized"] = True
    existing["version_bound_component_gap_authority"] = {
        "owner": "RunKernel.RunAuthoritySearchJudgment",
        "judgment_id": _clean_token(search_judgment_projection.get("judgment_id")),
        "accepted_contract_version": gap["accepted_contract_version"],
        "accepted_contract_digest": gap["accepted_contract_digest"],
        "answer_component_id": gap["answer_component_id"],
        "component_digest": gap["component_digest"],
        "semantic_gap_code": gap["semantic_gap_code"],
        "existing_candidate_query": query,
        "query_text_generated": False,
        "new_executable_query_text_generated": False,
    }
    return metadata, True, query, None


def _component_id_from_query_metadata(metadata: Mapping[str, Any]) -> str | None:
    accepted = metadata.get("accepted_component_ref")
    if isinstance(accepted, Mapping):
        component_id = _normalize_component_id(accepted.get("component_id"))
        if component_id:
            return component_id
    lineage = metadata.get("contributor_lineage")
    if isinstance(lineage, Sequence) and not isinstance(lineage, (str, bytes)):
        for item in lineage:
            if not isinstance(item, Mapping):
                continue
            component_id = _normalize_component_id(item.get("component_id"))
            if component_id:
                return component_id
    return _normalize_component_id(
        metadata.get("accepted_component_id")
        or metadata.get("search_work_component_id")
        or metadata.get("component_id")
    )


def _version_bound_component_gap(
    projection: Mapping[str, Any],
) -> tuple[dict[str, str] | None, str | None]:
    source = _mapping(projection)
    if source.get("owner") != "RunKernel.RunAuthoritySearchJudgment":
        return None, "search_judgment_projection_not_canonical"
    if source.get("canonical_state") is not True or source.get("trace_only") is not False:
        return None, "search_judgment_projection_not_canonical"
    if _clean_token(source.get("decision")) not in _COMPONENT_GAP_AUTHORIZING_DECISIONS:
        return None, "search_judgment_decision_does_not_authorize_component_gap_query"
    continuation = _mapping(source.get("continuation"))
    if "allowed" in continuation and continuation.get("allowed") is not True:
        return None, "search_judgment_decision_does_not_authorize_component_gap_query"
    gaps = [
        item for item in _sequence_of_mappings(source.get("gaps"))
        if _clean_token(item.get("semantic_gap_code"))
        == "missing_required_component_coverage"
    ]
    if not gaps:
        return None, "search_judgment_has_no_version_bound_component_gap"
    if len(gaps) > 1:
        return None, "search_judgment_has_multiple_version_bound_component_gaps"
    gap = gaps[0]
    required = {
        "accepted_contract_version": _clean_token(
            gap.get("accepted_contract_version")
        ),
        "accepted_contract_digest": _clean_token(
            gap.get("accepted_contract_digest"),
            limit=128,
        ),
        "answer_component_id": _clean_token(gap.get("answer_component_id")),
        "component_digest": _clean_token(gap.get("component_digest"), limit=128),
        "semantic_gap_code": _clean_token(gap.get("semantic_gap_code")),
    }
    if not all(required.values()):
        return None, "version_bound_component_gap_missing_identity"
    if _clean_token(gap.get("requirement_kind")) != "semantic_component_coverage":
        return None, "version_bound_component_gap_generic_kind_erases_identity"
    return {key: str(value) for key, value in required.items()}, None


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence_of_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _clean_query(value: Any) -> str:
    return " ".join(str(value or "").strip().split())[:300]


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _normalize_component_id(value: Any) -> str | None:
    token = _clean_token(value)
    if not token:
        return None
    return token.casefold().removeprefix("component:")


__all__ = [
    "SEARCH_WORK_QUERY_PLAN_CONSUMPTION_SCHEMA_VERSION",
    "authorize_existing_query_by_version_bound_component_gap",
]
