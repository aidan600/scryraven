"""PRODUCT-PATH-REGRESSION: generic single-relation live dogfood path.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex
--mvp-single-relation-live-dogfood-run --query "<supported query>"
Runtime consumer: proplex.__main__ ->
proplex.mvp_single_relation_live_dogfood_run ->
proplex.live_semantic_coverage_status
Why ordinary product-path work cannot be done directly: offline validation must
not make live provider, broker, fetch/read, retrieval, or model calls; injected
provider/fetch/D-prime callables preserve the same product entrypoint and
retained-artifact consumer.
Integration deadline: current phase.
Exit condition: keep while the generic single-relation live dogfood CLI exists,
or replace with a broader product-path guard when generic supported-query live
answering is deliberately broadened.
Why this is not a shadow product path: tests call the product entrypoint builder
and CLI route, then existing retained-artifact D-prime status consumers.
Forbidden interpretation: fake-provider PASS is not live validation PASS,
product correctness, arbitrary query answering, multi-component planning,
RunKernel DAG scheduling, FAP/Author execution, source-class adapter support, or
friend-level/general MVP readiness.
"""

from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping
from urllib.parse import urlparse

import pytest

import core.generic_product_provider_acquisition as product_acquisition
import proplex.live_semantic_coverage_status as semantic_status_runtime
import proplex.mvp_single_relation_live_dogfood_run as dogfood
from core.dprime_product_smart_one_shot_transport import product_smart_model_route_ref
from core.dprime_single_lane_answer_path_runtime import DPrimeSingleLaneAnswerPathError
from core.generic_query_to_relation_planning import (
    MVP_QUERY_PLAN_PACKET_NAME,
    build_generic_query_plan_status_output,
    build_generic_query_relation_plan,
)
from core.mvp_supported_query_class_boundary import MVP_SUPPORTED_QUERY_CLASS_ID
from core.product_model_route_config import (
    CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
    CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
    MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
    MVP_LIVE_DOGFOOD_RUN_FLAG,
    MVP_QUERY_PLAN_STATUS_FLAG,
    MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
    PRODUCT_STATUS_DRY_RUN_FLAGS,
    initialize_product_model_route_config,
)
from core.strict_accounted_model_route import (
    StrictAccountedModelRouteResult,
    build_strict_accounted_fast_model_planning_route,
)
from proplex.mvp_live_dogfood_run import (
    BLOCKED_MVP_LIVE_CONFIRMATION_REQUIRED,
    build_mvp_live_dogfood_run_output,
)
from proplex.mvp_single_relation_live_dogfood_run import (
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ALL_CANDIDATES_4XX,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_CANDIDATE_CONTRACT_MISSING,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_OBSERVABILITY_INSUFFICIENT,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_CREDENTIAL_UNAVAILABLE,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_ROUTE_UNAVAILABLE,
    BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED,
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED,
    DEFAULT_OUTPUT_DIR,
    GenericLiveFetchReadResult,
    GenericProviderProxyRunRequest,
    GenericProviderProxyRunResult,
    GenericSingleRelationLiveDogfoodRunError,
    build_generic_single_relation_live_dogfood_run_output,
    format_generic_single_relation_live_dogfood_output,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "proplex" / "mvp_single_relation_live_dogfood_run.py"
ADAPTER_MODULE_PATH = ROOT / "core" / "generic_product_provider_acquisition.py"
TEST_PATH = Path(__file__).resolve()
N400_QUERY = "What is the current USCIS Form N-400 paper filing fee?"
SMALL_CLAIMS_QUERY = (
    "What is the current filing fee for small claims in Example County?"
)
UNSUPPORTED_QUERY = "What does Reddit say about this paint?"
PRIVATE_CANARY = "sk-synthetic-private-canary-do-not-retain"


def test_unsupported_query_blocks_before_live_and_does_not_retain_text(
    tmp_path: Path,
) -> None:
    calls: list[GenericProviderProxyRunRequest] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=UNSUPPORTED_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="unsupported-query",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(calls, []),
        fetch_read_runner=_fake_fetch_runner("unused"),
        dprime_model_review_callable=lambda *_args, **_kwargs: {},
        environ={},
    )
    serialized = json.dumps(result.packet, sort_keys=True)

    assert result.return_code == 2
    assert result.packet["relation_plan_consumed"] is False
    assert result.packet["query"] == "unsupported query (not retained)"
    assert result.packet["unsupported_query_retained"] is False
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert calls == []
    assert UNSUPPORTED_QUERY not in serialized
    assert UNSUPPORTED_QUERY not in result.output


def test_supported_query_without_live_confirmation_consumes_plan_only(
    tmp_path: Path,
) -> None:
    calls: list[GenericProviderProxyRunRequest] = []
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="missing-live-confirmation",
        provider_proxy_runner=_recording_proxy_runner(calls, []),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED
    assert result.packet["relation_plan_consumed"] is True
    assert result.packet["relation_plan_id"] == plan["plan_id"]
    assert result.packet["component_id"] == plan["component_id"]
    assert result.packet["source_obligation_id"] == plan["source_obligation_id"]
    assert result.packet["search_requirement_id"] == plan["search_requirement_id"]
    assert result.packet["relation_plan_search_query_seed"] == (
        plan["search_query_seeds"][0]
    )
    assert result.packet["search_query_seed_used"] == result.packet["acquisition_query"]
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert result.packet["dprime_relation_intake_ref"] == {}
    assert calls == []


def test_product_named_single_fact_missing_confirmation_fails_closed(
    tmp_path: Path,
) -> None:
    calls: list[GenericProviderProxyRunRequest] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="product-single-fact-missing-confirmation",
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner(calls, []),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    detail = str(result.packet["blocker_detail"])
    assert result.return_code == 2
    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED
    assert result.packet["entrypoint_kind"] == dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
    assert result.packet["confirmation_flag"] == (
        CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG
    )
    assert CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG in detail
    assert dogfood.CONFIRM_LIVE_DOGFOOD_FLAG not in detail
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert calls == []


def test_product_named_single_fact_accepts_product_output_dir(
    tmp_path: Path,
) -> None:
    calls: list[GenericProviderProxyRunRequest] = []
    product_output_dir = (
        tmp_path / "output" / "current_source_record_single_fact_live_validation_01"
    )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=product_output_dir,
        run_id="product-single-fact-output-dir",
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner(calls, []),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED
    assert result.packet["entrypoint_kind"] == dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
    assert result.packet["diagnostic_dogfood_alias"] is False
    assert product_output_dir.exists()
    assert calls == []


def test_product_single_fact_packet_redacts_synthetic_private_route_config(
    tmp_path: Path,
) -> None:
    calls: list[GenericProviderProxyRunRequest] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "single-fact-canary",
        run_id="product-single-fact-private-canary",
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        fast_provider="OpenAI",
        fast_model=PRIVATE_CANARY,
        fast_model_local_url=PRIVATE_CANARY,
        require_model_assisted_planning=True,
        provider_proxy_runner=_recording_proxy_runner(calls, []),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )
    serialized = json.dumps(result.packet, sort_keys=True)

    assert result.return_code == 2
    assert result.packet["entrypoint_kind"] == dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
    assert result.packet["diagnostic_dogfood_alias"] is False
    assert result.packet["model_assisted_planning_configured_fast_model"] == (
        dogfood.PRIVATE_LOOKING_VALUE_REDACTION
    )
    assert result.packet["model_assisted_planning_configured_local_url_present"] is True
    assert result.packet["raw_private_retention_flags"] == dogfood.RAW_FALSE_FLAGS
    assert PRIVATE_CANARY not in serialized
    assert PRIVATE_CANARY not in result.output
    assert calls == []


def test_provider_failure_detail_redacts_synthetic_private_canary(
    tmp_path: Path,
) -> None:
    calls: list[GenericProviderProxyRunRequest] = []

    def failing_runner(
        request: GenericProviderProxyRunRequest,
    ) -> GenericProviderProxyRunResult:
        calls.append(request)
        return GenericProviderProxyRunResult(
            return_code=2,
            output_path=request.output_path,
            provider_calls_attempted=1,
            provider_calls_completed=0,
            blocker=BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_ROUTE_UNAVAILABLE,
            detail=f"provider failed with {PRIVATE_CANARY}",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "single-fact-provider-detail-canary",
        run_id="product-single-fact-provider-detail-canary",
        confirm_live_dogfood=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=failing_runner,
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )
    serialized = json.dumps(result.packet, sort_keys=True)

    assert result.return_code == 2
    assert len(calls) == 1
    assert result.packet["blocker_detail"] == dogfood.PRIVATE_LOOKING_DETAIL_REDACTION
    assert PRIVATE_CANARY not in serialized
    assert PRIVATE_CANARY not in result.output


def test_strict_fastmodel_route_refs_redact_synthetic_private_values() -> None:
    route = build_strict_accounted_fast_model_planning_route(
        fast_provider="OpenAI",
        fast_model=PRIVATE_CANARY,
        local_url=PRIVATE_CANARY,
        credential_lookup=lambda _name: PRIVATE_CANARY,
    )
    route_ref = route.to_ref()
    diagnostic = StrictAccountedModelRouteResult(
        return_code=2,
        blocker="BLOCKED_SYNTHETIC",
        detail=f"failed with {PRIVATE_CANARY}",
        configured_provider="OpenAI",
        configured_model=PRIVATE_CANARY,
        provider_used="OpenAI",
        model_used=PRIVATE_CANARY,
        credential_present=True,
    ).to_safe_diagnostic()
    serialized = json.dumps({"diagnostic": diagnostic, "route_ref": route_ref})

    assert route_ref["configured_fast_model"] == dogfood.PRIVATE_LOOKING_VALUE_REDACTION
    assert route_ref["configured_local_url_present"] is True
    assert diagnostic["credential_present"] is True
    assert diagnostic["credential_values_retained"] is False
    assert diagnostic["detail"] == "private-looking route detail redacted"
    assert PRIVATE_CANARY not in serialized


def test_dprime_smartmodel_route_ref_redacts_synthetic_private_values() -> None:
    ref = product_smart_model_route_ref(
        smart_provider="OpenAI",
        smart_model=PRIVATE_CANARY,
    )
    serialized = json.dumps(ref, sort_keys=True)

    assert ref["configured_smart_model"] == dogfood.PRIVATE_LOOKING_VALUE_REDACTION
    assert ref["approved_model"] == "gpt-5.4"
    assert PRIVATE_CANARY not in serialized


def test_private_retention_guard_reports_safe_nested_path_without_value(
    tmp_path: Path,
) -> None:
    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "single-fact-path-diagnostic",
        run_id="product-single-fact-path-diagnostic",
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner([], []),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )
    unsafe = dict(result.packet)
    unsafe["semantic_status_payload"] = {
        "dprime_status": {
            "product_model_route_ref": {
                "configured_smart_model": PRIVATE_CANARY,
            },
        },
    }

    with pytest.raises(GenericSingleRelationLiveDogfoodRunError) as excinfo:
        dogfood.validate_generic_single_relation_live_dogfood_packet(unsafe)
    detail = excinfo.value.detail

    assert excinfo.value.blocker == dogfood.BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE
    assert (
        "semantic_status_payload.dprime_status."
        "product_model_route_ref.configured_smart_model"
    ) in detail
    assert "type=str" in detail
    assert "marker=private_prefix_sk" in detail
    assert "category=credential_shaped_private_value" in detail
    assert PRIVATE_CANARY not in detail
    assert "sk-synthetic" not in detail
    assert "sk-" not in detail


def test_private_retention_guard_still_rejects_unsafe_packet_payload(
    tmp_path: Path,
) -> None:
    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "single-fact-unsafe-guard",
        run_id="product-single-fact-unsafe-guard",
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner([], []),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )
    unsafe = dict(result.packet)
    unsafe["answer_or_blocker_text"] = PRIVATE_CANARY

    with pytest.raises(GenericSingleRelationLiveDogfoodRunError) as excinfo:
        dogfood.validate_generic_single_relation_live_dogfood_packet(unsafe)

    assert excinfo.value.blocker == dogfood.BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE
    assert "private-looking values" in excinfo.value.detail
    assert "answer_or_blocker_text" in excinfo.value.detail
    assert "marker=private_prefix_sk" in excinfo.value.detail
    assert PRIVATE_CANARY not in excinfo.value.detail
    assert "sk-synthetic" not in excinfo.value.detail


def test_dogfood_entrypoint_still_rejects_non_dogfood_output_dir(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="must stay under"):
        build_generic_single_relation_live_dogfood_run_output(
            query=SMALL_CLAIMS_QUERY,
            repo_root=tmp_path,
            output_dir=(
                tmp_path
                / "output"
                / "current_source_record_single_fact_live_validation_01"
            ),
            run_id="dogfood-output-dir",
            environ={},
        )


