from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.query_shape_contract_resolution import ComponentCandidate, QueryShapeAssessment, QueryShapeKind, SearchMode
from core.semantic_contract_foundation import (
    AnswerComponentContract,
    Materiality,
    QuestionMeaningRecord,
    RequirementPosture,
    ResolverKind,
    SearchWorkPlanRef,
    SemanticSlot,
    SemanticSlotKind,
    SemanticSlotStatus,
    SourceObligationCandidateRef,
    SupportKind,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "semantic_contract_foundation.py"


def _entity_slot(
    *,
    slot_id: str = "slot:entity",
    status: SemanticSlotStatus = SemanticSlotStatus.EXPLICIT,
    confirmation: bool = False,
) -> SemanticSlot:
    return SemanticSlot(
        slot_id=slot_id,
        slot_kind=SemanticSlotKind.ENTITY,
        status=status,
        candidate_values=("IRS", "SSA"),
        selected_value="SSA" if status is SemanticSlotStatus.EXPLICIT else None,
        materiality=Materiality.MATERIAL,
        user_confirmation_required=confirmation,
        normalization_notes=("Use the agency named by the user when explicit.",),
        metadata={
            "safe_note": "kept",
            "raw_prompt": "SENTINEL_RAW_PROMPT",
            "token": "SENTINEL_TOKEN",
        },
    )


def _time_slot(
    *,
    slot_id: str = "slot:time-period",
    status: SemanticSlotStatus = SemanticSlotStatus.IMPLIED,
) -> SemanticSlot:
    return SemanticSlot(
        slot_id=slot_id,
        slot_kind=SemanticSlotKind.TIME_PERIOD,
        status=status,
        selected_value="2026",
        materiality=Materiality.MATERIAL,
        normalization_notes=("Calendar year unless user supplies another basis.",),
    )


def _component(
    component_id: str = "component:taxable-maximum",
    *,
    slot_ids: tuple[str, ...] = ("slot:entity", "slot:time-period"),
    dependencies: tuple[str, ...] = (),
    question: str = "What is the Social Security taxable maximum wage base for 2026?",
) -> AnswerComponentContract:
    return AnswerComponentContract(
        component_id=component_id,
        component_revision="1",
        user_facing_label="Social Security taxable maximum",
        user_facing_question=question,
        requirement_posture=RequirementPosture.REQUIRED,
        acceptance_criteria=("state the numeric wage base", "name the supporting source basis"),
        semantic_slot_ids=slot_ids,
        source_obligation_candidate_ids=("obligation:official-current",),
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
        normalization_policy="Use annual wage-base dollars.",
        dependency_component_ids=dependencies,
        mandatory_caveats=("Currentness depends on the official annual notice.",),
        prohibited_upgrades=("Do not replace official source-bound value with estimate.",),
        materiality=Materiality.MATERIAL,
        metadata={
            "provider_payload": "SENTINEL_PROVIDER",
            "bounded_label": "kept",
        },
    )


def _record(
    *,
    slots: tuple[SemanticSlot, ...] | None = None,
    components: tuple[AnswerComponentContract, ...] | None = None,
    search_ref: SearchWorkPlanRef | None = None,
) -> QuestionMeaningRecord:
    return QuestionMeaningRecord(
        record_id="qmr:ssa-taxable-maximum",
        run_id="run:offline-passive",
        request_id="request:1",
        request_digest="request-digest-001",
        requested_mode="balanced",
        resolver_kind=ResolverKind.PASSIVE_PROPOSAL,
        resolver_version="ag-sem-01-test",
        intent="Answer the current official taxable maximum question.",
        requested_output="Concise answer with official support.",
        semantic_slots=slots or (_entity_slot(), _time_slot()),
        answer_components=components or (_component(),),
        source_obligation_candidate_refs=(
            SourceObligationCandidateRef(
                candidate_id="obligation:official-current",
                obligation_kind="official_current",
                component_candidate_ids=("component:taxable-maximum",),
                strictness="required",
            ),
        ),
        search_work_plan_ref=search_ref,
        metadata={
            "private_log": "SENTINEL_PRIVATE_LOG",
            "safe_review_note": "passive only",
        },
    )


def test_happy_path_question_meaning_record_is_passive_json_safe() -> None:
    record = _record().require_valid()
    payload = record.to_dict()
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["schema_version"] == "semantic_contract_foundation_ag_sem_01_v1"
    assert payload["passive"] is True
    assert payload["canonical_state"] is False
    assert payload["runtime_behavior_changed"] is False
    assert payload["runtime_consumed"] is False
    assert payload["constructs_search_work_plan"] is False
    assert payload["provider_search_behavior_changed"] is False
    assert payload["record_digest"]
    assert payload["contract_lineage"]["proposal_digest"] == payload["record_digest"]
    assert payload["material_ambiguity_count"] == 0
    assert payload["user_confirmation_required"] is False
    assert encoded


def test_json_serialization_is_stable_and_scrubs_sensitive_metadata() -> None:
    record = _record().require_valid()
    first = json.dumps(record.to_dict(), sort_keys=True)
    second = json.dumps(record.to_dict(), sort_keys=True)

    assert first == second
    assert "safe_review_note" in first
    assert "bounded_label" in first
    assert "safe_note" in first
    for sentinel in (
        "SENTINEL_RAW_PROMPT",
        "SENTINEL_TOKEN",
        "SENTINEL_PROVIDER",
        "SENTINEL_PRIVATE_LOG",
    ):
        assert sentinel not in first
    for key in ("raw_prompt", "token", "provider_payload", "private_log"):
        assert key not in first


def test_duplicate_slot_and_component_ids_are_rejected() -> None:
    invalid = _record(
        slots=(_entity_slot(slot_id="dup"), _time_slot(slot_id="dup")),
        components=(_component("dup"), _component("dup")),
    )

    errors = invalid.validate().errors

    assert any("duplicate semantic slot_id" in error for error in errors)
    assert any("duplicate answer component_id" in error for error in errors)
    with pytest.raises(ValueError, match="duplicate semantic slot_id"):
        invalid.require_valid()


def test_unknown_slot_and_dependency_references_are_rejected() -> None:
    invalid = _record(
        components=(
            _component(
                component_id="component:derived",
                slot_ids=("slot:missing",),
                dependencies=("component:missing",),
            ),
        )
    )

    errors = invalid.validate().errors

    assert any("references missing semantic slot slot:missing" in error for error in errors)
    assert any("depends on missing component component:missing" in error for error in errors)


def test_factual_uncertainty_does_not_imply_user_confirmation() -> None:
    factual_uncertainty = _record(
        slots=(
            _entity_slot(status=SemanticSlotStatus.UNRESOLVED, confirmation=False),
            _time_slot(),
        )
    ).require_valid()
    explicit_user_choice = _record(
        slots=(
            _entity_slot(status=SemanticSlotStatus.AMBIGUOUS, confirmation=True),
            _time_slot(),
        )
    ).require_valid()

    factual_payload = factual_uncertainty.to_dict()
    explicit_payload = explicit_user_choice.to_dict()
    assert factual_payload["material_ambiguity_count"] == 1
    assert factual_payload["user_confirmation_required"] is False
    assert explicit_payload["material_ambiguity_count"] == 1
    assert explicit_payload["user_confirmation_required"] is True


def test_record_digest_is_deterministic_and_changes_with_meaningful_content() -> None:
    first = _record().require_valid()
    second = _record().require_valid()
    changed = _record(
        components=(
            _component(
                question="What is the Medicare wage threshold for 2026?",
            ),
        )
    ).require_valid()

    assert first.record_digest == second.record_digest
    assert first.to_dict()["record_digest"] == second.to_dict()["record_digest"]
    assert changed.record_digest != first.record_digest
    assert changed.answer_components[0].component_digest != first.answer_components[0].component_digest


def test_query_shape_relationship_is_passive_and_not_promoted_to_authority() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:ssa-taxable-maximum",
        requested_mode=SearchMode.BALANCED,
        query_shape_kinds=(QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,),
        component_candidates=(
            ComponentCandidate(
                candidate_id="candidate:taxable-maximum",
                component_id="component:taxable-maximum",
                user_facing_subquestion="Find the official taxable maximum.",
            ),
        ),
    ).require_valid()
    record = QuestionMeaningRecord.from_query_shape_assessment(
        record_id="qmr:from-query-shape",
        request_digest="request-digest-002",
        requested_mode="balanced",
        intent="Answer the official current wage-base question.",
        requested_output="Concise answer.",
        semantic_slots=(_entity_slot(), _time_slot()),
        answer_components=(_component(),),
        assessment=assessment,
    ).require_valid()

    ref = record.to_dict()["query_shape_assessment_ref"]

    assert record.resolver_kind is ResolverKind.QUERY_SHAPE_SEEDED
    assert ref["assessment_id"] == "assessment:ssa-taxable-maximum"
    assert ref["trace_only"] is True
    assert ref["promoted_to_authority"] is False
    assert "accepted_contract_ref" not in record.to_dict()["contract_lineage"]


