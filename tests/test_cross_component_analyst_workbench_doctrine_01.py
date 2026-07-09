"""PRODUCT-PATH-REGRESSION: cross-component doctrine static posture.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: Build / Proof / Repair phase routing
before future multi-component product-path work.
Runtime consumer: repo-visible architecture doctrine and Codex guidance map
consumed by future phase briefs.
Why ordinary product-path work cannot be done directly: this phase is
docs-first architecture repair and explicitly closes runtime implementation,
graph execution, scheduling, retrieval dispatch, FAP, Author, and live calls.
Integration deadline: COMPONENTWORKGRAPH-V0-NOEXEC-CONTRACT-01 must consume or
supersede this doctrine before opening graph contracts.
Exit condition: keep while cross-component work is gated by proposal-only
Workbench, synthesis D-prime validation, and RunKernel admission doctrine.
Why this is not a shadow product path: the test reads docs only; it does not
answer queries, execute graph nodes, dispatch search, validate synthesis, admit
support, package FAP, or render Author prose.
Forbidden interpretation: passing this test is not multi-component answering,
runtime graph behavior, retrieval quality, source-obligation satisfaction,
citation rendering, FAP/Author behavior, live validation, or product
correctness.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CROSS_COMPONENT_DOC = (
    ROOT / "docs" / "architecture" / "CROSS_COMPONENT_ANALYST_WORKBENCH.md"
)
GUIDANCE_MAP_DOC = ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md"
DAG_DOC = ROOT / "docs" / "architecture" / "RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md"
WORKBENCH_DOC = ROOT / "docs" / "architecture" / "ANALYST_WORKBENCH_FULL_SLICE.md"
DPRIME_DOC = ROOT / "docs" / "architecture" / "DPRIME_ARCHITECTURE.md"
RUN_CONTRACT_DOC = ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collapsed(path: Path) -> str:
    return " ".join(_read(path).split())


def test_cross_component_doctrine_inventory_and_verdict_are_visible() -> None:
    text = _read(CROSS_COMPONENT_DOC)

    for phrase in (
        "Capability Inventory / Reuse-First Gate",
        "ComponentWorkNode V0",
        "Per-component Analyst Workbench",
        "Per-component D-prime validation",
        "Same-component multi-source posture",
        "Follow-up / recovery re-entry",
        "RunKernel / AnswerContract / contract mutation",
        "SufficiencyReadiness / FAP / Author",
        "Verdict target: NO-BUT-JUSTIFIED.",
        "Cross-Component Analyst Workbench doctrine/docs first.",
        "No graph code yet.",
        "No two-node proof yet.",
        "No FAP / Author / source display yet.",
    ):
        assert phrase in text
    assert "YES-for-docs" not in text


def test_cross_component_doctrine_blocks_wrong_authority_paths() -> None:
    text = _collapsed(CROSS_COMPONENT_DOC)

    for phrase in (
        "component A final + component B final + component C final -> Author glues",
        "Analyst and D-prime must not directly dispatch search.",
        "FAP and Author must not dispatch search.",
        "ComponentWorkGraph must not directly dispatch search.",
        "Logical concurrency is not runtime parallelism.",
        "Local-model constraints require serial-compatible execution",
        "become component finals glued by FAP or Author",
        "D-prime must not become the Cross-Component Analyst",
    ):
        assert phrase in text


def test_cross_component_doctrine_names_next_phase_order() -> None:
    text = _read(CROSS_COMPONENT_DOC)

    for phase_name in (
        "MULTICOMPONENT-CROSS-COMPONENT-ANALYST-DOCTRINE-01",
        "COMPONENTWORKGRAPH-V0-NOEXEC-CONTRACT-01",
        "CROSS-COMPONENT-SYNTHESIS-PROPOSAL-V0-01",
        "DPRIME-SYNTHESIS-VALIDATION-V0-01",
        "RUNKERNEL-COMPONENT-GRAPH-ADMISSION-V0-01",
    ):
        assert phase_name in text


def test_current_guidance_crosslinks_new_doctrine() -> None:
    for path in (
        GUIDANCE_MAP_DOC,
        DAG_DOC,
        WORKBENCH_DOC,
        DPRIME_DOC,
        RUN_CONTRACT_DOC,
    ):
        assert "CROSS_COMPONENT_ANALYST_WORKBENCH.md" in _read(path), path.name
