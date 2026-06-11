from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.official_canonical_recovery_candidate_acquisition import (
    build_official_canonical_recovery_candidate_acquisition_trace,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.provider_result_represented_visibility import (
    PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY,
    build_provider_result_represented_visibility_projection,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.run_controller import RunController
from core.source_class_recovery import build_official_authority_acquisition_plan
from core.source_class_recovery_executor import execute_source_class_recovery_action
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_THIS_FILE = Path(__file__)
_OFFICIAL_CURRENT = "official_current_rules"


def _admission_trace() -> dict[str, Any]:
    return {
        "official_canonical_recovery_execution_admission_trace": {
            "OfficialCanonicalRecoveryExecutionAdmission": {
                "admission_considered": True,
                "admission_eligible": True,
                "admission_used": True,
                "recovery_query_count": 2,
                "recovery_query_previews": [
                    "official current source airport screening accepted-ID guidance",
                    "airport checkpoint identification documents current guidance",
                ],
            }
        }
    }


def _authority_trace(
    *,
    result_count: int = 1,
    accepted_url_count: int = 1,
) -> dict[str, Any]:
    trace = build_authority_runtime_arbitration(
        requirement_id=_OFFICIAL_CURRENT,
        required_authority=_OFFICIAL_CURRENT,
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=(
            "official current source airport screening accepted-ID guidance",
            "airport checkpoint identification documents current guidance",
        ),
        required_source_classes=(_OFFICIAL_CURRENT,),
        recovery_action_allowed=True,
    ).to_trace_fields()
    trace.update(
        {
            **_admission_trace(),
            "required_source_class": _OFFICIAL_CURRENT,
            "source_obligation_status": "official_current_required_unmet",
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:"
                "official_current_rules"
            ),
            "active_source_class_recovery_skip_reason": None,
            "active_source_class_recovery_blockers": [],
            "active_source_class_recovery_missing_classes": [_OFFICIAL_CURRENT],
            "active_source_class_recovery_queries": [
                "official current source airport screening accepted-ID guidance",
                "airport checkpoint identification documents current guidance",
            ],
            "active_source_class_recovery_result_count": result_count,
            "recovered_accepted_url_count": accepted_url_count,
            "recovered_candidate_domain_preview": [
                "nbcnews.com",
                "npr.org",
                "cbsnews.com",
                "apnews.com",
                "tsa.gov",
            ],
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": [_OFFICIAL_CURRENT],
                "allowed_action": True,
            },
        }
    )
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=result_count,
        recovered_result_count=result_count,
        accepted_url_count=accepted_url_count,
    )
    trace.update(
        build_official_canonical_recovery_candidate_acquisition_trace(
            lifecycle_trace=trace,
            provider_diagnostics=[
                {
                    "provider": "fixture_provider",
                    "provider_role": "source_class_recovery",
                    "success": True,
                    "result_count": result_count,
                    "accepted_url_count": accepted_url_count,
                    "new_source_count": accepted_url_count,
                }
            ],
        )
    )
    return trace


def _official_tsa_candidate(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "candidate_id": "tsa-accepted-id",
        "title": "TSA Acceptable Identification at the Checkpoint",
        "url": "https://www.tsa.gov/travel/security-screening/identification",
        "text": (
            "TSA current accepted identification guidance for airport security "
            "checkpoints and domestic flight screening."
        ),
        "source_tier": "official",
        "source_class": _OFFICIAL_CURRENT,
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "readable_text_available": True,
        "readability_status": "readable",
        "currentness_signal": "current",
    }
    candidate.update(overrides)
    return candidate


def _news_source(url: str = "https://www.nbcnews.com/travel/real-id-news") -> dict[str, Any]:
    return {
        "candidate_id": "news-visible",
        "title": "News explainer about airport ID rules",
        "url": url,
        "text": "News context about airport identification requirements.",
        "source_tier": "secondary",
        "source_class": "secondary_only",
    }


def _export(trace: dict[str, Any]) -> dict[str, Any]:
    return build_official_canonical_recovery_visibility_export(trace)


def _attach_provider_bridge(
    trace: dict[str, Any],
    provider_results: list[dict[str, Any]],
) -> None:
    trace[PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY] = {
        "ProviderResultRepresentedCandidateBridge": (
            build_provider_result_represented_visibility_projection(
                runtime_trace=trace,
                provider_results=provider_results,
            )
        )
    }