def test_confirmed_product_path_with_missing_tavily_credential_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_tavily(**_kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        raise RuntimeError("TAVILY_API_KEY is not set; secret-value-not-retained")

    monkeypatch.setattr(product_acquisition, "search_web_results", missing_tavily)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="missing-tavily-credential",
        confirm_live_dogfood=True,
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )
    detail = str(result.packet["blocker_detail"]).casefold()

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_CREDENTIAL_UNAVAILABLE
    )
    assert result.packet["relation_plan_consumed"] is True
    assert result.packet["provider_calls_attempted"] == 1
    assert result.packet["provider_calls_completed"] == 0
    assert result.packet["provider_acquisition_route_posture"] == (
        "product_provider_acquisition_adapter_failed_closed"
    )
    assert result.packet["serper_scout_calls_attempted"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert "tavily_api_key" in detail
    assert "secret-value" not in detail
    assert "approved broker" not in detail
    assert "broker/operator" not in detail


def test_default_product_owned_adapter_supplies_tavily_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_generic_query_relation_plan(N400_QUERY)
    tavily_calls: list[dict[str, Any]] = []
    fetch_urls: list[str] = []
    extracted_text = "USCIS lists the current Form N-400 paper filing fee as $760."

    def fake_tavily(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        tavily_calls.append(kwargs)
        return (
            [
                {
                    "title": "USCIS Form N-400 Filing Fee",
                    "url": "https://www.uscis.gov/forms/filing-fees",
                    "domain": "uscis.gov",
                    "snippet": "Current filing fee table.",
                    "raw_content": extracted_text,
                }
            ],
            [],
        )

    monkeypatch.setattr(product_acquisition, "search_web_results", fake_tavily)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="default-product-provider-adapter",
        confirm_live_dogfood=True,
        fetch_read_runner=_recording_fake_fetch_runner(fetch_urls, "unused"),
        environ={},
    )

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    ), result.packet.get("blocker_detail")
    assert tavily_calls[0]["query"] == result.packet["acquisition_query"]
    assert result.packet["relation_plan_search_query_seed"] == (
        plan["search_query_seeds"][0]
    )
    assert tavily_calls[0]["search_depth"] == "basic"
    assert fetch_urls == []
    assert result.packet["planner_marked_ambiguity"] is False
    assert result.packet["provider_calls_attempted"] == 1
    assert result.packet["provider_calls_completed"] == 1
    assert result.packet["serper_scout_calls_attempted"] == 0
    assert result.packet["provider_acquisition_route_posture"] == (
        "product_provider_acquisition_adapter_sanitized_results_to_"
        "plan_derived_retained_artifacts"
    )
    assert result.packet["decision"] != (
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_ROUTE_UNAVAILABLE
    )
    assert result.packet["provider_extracted_content_obtained"] is True
    assert result.packet["source_acquisition_mode"] == (
        "provider_extracted_source_content"
    )
    assert result.packet["direct_fetch_read_attempts"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    fetch_packet = _retained_fetch_packet(result)
    reference = fetch_packet["reference_records"][0]
    assert reference["content_acquisition_provider"] == "tavily"
    assert reference["bounded_text"] == extracted_text
    assert reference["original_source_url"] == "https://www.uscis.gov/forms/filing-fees"
    assert reference["raw_provider_payload_retained"] is False
    assert reference["raw_search_response_retained"] is False
    assert reference["not_citation_eligible"] is True
    assert reference["not_source_obligation_satisfaction"] is True


def test_default_product_owned_adapter_uses_serper_scout_for_ambiguity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query = "What is the current filing fee for the form?"
    scout_calls: list[dict[str, Any]] = []
    tavily_calls: list[dict[str, Any]] = []
    extracted_text = "USCIS lists the current Form N-400 paper filing fee as $760."

    def fake_scout(**kwargs: Any) -> list[dict[str, Any]]:
        scout_calls.append(kwargs)
        return [
            {
                "title": "USCIS Form N-400 Filing Fee",
                "url": "https://www.uscis.gov/forms/filing-fees",
                "domain": "uscis.gov",
                "snippet": "Directionality only scout result.",
                "position": 1,
            }
        ]

    def fake_tavily(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        tavily_calls.append(kwargs)
        return (
            [
                {
                    "title": "USCIS Form N-400 Filing Fee",
                    "url": "https://www.uscis.gov/forms/filing-fees",
                    "domain": "uscis.gov",
                    "snippet": "Current filing fee table.",
                    "raw_content": extracted_text,
                }
            ],
            [],
        )

    monkeypatch.setattr(product_acquisition, "search_scout_results", fake_scout)
    monkeypatch.setattr(product_acquisition, "search_web_results", fake_tavily)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=query,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="default-product-provider-ambiguous",
        confirm_live_dogfood=True,
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    ), result.packet.get("blocker_detail")
    assert scout_calls == [
        {
            "provider": "serper",
            "query": "What is the current filing fee for the form?",
            "max_results": 5,
        }
    ]
    assert len(tavily_calls) == 1
    assert "USCIS Form N-400 Filing Fee" in tavily_calls[0]["query"]
    assert result.packet["planner_marked_ambiguity"] is True
    assert result.packet["serper_scout_calls_attempted"] == 1
    assert result.packet["serper_scout_calls_completed"] == 1
    assert result.packet["extraction_provider_calls_attempted"] == 1
    assert result.packet["provider_acquisition_route_posture"] == (
        "product_provider_acquisition_adapter_sanitized_results_to_"
        "plan_derived_retained_artifacts"
    )
    assert result.packet["serper_output_recorded_as_non_evidence"] is True
    assert result.packet["serper_output_used_as_evidence"] is False
    observation = result.packet["disambiguation_record"]["observations"][0]
    assert observation["not_evidence"] is True
    assert observation["not_source_custody"] is True
    assert observation["not_citation_eligible"] is True
    assert "provider_extracted_text" not in observation
    assert result.packet["provider_extracted_content_obtained"] is True
    assert result.packet["direct_fetch_read_attempts"] == 0


def test_missing_serper_credential_for_ambiguous_scout_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_scout(**_kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError("SERPER_API_KEY is not set; secret-value-not-retained")

    def tavily_must_not_run(**_kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        raise AssertionError("Tavily extraction must not run after scout failure")

    monkeypatch.setattr(product_acquisition, "search_scout_results", missing_scout)
    monkeypatch.setattr(product_acquisition, "search_web_results", tavily_must_not_run)

    result = build_generic_single_relation_live_dogfood_run_output(
        query="What is the current filing fee for the form?",
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="missing-serper-credential",
        confirm_live_dogfood=True,
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )
    detail = str(result.packet["blocker_detail"]).casefold()

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_CREDENTIAL_UNAVAILABLE
    )
    assert result.packet["serper_scout_calls_attempted"] == 1
    assert result.packet["serper_scout_calls_completed"] == 0
    assert result.packet["extraction_provider_calls_attempted"] == 0
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["provider_acquisition_route_posture"] == (
        "product_provider_acquisition_adapter_selected_before_provider_search"
    )
    assert "serper_api_key" in detail
    assert "secret-value" not in detail
    assert "approved broker" not in detail
    assert "broker/operator" not in detail


def test_live_confirmation_without_dprime_stops_after_custody_status(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="no-dprime-confirmation",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [_provider_result("Example County Fee Schedule", _small_claims_url())],
        ),
        fetch_read_runner=_fake_fetch_runner(
            "Example County official fee schedule lists the current small claims "
            "filing fee as $42 for the example case type."
        ),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert calls[0].query == result.packet["acquisition_query"]
    assert result.packet["relation_plan_search_query_seed"] == (
        plan["search_query_seeds"][0]
    )
    assert result.packet["relation_plan_consumed"] is True
    assert result.packet["dprime_relation_intake_candidate_consumed_from_plan"] is True
    assert result.packet["provider_calls_attempted"] == 1
    assert result.packet["provider_calls_completed"] == 1
    assert result.packet["provider_results_returned"] == 1
    assert result.packet["fetch_read_attempts"] == 1
    assert result.packet["fetch_read_completed"] == 1
    assert result.packet["evidence_ledger_admissions"] == 1
    assert result.packet["dprime_review_licensed"] is False
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert result.packet["dprime_model_review_calls_completed"] == 0
    assert result.packet["product_correctness_claimed"] is False


def test_provider_link_field_feeds_generic_fetch_read_adapter_and_custody(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    provider_calls: list[GenericProviderProxyRunRequest] = []
    fetch_urls: list[str] = []
    link = "https://example-county.invalid/small-claims-fees-link"

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="link-field-fetch-read",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            provider_calls,
            [_provider_link_result("Example County Fee Schedule", link)],
        ),
        fetch_read_runner=_recording_fake_fetch_runner(
            fetch_urls,
            "Example County official fee schedule lists the current small claims "
            "filing fee as $42 for the example case type.",
        ),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert provider_calls[0].query == result.packet["acquisition_query"]
    assert result.packet["relation_plan_search_query_seed"] == (
        plan["search_query_seeds"][0]
    )
    assert fetch_urls == [link]
    assert result.packet["provider_results_returned"] == 1
    assert result.packet["fetch_read_attempts"] == 1
    assert result.packet["fetch_read_completed"] == 1
    assert result.packet["evidence_ledger_admissions"] == 1
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert result.packet["raw_provider_payload_retained"] is False
    assert result.packet["raw_search_response_retained"] is False
    assert result.packet["raw_prompt_retained"] is False
    assert result.packet["raw_model_response_retained"] is False
    candidate = result.packet["fetch_read_candidate_diagnostics"][0]
    assert candidate["candidate_id"]
    assert candidate["title"] == "Example County Fee Schedule"
    assert candidate["domain"] == "example-county.invalid"
    assert candidate["url"] == link
    assert candidate["url_source"] == "link"
    assert candidate["selected_for_fetch_read"] is True
    assert candidate["attempted"] is True
    assert "snippet" not in candidate
    assert candidate["provider_snippet_used_as_evidence"] is False
    assert candidate["candidate_diagnostic_satisfies_source_obligation"] is False
    assert result.packet["provider_snippets_used_as_evidence"] is False


def test_public_web_fetch_request_uses_generic_non_secret_headers() -> None:
    request_headers = dogfood._public_web_fetch_read_request_headers()

    assert request_headers == {
        "User-Agent": dogfood.FETCH_READ_PUBLIC_WEB_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
    }
    assert "ScryRaven/1.0" in request_headers["User-Agent"]
    assert "Cookie" not in request_headers
    assert "Referer" not in request_headers
    assert "Authorization" not in request_headers


def test_all_failed_fetch_read_returns_named_blocker_with_counts(
    tmp_path: Path,
) -> None:
    provider_calls: list[GenericProviderProxyRunRequest] = []
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="all-fetch-read-failed",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            provider_calls,
            [
                _provider_result(
                    "Example County Fee Schedule",
                    "https://example-county.invalid/fees",
                    rank=1,
                ),
                _provider_result(
                    "Example County Clerk Fees",
                    "https://example-county.invalid/clerk-fees",
                    rank=2,
                ),
            ],
        ),
        fetch_read_runner=_failing_fetch_runner(fetch_urls),
        environ={},
    )

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES
    )
    assert result.packet["provider_calls_attempted"] == 1
    assert result.packet["provider_calls_completed"] == 1
    assert result.packet["provider_results_returned"] == 2
    assert result.packet["fetch_read_attempts"] == 2
    assert result.packet["fetch_read_completed"] == 0
    assert result.packet["fetch_read_blocker"] == (
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES
    )
    assert "fetch_read_attempt_diagnostics" in result.packet["fetch_read_blocker_detail"]
    assert result.packet["fetch_read_status_class_summary"] == {"unknown": 2}
    assert result.packet["fetch_read_content_type_summary"] == {"unknown": 2}
    assert result.packet["fetch_read_failure_category_summary"] == {
        "FETCH_READ_EXCEPTION": 2
    }
    assert [
        item["failure_category"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == ["FETCH_READ_EXCEPTION", "FETCH_READ_EXCEPTION"]
    assert result.packet["evidence_ledger_admissions"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert result.packet["raw_provider_payload_retained"] is False
    assert result.packet["raw_search_response_retained"] is False
    assert len(fetch_urls) == 2


def test_all_fetch_read_4xx_returns_precise_blocker_and_status_summary(
    tmp_path: Path,
) -> None:
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="all-fetch-read-4xx",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_result(
                    f"Example County Fee Schedule {index}",
                    f"https://example-county.invalid/fees/{index}",
                    rank=index,
                )
                for index in range(1, 4)
            ],
        ),
        fetch_read_runner=_http_status_fetch_runner(fetch_urls, status_code=404),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == (
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ALL_CANDIDATES_4XX
    )
    assert result.packet["provider_calls_attempted"] == 1
    assert result.packet["provider_calls_completed"] == 1
    assert result.packet["provider_results_returned"] == 3
    assert result.packet["fetch_read_attempts"] == 3
    assert result.packet["fetch_read_completed"] == 0
    assert result.packet["fetch_read_blocker"] == (
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ALL_CANDIDATES_4XX
    )
    assert result.packet["fetch_read_status_class_summary"] == {"4xx": 3}
    assert result.packet["fetch_read_content_type_summary"] == {"text/html": 3}
    assert result.packet["fetch_read_failure_category_summary"] == {"HTTP_4XX": 3}
    assert [
        item["failure_category"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == ["HTTP_4XX", "HTTP_4XX", "HTTP_4XX"]
    assert all(
        item["raw_private_retention_flags"]["raw_source_content_retained"] is False
        for item in result.packet["fetch_read_attempt_diagnostics"]
    )
    assert result.packet["evidence_ledger_admissions"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert result.packet["raw_provider_payload_retained"] is False
    assert result.packet["raw_search_response_retained"] is False
    assert result.packet["raw_prompt_retained"] is False
    assert result.packet["raw_model_response_retained"] is False
    assert result.packet["official_http_source_survival_blocker_active"] is False
    assert len(fetch_urls) == 3


def test_official_http_4xx_returns_sharp_source_survival_blocker(
    tmp_path: Path,
) -> None:
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="official-http-source-survival-4xx",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                    rank=1,
                ),
                _provider_result(
                    "USCIS Application for Naturalization",
                    "https://www.uscis.gov/n-400",
                    rank=2,
                ),
                _provider_result(
                    "USCIS Form N-400 Fee Calculator",
                    "https://www.uscis.gov/feecalculator",
                    rank=3,
                ),
            ],
        ),
        fetch_read_runner=_http_status_fetch_runner(fetch_urls, status_code=403),
        environ={},
    )

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX
    )
    assert result.packet["fetch_read_blocker"] == (
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX
    )
    assert result.packet["official_http_source_survival_blocker_available"] is True
    assert result.packet["official_http_source_survival_blocker_active"] is True
    assert result.packet["http_source_survival_scope"] == (
        "ordinary_public_web_fetch_read_hygiene"
    )
    assert result.packet["fetch_read_status_class_summary"] == {"4xx": 3}
    assert result.packet["fetch_read_content_type_summary"] == {"text/html": 3}
    assert result.packet["fetch_read_failure_category_summary"] == {"HTTP_4XX": 3}
    assert [
        item["result_rank"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == [1, 2, 3]
    assert [
        item["fetch_read_priority_rank"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == [1, 2, 3]
    assert all(
        item["official_or_source_record_looking_http_candidate"] is True
        for item in result.packet["fetch_read_attempt_diagnostics"]
    )
    assert all(
        item["source_survival_candidate_signal"] == "source_of_record_looking"
        for item in result.packet["fetch_read_attempt_diagnostics"]
    )
    assert all(
        item["fetch_read_request_profile_id"]
        == dogfood.FETCH_READ_PUBLIC_WEB_REQUEST_PROFILE_ID
        for item in result.packet["fetch_read_attempt_diagnostics"]
    )
    assert all(
        item["final_url"] == item["attempted_url"]
        and item["http_status_code"] == 403
        and item["content_type"] == "text/html"
        for item in result.packet["fetch_read_attempt_diagnostics"]
    )
    assert result.packet["evidence_ledger_admissions"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert result.packet["source_display_entries"] == []
    assert result.packet["raw_provider_payload_retained"] is False
    assert result.packet["raw_search_response_retained"] is False
    assert result.packet["raw_source_content_retained"] is False
    assert result.packet["http_source_survival_access_control_bypass_opened"] is False
    assert result.packet["http_source_survival_login_session_handling_opened"] is False
    assert result.packet["http_source_survival_captcha_handling_opened"] is False
    assert (
        result.packet["http_source_survival_javascript_browser_automation_opened"]
        is False
    )
    assert result.packet["http_source_survival_proxy_rotation_opened"] is False
    assert result.packet["http_source_survival_referer_spoofing_opened"] is False
    assert (
        result.packet["http_source_survival_domain_specific_url_fallback_opened"]
        is False
    )
    assert result.packet["provider_routing_changed"] is True
    assert result.packet["direct_url_fetch_primary_happy_path"] is False
    assert result.packet["direct_url_fetch_fallback_or_diagnostic_only"] is True
    assert result.packet["provider_query_generation_changed"] is True
    assert result.packet["fetch_read_cap_preserved"] is True
    assert result.packet["fetch_read_cap_value"] == 3
    formatted = format_generic_single_relation_live_dogfood_output(
        result.packet,
        packet_path=tmp_path / "packet.json",
    )
    assert "- Fetch/read status classes: 4xx=3" in formatted
    assert "- Fetch/read content types: text/html=3" in formatted
    assert "- Fetch/read failure categories: HTTP_4XX=3" in formatted
    assert "- Official HTTP source-survival blocker active: true" in formatted
    assert len(fetch_urls) == 3


def test_clear_query_uses_extraction_provider_before_direct_fetch(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(N400_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []
    fetch_urls: list[str] = []
    extracted_text = "USCIS lists the current Form N-400 paper filing fee as $760."

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="clear-query-provider-extracted",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                    extracted_text,
                )
            ],
        ),
        fetch_read_runner=_recording_fake_fetch_runner(fetch_urls, "unused"),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert [call.provider for call in calls] == ["tavily"]
    assert calls[0].query == result.packet["acquisition_query"]
    assert result.packet["relation_plan_search_query_seed"] == (
        plan["search_query_seeds"][0]
    )
    assert not hasattr(calls[0], "broker_url")
    assert not hasattr(calls[0], "private_broker_path")
    assert fetch_urls == []
    assert result.packet["fast_planner_used"] is True
    assert result.packet["planner_marked_ambiguity"] is False
    assert result.packet["serper_scout_calls_attempted"] == 0
    assert result.packet["extraction_provider"] == "tavily"
    assert result.packet["extraction_provider_calls_attempted"] == 1
    assert result.packet["provider_acquisition_route_posture"] == (
        "injected_provider_runner_sanitized_results_to_plan_"
        "derived_retained_artifacts"
    )
    assert result.packet["provider_extracted_content_obtained"] is True
    assert result.packet["provider_extracted_original_url_bindings_preserved"] is True
    assert result.packet["source_acquisition_mode"] == (
        "provider_extracted_source_content"
    )
    assert result.packet["direct_fetch_read_attempts"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["fetch_read_completed"] == 1
    assert result.packet["evidence_ledger_admissions"] == 1
    assert result.packet["serper_used_as_primary_source_acquisition"] is False
    assert result.packet["provider_answer_products_used"] is False
    assert result.packet["provider_sourced_answer_used"] is False
    assert result.packet["provider_snippets_used_as_evidence"] is False
    assert result.packet["actual_source_authority_posture_created"] is False
    assert result.packet["candidate_selection_satisfies_source_obligation"] is False
    fetch_packet = _retained_fetch_packet(result)
    reference = fetch_packet["reference_records"][0]
    assert reference["content_acquisition_mode"] == (
        "provider_extracted_source_content"
    )
    assert reference["content_acquisition_provider"] == "tavily"
    assert reference["provider_extracted_source_content"] is True
    assert reference["original_source_url"] == "https://www.uscis.gov/forms/filing-fees"
    assert reference["candidate_url"] == "https://www.uscis.gov/forms/filing-fees"
    assert reference["bounded_text"] == extracted_text
    assert reference["raw_provider_payload_retained"] is False
    assert reference["raw_search_response_retained"] is False
    assert reference["not_citation_eligible"] is True
    assert reference["not_source_obligation_satisfaction"] is True


def test_ambiguous_query_uses_serper_scout_then_extraction_provider(
    tmp_path: Path,
) -> None:
    query = "What is the current filing fee for the form?"
    calls: list[GenericProviderProxyRunRequest] = []
    extracted_text = "USCIS lists the current Form N-400 paper filing fee as $760."

    result = build_generic_single_relation_live_dogfood_run_output(
        query=query,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="ambiguous-query-serper-scout",
        confirm_live_dogfood=True,
        provider_proxy_runner=_routing_proxy_runner(
            calls,
            {
                "serper": [
                    _provider_result(
                        "USCIS Form N-400 Filing Fee",
                        "https://www.uscis.gov/forms/filing-fees",
                    )
                ],
                "tavily": [
                    _provider_extracted_result(
                        "USCIS Form N-400 Filing Fee",
                        "https://www.uscis.gov/forms/filing-fees",
                        extracted_text,
                    )
                ],
            },
        ),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    assert result.return_code == 2
    assert [call.provider for call in calls] == ["serper", "tavily"]
    assert result.packet["planner_marked_ambiguity"] is True
    assert result.packet["run_kernel_local_accounting_authorized_disambiguation"] is True
    assert result.packet["serper_scout_calls_attempted"] == 1
    assert result.packet["serper_output_recorded_as_non_evidence"] is True
    assert result.packet["serper_output_used_as_evidence"] is False
    assert result.packet["disambiguation_record"]["observations"][0]["not_evidence"] is True
    assert result.packet["fast_planner_output"]["serper_scout_used"] is True
    assert result.packet["fast_planner_output"]["planner_revision_source"] == (
        "serper_directionality_bridge_term"
    )
    assert result.packet["extraction_provider_calls_attempted"] == 1
    assert result.packet["provider_extracted_content_obtained"] is True
    assert result.packet["direct_fetch_read_attempts"] == 0


def test_pdf_content_type_is_diagnostic_only_unsupported_content_type(
    tmp_path: Path,
) -> None:
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="pdf-content-type-diagnostic",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_result(
                    "Example County Fee Schedule PDF",
                    "https://example-county.invalid/fees.pdf",
                )
            ],
        ),
        fetch_read_runner=_http_status_fetch_runner(
            fetch_urls,
            status_code=200,
            content_type="application/pdf",
        ),
        environ={},
    )

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES
    )
    assert result.packet["fetch_read_attempts"] == 1
    assert result.packet["fetch_read_completed"] == 0
    assert result.packet["fetch_read_status_class_summary"] == {"2xx": 1}
    assert result.packet["fetch_read_content_type_summary"] == {"application/pdf": 1}
    assert result.packet["fetch_read_failure_category_summary"] == {
        "UNSUPPORTED_CONTENT_TYPE": 1
    }
    attempt = result.packet["fetch_read_attempt_diagnostics"][0]
    assert attempt["content_type"] == "application/pdf"
    assert attempt["failure_category"] == "UNSUPPORTED_CONTENT_TYPE"
    assert attempt["readable_content_type"] is False
    assert attempt["readable_text_obtained"] is False
    assert result.packet["pdf_content_type_support_opened"] is False
    assert result.packet["pdf_parsing_opened"] is False
    assert result.packet["evidence_ledger_admissions"] == 0
    assert result.packet["source_display_entries"] == []


def test_n400_fetch_read_prioritizes_source_of_record_candidates_under_cap(
    tmp_path: Path,
) -> None:
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="n400-source-of-record-priority",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                    rank=1,
                ),
                _provider_result(
                    "ILRC N-400 Fee Guide PDF",
                    "https://www.ilrc.org/sites/default/files/n-400-fee-guide.pdf",
                    rank=2,
                ),
                _provider_result(
                    "USCIS Application for Naturalization",
                    "https://www.uscis.gov/n-400",
                    rank=3,
                ),
                _provider_result(
                    "USCIS Form N-400 Instructions PDF",
                    "https://www.uscis.gov/sites/default/files/document/forms/n-400.pdf",
                    rank=4,
                ),
                _provider_result(
                    "New Americans Campaign N-400 Fee",
                    "https://www.newamericanscampaign.org/n400-fee",
                    rank=5,
                ),
            ],
        ),
        fetch_read_runner=_n400_priority_fetch_runner(fetch_urls),
        environ={},
    )

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES
    )
    assert result.packet["candidate_selection_policy_id"] == (
        "generic_single_relation_live_fetch_read_acquisition_priority_v1"
    )
    assert result.packet["candidate_selection_is_acquisition_only"] is True
    assert result.packet["candidate_selection_created_source_authority"] is False
    assert result.packet["candidate_selection_satisfies_source_obligation"] is False
    assert result.packet["candidate_selection_citation_eligible"] is False
    assert result.packet["candidate_selection_claims_correctness"] is False
    assert result.packet["candidate_ranking_policy_changed"] is False
    assert result.packet["official_http_source_survival_blocker_active"] is False
    assert result.packet["provider_results_returned"] == 5
    assert result.packet["fetch_read_attempts"] == 3
    assert result.packet["fetch_read_completed"] == 0
    assert [urlparse(url).netloc.lower() for url in fetch_urls] == [
        "www.uscis.gov",
        "www.uscis.gov",
        "www.uscis.gov",
    ]
    assert [
        item["result_rank"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == [1, 3, 4]
    assert [
        item["fetch_read_priority_rank"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == [1, 2, 3]
    assert result.packet["fetch_read_status_class_summary"] == {"2xx": 1, "4xx": 2}
    assert result.packet["fetch_read_content_type_summary"] == {
        "application/pdf": 1,
        "text/html": 2,
    }
    assert result.packet["fetch_read_failure_category_summary"] == {
        "HTTP_4XX": 2,
        "UNSUPPORTED_CONTENT_TYPE": 1,
    }

    by_rank = {
        item["result_rank"]: item
        for item in result.packet["fetch_read_candidate_diagnostics"]
    }
    assert by_rank[1]["fetch_read_priority_rank"] == 1
    assert by_rank[3]["fetch_read_priority_rank"] == 2
    assert by_rank[4]["fetch_read_priority_rank"] == 3
    assert by_rank[2]["selected_for_fetch_read"] is False
    assert by_rank[2]["skipped_reason"] == "FETCH_READ_CAP_EXHAUSTED"
    assert by_rank[5]["selected_for_fetch_read"] is False
    assert by_rank[5]["skipped_reason"] == "FETCH_READ_CAP_EXHAUSTED"
    assert by_rank[4]["content_type"] == "application/pdf"
    assert by_rank[4]["failure_category"] == "UNSUPPORTED_CONTENT_TYPE"
    assert by_rank[4]["readable_text_obtained"] is False
    assert result.packet["pdf_content_type_support_opened"] is False
    assert result.packet["pdf_parsing_opened"] is False
    for diagnostic in result.packet["fetch_read_candidate_diagnostics"]:
        features = diagnostic["candidate_selection_features"]
        assert features["feature_posture"] == "discovery_metadata_only"
        assert features["provider_rank"] == diagnostic["provider_rank"]
        assert features["final_fetch_read_priority_rank"] == (
            diagnostic["fetch_read_priority_rank"]
        )
        assert features["features_used_as_evidence"] is False
        assert features["features_create_source_authority"] is False
        assert features["features_satisfy_source_obligation"] is False
        assert features["features_make_candidate_citation_eligible"] is False
        assert features["features_claim_correctness"] is False
        assert diagnostic["not_evidence"] is True
        assert diagnostic["not_citation_eligible"] is True
        assert diagnostic["not_source_obligation_satisfaction"] is True
        assert diagnostic["candidate_selection_created_source_authority"] is False
        assert diagnostic["candidate_selection_satisfies_source_obligation"] is False
        assert diagnostic["candidate_selection_citation_eligible"] is False
        assert diagnostic["candidate_selection_claims_correctness"] is False


def test_candidate_priority_preserves_provider_rank_without_official_signal(
    tmp_path: Path,
) -> None:
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="no-official-signal-provider-rank-stable",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_result(
                    "Independent Filing Fee PDF",
                    "https://independent-fees.org/current-fee.pdf",
                    rank=1,
                ),
                _provider_result(
                    "Immigration Fee Summary",
                    "https://fee-summary.example/current",
                    rank=2,
                ),
                _provider_result(
                    "Naturalization Cost Page",
                    "https://another-fee-source.invalid/current",
                    rank=3,
                ),
            ],
        ),
        fetch_read_runner=_failing_fetch_runner(fetch_urls),
        environ={},
    )

    assert result.return_code == 2
    assert result.packet["fetch_read_attempts"] == 3
    assert fetch_urls == [
        "https://independent-fees.org/current-fee.pdf",
        "https://fee-summary.example/current",
        "https://another-fee-source.invalid/current",
    ]
    assert [
        item["result_rank"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == [1, 2, 3]
    assert [
        item["fetch_read_priority_rank"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == [1, 2, 3]
    assert all(
        item["candidate_selection_features"]["public_agency_domain_signal"] is False
        for item in result.packet["fetch_read_candidate_diagnostics"]
    )
    assert all(
        item["candidate_selection_features"]["source_of_record_domain_signal"]
        is False
        for item in result.packet["fetch_read_candidate_diagnostics"]
    )


def test_no_readable_text_attempt_records_no_readable_text_category(
    tmp_path: Path,
) -> None:
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="no-readable-text-diagnostic",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [_provider_result("Example County Empty Page", _small_claims_url())],
        ),
        fetch_read_runner=_http_status_fetch_runner(fetch_urls, status_code=200),
        environ={},
    )

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES
    )
    assert result.packet["fetch_read_status_class_summary"] == {"2xx": 1}
    assert result.packet["fetch_read_content_type_summary"] == {"text/html": 1}
    assert result.packet["fetch_read_failure_category_summary"] == {
        "NO_READABLE_TEXT": 1
    }
    attempt = result.packet["fetch_read_attempt_diagnostics"][0]
    assert attempt["failure_category"] == "NO_READABLE_TEXT"
    assert attempt["readable_content_type"] is True
    assert attempt["readable_text_obtained"] is False


def test_observability_insufficient_blocker_is_available_when_metadata_hidden(
    tmp_path: Path,
) -> None:
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="observability-insufficient",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [_provider_result("Example County Fee Schedule", _small_claims_url())],
        ),
        fetch_read_runner=_unknown_fetch_failure_runner(fetch_urls),
        environ={},
    )

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_OBSERVABILITY_INSUFFICIENT
    )
    assert result.packet["fetch_read_status_class_summary"] == {"unknown": 1}
    assert result.packet["fetch_read_content_type_summary"] == {"unknown": 1}
    assert result.packet["fetch_read_failure_category_summary"] == {"UNKNOWN": 1}
    assert result.packet["fetch_read_attempt_diagnostics"][0]["failure_category"] == (
        "UNKNOWN"
    )


