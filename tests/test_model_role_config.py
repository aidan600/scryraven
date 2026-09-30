"""Shipped defaults, user settings and ordinary entrypoints, all offline."""

import json
from dataclasses import asdict

import pytest
from test_model_transport import Response
from test_reading_room import submit
from test_research_loop import answer, decision

from scryraven import __main__ as cli
from scryraven import model as model_module
from scryraven.model import (
    ModelConfig,
    ModelRole,
    OpenAIModel,
    built_in_model_config,
    default_model_config,
    user_model_config_path,
)
from scryraven.reading_room import create_app
from scryraven.research import run
from scryraven.session import ResearchSession


@pytest.fixture(params=["shipped", "user"])
def role_file(monkeypatch, tmp_path, request):
    if request.param == "shipped":
        monkeypatch.setattr(model_module, "__file__", str(tmp_path / "model.py"))
        return tmp_path / "model_roles.defaults.json"
    return model_module.user_model_config_path()


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


def test_missing_shipped_configuration_fails_before_transport(monkeypatch, tmp_path):
    monkeypatch.setattr(model_module, "__file__", str(tmp_path / "model.py"))
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$"):
        OpenAIModel()


def test_unreadable_configuration_has_a_fixed_safe_failure(role_file, monkeypatch):
    role_file.write_text(json.dumps(configured_roles()), encoding="utf-8")

    def unreadable(*args, **kwargs):
        raise PermissionError("private filesystem detail")

    monkeypatch.setattr(model_module.Path, "read_text", unreadable)
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$") as failure:
        default_model_config()
    assert failure.value.__suppress_context__


