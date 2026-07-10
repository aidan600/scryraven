from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
DOCS = ROOT / "docs"

AGENTS_DOC = ROOT / "AGENTS.md"
QUARANTINE_DOC = DOCS / "architecture" / "AG_CURRENT_PATH_QUARANTINE_01.md"
CURRENT_STATE_DOC = DOCS / "architecture" / "SCRYRAVEN_CURRENT_STATE.md"
RUN_CONTRACT_DOC = DOCS / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md"
CODEX_GUIDANCE_DOC = DOCS / "codex" / "CODEX_GUIDANCE_MAP.md"
PROOF_CLASS_DOC = DOCS / "codex" / "PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md"
VALIDATION_BUCKETS_DOC = DOCS / "codex" / "VALIDATION_BUCKETS.md"
PHASE_TEMPLATE_DOC = DOCS / "codex" / "PHASE_BRIEF_TEMPLATE.md"
PHASE_ADDENDA_DOC = DOCS / "codex" / "PHASE_BRIEF_ADDENDA.md"
PLAYBOOK_DOC = DOCS / "codex" / "ARCHITECTURE_GROOVE_PLAYBOOK.md"
TEST_CLASSIFICATION_DOC = DOCS / "codex" / "TEST_CLASSIFICATION_LIBRARY.md"

AUTHOR_PROSE_RUNTIME = CORE / "author_prose_finalization_runtime.py"
RUN_KERNEL = CORE / "run_kernel.py"

