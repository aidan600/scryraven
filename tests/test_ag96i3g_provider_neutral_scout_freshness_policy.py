from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import patch

from core.followup_deliberation import ProviderJobKind
from core.followup_search_freshness_policy import (
    CURRENT_OR_STABLE,
    CURRENT_YEAR,
    HISTORICAL_OR_STABLE,
    KNOWN_YEAR,
    LATEST_BREAKING,
    MIXED_PROBE,
    RECENT_MONTHS,
    build_search_freshness_policy_diagnostics,
)

ROOT = Path(__file__).resolve().parents[1]
FRESHNESS_MODULE = ROOT / "core" / "followup_search_freshness_policy.py"
SEARCH_PROVIDERS = ROOT / "core" / "search_providers.py"
SCRIPT = ROOT / "scripts" / "ag96i3e_brokered_provider_neutral_discovery_validation.py"


def _policy(
    query: str,
    *,
    provider_job_kind: str = (
        ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value
    ),
    **kwargs: Any,
) -> dict[str, Any]:
    return build_search_freshness_policy_diagnostics(
        authorized_query=query,
        provider_job_kind=provider_job_kind,
        current_year=2026,
        **kwargs,
    )


def test_irs_known_year_current_query_forbids_past_week_only_freshness() -> None:
    packet = _policy(
        "What is the current IRS standard mileage rate for business use of a "
        "car in 2026, and what official source supports it?"
    )

    assert packet["freshness_intent"] in {KNOWN_YEAR, CURRENT_YEAR, CURRENT_OR_STABLE}
    assert packet["over_narrow_recent_window_forbidden"] is True
    assert packet["provider_freshness_value_by_provider"]["brave"] is None
    assert packet["live_call_authorized"] is False
    assert packet["provider_called"] is False
    assert packet["fetch_read_invoked"] is False
    assert packet["model_called"] is False
    assert packet["author_executor_invoked"] is False
    assert packet["evidence_boundary"]["freshness_policy_is_final_evidence"] is False
    assert packet["evidence_boundary"]["freshness_policy_is_citation_eligible"] is False


def test_shaped_irs_query_does_not_map_to_brave_past_week_freshness() -> None:
    packet = _policy(
        "IRS 2026 standard mileage rates business use car notice announcement"
    )

    assert packet["freshness_intent"] == KNOWN_YEAR
    assert packet["provider_freshness_policy"] == "omit_provider_freshness_filter"
    assert packet["provider_freshness_value_by_provider"]["brave"] is None


def test_latest_poe_patch_uses_broad_or_mixed_probe_not_past_week_only() -> None:
    packet = _policy(
        "latest PoE patch",
        provider_job_kind=ProviderJobKind.SCOUT_DISAMBIGUATION.value,
        canonical_subject_status="unresolved",
    )

    assert packet["freshness_intent"] in {RECENT_MONTHS, MIXED_PROBE}
    assert packet["provider_freshness_value_by_provider"]["brave"] != "pw"
    assert packet["over_narrow_recent_window_forbidden"] is True


def test_market_news_today_maps_to_narrow_freshness() -> None:
    packet = _policy("market news today")

    assert packet["freshness_intent"] == LATEST_BREAKING
    assert packet["provider_freshness_policy"] == "apply_narrow_recent_filter"
    assert packet["provider_freshness_value_by_provider"]["brave"] == "pd"


def test_historical_stable_query_maps_to_no_provider_freshness() -> None:
    packet = _policy("When was the Eiffel Tower built?")

    assert packet["freshness_intent"] == HISTORICAL_OR_STABLE
    assert packet["provider_freshness_value_by_provider"]["brave"] is None


def test_ambiguous_scout_query_allows_mixed_probes_without_canonical_promotion() -> None:
    packet = _policy(
        "funny reimbursement thing for driving",
        provider_job_kind=ProviderJobKind.SCOUT_DISAMBIGUATION.value,
        canonical_subject_status="unresolved",
    )

    assert packet["freshness_intent"] == MIXED_PROBE
    assert packet["mixed_probe_allowed"] is True
    assert packet["canonical_subject_status"] == "unresolved"
    assert packet["provider_freshness_value_by_provider"]["brave"] is None


