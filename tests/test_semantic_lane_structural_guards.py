from __future__ import annotations

import ast
from pathlib import Path

from core.ordinary_semantic_producer_runtime import (
    SKIP_REASON_ACCEPTED_ANSWER_CONTRACT_MISSING,
    SKIP_REASON_ADMISSION_PREFLIGHT_FAILED,
    SKIP_REASON_BINDABLE_PASSAGE_MISSING,
    SKIP_REASON_CANONICAL_SEMANTIC_STATE_ALREADY_PRESENT,
    SKIP_REASON_COMPONENT_CAP_EXCEEDED,
    SKIP_REASON_CONTRACT_PREFLIGHT_FAILED,
    SKIP_REASON_COVERAGE_PREFLIGHT_FAILED,
    SKIP_REASON_MULTIPART_ASSESSMENT,
    SKIP_REASON_PREFLIGHT_FAILED,
    SKIP_REASON_QUERY_SHAPE_CLASSIFIER_UNAVAILABLE,
)

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
PRODUCER_MODULE = CORE / "ordinary_semantic_producer_runtime.py"
PIPELINE = CORE / "pipeline_orchestrator.py"
RUN_KERNEL = CORE / "run_kernel.py"
SEMANTIC_BUNDLE_HELPER = CORE / "semantic_producer_bundle_commit_runtime.py"
FAP = CORE / "final_answer_packet.py"
FAP_ADAPTER = CORE / "final_answer_runtime_adapter.py"
FAP_RUNTIME = CORE / "final_answer_packet_runtime.py"
AUTHOR_RUNTIME = CORE / "author_execution_runtime.py"
RUNTIME_PROMPT_ASSEMBLY = CORE / "runtime_prompt_assembly.py"
RETRIEVAL = CORE / "retrieval.py"
RETRIEVAL_DISPATCH = CORE / "retrieval_dispatch_runtime.py"
SEARCH_PROVIDERS = CORE / "search_providers.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(_source(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _assert_tokens_absent(path: Path, tokens: tuple[str, ...]) -> None:
    source = _source(path)
    for token in tokens:
        assert token not in source, f"{token!r} leaked into {path}"


def test_run_kernel_owns_atomic_semantic_bundle_commit_boundary() -> None:
    source = _source(RUN_KERNEL)
    tree = ast.parse(source)
    for token in (
        "semantic_producer_history",
        "pre_sufficiency_semantic",
        "semantic_ledger_bridge",
    ):
        assert token not in source
    assert "commit_semantic_producer_bundle" in source
    assert "SEMANTIC_PRODUCER_BUNDLE_COMMIT" in source
    assert "_stage_semantic_producer_bundle_commit" not in source

    run_kernel_class = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "RunKernel"
    )
    commit_method = next(
        node
        for node in run_kernel_class.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "commit_semantic_producer_bundle"
    )
    method_source = ast.get_source_segment(source, commit_method) or ""
    assert "stage_semantic_producer_bundle_commit(" in method_source
    assert "self._apply_semantic_producer_bundle_commit(" in method_source
    for token in (
        "build_initial_answer_contract_acceptance_state",
        "build_semantic_observation_admission_state",
        "build_component_coverage_reduction_state",
    ):
        assert token not in method_source

    helper_source = _source(SEMANTIC_BUNDLE_HELPER)
    assert "stage_semantic_producer_bundle_commit" in helper_source
    assert "build_initial_answer_contract_acceptance_state" in helper_source
    assert "build_semantic_observation_admission_state" in helper_source
    assert "build_component_coverage_reduction_state" in helper_source


