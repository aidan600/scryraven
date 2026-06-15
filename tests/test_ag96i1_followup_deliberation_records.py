from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.followup_deliberation import (
    FollowupDecision,
    GapType,
    ProviderJobKind,
    ReasoningHopType,
    StopPosture,
    build_followup_deliberation_checkpoint,
)
from core.followup_deliberation_validation import (
    passive_module_static_guard,
    validate_followup_deliberation_checkpoint,
)

ROOT = Path(__file__).resolve().parents[1]


def _budget(**overrides: int) -> dict[str, int]:
    base = {
        "cost_points_remaining": 8,
        "provider_calls_remaining": 3,
        "fetches_remaining": 3,
        "read_units_remaining": 3,
        "followup_rounds_remaining": 2,
        "meso_authorizations_remaining": 3,
        "macro_hops_remaining": 0,
    }
    base.update(overrides)
    return base


def _component(component_id: str, *, served: bool = True) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "central": True,
        "served_minimum": served,
        "minimum_provider_calls": 1,
        "minimum_fetches": 1,
        "minimum_read_units": 1,
    }


def _gap(
    gap_type: str,
    *,
    gap_id: str = "gap.official",
    component_id: str = "component-rule",
    obligation_id: str = "obligation-official-current",
    requirement_id: str = "requirement-official-current",
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "gap_id": gap_id,
        "gap_type": gap_type,
        "component_id": component_id,
        "source_obligation_id": obligation_id,
        "requirement_ids": [requirement_id],
        "severity": "central_required",
        "evidence_indicators": ["required_obligation_unsatisfied"],
    }
    payload.update(overrides)
    return payload


def _checkpoint(**overrides: Any) -> Any:
    fixture = {
        "run_id": "ag96i1-fixture",
        "checkpoint_id": "after-first-pass",
        "mode": "balanced",
        "components": [_component("component-rule")],
        "budget_ledger": _budget(),
        "gaps": [_gap(GapType.OFFICIAL_CURRENT_GAP.value)],
        "sufficiency_handoff": {
            "satisfied_obligations": [],
            "missing_obligations": ["obligation-official-current"],
            "recommended_final_posture": "answer_with_caveats",
        },
    }
    fixture.update(overrides)
    return build_followup_deliberation_checkpoint(fixture)


def _records(checkpoint: Any) -> dict[str, Any]:
    return checkpoint.to_dict()["records"]


def test_balanced_one_hop_official_current_followup_recommendation_is_produced() -> None:
    checkpoint = _checkpoint()
    records = _records(checkpoint)

    assert records["gap_assessments"][0]["gap_type"] == "official_current_gap"
    assert records["gap_assessments"][0]["component_id"] == "component_rule"
    assert records["gap_assessments"][0]["source_obligation_id"] == (
        "obligation_official_current"
    )
    assert records["followup_recommendations"][0]["provider_job_kind"] == (
        "official_current_candidate_acquisition"
    )
    assert records["followup_authorization_candidates"][0]["decision"] == (
        "authorize_candidate"
    )
    assert records["followup_authorization_candidates"][0][
        "expected_evidence_ledger_custody_update"
    ]["custody_update_expected"]
    assert records["budget_decisions"][0]["decision"] == "authorize_candidate"
    assert validate_followup_deliberation_checkpoint(checkpoint).ok


def test_balanced_targeted_failure_stops_instead_of_repeated_retry() -> None:
    checkpoint = _checkpoint(
        prior_failed_followup_attempts=[
            {
                "gap_id": "gap.official",
                "source_obligation_id": "obligation-official-current",
            }
        ]
    )
    records = _records(checkpoint)

    assert records["followup_authorization_candidates"] == []
    assert records["budget_decisions"][0]["decision"] == "stop"
    assert records["stop_decisions"][0]["stop_reason"] == "repeated_failed_recovery"
    assert "do_not_treat_followup_candidate_as_executed_search" in (
        records["stop_decisions"][0]["prohibited_upgrades"]
    )