def test_provider_neutral_scout_wrapper_dispatches_brave_without_role_coupling() -> None:
    from core.search_providers import search_scout_results

    with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}, clear=False):
        with patch("httpx.get") as http_get:
            http_get.return_value.raise_for_status.return_value = None
            http_get.return_value.json.return_value = {
                "web": {
                    "results": [
                        {
                            "title": "Official result",
                            "url": "https://example.gov/result",
                            "description": "description",
                            "age": "1 day ago",
                        }
                    ]
                }
            }

            results = search_scout_results(
                provider="brave",
                query="market news today",
                max_results=3,
                provider_freshness_value="pd",
            )

    assert results[0]["url"] == "https://example.gov/result"
    params = http_get.call_args.kwargs["params"]
    assert params["q"] == "market news today"
    assert params["count"] == 3
    assert params["freshness"] == "pd"


def test_ag96i3e_packet_includes_freshness_policy_diagnostics() -> None:
    runner = _load_runner_module()

    packet = runner.build_validation_packet(
        provider="fixture",
        query="IRS 2026 standard mileage rates business use car notice announcement",
        job_id="ag96i3g-fixture-freshness-policy",
        max_results=5,
        raw_results=runner._fixture_results(),
        provider_search_call_count=0,
        fixture_mode=True,
    )

    freshness = packet["freshness_policy_diagnostics"]
    assert freshness["schema_version"] == (
        "ag96i3g_provider_neutral_search_freshness_policy_v1"
    )
    assert freshness["freshness_intent"] == KNOWN_YEAR
    assert freshness["provider_freshness_value_by_provider"]["brave"] is None
    assert packet["provider_result_set_diagnostics"]["record_type"] == (
        "provider_neutral_official_current_result_set_diagnostics"
    )


def test_mocked_brave_omits_freshness_for_known_year_official_artifact() -> None:
    from core.search_providers import search_scout_results

    policy = _policy(
        "IRS 2026 standard mileage rates business use car notice announcement"
    )
    with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}, clear=False):
        with patch("httpx.get") as http_get:
            http_get.return_value.raise_for_status.return_value = None
            http_get.return_value.json.return_value = {"web": {"results": []}}

            search_scout_results(
                provider="brave",
                query=policy["original_authorized_query"],
                max_results=5,
                freshness_policy=policy,
            )

    params = http_get.call_args.kwargs["params"]
    assert "freshness" not in params


def test_mocked_brave_can_use_narrow_freshness_for_breaking_posture() -> None:
    from core.search_providers import search_scout_results

    policy = _policy("market news today")
    with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}, clear=False):
        with patch("httpx.get") as http_get:
            http_get.return_value.raise_for_status.return_value = None
            http_get.return_value.json.return_value = {"web": {"results": []}}

            search_scout_results(
                provider="brave",
                query=policy["original_authorized_query"],
                max_results=5,
                freshness_policy=policy,
            )

    params = http_get.call_args.kwargs["params"]
    assert params["freshness"] == "pd"


def test_static_guard_no_serper_adapter_or_env_placeholder_added() -> None:
    search_source = SEARCH_PROVIDERS.read_text(encoding="utf-8").casefold()
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8").casefold()

    assert "serper_api_key" not in env_example
    assert "def search_serper" not in search_source
    assert "serper_api_key" not in search_source
    assert "api.serper" not in search_source


def test_static_guard_no_provider_calls_in_freshness_helper() -> None:
    source = FRESHNESS_MODULE.read_text(encoding="utf-8")
    imports = _imports(FRESHNESS_MODULE)
    forbidden_imports = {
        "core.search_providers",
        "requests",
        "httpx",
        "openai",
        "dotenv",
        "urllib.request",
        "core.pipeline_orchestrator",
    }

    assert imports.isdisjoint(forbidden_imports)
    for forbidden in (
        "BRAVE_API_KEY",
        "TAVILY_API_KEY",
        "LINKUP_API_KEY",
        "EXA_API_KEY",
        "load_dotenv",
        "urlopen",
        "httpx.",
        "requests.",
    ):
        assert forbidden not in source


def test_static_guard_no_pipeline_orchestrator_domain_logic() -> None:
    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )

    assert "followup_search_freshness_policy" not in pipeline_source
    assert "ag96i3g_provider_neutral_search_freshness_policy" not in pipeline_source
    assert "search_scout_results(" not in pipeline_source


def test_static_guard_no_author_citation_or_product_imports() -> None:
    imports = _imports(FRESHNESS_MODULE)
    forbidden_imports = {
        "core.author_execution_runtime",
        "core.citation_source_handoff_contract",
        "core.followup_final_answer_packet_runtime",
        "core.final_answer_packet",
        "core.evidence_ledger",
        "core.pipeline_orchestrator",
    }
    assert imports.isdisjoint(forbidden_imports)


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
