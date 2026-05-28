from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from core.allocation_candidate_selection_activation import (
    allocation_result_candidates_for_existing_selection_corridor,
)
from core.controller_provider_search_allocation import (
    BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
    PROVIDER_SEARCH_ALLOCATION_ACTION,
    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
)
from core.controller_recovery_decision import REQUEST_PROVIDER_SEARCH_REVIEW
from core.final_evidence_bundle_builder import (
    FinalEvidenceBundleInputs,
    build_final_evidence_bundle,
)
from core.recovered_evidence_visibility import (
    apply_controller_recovered_evidence_visibility,
    apply_recovered_evidence_visibility_boundary,
    recovered_evidence_selection_candidates,
)
from core.runtime_trace_projection_assembly import attach_passive_runtime_projection_traces
from core.source_class_recovery_candidate_stream import (
    runner_owned_recovered_candidate_stream,
    source_class_recovery_passage_candidates,
)

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_VISIBILITY_PATH = _ROOT / "core" / "recovered_evidence_visibility.py"
_STREAM_PATH = _ROOT / "core" / "source_class_recovery_candidate_stream.py"


def _official_source(**overrides: Any) -> dict[str, Any]:
    source = {
        "source_id": "official-current-rule",
        "title": "Official current rule",
        "url": "https://agency.gov/current-rule",
        "text": "The agency current rule is in force for 2026.",
        "score": 0.87,
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
        "retrieval_stage": "source_class_recovery",
    }
    source.update(overrides)
    return source


def _context_source(**overrides: Any) -> dict[str, Any]:
    source = {
        "title": "Context analysis",
        "url": "https://analysis.example/context",
        "text": "Background analysis.",
        "score": 0.99,
        "source_tier": "secondary",
        "source_class": "secondary",
    }
    source.update(overrides)
    return source


def _controller_trace(
    allocation_result: dict[str, Any] | None = None,
    *,
    authorized: bool = True,
) -> dict[str, Any]:
    owner = "ControllerRecoveryDecision" if authorized else "local_orchestrator_state"
    return {
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_official_canonical_admitted": True,
        "active_source_class_recovery_missing_classes": ["official_current_rules"],
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_reason": "answer_contract_official_gap_missing",
        "authority_lifecycle": {
            "execution_state": {"state": "attempted", "result_count": 1},
            "recovery_action": {
                "action_type": "recover_missing_source_class",
                "approved": True,
                "required_source_classes": ["official_current_rules"],
                "provider_role": "source_class_recovery",
            },
        },
        PROVIDER_SEARCH_ALLOCATION_TRACE_KEY: {
            PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY: {
                "allocation_owner": owner,
                "authorized_decision": (
                    REQUEST_PROVIDER_SEARCH_REVIEW if authorized else "continue_downstream"
                ),
                "authorized_executor_action": PROVIDER_SEARCH_ALLOCATION_ACTION,
                "bounded_profile": BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
                "executed": allocation_result is not None,
                "execution_attempted": allocation_result is not None,
                "result_count": 1 if allocation_result is not None else 0,
                "new_url_count": 1 if allocation_result is not None else 0,
                "allocation_result_summaries": (
                    [allocation_result] if allocation_result is not None else []
                ),
            }
        },
    }


def _allocation_result(**overrides: Any) -> dict[str, Any]:
    result = {
        "provider_result_id": "provider-result-1",
        "candidate_id": "candidate-1",
        "title": "Allocated official current rule",
        "url": "https://agency.gov/allocation-rule",
        "source_url": "https://agency.gov/allocation-rule",
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
        "classification_reason": "declared_source_class",
    }
    result.update(overrides)
    return result


def _legacy_candidate_stream(
    all_passages: list[dict[str, Any]],
    lifecycle_trace: dict[str, Any],
) -> list[dict[str, Any]]:
    recovered = [
        passage
        for passage in all_passages or ()
        if passage.get("retrieval_stage") == "source_class_recovery"
    ]
    recovered.extend(
        allocation_result_candidates_for_existing_selection_corridor(lifecycle_trace)
    )
    return recovered


def test_ag76c_cs_runner_stream_matches_legacy_stage_scan_order_and_shape() -> None:
    first = _official_source(url="https://agency.gov/current-rule")
    unrelated = _official_source(
        url="https://agency.gov/other-stage",
        retrieval_stage="official_canonical_recovery",
    )
    missing_stage = _official_source(url="https://agency.gov/missing-stage")
    missing_stage.pop("retrieval_stage")
    duplicate_url = _official_source(
        source_id="official-current-rule-duplicate",
        title="Official current rule duplicate",
        url="https://agency.gov/current-rule",
    )
    all_passages = [
        _context_source(),
        first,
        unrelated,
        missing_stage,
        duplicate_url,
    ]
    trace = _controller_trace()

    assert runner_owned_recovered_candidate_stream(
        all_passages=all_passages,
        lifecycle_trace=trace,
    ) == _legacy_candidate_stream(all_passages, trace)
    assert source_class_recovery_passage_candidates(all_passages=all_passages) == [
        first,
        duplicate_url,
    ]


