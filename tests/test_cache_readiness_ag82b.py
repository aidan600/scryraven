from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

from core.cache_readiness import (
    AG82B_REUSE_DISABLED_REASON,
    CACHE_READINESS_GENERATOR,
    CACHE_READINESS_SCHEMA_VERSION,
    NO_RUNTIME_REUSE_POSTURE,
    REDACTION_MARKER,
    build_cache_readiness_record,
    build_document_chunk_cache_candidate,
    build_document_parse_cache_candidate,
    build_future_project_source_index_cache_candidate,
    build_project_source_cache_candidate,
    build_report_packet_digest,
    build_report_provenance_digest,
    build_saved_report_artifact_cache_candidate,
    build_thread_report_cache_candidate,
    classify_blocked_reuse_reasons,
    classify_invalidation_reasons,
    read_cache_readiness_record,
    summarize_cache_readiness_record,
    write_cache_readiness_record,
)
from core.document_review import build_document_review_context
from core.project_sources import add_project_source_from_document_review, create_project, list_project_sources
from core.thread_reports import (
    THREAD_REPORT_GENERATOR,
    THREAD_REPORT_SCHEMA_VERSION,
    THREAD_REPORT_SYSTEM_PROMPT,
    build_report_input_packet,
    generate_and_save_thread_report,
    list_thread_reports,
)

ROOT = Path(__file__).resolve().parents[1]
CACHE_READINESS_PATH = ROOT / "core" / "cache_readiness.py"
STATIC_GUARD_PATHS = [CACHE_READINESS_PATH]
FORBIDDEN_IMPORTS = {
    "core.llm",
    "core.pipeline",
    "core.pipeline_orchestrator",
    "core.prompts",
    "core.retrieval",
    "core.search",
    "core.search_providers",
    "core.providers",
    "core.models",
    "core.cache",
    "core.storage",
    "core.db",
    "sqlite3",
    "requests",
    "httpx",
    "urllib.request",
}
FORBIDDEN_CALL_NAMES = {
    "ask_model",
    "compute_similarities",
    "embed_texts",
    "fetch_linkup_precision_block",
    "filter_top_evidence",
    "process_search_queries",
    "run_economist_step",
    "run_pipeline",
    "run_scout",
    "save_session",
    "configure_storage",
}
RAW_SENTINELS = {
    "NEVER_WRITE_RAW_PRIVATE_DOCUMENT_TEXT",
    "NEVER_WRITE_FULL_PROMPT_TEXT",
    "NEVER_WRITE_PROVIDER_PAYLOAD",
    "NEVER_WRITE_FULL_TRACE",
    "NEVER_WRITE_SECRET_VALUE",
    "NEVER_WRITE_REPORT_BODY",
}


def _clock() -> datetime:
    return datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)


def _ids():
    values = iter(("proj_ag82b", "src_ag82b", "rev_ag82b", "psrc_ag82b", "rpt_ag82b"))

    def factory(prefix: str) -> str:
        return next(values)

    return factory


def _context():
    return build_document_review_context(
        """
# AG-82B memo

Document parsing is local-only and contains NEVER_WRITE_RAW_PRIVATE_DOCUMENT_TEXT.
Chunking creates anchors without enabling cache reuse.
""",
        title="AG-82B memo",
        created_at=_clock(),
    )


def _session() -> dict[str, object]:
    return {
        "id": "sess_ag82b",
        "run_id": "run_ag82b",
        "title": "Cache readiness",
        "query": "Summarize readiness",
        "timestamp": "2026-06-05T11:00:00+00:00",
        "report": "Final answer should not be stored in cache readiness records.",
        "chat_messages": [
            {"role": "user", "content": "NEVER_WRITE_FULL_PROMPT_TEXT"},
            {"role": "assistant", "content": "Observer-only instrumentation."},
        ],
        "top_passages": [
            {
                "source_id": 1,
                "title": "Local evidence",
                "domain": "example.test",
                "url": "https://example.test/local",
                "text": "NEVER_WRITE_PROVIDER_PAYLOAD",
            }
        ],
        "runtime_trace": "NEVER_WRITE_FULL_TRACE",
        "secret": "NEVER_WRITE_SECRET_VALUE",
    }


