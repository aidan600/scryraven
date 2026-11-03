"""Hosted diagnostic custody and retention use synthetic source material only."""

import io
import json
import os
import zipfile
from threading import Event
from types import SimpleNamespace

import pytest

from scryraven.dogfood_diagnostics import TurnDiagnostics
from scryraven.hosted_diagnostics import HostedDiagnostics


def job(number=1, *, session=1, state="completed"):
    return SimpleNamespace(job_id=f"{number:032x}", session_id=f"{session:032x}",
                           revision=0, state=state)


def test_separate_body_free_summary_and_full_observer_association(tmp_path):
    sink = HostedDiagnostics(tmp_path / "diagnostics")
    current = job()
    event = {"stage": "research", "action": "acquired_material",
             "material": {"content": "SYNTHETIC_EXACT_SOURCE_BODY"}}
    safe = TurnDiagnostics()
    safe.observe(event)
    sink.observe(event, job=current, owner_id="tester@example.test")
    sink.finish(safe.record(session_id=current.session_id, revision_before=0, revision_after=1),
                job=current, owner_id="tester@example.test")
    files = sink.export(current.session_id)
    assert len(files) == 2
    forensic = json.loads(next(value for name, value in files.items() if name.endswith("jsonl")))
    summary_bytes = next(value for name, value in files.items() if name.endswith("diagnostic.json"))
    summary = json.loads(summary_bytes)
    assert forensic["event"] == event
    assert forensic["owner_id"] == summary["owner_id"] == "tester@example.test"
    assert forensic["session_id"] == summary["session_id"] == current.session_id
    assert forensic["job_id"] == summary["job_id"] == current.job_id
    assert forensic["run_id"] == summary["run_id"]
    assert forensic["event_sequence"] == 1
    assert summary["forensic_events"] == 1 and summary["forensic_stopped"] is None
    assert b"SYNTHETIC_EXACT_SOURCE_BODY" not in summary_bytes
    usage = sink.usage()
    assert usage["bytes"] == usage["managed_bytes"] == sum(map(len, files.values()))
    assert usage["files"] == 2 and usage["enabled"]


def test_age_retention_and_restart_leave_conversations_and_evidence_untouched(tmp_path):
    now = [100.0]
    folder = tmp_path / "diagnostics"
    database = tmp_path / "sessions.sqlite3"
    database.write_bytes(b"SYNTHETIC_CONVERSATIONS_CITATIONS_AND_EVIDENCE")
    sink = HostedDiagnostics(folder, clock=lambda: now[0])
    sink.observe({"body": "synthetic"}, job=job(), owner_id="tester")
    sink.finish(job=job(), owner_id="tester")
    # Unknown files are never managed, even if old or similarly named.
    unknown = folder / "operator-notes.txt"
    unknown.write_bytes(b"preserve")
    now[0] += 31 * 86400
    restarted = HostedDiagnostics(folder, clock=lambda: now[0])
    assert restarted.export(job().session_id) == {}
    assert restarted.usage()["unmanaged_files"] == 1
    assert unknown.read_bytes() == b"preserve"
    assert database.read_bytes() == b"SYNTHETIC_CONVERSATIONS_CITATIONS_AND_EVIDENCE"


def test_total_budget_evicts_oldest_complete_job_as_a_pair(tmp_path):
    now = [100.0]
    sink = HostedDiagnostics(tmp_path / "diagnostics", max_bytes=2200,
                             max_file_bytes=2000, clock=lambda: now[0])
    sink.observe({"body": "a" * 250}, job=job(), owner_id="first")
    sink.finish(job=job(), owner_id="first")
    assert sink.export(job().session_id)
    now[0] += 1
    sink.observe({"body": "b" * 900}, job=job(2, session=2), owner_id="second")
    sink.finish(job=job(2, session=2), owner_id="second")
    assert sink.export(job().session_id) == {}
    assert len(sink.export(job(2, session=2).session_id)) == 2
    assert sink.usage()["bytes"] <= 2200


