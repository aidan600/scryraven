from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.author_prose_conformance_runtime import review_author_prose_conformance
from core.author_prose_finalization_runtime import (
    FAP_TO_AUTHOR_PROSE_STATUS,
    build_author_prose_finalization_observation_payload,
    reduce_author_prose_finalization,
)
from core.final_answer_packet_hardening_runtime import (
    reduce_hardened_final_answer_packet,
)
from core.run_kernel import (
    AUTHOR_PROSE_FINALIZATION_STAGE,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.sufficiency_readiness_runtime import reduce_sufficiency_readiness
from tests.test_ag_final_answer_packet_hardening_01 import (
    _blocked_kernel,
    _contested_kernel,
    _followup_required_kernel,
    _full_ready_chain,
    _insufficient_kernel,
    _partial_ready_kernel,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "author_prose_finalization_runtime.py"
CONFORMANCE_MODULE = ROOT / "core" / "author_prose_conformance_runtime.py"
RUN_KERNEL_MODULE = ROOT / "core" / "run_kernel.py"
DOCS = (
    ROOT / "docs" / "architecture" / "AUTHOR_PROSE_ONLY_FINALIZATION_01.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
)


def _author(kernel: Any, policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    reduce_hardened_final_answer_packet(run_kernel=kernel)
    return reduce_author_prose_finalization(
        run_kernel=kernel,
        policy=policy,
    ).author_prose_projection


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


def _assert_author_boundaries(kernel: Any, projection: Mapping[str, Any]) -> None:
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert projection["author_prose_is_product_correctness"] is False
    assert projection["citation_eligible"] is False
    assert projection["citations_rendered"] is False
    assert projection["source_obligation_satisfied"] is False
    assert projection["product_correctness_claimed"] is False
    assert projection["model_called"] is False
    assert projection["provider_called"] is False
    assert projection["live_provider_called"] is False
    assert projection["search_executed"] is False
    assert projection["retrieval_executed"] is False
    assert projection["fetch_read_executed"] is False
    assert projection["old_author_runtime_called"] is False
    assert projection["pipeline_orchestrator_called"] is False
    for value in projection["closed_surface_flags"].values():
        assert value is False


def test_case_a_full_answer_prose_uses_hardened_fap_only() -> None:
    kernel = _full_ready_chain()["kernel"]

    projection = _author(kernel)

    assert projection["owner"] == "RunKernel.AuthorProseFinalization"
    assert projection["author_prose_status"] == "full_answer_prose_created"
    assert projection["fap_status"] == "full_answer_packet_ready"
    assert projection["answer_text"]
    assert not projection["answer_text"].lstrip().startswith("{")
    assert "hardened packet" in projection["answer_text"]
    assert projection["mandatory_caveats"]
    assert projection["prohibited_upgrades"]
    assert projection["prohibited_claims"]
    assert projection["source_ref_presentation"]["presentation_note"].endswith(
        "not citations."
    )
    assert projection["citations_rendered"] is False
    assert kernel.state.author_prose_state["answer_text"] == projection["answer_text"]
    assert kernel.state.author_prose_history == [projection]
    assert kernel.state.projections[AUTHOR_PROSE_FINALIZATION_STAGE] == projection
    _assert_author_boundaries(kernel, projection)


def test_case_b_partial_answer_separates_supported_and_unresolved() -> None:
    kernel = _partial_ready_kernel()

    projection = _author(kernel)

    assert projection["author_prose_status"] == "partial_answer_prose_created"
    assert projection["full_answer_implication_allowed"] is False
    block_types = {block["block_type"] for block in projection["answer_blocks"]}
    assert {"supported_parts", "unresolved_parts"}.issubset(block_types)
    assert projection["supported_component_ids"]
    assert projection["unresolved_component_ids"]
    assert "partial answer" in projection["answer_text"]
    _assert_author_boundaries(kernel, projection)


def test_case_c_blocked_answer_explains_blocker_only() -> None:
    kernel = _blocked_kernel()

    projection = _author(kernel)

    assert projection["author_prose_status"] == "blocked_answer_prose_created"
    assert projection["supported_claims_created"] is False
    assert projection["must_not_answer_component_ids"]
    assert "blocked" in projection["answer_text"].casefold()
    assert all(
        entry["prose_treatment"] != "supported_component"
        for entry in projection["component_prose_entries"]
        if entry.get("must_not_answer") is True
    )
    _assert_author_boundaries(kernel, projection)


def test_case_d_followup_required_does_not_authorize_or_complete_remediation() -> None:
    kernel = _followup_required_kernel()

    projection = _author(kernel)

    assert projection["author_prose_status"] == "followup_required_prose_created"
    assert "follow-up" in projection["answer_text"].casefold()
    assert "does not authorize" in projection["answer_text"]
    assert projection["followup_authorized_by_author_prose"] is False
    assert projection["remediation_completed_claimed"] is False
    _assert_author_boundaries(kernel, projection)


def test_case_e_contested_prose_preserves_disagreement() -> None:
    kernel = _contested_kernel()

    projection = _author(
        kernel,
        policy={"uncertainty_profile": "contested_first"},
    )

    assert projection["author_prose_status"] == "contested_answer_prose_created"
    assert projection["contested_posture_preserved"] is True
    assert projection["supported_claims_created"] is False
    assert "contested" in projection["answer_text"].casefold()
    assert all(
        entry["prose_treatment"] != "supported_component"
        for entry in projection["component_prose_entries"]
    )
    _assert_author_boundaries(kernel, projection)


def test_case_f_insufficient_evidence_prose_creates_no_supported_claims() -> None:
    kernel = _insufficient_kernel()

    projection = _author(kernel)

    assert projection["author_prose_status"] == (
        "insufficient_evidence_prose_created"
    )
    assert projection["supported_claims_created"] is False
    assert projection["supported_component_ids"] == []
    assert "insufficient" in projection["answer_text"].casefold()
    _assert_author_boundaries(kernel, projection)


def test_case_g_not_applicable_no_answer_projection_only() -> None:
    kernel = RunKernel.start(run_id="run:author:not-app", request_id="req:not-app")
    reduce_sufficiency_readiness(run_kernel=kernel)

    projection = _author(kernel)

    assert projection["author_prose_status"] == "not_applicable_no_answer"
    assert projection["fap_status"] == "not_applicable"
    assert "packet_id" not in projection
    assert "packet_digest" not in projection
    assert projection["supported_claims_created"] is False
    assert projection["component_prose_entries"] == []
    assert projection["answer_text"] == "No Answer: No answer is applicable for this run posture. Boundary: This prose does not render citations, satisfy source obligations, or claim product correctness."
    _assert_author_boundaries(kernel, projection)


def test_case_h_policy_knobs_change_form_not_authority() -> None:
    kernel = _full_ready_chain()["kernel"]
    reduce_hardened_final_answer_packet(run_kernel=kernel)

    terse = reduce_author_prose_finalization(
        run_kernel=kernel,
        policy={
            "style_profile": "direct",
            "format_profile": "paragraphs",
            "brevity_profile": "terse",
            "source_pass_through_profile": "minimal_refs",
        },
    ).author_prose_projection
    detailed = reduce_author_prose_finalization(
        run_kernel=kernel,
        policy={
            "style_profile": "research_note",
            "format_profile": "bullets",
            "brevity_profile": "detailed",
            "source_pass_through_profile": "source_appendix",
            "uncertainty_profile": "conservative",
        },
    ).author_prose_projection

    assert terse["answer_text"] != detailed["answer_text"]
    invariant_keys = (
        "fap_status",
        "mandatory_caveats",
        "prohibited_upgrades",
        "citation_eligible",
        "citations_rendered",
        "source_obligation_satisfied",
        "product_correctness_claimed",
        "supported_component_ids",
        "unresolved_component_ids",
        "must_not_answer_component_ids",
    )
    for key in invariant_keys:
        assert terse[key] == detailed[key]
    assert terse["policy_digest"] != detailed["policy_digest"]
    assert kernel.state.author_prose_history == [terse, detailed]


def test_case_i_stale_fap_projection_or_policy_binding_is_rejected() -> None:
    kernel = _full_ready_chain()["kernel"]
    reduce_hardened_final_answer_packet(run_kernel=kernel)
    action = kernel.authorize_author_prose_finalization()
    payload = build_author_prose_finalization_observation_payload(
        action_id=action.action_id,
        action_inputs=action.inputs,
    )
    kernel.state.final_answer_authority_projection = deepcopy(
        kernel.state.final_answer_authority_projection
    )
    kernel.state.final_answer_authority_projection["final_answer_packet_count"] = 99

    with pytest.raises(RunKernelTransitionError, match="stale"):
        kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.AUTHOR_PROSE_FINALIZED,
                status=RunStageStatus.COMPLETED,
                payload=payload,
            )
        )

    assert kernel.state.author_prose_state == {}

    fresh = _full_ready_chain()["kernel"]
    reduce_hardened_final_answer_packet(run_kernel=fresh)
    stale_policy_action = fresh.authorize_author_prose_finalization()
    stale_policy_action.inputs["policy"]["style_profile"] = "technical"
    stale_policy_payload = build_author_prose_finalization_observation_payload(
        action_id=stale_policy_action.action_id,
        action_inputs=stale_policy_action.inputs,
    )
    with pytest.raises(RunKernelTransitionError, match="policy_digest binding is stale"):
        fresh.reduce(
            Observation.from_action(
                stale_policy_action,
                observation_type=ObservationType.AUTHOR_PROSE_FINALIZED,
                status=RunStageStatus.COMPLETED,
                payload=stale_policy_payload,
            )
        )


def test_case_j_closed_surfaces_static_and_runtime_guards() -> None:
    kernel = _full_ready_chain()["kernel"]
    current_answer_contract = deepcopy(kernel.state.current_answer_contract)

    projection = _author(kernel)

    _assert_author_boundaries(kernel, projection)
    assert kernel.state.current_answer_contract == current_answer_contract
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    imports, calls, _classes = _imports_calls_and_classes(RUNTIME_MODULE)
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.final_answer_packet_runtime",
        "core.final_answer_runtime_adapter",
        "core.followup_final_answer_packet_runtime",
        "core.author_execution_runtime",
        "core.authoring",
        "core.runtime_prompt_assembly",
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
        "execute_author_action",
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
    }
    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)
    runtime_text = RUNTIME_MODULE.read_text(encoding="utf-8")
    assert "AUTHOR_EXECUTE" not in runtime_text
    assert "citation_eligible\": True" not in runtime_text
    run_kernel_source = RUN_KERNEL_MODULE.read_text(encoding="utf-8")
    assert "AUTHOR_PROSE_FINALIZE" in run_kernel_source
    assert "author_prose_state" in run_kernel_source
    assert "state.author_observation" not in runtime_text
    assert "state.final_answer_outcome" not in runtime_text


