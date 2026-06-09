"""Runtime consumers for reduced RunAuthority search judgment projections."""

from __future__ import annotations

from typing import Any, Mapping

from core.run_authority_search_judgment import (
    RunSearchJudgmentDecision,
    clean_text,
    clean_token,
    safe_json,
)

_RECOVERY_DECISIONS = {
    RunSearchJudgmentDecision.CONTINUE_TARGETED_SEARCH.value,
    RunSearchJudgmentDecision.RECOVER_MISSING_OFFICIAL_CURRENT.value,
    RunSearchJudgmentDecision.RECOVER_MISSING_LEGAL_PRIMARY.value,
    RunSearchJudgmentDecision.RECOVER_MISSING_CANONICAL.value,
    RunSearchJudgmentDecision.RECOVER_MISSING_SOURCE_BOUND_NUMERIC.value,
    RunSearchJudgmentDecision.ESCALATE_EXISTING_PROVIDER_OR_DEPTH.value,
}
_REQUIRED_SOURCE_CLASS_RECOVERY_DECISIONS = {
    RunSearchJudgmentDecision.RECOVER_MISSING_OFFICIAL_CURRENT.value,
    RunSearchJudgmentDecision.RECOVER_MISSING_LEGAL_PRIMARY.value,
    RunSearchJudgmentDecision.RECOVER_MISSING_CANONICAL.value,
    RunSearchJudgmentDecision.RECOVER_MISSING_SOURCE_BOUND_NUMERIC.value,
}
_BLOCK_DECISIONS = {
    RunSearchJudgmentDecision.BLOCK_REDUNDANT_QUERY.value,
    RunSearchJudgmentDecision.STOP_INSUFFICIENT.value,
}
_SOURCE_CLASS_QUERY_HINTS = {
    "official_current_rules": "official current rules",
    "current_primary_or_official": "current primary official source",
    "legal_or_regulatory_text": "current legal primary text",
    "primary_source_documents": "canonical documentation",
    "archival_primary_text": "archival primary source",
    "canonical_docs": "canonical documentation",
    "source_bound_numeric": "official numeric source",
    "source_bound": "source-bound numeric fact",
}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_list(value: Any, *, limit: int = 160) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple)) else [value]
    out: list[str] = []
    for item in values:
        token = clean_token(item, limit=limit)
        if token and token not in out:
            out.append(token)
    return out


def _subject(
    *,
    query: str | None,
    core_topic: str | None,
    primary_entity: str | None,
) -> str:
    return (
        clean_text(core_topic, limit=120)
        or clean_text(primary_entity, limit=120)
        or clean_text(query, limit=120)
        or "subject"
    )


def _fallback_queries(
    source_classes: list[str],
    *,
    query: str | None,
    core_topic: str | None,
    primary_entity: str | None,
) -> list[str]:
    topic = _subject(query=query, core_topic=core_topic, primary_entity=primary_entity)
    out: list[str] = []
    for source_class in source_classes[:2]:
        hint = _SOURCE_CLASS_QUERY_HINTS.get(source_class, source_class)
        candidate = f"{topic} {hint}"
        if candidate not in out:
            out.append(candidate)
    return out


def _compact_projection_ref(projection: Mapping[str, Any]) -> dict[str, Any]:
    return safe_json(
        {
            "owner": projection.get("owner"),
            "judgment_id": projection.get("judgment_id"),
            "decision": projection.get("decision"),
            "classifications": projection.get("classifications", []),
            "target_source_classes": projection.get("target_source_classes", []),
            "validation_status": projection.get("validation_status"),
            "canonical_state": projection.get("canonical_state"),
            "trace_only": projection.get("trace_only"),
        }
    )


def _has_source_class_gap_signal(recommendation: Mapping[str, Any]) -> bool:
    return bool(
        recommendation.get("source_class_underfire_shadow")
        or recommendation.get("source_class_recovery_recommended")
        or recommendation.get("source_class_gap_candidates")
        or recommendation.get("missing_expected_source_classes")
    )


