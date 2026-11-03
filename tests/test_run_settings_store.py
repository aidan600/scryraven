"""Job-owned inference snapshots survive preferences, concurrency and migration."""

import json
import sqlite3
from contextlib import closing
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from threading import Event, Lock

import pytest
from test_persistent_sessions import tmp_path as external_tmp_path
from test_research_jobs import engine, key, result

from scryraven.errors import RunError
from scryraven.model import ModelError
from scryraven.research_jobs import ResearchJobManager
from scryraven.run_settings import RunSettings
from scryraven.session_store import SessionStoreError, SQLiteSessionStore

tmp_path = external_tmp_path


def settings(model="gpt-6.1-sol", backend="openai"):
    return RunSettings(backend=backend, research_model=model, research_reasoning="low",
                       answer_model=model, answer_reasoning=None,
                       api_processing="standard" if backend == "openai" else None,
                       physical_request_limit=6)


def test_snapshot_and_last_used_preferences_are_independent_and_transactional(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    original = settings()
    first = store.accept_job("A", idempotency_key=key(1), run_settings=original)
    assert store.get_run_settings() == original
    changed = replace(original, research_model="custom.exact-model-v2", answer_reasoning="high")
    store.set_run_settings(changed)
    assert store.get_job(first.job_id).run_settings == original
    assert SQLiteSessionStore(store.path).get_run_settings() == changed
    with pytest.raises(FrozenInstanceError):
        first.run_settings.research_model = "changed"
    with pytest.raises(SessionStoreError, match="session_busy"):
        store.accept_job("Rejected", idempotency_key=key(2), session_id=first.session_id,
                         run_settings=original)
    assert store.get_run_settings() == changed
    assert store.accept_job("A", idempotency_key=key(1), run_settings=original).job_id == first.job_id
    assert store.get_run_settings() == changed  # A replay cannot roll preferences back.
    with pytest.raises(SessionStoreError, match="submission_conflict"):
        store.accept_job("A", idempotency_key=key(1), run_settings=changed)
    with pytest.raises(SessionStoreError, match="submission_conflict"):
        store.accept_job("Altered question", idempotency_key=key(1), run_settings=original)


def test_per_backend_profiles_preserve_exact_models_and_processing_with_legacy_fallback(tmp_path):
    store = SQLiteSessionStore(tmp_path / "profiles.sqlite3")
    assert store.get_run_settings() is None
    router = settings("anthropic/custom-version-2", "openrouter")
    # Existing schema-4 databases may contain only their single last-used value.
    with closing(sqlite3.connect(store.path)) as connection:
        connection.execute("INSERT INTO app_preferences VALUES ('run_settings',?)", (json.dumps(router.to_dict()),))
        connection.commit()
    assert store.get_run_settings_profiles() == {"openrouter": router}
    api = replace(settings("custom.exact-api-model"), api_processing="fast", physical_request_limit=40)
    job = store.accept_job("Offline profile", idempotency_key=key(1), run_settings=api)
    assert SQLiteSessionStore(store.path).get_run_settings_profiles() == {"openai": api, "openrouter": router}
    changed = replace(api, api_processing="standard")
    store.set_run_settings(changed)
    assert store.get_run_settings_profiles() == {"openai": changed, "openrouter": router}
    assert store.get_job(job.job_id).run_settings == api


def test_two_running_jobs_and_queued_snapshot_ignore_preference_changes(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    started = {name: Event() for name in "ABC"}
    release = {name: Event() for name in "ABC"}
    seen = {}
    lock = Lock()

    def options(job):
        snapshot = job.run_settings
        def run(question, **kwargs):
            with lock:
                seen[question] = snapshot
            started[question].set()
            assert release[question].wait(10)
            return result(question)
        return {"engine": run}

    manager = ResearchJobManager(store, session_options_factory=options)
    a, b, c = settings("model-a"), settings("model-b"), settings("vendor/model-c", "openrouter")
    try:
        first = manager.submit("A", idempotency_key=key(1), run_settings=a)
        second = manager.submit("B", idempotency_key=key(2), run_settings=b)
        assert started["A"].wait(5) and started["B"].wait(5)
        third = manager.submit("C", idempotency_key=key(3), run_settings=c)
        assert manager.get(third.job_id).state == "queued"
        store.set_run_settings(settings("changed-ui-model"))
        release["A"].set()
        assert started["C"].wait(5)
        assert seen == {"A": a, "B": b, "C": c}
        assert manager.get(first.job_id).run_settings == a
        assert manager.get(second.job_id).run_settings == b
        assert manager.get(third.job_id).run_settings == c
    finally:
        for event in release.values():
            event.set()
        assert manager.wait_idle(10)
        manager.shutdown()


def test_retry_reuses_original_settings_and_files_after_preferences_change(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    seen = []
    def options(job):
        seen.append(job.run_settings)
        def run(question, **kwargs):
            if len(seen) == 1:
                raise RuntimeError("controlled failure")
            return engine(question, **kwargs)
        return {"engine": run}
    manager = ResearchJobManager(store, session_options_factory=options)
    original = settings("exact-original-model")
    try:
        first = manager.submit("Question to retain", idempotency_key=key(1), run_settings=original)
        assert manager.wait_idle()
        changed = settings("new-ui-model")
        store.set_run_settings(changed)
        retried = manager.retry(first.job_id, idempotency_key=key(2))
        assert manager.wait_idle()
        assert seen == [original, original]
        assert retried.run_settings == original and manager.get(retried.job_id).state == "completed"
        assert manager.get(first.job_id).run_settings == original
        assert store.get_run_settings() == changed
        assert store.load(first.session_id).state.turns[0].question == first.question
    finally:
        manager.shutdown()


def test_version_three_migration_keeps_historical_payload_citations_and_unknown_config(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    store = SQLiteSessionStore(path)
    saved = store.create("Historical")
    payload = (Path(__file__).parent / "fixtures/historical_session_v1.json").read_text(encoding="utf-8")
    job = store.accept_job("Unknown historical runtime", idempotency_key=key(1))
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("UPDATE sessions SET payload=?,revision=1 WHERE session_id=?", (payload, saved.metadata.session_id))
        connection.execute("ALTER TABLE research_jobs DROP COLUMN run_settings")
        connection.execute("ALTER TABLE research_jobs DROP COLUMN run_receipt")
        connection.execute("DROP TABLE app_preferences")
        connection.execute("DROP INDEX sessions_owner")
        connection.execute("ALTER TABLE sessions DROP COLUMN owner_id")
        connection.execute("DROP TABLE user_submissions")
        connection.execute("PRAGMA user_version=3")
        connection.commit()
    reopened = SQLiteSessionStore(path)
    old = reopened.load(saved.metadata.session_id)
    assert old.state.turns[0].citations and old.state.turns[0].selected_evidence
    assert reopened.get_job(job.job_id).run_settings is None
    assert reopened.get_run_settings() is None
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("SELECT payload FROM sessions WHERE session_id=?", (saved.metadata.session_id,)).fetchone()[0] == payload
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SQLiteSessionStore.SCHEMA_VERSION
    manager = ResearchJobManager(reopened, session_options={"engine": engine})
    try:
        with pytest.raises(SessionStoreError, match="historical_run_settings_unknown"):
            manager.retry(job.job_id, idempotency_key=key(2))
        assert len(reopened.list_jobs()) == 1
    finally:
        manager.shutdown()


def test_usage_receipt_is_bounded_allowlisted_and_cannot_rewrite_history(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    job = store.accept_job("A", idempotency_key=key(1), run_settings=settings())
    receipt = {"requests": [{"role": "research", "backend": "openai", "model": "gpt-6.1-sol",
                              "reasoning": "low", "requested_service_tier": "default",
                              "returned_service_tier": "default", "input_tokens": 100,
                              "output_tokens": 20, "cached_input_tokens": None, "reasoning_tokens": 5}],
               "estimated_cost_usd": None, "actual_billed_usd": None}
    store.save_run_receipt(job.job_id, receipt)
    store.save_run_receipt(job.job_id, receipt)
    assert SQLiteSessionStore(store.path).get_job(job.job_id).run_receipt == receipt
    receipt["requests"][0]["input_tokens"] = 101
    with pytest.raises(SessionStoreError, match="run_receipt_conflict"):
        store.save_run_receipt(job.job_id, receipt)
    for unsafe in ({"requests": [], "api_key": "not retained"},  # pragma: allowlist secret
                   {"requests": [{"provider_payload": "not retained"}]},
                   {"requests": [{"input_tokens": -1}]},
                   {"requests": [], "estimated_cost_usd": float("nan")}):
        with pytest.raises(SessionStoreError, match="invalid_run_receipt"):
            store.save_run_receipt(job.job_id, unsafe)
    with closing(sqlite3.connect(store.path)) as connection:
        raw = connection.execute("SELECT run_receipt FROM research_jobs").fetchone()[0]
    assert json.loads(raw)["requests"][0]["input_tokens"] == 100


def test_receipts_accept_full_length_model_identifiers_without_losing_usage(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    model = "m" * 200
    job = store.accept_job("A", idempotency_key=key(1), run_settings=settings(model))
    receipt = {"requests": [{"model": model, "returned_model": "v/" + "m" * 198,
                              "provider": "p" * 80, "input_tokens": 100}], "estimated_cost_usd": None}
    store.save_run_receipt(job.job_id, receipt)
    assert SQLiteSessionStore(store.path).get_job(job.job_id).run_receipt == receipt
    for field, unsafe in (("model", "m" * 201), ("returned_model", "https://example.test/model"),
                          ("provider", "p" * 81)):
        with pytest.raises(SessionStoreError, match="invalid_run_receipt"):
            store.save_run_receipt(job.job_id, {"requests": [{field: unsafe}]})


def test_completed_state_answer_and_receipt_become_visible_in_same_transaction(tmp_path):
    receipt = {"requests": [{"role": "answer", "model": "gpt-6.1-sol", "input_tokens": 100}],
               "estimated_cost_usd": None, "actual_billed_usd": None}
    observed = []
    class ObservedStore(SQLiteSessionStore):
        def commit_job(self, job_id, session_id, revision, state, **kwargs):
            metadata = super().commit_job(job_id, session_id, revision, state, **kwargs)
            # Inspect before ResearchSession returns and before on_finished can
            # run. A browser observing completed already sees exact run usage.
            current = SQLiteSessionStore(self.path)
            observed.append((current.get_job(job_id), current.load(session_id)))
            return metadata
    store = ObservedStore(tmp_path / "sessions.sqlite3")
    manager = ResearchJobManager(store, session_options={"engine": engine},
                                 completion_receipt_factory=lambda job: receipt)
    try:
        job = manager.submit("A", idempotency_key=key(1), run_settings=settings())
        assert manager.wait_idle()
        committed, saved = observed[0]
        assert committed.state == "completed" and committed.run_receipt == receipt
        assert committed.run_settings == job.run_settings
        assert saved.metadata.revision == 1 and saved.state.turns[0].question == "A"
    finally:
        manager.shutdown()


@pytest.mark.parametrize("receipt", [{"requests": [], "raw_payload": "PRIVATE"}, None])
def test_invalid_optional_completion_receipt_never_discards_valid_answer(tmp_path, receipt):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    manager = ResearchJobManager(store, session_options={"engine": engine},
                                 completion_receipt_factory=lambda job: receipt)
    try:
        job = manager.submit("A", idempotency_key=key(1), run_settings=settings())
        assert manager.wait_idle()
        saved = store.get_job(job.job_id)
        assert saved.state == "completed" and saved.run_receipt is None
        assert store.load(job.session_id).metadata.revision == 1
        assert b"PRIVATE" not in store.path.read_bytes()
    finally:
        manager.shutdown()


@pytest.mark.parametrize("error,code", [
    (ModelError("model_configuration_missing"), "model_configuration_missing"),
    (ModelError("model_catalog_unavailable"), "model_catalog_unavailable"),
    (ModelError("model_identifier_invalid"), "model_identifier_invalid"),
    (ModelError("PRIVATE_PROVIDER_BODY"), "research_failed"),
    (RunError("research", "model_contract_incompatible", []), "model_contract_incompatible"),
    (ValueError("historical_run_settings_unknown"), "historical_run_settings_unknown"),
    (ValueError("PRIVATE_CONFIGURATION_VALUE"), "research_failed"),
])
def test_preflight_and_contract_failure_keep_safe_durable_error_and_question(tmp_path, error, code):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    snapshot = settings()
    def unavailable(job):
        raise error
    manager = ResearchJobManager(store, session_options_factory=unavailable)
    try:
        job = manager.submit("Preserve this question", idempotency_key=key(1), run_settings=snapshot)
        assert manager.wait_idle()
        reopened = SQLiteSessionStore(store.path).get_job(job.job_id)
        assert reopened.state == "failed" and reopened.error_code == code
        assert reopened.question == "Preserve this question" and reopened.run_settings == snapshot
        assert store.load(job.session_id).state.turns == ()
    finally:
        manager.shutdown()