def test_case_k_dogfood_conformance_passes_compliant_prose() -> None:
    kernel = _partial_ready_kernel()
    projection = _author(kernel)

    review = review_author_prose_conformance(
        fap_projection=kernel.state.final_answer_authority_projection,
        author_prose_projection=projection,
        policy=projection["policy_ref"],
    )

    assert review["dogfood_only"] is True
    assert review["production_blocking"] is False
    assert review["review_status"] == "conformance_passed"
    assert review["issue_codes"] == []


def test_case_l_dogfood_conformance_catches_laundering() -> None:
    kernel = _partial_ready_kernel()
    projection = _author(kernel)
    laundered = deepcopy(projection)
    laundered["author_prose_status"] = "full_answer_prose_created"
    laundered["full_answer_implication_allowed"] = True
    laundered["citation_eligible"] = True
    laundered["citations_rendered"] = True
    laundered["source_obligation_satisfied"] = True
    laundered["product_correctness_claimed"] = True
    laundered["component_prose_entries"].append(
        {
            "component_id": projection["must_not_answer_component_ids"][0],
            "prose_treatment": "supported_component",
            "supported_in_prose": True,
            "must_not_answer": True,
        }
    )

    review = review_author_prose_conformance(
        fap_projection=kernel.state.final_answer_authority_projection,
        author_prose_projection=laundered,
        policy=projection["policy_ref"],
    )

    assert review["review_status"] == "laundering_suspected"
    assert "partial_fap_upgraded_to_full_prose" in review["issue_codes"]
    assert "full_answer_implied_from_non_full_fap" in review["issue_codes"]
    assert "must_not_answer_component_presented_as_supported" in review["issue_codes"]
    assert "closed_flag_opened:citation_eligible" in review["issue_codes"]
    assert "closed_flag_opened:product_correctness_claimed" in review["issue_codes"]


