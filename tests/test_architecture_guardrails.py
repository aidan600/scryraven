"""Guardrails: headless import hygiene and no-Streamlit policy in core/proplex."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from core.protocols import ListStatusWriter, NullStatusWriter

_ROOT = Path(__file__).resolve().parents[1]


def test_proplex_main_import_does_not_load_streamlit() -> None:
    """Fresh interpreter: importing ``proplex.__main__`` must not load streamlit."""
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(_ROOT)!r})\n"
        "from proplex.__main__ import main\n"
        "assert 'streamlit' not in sys.modules, sorted(k for k in sys.modules if 'streamlit' in k)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def _streamlit_violations_in_file(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as e:
        pytest.fail(f"Syntax error in {path}: {e}")

    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == "streamlit" or name.startswith("streamlit."):
                    out.append((getattr(node, "lineno", 0), f"import {name}"))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module
            if mod and (mod == "streamlit" or mod.startswith("streamlit.")):
                out.append((getattr(node, "lineno", 0), f"from {mod} import ..."))
    return out


@pytest.mark.parametrize(
    "rel_dir",
    ["core", "proplex"],
    ids=["core", "proplex"],
)
def test_no_streamlit_imports_in_backend_packages(rel_dir: str) -> None:
    """``core/`` and ``proplex/`` must not import streamlit (AST check)."""
    root = _ROOT / rel_dir
    assert root.is_dir(), f"missing {root}"

    all_violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for lineno, snippet in _streamlit_violations_in_file(path):
            loc = f"{path.relative_to(_ROOT)}:{lineno}" if lineno else str(path.relative_to(_ROOT))
            all_violations.append(f"{loc}  {snippet}")

    assert not all_violations, "streamlit imports found:\n" + "\n".join(all_violations)


def test_null_status_writer_drops_calls() -> None:
    w = NullStatusWriter()
    w.update("a")
    w.step("b")
    w.write("c")
    w.done()


def test_list_status_writer_collects_calls() -> None:
    w = ListStatusWriter()
    w.update("u")
    w.step("s")
    w.write("w")
    w.done()
    assert w.log == [
        ("update", "u"),
        ("step", "s"),
        ("step", "w"),
        ("done", ""),
    ]
