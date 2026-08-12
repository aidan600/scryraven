"""Offline guards for SearchJudgment FAST-profile and CLI effort wiring."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

from core.run_config import RunConfig
from core.searchos_slice_a_product_runtime import _invoke_judgment_model

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_runconfig_profile_effort_defaults() -> None:
    config = RunConfig(query="example")
    assert config.fast_reasoning_effort == "medium"
    assert config.smart_reasoning_effort == "medium"
    assert config.fast_provider == "OpenAI"
    assert config.smart_provider == "OpenAI"


def test_searchjudgment_uses_fast_profile_effort() -> None:
    captured: dict[str, Any] = {}

    def fake_ask(prompt: str, system_prompt: str, **kwargs: Any) -> str:
        captured.update(kwargs)
        return "{}"

    raw = _invoke_judgment_model(
        model_input={"authorized_request": {"schema_version": "x"}},
        ask_model=fake_ask,
        provider="FastProvider",
        model="fast-model",
        base_url=None,
        api_key=None,
        effort="medium",
        use_reasoning=True,
        measure_context_stage=None,
    )
    assert raw == "{}"
    assert captured["provider"] == "FastProvider"
    assert captured["model"] == "fast-model"
    assert captured["effort"] == "medium"
    assert captured["require_json"] is True
    assert captured["use_reasoning"] is True


def test_searchjudgment_orchestrator_wires_fast_profile() -> None:
    source = (REPO_ROOT / "core" / "pipeline_orchestrator.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    judgment_calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name in {
            "execute_searchos_slice_a_iterative_judgment",
            "execute_searchos_recovery_cycle",
        }:
            judgment_calls.append(node)
    assert judgment_calls
    for call in judgment_calls:
        keywords = {kw.arg: kw.value for kw in call.keywords if kw.arg}
        assert "provider" in keywords and "model" in keywords and "effort" in keywords
        provider = keywords["provider"]
        model = keywords["model"]
        effort = keywords["effort"]
        assert isinstance(provider, ast.Name) and provider.id == "fast_provider"
        assert isinstance(model, ast.Name) and model.id == "fast_model"
        assert isinstance(effort, ast.Name) and effort.id == "fast_reasoning_effort"


def test_searchjudgment_request_parity_surface() -> None:
    source = inspect.getsource(_invoke_judgment_model)
    assert "require_json=True" in source
    assert "use_reasoning=use_reasoning" in source
    assert 'effort="high"' not in source
    assert "effort=effort" in source


def test_ordinary_role_local_effort_overrides_removed_from_multicomponent() -> None:
    path = REPO_ROOT / "core" / "multicomponent_role_runtime.py"
    text = path.read_text(encoding="utf-8")
    assert 'effort="high"' not in text
    assert "effort=prepared.effort" in text
    assert "effort=effort" in text


def test_cli_reasoning_effort_flags_exist() -> None:
    text = (REPO_ROOT / "proplex" / "__main__.py").read_text(encoding="utf-8")
    assert "--fast-reasoning-effort" in text
    assert "--smart-reasoning-effort" in text
    assert "SCRYRAVEN_FAST_REASONING_EFFORT" in text
    assert "SCRYRAVEN_SMART_REASONING_EFFORT" in text
    assert "fast_reasoning_effort=args.fast_reasoning_effort" in text
    assert "smart_reasoning_effort=args.smart_reasoning_effort" in text
