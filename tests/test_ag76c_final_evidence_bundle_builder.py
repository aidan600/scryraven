from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.final_evidence_bundle_builder import (
    FinalEvidenceBundleInputs,
    assign_stable_source_ids,
    attach_author_evidence,
    build_cached_prefix,
    build_final_evidence_bundle,
    build_final_source_telemetry_inputs,
    post_final_source_class_handoff_from_final_evidence_bundle,
)

_ROOT = Path(__file__).resolve().parents[1]
_BUILDER_PATH = _ROOT / "core" / "final_evidence_bundle_builder.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _passage(
    title: str,
    url: str,
    text: str,
    score: float,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "title": title,
        "url": url,
        "text": text,
        "score": score,
        **extra,
    }


def _filter_top_evidence(
    passages: list[dict[str, Any]],
    top_chunks: int,
    max_domain_chunks: int,
) -> list[dict[str, Any]]:
    assert max_domain_chunks == 3
    return passages[:top_chunks]


def _is_plausible_domain(url: str) -> bool:
    return bool(url) and "implausible.example" not in url


def _legacy_assign_source_ids(
    final_top_evidence: list[dict[str, Any]],
) -> tuple[dict[str, int], list[str]]:
    unique_source_urls: dict[str, int] = {}
    ordered_sources: list[str] = []
    next_source_id = 1
    for p in final_top_evidence:
        if p["url"] not in unique_source_urls:
            unique_source_urls[p["url"]] = next_source_id
            if _is_plausible_domain(p["url"]):
                ordered_sources.append(f"- [{next_source_id}] [{p['title']}]({p['url']})")
            next_source_id += 1
        p["source_id"] = unique_source_urls[p["url"]]
    return unique_source_urls, ordered_sources


def _legacy_evidence_block(passages: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"[Source {p['source_id']}] {p['title']}\nURL: {p['url']}\nExcerpt: {p['text'][:1200]}"
        for p in passages
    )


def _legacy_cached_prefix(evidence_block: str) -> str:
    return (
        f"<evidence_block>\n{evidence_block}\n</evidence_block>\n\n"
        "Today is 2026-05-28.\nUser's Original Prompt: compare source IDs\n"
    )


def _bundle_fixture() -> list[dict[str, Any]]:
    return [
        _passage("Lower score", "https://later.example/b", "later", 0.2),
        _passage("Alpha", "https://alpha.example/a", "alpha " * 250, 0.9),
        _passage("Duplicate alpha", "https://alpha.example/a", "duplicate", 0.8),
        _passage(
            "Implausible",
            "https://implausible.example/click",
            "implausible",
            0.7,
        ),
        _passage("Empty URL", "", "empty url", 0.6),
    ]


def test_assign_stable_source_ids_matches_legacy_order_duplicates_and_sources() -> None:
    passages = [
        _passage("Alpha", "https://alpha.example/a", "alpha", 1.0),
        _passage("Duplicate alpha", "https://alpha.example/a", "duplicate", 0.9),
        _passage("Beta", "https://beta.example/b", "beta", 0.8),
        _passage("Implausible", "https://implausible.example/c", "bad", 0.7),
        _passage("Empty URL", "", "empty", 0.6),
    ]
    expected_passages = deepcopy(passages)
    expected_urls, expected_sources = _legacy_assign_source_ids(expected_passages)

    identity = assign_stable_source_ids(
        passages,
        is_plausible_domain=_is_plausible_domain,
    )

    assert passages == expected_passages
    assert identity.unique_source_urls == expected_urls
    assert identity.ordered_sources == expected_sources
    assert [p["source_id"] for p in passages] == [1, 1, 2, 3, 4]
    assert identity.ordered_sources == [
        "- [1] [Alpha](https://alpha.example/a)",
        "- [2] [Beta](https://beta.example/b)",
    ]


def test_assign_stable_source_ids_preserves_missing_url_keyerror() -> None:
    with pytest.raises(KeyError):
        assign_stable_source_ids(
            [{"title": "Missing URL", "text": "missing"}],
            is_plausible_domain=_is_plausible_domain,
        )


