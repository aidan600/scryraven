from __future__ import annotations

from pathlib import Path

from core.post_author_output_projection import (
    _final_answer_source_citation_telemetry as projection_source_telemetry,
)

ROOT = Path(__file__).resolve().parents[1]
AG94G = ROOT / "docs" / "architecture" / "AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md"
CURRENT_STATE = ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md"
HISTORICAL_CURRENT_STATE = (
    ROOT
    / "docs"
    / "architecture"
    / "historical"
    / "SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md"
)
CURRENT_GUIDANCE = [
    ROOT / "AGENTS.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
    ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
    ROOT / "docs" / "codex" / "ARCHITECTURE_GROOVE_PLAYBOOK.md",
    ROOT / "docs" / "codex" / "PHASE_BRIEF_TEMPLATE.md",
    ROOT / "docs" / "codex" / "EXECUTION_PLAN_TEMPLATE.md",
    ROOT / "docs" / "codex" / "PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md",
    CURRENT_STATE,
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ag94g_map_exists_and_names_orchestrator_as_target_surface() -> None:
    text = _read(AG94G)

    assert "core/pipeline_orchestrator.py" in text
    assert "target surface" in text
    assert "Authority Inventory Table" in text
    assert "Retrieval stop/continue" in text
    assert "Decision Packet For Next Strangler Phase" in text


def test_current_guidance_uses_current_surface_vocabulary() -> None:
    combined = "\n".join(_read(path) for path in CURRENT_GUIDANCE)

    for phrase in (
        "licensed surface",
        "target surface",
        "high-custody surface",
        "closed-this-phase surface",
        "historical surface",
        "strangler target",
        "Protected\" is retired as active phase-control vocabulary",
        "call it a high-custody target or strangler target, not protected",
    ):
        assert phrase in combined

    assert "line delta `0` is a scope-control fact" in combined
    assert "not architecture success" in combined


def test_current_guidance_does_not_make_orchestrator_sacred() -> None:
    combined = "\n".join(_read(path).casefold() for path in CURRENT_GUIDANCE)
    normalized = " ".join(combined.replace("`", "").split())

    forbidden_phrases = (
        "pipeline_orchestrator.py is protected",
        "pipeline_orchestrator.py remains protected",
        "pipeline_orchestrator.py is sacred",
        "orchestrator untouched is architecture success",
        "orchestrator untouched as architecture success",
    )
    assert [phrase for phrase in forbidden_phrases if phrase in combined] == []
    assert "core/pipeline_orchestrator.py is a coordination shell" in normalized
    assert "licensed target surface" in normalized
    assert "strangler target" in normalized


def test_current_state_is_redirect_stub_and_history_is_preserved() -> None:
    current = _read(CURRENT_STATE)
    historical = _read(HISTORICAL_CURRENT_STATE)

    assert "current-state redirect stub" in current
    assert "AG-94G supersession banner" in historical
    assert "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md" in current
    assert "AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md" in current
    assert "AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md" in current
    assert "Controller decides, orchestrator executes" not in current
    assert "Controller decides, orchestrator executes" in historical


def test_final_answer_source_telemetry_extraction_owner_preserves_behavior() -> None:
    telemetry = projection_source_telemetry(
        "Alpha [[9]](https://example.test/a) and beta [[2]](https://example.test/b).",
        {"quantitative_packet": {"source_ids_used": ["2", "8"]}},
    )

    assert telemetry == {
        "final_answer_source_ids_used": ["2", "9"],
        "final_answer_source_ids_not_in_packet": ["9"],
        "packet_source_ids_not_in_final_answer": ["8"],
        "final_answer_packet_source_ids_diverged": True,
        "final_answer_source_telemetry_shadow_mode": True,
    }


def test_orchestrator_no_longer_defines_source_telemetry_parser() -> None:
    orchestrator = _read(ROOT / "core" / "pipeline_orchestrator.py")
    projection = _read(ROOT / "core" / "post_author_output_projection.py")

    assert "def _extract_final_answer_source_ids" not in orchestrator
    assert "def _extract_final_answer_source_ids" in projection
    assert "def _final_answer_source_citation_telemetry" not in orchestrator
    assert "def _final_answer_source_citation_telemetry" in projection