def test_search_work_plan_reference_remains_planning_only_not_semantic_owner() -> None:
    record = _record(
        search_ref=SearchWorkPlanRef(
            plan_id="search-work-plan:future",
            schema_version="search_work_plan_ag96c2_v1",
        )
    ).require_valid()
    invalid = _record(
        search_ref=SearchWorkPlanRef(
            plan_id="search-work-plan:bad-owner",
            schema_version="search_work_plan_ag96c2_v1",
            semantic_owner=True,
        )
    )

    ref = record.to_dict()["search_work_plan_ref"]

    assert ref["planning_only"] is True
    assert ref["semantic_owner"] is False
    assert any("planning-only" in error for error in invalid.validate().errors)


def test_no_coverage_sufficiency_author_or_final_answer_fields_are_created() -> None:
    payload = _record().require_valid().to_dict()
    keys = _collect_keys(payload)

    assert keys.isdisjoint(
        {
            "coverage",
            "coverage_state",
            "canonical_coverage",
            "sufficiency",
            "sufficiency_judgment",
            "final_answer",
            "final_answer_packet",
            "author_input",
            "semantic_observation",
        }
    )


def test_static_guards_keep_passive_module_off_runtime_product_and_live_surfaces() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.run_kernel",
        "core.llm",
        "core.author_execution_runtime",
        "core.final_answer_packet_runtime",
        "core.final_answer_packet",
        "core.retrieval_dispatch_runtime",
        "core.pipeline",
        "openai",
        "requests",
        "httpx",
        "urllib",
        "dotenv",
        "subprocess",
        "os",
    }
    forbidden_tokens = {
        "ask_model(",
        "search_web",
        "retrieve(",
        "fetch(",
        "execute_author",
        "authorize_",
        "run_pipeline",
        "render_citation",
        "format_citation",
    }
    imported_names: set[str] = set()
    called_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)

    assert imported_names.isdisjoint(forbidden_import_roots)
    assert called_names.isdisjoint({token.rstrip("(") for token in forbidden_tokens})
    for token in forbidden_tokens:
        assert token not in source


def _collect_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()