def test_ag76c_cs_allocation_candidates_append_only_with_controller_custody() -> None:
    recovered = _official_source(url="https://agency.gov/stage-rule")
    authorized_trace = _controller_trace(_allocation_result(), authorized=True)
    unauthorized_trace = _controller_trace(_allocation_result(), authorized=False)

    authorized = runner_owned_recovered_candidate_stream(
        all_passages=[recovered],
        lifecycle_trace=authorized_trace,
    )
    unauthorized = runner_owned_recovered_candidate_stream(
        all_passages=[recovered],
        lifecycle_trace=unauthorized_trace,
    )

    assert [source["url"] for source in authorized] == [
        "https://agency.gov/stage-rule",
        "https://agency.gov/allocation-rule",
    ]
    assert authorized[1]["selection_corridor_source"] == (
        "allocation_result_candidate_custody"
    )
    assert [source["url"] for source in unauthorized] == [
        "https://agency.gov/stage-rule"
    ]


def test_ag76c_cs_recovered_selection_output_matches_legacy_candidate_stream() -> None:
    all_passages = [_context_source(), _official_source()]
    trace = _controller_trace(_allocation_result(url="https://agency.gov/backup-rule"))
    expected_trace = deepcopy(trace)
    actual_trace = deepcopy(trace)
    expected_candidates = _legacy_candidate_stream(all_passages, expected_trace)

    expected, expected_decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_context_source()],
        recovered_passages=expected_candidates,
        lifecycle_trace=expected_trace,
        max_final_evidence=2,
        reserve_limit=1,
    )
    actual = apply_controller_recovered_evidence_visibility(
        final_top_evidence=[_context_source()],
        all_passages=all_passages,
        lifecycle_trace=actual_trace,
        max_final_evidence=2,
        reserve_limit=1,
    )

    assert recovered_evidence_selection_candidates(
        all_passages=all_passages,
        lifecycle_trace=trace,
    ) == expected_candidates
    assert [source["url"] for source in actual] == [
        source["url"] for source in expected
    ]
    assert actual_trace["recovered_visibility_source_fit_status"] == (
        expected_decision.source_fit_status
    )


def test_ag76c_cs_lower_tier_allocation_still_cannot_satisfy_current_official() -> None:
    trace = _controller_trace(
        _allocation_result(
            url="https://example.com/forum-thread",
            source_url="https://example.com/forum-thread",
            source_tier="secondary",
            source_class="secondary",
        )
    )

    assert runner_owned_recovered_candidate_stream(
        all_passages=[],
        lifecycle_trace=trace,
    ) == []


def test_ag76c_cs_final_evidence_bundle_uses_same_recovered_selection_output() -> None:
    all_passages = [_context_source(), _official_source()]
    trace = _controller_trace()

    bundle = build_final_evidence_bundle(
        FinalEvidenceBundleInputs(
            all_passages=all_passages,
            top_chunks=2,
            max_domain_chunks=2,
            filter_top_evidence=lambda passages, top_chunks, _max_domain_chunks: list(
                passages[:top_chunks]
            ),
            is_plausible_domain=lambda url: bool(url),
            current_date="2026-05-28",
            query="What is the current rule?",
            active_source_class_recovery_lifecycle=trace,
            recovered_evidence_visibility=apply_controller_recovered_evidence_visibility,
        )
    )

    assert [source["url"] for source in bundle.final_top_evidence] == [
        "https://analysis.example/context",
        "https://agency.gov/current-rule",
    ]
    assert "Official current rule" in bundle.evidence_block
    assert "https://agency.gov/current-rule" in bundle.cached_prefix


def test_ag76c_cs_trace_projection_accepts_runner_stream_without_output_drift() -> None:
    all_passages = [_official_source()]
    legacy_trace = _controller_trace()
    runner_trace = _controller_trace()
    legacy_stream = _legacy_candidate_stream(all_passages, legacy_trace)
    runner_stream = runner_owned_recovered_candidate_stream(
        all_passages=all_passages,
        lifecycle_trace=runner_trace,
    )

    legacy_projected = attach_passive_runtime_projection_traces(
        legacy_trace,
        recovered_passages=legacy_stream,
        final_top_evidence=legacy_stream,
    )
    runner_projected = attach_passive_runtime_projection_traces(
        runner_trace,
        recovered_passages=runner_stream,
        final_top_evidence=runner_stream,
    )

    assert runner_projected["controller_evidence_ledger"] == (
        legacy_projected["controller_evidence_ledger"]
    )
    assert runner_projected["authority_candidate_passport_projection"] == (
        legacy_projected["authority_candidate_passport_projection"]
    )


def test_ag76c_cs_candidate_stream_static_ownership_and_closed_surfaces() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()
    visibility_source = _VISIBILITY_PATH.read_text(encoding="utf-8").casefold()
    stream_source = _STREAM_PATH.read_text(encoding="utf-8").casefold()

    assert "retrieval_stage" not in orchestrator_source
    assert "allocation_result_candidates_for_existing_selection_corridor" not in (
        orchestrator_source
    )
    assert "allocation_result_candidates_for_existing_selection_corridor" not in (
        visibility_source
    )
    assert "for passage in all_passages" not in visibility_source
    assert "runner_owned_recovered_candidate_stream(" in visibility_source
    assert "allocation_result_candidates_for_existing_selection_corridor" in (
        stream_source
    )

    closed_terms = (
        "select_providers(",
        "process_search_queries(",
        "ask_model(",
        "build_final_answer(",
        "candidate_fit(",
        "author_prompt",
        "citation_format",
        "citation_selection",
        "raw_provider_payload",
        "source_classifier",
    )
    for term in closed_terms:
        assert term not in stream_source