def test_explicit_configuration_bypasses_user_and_shipped_reads(monkeypatch, tmp_path):
    monkeypatch.setattr(model_module, "__file__", str(tmp_path / "model.py"))
    user_file = model_module.user_model_config_path()
    user_file.write_text("malformed user file", encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("ordinary configuration read")

    monkeypatch.setattr(model_module.Path, "read_text", forbidden)
    config = ModelConfig(ModelRole("frozen-research", "high"), ModelRole("frozen-answer", "medium"))
    assert OpenAIModel(config).config is config
    assert user_file.read_bytes() == b"malformed user file"


def test_model_config_supports_partial_injection_from_effective_settings(role_file):
    data = configured_roles()
    role_file.write_text(json.dumps(data), encoding="utf-8")
    frozen = ModelRole("frozen", "medium", "fast")
    assert ModelConfig(answer=frozen) == ModelConfig(ModelRole(**data["research"]), frozen)
    assert ModelConfig(research=frozen) == ModelConfig(frozen, ModelRole(**data["answer"]))


def test_absent_user_file_uses_shipped_defaults_without_creating_settings():
    user_file = model_module.user_model_config_path()
    assert default_model_config() == ModelConfig() == built_in_model_config()
    assert not user_file.exists()


def test_user_settings_completely_override_defaults_and_builtin_loader_stays_independent():
    data = configured_roles()
    model_module.user_model_config_path().write_text(json.dumps(data), encoding="utf-8")
    assert asdict(default_model_config()) == data
    assert built_in_model_config() == ModelConfig(
        ModelRole("gpt-6-luna", "high", "fast"), ModelRole("gpt-6.1-sol", "medium", "fast"),
    )


def test_invalid_existing_user_file_fails_before_provider_io(monkeypatch):
    model_module.user_model_config_path().write_text("{", encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("provider I/O")

    monkeypatch.setattr(model_module.requests, "post", forbidden)
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$"):
        run("What follows?")


@pytest.mark.parametrize("failure", [PermissionError, NotADirectoryError])
def test_unavailable_user_file_is_not_treated_as_absent(monkeypatch, failure):
    def unavailable(*args, **kwargs):
        raise failure("private filesystem detail")

    monkeypatch.setattr(model_module.Path, "lstat", unavailable)
    with pytest.raises(ValueError, match="^invalid_model_role_configuration$"):
        default_model_config()


@pytest.mark.parametrize("injected", [None, "research", "answer"])
def test_one_construction_reads_one_coherent_snapshot(monkeypatch, injected):
    path = model_module.user_model_config_path()
    first = configured_roles()
    second = configured_roles()
    second["research"]["model"] = "amended-research"
    second["answer"]["model"] = "amended-answer"
    path.write_text(json.dumps(first), encoding="utf-8")
    read_text = model_module.Path.read_text
    reads = []

    def change_after_read(selected_path, *args, **kwargs):
        raw = read_text(selected_path, *args, **kwargs)
        reads.append(selected_path)
        path.write_text(json.dumps(second), encoding="utf-8")
        return raw

    monkeypatch.setattr(model_module.Path, "read_text", change_after_read)
    frozen = ModelRole("frozen", "medium", "fast")
    config = ModelConfig(**({injected: frozen} if injected else {}))
    expected = {name: ModelRole(**role) for name, role in first.items()}
    if injected:
        expected[injected] = frozen
    assert config == ModelConfig(**expected)
    assert reads == [path]


@pytest.mark.parametrize("platform,variable,value", [
    ("win32", "LOCALAPPDATA", "absolute"), ("win32", "LOCALAPPDATA", "relative"),
    ("win32", "LOCALAPPDATA", ""), ("win32", "LOCALAPPDATA", None),
    ("darwin", "LOCALAPPDATA", "absolute"),
    ("linux", "XDG_CONFIG_HOME", "absolute"), ("linux", "XDG_CONFIG_HOME", "relative"),
    ("linux", "XDG_CONFIG_HOME", ""), ("linux", "XDG_CONFIG_HOME", None),
])
def test_user_settings_platform_paths(monkeypatch, tmp_path, platform, variable, value):
    home = tmp_path / "home"
    configured_root = tmp_path / "configured"
    monkeypatch.setattr(model_module.sys, "platform", platform)
    monkeypatch.setattr(model_module.Path, "home", lambda: home)
    if value is None:
        monkeypatch.delenv(variable, raising=False)
    else:
        monkeypatch.setenv(variable, str(configured_root) if value == "absolute" else value)
    if platform == "win32":
        root = configured_root if value == "absolute" else home / "AppData" / "Local"
        expected = root / "ScryRaven" / "model_roles.json"
    elif platform == "darwin":
        expected = home / "Library" / "Application Support" / "ScryRaven" / "model_roles.json"
    else:
        root = configured_root if value == "absolute" else home / ".config"
        expected = root / "scryraven" / "model_roles.json"
    # Call the original helper, independently of the suite's isolation patch.
    assert user_model_config_path() == expected
    assert expected.is_absolute()


@pytest.mark.parametrize("surface", ["run", "session", "cli", "reading_room"])
@pytest.mark.parametrize("alternate_config", [False, True])
def test_ordinary_surfaces_resolve_the_same_effective_roles(
    monkeypatch, tmp_path, capsys, surface, alternate_config,
):
    expected = asdict(built_in_model_config())
    if alternate_config:
        expected = configured_roles()
        model_module.user_model_config_path().write_text(json.dumps(expected), encoding="utf-8")
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


@pytest.mark.parametrize("surface", ["run", "session", "cli", "reading_room"])
def test_user_amendment_is_used_by_the_next_ordinary_turn(monkeypatch, tmp_path, capsys, surface):
    path = model_module.user_model_config_path()
    before = configured_roles()
    after = {
        "research": {"model": "amended-research", "reasoning": "medium", "service_tier": "fast"},
        "answer": {"model": "amended-answer", "reasoning": "", "service_tier": None},
    }
    path.write_text(json.dumps(before), encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls = []
    text = "No source establishes this conclusion."
    outputs = iter([decision("answer"), answer(text, "unable")] * 2)

    def post(url, **kwargs):
        assert url == "https://api.openai.com/v1/responses"
        calls.append(kwargs["json"])
        return Response({"status": "completed", "output": [{
            "type": "message", "content": [{"type": "output_text", "text": json.dumps(next(outputs))}],
        }]})

    def amend():
        path.write_text(json.dumps(after), encoding="utf-8")

    monkeypatch.setattr(model_module.requests, "post", post)
    if surface == "run":
        assert run("First question?").answer == text
        amend()
        assert run("Next question?").answer == text
    elif surface == "session":
        session = ResearchSession()
        assert session.ask("First question?").answer == text
        amend()
        assert session.ask("Next question?").answer == text
        assert len(session.turns) == 2
    elif surface == "cli":
        questions = iter(["Next question?", ""])

        def next_question(*args):
            amend()
            return next(questions)

        monkeypatch.setattr("builtins.input", next_question)
        assert cli.main(["First question?", "--session"]) == 0
        assert capsys.readouterr().out.count(text) == 2
    else:
        client = create_app(database=tmp_path / "sessions.sqlite3").test_client()
        first = submit(client, question="First question?")
        assert first.status_code == 303
        amend()
        second = submit(client, first.headers["Location"].split("#", 1)[0], question="Next question?")
        assert second.status_code == 303
        assert client.get(second.headers["Location"]).get_data(as_text=True).count(text) == 2
    assert [call["text"]["format"]["name"] for call in calls] == ["research", "answer"] * 2
    for settings, turn_calls in ((before, calls[:2]), (after, calls[2:])):
        for stage, call in zip(("research", "answer"), turn_calls):
            role = settings[stage]
            assert call["model"] == role["model"]
            assert call.get("reasoning") == ({"effort": role["reasoning"]} if role["reasoning"] else None)
            assert call.get("service_tier") == role["service_tier"]


@pytest.mark.parametrize("field,value", [("model", "amended-answer"), ("reasoning", "high"),
                                        ("service_tier", "fast")])
def test_amended_answer_cache_and_telemetry_use_resolved_settings(monkeypatch, field, value):
    path = model_module.user_model_config_path()
    settings = configured_roles()
    path.write_text(json.dumps(settings), encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls = []

    def post(url, **kwargs):
        assert url == "https://api.openai.com/v1/responses"
        calls.append(kwargs["json"])
        stage = kwargs["json"]["text"]["format"]["name"]
        output = decision("answer") if stage == "research" else answer("No source establishes this.", "unable")
        return Response({"status": "completed", "output": [{
            "type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}],
        }]})

    monkeypatch.setattr(model_module.requests, "post", post)
    run("What follows?")
    settings["answer"][field] = value
    path.write_text(json.dumps(settings), encoding="utf-8")
    result = run("What follows?")
    assert calls[0]["prompt_cache_key"] == calls[2]["prompt_cache_key"]
    assert (calls[1]["prompt_cache_key"] == calls[3]["prompt_cache_key"]) == (field == "service_tier")
    starts = [item for item in result.trace if item["action"] == "model_started"]
    assert [(item["contract"], item["model"], item["reasoning_effort"], item["requested_service_tier"])
            for item in starts] == [
                (stage, settings[stage]["model"], settings[stage]["reasoning"], settings[stage]["service_tier"])
                for stage in ("research", "answer")
            ]


def test_explicitly_retained_model_keeps_its_resolved_snapshot():
    path = model_module.user_model_config_path()
    before = configured_roles()
    path.write_text(json.dumps(before), encoding="utf-8")
    retained = OpenAIModel()
    after = configured_roles()
    after["answer"]["model"] = "amended-answer"
    path.write_text(json.dumps(after), encoding="utf-8")
    assert asdict(retained.config) == before
    assert asdict(OpenAIModel().config) == after