def test_build_final_evidence_bundle_matches_legacy_blocks_and_recovery_handoff() -> None:
    all_passages = _bundle_fixture()
    recovered_seen: dict[str, Any] = {}

    def recovered_visibility(**kwargs: Any) -> list[dict[str, Any]]:
        recovered_seen.update(kwargs)
        return kwargs["final_top_evidence"] + [kwargs["all_passages"][3]]

    expected_all_passages = sorted(
        deepcopy(all_passages),
        key=lambda p: p.get("score", 0),
        reverse=True,
    )
    expected_final = _filter_top_evidence(expected_all_passages, 3, 3)
    expected_final = expected_final + [expected_all_passages[3]]
    expected_urls, expected_sources = _legacy_assign_source_ids(expected_final)
    expected_block = _legacy_evidence_block(expected_final)

    bundle = build_final_evidence_bundle(
        FinalEvidenceBundleInputs(
            all_passages=all_passages,
            top_chunks=3,
            max_domain_chunks=3,
            filter_top_evidence=_filter_top_evidence,
            is_plausible_domain=_is_plausible_domain,
            current_date="2026-05-28",
            query="compare source IDs",
            active_source_class_recovery_lifecycle={"active": True},
            recovered_evidence_visibility=recovered_visibility,
        ),
    )

    assert all_passages == expected_all_passages
    assert bundle.final_top_evidence == expected_final
    assert bundle.unique_source_urls == expected_urls
    assert bundle.ordered_sources == expected_sources
    assert bundle.evidence_block == expected_block
    assert bundle.cached_prefix == _legacy_cached_prefix(expected_block)
    assert recovered_seen["lifecycle_trace"] == {"active": True}
    assert recovered_seen["max_final_evidence"] == 3
    assert recovered_seen["reserve_limit"] == 1


def test_bundle_owns_recovered_visibility_post_final_handoff() -> None:
    all_passages = _bundle_fixture()
    lifecycle = {
        "authority_lifecycle": {
            "recovery_action": {
                "required_source_classes": [
                    "official_current_rules",
                    "legal_or_regulatory_text",
                ]
            }
        }
    }

    def recovered_visibility(**kwargs: Any) -> list[dict[str, Any]]:
        kwargs["lifecycle_trace"].update(
            {
                "recovered_visibility_used": True,
                "recovered_visibility_missing_source_class": (
                    "official_current_rules"
                ),
            }
        )
        return kwargs["final_top_evidence"]

    bundle = build_final_evidence_bundle(
        FinalEvidenceBundleInputs(
            all_passages=all_passages,
            top_chunks=3,
            max_domain_chunks=3,
            filter_top_evidence=_filter_top_evidence,
            is_plausible_domain=_is_plausible_domain,
            current_date="2026-05-28",
            query="compare source IDs",
            active_source_class_recovery_lifecycle=lifecycle,
            recovered_evidence_visibility=recovered_visibility,
        ),
    )
    handoff = post_final_source_class_handoff_from_final_evidence_bundle(
        bundle,
        source_class_recovery_telemetry={"recommendation": "base"},
        source_class_observability_telemetry={"observed": True},
        active_source_class_recovery_lifecycle=lifecycle,
    )

    assert bundle.recovered_visibility_trace["recovered_visibility_used"] is True
    assert handoff.source_class_recovery_telemetry["observed"] is True
    assert handoff.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_missing_classes"
    ] == ["legal_or_regulatory_text"]


def test_cached_prefix_supports_supplemental_and_remediation_linkup_rebuild_parity() -> None:
    all_passages = _bundle_fixture()
    initial = build_final_evidence_bundle(
        FinalEvidenceBundleInputs(
            all_passages=all_passages,
            top_chunks=2,
            max_domain_chunks=3,
            filter_top_evidence=_filter_top_evidence,
            is_plausible_domain=_is_plausible_domain,
            current_date="2026-05-28",
            query="compare source IDs",
        ),
    )
    all_passages.extend(
        [
            _passage("Supplemental", "https://supp.example/d", "supp", 0.95),
            _passage("Remediation", "https://remed.example/e", "remed", 0.96),
        ]
    )

    rebuilt = build_final_evidence_bundle(
        FinalEvidenceBundleInputs(
            all_passages=all_passages,
            top_chunks=3,
            max_domain_chunks=3,
            filter_top_evidence=_filter_top_evidence,
            is_plausible_domain=_is_plausible_domain,
            current_date="2026-05-28",
            query="compare source IDs",
        ),
        linkup_block="\nLINKUP BLOCK\n",
    )

    assert initial.cached_prefix == build_cached_prefix(
        evidence_block=initial.evidence_block,
        current_date="2026-05-28",
        query="compare source IDs",
    )
    assert rebuilt.final_top_evidence[0]["title"] == "Remediation"
    assert rebuilt.final_top_evidence[1]["title"] == "Supplemental"
    assert rebuilt.cached_prefix == (
        build_cached_prefix(
            evidence_block=rebuilt.evidence_block,
            current_date="2026-05-28",
            query="compare source IDs",
        )
        + "\nLINKUP BLOCK\n"
    )


