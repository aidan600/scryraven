from __future__ import annotations

import ast
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from core.document_review import build_document_review_context
from core.project_sources import add_project_source_from_document_review, create_project, list_project_sources
from core.thread_reports import (
    GENERATED_ARTIFACT_LABEL,
    NO_RETRIEVAL_INTEGRATION_LABEL,
    NOT_PRIMARY_EVIDENCE_LABEL,
    THREAD_REPORT_SYSTEM_PROMPT,
    THREAD_REPORT_TYPE,
    build_report_input_packet,
    build_thread_report_prompt,
    format_thread_report_row,
    generate_and_save_thread_report,
    list_thread_reports,
    load_thread_report,
    load_thread_report_body,
    save_thread_report_artifact,
    thread_report_boundary_caption,
)
from ui.pages_projects import (
    format_thread_report_download_name,
    save_thread_report_to_project,
    thread_attachment_refs_from_document_review_context,
)


def _clock() -> datetime:
    return datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)


def _ids():
    values = iter(("proj_ag86a", "src_ag86a", "rev_ag86a", "psrc_ag86a", "rpt_ag86a"))

    def factory(prefix: str) -> str:
        return next(values)

    return factory


def _session() -> dict[str, object]:
    return {
        "id": "sess_1",
        "run_id": "run_1",
        "title": "Mars launch window",
        "query": "Summarize the launch decision",
        "timestamp": "2026-06-05T11:00:00+00:00",
        "report": "Final answer: launch is blocked until telemetry source [1] is reconciled.",
        "chat_messages": [
            {"role": "user", "content": "Should we launch?"},
            {"role": "assistant", "content": "Only with caveats from source [1]."},
        ],
        "top_passages": [
            {
                "source_id": 1,
                "title": "Telemetry memo",
                "domain": "example.test",
                "url": "https://example.test/telemetry",
                "text": "Telemetry shows a missing final check.",
            }
        ],
    }


