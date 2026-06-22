from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

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
    MAX_BOUNDED_TEXT_CHARS,
    ContentKind,
    ObservationKind,
    SanitizedContentReference,
    SemanticObservation,
    SupportDirectness,
    SupportStatus,
    validate_content_references,
    validate_semantic_observation_collection,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "semantic_observation_foundation.py"


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
        acceptance_criteria=("state the bounded value", "bind it to evidence"),
        semantic_slot_ids=("slot:time-period",),
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
        materiality=Materiality.MATERIAL,
    )


def _question_meaning_record() -> QuestionMeaningRecord:
    return QuestionMeaningRecord(
        record_id="qmr:ssa-taxable-maximum",
        request_digest="request-digest-001",
        requested_mode="balanced",
        resolver_kind=ResolverKind.PASSIVE_PROPOSAL,
        resolver_version="ag-sem-02-test",
        intent="Answer the current official taxable maximum question.",
        requested_output="Concise answer with official support.",
        semantic_slots=(_slot(),),
        answer_components=(_component(),),
    ).require_valid()


def _content_ref(
    *,
    content_ref_id: str = "content:ssa-wage-base",
    component: AnswerComponentContract | None = None,
    qmr: QuestionMeaningRecord | None = None,
    bounded_text: str = "The 2026 Social Security taxable maximum is $184,500.",
) -> SanitizedContentReference:
    component = component or _component()
    qmr = qmr or _question_meaning_record()
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
        bounded_text=bounded_text,
        page=1,
        section="Annual wage base",
        char_range_start=10,
        char_range_end=70,
        extraction_method="offline_fixture",
        worker_kind="bounded_reader",
        currentness="current_for_2026",
        observed_at="2026-06-22T00:00:00Z",
        metadata={
            "safe_note": "kept",
            "raw_prompt": "SENTINEL_RAW_PROMPT",
            "token": "SENTINEL_TOKEN",
        },
    )


def _observation(
    *,
    observation_id: str = "observation:supports-wage-base",
    component: AnswerComponentContract | None = None,
    qmr: QuestionMeaningRecord | None = None,
    content_refs: tuple[str, ...] = ("content:ssa-wage-base",),
    evidence_refs: tuple[str, ...] = ("evidence:ssa-notice",),
    observation_kind: ObservationKind = ObservationKind.SUPPORT,
    support_status: SupportStatus = SupportStatus.SUPPORTS,
    claim_or_value: object = "$184,500",
) -> SemanticObservation:
    component = component or _component()
    qmr = qmr or _question_meaning_record()
    return SemanticObservation(
        observation_id=observation_id,
        observation_kind=observation_kind,
        question_meaning_record_id=qmr.record_id,
        question_meaning_record_digest=qmr.record_digest,
        contract_version=qmr.contract_lineage.contract_version,
        contract_digest=qmr.record_digest,
        answer_component_id=component.component_id,
        component_revision=component.component_revision,
        component_contract_digest=component.component_digest,
        evidence_refs=evidence_refs,
        content_refs=content_refs,
        support_kind=SupportDirectness.DIRECT,
        directness=SupportDirectness.DIRECT,
        support_status=support_status,
        claim_or_value=claim_or_value,
        normalization_fit="annual wage-base dollars",
        scope_fit="calendar year 2026",
        assumption_fit="uses source wording without runtime admission",
        inference_depth=0,
        candidate_caveats=("Currentness remains evidence-bound.",),
        candidate_followup_gaps=("Verify against admitted evidence in a later reducer.",),
        candidate_contract_amendment_notes=("Candidate only; does not mutate contract.",),
        metadata={
            "safe_review_note": "passive observation",
            "raw_provider_payload": "SENTINEL_PROVIDER",
            "coverage": "SENTINEL_COVERAGE",
        },
    )


def test_happy_path_sanitized_content_reference_is_bounded_json_safe_and_retention_safe() -> None:
    content_ref = _content_ref(bounded_text="x" * (MAX_BOUNDED_TEXT_CHARS + 50)).require_valid()
    payload = content_ref.to_dict()
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["schema_version"] == "semantic_observation_foundation_ag_sem_02_v1"
    assert payload["sanitized"] is True
    assert payload["bounded"] is True
    assert payload["trace_only"] is True
    assert payload["accepted_authority"] is False
    assert len(payload["bounded_text"]) == MAX_BOUNDED_TEXT_CHARS
    assert payload["content_digest"]
    assert payload["raw_content_retained"] is False
    assert payload["raw_provider_payload_retained"] is False
    assert payload["raw_prompt_retained"] is False
    assert payload["raw_model_response_retained"] is False
    assert payload["private_logs_retained"] is False
    assert payload["db_cache_rows_retained"] is False
    assert payload["full_trace_retained"] is False
    assert payload["secrets_returned"] is False
    assert encoded