def test_per_file_limit_stops_whole_lines_and_reports_truncation(tmp_path):
    sink = HostedDiagnostics(tmp_path / "diagnostics", max_file_bytes=1000)
    current = job()
    sink.observe({"body": "a" * 100}, job=current, owner_id="tester")
    sink.observe({"body": "b" * 1200}, job=current, owner_id="tester")
    sink.observe({"body": "ignored-after-full"}, job=current, owner_id="tester")
    sink.finish(job=current, owner_id="tester")
    files = sink.export(current.session_id)
    forensic = next(value for name, value in files.items() if name.endswith("jsonl"))
    assert len(forensic.splitlines()) == 1
    assert json.loads(forensic)["event"]["body"] == "a" * 100
    summary = json.loads(next(value for name, value in files.items() if name.endswith("diagnostic.json")))
    assert summary["forensic_stopped"] == "file_limit"
    assert all(len(value) <= 1000 for value in files.values())


def test_active_file_budget_is_hard_and_does_not_delete_other_active_user(tmp_path):
    sink = HostedDiagnostics(tmp_path / "diagnostics", max_bytes=1600, max_file_bytes=1500)
    sink.observe({"body": "a" * 500}, job=job(), owner_id="first")
    first = sink.export(job().session_id)
    sink.observe({"body": "b" * 900}, job=job(2, session=2), owner_id="second")
    assert sink.export(job().session_id) == first
    assert sink.usage()["bytes"] <= 1600
    sink.finish(job=job(2, session=2), owner_id="second")
    assert sink.usage()["bytes"] <= 1600


def test_selected_session_export_is_streamed_and_rejects_traversal(tmp_path):
    sink = HostedDiagnostics(tmp_path / "diagnostics")
    for current in (job(), job(2, session=2)):
        sink.observe({"body": current.session_id}, job=current, owner_id="tester")
        sink.finish(job=current, owner_id="tester")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        sink.add_to_archive(archive, job().session_id)
    with zipfile.ZipFile(buffer) as archive:
        assert len(archive.namelist()) == 2
        assert all(name.startswith("diagnostics/" + job().session_id + ".") for name in archive.namelist())
        assert all(job(2, session=2).session_id.encode() not in archive.read(name)
                   for name in archive.namelist())
    with pytest.raises(ValueError, match="invalid_diagnostic_identity"):
        sink.export("../../sessions.sqlite3")


def test_file_aliases_are_never_modified_exported_or_deleted(tmp_path):
    folder = tmp_path / "diagnostics"
    sink = HostedDiagnostics(folder, max_bytes=1024)
    protected = tmp_path / "sessions.sqlite3"
    protected.write_bytes(b"SYNTHETIC_DB_SENTINEL")
    current = job()
    alias = folder / f"{current.session_id}.{current.job_id}.forensic.jsonl"
    try:
        os.link(protected, alias)
    except OSError:
        pytest.skip("Hard links unavailable on this filesystem")
    sink.observe({"body": "must not write"}, job=current, owner_id="tester")
    sink.finish(job=current, owner_id="tester")
    assert protected.read_bytes() == b"SYNTHETIC_DB_SENTINEL"
    assert alias.exists()
    assert alias.name not in sink.export(current.session_id)
    assert sink.usage()["unmanaged_files"] == 1


def test_write_failure_is_contained_without_raw_error_output(tmp_path, monkeypatch, capsys):
    sink = HostedDiagnostics(tmp_path / "diagnostics")

    def denied(*args, **kwargs):
        raise OSError("SYNTHETIC_PRIVATE_FILESYSTEM_DETAIL")

    monkeypatch.setattr(sink, "_append", denied)
    sink.observe({"body": "synthetic"}, job=job(), owner_id="tester")
    sink.finish(job=job(), owner_id="tester")
    assert "SYNTHETIC_PRIVATE_FILESYSTEM_DETAIL" not in capsys.readouterr().err
    assert not sink._active


