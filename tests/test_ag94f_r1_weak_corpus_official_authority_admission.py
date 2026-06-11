from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.official_canonical_recovery_execution_admission import (
    OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY,
    build_official_canonical_recovery_execution_admission,
)
from core.official_canonical_recovery_query_acquisition import (
    OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.official_source_obligation_candidate_visibility import (
    NOT_REQUIRED,
    REQUIRED,
    OfficialSourceObligationCandidateVisibilityFacts,
)
from core.run_controller import RunController
from core.source_class_recovery import (
    build_official_authority_acquisition_plan,
    build_source_class_recovery_recommendation,
)

_LEGAL_PRIMARY = "legal_or_regulatory_text"
_OFFICIAL_CURRENT = "official_current_rules"
_CANONICAL_PRIMARY = "primary_source_documents"

_US_LEGAL_TERMS = (
    "Federal Register",
    "CFR",
    "eCFR",
    "GovInfo",
    "Code of Federal Regulations",
)
_NEUTRAL_AUTHORITY_TERMS = (
    "official legal text",
    "regulation",
    "current regulatory source",
    "competent authority",
    "primary legal source",
    "approved list",
    "regulator guidance",
    "current rule",
)
_DANISH_LIVE_QUERY = (
    "What official legal or regulatory source currently lists which "
    "preservatives or additives are permitted in infant formula sold in "
    "Denmark? Answer from official/current regulatory sources if available."
)


def _facts(
    required_classes: tuple[str, ...],
    *,
    status: str = REQUIRED,
    query_previews: tuple[str, ...] = (),
) -> OfficialSourceObligationCandidateVisibilityFacts:
    return OfficialSourceObligationCandidateVisibilityFacts(
        question_type="ag94f_fixture",
        obligation_status=status,
        obligation_reason="fixture_required_strong_authority",
        obligation_source="synthetic_fixture",
        obligation_required_or_preferred=status,
        obligation_detected_by_runtime=True,
        obligation_trigger_terms=required_classes,
        required_source_classes=required_classes,
        candidate_query_visibility_status="visible" if query_previews else "none_visible",
        candidate_query_count=len(query_previews),
        candidate_query_previews=query_previews,
        candidate_query_official_intent_status=(
            "visible" if query_previews else "absent"
        ),
        candidate_official_source_visibility_status="not_visible",
        candidate_official_source_count=0,
        candidate_official_source_domain_previews=(),
        accepted_or_readable_visibility_status="not_visible",
        accepted_or_readable_official_source_count=0,
        final_evidence_survival_status="not_visible",
        final_citation_survival_status="not_visible",
        final_evidence_official_or_canonical_count=0,
        final_citation_official_or_canonical_count=0,
        likely_visibility_gap="no_official_candidate_visible",
    )


def _recommendation(
    source_class: str,
    queries: tuple[str, ...],
    *,
    recommended: bool = True,
    reason: str | None = None,
    weak_blockers: bool = True,
    satisfaction_status: str = "unsatisfied",
) -> dict[str, Any]:
    blockers = (
        ["weak_corpus_recovery_owns_path", "blocked_by_corpus_weak"]
        if weak_blockers
        else []
    )
    return {
        "source_class_recovery_recommended": recommended,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [source_class] if source_class else [],
        "source_class_recovery_reason": (
            reason
            if reason is not None
            else f"missing_expected_source_class:{source_class}"
        ),
        "source_class_recovery_queries": list(queries),
        "source_class_recovery_query_count": len(queries),
        "source_class_recovery_trigger_fields": [
            "query",
            "source_tier_counts",
            "source_domain_counts",
            "official_evidence_found",
        ],
        "source_class_satisfaction_status": {source_class: satisfaction_status}
        if source_class
        else {},
        "source_class_strong_satisfaction_counts": {source_class: 0}
        if source_class
        else {},
        "active_source_class_recovery_blockers": list(blockers),
        "source_class_recovery_candidate_v2_blockers": list(blockers),
    }


def _runtime(
    source_class: str,
    queries: tuple[str, ...],
    *,
    corpus_weak: bool = True,
    weak_corpus_recovery_used: bool = True,
    terminal_stop_approved: bool = False,
    conflict_resolution_owns_path: bool = False,
    provider_policy_reusable: bool = True,
    search_depth_reusable: bool = True,
) -> dict[str, Any]:
    return {
        "query_preview": _DANISH_LIVE_QUERY,
        "core_topic": "infant formula additives",
        "primary_entity": "infant formula sold in Denmark",
        "corpus_weak": corpus_weak,
        "weak_corpus_recovery_used": weak_corpus_recovery_used,
        "terminal_stop_approved": terminal_stop_approved,
        "conflict_resolution_owns_path": conflict_resolution_owns_path,
        "provider_policy_reusable": provider_policy_reusable,
        "search_depth_reusable": search_depth_reusable,
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": [source_class] if source_class else [],
        "source_class_recovery_queries": list(queries),
        "source_class_recovery_query_count": len(queries),
        "source_class_recovery_reason": (
            f"missing_expected_source_class:{source_class}" if source_class else None
        ),
    }


def _admission_payload(
    *,
    source_class: str,
    queries: tuple[str, ...],
    recommendation: dict[str, Any] | None = None,
    runtime_trace: dict[str, Any] | None = None,
    existing_blockers: tuple[str, ...] = (
        "weak_corpus_recovery_owns_path",
        "blocked_by_corpus_weak",
    ),
    facts: OfficialSourceObligationCandidateVisibilityFacts | None = None,
    prior_recovery_attempt_count: int = 0,
    max_recovery_attempts: int = 1,
) -> dict[str, Any]:
    result = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation or _recommendation(source_class, queries),
        runtime_trace=runtime_trace or _runtime(source_class, queries),
        obligation_facts=facts or _facts((source_class,), query_previews=queries),
        existing_blockers=existing_blockers,
        prior_recovery_attempt_count=prior_recovery_attempt_count,
        max_recovery_attempts=max_recovery_attempts,
        ordinary_iteration_budget_remaining=1,
    )
    return result.trace["OfficialCanonicalRecoveryExecutionAdmission"]


