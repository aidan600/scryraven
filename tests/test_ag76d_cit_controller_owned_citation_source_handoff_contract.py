from __future__ import annotations

from pathlib import Path

from core.analyst_author_handoff_contract import build_analyst_author_handoff_state
from core.citation_source_handoff_contract import (
    CITATION_SOURCE_HANDOFF_SCHEMA_VERSION,
    CITATION_SOURCE_HANDOFF_TRACE_KEY,
    build_citation_source_handoff_state,
    execute_citation_source_handoff,
)
from core.final_evidence_bundle_builder import (
    FinalEvidenceBundleInputs,
    attach_author_evidence,
    build_final_evidence_bundle,
    build_final_source_telemetry_inputs,
)
from tests.static_import_guard_utils import assert_controller_contract_imports_closed

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "core" / "citation_source_handoff_contract.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
SESSION_OUTPUT_PROJECTION = ROOT / "core" / "session_output_projection.py"


def _passages() -> list[dict[str, object]]:
    return [
        {
            "title": "Official A",
            "url": "https://official.example/rules",
            "text": "A" * 50,
            "score": 0.99,
            "source_tier": "official",
            "source_class": "official_current_rules",
        },
        {
            "title": "Official A duplicate",
            "url": "https://official.example/rules",
            "text": "A duplicate" * 10,
            "score": 0.91,
            "source_tier": "official",
            "source_class": "official_current_rules",
        },
        {
            "title": "Secondary B",
            "url": "https://news.example/context",
            "text": "B" * 50,
            "score": 0.87,
            "source_tier": "secondary",
            "source_class": "reputable_secondary",
        },
        {
            "title": "Rejected URL",
            "url": "mailto:not-a-source",
            "text": "C" * 50,
            "score": 0.77,
        },
    ]


def _bundle():
    bundle = build_final_evidence_bundle(
        FinalEvidenceBundleInputs(
            all_passages=_passages(),
            top_chunks=4,
            max_domain_chunks=4,
            filter_top_evidence=lambda passages, top, _max: list(passages)[:top],
            is_plausible_domain=lambda url: str(url).startswith("https://"),
            current_date="2026-05-31",
            query="What are the rules?",
        )
    )
    return attach_author_evidence(bundle, precision_count=2)


def _analyst_author_state(bundle):
    return build_analyst_author_handoff_state(
        run_id="run-cit",
        analyst_skipped=False,
        analyst_skip_reason=None,
        post_retrieval_fast_path_used=False,
        pre_analyst_gate_signals=[],
        analyst_evidence=bundle.final_top_evidence,
        analyst_context_prefix=bundle.cached_prefix,
        corpus_weak=False,
        failure_card_payload={"show": False, "reason": ""},
        author_notes="",
        author_evidence=bundle.author_evidence,
        selected_evidence=bundle.final_top_evidence,
        final_evidence=bundle.final_top_evidence,
        ordered_sources=bundle.ordered_sources,
        unique_source_urls=bundle.unique_source_urls,
        author_evidence_block=bundle.author_evidence_block,
        source_telemetry_ref={"source_ids": [1, 1, 2, 3]},
        author_prompt="Today is 2026-05-31. Precision Evidence follows.",
        complexity="medium",
        author_system_prompt_key="author",
        author_effort="medium",
        includes_analysis=True,
        includes_recency_notes=False,
        includes_author_notes=False,
        image_context_active=False,
        answer_contract_ref={"answer_contract": "runtime"},
        final_evidence_ref={"final_evidence_count": 4},
    )