def test_balanced_does_not_starve_second_central_component() -> None:
    checkpoint = _checkpoint(
        components=[
            _component("component-rule", served=True),
            _component("component-second", served=False),
        ],
        budget_ledger=_budget(provider_calls_remaining=1, fetches_remaining=1, read_units_remaining=1),
    )
    budget_decision = _records(checkpoint)["budget_decisions"][0]

    assert budget_decision["decision"] == "insufficient_budget"
    assert budget_decision["starvation_check"]["passed"] is False
    assert budget_decision["starvation_check"]["protected_components"] == [
        "component_second"
    ]
    assert _records(checkpoint)["followup_authorization_candidates"] == []


def test_balanced_marks_needs_deep_for_conflict_currentness_reconciliation() -> None:
    checkpoint = _checkpoint(
        gaps=[
            _gap(
                GapType.CONFLICT_RECONCILIATION_GAP.value,
                gap_id="gap.conflict",
                obligation_id="obligation-currentness-conflict",
                requirement_id="requirement-currentness",
                evidence_indicators=["admitted_sources_conflict_on_currentness"],
            )
        ],
    )
    records = _records(checkpoint)

    assert records["reasoning_hops"][0]["hop_type"] == "macro_run_diagnosis"
    assert records["budget_decisions"][0]["decision"] == "needs_deep"
    assert records["followup_authorization_candidates"] == []
    assert records["stop_decisions"][0]["final_answer_posture"] == "needs_deep"


def test_fast_micro_verification_allowed_for_custody_and_final_answer_posture() -> None:
    checkpoint = _checkpoint(
        mode="fast",
        gaps=[
            _gap(
                GapType.CITATION_FINAL_ANSWER_POSTURE_GAP.value,
                gap_id="gap.citation",
                obligation_id="obligation-citation",
                requirement_id="requirement-citation",
                evidence_indicators=[
                    "bridge_only_provider_output_present",
                    "candidate_missing_answer_bearing_extract",
                ],
                bridge_only_provider_output_present=True,
            )
        ],
    )
    records = _records(checkpoint)

    assert records["reasoning_hops"][0]["hop_type"] == "micro_verification"
    assert records["reasoning_hops"][0]["may_request_followup"] is False
    assert records["followup_recommendations"][0]["decision"] == "caveat"
    assert "provider_job_kind" not in records["followup_recommendations"][0]
    assert "expected_custody_update" not in records["followup_recommendations"][0]
    assert records["followup_authorization_candidates"] == []
    assert validate_followup_deliberation_checkpoint(checkpoint).ok


def test_fast_official_current_gap_produces_no_followup_authorization_candidate() -> None:
    checkpoint = _checkpoint(mode="fast")
    records = _records(checkpoint)

    assert records["reasoning_hops"][0]["hop_type"] == "micro_verification"
    assert records["followup_recommendations"][0]["decision"] == "caveat"
    assert records["followup_recommendations"][0]["reason"] == (
        "fast_micro_validation_official_current_gap_no_followup_candidate"
    )
    assert records["followup_authorization_candidates"] == []
    assert records["budget_decisions"][0]["debit"]["budget_bucket"] == (
        "fast_micro_validation"
    )
    assert records["budget_decisions"][0]["debit"]["provider_calls"] == 0
    assert records["budget_decisions"][0]["debit"]["fetches_reserved"] == 0


def test_fast_citation_posture_gap_caveats_without_fetch_read_authorization() -> None:
    checkpoint = _checkpoint(
        mode="fast",
        gaps=[
            _gap(
                GapType.CITATION_FINAL_ANSWER_POSTURE_GAP.value,
                gap_id="gap.citation",
                obligation_id="obligation-citation",
                requirement_id="requirement-citation",
                evidence_indicators=["candidate_missing_answer_bearing_extract"],
            )
        ],
    )
    records = _records(checkpoint)

    recommendation = records["followup_recommendations"][0]
    assert recommendation["decision"] == "caveat"
    assert recommendation["hop_type"] == "micro_verification"
    assert "provider_job_kind" not in recommendation
    assert "query_intent" not in recommendation
    assert records["followup_authorization_candidates"] == []
    assert records["stop_decisions"][0]["final_answer_posture"] == "answer_with_caveats"


