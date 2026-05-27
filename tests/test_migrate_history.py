"""Tests for scripts/migrate_history.py (Sprint 5)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def _load_migrate():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "migrate_history.py"
    spec = importlib.util.spec_from_file_location("migrate_history", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migrate_execution_log_adds_missing_fields(tmp_path: Path) -> None:
    mh = _load_migrate()
    log = tmp_path / "execution_log.jsonl"
    log.write_text(
        json.dumps({"event": "run_completed", "run_id": "r1"}) + "\n",
        encoding="utf-8",
    )
    before = log.read_bytes()

    summary = mh.run_migration(tmp_path, apply=False)
    assert summary["files"]["execution_log.jsonl"]["changed"] is True
    st = summary["files"]["execution_log.jsonl"]["stats"]
    assert st["lines_touched"] == 1
    assert st["providers_used"] == 1
    assert log.read_bytes() == before

    mh.run_migration(tmp_path, apply=True)
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    obj = json.loads(lines[0])
    assert obj["providers_used"] == ["exa"]
    assert obj["retrieval_yield_chunks"] == 0
    assert obj["timing"] == {}
    assert obj["mode"] == "Balanced"
    assert log.with_suffix(log.suffix + ".bak").exists()


def test_migrate_history_sets_last_report_mode_preserves_existing(tmp_path: Path) -> None:
    mh = _load_migrate()
    hist = tmp_path / "history.json"
    hist.write_text(
        json.dumps(
            [
                {"id": "s1", "title": "t", "last_report_mode": "Fast", "pipeline_config": {"depth": "basic"}},
                {"id": "s2", "title": "u"},
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    mh.run_migration(tmp_path, apply=True)
    data = json.loads(hist.read_text(encoding="utf-8"))
    assert data[0]["last_report_mode"] == "Fast"
    assert data[0]["pipeline_config"]["mode"] == "Fast"
    assert data[1]["last_report_mode"] == mh.DEFAULT_MODE
    assert data[1]["pipeline_config"]["mode"] == mh.DEFAULT_MODE


def test_migrate_passages_source_id_is_deterministic(tmp_path: Path) -> None:
    mh = _load_migrate()
    pf = tmp_path / "abc_passages.json"
    pf.write_text(
        json.dumps(
            [
                {"url": "https://example.com/a", "text": "x", "date": "2020-01-01"},
                {"url": "https://example.com/a", "text": "y", "source_id": 99},
            ]
        ),
        encoding="utf-8",
    )
    mh.run_migration(tmp_path, apply=True)
    passages = json.loads(pf.read_text(encoding="utf-8"))
    expected = mh.passage_source_id("https://example.com/a", "2020-01-01")
    assert passages[0]["source_id"] == expected
    assert passages[1]["source_id"] == 99


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    mh = _load_migrate()
    (tmp_path / "execution_log.jsonl").write_text(
        '{"event":"x","run_id":"a"}\n',
        encoding="utf-8",
    )
    (tmp_path / "history.json").write_text("[]", encoding="utf-8")

    mh.run_migration(tmp_path, apply=True)
    exec_after_first = (tmp_path / "execution_log.jsonl").read_text(encoding="utf-8")

    s2 = mh.run_migration(tmp_path, apply=True)
    assert s2["files"]["execution_log.jsonl"]["stats"]["lines_touched"] == 0
    assert s2["files"]["execution_log.jsonl"]["changed"] is False
    exec_after_second = (tmp_path / "execution_log.jsonl").read_text(encoding="utf-8")
    assert exec_after_first == exec_after_second


def test_migrate_history_cli_dry_run_smoke(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "migrate_history.py"
    (tmp_path / "execution_log.jsonl").write_text("{}\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "migrate_history" in r.stdout


def test_migrate_history_cli_apply_smoke(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "migrate_history.py"
    log = tmp_path / "execution_log.jsonl"
    log.write_text('{"event":"run_started","run_id":"z"}\n', encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(tmp_path), "--apply"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    obj = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[0])
    assert "providers_used" in obj
