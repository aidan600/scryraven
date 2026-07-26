from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

import pytest

import tests.test_ag_sem_09_sufficiency_semantic_consumption as semantic_fixture
from core.component_coverage_record import (
    ConflictPosture,
    CoverageState,
    FollowupNeed,
    SemanticSupportStatus,
    SourceObligationStatus,
)
from core.final_answer_packet_hardening_runtime import (
    FAP_STATUSES,
    READINESS_TO_FAP_STATUS,
    build_final_answer_packet_hardening_observation_payload,
    reduce_hardened_final_answer_packet,
)
from core.run_kernel import (
    FINAL_ANSWER_PACKET_STAGE,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.semantic_contract_foundation import (
    AnswerComponentContract,
    Materiality,
    RequirementPosture,
    SupportKind,
)
from core.sufficiency_readiness_runtime import reduce_sufficiency_readiness

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "final_answer_packet_hardening_runtime.py"
RUN_KERNEL_MODULE = ROOT / "core" / "run_kernel.py"
PIPELINE_ORCHESTRATOR = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "AG_FINAL_ANSWER_PACKET_HARDENING_01.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
)


def _component_id(kernel: Any) -> str:
    accepted = kernel.state.current_answer_contract or kernel.state.initial_answer_contract
    return accepted["accepted_answer_component_refs"][0]["component_id"]


def _semantic_kernel(
    *,
    coverage_kwargs: dict[str, Any] | None = None,
    include_semantic: bool = True,
    include_coverage: bool = True,
    unresolved_component_id: str | None = None,
    unresolved_required: bool = False,
) -> RunKernel:
    kernel = RunKernel.start(
        run_id=semantic_fixture.RUN_ID,
        request_id=semantic_fixture.REQUEST_ID,
    )
    qmr = semantic_fixture._qmr()
    if unresolved_component_id is not None:
        unresolved_component = AnswerComponentContract(
            component_id=unresolved_component_id,
            component_revision="1",
            user_facing_label="Unresolved fixture component",
            user_facing_question="What remains unresolved for this answer?",
            requirement_posture=(RequirementPosture.REQUIRED if unresolved_required else RequirementPosture.OPTIONAL),
            acceptance_criteria=("state the bounded value", "bind it to evidence"),
            source_obligation_candidate_ids=(f"source-obligation:{unresolved_component_id}",),
            allowed_support_kinds=(SupportKind.DIRECT,),
            max_inference_depth=0,
            mandatory_caveats=(f"Component {unresolved_component_id} is unresolved.",),
            prohibited_upgrades=(f"Do not upgrade component {unresolved_component_id} beyond supported readiness.",),
            materiality=(Materiality.MATERIAL if unresolved_required else Materiality.NON_MATERIAL),
        )
        qmr = replace(
            qmr,
            answer_components=(*qmr.answer_components, unresolved_component),
        )
    action = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=qmr.record_id,
        parent_proposal_digest=qmr.record_digest,
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
            status=RunStageStatus.COMPLETED,
            payload={"question_meaning_record": qmr.to_dict()},
        )
    )
    accepted = kernel.state.initial_answer_contract
    if not include_semantic:
        return kernel
    semantic_fixture._seed_evidence_ledger(kernel)
    content_ref = semantic_fixture._content_ref(accepted)
    observation = replace(
        semantic_fixture._observation(accepted),
        claim_or_value="The reported total is supported by the public record.",
    )
    component_ref = accepted["accepted_answer_component_refs"][0]
    admission_action = kernel.authorize_semantic_observation_admission(
        semantic_observation_id=observation.observation_id,
        semantic_observation_digest=observation.observation_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
    )
    kernel.reduce(
        Observation.from_action(
            admission_action,
            observation_type=ObservationType.SEMANTIC_OBSERVATION_ADMITTED,
            status=RunStageStatus.COMPLETED,
            payload={
                "semantic_observation": observation.to_dict(),
                "sanitized_content_references": [content_ref.to_dict()],
            },
        )
    )
    if include_coverage:
        coverage = semantic_fixture._coverage_record(
            accepted,
            observation,
            content_ref,
            kernel,
            **(coverage_kwargs or {}),
        )
        semantic_fixture._reduce_coverage(kernel, accepted, coverage)
    return kernel


def _decide(kernel: Any, *, mode: str = "Balanced") -> dict[str, Any]:
    return reduce_sufficiency_readiness(
        run_kernel=kernel,
        mode=mode,
    ).readiness_projection


def _harden(kernel: Any) -> dict[str, Any]:
    return reduce_hardened_final_answer_packet(
        run_kernel=kernel,
    ).final_answer_authority_projection


