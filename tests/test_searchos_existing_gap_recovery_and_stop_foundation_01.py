from __future__ import annotations

import inspect
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

import pytest

import core.ordinary_multicomponent_synthesis_runtime as multicomponent_runtime
import core.pipeline_orchestrator as pipeline_orchestrator
import core.run_authority_sufficiency_adapter as sufficiency_adapter
import core.run_authority_sufficiency_validation as sufficiency_validation
from core.component_coverage_reduction_runtime import (
    ledger_qualification_blockers_for_satisfied_coverage,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_SCRUTINEER,
    ROLE_SYSTEM_PROMPTS,
)
from core.ordinary_semantic_producer_runtime import (
    source_requirement_ids_for_component_candidate,
)
from core.run_kernel import RunKernel
from core.searchos_existing_gap_recovery_runtime import (
    MAXIMUM_EXISTING_GAP_RECOVERY_CYCLES,
    SearchOSExistingGapRecoveryError,
    _digest,
    _envelope,
    _exact_recovery_coverage_chain,
    _refresh_state,
    admit_searchos_existing_gap_recovery_cycle,
    build_searchos_existing_gap_basis,
    build_searchos_materially_novel_recovery_purpose,
    finalize_searchos_existing_gap_recovery_cycle,
    validate_active_searchos_recovery_cycle_ref,
    validate_searchos_existing_gap_basis,
    validate_searchos_recovery_purpose,
)
from core.searchos_slice_a_product_runtime import (
    SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
    _coverage_ref_matches_contract_and_candidates,
    _coverage_ref_matches_slot,
)
from tests.helpers.offline_ordinary_pipeline import (
    PostRetirementOrdinaryPipelineHarness,
    run_post_retirement_ordinary_pipeline,
)


def _official_evidence_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha official operating rule",
            "url": "https://alpha.gov/operating-rule",
            "text": ("Alpha's current official operating rule sets an operating rate of 14 units per hour."),
            "credibility": 4,
            "source_tier": "official",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        }
    ]


def _initial_incomplete_evidence_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha official operating overview",
            "url": "https://alpha.gov/operating-overview",
            "text": (
                "Alpha publishes an official operating rule, but this overview "
                "omits the name of its current operating protocol."
            ),
            "credibility": 4,
            "source_tier": "official",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        }
    ]


def _recovered_official_evidence_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha official operating protocol",
            "url": "https://alpha.gov/operating-protocol",
            "text": (
                "Alpha's current official operating protocol is Raven."
            ),
            "credibility": 4,
            "source_tier": "official",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        }
    ]


def _recovered_numeric_evidence_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha official operating rate details",
            "url": "https://alpha.gov/operating-rate-details",
            "text": (
                "Alpha's current official operating rate is 14 units per hour."
            ),
            "credibility": 4,
            "source_tier": "official",
            "source_class": "sourced_numeric_values",
            "currentness_signal": "current",
            "evidence_material_type": "structured_numeric",
            "readable_status": "readable",
            "disposition": "accepted",
        }
    ]


def _initial_incomplete_canonical_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha canonical API documentation",
            "url": "https://docs.alpha.example/api",
            "text": (
                "Alpha's canonical API documentation lists the endpoint, "
                "but omits its current response name."
            ),
            "credibility": 4,
            "source_tier": "canonical",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        },
        {
            "title": "Alpha API overview",
            "url": "https://example.test/alpha-api-overview",
            "text": (
                "A secondary overview confirms that Alpha publishes an API, "
                "without stating the current canonical response name."
            ),
            "credibility": 3,
            "source_tier": "secondary",
            "source_class": "reputable_secondary",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        },
    ]


def _recovered_canonical_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha canonical Raven endpoint documentation",
            "url": "https://docs.alpha.example/api/raven",
            "text": (
                "Alpha's current canonical API response name is Raven."
            ),
            "credibility": 4,
            "source_tier": "canonical",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        }
    ]


def _capture_sufficiency_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> list[Any]:
    captured: list[Any] = []
    original = (
        sufficiency_adapter.build_sufficiency_judgment_input_from_runtime
    )

    def wrapped(**kwargs: Any) -> Any:
        judgment_input = original(**kwargs)
        captured.append(judgment_input)
        return judgment_input

    monkeypatch.setattr(
        sufficiency_adapter,
        "build_sufficiency_judgment_input_from_runtime",
        wrapped,
    )
    return captured


def _install_foreign_shared_obligation_at_sufficiency(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[Any], dict[str, str]]:
    captured: list[Any] = []
    ownership_refs: dict[str, str] = {}
    original = (
        sufficiency_adapter.build_sufficiency_judgment_input_from_runtime
    )

    def wrapped(**kwargs: Any) -> Any:
        judgment_input = original(**kwargs)
        terminal = dict(
            judgment_input.searchos_existing_gap_recovery_terminal_state
            or {}
        )
        if not terminal:
            captured.append(judgment_input)
            return judgment_input
        component_b_id = str(
            dict(terminal.get("component_ref") or {}).get(
                "component_id"
            )
            or ""
        )
        target_obligation_id = str(
            dict(terminal.get("source_obligation_ref") or {}).get(
                "source_obligation_id"
            )
            or ""
        )
        searchos_state = dict(judgment_input.searchos_state)
        required_slot_ids = set(
            searchos_state.get("required_slot_ids") or ()
        )
        component_b_obligation_ids = {
            str(
                dict(slot.get("slot_ref") or {}).get(
                    "source_obligation_id"
                )
                or ""
            )
            for slot_id, slot in dict(
                searchos_state.get("slots_by_id") or {}
            ).items()
            if isinstance(slot, Mapping)
            and slot_id in required_slot_ids
            and str(
                dict(slot.get("slot_ref") or {}).get("component_id")
                or ""
            )
            == component_b_id
        }
        sibling_obligation_ids = (
            component_b_obligation_ids - {target_obligation_id, ""}
        )
        assert len(sibling_obligation_ids) == 1
        shared_obligation_id = next(iter(sibling_obligation_ids))
        component_a_id = "component:foreign-owner-a"
        requirement_a_id = (
            "requirement:foreign-owner-a:official-current"
        )
        candidate_a_id = "candidate:foreign-owner-a:official-current"
        coverage_a_id = "coverage:foreign-owner-a:official-current"
        coverage_a_digest = "a" * 64
        ledger = deepcopy(
            dict(judgment_input.evidence_ledger_projection)
        )
        ledger.setdefault("source_requirements", []).append(
            {
                "requirement_id": requirement_a_id,
                "requirement_kind": "official_current",
                "component_id": component_a_id,
                "source_obligation_id": shared_obligation_id,
                "status": "satisfied",
                "linked_candidate_ids": [candidate_a_id],
            }
        )
        ledger.setdefault("requirement_links", []).append(
            {
                "requirement_id": requirement_a_id,
                "candidate_id": candidate_a_id,
                "link_status": "accepted",
                "link_reason": "foreign_component_a_exact_link",
            }
        )
        ledger.setdefault("candidate_records", []).append(
            {
                "candidate_id": candidate_a_id,
                "fact_disposition": "accepted",
            }
        )
        semantic_state = deepcopy(
            dict(judgment_input.semantic_state_facts)
        )
        semantic_refs = semantic_state.setdefault(
            "semantic_ref_projection", {}
        )
        semantic_refs.setdefault("source_obligation_refs", []).append(
            requirement_a_id
        )
        semantic_refs.setdefault("coverage_record_refs", []).append(
            {
                "coverage_record_id": coverage_a_id,
                "coverage_record_digest": coverage_a_digest,
                "answer_component_id": component_a_id,
            }
        )
        semantic_refs.setdefault(
            "source_obligation_coverage_refs", []
        ).append(
            {
                "requirement_id": requirement_a_id,
                "coverage_record_id": coverage_a_id,
                "coverage_record_digest": coverage_a_digest,
                "answer_component_id": component_a_id,
            }
        )
        ownership_refs.update(
            {
                "component_a_id": component_a_id,
                "component_b_id": component_b_id,
                "shared_obligation_id": shared_obligation_id,
                "target_obligation_id": target_obligation_id,
                "requirement_a_id": requirement_a_id,
                "candidate_a_id": candidate_a_id,
                "coverage_a_id": coverage_a_id,
            }
        )
        mutated = replace(
            judgment_input,
            evidence_ledger_projection=ledger,
            semantic_state_facts=semantic_state,
        )
        captured.append(mutated)
        return mutated

    monkeypatch.setattr(
        sufficiency_adapter,
        "build_sufficiency_judgment_input_from_runtime",
        wrapped,
    )
    return captured, ownership_refs


