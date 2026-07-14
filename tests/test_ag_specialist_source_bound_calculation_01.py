from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from core.run_kernel import SPECIALIST_SOURCE_BOUND_CALCULATION_STAGE
from core.specialist_source_bound_calculation_runtime import (
    SUPPORTED_OPERATORS,
    build_specialist_source_bound_calculation_record,
    reduce_specialist_source_bound_calculation,
)
from tests.test_ag_component_coverage_reliability_proof_01 import (
    _assert_downstream_closed,
)
from tests.test_ag_scrutineer_review_01 import (
    _reduce_review,
    _review_record,
    _supported_chain,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "specialist_source_bound_calculation_runtime.py"
RUN_KERNEL_MODULE = ROOT / "core" / "run_kernel.py"
SCRUTINEER_MODULE = ROOT / "core" / "scrutineer_review_runtime.py"
DOCS = (
    ROOT / "docs" / "architecture" / "AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
)


def _component_ref(chain: Mapping[str, Any]) -> dict[str, Any]:
    return dict(
        chain["kernel"].state.initial_answer_contract[
            "accepted_answer_component_refs"
        ][0]
    )


def _source_ref(chain: Mapping[str, Any]) -> dict[str, Any]:
    admission = chain["kernel"].state.semantic_observation_admission_projection
    coverage = chain["kernel"].state.component_coverage_projection
    analysis_packet = chain["analysis_packet"]
    content_ref = (admission.get("content_ref_records") or [{}])[0]
    return {
        "evidence_ledger_ref": analysis_packet["evidence_ledger_ref"],
        "content_ref": {
            "content_ref_id": content_ref.get("content_ref_id"),
            "content_digest": content_ref.get("content_digest"),
        },
        "semantic_observation_ref": {
            "observation_id": admission["observation_id"],
            "observation_digest": admission["observation_digest"],
        },
        "analysis_packet_ref": {
            "packet_id": analysis_packet["packet_id"],
            "packet_digest": analysis_packet["packet_digest"],
        },
        "component_ref": {
            "component_id": coverage["answer_component_id"],
            "component_digest": coverage["component_digest"],
        },
    }


def _input(
    chain: Mapping[str, Any],
    *,
    label: str,
    value: Any,
    unit: str | None = "USD",
    source_bound: bool = True,
    currentness: str = "current",
    source_class: str = "current_primary_or_official",
    conflict: str = "none",
    role: str | None = None,
    pair_id: str | None = None,
    fixture_bound: bool = False,
) -> dict[str, Any]:
    component = _component_ref(chain)
    return {
        "label": label,
        "numeric_value": value,
        "unit": unit,
        "scale": "ones",
        "source_bound": source_bound,
        "fixture_bound": fixture_bound,
        "source_bound_ref": _source_ref(chain),
        "fixture_ref": {"fixture": "explicit_weight"} if fixture_bound else {},
        "component_id": component["component_id"],
        "currentness_posture": currentness,
        "source_class_posture": source_class,
        "conflict_posture": conflict,
        "role": role,
        "pair_id": pair_id,
        "caveats": ["fixture numeric input; no answer authority"],
    }


def _record(
    chain: Mapping[str, Any],
    *,
    calculation_kind: str = "difference",
    inputs: list[dict[str, Any]] | None = None,
    output_unit: str | None = None,
) -> dict[str, Any]:
    kernel = chain["kernel"]
    return build_specialist_source_bound_calculation_record(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        calculation_kind=calculation_kind,
        formula_label=f"fixture {calculation_kind}",
        output_unit=output_unit,
        input_records=inputs
        or [
            _input(chain, label="gross", value=42),
            _input(chain, label="offset", value=12),
        ],
        reviewed_artifact_refs={
            "analysis_packet_ref": {
                "packet_id": chain["analysis_packet"]["packet_id"],
                "packet_digest": chain["analysis_packet"]["packet_digest"],
            }
        },
    )


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


def test_runkernel_reduces_successful_source_bound_calculation() -> None:
    chain = _supported_chain()
    kernel = chain["kernel"]
    current_contract_before = deepcopy(kernel.state.current_answer_contract)
    coverage_history_count = len(kernel.state.component_coverage_history)
    record = _record(chain)

    result = reduce_specialist_source_bound_calculation(
        run_kernel=kernel,
        specialist_source_bound_calculation_record=record,
    )
    projection = result.calculation_projection

    assert projection["owner"] == "RunKernel.SpecialistSourceBoundCalculation"
    assert projection["canonical_state"] is True
    assert projection["calculation_status"] == "computed"
    assert projection["deterministic_operator"] == "difference"
    assert projection["result"]["numeric_value"] == 30
    assert projection["result"]["unit"] == "USD"
    assert projection["input_records"][0]["source_bound"] is True
    assert projection["input_records"][0]["source_bound_ref"]["content_ref"]
    assert projection["reviewed_artifact_refs"]["semantic_observation_refs"]
    assert kernel.state.projections[SPECIALIST_SOURCE_BOUND_CALCULATION_STAGE] == (
        projection
    )
    assert len(kernel.state.component_coverage_history) == coverage_history_count
    assert kernel.state.current_answer_contract == current_contract_before
    for value in projection["closed_surface_flags"].values():
        assert value is False
    _assert_downstream_closed(kernel)


def test_successful_calculation_is_not_downstream_answer_authority() -> None:
    chain = _supported_chain()
    kernel = chain["kernel"]
    reduce_specialist_source_bound_calculation(
        run_kernel=kernel,
        specialist_source_bound_calculation_record=_record(chain),
    )
    projection = kernel.state.specialist_source_bound_calculation_projection

    assert projection["specialist_is_product_authority"] is False
    assert projection["component_coverage_reduced"] is False
    assert projection["sufficiency_decided"] is False
    assert projection["final_answer_packet_created"] is False
    assert projection["author_input_created"] is False
    assert projection["citation_eligible"] is False
    assert projection["source_obligation_satisfied"] is False
    assert projection["product_correctness_claimed"] is False
    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}


