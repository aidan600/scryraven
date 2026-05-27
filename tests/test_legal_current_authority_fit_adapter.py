from __future__ import annotations

import ast
import json
from pathlib import Path

from core.authoritative_source_obligations import (
    LEGAL_OR_REGULATORY_TEXT,
    OFFICIAL_CURRENT_RULES,
    AuthorityRequirementType,
    AuthorityStatus,
)
from core.legal_current_authority_fit import (
    LEGAL_CURRENT_AUTHORITY_FIT_SCHEMA_VERSION,
    LegalCurrentEvidenceFact,
    build_legal_current_primary_authority_fit,
)

_ROOT = Path(__file__).resolve().parents[1]
_ADAPTER_PATH = _ROOT / "core" / "legal_current_authority_fit.py"
_PROTECTED_RUNTIME_PATHS = (
    _ROOT / "core" / "pipeline_orchestrator.py",
    _ROOT / "core" / "pipeline.py",
    _ROOT / "core" / "prompts.py",
    _ROOT / "core" / "followup.py",
    _ROOT / "core" / "source_class_recovery_executor.py",
    _ROOT / "core" / "official_canonical_recovery_query_acquisition.py",
    _ROOT / "core" / "official_canonical_recovery_execution_admission.py",
    _ROOT / "core" / "official_source_obligation_bridge.py",
)


def _fit(*facts: LegalCurrentEvidenceFact | dict) -> object:
    return build_legal_current_primary_authority_fit(
        requirement_id="current-legal-authority",
        jurisdiction="California",
        current_anchor="2026-05-26",
        temporal_anchor="current compliance deadline",
        subject="current California compliance rule",
        evidence_facts=facts,
    )


def _status(result: object) -> AuthorityStatus:
    return result.state.satisfaction_for(result.requirement.requirement_id).status


def test_jurisdiction_anchor_is_represented_on_legal_current_primary_requirement() -> None:
    result = _fit()

    assert result.requirement.requirement_type is (
        AuthorityRequirementType.LEGAL_CURRENT_PRIMARY
    )
    assert result.requirement.jurisdiction == "California"
    assert result.to_projection()["requirement"]["jurisdiction"] == "California"


def test_currentness_and_temporal_anchors_are_represented() -> None:
    result = _fit()
    projection = result.to_projection()

    assert result.requirement.current_anchor == "2026-05-26"
    assert result.requirement.temporal_anchor == "current compliance deadline"
    assert projection["requirement"]["current_anchor"] == "2026-05-26"
    assert projection["requirement"]["temporal_anchor"] == (
        "current compliance deadline"
    )


def test_primary_legal_or_regulatory_source_satisfies_current_primary_authority() -> None:
    result = _fit(
        LegalCurrentEvidenceFact(
            evidence_id="ca-reg-text",
            source_class="statutory_or_regulatory_text",
            source_tier="official",
            jurisdiction="California",
            currentness_status="current",
            temporal_anchor="current compliance deadline",
        )
    )

    satisfaction = result.state.satisfaction_for(result.requirement.requirement_id)
    assert satisfaction.status is AuthorityStatus.FULFILLED
    assert satisfaction.satisfied_by_evidence_ids == ("ca-reg-text",)
    assert result.evidence_fits[0].observed_source_class == LEGAL_OR_REGULATORY_TEXT


def test_official_agency_guidance_fits_through_legal_specific_semantics() -> None:
    result = _fit(
        {
            "evidence_id": "agency-guidance",
            "source_class": "official_guidance_or_faq",
            "source_tier": "official",
            "jurisdiction": "California",
            "currentness_status": "effective",
        }
    )

    assert _status(result) is AuthorityStatus.FULFILLED
    assert result.evidence_fits[0].observed_source_class == OFFICIAL_CURRENT_RULES
    assert result.to_projection()["legal_evidence"][0]["legal_authority_kind"] == (
        "official_agency_guidance"
    )


def test_secondary_legal_explainer_is_context_allowed_not_authority_satisfying() -> None:
    result = _fit(
        LegalCurrentEvidenceFact(
            evidence_id="secondary-explainer",
            source_class="legal_explainer",
            source_tier="secondary",
            jurisdiction="California",
            currentness_status="current",
        )
    )

    assert _status(result) is AuthorityStatus.PARTIAL
    assert result.evidence_fits[0].context_allowed is True
    assert result.evidence_fits[0].satisfies_authority is False
    assert result.evidence_fits[0].mismatch_reason == "secondary_legal_context_only"


def test_stale_legal_source_does_not_satisfy_current_primary_authority() -> None:
    result = _fit(
        LegalCurrentEvidenceFact(
            evidence_id="superseded-reg",
            source_class="statutory_or_regulatory_text",
            source_tier="official",
            jurisdiction="California",
            currentness_status="superseded",
        )
    )

    assert _status(result) is AuthorityStatus.PARTIAL
    assert result.evidence_fits[0].satisfies_authority is False
    assert result.evidence_fits[0].mismatch_reason == (
        "temporal_currentness_anchor_not_satisfied"
    )


