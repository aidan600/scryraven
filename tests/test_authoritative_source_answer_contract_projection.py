from __future__ import annotations

import ast
import json
from dataclasses import fields
from pathlib import Path
from typing import Any

from core.answer_contract_controller import (
    AnswerContract,
    AnswerContractFamily,
    AnswerContractFulfillment,
    EvidenceStateSummary,
    build_answer_contract,
    build_answer_contract_fulfillment,
    build_answer_controller_state,
)
from core.authoritative_source_answer_contract_projection import (
    compare_authoritative_projection_to_answer_contract_handoff,
    project_authoritative_source_state_to_answer_contract_fields,
)
from core.authoritative_source_obligations import (
    ACADEMIC_LITERATURE,
    LEGAL_OR_REGULATORY_TEXT,
    OFFICIAL_CURRENT_RULES,
    PRIMARY_SOURCE_DOCUMENTS,
    REPUTABLE_SECONDARY,
    SECONDARY,
    SOURCED_NUMERIC_VALUES,
    AuthoritativeSourceObligationState,
    AuthorityComposition,
    AuthorityEvidenceFit,
    AuthorityRequirement,
)

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _ROOT / "core" / "authoritative_source_answer_contract_projection.py"
_PROTECTED_RUNTIME_PATHS = (
    _ROOT / "core" / "pipeline_orchestrator.py",
    _ROOT / "core" / "pipeline.py",
    _ROOT / "core" / "prompts.py",
    _ROOT / "core" / "followup.py",
    _ROOT / "core" / "source_class_recovery_executor.py",
)


def _state(
    requirement: AuthorityRequirement,
    *fits: AuthorityEvidenceFit,
) -> AuthoritativeSourceObligationState:
    return AuthoritativeSourceObligationState.evaluate([requirement], fits)


def _current_official_contract() -> AnswerContract:
    return build_answer_contract(
        family=AnswerContractFamily.CURRENT_OFFICIAL_RULES,
        user_intent_interpretation="User asks for current official rules.",
        answer_goal="Answer current official rules",
    )


def _handoff(
    contract: AnswerContract,
    *,
    evidence_sufficient: bool,
    source_classes_present: tuple[str, ...] = (),
    source_classes_missing: tuple[str, ...] = (),
    fulfilled_obligations: tuple[str, ...] = (),
    partial_obligations: tuple[str, ...] = (),
) -> AnswerContractFulfillment:
    evidence = EvidenceStateSummary(
        evidence_available=True,
        evidence_sufficient=evidence_sufficient,
        source_classes_present=source_classes_present,
        source_classes_missing=source_classes_missing,
        fulfilled_obligations=fulfilled_obligations,
        partial_obligations=partial_obligations,
    )
    return build_answer_contract_fulfillment(
        build_answer_controller_state(contract, evidence_state_summary=evidence)
    )