def test_partial_fetch_read_4xx_then_success_reaches_custody_admission(
    tmp_path: Path,
) -> None:
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="partial-fetch-read-survival",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_result(
                    "Example County Archived Fee Schedule",
                    "https://example-county.invalid/archived-fees",
                    rank=1,
                ),
                _provider_result(
                    "Example County Current Fee Schedule",
                    "https://example-county.invalid/current-fees",
                    rank=2,
                ),
            ],
        ),
        fetch_read_runner=_first_4xx_then_success_fetch_runner(
            fetch_urls,
            "Example County official fee schedule lists the current small claims "
            "filing fee as $42 for the example case type.",
        ),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert result.packet["provider_results_returned"] == 2
    assert result.packet["fetch_read_attempts"] == 2
    assert result.packet["fetch_read_completed"] == 1
    assert result.packet["fetch_read_status_class_summary"] == {"2xx": 1, "4xx": 1}
    assert result.packet["fetch_read_content_type_summary"] == {"text/html": 2}
    assert result.packet["fetch_read_failure_category_summary"] == {"HTTP_4XX": 1}
    assert [
        item["failure_category"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == ["HTTP_4XX", None]
    assert result.packet["evidence_ledger_admissions"] == 1
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert result.packet["source_display_entries"] == []
    assert result.packet["product_correctness_claimed"] is False
    assert result.packet["fap_author_opened"] is False
    assert len(fetch_urls) == 2


def test_official_http_source_survival_continues_when_later_html_survives(
    tmp_path: Path,
) -> None:
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="official-http-survival-after-4xx",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_result(
                    "USCIS Archived Form N-400 Filing Fee",
                    "https://www.uscis.gov/archive/n-400-fees",
                    rank=1,
                ),
                _provider_result(
                    "USCIS Current Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                    rank=2,
                ),
            ],
        ),
        fetch_read_runner=_first_4xx_then_success_fetch_runner(
            fetch_urls,
            "USCIS lists the current Form N-400 paper filing fee as $760.",
        ),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert result.packet["official_http_source_survival_blocker_active"] is False
    assert result.packet["fetch_read_attempts"] == 2
    assert result.packet["fetch_read_completed"] == 1
    assert result.packet["evidence_ledger_admissions"] == 1
    assert result.packet["fetch_read_status_class_summary"] == {"2xx": 1, "4xx": 1}
    assert result.packet["fetch_read_content_type_summary"] == {"text/html": 2}
    assert result.packet["fetch_read_failure_category_summary"] == {"HTTP_4XX": 1}
    assert [
        item["failure_category"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == ["HTTP_4XX", None]
    assert all(
        item["official_or_source_record_looking_http_candidate"] is True
        for item in result.packet["fetch_read_attempt_diagnostics"]
    )
    assert [
        item["readable_text_obtained"]
        for item in result.packet["fetch_read_attempt_diagnostics"]
    ] == [False, True]
    assert result.packet["raw_source_content_retained"] is False
    assert result.packet["actual_source_authority_posture_created"] is False
    assert result.packet["provider_snippets_used_as_evidence"] is False
    assert result.packet["candidate_diagnostics_satisfy_source_obligations"] is False
    assert result.packet["fetch_read_failure_metadata_citation_eligible"] is False
    assert result.packet["fetch_read_failure_metadata_satisfies_source_obligations"] is False
    assert result.packet["pdf_parsing_opened"] is False
    assert result.packet["fap_author_opened"] is False
    assert result.packet["product_correctness_claimed"] is False
    assert len(fetch_urls) == 2


def test_fetch_read_attempt_cap_limits_failed_candidates_to_three(
    tmp_path: Path,
) -> None:
    provider_calls: list[GenericProviderProxyRunRequest] = []
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="fetch-read-cap",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            provider_calls,
            [
                _provider_result(
                    f"Example County Fee Schedule {index}",
                    f"https://example-county.invalid/fees/{index}",
                    rank=index,
                )
                for index in range(1, 6)
            ],
        ),
        fetch_read_runner=_failing_fetch_runner(fetch_urls),
        environ={},
    )

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES
    )
    assert result.packet["provider_results_returned"] == 5
    assert result.packet["fetch_read_attempts"] == 3
    assert result.packet["fetch_read_completed"] == 0
    assert result.packet["fetch_read_blocker"] == (
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES
    )
    assert len(result.packet["fetch_read_candidate_diagnostics"]) == 5
    skipped = result.packet["fetch_read_candidate_diagnostics"][3:]
    assert [item["attempted"] for item in skipped] == [False, False]
    assert [item["skipped_reason"] for item in skipped] == [
        "FETCH_READ_CAP_EXHAUSTED",
        "FETCH_READ_CAP_EXHAUSTED",
    ]
    assert len(result.packet["fetch_read_attempt_diagnostics"]) == 3
    assert result.packet["evidence_ledger_admissions"] == 0
    assert len(fetch_urls) == 3