def _install_missing_same_family_component_at_sufficiency(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[Any], dict[str, str]]:
    captured: list[Any] = []
    ownership_refs = {
        "component_a_id": "component:answer-contract-owner-a",
        "requirement_a_id": (
            "requirement:answer-contract-owner-a:official-current"
        ),
        "obligation_a_id": (
            "obligation:answer-contract-owner-a:official-current"
        ),
        "source_class": "official_current_rules",
    }
    original = (
        sufficiency_adapter.build_sufficiency_judgment_input_from_runtime
    )

    def wrapped(**kwargs: Any) -> Any:
        judgment_input = original(**kwargs)
        terminal = dict(
            judgment_input.searchos_existing_gap_recovery_terminal_state
            or {}
        )
        if not terminal:
            captured.append(judgment_input)
            return judgment_input
        component_b_id = str(
            dict(terminal.get("component_ref") or {}).get(
                "component_id"
            )
            or ""
        )
        target_obligation_id = str(
            dict(terminal.get("source_obligation_ref") or {}).get(
                "source_obligation_id"
            )
            or ""
        )
        searchos_state = dict(judgment_input.searchos_state)
        required_slot_ids = set(
            searchos_state.get("required_slot_ids") or ()
        )
        component_b_sibling_obligation_refs = [
            dict(slot.get("source_obligation_ref") or {})
            for slot_id, slot in dict(
                searchos_state.get("slots_by_id") or {}
            ).items()
            if isinstance(slot, Mapping)
            and slot_id in required_slot_ids
            and str(
                dict(slot.get("slot_ref") or {}).get("component_id")
                or ""
            )
            == component_b_id
            and str(
                dict(slot.get("slot_ref") or {}).get(
                    "source_obligation_id"
                )
                or ""
            )
            != target_obligation_id
        ]
        assert len(component_b_sibling_obligation_refs) == 1
        sibling_obligation_ref = component_b_sibling_obligation_refs[0]
        sibling_obligation_id = str(
            sibling_obligation_ref.get("source_obligation_id") or ""
        )
        sibling_requirement_id = (
            "requirement:answer-contract-owner-b:sibling"
        )
        sibling_candidate_id = (
            "candidate:answer-contract-owner-b:sibling"
        )
        sibling_coverage_id = "coverage:answer-contract-owner-b:sibling"
        sibling_coverage_digest = "b" * 64
        contract = deepcopy(dict(judgment_input.contract_projection))
        contract.setdefault("source_requirements", []).append(
            {
                "requirement_id": ownership_refs["requirement_a_id"],
                "requirement_kind": "official_current",
                "required_source_class": ownership_refs["source_class"],
                "required_source_tier": "official",
                "required_currentness": "current",
                "strictness": "required",
                "component_id": ownership_refs["component_a_id"],
                "source_obligation_id": ownership_refs[
                    "obligation_a_id"
                ],
            }
        )
        ledger = deepcopy(
            dict(judgment_input.evidence_ledger_projection)
        )
        ledger.setdefault("source_requirements", []).append(
            {
                "requirement_id": ownership_refs["requirement_a_id"],
                "requirement_kind": "official_current",
                "required_source_class": ownership_refs["source_class"],
                "required_source_tier": "official",
                "required_currentness": "current",
                "component_id": ownership_refs["component_a_id"],
                "source_obligation_id": ownership_refs[
                    "obligation_a_id"
                ],
                "status": "unsatisfied",
                "reason": "component_a_exact_source_obligation_missing",
            }
        )
        ledger["source_requirements"].append(
            {
                "requirement_id": sibling_requirement_id,
                "requirement_kind": (
                    sibling_obligation_ref.get("kind")
                    or sibling_obligation_ref.get("obligation_kind")
                    or "general"
                ),
                "component_id": component_b_id,
                "source_obligation_id": sibling_obligation_id,
                "status": "satisfied",
                "linked_candidate_ids": [sibling_candidate_id],
            }
        )
        ledger.setdefault("requirement_links", []).append(
            {
                "requirement_id": sibling_requirement_id,
                "candidate_id": sibling_candidate_id,
                "link_status": "accepted",
                "link_reason": "component_b_exact_sibling_support",
            }
        )
        ledger.setdefault("candidate_records", []).append(
            {
                "candidate_id": sibling_candidate_id,
                "fact_disposition": "accepted",
            }
        )
        semantic_state = deepcopy(
            dict(judgment_input.semantic_state_facts)
        )
        semantic_refs = semantic_state.setdefault(
            "semantic_ref_projection", {}
        )
        semantic_refs.setdefault("source_obligation_refs", []).append(
            sibling_requirement_id
        )
        semantic_refs.setdefault("coverage_record_refs", []).append(
            {
                "coverage_record_id": sibling_coverage_id,
                "coverage_record_digest": sibling_coverage_digest,
                "answer_component_id": component_b_id,
            }
        )
        semantic_refs.setdefault(
            "source_obligation_coverage_refs", []
        ).append(
            {
                "requirement_id": sibling_requirement_id,
                "coverage_record_id": sibling_coverage_id,
                "coverage_record_digest": sibling_coverage_digest,
                "answer_component_id": component_b_id,
            }
        )
        answer_contract = deepcopy(
            dict(judgment_input.answer_contract_projection)
        )
        unfulfilled_source_classes = list(
            answer_contract.get("unfulfilled_source_classes") or ()
        )
        if (
            ownership_refs["source_class"]
            not in unfulfilled_source_classes
        ):
            unfulfilled_source_classes.append(
                ownership_refs["source_class"]
            )
        answer_contract[
            "unfulfilled_source_classes"
        ] = unfulfilled_source_classes
        mutated = replace(
            judgment_input,
            contract_projection=contract,
            evidence_ledger_projection=ledger,
            answer_contract_projection=answer_contract,
            semantic_state_facts=semantic_state,
        )
        ownership_refs.update(
            {
                "component_b_id": component_b_id,
                "target_obligation_id": target_obligation_id,
                "sibling_obligation_id": sibling_obligation_id,
            }
        )
        captured.append(mutated)
        return mutated

    monkeypatch.setattr(
        sufficiency_adapter,
        "build_sufficiency_judgment_input_from_runtime",
        wrapped,
    )
    return captured, ownership_refs


def _direct_component_ownership_assessment(
    *,
    requirements: list[dict[str, Any]],
    links: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    current_requirement_ids: set[str],
    current_coverage_refs: list[dict[str, Any]],
    source_obligation_coverage_refs: list[dict[str, Any]],
) -> Any:
    return sufficiency_validation._searchos_obligation_assessment(
        ledger={
            "source_requirements": requirements,
            "requirement_links": links,
            "candidate_records": candidates,
        },
        component_id="component:b",
        source_obligation_id="obligation:official_current",
        source_obligation_ref={
            "source_obligation_id": "obligation:official_current",
            "kind": "official_current",
            "required_source_class": "primary_source_documents",
        },
        current_requirement_ids=current_requirement_ids,
        current_coverage_refs=current_coverage_refs,
        source_obligation_coverage_refs=(
            source_obligation_coverage_refs
        ),
    )


def _forbid_post_terminal_blocked_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError(
            "post-terminal SearchOS blocked-FAP bypass was invoked"
        )

    monkeypatch.setattr(
        RunKernel,
        "authorize_searchos_required_needs_block",
        forbidden,
    )
    assert not hasattr(
        pipeline_orchestrator,
        "build_searchos_required_needs_blocked_fap_projection",
    )


def _install_initially_unsupported_component(
    monkeypatch: pytest.MonkeyPatch,
    *,
    remain_unsupported: bool,
    recovered_claim: str | None = None,
) -> None:
    original = PostRetirementOrdinaryPipelineHarness.ask_model
    analyst_calls = 0

    def scripted(
        self: PostRetirementOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        nonlocal analyst_calls
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            analyst_calls += 1
            if analyst_calls == 1 or remain_unsupported:
                self._record_model_call(system_prompt, kwargs)
                return json.dumps(
                    {
                        "claim_text": ("The current bounded material does not yet support this component."),
                        "support_status": "unsupported",
                        "caveats": [],
                        "nonclaims": ["No component conclusion is admitted."],
                        "blockers": ["exact_obligation_support_missing"],
                    }
                )
            if recovered_claim:
                self._record_model_call(system_prompt, kwargs)
                return json.dumps(
                    {
                        "claim_text": recovered_claim,
                        "support_status": "supported",
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
        return original(self, prompt, system_prompt, **kwargs)

    monkeypatch.setattr(
        PostRetirementOrdinaryPipelineHarness,
        "ask_model",
        scripted,
    )


def _capture_first_gap_basis(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    original = pipeline_orchestrator.build_searchos_existing_gap_basis

    def wrapped(**kwargs: Any) -> dict[str, Any]:
        try:
            basis = original(**kwargs)
        except Exception as exc:
            if not captured:
                captured.update(
                    {
                        "error": f"{type(exc).__name__}:{exc}",
                        "state": deepcopy(kwargs["state"]),
                        "slot_id": kwargs["slot_id"],
                        "component_admission_projection": deepcopy(
                            kwargs["component_admission_projection"]
                        ),
                    }
                )
            raise
        if not captured:
            captured.update(
                {
                    "state": deepcopy(kwargs["state"]),
                    "slot_id": kwargs["slot_id"],
                    "component_admission_projection": deepcopy(kwargs["component_admission_projection"]),
                    "component_coverage_history": deepcopy(kwargs["component_coverage_history"]),
                    "evidence_ledger_projection": deepcopy(kwargs["evidence_ledger_projection"]),
                    "basis": deepcopy(basis),
                }
            )
        return basis

    monkeypatch.setattr(
        pipeline_orchestrator,
        "build_searchos_existing_gap_basis",
        wrapped,
    )
    return captured


def _reenvelope_gap_basis(
    basis: dict[str, Any],
    **updates: Any,
) -> dict[str, Any]:
    core = {
        key: deepcopy(value)
        for key, value in basis.items()
        if key
        not in {
            "gap_basis_id",
            "gap_basis_digest",
            "replay_identity",
        }
    }
    core.update(deepcopy(updates))
    return _envelope(
        core,
        id_field="gap_basis_id",
        digest_field="gap_basis_digest",
        prefix="searchos-gap-basis",
    )


def _reenvelope_recovery_purpose(
    purpose: dict[str, Any],
    **updates: Any,
) -> dict[str, Any]:
    core = {
        key: deepcopy(value)
        for key, value in purpose.items()
        if key
        not in {
            "recovery_purpose_id",
            "recovery_purpose_digest",
            "replay_identity",
        }
    }
    core.update(deepcopy(updates))
    return _envelope(
        core,
        id_field="recovery_purpose_id",
        digest_field="recovery_purpose_digest",
        prefix="searchos-recovery-purpose",
    )


@pytest.mark.parametrize("mode", ["Fast", "Balanced", "Deep"])
def test_product_existing_gap_recovers_through_same_component_roles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    captured_gap = _capture_first_gap_basis(monkeypatch)
    sufficiency_inputs = _capture_sufficiency_inputs(monkeypatch)

    def forbidden_dynamic_recovery(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("retained Scrutineer-derived recovery path was invoked")

    def forbidden_legacy_recovery(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("legacy existing-gap recovery path was invoked")

    monkeypatch.setattr(
        multicomponent_runtime,
        "_begin_scheduler_dynamic_recovery",
        forbidden_dynamic_recovery,
    )
    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_component_gap_recovery",
        forbidden_legacy_recovery,
    )
    monkeypatch.setattr(
        pipeline_orchestrator,
        "run_source_class_recovery_dispatch",
        forbidden_legacy_recovery,
    )
    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_run_authority_search_judgment_action",
        forbidden_legacy_recovery,
    )
    recovery_results: list[Any] = []
    reassessment_errors: list[str] = []
    original_recovery = (
        pipeline_orchestrator.execute_searchos_existing_gap_recovery_cycle
    )

    def capture_recovery(**kwargs: Any) -> Any:
        result = original_recovery(**kwargs)
        recovery_results.append(result)
        return result

    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_searchos_existing_gap_recovery_cycle",
        capture_recovery,
    )
    original_reassessment = (
        pipeline_orchestrator
        .execute_searchos_same_component_reassessment_from_scope
    )

    def capture_reassessment(*args: Any, **kwargs: Any) -> Any:
        try:
            return original_reassessment(*args, **kwargs)
        except Exception as exc:
            reassessment_errors.append(f"{type(exc).__name__}:{exc}")
            raise

    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_searchos_same_component_reassessment_from_scope",
        capture_reassessment,
    )
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=False,
        recovered_claim=(
            "Alpha's current canonical API response name is Raven."
        ),
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode=mode,
        query=(
            "What do Alpha's current API docs say about the Raven endpoint?"
        ),
        core_topic="Alpha current API documentation",
        primary_entity="Alpha",
        researcher_queries=["Alpha current API documentation"],
        evidence_rows=_initial_incomplete_canonical_rows(),
        followup_evidence_rows=_recovered_canonical_rows(),
        read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
        read_content_by_url={
            "https://docs.alpha.example/api": (
                "Alpha's canonical API documentation lists the endpoint, "
                "but omits its current response name."
            ),
            "https://docs.alpha.example/api/raven": (
                "Alpha's current canonical API response name is Raven."
            ),
            "https://example.test/alpha-api-overview": (
                "A secondary overview confirms that Alpha publishes an API, "
                "without stating the current canonical response name."
            ),
        },
        raw_author_response=(
            "Alpha's current canonical API response name is Raven. "
            "[[1]](https://docs.alpha.example/api/raven)"
        ),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    terminal = kernel.state.projections["searchos_existing_gap_recovery_terminal"]
    admission = kernel.state.projections["multicomponent_component_admission"]
    role_system_prompts = [item["system_prompt"] for item in harness.model_calls]

    assert terminal["terminal_status"] == "recovered", (
        terminal["terminal_reason"],
        terminal["expenditure"],
        {
            key: kernel.state.searchos_state["slots_by_id"][terminal["recovery_slot_ref"]["slot_id"]].get(key)
            for key in (
                "posture",
                "latest_reason",
                "judgment_call_count",
                "custody_refs",
                "action_history",
            )
        },
        outcome.execution_trace["searchos_slice_a"]["existing_gap_recovery"].get("same_component_reassessment"),
        reassessment_errors,
    )
    recovered_replay_basis = captured_gap["basis"]
    recovered_replay_purpose = (
        build_searchos_materially_novel_recovery_purpose(
            recovered_replay_basis
        )
    )
    before_recovered_replay = deepcopy(kernel.state)
    recovered_replay = (
        kernel.authorize_searchos_existing_gap_recovery_admission(
            gap_basis=recovered_replay_basis,
            recovery_purpose=recovered_replay_purpose,
        )
    )
    assert isinstance(recovered_replay, Mapping)
    assert recovered_replay["exact_replay"] is True
    assert recovered_replay["work_authorized"] is False
    assert kernel.state == before_recovered_replay
    assert terminal["coverage_gained"] is True
    assert terminal["gap_remains"] is False
    assert terminal["further_existing_gap_recovery_authorized"] is False
    assert terminal["final_sufficiency_decided"] is False
    assert len(recovery_results) == 1
    initial_material = json.dumps(
        harness.searchos_semantic_material_before_pipeline_consumption,
        sort_keys=True,
    )
    recovered_material = json.dumps(
        recovery_results[0].searchos_semantic_material,
        sort_keys=True,
    )
    assert "response name is Raven" not in initial_material
    assert "response name is Raven" in recovered_material
    assert any(
        item.get("recovery_cycle_id")
        for item in harness.read_assessment_calls
    )
    assert len(harness.search_calls) == 2
    recovery_query_items = [
        item
        for item in outcome.execution_trace["query_plan"]["items"]
        if item.get("authorized_query")
        == "Alpha exact current official operating protocol details"
    ]
    assert len(recovery_query_items) == 1
    assert recovery_query_items[0]["iteration"] == 2
    assert admission["component_count"] == 2
    assert admission["component_admission_refs"][0]["admission_status"] == "unsupported"
    assert admission["component_admission_refs"][1]["admission_status"] in {"admitted", "admitted_with_caveats"}
    assert admission["component_admission_refs"][1]["same_component_reassessment"] is True
    recovered_coverage_ref = admission["component_admission_refs"][1][
        "component_coverage_ref"
    ]
    assert kernel.state.component_coverage_history[-1][
        "coverage_record_digest"
    ] == recovered_coverage_ref["coverage_record_digest"]
    recovered_evidence_ids = {
        item["evidence_ref_id"]
        for item in admission["component_admission_refs"][1]["evidence_refs"]
    }
    current_ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    recovered_candidates = [
        item
        for item in current_ledger["candidate_records"]
        if item.get("candidate_id") in recovered_evidence_ids
    ]
    assert recovered_candidates
    assert all(
        item.get("final_evidence_eligible") is True
        for item in recovered_candidates
    )
    target_obligation_id = terminal["source_obligation_ref"][
        "source_obligation_id"
    ]
    target_requirement_ids = kernel.state.component_coverage_history[-1][
        "evidence_ledger_binding"
    ]["source_requirement_ids"]
    assert len(target_requirement_ids) == 1
    target_requirement = next(
        item
        for item in current_ledger["source_requirements"]
        if item.get("requirement_id") == target_requirement_ids[0]
    )
    target_links = [
        item
        for item in current_ledger["requirement_links"]
        if item.get("requirement_id") == target_requirement_ids[0]
    ]
    cycle = kernel.state.searchos_state[
        "existing_gap_recovery_cycles"
    ][0]
    purpose = build_searchos_materially_novel_recovery_purpose(
        captured_gap["basis"]
    )
    _preview_state, preview_admission = (
        admit_searchos_existing_gap_recovery_cycle(
            state=captured_gap["state"],
            gap_basis=captured_gap["basis"],
            recovery_purpose=purpose,
        )
    )
    assert {
        captured_gap["basis"]["source_obligation_ref"][
            "source_obligation_id"
        ],
        purpose["source_obligation_ref"]["source_obligation_id"],
        cycle["source_obligation_ref"]["source_obligation_id"],
        cycle["recovery_slot_ref"]["source_obligation_id"],
        target_requirement["source_obligation_id"],
        terminal["source_obligation_ref"]["source_obligation_id"],
        terminal["recovery_slot_ref"]["source_obligation_id"],
    } == {target_obligation_id}
    assert preview_admission["lease"]["source_obligation_ref"][
        "source_obligation_id"
    ] == target_obligation_id
    assert {
        item["requirement_id"] for item in target_links
    } == set(target_requirement_ids)
    assert len(
        [
            item
            for item in target_links
            if item["candidate_id"] in recovered_evidence_ids
        ]
    ) == 1
    assert (
        terminal["component_coverage_ref"]["coverage_record_digest"]
        == recovered_coverage_ref["coverage_record_digest"]
    )
    assert role_system_prompts.count(ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]) == 2
    assert role_system_prompts.count(ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_DPRIME]) == 2
    assert ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER] not in role_system_prompts
    assert not harness.full_search_judgment_inputs
    sufficiency = kernel.state.sufficiency_judgment_projection
    assert sufficiency, (
        outcome.report,
        {
            key: outcome.execution_trace["searchos_slice_a"]
            .get("readiness_projection", {})
            .get(key)
            for key in (
                "all_required_slots_slice_a_ready",
                "unresolved_required_slots",
                "author_execution_allowed",
                "final_answer_packet_allowed",
            )
        },
    )
    assert sufficiency["decision"] == "partial_answer_authorized"
    assert sufficiency["final_answer_posture"] == "partial_answer"
    assert sufficiency["contract_fulfilled"] is False
    assert sufficiency["required_obligations_satisfied"] is False
    assert sufficiency["final_answer_allowed"] is True
    missing_by_id = {
        item["requirement_id"]: item
        for item in sufficiency["missing_required_obligations"]
    }
    assert set(missing_by_id) >= {
        "run-contract:canonical_docs",
        "answer-contract:primary_source_documents",
        "answer-contract:reputable_secondary",
    }
    assert sufficiency_inputs
    terminal_input = sufficiency_inputs[-1]
    assert (
        terminal_input.searchos_existing_gap_recovery_terminal_state
        == terminal
    )
    terminal_consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assert terminal_consumption["terminal_status"] == "recovered"
    assert (
        terminal_consumption["source_obligation_ref"][
            "source_obligation_id"
        ]
        == target_obligation_id
    )
    assert terminal_consumption["target_requirement_ids"] == (
        target_requirement_ids
    )
    assert terminal_consumption["terminal_component_ready"] is True
    assert all(
        item["status"] == "satisfied"
        for item in terminal_consumption[
            "required_source_obligation_assessments"
        ]
    )
    assert "response name is Raven" in outcome.report
    assert harness.author_prompts
    assert "Raven" in harness.author_prompts[-1]
    assert "could not produce a supported answer" not in outcome.report


