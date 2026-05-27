from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.authoritative_source_obligations import (
    ACADEMIC_LITERATURE,
    LEGAL_OR_REGULATORY_TEXT,
    OFFICIAL_CURRENT_RULES,
    PRIMARY_SOURCE_DOCUMENTS,
    REPUTABLE_SECONDARY,
    SECONDARY,
    SOCIAL_OR_FORUM,
    SOURCED_NUMERIC_VALUES,
    TRUSTED_COMMUNITY,
    AuthoritativeSourceObligationState,
    AuthorityComposition,
    AuthorityEvidenceFit,
    AuthorityRecoveryPlan,
    AuthorityRequirement,
    AuthorityRequirementType,
    AuthorityStatus,
)

_ROOT = Path(__file__).resolve().parents[1]
_KERNEL_PATH = _ROOT / "core" / "authoritative_source_obligations.py"


def _state(
    requirement: AuthorityRequirement,
    *fits: AuthorityEvidenceFit,
) -> AuthoritativeSourceObligationState:
    return AuthoritativeSourceObligationState.evaluate([requirement], fits)


def test_official_current_requirement_represents_current_anchors_and_satisfies() -> None:
    requirement = AuthorityRequirement.official_current(
        "irs-mileage-rate",
        current_anchor="2026-05-26",
        temporal_anchor="tax year 2026",
        subject="IRS standard mileage rate",
        fallback_posture="caveat_if_missing_current_official_source",
    )

    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "irs-mileage-rate",
            "irs-notice",
            OFFICIAL_CURRENT_RULES,
            observed_source_tier="official",
        ),
    )

    assert requirement.requirement_type is AuthorityRequirementType.OFFICIAL_CURRENT
    assert requirement.required_authority_classes == (OFFICIAL_CURRENT_RULES,)
    assert requirement.current_anchor == "2026-05-26"
    assert requirement.temporal_anchor == "tax year 2026"
    assert state.satisfaction_for("irs-mileage-rate").status is AuthorityStatus.FULFILLED


def test_canonical_academic_legal_and_source_bound_numeric_representations() -> None:
    canonical = AuthorityRequirement.canonical_project_doc(
        "postgres-docs", subject="PostgreSQL MVCC"
    )
    academic = AuthorityRequirement.academic_literature(
        "sqlite-literature", subject="SQLite WAL benchmarks"
    )
    legal = AuthorityRequirement.legal_current_primary(
        "ca-privacy-deadline",
        jurisdiction="California",
        current_anchor="2026-05-26",
        temporal_anchor="current compliance deadline",
        subject="privacy law deadline",
    )
    numeric = AuthorityRequirement.source_bound_numeric(
        "revenue-comparison",
        source_binding_id="alpha-beta-fy2025-revenue",
        subject="fiscal 2025 revenue comparison",
    )

    assert canonical.required_authority_classes == (PRIMARY_SOURCE_DOCUMENTS,)
    assert academic.required_authority_classes == (ACADEMIC_LITERATURE,)
    assert legal.required_authority_classes == (
        LEGAL_OR_REGULATORY_TEXT,
        OFFICIAL_CURRENT_RULES,
    )
    assert legal.jurisdiction == "California"
    assert numeric.required_authority_classes == (SOURCED_NUMERIC_VALUES,)
    assert numeric.source_binding_id == "alpha-beta-fy2025-revenue"


def test_lower_tier_only_evidence_can_fulfill_context_requirement() -> None:
    requirement = AuthorityRequirement.lower_tier_context(
        "background-context",
        allowed_context_classes=(REPUTABLE_SECONDARY, TRUSTED_COMMUNITY),
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.lower_tier_context(
            "background-context", "secondary-background", REPUTABLE_SECONDARY
        ),
    )

    satisfaction = state.satisfaction_for("background-context")
    assert satisfaction.status is AuthorityStatus.FULFILLED
    assert satisfaction.satisfied_by_evidence_ids == ("secondary-background",)
    assert satisfaction.authority_satisfying_count == 0


def test_multiple_simultaneous_requirements_can_represent_canonical_plus_academic() -> None:
    canonical = AuthorityRequirement.canonical_project_doc("postgres-docs")
    academic = AuthorityRequirement.academic_literature("postgres-studies")
    requirement = AuthorityRequirement.compose(
        "docs-and-studies",
        AuthorityComposition.ALL,
        (canonical, academic),
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "postgres-docs", "postgres-doc", PRIMARY_SOURCE_DOCUMENTS
        ),
        AuthorityEvidenceFit.authoritative(
            "postgres-studies", "peer-reviewed-study", ACADEMIC_LITERATURE
        ),
    )

    assert state.satisfaction_for("postgres-docs").status is AuthorityStatus.FULFILLED
    assert state.satisfaction_for("postgres-studies").status is AuthorityStatus.FULFILLED
    assert state.satisfaction_for("docs-and-studies").status is AuthorityStatus.FULFILLED


