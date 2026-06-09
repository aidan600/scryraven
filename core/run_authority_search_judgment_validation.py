"""Deterministic validation and repair for RunAuthority search judgments."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

from core.run_authority_search_judgment import (
    RunSearchJudgment,
    RunSearchJudgmentDecision,
    RunSearchJudgmentInput,
    SearchContinuationProposal,
    SearchGapAssessment,
    SearchJudgmentClassification,
    SearchJudgmentMode,
    SearchJudgmentValidationResult,
    SearchJudgmentValidationStatus,
    SearchRedundancyAssessment,
    SearchSatisfactionAssessment,
    clean_text,
    clean_token,
    stable_hash,
)

_PROTECTED_KINDS = frozenset(
    {
        "official_current",
        "legal_primary",
        "canonical_docs",
        "source_bound_numeric",
        "user_document",
    }
)
_OFFICIAL_CURRENT_CLASSES = frozenset(
    {"official_current_rules", "current_primary_or_official"}
)
_LEGAL_CLASSES = frozenset({"legal_or_regulatory_text"})
_CANONICAL_CLASSES = frozenset(
    {"primary_source_documents", "archival_primary_text", "canonical_docs"}
)
_SOURCE_BOUND_CLASSES = frozenset({"source_bound_numeric", "source_bound"})
_WEAK_SOURCE_CLASSES = frozenset(
    {
        "reputable_secondary",
        "secondary",
        "secondary_analysis",
        "trusted_community",
        "social_signal",
        "social_or_forum",
        "community",
        "forum",
    }
)
_WEAK_SOURCE_TIERS = frozenset(
    {"secondary", "trusted_community", "social_or_forum", "community", "context"}
)
_STALE_SIGNALS = frozenset({"stale", "outdated", "historical", "not_current"})
_OFF_TOPIC_SIGNALS = ("off-topic", "off_topic", "off class", "wrong source")
_RECOVERY_DECISIONS = frozenset(
    {
        RunSearchJudgmentDecision.CONTINUE_TARGETED_SEARCH,
        RunSearchJudgmentDecision.RECOVER_MISSING_OFFICIAL_CURRENT,
        RunSearchJudgmentDecision.RECOVER_MISSING_LEGAL_PRIMARY,
        RunSearchJudgmentDecision.RECOVER_MISSING_CANONICAL,
        RunSearchJudgmentDecision.RECOVER_MISSING_SOURCE_BOUND_NUMERIC,
        RunSearchJudgmentDecision.ESCALATE_EXISTING_PROVIDER_OR_DEPTH,
    }
)
_DECISION_KIND = {
    RunSearchJudgmentDecision.RECOVER_MISSING_OFFICIAL_CURRENT: "official_current",
    RunSearchJudgmentDecision.RECOVER_MISSING_LEGAL_PRIMARY: "legal_primary",
    RunSearchJudgmentDecision.RECOVER_MISSING_CANONICAL: "canonical_docs",
    RunSearchJudgmentDecision.RECOVER_MISSING_SOURCE_BOUND_NUMERIC: (
        "source_bound_numeric"
    ),
}


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _string_list(value: Any) -> list[str]:
    out: list[str] = []
    for item in _list(value):
        token = clean_token(item)
        if token and token not in out:
            out.append(token)
    return out


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _requirement_id_key(value: Any) -> str | None:
    token = clean_token(value)
    if not token:
        return None
    return token.replace("-", "_")


def _required_contract_requirements(
    projection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for requirement in _list(projection.get("source_requirements")):
        if not isinstance(requirement, Mapping):
            continue
        strictness = clean_token(requirement.get("strictness"))
        kind = clean_token(requirement.get("requirement_kind")) or "general"
        required_class = clean_token(requirement.get("required_source_class"))
        required_tier = clean_token(requirement.get("required_source_tier"))
        required_currentness = clean_token(requirement.get("required_currentness"))
        protected = (
            kind in _PROTECTED_KINDS
            or required_tier in {"official", "primary", "canonical"}
            or required_currentness in {"current", "official_current"}
        )
        if strictness != "required" and not protected:
            continue
        req_id = clean_token(requirement.get("requirement_id"))
        if not req_id:
            continue
        out.append(
            {
                "requirement_id": req_id,
                "requirement_kind": kind,
                "required_source_class": required_class,
                "required_source_tier": required_tier,
                "required_currentness": required_currentness,
                "strictness": strictness,
            }
        )
    return out


def _ledger_requirement_status(
    projection: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for requirement in _list(projection.get("source_requirements")):
        if not isinstance(requirement, Mapping):
            continue
        req_id = clean_token(requirement.get("requirement_id"))
        if req_id:
            out[req_id] = dict(requirement)
            key = _requirement_id_key(req_id)
            if key:
                out[key] = dict(requirement)
    return out


def _budget_exhausted(budget: Mapping[str, Any]) -> bool:
    recovery_slot_available = bool(
        budget.get("source_class_recovery_slot_available")
        or budget.get("recovery_slot_available")
    )
    if bool(budget.get("budget_exhausted")):
        return not recovery_slot_available
    iteration = _int_value(budget.get("iteration") or budget.get("iterations_run"))
    max_iterations = _int_value(budget.get("max_iterations"))
    remaining = budget.get("remaining_budget")
    if remaining is not None and _int_value(remaining) <= 0:
        return not recovery_slot_available
    return (
        max_iterations > 0
        and iteration >= max_iterations
        and not recovery_slot_available
    )


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _candidate_records(projection: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in _list(projection.get("candidate_records"))
        if isinstance(item, Mapping)
    ]


def _retrieval_has_lower_tier_lead(judgment_input: RunSearchJudgmentInput) -> bool:
    observations = _mapping(judgment_input.retrieval_observations)
    counts = _mapping(observations.get("source_tier_counts"))
    weak_count = sum(
        _int_value(counts.get(key))
        for key in ("secondary", "trusted_community", "social_or_forum", "context")
    )
    strong_count = sum(
        _int_value(counts.get(key)) for key in ("official", "primary", "canonical")
    )
    return weak_count > 0 and strong_count <= 0


def _retrieval_result_count(judgment_input: RunSearchJudgmentInput) -> int:
    observations = _mapping(judgment_input.retrieval_observations)
    return _int_value(observations.get("result_count"))


def _requirement_links_by_candidate(
    projection: Mapping[str, Any],
) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for link in _list(projection.get("requirement_links")):
        if not isinstance(link, Mapping):
            continue
        candidate_id = clean_token(link.get("candidate_id"))
        requirement_id = clean_token(link.get("requirement_id"))
        if candidate_id and requirement_id:
            out.setdefault(candidate_id, set()).add(requirement_id)
            key = _requirement_id_key(requirement_id)
            if key:
                out.setdefault(candidate_id, set()).add(key)
    return out


def _candidate_is_lower_tier(candidate: Mapping[str, Any]) -> bool:
    source_class = clean_token(candidate.get("source_class"))
    source_tier = clean_token(candidate.get("source_tier"))
    eligible = candidate.get("eligible_for_stronger_obligation")
    return (
        bool(candidate.get("lower_tier"))
        or bool(candidate.get("contextual_only"))
        or source_class in _WEAK_SOURCE_CLASSES
        or source_tier in _WEAK_SOURCE_TIERS
        or eligible is False
    )


def _candidate_is_stale_or_off_topic(candidate: Mapping[str, Any]) -> bool:
    currentness = clean_token(
        candidate.get("currentness_signal") or candidate.get("currentness")
    )
    if currentness in _STALE_SIGNALS:
        return True
    reason = " ".join(
        str(
            candidate.get(key)
            or ""
        ).casefold()
        for key in ("disposition_reason", "reason", "proposal_disposition")
    )
    return any(signal in reason for signal in _OFF_TOPIC_SIGNALS)


def _candidate_is_strong_lead(
    candidate: Mapping[str, Any],
    requirement: Mapping[str, Any],
) -> bool:
    if _candidate_is_lower_tier(candidate) or _candidate_is_stale_or_off_topic(candidate):
        return False
    required_class = clean_token(requirement.get("required_source_class"))
    required_tier = clean_token(requirement.get("required_source_tier"))
    required_currentness = clean_token(requirement.get("required_currentness"))
    source_class = clean_token(candidate.get("source_class"))
    source_tier = clean_token(candidate.get("source_tier"))
    currentness = clean_token(
        candidate.get("currentness_signal") or candidate.get("currentness")
    )
    if required_class and source_class != required_class:
        if not (
            required_class == "official_current_rules"
            and source_tier in {"official", "primary", "canonical"}
        ):
            return False
    if required_tier and source_tier != required_tier:
        return False
    if required_currentness in {"current", "official_current"} and (
        currentness in _STALE_SIGNALS
    ):
        return False
    return bool(source_class or source_tier)


def _candidate_matches_requirement(
    candidate: Mapping[str, Any],
    requirement: Mapping[str, Any],
    *,
    linked_requirement_ids: set[str] | None = None,
) -> bool:
    candidate_req_id = clean_token(candidate.get("requirement_id"))
    req_id = clean_token(requirement.get("requirement_id"))
    req_key = _requirement_id_key(req_id)
    if (
        req_id
        and linked_requirement_ids
        and (req_id in linked_requirement_ids or req_key in linked_requirement_ids)
    ):
        return True
    if candidate_req_id and req_id and (
        candidate_req_id == req_id
        or _requirement_id_key(candidate_req_id) == req_key
    ):
        return True
    required_class = clean_token(requirement.get("required_source_class"))
    source_class = clean_token(candidate.get("source_class"))
    source_tier = clean_token(candidate.get("source_tier"))
    if (
        required_class == "official_current_rules"
        and source_tier in {"official", "primary", "canonical"}
    ):
        return True
    return bool(required_class and source_class and required_class == source_class)


def _gap_kind_for_requirement(requirement: Mapping[str, Any]) -> str:
    kind = clean_token(requirement.get("requirement_kind")) or "general"
    source_class = clean_token(requirement.get("required_source_class"))
    if kind == "legal_primary" or source_class in _LEGAL_CLASSES:
        return "legal_primary"
    if kind == "canonical_docs" or source_class in _CANONICAL_CLASSES:
        return "canonical_docs"
    if kind == "source_bound_numeric" or source_class in _SOURCE_BOUND_CLASSES:
        return "source_bound_numeric"
    if kind == "official_current" or source_class in _OFFICIAL_CURRENT_CLASSES:
        return "official_current"
    return kind


def _decision_for_gap(requirement: Mapping[str, Any]) -> RunSearchJudgmentDecision:
    kind = _gap_kind_for_requirement(requirement)
    if kind == "legal_primary":
        return RunSearchJudgmentDecision.RECOVER_MISSING_LEGAL_PRIMARY
    if kind == "canonical_docs":
        return RunSearchJudgmentDecision.RECOVER_MISSING_CANONICAL
    if kind == "source_bound_numeric":
        return RunSearchJudgmentDecision.RECOVER_MISSING_SOURCE_BOUND_NUMERIC
    if kind == "official_current":
        return RunSearchJudgmentDecision.RECOVER_MISSING_OFFICIAL_CURRENT
    return RunSearchJudgmentDecision.CONTINUE_TARGETED_SEARCH


def _decision_matches_gap(
    decision: RunSearchJudgmentDecision,
    gap: SearchGapAssessment,
) -> bool:
    expected = _DECISION_KIND.get(decision)
    if expected is None:
        return True
    return _gap_kind_for_requirement(gap.to_dict()) == expected


def _preferred_gap_classes(judgment_input: RunSearchJudgmentInput) -> tuple[str, ...]:
    helper = _mapping(judgment_input.helper_proposals)
    out: list[str] = []
    for source in (
        _mapping(helper.get("answer_contract")),
        _mapping(helper.get("source_class_recovery")),
    ):
        for key in (
            "unfulfilled_source_classes",
            "partial_source_classes",
            "missing_expected_source_classes",
            "source_class_gap_candidates",
            "unfulfilled_source_classes",
            "partial_source_classes",
        ):
            for item in _string_list(source.get(key)):
                if item not in out:
                    out.append(item)
    return tuple(out)


def _judgment_context_text(judgment_input: RunSearchJudgmentInput) -> str:
    query_facts = _mapping(judgment_input.query_facts)
    helper = _mapping(judgment_input.helper_proposals)
    parts: list[str] = []
    for source in (
        query_facts,
        _mapping(helper.get("answer_contract")),
        _mapping(helper.get("source_class_recovery")),
    ):
        for key in (
            "query_preview",
            "core_topic",
            "primary_entity",
            "intent",
            "query_type",
            "report_type",
            "answer_contract_family",
            "final_answer_posture",
        ):
            value = clean_text(source.get(key), limit=220)
            if value:
                parts.append(value)
    return " ".join(parts).casefold()


def _context_prefers_legal(judgment_input: RunSearchJudgmentInput) -> bool:
    text = _judgment_context_text(judgment_input)
    return any(
        token in text
        for token in (
            " act",
            "statut",
            "legal",
            "regulatory",
            "law",
            "jurisdiction",
            "ordinance",
            "code",
        )
    )


def _context_prefers_official_current(judgment_input: RunSearchJudgmentInput) -> bool:
    text = _judgment_context_text(judgment_input)
    return "official" in text or "current" in text or "rules" in text


def _target_source_classes(requirements: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    out: list[str] = []
    for requirement in requirements:
        source_class = clean_token(requirement.get("required_source_class"))
        if source_class and source_class not in out:
            out.append(source_class)
    return tuple(out)


def _query_for_source_class(source_class: str, payload: Mapping[str, Any]) -> str:
    query_facts = _mapping(payload.get("query_ref_facts"))
    subject = (
        clean_text(query_facts.get("core_topic"), limit=120)
        or clean_text(query_facts.get("primary_entity"), limit=120)
        or clean_text(query_facts.get("query_preview"), limit=120)
        or "subject"
    )
    phrase_by_class = {
        "official_current_rules": "official current rules",
        "current_primary_or_official": "current primary official source",
        "legal_or_regulatory_text": "current legal primary text",
        "primary_source_documents": "canonical documentation",
        "archival_primary_text": "archival primary source",
        "canonical_docs": "canonical documentation",
        "source_bound_numeric": "official numeric source",
        "source_bound": "source-bound numeric fact",
    }
    return f"{subject} {phrase_by_class.get(source_class, source_class)}"


def _helper_says_satisfied(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = clean_token(item)
            key_token = clean_token(key)
            if key_token in {"satisfied", "contract_satisfied"} and bool(item):
                return True
            if token in {
                "satisfied",
                "stop_satisfied",
                "proceed_to_synthesis",
                "finalize",
            }:
                return True
            if _helper_says_satisfied(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_helper_says_satisfied(item) for item in value)
    else:
        token = clean_token(value)
        return token in {"satisfied", "stop_satisfied", "proceed_to_synthesis"}
    return False


def _redundancy_from_input(
    judgment_input: RunSearchJudgmentInput,
    *,
    active_gap_classes: Sequence[str],
) -> SearchRedundancyAssessment:
    facts = _mapping(judgment_input.query_facts)
    helper = _mapping(judgment_input.helper_proposals.get("continuation_candidate"))
    proposed_signature = clean_token(
        facts.get("proposed_query_signature")
        or facts.get("candidate_query_signature")
        or helper.get("proposed_query_signature")
        or helper.get("query_signature")
    )
    prior_signatures = set(_string_list(facts.get("prior_query_signatures")))
    target_classes = _string_list(
        facts.get("target_source_classes")
        or facts.get("proposed_target_source_classes")
        or helper.get("target_source_classes")
    )
    helper_redundant = bool(
        facts.get("candidate_query_redundant") or helper.get("redundant")
    )
    duplicate = bool(proposed_signature and proposed_signature in prior_signatures)
    redundant = helper_redundant or duplicate
    targets_new_gap = bool(set(target_classes).intersection(set(active_gap_classes)))
    return SearchRedundancyAssessment(
        proposed_query_signature=proposed_signature,
        duplicate_of=proposed_signature if duplicate else None,
        targets_new_gap=targets_new_gap,
        target_source_classes=tuple(target_classes),
        redundant=redundant,
        blocked=bool(redundant and not targets_new_gap),
        reason=(
            "duplicate_query_without_new_source_class_target"
            if redundant and not targets_new_gap
            else (
                "similar_query_targets_active_source_class_gap"
                if redundant and targets_new_gap
                else None
            )
        ),
    )


def build_deterministic_search_judgment(
    judgment_input: RunSearchJudgmentInput,
) -> RunSearchJudgment:
    """Apply conservative deterministic RunAuthority search judgment."""

    contract = _mapping(judgment_input.contract_projection)
    ledger = _mapping(judgment_input.evidence_ledger_projection)
    payload = judgment_input.to_model_payload()
    requirements = _required_contract_requirements(contract)
    ledger_status = _ledger_requirement_status(ledger)
    candidates = _candidate_records(ledger)
    links_by_candidate = _requirement_links_by_candidate(ledger)
    retrieval_has_lower_tier_lead = _retrieval_has_lower_tier_lead(judgment_input)

    gaps: list[SearchGapAssessment] = []
    satisfied_ids: list[str] = []
    lower_tier_ids: list[str] = []
    stale_ids: list[str] = []
    strong_lead_ids: list[str] = []
    for requirement in requirements:
        req_id = clean_token(requirement.get("requirement_id")) or "requirement"
        status = clean_token(
            _mapping(
                ledger_status.get(req_id)
                or ledger_status.get(_requirement_id_key(req_id) or "")
            ).get("status")
        )
        if status == "satisfied":
            satisfied_ids.append(req_id)
            continue
        matching = [
            candidate
            for candidate in candidates
            if _candidate_matches_requirement(
                candidate,
                requirement,
                linked_requirement_ids=links_by_candidate.get(
                    clean_token(candidate.get("candidate_id")) or ""
                ),
            )
        ]
        if any(_candidate_is_lower_tier(candidate) for candidate in matching):
            lower_tier_ids.append(req_id)
        elif retrieval_has_lower_tier_lead and _gap_kind_for_requirement(requirement) in {
            "official_current",
            "legal_primary",
            "canonical_docs",
            "source_bound_numeric",
        }:
            lower_tier_ids.append(req_id)
        if any(_candidate_is_stale_or_off_topic(candidate) for candidate in matching):
            stale_ids.append(req_id)
        if any(_candidate_is_strong_lead(candidate, requirement) for candidate in matching):
            strong_lead_ids.append(req_id)
        gaps.append(
            SearchGapAssessment(
                requirement_id=req_id,
                requirement_kind=clean_token(requirement.get("requirement_kind"))
                or "general",
                required_source_class=clean_token(
                    requirement.get("required_source_class")
                ),
                required_source_tier=clean_token(requirement.get("required_source_tier")),
                required_currentness=clean_token(
                    requirement.get("required_currentness")
                ),
                status="unsatisfied",
                reason=(
                    "lower_tier_or_stale_candidate_only"
                    if req_id in lower_tier_ids or req_id in stale_ids
                    else "required_evidence_ledger_gap"
                ),
            )
        )

    active_gap_classes = _target_source_classes(
        [gap.to_dict() for gap in gaps]
    )
    redundancy = _redundancy_from_input(
        judgment_input,
        active_gap_classes=active_gap_classes,
    )
    helper_satisfied = _helper_says_satisfied(judgment_input.helper_proposals)
    classifications: list[str] = []
    helper_assessments: dict[str, Any] = {
        "helper_satisfied": helper_satisfied,
        "helper_authority": "advisory",
    }
    decision = RunSearchJudgmentDecision.DEFER_TO_EXISTING_LEGACY_COMPATIBILITY
    rationale = "ordinary_or_compatibility_path_without_required_source_gap"

    if not gaps:
        if requirements:
            classifications.append(SearchJudgmentClassification.CONTRACT_SATISFIED.value)
            decision = RunSearchJudgmentDecision.STOP_SATISFIED
            rationale = "all_required_evidence_ledger_requirements_satisfied"
            if helper_satisfied:
                classifications.append(
                    SearchJudgmentClassification.HELPER_ASSESSMENT_PROMOTED.value
                )
                helper_assessments["satisfaction_promoted"] = True
        satisfaction = SearchSatisfactionAssessment(
            contract_satisfied=bool(requirements),
            satisfied_requirement_ids=tuple(satisfied_ids),
            unsatisfied_requirement_ids=(),
            reason=rationale,
        )
        return RunSearchJudgment(
            judgment_id=f"search-judgment:{stable_hash(payload)[:16]}",
            decision=decision,
            classifications=tuple(classifications),
            contract_id=clean_token(contract.get("contract_id")),
            selected_template_ids=tuple(
                _string_list(contract.get("selected_template_ids"))
            ),
            satisfaction=satisfaction,
            gaps=(),
            redundancy=redundancy,
            continuation=SearchContinuationProposal(
                allowed=decision
                is RunSearchJudgmentDecision.DEFER_TO_EXISTING_LEGACY_COMPATIBILITY,
                reason=rationale,
            ),
            target_source_classes=(),
            helper_assessments=helper_assessments,
            rationale=rationale,
        )

    classifications.append(SearchJudgmentClassification.ACTIVE_REQUIRED_GAP.value)
    if lower_tier_ids:
        classifications.extend(
            [
                SearchJudgmentClassification.LOWER_TIER_LEAD_ONLY.value,
                SearchJudgmentClassification.USEFUL_LEAD_NEEDS_TARGETED_RECOVERY.value,
            ]
        )
    if stale_ids:
        classifications.append(
            SearchJudgmentClassification.STALE_OR_OFF_TOPIC_ONLY.value
        )
    if helper_satisfied:
        classifications.append(
            SearchJudgmentClassification.HELPER_ASSESSMENT_REJECTED.value
        )
        helper_assessments["satisfaction_rejected_reason"] = (
            "required_evidence_ledger_gaps_remain"
        )
    if redundancy.blocked:
        classifications.append(SearchJudgmentClassification.REDUNDANT_QUERY_BLOCKED.value)
        decision = RunSearchJudgmentDecision.BLOCK_REDUNDANT_QUERY
        rationale = "redundant_query_targets_no_active_new_source_class_gap"
    elif redundancy.redundant and redundancy.targets_new_gap:
        classifications.append(
            SearchJudgmentClassification.NEW_SOURCE_CLASS_TARGET_ALLOWED.value
        )

    exhausted = _budget_exhausted(judgment_input.budget)
    if exhausted:
        classifications.extend(
            [
                SearchJudgmentClassification.BUDGET_EXHAUSTED.value,
                SearchJudgmentClassification.INSUFFICIENT_BUT_ANSWERABLE_WITH_CAVEATS.value,
            ]
        )
        decision = RunSearchJudgmentDecision.STOP_INSUFFICIENT
        rationale = "budget_exhausted_with_required_evidence_ledger_gaps"
    elif decision not in {
        RunSearchJudgmentDecision.BLOCK_REDUNDANT_QUERY,
    }:
        preferred_classes = set(_preferred_gap_classes(judgment_input))
        selected_gap = gaps[0]
        if _context_prefers_legal(judgment_input):
            for gap in gaps:
                if _gap_kind_for_requirement(gap.to_dict()) == "legal_primary":
                    selected_gap = gap
                    break
        elif _context_prefers_official_current(judgment_input):
            for gap in gaps:
                if _gap_kind_for_requirement(gap.to_dict()) == "official_current":
                    selected_gap = gap
                    break
        if selected_gap is gaps[0]:
            for gap in gaps:
                if gap.required_source_class in preferred_classes:
                    selected_gap = gap
                    break
        if selected_gap.requirement_id in strong_lead_ids:
            decision = RunSearchJudgmentDecision.DEFER_TO_EXISTING_LEGACY_COMPATIBILITY
            rationale = (
                "strong_source_class_lead_present_without_required_ledger_custody"
            )
        elif (
            (candidates or _retrieval_result_count(judgment_input) > 0)
            and not lower_tier_ids
            and not stale_ids
            and not strong_lead_ids
        ):
            decision = RunSearchJudgmentDecision.DEFER_TO_EXISTING_LEGACY_COMPATIBILITY
            rationale = "generic_candidates_without_source_class_fit"
        else:
            decision = _decision_for_gap(selected_gap.to_dict())
            rationale = "required_source_class_gap_needs_targeted_recovery"

    target_classes = tuple(
        source_class
        for source_class in active_gap_classes
        if any(
            gap.required_source_class == source_class
            and _decision_matches_gap(decision, gap)
            for gap in gaps
        )
    )
    if decision in {
        RunSearchJudgmentDecision.DEFER_TO_EXISTING_LEGACY_COMPATIBILITY,
        RunSearchJudgmentDecision.BLOCK_REDUNDANT_QUERY,
        RunSearchJudgmentDecision.STOP_INSUFFICIENT,
    }:
        target_classes = active_gap_classes
    recommended_queries = tuple(
        _query_for_source_class(source_class, payload) for source_class in target_classes[:3]
    )
    satisfaction = SearchSatisfactionAssessment(
        contract_satisfied=False,
        satisfied_requirement_ids=tuple(satisfied_ids),
        unsatisfied_requirement_ids=tuple(gap.requirement_id for gap in gaps),
        lower_tier_only_requirement_ids=tuple(lower_tier_ids),
        stale_or_off_topic_requirement_ids=tuple(stale_ids),
        reason=rationale,
    )
    return RunSearchJudgment(
        judgment_id=f"search-judgment:{stable_hash(payload)[:16]}",
        decision=decision,
        classifications=tuple(dict.fromkeys(classifications)),
        contract_id=clean_token(contract.get("contract_id")),
        selected_template_ids=tuple(_string_list(contract.get("selected_template_ids"))),
        satisfaction=satisfaction,
        gaps=tuple(gaps),
        redundancy=redundancy,
        continuation=SearchContinuationProposal(
            proposed_query_signature=redundancy.proposed_query_signature,
            target_source_classes=target_classes,
            targets_new_gap=bool(redundancy.targets_new_gap),
            allowed=decision in _RECOVERY_DECISIONS
            and not redundancy.blocked
            and not exhausted,
            reason=rationale,
        ),
        target_source_classes=target_classes,
        recommended_queries=recommended_queries,
        helper_assessments=helper_assessments,
        insufficient_posture=(
            {
                "posture": "insufficient_partial",
                "reason": rationale,
                "required_gap_count": len(gaps),
            }
            if decision is RunSearchJudgmentDecision.STOP_INSUFFICIENT
            else {}
        ),
        rationale=rationale,
    )


def _has_required_gaps(deterministic: RunSearchJudgment) -> bool:
    return bool(deterministic.gaps)


def _candidate_unsafe_reason(
    candidate: RunSearchJudgment,
    *,
    deterministic: RunSearchJudgment,
) -> str | None:
    if (
        candidate.decision is RunSearchJudgmentDecision.STOP_SATISFIED
        and _has_required_gaps(deterministic)
    ):
        return "blocked_stop_satisfied_with_required_gaps"
    if candidate.satisfaction.contract_satisfied and _has_required_gaps(deterministic):
        return "blocked_contract_satisfied_with_required_gaps"
    if (
        candidate.decision is not RunSearchJudgmentDecision.BLOCK_REDUNDANT_QUERY
        and deterministic.decision is RunSearchJudgmentDecision.BLOCK_REDUNDANT_QUERY
    ):
        return "blocked_redundant_query_without_new_gap_target"
    if (
        candidate.decision is RunSearchJudgmentDecision.STOP_SATISFIED
        and deterministic.classifications
        and SearchJudgmentClassification.LOWER_TIER_LEAD_ONLY.value
        in deterministic.classifications
    ):
        return "blocked_lower_tier_satisfaction"
    if (
        candidate.decision is RunSearchJudgmentDecision.STOP_SATISFIED
        and SearchJudgmentClassification.STALE_OR_OFF_TOPIC_ONLY.value
        in deterministic.classifications
    ):
        return "blocked_stale_or_off_topic_satisfaction"
    if (
        any(
            gap.requirement_kind == "source_bound_numeric"
            for gap in deterministic.gaps
        )
        and candidate.decision is RunSearchJudgmentDecision.STOP_SATISFIED
    ):
        return "blocked_source_bound_numeric_unknown_as_supported"
    return None


def validate_or_repair_search_judgment(
    candidate: RunSearchJudgment | Mapping[str, Any] | None,
    *,
    deterministic_judgment: RunSearchJudgment,
    model_attempted: bool = False,
    prompt_hash: str | None = None,
    prompt_length: int = 0,
    provider: str | None = None,
    model: str | None = None,
    effort: str | None = None,
    use_reasoning: bool | None = None,
    fallback_reason: str | None = None,
) -> tuple[RunSearchJudgment, SearchJudgmentValidationResult]:
    """Validate a model judgment and fall back to deterministic authority safely."""

    if candidate is None:
        reason = fallback_reason or "missing_model_search_judgment"
        committed = replace(
            deterministic_judgment,
            mode=SearchJudgmentMode.FALLBACK,
            prompt_hash=prompt_hash,
            prompt_length=prompt_length,
            model_identity={
                "provider": provider,
                "model": model,
                "effort": effort,
                "use_reasoning": use_reasoning,
            },
        )
        return (
            committed,
            SearchJudgmentValidationResult(
                status=SearchJudgmentValidationStatus.FALLBACK,
                reasons=(reason,),
                fallback_used=True,
                model_attempted=model_attempted,
                deterministic_decision=deterministic_judgment.decision.value,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
            ),
        )
    try:
        model_judgment = (
            RunSearchJudgment.from_mapping(candidate)
            if isinstance(candidate, Mapping)
            else candidate
        )
    except Exception as exc:
        return validate_or_repair_search_judgment(
            None,
            deterministic_judgment=deterministic_judgment,
            model_attempted=model_attempted,
            prompt_hash=prompt_hash,
            prompt_length=prompt_length,
            provider=provider,
            model=model,
            effort=effort,
            use_reasoning=use_reasoning,
            fallback_reason=(
                fallback_reason or f"invalid_model_search_judgment:{type(exc).__name__}"
            ),
        )

    unsafe_reason = _candidate_unsafe_reason(
        model_judgment,
        deterministic=deterministic_judgment,
    )
    if unsafe_reason:
        committed = replace(
            deterministic_judgment,
            mode=SearchJudgmentMode.REPAIRED,
            prompt_hash=prompt_hash,
            prompt_length=prompt_length,
            model_identity={
                "provider": provider,
                "model": model,
                "effort": effort,
                "use_reasoning": use_reasoning,
            },
        )
        return (
            committed,
            SearchJudgmentValidationResult(
                status=SearchJudgmentValidationStatus.REPAIRED,
                reasons=(unsafe_reason,),
                fallback_used=True,
                model_attempted=model_attempted,
                deterministic_decision=deterministic_judgment.decision.value,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
            ),
        )

    committed = replace(
        model_judgment,
        mode=SearchJudgmentMode.SMART_MODEL_ADAPTED,
        contract_id=model_judgment.contract_id or deterministic_judgment.contract_id,
        selected_template_ids=(
            model_judgment.selected_template_ids
            or deterministic_judgment.selected_template_ids
        ),
        prompt_hash=prompt_hash,
        prompt_length=prompt_length,
        model_identity={
            "provider": provider,
            "model": model,
            "effort": effort,
            "use_reasoning": use_reasoning,
        },
    )
    return (
        committed,
        SearchJudgmentValidationResult(
            status=SearchJudgmentValidationStatus.VALID,
            model_attempted=model_attempted,
            deterministic_decision=deterministic_judgment.decision.value,
            prompt_hash=prompt_hash,
            prompt_length=prompt_length,
            provider=provider,
            model=model,
            effort=effort,
            use_reasoning=use_reasoning,
        ),
    )


__all__ = [
    "build_deterministic_search_judgment",
    "validate_or_repair_search_judgment",
]
