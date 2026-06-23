from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.contract_amendment_record import (
    CONTRACT_AMENDMENT_RECORD_SCHEMA_VERSION,
    AffectedComponentRef,
    AmendmentOperation,
    AmendmentOperationKind,
    AmendmentTriggerRefs,
    ContractAmendmentRecord,
    CoverageInvalidationCandidateRef,
    MaterialityPosture,
    ModePermissionPosture,
    MonotonicityPosture,
    ProposalDisposition,
    StaleCoverageCandidatePosture,
    UserConfirmationPosture,
    WeakeningPosture,
)
from core.semantic_contract_foundation import (
    AnswerComponentContract,
    Materiality,
    QuestionMeaningRecord,
    RequirementPosture,
    ResolverKind,
    SemanticSlot,
    SemanticSlotKind,
    SemanticSlotStatus,
    SupportKind,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "contract_amendment_record.py"


def _slot() -> SemanticSlot:
    return SemanticSlot(
        slot_id="slot:time-period",
        slot_kind=SemanticSlotKind.TIME_PERIOD,
        status=SemanticSlotStatus.EXPLICIT,
        selected_value="2026",
        materiality=Materiality.MATERIAL,
    )


def _component(
    *,
    component_id: str = "component:taxable-maximum",
    component_revision: str = "1",
) -> AnswerComponentContract:
    return AnswerComponentContract(
        component_id=component_id,
        component_revision=component_revision,
        user_facing_label="Taxable maximum",
        user_facing_question="What is the Social Security taxable maximum wage base for 2026?",
        requirement_posture=RequirementPosture.REQUIRED,
        acceptance_criteria=("state the bounded value", "bind it to official evidence"),
        semantic_slot_ids=("slot:time-period",),
        source_obligation_candidate_ids=("obligation:official-current",),
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
        mandatory_caveats=("Currentness remains evidence-bound.",),
        prohibited_upgrades=("Do not replace official value with estimate.",),
        materiality=Materiality.MATERIAL,
    )


def _qmr(component: AnswerComponentContract | None = None) -> QuestionMeaningRecord:
    component = component or _component()
    return QuestionMeaningRecord(
        record_id="qmr:ssa-taxable-maximum",
        run_id="run:semantic-offline",
        request_id="request:1",
        request_digest="request-digest-001",
        requested_mode="balanced",
        resolver_kind=ResolverKind.PASSIVE_PROPOSAL,
        resolver_version="ag-sem-04-test",
        intent="Answer the current official taxable maximum question.",
        requested_output="Concise answer with official support.",
        semantic_slots=(_slot(),),
        answer_components=(component,),
    ).require_valid()


def _affected_component(component: AnswerComponentContract | None = None) -> AffectedComponentRef:
    component = component or _component()
    return AffectedComponentRef(
        component_id=component.component_id,
        component_revision=component.component_revision,
        component_digest=component.component_digest or "",
    )


def _trigger_refs() -> AmendmentTriggerRefs:
    return AmendmentTriggerRefs(
        semantic_observation_refs=("observation:missing-currentness",),
        evidence_refs=("evidence:ssa-notice",),
        sanitized_content_refs=("content:ssa-wage-base",),
        component_coverage_refs=("coverage:taxable-maximum",),
        gap_refs=("gap:currentness",),
    )


def _operation(
    *,
    operation_kind: AmendmentOperationKind = AmendmentOperationKind.ADD_CAVEAT,
    material_slot_kinds: tuple[str, ...] = (),
    payload: dict[str, object] | None = None,
    before_payload: dict[str, object] | None = None,
    after_payload: dict[str, object] | None = None,
    user_authority_ref: str | None = None,
    notes: tuple[str, ...] = (),
    revision_changed: bool = False,
    digest_changed: bool = False,
) -> AmendmentOperation:
    return AmendmentOperation(
        operation_id=f"operation:{operation_kind.value}",
        operation_kind=operation_kind,
        before_payload=before_payload if before_payload is not None else {},
        after_payload=after_payload if after_payload is not None else {},
        operation_payload=payload if payload is not None else {"typed_change": operation_kind.value},
        material_slot_kinds=material_slot_kinds,
        component_revision_changed=revision_changed,
        component_digest_changed=digest_changed,
        user_authority_ref=user_authority_ref,
        notes=notes,
        metadata={"safe_note": "kept", "raw_provider_payload": "SENTINEL_PROVIDER"},
    )


def _coverage_candidate() -> CoverageInvalidationCandidateRef:
    return CoverageInvalidationCandidateRef(
        coverage_record_id="coverage:taxable-maximum",
        coverage_record_digest="coverage-digest-001",
        answer_component_id="component:taxable-maximum",
        reason="component revision or material slot changed",
    )


def _record(
    *,
    component: AnswerComponentContract | None = None,
    parent_contract_version: str | None = None,
    parent_contract_digest: str | None = None,
    trigger_refs: AmendmentTriggerRefs | None = None,
    operations: tuple[AmendmentOperation, ...] | None = None,
    affected_components: tuple[AffectedComponentRef, ...] | None = None,
    materiality: MaterialityPosture = MaterialityPosture.NON_MATERIAL,
    confirmation: UserConfirmationPosture = UserConfirmationPosture.NOT_REQUIRED,
    monotonicity: MonotonicityPosture = MonotonicityPosture.PRESERVES,
    weakening: WeakeningPosture = WeakeningPosture.NONE,
    disposition: ProposalDisposition = ProposalDisposition.PROPOSED,
    user_authority_ref: str | None = None,
    coverage_candidates: tuple[CoverageInvalidationCandidateRef, ...] = (),
    stale_posture: StaleCoverageCandidatePosture = StaleCoverageCandidatePosture.NOT_APPLICABLE,
) -> ContractAmendmentRecord:
    component = component or _component()
    qmr = _qmr(component)
    return ContractAmendmentRecord(
        amendment_record_id="amendment:ssa-currentness-caveat",
        run_id="run:semantic-offline",
        request_id="request:1",
        request_digest="request-digest-001",
        parent_contract_version=parent_contract_version
        if parent_contract_version is not None
        else qmr.contract_lineage.contract_version,
        parent_contract_digest=parent_contract_digest if parent_contract_digest is not None else qmr.record_digest,
        parent_question_meaning_record_id=qmr.record_id,
        parent_question_meaning_record_digest=qmr.record_digest,
        accepted_contract_ref="contract:ssa-taxable-maximum:accepted",
        trigger_refs=trigger_refs if trigger_refs is not None else _trigger_refs(),
        affected_component_refs=affected_components
        if affected_components is not None
        else (_affected_component(component),),
        operations=operations
        if operations is not None
        else (
            _operation(
                operation_kind=AmendmentOperationKind.ADD_CAVEAT,
                payload={"caveat": "Currentness remains evidence-bound."},
            ),
        ),
        materiality=materiality,
        user_confirmation_posture=confirmation,
        monotonicity=monotonicity,
        weakening_posture=weakening,
        mode_permission_posture=ModePermissionPosture.WITHIN_MODE,
        disposition=disposition,
        user_authority_ref=user_authority_ref,
        candidate_new_contract_version="0.2-candidate",
        candidate_new_contract_digest="candidate-contract-digest-001",
        candidate_invalidated_coverage_refs=coverage_candidates,
        stale_coverage_candidate_posture=stale_posture,
        required_caveats=("Currentness remains evidence-bound.",),
        prohibited_upgrades=("Do not promote the candidate amendment to accepted authority.",),
        metadata={"safe_review_note": "passive amendment", "raw_prompt": "SENTINEL_RAW_PROMPT"},
    )


def test_happy_path_passive_non_material_caveat_amendment_is_valid_and_deterministic() -> None:
    first = _record().require_valid()
    second = _record().require_valid()
    payload = first.to_dict()

    assert payload["schema_version"] == CONTRACT_AMENDMENT_RECORD_SCHEMA_VERSION
    assert payload["parent_contract_version"]
    assert payload["parent_contract_digest"]
    assert payload["operations"][0]["operation_kind"] == "add_caveat"
    assert payload["materiality"] == "non_material"
    assert payload["monotonicity"] == "preserves"
    assert payload["passive"] is True
    assert payload["canonical_state"] is False
    assert payload["accepted_authority"] is False
    assert payload["contract_mutation_applied"] is False
    assert payload["coverage_invalidation_applied"] is False
    assert payload["runtime_behavior_changed"] is False
    assert payload["candidate_contract_is_canonical"] is False
    assert payload["record_digest"] == first.record_digest
    assert first.record_digest == second.record_digest
    assert json.dumps(payload, sort_keys=True) == json.dumps(second.to_dict(), sort_keys=True)


def test_typed_operation_is_required_and_prose_only_amendment_fails() -> None:
    invalid = _record(
        operations=(
            _operation(
                payload={},
                before_payload={},
                after_payload={},
                notes=("Only prose, no typed before/after or operation payload.",),
            ),
        )
    )

    assert any("requires typed before/after or payload" in error for error in invalid.validate().errors)


@pytest.mark.parametrize(
    ("version", "digest", "expected"),
    (
        ("", "parent-digest", "parent_contract_version"),
        ("0.1-passive", "", "parent_contract_digest"),
    ),
)
def test_parent_contract_binding_is_required(version: str, digest: str, expected: str) -> None:
    invalid = _record(parent_contract_version=version, parent_contract_digest=digest)

    assert any(expected in error for error in invalid.validate().errors)


def test_trigger_ref_is_required() -> None:
    invalid = _record(trigger_refs=AmendmentTriggerRefs())

    assert any("at least one trigger ref" in error for error in invalid.validate().errors)


def test_material_slot_change_requires_user_confirmation_or_scenario_treatment() -> None:
    invalid = _record(
        operations=(
            _operation(
                operation_kind=AmendmentOperationKind.RESOLVE_SLOT,
                material_slot_kinds=("time_period", "currency_basis"),
                payload={"slot_id": "slot:time-period", "after": "2026 calendar year"},
            ),
        ),
        materiality=MaterialityPosture.MATERIAL,
        confirmation=UserConfirmationPosture.NOT_REQUIRED,
        coverage_candidates=(_coverage_candidate(),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
    )
    valid = _record(
        operations=(
            _operation(
                operation_kind=AmendmentOperationKind.RESOLVE_SLOT,
                material_slot_kinds=("time_period",),
                payload={"slot_id": "slot:time-period", "after": "2026 calendar year"},
            ),
        ),
        materiality=MaterialityPosture.MATERIAL,
        confirmation=UserConfirmationPosture.EXPLICIT_USER_CONFIRMATION,
        coverage_candidates=(_coverage_candidate(),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
    ).require_valid()

    assert any("requires user confirmation" in error for error in invalid.validate().errors)
    assert valid.to_dict()["user_confirmation_posture"] == "explicit_user_confirmation"


def test_weakening_requires_explicit_user_authority_and_is_not_auto_eligible() -> None:
    invalid = _record(
        operations=(
            _operation(
                operation_kind=AmendmentOperationKind.REMOVE_OR_WEAKEN_REQUIREMENT,
                payload={"requirement": "official source obligation", "change": "optional"},
            ),
        ),
        monotonicity=MonotonicityPosture.WEAKENS,
        weakening=WeakeningPosture.WEAKENS_SOURCE_OBLIGATION,
        disposition=ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE,
        coverage_candidates=(_coverage_candidate(),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_INVALIDATION_REQUIRED,
    )
    valid = _record(
        operations=(
            _operation(
                operation_kind=AmendmentOperationKind.REMOVE_OR_WEAKEN_REQUIREMENT,
                payload={"requirement": "official source obligation", "change": "scenario-only"},
            ),
        ),
        confirmation=UserConfirmationPosture.EXPLICIT_USER_AUTHORITY,
        monotonicity=MonotonicityPosture.WEAKENS,
        weakening=WeakeningPosture.WEAKENS_SOURCE_OBLIGATION,
        user_authority_ref="user-authority:scenario-only",
        coverage_candidates=(_coverage_candidate(),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_INVALIDATION_REQUIRED,
    ).require_valid()

    errors = invalid.validate().errors

    assert any("requires explicit user authority" in error for error in errors)
    assert any("cannot be eligible" in error for error in errors)
    assert valid.to_dict()["accepted_authority"] is False


def test_non_material_strengthening_is_allowed_passively() -> None:
    record = _record(
        operations=(
            _operation(
                operation_kind=AmendmentOperationKind.STRENGTHEN_SOURCE_OBLIGATION,
                payload={"source_obligation": "official current source required"},
            ),
        ),
        materiality=MaterialityPosture.NON_MATERIAL,
        monotonicity=MonotonicityPosture.STRENGTHENS,
    ).require_valid()
    payload = record.to_dict()

    assert payload["operations"][0]["operation_kind"] == "strengthen_source_obligation"
    assert payload["materiality"] == "non_material"
    assert payload["monotonicity"] == "strengthens"
    assert payload["passive"] is True
    assert payload["canonical_state"] is False


@pytest.mark.parametrize(
    "operation_kind",
    (
        AmendmentOperationKind.ADD_COMPONENT,
        AmendmentOperationKind.REVISE_COMPONENT,
        AmendmentOperationKind.CHANGE_ANSWER_POSTURE,
    ),
)
def test_component_changing_amendment_requires_affected_component_binding(
    operation_kind: AmendmentOperationKind,
) -> None:
    invalid = _record(
        operations=(
            _operation(
                operation_kind=operation_kind,
                payload={"component_change": operation_kind.value},
            ),
        ),
        affected_components=(),
        coverage_candidates=(_coverage_candidate(),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
    )

    assert any("requires affected component refs" in error for error in invalid.validate().errors)


def test_coverage_invalidation_is_represented_but_not_applied() -> None:
    invalid = _record(
        operations=(
            _operation(
                operation_kind=AmendmentOperationKind.REVISE_COMPONENT,
                payload={"component_change": "revise source obligation wording"},
                revision_changed=True,
                digest_changed=True,
            ),
        ),
        stale_posture=StaleCoverageCandidatePosture.NOT_APPLICABLE,
    )
    valid = _record(
        operations=(
            _operation(
                operation_kind=AmendmentOperationKind.REVISE_COMPONENT,
                payload={"component_change": "revise source obligation wording"},
                revision_changed=True,
                digest_changed=True,
            ),
        ),
        coverage_candidates=(_coverage_candidate(),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
    ).require_valid()
    payload = valid.to_dict()

    assert any("requires candidate stale coverage" in error for error in invalid.validate().errors)
    assert payload["candidate_invalidated_coverage_refs"][0]["represented_only"] is True
    assert payload["candidate_invalidated_coverage_refs"][0]["coverage_invalidation_applied"] is False
    assert payload["coverage_invalidation_applied"] is False


def test_required_caveats_and_prohibited_upgrades_survive_serialization() -> None:
    payload = _record().require_valid().to_dict()

    assert payload["required_caveats"] == ["Currentness remains evidence-bound."]
    assert payload["prohibited_upgrades"] == [
        "Do not promote the candidate amendment to accepted authority.",
    ]


def test_sensitive_metadata_is_scrubbed() -> None:
    encoded = json.dumps(_record().require_valid().to_dict(), sort_keys=True)

    assert "safe_review_note" in encoded
    assert "safe_note" in encoded
    assert "SENTINEL_RAW_PROMPT" not in encoded
    assert "SENTINEL_PROVIDER" not in encoded
    assert "raw_prompt" not in encoded
    assert "raw_provider_payload" not in encoded


def test_static_runtime_live_and_authority_guard() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.run_kernel",
        "core.author_execution_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.retrieval_dispatch_runtime",
        "openai",
        "requests",
        "httpx",
        "urllib",
        "dotenv",
        "subprocess",
        "os",
    }
    forbidden_called_names = {
        "run_pipeline",
        "authorize_",
        "reduce_",
        "execute_author",
        "search_web",
        "retrieve",
        "fetch",
        "read_url",
        "render_citation",
        "broker",
        "live_provider",
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
    assert called_names.isdisjoint(forbidden_called_names)
    for token in forbidden_called_names:
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
