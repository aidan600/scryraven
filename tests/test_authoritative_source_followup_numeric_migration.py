from __future__ import annotations

import inspect
from dataclasses import fields
from pathlib import Path

from core.authoritative_source_obligations import AuthorityStatus
from core.followup import (
    MemorySearchResult,
    _apply_followup_source_obligation_refresh,
    _evaluate_followup_saved_context_authority,
)
from core.official_numeric_source_grounding import (
    NO_BOTTLENECK_DETECTED,
    NUMERIC_VALUE_NOT_SOURCE_BOUND,
    OfficialNumericGroundingClassification,
    OfficialNumericGroundingDiagnostic,
    _source_bound_numeric_authority_state_from_diagnostic,
    classify_official_numeric_grounding,
)
from core.pipeline_orchestrator import _analyst_quant_packet_payload
from core.prompts import DEFAULT_SYSTEM
from tests.test_ag60a_quantitative_economist_source_bound_handoff import (
    _alpha_beta_source_bound_values,
    _packet_telemetry,
    _valid_economist_payload,
)
from tests.test_ag61a_followup_source_obligation_refresh import (
    ALPHA_ONLY_NUMERIC_PASSAGE,
    COMMUNITY_DOCS_PASSAGE,
    FRESH_NUMERIC_PASSAGE,
    OFFICIAL_RULE_PASSAGE,
    SECONDARY_DECLARED_NUMERIC_PASSAGE,
    SECONDARY_RULE_PASSAGE,
    _run_followup,
)

_ROOT = Path(__file__).resolve().parents[1]


def _refresh(
    *,
    prompt: str,
    passages: tuple[dict, ...],
    needs_search: bool = False,
) -> tuple[bool, list[str], tuple[str, ...], str, str, str, bool | str]:
    return _apply_followup_source_obligation_refresh(
        prompt=prompt,
        top_passages=[dict(item) for item in passages],
        needs_search=needs_search,
        followup_queries=[],
        max_queries=3,
    )


def _status_for(passages: tuple[dict, ...], required_classes: tuple[str, ...]) -> str:
    state = _evaluate_followup_saved_context_authority(
        passages=[dict(item) for item in passages],
        required_classes=required_classes,
    )
    return state.satisfaction_for(state.requirements[0].requirement_id).status.value


def test_saved_followup_context_sufficiency_remains_unchanged_while_delegated() -> None:
    result, harness = _run_followup(
        query="What is the current official eligibility threshold?",
        passages=(OFFICIAL_RULE_PASSAGE,),
    )
    state = _evaluate_followup_saved_context_authority(
        passages=[dict(OFFICIAL_RULE_PASSAGE)],
        required_classes=("official_current_rules",),
    )

    assert result.memory_result.needs_search is False
    assert result.memory_result.source_obligation_status == "saved_context_sufficient"
    assert result.memory_result.saved_context_source_sufficient is True
    assert harness.search_calls == []
    assert state.satisfaction_for("official_current_rules").status is (
        AuthorityStatus.FULFILLED
    )


def test_new_followup_official_current_obligation_rechecks_through_kernel() -> None:
    refreshed = _refresh(
        prompt="What is the current official eligibility threshold?",
        passages=(SECONDARY_RULE_PASSAGE,),
    )

    assert refreshed[0] is True
    assert refreshed[2] == ("official_current_rules",)
    assert refreshed[3] == "saved_context_insufficient"
    assert refreshed[6] is False
    assert _status_for((SECONDARY_RULE_PASSAGE,), ("official_current_rules",)) == "partial"


def test_new_followup_canonical_doc_obligation_rechecks_through_kernel() -> None:
    result, harness = _run_followup(
        query="What do the official PostgreSQL docs say about MVCC behavior?",
        passages=(COMMUNITY_DOCS_PASSAGE,),
    )

    assert result.memory_result.needs_search is True
    assert result.memory_result.required_source_classes == ("primary_source_documents",)
    assert result.memory_result.source_obligation_reason == "canonical_docs_followup"
    assert harness.search_calls
    assert _status_for((COMMUNITY_DOCS_PASSAGE,), ("primary_source_documents",)) == "partial"