def test_all_composition_is_partial_when_one_required_child_is_only_context() -> None:
    official = AuthorityRequirement.official_current("official-rule")
    canonical = AuthorityRequirement.canonical_project_doc("project-doc")
    requirement = AuthorityRequirement.compose(
        "official-and-canonical",
        AuthorityComposition.ALL,
        (official, canonical),
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.lower_tier_context(
            "official-rule", "secondary-explainer", SECONDARY
        ),
        AuthorityEvidenceFit.authoritative(
            "project-doc", "reference-doc", PRIMARY_SOURCE_DOCUMENTS
        ),
    )

    satisfaction = state.satisfaction_for("official-and-canonical")
    assert satisfaction.status is AuthorityStatus.PARTIAL
    assert satisfaction.child_statuses["official-rule"] is AuthorityStatus.PARTIAL
    assert satisfaction.child_statuses["project-doc"] is AuthorityStatus.FULFILLED


def test_any_composition_fulfills_when_any_child_is_authority_satisfied() -> None:
    legal = AuthorityRequirement.legal_current_primary("legal-text")
    official = AuthorityRequirement.official_current("official-rule")
    requirement = AuthorityRequirement.compose(
        "legal-or-official",
        AuthorityComposition.ANY,
        (legal, official),
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "official-rule", "agency-rule", OFFICIAL_CURRENT_RULES
        ),
    )

    satisfaction = state.satisfaction_for("legal-or-official")
    assert satisfaction.status is AuthorityStatus.FULFILLED
    assert satisfaction.selected_child_requirement_id == "official-rule"


def test_one_of_composition_records_selected_satisfying_child() -> None:
    legal = AuthorityRequirement.legal_current_primary("legal-text")
    official = AuthorityRequirement.official_current("official-rule")
    requirement = AuthorityRequirement.compose(
        "one-authority-path",
        AuthorityComposition.ONE_OF,
        (legal, official),
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "legal-text", "regulatory-text", LEGAL_OR_REGULATORY_TEXT
        ),
        AuthorityEvidenceFit.lower_tier_context(
            "official-rule", "secondary-rule-context", SECONDARY
        ),
    )

    satisfaction = state.satisfaction_for("one-authority-path")
    assert satisfaction.status is AuthorityStatus.FULFILLED
    assert satisfaction.selected_child_requirement_id == "legal-text"


def test_fallback_ordered_composition_targets_first_unsatisfied_fallback() -> None:
    official = AuthorityRequirement.official_current("official-rule")
    canonical = AuthorityRequirement.canonical_project_doc("canonical-doc")
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

    satisfaction = state.satisfaction_for("fallback-authority")
    recovery_plan = state.recovery_plan()
    assert satisfaction.status is AuthorityStatus.PARTIAL
    assert satisfaction.selected_child_requirement_id == "official-rule"
    assert recovery_plan.missing_requirement_ids == ("official-rule",)
    assert recovery_plan.target_authority_classes == (OFFICIAL_CURRENT_RULES,)


def test_fallback_ordered_composition_can_use_later_authoritative_fallback() -> None:
    official = AuthorityRequirement.official_current("official-rule")
    canonical = AuthorityRequirement.canonical_project_doc("canonical-doc")
    requirement = AuthorityRequirement.compose(
        "fallback-authority",
        AuthorityComposition.FALLBACK_ORDERED,
        (official, canonical),
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit.authoritative(
            "canonical-doc", "reference-doc", PRIMARY_SOURCE_DOCUMENTS
        ),
    )

    satisfaction = state.satisfaction_for("fallback-authority")
    assert satisfaction.status is AuthorityStatus.FULFILLED
    assert satisfaction.selected_child_requirement_id == "canonical-doc"
    assert state.recovery_plan().missing_requirement_ids == ()


def test_evidence_fit_distinguishes_source_existence_from_authority_satisfaction() -> None:
    requirement = AuthorityRequirement.official_current("official-rule")
    fit = AuthorityEvidenceFit(
        requirement_id="official-rule",
        evidence_id="secondary-explainer",
        candidate_exists=True,
        observed_source_class=REPUTABLE_SECONDARY,
        observed_source_tier="secondary",
        context_allowed=True,
        satisfies_authority=False,
        mismatch_reason="secondary_only",
    )
    state = _state(requirement, fit)

    satisfaction = state.satisfaction_for("official-rule")
    assert fit.candidate_exists is True
    assert fit.context_allowed is True
    assert fit.satisfies_authority is False
    assert satisfaction.status is AuthorityStatus.PARTIAL
    assert satisfaction.candidate_exists_count == 1
    assert satisfaction.authority_satisfying_count == 0
    assert "context_allowed_but_not_authority_satisfying" in satisfaction.mismatch_reasons