CURRENT_GUIDANCE_DOCS = (
    AGENTS_DOC,
    QUARANTINE_DOC,
    CODEX_GUIDANCE_DOC,
    PROOF_CLASS_DOC,
    VALIDATION_BUCKETS_DOC,
    PHASE_TEMPLATE_DOC,
    PHASE_ADDENDA_DOC,
    PLAYBOOK_DOC,
    TEST_CLASSIFICATION_DOC,
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collapsed(value: str) -> str:
    return " ".join(value.split())


def _sym(*parts: str) -> str:
    return "".join(parts)


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(_source(path))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
    return imported, called


def test_current_guidance_retired_prove_mode_and_uses_bpr() -> None:
    combined = "\n".join(_source(path) for path in CURRENT_GUIDANCE_DOCS)
    collapsed = _collapsed(combined)

    required = (
        "Build / Proof / Repair is the active phase operating system",
        "Prove Mode\" is retired as a global workflow label",
        "Proof is only a phase mode under Build / Proof / Repair",
        "mandatory next Build/product checkpoint",
        "Skeptical outside-reviewer question",
        "Is this finally building the app, or is it building convincing apparatus around the app?",
        "a nice collection of harnesses",
    )
    for phrase in required:
        assert phrase in combined or phrase in collapsed

    assert "Architecture Groove / Prove Mode, Path B approved" not in combined


def test_surface_vocabulary_retires_protected_as_active_control_term() -> None:
    combined = "\n".join(_source(path) for path in CURRENT_GUIDANCE_DOCS)
    collapsed = _collapsed(combined)

    required = (
        "target surface",
        "high-custody surface",
        "closed-this-phase surface",
        "historical surface",
        "strangler target",
        "licensed surface",
        "Protected\" is retired as active phase-control vocabulary",
        "call it a high-custody target or strangler target, not protected",
    )
    for phrase in required:
        assert phrase in combined or phrase in collapsed

    active_forbidden = (
        "closed/protected unless separately licensed",
        "protected surface guarded",
        "Protected surface guarded",
    )
    for phrase in active_forbidden:
        assert phrase not in combined


def test_current_authority_is_distinguished_from_product_consumed_path() -> None:
    combined = "\n".join(_source(path) for path in CURRENT_GUIDANCE_DOCS)
    collapsed = _collapsed(combined)
    registry = _source(QUARANTINE_DOC)

    required = (
        "current internal authority path",
        "current product-consumed path",
        "fixture-only proof",
        "offline harness / proof-only harness",
        "integration-staging harness",
        "product-facing dry-run proof",
        "live product path",
        "historical/proof-only debt",
        "Use current product-consumed path only when ordinary product/CLI/app flow actually consumes the behavior",
    )
    for phrase in required:
        assert phrase in combined or phrase in collapsed

    assert "SearchResultCandidatePacket" in registry
    assert "FetchReadContentPacket / SanitizedContentReference" in registry
    assert "AuthorProseFinalization" in registry
    assert "current product-consumed path | fixture-only proof" not in registry
    assert "fixture-only proof | current product-consumed path" not in registry
    assert "offline harness | current product-consumed path" not in registry


def test_harness_labels_deadlines_and_forbidden_substitutes_are_required() -> None:
    combined = "\n".join(_source(path) for path in CURRENT_GUIDANCE_DOCS)
    collapsed = _collapsed(combined)

    required = (
        "Harness label:",
        "PRODUCT-PATH-REGRESSION",
        "SEAM-DIAGNOSTIC",
        "INTEGRATION-STAGING",
        "EXPLORATORY-PROOF-ONLY",
        "SHADOW-PRODUCT-HARNESS",
        "Ordinary product path guarded or fed:",
        "Runtime consumer:",
        "Integration deadline:",
        "Exit condition:",
        "Why this is not a shadow product path:",
        "Forbidden interpretation:",
        "A harness created in phase N should be consumed",
        "After N+2, unconsumed harness/proof scaffolding is historical/proof-only debt",
        "Forbidden substitute outputs:",
        "harness-only path",
        "fixture-only path",
        "proof-only script",
        "replay-only path",
        "packet-only artifact",
        "projection-only artifact",
        "docs-only doctrine",
        "shadow vertical slice",
        "Ordinary entrypoint:",
        "User-style demonstration input:",
        "Product-path pass condition:",
        "Product-path fail condition:",
    )
    for phrase in required:
        assert phrase in combined or phrase in collapsed


def test_current_path_registry_classifies_required_surfaces() -> None:
    text = _source(QUARANTINE_DOC)
    collapsed = _collapsed(text)
    required_phrases = (
        "Proof class: `docs_only` plus phase-focused docs-posture/static guards.",
        "Product-facing progress type: quarantine/docs-process work.",
        "Actual user-facing app delta: none.",
        "current mandatory next product checkpoint is tightly scoped limited live validation",
        "current internal authority path",
        "current product-consumed path",
        "current passive/supporting projection",
        "fixture-only proof",
        "offline harness / proof-only harness",
        "integration-staging harness",
        "live-search-only validation",
        "product-facing dry-run proof",
        "legacy/passive/historical",
        "closed-this-phase unless explicitly licensed",
        "SearchPlanner / initial_answer_contract",
        "SearchExecutorHandoff",
        "SearchResultCandidatePacket",
        "FetchReadContentPacket / SanitizedContentReference",
        "EvidenceLedger candidate/content custody",
        "EvidenceRelativeAnalysisPacket / AnalystReport",
        "FollowupSearchIntentPacket / AnalysisGapSearchProposal",
        "SemanticObservation admission",
        "ComponentCoverage reduction",
        "ScrutineerReview",
        "Specialist source-bound calculation",
        "SufficiencyReadiness",
        "hardened FinalAnswerPacket",
        "AuthorProseFinalization",
        "Old final-answer packet runtime paths",
        "Old Author execution paths",
        "`core/pipeline_orchestrator.py`",
        "`core/offline_search_executor_bridge.py`",
        "Historical docs",
    )
    for phrase in required_phrases:
        assert phrase in text or phrase in collapsed


def test_docs_posture_keeps_overclaims_quarantined() -> None:
    registry = _source(QUARANTINE_DOC)
    required_negative_posture = (
        "search candidates are not evidence",
        "fetch/read content is not semantic support",
        "EvidenceLedger custody is not component satisfaction",
        "Analyst proposal is not RunKernel authority",
        "Scrutineer sign-off is not product correctness",
        "Specialist calculation is not answer authority",
        "SufficiencyReadiness is not final answer prose",
        "hardened FAP is not product correctness",
        "AuthorProseFinalization does not prove citation rendering",
        "AuthorProseFinalization does not satisfy source obligations",
        "fixture-only proof is not product readiness",
        "live-search-only proof is not product correctness",
    )
    for phrase in required_negative_posture:
        assert phrase in registry

    scanned_docs = "\n".join(
        _source(path)
        for path in (CURRENT_STATE_DOC, RUN_CONTRACT_DOC, CODEX_GUIDANCE_DOC)
    )
    forbidden_overclaims = (
        "search candidates are evidence",
        "fetch/read content is semantic support",
        "EvidenceLedger custody is component satisfaction",
        "Analyst proposal is RunKernel authority",
        "Scrutineer sign-off is product correctness",
        "Specialist calculation is answer authority",
        "SufficiencyReadiness is final answer prose",
        "hardened FAP is product correctness",
        "AuthorProseFinalization proves citation rendering",
        "AuthorProseFinalization satisfies source obligations",
        "fixture-only proof is product readiness",
        "live-search-only proof is product correctness",
        "current fixture/offline chain proves product correctness",
        "current fixture/offline chain proves live product validation",
        "current fixture/offline chain proves citation rendering",
        "current fixture/offline chain proves source-obligation satisfaction",
        "current fixture/offline chain proves AuthorProse product proof",
        "AuthorProseFinalization proves product correctness",
        "AuthorProseFinalization is product proof",
    )
    for phrase in forbidden_overclaims:
        assert phrase not in scanned_docs
        assert phrase not in _collapsed(scanned_docs)


def test_what_this_phase_does_not_prove_is_visible_in_current_docs() -> None:
    combined = "\n".join(
        _source(path)
        for path in (QUARANTINE_DOC, CURRENT_STATE_DOC, RUN_CONTRACT_DOC)
    )
    non_proofs = (
        "ordinary-query execution",
        "source acquisition quality",
        "fetch/read survival on real sources",
        "semantic support from messy live evidence",
        "citation rendering",
        "citation eligibility in user-visible output",
        "source-obligation satisfaction",
        "product correctness",
        "product-quality Author prose",
    )
    for phrase in non_proofs:
        assert phrase in combined


def test_author_prose_current_path_does_not_call_old_author_or_old_fap() -> None:
    imports, calls = _imports_and_calls(AUTHOR_PROSE_RUNTIME)
    forbidden_imports = {
        _sym("core", ".", "pipeline_orchestrator"),
        _sym("core", ".", "final_answer_packet_runtime"),
        _sym("core", ".", "final_answer_runtime_adapter"),
        _sym("core", ".", "followup_final_answer_packet_runtime"),
        _sym("core", ".", "author_execution_runtime"),
        _sym("core", ".", "runtime_prompt_assembly"),
        _sym("core", ".", "search_providers"),
        _sym("core", ".", "retrieval"),
        _sym("open", "ai"),
        _sym("re", "quests"),
        _sym("ht", "tpx"),
        _sym("dot", "env"),
        _sym("sub", "process"),
    }
    forbidden_calls = {
        _sym("execute", "_author"),
        _sym("execute", "_author_action"),
        _sym("derive", "_author_input_payload"),
        _sym("prepare_final_answer_packet", "_author_handoff_from_scope"),
        _sym("execute_final_answer_packet", "_prepare_action"),
        _sym("render", "_citation"),
        _sym("run", "_pipeline"),
        _sym("call", "_broker"),
        _sym("invoke", "_broker"),
        _sym("search", "_web"),
        _sym("retr", "ieve"),
        _sym("dispatch", "_retrieval"),
        _sym("fetch", "_url"),
        _sym("fetch", "_page"),
        _sym("read", "_url"),
        _sym("ask", "_model"),
        _sym("P", "open"),
    }
    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)

    run_kernel = _source(RUN_KERNEL)
    start = run_kernel.index("elif action.action_type is ActionType.AUTHOR_PROSE_FINALIZE:")
    end = run_kernel.index(
        "elif action.action_type is ActionType.FINAL_ANSWER_PACKET_PREPARE:",
        start,
    )
    author_prose_branch = run_kernel[start:end]
    assert "build_author_prose_finalization_state(" in author_prose_branch
    assert "build_author_prose_finalization_projection(" in author_prose_branch
    for token in (
        _sym("execute", "_author"),
        _sym("author", "_execution"),
        _sym("runtime", "_prompt_assembly"),
        _sym("prepare_final_answer_packet", "_author_handoff_from_scope"),
        _sym("execute_final_answer_packet", "_prepare_action"),
        _sym("followup", "_final_answer_packet"),
        _sym("author", "_observation"),
        _sym("final_answer", "_outcome"),
        _sym("run", "_pipeline"),
    ):
        assert token not in author_prose_branch