def test_provider_result_without_url_or_link_records_missing_url_diagnostic(
    tmp_path: Path,
) -> None:
    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="missing-url-or-link",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [_provider_result_without_url("Example County Fee Schedule")],
        ),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == (
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_CANDIDATE_CONTRACT_MISSING
    )
    assert result.packet["provider_calls_attempted"] == 1
    assert result.packet["provider_calls_completed"] == 1
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["fetch_read_completed"] == 0
    assert result.packet["fetch_read_failure_category_summary"] == {"MISSING_URL": 1}
    candidate = result.packet["fetch_read_candidate_diagnostics"][0]
    assert candidate["url_source"] == "missing"
    assert candidate["url_valid"] is False
    assert candidate["attempted"] is False
    assert candidate["skipped_reason"] == "MISSING_URL"
    assert candidate["failure_category"] == "MISSING_URL"
    assert result.packet["evidence_ledger_admissions"] == 0
    assert result.packet["raw_provider_payload_retained"] is False
    assert result.packet["raw_search_response_retained"] is False


def test_provider_result_with_invalid_url_records_invalid_url_diagnostic(
    tmp_path: Path,
) -> None:
    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="invalid-provider-url",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [_provider_invalid_url_result("Example County Fee Schedule")],
        ),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == (
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_CANDIDATE_CONTRACT_MISSING
    )
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["fetch_read_failure_category_summary"] == {"INVALID_URL": 1}
    candidate = result.packet["fetch_read_candidate_diagnostics"][0]
    assert candidate["url_source"] == "url"
    assert candidate["url"] == "not-a-valid-url"
    assert candidate["url_valid"] is False
    assert candidate["skipped_reason"] == "INVALID_URL"
    assert candidate["failure_category"] == "INVALID_URL"
    assert candidate["raw_private_retention_flags"]["raw_provider_payload_retained"] is False