def _joined(values: Any) -> str:
    if isinstance(values, dict):
        values = values.values()
    if isinstance(values, str):
        values = (values,)
    return " ".join(str(value) for value in values or ())


def _assert_no_us_legal_terms(text: str) -> None:
    folded = text.casefold()
    for term in _US_LEGAL_TERMS:
        assert term.casefold() not in folded


def _answer_contract_result() -> SimpleNamespace:
    return SimpleNamespace(
        adapter_result=None,
        state=SimpleNamespace(
            evidence_state_summary=SimpleNamespace(source_classes_missing=())
        ),
        fulfillment_handoff=SimpleNamespace(unfulfilled_items=(), partial_items=()),
    )


def _orchestrator_state(
    *,
    query: str = _DANISH_LIVE_QUERY,
    recommendation: dict[str, Any] | None = None,
    source_class_observability: dict[str, Any] | None = None,
    corpus_weak: bool = True,
    weak_corpus_recovery_used: bool = True,
) -> dict[str, Any]:
    return {
        "query": query,
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
        "core_topic": (
            "preservatives and additives permitted in infant formula sold in Denmark"
        ),
        "primary_entity": "infant formula sold in Denmark",
        "_source_class_recovery_lifecycle_recommendation": recommendation
        if recommendation is not None
        else _recommendation(
            _LEGAL_PRIMARY,
            (
                "infant formula additives official legal text current regulatory "
                "source competent authority",
            ),
        ),
        "_source_class_recovery_answer_contract_observability": (
            source_class_observability
            if source_class_observability is not None
            else {
                "source_class_satisfaction_status": {
                    _LEGAL_PRIMARY: "expected_but_only_secondary"
                },
                "source_class_strong_satisfaction_counts": {_LEGAL_PRIMARY: 0},
            }
        ),
        "_source_tier_recovery_lifecycle": {
            "source_tier_counts": {"secondary": 3},
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        "_source_domain_recovery_lifecycle": {
            "source_domain_counts": {"trade.example": 2, "manufacturer.example": 1},
            "top_source_domains": [{"domain": "trade.example", "count": 2}],
            "unique_source_domain_count": 2,
            "on_domain_source_count": 0,
            "off_domain_source_count": 2,
        },
        "_pre_recovery_answer_contract_result": _answer_contract_result(),
        "corpus_state": "OFF_TOPIC" if corpus_weak else "HEALTHY",
        "corpus_weak": corpus_weak,
        "weak_corpus_recovery_considered": corpus_weak,
        "weak_corpus_recovery_used": weak_corpus_recovery_used,
        "weak_corpus_recovery_skip_reason": (
            "weak_corpus_recovery_used" if weak_corpus_recovery_used else None
        ),
        "evidence_integration_checkpoint_trace": {},
        "current_search_depth_for_recovery": "basic",
        "iterations_run": 0,
        "max_iterations": 1,
        "waste_flags": [],
    }


def _handoff(**overrides: Any) -> Any:
    return build_authoritative_source_action_orchestrator_handoff(
        RunController(),
        orchestrator_state=_orchestrator_state(**overrides),
    )


def _export(handoff: Any) -> dict[str, Any]:
    trace = dict(handoff.active_source_class_recovery_lifecycle)
    if handoff.official_canonical_recovery_query_acquisition_trace:
        trace[OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY] = (
            handoff.official_canonical_recovery_query_acquisition_trace
        )
    if handoff.official_canonical_recovery_execution_admission_trace:
        trace[OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY] = (
            handoff.official_canonical_recovery_execution_admission_trace
        )
    return build_official_canonical_recovery_visibility_export(trace)


def test_weak_corpus_does_not_block_unsatisfied_legal_regulatory_recovery() -> None:
    queries = (
        "infant formula additives official legal text current regulatory source",
        "infant formula additives competent authority primary legal source",
    )

    admission = _admission_payload(source_class=_LEGAL_PRIMARY, queries=queries)

    assert admission["admission_considered"] is True
    assert admission["admission_eligible"] is True
    assert admission["admission_used"] is True
    assert admission["source_class_recovery_execution_admitted"] is True
    assert "weak_corpus_recovery_owns_path" not in admission["admission_blockers"]
    assert "blocked_by_corpus_weak" not in admission["admission_blockers"]
    assert admission["weak_corpus_coexistence_reason"] is not None


def test_weak_corpus_does_not_block_unsatisfied_official_current_recovery() -> None:
    queries = (
        "benefit threshold current regulatory source official requirements",
        "benefit threshold regulator guidance current rule",
    )

    admission = _admission_payload(source_class=_OFFICIAL_CURRENT, queries=queries)

    assert admission["admission_eligible"] is True
    assert admission["admission_used"] is True
    assert admission["admission_blockers"] == []


def test_weak_corpus_does_not_block_unsatisfied_canonical_primary_recovery_if_lane_supports_it() -> None:
    queries = (
        "package cache option official documentation reference manual",
        "package cache option reference documentation official docs",
    )

    runtime = _runtime(_CANONICAL_PRIMARY, queries)
    runtime["authority_lifecycle_required_recovery_allowed"] = True

    admission = _admission_payload(
        source_class=_CANONICAL_PRIMARY,
        queries=queries,
        runtime_trace=runtime,
    )

    assert admission["admission_eligible"] is True
    assert admission["admission_used"] is True
    assert admission["required_source_classes"] == [_CANONICAL_PRIMARY]
    assert admission["unsatisfied_required_source_classes"] == [_CANONICAL_PRIMARY]


def test_weak_corpus_still_blocks_when_no_stronger_source_obligation_exists() -> None:
    admission = _admission_payload(
        source_class="",
        queries=("ordinary explainer secondary context",),
        recommendation=_recommendation("", ("ordinary explainer secondary context",)),
        runtime_trace=_runtime("", ("ordinary explainer secondary context",)),
        facts=_facts((), status=NOT_REQUIRED),
    )

    assert admission["admission_eligible"] is False
    assert admission["admission_used"] is False
    assert admission["admission_skip_reason"] == "obligation_not_required"
    assert "weak_corpus_recovery_owns_path" in admission["admission_blockers"]


def test_weak_corpus_with_official_obligation_but_no_recovery_queries_remains_ineligible() -> None:
    admission = _admission_payload(source_class=_LEGAL_PRIMARY, queries=())

    assert admission["admission_eligible"] is False
    assert admission["admission_used"] is False
    assert admission["recovery_query_available"] is False
    assert "weak_corpus_recovery_owns_path" in admission["admission_blockers"]


def test_terminal_stop_still_blocks_official_recovery() -> None:
    queries = ("infant formula official legal text current regulatory source",)
    admission = _admission_payload(
        source_class=_LEGAL_PRIMARY,
        queries=queries,
        runtime_trace=_runtime(
            _LEGAL_PRIMARY,
            queries,
            terminal_stop_approved=True,
        ),
    )

    assert admission["admission_eligible"] is False
    assert admission["admission_used"] is False
    assert "terminal_stop_approved" in admission["admission_blockers"]


def test_hard_budget_exhaustion_still_blocks_official_recovery() -> None:
    admission = _admission_payload(
        source_class=_LEGAL_PRIMARY,
        queries=("infant formula official legal text current regulatory source",),
        existing_blockers=("budget_hard_exhausted",),
    )

    assert admission["admission_eligible"] is False
    assert admission["admission_used"] is False
    assert "budget_hard_exhausted" in admission["admission_blockers"]


def test_existing_attempt_cap_still_blocks_official_recovery() -> None:
    admission = _admission_payload(
        source_class=_LEGAL_PRIMARY,
        queries=("infant formula official legal text current regulatory source",),
        existing_blockers=("already_attempted",),
        prior_recovery_attempt_count=1,
        max_recovery_attempts=1,
    )

    assert admission["admission_eligible"] is False
    assert admission["admission_used"] is False
    assert "already_attempted" in admission["admission_blockers"]
    assert "budget_hard_exhausted" in admission["admission_blockers"]


def test_conflict_resolution_still_blocks_official_recovery() -> None:
    queries = ("infant formula official legal text current regulatory source",)
    admission = _admission_payload(
        source_class=_LEGAL_PRIMARY,
        queries=queries,
        runtime_trace=_runtime(
            _LEGAL_PRIMARY,
            queries,
            conflict_resolution_owns_path=True,
        ),
    )

    assert admission["admission_eligible"] is False
    assert "conflict_resolution_owns_path" in admission["admission_blockers"]


def test_acquisition_path_visible_from_generic_source_class_recovery_recommendation() -> None:
    queries = (
        "infant formula additives official legal text current regulatory source",
    )
    recommendation = _recommendation(
        _LEGAL_PRIMARY,
        queries,
        reason=f"missing_expected_source_class:{_LEGAL_PRIMARY}",
    )
    recommendation.pop("official_canonical_acquisition_path_visible", None)

    admission = _admission_payload(
        source_class=_LEGAL_PRIMARY,
        queries=queries,
        recommendation=recommendation,
    )

    assert admission["admission_acquisition_path_visible"] is True
    assert admission["admission_used"] is True


def test_ordinary_explainer_control_does_not_trigger_official_recovery() -> None:
    rec = build_source_class_recovery_recommendation(
        query="Explain why coffee tastes bitter in simple terms.",
        current_date="2026-06-11",
        intent="general",
        report_type="general_research",
        query_type="other",
        core_topic="coffee bitterness explainer",
        primary_entity="coffee bitterness",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"science.example": 1},
        top_source_domains=[{"domain": "science.example", "count": 1}],
        official_evidence_found=False,
    )

    assert rec["source_class_recovery_recommended"] is False
    assert rec["missing_expected_source_classes"] == []