def test_two_obligation_recovery_credits_only_the_exact_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sufficiency_inputs = _capture_sufficiency_inputs(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=False,
        recovered_claim=(
            "Alpha's current official operating protocol is Raven."
        ),
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating protocol?",
        core_topic="Alpha current official operating protocol",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating protocol"],
        evidence_rows=_initial_incomplete_evidence_rows(),
        followup_evidence_rows=_recovered_official_evidence_rows(),
        read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
        read_content_by_url={
            "https://alpha.gov/operating-overview": (
                "Alpha publishes an official operating rule, but this overview "
                "omits the name of its current operating protocol."
            ),
            "https://alpha.gov/operating-protocol": (
                "Alpha's current official operating protocol is Raven."
            ),
        },
        raw_author_response=(
            "Alpha's current official operating protocol is Raven. "
            "[[1]](https://alpha.gov/operating-protocol)"
        ),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    terminal = kernel.state.projections[
        "searchos_existing_gap_recovery_terminal"
    ]
    assert terminal["terminal_status"] == "recovered", terminal
    target_obligation_id = terminal["source_obligation_ref"][
        "source_obligation_id"
    ]
    component_ref = terminal["component_ref"]
    component_obligation_ids = set(
        next(
            item
            for item in kernel.state.initial_answer_contract[
                "accepted_answer_component_refs"
            ]
            if item["component_id"] == component_ref["component_id"]
        )["source_obligation_candidate_ids"]
    )
    assert len(component_obligation_ids) == 2
    sibling_obligation_id = next(
        item
        for item in component_obligation_ids
        if item != target_obligation_id
    )
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    coverage = kernel.state.component_coverage_history[-1]
    target_requirement_ids = coverage["evidence_ledger_binding"][
        "source_requirement_ids"
    ]
    assert target_requirement_ids
    target_requirements = [
        item
        for item in ledger["source_requirements"]
        if item.get("requirement_id") in target_requirement_ids
    ]
    assert {
        item.get("source_obligation_id")
        for item in target_requirements
    } == {target_obligation_id}
    recovered_candidate_ids = {
        item["evidence_ref_id"]
        for item in kernel.state.projections[
            "multicomponent_component_admission"
        ]["component_admission_refs"][-1]["evidence_refs"]
    }
    novel_ids = set(
        outcome.execution_trace["searchos_slice_a"][
            "existing_gap_recovery"
        ].get("materially_novel_recovery_evidence_ids") or ()
    )
    assert recovered_candidate_ids == novel_ids, {
        "recovered": recovered_candidate_ids,
        "novel": novel_ids,
        "reassessment": outcome.execution_trace["searchos_slice_a"][
            "existing_gap_recovery"
        ].get("same_component_reassessment"),
    }
    recovered_links = [
        item
        for item in ledger["requirement_links"]
        if item.get("candidate_id") in recovered_candidate_ids
        and item.get("requirement_id") in target_requirement_ids
    ]
    assert len(recovered_links) == len(target_requirement_ids)
    assert not [
        item
        for item in ledger["source_requirements"]
        if item.get("source_obligation_id") == sibling_obligation_id
        and item.get("requirement_id") in target_requirement_ids
    ]
    assert not [
        item
        for item in ledger["requirement_links"]
        if item.get("candidate_id") in recovered_candidate_ids
        and any(
            requirement.get("requirement_id")
            == item.get("requirement_id")
            and requirement.get("source_obligation_id")
            == sibling_obligation_id
            for requirement in ledger["source_requirements"]
        )
    ]
    semantic_outcomes = outcome.execution_trace["searchos_slice_a"][
        "semantic_outcomes_by_slot"
    ]
    target_original_slot = next(
        slot_id
        for slot_id, slot in kernel.state.searchos_state[
            "slots_by_id"
        ].items()
        if slot["slot_ref"].get("source_obligation_id")
        == target_obligation_id
        and not slot["slot_ref"].get("recovery_cycle_id")
    )
    sibling_slot = next(
        slot_id
        for slot_id, slot in kernel.state.searchos_state[
            "slots_by_id"
        ].items()
        if slot["slot_ref"].get("source_obligation_id")
        == sibling_obligation_id
    )
    assert semantic_outcomes[target_original_slot][
        "searchos_handoff_material_consumed"
    ] is True
    assert semantic_outcomes[sibling_slot][
        "searchos_handoff_material_consumed"
    ] is False
    readiness = outcome.execution_trace["searchos_slice_a"][
        "readiness_projection"
    ]
    sibling_readiness = next(
        item
        for item in readiness["slot_records"]
        if item["slot_ref"]["slot_id"] == sibling_slot
    )
    assert sibling_readiness["slice_a_ready"] is False
    sufficiency = kernel.state.sufficiency_judgment_projection
    assert sufficiency["decision"] != "satisfied"
    assert sufficiency["final_answer_posture"] != "satisfied"
    consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assessments = {
        item["source_obligation_id"]: item
        for item in consumption[
            "required_source_obligation_assessments"
        ]
    }
    assert assessments[target_obligation_id]["status"] == "satisfied"
    assert assessments[sibling_obligation_id]["status"] != "satisfied"
    assert sufficiency_inputs[-1].to_model_payload()[
        "searchos_existing_gap_recovery_terminal_ref"
    ]["terminal_aggregate_id"] == terminal["terminal_aggregate_id"]
    if sufficiency["final_answer_allowed"]:
        assert sufficiency["final_answer_posture"] == "partial_answer"
        assert harness.author_prompts
    else:
        assert not harness.author_prompts


def test_two_component_shared_obligation_preserves_component_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sufficiency_inputs, ownership_refs = (
        _install_foreign_shared_obligation_at_sufficiency(monkeypatch)
    )
    _forbid_post_terminal_blocked_adapter(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=False,
        recovered_claim=(
            "Alpha's current official operating protocol is Raven."
        ),
    )
    _outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating protocol?",
        core_topic="Alpha current official operating protocol",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating protocol"],
        evidence_rows=_initial_incomplete_evidence_rows(),
        followup_evidence_rows=_recovered_official_evidence_rows(),
        read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
        read_content_by_url={
            "https://alpha.gov/operating-overview": (
                "Alpha publishes an official operating rule, but this "
                "overview omits the name of its current operating protocol."
            ),
            "https://alpha.gov/operating-protocol": (
                "Alpha's current official operating protocol is Raven."
            ),
        },
        raw_author_response=(
            "Alpha's current official operating protocol is Raven. "
            "[[1]](https://alpha.gov/operating-protocol)"
        ),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    assert sufficiency_inputs and ownership_refs
    judgment_input = sufficiency_inputs[-1]
    ledger = dict(judgment_input.evidence_ledger_projection)
    foreign_requirement = next(
        item
        for item in ledger["source_requirements"]
        if item.get("requirement_id")
        == ownership_refs["requirement_a_id"]
    )
    assert foreign_requirement["component_id"] == ownership_refs[
        "component_a_id"
    ]
    assert (
        foreign_requirement["source_obligation_id"]
        == ownership_refs["shared_obligation_id"]
    )
    assert any(
        item.get("requirement_id")
        == ownership_refs["requirement_a_id"]
        and item.get("candidate_id")
        == ownership_refs["candidate_a_id"]
        for item in ledger["requirement_links"]
    )
    semantic_refs = dict(
        judgment_input.semantic_state_facts[
            "semantic_ref_projection"
        ]
    )
    assert any(
        item.get("coverage_record_id")
        == ownership_refs["coverage_a_id"]
        and item.get("answer_component_id")
        == ownership_refs["component_a_id"]
        for item in semantic_refs["coverage_record_refs"]
    )

    sufficiency = kernel.state.sufficiency_judgment_projection
    consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assessments = {
        item["source_obligation_id"]: item
        for item in consumption[
            "required_source_obligation_assessments"
        ]
    }
    shared_assessment = assessments[
        ownership_refs["shared_obligation_id"]
    ]
    target_assessment = assessments[
        ownership_refs["target_obligation_id"]
    ]
    assert shared_assessment["status"] == "missing"
    assert target_assessment["status"] == "satisfied"
    assert ownership_refs["candidate_a_id"] not in {
        candidate_id
        for assessment in assessments.values()
        for candidate_id in assessment.get(
            "satisfied_candidate_ids", []
        )
    }
    assert consumption["terminal_component_ready"] is False
    assert sufficiency["decision"] not in {
        "ready_direct",
        "ready_with_caveats",
    }
    serialized_consumption = json.dumps(
        consumption,
        sort_keys=True,
    )
    for foreign_ref in (
        ownership_refs["component_a_id"],
        ownership_refs["requirement_a_id"],
        ownership_refs["candidate_a_id"],
        ownership_refs["coverage_a_id"],
    ):
        assert foreign_ref not in serialized_consumption
    fap_executed = bool(
        kernel.state.final_answer_packet
        or kernel.state.final_answer_packet_history
    )
    assert not fap_executed or (
        sufficiency["final_answer_allowed"]
        and sufficiency["final_answer_posture"] == "partial_answer"
    )
    if sufficiency["final_answer_allowed"]:
        assert sufficiency["final_answer_posture"] == "partial_answer"
        assert harness.author_prompts
    else:
        assert not harness.author_prompts


def test_unscoped_different_id_survives_same_family_terminal_recovery() -> None:
    existing = sufficiency_validation.SufficiencyRequirementAssessment(
        requirement_id="run-contract:canonical_docs",
        requirement_kind="canonical_docs",
        required_source_class="primary_source_documents",
        status="missing",
    )
    terminal = sufficiency_validation.SufficiencyRequirementAssessment(
        requirement_id=(
            "searchos_semantic_requirement:canonical_documentation:terminal"
        ),
        requirement_kind="canonical_documentation",
        required_source_class="primary_source_documents",
        component_id="component:b",
        source_obligation_id="obligation:canonical_documentation",
        status="satisfied",
    )

    assert not sufficiency_validation._terminal_assessment_exactly_reconciles(
        existing,
        terminal,
    )


def test_exact_unscoped_id_reconciles_once_and_only_once() -> None:
    exact = sufficiency_validation.SufficiencyRequirementAssessment(
        requirement_id="requirement:exact-terminal-id",
        requirement_kind="canonical_docs",
        required_source_class="primary_source_documents",
        status="missing",
    )
    same_family_sibling = (
        sufficiency_validation.SufficiencyRequirementAssessment(
            requirement_id="requirement:different-id",
            requirement_kind="canonical_documentation",
            required_source_class="primary_source_documents",
            status="missing",
        )
    )
    terminal = sufficiency_validation.SufficiencyRequirementAssessment(
        requirement_id="requirement:exact-terminal-id",
        requirement_kind="canonical_documentation",
        required_source_class="primary_source_documents",
        component_id="component:b",
        source_obligation_id="obligation:canonical_documentation",
        status="satisfied",
    )

    reconciled = [
        item
        for item in (exact, same_family_sibling)
        if sufficiency_validation._terminal_assessment_exactly_reconciles(
            item,
            terminal,
        )
    ]
    assert reconciled == [exact]


def test_answer_contract_summary_requires_every_exact_requirement() -> None:
    assessment = sufficiency_validation.SufficiencyRequirementAssessment(
        requirement_id="answer-contract:primary_source_documents",
        requirement_kind="answer_contract_source_class",
        required_source_class="primary_source_documents",
        status="missing",
    )
    contract_requirements = [
        {
            "requirement_id": "requirement:component-a:primary",
            "required_source_class": "primary_source_documents",
            "component_id": "component:a",
            "source_obligation_id": "obligation:a:primary",
        },
        {
            "requirement_id": "requirement:component-b:primary",
            "required_source_class": "primary_source_documents",
            "component_id": "component:b",
            "source_obligation_id": "obligation:b:primary",
        },
    ]
    one_missing = [
        {
            **contract_requirements[0],
            "status": "missing",
        },
        {
            **contract_requirements[1],
            "status": "satisfied",
        },
    ]
    independently_satisfied = [
        {
            **requirement,
            "status": "satisfied",
        }
        for requirement in contract_requirements
    ]
    foreign_component = [
        {
            **contract_requirements[0],
            "component_id": "component:foreign",
            "source_obligation_id": "obligation:foreign:primary",
            "status": "satisfied",
        },
        {
            **contract_requirements[1],
            "status": "satisfied",
        },
    ]
    foreign_obligation = [
        {
            **contract_requirements[0],
            "source_obligation_id": "obligation:foreign:primary",
            "status": "satisfied",
        },
        {
            **contract_requirements[1],
            "status": "satisfied",
        },
    ]
    duplicate_contract_id = [
        contract_requirements[0],
        {
            **contract_requirements[1],
            "requirement_id": contract_requirements[0]["requirement_id"],
        },
    ]
    duplicate_ledger_id = [
        independently_satisfied[0],
        {
            **independently_satisfied[0],
            "component_id": "component:foreign",
            "status": "missing",
        },
        independently_satisfied[1],
    ]

    assert not (
        sufficiency_validation
        ._answer_contract_assessment_exactly_reconciled(
            assessment,
            contract_requirements=contract_requirements,
            ledger_requirements=one_missing,
        )
    )
    assert not sufficiency_validation._answer_contract_assessment_exactly_reconciled(
        assessment,
        contract_requirements=contract_requirements,
        ledger_requirements=foreign_component,
    )
    assert not sufficiency_validation._answer_contract_assessment_exactly_reconciled(
        assessment,
        contract_requirements=contract_requirements,
        ledger_requirements=foreign_obligation,
    )
    assert not sufficiency_validation._answer_contract_assessment_exactly_reconciled(
        assessment,
        contract_requirements=duplicate_contract_id,
        ledger_requirements=[independently_satisfied[0]],
    )
    assert not sufficiency_validation._answer_contract_assessment_exactly_reconciled(
        assessment,
        contract_requirements=contract_requirements,
        ledger_requirements=duplicate_ledger_id,
    )
    assert sufficiency_validation._answer_contract_assessment_exactly_reconciled(
        assessment,
        contract_requirements=contract_requirements,
        ledger_requirements=independently_satisfied,
    )
    normalized_owned_positive = [
        {
            **independently_satisfied[0],
            "requirement_id": "REQUIREMENT-COMPONENT-A-PRIMARY",
            "component_id": "COMPONENT-A",
            "source_obligation_id": "OBLIGATION-A-PRIMARY",
        },
        independently_satisfied[1],
    ]
    assert sufficiency_validation._answer_contract_assessment_exactly_reconciled(
        assessment,
        contract_requirements=contract_requirements,
        ledger_requirements=normalized_owned_positive,
    )


def test_two_component_same_family_missing_owner_survives_terminal_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sufficiency_inputs, ownership_refs = (
        _install_missing_same_family_component_at_sufficiency(
            monkeypatch
        )
    )
    _forbid_post_terminal_blocked_adapter(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=False,
        recovered_claim=(
            "Alpha's current official operating protocol is Raven."
        ),
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating protocol?",
        core_topic="Alpha current official operating protocol",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating protocol"],
        evidence_rows=_initial_incomplete_evidence_rows(),
        followup_evidence_rows=_recovered_official_evidence_rows(),
        read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
        read_content_by_url={
            "https://alpha.gov/operating-overview": (
                "Alpha publishes an official operating rule, but this "
                "overview omits the name of its current operating protocol."
            ),
            "https://alpha.gov/operating-protocol": (
                "Alpha's current official operating protocol is Raven."
            ),
        },
        raw_author_response=(
            "Alpha's current official operating protocol is Raven. "
            "[[1]](https://alpha.gov/operating-protocol)"
        ),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    terminal = kernel.state.projections[
        "searchos_existing_gap_recovery_terminal"
    ]
    assert terminal["terminal_status"] == "recovered"
    assert sufficiency_inputs
    final_input = sufficiency_inputs[-1]
    assert any(
        item.get("requirement_id")
        == ownership_refs["requirement_a_id"]
        and item.get("component_id")
        == ownership_refs["component_a_id"]
        for item in final_input.contract_projection[
            "source_requirements"
        ]
    )
    sufficiency = kernel.state.sufficiency_judgment_projection
    missing_by_id = {
        item["requirement_id"]: item
        for item in sufficiency["missing_required_obligations"]
    }
    missing_a = missing_by_id[ownership_refs["requirement_a_id"]]
    assert sufficiency_validation._evidence_ledger_identity(
        missing_a["component_id"]
    ) == sufficiency_validation._evidence_ledger_identity(
        ownership_refs["component_a_id"]
    )
    assert sufficiency_validation._evidence_ledger_identity(
        missing_a["source_obligation_id"]
    ) == sufficiency_validation._evidence_ledger_identity(
        ownership_refs["obligation_a_id"]
    )
    answer_contract_missing = missing_by_id[
        "answer-contract:official_current_rules"
    ]
    assert (
        answer_contract_missing["required_source_class"]
        == ownership_refs["source_class"]
    )
    consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    target_assessments = consumption[
        "required_source_obligation_assessments"
    ]
    assert target_assessments
    exact_target = [
        item
        for item in target_assessments
        if item["source_obligation_id"]
        == terminal["source_obligation_ref"][
            "source_obligation_id"
        ]
    ]
    assert len(exact_target) == 1
    assert exact_target[0]["status"] == "satisfied"
    assert sufficiency_validation._evidence_ledger_identity(
        exact_target[0]["component_id"]
    ) == sufficiency_validation._evidence_ledger_identity(
        terminal["component_ref"]["component_id"]
    )
    target_assessment = next(
        item
        for item in target_assessments
        if sufficiency_validation._evidence_ledger_identity(
            item["source_obligation_id"]
        )
        == sufficiency_validation._evidence_ledger_identity(
            ownership_refs["target_obligation_id"]
        )
    )
    assert (
        sufficiency_validation._kind_family(target_assessment)
        == "official_current"
    )
    assert (
        sufficiency_validation._kind_family(missing_a)
        == "official_current"
    )
    assert consumption["terminal_component_ready"] is False
    assert sufficiency["decision"] not in {
        "ready_direct",
        "ready_with_caveats",
    }
    assert sufficiency["required_obligations_satisfied"] is False
    assert sufficiency["contract_fulfilled"] is False
    assert sufficiency["final_answer_allowed"] is True
    assert sufficiency["final_answer_posture"] == "partial_answer"
    assert harness.author_prompts
    assert "Raven" in outcome.report


def test_foreign_component_same_obligation_id_cannot_satisfy_component_b() -> None:
    assessment = _direct_component_ownership_assessment(
        requirements=[
            {
                "requirement_id": "requirement:b:official-current",
                "requirement_kind": "official_current",
                "component_id": "component:b",
                "source_obligation_id": "obligation:official_current",
                "status": "missing",
            },
            {
                "requirement_id": "requirement:a:official-current",
                "requirement_kind": "official_current",
                "component_id": "component:a",
                "source_obligation_id": "obligation:official_current",
                "status": "satisfied",
            },
        ],
        links=[
            {
                "requirement_id": "requirement:a:official-current",
                "candidate_id": "candidate:a:official-current",
                "link_status": "accepted",
            }
        ],
        candidates=[
            {
                "candidate_id": "candidate:a:official-current",
                "fact_disposition": "accepted",
            }
        ],
        current_requirement_ids={
            "requirement:a:official-current",
            "requirement:b:official-current",
        },
        current_coverage_refs=[],
        source_obligation_coverage_refs=[],
    )

    assert assessment.component_id == "component:b"
    assert assessment.status == "missing"
    assert assessment.satisfied_candidate_ids == ()


def test_foreign_component_same_requirement_id_is_ambiguous_and_fails_closed() -> None:
    assessment = _direct_component_ownership_assessment(
        requirements=[
            {
                "requirement_id": "requirement:shared-id",
                "requirement_kind": "official_current",
                "component_id": "component:b",
                "source_obligation_id": "obligation:official_current",
                "status": "missing",
            },
            {
                "requirement_id": "requirement:shared-id",
                "requirement_kind": "official_current",
                "component_id": "component:a",
                "source_obligation_id": "obligation:official_current",
                "status": "satisfied",
            },
        ],
        links=[
            {
                "requirement_id": "requirement:shared-id",
                "candidate_id": "candidate:a:shared-id",
                "link_status": "accepted",
            }
        ],
        candidates=[
            {
                "candidate_id": "candidate:a:shared-id",
                "fact_disposition": "accepted",
            }
        ],
        current_requirement_ids={"requirement:shared-id"},
        current_coverage_refs=[],
        source_obligation_coverage_refs=[],
    )

    assert assessment.component_id == "component:b"
    assert assessment.status == "missing"
    assert assessment.satisfied_candidate_ids == ()


@pytest.mark.parametrize(
    ("join_case", "expected_status"),
    [
        ("missing", "missing"),
        ("stale", "missing"),
        ("foreign_component", "missing"),
        ("duplicated", "missing"),
        ("exact_current", "satisfied"),
    ],
)
def test_unscoped_requirement_requires_one_exact_current_component_coverage_join(
    join_case: str,
    expected_status: str,
) -> None:
    requirement_id = "requirement:unscoped:official-current"
    coverage_b = {
        "coverage_record_id": "coverage:b:current",
        "coverage_record_digest": "b" * 64,
        "answer_component_id": "component:b",
    }
    exact_join = {
        "requirement_id": requirement_id,
        "source_obligation_ids": [
            "obligation:official_current"
        ],
        **coverage_b,
    }
    if join_case == "missing":
        current_coverage_refs: list[dict[str, Any]] = [coverage_b]
        ownership_joins: list[dict[str, Any]] = []
    elif join_case == "stale":
        current_coverage_refs = [coverage_b]
        ownership_joins = [
            {
                "requirement_id": requirement_id,
                "coverage_record_id": "coverage:b:stale",
                "coverage_record_digest": "c" * 64,
                "answer_component_id": "component:b",
            }
        ]
    elif join_case == "foreign_component":
        coverage_a = {
            "coverage_record_id": "coverage:a:current",
            "coverage_record_digest": "a" * 64,
            "answer_component_id": "component:a",
        }
        current_coverage_refs = [coverage_a]
        ownership_joins = [
            {
                "requirement_id": requirement_id,
                **coverage_a,
            }
        ]
    elif join_case == "duplicated":
        current_coverage_refs = [coverage_b]
        ownership_joins = [
            exact_join,
            {
                "requirement_id": requirement_id,
                "coverage_record_id": "coverage:b:other",
                "coverage_record_digest": "d" * 64,
                "answer_component_id": "component:b",
            },
        ]
    else:
        current_coverage_refs = [coverage_b]
        ownership_joins = [exact_join]

    assessment = _direct_component_ownership_assessment(
        requirements=[
            {
                "requirement_id": requirement_id,
                "requirement_kind": "official_current",
                "component_id": "",
                "source_obligation_id": "obligation:official_current",
                "status": "satisfied",
            }
        ],
        links=[
            {
                "requirement_id": requirement_id,
                "candidate_id": "candidate:unscoped:official-current",
                "link_status": "accepted",
            }
        ],
        candidates=[
            {
                "candidate_id": (
                    "candidate:unscoped:official-current"
                ),
                "fact_disposition": "accepted",
            }
        ],
        current_requirement_ids={requirement_id},
        current_coverage_refs=current_coverage_refs,
        source_obligation_coverage_refs=ownership_joins,
    )

    assert assessment.component_id == "component:b"
    assert assessment.status == expected_status
    if expected_status == "satisfied":
        assert assessment.requirement_id == requirement_id
        assert assessment.satisfied_candidate_ids == (
            "candidate:unscoped:official-current",
        )
    else:
        assert assessment.satisfied_candidate_ids == ()


def test_two_obligation_recovery_completes_with_prior_sibling_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_gap = _capture_first_gap_basis(monkeypatch)
    sufficiency_inputs = _capture_sufficiency_inputs(monkeypatch)
    original_ask_model = PostRetirementOrdinaryPipelineHarness.ask_model
    analyst_calls = 0

    def scripted_model(
        self: PostRetirementOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        nonlocal analyst_calls
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            analyst_calls += 1
            self._record_model_call(system_prompt, kwargs)
            return json.dumps(
                {
                    "claim_text": (
                        "Alpha's current official operating rule is "
                        "canonically published."
                        if analyst_calls == 1
                        else (
                            "Alpha's current official operating rate is "
                            "14 units per hour."
                        )
                    ),
                    "support_status": "supported",
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                }
            )
        return original_ask_model(
            self,
            prompt,
            system_prompt,
            **kwargs,
        )

    monkeypatch.setattr(
        PostRetirementOrdinaryPipelineHarness,
        "ask_model",
        scripted_model,
    )
    original_outcomes = (
        pipeline_orchestrator.build_searchos_semantic_outcomes_by_slot
    )

    def keep_numeric_obligation_unresolved_until_recovery(
        **kwargs: Any,
    ) -> dict[str, dict[str, Any]]:
        outcomes = original_outcomes(**kwargs)
        admissions = list(
            dict(kwargs["component_admission_projection"]).get(
                "component_admission_refs"
            )
            or ()
        )
        if not any(
            dict(item).get("searchos_recovery_cycle_ref")
            for item in admissions
            if isinstance(item, Mapping)
        ):
            for slot_id, outcome in outcomes.items():
                if slot_id.endswith("obligation:source_bound_numeric"):
                    outcome.update(
                        {
                            "component_analyst_proposal_ref": {},
                            "component_analyst_proposal_status": (
                                "not_proposed"
                            ),
                            "component_dprime_validation_ref": {},
                            "component_dprime_validation_status": (
                                "not_accepted"
                            ),
                            "semantic_admission_outcome_ref": {},
                            "semantic_admission_status": "not_admitted",
                            "searchos_handoff_material_consumed": False,
                        }
                    )
        return outcomes

    monkeypatch.setattr(
        pipeline_orchestrator,
        "build_searchos_semantic_outcomes_by_slot",
        keep_numeric_obligation_unresolved_until_recovery,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating protocol?",
        core_topic="Alpha current official operating protocol",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating protocol"],
        evidence_rows=_official_evidence_rows(),
        followup_evidence_rows=_recovered_numeric_evidence_rows(),
        read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
        read_content_by_url={
            "https://alpha.gov/operating-rule": (
                "Alpha's current official operating rule is canonically "
                "published."
            ),
            "https://alpha.gov/operating-rate-details": (
                "Alpha's current official operating rate is 14 units per hour."
            ),
        },
        raw_author_response=(
            "Alpha's current official operating rule is canonically published. "
            "[[1]](https://alpha.gov/operating-rule)"
        ),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    assert "searchos_existing_gap_recovery_terminal" in kernel.state.projections, {
        slot_id: {
            "posture": slot.get("posture"),
            "latest_reason": slot.get("latest_reason"),
        }
        for slot_id, slot in kernel.state.searchos_state.get(
            "slots_by_id", {}
        ).items()
    }
    terminal = kernel.state.projections[
        "searchos_existing_gap_recovery_terminal"
    ]
    assert terminal["terminal_status"] == "recovered", (
        terminal["terminal_reason"],
        terminal["terminal_blocker"],
        outcome.execution_trace["searchos_slice_a"][
            "existing_gap_recovery"
        ],
    )
    target_obligation_id = terminal["source_obligation_ref"][
        "source_obligation_id"
    ]
    assert target_obligation_id == "obligation:source_bound_numeric"
    component_obligation_ids = set(
        next(
            item
            for item in kernel.state.initial_answer_contract[
                "accepted_answer_component_refs"
            ]
            if item["component_id"]
            == terminal["component_ref"]["component_id"]
        )["source_obligation_candidate_ids"]
    )
    assert len(component_obligation_ids) == 2
    sibling_obligation_id = next(
        item
        for item in component_obligation_ids
        if item != target_obligation_id
    )
    prior_ledger = captured_gap["evidence_ledger_projection"]
    prior_sibling_requirements = [
        deepcopy(item)
        for item in prior_ledger["source_requirements"]
        if item.get("source_obligation_id") == sibling_obligation_id
        and item.get("status") == "satisfied"
    ]
    assert prior_sibling_requirements
    prior_sibling_ids = {
        item["requirement_id"] for item in prior_sibling_requirements
    }
    prior_sibling_links = [
        deepcopy(item)
        for item in prior_ledger["requirement_links"]
        if item.get("requirement_id") in prior_sibling_ids
    ]
    assert prior_sibling_links
    prior_coverage = deepcopy(
        captured_gap["component_coverage_history"][-1]
    )

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    current_sibling_requirements = [
        item
        for item in ledger["source_requirements"]
        if item.get("requirement_id") in prior_sibling_ids
    ]
    assert [
        {
            key: value
            for key, value in item.items()
            if key != "linked_candidate_ids"
        }
        for item in current_sibling_requirements
    ] == [
        {
            key: value
            for key, value in item.items()
            if key != "linked_candidate_ids"
        }
        for item in prior_sibling_requirements
    ]
    assert [
        item
        for item in ledger["requirement_links"]
        if item.get("requirement_id") in prior_sibling_ids
    ] == prior_sibling_links
    assert kernel.state.component_coverage_history[0] == prior_coverage
    terminal_coverage_ref = terminal["component_coverage_ref"]
    assert terminal_coverage_ref.get("coverage_record_id"), (
        terminal_coverage_ref
    )
    matching_terminal_coverage = [
        item
        for item in kernel.state.component_coverage_history
        if item.get("coverage_record_id")
        == terminal_coverage_ref["coverage_record_id"]
        and item.get("coverage_record_digest")
        == terminal_coverage_ref["coverage_record_digest"]
    ]
    assert len(matching_terminal_coverage) == 1, {
        "terminal_coverage_ref": terminal_coverage_ref,
        "coverage_history_refs": [
            {
                "coverage_record_id": item.get("coverage_record_id"),
                "coverage_record_digest": item.get(
                    "coverage_record_digest"
                ),
            }
            for item in kernel.state.component_coverage_history
        ],
    }
    coverage = matching_terminal_coverage[0]
    target_requirement_ids = coverage["evidence_ledger_binding"][
        "source_requirement_ids"
    ]
    recovered_candidate_ids = {
        item["evidence_ref_id"]
        for item in kernel.state.projections[
            "multicomponent_component_admission"
        ]["component_admission_refs"][-1]["evidence_refs"]
    }
    assert len(target_requirement_ids) == 1, {
        "target_obligation_id": target_obligation_id,
        "target_requirement_ids": target_requirement_ids,
        "recovered_candidate_ids": recovered_candidate_ids,
        "recovered_candidate_links": [
            item
            for item in ledger["requirement_links"]
            if item.get("candidate_id") in recovered_candidate_ids
        ],
        "novel_ids": outcome.execution_trace["searchos_slice_a"][
            "existing_gap_recovery"
        ].get("materially_novel_recovery_evidence_ids"),
        "reassessment_evidence_refs": outcome.execution_trace[
            "searchos_slice_a"
        ]["existing_gap_recovery"].get(
            "same_component_reassessment", {}
        ).get("component_admission_ref", {}).get("evidence_refs"),
    }
    assert not prior_sibling_ids.intersection(target_requirement_ids)
    assert not [
        item
        for item in ledger["requirement_links"]
        if item.get("requirement_id") in prior_sibling_ids
        and item.get("candidate_id") in recovered_candidate_ids
    ]
    sufficiency = kernel.state.sufficiency_judgment_projection
    consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assessments = {
        item["source_obligation_id"]: item
        for item in consumption[
            "required_source_obligation_assessments"
        ]
    }
    assert assessments[target_obligation_id]["status"] == "satisfied"
    assert assessments[sibling_obligation_id]["status"] == "satisfied"
    assert sufficiency["decision"] not in {
        "ready_direct",
        "ready_with_caveats",
    }
    assert sufficiency["final_answer_posture"] == "partial_answer"
    assert sufficiency["contract_fulfilled"] is False
    assert sufficiency["required_obligations_satisfied"] is False
    assert sufficiency["final_answer_allowed"] is True
    assert consumption["terminal_component_ready"] is True
    assert sufficiency_inputs[-1].to_model_payload()[
        "searchos_existing_gap_recovery_terminal_ref"
    ]["terminal_aggregate_id"] == terminal["terminal_aggregate_id"]
    assert harness.author_prompts
    assert "canonically published" in outcome.report


def test_product_existing_gap_exhaustion_reaches_sufficiency_posture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sufficiency_inputs = _capture_sufficiency_inputs(monkeypatch)
    _forbid_post_terminal_blocked_adapter(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=True,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=_official_evidence_rows(),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    terminal = kernel.state.projections["searchos_existing_gap_recovery_terminal"]
    trace = outcome.execution_trace["searchos_slice_a"]
    assert terminal["terminal_status"] == "exhausted_insufficient"
    assert terminal["coverage_gained"] is False
    assert terminal["gap_remains"] is True
    assert terminal["whole_run_lease_status"] == (
        "settled_exhausted_insufficient"
    )
    assert terminal["local_budget_status"]["terminal"] is True
    assert terminal["novelty_exhausted"] is True
    assert (
        terminal[
            "lawful_materially_novel_recovery_purpose_remains"
        ]
        is False
    )
    recovery_slot = kernel.state.searchos_state["slots_by_id"][
        terminal["recovery_slot_ref"]["slot_id"]
    ]
    recovery_cycle = kernel.state.searchos_state[
        "existing_gap_recovery_cycles"
    ][0]
    prior_slot = kernel.state.searchos_state["slots_by_id"][
        recovery_cycle["prior_terminal_slot_ref"]["slot_id"]
    ]
    assert any(
        item.get("same_normalized_url_reused") is True
        for item in recovery_slot["custody_refs"]
    )
    assert {
        item["evidence_ledger_candidate_id"]
        for item in recovery_slot["custody_refs"]
    } <= {
        item["evidence_ledger_candidate_id"]
        for item in prior_slot["custody_refs"]
    }
    assert not kernel.state.component_coverage_history
    assert not kernel.state.semantic_observation_admission_history
    assert sufficiency_inputs
    terminal_input = sufficiency_inputs[-1]
    assert (
        terminal_input.searchos_existing_gap_recovery_terminal_state
        == terminal
    )
    assert terminal_input.to_model_payload()[
        "searchos_existing_gap_recovery_terminal_ref"
    ]["terminal_status"] == "exhausted_insufficient"
    sufficiency = kernel.state.sufficiency_judgment_projection
    assert sufficiency["final_answer_posture"] in {
        "partial_answer",
        "insufficient",
        "blocked",
    }
    consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assert consumption["terminal_status"] == "exhausted_insufficient"
    assert consumption["target_source_truth_status"] != "satisfied"
    assert trace["existing_gap_recovery"]["derived_component_recovery_invoked"] is False
    assert trace["existing_gap_recovery"]["scrutineer_recovery_input_used"] is False
    if sufficiency["final_answer_allowed"]:
        assert sufficiency["final_answer_posture"] == "partial_answer"
        assert harness.author_prompts
        assert "could not produce a supported answer" not in outcome.report
    else:
        assert not harness.author_prompts


def test_recovery_policy_limit_and_exact_replay_do_not_open_more_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_first_gap_basis(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=True,
    )
    _outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=_official_evidence_rows(),
    )
    kernel = harness.run_kernel
    assert kernel is not None
    terminal_state = deepcopy(kernel.state.searchos_state)
    pre_state = captured["state"]
    basis = captured["basis"]
    purpose = build_searchos_materially_novel_recovery_purpose(basis)
    prior_slot_id = basis["prior_terminal_slot_ref"]["slot_id"]
    prior_slot = deepcopy(pre_state["slots_by_id"][prior_slot_id])
    admitted_state, admission = admit_searchos_existing_gap_recovery_cycle(
        state=pre_state,
        gap_basis=basis,
        recovery_purpose=purpose,
    )

    assert len(pre_state["existing_gap_recovery_cycles"]) == 0
    assert admission["work_authorized"] is True
    assert len(admitted_state["existing_gap_recovery_cycles"]) == 1
    assert admitted_state["slots_by_id"][prior_slot_id] == prior_slot
    assert admitted_state["active_slot_ids"][:-1] == pre_state["active_slot_ids"]
    assert admitted_state["required_slot_ids"][:-1] == pre_state["required_slot_ids"]
    assert (
        admitted_state["budget"]["charged_logical_judgment_calls"]
        == pre_state["budget"]["charged_logical_judgment_calls"]
    )

    replayed_state, replay = admit_searchos_existing_gap_recovery_cycle(
        state=admitted_state,
        gap_basis=basis,
        recovery_purpose=purpose,
    )
    assert replayed_state == admitted_state
    assert replay == {
        **replay,
        "status": "already_admitted",
        "exact_replay": True,
        "work_authorized": False,
    }

    recovery_slot = admitted_state["slots_by_id"][
        admission["recovery_slot_ref"]["slot_id"]
    ]
    recovery_component_ref = recovery_slot["component_ref"]
    recovery_contract_ref = admitted_state["answer_contract_ref"]
    target_obligation_id = admission["recovery_slot_ref"][
        "source_obligation_id"
    ]
    sibling_obligation_id = next(
        admitted_state["slots_by_id"][candidate_slot_id]["slot_ref"][
            "source_obligation_id"
        ]
        for candidate_slot_id in pre_state["required_slot_ids"]
        if candidate_slot_id != prior_slot_id
    )

    def exact_shaped_admission(
        *,
        coverage_component_id: str,
        coverage_obligation_id: str,
    ) -> dict[str, Any]:
        candidate_id = "candidate:recovery-finalization-proof"
        requirement_id = "requirement:recovery-finalization-proof"
        return {
            "admission_status": "admitted",
            "component_id": recovery_component_ref["component_id"],
            "component_revision": recovery_component_ref[
                "component_revision"
            ],
            "component_digest": recovery_component_ref[
                "component_digest"
            ],
            "accepted_contract_version": recovery_contract_ref[
                "contract_version"
            ],
            "accepted_contract_digest": recovery_contract_ref[
                "answer_contract_digest"
            ],
            "searchos_recovery_cycle_ref": admission["cycle_ref"],
            "evidence_refs": [{"evidence_ref_id": candidate_id}],
            "component_coverage_ref": {
                "coverage_record_id": "coverage:recovery-finalization-proof",
                "coverage_record_digest": "d" * 64,
                "coverage_state": "satisfied",
                "answer_component_id": coverage_component_id,
                "component_revision": recovery_component_ref[
                    "component_revision"
                ],
                "component_digest": recovery_component_ref[
                    "component_digest"
                ],
                "accepted_contract_version": recovery_contract_ref[
                    "contract_version"
                ],
                "accepted_contract_digest": recovery_contract_ref[
                    "answer_contract_digest"
                ],
                "source_requirement_ids": [requirement_id],
                "source_obligation_ids": [coverage_obligation_id],
                "candidate_ids": [candidate_id],
                "owned_requirement_candidate_refs": [
                    {
                        "requirement_id": requirement_id,
                        "source_obligation_id": (
                            coverage_obligation_id
                        ),
                        "candidate_id": candidate_id,
                        "link_status": "accepted",
                    }
                ],
            },
        }

    for foreign_or_sibling in (
        exact_shaped_admission(
            coverage_component_id="component:foreign",
            coverage_obligation_id=target_obligation_id,
        ),
        exact_shaped_admission(
            coverage_component_id=recovery_component_ref[
                "component_id"
            ],
            coverage_obligation_id=sibling_obligation_id,
        ),
    ):
        _failed_state, failed_terminal = (
            finalize_searchos_existing_gap_recovery_cycle(
                state=deepcopy(admitted_state),
                cycle_ref=admission["cycle_ref"],
                component_admission_ref=foreign_or_sibling,
            )
        )
        assert (
            failed_terminal["terminal_status"]
            == "exhausted_insufficient"
        )
        assert failed_terminal["terminal_blocker"][
            "blocker_class"
        ] == "validation"
        assert failed_terminal["component_admission_ref"] == {}
        assert failed_terminal["component_coverage_ref"] == {}

    _recovered_state, exact_terminal = (
        finalize_searchos_existing_gap_recovery_cycle(
            state=deepcopy(admitted_state),
            cycle_ref=admission["cycle_ref"],
            component_admission_ref=exact_shaped_admission(
                coverage_component_id=recovery_component_ref[
                    "component_id"
                ],
                coverage_obligation_id=target_obligation_id,
            ),
        )
    )
    assert exact_terminal["terminal_status"] == "recovered"

    terminal_replay_state, terminal_replay = admit_searchos_existing_gap_recovery_cycle(
        state=terminal_state,
        gap_basis=basis,
        recovery_purpose=purpose,
    )
    assert terminal_replay_state == terminal_state
    assert terminal_replay["work_authorized"] is False
    assert terminal_replay["exact_replay"] is True

    active_kernel = RunKernel(deepcopy(kernel.state))
    active_kernel.state.searchos_state = deepcopy(admitted_state)
    before_active_run_state = deepcopy(active_kernel.state)
    active_replay = (
        active_kernel.authorize_searchos_existing_gap_recovery_admission(
            gap_basis=basis,
            recovery_purpose=purpose,
        )
    )
    assert isinstance(active_replay, Mapping)
    assert active_replay["exact_replay"] is True
    assert active_replay["work_authorized"] is False
    assert active_kernel.state == before_active_run_state

    before_kernel_replay_state = deepcopy(kernel.state)
    before_sufficiency = deepcopy(
        kernel.state.sufficiency_judgment_projection
    )
    before_ledger = deepcopy(
        kernel.state.evidence_ledger.to_projection().to_dict()
    )
    before_search_calls = len(harness.search_calls)
    before_read_calls = len(harness.read_transport_calls)
    before_read_assessments = len(harness.read_assessment_calls)
    before_model_calls = len(harness.model_calls)
    before_admission = deepcopy(
        kernel.state.projections["multicomponent_component_admission"]
    )
    before_semantic_admission_count = len(
        kernel.state.semantic_observation_admission_history
    )
    before_coverage = deepcopy(kernel.state.component_coverage_history)
    before_sufficiency_count = len(
        kernel.state.sufficiency_judgment_history
    )
    before_fap = deepcopy(kernel.state.final_answer_packet_history)
    before_author_calls = len(harness.author_prompts)
    replay = (
        kernel.authorize_searchos_existing_gap_recovery_admission(
            gap_basis=basis,
            recovery_purpose=purpose,
        )
    )
    assert isinstance(replay, Mapping)
    assert replay["exact_replay"] is True
    assert replay["work_authorized"] is False
    assert kernel.state == before_kernel_replay_state
    assert kernel.state.sufficiency_judgment_projection == before_sufficiency
    assert (
        kernel.state.evidence_ledger.to_projection().to_dict()
        == before_ledger
    )
    assert len(harness.search_calls) == before_search_calls
    assert len(harness.read_transport_calls) == before_read_calls
    assert len(harness.read_assessment_calls) == before_read_assessments
    assert len(harness.model_calls) == before_model_calls
    assert (
        kernel.state.projections["multicomponent_component_admission"]
        == before_admission
    )
    assert len(
        kernel.state.semantic_observation_admission_history
    ) == before_semantic_admission_count
    assert kernel.state.component_coverage_history == before_coverage
    assert len(
        kernel.state.sufficiency_judgment_history
    ) == before_sufficiency_count
    assert kernel.state.final_answer_packet_history == before_fap
    assert len(harness.author_prompts) == before_author_calls

    alternate_gap_kind = (
        "same_component_source_obligation_not_covered"
        if basis["gap_kind"] == "same_component_semantic_admission_not_supported"
        else "same_component_semantic_admission_not_supported"
    )
    stale_second_basis = _reenvelope_gap_basis(
        basis,
        gap_kind=alternate_gap_kind,
    )
    stale_second_purpose = build_searchos_materially_novel_recovery_purpose(stale_second_basis)
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="stale against canonical SearchOS state",
    ):
        admit_searchos_existing_gap_recovery_cycle(
            state=admitted_state,
            gap_basis=stale_second_basis,
            recovery_purpose=stale_second_purpose,
        )

    other_slot_id = next(
        slot_id
        for slot_id in pre_state["required_slot_ids"]
        if slot_id != prior_slot_id
    )
    other_gap_basis = build_searchos_existing_gap_basis(
        state=pre_state,
        slot_id=other_slot_id,
        component_admission_projection=(
            captured["component_admission_projection"]
        ),
        component_coverage_history=(
            captured["component_coverage_history"]
        ),
        evidence_ledger_projection=(
            captured["evidence_ledger_projection"]
        ),
    )
    assert (
        other_gap_basis["prior_terminal_slot_ref"][
            "source_obligation_id"
        ]
        != basis["prior_terminal_slot_ref"]["source_obligation_id"]
    )
    limit_plus_one_basis = _reenvelope_gap_basis(
        other_gap_basis,
        searchos_state_ref={
            "state_id": admitted_state["state_id"],
            "state_digest": admitted_state["state_digest"],
        },
    )
    limit_plus_one_purpose = build_searchos_materially_novel_recovery_purpose(limit_plus_one_basis)
    assert (
        limit_plus_one_purpose["recovery_purpose_id"]
        != purpose["recovery_purpose_id"]
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="cycle limit exhausted",
    ):
        admit_searchos_existing_gap_recovery_cycle(
            state=admitted_state,
            gap_basis=limit_plus_one_basis,
            recovery_purpose=limit_plus_one_purpose,
        )

    assert len(terminal_state["existing_gap_recovery_cycles"]) == MAXIMUM_EXISTING_GAP_RECOVERY_CYCLES
    assert terminal_state["active_existing_gap_recovery_cycle_ref"] == {}
    assert (
        terminal_state["existing_gap_recovery_terminal_aggregate"]["further_existing_gap_recovery_authorized"] is False
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="absent or terminal|exact active cycle",
    ):
        validate_active_searchos_recovery_cycle_ref(
            terminal_state,
            terminal_replay["cycle_ref"],
        )
    with pytest.raises(SearchOSExistingGapRecoveryError):
        finalize_searchos_existing_gap_recovery_cycle(
            state=terminal_state,
            cycle_ref=terminal_replay["cycle_ref"],
            component_admission_ref=None,
        )


def test_gap_eligibility_and_novelty_are_exact_and_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_first_gap_basis(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=True,
    )
    run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=_official_evidence_rows(),
    )

    assert "basis" in captured, captured.get("error")
    state = captured["state"]
    slot_id = captured["slot_id"]
    basis = captured["basis"]
    projection = captured["component_admission_projection"]
    ledger = captured["evidence_ledger_projection"]
    purpose = build_searchos_materially_novel_recovery_purpose(basis)

    nonterminal = deepcopy(state)
    nonterminal_slot = deepcopy(nonterminal["slots_by_id"][slot_id])
    nonterminal_slot["posture"] = "active_unjudged"
    nonterminal_slot.pop("slot_state_digest", None)
    nonterminal_slot["slot_state_digest"] = _digest(nonterminal_slot)
    nonterminal["slots_by_id"][slot_id] = nonterminal_slot
    nonterminal = _refresh_state(nonterminal)
    with pytest.raises(ValueError):
        build_searchos_existing_gap_basis(
            state=nonterminal,
            slot_id=slot_id,
            component_admission_projection=projection,
            component_coverage_history=[],
            evidence_ledger_projection=ledger,
        )

    optional_basis = _reenvelope_gap_basis(
        basis,
        requirement_posture="optional",
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="broadens recovery authority",
    ):
        validate_searchos_existing_gap_basis(optional_basis)

    stale_or_foreign_coverage = [
        {
            "answer_component_id": basis["prior_terminal_slot_ref"]["component_id"],
            "coverage_state": "unsatisfied",
        }
    ]
    foreign_basis = build_searchos_existing_gap_basis(
        state=state,
        slot_id=slot_id,
        component_admission_projection=projection,
        component_coverage_history=stale_or_foreign_coverage,
        evidence_ledger_projection=ledger,
    )
    assert (
        foreign_basis["coverage_basis"]["basis_kind"]
        == "explicit_canonical_absence"
    )

    slot = state["slots_by_id"][slot_id]
    current_coverage = {
        "canonical_state": True,
        "stale": False,
        "answer_component_id": basis["prior_terminal_slot_ref"][
            "component_id"
        ],
        "accepted_contract_version": state["answer_contract_ref"][
            "contract_version"
        ],
        "accepted_contract_digest": state["answer_contract_ref"][
            "answer_contract_digest"
        ],
        "component_revision": slot["component_ref"][
            "component_revision"
        ],
        "component_digest": slot["component_ref"][
            "component_digest"
        ],
        "source_obligation_ids": [
            basis["prior_terminal_slot_ref"]["source_obligation_id"]
        ],
        "coverage_state": "unsatisfied",
        "evidence_ledger_binding": {"source_requirement_ids": []},
    }
    for stale_lineage_coverage in (
        {
            **current_coverage,
            "coverage_record_id": "coverage:stale-contract",
            "coverage_record_digest": "b" * 64,
            "accepted_contract_digest": "f" * 64,
        },
        {
            **current_coverage,
            "coverage_record_id": "coverage:stale-component",
            "coverage_record_digest": "c" * 64,
            "component_revision": "stale-revision",
        },
    ):
        stale_lineage_basis = build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=projection,
            component_coverage_history=[stale_lineage_coverage],
            evidence_ledger_projection=ledger,
        )
        assert stale_lineage_basis["coverage_basis"][
            "basis_kind"
        ] == "explicit_canonical_absence"

    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="competing current target coverage",
    ):
        build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=projection,
            component_coverage_history=[
                {
                    **current_coverage,
                    "coverage_record_id": "coverage:current:1",
                    "coverage_record_digest": "1" * 64,
                },
                {
                    **current_coverage,
                    "coverage_record_id": "coverage:current:2",
                    "coverage_record_digest": "2" * 64,
                },
            ],
            evidence_ledger_projection=ledger,
        )

    satisfied_projection = deepcopy(projection)
    satisfied_projection["component_admission_refs"][-1]["admission_status"] = "admitted"
    satisfied_coverage = [
        {
            **current_coverage,
            "coverage_record_id": "coverage:component_1",
            "coverage_record_digest": "a" * 64,
            "coverage_state": "satisfied",
            "evidence_ledger_binding": {"source_requirement_ids": ["requirement:official_current"]},
        }
    ]
    satisfied_ledger = deepcopy(ledger)
    satisfied_ledger.setdefault("source_requirements", []).append(
        {
            "requirement_id": "requirement:official_current",
            "requirement_kind": "official_current",
            "source_obligation_id": basis["prior_terminal_slot_ref"][
                "source_obligation_id"
            ],
            "component_id": basis["prior_terminal_slot_ref"][
                "component_id"
            ],
            "status": "satisfied",
        }
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="cannot reopen a satisfied source obligation",
    ):
        build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=satisfied_projection,
            component_coverage_history=satisfied_coverage,
            evidence_ledger_projection=satisfied_ledger,
        )

    missing_role_projection = deepcopy(projection)
    missing_role_projection["component_admission_refs"][-1]["dprime_validation_ref"] = {}
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="role provenance",
    ):
        build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=missing_role_projection,
            component_coverage_history=[],
            evidence_ledger_projection=ledger,
        )

    stale_component_projection = deepcopy(projection)
    stale_component_projection["component_admission_refs"][-1][
        "component_revision"
    ] = "stale-revision"
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="role provenance",
    ):
        build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=stale_component_projection,
            component_coverage_history=[],
            evidence_ledger_projection=ledger,
        )

    stale_contract_projection = deepcopy(projection)
    stale_contract_projection["component_admission_refs"][-1][
        "accepted_contract_digest"
    ] = "f" * 64
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="role provenance",
    ):
        build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=stale_contract_projection,
            component_coverage_history=[],
            evidence_ledger_projection=ledger,
        )

    source_identity_purpose = _reenvelope_recovery_purpose(
        purpose,
        physical_source_identity_establishes_novelty=True,
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="non-semantic novelty basis",
    ):
        validate_searchos_recovery_purpose(source_identity_purpose)

    no_delta_purpose = _reenvelope_recovery_purpose(
        purpose,
        intended_evidence_delta={
            "delta_kind": "same_source_rewording",
            "component_id": basis["prior_terminal_slot_ref"]["component_id"],
            "source_obligation_id": basis["prior_terminal_slot_ref"]["source_obligation_id"],
        },
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="materially novel evidence delta",
    ):
        validate_searchos_recovery_purpose(no_delta_purpose)

    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="absent or terminal|exact active cycle",
    ):
        validate_active_searchos_recovery_cycle_ref(state, {})