def test_document_review_parse_and_chunk_candidate_keys_use_stable_redacted_fields() -> None:
    context = _context()

    parse_candidate = build_document_parse_cache_candidate(context)
    chunk_candidate = build_document_chunk_cache_candidate(context)
    parse_fields = dict(parse_candidate.fields)
    chunk_fields = dict(chunk_candidate.fields)

    assert parse_candidate.surface == "document-parse"
    assert parse_candidate.schema_version == CACHE_READINESS_SCHEMA_VERSION
    assert parse_candidate.privacy_scope == "session-private-document"
    assert parse_fields["document_hash"] == context.metadata.document_hash
    assert parse_fields["input_format"] == context.metadata.input_format
    assert parse_fields["parser_name"] == context.metadata.parser_name
    assert parse_fields["parser_version"] == context.metadata.parser_version
    assert parse_fields["parser_confidence"] == f"{context.metadata.parser_confidence:.4f}"
    assert parse_fields["schema_version"] == CACHE_READINESS_SCHEMA_VERSION
    assert parse_candidate.safe_for_future_consideration is True

    assert chunk_candidate.surface == "document-chunk"
    assert chunk_fields["document_hash"] == context.metadata.document_hash
    assert chunk_fields["input_format"] == context.metadata.input_format
    assert chunk_fields["parser_name"] == context.metadata.parser_name
    assert chunk_fields["parser_version"] == context.metadata.parser_version
    assert chunk_fields["parser_confidence"] == f"{context.metadata.parser_confidence:.4f}"
    assert chunk_fields["anchor_count"] == str(len(context.anchors))
    assert chunk_fields["chunk_count"] == str(len(context.chunks))
    assert "NEVER_WRITE_RAW_PRIVATE_DOCUMENT_TEXT" not in str(chunk_candidate.to_dict())