def test_fast_source_bound_numeric_unresolved_remains_unknown_without_quantwork() -> None:
    checkpoint = _checkpoint(
        mode="fast",
        gaps=[
            _gap(
                GapType.SOURCE_BOUND_NUMERIC_GAP.value,
                gap_id="gap.numeric",
                obligation_id="obligation-numeric",
                requirement_id="requirement-numeric",
                evidence_indicators=["source_bound_numeric_unresolved"],
            )
        ],
    )
    records = _records(checkpoint)

    assert records["reasoning_hops"][0]["hop_type"] == "micro_verification"
    assert records["followup_recommendations"][0]["decision"] == "stop"
    assert records["followup_authorization_candidates"] == []
    assert records["sufficiency_handoff"]["source_bound_numeric_unknowns"] == [
        "obligation_numeric"
    ]
    encoded = json.dumps(records, sort_keys=True)
    assert "source_bound_numeric_extraction_calculation_support" not in encoded
    assert "direct_candidate_search" not in encoded


def test_fast_conflict_or_contract_shape_gap_marks_selected_mode_insufficient() -> None:
    for gap_type in (
        GapType.CONFLICT_RECONCILIATION_GAP.value,
        GapType.CONTRACT_SHAPE_GAP.value,
    ):
        checkpoint = _checkpoint(
            mode="fast",
            gaps=[
                _gap(
                    gap_type,
                    gap_id=f"gap.{gap_type}",
                    obligation_id="obligation-contract",
                    requirement_id="requirement-contract",
                    evidence_indicators=["requires_reconciliation_or_contract_shape"],
                )
            ],
        )
        records = _records(checkpoint)

        assert records["reasoning_hops"][0]["hop_type"] == "micro_verification"
        assert records["budget_decisions"][0]["decision"] == (
            "selected_mode_insufficient"
        )
        assert records["stop_decisions"][0]["final_answer_posture"] == (
            "needs_balanced_or_deep"
        )
        assert records["followup_authorization_candidates"] == []
        assert validate_followup_deliberation_checkpoint(checkpoint).ok


def test_deep_may_produce_macro_diagnosis_and_reconciliation_support_candidate() -> None:
    checkpoint = _checkpoint(
        mode="deep",
        budget_ledger=_budget(macro_hops_remaining=1),
        gaps=[
            _gap(
                GapType.CONFLICT_RECONCILIATION_GAP.value,
                gap_id="gap.conflict",
                obligation_id="obligation-conflict",
                requirement_id="requirement-conflict",
                evidence_indicators=["admitted_sources_conflict"],
            )
        ],
    )
    records = _records(checkpoint)

    assert records["reasoning_hops"][0]["hop_type"] == "macro_run_diagnosis"
    assert records["followup_authorization_candidates"][0]["provider_job_kind"] == (
        "reconciliation_support"
    )
    assert records["budget_decisions"][0]["debit"]["macro_hops"] == 1
    assert records["deep_assumption_audit"]["mode"] == "deep"
    assert validate_followup_deliberation_checkpoint(checkpoint).ok


def test_deep_assumption_audit_records_fragility_and_change_conditions() -> None:
    checkpoint = _checkpoint(
        mode="deep",
        budget_ledger=_budget(macro_hops_remaining=1),
        deep_assumption_audit={
            "assumptions": [
                {
                    "assumption_id": "assumption.jurisdiction",
                    "statement": "The user means the federal rule.",
                    "support": "Fixture query names federal agency.",
                    "fragility": "medium",
                    "what_would_change_answer": "A state-specific jurisdiction.",
                }
            ],
            "sensitivity": [
                {"variable": "effective_date", "impact": "Answer changes by date."}
            ],
        },
    )
    audit = _records(checkpoint)["deep_assumption_audit"]

    assert audit["assumptions"][0]["fragility"] == "medium"
    assert audit["assumptions"][0]["what_would_change_answer"] == (
        "A state-specific jurisdiction."
    )
    assert audit["sensitivity"][0]["variable"] == "effective_date"


