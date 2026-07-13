"""Static guards for bulk historical architecture/validation archive (D3B).

Test path: tests/test_docs_history_bulk_archive_01.py
Proof class: docs_only.
Validation bucket: phase_focus.
Surface guarded: docs/history architecture and validation archive layout,
ARCHIVE_MANIFEST.json integrity, keep-gates for current owners, and
repository Markdown link integrity for tracked docs.
Runtime/product path guarded: repository documentation routing only.
Expected cost: local text reads, a few seconds.
Promotion posture: remain phase_focus.
Why not fast_pr: focused bulk historical-routing posture guard.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GUIDANCE = DOCS / "codex" / "CODEX_GUIDANCE_MAP.md"
CURRENT_STATE = DOCS / "architecture" / "SCRYRAVEN_CURRENT_STATE.md"
ROADMAP = DOCS / "roadmap" / "CURRENT_ROADMAP.md"
HISTORY_INDEX = DOCS / "history" / "INDEX.md"
ARCH_INDEX = DOCS / "history" / "architecture" / "INDEX.md"
VAL_INDEX = DOCS / "history" / "validation" / "INDEX.md"
MANIFEST = DOCS / "history" / "ARCHIVE_MANIFEST.json"

MANDATORY_OWNERS = (
    "SCRYRAVEN_CURRENT_STATE.md",
    "RUN_CONTRACT_SEMANTIC_LOOP.md",
    "DPRIME_ARCHITECTURE.md",
    "RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md",
    "FAP_AUTHOR_BOUNDARY.md",
    "MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md",
    "CROSS_COMPONENT_ANALYST_WORKBENCH.md",
    "ANALYST_WORKBENCH_FULL_SLICE.md",
    "MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md",
    "AG_CURRENT_PATH_QUARANTINE_01.md",
)

SUPPORTING_EXACT = (
    "AG_ANALYST_EVIDENCE_RELATIVE_REPORT_01.md",
    "AG_ANALYSIS_GAP_FOLLOWUP_SEARCH_01.md",
    "AG_COMPONENT_COVERAGE_RELIABILITY_PROOF_01.md",
    "AG_DOC_SEMANTIC_COVERAGE_CHECKPOINT_01.md",
    "AG_FOLLOWUP_SEARCH_AUTHORIZATION_REENTRY_01.md",
    "AG_SCRUTINEER_REVIEW_01.md",
    "AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md",
    "AG_SUFFICIENCY_PARTIAL_ANSWER_READINESS_01.md",
    "AG_FINAL_ANSWER_PACKET_HARDENING_01.md",
    "AUTHOR_PROSE_ONLY_FINALIZATION_01.md",
    "AG_ANSWER_CONTRACT_AUTHORITY_MAP_01_DECISION.md",
    "DPRIME_PRODUCT_MODEL_ROUTE_CONFIG_BOUNDARY.md",
    "SOURCE_AUTHORITY_POSTURE.md",
    "LEGAL_CURRENT_PRIMARY_TRIAGE_L2A.md",
    "LEGAL_CURRENT_SOURCE_QUALITY_L2B.md",
    "OFFICIAL_NUMERIC_SOURCE_GROUNDING_AG48A.md",
    "OFFICIAL_SOURCE_ACQUISITION_SURVIVAL_AG48B.md",
    "TARGETED_RETRIEVAL_OWNERSHIP_AG42.md",
    "TARGETED_RETRIEVAL_SPINE_REPRESENTATION_AG43C.md",
    "TYPED_RETRIEVAL_BATCH_DESIGN_AG46A.md",
    "AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md",
    "AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md",
    "AG95Q_PROVIDER_REVIEW_ALLOCATION_BURNDOWN.md",
)

SUPPORTING_PREFIXES = (
    "AG_LIMITED_LIVE_",
    "AG_LIVE_",
    "AG_ORDINARY_LIVE_",
    "AG_LOCAL_DRYRUN_",
    "AG_FIXTURE_DOGFOOD_",
    "AG_CHECK_01_",
)

HIST_PREFIXES = (
    "AG51B_",
    "AG74",
    "AG75",
    "AG76",
    "AG77",
    "AG78",
    "AG79",
    "AG89",
    "AG90",
    "AG91",
    "AG92",
    "AG93",
    "AG94",
    "AG95",
    "AG96",
    "ACTIVE_",
    "CONFLICT_",
    "CONTROLLER_",
    "DOCUMENTATION_ROLES_",
    "EVIDENCE_INTEGRATION_",
    "OFFICIAL_",
    "SOURCE_CLASS_",
    "WEAK_CORPUS_",
    "AG_SEM_",
)

RUNTIME_GLOBS = (
    "core/**/*.py",
    "proplex/**/*.py",
    "scryraven/**/*.py",
    "ui/**/*.py",
    "scripts/**/*.py",
    "app.py",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _banner(path: Path) -> str:
    return "\n".join(_read(path).splitlines()[:12])


def _links(path: Path) -> list[Path]:
    targets = re.findall(r"\[[^]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)", _read(path))
    return [(path.parent / target).resolve() for target in targets]


def _manifest() -> dict:
    return json.loads(_read(MANIFEST))


def _d3b_entries() -> list[dict]:
    data = _manifest()
    return list(data["batches"]["D3B"]["architecture"]) + list(
        data["batches"]["D3B"]["validation"]
    )


def _tracked(pattern: str) -> list[str]:
    out = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", pattern],
        text=True,
    )
    return [line.replace("\\", "/") for line in out.splitlines() if line]


def test_manifest_exists_parses_and_is_deterministic() -> None:
    data = _manifest()
    assert data["schema"] == "scryraven-doc-history-manifest-v1"
    arch = data["batches"]["D3B"]["architecture"]
    val = data["batches"]["D3B"]["validation"]
    assert 150 <= len(arch) <= 205
    assert 70 <= len(val) <= 90
    assert [e["original_path"] for e in arch] == sorted(
        e["original_path"] for e in arch
    )
    assert [e["original_path"] for e in val] == sorted(
        e["original_path"] for e in val
    )
    originals = [e["original_path"] for e in arch + val]
    archived = [e["archived_path"] for e in arch + val]
    assert len(originals) == len(set(originals))
    assert len(archived) == len(set(archived))


def test_manifest_paths_and_historical_banners() -> None:
    for entry in _d3b_entries():
        old = ROOT / entry["original_path"]
        new = ROOT / entry["archived_path"]
        assert not old.exists(), entry["original_path"]
        assert new.is_file(), entry["archived_path"]
        banner = _banner(new)
        assert "Status: historical" in banner
        assert "Authority: none" in banner
        assert "Default-read: no" in banner
        assert "Authority: canonical:" not in banner


def test_counts_match_filesystem() -> None:
    data = _manifest()
    arch = data["batches"]["D3B"]["architecture"]
    val = data["batches"]["D3B"]["validation"]
    phase_files = list((DOCS / "history" / "architecture" / "phases").glob("*.md"))
    controller = (
        DOCS
        / "history"
        / "architecture"
        / "SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md"
    )
    assert controller.is_file()
    assert len(arch) == len(phase_files) + 1
    assert {e["archived_path"] for e in arch} == {
        *(f"docs/history/architecture/phases/{path.name}" for path in phase_files),
        "docs/history/architecture/SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md",
    }
    validation_files = [
        path
        for path in (DOCS / "history" / "validation").glob("*.md")
        if path.name != "INDEX.md"
    ]
    assert len(val) == len(validation_files)
    assert _tracked("docs/validation/*.md") == []
    assert not (DOCS / "validation").exists() or not any(
        (DOCS / "validation").glob("*.md")
    )


def test_no_historical_candidate_remains_in_architecture_root() -> None:
    keep_names = set(MANDATORY_OWNERS) | set(SUPPORTING_EXACT)
    remaining = sorted(p.name for p in (DOCS / "architecture").glob("*.md"))
    for name in remaining:
        if name in keep_names:
            continue
        if any(name.startswith(prefix) for prefix in SUPPORTING_PREFIXES):
            continue
        if name == "source_hierarchy_answer_contract_invariants.md":
            raise AssertionError(name)
        if any(name.startswith(prefix) for prefix in HIST_PREFIXES):
            raise AssertionError(f"historical candidate remained: {name}")


def test_current_owners_and_supporting_contracts_remain() -> None:
    for name in MANDATORY_OWNERS + SUPPORTING_EXACT:
        assert (DOCS / "architecture" / name).is_file(), name
    for name in SUPPORTING_PREFIXES:
        matches = list((DOCS / "architecture").glob(f"{name}*.md"))
        assert matches, name


def test_guidance_and_history_indexes() -> None:
    guidance = _read(GUIDANCE)
    assert "history/INDEX.md" in guidance
    assert "history/architecture/INDEX.md" in guidance
    assert "history/validation/INDEX.md" in guidance
    default_read = guidance.split("## Temporal Owners", maxsplit=1)[0]
    assert "history/architecture/INDEX.md" not in default_read
    assert "history/validation/INDEX.md" not in default_read
    for path in (GUIDANCE, HISTORY_INDEX, ARCH_INDEX, VAL_INDEX):
        for target in _links(path):
            assert target.is_file(), (path, target)
    for path in (HISTORY_INDEX, ARCH_INDEX, VAL_INDEX):
        text = _read(path)
        assert "Status: supporting" in text
        assert "Authority: none" in text
        assert "Default-read: no" in text


def test_all_tracked_markdown_links_resolve() -> None:
    files = _tracked("*.md")
    for rel in files:
        path = ROOT / rel
        for target in _links(path):
            assert target.is_file(), (rel, target)


def test_no_code_or_test_references_missing_original_paths() -> None:
    originals = [entry["original_path"] for entry in _d3b_entries()]
    checked = _tracked("*.py") + _tracked("*.md") + _tracked("*.mdc")
    for rel in checked:
        if rel.replace("\\", "/") == "docs/history/ARCHIVE_MANIFEST.json":
            continue
        text = _read(ROOT / rel)
        for original in originals:
            if original not in text:
                continue
            for line in text.splitlines():
                if original not in line:
                    continue
                if f"`{original}`" in line and (
                    "Original path" in line or line.lstrip().startswith("|")
                ):
                    continue
                if '"original_path"' in line or "original_path" in line:
                    continue
                raise AssertionError(f"{rel} still references {original}: {line}")


def test_temporal_owners_remain_exclusive() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    for authority, owner in (
        ("canonical:current-installed-state", CURRENT_STATE),
        ("canonical:current-roadmap", ROADMAP),
    ):
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]


def test_no_runtime_product_files_changed_in_diff() -> None:
    diff = subprocess.check_output(
        ["git", "-C", str(ROOT), "diff", "--name-only", "origin/main...HEAD"],
        text=True,
    )
    # Working tree may also have unstaged D3B changes; include status
    status = subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--porcelain"],
        text=True,
    )
    paths: set[str] = set()
    for line in diff.splitlines():
        if line.strip():
            paths.add(line.strip().replace("\\", "/"))
    for line in status.splitlines():
        raw = line[3:].strip().replace("\\", "/")
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        if raw:
            paths.add(raw)
    forbidden_prefixes = (
        "core/",
        "proplex/",
        "scryraven/",
        "ui/",
        "scripts/",
        "app.py",
    )
    runtime_hits = [
        path
        for path in sorted(paths)
        if path == "app.py" or any(path.startswith(prefix) for prefix in forbidden_prefixes)
    ]
    assert runtime_hits == []


def test_manifest_sha_matches_archived_content() -> None:
    import hashlib

    for entry in _d3b_entries():
        text = _read(ROOT / entry["archived_path"])
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert digest == entry["content_sha256"], entry["archived_path"]