def test_recovery_model_failure_exhausts_without_author_or_role_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_first_gap_basis(monkeypatch)
    sufficiency_inputs = _capture_sufficiency_inputs(monkeypatch)
    _forbid_post_terminal_blocked_adapter(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=False,
    )
    prior = PostRetirementOrdinaryPipelineHarness.ask_model

    def fail_recovery_judgment(
        self: PostRetirementOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if system_prompt == SEARCHOS_JUDGMENT_SYSTEM_PROMPT and captured:
            raise AssertionError("offline recovery SearchOS model failure")
        return prior(self, prompt, system_prompt, **kwargs)

    monkeypatch.setattr(
        PostRetirementOrdinaryPipelineHarness,
        "ask_model",
        fail_recovery_judgment,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=_official_evidence_rows(),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    terminal = kernel.state.projections["searchos_existing_gap_recovery_terminal"]
    role_system_prompts = [item["system_prompt"] for item in harness.model_calls]
    assert terminal["terminal_status"] == "exhausted_insufficient"
    assert terminal["expenditure"]["failed_logical_judgment_calls"] > 0
    assert terminal["terminal_blocker"]["blocker_class"] == (
        "provider_or_acquisition"
    )
    assert "model" in terminal["terminal_blocker"]["reason_code"]
    assert sufficiency_inputs
    assert (
        sufficiency_inputs[-1]
        .searchos_existing_gap_recovery_terminal_state
        == terminal
    )
    sufficiency = kernel.state.sufficiency_judgment_projection
    assert sufficiency["final_answer_posture"] == "blocked"
    assert sufficiency["final_answer_allowed"] is False
    consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assert consumption["terminal_blocker"] == terminal[
        "terminal_blocker"
    ]
    assert any(
        "provider_or_acquisition" in reason
        for reason in sufficiency["readiness_reasons"]
    )
    assert role_system_prompts.count(ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]) == 1
    assert ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER] not in role_system_prompts
    assert not harness.author_prompts
    assert "could not produce a supported answer" in outcome.report