def test_product_single_fact_cli_consumes_existing_dprime_answer_path_for_n400(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(N400_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []
    review_calls = 0

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal review_calls
        review_calls += 1
        return _assessment_payload(
            plan,
            "USCIS Form N-400 paper filing fee is $760.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="product-n400-answer-path",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                )
            ],
        ),
        fetch_read_runner=_fake_fetch_runner(
            "USCIS lists the current Form N-400 paper filing fee as $760."
        ),
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert result.return_code == 0, result.packet.get("blocker_detail")
    assert result.decision == "PASS"
    assert result.packet["blocker_code"] is None
    assert result.packet["command_flag"] == MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG
    assert result.packet["confirmation_flag"] == (
        CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG
    )
    assert result.packet["entrypoint_kind"] == dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
    assert result.packet["diagnostic_dogfood_alias"] is False
    assert result.packet["supported_query_class"] == (
        dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS
    )
    assert result.packet["answer_text_present"] is True
    assert result.packet["product_answer_text"]
    assert result.packet["final_answer_packet_created"] is True
    assert result.packet["author_answer_created"] is True
    assert result.packet["citation_source_display_created"] is True
    assert result.packet["product_correctness_claimed"] is False
    assert result.packet["source_display_entries"]
    assert review_calls == 1

    semantic_payload = result.packet["semantic_status_payload"]
    dprime_status = semantic_payload["dprime_status"]
    assert semantic_payload["dprime_source_citation_authority_enabled"] is True
    assert semantic_payload["dprime_single_lane_answer_path_enabled"] is True
    assert dprime_status["objects_created"]["final_answer_packet"] is True
    assert dprime_status["objects_created"]["author_answer"] is True
    assert dprime_status["objects_created"]["citation_source_display"] is True
    answer_path_ref = result.packet["dprime_answer_path_ref"]
    assert answer_path_ref["status"] == "consumed"
    assert answer_path_ref["final_answer_packet_ref"]["packet_created"] is True
    assert answer_path_ref["author_answer_ref"]["author_prose_status"] in {
        "full_answer_prose_created",
        "partial_answer_prose_created",
    }
    assert answer_path_ref["citation_source_display_ref"]["status"] == "created"
    assert answer_path_ref["product_correctness_claimed"] is False

    integration = result.packet["single_relation_dprime_authority_integration"]
    assert integration["status"] == "consumed"
    assert integration["blocker_code"] == "PASS"
    assert integration["dprime_single_lane_answer_path_enabled"] is True
    assert integration["source_obligation_authority_consumed"] is True
    assert integration["citation_source_handoff_authority_consumed"] is True
    assert integration["final_answer_packet_created"] is True
    assert integration["author_answer_created"] is True
    assert integration["citation_source_display_created"] is True
    assert integration["product_correctness_claimed"] is False

    boundary = result.packet["source_citation_display_boundary"]
    assert boundary["status"] == "created"
    assert boundary["blocker_code"] == "PASS"
    assert boundary["authority_source"] == "core.dprime_single_lane_answer_path_runtime"
    assert boundary["derived_from_dprime_authority"] is True
    assert boundary["derived_from_gateway_only"] is False
    assert result.packet["source_citation_display_entries_created"] is True
    assert result.packet["source_citation_display_entries"]
    assert BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED not in {
        result.decision,
        result.packet["blocker_code"],
    }
    assert "FAP, Author" not in result.packet["answer_or_blocker_text"]
    assert "remain unclaimed" not in result.packet["answer_or_blocker_text"]
    assert "Final answer prose" not in result.packet["answer_or_blocker_text"]
    assert "SufficiencyReadiness" in result.packet["answer_or_blocker_text"]
    assert "hardened FinalAnswerPacket" in result.packet["answer_or_blocker_text"]
    assert "AuthorProse" in result.packet["answer_or_blocker_text"]
    assert "Product answer text: " in result.output
    assert result.packet["product_answer_text"] in result.output
    assert "FinalAnswerPacket created: true" in result.output
    assert "FAP/Author consumed through existing D-prime path: true" in result.output
    assert "Product correctness claimed: false." in result.output
    assert "FAP created: false" not in result.output
    assert "Author invoked: false" not in result.output
    serialized = json.dumps(result.packet, sort_keys=True).casefold()
    assert "bounded_text" not in serialized
    assert result.packet["raw_prompt_retained"] is False
    assert result.packet["raw_model_response_retained"] is False
    assert result.packet["raw_provider_payload_retained"] is False


def test_product_single_fact_redacts_live_semantic_model_route_ref_canary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_generic_query_relation_plan(N400_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []

    def unsafe_route_ref(**_kwargs: Any) -> dict[str, Any]:
        ref = product_smart_model_route_ref(
            smart_provider="OpenAI",
            smart_model="gpt-5.4",
        )
        ref["configured_smart_model"] = PRIVATE_CANARY
        return ref

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return _assessment_payload(
            plan,
            "USCIS Form N-400 paper filing fee is $760.",
        )

    monkeypatch.setattr(
        semantic_status_runtime,
        "product_smart_model_route_ref",
        unsafe_route_ref,
    )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="product-n400-semantic-route-canary",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                )
            ],
        ),
        fetch_read_runner=_fake_fetch_runner(
            "USCIS lists the current Form N-400 paper filing fee as $760."
        ),
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )
    serialized = json.dumps(result.packet, sort_keys=True)
    route_ref = result.packet["semantic_status_payload"]["dprime_status"][
        "product_model_route_ref"
    ]

    assert result.return_code == 0, result.packet.get("blocker_detail")
    assert result.decision == "PASS"
    assert route_ref["configured_smart_model"] == (
        dogfood.PRIVATE_LOOKING_VALUE_REDACTION
    )
    assert PRIVATE_CANARY not in serialized
    assert PRIVATE_CANARY not in result.output
    assert "sk-synthetic" not in serialized
    assert "sk-synthetic" not in result.output
    assert len(calls) == 1


def test_product_single_fact_cli_reports_exact_dprime_answer_path_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_generic_query_relation_plan(N400_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return _assessment_payload(
            plan,
            "USCIS Form N-400 paper filing fee is $760.",
        )

    def blocked_answer_path(*_args: Any, **_kwargs: Any) -> None:
        raise DPrimeSingleLaneAnswerPathError(
            "BLOCKED_DPRIME_AUTHOR_OUTPUT_AUTHORITY_MISSING",
            "Author/answer output did not create answer text",
            "Author/answer output",
        )

    monkeypatch.setattr(
        semantic_status_runtime,
        "build_dprime_single_lane_answer_path",
        blocked_answer_path,
    )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="product-n400-answer-path-blocked",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                )
            ],
        ),
        fetch_read_runner=_fake_fetch_runner(
            "USCIS lists the current Form N-400 paper filing fee as $760."
        ),
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert result.return_code == 2
    assert result.decision == "BLOCKED_DPRIME_AUTHOR_OUTPUT_AUTHORITY_MISSING"
    assert result.packet["blocker_code"] == result.decision
    assert result.packet["failure_attribution_bucket"] == "dprime_answer_path"
    assert result.packet["answer_text_present"] is False
    assert result.packet["product_answer_text"] == ""
    assert result.packet["product_correctness_claimed"] is False
    assert result.packet["answer_path_existing_blocker"] == result.decision
    assert result.packet["answer_path_next_blocked_surface"] == (
        "Author/answer output"
    )
    answer_path_ref = result.packet["dprime_answer_path_ref"]
    assert answer_path_ref["status"] == "blocked"
    assert answer_path_ref["blocker"] == result.decision
    assert answer_path_ref["next_blocked_surface"] == "Author/answer output"
    integration = result.packet["single_relation_dprime_authority_integration"]
    assert integration["status"] == "consumed"
    assert integration["blocker_code"] == result.decision
    assert integration["dprime_single_lane_answer_path_enabled"] is True
    assert integration["source_obligation_authority_consumed"] is True
    assert integration["citation_source_handoff_authority_consumed"] is True
    assert integration["author_answer_created"] is False
    assert BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED not in {
        result.decision,
        result.packet["blocker_code"],
    }


