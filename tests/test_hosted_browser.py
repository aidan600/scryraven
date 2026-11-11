"""Hosted UI acceptance with isolated users and a loopback-only HTTPS server.

The browser sees the intended HTTPS-origin topology on an ephemeral local port.
No public DNS, identity or inference service is contacted. Identity injection is
confined to this test fixture.
"""

import json
import os
from contextlib import ExitStack
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from urllib.parse import urlsplit
from zipfile import ZipFile

import pytest
import test_citation_preview_browser as citation_browser
from pdf_fixtures import text_pdf
from PIL import Image
from reading_room_samples import no_io, prepared_session
from test_persistent_sessions import tmp_path as external_tmp_path
from test_research_loop import answer, decision
from werkzeug.serving import make_server

from scryraven.hosted import AccessDenied, AccessIdentity, HostedConfig
from scryraven.reading_room import _QuietHandler, create_app
from scryraven.run_settings import RunSettings
from scryraven.session_store import SQLiteSessionStore

tmp_path = external_tmp_path
EMAILS = {"alice": "alice@example.test", "bob": "bob@example.test", "admin": "admin@example.test"}


@pytest.fixture
def browser():
    yield from citation_browser.browser.__wrapped__()


class OwnedPreparationStore:
    """Prepare ordinary synthetic historical turns under an explicit owner."""

    def __init__(self, store, owner):
        self.store, self.owner = store, owner

    def __getattr__(self, name):
        return getattr(self.store, name)

    def create(self, title=""):
        return self.store.create(title, owner_id=self.owner)


class InjectedIdentities:
    def validate(self, token):
        if token not in EMAILS:
            raise AccessDenied()
        return AccessIdentity(EMAILS[token], "synthetic-" + token, token == "admin")


@dataclass(frozen=True)
class LoopbackHostedConfig(HostedConfig):
    """Use a test server's ephemeral HTTPS port instead of production's 443."""

    port: int = 443

    @property
    def origin(self):
        return f"https://localhost:{self.port}"


def premise_model(stage, prompt, material, schema):
    return json.dumps(decision("return") if stage == "research" else
                      answer("Given your premises, **8 apples remain**.", support_basis="user_premises"))


@pytest.fixture
def hosted_ui(tmp_path):
    server = make_server("127.0.0.1", 0, lambda environ, start: (), threaded=True,
                         request_handler=_QuietHandler, ssl_context="adhoc")
    settings = RunSettings("openai", "gpt-6-luna", "medium", "gpt-6-luna", "medium", "standard", 40)
    config = LoopbackHostedConfig("localhost", "https://synthetic.cloudflareaccess.com", "offline-audience",
                                  EMAILS["admin"], frozenset((EMAILS["alice"], EMAILS["bob"])), tmp_path, settings,
                                  port=server.server_port)
    store = SQLiteSessionStore(config.database)
    alice = prepared_session(OwnedPreparationStore(store, EMAILS["alice"]))
    bob = prepared_session(OwnedPreparationStore(store, EMAILS["bob"]))
    store.rename(alice.session_id, "Alice canopy notebook")
    store.rename(bob.session_id, "Bob private notebook")
    app = create_app(store=store, hosted=config, identity_validator=InjectedIdentities(),
                     session_options={"model": premise_model, "search": no_io, "fetch": no_io})
    server.app = app
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield SimpleNamespace(app=app, store=store, config=config, origin=config.origin,
                              alice_id=alice.session_id, bob_id=bob.session_id)
    finally:
        app.extensions["research_jobs"].shutdown()
        assert app.extensions["research_jobs"].wait_idle(10)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def private_context(stack, browser, hosted_ui, user, width):
    context = stack.enter_context(browser.new_context(viewport={"width": width, "height": 1000 if width == 1440 else 844},
                                                      extra_http_headers={"Cf-Access-Jwt-Assertion": user},
                                                      ignore_https_errors=True, has_touch=width < 761,
                                                      is_mobile=width < 761))
    attempted_external, errors = [], []
    def loopback_only(route):
        outgoing = urlsplit(route.request.url)
        if outgoing.scheme != "https" or outgoing.netloc != urlsplit(hosted_ui.origin).netloc:
            attempted_external.append(route.request.url)
            route.abort()
            return
        route.continue_()
    context.route("**/*", loopback_only)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    def record_request_failure(failed):
        path = urlsplit(failed.url).path
        # Native navigation can leave a document before its deferred scripts
        # arrive. Chromium also reports canceled downloads via requestfailed.
        if failed.failure == "net::ERR_ABORTED" and (
            path in {"/static/reading_room.js", "/static/reading_room_dictation.js"} or path.endswith("/export")
        ):
            return
        errors.append(f"{failed.url}: {failed.failure}")
    page.on("requestfailed", record_request_failure)
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" and "the server responded with a status of" not in message.text else None)
    return context, page, attempted_external, errors


