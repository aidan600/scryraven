import ast
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_APP = _ROOT / "app.py"

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")


def test_project_has_current_entrypoint_files() -> None:
    assert _APP.exists()
    assert (_ROOT / "scryraven" / "__main__.py").exists()
    assert (_ROOT / "proplex" / "__main__.py").exists()
    assert (_ROOT / "README.md").exists()


def test_app_import_is_side_effect_free(tmp_path: Path) -> None:
    code = (
        "import pathlib, sys\n"
        "sys.dont_write_bytecode = True\n"
        f"sys.path.insert(0, {str(_ROOT)!r})\n"
        "before = set(pathlib.Path.cwd().iterdir())\n"
        "import app\n"
        "after = set(pathlib.Path.cwd().iterdir())\n"
        "assert before == after\n"
        "assert 'streamlit' not in sys.modules\n"
        "assert not any(name == 'ui' or name.startswith('ui.') for name in sys.modules)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == ""
    assert proc.stderr == ""
    assert not (tmp_path / "output").exists()


def test_app_is_a_dependency_closed_tombstone() -> None:
    source = _APP.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(_APP))
    imported_modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert imported_modules == {"sys"}
    assert "SCRYRAVEN_RUN_QUERY" not in source
    assert "PROPLEX_RUN_QUERY" not in source
    assert "load_dotenv" not in source
    assert "configure_storage" not in source


def test_executing_app_fails_closed_with_retirement_message() -> None:
    proc = subprocess.run(
        [sys.executable, str(_APP)],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )

    assert proc.returncode != 0
    message = proc.stdout + proc.stderr
    assert "legacy Streamlit shell is retired" in message
    assert "CLI is the current supported interface" in message
    assert "Future UI integration is intentionally undecided" in message


def test_current_docs_quarantine_streamlit_and_saved_thread_followup() -> None:
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    current = (
        _ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md"
    ).read_text(encoding="utf-8")
    containment = (
        _ROOT
        / "docs"
        / "architecture"
        / "AG_S1_QUANTITATIVE_FINALIZATION_CONTAINMENT_01.md"
    ).read_text(encoding="utf-8")
    normalized_containment = " ".join(containment.split())

    assert "streamlit run app.py" not in readme
    assert "python -m scryraven" in readme
    assert "python -m proplex" in readme
    assert "reference and migration only" in readme
    assert "no replacement ui framework has been selected" in readme.lower()

    assert "public CLI is the current supported executable interface" in current
    assert "legacy Streamlit shell" in current
    assert "saved-thread Streamlit follow-up" in current
    assert "not ordinary product consumption" in current
    assert "future conversation and follow-up product work" in current

    assert "retired from ordinary product use" in normalized_containment
    assert "future follow-up activation" in normalized_containment
    assert "shared accepted-prose validator" in normalized_containment


def test_public_and_compatibility_cli_help_remain_available() -> None:
    for module in ("scryraven", "proplex"):
        proc = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "ScryRaven" in proc.stdout