def apply_search_judgment_to_source_class_recovery_recommendation(
    recommendation: Mapping[str, Any] | None,
    *,
    search_judgment_projection: Mapping[str, Any] | None,
    query: str | None = None,
    core_topic: str | None = None,
    primary_entity: str | None = None,
) -> dict[str, Any]:
    """Promote/block source-class recovery from reduced RunKernel judgment."""

    out = _mapping(recommendation)
    projection = _mapping(search_judgment_projection)
    if projection.get("owner") != "RunKernel.RunAuthoritySearchJudgment":
        return out
    if projection.get("canonical_state") is not True:
        return out

    decision = clean_token(projection.get("decision")) or ""
    target_classes = _string_list(projection.get("target_source_classes"))
    recommended_queries = _string_list(projection.get("recommended_queries"), limit=220)
    ref = _compact_projection_ref(projection)
    signal_present = bool(
        out.get("run_authority_source_gap_signal_present")
        if "run_authority_source_gap_signal_present" in out
        else _has_source_class_gap_signal(out)
    )
    run_authority_required_gap_signal = bool(
        decision in _REQUIRED_SOURCE_CLASS_RECOVERY_DECISIONS and target_classes
    )
    effective_signal_present = bool(
        signal_present or run_authority_required_gap_signal
    )

    out["run_authority_search_judgment_ref"] = ref
    out["run_authority_search_judgment_consumed"] = True
    out["run_authority_source_gap_signal_present"] = effective_signal_present
    out["run_authority_required_gap_signal_present"] = (
        run_authority_required_gap_signal
    )
    trigger_fields = _string_list(out.get("source_class_recovery_trigger_fields"))
    if "run_authority_search_judgment" not in trigger_fields:
        trigger_fields.append("run_authority_search_judgment")
    out["source_class_recovery_trigger_fields"] = trigger_fields

    if decision in _RECOVERY_DECISIONS and target_classes and effective_signal_present:
        existing_classes = _string_list(out.get("missing_expected_source_classes"))
        for source_class in target_classes:
            if source_class not in existing_classes:
                existing_classes.append(source_class)
        queries = _string_list(out.get("source_class_recovery_queries"), limit=220)
        for candidate in recommended_queries or _fallback_queries(
            target_classes,
            query=query,
            core_topic=core_topic,
            primary_entity=primary_entity,
        ):
            if candidate not in queries:
                queries.append(candidate)
        out["source_class_recovery_recommended"] = True
        out["run_authority_search_judgment_promoted_recovery"] = True
        out["missing_expected_source_classes"] = existing_classes
        out["source_class_recovery_queries"] = queries[:2]
        out["source_class_recovery_query_count"] = len(queries[:2])
        existing_reason = clean_text(out.get("source_class_recovery_reason"), limit=220)
        reason_matches_target = bool(
            existing_reason
            and any(source_class in existing_reason for source_class in target_classes)
        )
        if not reason_matches_target:
            if decision == RunSearchJudgmentDecision.RECOVER_MISSING_LEGAL_PRIMARY.value:
                existing_reason = "answer_contract_legal_text_gap:" + ",".join(
                    target_classes
                )
            else:
                existing_reason = "missing_expected_source_class:" + ",".join(
                    target_classes
                )
        out["source_class_recovery_reason"] = existing_reason
        out["run_authority_search_judgment_reason"] = decision
        out["authority_lifecycle_required_recovery_allowed"] = True
        out["authority_lifecycle_recovery_source"] = "RunKernel.RunAuthoritySearchJudgment"
        out["authority_lifecycle_final_posture"] = None
        return safe_json(out)

    if decision == RunSearchJudgmentDecision.STOP_SATISFIED.value:
        out["source_class_recovery_recommended"] = False
        out["missing_expected_source_classes"] = []
        out["source_class_recovery_queries"] = []
        out["source_class_recovery_query_count"] = 0
        out["source_class_recovery_reason"] = (
            "run_authority_search_judgment:stop_satisfied"
        )
        out["authority_lifecycle_required_recovery_allowed"] = False
        return safe_json(out)

    if decision == RunSearchJudgmentDecision.STOP_INSUFFICIENT.value:
        existing_classes = _string_list(out.get("missing_expected_source_classes"))
        for source_class in target_classes:
            if source_class not in existing_classes:
                existing_classes.append(source_class)
        queries = _string_list(out.get("source_class_recovery_queries"), limit=220)
        if target_classes:
            for candidate in recommended_queries or _fallback_queries(
                target_classes,
                query=query,
                core_topic=core_topic,
                primary_entity=primary_entity,
            ):
                if candidate not in queries:
                    queries.append(candidate)
            out["source_class_recovery_recommended"] = True
            out["run_authority_search_judgment_promoted_recovery"] = True
            out["missing_expected_source_classes"] = existing_classes
            out["source_class_recovery_queries"] = queries[:2]
            out["source_class_recovery_query_count"] = len(queries[:2])
        blockers = list(out.get("authority_lifecycle_blockers") or [])
        blocker = {
            "source": "RunKernel.RunAuthoritySearchJudgment",
            "reason": "run_authority_stop_insufficient",
            "decision": decision,
        }
        if blocker not in blockers:
            blockers.append(blocker)
        existing_reason = clean_text(out.get("source_class_recovery_reason"), limit=220)
        out["source_class_recovery_blocked_by_run_authority"] = True
        out["source_class_recovery_reason"] = (
            existing_reason or f"run_authority_search_judgment:{decision}"
        )
        out["authority_lifecycle_blockers"] = blockers
        out["authority_lifecycle_required_recovery_allowed"] = False
        out["authority_lifecycle_final_posture"] = "insufficient_partial"
        out["insufficient_posture"] = _mapping(projection.get("insufficient_posture"))
        return safe_json(out)

    if (
        decision in _RECOVERY_DECISIONS
        and target_classes
        and not effective_signal_present
        and decision != RunSearchJudgmentDecision.RECOVER_MISSING_LEGAL_PRIMARY.value
        and str(out.get("source_class_recovery_reason") or "").startswith(
            "answer_contract_"
        )
    ):
        out["source_class_recovery_recommended"] = False
        out["missing_expected_source_classes"] = []
        out["source_class_recovery_queries"] = []
        out["source_class_recovery_query_count"] = 0
        out["source_class_recovery_blocked_by_run_authority"] = True
        out["source_class_recovery_reason"] = (
            "run_authority_search_judgment:no_source_class_gap_signal"
        )
        out["authority_lifecycle_required_recovery_allowed"] = False
        return safe_json(out)

    if decision in _BLOCK_DECISIONS:
        blockers = list(out.get("authority_lifecycle_blockers") or [])
        blocker_reason = (
            "run_authority_blocked_redundant_query"
            if decision == RunSearchJudgmentDecision.BLOCK_REDUNDANT_QUERY.value
            else "run_authority_stop_insufficient"
        )
        blocker = {
            "source": "RunKernel.RunAuthoritySearchJudgment",
            "reason": blocker_reason,
            "decision": decision,
        }
        if blocker not in blockers:
            blockers.append(blocker)
        out["source_class_recovery_recommended"] = False
        out["source_class_recovery_blocked_by_run_authority"] = True
        out["source_class_recovery_reason"] = (
            f"run_authority_search_judgment:{decision}"
        )
        out["authority_lifecycle_blockers"] = blockers
        out["authority_lifecycle_required_recovery_allowed"] = False
        if decision == RunSearchJudgmentDecision.STOP_INSUFFICIENT.value:
            out["authority_lifecycle_final_posture"] = "insufficient_partial"
            out["insufficient_posture"] = _mapping(
                projection.get("insufficient_posture")
            )
        return safe_json(out)

    rationale = str(projection.get("rationale") or "")
    existing_recovery_reason = str(out.get("source_class_recovery_reason") or "")
    if decision == RunSearchJudgmentDecision.DEFER_TO_EXISTING_LEGACY_COMPATIBILITY.value and (
        rationale.startswith("strong_source_class_lead_present")
        or (
            rationale == "generic_candidates_without_source_class_fit"
            and existing_recovery_reason.startswith("answer_contract_")
        )
    ):
        blockers = list(out.get("authority_lifecycle_blockers") or [])
        blocker = {
            "source": "RunKernel.RunAuthoritySearchJudgment",
            "reason": "run_authority_strong_lead_blocks_redundant_recovery",
            "decision": decision,
        }
        if blocker not in blockers:
            blockers.append(blocker)
        out["source_class_recovery_recommended"] = False
        out["missing_expected_source_classes"] = []
        out["source_class_recovery_queries"] = []
        out["source_class_recovery_query_count"] = 0
        out["source_class_recovery_blocked_by_run_authority"] = True
        out["source_class_recovery_reason"] = "run_authority_search_judgment:" + (
            "strong_source_class_lead"
            if rationale.startswith("strong_source_class_lead_present")
            else "generic_candidates_without_source_class_fit"
        )
        out["authority_lifecycle_blockers"] = blockers
        out["authority_lifecycle_required_recovery_allowed"] = False
        return safe_json(out)

    return safe_json(out)


__all__ = [
    "apply_search_judgment_to_source_class_recovery_recommendation",
]
