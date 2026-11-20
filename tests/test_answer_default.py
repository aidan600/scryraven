"""New Answer defaults and explicit selections through the ordinary app, offline."""

import json
import re
from dataclasses import replace

import pytest
import test_citation_preview_browser as citation_browser
import test_hosted_identity as identity
from reading_room_samples import no_io
from test_model_transport import Response
from test_reading_room import Form
from test_research_loop import answer, decision

from scryraven.hosted import HostedConfig
from scryraven.hosted_preferences import HOSTED_MODEL_CHOICES
from scryraven.model import ModelConfig, ModelRole, OpenAIModel, built_in_model_config
from scryraven.reading_room import create_app
from scryraven.run_settings import RunSettings
from scryraven.session_store import SQLiteSessionStore

key = identity.key


def offline_app(tmp_path, monkeypatch, *, saved=False, hosted=None, validator=None):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-offline-key")
    store = SQLiteSessionStore(hosted.database if hosted else tmp_path / "default.sqlite3")
    settings = RunSettings.effective()
    if saved:
        settings = replace(settings, answer_model="gpt-6.1-sol", answer_reasoning="high",
                           research_model="gpt-6-luna", research_reasoning="low")
        if hosted:
            store.set_hosted_preferences(settings.to_dict())
        else:
            store.set_run_settings(settings)
    store.set_billing_authorization("openai", True)
    calls = []

    def post(_url, **kwargs):
        payload = kwargs["json"]
        calls.append(payload)
        result = (decision("return") if payload["text"]["format"]["name"] == "research" else
                  answer("Eight remain.", support_basis="user_premises"))
        return Response({"status": "completed", "output": [{"type": "message", "content": [{
            "type": "output_text", "text": json.dumps(result),
        }]}]})

    app = create_app(store=store, session_options={"search": no_io, "fetch": no_io}, hosted=hosted,
                     identity_validator=validator,
                     run_model_factory=lambda selected: OpenAIModel(selected.model_config(), post=post))
    return app, store, settings, calls


@pytest.mark.parametrize("saved", [False, True])
def test_web_selection_and_effective_answer_agree_and_saved_choices_survive(tmp_path, monkeypatch, saved):
    app, store, expected, calls = offline_app(tmp_path, monkeypatch, saved=saved)
    client = app.test_client()
    fields = Form(client.get("/").text, "/ask").fields
    assert fields["answer_model"] == expected.answer_model == ("gpt-6.1-sol" if saved else "gpt-6.2-sol")
    assert fields["research_model"] == expected.research_model
    response = client.post("/ask", data=fields | {"question": "Given ten units and two removed, how many remain?"})
    assert response.status_code == 303
    assert app.extensions["research_jobs"].wait_idle(10)
    assert [call["model"] for call in calls] == [expected.research_model, expected.answer_model]
    assert [call["reasoning"]["effort"] for call in calls] == [expected.research_reasoning, expected.answer_reasoning]
    location = response.headers["Location"]
    completed = client.get(location)
    assert "Eight remain." in completed.text
    reopened = Form(completed.text, location.split("#", 1)[0] + "/ask").fields
    assert reopened["answer_model"] == expected.answer_model
    job, = store.list_jobs()
    assert job.state == "completed"
    assert job.run_settings == expected


@pytest.fixture
def browser():
    yield from citation_browser.browser.__wrapped__()


def test_browser_default_and_answer_choices_preserve_research_menu(browser, tmp_path, monkeypatch):
    app, _, _, calls = offline_app(tmp_path, monkeypatch)
    with citation_browser.running_room(app) as base:
        with citation_browser.page_at(browser, base) as page:
            page.locator(".run-settings-open").click()
            answer_model = page.get_by_label("Answer model identifier")
            assert answer_model.input_value() == "gpt-6.2-sol"
            assert page.get_by_label("Research model identifier").input_value() == "gpt-6.1-terra"
            research = page.locator("#research-suggestions option").evaluate_all("rows => rows.map(row => row.value)")
            assert research == ["", "gpt-6.1-terra", "gpt-6.1-sol", "gpt-6-luna"]
            assert page.locator("#answer-suggestions option").evaluate_all("rows => rows.map(row => row.value)") == [
                "", "gpt-6.2-sol", "gpt-6.1-terra", "gpt-6.1-sol", "gpt-6-luna",
            ]
            page.get_by_label("Answer suggested models").select_option("gpt-6.1-sol")
            assert answer_model.input_value() == "gpt-6.1-sol"
            page.get_by_label("Answer suggested models").select_option("gpt-6.2-sol")
            assert answer_model.input_value() == "gpt-6.2-sol"
            page.get_by_role("button", name="Use these settings").click()
            page.locator("#question").fill("Given ten units and two removed, how many remain?")
            page.locator(".submit-question").click()
            page.locator(".answer").get_by_text("Eight remain.").wait_for(timeout=10000)
            assert [call["model"] for call in calls] == ["gpt-6.1-terra", "gpt-6.2-sol"]


