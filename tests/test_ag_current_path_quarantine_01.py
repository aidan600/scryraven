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

AUTHOR_PROSE_RUNTIME = CORE / "author_prose_finalization_runtime.py"
RUN_KERNEL = CORE / "run_kernel.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collapsed(value: str) -> str:
    return " ".join(value.split())


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


def test_current_path_registry_classifies_required_surfaces() -> None:
    text = _source(QUARANTINE_DOC)
    collapsed = _collapsed(text)
    required_phrases = (
        "Proof class: `docs_only` plus phase-focused docs-posture/static guards.",
        "Product-facing progress type: quarantine/docs-process work.",
        "Actual user-facing app delta: none.",
        "mandatory next product-path checkpoint is `AG-FIXTURE-DOGFOOD-INTEGRATION-01`",
        "Existing machinery reused:",
        "New machinery introduced:",
        "Why this is not reinventing an existing surface:",
        "current authority path",
        "current passive/supporting projection",
        "fixture-only proof",
        "offline harness",
        "live-search-only validation",
        "product-facing dry-run proof",
        "legacy/passive/historical",
        "closed/protected unless separately licensed",
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
        "Old follow-up Author/FAP paths",
        "Old sufficiency judgment surfaces",
        "`core/pipeline_orchestrator.py`",
        "`core/offline_search_executor_bridge.py`",
        "Historical docs",
    )
    for phrase in required_phrases:
        assert phrase in text or phrase in collapsed


def test_consumer_seam_matrix_requires_non_proof_and_output_posture() -> None:
    text = _source(QUARANTINE_DOC)
    required_phrases = (
        "## Consumer-Seam Matrix",
        "| Lane | Producer | Consumer | RunKernel owner | Proof class |",
        "Human-reviewable product output",
        "Explicit non-proofs",
        "AuthorProseFinalization",
        "yes, prose-only",
        "does not prove citation rendering",
        "Old FAP/Author/AG-96 lanes",
        "not current path proof",
    )
    for phrase in required_phrases:
        assert phrase in text


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


def test_normal_entrypoints_require_product_path_quarantine_fields() -> None:
    combined = "\n".join(
        _source(path)
        for path in (
            AGENTS_DOC,
            QUARANTINE_DOC,
            CODEX_GUIDANCE_DOC,
            PROOF_CLASS_DOC,
            VALIDATION_BUCKETS_DOC,
            PHASE_TEMPLATE_DOC,
        )
    )
    combined_lower = combined.casefold()
    required_fields = (
        "proof class",
        "product-facing progress type",
        "actual consumer seam",
        "actual user-facing app delta",
        "user-facing/reviewable output delta",
        "non-product exception leash",
        "mandatory next product-path checkpoint",
        "existing machinery reused",
        "new machinery introduced",
        "why this is not reinventing an existing surface",
        "old path treatment",
        "explicit non-proofs",
        "human-reviewable product output",
        "structural proof",
        "whether live validation was run",
        "live validation was prohibited",
        "not licensed",
        "ag-fixture-dogfood-integration-01",
    )
    for field in required_fields:
        assert field in combined_lower


def test_agents_contains_standing_product_facing_progress_default() -> None:
    text = _source(AGENTS_DOC)
    collapsed = _collapsed(text)
    required_phrases = (
        "## Product-facing progress default",
        "Default to converting existing machinery into product-path output",
        "non-product exception leash",
        "mandatory next product-path checkpoint is `AG-FIXTURE-DOGFOOD-INTEGRATION-01`",
        "actual app delta is vague",
        "new harness/proof/packet/projection",
        "named current-path consumer or blocker removal",
        "fixture or offline proof",
        "product correctness",
        "live product validation",
        "citation rendering",
        "source-obligation satisfaction",
        "AuthorProse product proof",
    )
    for phrase in required_phrases:
        assert phrase in text or phrase in collapsed


def test_proof_gate_hard_stops_unconsumed_harness_or_vague_delta() -> None:
    text = _source(PROOF_CLASS_DOC)
    collapsed = _collapsed(text)
    required_phrases = (
        "Another harness, proof, packet, projection, registry, or passive record is not",
        "named current-path consumer",
        "removes a named blocker",
        "actual app delta is vague",
        "mandatory next product-path checkpoint is missing",
        "why-this-is-not-reinventing is unstated",
        "product correctness is claimed from fixture/offline proof",
        "live product validation is claimed from live-search-only or offline proof",
        "citation rendering, source-obligation satisfaction, or AuthorProse product",
        "without a named current-path consumer or named blocker removal",
    )
    for phrase in required_phrases:
        assert phrase in text or phrase in collapsed


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
        "core.pipeline_orchestrator",
        "core.final_answer_packet_runtime",
        "core.final_answer_runtime_adapter",
        "core.followup_final_answer_packet_runtime",
        "core.author_execution_runtime",
        "core.runtime_prompt_assembly",
        "core.search_providers",
        "core.retrieval",
        "openai",
        "requests",
        "httpx",
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
        "execute_author",
        "author_execution",
        "runtime_prompt_assembly",
        "prepare_final_answer_packet_author_handoff_from_scope",
        "execute_final_answer_packet_prepare_action",
        "followup_final_answer_packet",
        "author_observation",
        "final_answer_outcome",
        "run_pipeline",
    ):
        assert token not in author_prose_branch