def _full_ready_chain() -> dict[str, Any]:
    kernel = _semantic_kernel()
    _decide(kernel)
    return {"kernel": kernel}


def _partial_ready_kernel() -> Any:
    kernel = _semantic_kernel(
        unresolved_component_id="component:optional-context",
        unresolved_required=False,
    )
    _decide(kernel)
    return kernel


def _blocked_kernel() -> Any:
    kernel = _semantic_kernel(
        unresolved_component_id="component:required-gap",
        unresolved_required=True,
    )
    _decide(kernel)
    return kernel


def _followup_required_kernel() -> Any:
    kernel = _semantic_kernel(
        coverage_kwargs={
            "coverage_state": CoverageState.PARTIAL,
            "semantic_support_status": SemanticSupportStatus.PARTIAL,
            "source_obligation_status": SourceObligationStatus.PARTIAL,
            "followup_need": FollowupNeed.REQUIRED,
            "remaining_unknowns": ("Currentness requires follow-up.",),
        },
    )
    _decide(kernel)
    return kernel


def _contested_kernel() -> Any:
    kernel = _semantic_kernel(
        coverage_kwargs={
            "coverage_state": CoverageState.CONFLICTED,
            "conflict_posture": ConflictPosture.PRESENT,
            "remaining_unknowns": ("Conflicting source treatment is unresolved.",),
        },
    )
    _decide(kernel)
    return kernel


def _insufficient_kernel() -> Any:
    kernel = _semantic_kernel(include_semantic=False, include_coverage=False)
    _decide(kernel)
    return kernel