@pytest.mark.parametrize(
    ("query", "title", "url", "bounded_text", "answer_claim"),
    [
        (
            SMALL_CLAIMS_QUERY,
            "Example County Fee Schedule",
            "https://example-county.gov/small-claims-fees",
            "Example County official fee schedule lists the current small claims "
            "filing fee as $42 for the example case type.",
            "Example County small claims filing fee is $42.",
        ),
    ],
)
def test_dprime_pass_ready_gateway_creates_authority_backed_display_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    title: str,
    url: str,
    bounded_text: str,
    answer_claim: str,
) -> None:
    plan = build_generic_query_relation_plan(query)
    calls: list[GenericProviderProxyRunRequest] = []
    review_calls = 0

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal review_calls
        review_calls += 1
        return _assessment_payload(plan, answer_claim)

    def fail_if_answer_path_called(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("generic dogfood stop-point mode opened answer path")

    monkeypatch.setattr(
        semantic_status_runtime,
        "build_dprime_single_lane_answer_path",
        fail_if_answer_path_called,
    )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=query,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id=f"pass-{abs(hash(query))}",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        entrypoint_surface=(
            dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE
            if query == N400_QUERY
            else dogfood.DOGFOOD_ENTRYPOINT_SURFACE
        ),
        entrypoint_kind=(
            dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
            if query == N400_QUERY
            else dogfood.DOGFOOD_ENTRYPOINT_KIND
        ),
        diagnostic_dogfood_alias=query != N400_QUERY,
        supported_query_class=(
            dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS
            if query == N400_QUERY
            else dogfood.DOGFOOD_SUPPORTED_QUERY_CLASS
        ),
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [_provider_result(title, url)],
        ),
        fetch_read_runner=_fake_fetch_runner(bounded_text),
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )
    serialized = json.dumps(result.packet, sort_keys=True).casefold()

    assert result.return_code == 2, result.packet.get("blocker_detail")
    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED
    assert result.packet["blocker_code"] == result.decision
    assert result.packet["failure_attribution_bucket"] == (
        "source_citation_display_boundary"
    )
    assert review_calls == 1
    assert calls[0].query == result.packet["acquisition_query"]
    assert result.packet["relation_plan_search_query_seed"] == (
        plan["search_query_seeds"][0]
    )
    assert result.packet["relation_plan_consumed"] is True
    if query == N400_QUERY:
        assert result.packet["command_flag"] == (
            MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG
        )
        assert result.packet["confirmation_flag"] == (
            CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG
        )
        assert result.packet["entrypoint_surface"] == (
            dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE
        )
        assert result.packet["entrypoint_kind"] == (
            dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
        )
        assert result.packet["diagnostic_dogfood_alias"] is False
        assert result.packet["supported_query_class"] == (
            dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS
        )
        assert "current source-of-record single-fact run" in result.output
        assert MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG in (
            result.packet["command_harness_used"]
        )
        assert CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG in (
            result.packet["command_harness_used"]
        )
        assert dogfood.CONFIRM_LIVE_DOGFOOD_FLAG not in (
            result.packet["command_harness_used"]
        )
    else:
        assert result.packet["command_flag"] == MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG
        assert result.packet["confirmation_flag"] == dogfood.CONFIRM_LIVE_DOGFOOD_FLAG
        assert result.packet["entrypoint_surface"] == dogfood.DOGFOOD_ENTRYPOINT_SURFACE
        assert result.packet["entrypoint_kind"] == dogfood.DOGFOOD_ENTRYPOINT_KIND
        assert result.packet["diagnostic_dogfood_alias"] is True
        assert result.packet["supported_query_class"] == (
            dogfood.DOGFOOD_SUPPORTED_QUERY_CLASS
        )
        assert "generic single-relation live dogfood run" in result.output
    assert result.packet["relation_plan_id"] == plan["plan_id"]
    assert result.packet["supported_query_class_id"] == MVP_SUPPORTED_QUERY_CLASS_ID
    assert result.packet["source_authority_posture_contract_ref"] == (
        plan["source_authority_posture_contract_ref"]
    )
    assert result.packet["source_authority_posture_requirement_ref"] == (
        plan["source_authority_posture_requirement"]["requirement_id"]
    )
    assert result.packet["component_id"] == plan["component_id"]
    assert result.packet["component_text"] == plan["component_text"]
    assert result.packet["source_obligation_id"] == plan["source_obligation_id"]
    assert result.packet["search_requirement_id"] == plan["search_requirement_id"]
    assert result.packet["search_query_seed_used"] == result.packet["acquisition_query"]
    assert result.packet["relation_plan_dprime_relation_intake_candidate"][
        "component_id"
    ] == plan["component_id"]
    assert result.packet["dprime_relation_intake_candidate_consumed_from_plan"] is True
    assert result.packet["provider_calls_attempted"] == 1
    assert result.packet["provider_results_returned"] == 1
    assert result.packet["fetch_read_attempts"] == 1
    assert result.packet["evidence_ledger_admissions"] == 1
    assert result.packet["dprime_model_review_calls_attempted"] == 1
    assert result.packet["dprime_model_review_calls_completed"] == 1
    gateway = result.packet["source_readiness_gateway"]
    assert gateway["status"] == "ready"
    assert result.packet["source_readiness_gateway_status"] == "ready"
    assert gateway["selected_current_value_text"] == answer_claim
    assert gateway["selected_current_value_display_status"] == (
        "displayed_from_current_path_admitted_dprime_state"
    )
    assert gateway["selected_current_value_ref"]["value_source"] == (
        "dprime_assessment_material_ref.answer_component_claim.claim"
    )
    assert gateway["selected_current_value_ref"]["not_final_answer_prose"] is True
    assert gateway["selected_source_ref"]["title"] == title
    assert gateway["selected_source_ref"]["url"] == url
    assert gateway["selected_source_ref"]["candidate_id"]
    assert gateway["selected_window_ref"]["selected_window_digest"]
    assert gateway["selected_window_ref"]["evidence_window_ref"]
    assert gateway["explicit_non_claims"] == {
        "source_obligation_satisfied": False,
        "citation_eligible": False,
        "source_authority_finalized": False,
        "final_answer_packet_created": False,
        "author_prose_created": False,
        "product_correctness_claimed": False,
    }
    assert result.packet["product_answer_text"] == ""
    assert result.packet["answer_text_present"] is False
    assert result.packet["source_display_entries"] == []
    semantic_payload = result.packet["semantic_status_payload"]
    dprime_status = semantic_payload["dprime_status"]
    assert semantic_payload["dprime_downstream_authority_enabled"] is False
    assert semantic_payload["dprime_source_citation_authority_enabled"] is True
    assert semantic_payload["dprime_single_lane_answer_path_enabled"] is False
    assert semantic_payload["dprime_source_citation_stoppoint_status"] == "consumed"
    assert dprime_status["objects_created"]["semantic_observation"] is True
    assert dprime_status["objects_created"]["component_coverage"] is True
    assert dprime_status["source_obligation_authority_consumed"] is True
    assert (
        dprime_status["citation_eligibility_or_source_handoff_authority_consumed"]
        is True
    )
    assert dprime_status["single_lane_answer_path_disabled_by_caller"] is True
    assert dprime_status["objects_created"]["final_answer_packet"] is False
    assert dprime_status["objects_created"]["author_answer"] is False
    assert dprime_status["objects_created"]["citation_source_display"] is False
    integration = result.packet["single_relation_dprime_authority_integration"]
    assert integration["status"] == "consumed"
    assert (
        integration["blocker_code"]
        == BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED
    )
    assert result.packet["single_relation_dprime_authority_integration_status"] == (
        "consumed"
    )
    assert result.packet["source_obligation_citation_readiness_status"] == "consumed"
    assert result.packet["source_obligation_citation_readiness_blocker"] == (
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED
    )
    assert result.packet["dprime_source_citation_stoppoint_status"] == "consumed"
    assert result.packet["source_obligation_authority_consumed"] is True
    assert result.packet["citation_source_handoff_authority_consumed"] is True
    assert integration["existing_dprime_authority_referenced"] is True
    assert integration["existing_dprime_authority_reused"] is True
    assert integration[
        "existing_dprime_source_obligation_citation_authority_exists"
    ] is True
    assert integration["existing_dprime_source_obligation_citation_authority_module"] == (
        "core.dprime_source_obligation_citation_authority_runtime"
    )
    assert integration["existing_single_lane_answer_path_module"] == (
        "core.dprime_single_lane_answer_path_runtime"
    )
    assert integration["dprime_downstream_authority_enabled"] is False
    assert integration["dprime_source_citation_authority_enabled"] is True
    assert integration["dprime_single_lane_answer_path_enabled"] is False
    assert integration["generic_dogfood_downstream_authority_kept_disabled"] is True
    assert integration["generic_dogfood_single_lane_answer_path_kept_disabled"] is True
    assert integration["dprime_support_slice_present"] is True
    assert integration["gateway_display_present"] is True
    assert integration["gateway_treated_as_authority"] is False
    assert integration["source_readiness_gateway_is_authority"] is False
    assert integration["dprime_support_slice_treated_as_readiness"] is False
    assert integration[
        "gateway_ready_and_dprime_pass_insufficient_for_"
        "source_obligation_citation_readiness"
    ] is False
    assert integration["dprime_source_citation_authority_invoked"] is True
    assert integration["downstream_dprime_authority_invoked"] is True
    assert integration["component_coverage_created"] is True
    assert integration["semantic_observation_created"] is True
    assert integration["source_obligation_authority_consumed"] is True
    assert integration["citation_source_handoff_authority_consumed"] is True
    assert integration["single_relation_source_obligation_ready"] is True
    assert integration["single_relation_citation_handoff_ready"] is True
    assert result.packet["single_relation_source_obligation_ready"] is True
    assert result.packet["single_relation_citation_handoff_ready"] is True
    assert integration["source_citation_authority_refs_are_dprime_runtime_refs"] is True
    source_authority = integration["source_obligation_authority_ref"]
    citation_handoff = integration["citation_source_handoff_authority_ref"]
    assert source_authority["owner"] == "RunKernel.DPrimeSourceObligationAuthority"
    assert source_authority["runtime_surface"] == (
        "core.dprime_source_obligation_citation_authority_runtime"
    )
    assert source_authority["authority_consumed"] is True
    assert source_authority["source_obligation_authority_id"]
    assert source_authority["source_obligation_authority_digest"]
    assert source_authority != gateway
    assert citation_handoff["owner"] == (
        "RunKernel.DPrimeCitationSourceHandoffAuthority"
    )
    assert citation_handoff["runtime_surface"] == (
        "core.dprime_source_obligation_citation_authority_runtime"
    )
    assert citation_handoff["authority_consumed"] is True
    assert citation_handoff["citation_source_handoff_consumed"] is True
    assert citation_handoff["citation_source_handoff_id"]
    assert citation_handoff["citation_source_handoff_digest"]
    assert citation_handoff != gateway
    boundary = result.packet["source_citation_display_boundary"]
    entries = result.packet["source_citation_display_entries"]
    assert boundary["status"] == "created"
    assert (
        boundary["blocker_code"]
        == BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED
    )
    assert result.packet["source_citation_display_boundary_status"] == "created"
    assert (
        result.packet["source_citation_display_boundary_blocker"]
        == BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED
    )
    assert boundary["authority_source"] == (
        "core.dprime_source_obligation_citation_authority_runtime"
    )
    assert result.packet["source_citation_display_authority_source"] == (
        "core.dprime_source_obligation_citation_authority_runtime"
    )
    assert boundary["derived_from_dprime_authority"] is True
    assert boundary["derived_from_gateway_only"] is False
    assert boundary["gateway_treated_as_authority"] is False
    assert result.packet["source_citation_display_derived_from_dprime_authority"] is True
    assert result.packet["source_citation_display_derived_from_gateway_only"] is False
    assert boundary["source_obligation_authority_ref_owner"] == (
        "RunKernel.DPrimeSourceObligationAuthority"
    )
    assert boundary["citation_source_handoff_authority_ref_owner"] == (
        "RunKernel.DPrimeCitationSourceHandoffAuthority"
    )
    assert boundary["source_obligation_authority_ref"][
        "source_obligation_authority_digest"
    ] == source_authority["source_obligation_authority_digest"]
    assert boundary["citation_source_handoff_authority_ref"][
        "citation_source_handoff_digest"
    ] == citation_handoff["citation_source_handoff_digest"]
    assert result.packet["source_citation_display_entries_created"] is True
    assert len(entries) == 1
    entry = entries[0]
    assert entry["source_title"] == citation_handoff["citation_source_records"][0][
        "title"
    ]
    assert entry["source_url"] == url
    assert entry["selected_current_value_display_text"] == answer_claim
    assert entry["selected_window_digest"] == gateway["selected_window_ref"][
        "selected_window_digest"
    ]
    assert entry["source_obligation_authority_digest"] == source_authority[
        "source_obligation_authority_digest"
    ]
    assert entry["citation_source_handoff_digest"] == citation_handoff[
        "citation_source_handoff_digest"
    ]
    assert entry["derived_from_dprime_authority"] is True
    assert entry["derived_from_gateway_only"] is False
    assert entry["citation_rendering_created"] is False
    assert entry["final_answer_prose_created"] is False
    assert entry["product_correctness_claimed"] is False
    assert boundary["sufficiency_readiness_created"] is False
    assert boundary["final_answer_prose_created"] is False
    assert boundary["final_answer_packet_created"] is False
    assert boundary["author_answer_created"] is False
    assert boundary["author_invoked"] is False
    assert boundary["citation_rendering_invoked"] is False
    assert boundary["final_citation_rendering_created"] is False
    assert boundary["product_correctness_claimed"] is False
    assert result.packet["final_citation_rendering_created"] is False
    assert integration["source_obligation_satisfied"] is False
    assert integration["citation_eligible"] is False
    assert integration["source_authority_finalized"] is False
    assert integration["final_answer_packet_created"] is False
    assert integration["author_prose_created"] is False
    assert integration["author_answer_created"] is False
    assert integration["citation_source_display_created"] is False
    assert integration["product_correctness_claimed"] is False
    assert integration["next_phase"] == (
        dogfood.SOURCE_CITATION_DISPLAY_BOUNDARY_NEXT_PHASE
    )
    assert integration["next_product_path_checkpoint"] == (
        dogfood.SOURCE_CITATION_DISPLAY_BOUNDARY_NEXT_PHASE
    )
    assert boundary["next_product_path_checkpoint"] == (
        dogfood.SOURCE_CITATION_DISPLAY_BOUNDARY_NEXT_PHASE
    )
    assert result.packet["next_product_path_checkpoint"] == (
        dogfood.SOURCE_CITATION_DISPLAY_BOUNDARY_NEXT_PHASE
    )
    assert dogfood.DPRIME_AUTHORITY_INTEGRATION_NEXT_PHASE not in result.output
    assert result.packet["actual_source_authority_posture_created"] is False
    assert result.packet["product_correctness_claimed"] is False
    assert result.packet["friend_level_mvp_claimed"] is False
    assert result.packet["general_supported_query_mvp_claimed"] is False
    assert result.packet["source_obligation_satisfied"] is False
    assert result.packet["citation_eligible"] is False
    assert result.packet["source_authority_finalized"] is False
    assert result.packet["final_answer_packet_created"] is False
    assert result.packet["author_prose_created"] is False
    assert result.packet["citation_source_display_created"] is False
    assert result.packet["citation_rendering_invoked"] is False
    assert result.packet["multi_component_planning_opened"] is False
    assert result.packet["runkernel_dag_scheduling_opened"] is False
    assert result.packet["fap_author_opened"] is False
    assert result.packet["followup_loop_count"] == 0
    assert result.packet["raw_provider_payload_retained"] is False
    assert result.packet["raw_search_response_retained"] is False
    assert result.packet["raw_prompt_retained"] is False
    assert result.packet["raw_model_response_retained"] is False
    assert "Source/readiness gateway" in result.output
    assert "D-prime authority integration" in result.output
    assert "Source/citation display boundary" in result.output
    assert "- Entries created: true" in result.output
    assert "- Derived from D-prime authority: true" in result.output
    assert "- Derived from gateway-only state: false" in result.output
    assert "D-prime pass + gateway display sufficient for readiness: false." in (
        result.output
    )
    assert "- Boundary-only FAP created: false." in result.output
    assert "- Boundary-only Author invoked: false." in result.output
    assert "- Final answer prose created: false." in result.output
    assert "passport" not in serialized
    assert "travel.state.gov" not in serialized


def test_ready_gateway_and_dprime_slice_still_block_without_source_citation_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_generic_query_relation_plan(N400_QUERY)
    answer_claim = "USCIS lists the current Form N-400 paper filing fee as $760."

    def fake_semantic_status(**_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            decision="PASS",
            payload={
                "dprime_downstream_authority_enabled": False,
                "dprime_source_citation_authority_enabled": False,
                "dprime_single_lane_answer_path_enabled": False,
                "generic_relation_intake_consumed_by_product_status": True,
                "dprime_relation_intake_ref": {
                    "status": "consumed",
                    "component_id": plan["component_id"],
                    "source_obligation_candidate_ids": [
                        plan["source_obligation_id"]
                    ],
                    "source_title": "USCIS Form N-400 Filing Fee",
                    "source_url": "https://www.uscis.gov/forms/filing-fees",
                    "source_domain": "www.uscis.gov",
                    "candidate_id": "candidate:n400",
                    "candidate_digest": "candidate-digest:n400",
                },
                "source_evidence_admission_ref": {
                    "status": "custody_created",
                    "candidate_id": "candidate:n400",
                    "candidate_digest": "candidate-digest:n400",
                    "reference_id": "reference:n400",
                    "reference_digest": "reference-digest:n400",
                },
                "source_obligation_authority_ref": {
                    "status": "not reached",
                    "authority_consumed": False,
                },
                "citation_eligibility_authority_ref": {
                    "status": "not reached",
                    "authority_consumed": False,
                },
                "dprime_status": {
                    "assessment_status": "assessed",
                    "support_relation": "directly_supports",
                    "proposal_validation_status": (
                        "DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED"
                    ),
                    "run_kernel_admission_decision_status": "admitted",
                    "semantic_observation_admission_status": "materialized",
                    "source_obligation_authority_consumed": False,
                    "citation_eligibility_or_source_handoff_authority_consumed": (
                        False
                    ),
                    "objects_created": {
                        "semantic_observation": True,
                        "component_coverage": False,
                        "final_answer_packet": False,
                        "author_answer": False,
                        "citation_source_display": False,
                    },
                    "assessment_material_ref": {
                        "assessment_id": "assessment:n400",
                        "assessment_digest": "assessment-digest:n400",
                        "answer_component_claim": {
                            "component_id": plan["component_id"],
                            "claim": answer_claim,
                        },
                    },
                    "semantic_observation_ref": {
                        "observation_id": "semantic-observation:n400",
                        "observation_digest": "semantic-digest:n400",
                    },
                    "input_packet_ref": {
                        "selected_window_diagnostic_ref": {
                            "bounded_content_digest": "window-digest:n400",
                            "bounded_character_count": 80,
                            "value_token_observed": True,
                        },
                        "evidence_window_ref": {
                            "bounded_content_digest": "window-digest:n400",
                            "bounded_character_count": 80,
                            "window_text_retained": False,
                            "window_text_printed": False,
                        },
                    },
                },
            },
        )

    monkeypatch.setattr(dogfood, "build_live_semantic_coverage_status", fake_semantic_status)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="gateway-ready-no-source-citation-authority",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                )
            ],
        ),
        fetch_read_runner=_fake_fetch_runner(answer_claim),
        dprime_model_review_callable=lambda *_args, **_kwargs: {},
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    integration = result.packet["single_relation_dprime_authority_integration"]
    assert result.return_code == 2
    assert result.decision == dogfood.BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD
    assert result.packet["source_readiness_gateway_status"] == "ready"
    assert integration["status"] == "blocked"
    assert integration["gateway_display_present"] is True
    assert integration["dprime_support_slice_present"] is True
    assert integration["source_obligation_authority_consumed"] is False
    assert integration["citation_source_handoff_authority_consumed"] is False
    assert result.packet["source_obligation_authority_consumed"] is False
    assert result.packet["citation_source_handoff_authority_consumed"] is False
    assert integration["single_relation_source_obligation_ready"] is False
    assert integration["single_relation_citation_handoff_ready"] is False
    assert integration["gateway_treated_as_authority"] is False
    boundary = result.packet["source_citation_display_boundary"]
    assert boundary["status"] == "not_reached"
    assert boundary["source_citation_display_entries"] == []
    assert boundary["source_citation_display_entries_created"] is False
    assert boundary["derived_from_dprime_authority"] is False
    assert boundary["derived_from_gateway_only"] is False
    assert boundary["gateway_treated_as_authority"] is False
    assert result.packet["source_citation_display_entries"] == []
    assert result.packet["source_citation_display_entries_created"] is False
    assert result.packet["source_citation_display_derived_from_dprime_authority"] is False
    assert result.packet["source_citation_display_derived_from_gateway_only"] is False


