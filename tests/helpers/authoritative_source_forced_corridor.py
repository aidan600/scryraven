"""Offline forced-corridor validation for authoritative-source recovery.

This module is a test/validation harness. It does not retrieve, route
providers, choose depth, rank/filter sources, alter prompts, cite sources, or
affect final-answer behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.authoritative_source_action import (
    AuthoritativeSourceActionFacts,
    AuthoritativeSourceActionResult,
    build_authoritative_source_obligation_state_and_action,
)
from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS
from core.run_controller import RunController
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)

AUTHORITATIVE_SOURCE_FORCED_CORRIDOR_SCHEMA_VERSION = (
    "authoritative_source_forced_corridor_validation_ag67a_v1"
)

_OFFICIAL_CURRENT = "official_current_rules"
_CANONICAL_DOC = "primary_source_documents"
_SUPPORTED_CLASSES = frozenset({_OFFICIAL_CURRENT, _CANONICAL_DOC})
_STRONG = "satisfied_strong"
_SECONDARY_ONLY = "expected_but_only_secondary"
_WEAK = "satisfied_weak"
_UNSATISFIED = "unsatisfied"
_VALID_STATUSES = frozenset({_STRONG, _SECONDARY_ONLY, _WEAK, _UNSATISFIED})


class ForcedCorridorKind(str, Enum):
    OFFICIAL_CURRENT = "official_current"
    CANONICAL_DOC = "canonical_doc"


@dataclass(frozen=True)
class ForcedCorridorFixture:
    """Sanitized fixture inputs for an offline recovery corridor."""

    kind: ForcedCorridorKind
    query: str
    query_type: str
    core_topic: str
    primary_entity: str
    source_class: str
    ordinary_evidence_status: str = _SECONDARY_ONLY
    execute_dispatch_fixture: bool = True
    recovered_fixture_passages: tuple[Mapping[str, Any], ...] = ()
    current_search_depth: str = "basic"


@dataclass(frozen=True)
class ForcedCorridorValidationResult:
    """Trace-safe classification of ordinary acquisition vs recovery execution."""

    classification: dict[str, Any]
    action_result: AuthoritativeSourceActionResult
    controller_snapshot: dict[str, Any]
    dispatch_trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": dict(self.classification),
            "action_trace": dict(self.action_result.trace),
            "controller_snapshot": dict(self.controller_snapshot),
            "dispatch_trace": dict(self.dispatch_trace),
        }


def official_current_forced_corridor_fixture(
    *,
    ordinary_evidence_status: str = _SECONDARY_ONLY,
    execute_dispatch_fixture: bool = True,
) -> ForcedCorridorFixture:
    """Return an offline IRS-style official/current forced corridor."""

    return ForcedCorridorFixture(
        kind=ForcedCorridorKind.OFFICIAL_CURRENT,
        query=(
            "What is the current IRS standard mileage rate for business use of "
            "a car in 2026?"
        ),
        query_type="official_current_status",
        core_topic="IRS 2026 standard mileage rate business",
        primary_entity="IRS",
        source_class=_OFFICIAL_CURRENT,
        ordinary_evidence_status=ordinary_evidence_status,
        execute_dispatch_fixture=execute_dispatch_fixture,
        recovered_fixture_passages=(
            {
                "url": "https://www.irs.gov/ag67a-offline-fixture",
                "title": "IRS offline fixture",
                "text": "Offline fixture for official/current recovery dispatch.",
                "source_class": _OFFICIAL_CURRENT,
                "source_tier": "official",
            },
        ),
    )


def canonical_doc_forced_corridor_fixture(
    *,
    ordinary_evidence_status: str = _SECONDARY_ONLY,
    execute_dispatch_fixture: bool = True,
) -> ForcedCorridorFixture:
    """Return an offline canonical-documentation forced corridor."""

    return ForcedCorridorFixture(
        kind=ForcedCorridorKind.CANONICAL_DOC,
        query="Explain how PostgreSQL MVCC works in a database.",
        query_type="technical_reference",
        core_topic="PostgreSQL MVCC official documentation",
        primary_entity="PostgreSQL",
        source_class=_CANONICAL_DOC,
        ordinary_evidence_status=ordinary_evidence_status,
        execute_dispatch_fixture=execute_dispatch_fixture,
        recovered_fixture_passages=(
            {
                "url": "https://www.postgresql.org/docs/ag67a-offline-fixture.html",
                "title": "PostgreSQL offline fixture",
                "text": "Offline fixture for canonical documentation dispatch.",
                "source_class": _CANONICAL_DOC,
                "source_tier": "canonical",
            },
        ),
    )


def run_forced_corridor_validation(
    fixture: ForcedCorridorFixture,
) -> ForcedCorridorValidationResult:
    """Classify whether an offline corridor truly reaches recovery execution."""

    _validate_fixture(fixture)
    controller = RunController()
    action_result = build_authoritative_source_obligation_state_and_action(
        controller,
        facts=_facts_for_fixture(fixture),
    )
    dispatch_trace = _dispatch_fixture(
        controller=controller,
        lifecycle=action_result.active_source_class_recovery_lifecycle,
        fixture=fixture,
    )
    classification = _classification(
        fixture=fixture,
        action_result=action_result,
        dispatch_trace=dispatch_trace,
    )
    return ForcedCorridorValidationResult(
        classification=classification,
        action_result=action_result,
        controller_snapshot=controller.snapshot_ledger(),
        dispatch_trace=dispatch_trace,
    )


def _validate_fixture(fixture: ForcedCorridorFixture) -> None:
    if fixture.source_class not in _SUPPORTED_CLASSES:
        raise ValueError("forced corridor supports official/current or canonical docs")
    if fixture.ordinary_evidence_status not in _VALID_STATUSES:
        raise ValueError("unsupported ordinary evidence status")


def _facts_for_fixture(fixture: ForcedCorridorFixture) -> AuthoritativeSourceActionFacts:
    recommendation = {
        "source_class_recovery_recommended": False,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [],
        "source_class_recovery_reason": None,
        "source_class_recovery_queries": [],
        "source_class_recovery_query_count": 0,
        "source_class_recovery_trigger_fields": [],
    }
    observability = {
        "source_class_satisfaction_status": {
            fixture.source_class: fixture.ordinary_evidence_status
        },
        "source_class_strong_satisfaction_counts": {
            fixture.source_class: 1
            if fixture.ordinary_evidence_status == _STRONG
            else 0
        },
        "source_class_gap_candidates": [fixture.source_class],
    }
    return AuthoritativeSourceActionFacts(
        query=fixture.query,
        intent="general",
        report_type="answer",
        query_type=fixture.query_type,
        core_topic=fixture.core_topic,
        primary_entity=fixture.primary_entity,
        recommendation=recommendation,
        source_class_observability=observability,
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2},
            "source_domain_counts": {"analysis.example": 2},
            "top_source_domains": [{"domain": "analysis.example", "count": 2}],
            "unique_source_domain_count": 1,
            "on_domain_source_count": 0,
            "off_domain_source_count": 1,
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth=fixture.current_search_depth,
        iteration_budget_available=False,
        answer_contract_source_class_slot_available=False,
        provider_policy_reusable=True,
        provider_swap_required=False,
        search_depth_reusable=True,
        search_depth_escalation_required=False,
        retrieve_to_anchor_recommended=False,
        pre_analyst_phase=True,
        author_phase=False,
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )


def _payload(trace: Mapping[str, Any] | None, key: str) -> Mapping[str, Any]:
    if not isinstance(trace, Mapping):
        return {}
    payload = trace.get(key)
    return payload if isinstance(payload, Mapping) else {}


def _lifecycle_dispatch_authorized(lifecycle: Mapping[str, Any]) -> bool:
    authority = lifecycle.get("authority_lifecycle")
    if not isinstance(authority, Mapping):
        return False
    action = authority.get("recovery_action")
    if not isinstance(action, Mapping):
        return False
    return (
        authority.get("recovery_needed") == "required"
        and action.get("action_type") == RECOVER_MISSING_SOURCE_CLASS
        and action.get("approved") is True
    )


def _dispatch_fixture(
    *,
    controller: RunController,
    lifecycle: dict[str, Any],
    fixture: ForcedCorridorFixture,
) -> dict[str, Any]:
    if not fixture.execute_dispatch_fixture:
        return {
            "dispatch_fixture_attempted": False,
            "dispatch_authorized": _lifecycle_dispatch_authorized(lifecycle),
            "executor_attempted": False,
            "result_count": 0,
            "new_url_count": 0,
            "captured_queries": [],
        }

    captured_queries: list[str] = []
    all_passages: list[dict[str, Any]] = []

    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        _search_depth: str,
        _results_per_query: int,
        _include_domains: list[str],
        _exclude_domains: list[str],
        _query_embedding: Any,
        seen_urls: set[str],
        _collected_images: set[str],
        *_args: Any,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured_queries.extend(queries)
        passages = [dict(passage) for passage in fixture.recovered_fixture_passages]
        for passage in passages:
            seen_urls.add(str(passage.get("url") or ""))
        return passages

    result = run_source_class_recovery_dispatch(
        SourceClassRecoveryRunnerContext(
            controller=controller,
            lifecycle_trace=lifecycle,
            process_search_queries=fake_search,
            all_passages=all_passages,
            intent="general",
            complexity="medium",
            results_per_query=5,
            include_domains=[],
            exclude_domains=[],
            query_embedding=[0.0],
            seen_urls=set(),
            collected_images=set(),
            embed_provider="OpenAI",
            embed_model="text-embedding-3-small",
            local_url="http://localhost",
            embed_texts=lambda *_args, **_kwargs: [],
            compute_similarities=lambda *_args, **_kwargs: [],
            status_container=object(),
            search_providers=["offline-fixture"],
            exa_domain_filter=None,
            entity_hint=fixture.primary_entity,
            provider_diagnostics=[],
            retrieval_pass_records=[],
        )
    ).source_class_recovery_execution
    return {
        "dispatch_fixture_attempted": True,
        "dispatch_authorized": bool(
            lifecycle.get("source_class_recovery_dispatch_authorized")
        ),
        "executor_attempted": bool(result["attempted"]),
        "result_count": int(result["result_count"]),
        "new_url_count": int(result["new_url_count"]),
        "captured_queries": list(captured_queries),
        "recovered_passage_count": len(all_passages),
        "recovered_passage_stages": [
            passage.get("retrieval_stage") for passage in all_passages
        ],
    }


def _classification(
    *,
    fixture: ForcedCorridorFixture,
    action_result: AuthoritativeSourceActionResult,
    dispatch_trace: Mapping[str, Any],
) -> dict[str, Any]:
    bridge = _payload(
        action_result.official_source_obligation_bridge_trace,
        "OfficialSourceObligationBridge",
    )
    acquisition = _payload(
        action_result.official_canonical_recovery_query_acquisition_trace,
        "OfficialCanonicalRecoveryQueryAcquisition",
    )
    admission = _payload(
        action_result.official_canonical_recovery_execution_admission_trace,
        "OfficialCanonicalRecoveryExecutionAdmission",
    )
    lifecycle = action_result.active_source_class_recovery_lifecycle
    ordinary_present = fixture.ordinary_evidence_status == _STRONG
    missing_forced = bool(
        fixture.source_class
        in set(action_result.recommendation.get("missing_expected_source_classes") or ())
        or fixture.source_class
        in set(lifecycle.get("active_source_class_recovery_missing_classes") or ())
    )
    recovery_query_created = bool(
        action_result.recommendation.get("source_class_recovery_queries")
        or lifecycle.get("active_source_class_recovery_queries")
    )
    admitted = bool(
        action_result.official_canonical_recovery_execution_admitted
        or admission.get("admission_used")
    )
    dispatch_authorized = bool(dispatch_trace.get("dispatch_authorized"))
    recovered_visible: bool | str
    if dispatch_trace.get("dispatch_fixture_attempted"):
        recovered_visible = bool(
            dispatch_trace.get("recovered_passage_count")
            and all(
                stage == "source_class_recovery"
                for stage in dispatch_trace.get("recovered_passage_stages") or ()
            )
        )
    else:
        recovered_visible = "not_applicable_offline"

    next_failure_layer = _next_failure_layer(
        ordinary_present=ordinary_present,
        missing_forced=missing_forced,
        recovery_query_created=recovery_query_created,
        admitted=admitted,
        lifecycle=lifecycle,
        dispatch_authorized=dispatch_authorized,
        dispatch_trace=dispatch_trace,
        recovered_visible=recovered_visible,
        admission=admission,
    )
    return {
        "schema_version": AUTHORITATIVE_SOURCE_FORCED_CORRIDOR_SCHEMA_VERSION,
        "ordinary_authoritative_source_already_present": ordinary_present,
        "ordinary_evidence_status": fixture.ordinary_evidence_status,
        "missing_authoritative_source_state_forced": missing_forced,
        "authoritative_recovery_bridge_visible": bool(bridge.get("bridge_used")),
        "authoritative_recovery_query_created": recovery_query_created,
        "recovery_query_count": len(
            action_result.recommendation.get("source_class_recovery_queries") or ()
        ),
        "recovery_execution_admitted": admitted,
        "recovery_dispatch_authorized": dispatch_authorized,
        "recovered_evidence_visible": recovered_visible,
        "final_answer_citation_or_use": "not_applicable_offline",
        "ordinary_acquisition_counted_as_recovery_success": False,
        "source_class_recovery_lifecycle_action_ready": bool(
            lifecycle.get("active_source_class_recovery_eligible")
        ),
        "source_class_recovery_execution_attempted": bool(
            lifecycle.get("active_source_class_recovery_execution_attempted")
            or dispatch_trace.get("executor_attempted")
        ),
        "bridge_used": bool(bridge.get("bridge_used")),
        "acquisition_repair_used": bool(acquisition.get("acquisition_repair_used")),
        "admission_used": bool(admission.get("admission_used")),
        "next_failure_layer": next_failure_layer,
        "protected_surface": {
            "provider_policy_unchanged": True,
            "provider_selection_unchanged": True,
            "depth_policy_unchanged": True,
            "retrieval_ranking_filtering_unchanged": True,
            "query_wording_unchanged_except_existing_adapter": True,
            "prompt_unchanged": True,
            "citation_behavior_unchanged": True,
            "final_answer_behavior_unchanged": True,
            "followup_behavior_unchanged": True,
            "author_behavior_unchanged": True,
            "analyst_behavior_unchanged": True,
            "economist_behavior_unchanged": True,
            "scrutineer_behavior_unchanged": True,
            "live_validation_used": False,
        },
    }


def _next_failure_layer(
    *,
    ordinary_present: bool,
    missing_forced: bool,
    recovery_query_created: bool,
    admitted: bool,
    lifecycle: Mapping[str, Any],
    dispatch_authorized: bool,
    dispatch_trace: Mapping[str, Any],
    recovered_visible: bool | str,
    admission: Mapping[str, Any],
) -> str:
    if ordinary_present and not missing_forced:
        return "ordinary_authoritative_source_already_present"
    if not missing_forced:
        return "missing_authoritative_source_state_not_forced"
    if not recovery_query_created:
        return "recovery_query_not_created"
    if not admitted:
        skip_reason = admission.get("admission_skip_reason")
        return f"execution_admission_blocked:{skip_reason or 'unknown'}"
    if not lifecycle.get("active_source_class_recovery_eligible"):
        skip_reason = lifecycle.get("active_source_class_recovery_skip_reason")
        return f"source_class_recovery_lifecycle_not_ready:{skip_reason or 'unknown'}"
    if not dispatch_authorized:
        gate_reason = lifecycle.get("source_class_recovery_dispatch_reason")
        return f"dispatch_not_authorized:{gate_reason or 'unknown'}"
    if not dispatch_trace.get("executor_attempted"):
        return "executor_not_attempted"
    if not dispatch_trace.get("result_count"):
        return "execution_attempted_zero_candidates"
    if recovered_visible is not True:
        return "recovered_evidence_not_visible"
    return "offline_recovery_dispatch_fixture_succeeded"


__all__ = [
    "AUTHORITATIVE_SOURCE_FORCED_CORRIDOR_SCHEMA_VERSION",
    "ForcedCorridorFixture",
    "ForcedCorridorKind",
    "ForcedCorridorValidationResult",
    "canonical_doc_forced_corridor_fixture",
    "official_current_forced_corridor_fixture",
    "run_forced_corridor_validation",
]
