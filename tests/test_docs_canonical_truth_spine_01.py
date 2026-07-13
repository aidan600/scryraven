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
)


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
    for authority, owner in (
        ("canonical:current-installed-state", CURRENT_STATE),
        ("canonical:current-roadmap", ROADMAP),
    ):
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]
        assert "Status: current" in _read(owner)
        assert "Default-read: yes" in _read(owner)


def test_concern_authorities_are_unique_current_and_default_no() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    for authority, owner in CONCERN_OWNERS.items():
        text = _read(owner)
        verified_runtime = (
            "46f4fc998f1aae338aff24e9a7033f32ee90c78a"  # pragma: allowlist secret
            if authority == "canonical:specialist-graph-substrate"
            else "276d2e7b7608df8c2e26ad7a49125e1a422798f1"  # pragma: allowlist secret
        )
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
    assert "future answer rendering" not in fap.casefold()


def test_current_state_has_all_installed_capability_markers() -> None:
    current = _read(CURRENT_STATE)
    for marker in MARKERS:
        assert current.count(f"`{marker}`") == 1


def test_roadmap_records_installed_s0_before_active_s1() -> None:
    roadmap = _read(ROADMAP)
    assert roadmap.index("## Installed Foundation: S0") < roadmap.index(
        "## Active Next: S1"
    )
    assert "no product Specialist activation" in roadmap
    assert "claims that planned capabilities are installed" in roadmap
    for marker in MARKERS:
        assert marker not in roadmap


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
