"""Static guards for the D0 canonical documentation truth spine.

Test path: tests/test_docs_canonical_truth_spine_01.py
Proof class: docs_only.
Validation bucket: phase_focus.
Surface guarded: current-state, roadmap, and routed-support ownership.
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
GUIDANCE = DOCS / "codex" / "CODEX_GUIDANCE_MAP.md"
CURRENT_STATE = DOCS / "architecture" / "SCRYRAVEN_CURRENT_STATE.md"
ROADMAP = DOCS / "roadmap" / "CURRENT_ROADMAP.md"
SUPPORTING = (
    DOCS / "architecture" / "AG_CURRENT_PATH_QUARANTINE_01.md",
    DOCS / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    DOCS / "architecture" / "DPRIME_ARCHITECTURE.md",
)
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
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
        ("Authority: canonical:current-installed-state", CURRENT_STATE),
        ("Authority: canonical:current-roadmap", ROADMAP),
    ):
        claimants = [path for path in markdown if authority in _read(path)]
        assert claimants == [owner]
        assert "Default-read: yes" in _read(owner)


def test_mixed_status_docs_are_routed_support_only() -> None:
    warning_terms = (
        "does not own current installed state or the current roadmap",
        "await D1 repair",
        "must not override code/tests or the canonical current-state owner",
    )
    for path in SUPPORTING:
        text = _read(path)
        collapsed = " ".join(text.split())
        assert "Status: supporting" in text
        assert "Authority: routed-support" in text
        assert "Default-read: no" in text
        for term in warning_terms:
            assert term in collapsed, (path, term)

    temporal_routes = _read(GUIDANCE).split("## Phase Operation", maxsplit=1)[0]
    for path in SUPPORTING:
        assert path.name not in temporal_routes


def test_current_state_has_all_installed_capability_markers() -> None:
    current = _read(CURRENT_STATE)
    for marker in MARKERS:
        assert current.count(f"`{marker}`") == 1


def test_roadmap_orders_s0_before_s1_without_installation_claims() -> None:
    roadmap = _read(ROADMAP)
    assert roadmap.index("## Active Next: S0") < roadmap.index("## Committed Next: S1")
    assert "no product Specialist activation yet" in roadmap
    assert "claims that planned capabilities are installed" in roadmap
    for marker in MARKERS:
        assert marker not in roadmap


def test_default_read_docs_do_not_make_completed_work_future() -> None:
    forbidden = (
        "dynamic recovery is next",
        "dynamic graph recovery is next",
        "recommended next phase is `AG-MULTICOMPONENT-DYNAMIC-GRAPH-RECOVERY-01`",
        "selective recomputation is next",
        "scheduling and leases are next",
        "scheduler leases are next",
        "phase 5a is next",
    )
    for path in DEFAULT_SPINE:
        text = " ".join(_read(path).casefold().split())
        for phrase in forbidden:
            assert phrase.casefold() not in text, (path, phrase)


def test_project_sources_are_external_not_repository_paths() -> None:
    guidance = _read(GUIDANCE)
    assert "Project Sources are external context, not repository files" in guidance
    for path in DEFAULT_SPINE:
        text = _read(path)
        assert not re.search(r"\[[^]]*Project Sources?[^]]*\]\([^)]+\)", text)
        assert not re.search(r"Project Sources?[^\n]*`[^`]+\.md`", text)


def test_default_spine_does_not_link_to_historical_or_superseded_docs() -> None:
    for source in DEFAULT_SPINE:
        for target in _links(source):
            text = _read(target).casefold()
            assert "status: historical" not in text, (source, target)
            assert "status: superseded" not in text, (source, target)
