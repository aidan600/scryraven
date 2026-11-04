"""Signed users overlap through HTTP, per-job API models and durable sessions.

Only the provider wire reply is synthetic. Admission, model cloning, the ordinary
Research/Answer loop, physical request accounting and persistence remain real.
"""

import json
from collections import Counter
from copy import deepcopy
from threading import Event, Lock

import pytest
import test_hosted_identity as identity
from test_hosted_identity import token, validator
from test_reading_room import Form
from test_research_loop import answer, decision
from test_run_settings_integration import response

from scryraven.model import OpenAIModel
from scryraven.reading_room import create_app
from scryraven.session_store import SQLiteSessionStore

config = identity.config
key = identity.key

_QUESTIONS = {
    "ALICE_A": "ALICE_A: Given ten apples and two removed, how many remain?",
    "ALICE_B": "ALICE_B: Given twenty apples and three removed, how many remain?",
    "BOB_C": "BOB_C: Given thirty apples and four removed, how many remain?",
    "ALICE_D": "ALICE_D: Given forty apples and five removed, how many remain?",
    "ALICE_E": "ALICE_E: Given fifty apples and six removed, how many remain?",
}
_ANSWERS = {"ALICE_A": "Eight apples remain.", "ALICE_B": "Seventeen apples remain.",
            "BOB_C": "Twenty-six apples remain.", "ALICE_D": "Thirty-five apples remain.",
            "ALICE_E": "Forty-four apples remain."}


def _packet(payload):
    message = next(item for item in payload["input"] if item.get("role") == "user")
    return json.loads("".join(item["text"] for item in message["content"] if item["type"] == "input_text"))