def test_official_current_fulfilled_projection_parity() -> None:
    requirement = AuthorityRequirement.official_current("official-rule")
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "official-rule", "agency-rule", OFFICIAL_CURRENT_RULES
        ),
    )
    handoff = _handoff(
        _current_official_contract(),
        evidence_sufficient=True,
        source_classes_present=(OFFICIAL_CURRENT_RULES,),
        fulfilled_obligations=("identify the current official rule or policy",),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(state)

    assert projection.source_obligation_status == handoff.source_obligation_status
    assert projection.unfulfilled_source_classes == handoff.unfulfilled_source_classes
    assert projection.partial_source_classes == handoff.partial_source_classes
    assert compare_authoritative_projection_to_answer_contract_handoff(
        projection, handoff
    )["matches"]


def test_official_current_missing_projection_parity() -> None:
    requirement = AuthorityRequirement.official_current("official-rule")
    state = _state(requirement)
    handoff = _handoff(
        _current_official_contract(),
        evidence_sufficient=False,
        source_classes_missing=(OFFICIAL_CURRENT_RULES,),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(state)

    assert projection.source_obligation_status == "unfulfilled"
    assert projection.unfulfilled_source_classes == (OFFICIAL_CURRENT_RULES,)
    assert projection.partial_source_classes == ()
    assert projection.warnings_to_Analyst_or_Author == (
        "official/current legal evidence missing or secondary-only",
    )
    assert compare_authoritative_projection_to_answer_contract_handoff(
        projection, handoff
    )["matches"]


def test_canonical_project_doc_fulfilled_projection_parity() -> None:
    requirement = AuthorityRequirement.canonical_project_doc("project-doc")
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "project-doc", "docs", PRIMARY_SOURCE_DOCUMENTS
        ),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(state)

    assert projection.source_obligation_status == "fulfilled"
    assert projection.fulfilled_source_classes == (PRIMARY_SOURCE_DOCUMENTS,)
    assert projection.unfulfilled_source_classes == ()
    assert projection.source_class_satisfaction_status == {
        PRIMARY_SOURCE_DOCUMENTS: "satisfied_strong"
    }


def test_academic_literature_requirement_projection_parity() -> None:
    requirement = AuthorityRequirement.academic_literature("academic-review")
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "academic-review", "paper", ACADEMIC_LITERATURE
        ),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(state)

    assert projection.source_obligation_status == "fulfilled"
    assert projection.fulfilled_source_classes == (ACADEMIC_LITERATURE,)
    assert projection.unfulfilled_source_classes == ()


def test_legal_current_primary_representation_projects_without_behavior_change() -> None:
    requirement = AuthorityRequirement.legal_current_primary(
        "current-legal-text",
        jurisdiction="California",
        current_anchor="2026-05-26",
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "current-legal-text",
            "statute",
            LEGAL_OR_REGULATORY_TEXT,
        ),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(state)
    payload = projection.to_dict()

    assert projection.source_obligation_status == "fulfilled"
    assert projection.fulfilled_source_classes == (LEGAL_OR_REGULATORY_TEXT,)
    assert "provider_role" not in json.dumps(payload)
    assert "search_depth" not in json.dumps(payload)


def test_source_bound_numeric_representation_projects_without_economist_behavior() -> None:
    requirement = AuthorityRequirement.source_bound_numeric(
        "alpha-beta-revenue",
        source_binding_id="alpha-beta-fy2025-revenue",
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "alpha-beta-revenue",
            "alpha-beta-fy2025-revenue",
            SOURCED_NUMERIC_VALUES,
        ),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(state)
    payload = json.dumps(projection.to_dict(), sort_keys=True)

    assert projection.source_obligation_status == "fulfilled"
    assert projection.fulfilled_source_classes == (SOURCED_NUMERIC_VALUES,)
    assert "economist" not in payload.casefold()
    assert "source_bound_values" not in payload.casefold()


def test_multiple_simultaneous_requirements_project_stable_classes() -> None:
    official = AuthorityRequirement.official_current("official-rule")
    canonical = AuthorityRequirement.canonical_project_doc("project-doc")
    academic = AuthorityRequirement.academic_literature("academic-review")
    requirement = AuthorityRequirement.compose(
        "multi-authority",
        AuthorityComposition.ALL,
        (official, canonical, academic),
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "official-rule", "agency-rule", OFFICIAL_CURRENT_RULES
        ),
        AuthorityEvidenceFit.lower_tier_context(
            "project-doc", "secondary-docs", SECONDARY
        ),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(state)

    assert projection.source_obligation_status == "partial"
    assert projection.fulfilled_source_classes == (OFFICIAL_CURRENT_RULES,)
    assert projection.partial_source_classes == (PRIMARY_SOURCE_DOCUMENTS,)
    assert projection.unfulfilled_source_classes == (
        PRIMARY_SOURCE_DOCUMENTS,
        ACADEMIC_LITERATURE,
    )