def test_output_taxonomy_matches_fap_statuses() -> None:
    assert FAP_TO_AUTHOR_PROSE_STATUS == {
        "full_answer_packet_ready": "full_answer_prose_created",
        "partial_answer_packet_ready": "partial_answer_prose_created",
        "blocked_answer_packet": "blocked_answer_prose_created",
        "followup_required_packet": "followup_required_prose_created",
        "contested_answer_packet": "contested_answer_prose_created",
        "insufficient_evidence_packet": "insufficient_evidence_prose_created",
        "not_applicable": "not_applicable_no_answer",
    }


def test_docs_record_author_prose_only_finalization_posture() -> None:
    docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
    required = (
        "AUTHOR-PROSE-ONLY-FINALIZATION-01",
        "AuthorProseFinalization is the prose-only finalization surface",
        "consumes hardened FAP only",
        "style/format/brevity/source-pass-through/uncertainty",
        "does not call a model or provider",
        "does not execute old Author",
        "does not render citations",
        "does not satisfy source obligations",
        "does not claim product correctness",
        "does not mutate current_answer_contract",
        "does not write canonical output to legacy `author_observation` / `final_answer_outcome`",
        "AuthorProseConformanceReview is dogfood/testing-only",
    )
    for phrase in required:
        assert phrase in docs_text