def _state():
    bundle = _bundle()
    final_answer_source_telemetry = {
        "final_answer_source_ids_used": ["1", "2"],
        "final_answer_source_ids_not_in_packet": ["1"],
        "packet_source_ids_not_in_final_answer": [],
        "final_answer_packet_source_ids_diverged": True,
        "final_answer_source_telemetry_shadow_mode": True,
    }
    source_telemetry = build_final_source_telemetry_inputs(
        final_top_evidence=bundle.final_top_evidence,
        unique_source_urls=bundle.unique_source_urls,
        ordered_sources=bundle.ordered_sources,
        seen_urls=["https://official.example/rules"],
        collected_images=[],
        final_answer_source_telemetry=final_answer_source_telemetry,
    )
    return build_citation_source_handoff_state(
        run_id="run-cit",
        final_evidence=bundle.final_top_evidence,
        selected_evidence=bundle.final_top_evidence,
        author_evidence=bundle.author_evidence,
        unique_source_urls=bundle.unique_source_urls,
        ordered_sources=bundle.ordered_sources,
        evidence_block=bundle.evidence_block,
        cached_prefix=bundle.cached_prefix,
        author_evidence_block=bundle.author_evidence_block,
        final_answer_source_telemetry=final_answer_source_telemetry,
        final_citation_observation_refs=final_answer_source_telemetry[
            "final_answer_source_ids_used"
        ],
        final_evidence_bundle_ref={
            "final_evidence_count": len(bundle.final_top_evidence),
            "author_evidence_count": len(bundle.author_evidence),
            "ordered_source_count": len(bundle.ordered_sources),
            "unique_source_url_count": len(bundle.unique_source_urls),
        },
        ledger_ref={"final_evidence_snapshot_recorded": True},
        answer_contract_ref={"answer_contract": "runtime"},
        analyst_author_handoff_state=_analyst_author_state(bundle),
        source_telemetry_ref={
            "source_ids": list(source_telemetry.source_ids),
            "ordered_sources": list(source_telemetry.ordered_sources),
            "final_answer_source_telemetry": dict(
                source_telemetry.final_answer_source_telemetry
            ),
        },
    )


def test_source_id_parity_and_duplicate_url_reuse_are_copied_without_reassignment():
    bundle = _bundle()
    state = _state()
    envelope = execute_citation_source_handoff(state)

    assert envelope.unique_source_urls == bundle.unique_source_urls
    assert [p["source_id"] for p in bundle.final_top_evidence] == [1, 1, 2, 3]
    trace = state.to_controller_state()["source_identity"]
    assert trace["source_id_mapping"] == [
        {
            "source_id": 1,
            "url": "https://official.example/rules",
            "title": "Official A",
            "domain": "official.example",
            "first_final_evidence_position": 1,
        },
        {
            "source_id": 2,
            "url": "https://news.example/context",
            "title": "Secondary B",
            "domain": "news.example",
            "first_final_evidence_position": 3,
        },
        {
            "source_id": 3,
            "url": "mailto:not-a-source",
            "title": "Rejected URL",
            "domain": "mailto:not-a-source",
            "first_final_evidence_position": 4,
        },
    ]
    assert trace["duplicate_url_reuse_facts"] == [
        {
            "url": "https://official.example/rules",
            "source_id": 1,
            "positions": [1, 2],
            "duplicate_count": 1,
            "source_id_reused": True,
        }
    ]
    assert trace["source_id_assignment_included"] is False


def test_ordered_source_parity_and_handoff_envelope_preserve_lines():
    bundle = _bundle()
    state = _state()
    envelope = execute_citation_source_handoff(state)

    assert envelope.ordered_sources == bundle.ordered_sources
    assert state.to_controller_state()["ordered_source_list"]["ordered_sources"] == [
        "- [1] [Official A](https://official.example/rules)",
        "- [2] [Secondary B](https://news.example/context)",
    ]
    assert state.to_controller_state()["ordered_source_list"]["source_list_formatting_included"] is False


def test_author_source_input_parity_hashes_existing_blocks_without_prompt_text():
    bundle = _bundle()
    trace = _state().to_controller_state()["author_source_inputs"]

    assert trace["evidence_block_length"] == len(bundle.evidence_block)
    assert trace["cached_prefix_length"] == len(bundle.cached_prefix)
    assert trace["author_evidence_block_length"] == len(bundle.author_evidence_block)
    assert trace["evidence_block_hash"]
    assert trace["cached_prefix_hash"]
    assert trace["author_evidence_block_hash"]
    assert trace["prompt_text_included"] is False
    assert trace["author_prompt_input_ref"]["prompt_text_included"] is False


