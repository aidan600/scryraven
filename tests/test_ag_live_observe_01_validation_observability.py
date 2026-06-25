from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from core.cap_enforcement import RunCapPolicy
from core.provider_diagnostics import build_provider_attempt_diagnostic
from core.retrieval_loop_contract import RETRIEVAL_LOOP_TRACE_KEY
from core.run_config import RunConfig
from core.validation_observability import build_validation_observability
from core.validation_profiles import (
    AG_LIVE_SMOKE,
    AG_LIVE_SOURCE_CUSTODY,
    get_validation_profile,
)
from scripts import ag_live_bound_01_support as support

ROOT = Path(__file__).resolve().parents[1]


def _context(profile_name: str = AG_LIVE_SMOKE) -> support.PreflightContext:
    return support.build_preflight_context(
        root=ROOT,
        profile_name=profile_name,
        query=support.PRIMARY_QUERY,
        mode=support.REQUIRED_MODE,
        include_domains=[support.REQUIRED_DOMAIN],
        output_path=ROOT / "output" / "ag_live_observe_01_packet.json",
        caps=support.AgLiveBoundCaps(),
        run_id="ag-live-observe-test",
        confirm_live_product_run=True,
        approved_backup_query=False,
    )


def _cap_policy(
    *,
    search_dispatches: int = 2,
    fetch_read_operations: int = 1,
    author_model_calls: int = 1,
) -> RunCapPolicy:
    policy = RunCapPolicy(
        max_search_dispatches=2,
        max_fetch_read_operations=3,
        max_author_model_calls=1,
        max_smart_search_judgment_model_calls=0,
        max_retries=0,
    )
    policy.search_dispatches = search_dispatches
    policy.fetch_read_operations = fetch_read_operations
    policy.author_model_calls = author_model_calls
    return policy


def _run_config() -> RunConfig:
    return RunConfig(
        query=support.PRIMARY_QUERY,
        mode=support.REQUIRED_MODE,
        fast_provider="FixtureFastProvider",
        fast_model="fixture-fast-model",
        smart_provider="FixtureSmartProvider",
        smart_model="fixture-smart-model",
        embed_provider="FixtureEmbedProvider",
        embed_model="fixture-embed-model",
    )


def _provider_attempts() -> list[dict[str, Any]]:
    return [
        build_provider_attempt_diagnostic(
            provider="tavily",
            provider_role="main_retrieval",
            cost_phase="retrieval",
            query="bounded preview query should not become a pass record query",
            iteration=1,
            depth="advanced",
            max_results=6,
            success=True,
            result_count=1,
            accepted_url_count=1,
            provider_result_summaries=[
                {
                    "rank": 1,
                    "title": "Python docs",
                    "snippet": "not serialized by validation observability",
                }
            ],
        ),
        build_provider_attempt_diagnostic(
            provider="linkup",
            provider_role="main_retrieval",
            cost_phase="retrieval",
            query="bounded preview query should not become a pass record query",
            iteration=1,
            depth="standard",
            success=False,
            failure_type="RuntimeError",
            result_count=0,
            accepted_url_count=0,
        ),
    ]


