from pathlib import Path


def test_project_has_core_files() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "app.py").exists()
    assert (root / "requirements.txt").exists()
    assert (root / "README.md").exists()


def test_readme_mentions_run_command() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "streamlit run app.py" in readme
