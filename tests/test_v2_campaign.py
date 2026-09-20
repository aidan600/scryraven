"""Offline coverage of campaign invocation and the public diagnostic boundary."""

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from scripts import v2_campaign as campaign
from scryraven.model import ModelConfig, ModelRole, ModelUsage
from scryraven.research import RunError
from scryraven.session_store import SessionStoreError
from scryraven.sources import Evidence


@dataclass
class Limits:
    semantic_attempts: int
    external_attempts: int
    seconds: float
    attention_characters: int


def runtime(*, failure=None, saved_question=None):
    observed = SimpleNamespace(sessions=[], questions=[], models=[], stores=[])
    evidence = Evidence("E1", "https://example.test/standard", "Synthetic standard", "A retained exact fact.")
    result = SimpleNamespace(
        answer="A fact.", posture="supported", stop_reason="answered", evidence=(evidence,),
        selected_evidence=(evidence,), citations=(), citation_uses=(), trace=[{"action": "completed"}],
    )

    class Model:
        def __init__(self, config, *, usage_observer):
            observed.models.append(config)
            self.usage_observer = usage_observer

    def engine(question, *, observe, model, limits, **kwargs):
        observed.questions.append(question)
        observe({"action": "exposure", "evidence": [evidence.material()]})
        model.usage_observer(ModelUsage(
            "research", "research", "must-not-be-exported", "gpt-5.6-luna", (),
            100, 20, 10, 30, 5,
        ))
        if failure:
            raise failure
        return result

    class Session:
        def __init__(self, **options):
            self.options = options
            self.session_id = None
            self.turns = []
            self.acquisitions = ()
            observed.sessions.append(self)

        @classmethod
        def create(cls, *, store, **options):
            instance = cls(**options)
            instance.session_id = f"session-{len(observed.sessions)}"
            return instance

        @classmethod
        def open(cls, session_id, *, store, **options):
            instance = cls(**options)
            instance.session_id = session_id
            instance.turns = [SimpleNamespace(question=saved_question)]
            instance.acquisitions = (evidence,)
            return instance

        def ask(self, question):
            reply = engine(question, **self.options)
            self.turns.append(SimpleNamespace(question=question))
            self.acquisitions = reply.evidence
            return reply

    def store(path):
        observed.stores.append(path)
        return object()

    bindings = SimpleNamespace(
        engine=engine, limits=Limits, model=Model, config=ModelConfig, role=ModelRole,
        session=Session, store=store, run_error=RunError, store_error=SessionStoreError,
    )
    return bindings, observed


def output(capsys):
    import json

    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def test_retained_sequence_uses_one_session_and_only_questions_enter_runtime(monkeypatch, capsys):
    bindings, observed = runtime()
    monkeypatch.setattr(campaign, "_runtime", lambda: bindings)
    assert campaign.main(["--case", "F01", "--case", "F02", "--revision", "abc1234"]) == 0
    manifest, digest = campaign.load_manifest()
    assert observed.questions == [item["question"] for item in manifest["cases"][:2]]
    assert len(observed.sessions) == 1
    assert observed.models == [ModelConfig()]
    rows = output(capsys)
    assert rows[0]["manifest_sha256"] == digest
    assert rows[0]["configuration"]["limits"] == {
        "semantic_attempts": 12, "external_attempts": 16, "seconds": 120,
        "attention_characters": 128000,
    }
    starts = [row for row in rows if row["kind"] == "submission_started"]
    assert starts[0]["entering_acquisitions"] == []
    assert starts[1]["entering_acquisitions"][0]["content"] == "A retained exact fact."
    observations = [row for row in rows if row["kind"] == "observation"]
    assert [row["case_id"] for row in observations] == ["F01", "F02"]
    assert all("rubric" not in row for row in observations)
    completed = [row for row in rows if row["kind"] == "submission_completed"]
    assert [row["counters"]["semantic_attempts_observed"] for row in completed] == [1, 1]
    assert "cache_family" not in completed[0]["usage"][0]
    assert rows[-1] == {"kind": "campaign_completed", "submissions_started": 2}