def test_author_evidence_slice_and_block_match_legacy_formatting() -> None:
    final_top_evidence = [
        _passage("One", "https://one.example", "one", 3.0),
        _passage("Two", "https://two.example", "two", 2.0),
        _passage("Three", "https://three.example", "three", 1.0),
    ]
    _legacy_assign_source_ids(final_top_evidence)
    bundle = build_final_evidence_bundle(
        FinalEvidenceBundleInputs(
            all_passages=final_top_evidence,
            top_chunks=3,
            max_domain_chunks=3,
            filter_top_evidence=_filter_top_evidence,
            is_plausible_domain=_is_plausible_domain,
            current_date="2026-05-28",
            query="compare source IDs",
        ),
    )

    attach_author_evidence(bundle, precision_count=2)

    assert bundle.author_evidence == bundle.final_top_evidence[:2]
    assert bundle.author_evidence_block == _legacy_evidence_block(
        bundle.final_top_evidence[:2]
    )


def test_final_source_telemetry_and_snapshot_payload_match_existing_values() -> None:
    final_top_evidence = [
        _passage("One", "https://one.example", "one", 3.0),
        _passage("Two", "https://two.example", "two", 2.0),
    ]
    unique_source_urls, ordered_sources = _legacy_assign_source_ids(final_top_evidence)
    final_answer_source_telemetry = {
        "final_answer_source_ids_used": ["1"],
        "final_answer_source_telemetry_shadow_mode": True,
    }

    telemetry = build_final_source_telemetry_inputs(
        final_top_evidence=final_top_evidence,
        unique_source_urls=unique_source_urls,
        ordered_sources=ordered_sources,
        seen_urls=["https://one.example", "https://two.example"],
        collected_images=["https://image.example/one.png"],
        final_answer_source_telemetry=final_answer_source_telemetry,
    )

    assert telemetry.source_ids == [1, 2]
    assert telemetry.unique_source_url_count == 2
    assert telemetry.ordered_sources == ordered_sources
    assert telemetry.final_evidence_count == 2
    assert telemetry.final_answer_source_telemetry == final_answer_source_telemetry
    assert telemetry.final_evidence_snapshot_payload == {
        "final_top_evidence": final_top_evidence,
        "seen_urls": ["https://one.example", "https://two.example"],
        "collected_images": ["https://image.example/one.png"],
    }


def test_pipeline_orchestrator_no_longer_owns_final_source_id_assignment_loop() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    assert "next_source_id" not in orchestrator_source
    assert "unique_source_urls = {}" not in orchestrator_source
    assert "p[\"source_id\"] = unique_source_urls[p[\"url\"]]" not in orchestrator_source
    assert "build_final_evidence_bundle(" in orchestrator_source
    assert "attach_selected_authority_evidence_to_final_bundle(" in orchestrator_source
    assert "build_final_source_telemetry_inputs(" in orchestrator_source
    assert "recovered_visibility_used" not in orchestrator_source
    assert "recovered_visibility_missing_source_class" not in orchestrator_source


def test_final_evidence_builder_does_not_import_or_call_protected_surfaces() -> None:
    tree = ast.parse(_BUILDER_PATH.read_text(encoding="utf-8"))
    protected_import_fragments = (
        "pipeline_decision_registry",
        "author",
        "citation",
        "provider",
        "query",
        "classifier",
        "fit",
        "pipeline_orchestrator",
    )
    protected_call_names = {
        "ask_model",
        "build_final_answer",
        "select_providers",
        "process_search_queries",
        "source_classifier",
        "candidate_fit",
        "author_prompt",
        "citation_format",
        "citation_selection",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(
                    fragment in alias.name.casefold()
                    for fragment in protected_import_fragments
                )
        if isinstance(node, ast.ImportFrom):
            module = (node.module or "").casefold()
            assert not any(fragment in module for fragment in protected_import_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in protected_call_names
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in protected_call_names