def test_success_packet_contains_consolidated_sanitized_observability() -> None:
    context = _context()
    policy = _cap_policy()
    outcome = SimpleNamespace(
        report="The defaults are rel_tol=1e-09 and abs_tol=0.0. [[1]](https://docs.python.org/3/library/math.html#math.isclose)",
        top_passages=[
            {
                "source_id": 1,
                "url": "https://docs.python.org/3/library/math.html#math.isclose",
                "text": "[SNIPPET] snippet body must not serialize",
                "source_tier": "official",
            },
            {
                "source_id": 2,
                "url": "https://docs.python.org/3/library/itertools.html#itertools.count",
                "text": "[FULL_PAGE] full page body must not serialize",
                "source_tier": "official",
            },
        ],
        seen_urls=[
            "https://docs.python.org/3/library/math.html#math.isclose",
            "https://docs.python.org/3/library/itertools.html#itertools.count",
        ],
        execution_trace={
            "final_answer_source_ids_used": ["1", "2"],
            "provider_diagnostics": _provider_attempts(),
            "pass_providers": [["tavily", "linkup"]],
            "retrieval_pass_records": [
                {
                    "stage": "main_retrieval",
                    "iteration": 1,
                    "queries": ["full query must not serialize"],
                    "providers": ["tavily", "linkup"],
                    "provider_role": "main_retrieval",
                    "search_depth": "advanced",
                    "results_per_query": 6,
                }
            ],
            "author_system_prompt_key": "author",
            "final_answer_packet": {
                "citation_eligible_source_ids": ["1", "2"],
                "author_input_refs": {
                    "author_provider": "FixtureAuthorProvider",
                    "author_model": "fixture-author-model",
                    "author_system_prompt_key": "author",
                },
                "official_current_custody_summary": {
                    "requirements": [
                        {
                            "source_class": "current_primary_or_official",
                            "status": "requirement_satisfied",
                        }
                    ]
                },
                "source_obligations": [
                    {
                        "source_class": "current_primary_or_official",
                        "status": "satisfied",
                    }
                ],
            },
        },
    )

    packet = support.build_live_success_packet(
        context,
        outcome=outcome,
        cap_policy=policy,
        run_config=_run_config(),
    )

    observability = packet["validation_observability"]
    model = observability["model_invocation_summary"]
    assert model["fast_provider"] == "FixtureFastProvider"
    assert model["fast_model"] == "fixture-fast-model"
    assert model["embed_provider"] == "FixtureEmbedProvider"
    assert model["author_provider"] == "FixtureAuthorProvider"
    assert model["author_model"] == "fixture-author-model"
    assert model["author_system_prompt_key"] == "author"

    search = observability["search_provider_summary"]
    assert search["providers_attempted_by_name"] == ["tavily", "linkup"]
    assert search["provider_successful_attempts_by_provider"] == {"tavily": 1}
    assert search["provider_failed_attempts_by_provider"] == {"linkup": 1}
    assert search["provider_attempts_by_role"] == {"main_retrieval": 2}
    assert search["provider_accepted_url_count_by_provider"] == {"tavily": 1}
    assert search["provider_result_summary_count"] == 1

    retrieval = observability["retrieval_dispatch_summary"]
    assert retrieval["retrieval_pass_count"] == 1
    assert retrieval["pass_records"] == [
        {
            "stage": "main_retrieval",
            "iteration": 1,
            "query_count": 1,
            "providers": ["tavily", "linkup"],
            "provider_role": "main_retrieval",
            "search_depth": "advanced",
            "results_per_query": 6,
        }
    ]
    assert "queries" not in retrieval["pass_records"][0]

    material = observability["source_material_summary"]
    assert material["cited_source_ids"] == ["1", "2"]
    assert material["cited_urls_seen_in_top_passages"] is True
    assert material["source_tiers_by_cited_url"] == {
        "https://docs.python.org/3/library/math.html#math.isclose": "official",
        "https://docs.python.org/3/library/itertools.html#itertools.count": "official",
    }
    assert material["evidence_material_type_by_cited_url"] == {
        "https://docs.python.org/3/library/math.html#math.isclose": "snippet_only",
        "https://docs.python.org/3/library/itertools.html#itertools.count": (
            "full_page_fetched"
        ),
    }

    rendered = json.dumps(packet, sort_keys=True)
    assert "snippet body must not serialize" not in rendered
    assert "full page body must not serialize" not in rendered
    assert "full query must not serialize" not in rendered
    assert '"raw_prompt":' not in rendered
    assert '"provider_payload":' not in rendered
    assert '"raw_request_text":' not in rendered
    support.reject_forbidden_packet(packet)


