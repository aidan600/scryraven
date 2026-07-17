from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.provider_plan import ProviderPlan
from core.routing import (
    AcquisitionCapability,
    DiscoverQualifier,
    ProviderCapabilityRequest,
    ProviderRouteBlockedError,
    RouteFidelity,
    route_provider_capability,
    select_providers,
)
from tests.helpers.offline_ordinary_pipeline import (
    PostRetirementOrdinaryPipelineHarness,
    offline_balanced_run_config,
    scrub_offline_runtime,
)

ROOT = Path(__file__).resolve().parents[1]

_PROVIDER_ENV_KEYS = {
    "tavily": "TAVILY_API_KEY",
    "linkup": "LINKUP_API_KEY",
    "exa": "EXA_API_KEY",
    "serper": "SERPER_API_KEY",
    "brave": "BRAVE_API_KEY",
}


@dataclass
class CapabilityRoutingPipelineHarness(PostRetirementOrdinaryPipelineHarness):
    router_is_academic: bool = False

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt == DEFAULT_SYSTEM["router"]:
            self._record_model_call(system_prompt, kwargs)
            entities = list(self.router_entities or (self.primary_entity,))
            return json.dumps(
                {
                    "intent": "general",
                    "report_type": self.router_report_type,
                    "image_mode": "none",
                    "core_topic": self.core_topic,
                    "is_academic": self.router_is_academic,
                    "query_type": self.router_query_type,
                    "entities": entities,
                    "primary_entity": self.primary_entity,
                }
            )
        return super().ask_model(prompt, system_prompt, **kwargs)

    def process_search_queries(
        self,
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        results_per_query: int,
        include_domains: Sequence[str],
        exclude_domains: Sequence[str],
        *args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        passages = super().process_search_queries(
            queries,
            intent,
            complexity,
            search_depth,
            results_per_query,
            include_domains,
            exclude_domains,
            *args,
            **kwargs,
        )
        self.search_calls[-1].update(
            {
                "include_domains": list(include_domains),
                "exclude_domains": list(exclude_domains),
                "linkup_depth_override": kwargs.get("linkup_depth_override"),
            }
        )
        return passages


def _run_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    providers: Sequence[str],
    mode: str = "Balanced",
    include_domains: Sequence[str] = (),
    exclude_domains: Sequence[str] = (),
    is_academic: bool = False,
    capture: dict[str, Any] | None = None,
) -> tuple[Any, CapabilityRoutingPipelineHarness]:
    scrub_offline_runtime(monkeypatch)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    for provider in providers:
        monkeypatch.setenv(_PROVIDER_ENV_KEYS[provider], "offline-placeholder")

    query = (
        "Find peer-reviewed semantic-search research."
        if is_academic
        else "Find the current official Alpha operating rule."
    )
    harness = CapabilityRoutingPipelineHarness(
        tmp_path=tmp_path,
        query=query,
        core_topic="Alpha operating rule",
        primary_entity="Alpha",
        raw_author_response=("The retrieved material supports the bounded rule. [[1]](https://alpha.example/report-1)"),
        router_report_type="general_research",
        router_query_type="concept" if is_academic else "other",
        router_is_academic=is_academic,
    )
    if capture is not None:
        capture["harness"] = harness
    config = replace(
        offline_balanced_run_config(
            query=query,
            current_date="2026-07-16",
            session_id=f"session-{mode.casefold()}",
            run_id=f"run-{mode.casefold()}",
        ),
        mode=mode,
        include_domains=list(include_domains),
        exclude_domains=list(exclude_domains),
    )
    outcome = orchestrator.run_pipeline(
        config,
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    return outcome, harness


def _main_record(outcome: Any) -> Mapping[str, Any]:
    records = outcome.execution_trace["provider_plan"]["records"]
    return next(record for record in records if record["role"] == "main_retrieval")


@pytest.mark.parametrize(
    ("providers", "expected_provider"),
    [
        (("linkup",), "linkup"),
        (("tavily", "linkup", "exa", "serper", "brave"), "linkup"),
        (("tavily",), "tavily"),
    ],
)
def test_real_run_pipeline_general_discovery_dispatches_one_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    providers: Sequence[str],
    expected_provider: str,
) -> None:
    outcome, harness = _run_pipeline(
        tmp_path,
        monkeypatch,
        providers=providers,
    )

    record = _main_record(outcome)
    decision = record["route_decision"]
    assert record["providers"] == [expected_provider]
    assert decision["capability"] == "DISCOVER"
    assert decision["qualifier"] == "general"
    assert decision["selected_provider"] == expected_provider
    assert harness.search_calls
    assert all(call["search_providers"] == [expected_provider] for call in harness.search_calls)
    if expected_provider == "linkup":
        assert decision["operation"] == "search"
        assert decision["variant"] == "standard"
        assert decision["output_type"] == "searchResults"
        assert all(call["linkup_depth_override"] == "standard" for call in harness.search_calls), harness.search_calls


def test_all_providers_records_fallback_without_dispatching_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness = _run_pipeline(
        tmp_path,
        monkeypatch,
        providers=("tavily", "linkup", "exa", "serper", "brave"),
    )

    decision = _main_record(outcome)["route_decision"]
    assert [candidate["provider"] for candidate in decision["fallback_candidates"]] == ["tavily"]
    assert harness.search_calls
    assert all(call["search_providers"] == ["linkup"] for call in harness.search_calls)


def test_real_run_pipeline_academic_request_dispatches_exa_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness = _run_pipeline(
        tmp_path,
        monkeypatch,
        providers=("tavily", "linkup", "exa"),
        is_academic=True,
    )

    decision = _main_record(outcome)["route_decision"]
    assert decision["qualifier"] == "academic_technical_semantic"
    assert decision["selected_provider"] == "exa"
    assert decision["fidelity"] == "exact"
    assert harness.search_calls
    assert all(call["search_providers"] == ["exa"] for call in harness.search_calls)