def test_project_source_and_future_index_candidate_keys_use_manifest_ids(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("AG82B", storage_root=tmp_path, clock=_clock, id_factory=ids)
    context = _context()
    promoted = add_project_source_from_document_review(
        project,
        context,
        storage_root=tmp_path,
        clock=_clock,
        id_factory=ids,
    )

    source_candidate = build_project_source_cache_candidate(promoted.project_source)
    revision_candidate = build_project_source_cache_candidate(promoted.source_revision)
    future_candidate = build_future_project_source_index_cache_candidate(promoted.project_source)
    fields = dict(source_candidate.fields)

    assert source_candidate.surface == "project-source-manifest"
    assert fields["source_record_id"] == "src_ag82b"
    assert fields["source_revision_id"] == "rev_ag82b"
    assert fields["project_source_id"] == "psrc_ag82b"
    assert fields["project_id"] == "proj_ag82b"
    assert fields["document_hash"] == context.metadata.document_hash
    assert fields["parser_name"] == context.metadata.parser_name
    assert fields["parser_version"] == context.metadata.parser_version
    assert fields["privacy_class"] == "local-private"
    assert revision_candidate.safe_for_future_consideration is True
    assert future_candidate.surface == "future-project-source-indexing-retrieval"
    assert dict(future_candidate.fields)["indexer_version"] == "future-indexer-unimplemented-ag82b"
    assert dict(future_candidate.fields)["retrieval_profile"] == "future-project-source-retrieval-unimplemented-ag82b"


def test_thread_report_generation_and_saved_artifact_candidate_keys_use_digests(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("Reports", storage_root=tmp_path, clock=_clock, id_factory=ids)
    context = _context()
    promoted = add_project_source_from_document_review(
        project,
        context,
        storage_root=tmp_path,
        clock=_clock,
        id_factory=ids,
    )
    packet = build_report_input_packet(_session(), promoted.project, storage_root=tmp_path)

    def fake_model(prompt: str, system_prompt: str) -> str:
        assert "NEVER_WRITE_FULL_PROMPT_TEXT" in prompt
        assert system_prompt == THREAD_REPORT_SYSTEM_PROMPT
        return "# NEVER_WRITE_REPORT_BODY\n\nGenerated Project artifact; not primary evidence."

    result = generate_and_save_thread_report(
        _session(),
        promoted.project,
        fake_model,
        storage_root=tmp_path,
        clock=_clock,
        id_factory=ids,
    )
    report_candidate = build_thread_report_cache_candidate(packet, artifact=result.artifact)
    artifact_candidate = build_saved_report_artifact_cache_candidate(result.artifact, packet=packet)
    fields = dict(report_candidate.fields)

    assert report_candidate.surface == "thread-report-generation"
    assert fields["project_id"] == "proj_ag82b"
    assert fields["report_type"] == "thread_report"
    assert fields["model_identity"] == "model-identity-placeholder-ag82b-no-selection-change"
    assert fields["report_generator"] == THREAD_REPORT_GENERATOR
    assert fields["packet_schema_version"] == THREAD_REPORT_SCHEMA_VERSION
    assert fields["packet_digest"] == build_report_packet_digest(packet)
    assert fields["provenance_digest"] == build_report_provenance_digest(packet)
    assert artifact_candidate.surface == "saved-report-artifact-storage"
    combined = json.dumps(
        {"report": report_candidate.to_dict(), "artifact": artifact_candidate.to_dict()}, sort_keys=True
    )
    for sentinel in RAW_SENTINELS:
        assert sentinel not in combined


def test_invalidation_and_blocked_reuse_classification_labels() -> None:
    assert classify_invalidation_reasons(
        document_hash_changed=True,
        parser_version_changed=True,
        source_revision_changed=True,
        privacy_scope_changed=True,
        report_packet_or_provenance_digest_changed=True,
    ) == (
        "document-hash-changed",
        "parser-version-changed",
        "source-revision-changed",
        "privacy-scope-changed",
        "report-packet-or-provenance-digest-changed",
    )
    assert classify_blocked_reuse_reasons(
        reuse_disabled_ag82b=True,
        private_scope_not_licensed_for_reuse=True,
        missing_stable_key=True,
        freshness_or_validation_required=True,
        raw_private_text_not_cacheable=True,
    ) == (
        "reuse-disabled-ag82b",
        "private-scope-not-licensed-for-reuse",
        "missing-stable-key",
        "freshness-or-validation-required",
        "raw-private-text-not-cacheable",
    )
    assert AG82B_REUSE_DISABLED_REASON == "reuse-disabled-ag82b"


def test_redacted_write_read_and_summary_exclude_raw_text_prompts_payloads_traces_and_secrets(tmp_path: Path) -> None:
    context = _context()
    candidate = build_document_chunk_cache_candidate(context)
    record = build_cache_readiness_record(
        candidate,
        blocked_reuse_reasons=classify_blocked_reuse_reasons(
            private_scope_not_licensed_for_reuse=True,
            raw_private_text_not_cacheable=True,
        ),
        cost_latency_class="medium-cost-medium-latency",
        would_save="repeated local parsing/chunking work if future reuse is licensed",
        notes=("Redacted observer-only local readiness record.",),
        observed_at=_clock(),
        record_id="cr_ag82b_test",
    )

    path = write_cache_readiness_record(record, output_root=tmp_path / "cache_readiness")
    payload = read_cache_readiness_record(path)
    serialized = path.read_text(encoding="utf-8")
    summary = summarize_cache_readiness_record(payload)

    assert payload["schema_version"] == CACHE_READINESS_SCHEMA_VERSION
    assert payload["generator"] == CACHE_READINESS_GENERATOR
    assert payload["redaction_marker"] == REDACTION_MARKER
    assert payload["runtime_reuse_posture"] == NO_RUNTIME_REUSE_POSTURE
    assert summary["surface"] == "document-chunk"
    assert summary["runtime_reuse_posture"] == NO_RUNTIME_REUSE_POSTURE
    for sentinel in RAW_SENTINELS:
        assert sentinel not in serialized
    assert "normalized_text" not in serialized
    assert '"prompt"' not in serialized
    assert '"provider_payload"' not in serialized
    assert '"full_trace"' not in serialized
    assert '"body"' not in serialized
    assert '"secret"' not in serialized


def test_candidate_records_are_observer_only_for_document_project_source_and_report_outputs(tmp_path: Path) -> None:
    ids = _ids()
    context = _context()
    parse_candidate = build_document_parse_cache_candidate(context)
    chunk_candidate = build_document_chunk_cache_candidate(context)
    assert context.normalized_text.endswith("enabling cache reuse.")
    assert parse_candidate.key_digest != chunk_candidate.key_digest

    project = create_project("Observer", storage_root=tmp_path, clock=_clock, id_factory=ids)
    before_ids = project.project_source_ids
    promoted = add_project_source_from_document_review(
        project, context, storage_root=tmp_path, clock=_clock, id_factory=ids
    )
    source_candidate = build_project_source_cache_candidate(promoted.project_source)
    assert before_ids == ()
    assert promoted.project.project_source_ids == ("psrc_ag82b",)
    assert list_project_sources(promoted.project, storage_root=tmp_path) == (promoted.project_source,)
    assert source_candidate.key_digest

    packet = build_report_input_packet(_session(), promoted.project, storage_root=tmp_path)
    calls: list[str] = []

    def fake_model(prompt: str, system_prompt: str) -> str:
        calls.append(prompt)
        return "# Observer report\n\nGenerated Project artifact; not primary evidence."

    result = generate_and_save_thread_report(
        _session(),
        promoted.project,
        fake_model,
        storage_root=tmp_path,
        clock=_clock,
        id_factory=ids,
    )
    report_candidate = build_thread_report_cache_candidate(packet, artifact=result.artifact)
    record = build_cache_readiness_record(report_candidate, record_id="cr_observer", observed_at=_clock())
    assert len(calls) == 1
    assert result.artifact.report_id == "rpt_ag82b"
    assert "# Observer report" in result.body
    assert list_thread_reports(promoted.project, storage_root=tmp_path) == (result.artifact,)
    assert "reuse-disabled-ag82b" in record.blocked_reuse_reasons


def test_static_guard_no_provider_search_retrieval_or_prompt_imports_or_calls_added() -> None:
    for path in STATIC_GUARD_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: set[str] = set()
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        assert not (imports & FORBIDDEN_IMPORTS), f"{path} imports forbidden modules: {imports & FORBIDDEN_IMPORTS}"
        assert not (calls & FORBIDDEN_CALL_NAMES), f"{path} calls forbidden functions: {calls & FORBIDDEN_CALL_NAMES}"
