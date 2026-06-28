from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import patch

import pytest

from core.followup_deliberation import ProviderJobKind
from core.followup_search_freshness_policy import (
    KNOWN_YEAR,
    LATEST_BREAKING,
    RECENT_MONTHS,
    RECENT_WEEKS,
    build_search_freshness_policy_diagnostics,
)
from core.search_providers import retrieval_timeout_seconds, search_scout_results

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ag96i3e_brokered_provider_neutral_discovery_validation.py"
SEARCH_PROVIDERS = ROOT / "core" / "search_providers.py"
TEMPLATE = ROOT / "docs" / "examples" / "scryraven_live_broker_private_template.py"
_SERPER_ENV_KEY = "SERPER" + "_API" + "_KEY"


def test_env_example_contains_serper_placeholder_and_timeout_default() -> None:
    source = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert f"{_SERPER_ENV_KEY}=<your_serper_api_key>" in source
    assert "# SERPER_SEARCH_TIMEOUT_SEC=8" in source
    assert "Brave/Serper 8" in source


def test_retrieval_timeout_seconds_returns_serper_timeout() -> None:
    import core.search_providers as search_providers

    assert retrieval_timeout_seconds("serper") == search_providers.SERPER_SEARCH_TIMEOUT_SEC


def test_search_scout_results_dispatches_serper_through_neutral_interface() -> None:
    policy = _policy("market news today")

    with patch("core.search_providers._serper_search_results") as serper_search:
        serper_search.return_value = [{"title": "Result", "url": "https://example.gov"}]

        results = search_scout_results(
            provider="serper",
            query="market news today",
            max_results=4,
            freshness_policy=policy,
        )

    assert results == [{"title": "Result", "url": "https://example.gov"}]
    assert serper_search.call_args.args == ("market news today",)
    assert serper_search.call_args.kwargs["num_results"] == 4
    assert serper_search.call_args.kwargs["freshness"] == "qdr:d"


def test_serper_wrapper_maps_mocked_organic_results_to_sanitized_shape() -> None:
    with patch.dict("os.environ", {_SERPER_ENV_KEY: "placeholder-for-unit-test"}, clear=False):
        with patch("requests.post") as post:
            post.return_value.raise_for_status.return_value = None
            post.return_value.json.return_value = {
                "organic": [
                    {
                        "title": "IRS current official notice 2026",
                        "link": "https://www.irs.gov/newsroom/notice-2026",
                        "snippet": "Official notice summary",
                        "position": 1,
                        "date": "Jan 10, 2026",
                        "sitelinks": [{"title": "Raw child", "link": "https://example.test"}],
                    }
                ],
                "searchParameters": {"q": "blocked raw payload marker"},
            }

            results = search_scout_results(
                provider="serper",
                query="IRS 2026 standard mileage rates",
                max_results=5,
                provider_freshness_value="qdr:m",
            )

    assert results == [
        {
            "title": "IRS current official notice 2026",
            "url": "https://www.irs.gov/newsroom/notice-2026",
            "snippet": "Official notice summary",
            "domain": "irs.gov",
            "credibility": 5,
            "position": 1,
            "date": "Jan 10, 2026",
        }
    ]
    assert post.call_args.kwargs["headers"]["X-API-KEY"] == "placeholder-for-unit-test"
    assert post.call_args.kwargs["json"] == {
        "q": "IRS 2026 standard mileage rates",
        "num": 5,
        "tbs": "qdr:m",
    }
    serialized = json.dumps(results, sort_keys=True)
    assert "blocked raw payload marker" not in serialized
    assert "sitelinks" not in serialized
    assert "link" not in results[0]


def test_serper_wrapper_raises_clear_missing_config_error() -> None:
    with patch.dict("os.environ", {}, clear=True):
        with patch("requests.post") as post:
            with pytest.raises(RuntimeError, match=f"{_SERPER_ENV_KEY} is not set"):
                search_scout_results(provider="serper", query="query", max_results=1)

    post.assert_not_called()


def test_serper_wrapper_drops_nested_raw_provider_values() -> None:
    with patch.dict("os.environ", {_SERPER_ENV_KEY: "placeholder-for-unit-test"}, clear=False):
        with patch("requests.post") as post:
            post.return_value.raise_for_status.return_value = None
            post.return_value.json.return_value = {
                "organic": [
                    {
                        "title": {"raw": "blocked title object"},
                        "link": "https://example.gov/result",
                        "snippet": {"raw": "blocked snippet object"},
                        "position": "2",
                        "date": {"raw": "blocked date object"},
                    }
                ],
                "rawResponse": "blocked raw response body",
            }

            results = search_scout_results(provider="serper", query="query", max_results=1)

    assert results == [
        {
            "title": "",
            "url": "https://example.gov/result",
            "snippet": "",
            "domain": "example.gov",
            "credibility": 4,
            "position": 2,
        }
    ]
    serialized = json.dumps(results, sort_keys=True)
    for forbidden in (
        "blocked title object",
        "blocked snippet object",
        "blocked date object",
        "blocked raw response body",
        "placeholder-for-unit-test",
    ):
        assert forbidden not in serialized