def test_news_only_provider_results_classified_as_provider_or_query_no_official_candidate() -> None:
    trace = _authority_trace(result_count=4, accepted_url_count=4)
    trace.update(
        {
            "recovered_candidate_domain_preview": [
                "nbcnews.com",
                "npr.org",
                "cbsnews.com",
                "apnews.com",
            ],
            "recovered_source_tier_counts": {"secondary": 4},
            "recovered_source_class_counts": {},
        }
    )

    export = _export(trace)

    assert export["candidate_acquisition_result_status"] == "provider_results_returned"
    assert export["candidate_official_or_canonical_count"] == 0
    assert export["official_source_acquisition_quality_layer"] == (
        "provider_or_query_failed_to_return_official_candidate"
    )


def test_official_tsa_candidate_survives_provider_forwarding_into_candidate_acquisition() -> None:
    trace = _authority_trace(result_count=4, accepted_url_count=3)
    trace["candidate_official_or_canonical_count"] = 0
    _attach_provider_bridge(
        trace,
        [
            {
                "provider_name": "fixture_provider",
                "provider_role": "source_class_recovery",
                "source_url": "https://www.tsa.gov/travel/security-screening/identification",
                "normalized_domain": "tsa.gov",
                "title": "TSA Acceptable Identification",
                "source_tier": "official",
                "source_class": _OFFICIAL_CURRENT,
                "non_representation_reason": "filtered_before_candidate_acquisition",
            },
            {
                "provider_name": "fixture_provider",
                "provider_role": "source_class_recovery",
                "source_url": "https://www.nbcnews.com/travel/real-id-news",
                "normalized_domain": "nbcnews.com",
                "title": "News explainer",
                "source_tier": "secondary",
                "source_class": "secondary_only",
            },
        ],
    )

    export = _export(trace)

    assert export["provider_result_official_or_canonical_count"] == 1
    assert export["provider_result_unrepresented_official_or_canonical_count"] == 1
    assert export["official_source_acquisition_quality_layer"] == (
        "provider_result_forwarding_or_filtering_dropped_official_candidate"
    )


def test_candidate_fit_accepts_relevant_official_tsa_or_dhs_guidance() -> None:
    trace = _authority_trace()
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_news_source()],
        recovered_passages=[_official_tsa_candidate()],
        lifecycle_trace=trace,
        max_final_evidence=4,
    )
    trace.update(decision.to_trace_fields())
    trace["source_survival_final_evidence_official_or_canonical_count"] = 1

    export = _export(trace)

    assert final[-1]["url"] == "https://www.tsa.gov/travel/security-screening/identification"
    assert decision.source_fit_status == "matched_selected"
    assert export["accepted_readable_authority_evidence_count"] == 1
    assert export["official_source_acquisition_quality_layer"] == (
        "official_source_acquisition_quality_satisfied"
    )


def test_visible_news_source_does_not_block_official_candidate_as_already_visible_authority_satisfying() -> None:
    shared_url = "https://www.tsa.gov/travel/security-screening/identification"
    trace = _authority_trace()
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_news_source(shared_url)],
        recovered_passages=[_official_tsa_candidate(url=shared_url)],
        lifecycle_trace=trace,
        max_final_evidence=4,
    )
    trace.update(decision.to_trace_fields())
    export = _export(trace)

    assert len(final) == 1
    assert final[0]["source_tier"] == "official"
    assert decision.reason == "reserved_replace_non_authority_duplicate"
    assert decision.source_fit_status == "matched_selected"
    assert "already_visible_not_authority_satisfying" not in (
        decision.source_fit_rejection_reasons
    )
    assert export["accepted_readable_authority_evidence_count"] == 1


def test_candidate_fit_rejected_official_candidate_is_distinct_from_provider_miss() -> None:
    trace = _authority_trace()
    stale = _official_tsa_candidate(
        title="TSA historical archive of accepted identification",
        text="Historical archive of identification rules from prior years.",
        currentness_signal="historical",
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=[stale],
        lifecycle_trace=trace,
        max_final_evidence=4,
    )
    trace.update(decision.to_trace_fields())
    trace["recovered_source_class_counts"] = {_OFFICIAL_CURRENT: 1}

    export = _export(trace)

    assert final == []
    assert "historical_or_archival_not_current" in (
        decision.source_fit_rejection_reasons
    )
    assert export["official_source_acquisition_quality_layer"] == (
        "candidate_source_fit_rejected_official_candidate"
    )