def test_secondary_only_evidence_does_not_satisfy_stronger_obligation() -> None:
    queries = ("infant formula additives official legal text current regulatory source",)
    admission = _admission_payload(
        source_class=_LEGAL_PRIMARY,
        queries=queries,
        recommendation=_recommendation(
            _LEGAL_PRIMARY,
            queries,
            satisfaction_status="expected_but_only_secondary",
        ),
    )

    assert admission["unsatisfied_required_source_classes"] == [_LEGAL_PRIMARY]
    assert admission["admission_used"] is True


def test_non_us_legal_regulatory_recovery_query_does_not_inject_us_legal_sources_without_us_context() -> None:
    rec = build_source_class_recovery_recommendation(
        query=(
            "What official legal or regulatory text currently lists approved "
            "preservatives and additives in Danish baby formula?"
        ),
        current_date="2026-06-11",
        intent="general",
        report_type="general_research",
        query_type="other",
        core_topic="Danish infant formula additives approved list",
        primary_entity="infant formula additives",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"trade.example": 1},
        top_source_domains=[{"domain": "trade.example", "count": 1}],
        official_evidence_found=False,
    )
    plan = build_official_authority_acquisition_plan(
        source_classes=(_LEGAL_PRIMARY,),
        subject="infant formula additives",
        context_text=(
            "What official legal or regulatory text currently lists approved "
            "preservatives and additives in Danish baby formula?"
        ),
        max_query_variants=3,
    )

    assert rec["missing_expected_source_classes"] == [_LEGAL_PRIMARY]
    _assert_no_us_legal_terms(_joined(rec["source_class_recovery_queries"]))
    _assert_no_us_legal_terms(_joined(plan["query_variants"]))
    assert rec.get("source_class_recovery_official_domains") in (None, [])
    assert plan["hard_domains"] == []