def test_serper_known_year_current_policy_omits_narrow_freshness() -> None:
    packet = _policy("IRS 2026 standard mileage rates business use car notice announcement")

    assert packet["freshness_intent"] == KNOWN_YEAR
    assert packet["provider_freshness_policy"] == "omit_provider_freshness_filter"
    assert packet["provider_freshness_value_by_provider"]["serper"] is None


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        (LATEST_BREAKING, "qdr:d"),
        (RECENT_WEEKS, "qdr:w"),
        (RECENT_MONTHS, "qdr:m"),
    ],
)
def test_serper_recent_freshness_maps_to_google_tbs_values(
    intent: str,
    expected: str,
) -> None:
    packet = _policy("placeholder query", freshness_intent=intent)

    assert packet["provider_freshness_value_by_provider"]["serper"] == expected


def test_ag96i3e_dispatch_supports_serper_without_live_call_in_mocked_test() -> None:
    runner = _load_runner_module()
    budget = runner.ProviderCallBudget()
    policy = _policy("market news today")

    with patch("core.search_providers.search_scout_results") as scout:
        scout.return_value = [
            {"title": "SEC current official filing rule", "url": "https://www.sec.gov/rules/current"}
        ]

        results = list(
            runner._dispatch_provider(
                "serper",
                "market news today",
                5,
                budget=budget,
                freshness_policy=policy,
            )
        )

    assert budget.provider_search_call_count == 1
    assert results[0]["url"] == "https://www.sec.gov/rules/current"
    assert scout.call_args.kwargs["provider"] == "serper"
    assert scout.call_args.kwargs["max_results"] == 5
    assert scout.call_args.kwargs["freshness_policy"] == policy


def test_ag96i3e_live_budget_remains_one_provider_search_call_for_serper() -> None:
    runner = _load_runner_module()
    budget = runner.ProviderCallBudget()

    with patch("core.search_providers.search_scout_results", return_value=[]):
        runner._dispatch_provider(
            "serper",
            "official current discovery",
            5,
            budget=budget,
            freshness_policy=_policy("official current discovery"),
        )

    assert budget.provider_search_call_count == 1
    with pytest.raises(RuntimeError, match="provider search call budget exceeded"):
        budget.mark_provider_search_call()


def test_private_broker_template_includes_generic_serper_proxy_without_secret_values() -> None:
    module = _load_template_module()

    assert module.REQUEST_KIND == "generic_provider_proxy_request"
    assert "serper" in module.SUPPORTED_PROVIDERS
    assert "search" in module.SUPPORTED_OPERATIONS
    assert module.MAX_RESULTS_CAP == 10
    request = module.validate_provider_proxy_request(
        {
            "request_kind": module.REQUEST_KIND,
            "provider": "serper",
            "operation": "search",
            "query": "official current discovery",
            "max_results": 5,
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        }
    )
    assert request == {
        "provider": "serper",
        "operation": "search",
        "query": "official current discovery",
        "max_results": 5,
    }

    source = TEMPLATE.read_text(encoding="utf-8")
    assert "replace-in-private-copy" in source
    assert "placeholder-for-unit-test" not in source
    assert "test-key" not in source
    assert _SERPER_ENV_KEY not in source
    assert "ALLOWLISTED_JOBS" not in source


def test_static_guard_no_product_routing_changes_for_serper() -> None:
    forbidden_paths = [
        ROOT / "core" / "pipeline.py",
        ROOT / "core" / "query_production_runtime.py",
        ROOT / "core" / "provider_selection.py",
    ]
    for path in forbidden_paths:
        if path.exists():
            assert "serper" not in path.read_text(encoding="utf-8").casefold()


def test_static_guard_no_pipeline_orchestrator_provider_specific_logic() -> None:
    source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(encoding="utf-8")

    assert "serper" not in source.casefold()
    assert "search_scout_results(" not in source


def test_static_guard_no_author_citation_or_product_imports() -> None:
    imports = _imports(SEARCH_PROVIDERS) | _imports(SCRIPT)
    forbidden_imports = {
        "core.author_execution_runtime",
        "core.citation_source_handoff_contract",
        "core.followup_final_answer_packet_runtime",
        "core.final_answer_packet",
        "core.evidence_ledger",
        "core.pipeline_orchestrator",
        "openai",
        "dotenv",
    }

    assert imports.isdisjoint(forbidden_imports)


def _policy(query: str, **kwargs: Any) -> dict[str, Any]:
    return build_search_freshness_policy_diagnostics(
        authorized_query=query,
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        current_year=2026,
        **kwargs,
    )


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _load_runner_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "ag96i3e_brokered_provider_neutral_discovery_validation",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_template_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "scryraven_live_broker_private_template",
        TEMPLATE,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