def _imports_calls_and_classes(path: Path) -> tuple[set[str], set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    called_names: set[str] = set()
    class_names: set[str] = set()
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
        elif isinstance(node, ast.ClassDef):
            class_names.add(node.name)
    return imported_names, called_names, class_names


def _assert_no_author_or_citation_surface(
    kernel: Any,
    projection: Mapping[str, Any],
) -> None:
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert "author_payload_ref" not in projection
    assert "author_handoff_payload" not in projection
    assert "author_prompt" not in projection
    assert projection["fap_is_answer"] is False
    assert projection["author_input_created"] is False
    assert projection["author_payload_created"] is False
    assert projection["author_input_materialized"] is False
    assert projection["author_execution_allowed"] is False
    assert projection["author_called"] is False
    assert projection["citation_eligible"] is False
    assert projection["citation_eligibility_created"] is False
    assert projection["citations_rendered"] is False
    assert projection["source_obligation_satisfied"] is False
    assert projection["product_correctness_claimed"] is False
    assert projection["current_answer_contract_mutated"] is False
    assert projection["live_provider_called"] is False
    assert projection["search_executed"] is False
    assert projection["retrieval_executed"] is False
    assert projection["fetch_read_executed"] is False
    assert projection["model_called"] is False
    for value in projection["closed_surface_flags"].values():
        assert value is False


def _entry_by_component(
    projection: Mapping[str, Any],
    component_id: str,
) -> dict[str, Any]:
    for entry in projection["component_packet_entries"]:
        if entry["component_id"] == component_id:
            return dict(entry)
    raise AssertionError(f"missing component entry {component_id}")


def test_case_a_full_answer_fap_preserves_supported_treatment_and_closes_author() -> None:
    chain = _full_ready_chain()
    kernel = chain["kernel"]
    component_id = _component_id(kernel)

    projection = _harden(kernel)
    entry = _entry_by_component(projection, component_id)

    assert projection["owner"] == "RunKernel.FinalAnswerPacket"
    assert projection["packet_created"] is True
    assert projection["fap_status"] == "full_answer_packet_ready"
    assert kernel.state.final_answer_packet["packet_kind"] == ("hardened_final_answer_packet")
    assert entry["component_readiness_status"] == "full_answer_ready"
    assert entry["fap_component_status"] == "supported_component"
    assert entry["allowed_author_treatment"] in {
        "may_state_as_supported",
        "may_state_with_caveat",
    }
    assert entry["supported_claim_allowed"] is True
    assert projection["mandatory_caveats"]
    assert projection["source_support_refs"]
    assert projection["citation_posture"] == ("requirements_preserved_eligibility_deferred")
    assert projection["source_obligation_posture"] == ("requirements_preserved_not_satisfied_by_fap")
    assert kernel.state.projections[FINAL_ANSWER_PACKET_STAGE] == projection
    assert kernel.state.final_answer_packet_history == [projection]
    _assert_no_author_or_citation_surface(kernel, projection)


def test_case_b_partial_answer_fap_keeps_unresolved_components_visible() -> None:
    kernel = _partial_ready_kernel()

    projection = _harden(kernel)
    unresolved_id = "component:optional-context"
    unresolved_entry = _entry_by_component(projection, unresolved_id)

    assert projection["fap_status"] == "partial_answer_packet_ready"
    assert projection["readiness_ref"]["final_readiness_status"] == ("partial_answer_ready")
    assert projection["missing_component_refs"]
    assert unresolved_entry["component_readiness_status"] == "insufficient_evidence"
    assert unresolved_entry["allowed_author_treatment"] == "must_state_as_unresolved"
    assert unresolved_entry["must_not_answer"] is True
    assert projection["author_handoff_constraints"]["must_not_imply_full_answer"] is True
    assert projection["author_allowed_response_posture"]["full_answer_implication_allowed"] is False
    assert "Do not imply full-answer readiness." in projection["author_prohibited_claims"]
    _assert_no_author_or_citation_surface(kernel, projection)


def test_case_c_blocked_fap_allows_blocker_explanation_only() -> None:
    kernel = _blocked_kernel()

    projection = _harden(kernel)

    assert projection["fap_status"] == "blocked_answer_packet"
    assert projection["blocked_component_refs"] or projection["missing_component_refs"]
    assert projection["author_handoff_constraints"]["allowed_scope"] == ("blocker_explanation_only")
    assert projection["author_handoff_constraints"]["must_not_answer_unsupported_components"] is True
    assert "Do not answer blocked or unsupported components." in projection["author_prohibited_claims"]
    for entry in projection["component_packet_entries"]:
        if entry["component_readiness_status"] != "full_answer_ready":
            assert entry["must_not_answer"] is True
    _assert_no_author_or_citation_surface(kernel, projection)


def test_case_d_followup_required_fap_preserves_remediation_without_authorizing() -> None:
    kernel = _followup_required_kernel()

    projection = _harden(kernel)

    assert projection["fap_status"] == "followup_required_packet"
    assert projection["followup_required_component_refs"]
    assert projection["author_handoff_constraints"]["allowed_scope"] == ("remediation_required_explanation_only")
    assert projection["author_handoff_constraints"]["followup_authorized_by_fap"] is (False)
    assert projection["followup_authorized"] is False
    assert projection["followup_search_authorized"] is False
    assert "Do not authorize follow-up or imply remediation completed." in projection["author_prohibited_claims"]
    _assert_no_author_or_citation_surface(kernel, projection)


def test_case_e_contested_fap_preserves_contested_refs_and_forbids_smoothing() -> None:
    kernel = _contested_kernel()

    projection = _harden(kernel)
    contested_entry = _entry_by_component(projection, _component_id(kernel))

    assert projection["fap_status"] == "contested_answer_packet"
    assert projection["contested_component_refs"]
    assert contested_entry["allowed_author_treatment"] == "must_state_as_contested"
    assert "must_not_present_as_fact" in contested_entry["author_treatment_constraints"]
    assert projection["author_handoff_constraints"]["must_not_smooth_disagreement_into_fact"] is True
    assert "Do not smooth contested disagreement into fact." in projection["author_prohibited_claims"]
    _assert_no_author_or_citation_surface(kernel, projection)


def test_case_f_insufficient_evidence_fap_allows_no_supported_claims() -> None:
    kernel = _insufficient_kernel()

    projection = _harden(kernel)

    assert projection["fap_status"] == "insufficient_evidence_packet"
    assert projection["supported_component_refs"] == []
    assert projection["source_support_refs"] == []
    assert projection["author_handoff_constraints"]["supported_claims_allowed"] is (False)
    assert projection["author_allowed_response_posture"]["supported_claims_allowed"] is False
    for entry in projection["component_packet_entries"]:
        assert entry["supported_claim_allowed"] is False
        assert entry["allowed_author_treatment"] == "must_not_answer"
    _assert_no_author_or_citation_surface(kernel, projection)


def test_case_g_not_applicable_records_no_packet_posture_only() -> None:
    kernel = RunKernel.start(run_id="run:not-applicable", request_id="req:not-app")
    readiness = _decide(kernel)

    projection = _harden(kernel)

    assert readiness["final_readiness_status"] == "not_applicable"
    assert projection["fap_status"] == "not_applicable"
    assert projection["packet_created"] is False
    assert projection["final_answer_packet_created"] is False
    assert "packet_id" not in projection
    assert "packet_digest" not in projection
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.final_answer_authority_projection == projection
    assert kernel.state.projections[FINAL_ANSWER_PACKET_STAGE] == projection
    assert projection["author_handoff_constraints"]["must_not_answer"] is True
    _assert_no_author_or_citation_surface(kernel, projection)


def test_case_h_stale_readiness_digest_or_projection_is_rejected() -> None:
    chain = _full_ready_chain()
    kernel = chain["kernel"]
    action = kernel.authorize_final_answer_packet_hardening()
    payload = build_final_answer_packet_hardening_observation_payload(
        action_id=action.action_id,
        action_inputs=action.inputs,
    )
    kernel.state.sufficiency_readiness_projection = deepcopy(kernel.state.sufficiency_readiness_projection)
    kernel.state.sufficiency_readiness_projection["readiness_count"] = 99

    with pytest.raises(RunKernelTransitionError, match="stale"):
        kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.FINAL_ANSWER_PACKET_HARDENED,
                status=RunStageStatus.COMPLETED,
                payload=payload,
            )
        )

    assert kernel.state.final_answer_packet == {}
    assert kernel.state.final_answer_authority_projection == {}


