from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from core.run_kernel import SUFFICIENCY_READINESS_STAGE
from core.specialist_source_bound_calculation_runtime import (
    reduce_specialist_source_bound_calculation,
)
from core.sufficiency_readiness_runtime import (
    READINESS_STATUSES,
    reduce_sufficiency_readiness,
)
from tests.test_ag_analyst_evidence_relative_report_01 import _analysis_fixture
from tests.test_ag_scrutineer_review_01 import (
    _gap_chain,
    _reduce_review,
    _review_record,
    _supported_chain,
)
from tests.test_ag_specialist_source_bound_calculation_01 import (
    _input as _specialist_input,
)
from tests.test_ag_specialist_source_bound_calculation_01 import (
    _record as _specialist_record,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "sufficiency_readiness_runtime.py"
RUN_KERNEL_MODULE = ROOT / "core" / "run_kernel.py"
DOCS = (
    ROOT / "docs" / "architecture" / "AG_SUFFICIENCY_PARTIAL_ANSWER_READINESS_01.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
)


def _decide(kernel: Any, *, mode: str = "Balanced") -> dict[str, Any]:
    return reduce_sufficiency_readiness(run_kernel=kernel, mode=mode).readiness_projection


def _component_id(kernel: Any) -> str:
    return kernel.state.current_answer_contract["accepted_answer_component_refs"][0][
        "component_id"
    ]


def _add_component(
    kernel: Any,
    *,
    component_id: str,
    required: bool,
) -> dict[str, Any]:
    component = deepcopy(
        kernel.state.current_answer_contract["accepted_answer_component_refs"][0]
    )
    component["component_id"] = component_id
    component["component_revision"] = "1"
    component["component_digest"] = f"digest:{component_id}"
    component["requirement_posture"] = "required" if required else "optional"
    component["materiality"] = "material" if required else "non_material"
    component["mandatory_caveats"] = [
        f"Component {component_id} is unresolved in the readiness preview."
    ]
    component["prohibited_upgrades"] = [
        f"Do not upgrade component {component_id} beyond supported readiness."
    ]
    refs = kernel.state.current_answer_contract["accepted_answer_component_refs"]
    refs.append(component)
    kernel.state.current_answer_contract["accepted_answer_component_count"] = len(refs)
    return component


def _assert_readiness_closed(kernel: Any, projection: Mapping[str, Any]) -> None:
    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.sufficiency_judgment_projection == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert projection["sufficiency_readiness_is_product_authority"] is False
    assert projection["final_answer_packet_created"] is False
    assert projection["author_input_created"] is False
    assert projection["citation_eligible"] is False
    assert projection["source_obligation_satisfied"] is False
    assert projection["product_correctness_claimed"] is False
    for value in projection["closed_surface_flags"].values():
        assert value is False


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


def test_case_a_full_readiness_reduces_through_runkernel_without_fap_author() -> None:
    chain = _supported_chain()
    kernel = chain["kernel"]
    current_contract_before = deepcopy(kernel.state.current_answer_contract)
    calculation = _specialist_record(chain)
    reduce_specialist_source_bound_calculation(
        run_kernel=kernel,
        specialist_source_bound_calculation_record=calculation,
    )
    review = _review_record(
        chain,
        mode="Balanced",
        red_flag_context=True,
        specialist_source_bound_calculation_projection=(
            kernel.state.specialist_source_bound_calculation_projection
        ),
        specialist_source_bound_calculation_history=(
            kernel.state.specialist_source_bound_calculation_history
        ),
    )
    _reduce_review(chain, review)

    projection = _decide(kernel)
    component = projection["component_readiness_map"][_component_id(kernel)]

    assert projection["owner"] == "RunKernel.SufficiencyReadiness"
    assert projection["canonical_state"] is True
    assert projection["final_readiness_status"] == "full_answer_ready"
    assert component["component_readiness_status"] == "full_answer_ready"
    assert projection["scrutineer_review_refs"]
    assert projection["specialist_calculation_refs"]
    assert kernel.state.projections[SUFFICIENCY_READINESS_STAGE] == projection
    assert kernel.state.current_answer_contract == current_contract_before
    _assert_readiness_closed(kernel, projection)


def test_case_b_partial_readiness_names_noncritical_unresolved_component() -> None:
    chain = _supported_chain()
    kernel = chain["kernel"]
    optional = _add_component(
        kernel,
        component_id="component:optional-context",
        required=False,
    )

    projection = _decide(kernel)
    optional_entry = projection["component_readiness_map"][optional["component_id"]]

    assert projection["final_readiness_status"] == "partial_answer_ready"
    assert projection["supported_component_refs"][0]["component_id"] == (
        _component_id(kernel)
    )
    assert optional_entry["required_or_material"] is False
    assert optional_entry["component_readiness_status"] == "insufficient_evidence"
    assert optional["component_id"] in " ".join(projection["mandatory_caveats"])
    assert optional["component_id"] in " ".join(projection["prohibited_upgrades"])
    assert projection["fap_handoff_preview"]["readiness_status"] == (
        "partial_answer_ready"
    )
    _assert_readiness_closed(kernel, projection)


def test_case_c_required_component_missing_coverage_blocks_false_partial() -> None:
    chain = _supported_chain()
    kernel = chain["kernel"]
    required = _add_component(
        kernel,
        component_id="component:required-gap",
        required=True,
    )

    projection = _decide(kernel)
    required_entry = projection["component_readiness_map"][required["component_id"]]

    assert projection["final_readiness_status"] == "blocked"
    assert required_entry["required_or_material"] is True
    assert required_entry["component_readiness_status"] == "insufficient_evidence"
    assert projection["supported_component_refs"]
    assert projection["missing_component_refs"]
    assert projection["final_readiness_status"] not in {
        "full_answer_ready",
        "partial_answer_ready",
    }
    _assert_readiness_closed(kernel, projection)


def test_case_d_material_gap_with_available_followup_is_followup_required() -> None:
    chain = _gap_chain("currentness_concern")
    kernel = chain["kernel"]
    review = _review_record(
        chain,
        mode="Balanced",
        followup_search_intent_packet=chain["followup_packet"],
    )
    review_result = _reduce_review(chain, review)

    projection = _decide(kernel)

    assert review_result.review_projection["review_outcome"] == (
        "remediation_required"
    )
    assert projection["followup_budget_posture"] == "available"
    assert projection["final_readiness_status"] == "followup_required"
    assert projection["followup_required_component_refs"]
    assert kernel.state.projections.get("followup_search_authorization") is None
    _assert_readiness_closed(kernel, projection)


def test_case_e_contested_specialist_or_review_posture_wins() -> None:
    chain = _supported_chain()
    kernel = chain["kernel"]
    contested = _specialist_record(
        chain,
        calculation_kind="sum",
        inputs=[
            _specialist_input(chain, label="current", value=10),
            _specialist_input(
                chain,
                label="stale",
                value=15,
                currentness="unknown",
                source_class="weak_secondary",
            ),
        ],
    )
    assert contested["calculation_status"] == "contested"
    reduce_specialist_source_bound_calculation(
        run_kernel=kernel,
        specialist_source_bound_calculation_record=contested,
    )

    projection = _decide(kernel)

    assert projection["final_readiness_status"] == "contested"
    assert projection["contested_component_refs"]
    assert "Specialist calculation is contested" in (
        projection["component_readiness_map"][_component_id(kernel)]["blockers"]
    )
    _assert_readiness_closed(kernel, projection)


def test_case_f_custody_without_admitted_support_is_insufficient_evidence() -> None:
    kernel, _fetch_read_packet, ledger_projection = _analysis_fixture(
        readable_count=1,
        failed_count=0,
    )
    assert ledger_projection["fetch_read_candidate_custody"]["custody_record_count"]
    assert kernel.state.component_coverage_projection == {}

    projection = _decide(kernel)

    assert projection["final_readiness_status"] == "insufficient_evidence"
    assert projection["supported_component_refs"] == []
    assert projection["missing_component_refs"]
    _assert_readiness_closed(kernel, projection)


def test_case_g_stale_wrong_contract_coverage_is_ignored() -> None:
    chain = _supported_chain()
    kernel = chain["kernel"]
    component = kernel.state.current_answer_contract["accepted_answer_component_refs"][0]
    component["component_digest"] = "digest:current-contract-has-moved"

    projection = _decide(kernel)
    entry = projection["component_readiness_map"][component["component_id"]]

    assert projection["final_readiness_status"] == "insufficient_evidence"
    assert entry["coverage_refs"] == []
    assert entry["component_readiness_status"] == "insufficient_evidence"
    assert "no current-contract ComponentCoverage ref" in entry["blockers"]
    _assert_readiness_closed(kernel, projection)


def test_case_h_closed_surface_static_guards_and_runtime_flags() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.author_execution_runtime",
        "core.authoring",
        "openai",
        "requests",
        "httpx",
        "urllib",
        "dotenv",
        "subprocess",
        "importlib",
    }
    forbidden_calls = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "run_pipeline",
        "call_broker",
        "invoke_broker",
        "search_web",
        "retrieve",
        "dispatch_retrieval",
        "fetch_url",
        "fetch_page",
        "read_url",
        "execute_author",
        "execute_author_action",
        "create_final_answer_packet",
        "derive_author_input_payload",
        "ask_model",
        "Popen",
        "run",
    }
    imports, calls, _classes = _imports_calls_and_classes(RUNTIME_MODULE)
    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)

    chain = _supported_chain()
    projection = _decide(chain["kernel"])
    _assert_readiness_closed(chain["kernel"], projection)