@pytest.mark.parametrize("saved_destination", [False, True])
def test_openrouter_to_openai_restores_launch_or_saved_settings(browser, tmp_path, saved_destination):
    launch_model = OpenAIModel(ModelConfig(
        ModelRole("gpt-6-luna", "high", "fast"),
        ModelRole("gpt-6.1-sol", "xhigh", "fast"),
    ), post=no_io)
    launch = RunSettings.effective(launch_model)
    store = SQLiteSessionStore(tmp_path / "switch.sqlite3")
    expected = launch
    if saved_destination:
        expected = replace(launch, research_model="gpt-6.1-terra", research_reasoning="medium",
                           answer_model="gpt-6-luna", answer_reasoning=None, api_processing="standard")
        store.set_run_settings(expected)
    store.set_run_settings(replace(
        launch, backend="openrouter", research_model="vendor/research", research_reasoning="low",
        answer_model="vendor/answer", answer_reasoning="medium", api_processing=None,
    ))
    app = create_app(store=store, session_options={"model": launch_model, "search": no_io, "fetch": no_io})

    with citation_browser.running_room(app) as base, citation_browser.page_at(browser, base) as page:
        page.locator(".run-settings-open").click()
        backend = page.get_by_label("Inference backend")
        assert backend.input_value() == "openrouter"
        backend.select_option("openai")
        assert page.get_by_label("Answer model identifier").input_value() == expected.answer_model
        assert page.get_by_label("Answer reasoning effort").input_value() == (expected.answer_reasoning or "")
        assert page.get_by_label("Research model identifier").input_value() == expected.research_model
        assert page.get_by_label("Research reasoning effort").input_value() == expected.research_reasoning
        assert page.get_by_label("OpenAI API processing").input_value() == expected.api_processing


@pytest.mark.parametrize("saved", [False, True])
def test_hosted_default_and_saved_answer_preserve_research_choices(tmp_path, monkeypatch, key, saved):
    config = HostedConfig.from_env(identity.environment(tmp_path))
    app, store, expected, calls = offline_app(tmp_path, monkeypatch, saved=saved, hosted=config,
                                             validator=identity.validator(config, key))
    client = app.test_client()
    headers = {"Cf-Access-Jwt-Assertion": identity.token(config, key, email=config.admin_email)}
    page = client.get("/", base_url=config.origin, headers=headers)
    fields = Form(page.text, "/settings/hosted").fields
    assert fields["answer_model"] == expected.answer_model
    assert fields["research_model"] == expected.research_model

    def choices(role):
        select = re.search(r'<select id="hosted-' + role + r'-model"[^>]*>(.*?)</select>', page.text, re.S)[1]
        return re.findall(r'<option value="([^"]+)"', select)

    assert choices("research") == list(HOSTED_MODEL_CHOICES)
    assert "gpt-6.2-sol" in choices("answer")
    response = client.post("/ask", base_url=config.origin, headers=headers | {"Origin": config.origin},
                           data=Form(page.text, "/ask").fields | {"question": "Given ten units and two removed, how many remain?"})
    assert response.status_code == 303
    assert app.extensions["research_jobs"].wait_idle(10)
    assert [call["model"] for call in calls] == [expected.research_model, expected.answer_model]
    assert [call["reasoning"]["effort"] for call in calls] == [expected.research_reasoning, expected.answer_reasoning]
    job, = store.list_jobs()
    assert job.state == "completed"
    assert job.run_settings == expected
    assert built_in_model_config().answer.model == "gpt-6.2-sol"

    if saved:
        update = client.post("/settings/hosted", base_url=config.origin, headers=headers | {"Origin": config.origin},
                             data=fields | {"answer_model": "gpt-6.2-sol"})
        assert update.status_code == 303
        assert RunSettings.from_dict(store.get_hosted_preferences()) == replace(expected, answer_model="gpt-6.2-sol")