def test_recovery_records_are_ref_only_and_boundary_b_is_static_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_first_gap_basis(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=True,
    )
    _outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=_official_evidence_rows(),
    )
    kernel = harness.run_kernel
    assert kernel is not None
    purpose = build_searchos_materially_novel_recovery_purpose(captured["basis"])
    terminal = kernel.state.projections["searchos_existing_gap_recovery_terminal"]
    cycle = kernel.state.searchos_state["existing_gap_recovery_cycles"][0]
    serialized = json.dumps(
        {
            "basis": captured["basis"],
            "purpose": purpose,
            "cycle": cycle,
            "terminal": terminal,
        },
        sort_keys=True,
    ).casefold()
    assert "http://" not in serialized
    assert "https://" not in serialized
    assert "raw_provider_payload" not in serialized
    assert "raw_model_response" not in serialized
    assert "system_prompt" not in serialized
    assert '"raw_content_retained": true' not in serialized

    same_component_source = inspect.getsource(
        multicomponent_runtime.execute_searchos_same_component_reassessment_from_scope
    )
    for forbidden in (
        "_begin_scheduler_dynamic_recovery(",
        "ROLE_SCRUTINEER",
        "execute_specialist",
        "component_work_graph",
    ):
        assert forbidden not in same_component_source
    retained_source = inspect.getsource(multicomponent_runtime._begin_scheduler_dynamic_recovery)
    assert "recovery_authorization" in retained_source
    pipeline_source = inspect.getsource(
        pipeline_orchestrator._run_pipeline_inner
    )
    assert (
        "if searchos_slice_a_active:\n"
        "        authorized_spine_action = None\n"
        "        source_class_recovery_execution"
    ) in pipeline_source
    assert (
        "component_gap_recovery_result = None\n"
        "    if not searchos_slice_a_active:\n"
        "        recovery_policy"
    ) in pipeline_source
    assert (
        "if not searchos_slice_a_active\n"
        "        else None"
    ) in pipeline_source


