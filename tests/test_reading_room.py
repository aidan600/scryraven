"""The ordinary HTTP -> ResearchSession -> SQLite path, with external I/O faked."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from html.parser import HTMLParser
from threading import Event

import pytest
from reading_room_samples import (
    EARLY,
    FOLLOWUP,
    LATER,
    QUESTION,
    Script,
    first_script,
    no_io,
    prepared_session,
    source_search,
)
from test_answer_presentation import Page
from test_persistent_sessions import tmp_path as external_tmp_path
from test_research_session import assess
from test_source_acquisition import use
from test_walking_skeleton import analysis, author, done, orient

from scryraven import reading_room
from scryraven.presentation import answer_html, source_body_html
from scryraven.session import ResearchSession
from scryraven.session_store import SessionConflictError, SQLiteSessionStore, default_session_path

tmp_path = external_tmp_path


class Form(HTMLParser):
    def __init__(self, html, action):
        super().__init__()
        self.action, self.active, self.fields = action, False, {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.active = attrs.get("action") == self.action
        if self.active and tag == "input" and "name" in attrs:
            self.fields[attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = False


def token(page, action):
    return Form(page.get_data(as_text=True), action).fields


def app_for(store, **options):
    return reading_room.create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io} | options)


def submit(client, location="/", question=QUESTION):
    page = client.get(location)
    action = "/ask" if location == "/" else location + "/ask"
    return client.post(action, data=token(page, action) | {"question": question})


def test_new_state_does_not_create_session_and_history_opens_without_io(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    client = app_for(store).test_client()
    assert client.get("/").status_code == 200
    assert store.list_sessions() == ()
    session = prepared_session(store)
    older = store.create("A quiet older question")
    store.rename(session.session_id, "Tree canopy & the city")
    page = client.get(f"/sessions/{session.session_id}")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert html.index('title="Tree canopy &amp; the city"') < html.index('title="A quiet older question"')
    assert len([1 for tag, a in Page(html).tags if tag == "section" and a.get("class") == "turn"]) == 3
    assert QUESTION in html and FOLLOWUP in html
    assert all(turn.answer for turn in store.load(session.session_id).state.turns)
    assert store.load(older.metadata.session_id).state.turns == ()


def test_exact_historical_citations_multiple_materials_and_all_acquisitions(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = prepared_session(store)
    # A fresh app and store have no session/process state. Display only saved turns.
    client = app_for(SQLiteSessionStore(store.path)).test_client()
    html = client.get(f"/sessions/{session.session_id}").get_data(as_text=True)
    page = Page(html)
    ids = [a["id"] for tag, a in page.tags if "id" in a]
    assert len(ids) == len(set(ids))
    assert {"turn-1-source-1", "turn-2-source-1", "turn-3-source-1"} <= set(ids)
    links = [a["href"] for tag, a in page.tags if a.get("class") == "citation"]
    assert {"#turn-1-source-1", "#turn-2-source-1", "#turn-3-source-1"} <= set(links)
    old = html.split('id="turn-1-source-1"', 1)[1].split('</details>', 1)[0]
    assert EARLY in old and LATER[:100] not in old
    assert session.turns[0].citations[0].materials == (session.acquisitions[0],)
    assert len(session.turns[1].citations[0].materials) == 2
    assert session.turns[2].citations[0].url != session.turns[0].citations[0].url
    assert {"Extractive highlight", "Fetched source text", "Selected slice"} <= set(
        label for label in ["Extractive highlight", "Fetched source text", "Selected slice"] if label in html)
    assert "Show full material" in html and "END OF COMPLETE SAVED MATERIAL" in html
    assert page.pre == [item.content for turn in session.turns for c in turn.citations for item in c.materials]
    assert html.count('class="citation"') == len([use for turn in session.turns for use in turn.citation_uses])
    assert 'ordinary numeric text [1]' in html
    assert {"table", "blockquote", "ul", "strong"} <= {tag for tag, a in page.tags}


def test_browser_new_and_followup_use_real_session_and_survive_app_replacement(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    model = Script(*first_script(), orient(FOLLOWUP), use("C1"), assess(FOLLOWUP, EARLY, "E1"), author("A follow-up. [E1]"))
    client = app_for(store, model=model, search=source_search).test_client()
    response = submit(client)
    assert response.status_code == 303
    metadata, = store.list_sessions()
    assert metadata.title == QUESTION and metadata.revision == 1
    location = f"/sessions/{metadata.session_id}"
    assert submit(client, location, FOLLOWUP).status_code == 303
    assert store.load(metadata.session_id).metadata.revision == 2
    analyst_inputs = [m for stage, m in model.calls if stage == "analyst"]
    assert analyst_inputs[-1]["conversation_context"] == [{"question": QUESTION, "answer": store.load(metadata.session_id).state.turns[0].answer}]
    fresh = app_for(SQLiteSessionStore(store.path)).test_client()
    assert "A follow-up." in fresh.get(location).get_data(as_text=True)
    assert not model.replies


@pytest.mark.parametrize("existing", [False, True])
def test_failure_preserves_all_prior_durable_state_and_keeps_question_for_edit(tmp_path, existing):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = prepared_session(store) if existing else None
    before = store.load(session.session_id) if session else None
    def failing(*a):
        raise RuntimeError("PRIVATE_EXCEPTION_DETAILS_C:/secret/path")
    client = app_for(store, model=failing).test_client()
    response = submit(client, f"/sessions/{session.session_id}" if session else "/", "Keep this question")
    html = response.get_data(as_text=True)
    assert response.status_code == 503 and "Research didn’t complete" in html
    assert "Keep this question</textarea>" in html and "PRIVATE_EXCEPTION" not in html
    assert store.load(session.session_id) == before if session else store.list_sessions() == ()


@pytest.mark.parametrize("partial", [False, True])
def test_partial_and_unable_are_completed_answers(tmp_path, partial):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    start = (use("C1"),) if partial else (done(),)
    model = Script(orient(QUESTION), *start, analysis("unable", refs=("E1",) if partial else ()),
                   author("Some parts remain unresolved. [E1]" if partial else "An answer was not established."))
    if partial:
        prepared_session(store)
        session_id = store.list_sessions()[0].session_id
        location = f"/sessions/{session_id}"
    else:
        location = "/"
    client = app_for(store, model=model).test_client()
    response = submit(client, location)
    assert response.status_code == 303
    html = client.get(response.location).get_data(as_text=True)
    assert 'class="research-limitation"' in html and 'class="error-notice"' not in html
    saved = store.load(store.list_sessions()[0].session_id)
    assert saved.state.turns[-1].posture == ("partial" if partial else "unable")


def test_rename_edits_only_metadata_preserves_revision_and_inflight_commit_title(tmp_path):
    import sqlite3
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = prepared_session(store)
    before = store.load(session.session_id)
    with closing(sqlite3.connect(store.path)) as connection:
        payload = connection.execute("SELECT payload FROM sessions").fetchone()[0]
    # This ask object predates the title edit; commit must use the current title.
    inflight = ResearchSession.open(session.session_id, store=store, model=Script(
        orient(FOLLOWUP), use("C1"), assess(FOLLOWUP, EARLY, "E1"), author("More. [E1]")), search=no_io, fetch=no_io)
    client = app_for(store).test_client()
    location = f"/sessions/{session.session_id}"
    form = token(client.get(location + "?edit=rename"), location + "/rename")
    response = client.post(location + "/rename", data=form | {"title": "  A new title  "})
    assert response.status_code == 303
    after = store.load(session.session_id)
    assert after.state == before.state and after.metadata.revision == before.metadata.revision
    assert after.metadata.created_at == before.metadata.created_at and after.metadata.title == "A new title"
    with closing(sqlite3.connect(store.path)) as connection:
        assert connection.execute("SELECT payload FROM sessions").fetchone()[0] == payload
    inflight.ask(FOLLOWUP)
    assert store.load(session.session_id).metadata.title == "A new title"
    form = token(client.get(location + "?edit=rename"), location + "/rename")
    assert client.post(location + "/rename", data=form | {"title": "   "}).status_code == 400
    assert store.load(session.session_id).metadata.title == "A new title"


def test_confirmation_delete_is_exact_and_stale_tabs_fail_safely(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = prepared_session(store)
    other = store.create("Keep this one")
    client = app_for(store).test_client()
    location = f"/sessions/{session.session_id}"
    old_ask_form = token(client.get(location), location + "/ask")
    assert not token(client.get(location), location + "/delete")  # Only the confirmation page issues this action.
    confirmation = client.get(location + "/delete")
    assert "This permanently removes" in confirmation.get_data(as_text=True)
    assert len(store.list_sessions()) == 2  # GET never deletes.
    form = token(confirmation, location + "/delete")
    assert client.post(location + "/delete", data=form).status_code == 400
    form = token(client.get(location + "/delete"), location + "/delete")
    assert client.post(location + "/delete", data=form | {"confirm": "delete"}).status_code == 303
    assert store.list_sessions() == (other.metadata,)
    assert client.get(location).status_code == 303
    stale = client.post(location + "/ask", data=old_ask_form | {"question": "My unsaved question"})
    assert stale.status_code == 409 and "My unsaved question</textarea>" in stale.get_data(as_text=True)
    assert store.list_sessions() == (other.metadata,)


def test_stale_research_and_delete_forms_do_not_run_or_remove_new_turns(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = prepared_session(store)
    client = app_for(store).test_client()
    location = f"/sessions/{session.session_id}"
    old = token(client.get(location), location + "/ask")
    deletion = token(client.get(location + "/delete"), location + "/delete")
    next_session = ResearchSession.open(session.session_id, store=store, model=Script(
        orient(FOLLOWUP), use("C1"), assess(FOLLOWUP, EARLY, "E1"), author("A new answer. [E1]")), search=no_io, fetch=no_io)
    next_session.ask(FOLLOWUP)
    before = store.load(session.session_id)
    assert client.post(location + "/ask", data=old | {"question": FOLLOWUP}).status_code == 409
    assert client.post(location + "/delete", data=deletion | {"confirm": "delete"}).status_code == 409
    assert store.load(session.session_id) == before


def test_duplicate_inflight_new_submission_is_claimed_once(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    entered, release = Event(), Event()
    model = Script(*first_script())
    def delayed(*args):
        entered.set()
        assert release.wait(5)
        return model(*args)
    app = app_for(store, model=delayed, search=source_search)
    data = token(app.test_client().get("/"), "/ask") | {"question": QUESTION}
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(lambda: app.test_client().post("/ask", data=data))
        try:
            assert entered.wait(5)
            assert app.test_client().post("/ask", data=data).status_code == 409
        finally:
            release.set()
        assert pending.result().status_code == 303
    assert len(store.list_sessions()) == 1 and store.list_sessions()[0].revision == 1
    assert app.test_client().post("/ask", data=data).status_code == 409


@pytest.mark.parametrize("headers", [
    {"Origin": "https://evil.example"}, {"Origin": "null"}, {"Origin": "http://localhost:9999"},
    {"Sec-Fetch-Site": "cross-site"}, {"Host": "evil.example"},
])
def test_host_and_cross_origin_guards_before_mutations(tmp_path, headers):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    client = app_for(store).test_client()
    form = token(client.get("/"), "/ask")
    assert client.post("/ask", data=form | {"question": QUESTION}, headers=headers).status_code in {400, 403}
    assert store.list_sessions() == ()


def test_forged_misdirected_and_restarted_forms_fail_without_io(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    client = app_for(store).test_client()
    assert client.post("/ask", data={"question": QUESTION}).status_code == 409
    fields = token(client.get("/"), "/ask")
    assert client.post("/sessions/another/rename", data=fields | {"title": "No"}).status_code == 409
    assert app_for(store).test_client().post("/ask", data=fields | {"question": QUESTION}).status_code == 409
    assert store.list_sessions() == ()
    response = client.get("/")
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert response.headers["X-Frame-Options"] == "DENY" and response.headers["Cache-Control"] == "no-store"


def test_untrusted_question_title_answer_and_material_are_inert(tmp_path):
    attack = '<img src=x onerror="alert(1)"><script>alert(1)</script>'
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    client = app_for(store, model=Script(*first_script(attack + " [E1]")),
                     search=lambda q: [replace(source_search(q)[0], title=attack, context=attack)]).test_client()
    response = submit(client, question=attack)
    html = client.get(response.location).get_data(as_text=True)
    page = Page(html)
    assert not any(tag in {"img", "iframe", "object", "embed"} for tag, a in page.tags)
    assert not any(name.startswith("on") for tag, a in page.tags for name in a)
    assert len([1 for tag, a in page.tags if tag == "script"]) == 1
    assert page.pre == [attack]
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,test", "//example.com/", "https://u:p@example.com", "https://example.com/\n"])
def test_source_urls_fail_safely_and_markdown_cannot_forge_citations(tmp_path, url):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = prepared_session(store)
    body = Page(source_body_html(replace(session.turns[0].citations[0], url=url)))
    assert not any(tag == "a" for tag, a in body.tags)
    turn = replace(session.turns[0], answer="[fake](#source-1) [unsafe](javascript:alert(1))", citation_uses=())
    assert not any(a.get("class") == "citation" or a.get("href", "").startswith("#") for tag, a in Page(answer_html(turn)).tags)


def test_launch_path_and_loopback_binding(monkeypatch, tmp_path, capsys):
    captured = {}
    def fake_serve(app, *, port):
        captured["port"] = port
        assert app.test_client().get("/").status_code == 200
    monkeypatch.setattr(reading_room, "serve", fake_serve)
    path = tmp_path / "chosen" / "sessions.sqlite3"
    assert reading_room.main(["--database", str(path), "--port", "7339"]) == 0
    assert path.is_file() and captured["port"] == 7339
    assert SQLiteSessionStore().path == default_session_path().resolve()  # Constructor performs no I/O.
    monkeypatch.undo()
    class Server:
        server_port = 7331
        def serve_forever(self): pass
        def server_close(self): captured["closed"] = True
    def server(host, port, app, **kwargs):
        captured.update(host=host, kwargs=kwargs)
        return Server()
    monkeypatch.setattr(reading_room, "make_server", server)
    reading_room.serve(app_for(SQLiteSessionStore(path)))
    assert captured["host"] == "127.0.0.1" and captured["closed"]
    assert "http://127.0.0.1:7331" in capsys.readouterr().out


def test_unavailable_database_and_post_commit_conflict_are_bounded(tmp_path):
    path = tmp_path / "bad.sqlite3"
    path.write_text("not a database")
    client = app_for(SQLiteSessionStore(path)).test_client()
    response = client.get("/")
    assert response.status_code == 503 and str(path) not in response.get_data(as_text=True)
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = prepared_session(store)
    before = store.load(session.session_id)
    class ConflictedStore(SQLiteSessionStore):
        def commit(self, *args):
            raise SessionConflictError()
    client = app_for(ConflictedStore(store.path), model=Script(
        orient(FOLLOWUP), use("C1"), assess(FOLLOWUP, EARLY, "E1"), author("Unsaved. [E1]"))).test_client()
    response = submit(client, f"/sessions/{session.session_id}", FOLLOWUP)
    assert response.status_code == 409 and "Unsaved." not in response.get_data(as_text=True)
    assert store.load(session.session_id) == before


def test_native_same_origin_post_and_external_links_preserve_privacy(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    client = app_for(store, model=Script(*first_script()), search=source_search).test_client()
    form = token(client.get("/", base_url="http://127.0.0.1:7331"), "/ask")
    response = client.post("/ask", base_url="http://127.0.0.1:7331",
                           headers={"Origin": "http://127.0.0.1:7331", "Sec-Fetch-Site": "same-origin"},
                           data=form | {"question": QUESTION})
    assert response.status_code == 303
    html = client.get(response.location).get_data(as_text=True)
    assert '<meta name="referrer" content="same-origin">' in html
    assert all(a.get("rel") == "noopener noreferrer" and a.get("target") == "_blank"
               for tag, a in Page(html).tags if tag == "a" and a.get("href", "").startswith("https://"))