def test_semantic_observation_happy_path_is_passive_and_non_canonical() -> None:
    component = _component()
    qmr = _question_meaning_record()
    content_ref = _content_ref(component=component, qmr=qmr).require_valid()
    observation = _observation(component=component, qmr=qmr).require_valid(content_references=(content_ref,))
    payload = observation.to_dict()

    assert payload["passive"] is True
    assert payload["canonical_state"] is False
    assert payload["coverage_decision"] is False
    assert payload["component_satisfied"] is False
    assert payload["sufficiency_decision"] is False
    assert payload["final_answer_authority"] is False
    assert payload["author_input_created"] is False
    assert payload["runtime_behavior_changed"] is False
    assert payload["accepted_authority"] is False
    assert payload["accepted_contract_amendment"] is False
    assert payload["observation_digest"]


def test_sensitive_metadata_and_raw_payload_fields_are_scrubbed_or_rejected() -> None:
    content_ref = SanitizedContentReference(
        content_ref_id="content:structured",
        evidence_ref_id="evidence:structured",
        answer_component_id="component:taxable-maximum",
        content_kind=ContentKind.STRUCTURED_EXTRACT,
        structured_value={
            "safe_value": "$184,500",
            "raw_page": "SENTINEL_RAW_PAGE",
            "nested": {"api_key": "SENTINEL_API_KEY", "safe_nested": "kept"},
        },
        metadata={
            "password": "SENTINEL_PASSWORD",
            "safe_metadata": "kept",
        },
    ).require_valid()
    observation = _observation(
        claim_or_value={
            "safe_claim": "$184,500",
            "raw_model_response": "SENTINEL_MODEL_RESPONSE",
            "safe_nested": {"private_log": "SENTINEL_PRIVATE_LOG", "value": "kept"},
        }
    )
    encoded = json.dumps({"content": content_ref.to_dict(), "observation": observation.to_dict()}, sort_keys=True)

    assert "safe_metadata" in encoded
    assert "safe_nested" in encoded
    assert "safe_claim" in encoded
    for sentinel in (
        "SENTINEL_RAW_PAGE",
        "SENTINEL_API_KEY",
        "SENTINEL_PASSWORD",
        "SENTINEL_MODEL_RESPONSE",
        "SENTINEL_PRIVATE_LOG",
        "SENTINEL_PROVIDER",
        "SENTINEL_COVERAGE",
    ):
        assert sentinel not in encoded
    keys = _collect_keys({"content": content_ref.to_dict(), "observation": observation.to_dict()})
    assert keys.isdisjoint({"raw_page", "api_key", "password", "raw_model_response", "private_log", "coverage"})


def test_digests_are_deterministic_and_change_on_meaningful_semantic_change() -> None:
    first_content = _content_ref().require_valid()
    second_content = _content_ref().require_valid()
    changed_content = _content_ref(bounded_text="The 2026 wage base is unavailable.").require_valid()
    first_observation = _observation().require_valid(content_references=(first_content,))
    second_observation = _observation().require_valid(content_references=(second_content,))
    changed_observation = _observation(claim_or_value="$185,000").require_valid(content_references=(first_content,))

    assert first_content.content_digest == second_content.content_digest
    assert changed_content.content_digest != first_content.content_digest
    assert first_observation.observation_digest == second_observation.observation_digest
    assert changed_observation.observation_digest != first_observation.observation_digest


@pytest.mark.parametrize(
    ("kind", "status"),
    (
        (ObservationKind.SUPPORT, SupportStatus.SUPPORTS),
        (ObservationKind.CONTRADICTION, SupportStatus.CONTRADICTS),
        (ObservationKind.QUALIFICATION, SupportStatus.QUALIFIES),
    ),
)
def test_support_contradiction_and_qualification_observations_require_content_refs(
    kind: ObservationKind,
    status: SupportStatus,
) -> None:
    observation = _observation(
        observation_kind=kind,
        support_status=status,
        content_refs=(),
    )

    assert any("requires at least one content ref" in error for error in observation.validate().errors)