def test_provider_answer_deep_product_is_bridge_only_and_cannot_satisfy_final_evidence() -> None:
    checkpoint = _checkpoint(
        gaps=[
            _gap(
                GapType.CITATION_FINAL_ANSWER_POSTURE_GAP.value,
                gap_id="gap.bridge",
                obligation_id="obligation-bridge",
                requirement_id="requirement-bridge",
                bridge_only_provider_output_present=True,
                evidence_indicators=["provider_answer_context_only"],
            )
        ],
        sufficiency_handoff={
            "missing_obligations": ["obligation-bridge"],
            "bridge_only_provider_outputs_satisfy_final_evidence": False,
        },
    )
    records = _records(checkpoint)

    assert records["followup_recommendations"][0]["bridge_only_provider_output"] is True
    assert records["followup_authorization_candidates"][0]["bridge_only_provider_output"] is True
    assert records["sufficiency_handoff"][
        "bridge_only_provider_outputs_satisfy_final_evidence"
    ] is False
    assert validate_followup_deliberation_checkpoint(checkpoint).ok


def test_repeated_followup_cannot_loop_indefinitely() -> None:
    checkpoint = _checkpoint(
        prior_failed_followup_attempts=[
            {
                "gap_id": "gap.official",
                "source_obligation_id": "obligation-official-current",
            },
            {
                "gap_id": "gap.official",
                "source_obligation_id": "obligation-official-current",
            },
        ]
    )

    assert len(_records(checkpoint)["stop_decisions"]) == 1
    assert _records(checkpoint)["followup_authorization_candidates"] == []


def test_source_bound_numeric_unresolved_remains_unknown() -> None:
    checkpoint = _checkpoint(
        gaps=[
            _gap(
                GapType.SOURCE_BOUND_NUMERIC_GAP.value,
                gap_id="gap.numeric",
                obligation_id="obligation-numeric",
                requirement_id="requirement-numeric",
                evidence_indicators=["source_bound_numeric_unresolved"],
            )
        ],
    )
    records = _records(checkpoint)

    assert records["followup_authorization_candidates"] == []
    assert records["stop_decisions"][0]["stop_reason"] == (
        "source_bound_numeric_unresolved_remains_unknown"
    )
    assert records["sufficiency_handoff"]["source_bound_numeric_unknowns"] == [
        "obligation_numeric"
    ]


def test_resolved_quantwork_only_satisfies_numeric_not_unrelated_official_current() -> None:
    checkpoint = _checkpoint(
        gaps=[
            _gap(
                GapType.SOURCE_BOUND_NUMERIC_GAP.value,
                gap_id="gap.numeric",
                obligation_id="obligation-numeric",
                requirement_id="requirement-numeric",
                evidence_indicators=["source_bound_numeric_resolved"],
            ),
            _gap(
                GapType.OFFICIAL_CURRENT_GAP.value,
                gap_id="gap.official-missing",
                obligation_id="obligation-official-current",
                requirement_id="requirement-official-current",
            ),
        ],
        sufficiency_handoff={
            "satisfied_obligations": ["obligation-numeric"],
            "missing_obligations": ["obligation-official-current"],
        },
    )
    handoff = _records(checkpoint)["sufficiency_handoff"]

    assert handoff["source_bound_numeric_resolutions"] == ["obligation_numeric"]
    assert "obligation_official_current" in handoff["missing_obligations"]
    assert "obligation_official_current" not in handoff["satisfied_obligations"]


def test_citation_posture_gap_recommends_fetch_read_repair_if_budget_allows() -> None:
    checkpoint = _checkpoint(
        gaps=[
            _gap(
                GapType.CITATION_FINAL_ANSWER_POSTURE_GAP.value,
                gap_id="gap.citation",
                obligation_id="obligation-citation",
                requirement_id="requirement-citation",
                evidence_indicators=["candidate_missing_answer_bearing_extract"],
            )
        ]
    )
    records = _records(checkpoint)

    assert records["followup_recommendations"][0]["provider_job_kind"] == (
        "fetch_read_extract"
    )
    assert records["followup_authorization_candidates"][0]["budget_debit"][
        "fetches_reserved"
    ] == 1


