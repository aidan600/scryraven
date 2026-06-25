from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUNNER_PATH = ROOT / "scripts" / "ag_live_bound_01_bounded_product_runner.py"
SUPPORT_PATH = ROOT / "scripts" / "ag_live_bound_01_support.py"
DEFAULT_OUTPUT = ROOT / "output" / "ag_live_bound_01_packet.json"

PRIMARY_QUERY = (
    "According to the official Python 3 documentation, what are the default "
    "values for rel_tol and abs_tol in math.isclose()?"
)
VALID_ARGS = [
    "--query",
    PRIMARY_QUERY,
    "--mode",
    "Balanced",
    "--include-domains",
    "docs.python.org",
    "--output",
    "output/ag_live_bound_01_packet.json",
]


def _ensure_scripts_package() -> None:
    if "scripts" not in sys.modules:
        scripts_pkg = ModuleType("scripts")
        scripts_pkg.__path__ = [str(ROOT / "scripts")]  # type: ignore[attr-defined]
        sys.modules["scripts"] = scripts_pkg


def _load_module(path: Path, module_name: str) -> ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]
    _ensure_scripts_package()
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_runner() -> ModuleType:
    return _load_module(
        RUNNER_PATH,
        "scripts.ag_live_bound_01_bounded_product_runner",
    )


def _load_support() -> ModuleType:
    return _load_module(SUPPORT_PATH, "scripts.ag_live_bound_01_support")


def _gitignored_output_path(name: str) -> str:
    return f"output/{name}"


@pytest.fixture(autouse=True)
def _cleanup_output_packets() -> Any:
    yield
    for path in ROOT.glob("output/ag_live_bound_01*.json"):
        if path.exists():
            path.unlink()


def test_dry_run_writes_sanitized_packet(tmp_path: Path) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_dry_run_packet.json")

    result = runner.main([*VALID_ARGS, "--output", output])

    assert result == 0
    packet_path = ROOT / output
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["dry_run"] is True
    assert packet["confirm_live_product_run"] is False
    assert packet["planned_live_dispatch"] is False
    assert packet["packet_marker"] == "LOCAL/UNTRACKED — DO NOT COMMIT"
    assert packet["caps_requested"]["max_search_dispatches"] == 2
    assert packet["caps_observed"]["enforcement"] == "not_executed"