def test_missing_fact_observation_may_omit_content_refs_without_coverage_or_satisfaction() -> None:
    observation = _observation(
        observation_id="observation:missing-fact",
        observation_kind=ObservationKind.MISSING_FACT,
        support_status=SupportStatus.MISSING,
        content_refs=(),
        claim_or_value="Official 2026 wage base evidence is missing.",
    ).require_valid()
    payload = observation.to_dict()

    assert payload["support_status"] == "missing"
    assert "content_refs" not in payload
    assert payload["coverage_decision"] is False
    assert payload["component_satisfied"] is False
    assert payload["sufficiency_decision"] is False


def test_duplicate_content_and_observation_refs_are_rejected() -> None:
    duplicate_content = (
        _content_ref(content_ref_id="dup"),
        _content_ref(content_ref_id="dup"),
    )
    duplicate_observation = _observation(
        evidence_refs=("evidence:dup", "evidence:dup"),
        content_refs=("content:ssa-wage-base", "content:ssa-wage-base"),
    )

    assert any("duplicate content_ref_id" in error for error in validate_content_references(duplicate_content).errors)
    errors = duplicate_observation.validate().errors
    assert any("duplicate evidence_refs" in error for error in errors)
    assert any("duplicate content_refs" in error for error in errors)


def test_observation_content_component_contract_mismatch_is_rejected() -> None:
    observation_component = _component(component_id="component:taxable-maximum")
    content_component = _component(component_id="component:other")
    qmr = _question_meaning_record()
    content_ref = _content_ref(component=content_component, qmr=qmr)
    observation = _observation(component=observation_component, qmr=qmr)

    errors = observation.validate(content_references=(content_ref,)).errors

    assert any("does not match observation component" in error for error in errors)
    assert any("component_contract_digest does not match observation" in error for error in errors)


def test_forbidden_coverage_author_final_answer_and_amendment_fields_do_not_appear() -> None:
    content_ref = _content_ref().require_valid()
    observation = _observation().require_valid(content_references=(content_ref,))
    keys = _collect_keys({"content": content_ref.to_dict(), "observation": observation.to_dict()})

    assert keys.isdisjoint(
        {
            "coverage",
            "canonical_coverage",
            "component_coverage",
            "sufficiency",
            "sufficiency_judgment",
            "final_answer",
            "final_answer_packet",
            "author_input",
            "accepted_amendment",
            "accepted_contract_ref",
        }
    )
    assert observation.to_dict()["accepted_contract_amendment"] is False


def test_static_guards_keep_passive_module_off_runtime_live_search_author_and_citation_surfaces() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.run_kernel",
        "core.llm",
        "core.author_execution_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.evidence_ledger",
        "core.retrieval_dispatch_runtime",
        "core.pipeline",
        "openai",
        "requests",
        "httpx",
        "urllib",
        "dotenv",
        "subprocess",
        "os",
        "core.semantic_contract_foundation",
    }
    forbidden_tokens = {
        "run_pipeline",
        "ask_model",
        "search_web",
        "retrieve",
        "fetch",
        "read_url",
        "execute_author",
        "authorize_",
        "reduce_coverage",
        "sufficiency",
        "final_answer_packet",
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
    assert called_names.isdisjoint(forbidden_tokens)
    for token in forbidden_tokens:
        assert token not in source


def test_relationship_to_ag_sem_01_records_is_passive_and_by_ref_or_digest_only() -> None:
    qmr = _question_meaning_record()
    component = qmr.answer_components[0]
    content_ref = _content_ref(component=component, qmr=qmr).require_valid()
    observation = _observation(component=component, qmr=qmr).require_valid(content_references=(content_ref,))
    payload = {
        "content": content_ref.to_dict(),
        "observation": observation.to_dict(),
    }
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["content"]["question_meaning_record_id"] == qmr.record_id
    assert payload["content"]["question_meaning_record_digest"] == qmr.record_digest
    assert payload["content"]["component_contract_digest"] == component.component_digest
    assert payload["observation"]["question_meaning_record_id"] == qmr.record_id
    assert payload["observation"]["contract_digest"] == qmr.record_digest
    assert payload["observation"]["component_contract_digest"] == component.component_digest
    assert "semantic_slots" not in encoded
    assert "answer_components" not in encoded


def test_collection_validator_rejects_missing_content_ref_for_supporting_observation() -> None:
    observation = _observation(content_refs=("content:missing",))
    result = validate_semantic_observation_collection(content_references=(), observations=(observation,))

    assert any("references missing content ref content:missing" in error for error in result.errors)


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
