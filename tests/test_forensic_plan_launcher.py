"""Offline child launch checks; no credentials or provider requests are used."""

import json
import os
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from scripts import forensic_reading_room as child
from scryraven.model import ModelConfig, OpenAIModel


def _run(tmp_path):
    manifest = {"port": 7332, "git_sha": "stale", "model_profile": {"stale": True}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return ["--run-directory", str(tmp_path)]


def _manifest(tmp_path):
    return json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("exa", [None, "", " \t"])
def test_missing_required_search_fails_before_model_or_server(tmp_path, monkeypatch, capsys, exa):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    if exa is not None:
        monkeypatch.setenv("EXA_API_KEY", exa)
    monkeypatch.setenv("SERPER_API_KEY", "synthetic-serper-value")
    monkeypatch.setenv("LINKUP_API_KEY", "  ")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-api-value")
    monkeypatch.setattr(child, "OpenAIModel", lambda **_: pytest.fail("model constructed"))
    monkeypatch.setattr(child.reading_room, "serve", lambda *a, **k: pytest.fail("server started"))
    assert child.main(_run(tmp_path)) == 2
    result = _manifest(tmp_path)
    assert result["safe_error_code"] == "exa_configuration_missing"
    assert result["launch_status"] == "failed"
    assert result["acquisition_configuration"] == {"exa": False, "serper": True, "linkup": False}
    assert "OPENAI_API_KEY" not in os.environ
    assert not (tmp_path / "sessions.sqlite3").exists()
    assert not (tmp_path / "observer.jsonl").exists()
    assert "synthetic-" not in (tmp_path / "manifest.json").read_text(encoding="utf-8")
    assert capsys.readouterr().out == "Forensic Reading Room could not start: exa_configuration_missing\n"


def test_explicit_plan_injection_isolated_logs_real_application_and_zero_startup_inference(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("EXA_API_KEY", "synthetic-exa-value")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-api-value")
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.setenv("LINKUP_API_KEY", "synthetic-linkup-value")
    models = []

    def construct(**kwargs):
        assert kwargs == {"backend": "chatgpt_plan", "plan_account": "personal"}
        assert "OPENAI_API_KEY" not in os.environ
        # Real model/transport, synthetic Auth: constructing and GET must not
        # authenticate or send any inference request.
        auth = SimpleNamespace(access=lambda *a, **k: pytest.fail("authentication requested"))
        model = OpenAIModel(**kwargs, plan_auth=auth)
        models.append(model)
        return model

    monkeypatch.setattr(child, "OpenAIModel", construct)
    original_create = child.reading_room.create_app
    injected = []

    def create(**kwargs):
        injected.append(kwargs["session_options"]["model"])
        return original_create(**kwargs)

    def serve(app, *, port, on_ready):
        assert port == 7332
        on_ready(port)
        manifest = _manifest(tmp_path)
        assert manifest["launch_status"] == "ready"
        assert manifest["server_pid"] == os.getpid()
        assert manifest["model_profile"] == asdict(models[0].config)
        assert manifest["git_sha"] != "stale"
        assert manifest["startup_model_dispatches"] == 0
        assert manifest["api_inference_fallback"] is False
        assert manifest["inference_backend"] == "chatgpt_plan"
        assert manifest["plan_account"] == "personal"
        assert manifest["acquisition_configuration"] == {"exa": True, "serper": False, "linkup": True}
        assert app.test_client().get("/").status_code == 200
        assert models[0].plan_transport.physical_requests == 0

    monkeypatch.setattr(child.reading_room, "create_app", create)
    monkeypatch.setattr(child.reading_room, "serve", serve)
    assert child.main(_run(tmp_path)) == 0
    assert injected == models
    assert _manifest(tmp_path)["launch_status"] == "stopped"
    assert (tmp_path / "sessions.sqlite3").is_file()
    assert (tmp_path / "turns.jsonl").read_text(encoding="utf-8") == ""
    assert (tmp_path / "observer.jsonl").read_text(encoding="utf-8") == ""
    assert set(p.name for p in tmp_path.iterdir()) >= {
        "sessions.sqlite3", "turns.jsonl", "observer.jsonl", "manifest.json",
    }


@pytest.mark.parametrize("failure", ["raise", "wrong_backend"])
def test_plan_failure_is_safe_and_has_no_api_fallback(tmp_path, monkeypatch, capsys, failure):
    monkeypatch.setenv("EXA_API_KEY", "synthetic-exa-value")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-api-value")

    def construct(**kwargs):
        if failure == "raise":
            raise RuntimeError("synthetic-private-exception")
        return SimpleNamespace(backend="api", config=ModelConfig(), plan_transport=None)

    monkeypatch.setattr(child, "OpenAIModel", construct)
    monkeypatch.setattr(child.reading_room, "create_app", lambda **k: pytest.fail("app created"))
    assert child.main(_run(tmp_path)) == 2
    assert _manifest(tmp_path)["safe_error_code"] == "chatgpt_plan_backend_unavailable"
    assert "synthetic-" not in capsys.readouterr().out
    assert not (tmp_path / "sessions.sqlite3").exists()


def test_serve_notifies_after_bind_and_closes_on_callback_failure(monkeypatch):
    events = []
    server = SimpleNamespace(server_port=7442,
                             serve_forever=lambda: events.append("serve"),
                             server_close=lambda: events.append("close"))
    monkeypatch.setattr(child.reading_room, "make_server", lambda *a, **k: server)

    def ready(port):
        events.append(port)
        raise OSError("unavailable manifest")

    with pytest.raises(OSError):
        child.reading_room.serve(object(), port=7442, on_ready=ready)
    assert events == [7442, "close"]