def test_ordinary_semantic_producer_keeps_closed_runtime_boundaries() -> None:
    source = _source(PRODUCER_MODULE)
    assert "execute_ordinary_semantic_producer_handoff_from_scope" in source
    assert "SKIP_REASON_ACCEPTED_ANSWER_CONTRACT_MISSING" in source
    assert "commit_semantic_producer_bundle(" not in source

    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.author_execution_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.retrieval_dispatch_runtime",
        "core.retrieval",
        "openai",
        "requests",
        "httpx",
    }
    assert _imports(PRODUCER_MODULE).isdisjoint(forbidden_imports)

    for token in (
        "semantic_producer_history",
        "pre_sufficiency_semantic",
        "semantic_ledger_bridge",
        "run_kernel.reduce(",
        "ask_model(",
        "fetch_linkup_precision_block",
        "run_scout",
        "followup_author",
        "provider_payload",
        "raw_prompt",
        "Sample Relief Program",
        "Example Program",
        "Example Permit",
        "Acme Widget",
        "official rule wording",
        "state the bounded official answer",
    ):
        assert token not in source


def test_semantic_producer_has_no_compensating_rollback_paths() -> None:
    tree = ast.parse(_source(PRODUCER_MODULE))
    forbidden_tokens = ("rollback", "revert", "undo_semantic", "cleanup_reduce")
    forbidden_names = {"rollback", "revert", "undo_semantic"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.casefold()
            for token in forbidden_tokens:
                assert token not in lowered
        if isinstance(node, ast.Name):
            assert node.id.casefold() not in forbidden_names


def test_semantic_skip_reasons_remain_return_only_in_producer_core() -> None:
    skip_reason_values = (
        SKIP_REASON_QUERY_SHAPE_CLASSIFIER_UNAVAILABLE,
        SKIP_REASON_MULTIPART_ASSESSMENT,
        SKIP_REASON_BINDABLE_PASSAGE_MISSING,
        SKIP_REASON_CONTRACT_PREFLIGHT_FAILED,
        SKIP_REASON_ADMISSION_PREFLIGHT_FAILED,
        SKIP_REASON_COVERAGE_PREFLIGHT_FAILED,
        SKIP_REASON_COMPONENT_CAP_EXCEEDED,
        SKIP_REASON_PREFLIGHT_FAILED,
        SKIP_REASON_CANONICAL_SEMANTIC_STATE_ALREADY_PRESENT,
        SKIP_REASON_ACCEPTED_ANSWER_CONTRACT_MISSING,
    )
    allowed_nonproducer_error_codes: set[tuple[Path, str]] = set()
    for path in CORE.rglob("*.py"):
        if path == PRODUCER_MODULE:
            continue
        source = _source(path)
        assert "skipped_reason" not in source, str(path)
        for value in skip_reason_values:
            if (path, value) in allowed_nonproducer_error_codes:
                continue
            assert value not in source, str(path)


def test_orchestrator_semantic_producer_callsites_are_bounded() -> None:
    source = _source(PIPELINE)
    assert "execute_ordinary_semantic_producer_handoff_from_scope(" not in source
    selector = "execute_ordinary_semantic_or_multicomponent_handoff_from_scope("
    assert source.count(selector) == 4
    assert "allow_searchos_component_receiver=True" in source
    assert (
        "if not run_kernel.state.initial_answer_contract:\n"
        "            final_top_evidence = list(all_passages)\n"
        f"            {selector}"
        in source
    )
    early_selector = source.index(selector)
    assert "execute_selected_lane=False" in source[early_selector : early_selector + 300]


def test_semantic_phase_fixture_labels_stay_out_of_closed_runtime_surfaces() -> None:
    for path in (FAP, FAP_ADAPTER, FAP_RUNTIME, AUTHOR_RUNTIME):
        _assert_tokens_absent(path, ("AG-SEM-11C", "Sample Relief Program"))

    for path in (
        PIPELINE,
        RUNTIME_PROMPT_ASSEMBLY,
        RETRIEVAL,
        RETRIEVAL_DISPATCH,
        SEARCH_PROVIDERS,
    ):
        _assert_tokens_absent(path, ("AG-SEM-MULTI-01", "Example Permit"))

    for path in (FAP, FAP_ADAPTER, RUNTIME_PROMPT_ASSEMBLY):
        _assert_tokens_absent(path, ("AG-SEM-PROD-02", "Acme Widget"))
