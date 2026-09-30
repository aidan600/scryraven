"""Tracked role configuration and ordinary entrypoints, with transport offline."""

import json
from dataclasses import asdict

import pytest
from test_model_transport import Response
from test_reading_room import submit
from test_research_loop import answer, decision

from scryraven import __main__ as cli
from scryraven import model as model_module
from scryraven.model import ModelConfig, ModelRole, OpenAIModel, default_model_config
from scryraven.reading_room import create_app
from scryraven.research import run
from scryraven.session import ResearchSession


@pytest.fixture
def role_file(monkeypatch, tmp_path):
    monkeypatch.setattr(model_module, "__file__", str(tmp_path / "model.py"))
    return tmp_path / "model_roles.json"


def configured_roles():
    return {
        "research": {"model": "configured-research", "reasoning": "", "service_tier": None},
        "answer": {"model": "configured-answer", "reasoning": "low", "service_tier": "default"},
    }


@pytest.mark.parametrize("data", [None, [], {}, {"research": {}}, {"answer": {}},
                                 configured_roles() | {"extra": {}}])
def test_loader_requires_exactly_the_two_roles(role_file, data):
    role_file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$"):
        default_model_config()


@pytest.mark.parametrize("name", ["research", "answer"])
@pytest.mark.parametrize("field,value", [
    ("model", ""), ("model", "  "), ("model", None), ("model", 42),
    ("reasoning", None), ("reasoning", []), ("reasoning", True),
    ("service_tier", "priority"), ("service_tier", "unknown"),
    ("service_tier", []), ("service_tier", True), ("unknown", "discarded"),
])
def test_loader_rejects_invalid_or_unknown_role_fields(role_file, name, field, value):
    data = configured_roles()
    data[name][field] = value
    role_file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$"):
        default_model_config()


@pytest.mark.parametrize("name", ["research", "answer"])
@pytest.mark.parametrize("field", ["model", "reasoning", "service_tier"])
def test_loader_rejects_missing_role_fields(role_file, name, field):
    data = configured_roles()
    del data[name][field]
    role_file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$"):
        default_model_config()


@pytest.mark.parametrize("value", [None, [], "model"])
def test_loader_rejects_nonobject_role(role_file, value):
    data = configured_roles()
    data["answer"] = value
    role_file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$"):
        default_model_config()


@pytest.mark.parametrize("raw", [b"{", b"\xff"])
def test_loader_rejects_invalid_encoding_and_json(role_file, raw):
    role_file.write_bytes(raw)
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$"):
        default_model_config()


@pytest.mark.parametrize("key", ["research", "model"])
def test_loader_rejects_duplicate_keys_in_otherwise_valid_configuration(role_file, key):
    raw = json.dumps(configured_roles()).replace(f'"{key}":', f'"{key}": "discarded", "{key}":', 1)
    role_file.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$"):
        default_model_config()


def test_missing_configuration_fails_before_transport(role_file):
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$"):
        OpenAIModel()


def test_unreadable_configuration_has_a_fixed_safe_failure(role_file, monkeypatch):
    def unreadable(*args, **kwargs):
        raise PermissionError("private filesystem detail")

    monkeypatch.setattr(model_module.Path, "read_text", unreadable)
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$") as failure:
        default_model_config()
    assert failure.value.__suppress_context__


def test_explicit_configuration_bypasses_missing_defaults(role_file):
    config = ModelConfig(ModelRole("frozen-research", "high"), ModelRole("frozen-answer", "medium"))
    assert OpenAIModel(config).config is config


def test_model_config_supports_partial_injection_from_tracked_defaults(role_file):
    data = configured_roles()
    role_file.write_text(json.dumps(data), encoding="utf-8")
    frozen = ModelRole("frozen", "medium", "fast")
    assert ModelConfig(answer=frozen) == ModelConfig(ModelRole(**data["research"]), frozen)
    assert ModelConfig(research=frozen) == ModelConfig(frozen, ModelRole(**data["answer"]))


@pytest.mark.parametrize("surface", ["run", "session", "cli", "reading_room"])
@pytest.mark.parametrize("alternate_config", [False, True])
def test_ordinary_surfaces_resolve_the_same_tracked_roles(
    monkeypatch, tmp_path, capsys, surface, alternate_config,
):
    expected = asdict(default_model_config())
    if alternate_config:
        expected = configured_roles()
        monkeypatch.setattr(model_module, "__file__", str(tmp_path / "model.py"))
        (tmp_path / "model_roles.json").write_text(json.dumps(expected), encoding="utf-8")
    assert asdict(ModelConfig()) == expected
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls = []
    text = "No source establishes this conclusion."
    outputs = iter([decision("answer"), answer(text, "unable")])

    def post(url, **kwargs):
        assert url == "https://api.openai.com/v1/responses"
        calls.append(kwargs["json"])
        return Response({"status": "completed", "output": [{
            "type": "message", "content": [{"type": "output_text", "text": json.dumps(next(outputs))}],
        }]})

    monkeypatch.setattr(model_module.requests, "post", post)
    if surface == "run":
        assert run("What follows?").answer == text
    elif surface == "session":
        assert ResearchSession().ask("What follows?").answer == text
    elif surface == "cli":
        assert cli.main(["What follows?"]) == 0
        assert text in capsys.readouterr().out
    else:
        client = create_app(database=tmp_path / "sessions.sqlite3").test_client()
        response = submit(client, question="What follows?")
        assert response.status_code == 303
        assert text in client.get(response.headers["Location"]).get_data(as_text=True)
    assert [call["text"]["format"]["name"] for call in calls] == ["research", "answer"]
    for stage, call in zip(("research", "answer"), calls):
        role = expected[stage]
        assert call["model"] == role["model"]
        assert call.get("reasoning") == ({"effort": role["reasoning"]} if role["reasoning"] else None)
        assert call.get("service_tier") == role["service_tier"]