def test_case_i_no_packet_sprawl_and_canonical_runkernel_projection() -> None:
    chain = _supported_chain()
    kernel = chain["kernel"]
    projection = _decide(kernel)
    _imports, _calls, classes = _imports_calls_and_classes(RUNTIME_MODULE)

    assert READINESS_STATUSES == {
        "full_answer_ready",
        "partial_answer_ready",
        "blocked",
        "followup_required",
        "contested",
        "insufficient_evidence",
        "not_applicable",
    }
    assert not any(name.endswith("Packet") for name in classes)
    assert kernel.state.sufficiency_readiness_state["proposal_packet"] is False
    assert kernel.state.sufficiency_readiness_state["durable_packet"] is False
    assert kernel.state.sufficiency_readiness_projection == projection
    assert kernel.state.projections[SUFFICIENCY_READINESS_STAGE] == projection
    run_kernel_source = RUN_KERNEL_MODULE.read_text(encoding="utf-8")
    assert "SUFFICIENCY_READINESS_DECIDE" in run_kernel_source
    assert "SUFFICIENCY_READINESS_DECIDED" in run_kernel_source
    assert "sufficiency_readiness_projection" in run_kernel_source


def test_docs_record_sufficiency_readiness_phase_posture() -> None:
    docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
    required = (
        "AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01",
        "pre-FAP readiness reducer",
        "SufficiencyReadiness is RunKernel-owned",
        "component-level and answer-level readiness",
        "full_answer_ready",
        "partial_answer_ready",
        "followup_required",
        "insufficient_evidence",
        "not_applicable",
        "does not create FinalAnswerPacket",
        "Author input",
        "citation eligibility",
        "source-obligation satisfaction",
        "current_answer_contract mutation",
        "live calls",
        "product correctness",
        "AG-FINAL-ANSWER-PACKET-HARDENING-01",
        "Author prose-only finalization comes next",
        "AG-92C Sufficiency/FAP",
        "AG-96/FAP/Author surfaces remain legacy/passive/closed",
    )
    for phrase in required:
        assert phrase in docs_text