def test_independent_cases_have_fresh_sessions(monkeypatch, capsys):
    bindings, observed = runtime()
    monkeypatch.setattr(campaign, "_runtime", lambda: bindings)
    assert campaign.main(["--case", "F03", "--case", "F04", "--revision", "abc1234"]) == 0
    assert len(observed.sessions) == 2
    assert all(row["entering_acquisitions"] == []
               for row in output(capsys) if row["kind"] == "submission_started")


def test_external_manifest_drives_ordinary_session_questions(monkeypatch, tmp_path, capsys):
    bindings, observed = runtime()
    manifest_path = tmp_path / "frozen.md"
    manifest_path.write_text(campaign.MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(campaign, "_runtime", lambda: bindings)
    assert campaign.main([
        "--case", "F03", "--revision", "abc1234", "--manifest", str(manifest_path),
    ]) == 0
    manifest, digest = campaign.load_manifest(manifest_path)
    assert observed.questions == [manifest["cases"][2]["question"]]
    assert output(capsys)[0]["manifest_sha256"] == digest


@pytest.mark.parametrize("extra", [
    ["--semantic-attempts", "21"], ["--external-attempts", "25"], ["--seconds", "301"],
    ["--seconds", "nan"], ["--seconds", "0"], ["--database", "relative.sqlite3"],
])
def test_invalid_envelope_rejected_before_runtime(monkeypatch, extra):
    def forbidden():
        pytest.fail("Invalid arguments must not initialize the runtime.")

    monkeypatch.setattr(campaign, "_runtime", forbidden)
    with pytest.raises(SystemExit, match="2"):
        campaign.main(["--case", "F01", "--revision", "abc1234", *extra])


def test_followup_requires_actual_seed_session():
    with pytest.raises(SystemExit, match="2"):
        campaign.main(["--case", "F02", "--revision", "abc1234"])


def test_failed_submission_stops_and_preserves_observed_material(monkeypatch, capsys):
    failure = RunError("research", "model_transport_failed", [{"action": "model_attempt"}])
    bindings, observed = runtime(failure=failure)
    monkeypatch.setattr(campaign, "_runtime", lambda: bindings)
    assert campaign.main(["--case", "F01", "--case", "F02", "--revision", "abc1234"]) == 1
    assert len(observed.questions) == 1
    rows = output(capsys)
    assert any(row["kind"] == "observation" and row["event"]["evidence"] for row in rows)
    assert rows[-1]["kind"] == "submission_failed"
    assert rows[-1]["submissions_started"] == 1
    assert rows[-1]["trace"] == list(failure.trace)


def test_unexpected_exception_does_not_publish_exception_text(monkeypatch, capsys):
    bindings, _ = runtime(failure=RuntimeError("private diagnostic must stay private"))
    monkeypatch.setattr(campaign, "_runtime", lambda: bindings)
    assert campaign.main(["--case", "F01", "--revision", "abc1234"]) == 1
    captured = capsys.readouterr()
    assert "unexpected_runtime_failure" in captured.out
    assert "private diagnostic" not in captured.out + captured.err


def test_resume_requires_exact_previous_seed_question(monkeypatch, tmp_path, capsys):
    bindings, observed = runtime(saved_question="An unrelated earlier question.")
    monkeypatch.setattr(campaign, "_runtime", lambda: bindings)
    # Test database placement against a separate synthetic repository root.
    monkeypatch.setattr(campaign, "REPOSITORY", tmp_path / "checkout")
    assert campaign.main([
        "--case", "F02", "--revision", "abc1234", "--database", str(tmp_path / "session.sqlite3"),
        "--resume", "saved-session",
    ]) == 1
    assert observed.questions == []
    assert output(capsys)[-1] == {
        "kind": "campaign_failure", "code": "resume_requires_frozen_seed", "submissions_started": 0,
    }


def test_usage_missing_counters_remain_unknown():
    rows = [{name: None for name in campaign.TOKEN_FIELDS}]
    assert campaign._usage_summary(rows) == {
        "semantic_attempts_observed": 1, **{name: None for name in campaign.TOKEN_FIELDS},
    }