def test_citation_posture_gap_blocks_when_fetch_read_budget_exhausted() -> None:
    checkpoint = _checkpoint(
        budget_ledger=_budget(fetches_remaining=0),
        gaps=[
            _gap(
                GapType.CITATION_FINAL_ANSWER_POSTURE_GAP.value,
                gap_id="gap.citation",
                obligation_id="obligation-citation",
                requirement_id="requirement-citation",
            )
        ],
    )

    assert _records(checkpoint)["budget_decisions"][0]["decision"] == (
        "insufficient_budget"
    )
    assert _records(checkpoint)["followup_authorization_candidates"] == []


def test_budget_exhaustion_is_multidimensional() -> None:
    cases = (
        {"cost_points_remaining": 0},
        {"provider_calls_remaining": 0},
        {"fetches_remaining": 0},
        {"read_units_remaining": 0},
        {"followup_rounds_remaining": 0},
        {"meso_authorizations_remaining": 0},
    )
    for case in cases:
        checkpoint = _checkpoint(budget_ledger=_budget(**case))
        assert _records(checkpoint)["budget_decisions"][0]["decision"] == (
            "insufficient_budget"
        )

    deep = _checkpoint(
        mode="deep",
        budget_ledger=_budget(macro_hops_remaining=0),
        gaps=[
            _gap(
                GapType.CONFLICT_RECONCILIATION_GAP.value,
                gap_id="gap.conflict",
                obligation_id="obligation-conflict",
                requirement_id="requirement-conflict",
            )
        ],
    )
    assert _records(deep)["budget_decisions"][0]["decision"] == "insufficient_budget"


def test_records_redact_sensitive_private_material() -> None:
    checkpoint = _checkpoint(
        input_state_refs={
            "raw_prompt": "RAW_PROMPT_SENTINEL",
            "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
            "raw_model_response": "RAW_MODEL_SENTINEL",
            "raw_text": "RAW_TEXT_SENTINEL",
            "full_text": "FULL_TEXT_SENTINEL",
            "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
            "token": "TOKEN_SENTINEL",
            "db_row": "DB_ROW_SENTINEL",
            "full_trace": "FULL_TRACE_SENTINEL",
        }
    )
    encoded = json.dumps(checkpoint.to_dict(), sort_keys=True)

    for sentinel in (
        "RAW_PROMPT_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "RAW_MODEL_SENTINEL",
        "RAW_TEXT_SENTINEL",
        "FULL_TEXT_SENTINEL",
        "SECRET_SENTINEL",
        "TOKEN_SENTINEL",
        "DB_ROW_SENTINEL",
        "FULL_TRACE_SENTINEL",
    ):
        assert sentinel not in encoded


def test_validation_rejects_forbidden_capability_claims_and_bridge_final_satisfaction() -> None:
    checkpoint = _checkpoint()
    payload = checkpoint.to_dict()
    payload["capabilities"]["may_directly_browse"] = True
    payload["records"]["sufficiency_handoff"][
        "bridge_only_provider_outputs_satisfy_final_evidence"
    ] = True

    result = validate_followup_deliberation_checkpoint(payload)

    assert not result.ok
    assert any("may_directly_browse" in error for error in result.errors)
    assert any("bridge-only provider output" in error for error in result.errors)