def test_all_composition_projects_partial_for_lower_tier_child() -> None:
    official = AuthorityRequirement.official_current("official-rule")
    canonical = AuthorityRequirement.canonical_project_doc("project-doc")
    requirement = AuthorityRequirement.compose(
        "official-and-canonical",
        AuthorityComposition.ALL,
        (official, canonical),
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "project-doc", "docs", PRIMARY_SOURCE_DOCUMENTS
        ),
        AuthorityEvidenceFit.lower_tier_context(
            "official-rule", "secondary-explainer", REPUTABLE_SECONDARY
        ),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(state)

    assert projection.source_obligation_status == "partial"
    assert projection.partial_source_classes == (OFFICIAL_CURRENT_RULES,)
    assert projection.unfulfilled_source_classes == (OFFICIAL_CURRENT_RULES,)
    assert projection.source_class_satisfaction_status[OFFICIAL_CURRENT_RULES] == (
        "expected_but_only_secondary"
    )


def test_any_and_one_of_compositions_project_fulfilled_allowed_path() -> None:
    legal = AuthorityRequirement.legal_current_primary("legal-text")
    official = AuthorityRequirement.official_current("official-rule")
    any_requirement = AuthorityRequirement.compose(
        "legal-or-official",
        AuthorityComposition.ANY,
        (legal, official),
    )
    one_of_requirement = AuthorityRequirement.compose(
        "one-authority-path",
        AuthorityComposition.ONE_OF,
        (legal, official),
    )

    for requirement in (any_requirement, one_of_requirement):
        state = _state(
            requirement,
            AuthorityEvidenceFit.authoritative(
                "official-rule", "agency-rule", OFFICIAL_CURRENT_RULES
            ),
        )
        projection = project_authoritative_source_state_to_answer_contract_fields(state)
        assert projection.source_obligation_status == "fulfilled"
        assert projection.unfulfilled_source_classes == ()
        assert projection.fulfilled_source_classes == (OFFICIAL_CURRENT_RULES,)