def test_missing_user_association_disables_only_the_incomplete_diagnostic_copy(tmp_path):
    sink = HostedDiagnostics(tmp_path / "diagnostics")
    sink.observe({"body": "synthetic"}, job=job(), owner_id=None)
    sink.finish(job=job(), owner_id=None)
    assert sink.export(job().session_id) == {}
    assert not sink._active


def test_periodic_maintenance_removes_expired_files_while_service_is_idle(tmp_path, monkeypatch):
    now = [100.0]
    sink = HostedDiagnostics(tmp_path / "diagnostics", clock=lambda: now[0])
    sink.observe({"body": "synthetic"}, job=job(), owner_id="tester")
    sink.finish(job=job(), owner_id="tester")
    assert len(tuple(sink.directory.iterdir())) == 2
    now[0] += 31 * 86400
    cleaned = Event()
    ordinary_maintenance = sink.maintenance

    def observe_cleanup():
        ordinary_maintenance()
        cleaned.set()

    monkeypatch.setattr(sink, "maintenance", observe_cleanup)
    try:
        assert sink.start_maintenance(interval_seconds=0.01)
        thread = sink._maintenance_thread
        assert sink.start_maintenance(interval_seconds=0.01)
        assert sink._maintenance_thread is thread
        assert cleaned.wait(2), "Idle cleanup did not run"
        # No usage/export/read request is needed to trigger this removal.
        assert tuple(sink.directory.iterdir()) == ()
    finally:
        sink.close()
        sink.close()
    assert not thread.is_alive()
    assert not sink.start_maintenance(interval_seconds=0.01)


def test_periodic_maintenance_keeps_active_job_files(tmp_path, monkeypatch):
    now = [100.0]
    sink = HostedDiagnostics(tmp_path / "diagnostics", clock=lambda: now[0])
    sink.observe({"body": "synthetic active file"}, job=job(), owner_id="tester")
    now[0] += 31 * 86400
    cleaned = Event()
    ordinary_maintenance = sink.maintenance

    def observe_cleanup():
        ordinary_maintenance()
        cleaned.set()

    monkeypatch.setattr(sink, "maintenance", observe_cleanup)
    try:
        assert sink.start_maintenance(interval_seconds=0.01)
        assert cleaned.wait(2)
        assert len(tuple(sink.directory.iterdir())) == 1
        assert sink._enabled
    finally:
        sink.close()


def test_periodic_failure_disables_only_diagnostics_without_raw_traceback(tmp_path, monkeypatch, capsys):
    sink = HostedDiagnostics(tmp_path / "diagnostics")
    failure_contained = Event()

    def failing_cleanup():
        if not sink._enabled:
            failure_contained.set()
        raise OSError("SYNTHETIC_PRIVATE_FILESYSTEM_PATH")

    monkeypatch.setattr(sink, "maintenance", failing_cleanup)
    try:
        assert sink.start_maintenance(interval_seconds=0.01)
        assert failure_contained.wait(2)
        assert not sink._enabled
        sink.observe({"body": "not recorded after storage failure"}, job=job(), owner_id="tester")
        assert tuple(sink.directory.iterdir()) == ()
    finally:
        sink.close()
    assert "SYNTHETIC_PRIVATE_FILESYSTEM_PATH" not in capsys.readouterr().err


@pytest.mark.parametrize("interval", [0, -1, float("nan"), float("inf"), True])
def test_periodic_maintenance_rejects_invalid_intervals_without_threads(tmp_path, interval):
    sink = HostedDiagnostics(tmp_path / "diagnostics")
    with pytest.raises(ValueError, match="invalid_diagnostic_maintenance_interval"):
        sink.start_maintenance(interval)
    assert sink._maintenance_thread is None
    sink.close()


@pytest.mark.parametrize("setting", [{"retention_days": 0}, {"max_bytes": -1}, {"max_file_bytes": 0}])
def test_invalid_limits_fail_startup(tmp_path, setting):
    with pytest.raises(ValueError, match="invalid_diagnostic_retention"):
        HostedDiagnostics(tmp_path / "diagnostics", **setting)