def test_dprime_pass_without_stable_selected_value_fails_closed_at_gateway(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_generic_query_relation_plan(N400_QUERY)

    def fake_semantic_status(**_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            decision="PASS",
            payload={
                "generic_relation_intake_consumed_by_product_status": True,
                "dprime_relation_intake_ref": {
                    "status": "consumed",
                    "component_id": plan["component_id"],
                    "source_obligation_candidate_ids": [
                        plan["source_obligation_id"]
                    ],
                    "source_title": "USCIS Form N-400 Filing Fee",
                    "source_url": "https://www.uscis.gov/forms/filing-fees",
                    "source_domain": "www.uscis.gov",
                    "candidate_id": "candidate:n400",
                    "candidate_digest": "candidate-digest:n400",
                },
                "source_evidence_admission_ref": {
                    "status": "custody_created",
                    "candidate_id": "candidate:n400",
                    "candidate_digest": "candidate-digest:n400",
                    "reference_id": "reference:n400",
                    "reference_digest": "reference-digest:n400",
                },
                "dprime_status": {
                    "assessment_status": "assessed",
                    "support_relation": "directly_supports",
                    "validated_support_proposal_available": True,
                    "proposal_validation_status": (
                        "DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED"
                    ),
                    "run_kernel_admission_decision_status": "admitted",
                    "semantic_observation_admission_status": "materialized",
                    "objects_created": {
                        "semantic_observation": True,
                        "component_coverage": False,
                        "final_answer_packet": False,
                        "author_answer": False,
                        "citation_source_display": False,
                    },
                    "model_review_status": "completed",
                    "model_review_call_count": 1,
                    "assessment_material_ref": {
                        "assessment_id": "assessment:n400",
                        "assessment_digest": "assessment-digest:n400",
                        "answer_component_claim": {
                            "component_id": plan["component_id"],
                        },
                    },
                    "semantic_observation_ref": {
                        "observation_id": "semantic-observation:n400",
                        "observation_digest": "semantic-digest:n400",
                        "owner": "RunKernel.SemanticObservationAdmission",
                    },
                    "input_packet_ref": {
                        "selected_window_diagnostic_ref": {
                            "bounded_content_digest": "window-digest:n400",
                            "bounded_character_count": 80,
                            "value_token_observed": True,
                        },
                        "evidence_window_ref": {
                            "bounded_content_digest": "window-digest:n400",
                            "bounded_character_count": 80,
                            "window_text_retained": False,
                            "window_text_printed": False,
                        },
                    },
                },
            },
        )

    monkeypatch.setattr(dogfood, "build_live_semantic_coverage_status", fake_semantic_status)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="gateway-missing-selected-value",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                )
            ],
        ),
        fetch_read_runner=_fake_fetch_runner(
            "USCIS lists the current Form N-400 paper filing fee as $760."
        ),
        dprime_model_review_callable=lambda *_args, **_kwargs: {},
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    gateway = result.packet["source_readiness_gateway"]

    assert result.return_code == 2
    assert result.decision == (
        dogfood.BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_STATE_MISSING
    )
    assert gateway["status"] == "blocked"
    assert gateway["blocker_code"] == result.decision
    assert "selected_current_value_text" in gateway["blocker_detail"]
    assert result.packet["selected_current_value_text_present"] is False
    assert result.packet["answer_text_present"] is False
    assert result.packet["product_answer_text"] == ""
    assert result.packet["source_display_entries"] == []
    assert "Source/readiness gateway" in result.output
    assert "Blocked before answer" in result.output


def test_caps_fail_closed_when_provider_returns_too_many_results(
    tmp_path: Path,
) -> None:
    result_count = 6
    calls: list[GenericProviderProxyRunRequest] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="provider-cap",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_result(
                    f"Example County Fee Schedule {index}",
                    f"https://example-county.invalid/fees/{index}",
                    rank=index,
                )
                for index in range(1, result_count + 1)
            ],
        ),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED
    assert result.packet["caps_exhausted"] is True
    assert result.packet["provider_calls_attempted"] == 1
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0


def test_existing_fixed_live_dogfood_and_query_plan_paths_remain_unchanged(
    tmp_path: Path,
) -> None:
    fixed = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="fixed-confirmation-required",
    )
    plan = build_generic_query_plan_status_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_query_plan_01",
        run_id="query-plan-unchanged",
    )

    assert fixed.decision == BLOCKED_MVP_LIVE_CONFIRMATION_REQUIRED
    assert fixed.packet["status_flag"] == MVP_LIVE_DOGFOOD_RUN_FLAG
    assert plan.return_code == 0
    assert plan.packet_path.name == MVP_QUERY_PLAN_PACKET_NAME
    assert plan.packet["planning_status"] == "planned"
    assert plan.packet["live_calls_made"] is False
    assert plan.packet["model_calls_made"] is False