def test_report_input_packet_packages_available_and_missing_fields(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("Reports", storage_root=tmp_path, clock=_clock, id_factory=ids)
    context = build_document_review_context(
        "# Local memo\n\nA document-local launch constraint exists.", created_at=_clock()
    )
    promoted = add_project_source_from_document_review(
        project,
        context,
        storage_root=tmp_path,
        clock=_clock,
        id_factory=ids,
    )

    packet = build_report_input_packet(_session(), promoted.project, storage_root=tmp_path)

    assert packet.report_type == THREAD_REPORT_TYPE
    assert packet.project["project_id"] == "proj_ag86a"
    assert packet.thread["session_id"] == "sess_1"
    assert len(packet.messages) == 2
    assert packet.final_report["available"] is True
    assert any(ref.reference_type == "thread_web_evidence" for ref in packet.provenance_references)
    assert any(ref.project_source_id == "psrc_ag86a" for ref in packet.provenance_references)
    assert GENERATED_ARTIFACT_LABEL in packet.evidence_posture_labels
    assert NOT_PRIMARY_EVIDENCE_LABEL in packet.evidence_posture_labels
    assert NO_RETRIEVAL_INTEGRATION_LABEL in packet.evidence_posture_labels
    assert packet.missing == ()
    assert list_project_sources(promoted.project, storage_root=tmp_path)


def test_report_input_packet_records_unavailable_provenance(tmp_path: Path) -> None:
    project = create_project("Sparse", storage_root=tmp_path, clock=_clock, id_factory=lambda prefix: "proj_sparse")

    packet = build_report_input_packet({"id": "sess_sparse", "query": "Q"}, project, storage_root=tmp_path)

    assert packet.messages[0]["message_id"] == "thread_query"
    assert packet.final_report["available"] is False
    assert "assistant final report unavailable" in packet.missing
    assert "thread retrieved evidence unavailable" in packet.missing
    assert "source/provenance references unavailable" in packet.missing
    assert "some-provenance-may-be-unavailable" in packet.evidence_posture_labels


def test_prompt_template_is_scoped_to_thread_reports_and_preserves_boundaries(tmp_path: Path) -> None:
    project = create_project("Prompt", storage_root=tmp_path, clock=_clock, id_factory=lambda prefix: "proj_prompt")
    packet = build_report_input_packet(_session(), project, storage_root=tmp_path)

    prompt = build_thread_report_prompt(packet)

    assert "structured Markdown thread report" in prompt
    assert "generated Project artifact" in prompt
    assert "not primary evidence" in prompt
    assert "Do not invent sources" in prompt
    assert "JSON packet" in prompt
    assert "normal chat Author" in THREAD_REPORT_SYSTEM_PROMPT
    assert "Do not perform search, retrieval" in THREAD_REPORT_SYSTEM_PROMPT


def test_fake_model_generation_seam_and_save_load_list_behavior(tmp_path: Path) -> None:
    values = iter(("proj_save", "rpt_ag86a"))
    ids = lambda prefix: next(values)
    project = create_project("Save Report", storage_root=tmp_path, clock=_clock, id_factory=ids)
    calls: list[tuple[str, str]] = []

    def fake_model(prompt: str, system_prompt: str) -> str:
        calls.append((prompt, system_prompt))
        return "# Generated report\n\nGenerated Project artifact; not primary evidence.\n\n## Evidence\n- See thread_evidence_1."

    result = generate_and_save_thread_report(
        _session(),
        project,
        fake_model,
        storage_root=tmp_path,
        title="Launch thread synthesis",
        clock=_clock,
        id_factory=ids,
    )

    assert len(calls) == 1
    assert "thread report" in calls[0][0]
    assert calls[0][1] == THREAD_REPORT_SYSTEM_PROMPT
    assert result.artifact.report_id == "rpt_ag86a"
    assert result.artifact.generated_artifact is True
    assert result.artifact.not_primary_evidence == NOT_PRIMARY_EVIDENCE_LABEL
    assert result.artifact.body_path == "reports/bodies/rpt_ag86a.md"
    assert result.artifact_manifest_path == tmp_path / "reports" / "rpt_ag86a.json"
    assert result.body_path == tmp_path / "reports" / "bodies" / "rpt_ag86a.md"
    assert "generated-project-artifact" in result.body
    assert load_thread_report("rpt_ag86a", storage_root=tmp_path) == result.artifact
    assert load_thread_report_body(result.artifact, storage_root=tmp_path) == result.body
    assert list_thread_reports(project, storage_root=tmp_path) == (result.artifact,)

    row = format_thread_report_row(result.artifact)
    assert row["Generated artifact"] is True
    assert row["Not primary evidence"] == NOT_PRIMARY_EVIDENCE_LABEL
    assert row["Retrieval integration"] == NO_RETRIEVAL_INTEGRATION_LABEL


def test_save_thread_report_artifact_does_not_create_project_source(tmp_path: Path) -> None:
    project = create_project(
        "No Launder", storage_root=tmp_path, clock=_clock, id_factory=lambda prefix: "proj_nolaunder"
    )
    packet = build_report_input_packet(_session(), project, storage_root=tmp_path)

    result = save_thread_report_artifact(
        project,
        "# Report\n\nGenerated Project artifact; not primary evidence.",
        packet,
        storage_root=tmp_path,
        title="Not source",
        clock=_clock,
        id_factory=lambda prefix: "rpt_nolaunder",
    )

    assert list_project_sources(project, storage_root=tmp_path) == ()
    assert list_thread_reports(project, storage_root=tmp_path) == (result.artifact,)
    relative_dirs = {path.relative_to(tmp_path).parts[0] for path in tmp_path.rglob("*") if path.is_file()}
    assert "project_sources" not in relative_dirs
    assert "reports" in relative_dirs


def test_thread_attachment_refs_from_document_review_context_are_compact() -> None:
    raw_document = "# Attachment\n\n" + "PRIVATE ATTACHMENT DETAIL " * 80 + "NEVER_EXPOSE_ATTACHMENT_TAIL"
    context = build_document_review_context(raw_document, created_at=_clock())

    refs = thread_attachment_refs_from_document_review_context(context)
    combined = str(refs)

    assert refs[0]["reference_type"] == "thread_document_review_attachment"
    assert "document-local-thread-attachment-reference" in refs[0]["posture_label"]
    assert any(ref["reference_type"] == "thread_document_anchor_reference" for ref in refs)
    assert context.normalized_text not in combined
    assert "NEVER_EXPOSE_ATTACHMENT_TAIL" not in combined


def test_ui_save_helper_and_formatting_use_fake_model(tmp_path: Path) -> None:
    project = create_project(
        "UI Report", storage_root=tmp_path, clock=_clock, id_factory=lambda prefix: "proj_ui_report"
    )

    def fake_model(prompt: str, system_prompt: str) -> str:
        assert system_prompt == THREAD_REPORT_SYSTEM_PROMPT
        return "# UI saved report\n\nGenerated Project artifact; not primary evidence."

    result = save_thread_report_to_project(
        _session(),
        project,
        fake_model,
        storage_root=tmp_path,
        title="UI saved report",
    )

    assert result.artifact.project_id == project.project_id
    assert format_thread_report_download_name("rpt", "UI saved report!") == "ui-saved-report-rpt.md"
    caption = thread_report_boundary_caption()
    assert "Generated Project artifact" in caption
    assert "not primary evidence" in caption
    assert "No retrieval integration" in caption


def test_report_artifact_storage_does_not_persist_raw_private_document_text(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("Privacy", storage_root=tmp_path, clock=_clock, id_factory=ids)
    raw_document = "# Private\n\n" + "ALPHA PRIVATE DETAIL " * 80 + "NEVER_STORE_REPORT_SOURCE_TAIL"
    context = build_document_review_context(raw_document, created_at=_clock())
    promoted = add_project_source_from_document_review(
        project,
        context,
        storage_root=tmp_path,
        clock=_clock,
        id_factory=ids,
    )

    def fake_model(_prompt: str, system_prompt: str) -> str:
        assert system_prompt == THREAD_REPORT_SYSTEM_PROMPT
        return "# Privacy report\n\nGenerated Project artifact; not primary evidence."

    generate_and_save_thread_report(
        _session(),
        promoted.project,
        fake_model,
        storage_root=tmp_path,
        clock=_clock,
        id_factory=ids,
    )

    combined_reports = "\n".join(
        path.read_text(encoding="utf-8") for path in (tmp_path / "reports").rglob("*") if path.is_file()
    )
    assert context.normalized_text not in combined_reports
    assert "NEVER_STORE_REPORT_SOURCE_TAIL" not in combined_reports
    assert "psrc_ag86a" in combined_reports


def test_thread_reports_module_has_no_closed_surface_imports_or_calls() -> None:
    module = ast.parse(Path("core/thread_reports.py").read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    call_names: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                call_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                call_names.add(node.func.attr)

    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.pipeline",
        "core.prompts",
        "core.llm",
        "core.search_providers",
        "core.retrieval",
        "core.storage",
        "core.db",
        "core.run_logging",
    }
    assert imported_modules.isdisjoint(forbidden_imports)
    assert {"process_search_queries", "embed_texts", "ask_model"}.isdisjoint(call_names)


def test_normal_author_prompt_and_orchestrator_surfaces_unchanged_by_report_module() -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if "core/pipeline_orchestrator.py" in changed:
        diff = subprocess.run(
            ["git", "diff", "HEAD", "--", "core/pipeline_orchestrator.py"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert (
            "final_answer_runtime_adapter" in diff
            or "FinalAnswerPacket" in diff
            or "pre_author_source_obligation_projection" in diff
        )
    assert "core/prompts.py" not in changed