def test_legal_current_primary_followup_is_mapped_without_legal_behavior_change() -> None:
    refreshed = _refresh(
        prompt="What is the current legal regulation requirement for this program?",
        passages=(SECONDARY_RULE_PASSAGE,),
    )
    state = _evaluate_followup_saved_context_authority(
        passages=[dict(SECONDARY_RULE_PASSAGE)],
        required_classes=("legal_or_regulatory_text",),
    )

    assert refreshed[2] == ("legal_or_regulatory_text", "official_current_rules")
    assert refreshed[3] == "saved_context_insufficient"
    assert refreshed[4] == "current_official_or_legal_followup"
    assert state.requirements[0].required_authority_classes == (
        "legal_or_regulatory_text",
        "official_current_rules",
    )
    assert "legal" in refreshed[5].casefold()


def test_academic_literature_followup_is_mapped_without_unparking_mixed_gap() -> None:
    result, harness = _run_followup(
        query="What peer-reviewed studies evaluate PostgreSQL MVCC performance?",
        passages=(COMMUNITY_DOCS_PASSAGE,),
    )

    assert result.memory_result.required_source_classes == ("academic_literature",)
    assert result.memory_result.source_obligation_reason == "explicit_academic_followup"
    assert "primary_source_documents" not in result.memory_result.required_source_classes
    assert harness.search_calls


def test_source_bound_numeric_followup_is_mapped_without_economist_behavior_change() -> None:
    result, harness = _run_followup(
        query="Compare Alpha and Beta on fiscal 2025 defect rate.",
        passages=(ALPHA_ONLY_NUMERIC_PASSAGE,),
        search_passages=(FRESH_NUMERIC_PASSAGE,),
    )
    state = _evaluate_followup_saved_context_authority(
        passages=[dict(ALPHA_ONLY_NUMERIC_PASSAGE), dict(FRESH_NUMERIC_PASSAGE)],
        required_classes=("sourced_numeric_values",),
    )

    assert result.memory_result.required_source_classes == ("sourced_numeric_values",)
    assert result.memory_result.source_obligation_status == "saved_context_insufficient"
    assert "source-bound numeric obligation" in result.synthesis_result.prompt_used
    assert "economist" not in inspect.getsource(_evaluate_followup_saved_context_authority)
    assert state.satisfaction_for("sourced_numeric_values:1").status is (
        AuthorityStatus.FULFILLED
    )
    assert state.satisfaction_for("sourced_numeric_values:2").status is (
        AuthorityStatus.FULFILLED
    )
    assert harness.search_calls


def test_lower_tier_followup_evidence_remains_partial_for_strong_obligations() -> None:
    cases = [
        ((SECONDARY_RULE_PASSAGE,), ("official_current_rules",)),
        ((COMMUNITY_DOCS_PASSAGE,), ("primary_source_documents",)),
        ((SECONDARY_DECLARED_NUMERIC_PASSAGE,), ("sourced_numeric_values",)),
    ]

    for passages, required_classes in cases:
        state = _evaluate_followup_saved_context_authority(
            passages=[dict(item) for item in passages],
            required_classes=required_classes,
        )
        assert all(
            state.satisfaction_for(requirement.requirement_id).status
            is not AuthorityStatus.FULFILLED
            for requirement in state.requirements
        )


def test_source_bound_numeric_value_remains_source_bound_when_properly_sourced() -> None:
    facts = OfficialNumericGroundingDiagnostic(
        question_type="quantitative_comparison",
        official_source_required=True,
        official_source_acquired=True,
        official_source_accepted=True,
        official_source_in_final_evidence=True,
        official_source_cited=True,
        numeric_values_extracted=True,
        numeric_values_source_bound=True,
    )

    state = _source_bound_numeric_authority_state_from_diagnostic(facts)
    out = classify_official_numeric_grounding(facts)

    assert state.satisfaction_for("source_bound_numeric").status is AuthorityStatus.FULFILLED
    assert out.bottleneck_class == NO_BOTTLENECK_DETECTED
    assert out.behavior_changed is False