def test_source_custody_profile_with_zero_fetch_read_diagnoses_unsatisfied() -> None:
    context = _context(AG_LIVE_SOURCE_CUSTODY)
    policy = _cap_policy(search_dispatches=2, fetch_read_operations=0)
    outcome = SimpleNamespace(
        report=(
            "The docs say rel_tol defaults to 1e-09 and abs_tol defaults to 0.0. "
            "Source-obligation/citation posture remains custody partial."
        ),
        top_passages=[
            {
                "source_id": 1,
                "url": "https://docs.python.org/3/library/math.html#math.isclose",
                "text": "[SNIPPET] official docs snippet must not serialize",
                "source_tier": "official",
            }
        ],
        seen_urls=["https://docs.python.org/3/library/math.html#math.isclose"],
        execution_trace={
            "final_answer_source_ids_used": ["1"],
            "provider_diagnostics": _provider_attempts()[:1],
            "pass_providers": [["tavily"]],
            "author_system_prompt_key": "author",
            "final_answer_packet": {
                "citation_eligible_source_ids": ["1"],
                "author_input_refs": {
                    "author_provider": "FixtureAuthorProvider",
                    "author_model": "fixture-author-model",
                    "author_system_prompt_key": "author",
                },
                "source_obligations": [
                    {
                        "source_class": "current_primary_or_official",
                        "status": "official_current_unsatisfied",
                    }
                ],
            },
        },
    )

    packet = support.build_live_success_packet(
        context,
        outcome=outcome,
        cap_policy=policy,
        run_config=_run_config(),
    )

    assert packet["success_classification"] == "success"
    custody = packet["validation_observability"]["source_custody_summary"]
    assert custody["source_custody_expected"] is True
    assert custody["fetch_read_required"] is True
    assert custody["fetch_read_operations"] == 0
    assert custody["source_custody_satisfied"] is False
    assert custody["source_custody_diagnosis"] == (
        "fetch_read_operations_zero_with_official_doc_citations"
    )
    assert "fetch/read operations were zero" in custody["source_custody_explanation"]
    assert custody["citation_eligible_source_ids"] == ["1"]
    assert custody["final_answer_source_ids_used"] == ["1"]
    assert packet["validation_observability"]["model_invocation_summary"][
        "fast_model"
    ] == "fixture-fast-model"

    rendered = json.dumps(packet, sort_keys=True)
    assert "official docs snippet must not serialize" not in rendered
    support.reject_forbidden_packet(packet)


def test_retrieval_dispatch_summary_can_fall_back_to_loop_contract() -> None:
    policy = _cap_policy(search_dispatches=1, fetch_read_operations=0)
    outcome = SimpleNamespace(
        report="No citations.",
        top_passages=[],
        seen_urls=[],
        execution_trace={
            RETRIEVAL_LOOP_TRACE_KEY: {
                "iteration": 1,
                "current_queries": ["loop query must not serialize"],
                "provider_list": ["exa"],
                "search_depth": "basic",
                "results_per_query": 3,
                "pass_descriptor": {
                    "iteration": 1,
                    "current_queries": ["loop query must not serialize"],
                    "provider_list": ["exa"],
                    "provider_role": "main_retrieval",
                    "search_depth": "basic",
                    "results_per_query": 3,
                },
                "pass_result_summaries": [
                    {
                        "iteration": 1,
                        "query_count": 1,
                        "provider_count": 1,
                        "result_count": 2,
                    }
                ],
            }
        },
    )

    observability = build_validation_observability(
        validation_profile=get_validation_profile(AG_LIVE_SMOKE),
        preflight_context=_context(),
        run_config=_run_config(),
        outcome=outcome,
        cap_policy=policy,
    )

    retrieval = observability["retrieval_dispatch_summary"]
    assert retrieval["retrieval_pass_records_available"] is False
    assert retrieval["retrieval_loop_contract_available"] is True
    assert retrieval["retrieval_pass_count"] == 1
    assert retrieval["pass_records"][0]["query_count"] == 1
    assert retrieval["pass_records"][0]["providers"] == ["exa"]
    assert "loop query must not serialize" not in json.dumps(observability)


def test_forbidden_packet_rejection_still_recurses_into_observability() -> None:
    with pytest.raises(support.AgLiveBoundPacketError, match="raw_request_text"):
        support.reject_forbidden_packet(
            {
                "validation_observability": {
                    "nested": {"raw_request_text": "must not serialize"}
                }
            }
        )
