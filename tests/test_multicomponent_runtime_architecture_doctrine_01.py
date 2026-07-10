"""PRODUCT-PATH-REGRESSION: canonical multi-component doctrine posture.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: future phase routing for the default
ordinary multi-component answer path.
Runtime consumer: repo-visible architecture doctrine and Codex phase guidance.
Why ordinary product-path work cannot be done directly: this REPAIR is limited
to doctrine and static guards; runtime Python and answer behavior are closed.
Integration deadline: AG-MULTICOMPONENT-ORDINARY-END-TO-END-SYNTHESIS-01.
Exit condition: replace only with an equal-or-stronger guard over the installed
ordinary end-to-end component validation and synthesis path.
Why this is not a shadow product path: it reads Markdown only and creates no
query, graph, semantic output, admission, readiness, packet, or prose.
Forbidden interpretation: passing is not runtime multi-component behavior,
live validation, citation/source-obligation satisfaction, or correctness.

Test path/node id: tests/test_multicomponent_runtime_architecture_doctrine_01.py
Proof class: docs/process repair static posture.
Validation bucket: phase_focus.
Surface guarded: canonical architecture ownership and next-BUILD routing.
High-custody or closed-this-phase surface: all runtime product Python and
ordinary answer output remain closed.
Runtime/product path guarded: docs consumed by future product phases; no runtime.
Expected cost: local Markdown reads only, well under one second.
Promotion posture: remain phase_focus unless it becomes the repo's selected
cheap broad docs sentinel.
Demotion/retirement condition: an equal-or-stronger current doctrine guard owns
the installed ordinary path.
Why not fast_pr: this is detailed phase doctrine, not ordinary PR tax.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "architecture"
CODEX = ROOT / "docs" / "codex"

CANONICAL = ARCH / "MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md"
CURRENT_STATE = ARCH / "SCRYRAVEN_CURRENT_STATE.md"
SEMANTIC_LOOP = ARCH / "RUN_CONTRACT_SEMANTIC_LOOP.md"
DAG = ARCH / "RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md"
WORKBENCH = ARCH / "CROSS_COMPONENT_ANALYST_WORKBENCH.md"
DPRIME = ARCH / "DPRIME_ARCHITECTURE.md"
ANALYST = ARCH / "ANALYST_WORKBENCH_FULL_SLICE.md"
FAP_AUTHOR = ARCH / "FAP_AUTHOR_BOUNDARY.md"
GUIDANCE = CODEX / "CODEX_GUIDANCE_MAP.md"
PLAYBOOK = CODEX / "ARCHITECTURE_GROOVE_PLAYBOOK.md"

NEXT = "AG-MULTICOMPONENT-ORDINARY-END-TO-END-SYNTHESIS-01"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collapsed(path: Path) -> str:
    return " ".join(_read(path).split())


def test_canonical_owner_separates_current_reuse_and_target() -> None:
    text = _collapsed(CANONICAL)

    for phrase in (
        "Current default ordinary behavior",
        "Existing reusable bounded capability",
        "Approved Phase 1 target",
        "commit_semantic_producer_bundle(...)",
        "does not establish a typed general regular-Analyst proposal",
        "The V0 contracts and serial checkpoint are not ordinary answer consumption.",
        "This complete target is approved but not installed.",
        "ordinary-bounded-multicomponent-factual-synthesis-v1",
    ):
        assert phrase in text


def test_roles_remain_separate_smartmodel_capabilities() -> None:
    text = _read(CANONICAL)
    collapsed = _collapsed(CANONICAL)

    for role in (
        "Regular component Analyst",
        "Component D-prime",
        "Cross-Component Analyst",
        "Synthesis D-prime",
        "Scrutineer",
        "RunKernel",
        "Sufficiency",
        "FinalAnswerPacket",
        "Author",
    ):
        assert role in text

    for phrase in (
        "D-prime verifies the claim.",
        "Scrutineer attacks the case.",
        "separately configured SmartModel role",
        "must not hardcode GPT-5.6",
        "must not replace broad semantic analysis",
        "RunKernel | Authorizes role calls",
    ):
        assert phrase in collapsed

    assert "existing narrow deterministic same-component multi-source Scrutineer gate is not the full Scrutineer" in collapsed


def test_unsafe_authority_shortcuts_are_explicitly_closed() -> None:
    collapsed = _collapsed(CANONICAL)

    for phrase in (
        "Validate or admit its own synthesis",
        "Act as first-pass Analyst, invent the claim",
        "Invent synthesis, act as Cross-Component Analyst",
        "Act as the first-pass Analyst",
        "Manufacture semantic output",
        "Generate, repair, validate, or reinterpret synthesis",
        "Create synthesis, glue unadmitted component outputs",
        "Deterministic logic must not replace broad semantic analysis",
    ):
        assert phrase in collapsed


def test_graph_is_n_capable_layered_and_v1_is_a_successor() -> None:
    text = _read(CANONICAL)
    collapsed = _collapsed(CANONICAL)

    for phrase in (
        "n-capable",
        "mode-budgeted",
        "acyclic",
        "serial-compatible initially",
        "bounded synthesis-of-synthesis",
        "SynthesisWorkNode",
        "synthesis-to-synthesis edges",
        "node-, edge-, subgraph-, and whole-graph challenges",
        "ComponentWorkGraph V1",
        "Do not silently redefine the established V0 contract.",
        "An empty edge set does not prove semantic independence.",
    ):
        assert phrase in text or phrase in collapsed

    assert "Two components are an example, not a schema limit" in collapsed
    assert "one synthesis layer is not the durable architecture" in collapsed


def test_answer_contract_and_product_endpoint_block_downstream_glue() -> None:
    text = _read(CANONICAL)
    collapsed = _collapsed(CANONICAL)

    for phrase in (
        "something the run owes the user",
        "subordinate derived reasoning needed to fulfill one or more obligations",
        "A synthesis node does not automatically become an AnswerContract component.",
        "default ordinary entrypoint",
        "ordinary RunAuthority Sufficiency",
        "ordinary FinalAnswerPacket",
        "ordinary Author",
        "user-facing answer containing appropriate admitted synthesis",
        "Graph admission alone is not product completion.",
    ):
        assert phrase in text or phrase in collapsed

    for substitute in (
        "Contracts",
        "packets",
        "fixtures",
        "serial checkpoints",
        "diagnostic output",
        "diagnostic finalization",
    ):
        assert substitute in text


def test_phase_one_bounds_scrutiny_triggers_and_later_commitments_are_owned() -> None:
    text = _read(CANONICAL)

    for phrase in (
        "Explicit component nodes | 2-5",
        "Maximum synthesis nodes | 4",
        "Maximum synthesis depth | 2",
        "Automatic recovery rounds | 0",
        "Graph amendment rounds | 0",
        "mode is Deep",
        "one synthesis node depends on another synthesis node",
        "dynamic graph and AnswerContract amendment",
        "selective synthesis recomputation",
        "revision-specific validation and scrutiny",
        "RunKernel scheduling and budget leases",
        "runtime parallelism where supported",
        "These Boundary 3 capabilities are deferred, not rejected",
    ):
        assert phrase in text


def test_companion_docs_crosslink_and_keep_narrow_ownership() -> None:
    for path in (
        CURRENT_STATE,
        SEMANTIC_LOOP,
        DAG,
        WORKBENCH,
        DPRIME,
        ANALYST,
        FAP_AUTHOR,
        GUIDANCE,
        PLAYBOOK,
    ):
        assert CANONICAL.name in _read(path), path.name

    current = _collapsed(CURRENT_STATE)
    assert "Current default ordinary semantic production is direct" in current
    assert "typed general component Analyst proposal followed by component D-prime validation is not installed" in current
    assert "V0" in current and "not consumed by the ordinary answer path" in current

    semantic = _read(SEMANTIC_LOOP)
    for heading in (
        "current default ordinary component loop",
        "approved Phase 1 component-validation loop",
        "approved Phase 1 cross-component loop",
        "committed dynamic recovery loop",
    ):
        assert heading in semantic

    workbench = _collapsed(WORKBENCH)
    assert "real dedicated configured-SmartModel Cross-Component Analyst call" in workbench
    assert "may not validate its own proposal, admit graph state, dispatch recovery, or render answer prose" in workbench

    fap = _collapsed(FAP_AUTHOR)
    assert "FAP may package admitted direct component material and admitted synthesis" in fap
    assert "FAP must not generate, repair, reinterpret, or validate synthesis" in fap
    assert "explain synthesis that is already admitted and packaged by FAP" in fap


def test_guidance_routes_directly_to_the_mandatory_product_build() -> None:
    for path in (CANONICAL, CURRENT_STATE, SEMANTIC_LOOP, DAG, WORKBENCH, GUIDANCE, PLAYBOOK):
        assert NEXT in _read(path), path.name

    for path in (GUIDANCE, PLAYBOOK):
        collapsed = _collapsed(path)
        assert "No intervening proof or contract-only phase is authorized by default" in collapsed
        assert "ordinary Sufficiency" in collapsed
        assert "FinalAnswerPacket" in collapsed
        assert "Author" in collapsed
        assert "user-facing answer" in collapsed