def test_blocked_and_invalid_calculations_preserve_blockers_without_computing() -> None:
    chain = _supported_chain()
    denominator_zero = _record(
        chain,
        calculation_kind="percentage",
        inputs=[
            _input(chain, label="part", value=10),
            _input(chain, label="whole", value=0),
        ],
    )
    invalid = _record(
        chain,
        calculation_kind="sum",
        inputs=[
            _input(chain, label="numeric string", value="10"),
            _input(chain, label="valid", value=2),
        ],
    )

    assert denominator_zero["calculation_status"] == "blocked"
    assert "numeric_value" not in denominator_zero["result"]
    assert {
        blocker["blocker_kind"] for blocker in denominator_zero["blockers"]
    } == {"denominator_zero"}
    assert invalid["calculation_status"] == "invalid_input"
    assert "non_numeric_input" in {
        blocker["blocker_kind"] for blocker in invalid["blockers"]
    }

    result = reduce_specialist_source_bound_calculation(
        run_kernel=chain["kernel"],
        specialist_source_bound_calculation_record=denominator_zero,
    )
    assert result.calculation_projection["calculation_status"] == "blocked"
    _assert_downstream_closed(chain["kernel"])


def test_contested_stale_or_weak_input_does_not_cleanly_compute() -> None:
    chain = _supported_chain()
    record = _record(
        chain,
        calculation_kind="sum",
        inputs=[
            _input(chain, label="current", value=10),
            _input(
                chain,
                label="stale",
                value=15,
                currentness="unknown",
                source_class="weak_secondary",
            ),
        ],
    )
    assert record["calculation_status"] == "contested"
    assert "numeric_value" not in record["result"]
    assert {
        blocker["blocker_kind"] for blocker in record["blockers"]
    } == {"stale_input", "weak_source_class"}

    reduce_specialist_source_bound_calculation(
        run_kernel=chain["kernel"],
        specialist_source_bound_calculation_record=record,
    )
    review = _review_record(
        chain,
        mode="Balanced",
        red_flag_context=True,
        specialist_source_bound_calculation_projection=(
            chain["kernel"].state.specialist_source_bound_calculation_projection
        ),
    )
    result = _reduce_review(chain, review)
    issue_kinds = {
        issue["issue_kind"] for issue in result.review_projection["issues"]
    }
    assert "currentness_unresolved" in issue_kinds


