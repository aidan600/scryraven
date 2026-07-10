from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AGENTS_DOC = ROOT / "AGENTS.md"
PHASE_TEMPLATE_DOC = ROOT / "docs" / "codex" / "PHASE_BRIEF_TEMPLATE.md"
PHASE_ADDENDA_DOC = ROOT / "docs" / "codex" / "PHASE_BRIEF_ADDENDA.md"
PROOF_GATE_DOC = ROOT / "docs" / "codex" / "PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md"
GUIDANCE_MAP_DOC = ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md"
QUARANTINE_DOC = ROOT / "docs" / "architecture" / "AG_CURRENT_PATH_QUARANTINE_01.md"

TOUCHED_DOCS = (
    AGENTS_DOC,
    PHASE_TEMPLATE_DOC,
    PHASE_ADDENDA_DOC,
    PROOF_GATE_DOC,
    GUIDANCE_MAP_DOC,
    QUARANTINE_DOC,
)

CURRENT_NEXT_GATE = "AG-MULTICOMPONENT-ORDINARY-END-TO-END-SYNTHESIS-01"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collapsed(value: str) -> str:
    return " ".join(value.split())


def _all_touched_text() -> str:
    return "\n".join(_source(path) for path in TOUCHED_DOCS)


def test_phase_mode_gate_is_declared_in_primary_docs() -> None:
    agents = _source(AGENTS_DOC)
    phase_template = _source(PHASE_TEMPLATE_DOC)
    proof_gate = _source(PROOF_GATE_DOC)

    assert "Mode: BUILD | PROOF | REPAIR" in agents
    assert "Mode:" in phase_template
    assert "BUILD | PROOF | REPAIR" in phase_template
    assert "Usable-answer verdict target:" in phase_template
    assert "YES | NO-BUT-JUSTIFIED" in phase_template

    for mode in ("BUILD", "PROOF", "REPAIR"):
        assert re.search(rf"\b{mode}\b", proof_gate)


def test_build_proof_repair_approval_standards_are_visible() -> None:
    combined = _collapsed(_all_touched_text())
    combined_lower = combined.casefold()

    assert "build is the default" in combined_lower
    assert "proof is an explicit exception" in combined_lower
    assert "proof" in combined_lower
    assert "no-but-justified" in combined_lower
    assert "mandatory next build checkpoint" in combined_lower
    assert (
        "no second proof phase for the same blocker is allowed without explicit user approval"
        in combined_lower
    )
    assert "repair fixes a named integrity defect" in combined_lower


def test_guidance_map_routes_to_current_multicomponent_product_gate() -> None:
    guidance = _source(GUIDANCE_MAP_DOC)
    guidance_lower = guidance.casefold()

    assert CURRENT_NEXT_GATE.casefold() in guidance_lower
    assert "current mandatory next build" in guidance_lower
    assert "no intervening proof or contract-only phase" in _collapsed(guidance_lower)


def test_touched_docs_do_not_present_retired_checkpoint_as_current() -> None:
    for path in TOUCHED_DOCS:
        text = _source(path)
        lower = _collapsed(text).casefold()
        assert (
            "mandatory next product-path checkpoint is `ag-fixture-dogfood-integration-01`"
            not in lower
        ), path
        assert (
            "mandatory next product checkpoint is `ag-fixture-dogfood-integration-01`"
            not in lower
        ), path

    combined_lower = _all_touched_text().casefold()
    assert CURRENT_NEXT_GATE.casefold() in combined_lower
    forbidden_current_claims = (
        "fixture dogfood is still the next checkpoint",
        "fixture dogfood is the next checkpoint after #355",
        "authorprosefinalization is still the final current roadmap gate",
        "proof work counts as product progress without a build-mode consumer",
    )
    for phrase in forbidden_current_claims:
        assert phrase not in combined_lower


def test_historical_checkpoint_narrative_is_not_current_routing() -> None:
    guidance = _source(GUIDANCE_MAP_DOC).casefold()
    assert "older pr-number timelines" in guidance
    assert "historical context" in guidance
    assert "## current productization posture" not in guidance
