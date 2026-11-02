"""Run Settings exercise ordinary HTTP, jobs, role transports and durable answers."""

import json
from copy import deepcopy

import pytest
from reading_room_samples import no_io
from test_model_transport import Response
from test_persistent_sessions import tmp_path as external_tmp_path
from test_production_plan_transport import FrozenAuth, Reply, usage
from test_reading_room import token
from test_research_loop import answer, decision

from scryraven.model import OpenAIModel
from scryraven.reading_room import create_app
from scryraven.session_store import SQLiteSessionStore

tmp_path = external_tmp_path
QUESTION = "Given that a box holds 12 apples and four are removed, how many apples remain?"
FINAL = answer("Eight apples remain, given those premises.", support_basis="user_premises")


def selected_fields(client, backend="openai", processing="standard"):
    fields = token(client.get("/"), "/ask")
    prefix = "openai/" if backend == "openrouter" else ""
    fields.update(question=QUESTION, backend=backend, research_model=prefix + "gpt-6.1-terra",
                  research_reasoning="low", answer_model=prefix + "gpt-6.1-sol",
                  answer_reasoning="", physical_request_limit="6")
    if backend == "openai":
        fields["api_processing"] = processing
    else:
        fields.pop("api_processing", None)
    if backend != "chatgpt_plan":
        fields["paid_inference_confirmed"] = "1"
    else:
        fields.pop("paid_inference_confirmed", None)
    return fields