def test_supported_operator_set_and_weighted_average_are_deterministic() -> None:
    chain = _supported_chain()
    assert SUPPORTED_OPERATORS == {
        "sum",
        "difference",
        "product",
        "ratio",
        "percentage",
        "percentage_point_difference",
        "simple_rate",
        "weighted_average",
    }
    record = _record(
        chain,
        calculation_kind="weighted_average",
        inputs=[
            _input(chain, label="value a", value=10, role="value", pair_id="a"),
            _input(
                chain,
                label="weight a",
                value=2,
                unit="weight",
                role="weight",
                pair_id="a",
                fixture_bound=True,
            ),
            _input(chain, label="value b", value=20, role="value", pair_id="b"),
            _input(
                chain,
                label="weight b",
                value=1,
                unit="weight",
                role="weight",
                pair_id="b",
                fixture_bound=True,
            ),
        ],
    )

    assert record["calculation_status"] == "computed"
    assert record["result"]["numeric_value_text"] == "13.33333333333333333333333333"
    assert record["result"]["unit"] == "USD"


def test_scrutineer_can_review_specialist_posture_without_authority_transfer() -> None:
    chain = _supported_chain()
    kernel = chain["kernel"]
    clean = _record(chain)
    reduce_specialist_source_bound_calculation(
        run_kernel=kernel,
        specialist_source_bound_calculation_record=clean,
    )
    clean_review = _review_record(
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
    clean_result = _reduce_review(chain, clean_review)

    assert clean_result.review_projection["review_outcome"] == "signed_off"
    refs = clean_result.review_projection["reviewed_artifact_refs"][
        "specialist_source_bound_calculation_refs"
    ]
    assert refs[0]["scrutineer_recalculates"] is False
    assert refs[0]["scrutineer_authorizes_calculation"] is False

    blocked_chain = _supported_chain()
    blocked = _record(
        blocked_chain,
        calculation_kind="ratio",
        inputs=[
            _input(blocked_chain, label="unbound", value=3, source_bound=False),
            _input(blocked_chain, label="denominator", value=2),
        ],
    )
    reduce_specialist_source_bound_calculation(
        run_kernel=blocked_chain["kernel"],
        specialist_source_bound_calculation_record=blocked,
    )
    blocked_review = _review_record(
        blocked_chain,
        mode="Balanced",
        red_flag_context=True,
        specialist_source_bound_calculation_projection=(
            blocked_chain[
                "kernel"
            ].state.specialist_source_bound_calculation_projection
        ),
    )
    blocked_result = _reduce_review(blocked_chain, blocked_review)
    issue_kinds = {
        issue["issue_kind"] for issue in blocked_result.review_projection["issues"]
    }
    assert blocked_result.review_projection["review_outcome"] == (
        "remediation_required"
    )
    assert "missing_source_bound_lineage" in issue_kinds
    assert blocked_chain["kernel"].state.sufficiency_judgment == {}
    assert blocked_chain["kernel"].state.final_answer_packet == {}


def test_static_guards_keep_specialist_out_of_closed_surfaces() -> None:
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
    imports, calls, classes = _imports_calls_and_classes(RUNTIME_MODULE)
    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)
    assert not any(name.endswith("Packet") for name in classes)

    run_kernel_source = RUN_KERNEL_MODULE.read_text(encoding="utf-8")
    assert "SPECIALIST_SOURCE_BOUND_CALCULATION_REDUCE" in run_kernel_source
    assert "SPECIALIST_SOURCE_BOUND_CALCULATION_REDUCED" in run_kernel_source
    scrutineer_source = SCRUTINEER_MODULE.read_text(encoding="utf-8")
    assert "specialist_source_bound_calculation_refs" in scrutineer_source
    assert "pipeline_orchestrator" not in RUNTIME_MODULE.read_text(encoding="utf-8")


def test_docs_record_specialist_source_bound_calculation_posture() -> None:
    docs_text = " ".join(
        "\n".join(path.read_text(encoding="utf-8") for path in DOCS).split()
    )
    required = (
        "Quantitative Specialist Product Activation",
        "Installed runtime class: quantitative-specialist-product-activation-s1",
        "quantitative_specialist_proposal_contract.v1",
        "same declarative facts build the model-visible contract",
        "structured candidate record as primary",
        "Missing facts remain `unknown`",
        "two-hop proof",
        "legacy RunKernel calculation reducer remains compatibility support only",
        "The Specialist cannot validate or admit its own result",
        "next roadmap checkpoint is separately licensed quantitative live validation",
    )
    for phrase in required:
        assert phrase in docs_text