def test_jurisdiction_neutral_legal_regulatory_recovery_query_uses_neutral_authority_terms() -> None:
    rec = build_source_class_recovery_recommendation(
        query=(
            "What official legal or regulatory text currently lists approved "
            "additives for infant formula?"
        ),
        current_date="2026-06-11",
        intent="general",
        report_type="general_research",
        query_type="other",
        core_topic="infant formula additives approved list",
        primary_entity="infant formula additives",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"trade.example": 1},
        top_source_domains=[{"domain": "trade.example", "count": 1}],
        official_evidence_found=False,
    )
    query_text = _joined(rec["source_class_recovery_queries"]).casefold()

    _assert_no_us_legal_terms(query_text)
    assert any(term in query_text for term in _NEUTRAL_AUTHORITY_TERMS)
    assert "approved list" in query_text


def test_us_legal_regulatory_recovery_query_may_include_us_legal_sources_when_us_context() -> None:
    rec = build_source_class_recovery_recommendation(
        query=(
            "What U.S. legal or regulatory text currently lists "
            "approved additives for infant formula?"
        ),
        current_date="2026-06-11",
        intent="general",
        report_type="general_research",
        query_type="other",
        core_topic="U.S. infant formula additives approved list",
        primary_entity="infant formula additives",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"trade.example": 1},
        top_source_domains=[{"domain": "trade.example", "count": 1}],
        official_evidence_found=False,
    )
    query_text = _joined(rec["source_class_recovery_queries"])

    assert rec["missing_expected_source_classes"] == [_LEGAL_PRIMARY]
    assert any(term.casefold() in query_text.casefold() for term in _US_LEGAL_TERMS)
    assert rec.get("source_class_recovery_official_domains")