def test_out_of_jurisdiction_source_does_not_satisfy_bound_authority() -> None:
    result = _fit(
        LegalCurrentEvidenceFact(
            evidence_id="nv-reg-text",
            source_class="statutory_or_regulatory_text",
            source_tier="official",
            jurisdiction="Nevada",
            currentness_status="current",
        )
    )

    assert _status(result) is AuthorityStatus.PARTIAL
    assert result.evidence_fits[0].satisfies_authority is False
    assert result.evidence_fits[0].mismatch_reason == "jurisdiction_anchor_mismatch"


def test_missing_legal_current_primary_source_produces_unfulfilled_state() -> None:
    result = _fit()

    assert _status(result) is AuthorityStatus.UNFULFILLED
    assert result.evidence_fits[0].candidate_exists is False
    assert result.evidence_fits[0].insufficiency_reason == (
        "no_candidate_source_observed"
    )


def test_ordinary_non_legal_controls_do_not_trigger_legal_authority_satisfaction() -> None:
    result = _fit(
        LegalCurrentEvidenceFact(
            evidence_id="official-nonlegal-control",
            source_class="official_current_rules",
            source_tier="official",
            jurisdiction="California",
            currentness_status="current",
        )
    )

    assert _status(result) is AuthorityStatus.PARTIAL
    assert result.evidence_fits[0].satisfies_authority is False
    assert result.evidence_fits[0].mismatch_reason == (
        "generic_official_source_not_legal_current_primary"
    )


def test_lower_tier_laundering_is_blocked_for_legal_current_primary() -> None:
    result = _fit(
        LegalCurrentEvidenceFact(
            evidence_id="secondary-declared-legal",
            source_class="legal_or_regulatory_text",
            source_tier="secondary",
            jurisdiction="California",
            currentness_status="current",
        )
    )

    assert _status(result) is AuthorityStatus.PARTIAL
    assert result.evidence_fits[0].observed_source_class != LEGAL_OR_REGULATORY_TEXT
    assert result.evidence_fits[0].context_allowed is True
    assert result.evidence_fits[0].satisfies_authority is False


def test_trace_safe_projection_contains_no_raw_private_material() -> None:
    result = build_legal_current_primary_authority_fit(
        requirement_id="raw_prompt legal requirement",
        jurisdiction="California",
        current_anchor="2026-05-26",
        temporal_anchor="current status",
        evidence_facts=(
            {
                "evidence_id": "raw_provider cache secret evidence",
                "source_class": "official_guidance_or_faq",
                "source_tier": "official",
                "jurisdiction": "California",
                "currentness_status": "current",
                "raw_provider_payload": {"token": "secret", "legal_text": "full law"},
                "raw_prompt": "provider_payload full_trace private log",
                "text": "raw legal text should not appear",
            },
        ),
    )
    payload = json.dumps(result.to_projection(), sort_keys=True)

    assert result.to_projection()["schema_version"] == (
        LEGAL_CURRENT_AUTHORITY_FIT_SCHEMA_VERSION
    )
    assert result.to_projection()["trace_safe"] is True
    assert "[redacted protected material]" in payload
    for forbidden in (
        "raw_prompt",
        "raw_provider",
        "provider_payload",
        "full_trace",
        "private log",
        "raw legal text",
        "token",
    ):
        assert forbidden not in payload.casefold()


def test_recovery_plan_preserves_jurisdiction_and_currentness_anchors_when_unfulfilled() -> None:
    result = _fit(
        LegalCurrentEvidenceFact(
            evidence_id="secondary-explainer",
            source_class="secondary_legal_analysis",
            source_tier="secondary",
            jurisdiction="California",
            currentness_status="current",
        )
    )
    plan = result.state.recovery_plan()

    assert plan.missing_requirement_ids == ("current-legal-authority",)
    assert plan.target_authority_classes == (
        LEGAL_OR_REGULATORY_TEXT,
        OFFICIAL_CURRENT_RULES,
    )
    assert plan.jurisdiction_anchors == ("California",)
    assert plan.temporal_anchors == ("2026-05-26", "current compliance deadline")


def test_adapter_static_import_guard_keeps_runtime_surfaces_closed() -> None:
    tree = ast.parse(_ADAPTER_PATH.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imports.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    forbidden_imports = {
        "core.answer_contract_controller",
        "core.answer_contract_runtime_handoff",
        "core.db",
        "core.followup",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.provider",
        "core.providers",
        "core.routing",
        "core.run_logging",
        "core.search_providers",
        "core.source_class_recovery",
        "core.source_class_recovery_executor",
        "core.source_classifier",
        "openai",
        "requests",
    }
    assert imports.isdisjoint(forbidden_imports)


def test_static_guard_no_provider_retrieval_prompt_answer_or_actor_drift() -> None:
    adapter_source = _ADAPTER_PATH.read_text(encoding="utf-8").casefold()
    forbidden_markers = (
        "select_providers(",
        "choose_supplemental_search_depth(",
        "rank_sources(",
        "retrieve(",
        "search_providers",
        "provider_role",
        "author_prompt",
        "build_author_prompt(",
        "analyst_quant_packet",
        "economist_v1",
        "scrutineer_policy",
        "followup_prompt",
        "build_final_answer(",
        "pipeline_orchestrator",
    )
    for marker in forbidden_markers:
        assert marker not in adapter_source

    for path in _PROTECTED_RUNTIME_PATHS:
        source = path.read_text(encoding="utf-8")
        assert "legal_current_authority_fit" not in source
        assert "build_legal_current_primary_authority_fit" not in source