def response(payload, output, *, cost=None):
    body = {"status": "completed", "model": payload["model"], "usage": usage(),
            "output": output if isinstance(output, list) else [
                {"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]}]}
    if "service_tier" in payload:
        body["service_tier"] = payload["service_tier"]
    if cost is not None:
        body["provider"] = "Synthetic provider"
        body["usage"]["cost"] = cost
    return Response(body)


@pytest.mark.parametrize("backend,processing", [
    ("chatgpt_plan", None), ("openai", "standard"), ("openai", "fast"), ("openrouter", None),
])
def test_ordinary_submission_snapshots_exact_roles_and_persists_each_request_receipt(tmp_path, monkeypatch, backend, processing):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-openai-token")
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-router-token")
    monkeypatch.setattr(OpenAIModel, "plan_catalog", lambda self: (
        {"slug": "gpt-6.1-terra", "reasoning_efforts": ("low", "medium")},
        {"slug": "gpt-6.1-sol", "reasoning_efforts": ("low", "medium")},
    ))
    calls, credentials, plans = [], [], []
    outputs = iter([decision("return"), [{"type": "function_call", "name": "calculate",
        "call_id": "apples-calculation", "arguments": '{"expression":"12 - 4"}'}], FINAL])

    def post(url, **kwargs):
        calls.append((url, deepcopy(kwargs["json"])))
        credentials.append(kwargs["headers"]["Authorization"])
        return response(kwargs["json"], next(outputs), cost=.00001 if backend == "openrouter" else None)

    def factory(settings):
        auth = None
        if settings.backend == "chatgpt_plan":
            auth = FrozenAuth(Reply("research", decision("return")), Reply("answer", tool="12 - 4"),
                              Reply("answer", FINAL))
            plans.append(auth)
        return OpenAIModel(settings.model_config(), backend="api" if settings.backend == "openai" else settings.backend,
                           post=post, plan_auth=auth)

    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    app = create_app(store=store, run_model_factory=factory,
                     session_options={"search": no_io, "fetch": no_io, "lexical_search": no_io})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    try:
        fields = selected_fields(client, backend, processing)
        accepted = client.post("/ask", data=fields)
        assert accepted.status_code == 303 and manager.wait_idle(10)
        job, = store.list_jobs()
        assert job.state == "completed" and job.run_settings.backend == backend
        assert job.run_settings.research_model == fields["research_model"]
        assert job.run_settings.answer_model == fields["answer_model"]
        assert job.run_settings.research_reasoning == "low" and job.run_settings.answer_reasoning is None
        assert job.run_settings.api_processing == processing and job.run_settings.physical_request_limit == 6
        saved = SQLiteSessionStore(store.path).load(job.session_id)
        assert saved.state.turns[0].answer == FINAL["answer"]
        assert saved.state.turns[0].citations == saved.state.turns[0].selected_evidence == ()
        assert b"Eight apples remain" in client.get(accepted.location).data
        payloads = plans[0].calls if plans else [payload for _, payload in calls]
        assert len(payloads) == 3
        assert [item["model"] for item in payloads] == [fields["research_model"], fields["answer_model"], fields["answer_model"]]
        assert payloads[0]["reasoning"] == {"effort": "low"}
        assert all("reasoning" not in item for item in payloads[1:])
        assert all(item["text"]["format"]["strict"] is True for item in payloads)
        assert any(item.get("type") == "function_call_output" for item in payloads[-1]["input"])
        receipt = SQLiteSessionStore(store.path).get_job(job.job_id).run_receipt
        assert len(receipt["requests"]) == 3
        assert [row["role"] for row in receipt["requests"]] == ["research", "answer", "answer"]
        assert all(row["input_tokens"] == 10 and row["output_tokens"] == 5 for row in receipt["requests"])
        if backend == "openai":
            tier = "fast" if processing == "fast" else "default"
            assert all(item["service_tier"] == tier for item in payloads)
            assert all(url == "https://api.openai.com/v1/responses" for url, _ in calls)
            assert credentials == ["Bearer offline-openai-token"] * 3
            assert all(row["requested_service_tier"] == row["returned_service_tier"] == tier for row in receipt["requests"])
        else:
            assert all("service_tier" not in item for item in payloads)
            assert all(row["requested_service_tier"] is None for row in receipt["requests"])
        if backend == "openrouter":
            assert all(url == "https://openrouter.ai/api/v1/responses" for url, _ in calls)
            assert credentials == ["Bearer offline-router-token"] * 3
            assert all(item["provider"] == {"require_parameters": True, "allow_fallbacks": False} for item in payloads)
            assert all(row["reported_cost_usd"] == .00001 for row in receipt["requests"])
        raw = store.path.read_bytes()
        assert b"offline-openai-token" not in raw and b"offline-router-token" not in raw
        assert b"synthetic-plan-token" not in raw
        assert receipt["actual_billed_usd"] is receipt["estimated_cost_usd"] is None
    finally:
        manager.shutdown()


@pytest.mark.parametrize("backend", ["openai", "openrouter"])
def test_missing_credential_retains_question_and_selected_configuration_without_dispatch(tmp_path, monkeypatch, backend):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    app = create_app(store=store, run_model_factory=lambda settings: OpenAIModel(settings.model_config(),
        backend="api" if settings.backend == "openai" else settings.backend, post=no_io))
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    try:
        accepted = client.post("/ask", data=selected_fields(client, backend))
        assert accepted.status_code == 303 and manager.wait_idle()
        job, = store.list_jobs()
        assert job.state == "failed" and job.error_code == "model_configuration_missing"
        assert job.question == QUESTION and job.run_settings.backend == backend
        assert b"selected backend is unavailable" in client.get(accepted.location).data
        assert store.load(job.session_id).state.turns == ()
    finally:
        manager.shutdown()


@pytest.mark.parametrize("phase", ["research", "answer", "delegated_research"])
def test_openrouter_incompatible_output_spends_no_repair_and_duplicate_tampering_is_rejected(tmp_path, monkeypatch, phase):
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-router")
    outputs = iter(([decision("return")] if phase == "answer" else
                    [decision("return"), [{"type": "function_call", "name": "research",
                        "call_id": "delegated-contract", "arguments": '{"need":"Check the stipulated quantity."}'}]]
                    if phase == "delegated_research" else []) + [{"invalid": "REJECTED CONTRACT CLAIM"}])
    calls = []
    def post(url, **kwargs):
        calls.append((url, deepcopy(kwargs["json"])))
        return response(kwargs["json"], next(outputs))
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    app = create_app(store=store, run_model_factory=lambda settings: OpenAIModel(settings.model_config(),
        backend="api" if settings.backend == "openai" else settings.backend, post=post),
        session_options={"search": no_io, "fetch": no_io, "lexical_search": no_io})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    try:
        fields = selected_fields(client, "openrouter")
        accepted = client.post("/ask", data=fields)
        assert accepted.status_code == 303 and manager.wait_idle()
        job, = store.list_jobs()
        assert job.state == "failed" and job.error_code == "model_contract_incompatible"
        requests = {"research": 1, "answer": 2, "delegated_research": 3}[phase]
        assert len(calls) == requests and job.run_settings.research_model == fields["research_model"]
        assert all(url == "https://openrouter.ai/api/v1/responses" for url, _ in calls)
        assert len(job.run_receipt["requests"]) == requests
        assert store.load(job.session_id).state.turns == ()
        assert "REJECTED CONTRACT CLAIM" not in json.dumps(calls)
        assert client.post("/ask", data=fields).status_code == 303
        assert client.post("/ask", data=fields | {"answer_model": fields["answer_model"] + "-changed"}).status_code == 409
        assert client.post("/ask", data=fields | {"question": "Changed question"}).status_code == 409
        assert len(calls) == requests and len(store.list_jobs()) == 1
    finally:
        manager.shutdown()


@pytest.mark.parametrize("processing", ["standard", "fast"])
def test_openai_submission_repairs_research_and_answer_once_with_original_settings(tmp_path, monkeypatch, processing):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-openai")
    calls = []
    opaque = {"type": "reasoning", "id": "calculation-reasoning", "encrypted_content": "opaque-offline-context"}
    calculation = {"type": "function_call", "name": "calculate", "call_id": "accepted-calculation",
                   "arguments": '{"expression":"12 - 4"}'}
    outputs = iter([{"invalid": "REJECTED RESEARCH CLAIM"}, decision("return"),
                    [opaque, calculation], {"invalid": "REJECTED ANSWER CLAIM"}, FINAL])

    def post(url, **kwargs):
        calls.append((url, deepcopy(kwargs["json"])))
        return response(kwargs["json"], next(outputs))

    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    app = create_app(store=store, run_model_factory=lambda settings: OpenAIModel(
        settings.model_config(), backend="api", post=post),
        session_options={"search": no_io, "fetch": no_io, "lexical_search": no_io})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    try:
        fields = selected_fields(client, "openai", processing)
        accepted = client.post("/ask", data=fields)
        assert accepted.status_code == 303 and manager.wait_idle(10)
        job, = store.list_jobs()
        assert job.state == "completed" and job.run_settings.backend == "openai"
        assert job.run_settings.api_processing == processing and job.run_settings.physical_request_limit == 6
        assert all(url == "https://api.openai.com/v1/responses" for url, _ in calls)
        payloads = [payload for _, payload in calls]
        assert len(payloads) == 5
        assert [payload["text"]["format"]["name"] for payload in payloads] == [
            "research", "research", "answer", "answer", "answer"]
        assert [payload["model"] for payload in payloads] == [fields["research_model"]] * 2 + [fields["answer_model"]] * 3
        tier = "fast" if processing == "fast" else "default"
        assert all(payload["service_tier"] == tier for payload in payloads)
        assert all(payload["reasoning"] == {"effort": "low"} for payload in payloads[:2])
        assert all("reasoning" not in payload for payload in payloads[2:])
        assert "output_correction" in json.dumps(payloads[1])
        assert payloads[-1]["input"][:len(payloads[-2]["input"])] == payloads[-2]["input"]
        assert opaque in payloads[-1]["input"] and calculation in payloads[-1]["input"]
        assert any(item.get("type") == "function_call_output" and item.get("call_id") == "accepted-calculation"
                   for item in payloads[-1]["input"])
        assert "output_correction" in json.dumps(payloads[-1]["input"][-1])
        assert "REJECTED RESEARCH CLAIM" not in json.dumps(payloads)
        assert "REJECTED ANSWER CLAIM" not in json.dumps(payloads)
        assert len(job.run_receipt["requests"]) == 5
        saved = SQLiteSessionStore(store.path).load(job.session_id)
        assert saved.state.turns[0].answer == FINAL["answer"]
        assert saved.state.turns[0].citations == saved.state.turns[0].selected_evidence == ()
    finally:
        manager.shutdown()


def test_unsupported_plan_model_fails_preflight_with_original_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(OpenAIModel, "plan_catalog", lambda self: ())
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    app = create_app(store=store, run_model_factory=lambda settings: OpenAIModel(settings.model_config(),
        backend="chatgpt_plan", plan_auth=FrozenAuth(), post=no_io))
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    try:
        accepted = client.post("/ask", data=selected_fields(client, "chatgpt_plan"))
        assert accepted.status_code == 303 and manager.wait_idle()
        job, = store.list_jobs()
        assert job.state == "failed" and job.error_code == "model_unavailable"
        assert job.run_settings.research_model == "gpt-6.1-terra" and job.question == QUESTION
        assert store.load(job.session_id).state.turns == ()
    finally:
        manager.shutdown()