def test_real_run_pipeline_domain_targeting_preserves_exact_social_constraint_without_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness = _run_pipeline(
        tmp_path,
        monkeypatch,
        providers=("linkup",),
        include_domains=("reddit.com",),
        exclude_domains=("blocked.example",),
    )

    decision = _main_record(outcome)["route_decision"]
    assert decision["qualifier"] == "domain_targeted"
    assert decision["selected_provider"] == "linkup"
    assert decision["social_authority_granted"] is False
    assert decision["authority_posture"] == "non_authoritative_acquisition_material"
    assert harness.search_calls
    assert all(call["include_domains"] == ["reddit.com"] for call in harness.search_calls)
    assert all(call["exclude_domains"] == ["blocked.example"] for call in harness.search_calls)


@pytest.mark.parametrize("mode", ["Fast", "Balanced", "Deep"])
def test_real_run_pipeline_mode_does_not_change_linkup_standard_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    outcome, harness = _run_pipeline(
        tmp_path,
        monkeypatch,
        providers=("linkup",),
        mode=mode,
    )

    decision = _main_record(outcome)["route_decision"]
    assert (decision["operation"], decision["variant"], decision["output_type"]) == (
        "search",
        "standard",
        "searchResults",
    )
    assert harness.search_calls
    assert all(call["linkup_depth_override"] == "standard" for call in harness.search_calls), harness.search_calls


def test_real_run_pipeline_no_provider_records_typed_block_and_zero_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture: dict[str, Any] = {}
    with pytest.raises(ProviderRouteBlockedError) as blocked:
        _run_pipeline(
            tmp_path,
            monkeypatch,
            providers=(),
            capture=capture,
        )

    decision = blocked.value.decision
    harness = capture["harness"]
    assert decision.providers() == ()
    assert decision.fidelity is RouteFidelity.BLOCKED
    assert decision.block_reason == "no_compatible_provider_available"
    assert harness.search_calls == []


def test_read_is_installed_while_provider_synthesis_still_fails_closed() -> None:
    available = {provider: True for provider in _PROVIDER_ENV_KEYS}

    read_decision = route_provider_capability(
        ProviderCapabilityRequest(capability=AcquisitionCapability.READ),
        available,
    )
    synthesis_decision = route_provider_capability(
        ProviderCapabilityRequest(capability=AcquisitionCapability.PROVIDER_SYNTHESIS),
        available,
    )

    assert read_decision.fidelity is RouteFidelity.EXACT
    assert read_decision.selected_provider == "linkup"
    assert read_decision.operation == "fetch"
    assert {candidate.provider for candidate in read_decision.fallback_candidates} == {
        "tavily",
    }
    assert all(candidate.adapter_installed for candidate in read_decision.fallback_candidates)
    assert synthesis_decision.fidelity is RouteFidelity.BLOCKED
    assert synthesis_decision.block_reason == "provider_synthesis_disabled"
    assert synthesis_decision.provider_synthesis_disabled is True


@pytest.mark.parametrize(
    ("qualifier", "expected_provider"),
    [
        (DiscoverQualifier.LIGHTWEIGHT_DISAMBIGUATION, "serper"),
        (DiscoverQualifier.INDEPENDENT_INDEX, "brave"),
    ],
)
def test_explicit_discovery_roles_remain_candidate_only(
    qualifier: DiscoverQualifier,
    expected_provider: str,
) -> None:
    decision = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.DISCOVER,
            qualifier=qualifier,
        ),
        {expected_provider: True},
    )

    assert decision.selected_provider == expected_provider
    assert decision.returned_material_class == "directional_candidate_material"
    assert decision.authority_posture == "candidate_only_no_evidence_authority"


def test_overrides_are_ordered_compatible_preferences_or_a_typed_block() -> None:
    assert select_providers(
        "other",
        "general",
        "medium",
        {"tavily": True, "linkup": True},
        override=["tavily", "linkup"],
    ) == ["tavily"]
    assert select_providers(
        "other",
        "general",
        "medium",
        {"tavily": False, "linkup": True},
        override=["tavily", "linkup"],
    ) == ["linkup"]
    assert (
        select_providers(
            "other",
            "general",
            "medium",
            {"serper": True, "linkup": True},
            override=["serper"],
        )
        == []
    )


def test_provider_plan_availability_is_boolean_bounded_and_scrutineer_deep_is_unchanged() -> None:
    plan = ProviderPlan.from_available_keys(
        {
            "tavily": 1,
            "linkup": "configured",
            "exa": None,
            "serper": object(),
            "brave": False,
            "private_value": "must-not-survive",
        }
    )
    assert plan.capability_available_keys() == {
        "tavily": True,
        "linkup": True,
        "exa": False,
        "serper": True,
        "brave": False,
    }
    assert "private_value" not in json.dumps(plan.to_trace(), sort_keys=True)

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


def test_policy_and_mechanical_owner_boundaries_are_static() -> None:
    routing_source = (ROOT / "core" / "routing.py").read_text(encoding="utf-8")
    scheduler_source = (ROOT / "core" / "retrieval_scheduler.py").read_text(encoding="utf-8")
    dispatch_source = (ROOT / "core" / "retrieval_dispatch_runtime.py").read_text(encoding="utf-8")

    assert "class ProviderCapabilityCatalogEntry" in routing_source
    assert "def route_provider_capability" in routing_source
    assert "core.routing" not in scheduler_source
    assert "core.routing" not in dispatch_source
    assert "fallback_candidates" not in dispatch_source