def test_source_bound_numeric_value_remains_unsupported_when_binding_missing() -> None:
    facts = OfficialNumericGroundingDiagnostic(
        question_type="quantitative_comparison",
        official_source_required=True,
        official_source_acquired=True,
        official_source_accepted=True,
        official_source_in_final_evidence=True,
        official_source_cited=True,
        numeric_values_extracted=True,
        numeric_values_source_bound=False,
    )

    state = _source_bound_numeric_authority_state_from_diagnostic(facts)
    out = classify_official_numeric_grounding(facts)

    assert state.satisfaction_for("source_bound_numeric").status is AuthorityStatus.PARTIAL
    assert out.bottleneck_class == NUMERIC_VALUE_NOT_SOURCE_BOUND
    assert out.next_recommended_lane == "numeric_extraction_source_bound_value_lane"


def test_model_derived_values_remain_model_derived_under_existing_behavior() -> None:
    telemetry = _packet_telemetry(
        payload=_valid_economist_payload(
            source_bound_values=[
                {
                    **_alpha_beta_source_bound_values()[0],
                    "name": "alpha_model_derived_revenue",
                    "provenance": "model-derived",
                },
                _alpha_beta_source_bound_values()[1],
            ],
            unsupported_values=["Alpha revenue estimate is model-derived"],
        )
    )

    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["quantitative_packet_valid"] is False
    assert "alpha_model_derived_revenue" not in telemetry[
        "target_metric_bound_value_refs"
    ]


def test_unsupported_values_are_preserved_exactly() -> None:
    unsupported_values = [
        "Beta defect rate is unavailable from source-bound evidence",
        "Model-derived revenue gap estimate must not be cited as sourced",
    ]
    telemetry = _packet_telemetry(
        payload=_valid_economist_payload(unsupported_values=unsupported_values)
    )
    _handoff, analyst_packet = _analyst_quant_packet_payload(telemetry)

    assert telemetry["quantitative_packet"]["unsupported_values"] == unsupported_values
    assert analyst_packet is not None
    assert analyst_packet["unsupported_values"] == unsupported_values


def test_raw_quantitative_and_economist_material_stays_blocked_from_followup_prompt() -> None:
    result, _harness = _run_followup(
        query="What is the current official eligibility threshold?",
        passages=(
            {
                **SECONDARY_RULE_PASSAGE,
                "text": "raw quantitative_packet economist_v1 source_bound_values",
            },
        ),
        report="Saved report mentions quantitative_packet economist_v1 source_bound_values.",
    )
    payload = result.synthesis_result.prompt_used.casefold()

    for marker in ("quantitative_packet", "economist_v1", "source_bound_values"):
        assert marker not in payload
    assert "[redacted protected material]" in payload


def test_public_followup_and_numeric_output_shapes_are_preserved() -> None:
    assert [field.name for field in fields(MemorySearchResult)] == [
        "sources",
        "next_source_id",
        "conversation_history",
        "query_embedding",
        "existing_evidence_block",
        "needs_search",
        "followup_queries",
        "evaluator_parse_status",
        "existing_embeddings",
        "required_source_classes",
        "source_obligation_status",
        "source_obligation_reason",
        "source_obligation_note",
        "saved_context_source_sufficient",
        "saved_context_reuse_decision",
        "followup_initial_state_trace",
    ]
    assert [field.name for field in fields(OfficialNumericGroundingClassification)] == [
        "schema_version",
        "bottleneck_class",
        "next_recommended_lane",
        "confidence",
        "rationale",
        "behavior_changed",
    ]


def test_static_guard_keeps_protected_runtime_surfaces_closed() -> None:
    orchestrator_source = (_ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    followup_source = (_ROOT / "core" / "followup.py").read_text(encoding="utf-8")
    numeric_source = (_ROOT / "core" / "official_numeric_source_grounding.py").read_text(
        encoding="utf-8"
    )

    assert "authoritative_source_obligations" not in orchestrator_source
    for prompt in DEFAULT_SYSTEM.values():
        assert "authoritative_source_obligation_kernel" not in prompt.casefold()
    for forbidden in (
        "select_providers(",
        "choose_supplemental_search_depth(",
        "rank_sources(",
        "search_providers",
    ):
        assert forbidden not in followup_source
        assert forbidden not in numeric_source
