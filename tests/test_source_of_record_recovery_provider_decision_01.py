"""SEAM-DIAGNOSTIC: recovery provider decision harness.

Harness label: SEAM-DIAGNOSTIC
Ordinary product path guarded or fed: generic single-relation source-obligation
recovery acquisition provider-role config.
Runtime consumer: core.single_relation_source_obligation_recovery_authorization
recovery plan consumed by proplex.mvp_single_relation_live_dogfood_run.
Why ordinary product-path work cannot be done directly: offline validation uses
fake provider callables so no live provider/search, broker, fetch/read, model,
FAP, or Author call occurs.
Integration deadline: current phase.
Exit condition: selected provider is wired into the recovery role/config seam,
or the packet records no safe winner and recommends a follow-up.
Why this is not a shadow product path: tests exercise the same product-owned
provider acquisition adapter used by the ordinary runner, with only the live
transport replaced.
Forbidden interpretation: harness PASS is not product correctness, source
authority, source-obligation satisfaction, citation eligibility, D-prime
admission, FAP, Author, or a global provider default.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.generic_product_provider_acquisition import (
    build_generic_product_provider_acquisition_runner,
)
from scripts.source_of_record_recovery_provider_decision_01 import (
    QUALITY_NON_OFFICIAL_ANSWER,
    QUALITY_OFFICIAL_ANSWER,
    QUALITY_OFFICIAL_NOT_ANSWER,
    QUALITY_SCOUT_ONLY,
    run_source_of_record_recovery_provider_decision_comparison,
)


def test_linkup_can_win_recovery_extraction_role_with_fake_callables(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    hidden_answer_sentence = (
        "USCIS source table confirms Form N-400 paper filing fee is $760."
    )

    runner = build_generic_product_provider_acquisition_runner(
        tavily_product_provider_callable=_fake_tavily(calls, answer_bearing=False),
        linkup_product_provider_callable=_fake_linkup(calls, hidden_answer_sentence),
        exa_product_provider_callable=_fake_exa_non_official(calls),
        scout_product_provider_callable=_fake_scout(calls),
    )

    result = run_source_of_record_recovery_provider_decision_comparison(
        repo_root=tmp_path,
        output_root=tmp_path / "output" / "decision",
        run_id="linkup-wins",
        confirm_live_provider_comparison=True,
        product_provider_acquisition_runner=runner,
    )
    packet = result.packet
    buckets = packet["quality_bucket_by_provider"]
    serialized_packet = json.dumps(packet, sort_keys=True)

    assert result.return_code == 0
    assert result.selected_provider == "linkup"
    assert packet["selected_source_of_record_recovery_extraction_provider"] == "linkup"
    assert packet["selected_provider_role"] == (
        "source_of_record_recovery_extraction_provider"
    )
    assert buckets["tavily"] == QUALITY_OFFICIAL_NOT_ANSWER
    assert buckets["linkup"] == QUALITY_OFFICIAL_ANSWER
    assert buckets["exa"] == QUALITY_NON_OFFICIAL_ANSWER
    assert buckets["brave"] == QUALITY_SCOUT_ONLY
    assert buckets["serper"] == QUALITY_SCOUT_ONLY
    assert packet["provider_call_counts"]["total_logical_provider_calls_attempted"] == 5
    assert packet["provider_call_counts"]["fetch_read_calls"] == 0
    assert packet["provider_call_counts"]["model_calls"] == 0
    assert packet["raw_provider_payload_retained"] is False
    assert packet["raw_search_response_retained"] is False
    assert packet["closed_surface_flags"]["global_provider_chooser_created"] is False
    assert packet["closed_surface_flags"]["source_obligation_satisfied"] is False
    assert calls[1][0] == "linkup"
    assert calls[1][1]["output_type"] == "searchResults"
    assert calls[1][1]["include_domains"] == ["uscis.gov"]
    assert hidden_answer_sentence not in serialized_packet
    assert '"provider_extracted_text":' not in serialized_packet


def test_scout_only_promising_urls_do_not_select_provider(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    runner = build_generic_product_provider_acquisition_runner(
        tavily_product_provider_callable=_fake_tavily(calls, answer_bearing=False),
        linkup_product_provider_callable=_fake_linkup_generic(calls),
        exa_product_provider_callable=_fake_exa_generic(calls),
        scout_product_provider_callable=_fake_scout(calls),
    )

    result = run_source_of_record_recovery_provider_decision_comparison(
        repo_root=tmp_path,
        output_root=tmp_path / "output" / "decision",
        run_id="scout-only-no-winner",
        confirm_live_provider_comparison=True,
        product_provider_acquisition_runner=runner,
    )
    packet = result.packet

    assert result.return_code == 2
    assert result.selected_provider is None
    assert result.blocker == "NO_SAFE_SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_SELECTED"
    assert packet["quality_bucket_by_provider"]["brave"] == QUALITY_SCOUT_ONLY
    assert packet["quality_bucket_by_provider"]["serper"] == QUALITY_SCOUT_ONLY
    assert packet["selected_source_of_record_recovery_extraction_provider"] is None
    assert packet["selection_rule"]["scout_only_providers_cannot_win"] is True


def test_comparison_harness_is_default_off(tmp_path: Path) -> None:
    calls: list[Any] = []

    def runner(_request: Any) -> Any:
        calls.append(_request)
        raise AssertionError("provider calls must be confirmation-gated")

    result = run_source_of_record_recovery_provider_decision_comparison(
        repo_root=tmp_path,
        output_root=tmp_path / "output" / "decision",
        run_id="default-off",
        product_provider_acquisition_runner=runner,
    )

    assert result.return_code == 2
    assert result.selected_provider is None
    assert result.packet["decision_blocker"] == "CONFIRM_LIVE_PROVIDER_COMPARISON_REQUIRED"
    assert result.packet["provider_call_counts"]["total_logical_provider_calls_attempted"] == 0
    assert calls == []


def test_output_directory_preflight_blocks_before_provider_calls(tmp_path: Path) -> None:
    calls: list[Any] = []
    output_file = tmp_path / "not-a-directory"
    output_file.write_text("not a directory\n", encoding="utf-8")

    def runner(_request: Any) -> Any:
        calls.append(_request)
        raise AssertionError("provider calls must not run without packet output")

    result = run_source_of_record_recovery_provider_decision_comparison(
        repo_root=tmp_path,
        output_root=output_file,
        run_id="output-blocked",
        confirm_live_provider_comparison=True,
        product_provider_acquisition_runner=runner,
    )

    assert result.return_code == 2
    assert result.selected_provider is None
    assert result.packet["decision_blocker"] == (
        "PROVIDER_DECISION_PACKET_OUTPUT_UNAVAILABLE"
    )
    assert result.packet["provider_call_counts"][
        "total_logical_provider_calls_attempted"
    ] == 0
    assert calls == []


def _fake_tavily(
    calls: list[tuple[str, dict[str, Any]]],
    *,
    answer_bearing: bool,
) -> Any:
    def fake(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        calls.append(("tavily", kwargs))
        text = (
            "USCIS Form N-400 paper filing fee is $760."
            if answer_bearing
            else "USCIS Form N-400 instructions and general filing guidance."
        )
        return (
            [
                {
                    "title": "USCIS Form N-400 Filing Guidance",
                    "url": "https://www.uscis.gov/n-400",
                    "snippet": "Official USCIS guidance.",
                    "raw_content": text,
                }
            ],
            [],
        )

    return fake


def _fake_linkup(
    calls: list[tuple[str, dict[str, Any]]],
    hidden_answer_sentence: str,
) -> Any:
    def fake(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        calls.append(("linkup", kwargs))
        return (
            [
                {
                    "title": "USCIS Fee Schedule",
                    "url": "https://www.uscis.gov/g-1055",
                    "snippet": "Official fee schedule.",
                    "raw_content": hidden_answer_sentence,
                }
            ],
            [],
        )

    return fake


def _fake_linkup_generic(calls: list[tuple[str, dict[str, Any]]]) -> Any:
    def fake(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        calls.append(("linkup", kwargs))
        return (
            [
                {
                    "title": "USCIS Fee Schedule",
                    "url": "https://www.uscis.gov/g-1055",
                    "snippet": "Official fee schedule.",
                    "raw_content": "USCIS Form N-400 general fee instructions.",
                }
            ],
            [],
        )

    return fake


def _fake_exa_non_official(calls: list[tuple[str, dict[str, Any]]]) -> Any:
    def fake(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        calls.append(("exa", kwargs))
        return (
            [
                {
                    "title": "Immigration Fee Explainer",
                    "url": "https://example-law.invalid/n-400-fee",
                    "snippet": "Non-official explainer.",
                    "raw_content": "Example explainer says Form N-400 paper filing fee is $760.",
                }
            ],
            [],
        )

    return fake


def _fake_exa_generic(calls: list[tuple[str, dict[str, Any]]]) -> Any:
    def fake(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        calls.append(("exa", kwargs))
        return (
            [
                {
                    "title": "USCIS General Forms Page",
                    "url": "https://www.uscis.gov/forms",
                    "snippet": "Official forms page.",
                    "raw_content": "USCIS forms overview and instructions.",
                }
            ],
            [],
        )

    return fake


def _fake_scout(calls: list[tuple[str, dict[str, Any]]]) -> Any:
    def fake(**kwargs: Any) -> list[dict[str, Any]]:
        calls.append((str(kwargs["provider"]), kwargs))
        return [
            {
                "title": "USCIS Fee Schedule",
                "url": "https://www.uscis.gov/g-1055",
                "snippet": "Official URL signal only.",
                "position": 1,
            }
        ]

    return fake