def test_validation_rejects_fast_meso_macro_and_reconciliation_candidates() -> None:
    checkpoint = _checkpoint(mode="fast")
    payload = checkpoint.to_dict()
    payload["records"]["followup_authorization_candidates"] = [
        {
            "authorization_id": "auth.fast.bad.meso",
            "recommendation_id": "rec.001",
            "decision": "authorize_candidate",
            "mode": "fast",
            "hop_type": "meso_targeted_repair",
            "provider_job_kind": "official_current_candidate_acquisition",
            "component_id": "component-rule",
            "source_obligation_id": "obligation-official-current",
            "requirement_ids": ["requirement-official-current"],
            "budget_debit": {},
            "expected_evidence_ledger_custody_update": {"custody_update_expected": []},
            "fallback_stop_posture": "answer_with_caveats",
            "fallback_caveat_refuse_posture": "insufficient_evidence",
        },
        {
            "authorization_id": "auth.fast.bad.macro",
            "recommendation_id": "rec.002",
            "decision": "authorize_candidate",
            "mode": "fast",
            "hop_type": "macro_run_diagnosis",
            "provider_job_kind": "reconciliation_support",
            "component_id": "component-rule",
            "source_obligation_id": "obligation-conflict",
            "requirement_ids": ["requirement-conflict"],
            "budget_debit": {},
            "expected_evidence_ledger_custody_update": {"custody_update_expected": []},
            "fallback_stop_posture": "needs_balanced_or_deep",
            "fallback_caveat_refuse_posture": "insufficient_evidence",
        },
    ]

    result = validate_followup_deliberation_checkpoint(payload)

    assert not result.ok
    assert any("Fast may not contain authorization candidates" in e for e in result.errors)
    assert any("Fast cannot authorize meso_targeted_repair" in e for e in result.errors)
    assert any("Fast cannot authorize macro_run_diagnosis" in e for e in result.errors)
    assert any("Fast cannot authorize reconciliation_support" in e for e in result.errors)


def test_validation_rejects_fast_execution_shaped_recommendation() -> None:
    checkpoint = _checkpoint(mode="fast")
    payload = checkpoint.to_dict()
    recommendation = payload["records"]["followup_recommendations"][0]
    recommendation["decision"] = "recommend"
    recommendation["hop_type"] = "meso_targeted_repair"
    recommendation["provider_job_kind"] = "official_current_candidate_acquisition"
    recommendation["expected_custody_update"] = {"custody_update_expected": []}

    result = validate_followup_deliberation_checkpoint(payload)

    assert not result.ok
    assert any("Fast may only record micro_verification" in e for e in result.errors)
    assert any("Fast may not recommend follow-up execution" in e for e in result.errors)
    assert any("Fast may not name provider_job_kind" in e for e in result.errors)
    assert any("Fast may not define follow-up custody update" in e for e in result.errors)


def test_static_guards_keep_new_modules_passive_and_closed_surfaces_untouched() -> None:
    module_paths = [
        ROOT / "core" / "followup_deliberation.py",
        ROOT / "core" / "followup_deliberation_validation.py",
    ]
    forbidden_imports = {
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.pipeline_orchestrator",
        "subprocess",
        "os",
    }

    for path in module_paths:
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()
        assert _imports(path).isdisjoint(forbidden_imports)
        for token in ("ask_model", "eval(", "exec(", "format_citation"):
            assert token not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "followup_deliberation" not in pipeline_source
    assert "FollowupDeliberationCheckpoint" not in pipeline_source


def test_taxonomy_contains_all_ag96i1_canonical_values() -> None:
    assert {gap.value for gap in GapType} >= {
        "component_coverage_gap",
        "source_class_gap",
        "official_current_gap",
        "legal_current_primary_gap",
        "canonical_doc_gap",
        "source_bound_numeric_gap",
        "currentness_gap",
        "conflict_reconciliation_gap",
        "entity_ambiguity_gap",
        "weak_corpus_gap",
        "citation_final_answer_posture_gap",
        "contract_shape_gap",
    }
    assert {hop.value for hop in ReasoningHopType} == {
        "micro_verification",
        "meso_targeted_repair",
        "macro_run_diagnosis",
    }
    assert {decision.value for decision in FollowupDecision} >= {
        "authorize_candidate",
        "recommend",
        "deny",
        "stop",
        "caveat",
        "refuse",
        "needs_deep",
        "selected_mode_insufficient",
        "insufficient_budget",
        "decorative_search_blocked",
    }
    assert ProviderJobKind.PROVIDER_ANSWER_CONTEXT.value == "provider_answer_context"
    assert StopPosture.NEEDS_BALANCED_OR_DEEP.value == "needs_balanced_or_deep"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
