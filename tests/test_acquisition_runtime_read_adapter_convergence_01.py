from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core.acquisition_adapters import AcquisitionTransports, dispatch_acquisition
from core.acquisition_contracts import (
    AcquisitionArtifactKind,
    AcquisitionExecutionStatus,
    AcquisitionRequest,
)
from core.generic_product_provider_acquisition import (
    ProductProviderAcquisitionRequest,
    ProductProviderAcquisitionResult,
    run_generic_product_provider_acquisition,
)
from core.provider_plan import ProviderPlan
from core.routing import (
    AcquisitionCapability,
    DiscoverQualifier,
    GeneralDeepAuthorization,
    ProviderCapabilityRequest,
    RouteFidelity,
    route_provider_capability,
)
from tests.helpers.offline_ordinary_pipeline import scrub_offline_runtime
from tests.test_ag_ordinary_live_source_custody_integration_01 import (
    CANDIDATE_URL,
    FakeSourceFetchRead,
    _candidate_results,
    _run_pipeline,
)

READ_URL = "https://official.example.test/source"
ROOT_URL = "https://docs.example.test/guide"
OBSERVED_AT = "2026-07-17T00:00:00Z"


def _route(
    capability: AcquisitionCapability,
    *,
    linkup: bool = True,
    tavily: bool = True,
    typed_runtime_only: bool = False,
) -> Any:
    return route_provider_capability(
        ProviderCapabilityRequest(capability=capability),
        {"linkup": linkup, "tavily": tavily},
        typed_runtime_only=typed_runtime_only,
    )


def _read_request(*, linkup: bool = True, tavily: bool = True) -> AcquisitionRequest:
    return AcquisitionRequest(
        acquisition_job_id="read-job-1",
        route_decision=_route(
            AcquisitionCapability.READ,
            linkup=linkup,
            tavily=tavily,
        ),
        selected_urls=(READ_URL,),
        max_retained_characters=20_000,
        candidate_reference="candidate-1",
    )


def _tavily_typed_request(
    capability: AcquisitionCapability,
    **kwargs: Any,
) -> AcquisitionRequest:
    return AcquisitionRequest(
        acquisition_job_id=f"{capability.value.casefold()}-job-1",
        route_decision=_route(capability, typed_runtime_only=True),
        **kwargs,
    )


def test_selected_candidate_read_reaches_existing_packet_and_evidence_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrub_offline_runtime(monkeypatch, available_search_providers=("tavily",))
    fetcher = FakeSourceFetchRead()

    _captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    projection = outcome.execution_trace["ordinary_live_source_custody"]
    assert projection["source_candidate"]["url"] == CANDIDATE_URL
    assert projection["read_route_decision"]["selected_provider"] == "linkup"
    assert projection["read_route_decision"]["operation"] == "fetch"
    assert projection["read_acquisition_job"]["status"] == "succeeded"
    assert projection["fetch_read_content_packet_ref"]["packet_id"]
    assert projection["evidence_ledger_custody_count"] == 1
    assert projection["evidence_ledger_custody_ref"]["custody_record_id"]
    assert len(fetcher.calls) == 1
    assert harness.forbidden_live_calls == []