def test_consolidated_exact_ownership_matrix_spans_ledger_coverage_and_slot() -> None:
    component_a = "component:a"
    component_b = "component:b"
    obligation_a = "obligation:a"
    obligation_sibling = "obligation:a:sibling"
    requirement_id = "requirement:shared-family:a"
    candidate_id = "candidate:shared-family"
    projection = {
        "candidate_records": [
            {
                "candidate_id": candidate_id,
                "fact_disposition": "accepted",
            }
        ],
        "custody_records": [
            {
                "candidate_id": candidate_id,
                "record_kind": "fact",
                "disposition": "accepted",
            }
        ],
        "source_requirements": [
            {
                "requirement_id": requirement_id,
                "requirement_kind": "shared_family",
                "component_id": component_a,
                "source_obligation_id": obligation_a,
                "status": "satisfied",
            }
        ],
        "requirement_links": [
            {
                "requirement_id": requirement_id,
                "candidate_id": candidate_id,
                "link_status": "accepted",
            }
        ],
    }

    assert source_requirement_ids_for_component_candidate(
        projection,
        evidence_ref_id=candidate_id,
        component_id=component_a,
        source_obligation_candidate_ids=[obligation_a],
    ) == (requirement_id,)
    for foreign_owner in (
        {
            "component_id": component_b,
            "source_obligation_candidate_ids": [obligation_a],
        },
        {
            "component_id": component_a,
            "source_obligation_candidate_ids": [obligation_sibling],
        },
    ):
        assert not source_requirement_ids_for_component_candidate(
            projection,
            evidence_ref_id=candidate_id,
            **foreign_owner,
        )
    ambiguous_projection = deepcopy(projection)
    ambiguous_projection["source_requirements"].append(
        {
            **projection["source_requirements"][0],
            "component_id": component_b,
        }
    )
    assert not source_requirement_ids_for_component_candidate(
        ambiguous_projection,
        evidence_ref_id=candidate_id,
        component_id=component_a,
        source_obligation_candidate_ids=[obligation_a],
    )
    implicit_projection = deepcopy(projection)
    implicit_projection["requirement_links"][0]["link_reason"] = (
        "selected_candidate_matches_existing_requirement"
    )
    assert not source_requirement_ids_for_component_candidate(
        implicit_projection,
        evidence_ref_id=candidate_id,
        component_id=component_a,
        source_obligation_candidate_ids=[obligation_a],
    )

    coverage = {
        "coverage_state": "satisfied",
        "answer_component_id": component_a,
        "source_obligation_status": "satisfied",
        "source_obligation_ids": [obligation_a],
        "content_reference_bindings": [
            {"evidence_ref_id": candidate_id}
        ],
        "evidence_ledger_binding": {
            "source_requirement_ids": [requirement_id]
        },
    }
    accepted_component = {
        "component_id": component_a,
        "source_obligation_candidate_ids": [obligation_a],
    }
    assert not ledger_qualification_blockers_for_satisfied_coverage(
        coverage=coverage,
        evidence_ledger_projection=projection,
        accepted_component=accepted_component,
    )
    assert "ledger_candidate_exact_accepted_link_missing" in {
        item["code"]
        for item in ledger_qualification_blockers_for_satisfied_coverage(
            coverage=coverage,
            evidence_ledger_projection=implicit_projection,
            accepted_component=accepted_component,
        )
    }
    foreign_component_codes = {
        item["code"]
        for item in ledger_qualification_blockers_for_satisfied_coverage(
            coverage={**coverage, "answer_component_id": component_b},
            evidence_ledger_projection=projection,
            accepted_component={
                **accepted_component,
                "component_id": component_b,
            },
        )
    }
    assert "ledger_source_requirement_foreign_component" in foreign_component_codes
    sibling_obligation_codes = {
        item["code"]
        for item in ledger_qualification_blockers_for_satisfied_coverage(
            coverage={
                **coverage,
                "source_obligation_ids": [obligation_sibling],
            },
            evidence_ledger_projection=projection,
            accepted_component={
                **accepted_component,
                "source_obligation_candidate_ids": [obligation_sibling],
            },
        )
    }
    assert "ledger_source_requirement_foreign_obligation" in sibling_obligation_codes

    component_ref = {
        "component_id": component_a,
        "component_revision": 1,
        "component_digest": "c" * 64,
    }
    contract_ref = {
        "contract_version": 1,
        "answer_contract_digest": "a" * 64,
    }
    exact_coverage_ref = {
        **coverage,
        "coverage_record_id": "coverage:a",
        "coverage_record_digest": "d" * 64,
        **component_ref,
        "accepted_contract_version": contract_ref["contract_version"],
        "accepted_contract_digest": contract_ref["answer_contract_digest"],
        "source_requirement_ids": [requirement_id],
        "candidate_ids": [candidate_id],
        "owned_requirement_candidate_refs": [
            {
                "requirement_id": requirement_id,
                "source_obligation_id": obligation_a,
                "candidate_id": candidate_id,
                "link_status": "accepted",
            }
        ],
    }
    admission = {"component_coverage_ref": exact_coverage_ref}
    exact_slot = {
        "component_ref": component_ref,
        "slot_ref": {
            "component_id": component_a,
            "source_obligation_id": obligation_a,
        },
    }
    sibling_slot = {
        **exact_slot,
        "slot_ref": {
            **exact_slot["slot_ref"],
            "source_obligation_id": obligation_sibling,
        },
    }
    assert _coverage_ref_matches_slot(admission=admission, slot=exact_slot)
    assert not _coverage_ref_matches_slot(
        admission=admission,
        slot=sibling_slot,
    )
    assert _coverage_ref_matches_contract_and_candidates(
        coverage_ref=exact_coverage_ref,
        answer_contract_ref=contract_ref,
        consumed_candidate_ids={candidate_id},
    )
    assert _exact_recovery_coverage_chain(
        coverage_ref=exact_coverage_ref,
        component_ref=component_ref,
        answer_contract_ref=contract_ref,
        source_obligation_id=obligation_a,
        consumed_candidate_ids=[candidate_id],
    )
    assert not _exact_recovery_coverage_chain(
        coverage_ref=exact_coverage_ref,
        component_ref=component_ref,
        answer_contract_ref=contract_ref,
        source_obligation_id=obligation_sibling,
        consumed_candidate_ids=[candidate_id],
    )
