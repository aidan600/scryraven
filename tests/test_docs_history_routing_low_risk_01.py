"""Static guards for low-risk historical docs routing (D3A).

Test path: tests/test_docs_history_routing_low_risk_01.py
Proof class: docs_only.
Validation bucket: phase_focus.
Surface guarded: docs/history archive layout, moved-file banners, last-resort
guidance routing, and retirement of original candidate paths.
Runtime/product path guarded: repository documentation routing only.
Expected cost: local text reads, under one second.
Promotion posture: remain phase_focus.
Why not fast_pr: focused historical-routing posture guard.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GUIDANCE = DOCS / "codex" / "CODEX_GUIDANCE_MAP.md"
CURRENT_STATE = DOCS / "architecture" / "SCRYRAVEN_CURRENT_STATE.md"
ROADMAP = DOCS / "roadmap" / "CURRENT_ROADMAP.md"
HISTORY_INDEX = DOCS / "history" / "INDEX.md"

MOVED = (
    (
        DOCS / "RETRIEVAL_AND_FAILURE_UX_ROADMAP.md",
        DOCS / "history" / "roadmaps" / "RETRIEVAL_AND_FAILURE_UX_ROADMAP.md",
    ),
    (
        DOCS / "ROADMAP_IMPLEMENTATION_NOTES.md",
        DOCS / "history" / "roadmaps" / "ROADMAP_IMPLEMENTATION_NOTES.md",
    ),
    (
        DOCS / "phase14_checkpoint_handoff_6f7cc76.md",
        DOCS / "history" / "handoffs" / "phase14_checkpoint_handoff_6f7cc76.md",
    ),
    (
        DOCS / "phase15_checkpoint_handoff_5e72fcc.md",
        DOCS / "history" / "handoffs" / "phase15_checkpoint_handoff_5e72fcc.md",
    ),
    (
        DOCS / "source_refresh_phase14_draft.md",
        DOCS / "history" / "drafts" / "source_refresh_phase14_draft.md",
    ),
    (
        ROOT
        / "outputs"
        / "local_only"
        / "ag94c_project_source_candidates"
        / "02_SCRYRAVEN_CURRENT_ARCHITECTURE_AND_RUNAUTHORITY_STATE_v4.md",
        DOCS
        / "history"
        / "project-source-candidates"
        / "02_SCRYRAVEN_CURRENT_ARCHITECTURE_AND_RUNAUTHORITY_STATE_v4.md",
    ),
    (
        ROOT
        / "outputs"
        / "local_only"
        / "ag94c_project_source_candidates"
        / "03_SCRYRAVEN_SOURCE_HIERARCHY_RUNAUTHORITY_AND_EVIDENCE_POSTURE_v4.md",
        DOCS
        / "history"
        / "project-source-candidates"
        / "03_SCRYRAVEN_SOURCE_HIERARCHY_RUNAUTHORITY_AND_EVIDENCE_POSTURE_v4.md",
    ),
    (
        ROOT
        / "outputs"
        / "local_only"
        / "ag94c_project_source_candidates"
        / "05_SCRYRAVEN_PRODUCTIZATION_ROADMAP_v11_AUTHORITY_DOCTRINE_AND_OFFICIAL_ACQUISITION.md",
        DOCS
        / "history"
        / "project-source-candidates"
        / "05_SCRYRAVEN_PRODUCTIZATION_ROADMAP_v11_AUTHORITY_DOCTRINE_AND_OFFICIAL_ACQUISITION.md",
    ),
)

CHANGED = (
    HISTORY_INDEX,
    GUIDANCE,
    DOCS / "DOCS_INVENTORY_AND_CONSOLIDATION_PLAN.md",
    DOCS / "architecture" / "AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md",
    *(new for _, new in MOVED),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _banner(path: Path) -> str:
    return "\n".join(_read(path).splitlines()[:12])


def _links(path: Path) -> list[Path]:
    targets = re.findall(r"\[[^]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)", _read(path))
    return [(path.parent / target).resolve() for target in targets]


def test_history_index_exists_as_supporting_not_default_read() -> None:
    text = _read(HISTORY_INDEX)
    assert "Status: supporting" in text
    assert "Authority: none" in text
    assert "Default-read: no" in text
    assert "historical document discovery and provenance only" in text.casefold()


def test_eight_moved_files_exist_only_at_archive_paths() -> None:
    for old, new in MOVED:
        assert new.is_file(), new
        assert not old.exists(), old
        banner = _banner(new)
        assert "Status: historical" in banner
        assert "Authority: none" in banner
        assert "Default-read: no" in banner
        assert "Authority: canonical:" not in banner


def test_no_tracked_project_source_candidates_under_outputs_local_only() -> None:
    remnant = ROOT / "outputs" / "local_only" / "ag94c_project_source_candidates"
    assert not remnant.exists()
    tracked = list(remnant.rglob("*.md")) if remnant.exists() else []
    assert tracked == []


def test_guidance_routes_history_index_as_last_resort_only() -> None:
    guidance = _read(GUIDANCE)
    assert "Historical provenance, only when a current owner or phase explicitly requires it" in guidance
    assert "(last resort; not default-read)" in guidance
    assert "history/INDEX.md" in guidance
    default_read = guidance.split("## Temporal Owners", maxsplit=1)[0]
    assert "history/INDEX.md" not in default_read
    for target in _links(GUIDANCE):
        assert target.is_file(), target


def test_default_read_docs_do_not_treat_moved_files_as_owners() -> None:
    moved_names = {new.name for _, new in MOVED}
    for path in DOCS.rglob("*.md"):
        text = _read(path)
        if "Default-read: yes" not in text:
            continue
        for name in moved_names:
            assert name not in text, (path, name)


def test_temporal_owners_remain_exclusive() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    for authority, owner in (
        ("canonical:current-installed-state", CURRENT_STATE),
        ("canonical:current-roadmap", ROADMAP),
    ):
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]


def test_changed_markdown_links_resolve() -> None:
    for path in CHANGED:
        for target in _links(path):
            assert target.is_file(), (path, target)