def test_cli_route_skips_key_validation_until_dprime_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dotenv_calls = 0

    def fake_dotenv() -> bool:
        nonlocal dotenv_calls
        dotenv_calls += 1
        return True

    no_review = initialize_product_model_route_config(
        [MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG, "--query", SMALL_CLAIMS_QUERY],
        load_dotenv_func=fake_dotenv,
        environ={},
    )
    with_review = initialize_product_model_route_config(
        [
            MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
            "--query",
            SMALL_CLAIMS_QUERY,
            CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
        ],
        load_dotenv_func=fake_dotenv,
        environ={},
    )

    assert no_review.dotenv_skipped_for_status_dry_run is True
    assert no_review.dotenv_helper_invoked is False
    assert with_review.dotenv_skipped_for_status_dry_run is False
    assert with_review.dotenv_helper_invoked is True
    assert dotenv_calls == 1

    cli = importlib.import_module("proplex.__main__")
    captured: dict[str, Any] = {}

    def fail_key_validation(**_kwargs: Any) -> list[str]:
        raise AssertionError("generic live dogfood must preempt model key validation")

    def fake_live_run(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return type(
            "FakeResult",
            (),
            {"return_code": 2, "output": "fake generic live blocker"},
        )()

    monkeypatch.setattr(cli, "_build_logger", lambda _verbose: None)
    monkeypatch.setattr(cli, "missing_required_api_keys", fail_key_validation)
    monkeypatch.setattr(
        cli,
        "build_generic_single_relation_live_dogfood_run_output",
        fake_live_run,
    )

    rc = cli.main(
        [
            MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
            "--query",
            SMALL_CLAIMS_QUERY,
            "--fast-provider",
            "OpenRouter",
            "--fast-model",
            "fast-planner-model",
            "--local-url",
            "http://localhost:5678/v1",
            "--smart-provider",
            "OpenAI",
            "--smart-model",
            "smart-dprime-model",
            "--confirm-live-dogfood",
        ]
    )

    assert rc == 2
    assert captured["query"] == SMALL_CLAIMS_QUERY
    assert captured["confirm_live_dogfood"] is True
    assert captured["confirm_live_dprime_review"] is False
    assert captured["entrypoint_surface"] == dogfood.DOGFOOD_ENTRYPOINT_SURFACE
    assert captured["entrypoint_kind"] == dogfood.DOGFOOD_ENTRYPOINT_KIND
    assert captured["diagnostic_dogfood_alias"] is True
    assert captured["supported_query_class"] == dogfood.DOGFOOD_SUPPORTED_QUERY_CLASS
    assert captured["fast_provider"] == "OpenRouter"
    assert captured["fast_model"] == "fast-planner-model"
    assert captured["fast_model_local_url"] == "http://localhost:5678/v1"
    assert captured["smart_provider"] == "OpenAI"
    assert captured["smart_model"] == "smart-dprime-model"
    assert callable(captured["fast_model_planner_callable"])
    assert captured["fast_model_planner_clean_json_response"] is cli.clean_json_response
    route_ref = captured["fast_model_planner_strict_route_ref"]
    serialized_route_ref = json.dumps(route_ref, sort_keys=True)
    assert route_ref["model_task"] == "model_assisted_single_relation_planning"
    assert route_ref["product_model_role"] == "fast"
    assert route_ref["product_route_kind"] == "strict_accounted_fast_model_route"
    assert route_ref["configured_fast_provider"] == "OpenRouter"
    assert route_ref["configured_fast_model"] == "fast-planner-model"
    assert route_ref["configured_endpoint_kind"] == "chat_completions_compatible"
    assert route_ref["configured_local_url_present"] is True
    assert route_ref["configured_local_url_posture"] == "local_configured_not_retained"
    assert route_ref["strict_one_shot"] is True
    assert route_ref["retry_policy"] == "forbidden"
    assert route_ref["fallback_policy"] == "forbidden"
    assert route_ref["provider_switching_allowed"] is False
    assert route_ref["endpoint_switching_allowed"] is False
    assert "smart-dprime-model" not in serialized_route_ref
    assert "http://localhost:5678/v1" not in serialized_route_ref
    assert "broker_url" not in captured
    assert "private_broker_path" not in captured
    assert "env_file_paths" not in captured
    assert "fake generic live blocker" in capsys.readouterr().out


def test_product_named_single_fact_cli_uses_same_generic_runtime(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = importlib.import_module("proplex.__main__")
    captured: dict[str, Any] = {}

    def fail_key_validation(**_kwargs: Any) -> list[str]:
        raise AssertionError("product-supported query CLI must preempt key validation")

    def fake_live_run(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return type(
            "FakeResult",
            (),
            {"return_code": 2, "output": "fake product single-fact blocker"},
        )()

    monkeypatch.setattr(cli, "_build_logger", lambda _verbose: None)
    monkeypatch.setattr(cli, "missing_required_api_keys", fail_key_validation)
    monkeypatch.setattr(
        cli,
        "build_generic_single_relation_live_dogfood_run_output",
        fake_live_run,
    )

    rc = cli.main(
        [
            MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
            "--query",
            N400_QUERY,
            CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
            "--confirm-live-dprime-review",
        ]
    )

    assert rc == 2
    assert captured["query"] == N400_QUERY
    assert captured["confirm_live_dogfood"] is True
    assert captured["confirm_live_dprime_review"] is True
    assert captured["entrypoint_surface"] == (
        dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE
    )
    assert captured["entrypoint_kind"] == dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
    assert captured["diagnostic_dogfood_alias"] is False
    assert captured["supported_query_class"] == (
        dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS
    )
    assert callable(captured["fast_model_planner_callable"])
    assert captured["fast_model_planner_clean_json_response"] is cli.clean_json_response
    assert "broker_url" not in captured
    assert "private_broker_path" not in captured
    assert "fake product single-fact blocker" in capsys.readouterr().out


def test_cli_env_fastmodel_config_flows_into_strict_route(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = importlib.import_module("proplex.__main__")
    captured: dict[str, Any] = {}

    def fake_live_run(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return type(
            "FakeResult",
            (),
            {"return_code": 2, "output": "fake env generic live blocker"},
        )()

    monkeypatch.setenv("SCRYRAVEN_FAST_PROVIDER", "Local (LM Studio)")
    monkeypatch.setenv("SCRYRAVEN_FAST_MODEL", "env-fast-planner-model")
    monkeypatch.setenv("SCRYRAVEN_LOCAL_URL", "http://localhost:6789/v1")
    monkeypatch.setenv("SCRYRAVEN_SMART_PROVIDER", "OpenAI")
    monkeypatch.setenv("SCRYRAVEN_SMART_MODEL", "env-smart-dprime-model")
    monkeypatch.setattr(cli, "_build_logger", lambda _verbose: None)
    monkeypatch.setattr(
        cli,
        "build_generic_single_relation_live_dogfood_run_output",
        fake_live_run,
    )

    rc = cli.main(
        [
            MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
            "--query",
            SMALL_CLAIMS_QUERY,
            "--confirm-live-dogfood",
        ]
    )

    route_ref = captured["fast_model_planner_strict_route_ref"]
    serialized_route_ref = json.dumps(route_ref, sort_keys=True)
    assert rc == 2
    assert captured["fast_provider"] == "Local (LM Studio)"
    assert captured["fast_model"] == "env-fast-planner-model"
    assert captured["fast_model_local_url"] == "http://localhost:6789/v1"
    assert captured["smart_model"] == "env-smart-dprime-model"
    assert route_ref["configured_fast_provider"] == "Local (LM Studio)"
    assert route_ref["configured_fast_model"] == "env-fast-planner-model"
    assert route_ref["configured_endpoint_kind"] == "chat_completions_compatible"
    assert route_ref["configured_local_url_present"] is True
    assert route_ref["configured_local_url_posture"] == "local_configured_not_retained"
    assert "env-smart-dprime-model" not in serialized_route_ref
    assert "http://localhost:6789/v1" not in serialized_route_ref
    assert "fake env generic live blocker" in capsys.readouterr().out


def test_new_flag_is_registered_as_default_off_status_path() -> None:
    cli = importlib.import_module("proplex.__main__")
    assert MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG in PRODUCT_STATUS_DRY_RUN_FLAGS
    assert (
        MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG
        in PRODUCT_STATUS_DRY_RUN_FLAGS
    )
    assert MVP_QUERY_PLAN_STATUS_FLAG in PRODUCT_STATUS_DRY_RUN_FLAGS
    assert initialize_product_model_route_config(
        [MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG, "--query", N400_QUERY],
        load_dotenv_func=lambda: True,
        environ={},
    ).dotenv_skipped_for_status_dry_run is True
    assert initialize_product_model_route_config(
        [
            MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
            "--query",
            N400_QUERY,
            CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
        ],
        load_dotenv_func=lambda: True,
        environ={},
    ).dotenv_skipped_for_status_dry_run is False
    parsed = cli._parse_args(
        [
            MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
            "--query",
            N400_QUERY,
            CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
        ]
    )
    assert parsed.mvp_current_source_of_record_single_fact_run is True
    assert parsed.confirm_current_source_of_record_single_fact_run is True


def test_static_guards_do_not_open_closed_runtime_surfaces() -> None:
    imported, called = _module_static_shape(MODULE_PATH)
    adapter_imported, adapter_called = _module_static_shape(ADAPTER_MODULE_PATH)
    test_imported, test_called = _module_static_shape(TEST_PATH)
    module_text = MODULE_PATH.read_text(encoding="utf-8")
    adapter_text = ADAPTER_MODULE_PATH.read_text(encoding="utf-8")
    forbidden_imports = {
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.author_execution_runtime",
        "core.author_prose_finalization_runtime",
        "core.dprime_evidence_support_bundle_runtime",
        "core.dprime_single_lane_answer_path_runtime",
        "core.dprime_source_obligation_citation_authority_runtime",
        "core.final_answer_packet_runtime",
        "core.social_signal_controller",
        "core.social_signal_scoring",
        "proplex.mvp_live_dogfood_run",
        "subprocess",
        "scripts.request_provider_proxy_broker",
        "scripts.run_provider_proxy_broker_once",
    }
    forbidden_calls = {
        "run_pipeline",
        "build_mvp_live_dogfood_run_output",
        "build_dprime_single_lane_answer_path",
        "consume_dprime_source_obligation_and_citation_authority",
        "run_provider_proxy_helper_once",
    }
    forbidden_test_imports = {
        "openai",
        "requests",
        "subprocess",
        "scripts.run_provider_proxy_broker_once",
    }
    forbidden_test_calls = {
        "fetch_public_url_once",
        "run_provider_proxy_helper_once",
    }
    forbidden_policy_text = {
        "approved_domains",
        "authority_score",
        "domain_allowlist",
        "domain_blocklist",
    }
    forbidden_product_route_text = {
        "DEFAULT_PRIVATE_BROKER_PATH",
        "SCRYRAVEN_BROKER_TOKEN",
        "ScryRavenLiveBroker",
        "broker_url",
        "private_broker_path",
        "provider_broker_posture",
        "run_provider_proxy_helper_once",
    }

    assert imported.isdisjoint(forbidden_imports)
    assert "core.run_kernel" in imported
    assert "authorize_single_relation_source_obligation_recovery" in module_text
    assert "run_kernel.reduce(observation)" in module_text
    assert "dprime_downstream_authority_enabled=False" in module_text
    assert "dprime_source_citation_authority_enabled=True" in module_text
    assert "product_single_fact_answer_path_enabled" in module_text
    assert "PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND" in module_text
    assert "DOGFOOD_ENTRYPOINT_KIND" in module_text
    assert (
        "BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD"
        in module_text
    )
    assert "core.dprime_source_obligation_citation_authority_runtime" in module_text
    assert adapter_imported.isdisjoint(forbidden_imports)
    assert called.isdisjoint(forbidden_calls)
    assert adapter_called.isdisjoint(forbidden_calls)
    assert test_imported.isdisjoint(forbidden_test_imports)
    assert test_called.isdisjoint(forbidden_test_calls)
    assert not any(text in module_text for text in forbidden_policy_text)
    assert not any(text in module_text for text in forbidden_product_route_text)
    assert not any(text in adapter_text for text in forbidden_product_route_text)


def _recording_proxy_runner(
    calls: list[GenericProviderProxyRunRequest],
    results: list[dict[str, Any]],
) -> Any:
    def runner(request: GenericProviderProxyRunRequest) -> GenericProviderProxyRunResult:
        calls.append(request)
        payload = {
            "request_kind": "provider_proxy_search",
            "provider": request.provider,
            "operation": request.operation,
            "result_count": len(results),
            "results": results,
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        }
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return GenericProviderProxyRunResult(
            return_code=0,
            output_path=request.output_path,
            provider_calls_attempted=1,
            provider_calls_completed=1,
        )

    return runner


def _routing_proxy_runner(
    calls: list[GenericProviderProxyRunRequest],
    results_by_provider: Mapping[str, list[dict[str, Any]]],
) -> Any:
    def runner(request: GenericProviderProxyRunRequest) -> GenericProviderProxyRunResult:
        calls.append(request)
        results = results_by_provider.get(request.provider, [])
        payload = {
            "request_kind": "provider_proxy_search",
            "provider": request.provider,
            "operation": request.operation,
            "result_count": len(results),
            "results": results,
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        }
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return GenericProviderProxyRunResult(
            return_code=0,
            output_path=request.output_path,
            provider_calls_attempted=1,
            provider_calls_completed=1,
        )

    return runner


def _fake_fetch_runner(text: str) -> Any:
    def runner(url: str) -> GenericLiveFetchReadResult:
        parsed = urlparse(url)
        return GenericLiveFetchReadResult(
            attempted_url=url,
            final_url=url,
            final_domain=parsed.netloc.lower(),
            status_code=200,
            status_class="2xx",
            content_type="text/html",
            fetched_byte_count=512,
            sanitized_text=text,
            content_title="Fake Source",
            redirect_count=0,
            retrieved_or_observed_at="2026-07-03T00:00:00+00:00",
        )

    return runner


def _recording_fake_fetch_runner(fetch_urls: list[str], text: str) -> Any:
    def runner(url: str) -> GenericLiveFetchReadResult:
        fetch_urls.append(url)
        return _fake_fetch_runner(text)(url)

    return runner


def _failing_fetch_runner(fetch_urls: list[str]) -> Any:
    def runner(url: str) -> GenericLiveFetchReadResult:
        fetch_urls.append(url)
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "offline fake fetch failed safely",
        )

    return runner


def _http_status_fetch_runner(
    fetch_urls: list[str],
    *,
    status_code: int,
    content_type: str = "text/html",
    sanitized_text: str = "",
) -> Any:
    def runner(url: str) -> GenericLiveFetchReadResult:
        fetch_urls.append(url)
        parsed = urlparse(url)
        return GenericLiveFetchReadResult(
            attempted_url=url,
            final_url=url,
            final_domain=parsed.netloc.lower(),
            status_code=status_code,
            status_class=f"{status_code // 100}xx",
            content_type=content_type,
            fetched_byte_count=0,
            sanitized_text=sanitized_text,
            content_title="Fetch failed",
            redirect_count=0,
            retrieved_or_observed_at="2026-07-03T00:00:00+00:00",
        )

    return runner


def _n400_priority_fetch_runner(fetch_urls: list[str]) -> Any:
    def runner(url: str) -> GenericLiveFetchReadResult:
        if url.endswith(".pdf"):
            return _http_status_fetch_runner(
                fetch_urls,
                status_code=200,
                content_type="application/pdf",
            )(url)
        return _http_status_fetch_runner(fetch_urls, status_code=404)(url)

    return runner


def _unknown_fetch_failure_runner(fetch_urls: list[str]) -> Any:
    def runner(url: str) -> GenericLiveFetchReadResult:
        fetch_urls.append(url)
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "offline fake fetch failed without diagnostic metadata",
            fetch_status_class="unknown",
            fetch_content_type="unknown",
            fetch_readable_content_type="unknown",
            fetch_readable_text_obtained=False,
            fetch_failure_category="UNKNOWN",
        )

    return runner


def _first_4xx_then_success_fetch_runner(fetch_urls: list[str], text: str) -> Any:
    calls = 0

    def runner(url: str) -> GenericLiveFetchReadResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _http_status_fetch_runner(fetch_urls, status_code=404)(url)
        return _recording_fake_fetch_runner(fetch_urls, text)(url)

    return runner


def _provider_result(title: str, url: str, *, rank: int = 1) -> dict[str, Any]:
    return {
        "title": title,
        "url": url,
        "domain": urlparse(url).netloc.lower(),
        "snippet": f"{title} states the current filing fee.",
        "published_or_observed_date": "2026-07-03",
        "result_rank": rank,
        "provider_call_index": 1,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _provider_extracted_result(
    title: str,
    url: str,
    extracted_text: str,
    *,
    rank: int = 1,
) -> dict[str, Any]:
    result = _provider_result(title, url, rank=rank)
    result.update(
        {
            "provider_extracted_text": extracted_text,
            "provider_extracted_text_sanitized": True,
            "provider_extracted_text_bounded": True,
            "provider_extracted_text_char_count": len(extracted_text),
            "provider_extracted_text_digest": dogfood._digest_json(
                {"provider_extracted_text": extracted_text}
            ),
            "provider_extracted_source_text_digest": dogfood._digest_json(
                {"provider_extracted_text": extracted_text}
            ),
            "provider_extracted_content_type": "text/html",
            "provider_extracted_at": "2026-07-03T00:00:00+00:00",
        }
    )
    return result


def _provider_link_result(title: str, link: str, *, rank: int = 1) -> dict[str, Any]:
    result = _provider_result(title, link, rank=rank)
    result["link"] = result.pop("url")
    return result


def _provider_result_without_url(title: str, *, rank: int = 1) -> dict[str, Any]:
    return {
        "title": title,
        "domain": "example-county.invalid",
        "snippet": f"{title} states the current filing fee.",
        "published_or_observed_date": "2026-07-03",
        "result_rank": rank,
        "provider_call_index": 1,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _provider_invalid_url_result(title: str, *, rank: int = 1) -> dict[str, Any]:
    result = _provider_result(title, "https://example-county.invalid/fees", rank=rank)
    result["url"] = "not-a-valid-url"
    return result


def _assessment_payload(plan: Mapping[str, Any], answer_claim: str) -> dict[str, Any]:
    component_text = str(plan["component_text"])
    return {
        "source_proposition": f"The retained source states: {answer_claim}",
        "answer_component_claim": {
            "component_id": plan["component_id"],
            "claim": answer_claim,
        },
        "support_relation": "directly_supports",
        "required_qualifiers": [component_text],
        "observed_qualifiers": [component_text],
        "missing_qualifiers": [],
        "scope_check": {"status": "passed"},
        "currentness_check": {"status": "current"},
        "contradiction_check": {"status": "absent"},
        "evidential_adequacy_notes": (
            "The fake review maps the retained source proposition to the same "
            "plan-derived component."
        ),
        "non_support_reason_when_not_direct": "",
        "producer_abstained": False,
        "challenge_recommended": False,
        "closed_surface_flags": {
            "model_review_licensed": False,
            "assessment_created": False,
            "validated_support_proposal_created": False,
            "run_kernel_support_admission_request_created": False,
            "semantic_observation_created": False,
            "component_coverage_bound": False,
            "citation_eligibility_claimed": False,
            "source_obligation_satisfaction_claimed": False,
            "answer_text_created": False,
            "product_correctness_claimed": False,
        },
    }


def _small_claims_url() -> str:
    return "https://example-county.invalid/small-claims-fees"


def _retained_fetch_packet(result: Any) -> dict[str, Any]:
    root = Path(result.retained_artifact_root)
    path = root / dogfood.FETCH_READ_ARTIFACT_DIR / dogfood.FETCH_READ_CONTENT_PACKET_NAME
    return json.loads(path.read_text(encoding="utf-8"))


def _module_static_shape(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    return imported, called
