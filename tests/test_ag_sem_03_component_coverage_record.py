from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.component_coverage_record import (
    COMPONENT_COVERAGE_RECORD_SCHEMA_VERSION,
    ComponentCoverageRecord,
    ConflictPosture,
    ContentAvailabilityStatus,
    ContentReferenceCoverageBinding,
    CoverageState,
    CurrentnessPosture,
    DerivedSupportStatus,
    EvidenceBasis,
    EvidenceCustodyStatus,
    EvidenceLedgerSnapshotBinding,
    ExplicitnessPosture,
    FollowupNeed,
    ModeBudgetPosture,
    SemanticObservationCoverageRef,
    SemanticSupportStatus,
    SourceObligationStatus,
    SupportPosture,
    VersionValidity,
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
from core.semantic_observation_foundation import (
    ContentKind,
    ObservationKind,
    SanitizedContentReference,
    SemanticObservation,
    SupportDirectness,
    SupportStatus,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "component_coverage_record.py"


def _component(
    *,
    component_id: str = "component:taxable-maximum",
    component_revision: str = "1",
    allowed_support: tuple[SupportKind, ...] = (SupportKind.DIRECT,),
) -> AnswerComponentContract:
    return AnswerComponentContract(
        component_id=component_id,
        component_revision=component_revision,
        user_facing_label="Taxable maximum",
        user_facing_question="What is the Social Security taxable maximum wage base for 2026?",
        requirement_posture=RequirementPosture.REQUIRED,
        acceptance_criteria=("state the bounded value", "bind it to evidence"),
        semantic_slot_ids=("slot:time-period",),
        source_obligation_candidate_ids=("obligation:official-current",),
        allowed_support_kinds=allowed_support,
        max_inference_depth=1 if SupportKind.INFERRED in allowed_support else 0,
        normalization_policy="Use annual wage-base dollars.",
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
        resolver_version="ag-sem-03-test",
        intent="Answer the current official taxable maximum question.",
        requested_output="Concise answer with official support.",
        semantic_slots=(
            SemanticSlot(
                slot_id="slot:time-period",
                slot_kind=SemanticSlotKind.TIME_PERIOD,
                status=SemanticSlotStatus.EXPLICIT,
                selected_value="2026",
                materiality=Materiality.MATERIAL,
            ),
        ),
        answer_components=(component,),
    ).require_valid()


def _content_ref(
    *,
    component: AnswerComponentContract | None = None,
    qmr: QuestionMeaningRecord | None = None,
    content_ref_id: str = "content:ssa-wage-base",
) -> SanitizedContentReference:
    component = component or _component()
    qmr = qmr or _qmr(component)
    return SanitizedContentReference(
        content_ref_id=content_ref_id,
        evidence_ref_id="evidence:ssa-notice",
        admitted_evidence_ref="evidence:ssa-notice",
        source_id="source:ssa",
        source_digest="source-digest-001",
        source_url="https://www.ssa.gov/example",
        source_title="Contribution and Benefit Base",
        source_domain="ssa.gov",
        answer_component_id=component.component_id,
        component_revision=component.component_revision,
        component_contract_digest=component.component_digest,
        question_meaning_record_id=qmr.record_id,
        question_meaning_record_digest=qmr.record_digest,
        content_kind=ContentKind.BOUNDED_EXCERPT,
        bounded_text="The 2026 Social Security taxable maximum is $184,500.",
        extraction_method="offline_fixture",
        worker_kind="bounded_reader",
        currentness="current_for_2026",
        observed_at="2026-06-22T00:00:00Z",
    ).require_valid()


def _observation(
    *,
    component: AnswerComponentContract | None = None,
    qmr: QuestionMeaningRecord | None = None,
    content_ref: SanitizedContentReference | None = None,
    support_kind: SupportDirectness = SupportDirectness.DIRECT,
    support_status: SupportStatus = SupportStatus.SUPPORTS,
) -> SemanticObservation:
    component = component or _component()
    qmr = qmr or _qmr(component)
    content_ref = content_ref or _content_ref(component=component, qmr=qmr)
    return SemanticObservation(
        observation_id="observation:supports-wage-base",
        observation_kind=ObservationKind.SUPPORT,
        question_meaning_record_id=qmr.record_id,
        question_meaning_record_digest=qmr.record_digest,
        contract_version=qmr.contract_lineage.contract_version,
        contract_digest=qmr.record_digest,
        answer_component_id=component.component_id,
        component_revision=component.component_revision,
        component_contract_digest=component.component_digest,
        evidence_refs=("evidence:ssa-notice",),
        content_refs=(content_ref.content_ref_id,),
        support_kind=support_kind,
        directness=support_kind,
        support_status=support_status,
        claim_or_value="$184,500",
        normalization_fit="annual wage-base dollars",
        scope_fit="calendar year 2026",
        assumption_fit="uses source wording only",
        inference_depth=0 if support_kind is SupportDirectness.DIRECT else 1,
    ).require_valid(content_references=(content_ref,))


def _ledger_binding(
    *,
    custody_status: EvidenceCustodyStatus = EvidenceCustodyStatus.CUSTODIED,
    version_validity: VersionValidity = VersionValidity.VALID,
) -> EvidenceLedgerSnapshotBinding:
    return EvidenceLedgerSnapshotBinding(
        ledger_snapshot_id="ledger:snapshot:1",
        ledger_schema_version="evidence_ledger_ag91j_v1",
        ledger_digest="ledger-digest-001",
        custody_status=custody_status,
        source_requirement_ids=("obligation:official-current",),
        ledger_observation_refs=("evidence-ledger-observation:1",),
        version_validity=version_validity,
    )


def _coverage(
    *,
    component: AnswerComponentContract | None = None,
    qmr: QuestionMeaningRecord | None = None,
    content_ref: SanitizedContentReference | None = None,
    observation: SemanticObservation | None = None,
    coverage_state: CoverageState = CoverageState.SATISFIED,
    support_posture: SupportPosture = SupportPosture.DIRECT,
    derived_support_status: DerivedSupportStatus = DerivedSupportStatus.NOT_APPLICABLE,
    assumption_posture: ExplicitnessPosture = ExplicitnessPosture.NOT_APPLICABLE,
    normalization_posture: ExplicitnessPosture = ExplicitnessPosture.NOT_APPLICABLE,
    semantic_support_status: SemanticSupportStatus = SemanticSupportStatus.SUPPORTED,
    source_obligation_status: SourceObligationStatus = SourceObligationStatus.SATISFIED,
    content_availability_status: ContentAvailabilityStatus = ContentAvailabilityStatus.AVAILABLE,
    evidence_custody_status: EvidenceCustodyStatus = EvidenceCustodyStatus.CUSTODIED,
    version_validity: VersionValidity = VersionValidity.VALID,
    ledger_binding: EvidenceLedgerSnapshotBinding | None = None,
    evidence_basis: tuple[EvidenceBasis, ...] | None = None,
    content_bindings: tuple[ContentReferenceCoverageBinding, ...] | None = None,
    observation_refs: tuple[SemanticObservationCoverageRef, ...] | None = None,
    conflict_posture: ConflictPosture = ConflictPosture.NONE,
    currentness_posture: CurrentnessPosture = CurrentnessPosture.CURRENT,
    remaining_unknowns: tuple[str, ...] = (),
    required_caveats: tuple[str, ...] = ("Currentness remains evidence-bound.",),
    prohibited_upgrades: tuple[str, ...] = ("Do not replace official value with estimate.",),
    followup_need: FollowupNeed = FollowupNeed.NONE,
    mode_budget_posture: ModeBudgetPosture = ModeBudgetPosture.AVAILABLE,
    stale: bool = False,
    diagnostic_score: float | None = None,
) -> ComponentCoverageRecord:
    component = component or _component()
    qmr = qmr or _qmr(component)
    content_ref = content_ref or _content_ref(component=component, qmr=qmr)
    observation = observation or _observation(component=component, qmr=qmr, content_ref=content_ref)
    return ComponentCoverageRecord(
        record_id="coverage:taxable-maximum",
        run_id="run:semantic-offline",
        request_id="request:1",
        request_digest="request-digest-001",
        accepted_contract_version=qmr.contract_lineage.contract_version,
        accepted_contract_digest=qmr.record_digest,
        answer_component_id=component.component_id,
        component_revision=component.component_revision,
        component_digest=component.component_digest or "",
        evidence_ledger_binding=ledger_binding or _ledger_binding(),
        coverage_state=coverage_state,
        semantic_support_status=semantic_support_status,
        support_posture=support_posture,
        derived_support_status=derived_support_status,
        source_obligation_status=source_obligation_status,
        content_availability_status=content_availability_status,
        evidence_custody_status=evidence_custody_status,
        version_validity=version_validity,
        accepted_observation_refs=(
            observation_refs
            if observation_refs is not None
            else (SemanticObservationCoverageRef.from_observation(observation),)
        ),
        content_reference_bindings=(
            content_bindings
            if content_bindings is not None
            else (ContentReferenceCoverageBinding.from_content_reference(content_ref),)
        ),
        evidence_basis=evidence_basis
        if evidence_basis is not None
        else (
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        normalization_posture=normalization_posture,
        assumption_posture=assumption_posture,
        conflict_posture=conflict_posture,
        currentness_posture=currentness_posture,
        remaining_unknowns=remaining_unknowns,
        required_caveats=required_caveats,
        prohibited_upgrades=prohibited_upgrades,
        followup_need=followup_need,
        mode_budget_posture=mode_budget_posture,
        stale=stale,
        diagnostic_score=diagnostic_score,
        metadata={"safe_note": "kept", "raw_prompt": "SENTINEL_RAW_PROMPT"},
    )


def test_happy_path_component_coverage_record_is_passive_schema_only() -> None:
    record = _coverage().require_valid()
    payload = record.to_dict()

    assert payload["schema_version"] == COMPONENT_COVERAGE_RECORD_SCHEMA_VERSION
    assert payload["coverage_state"] == "satisfied"
    assert payload["passive"] is True
    assert payload["canonical_state"] is False
    assert payload["runtime_behavior_changed"] is False
    assert payload["accepted_authority"] is False
    assert payload["lineage"]["reducer_consumed"] is False
    assert payload["lineage"]["runtime_consumed"] is False
    assert payload["record_digest"]
    assert json.dumps(payload, sort_keys=True)


def test_categorical_coverage_states_are_explicit() -> None:
    assert {item.value for item in CoverageState} == {
        "unassessed",
        "unsupported",
        "partial",
        "supported_with_caveats",
        "satisfied",
        "conflicted",
        "blocked",
        "stale",
    }


@pytest.mark.parametrize(
    "basis",
    (
        (EvidenceBasis.IDS_OR_DIGESTS_ONLY,),
        (EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,),
        (EvidenceBasis.CANDIDATE_DISCOVERY,),
        (EvidenceBasis.SEARCH_RESULT_SNIPPET,),
        (EvidenceBasis.PROVIDER_ANSWER_PRODUCT,),
        (EvidenceBasis.WORK_ATTEMPTED,),
        (EvidenceBasis.WORK_COMPLETED,),
    ),
)
def test_satisfied_coverage_cannot_arise_from_non_semantic_basis_alone(
    basis: tuple[EvidenceBasis, ...],
) -> None:
    record = _coverage(
        evidence_basis=basis,
        content_bindings=(),
        observation_refs=(),
        semantic_support_status=SemanticSupportStatus.UNKNOWN,
    )

    errors = record.validate().errors

    assert any("SemanticObservation refs" in error for error in errors)
    assert any("answer-bearing content" in error for error in errors)
    assert any("cannot be based solely" in error for error in errors)


def test_satisfied_coverage_rejects_missing_answer_bearing_content_reference() -> None:
    record = _coverage(
        content_bindings=(
            ContentReferenceCoverageBinding(
                content_ref_id="content:context-only",
                content_digest="content-digest-context",
                evidence_ref_id="evidence:context",
                answer_component_id="component:taxable-maximum",
                component_revision="1",
                component_contract_digest=_component().component_digest or "",
                answer_bearing=False,
            ),
        ),
    )

    assert any("answer-bearing content reference" in error for error in record.validate().errors)


def test_observation_bound_to_another_component_revision_cannot_satisfy() -> None:
    component = _component(component_revision="1")
    qmr = _qmr(component)
    content_ref = _content_ref(component=component, qmr=qmr)
    observation = _observation(component=component, qmr=qmr, content_ref=content_ref)
    bad_ref = SemanticObservationCoverageRef.from_observation(observation.to_dict() | {"component_revision": "2"})
    record = _coverage(component=component, qmr=qmr, content_ref=content_ref, observation_refs=(bad_ref,))

    assert any("another component revision" in error for error in record.validate().errors)


@pytest.mark.parametrize(
    ("version_validity", "ledger_validity", "expected"),
    (
        (VersionValidity.STALE_CONTRACT, VersionValidity.VALID, "valid contract"),
        (VersionValidity.VALID, VersionValidity.STALE_EVIDENCE_LEDGER, "non-stale EvidenceLedger"),
    ),
)
def test_stale_contract_or_evidence_ledger_version_cannot_satisfy(
    version_validity: VersionValidity,
    ledger_validity: VersionValidity,
    expected: str,
) -> None:
    record = _coverage(
        version_validity=version_validity,
        ledger_binding=_ledger_binding(version_validity=ledger_validity),
    )

    assert any(expected in error for error in record.validate().errors)


@pytest.mark.parametrize(
    "support_posture",
    (SupportPosture.INFERRED, SupportPosture.COMPUTED),
)
def test_unsupported_inferred_or_computed_claims_cannot_satisfy(
    support_posture: SupportPosture,
) -> None:
    record = _coverage(
        support_posture=support_posture,
        derived_support_status=DerivedSupportStatus.UNSUPPORTED,
        assumption_posture=ExplicitnessPosture.MISSING,
        normalization_posture=ExplicitnessPosture.MISSING,
    )

    errors = record.validate().errors

    assert any("supported premises or computation" in error for error in errors)
    assert any("explicit assumptions" in error for error in errors)


def test_direct_inferred_and_computed_support_remain_distinguishable() -> None:
    direct = _coverage(support_posture=SupportPosture.DIRECT).require_valid()
    inferred = _coverage(
        support_posture=SupportPosture.INFERRED,
        derived_support_status=DerivedSupportStatus.PREMISES_SUPPORTED,
        assumption_posture=ExplicitnessPosture.EXPLICIT,
    ).require_valid()
    computed = _coverage(
        support_posture=SupportPosture.COMPUTED,
        derived_support_status=DerivedSupportStatus.COMPUTATION_SUPPORTED,
        assumption_posture=ExplicitnessPosture.EXPLICIT,
        normalization_posture=ExplicitnessPosture.EXPLICIT,
    ).require_valid()

    assert direct.to_dict()["support_posture"] == "direct"
    assert inferred.to_dict()["support_posture"] == "inferred"
    assert inferred.to_dict()["derived_support_status"] == "premises_supported"
    assert computed.to_dict()["support_posture"] == "computed"
    assert computed.to_dict()["derived_support_status"] == "computation_supported"


def test_assumptions_normalization_conflict_currentness_and_unknowns_survive_serialization() -> None:
    record = _coverage(
        coverage_state=CoverageState.SUPPORTED_WITH_CAVEATS,
        semantic_support_status=SemanticSupportStatus.PARTIAL,
        support_posture=SupportPosture.COMPUTED,
        derived_support_status=DerivedSupportStatus.UNKNOWN,
        assumption_posture=ExplicitnessPosture.EXPLICIT,
        normalization_posture=ExplicitnessPosture.EXPLICIT,
        conflict_posture=ConflictPosture.PRESENT,
        currentness_posture=CurrentnessPosture.UNKNOWN,
        remaining_unknowns=("whether the official notice has superseded this value",),
        followup_need=FollowupNeed.OPTIONAL,
    ).require_valid()
    payload = record.to_dict()

    assert payload["assumption_posture"] == "explicit"
    assert payload["normalization_posture"] == "explicit"
    assert payload["conflict_posture"] == "present"
    assert payload["currentness_posture"] == "unknown"
    assert payload["remaining_unknowns"] == ["whether the official notice has superseded this value"]


def test_stale_coverage_cannot_present_as_satisfied() -> None:
    record = _coverage(stale=True)

    assert any("stale coverage cannot present as satisfied" in error for error in record.validate().errors)


def test_required_caveats_and_prohibited_upgrades_are_retained() -> None:
    payload = (
        _coverage(
            coverage_state=CoverageState.SUPPORTED_WITH_CAVEATS,
            required_caveats=("Label computed estimates.", "Name missing official source."),
            prohibited_upgrades=("Do not upgrade candidate discovery to support.",),
        )
        .require_valid()
        .to_dict()
    )

    assert payload["required_caveats"] == ["Label computed estimates.", "Name missing official source."]
    assert payload["prohibited_upgrades"] == ["Do not upgrade candidate discovery to support."]


def test_deterministic_serialization_and_digest_behavior() -> None:
    first = _coverage().require_valid()
    second = _coverage().require_valid()
    changed = _coverage(required_caveats=("Different caveat.",)).require_valid()

    assert json.dumps(first.to_dict(), sort_keys=True) == json.dumps(second.to_dict(), sort_keys=True)
    assert first.record_digest == second.record_digest
    assert changed.record_digest != first.record_digest


def test_validation_can_check_exact_ag_sem_02_input_bindings() -> None:
    component = _component()
    qmr = _qmr(component)
    content_ref = _content_ref(component=component, qmr=qmr)
    observation = _observation(component=component, qmr=qmr, content_ref=content_ref)
    other_component = _component(component_id="component:other")
    bad_content_ref = _content_ref(component=other_component, qmr=_qmr(other_component))

    valid = _coverage(component=component, qmr=qmr, content_ref=content_ref, observation=observation).require_valid(
        content_references=(content_ref,),
        observations=(observation,),
    )
    errors = valid.validate(content_references=(bad_content_ref,), observations=(observation,)).errors

    assert valid.coverage_state is CoverageState.SATISFIED
    assert any("component does not match coverage record" in error for error in errors)


def test_diagnostic_score_is_non_authoritative_for_satisfied_coverage() -> None:
    record = _coverage(diagnostic_score=0.99)

    assert any("non-authoritative" in error for error in record.validate().errors)


def test_sensitive_metadata_is_scrubbed() -> None:
    encoded = json.dumps(_coverage().require_valid().to_dict(), sort_keys=True)

    assert "safe_note" in encoded
    assert "SENTINEL_RAW_PROMPT" not in encoded
    assert "raw_prompt" not in encoded


def test_static_guards_keep_component_coverage_record_off_runtime_live_and_author_surfaces() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.run_kernel",
        "core.llm",
        "core.author_execution_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
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
    forbidden_called_names = {
        "run_pipeline",
        "ask_model",
        "search_web",
        "retrieve",
        "fetch",
        "read_url",
        "execute_author",
        "authorize_",
        "reduce_coverage",
        "render_citation",
        "format_citation",
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