def screenshot(page, name):
    destination = os.environ.get("SCRYRAVEN_REVIEW_OUTPUT")
    if destination:
        folder = Path(destination)
        folder.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(folder / name))


def fits(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_viewed_completion_survives_administration_and_a_separate_authenticated_device(browser, hosted_ui):
    store = hosted_ui.store
    manager = hosted_ui.app.extensions["research_jobs"]
    job = manager.submit("Given ten apples and two removed, how many remain?", owner_id=EMAILS["admin"],
                         idempotency_key="admin-completion-view", run_settings=hosted_ui.config.run_settings)
    assert manager.wait_idle(10)
    assert store.get_job(job.job_id).state == "completed"
    base = hosted_ui.origin
    with ExitStack() as stack:
        _, admin, external, errors = private_context(stack, browser, hosted_ui, "admin", 1440)
        _, other_device, external_other, errors_other = private_context(stack, browser, hosted_ui, "admin", 1440)
        admin.goto(base)
        badge = admin.locator(f'.session-row[data-session-id="{job.session_id}"] .session-completion-state')
        assert badge.is_visible()
        admin.get_by_role("link", name="Administration").click()
        admin.wait_for_load_state("load")
        assert admin.url == base + "/admin"
        assert not store.get_job(job.job_id).viewed
        admin.goto(base)
        assert badge.is_visible()
        with admin.expect_response(lambda response: response.url.endswith("/viewed") and response.status == 204) as viewed:
            admin.locator(f'.session-row[data-session-id="{job.session_id}"] .session-link').click()
        assert viewed.value.status == 204
        admin.wait_for_url(f"{base}/sessions/{job.session_id}#turn-1")
        badge.wait_for(state="hidden")
        assert store.get_job(job.job_id).viewed
        admin.get_by_role("link", name="Administration").click()
        admin.wait_for_load_state("load")
        admin.goto(base + f"/sessions/{job.session_id}")
        assert badge.is_hidden()
        admin.reload()
        assert badge.is_hidden()
        other_device.goto(base)
        assert other_device.locator(".session-completion-state").is_hidden()
        # Navigation may cancel the browser's delivery of an already committed
        # keepalive acknowledgment. The independent-device assertions prove custody.
        viewed_url = f"{base}/sessions/{job.session_id}/jobs/{job.job_id}/viewed"
        navigation_cancellations = {
            viewed_url + ": net::ERR_ABORTED", viewed_url + ": Load request cancelled",
            base + "/jobs/status: net::ERR_ABORTED", base + "/jobs/status: Load request cancelled",
        }
        assert external == external_other == errors_other == []
        assert all(error in navigation_cancellations for error in errors), errors


@pytest.mark.parametrize("width", [1440, 390, 320])
def test_separate_user_history_citations_and_admin_read_only(browser, hosted_ui, width, tmp_path):
    with ExitStack() as stack:
        alice_context, alice, external_a, errors_a = private_context(stack, browser, hosted_ui, "alice", width)
        bob_context, bob, external_b, errors_b = private_context(stack, browser, hosted_ui, "bob", width)
        _, admin, external_admin, errors_admin = private_context(stack, browser, hosted_ui, "admin", width)
        alice.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id)
        bob.goto(hosted_ui.origin + "/sessions/" + hosted_ui.bob_id)
        assert "Alice canopy notebook" in alice.locator(".history-list").inner_text()
        assert "Bob private notebook" not in alice.locator(".history-list").inner_text()
        assert "Bob private notebook" in bob.locator(".history-list").inner_text()
        assert "Alice canopy notebook" not in bob.locator(".history-list").inner_text()
        assert alice_context != bob_context
        for page in (alice, bob):
            fits(page)
            assert not page.locator("#run-backend, input[name=research_model], input[name=answer_model]").count()
            assert not page.locator(".hosted-run-settings").count()
            assert "Standard processing" in page.locator(".hosted-processing-note").inner_text()
            citation = page.locator("a.citation").first
            citation.focus()
            page.locator("#citation-preview").wait_for(state="visible")
            page.locator(".saved-excerpt-link").click()
            assert "Synthetic field note, initial edition." in page.locator("#turn-1-source-1-excerpt").inner_text()
            assert page.locator("#turn-1-source-1-excerpt").get_attribute("open") is not None
            fits(page)
        screenshot(alice, f"hosted-alice-citations-{width}.png")
        assert alice.goto(hosted_ui.origin + "/sessions/" + hosted_ui.bob_id).status == 404
        assert bob.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id).status == 404
        admin.goto(hosted_ui.origin + "/admin")
        assert EMAILS["alice"] in admin.locator(".admin-sessions").inner_text()
        assert EMAILS["bob"] in admin.locator(".admin-sessions").inner_text()
        fits(admin)
        screenshot(admin, f"hosted-admin-{width}.png")
        admin.get_by_role("link", name="Alice canopy notebook", exact=True).click()
        assert "Administrator view · read only" in admin.locator(".notice").inner_text()
        assert not admin.locator(".ask-form, .rename-form, .session-actions, .delete-button").count()
        assert admin.locator("a.citation").count()
        admin.locator("a.citation").first.focus()
        admin.locator(".saved-excerpt-link").click()
        assert "Synthetic field note, initial edition." in admin.locator("#turn-1-source-1-excerpt").inner_text()
        screenshot(admin, f"hosted-readonly-{width}.png")
        with admin.expect_download() as download:
            admin.get_by_role("link", name="Export session and diagnostics", exact=True).click()
        export_path = tmp_path / f"admin-session-{width}.zip"
        download.value.save_as(export_path)
        with ZipFile(export_path) as archive:
            record = json.loads(archive.read("session.json"))
        assert record["metadata"]["owner_id"] == EMAILS["alice"]
        assert record["state"]["turns"][0]["citations"]
        assert external_a == external_b == external_admin == []
        assert errors_a == errors_b == errors_admin == []