def test_unreadable_official_candidate_exposes_readability_failure_not_no_matching_fit() -> None:
    trace = _authority_trace()
    unreadable = _official_tsa_candidate(
        candidate_id="tsa-unreadable",
        text="",
        readable_text_available=False,
        readability_status="readability_failed",
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=[unreadable],
        lifecycle_trace=trace,
        max_final_evidence=4,
    )
    trace.update(decision.to_trace_fields())
    trace["recovered_source_class_counts"] = {_OFFICIAL_CURRENT: 1}

    export = _export(trace)

    assert final == []
    assert decision.source_fit_status == "no_matching_source_fit"
    assert "readability_failed" in decision.source_fit_rejection_reasons
    assert export["official_source_acquisition_quality_layer"] == (
        "official_candidate_readability_or_passport_failed"
    )


def test_accepted_readable_official_candidate_lost_after_acquisition_is_exposed() -> None:
    trace = _authority_trace()
    trace.update(
        {
            "recovered_source_class_counts": {_OFFICIAL_CURRENT: 1},
            "recovered_visibility_source_fit_status": "matched_selected",
            "recovered_visibility_source_fit_candidate_count": 1,
            "recovered_visibility_source_fit_selected_count": 1,
            "recovered_visibility_accepted_readable_authority_evidence_count": 1,
            "recovered_visibility_source_fit_rejection_reasons": [],
            "source_survival_final_evidence_official_or_canonical_count": 0,
        }
    )

    export = _export(trace)

    assert export["accepted_readable_authority_evidence_count"] == 1
    assert export["official_source_acquisition_quality_layer"] == (
        "accepted_official_candidate_lost_after_acquisition"
    )


def test_role_only_airport_id_plan_exposes_tsa_dhs_soft_candidate_domains() -> None:
    plan = build_official_authority_acquisition_plan(
        source_classes=[_OFFICIAL_CURRENT],
        subject="airport checkpoint accepted identification for domestic flights",
        context_text=(
            "Which identification documents are accepted at airport checkpoints "
            "and when does enforcement begin?"
        ),
    )
    query_text = " ".join(plan["query_variants"]).casefold()

    assert "airport_screening_identity_access_rule" in plan["venue_families"]
    assert plan["hard_domains"] == []
    assert {"tsa.gov", "dhs.gov"}.issubset(set(plan["soft_candidate_domains"]))
    assert "accepted-id guidance" in query_text


def test_hard_official_domains_forward_to_supported_provider_include_domain_arguments_when_present() -> None:
    recommendation = {
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": [_OFFICIAL_CURRENT],
        "source_class_recovery_queries": ["IRS standard mileage rate official notice"],
        "source_class_recovery_query_count": 1,
        "source_class_recovery_reason": "answer_contract_official_gap",
        "source_class_recovery_official_domains": ["irs.gov"],
    }
    controller = RunController()
    lifecycle = record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={"source_tier_counts": {"secondary": 1}},
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=True,
        official_canonical_source_class_slot_available=True,
    )
    captured: dict[str, Any] = {}

    def fake_search(
        _queries: list[str],
        _intent: str,
        _complexity: str,
        _search_depth: str,
        _results_per_query: int,
        include_domains: list[str],
        _exclude_domains: list[str],
        _query_embedding: Any,
        _seen_urls: set[str],
        _collected_images: set[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured["include_domains"] = list(include_domains)
        captured["exa_domain_filter"] = list(kwargs.get("exa_domain_filter") or [])
        kwargs["provider_diagnostics"].append(
            {
                "provider": "fixture_provider",
                "provider_role": kwargs["provider_role"],
                "success": True,
                "result_count": 0,
                "accepted_url_count": 0,
            }
        )
        return []

    execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=[],
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
        search_providers=["tavily"],
        exa_domain_filter=None,
        entity_hint=None,
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )

    assert captured["include_domains"] == ["irs.gov"]
    assert captured["exa_domain_filter"] == ["irs.gov"]


def test_no_live_provider_calls_required_for_acquisition_quality_fixtures() -> None:
    tree = ast.parse(_THIS_FILE.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    assert "core.search_providers" not in imported_modules
    assert "core.pipeline" not in imported_modules
    assert "core.pipeline_orchestrator" not in imported_modules
    assert "requests" not in imported_modules
    assert "openai" not in imported_modules
