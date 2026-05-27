"""PipelineConfig dataclass round-trip (session JSON compatibility)."""

from __future__ import annotations

from core.pipeline_config import UI_MODES, PipelineConfig


def test_from_mapping_defaults() -> None:
    assert PipelineConfig.from_mapping(None) == PipelineConfig()
    assert PipelineConfig.from_mapping({}) == PipelineConfig()


def test_from_mapping_coerces_strings() -> None:
    pc = PipelineConfig.from_mapping(
        {"intent": "news", "complexity": "high", "search_depth": "advanced", "mode": "Deep"}
    )
    assert pc.intent == "news"
    assert pc.complexity == "high"
    assert pc.search_depth == "advanced"
    assert pc.mode == "Deep"


def test_to_mapping_includes_none_search_depth() -> None:
    """Persist explicit nulls like older sessions may omit — callers may rely on key presence."""
    d = PipelineConfig(intent="general", complexity="low", search_depth=None, mode="Fast").to_mapping()
    assert d["search_depth"] is None
    assert d["mode"] == "Fast"


def test_ui_modes_frozen() -> None:
    assert "Balanced" in UI_MODES