def test_danish_baby_formula_live_shape_admission_becomes_used_without_domain_registry() -> None:
    handoff = _handoff(
        query=_DANISH_LIVE_QUERY,
        recommendation=build_source_class_recovery_recommendation(
            query=_DANISH_LIVE_QUERY,
            current_date="2026-06-11",
            intent="general",
            report_type="general_research",
            query_type="other",
            core_topic=(
                "preservatives and additives permitted in infant formula sold in Denmark"
            ),
            primary_entity="infant formula sold in Denmark",
            anchor_packet=None,
            source_tier_counts={"secondary": 3},
            source_domain_counts={"trade.example": 2, "manufacturer.example": 1},
            top_source_domains=[{"domain": "trade.example", "count": 2}],
            official_evidence_found=False,
        ),
    )
    admission = handoff.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]
    acquisition = handoff.official_canonical_recovery_query_acquisition_trace[
        "OfficialCanonicalRecoveryQueryAcquisition"
    ]
    export = _export(handoff)

    assert admission["admission_considered"] is True
    assert admission["admission_eligible"] is True
    assert admission["admission_used"] is True
    assert admission["source_class_recovery_execution_admitted"] is True
    assert admission["admission_blockers"] == []
    assert handoff.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_official_canonical_admitted"
    ] is True
    assert handoff.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_eligible"
    ] is True
    assert export["official_source_acquisition_quality_layer"] != "admission_not_used"
    assert acquisition["official_authority_acquisition_plan"]["hard_domains"] == []
    _assert_no_us_legal_terms(
        _joined(acquisition["official_authority_acquisition_plan"]["query_variants"])
    )


def test_language_aware_acquisition_deferred_not_implemented() -> None:
    rec = build_source_class_recovery_recommendation(
        query=(
            "What official legal or regulatory text currently lists approved "
            "preservatives and additives in Danish baby formula?"
        ),
        current_date="2026-06-11",
        intent="general",
        report_type="general_research",
        query_type="other",
        core_topic="Danish infant formula additives approved list",
        primary_entity="infant formula additives",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"trade.example": 1},
        top_source_domains=[{"domain": "trade.example", "count": 1}],
        official_evidence_found=False,
    )
    query_text = _joined(rec["source_class_recovery_queries"]).casefold()

    assert "fødevare" not in query_text
    assert "tilsætningsstoffer" not in query_text
    assert "konserveringsmidler" not in query_text
    assert "official legal text" in query_text


def test_no_live_provider_calls_required() -> None:
    test_source = Path(__file__).read_text(encoding="utf-8")
    live_call_marker = "process" + "_search_queries"
    executor_marker = "source_class_recovery" + "_executor"
    payload_marker = "provider" + "_payload"

    assert live_call_marker not in test_source
    assert executor_marker not in test_source
    assert payload_marker not in test_source