@pytest.mark.parametrize("width", [1440, 390, 320])
def test_owner_creates_reopens_renames_and_deletes_with_attachment_composer(browser, hosted_ui, width):
    with ExitStack() as stack:
        _, page, external, errors = private_context(stack, browser, hosted_ui, "alice", width)
        page.goto(hosted_ui.origin)
        png = BytesIO()
        Image.new("RGB", (4, 4), "green").save(png, format="PNG")
        page.locator("#attachment-files").set_input_files([
            {"name": "synthetic-note.pdf", "mimeType": "application/pdf", "buffer": text_pdf(["Synthetic attached note."])},
            {"name": "synthetic-image.png", "mimeType": "image/png", "buffer": png.getvalue()},
        ])
        assert page.locator(".attachment-chips [role=listitem]").count() == 2
        page.get_by_label("Your research question").fill("Assume a box holds 12 apples and four are removed. How many remain?")
        screenshot(page, f"hosted-composer-{width}.png")
        page.get_by_role("button", name="Start research", exact=True).click()
        page.wait_for_function("""() => location.pathname.startsWith('/sessions/') ||
            (!document.querySelector('.ask-form')?.hasAttribute('aria-busy') &&
             document.querySelector('.composer-error')?.hidden === false)""")
        assert urlsplit(page.url).path.startswith("/sessions/"), (page.locator(".composer-error").inner_text(), errors, external)
        session_id = urlsplit(page.url).path.split("/")[-1]
        assert hosted_ui.app.extensions["research_jobs"].wait_idle(10)
        job = hosted_ui.app.extensions["research_jobs"].list(session_id)[0]
        assert job.state == "completed", (job.state, job.error_code)
        result = page.locator(".answer")
        result.wait_for(state="visible")
        result.scroll_into_view_if_needed()
        badge = page.locator(f'.session-row[data-session-id="{session_id}"] .session-completion-state[hidden]')
        badge.wait_for(state="attached")
        assert hosted_ui.store.get_job(job.job_id).viewed
        page.reload()
        assert "8 apples remain" in result.inner_text()
        saved = hosted_ui.store.load(session_id)
        assert saved.metadata.owner_id == EMAILS["alice"]
        assert len(saved.documents) == len(saved.images) == 1
        assert page.locator(".turn-attachments li").count() == 2
        fits(page)
        page.goto(hosted_ui.origin)
        if width < 761:
            page.get_by_role("link", name="Open history", exact=True).click()
        page.locator(f'.session-row[data-session-id="{session_id}"] .session-link').click()
        assert "8 apples remain" in page.locator(".answer").inner_text()
        page.locator(".room-header .session-actions summary").click()
        page.locator(".room-header").get_by_role("link", name="Rename", exact=True).click()
        page.get_by_label("Session title", exact=True).fill("Alice browser lifecycle")
        page.get_by_role("button", name="Save", exact=True).click()
        assert page.locator("h1.session-title").inner_text() == "Alice browser lifecycle"
        screenshot(page, f"hosted-reopened-{width}.png")
        page.locator(".room-header .session-actions summary").click()
        page.locator(".room-header").get_by_role("link", name="Delete", exact=True).click()
        page.get_by_role("button", name="Delete session", exact=True).click()
        page.wait_for_url(hosted_ui.origin + "/?notice=deleted")
        assert len(hosted_ui.store.list_sessions(owner_id=EMAILS["alice"])) == 1
        assert session_id not in {item.session_id for item in hosted_ui.store.list_sessions()}
        assert external == []
        # Reload may cancel response delivery after the acknowledgment has committed.
        acknowledged_abort = f"{hosted_ui.origin}/sessions/{session_id}/jobs/{job.job_id}/viewed: net::ERR_ABORTED"
        assert all(error == acknowledged_abort for error in errors), errors