def test_final_citation_observation_parity_and_trace_compatibility():
    state = _state()
    trace = state.to_trace_fragment()[CITATION_SOURCE_HANDOFF_TRACE_KEY]
    envelope = execute_citation_source_handoff(state)

    assert state.schema_version == CITATION_SOURCE_HANDOFF_SCHEMA_VERSION
    assert trace["citation_observations"]["final_answer_source_telemetry"] == {
        "final_answer_source_ids_used": ["1", "2"],
        "final_answer_source_ids_not_in_packet": ["1"],
        "packet_source_ids_not_in_final_answer": [],
        "final_answer_packet_source_ids_diverged": True,
        "final_answer_source_telemetry_shadow_mode": True,
    }
    assert envelope.final_answer_source_telemetry == trace["citation_observations"][
        "final_answer_source_telemetry"
    ]
    assert trace["citation_observations"]["final_citation_observation_refs"] == [
        "1",
        "2",
    ]
    assert trace["trace_visibility"]["additive_only"] is True


def test_controller_owned_visibility_ledger_answer_contract_and_aa_integration():
    trace = _state().to_controller_state()

    assert trace["controller_owned"] is True
    assert [
        item["source_id"] for item in trace["citation_eligibility"]["final_evidence_refs"]
    ] == [1, 1, 2, 3]
    assert trace["citation_eligibility"]["citation_eligible_source_ids"] == [1, 2, 3]
    assert trace["final_evidence_bundle_ref"] == {
        "final_evidence_count": 4,
        "author_evidence_count": 2,
        "ordered_source_count": 2,
        "unique_source_url_count": 3,
    }
    assert trace["ledger_ref"] == {
        "final_evidence_snapshot_recorded": True
    }
    assert trace["answer_contract_ref"] == {"answer_contract": "runtime"}
    assert trace["analyst_author_handoff_ref"]["controller_owned"] is True
    assert trace["analyst_author_handoff_ref"]["author_prompt_input"][
        "prompt_text_included"
    ] is False


def test_static_protected_import_guard_for_citation_source_contract():
    assert_controller_contract_imports_closed(
        CONTRACT,
        allowed_import_roots={"copy", "dataclasses", "hashlib", "typing"},
        forbidden_module_fragments=(
            "ask_model",
            "provider",
            "search",
            "prompts",
            "author",
            "final_answer",
            "economist",
            "scrutineer",
            "follow_up",
            "session",
            "run_outcome",
            "cache",
            "pipeline_orchestrator",
            "database",
            "sqlite",
        ),
    )


def test_orchestrator_authority_guard_wires_citation_contract_additively():
    pipeline = PIPELINE.read_text() + SESSION_OUTPUT_PROJECTION.read_text()
    contract = CONTRACT.read_text()

    assert "build_citation_source_handoff_state" in pipeline
    assert "execute_citation_source_handoff" in pipeline
    assert "citation_source_handoff_trace_fragment" in pipeline
    assert "citation_source_handoff_state = build_citation_source_handoff_state" in pipeline
    assert "build_evidence_block(" not in pipeline
    assert "next_source_id" not in pipeline
    assert "final_answer_source_ids_used" in pipeline
    assert "ask_model(" not in contract
    assert "DEFAULT_SYSTEM" not in contract


def test_protected_surface_guard_and_no_live_product_path_guard():
    contract = CONTRACT.read_text()
    pipeline = PIPELINE.read_text()

    forbidden_contract_calls = (
        "ask_model(",
        "process_search_queries(",
        "RunOutcome",
        "sqlite",
        "DEFAULT_SYSTEM",
        "SCRYRAVEN_",
        "PROPLEX_",
        ".env",
        "stream=True",
    )
    assert [call for call in forbidden_contract_calls if call in contract] == []
    assert "_final_answer_source_citation_telemetry" in pipeline
    assert "build_citation_source_handoff_state" in pipeline


def test_final_answer_fixture_parity_by_stable_handoff_inputs_when_text_is_not_fixture_stable():
    bundle = _bundle()
    state = _state()

    # The product final answer is generated by a provider in the full pipeline, so
    # this offline phase asserts the stable inputs and observations that feed the
    # final citation/source handoff instead of running a live Author call.
    assert state.to_controller_state()["ordered_source_list"]["ordered_sources"] == bundle.ordered_sources
    assert state.to_controller_state()["author_source_inputs"]["evidence_block_length"] == len(
        bundle.evidence_block
    )
    assert state.to_controller_state()["citation_observations"][
        "final_answer_source_telemetry"
    ]["final_answer_source_ids_used"] == ["1", "2"]
