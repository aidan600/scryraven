"""Static guards for the compact canonical documentation truth spine.

These tests protect ownership, routing, installed/selected distinctions, and the
current semantic boundaries. They intentionally do not preserve phase chronology
or require current documents to repeat every historical capability milestone.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARCH = DOCS / "architecture"
GUIDANCE = DOCS / "codex" / "CODEX_GUIDANCE_MAP.md"
CURRENT_STATE = ARCH / "SCRYRAVEN_CURRENT_STATE.md"
ROADMAP = DOCS / "roadmap" / "CURRENT_ROADMAP.md"
ANALYSTOS = ARCH / "ANALYSTOS_OPERATING_MODEL.md"
DPRIME = ARCH / "DPRIME_ARCHITECTURE.md"
FAP_AUTHOR = ARCH / "FAP_AUTHOR_BOUNDARY.md"
QUANT_CONTAINMENT = ARCH / "AG_S1_QUANTITATIVE_FINALIZATION_CONTAINMENT_01.md"
CURRENT_RUNTIME_SHA = "d3df96994f72b371f6a2451677784376ac3f7cb9"  # pragma: allowlist secret

CONCERN_OWNERS = {
    "canonical:analystos-operating-model": ANALYSTOS,
    "canonical:dprime-role-contract": DPRIME,
    "canonical:run-contract-semantic-loop": ARCH / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    "canonical:component-dag-scheduling-concurrency": (
        ARCH / "RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md"
    ),
    "canonical:fap-author-boundary": FAP_AUTHOR,
    "canonical:bounded-multicomponent-runtime": (
        ARCH / "MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md"
    ),
    "canonical:specialist-graph-substrate": ARCH / "SPECIALIST_GRAPH_SUBSTRATE.md",
    "canonical:quantitative-specialist-product-activation": (
        ARCH / "AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md"
    ),
    "canonical:quantitative-finalization-containment": QUANT_CONTAINMENT,
    "canonical:searchos-post-analysis-recovery-and-inference-direction": (
        ARCH / "SEARCHOS_POST_ANALYSIS_RECOVERY_AND_INFERENCE_DIRECTION.md"
    ),
}

COMPACT_LINE_BUDGETS = {
    CURRENT_STATE: 260,
    ROADMAP: 220,
    ANALYSTOS: 240,
    FAP_AUTHOR: 230,
    DPRIME: 220,
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collapsed(path: Path) -> str:
    return " ".join(_read(path).split())


def _links(path: Path) -> list[Path]:
    targets = re.findall(r"\[[^]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)", _read(path))
    return [(path.parent / target).resolve() for target in targets]


def test_guidance_links_resolve() -> None:
    links = _links(GUIDANCE)
    assert links
    for target in links:
        assert target.is_file(), target


def test_temporal_authorities_are_unique_and_compact() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    for authority, owner in (
        ("canonical:current-installed-state", CURRENT_STATE),
        ("canonical:current-roadmap", ROADMAP),
    ):
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]
        text = _read(owner)
        assert "Status: current" in text
        assert "Default-read: yes" in text

    current = _read(CURRENT_STATE)
    roadmap = _read(ROADMAP)
    assert current.count(f"Runtime-audit-through: {CURRENT_RUNTIME_SHA}") == 1
    assert "Verified-against-runtime:" not in current
    assert "Runtime-audit-through:" not in roadmap
    assert "Verified-against-runtime:" not in roadmap


def test_concern_authorities_are_unique_current_and_routed() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    guidance = _read(GUIDANCE)
    for authority, owner in CONCERN_OWNERS.items():
        text = _read(owner)
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]
        assert "Status: current" in text
        assert "Default-read: no" in text
        assert len(
            re.findall(
                r"^Verified-against-runtime: [0-9a-f]{40}$",
                text,
                re.MULTILINE,
            )
        ) == 1
        assert owner.name in guidance
        assert f"`{authority}`" in guidance


def test_current_state_describes_installed_authority_chain() -> None:
    current = _collapsed(CURRENT_STATE)
    for phrase in (
        "python -m scryraven",
        "python -m proplex",
        "SearchOS acquisition and lawful handoff",
        "Component Analyst case",
        "RunKernel exact binding and admission",
        "ComponentCoverage",
        "Sufficiency whole-run readiness",
        "FinalAnswerPacket packaging",
        "Author is the final semantic actor",
        "FinalAnswerPacket is semantically stupid and mechanically strict",
        "Direct-source numbers are ordinary admitted claim content",
        "specialist_derived_numeric",
        "Source-class observability and telemetry are helper/diagnostic only",
        "ordinary-bounded-multicomponent-factual-synthesis-v1",
        "Run 04",
        CURRENT_RUNTIME_SHA,
    ):
        assert phrase in current

    assert "no additional live Q1 run was made on the final merged SHA" in current
    assert "Real-model Component Analyst output-validation behavior on the current Q1 path remains the immediate product frontier" not in current
    assert "proposition-fingerprint" not in current
    assert "complete literal-signature binding" not in current


def test_roadmap_has_one_current_product_gate_not_chronology() -> None:
    roadmap = _read(ROADMAP)
    collapsed = _collapsed(ROADMAP)
    assert roadmap.count("## Active Decision Gate:") == 1
    assert "## Active Decision Gate: REPRESENTATIVE MULTI-COMPONENT PRODUCT OBSERVATION" in roadmap
    for phrase in (
        "multiple Component Analyst cases admitted",
        "Cross invoked only when the request needs relationship meaning",
        "no forced synthesis",
        "Sufficiency computes a defensible whole-answer posture",
        "QF-01",
        "QF-02",
        "QF-03",
        "Do not continue optimizing that query",
    ):
        assert phrase in collapsed

    assert "Completed Repair:" not in roadmap
    assert "Completed Build:" not in roadmap
    assert "Active Decision Gate: ANALYSTOS COMPONENT-PATH REPLACEMENT" not in roadmap
    assert "Representative Bounded Real-Model/Product Validation" not in roadmap


def test_analystos_separates_meaning_admission_and_readiness() -> None:
    analystos = _collapsed(ANALYSTOS)
    for phrase in (
        "INSTALLED:",
        "SELECTED TARGET:",
        "Component D-prime has no ordinary component producer or consumer",
        "the installed bounded path still uses Cross-Component Analyst followed by a separate synthesis D-prime model call",
        "Analyst explains",
        "RunKernel admits",
        "Coverage checks components",
        "Sufficiency computes whole-answer readiness",
        "FAP packs",
        "Author writes",
        "Sufficiency is a deterministic whole-run policy reduction over canonical state",
        "Ordinary N=1 does not schedule Cross",
        "Zero is lawful",
        "Source-stated literals are ordinary direct evidence",
    ):
        assert phrase in analystos

    assert "Sufficiency is the sole whole-run stopper" not in analystos
    assert "real-model Component Analyst output-validation behavior" not in analystos


def test_fap_boundary_is_semantically_stupid_and_mechanically_strict() -> None:
    fap = _collapsed(FAP_AUTHOR)
    for phrase in (
        "FAP is the final semantic-authority boundary",
        "It is not a semantic adjudicator",
        "Semantically Stupid, Mechanically Strict",
        "which number matters",
        "Direct-source numbers are ordinary admitted claim content",
        "does not create or require a separate `direct_source_numeric` PRODUCT authority row",
        "up to 2,000 characters",
        "independently capped at 600 characters",
        "Extra context is a resource, not an output checklist",
        "specialist_derived_numeric",
        "Author is the final semantic actor",
        "Post-Author code does not reinterpret free-form prose",
        "When FAP mechanical readiness is blocked, Author does not run",
    ):
        assert phrase in fap

    for stale in (
        "proposition-fingerprint",
        "complete literal-signature binding",
        "narrow component/content/coverage-bound equivalence",
        "every required numeric claim",
    ):
        assert stale not in fap


def test_dprime_contract_preserves_installed_selected_split() -> None:
    dprime = _collapsed(DPRIME)
    for phrase in (
        "Component D-prime has no ordinary component producer or consumer",
        "The bounded genuine N>=2 path still executes a synthesis D-prime model call",
        "selected for retirement",
        "RunKernel synthesis admission",
        "D-prime has no direct FAP or Author authority",
        "does not reparse claim prose, compare literal signatures",
        "specialist_derived_numeric",
    ):
        assert phrase in dprime

    assert "complete proposition and literal signature" not in dprime
    assert "Final accepted-prose binding" not in dprime


def test_quantitative_containment_matches_merged_fap_boundary() -> None:
    containment = _collapsed(QUANT_CONTAINMENT)
    for phrase in (
        "Direct-source semantic support is Analyst explanation plus RunKernel admission",
        "Admitted direct-source numbers are ordinary claim content",
        "does not extract claim-text literals",
        "specialist_derived_numeric",
        "The evaluator may be wrong",
        "No PRODUCT runtime consumer may use it as a success or failure decision",
    ):
        assert phrase in containment

    assert "proposition-fingerprint, and complete literal-signature binding" not in containment


def test_default_read_spine_stays_small_and_nonhistorical() -> None:
    guidance = _read(GUIDANCE)
    default_path = guidance.split("## Smallest Default Read Path", maxsplit=1)[1].split(
        "## Temporal Owners", maxsplit=1
    )[0]
    assert CURRENT_STATE.name in default_path
    assert ROADMAP.name in default_path
    assert "Historical Document Index" not in default_path
    assert "Historical Architecture Index" not in default_path
    assert "ChatGPT Project Sources are external context, not repository files" in guidance


def test_current_docs_have_compactness_budgets() -> None:
    for path, limit in COMPACT_LINE_BUDGETS.items():
        line_count = len(_read(path).splitlines())
        assert line_count <= limit, (path.name, line_count, limit)


def test_current_docs_exclude_retired_fap_semantic_doctrine() -> None:
    current_docs = (CURRENT_STATE, ROADMAP, ANALYSTOS, FAP_AUTHOR, DPRIME, QUANT_CONTAINMENT)
    forbidden = (
        "FAP decides which numbers matter",
        "FAP re-proves literal signatures",
        "direct-source numeric proposition fingerprint",
        "Author output is withheld solely because a prose evaluator disagrees",
        "FAP parses admitted prose to determine authority",
    )
    for path in current_docs:
        normalized = _collapsed(path)
        for phrase in forbidden:
            assert phrase not in normalized, (path.name, phrase)
