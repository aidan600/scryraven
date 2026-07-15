"""Static guards for the canonical documentation truth spine.

Test path: tests/test_docs_canonical_truth_spine_01.py
Proof class: docs_only.
Validation bucket: phase_focus.
Surface guarded: temporal owners, concern owners, routing, and stale-doctrine
exclusion.
Runtime/product path guarded: repository guidance only; no runtime behavior.
Expected cost: local text reads, under one second.
Promotion posture: remain phase_focus.
Why not fast_pr: detailed documentation-owner repair guard.
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
QUARANTINE = ARCH / "AG_CURRENT_PATH_QUARANTINE_01.md"
CONCERN_OWNERS = {
    "canonical:dprime-role-contract": ARCH / "DPRIME_ARCHITECTURE.md",
    "canonical:run-contract-semantic-loop": ARCH / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    "canonical:component-dag-scheduling-concurrency": (
        ARCH / "RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md"
    ),
    "canonical:fap-author-boundary": ARCH / "FAP_AUTHOR_BOUNDARY.md",
    "canonical:bounded-multicomponent-runtime": (
        ARCH / "MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md"
    ),
    "canonical:specialist-graph-substrate": ARCH / "SPECIALIST_GRAPH_SUBSTRATE.md",
    "canonical:quantitative-specialist-product-activation": (
        ARCH / "AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md"
    ),
    "canonical:quantitative-finalization-containment": (
        ARCH / "AG_S1_QUANTITATIVE_FINALIZATION_CONTAINMENT_01.md"
    ),
}
DEFAULT_SPINE = (GUIDANCE, CURRENT_STATE, ROADMAP)
MARKERS = (
    "MC-P1-ORDINARY",
    "MC-P2-DYNAMIC-RECOVERY",
    "MC-P3-SELECTIVE-RECOMPUTE",
    "MC-P4-SCHEDULER-LEASES",
    "MC-P5A-HOSTED-W2",
    "MC-P5A-STRICT-ONE-SHOT",
    "MC-P5A-SAMPLING-COMPAT",
    "MC-P5A-MAIN-THREAD-COST",
    "SPECIALIST-S0-GENERIC",
    "SPECIALIST-S1-QUANTITATIVE",
    "QUANT-FINALIZATION-CONTAINMENT",
)
QUANT_FINALIZATION_RUNTIME_SHA = (
    "4e095c7db287ab29fbe748bdd5c24cf4f2545e15"  # pragma: allowlist secret
)
QUANT_LINEAGE_RUNTIME_SHA = (
    "bba0d16313944b742251298b4fc929b4ceb55d76"  # pragma: allowlist secret
)
S1_RUNTIME_SHA = (
    "4232c4570908065adf589ec2b44be695f82fce56"  # pragma: allowlist secret
)
RUNTIME_SHA_BY_CONCERN = {
    "canonical:dprime-role-contract": QUANT_LINEAGE_RUNTIME_SHA,
    "canonical:run-contract-semantic-loop": QUANT_FINALIZATION_RUNTIME_SHA,
    "canonical:component-dag-scheduling-concurrency": S1_RUNTIME_SHA,
    "canonical:fap-author-boundary": QUANT_LINEAGE_RUNTIME_SHA,
    "canonical:bounded-multicomponent-runtime": QUANT_FINALIZATION_RUNTIME_SHA,
    "canonical:specialist-graph-substrate": S1_RUNTIME_SHA,
    "canonical:quantitative-specialist-product-activation": (
        QUANT_LINEAGE_RUNTIME_SHA
    ),
    "canonical:quantitative-finalization-containment": (
        QUANT_LINEAGE_RUNTIME_SHA
    ),
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


def test_temporal_authorities_are_unique_and_default_read() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    for authority, owner, verified_runtime in (
        (
            "canonical:current-installed-state",
            CURRENT_STATE,
            QUANT_LINEAGE_RUNTIME_SHA,
        ),
        ("canonical:current-roadmap", ROADMAP, S1_RUNTIME_SHA),
    ):
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]
        assert "Status: current" in _read(owner)
        assert "Default-read: yes" in _read(owner)
        assert f"Verified-against-runtime: {verified_runtime}" in _read(owner)


def test_concern_authorities_are_unique_current_and_default_no() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    for authority, owner in CONCERN_OWNERS.items():
        text = _read(owner)
        verified_runtime = RUNTIME_SHA_BY_CONCERN[authority]
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]
        assert "Status: current" in text
        assert "Default-read: no" in text
        assert f"Verified-against-runtime: {verified_runtime}" in text


def test_quarantine_is_narrow_routed_support_not_temporal_authority() -> None:
    text = _read(QUARANTINE)
    assert "Status: supporting" in text
    assert "Authority: routed-support" in text
    assert "Default-read: no" in text
    assert "not an installed-state registry or a roadmap" in text
    assert "contains no broad product-state registry" in text
    assert "canonical:current-installed-state" not in text
    assert "canonical:current-roadmap" not in text

    temporal_routes = _read(GUIDANCE).split("## Phase Operation", maxsplit=1)[0]
    assert QUARANTINE.name not in temporal_routes


def test_guidance_routes_to_exact_concern_owners() -> None:
    guidance = _read(GUIDANCE)
    for authority, owner in CONCERN_OWNERS.items():
        assert f"`{authority}`" in guidance
        assert owner.name in guidance
    assert "await D1 repair" not in guidance
    assert "implementation-status sections" not in guidance


def test_repaired_contracts_exclude_active_roadmap_and_obsolete_status() -> None:
    forbidden = (
        "recommended next phase",
        "recommended next build",
        "next implementation gate",
        "post-merge next gate",
        "## current roadmap",
        "## historical second-half roadmap",
        "await d1 repair",
    )
    for path in CONCERN_OWNERS.values():
        text = _collapsed(path).casefold()
        for phrase in forbidden:
            assert phrase not in text, (path, phrase)

    dprime = _collapsed(CONCERN_OWNERS["canonical:dprime-role-contract"])
    assert "ordinary bounded multi-component path consumes both component D-prime and synthesis D-prime" in dprime
    assert "Review and admission alone do not prove" in dprime
    assert "approved general ordinary component Analyst" not in dprime

    semantic = _collapsed(CONCERN_OWNERS["canonical:run-contract-semantic-loop"])
    assert "PR #" not in _read(CONCERN_OWNERS["canonical:run-contract-semantic-loop"])
    assert "Workers propose. RunKernel authorizes and reduces." in semantic

    dag = _collapsed(CONCERN_OWNERS["canonical:component-dag-scheduling-concurrency"])
    assert "ComponentWorkGraph V1 is installed" in dag
    assert "future shape" not in dag.casefold()
    assert "next BUILD must install ordinary consumption" not in dag

    fap = _collapsed(CONCERN_OWNERS["canonical:fap-author-boundary"])
    assert "When FAP readiness is blocked, Author does not run." in fap
    assert "generic D-prime admission is not numeric rendering authority" in fap
    assert "future answer rendering" not in fap.casefold()

    containment = _collapsed(
        CONCERN_OWNERS["canonical:quantitative-finalization-containment"]
    )
    assert "The two authority kinds are" in containment
    assert "Generic admission is not an authority kind." in containment
    assert "`admitted_quantitative_claim`" not in containment


def test_current_state_has_all_installed_capability_markers() -> None:
    current = _read(CURRENT_STATE)
    for marker in MARKERS:
        assert current.count(f"`{marker}`") == 1


def test_roadmap_records_installed_s0_and_s1_before_live_validation() -> None:
    roadmap = _read(ROADMAP)
    s0 = roadmap.index("## Installed Foundation: S0")
    s1 = roadmap.index("## Installed Product Activation: S1")
    live = roadmap.index(
        "## Active Next: Separately Licensed Quantitative Live Validation"
    )
    assert s0 < s1 < live
    assert "no product Specialist activation" in roadmap
    assert "Quantitative Specialist ordinary product activation is installed" in roadmap
    assert "offline proofs do not authorize" in roadmap
    assert "claims that planned capabilities are installed" in roadmap
    for marker in MARKERS:
        assert marker not in roadmap


def test_quantitative_specialist_has_one_current_owner_and_installed_boundaries() -> None:
    owner = CONCERN_OWNERS[
        "canonical:quantitative-specialist-product-activation"
    ]
    text = _collapsed(owner)
    current = _collapsed(CURRENT_STATE)
    for phrase in (
        "Installed runtime class: quantitative-specialist-product-activation-s1",
        "specialist.source_bound_calculation",
        "source_bound_numeric_literal_parser.v1",
        "two-hop proof",
        "component calculation priority before a later synthesis calculation",
        "legacy RunKernel calculation reducer remains compatibility support only",
        "quantitative_specialist_proposal_contract.v1",
        "The same declarative facts build the model-visible contract and drive runtime proposal/request validation",
        "structured candidate record as primary and passage metadata as an exact fallback",
        "Missing facts remain `unknown`",
        "authoritative_current_clear",
        "contested_source_posture",
        "incomplete_lineage",
        "identical nonmaterial fields and `posture_digest`",
        "Component D-prime receives the exact ordinary component input without it",
        "full source catalogs, source material, and complete candidate records are absent from canonical RunKernel projections",
        "next roadmap checkpoint is separately licensed quantitative live validation",
    ):
        assert phrase in text
    assert "Ordinary quantitative Specialist graph activation" not in current
    assert "Estimates, arbitrary formulas, conversions" in current


def test_multicomponent_owner_guards_phase5a_transport_contract() -> None:
    text = _collapsed(CONCERN_OWNERS["canonical:bounded-multicomponent-runtime"])
    for phrase in (
        "each child makes at most one provider request",
        "SDK retries are disabled",
        "endpoint, provider, and model fallback or switching are forbidden",
        "temperature `0.3`",
        "OpenAI Responses requests omit temperature",
        "caller-authored temperature is rejected",
        "Workers never receive `CostAccumulator`",
        "exactly once on the main thread before artifact reduction",
        "Provider-attempt accounting remains separate from product cost accounting",
    ):
        assert phrase in text


def test_project_sources_are_external_not_repository_paths() -> None:
    guidance = _read(GUIDANCE)
    assert "Project Sources are external context, not repository files" in guidance
    for path in (*DEFAULT_SPINE, *CONCERN_OWNERS.values()):
        text = _read(path)
        assert not re.search(r"\[[^]]*Project Sources?[^]]*\]\([^)]+\)", text)
        assert not re.search(r"Project Sources?[^\n]*`[^`]+\.md`", text)


def test_default_spine_does_not_link_to_historical_or_superseded_docs() -> None:
    for source in DEFAULT_SPINE:
        for target in _links(source):
            text = _read(target).casefold()
            assert "status: historical" not in text, (source, target)
            assert "status: superseded" not in text, (source, target)