def test_dry_run_never_calls_run_pipeline(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_no_pipeline.json")

    with patch("core.pipeline_orchestrator.run_pipeline") as run_pipeline:
        result = runner.main([*VALID_ARGS, "--output", output])

    run_pipeline.assert_not_called()
    assert result == 0
    capsys.readouterr()


def test_confirm_live_fails_closed_before_run_pipeline(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_confirm_fail_closed.json")

    with patch("core.pipeline_orchestrator.run_pipeline") as run_pipeline:
        result = runner.main(
            [
                *VALID_ARGS,
                "--output",
                output,
                "--confirm-live-product-run",
            ]
        )

    run_pipeline.assert_not_called()
    captured = capsys.readouterr()
    assert result == 2
    assert "live_execution_not_enabled_in_ag_live_bridge_01" in captured.err

    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    assert packet["confirm_live_product_run"] is True
    assert packet["planned_live_dispatch"] is False
    assert packet["primary_stop_reason"] == (
        "live_execution_not_enabled_in_ag_live_bridge_01"
    )
    assert "orchestrator_utilization_retry_not_disableable" in packet["stop_reasons"]


def test_unsafe_output_path_blocks(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()

    result = runner.main(
        [
            *VALID_ARGS,
            "--output",
            str(ROOT / "docs" / "ag_live_bound_01_packet.json"),
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "output path must be under ignored repo output/" in captured.err


def test_tracked_output_path_blocks(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()

    def fake_gitignored(_root: Path, _path: Path) -> bool:
        return False

    monkeypatch.setattr(
        "scripts.ag_live_bound_01_support.is_gitignored",
        fake_gitignored,
    )
    result = runner.main(
        [
            *VALID_ARGS,
            "--output",
            _gitignored_output_path("ag_live_bound_01_tracked.json"),
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "output path must be under ignored repo output/" in captured.err


def test_missing_domain_allowlist_blocks(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_missing_domain.json")

    result = runner.main(
        [
            "--query",
            PRIMARY_QUERY,
            "--mode",
            "Balanced",
            "--include-domains",
            "example.com",
            "--output",
            output,
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "docs.python.org" in captured.err


def test_non_exact_query_blocks(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_bad_query.json")

    result = runner.main(
        [
            "--query",
            "What is math.isclose?",
            "--mode",
            "Balanced",
            "--include-domains",
            "docs.python.org",
            "--output",
            output,
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "query must match" in captured.err


def test_backup_query_requires_flag(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_backup_without_flag.json")
    backup_query = (
        "According to the official Python 3 documentation, what are the default "
        "values for start and step in itertools.count()?"
    )

    result = runner.main(
        [
            "--query",
            backup_query,
            "--mode",
            "Balanced",
            "--include-domains",
            "docs.python.org",
            "--output",
            output,
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "query must match" in captured.err


def test_caps_serialized_and_validated(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_caps_ok.json")

    result = runner.main([*VALID_ARGS, "--output", output])
    assert result == 0
    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    assert packet["caps_requested"]["max_retries"] == 0

    bad_caps_result = runner.main(
        [
            *VALID_ARGS,
            "--output",
            _gitignored_output_path("ag_live_bound_01_bad_caps.json"),
            "--max-search-dispatches",
            "3",
        ]
    )
    captured = capsys.readouterr()
    assert bad_caps_result == 2
    assert "caps must match" in captured.err


def test_cap_overflow_fails_closed_with_fake_wrappers() -> None:
    support = _load_support()
    caps = support.AgLiveBoundCaps(max_search_dispatches=1)

    def fake_search(*_args: Any, **_kwargs: Any) -> list[Any]:
        return []

    wrapped = support.compose_capped_run_callables(
        process_search_queries=fake_search,
        fetch_linkup_precision_block=lambda *_a, **_k: None,
        ask_model=lambda *_a, **_k: None,
        caps=caps,
    )

    wrapped.process_search_queries("q")
    with pytest.raises(RuntimeError, match="search_dispatch budget exceeded"):
        wrapped.process_search_queries("q")


def test_author_and_smart_judgment_counters_with_fake_wrappers() -> None:
    support = _load_support()
    caps = support.AgLiveBoundCaps(
        max_author_model_calls=1,
        max_smart_search_judgment_model_calls=0,
    )

    wrapped = support.compose_capped_run_callables(
        process_search_queries=lambda *_a, **_k: [],
        fetch_linkup_precision_block=lambda *_a, **_k: None,
        ask_model=lambda *_a, **_k: "ok",
        caps=caps,
    )

    wrapped.ask_model("x", cost_phase="author")
    with pytest.raises(RuntimeError, match="smart_search_judgment_model_call budget exceeded"):
        wrapped.ask_model("x", cost_phase="search_judgment")


def test_forbidden_packet_fields_absent() -> None:
    support = _load_support()
    context = support.build_preflight_context(
        root=ROOT,
        query=PRIMARY_QUERY,
        mode="Balanced",
        include_domains=["docs.python.org"],
        output_path=DEFAULT_OUTPUT,
        caps=support.AgLiveBoundCaps(),
        run_id="test-run",
        confirm_live_product_run=False,
        approved_backup_query=False,
    )
    packet = support.build_dry_run_packet(context)
    support.reject_forbidden_packet(packet)


def test_dry_run_module_does_not_reference_live_imports() -> None:
    runner_source = RUNNER_PATH.read_text(encoding="utf-8")
    support_source = SUPPORT_PATH.read_text(encoding="utf-8")
    forbidden_tokens = (
        "run_pipeline",
        "load_dotenv",
        "request_live_validation_broker",
        "search_providers",
        "dotenv",
    )
    for token in forbidden_tokens:
        assert token not in runner_source
    support_tree = ast.parse(support_source)
    imported = {
        alias.name
        for node in ast.walk(support_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {
        node.module
        for node in ast.walk(support_tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "run_pipeline" not in imported
    assert "dotenv" not in imported
    assert all("pipeline_orchestrator" not in (name or "") for name in imported_from)


def test_dry_run_no_dotenv_broker_env_access(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_no_env.json")

    def fail_dotenv(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("dotenv must not be loaded in dry-run")

    def fail_broker(*_args: Any, **_kwargs: Any) -> int:
        raise AssertionError("broker client must not be invoked in dry-run")

    monkeypatch.setitem(sys.modules, "dotenv", type(sys)("dotenv"))
    sys.modules["dotenv"].load_dotenv = fail_dotenv  # type: ignore[attr-defined]
    broker_module = _load_module(
        ROOT / "scripts" / "request_live_validation_broker.py",
        "request_live_validation_broker_test_guard",
    )
    monkeypatch.setattr(broker_module, "main", fail_broker)

    result = runner.main([*VALID_ARGS, "--output", output])
    capsys.readouterr()
    assert result == 0


def test_is_allowed_output_path_requires_gitignore() -> None:
    support = _load_support()
    allowed = support.is_allowed_output_path(ROOT, ROOT / "output" / "probe.json")
    assert allowed == support.is_gitignored(ROOT, ROOT / "output" / "probe.json")
    assert support.is_allowed_output_path(ROOT, ROOT / "README.md") is False


def test_runner_ast_has_no_run_pipeline_import() -> None:
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"))
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
        for alias in node.names
    }
    assert "run_pipeline" not in imported_names
    assert "run_pipeline" not in imported_from
    assert "dotenv" not in imported_names
    assert all("pipeline_orchestrator" not in name for name in imported_from)