def test_fallback_ordered_projects_selected_missing_requirement_only() -> None:
    official = AuthorityRequirement.official_current("official-rule")
    canonical = AuthorityRequirement.canonical_project_doc("project-doc")
    requirement = AuthorityRequirement.compose(
        "fallback-authority",
        AuthorityComposition.FALLBACK_ORDERED,
        (official, canonical),
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.lower_tier_context(
            "official-rule", "secondary-rule-context", REPUTABLE_SECONDARY
        ),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(state)

    assert projection.source_obligation_status == "partial"
    assert projection.partial_source_classes == (OFFICIAL_CURRENT_RULES,)
    assert projection.unfulfilled_source_classes == (OFFICIAL_CURRENT_RULES,)
    assert projection.recovery_posture_summary["target_authority_classes"] == [
        OFFICIAL_CURRENT_RULES
    ]
    assert "query" not in json.dumps(projection.to_dict()).casefold()


def test_existing_unfulfilled_partial_and_warning_fields_are_preserved() -> None:
    requirement = AuthorityRequirement.official_current("official-rule")
    state = _state(requirement)
    existing = AnswerContractFulfillment(
        fulfilled_items=(),
        partial_items=(),
        unfulfilled_items=(),
        source_obligation_status="partial",
        unfulfilled_source_classes=("current_primary_or_official",),
        partial_source_classes=("current_primary_or_official",),
        warnings_to_Analyst_or_Author=("existing downstream warning",),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(
        state,
        existing_handoff=existing,
    )

    assert projection.unfulfilled_source_classes == (
        "current_primary_or_official",
        OFFICIAL_CURRENT_RULES,
    )
    assert projection.partial_source_classes == ("current_primary_or_official",)
    assert projection.warnings_to_Analyst_or_Author[0] == "existing downstream warning"


def test_lower_tier_evidence_stays_partial_and_does_not_satisfy_stronger_class() -> None:
    requirement = AuthorityRequirement.official_current("official-rule")
    state = _state(
        requirement,
        AuthorityEvidenceFit.lower_tier_context(
            "official-rule", "secondary-explainer", REPUTABLE_SECONDARY
        ),
    )

    projection = project_authoritative_source_state_to_answer_contract_fields(state)

    assert projection.source_obligation_status == "partial"
    assert projection.fulfilled_source_classes == ()
    assert projection.partial_source_classes == (OFFICIAL_CURRENT_RULES,)
    assert projection.source_class_satisfaction_status[OFFICIAL_CURRENT_RULES] == (
        "expected_but_only_secondary"
    )


def test_projection_contains_only_trace_safe_primitive_structured_summaries() -> None:
    requirement = AuthorityRequirement.official_current(
        "raw_prompt official requirement",
        subject="provider_payload private log full_trace",
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.lower_tier_context(
            "raw_prompt official requirement",
            "raw_provider cache secret evidence",
            REPUTABLE_SECONDARY,
        ),
    )

    payload = project_authoritative_source_state_to_answer_contract_fields(
        state
    ).to_dict()
    serialized = json.dumps(payload, sort_keys=True)

    assert payload["trace_safe"] is True
    assert "[redacted protected material]" in serialized
    for marker in (
        "raw_prompt",
        "provider_payload",
        "full_trace",
        "private log",
        "raw_provider",
        "cache secret",
    ):
        assert marker not in serialized.casefold()


def test_public_answer_contract_dataclass_api_shape_remains_stable() -> None:
    assert [field.name for field in fields(AnswerContract)] == [
        "family",
        "user_intent_interpretation",
        "answer_goal",
        "must_satisfy",
        "should_satisfy",
        "optional_checks",
        "evidence_classes_needed",
        "social_signal_relevance",
        "scrutineer_relevance",
        "stop_conditions",
        "answer_posture_if_fulfilled",
        "answer_posture_if_partial",
        "schema_version",
    ]
    assert [field.name for field in fields(AnswerContractFulfillment)] == [
        "fulfilled_items",
        "partial_items",
        "unfulfilled_items",
        "evidence_used",
        "actions_taken",
        "actions_skipped_and_why",
        "contract_revisions",
        "stop_reason",
        "final_answer_posture",
        "source_obligation_status",
        "unfulfilled_source_classes",
        "partial_source_classes",
        "warnings_to_Analyst_or_Author",
        "social_signal_summary",
        "evidence_integration_checkpoint",
        "schema_version",
    ]


def test_projection_helper_static_import_guard_keeps_runtime_surfaces_closed() -> None:
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.pipeline",
        "core.prompts",
        "core.followup",
        "core.source_class_recovery_executor",
        "core.source_classifier",
        "core.search_providers",
        "core.db",
        "openai",
        "requests",
    }

    assert imported.isdisjoint(forbidden_imports)


def test_static_guard_no_ag65b_runtime_wiring_into_protected_paths() -> None:
    forbidden_markers = (
        "authoritative_source_answer_contract_projection",
        "project_authoritative_source_state_to_answer_contract_fields",
        "AnswerContractAuthorityProjection",
    )

    for path in _PROTECTED_RUNTIME_PATHS:
        source = path.read_text(encoding="utf-8")
        assert all(marker not in source for marker in forbidden_markers)


def test_projection_payload_is_json_primitive_compatible() -> None:
    requirement = AuthorityRequirement.source_bound_numeric("source-bound")
    state = _state(requirement)
    payload = project_authoritative_source_state_to_answer_contract_fields(
        state
    ).to_dict()

    def assert_primitive(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                assert isinstance(key, str)
                assert_primitive(child)
        elif isinstance(value, list):
            for child in value:
                assert_primitive(child)
        else:
            assert value is None or isinstance(value, (str, bool, int, float))

    assert_primitive(payload)
    json.dumps(payload, sort_keys=True)