def test_browser_manipulations_cannot_cross_owner_or_change_hosted_policy(browser, hosted_ui):
    with ExitStack() as stack:
        _, alice, external_a, errors_a = private_context(stack, browser, hosted_ui, "alice", 1440)
        _, bob, external_b, errors_b = private_context(stack, browser, hosted_ui, "bob", 1440)
        _, admin, external_admin, errors_admin = private_context(stack, browser, hosted_ui, "admin", 1440)
        alice.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id)
        bob.goto(hosted_ui.origin + "/sessions/" + hosted_ui.bob_id)
        alice_token = alice.locator('.ask-form input[name=form_token]').input_value()
        # Native fetch supplies the real browser Origin, preserving application
        # authorization and cross-origin request checks.
        statuses = bob.evaluate("""async ({foreign, stolen}) => {
            const form = document.querySelector('.ask-form');
            const data = new FormData(form); data.set('question', 'forged question');
            const post = async (url, body) => (await fetch(url, {method:'POST', body, redirect:'manual'})).status;
            const foreignStatus = await post('/sessions/' + foreign + '/ask', data);
            data.set('form_token', stolen);
            const stolenStatus = await post(form.action, data);
            data.set('form_token', form.querySelector('[name=form_token]').value);
            data.set('owner_id', 'alice@example.test'); data.set('session_id', foreign);
            const fieldsStatus = await post(form.action, data);
            data.delete('owner_id'); data.delete('session_id'); data.set('backend','openrouter');
            const policyStatus = await post(form.action, data);
            return [foreignStatus, stolenStatus, fieldsStatus, policyStatus];
        }""", {"foreign": hosted_ui.alice_id, "stolen": alice_token})
        assert statuses == [404, 409, 400, 400]
        assert hosted_ui.app.extensions["research_jobs"].list() == ()
        assert bob.evaluate("async () => (await fetch('/jobs/status')).json()") == {"jobs": []}
        assert bob.evaluate("async () => (await fetch('/admin')).status") == 404
        assert bob.evaluate("async id => (await fetch('/admin/sessions/'+id+'/export')).status", hosted_ui.bob_id) == 404
        admin.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id)
        assert admin.evaluate("async id => (await fetch('/sessions/'+id+'/rename', {method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'title=forged'})).status", hosted_ui.alice_id) == 404
        assert hosted_ui.store.get_metadata(hosted_ui.alice_id).title == "Alice canopy notebook"
        assert external_a == external_b == external_admin == []
        assert errors_a == errors_b == errors_admin == []