def test_linkup_route_time_unavailable_selects_tavily_extract_once() -> None:
    request = _read_request(linkup=False, tavily=True)
    calls: list[dict[str, Any]] = []

    def tavily_extract(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(payload)
        return {
            "results": [{"url": READ_URL, "raw_content": "Readable material."}],
            "failed_results": [],
        }

    result = dispatch_acquisition(
        request,
        transports=AcquisitionTransports(tavily_extract=tavily_extract),
    )

    assert request.route_decision.selected_provider == "tavily"
    assert request.route_decision.operation == "extract"
    assert result.succeeded is True
    assert result.provider_calls_attempted == 1
    assert len(calls) == 1
    artifact = result.artifacts[0]
    assert artifact.requested_url == READ_URL
    assert artifact.attempted_url == READ_URL
    assert artifact.provider_reported_url == READ_URL
    assert artifact.resolved_url is None
    assert artifact.final_url is None
    assert artifact.canonical_url is None
    assert artifact.http_status is None


def test_minimal_linkup_read_preserves_unknown_lineage_and_explicit_rendering() -> None:
    payloads: list[dict[str, Any]] = []
    request = _read_request()

    def linkup_fetch(payload: dict[str, Any]) -> dict[str, Any]:
        payloads.append(payload)
        return {"markdown": "Readable minimal Linkup material."}

    result = dispatch_acquisition(
        request,
        transports=AcquisitionTransports(linkup_fetch=linkup_fetch),
    )

    assert result.succeeded is True
    assert payloads == [
        {
            "url": READ_URL,
            "extractImages": False,
            "includeRawHtml": False,
            "renderJs": False,
        }
    ]
    assert request.to_trace()["render_javascript"] is False
    artifact = result.artifacts[0]
    assert artifact.requested_url == READ_URL
    assert artifact.attempted_url == READ_URL
    assert artifact.provider_reported_url is None
    assert artifact.resolved_url is None
    assert artifact.final_url is None
    assert artifact.canonical_url is None
    assert artifact.http_status is None


def test_selected_linkup_failure_is_typed_and_never_calls_tavily() -> None:
    linkup_calls = 0
    tavily_calls = 0

    def linkup_fetch(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal linkup_calls
        linkup_calls += 1
        raise RuntimeError("offline fixture failure")

    def tavily_extract(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal tavily_calls
        tavily_calls += 1
        return {}

    result = dispatch_acquisition(
        _read_request(),
        transports=AcquisitionTransports(
            linkup_fetch=linkup_fetch,
            tavily_extract=tavily_extract,
        ),
    )

    assert result.status is AcquisitionExecutionStatus.FAILED
    assert result.failure_code == "selected_provider_transport_failed"
    assert result.transport_posture == "selected_adapter_failed_no_fallback"
    assert result.provider_calls_attempted == 1
    assert linkup_calls == 1
    assert tavily_calls == 0


def test_read_preserves_redirect_final_and_canonical_lineage() -> None:
    final_url = "https://official.example.test/current/source"
    canonical_url = "https://official.example.test/canonical/source"
    result = dispatch_acquisition(
        _read_request(),
        transports=AcquisitionTransports(
            linkup_fetch=lambda _payload: {
                "markdown": "Redirected readable material.",
                "requested_url": READ_URL,
                "attempted_url": READ_URL,
                "resolved_url": final_url,
                "final_url": final_url,
                "canonical_url": canonical_url,
                "http_status": 200,
                "observed_at": OBSERVED_AT,
            }
        ),
    )

    artifact = result.artifacts[0]
    assert artifact.requested_url == READ_URL
    assert artifact.attempted_url == READ_URL
    assert artifact.resolved_url == final_url
    assert artifact.final_url == final_url
    assert artifact.canonical_url == canonical_url
    assert artifact.candidate_reference == "candidate-1"


@pytest.mark.parametrize(
    ("response", "failure_code"),
    [
        ({}, "provider_response_missing"),
        ({"markdown": ""}, "read_material_empty_or_unreadable"),
        (
            {"markdown": "unreadable", "http_status": 503},
            "read_http_status_unreadable",
        ),
        (
            {
                "markdown": "mismatched",
                "attempted_url": "https://other.example.test/source",
            },
            "read_attempted_url_mismatch",
        ),
        ([], "provider_response_missing"),
    ],
)
def test_empty_malformed_unreadable_or_mismatched_read_fails_closed(
    response: Any,
    failure_code: str,
) -> None:
    result = dispatch_acquisition(
        _read_request(),
        transports=AcquisitionTransports(linkup_fetch=lambda _payload: response),
    )

    assert result.status is AcquisitionExecutionStatus.FAILED
    assert result.failure_code == failure_code
    assert result.provider_calls_attempted == 1
    assert result.provider_calls_completed == 1


def test_focused_extract_requires_selected_urls_and_bounded_focus() -> None:
    calls: list[dict[str, Any]] = []
    valid = _tavily_typed_request(
        AcquisitionCapability.FOCUSED_EXTRACT,
        selected_urls=(READ_URL,),
        focus_text="official filing threshold",
        max_retained_characters=8,
    )

    def extract(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(payload)
        return {
            "results": [
                {"url": READ_URL, "raw_content": "1234567890", "title": "Source"}
            ]
        }

    succeeded = dispatch_acquisition(
        valid,
        transports=AcquisitionTransports(tavily_extract=extract),
    )
    missing_urls = dispatch_acquisition(
        replace(valid, selected_urls=()),
        transports=AcquisitionTransports(tavily_extract=extract),
    )
    excessive_focus = dispatch_acquisition(
        replace(valid, focus_text="x" * 2_001),
        transports=AcquisitionTransports(tavily_extract=extract),
    )

    assert succeeded.succeeded is True
    assert succeeded.artifacts[0].retained_character_count == 8
    assert succeeded.artifacts[0].truncation_posture != "not_truncated"
    assert calls[0]["urls"] == READ_URL
    assert calls[0]["query"] == "official filing threshold"
    assert missing_urls.block_code == "focused_extract_requires_selected_urls"
    assert excessive_focus.block_code == "focused_extract_focus_invalid"
    assert len(calls) == 1


def test_map_enforces_root_domain_url_ceiling_and_no_authority() -> None:
    request = _tavily_typed_request(
        AcquisitionCapability.MAP_SITE,
        root_url=ROOT_URL,
        include_domains=("docs.example.test",),
        max_results=100,
    )
    returned_urls = [
        f"https://docs.example.test/guide/page-{index}" for index in range(105)
    ]
    calls: list[dict[str, Any]] = []

    def map_site(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(payload)
        return {"results": [*returned_urls, returned_urls[0]]}

    result = dispatch_acquisition(
        request,
        transports=AcquisitionTransports(tavily_map=map_site),
    )
    wrong_domain = dispatch_acquisition(
        replace(request, include_domains=("other.example.test",)),
        transports=AcquisitionTransports(tavily_map=map_site),
    )

    artifact = result.artifacts[0]
    durable = artifact.to_dict()
    assert artifact.kind is AcquisitionArtifactKind.SITE_URL_TOPOLOGY
    assert len(artifact.urls) == 100
    assert artifact.root_url == ROOT_URL
    assert artifact.truncation_posture == (
        "provider_excess_urls_truncated_to_authorized_limit"
    )
    assert calls[0]["limit"] == 100
    assert calls[0]["allow_external"] is False
    assert durable["evidence_authority_granted"] is False
    assert durable["citation_authority_granted"] is False
    assert wrong_domain.block_code == "root_domain_not_allowed"
    assert len(calls) == 1


def test_crawl_enforces_global_ceilings_and_page_lineage() -> None:
    request = _tavily_typed_request(
        AcquisitionCapability.CRAWL_SITE,
        root_url=ROOT_URL,
        include_domains=("docs.example.test",),
        include_path_prefix="/guide",
        max_depth=2,
        max_pages=10,
        max_retained_characters=20_000,
        max_aggregate_retained_characters=100_000,
        crawl_job_ordinal=1,
    )
    page_url = "https://docs.example.test/guide/page-1"
    calls: list[dict[str, Any]] = []

    def crawl(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(payload)
        return {
            "results": [
                {
                    "url": page_url,
                    "attempted_url": page_url,
                    "resolved_url": page_url,
                    "final_url": page_url,
                    "canonical_url": page_url,
                    "raw_content": "bounded page material",
                    "observed_at": OBSERVED_AT,
                }
            ]
        }

    result = dispatch_acquisition(
        request,
        transports=AcquisitionTransports(tavily_crawl=crawl),
    )
    for invalid, expected in (
        (replace(request, max_depth=3), "crawl_depth_ceiling_exceeded"),
        (replace(request, max_pages=11), "crawl_page_ceiling_exceeded"),
        (
            replace(request, max_retained_characters=20_001),
            "crawl_page_character_ceiling_exceeded",
        ),
        (
            replace(request, max_aggregate_retained_characters=100_001),
            "crawl_aggregate_character_ceiling_exceeded",
        ),
        (
            replace(request, crawl_job_ordinal=2),
            "crawl_job_authorization_exhausted",
        ),
    ):
        blocked = dispatch_acquisition(
            invalid,
            transports=AcquisitionTransports(tavily_crawl=crawl),
        )
        assert blocked.block_code == expected
        assert blocked.provider_calls_attempted == 0

    artifact = result.artifacts[0]
    page = artifact.pages[0]
    assert calls[0]["max_depth"] == 2
    assert calls[0]["limit"] == 10
    assert page.requested_url is None
    assert page.attempted_url == page_url
    assert page.provider_reported_url == page_url
    assert page.resolved_url == page_url
    assert page.final_url == page_url
    assert page.canonical_url == page_url
    assert page.parent_url is None
    assert page.http_status is None


def test_minimal_crawl_retains_provider_url_without_invented_lineage() -> None:
    page_url = f"{ROOT_URL}/minimal"
    request = _tavily_typed_request(
        AcquisitionCapability.CRAWL_SITE,
        root_url=ROOT_URL,
        include_domains=("docs.example.test",),
        max_pages=1,
        max_depth=1,
        max_retained_characters=20_000,
        max_aggregate_retained_characters=20_000,
    )

    result = dispatch_acquisition(
        request,
        transports=AcquisitionTransports(
            tavily_crawl=lambda _payload: {
                "results": [
                    {
                        "url": page_url,
                        "raw_content": "Minimal bounded crawl material.",
                    }
                ]
            }
        ),
    )

    assert result.succeeded is True
    page = result.artifacts[0].pages[0]
    assert page.provider_reported_url == page_url
    assert page.requested_url is None
    assert page.attempted_url is None
    assert page.resolved_url is None
    assert page.final_url is None
    assert page.canonical_url is None
    assert page.parent_url is None
    assert page.http_status is None


def test_crawl_excess_is_explicitly_truncated_and_out_of_scope_is_rejected() -> None:
    request = _tavily_typed_request(
        AcquisitionCapability.CRAWL_SITE,
        root_url=ROOT_URL,
        include_domains=("docs.example.test",),
        include_path_prefix="/guide",
        max_depth=1,
        max_pages=2,
        max_retained_characters=5,
        max_aggregate_retained_characters=8,
    )
    oversized = {
        "results": [
            {
                "url": f"https://docs.example.test/guide/page-{index}",
                "raw_content": "abcdefghij",
            }
            for index in range(3)
        ]
    }
    truncated = dispatch_acquisition(
        request,
        transports=AcquisitionTransports(
            tavily_crawl=lambda _payload: oversized
        ),
    )
    rejected = dispatch_acquisition(
        request,
        transports=AcquisitionTransports(
            tavily_crawl=lambda _payload: {
                "results": [
                    {
                        "url": "https://outside.example.test/guide/page",
                        "raw_content": "outside",
                    }
                ]
            }
        ),
    )

    artifact = truncated.artifacts[0]
    assert len(artifact.pages) == 2
    assert sum(page.retained_character_count for page in artifact.pages) == 8
    assert "provider_excess_pages" in artifact.truncation_posture
    assert "provider_excess_content" in artifact.truncation_posture
    assert "retained_text" not in json.dumps(artifact.to_dict(), sort_keys=True)
    assert rejected.failure_code == "crawl_result_out_of_scope"


def test_general_deep_never_activates_from_product_mode_or_complexity() -> None:
    for product_mode in ("Fast", "Balanced", "Deep"):
        for complexity in ("low", "medium", "high"):
            request = ProviderCapabilityRequest(
                capability=AcquisitionCapability.DISCOVER,
                qualifier=DiscoverQualifier.GENERAL,
                derivation_reason=f"product_mode={product_mode};complexity={complexity}",
                general_deep_requested=True,
            )
            decision = route_provider_capability(
                request,
                {"linkup": True, "tavily": True},
                typed_runtime_only=True,
            )
            assert decision.fidelity is RouteFidelity.BLOCKED
            assert decision.block_reason == "general_deep_authorization_required"

    authorization = _deep_authorization()
    ordinary = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.DISCOVER,
            qualifier=DiscoverQualifier.GENERAL,
            general_deep_requested=True,
            general_deep_authorization=authorization,
        ),
        {"linkup": True},
    )
    assert ordinary.block_reason == "general_deep_no_ordinary_product_requester"


def _deep_authorization() -> GeneralDeepAuthorization:
    return GeneralDeepAuthorization(
        parent_standard_acquisition_job_id="standard-job-1",
        acquisition_lineage_id="acquisition-lineage-1",
        obligation_reference="obligation-1",
        sequential_acquisition_required=True,
        premium_authorized=True,
        remaining_run_budget=1,
        general_escalations_used=0,
        queries=("bounded follow-up query", "second authorized query"),
        max_results_per_query=5,
    )


def test_valid_general_deep_authorization_dispatches_one_bounded_job() -> None:
    authorization = _deep_authorization()
    decision = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.DISCOVER,
            qualifier=DiscoverQualifier.GENERAL,
            general_deep_requested=True,
            general_deep_authorization=authorization,
        ),
        {"linkup": True},
        typed_runtime_only=True,
    )
    request = AcquisitionRequest(
        acquisition_job_id="deep-job-1",
        parent_acquisition_job_id="standard-job-1",
        acquisition_lineage_id="acquisition-lineage-1",
        obligation_reference="obligation-1",
        query_reference="deep-query-1",
        route_decision=decision,
        queries=("bounded follow-up query",),
        max_results=5,
        max_retained_characters=1_000,
    )
    calls: list[dict[str, Any]] = []

    def deep_search(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(payload)
        return {
            "results": [
                {
                    "name": "Candidate",
                    "url": "https://source.example.test/item",
                    "content": "bounded candidate material",
                }
            ]
        }

    result = dispatch_acquisition(
        request,
        transports=AcquisitionTransports(linkup_deep_search=deep_search),
    )
    mismatched = dispatch_acquisition(
        replace(request, parent_acquisition_job_id="wrong-parent"),
        transports=AcquisitionTransports(linkup_deep_search=deep_search),
    )

    assert decision.selected_provider == "linkup"
    assert decision.variant == "deep"
    assert decision.output_type == "searchResults"
    assert decision.adapter_posture == "installed_authorized_runtime_only"
    assert result.succeeded is True
    assert result.provider_calls_attempted == 1
    assert len(calls) == 1
    assert calls[0]["q"] == "bounded follow-up query"
    assert calls[0]["depth"] == "deep"
    assert calls[0]["outputType"] == "searchResults"
    assert calls[0]["maxResults"] == 5
    assert result.artifacts[0].parent_acquisition_job_id == "standard-job-1"
    assert mismatched.block_code == "general_deep_lineage_mismatch"


def test_scrutineer_deep_route_remains_unchanged() -> None:
    plan = ProviderPlan.from_available_keys({"linkup": True, "tavily": True})

    remediation = plan.record_scrutineer_remediation(
        query_type="other",
        intent="general",
        complexity="high",
        report_type="general_research",
        is_academic=False,
        suppress_tavily=True,
        search_depth="advanced",
    )

    assert remediation.providers_list() == ["linkup"]
    assert remediation.route_decision.variant == "deep"
    assert remediation.route_decision.output_type == "searchResults"
    assert remediation.route_decision.request.general_deep_requested is False


def test_provider_synthesis_remains_blocked_before_transport() -> None:
    calls = 0
    decision = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.PROVIDER_SYNTHESIS
        ),
        {"linkup": True, "tavily": True},
        typed_runtime_only=True,
    )
    request = AcquisitionRequest(
        acquisition_job_id="synthesis-job-1",
        route_decision=decision,
    )

    def forbidden(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {}

    result = dispatch_acquisition(
        request,
        transports=AcquisitionTransports(linkup_deep_search=forbidden),
    )

    assert decision.block_reason == "provider_synthesis_disabled"
    assert result.status is AcquisitionExecutionStatus.BLOCKED
    assert result.provider_calls_attempted == 0
    assert calls == 0


def test_generic_single_relation_acquisition_consumes_core_routing(
    tmp_path: Path,
) -> None:
    linkup_calls: list[dict[str, Any]] = []
    tavily_calls = 0

    def linkup(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        linkup_calls.append(kwargs)
        return (
            [
                {
                    "title": "Routed source",
                    "url": "https://source.example.test/item",
                    "raw_content": "bounded source material",
                }
            ],
            [],
        )

    def tavily(**_kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        nonlocal tavily_calls
        tavily_calls += 1
        return ([], [])

    result = run_generic_product_provider_acquisition(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=tmp_path / "generic-acquisition.json",
            query="current official threshold",
            available_providers={"linkup": True, "tavily": True},
        ),
        tavily_product_provider_callable=tavily,
        linkup_product_provider_callable=linkup,
    )

    assert result.return_code == 0
    assert result.route_decision is not None
    assert result.route_decision.selected_provider == "linkup"
    assert result.route_decision.decision_reason == (
        "first_reachable_policy_preference_selected"
    )
    assert len(linkup_calls) == 1
    assert tavily_calls == 0

    from proplex.mvp_single_relation_live_dogfood_run import (
        GenericProviderProxyRunRequest,
        _provider_runner_from_product_acquisition_runner,
    )

    completed_requests: list[ProductProviderAcquisitionRequest] = []

    def capture_completed(
        request: ProductProviderAcquisitionRequest,
    ) -> ProductProviderAcquisitionResult:
        completed_requests.append(request)
        return ProductProviderAcquisitionResult(
            return_code=0,
            output_path=request.output_path,
            provider_calls_attempted=1,
            provider_calls_completed=1,
            route_decision=request.route_decision,
        )

    product_bridge = _provider_runner_from_product_acquisition_runner(
        capture_completed
    )
    product_bridge(
        GenericProviderProxyRunRequest(
            repo_root=tmp_path,
            output_path=tmp_path / "product-bridge.json",
            query="current official threshold",
            provider="linkup",
            available_providers={"linkup": True},
        )
    )
    assert completed_requests[0].route_decision is not None
    assert completed_requests[0].route_decision.selected_provider == "linkup"


def test_generic_provider_preference_cannot_create_availability(
    tmp_path: Path,
) -> None:
    calls = 0

    def forbidden_linkup(**_kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        nonlocal calls
        calls += 1
        return ([], [])

    result = run_generic_product_provider_acquisition(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=tmp_path / "undeclared-linkup.json",
            query="current official threshold",
            provider="linkup",
            available_providers={},
        ),
        linkup_product_provider_callable=forbidden_linkup,
    )

    assert result.return_code == 2
    assert result.provider_calls_attempted == 0
    assert result.route_decision is not None
    assert result.route_decision.blocked is True
    assert calls == 0


def test_generic_provider_preference_with_explicit_availability_calls_once(
    tmp_path: Path,
) -> None:
    calls = 0

    def linkup(**_kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        nonlocal calls
        calls += 1
        return (
            [
                {
                    "title": "Explicitly available source",
                    "url": "https://source.example.test/item",
                    "raw_content": "bounded source material",
                }
            ],
            [],
        )

    result = run_generic_product_provider_acquisition(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=tmp_path / "available-linkup.json",
            query="current official threshold",
            provider="linkup",
            available_providers={"linkup": True},
        ),
        linkup_product_provider_callable=linkup,
    )

    assert result.return_code == 0
    assert result.provider_calls_attempted == 1
    assert result.route_decision is not None
    assert result.route_decision.selected_provider == "linkup"
    assert calls == 1


def test_migrated_product_operations_select_one_provider_or_zero_transport(
    tmp_path: Path,
) -> None:
    blocked_read = _read_request(linkup=False, tavily=False)
    adapter_calls = 0

    def forbidden_adapter(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal adapter_calls
        adapter_calls += 1
        return {}

    read_result = dispatch_acquisition(
        blocked_read,
        transports=AcquisitionTransports(
            linkup_fetch=forbidden_adapter,
            tavily_extract=forbidden_adapter,
        ),
    )
    generic_result = run_generic_product_provider_acquisition(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=tmp_path / "blocked-generic.json",
            query="blocked generic request",
        ),
        tavily_product_provider_callable=lambda **_kwargs: ([], []),
        linkup_product_provider_callable=lambda **_kwargs: ([], []),
    )

    assert blocked_read.route_decision.providers() == ()
    assert read_result.provider_calls_attempted == 0
    assert adapter_calls == 0
    assert generic_result.provider_calls_attempted == 0
    assert generic_result.route_decision is not None
    assert generic_result.route_decision.providers() == ()

    from core.pipeline import process_search_queries

    status = MagicMock()
    with patch("core.pipeline.search_web_results") as tavily:
        with patch("core.pipeline.search_exa_results") as exa:
            with patch("core.pipeline.search_linkup_results") as linkup:
                process_search_queries(
                    ["no completed route"],
                    "general",
                    "medium",
                    "advanced",
                    6,
                    [],
                    [],
                    [0.0, 1.0],
                    set(),
                    set(),
                    "OpenAI",
                    "text-embedding-3-small",
                    "http://localhost",
                    lambda *_args, **_kwargs: [[0.0]],
                    lambda *_args, **_kwargs: None,
                    status_container=status,
                    search_providers=None,
                )
                tavily.assert_not_called()
                exa.assert_not_called()
                linkup.assert_not_called()


@pytest.mark.parametrize(
    "closed_field",
    [
        "evidence_admitted",
        "citation_eligible",
        "source_obligation_satisfied",
        "sufficiency_decided",
        "final_answer_packet",
        "author",
    ],
)
def test_adapter_output_cannot_create_closed_authority_fields(
    closed_field: str,
) -> None:
    result = dispatch_acquisition(
        _read_request(),
        transports=AcquisitionTransports(
            linkup_fetch=lambda _payload: {
                "markdown": "readable material",
                closed_field: True,
            }
        ),
    )

    assert result.status is AcquisitionExecutionStatus.FAILED
    assert result.failure_code == "provider_response_closed_fields_rejected"
    assert result.artifacts[0].kind is AcquisitionArtifactKind.PROVIDER_FAILURE
