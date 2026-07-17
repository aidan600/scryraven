"""PRODUCT-PATH-REGRESSION: official source-challenge recovery acquisition.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex
--mvp-single-relation-live-dogfood-run --query "<supported query>"
Runtime consumer: proplex.mvp_single_relation_live_dogfood_run.
Why ordinary product-path work cannot be done directly: offline validation must
inject fake provider and D-prime callables so no live provider, broker,
fetch/read, retrieval, or model calls occur.
Integration deadline: current phase.
Exit condition: keep while D-prime source-challenge recovery feeds the generic
single-relation product runner, or replace with a broader ordinary supported
query live validation guard after the recovery lane is validated live.
Why this is not a shadow product path: tests call the ordinary dogfood builder
and product-owned provider acquisition adapter, then assert the packet consumed
by the existing product path.
Forbidden interpretation: recovery acquisition is not source authority,
semantic support, citation eligibility, source-obligation satisfaction, answer
correctness, FAP/Author output, provider comparison, or live validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.generic_product_provider_acquisition import (
    build_generic_product_provider_acquisition_runner,
)
from core.source_of_record_recovery_provider_config import (
    SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE,
)
from proplex.mvp_single_relation_live_dogfood_run import (
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED,
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL,
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED,
    CONFIRM_LIVE_SOURCE_CHALLENGE_RECOVERY_FLAG,
    DEFAULT_OUTPUT_DIR,
    GenericLiveFetchReadResult,
    build_generic_single_relation_live_dogfood_run_output,
)
from tests.test_generic_single_relation_live_dprime_non_support_repair_01 import (
    _assessment_payload,
)

SMALL_CLAIMS_QUERY = (
    "What is the current filing fee for small claims in Example County?"
)
ANSWER_CLAIM = "Example County small claims filing fee is $42."
OFFLINE_LINKUP_ROUTING_ENV = {  # pragma: allowlist secret
    "PYTEST_CURRENT_TEST": "test",
    "LINKUP_API_KEY": "offline",  # pragma: allowlist secret
    "TAVILY_API_KEY": "offline",  # pragma: allowlist secret
}


def test_challenge_recovery_plan_is_default_off_without_extra_provider_call(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="source-challenge-default-off",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        product_provider_acquisition_runner=_product_runner(calls),
        fetch_read_runner=_fetch_read_must_not_run,
        dprime_model_review_callable=_weak_or_overclaim_review,
        environ=OFFLINE_LINKUP_ROUTING_ENV,
    )

    packet = result.packet
    plan = packet["source_challenge_recovery_plan"]

    assert len(calls) == 1
    assert "include_domains" not in calls[0]
    assert packet["source_challenge_recovery_plan_created"] is True
    assert packet["source_challenge_recovery_status"] == (
        "not_executed_confirmation_required"
    )
    assert packet["source_challenge_recovery_blocker"] == (
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED
    )
    assert packet["source_challenge_recovery_provider_calls_attempted"] == 0
    assert plan["provider_role"] == SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE
    assert plan["provider_neutral_requirement"] == {
        "capability": "DISCOVER",
        "discover_qualifier": "domain_targeted",
        "provider_selection_owner": "core.routing",
    }
    assert plan["ordinary_first_stage_provider"] == "linkup"
    assert plan["official_source_of_record_recovery_intent"] is True
    assert plan["domain_constraints"] == ["example-county.gov"]
    assert plan["include_domains"] == ["example-county.gov"]
    assert plan["source_of_record_domain_constraints"] == ["example-county.gov"]
    assert plan["domain_constraints_acquisition_only"] is True
    assert plan["closed_surface_flags"]["provider_chooser_created"] is False
    assert plan["closed_surface_flags"]["provider_bakeoff_created"] is False
    assert packet["source_challenge_recovery_support_created"] is False
    assert packet["source_challenge_recovery_source_authority_adjudicated"] is False
    assert packet["source_challenge_recovery_source_obligation_satisfied"] is False
    assert packet["source_challenge_recovery_answer_created"] is False
    assert packet["answer_text_present"] is False
    assert packet["source_display_entries"] == []
    assert CONFIRM_LIVE_SOURCE_CHALLENGE_RECOVERY_FLAG not in packet[
        "command_harness_used"
    ]


def test_confirmed_recovery_carries_neutral_domain_constraints_to_adapter(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="source-challenge-official-recovery",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_live_source_challenge_recovery=True,
        product_provider_acquisition_runner=_product_runner(
            calls,
            recovery_results=_official_answer_bearing_recovery_results(),
        ),
        fetch_read_runner=_fetch_read_must_not_run,
        dprime_model_review_callable=_weak_or_overclaim_review,
        environ=OFFLINE_LINKUP_ROUTING_ENV,
    )

    packet = result.packet
    plan = packet["source_challenge_recovery_plan"]
    recovery = packet["source_challenge_recovery_result"]

    assert len(calls) == 2
    assert calls[1]["include_domains"] == ["example-county.gov"]
    assert calls[1]["query"] == plan["recovery_query"]
    serialized_plan = json.dumps(plan, sort_keys=True)
    assert "source_challenge_recovery_tavily" not in serialized_plan
    assert "tavily_recovery" not in serialized_plan
    assert plan["provider_role"] == SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE
    assert plan["ordinary_first_stage_provider"] == "linkup"
    assert plan["ordinary_first_stage_route_ref"]["selected_provider"] == "linkup"
    assert recovery["completed_provider_route"]["selected_provider"] == "linkup"
    assert recovery["selected_provider"] == "linkup"
    assert packet["source_challenge_recovery_provider_calls_attempted"] == 1
    assert packet["source_challenge_recovery_provider_calls_completed"] == 1
    assert packet["source_challenge_recovery_material_acquired"] is True
    assert packet["source_challenge_recovery_official_candidate_selected"] is True
    assert recovery["official_answer_bearing_material_acquired"] is True
    assert recovery["source_authority_adjudicated"] is False
    assert recovery["source_obligation_satisfied"] is False
    assert recovery["citation_eligible"] is False
    assert recovery["answer_created"] is False
    assert result.decision == (
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED
    )
    assert packet["dprime_model_review_calls_attempted"] == 1
    assert packet["answer_text_present"] is False
    assert packet["source_display_entries"] == []
    assert CONFIRM_LIVE_SOURCE_CHALLENGE_RECOVERY_FLAG in packet[
        "command_harness_used"
    ]


def test_routing_selects_linkup_for_initial_and_recovery_without_stale_tavily(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="source-challenge-linkup-role-config",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_live_source_challenge_recovery=True,
        product_provider_acquisition_runner=_product_runner(calls),
        fetch_read_runner=_fetch_read_must_not_run,
        dprime_model_review_callable=_weak_or_overclaim_review,
        environ=OFFLINE_LINKUP_ROUTING_ENV,
    )
    packet = result.packet
    plan = packet["source_challenge_recovery_plan"]

    assert len(calls) == 2
    assert calls[0]["transport_provider"] == "linkup"
    assert calls[1]["transport_provider"] == "linkup"
    assert calls[1]["include_domains"] == ["example-county.gov"]
    assert plan["provider_role"] == SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE
    assert plan["ordinary_first_stage_provider"] == "linkup"
    assert plan["ordinary_first_stage_route_ref"]["selected_provider"] == "linkup"
    assert plan["provider_decision_hardcoded_in_runner"] is False
    assert packet["extraction_provider"] == "linkup"
    assert packet["single_relation_answer_contract_projection"][
        "completed_provider_route_ref"
    ]["selected_provider"] == "linkup"
    assert plan["completed_provider_route"]["selected_provider"] == "linkup"
    assert plan.get("provider") is None
    assert packet["source_challenge_recovery_material_acquired"] is True
    assert result.decision == (
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED
    )


def test_confirmed_recovery_reports_no_official_answer_bearing_material(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="source-challenge-no-official-answer",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_live_source_challenge_recovery=True,
        product_provider_acquisition_runner=_product_runner(
            calls,
            recovery_results=_official_generic_recovery_results(),
        ),
        fetch_read_runner=_fetch_read_must_not_run,
        dprime_model_review_callable=_weak_or_overclaim_review,
        environ=OFFLINE_LINKUP_ROUTING_ENV,
    )

    packet = result.packet

    assert len(calls) == 2
    assert packet["source_challenge_recovery_provider_calls_attempted"] == 1
    assert packet["source_challenge_recovery_material_acquired"] is False
    assert packet["source_challenge_recovery_official_candidate_selected"] is True
    assert result.decision == (
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL
    )
    assert packet["source_challenge_recovery_support_created"] is False
    assert packet["source_challenge_recovery_source_authority_adjudicated"] is False
    assert packet["source_challenge_recovery_source_obligation_satisfied"] is False
    assert packet["candidate_selection_citation_eligible"] is False
    assert packet["product_correctness_claimed"] is False
    assert packet["fap_author_opened"] is False


def test_non_trigger_relations_do_not_start_recovery(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="source-challenge-non-trigger",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_live_source_challenge_recovery=True,
        product_provider_acquisition_runner=_product_runner(calls),
        fetch_read_runner=_fetch_read_must_not_run,
        dprime_model_review_callable=_absent_review,
        environ=OFFLINE_LINKUP_ROUTING_ENV,
    )

    assert len(calls) == 1
    assert result.packet["source_challenge_recovery_plan_created"] is False
    assert result.packet["source_challenge_recovery_status"] == "not_triggered"
    assert result.packet["source_challenge_recovery_provider_calls_attempted"] == 0


def _product_runner(
    calls: list[dict[str, Any]],
    *,
    recovery_results: list[dict[str, Any]] | None = None,
) -> Any:
    call_index = 0

    def fake_provider(
        transport_provider: str,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], list[Any]]:
        nonlocal call_index
        call_index += 1
        calls.append({"transport_provider": transport_provider, **kwargs})
        if call_index == 1:
            return _first_stage_results(), []
        return (recovery_results or _official_answer_bearing_recovery_results()), []

    def fake_linkup(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        return fake_provider("linkup", **kwargs)

    def fake_tavily(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        return fake_provider("tavily", **kwargs)

    def fake_scout(**_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("Serper scout must not run in this recovery test")

    return build_generic_product_provider_acquisition_runner(
        tavily_product_provider_callable=fake_tavily,
        linkup_product_provider_callable=fake_linkup,
        scout_product_provider_callable=fake_scout,
    )


def _fetch_read_must_not_run(_url: str) -> GenericLiveFetchReadResult:
    raise AssertionError("fetch/read must not run in source-challenge recovery tests")


def _first_stage_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example County Filing Fee Guide",
            "url": "https://example-law.invalid/small-claims-fees",
            "snippet": "Non-official current filing fee explainer.",
            "raw_content": (
                "Example County small claims filing fee guide. The current "
                "small claims filing fee is $42 in this non-official explainer."
            ),
            "rank": 1,
        },
        {
            "title": "Example County Court Fees",
            "url": "https://example-county.gov/court/fees",
            "snippet": "Official fee schedule overview.",
            "raw_content": (
                "Example County official court fee schedule and filing fee "
                "overview without the current small claims amount."
            ),
            "rank": 2,
        },
    ]


def _official_answer_bearing_recovery_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example County Official Small Claims Fee Schedule",
            "url": "https://example-county.gov/court/small-claims-fee-schedule",
            "snippet": "Official current small claims fee schedule.",
            "raw_content": (
                "Example County official small claims fee schedule. The current "
                "small claims filing fee is $42."
            ),
            "rank": 1,
        }
    ]


def _official_generic_recovery_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example County Official Small Claims Filing",
            "url": "https://example-county.gov/court/small-claims",
            "snippet": "Official filing instructions.",
            "raw_content": (
                "Example County official small claims filing instructions, "
                "eligibility, and courthouse hours."
            ),
            "rank": 1,
        }
    ]


def _weak_or_overclaim_review(*_args: Any, **kwargs: Any) -> dict[str, Any]:
    payload = _assessment_payload(
        kwargs["input_packet"],
        support_relation="weak_or_overclaim_risk",
        claim=ANSWER_CLAIM,
    )
    payload["challenge_recommended"] = True
    payload["non_support_reason_when_not_direct"] = (
        "The answer-bearing material is not source-of-record confirmation."
    )
    return payload


def _absent_review(*_args: Any, **kwargs: Any) -> dict[str, Any]:
    return _assessment_payload(
        kwargs["input_packet"],
        support_relation="absent",
        claim=ANSWER_CLAIM,
    )