def test_case_i_no_closed_surface_openings_and_no_pipeline_orchestrator_runtime() -> None:
    chain = _full_ready_chain()
    kernel = chain["kernel"]

    projection = _harden(kernel)

    _assert_no_author_or_citation_surface(kernel, projection)
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert PIPELINE_ORCHESTRATOR.read_text(encoding="utf-8")
    imports, calls, _classes = _imports_calls_and_classes(RUNTIME_MODULE)
    assert "core.pipeline_orchestrator" not in imports
    assert "run_pipeline" not in calls


def test_case_j_static_guards_keep_runtime_off_closed_surfaces() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.final_answer_packet_runtime",
        "core.final_answer_runtime_adapter",
        "core.followup_final_answer_packet_runtime",
        "core.author_execution_runtime",
        "core.authoring",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "openai",
        "requests",
        "httpx",
        "urllib",
        "dotenv",
        "subprocess",
    }
    forbidden_calls = {
        "execute_author",
        "derive_author_input_payload",
        "prepare_final_answer_packet_author_handoff_from_scope",
        "execute_final_answer_packet_prepare_action",
        "render_citation",
        "run_pipeline",
        "call_broker",
        "invoke_broker",
        "search_web",
        "retrieve",
        "dispatch_retrieval",
        "fetch_url",
        "fetch_page",
        "read_url",
        "ask_model",
        "Popen",
        "run",
    }
    imports, calls, _classes = _imports_calls_and_classes(RUNTIME_MODULE)

    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)
    run_kernel_source = RUN_KERNEL_MODULE.read_text(encoding="utf-8")
    assert "FINAL_ANSWER_PACKET_HARDEN" in run_kernel_source
    assert "FINAL_ANSWER_PACKET_HARDENED" in run_kernel_source
    assert "final_answer_packet_history" in run_kernel_source


def test_case_k_no_packet_laundering_across_non_full_statuses() -> None:
    cases = [
        ("partial_answer_ready", _partial_ready_kernel()),
        ("blocked", _blocked_kernel()),
        ("followup_required", _followup_required_kernel()),
        ("contested", _contested_kernel()),
        ("insufficient_evidence", _insufficient_kernel()),
    ]

    for readiness_status, kernel in cases:
        projection = _harden(kernel)
        expected_fap = READINESS_TO_FAP_STATUS[readiness_status]

        assert projection["fap_status"] == expected_fap
        assert projection["readiness_ref"]["final_readiness_status"] == (readiness_status)
        assert projection["author_handoff_constraints"]["must_preserve_readiness_status"] == readiness_status
        assert projection["fap_status"] != "full_answer_packet_ready"
        assert projection["fap_status"] in FAP_STATUSES
        if readiness_status != "partial_answer_ready":
            assert not projection["author_allowed_response_posture"]["full_answer_implication_allowed"]
        for entry in projection["component_packet_entries"]:
            if entry["component_readiness_status"] != "full_answer_ready":
                assert entry["supported_claim_allowed"] is False
                assert entry["must_not_answer"] is True


def test_docs_record_final_answer_packet_hardening_phase_posture() -> None:
    docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
    required = (
        "AG-FINAL-ANSWER-PACKET-HARDENING-01",
        "hardened FAP handoff surface",
        "consumes SufficiencyReadiness",
        "canonical `final_answer_packet` stage/state slot",
        "does not use old AG-92C/AG-96 FAP/Author authority",
        "does not execute Author or create prose",
        "full/partial/blocked/follow-up/contested/insufficient/not-applicable",
        "defers citation eligibility/rendering",
        "does not satisfy source obligations",
        "Author prose-only finalization comes next",
    )
    for phrase in required:
        assert phrase in docs_text
