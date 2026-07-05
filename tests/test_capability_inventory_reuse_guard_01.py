from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PLAYBOOK_DOC = ROOT / "docs" / "codex" / "ARCHITECTURE_GROOVE_PLAYBOOK.md"
PHASE_TEMPLATE_DOC = ROOT / "docs" / "codex" / "PHASE_BRIEF_TEMPLATE.md"
GUIDANCE_MAP_DOC = ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md"
DPRIME_DOC = ROOT / "docs" / "architecture" / "DPRIME_ARCHITECTURE.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_capability_inventory_gate_is_visible_in_primary_phase_docs() -> None:
    combined = "\n".join(
        _read(path) for path in (PLAYBOOK_DOC, PHASE_TEMPLATE_DOC, GUIDANCE_MAP_DOC)
    )

    for phrase in (
        "Capability inventory / reuse-first gate",
        "REUSE",
        "ADAPT",
        "UPGRADE",
        "RETIRE",
        "REPLACE",
        "If existing current capability may already own the responsibility, stop for",
        "Surface:",
        "Existing owner module/doc:",
        "Current consumer:",
        "Current status:",
        "Why not duplicate:",
        "Tests/guards:",
    ):
        assert phrase in combined


def test_capability_inventory_trigger_surfaces_are_named() -> None:
    combined = "\n".join(
        _read(path) for path in (PLAYBOOK_DOC, PHASE_TEMPLATE_DOC, GUIDANCE_MAP_DOC)
    )

    for phrase in (
        "D-prime / DPrime",
        "Analyst / EvidenceRelativeAnalysisPacket",
        "source authority",
        "source obligation",
        "citation eligibility / citation-source handoff",
        "SufficiencyReadiness",
        "FinalAnswerPacket / FAP",
        "Author",
        "SemanticObservation",
        "ComponentCoverage",
        "RunKernel admission / RunKernel authority",
        "follow-up / recovery",
        "SearchPlanner / query planner",
        "model-assisted planning",
        "FastModel / SmartModel",
        "Scrutineer",
        "multi-source",
        "multi-component",
        "EvidenceLedger",
        "fetch/read",
        "provider acquisition",
        "evidence triage",
        "source gateway / answer gateway / readiness",
    ):
        assert phrase in combined


def test_dprime_reuse_lesson_points_to_existing_downstream_machinery() -> None:
    combined = "\n".join(_read(path) for path in (PLAYBOOK_DOC, GUIDANCE_MAP_DOC, DPRIME_DOC))
    collapsed = " ".join(combined.split())

    for phrase in (
        "source-obligation authority",
        "citation-source handoff",
        "single-lane answer path",
        "follow-up re-entry",
        "same-lane multi-source scrutiny",
        "prefer reuse or adaptation",
    ):
        assert phrase in combined

    forbidden = (
        "rebuild source-obligation",
        "rebuilding source-obligation or citation-readiness machinery",
    )
    assert any(phrase in collapsed for phrase in forbidden)


def test_generic_dogfood_planning_and_acquisition_reuse_lesson_is_visible() -> None:
    combined = "\n".join(_read(path) for path in (PLAYBOOK_DOC, GUIDANCE_MAP_DOC))
    collapsed = " ".join(combined.split())

    for phrase in (
        "model-assisted single-relation planning",
        "strict accounted FastModel",
        "OpenAI Responses",
        "provider acquisition",
        "answer-bearing candidate/window",
        "source/readiness gateway",
        "D-prime authority integration blocker",
        "Prefer `REUSE` / `ADAPT` / `UPGRADE`",
        "generic single-relation dogfood path",
    ):
        assert phrase in combined or phrase in collapsed