@pytest.mark.parametrize(
    ("requirement", "allowed_class"),
    [
        (AuthorityRequirement.official_current("official-current"), OFFICIAL_CURRENT_RULES),
        (
            AuthorityRequirement.legal_current_primary("legal-current"),
            LEGAL_OR_REGULATORY_TEXT,
        ),
        (
            AuthorityRequirement.canonical_project_doc("canonical-doc"),
            PRIMARY_SOURCE_DOCUMENTS,
        ),
        (
            AuthorityRequirement.academic_literature("academic-lit"),
            ACADEMIC_LITERATURE,
        ),
        (
            AuthorityRequirement.source_bound_numeric("source-bound"),
            SOURCED_NUMERIC_VALUES,
        ),
    ],
)
def test_lower_tier_evidence_does_not_launder_into_stronger_obligations(
    requirement: AuthorityRequirement,
    allowed_class: str,
) -> None:
    lower_tier = AuthorityEvidenceFit.lower_tier_context(
        requirement.requirement_id,
        "lower-tier-context",
        REPUTABLE_SECONDARY,
    )
    malicious_claim = AuthorityEvidenceFit(
        requirement_id=requirement.requirement_id,
        evidence_id="declared-authority-but-secondary",
        candidate_exists=True,
        observed_source_class=REPUTABLE_SECONDARY,
        observed_source_tier="secondary",
        context_allowed=True,
        satisfies_authority=True,
        mismatch_reason="declared_class_laundering_attempt",
    )
    state = _state(requirement, lower_tier, malicious_claim)
    satisfaction = state.satisfaction_for(requirement.requirement_id)

    assert allowed_class in requirement.required_authority_classes
    assert satisfaction.status is AuthorityStatus.PARTIAL
    assert satisfaction.authority_satisfying_count == 0
    assert "observed_source_class_not_allowed_for_requirement" in (
        satisfaction.mismatch_reasons
    )
    assert "context_allowed_but_not_authority_satisfying" in (
        satisfaction.mismatch_reasons
    )


def test_authority_recovery_plan_is_provider_agnostic_and_execution_free() -> None:
    legal = AuthorityRequirement.legal_current_primary(
        "legal-current",
        jurisdiction="California",
        current_anchor="2026-05-26",
        temporal_anchor="current deadline",
    )
    numeric = AuthorityRequirement.source_bound_numeric(
        "source-bound", source_binding_id="metric-source-binding"
    )
    state = AuthoritativeSourceObligationState.evaluate([legal, numeric], [])
    plan = AuthorityRecoveryPlan.from_state(state)
    payload = json.dumps(plan.to_projection(), sort_keys=True)

    assert plan.missing_requirement_ids == ("legal-current", "source-bound")
    assert plan.target_authority_classes == (
        LEGAL_OR_REGULATORY_TEXT,
        OFFICIAL_CURRENT_RULES,
        SOURCED_NUMERIC_VALUES,
    )
    assert plan.temporal_anchors == ("2026-05-26", "current deadline")
    assert plan.jurisdiction_anchors == ("California",)
    assert plan.provider_agnostic is True
    assert plan.execution_free is True
    for forbidden in (
        "provider_name",
        "provider_depth",
        "search_depth",
        "dispatch",
        "query",
        "retrieval",
        "ranking",
        "prompt",
    ):
        assert forbidden not in payload.casefold()


def test_trace_safe_projection_contains_no_raw_private_material() -> None:
    requirement = AuthorityRequirement.official_current(
        "raw_prompt official requirement",
        subject="provider_payload full_trace private log",
        current_anchor="2026-05-26",
    )
    state = _state(
        requirement,
        AuthorityEvidenceFit(
            requirement_id="raw_prompt official requirement",
            evidence_id="raw provider_payload cache secret text",
            candidate_exists=True,
            observed_source_class=SOCIAL_OR_FORUM,
            observed_source_tier=SOCIAL_OR_FORUM,
            context_allowed=True,
            satisfies_authority=False,
            mismatch_reason="private log mismatch",
        ),
    )
    projection = state.projection().to_dict()
    payload = json.dumps(projection, sort_keys=True)

    assert projection["trace_safe"] is True
    assert "[redacted protected material]" in payload
    for forbidden in (
        "raw_prompt",
        "provider_payload",
        "full_trace",
        "private log",
        "cache secret",
        "raw provider",
    ):
        assert forbidden not in payload.casefold()


def test_static_import_guard_for_pure_kernel_boundaries() -> None:
    tree = ast.parse(_KERNEL_PATH.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    forbidden_exact = {
        "logging",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.routing",
        "core.search_providers",
        "core.source_class_recovery",
        "core.source_class_recovery_executor",
        "core.followup",
        "app",
        "streamlit",
        "sqlite3",
    }
    forbidden_fragments = (
        "provider",
        "retrieval",
        "prompt",
        "storage",
        "database",
        "logging",
        "streamlit",
        "live",
        "orchestrator",
        "proplex",
    )

    assert forbidden_exact.isdisjoint(imports)
    assert all(
        not any(fragment in imported.casefold() for fragment in forbidden_fragments)
        for imported in imports
    )