@pytest.mark.parametrize("same_owner", [True, False])
def test_four_hosted_workers_have_independent_models_and_fifth_queues(
    config, key, monkeypatch, same_owner,
):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-concurrency-api-key")
    started = {name: Event() for name in _QUESTIONS}
    release = Event()
    lock = Lock()
    factories, clones, dispatches, authorized = [], [], [], []
    original_clone = OpenAIModel.with_config

    def clone(self, selected, *, backend=None):
        result = original_clone(self, selected, backend=backend)
        with lock:
            clones.append((self, result, selected, backend))
        return result

    monkeypatch.setattr(OpenAIModel, "with_config", clone)

    def no_acquisition(*_args, **_kwargs):
        pytest.fail("Synthetic premise research attempted external acquisition")

    def factory(settings):
        with lock:
            factory_id = len(factories)

        def authorize():
            with lock:
                authorized.append(factory_id)

        def post(url, **kwargs):
            payload = deepcopy(kwargs["json"])
            packet = _packet(payload)
            name, = [name for name, question in _QUESTIONS.items() if packet["question"] == question]
            stage = payload["text"]["format"]["name"]
            assert url == "https://api.openai.com/v1/responses"
            assert kwargs["headers"]["Authorization"] == "Bearer synthetic-concurrency-api-key"
            assert not packet.get("conversation_context")
            assert all(other_question not in json.dumps(packet)
                       for other_name, other_question in _QUESTIONS.items() if other_name != name)
            with lock:
                dispatches.append((factory_id, name, stage, payload))
            if stage == "research":
                started[name].set()
                assert release.wait(10), "Synthetic provider barrier was not released"
                output = decision("return", briefing=f"Use only the explicit {name} premises.")
            else:
                assert stage == "answer"
                output = answer(_ANSWERS[name], support_basis="user_premises")
            return response(payload, output)

        model = OpenAIModel(settings.model_config(), backend="api", post=post,
                            request_authorizer=authorize)
        with lock:
            factories.append(model)
        return model

    store = SQLiteSessionStore(config.database)
    app = create_app(store=store, hosted=config, identity_validator=validator(config, key),
                     run_model_factory=factory,
                     session_options={"model": OpenAIModel(config.run_settings.model_config(), backend="api"),
                                      "search": no_acquisition, "fetch": no_acquisition,
                                      "lexical_search": no_acquisition})
    manager = app.extensions["research_jobs"]
    alice, bob = app.test_client(), app.test_client()
    alice_headers = {"Cf-Access-Jwt-Assertion": token(config, key, email="alice@example.test")}
    bob_headers = {"Cf-Access-Jwt-Assertion": token(config, key, email="bob@example.test")}

    def get(client, headers, path="/"):
        return client.get(path, base_url=config.origin, headers=headers)

    def submit(client, headers, name):
        fields = Form(get(client, headers).text, "/ask").fields
        fields["question"] = _QUESTIONS[name]
        accepted = client.post("/ask", base_url=config.origin,
                               headers={**headers, "Origin": config.origin}, data=fields)
        assert accepted.status_code == 303
        return accepted

    try:
        accepted_a = submit(alice, alice_headers, "ALICE_A")
        assert started["ALICE_A"].wait(5)
        accepted_b = submit(alice, alice_headers, "ALICE_B")
        accepted_c = submit(alice if same_owner else bob, alice_headers if same_owner else bob_headers, "BOB_C")
        submit(alice, alice_headers, "ALICE_D")
        assert started["ALICE_D"].wait(5)
        submit(alice, alice_headers, "ALICE_E")
        assert started["BOB_C"].wait(5)
        assert started["ALICE_B"].wait(5)
        assert not started["ALICE_E"].is_set()

        by_question = {item.question: item for item in store.list_jobs()}
        first, waiting, second = (by_question[_QUESTIONS[name]] for name in ("ALICE_A", "ALICE_E", "BOB_C"))
        assert first.state == second.state == "researching" and waiting.state == "queued"
        assert len({first.session_id, waiting.session_id, second.session_id}) == 3
        assert len({first.job_id, waiting.job_id, second.job_id}) == 3
        assert all(item.run_settings == config.run_settings for item in by_question.values())
        assert len(factories) == len(clones) == 4
        assert {(name, stage) for _, name, stage, _ in dispatches} == {
            (name, "research") for name in _QUESTIONS if name != "ALICE_E"}

        alice_status = get(alice, alice_headers, "/jobs/status").get_json()["jobs"]
        bob_status = get(bob, bob_headers, "/jobs/status").get_json()["jobs"]
        alice_ids = {job.session_id for name, job in by_question.items()
                     if same_owner or name != _QUESTIONS["BOB_C"]}
        assert {item["session_id"] for item in alice_status} == alice_ids
        assert {item["session_id"] for item in bob_status} == (set() if same_owner else {second.session_id})
        assert get(alice, alice_headers, accepted_c.location).status_code == (200 if same_owner else 404)
        assert get(bob, bob_headers, accepted_a.location).status_code == 404
        assert get(bob, bob_headers, accepted_b.location).status_code == 404

        tampered = Form(get(alice, alice_headers).text, "/ask").fields
        tampered.update(question="Must not dispatch", backend="openrouter", answer_model="unauthorized-model")
        rejected = alice.post("/ask", base_url=config.origin, headers=alice_headers, data=tampered)
        assert rejected.status_code == 400
        assert len(store.list_jobs()) == 5 and len(dispatches) == 4
        assert alice.post("/settings/billing", base_url=config.origin,
                          headers=alice_headers, data={"backend": "openrouter", "authorized": "1"}).status_code == 403

        release.set()
        assert manager.wait_idle(15)
        assert started["ALICE_E"].is_set()
        assert len(factories) == len(clones) == 5
        assert len({id(item[1]) for item in clones}) == 5
        assert all(original is not copied and copied.backend == "api"
                   and selected == config.run_settings.model_config() and backend == "api"
                   for original, copied, selected, backend in clones)
        assert {id(item[0]) for item in clones} == {id(model) for model in factories}
        assert Counter(authorized) == Counter({n: 2 for n in range(5)})
        assert len(dispatches) == 10
        for factory_id in range(5):
            own_calls = [item for item in dispatches if item[0] == factory_id]
            assert len({item[1] for item in own_calls}) == 1
            assert [item[2] for item in own_calls] == ["research", "answer"]
            assert [item[3]["model"] for item in own_calls] == [config.run_settings.research_model,
                                                                  config.run_settings.answer_model]
            assert all(item[3]["service_tier"] == "default" for item in own_calls)

        reopened = SQLiteSessionStore(config.database)
        for job_record in reopened.list_jobs():
            name, = [name for name, question in _QUESTIONS.items() if job_record.question == question]
            saved = reopened.load(job_record.session_id)
            assert job_record.state == "completed" and job_record.run_settings == config.run_settings
            assert saved.metadata.owner_id == ("bob@example.test" if name == "BOB_C" and not same_owner else "alice@example.test")
            assert saved.metadata.revision == 1 and len(saved.state.turns) == 1
            assert saved.state.turns[0].question == _QUESTIONS[name]
            assert saved.state.turns[0].answer == _ANSWERS[name]
            assert saved.state.acquisitions == saved.state.turns[0].citations == ()
            receipt = job_record.run_receipt
            assert [item["role"] for item in receipt["requests"]] == ["research", "answer"]
            assert [item["model"] for item in receipt["requests"]] == [config.run_settings.research_model,
                                                                      config.run_settings.answer_model]
            assert all(item["backend"] == "openai" and item["input_tokens"] == 10
                       and item["output_tokens"] == 5 for item in receipt["requests"])
            client, headers = (bob, bob_headers) if name == "BOB_C" and not same_owner else (alice, alice_headers)
            page = get(client, headers, f"/sessions/{job_record.session_id}")
            assert page.status_code == 200 and _ANSWERS[name] in page.text
            assert all(other_answer not in page.text for other_name, other_answer in _ANSWERS.items()
                       if other_name != name)
    finally:
        release.set()
        manager.shutdown()
        assert manager.wait_idle(15)
