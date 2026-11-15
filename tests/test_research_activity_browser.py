"""Exercise live activity through ordinary Reading Room jobs and a real browser."""

from threading import Event
from time import monotonic

import pytest
from test_citation_preview_browser import browser_at, running_room
from test_hosted_browser import screenshot
from test_research_loop import Script, answer, decision
from test_research_loop import request as operation

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven.reading_room import create_app
from scryraven.research_activity import QUERY_CHARACTERS
from scryraven.session_store import SQLiteSessionStore


@pytest.mark.parametrize("width", [1440, 320])
def test_live_activity_recovers_and_reopens_with_the_saved_answer(tmp_path, width, record_property):
    initial_model_started = Event()
    release_model = Event()
    searches_started = Event()
    release_search = Event()
    retrieval_started = Event()
    release_retrieval = Event()
    query_one = "official source for the synthetic count"
    query_two = '<img src=x onerror="window.injected=true">' + "z" * QUERY_CHARACTERS
    calls = {"search": [], "read": []}
    dispatch_times = {}

    def initial_model(_packet):
        initial_model_started.set()
        assert release_model.wait(30)
        return decision(requests=[operation(query=query_one), operation(query=query_two)])

    def search(query):
        calls["search"].append(query)
        dispatch_times[query] = monotonic()
        if len(dispatch_times) == 2:
            searches_started.set()
        assert release_search.wait(30)
        key = "one" if query == query_one else "two"
        return [DiscoveryCandidate(
            "Synthetic " + key, f"https://example.org/{key}?private=omitted",
            "A short highlight from " + key, context_kind="provider_highlights",
        )]

    def fetch(url):
        calls["read"].append(url)
        if url == "https://example.org/one?private=omitted":
            retrieval_started.set()
            assert release_retrieval.wait(30)
            return FetchedMaterial(url, "The documented synthetic count is seven.")
        raise OSError("Private transport detail")

    def read_sources(packet):
        return decision(refs=[row["id"] for row in packet["evidence"]], requests=[
            operation("read", target="https://example.org/one?private=omitted", mode="full"),
            operation("read", target="https://example.org/two?private=omitted", mode="full"),
        ])

    def return_source(packet):
        ref = next(row["id"] for row in packet["evidence"] if "count is seven" in row["content"])
        return decision("return", [ref])

    def answer_from_source(packet):
        return answer(f"The synthetic count is seven. [{packet['evidence'][0]['id']}]")

    model = Script(initial_model, read_sources, return_source, answer_from_source)
    store = SQLiteSessionStore(tmp_path / "activity-browser.sqlite3")
    app = create_app(store=store, session_options={"model": model, "search": search, "fetch": fetch})
    try:
        with running_room(app) as base:
            for browser in browser_at():
                with browser.new_context(viewport={"width": width, "height": 640 if width == 320 else 850}) as context:
                    page = context.new_page()
                    requests = []
                    errors = []
                    page.on("request", lambda request: requests.append(request.url))
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base)
                    page.locator("#question").fill("What is the synthetic count?")
                    page.get_by_role("button", name="Start research", exact=True).click()
                    active = page.locator(".research-job")
                    active.wait_for()
                    assert initial_model_started.wait(5)
                    conversation = page.url.split("#")[0]
                    state = active.get_by_role("status", name="Current activity")
                    state.filter(has_text="Investigating your question").wait_for(timeout=5000)
                    timer = active.locator("[data-activity-timer]")
                    timer.wait_for()
                    timeline = active.locator("[data-activity-recent]")
                    before = timeline.inner_text()
                    elapsed = timer.get_attribute("datetime")
                    page.wait_for_function(
                        "previous => document.querySelector('[data-activity-timer]').dateTime !== previous",
                        arg=elapsed, timeout=5000,
                    )
                    assert timeline.inner_text() == before
                    assert timer.get_attribute("aria-live") == "off"
                    assert timer.locator("xpath=ancestor::*[@role='status']").count() == 0

                    release_model.set()
                    assert searches_started.wait(5)
                    state.filter(has_text="Running parallel searches").wait_for(timeout=4000)
                    elapsed_to_render = monotonic() - min(dispatch_times.values())
                    record_property(f"event_to_render_{width}_seconds", round(elapsed_to_render, 3))
                    assert elapsed_to_render <= 3.0
                    details = active.locator("[data-activity-searches]")
                    assert details.locator(".activity-query").first.is_hidden()
                    summary = details.locator("summary")
                    summary.focus()
                    assert summary.evaluate("(el) => getComputedStyle(el).outlineStyle !== 'none'")
                    summary.press("Enter")
                    assert details.locator(".activity-query").all_text_contents() == [
                        query_one, query_two[:QUERY_CHARACTERS],
                    ]
                    assert details.locator(".activity-searches > li").count() == 1
                    assert "Query truncated." in details.inner_text()
                    assert "may include wording from your question or supplied documents" in details.inner_text()
                    assert details.locator("img, script").count() == 0
                    assert not page.evaluate("Boolean(window.injected)")
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    screenshot(page, f"research-activity-live-{width}.png")
                    reader = page.locator(".reading-scroll")
                    scroll_top = reader.evaluate("(el) => el.scrollTop")
                    tick = timer.get_attribute("datetime")
                    page.wait_for_function(
                        "previous => document.querySelector('[data-activity-timer]').dateTime !== previous",
                        arg=tick, timeout=5000,
                    )
                    assert reader.evaluate("(el) => el.scrollTop") == scroll_top
                    assert summary.evaluate("(el) => el === document.activeElement")

                    activity_request = "**/activity?after=*"
                    page.route(activity_request, lambda route: route.abort())
                    unavailable = active.get_by_text("Research activity is temporarily unavailable.", exact=True)
                    unavailable.wait_for(timeout=5000)
                    assert state.filter(has_text="Running parallel searches").is_visible()
                    page.unroute(activity_request)
                    unavailable.wait_for(state="hidden", timeout=5000)
                    assert summary.evaluate("(el) => el === document.activeElement")

                    page.reload()
                    state.filter(has_text="Running parallel searches").wait_for(timeout=5000)
                    page.goto(base)
                    page.goto(conversation)
                    state.filter(has_text="Running parallel searches").wait_for(timeout=5000)
                    release_search.set()
                    assert retrieval_started.wait(5)
                    state.filter(has_text="Retrieving source text").wait_for(timeout=5000)
                    assert "2 candidate links" in timeline.inner_text()
                    assert "source highlights in 2 results" in timeline.inner_text()
                    page.locator("#question").fill("Keep this follow-up draft")
                    release_retrieval.set()
                    page.locator(".answer").wait_for(timeout=10000)
                    assert page.locator("#question").input_value() == "Keep this follow-up draft"
                    archive = page.locator(".activity-archive")
                    assert archive.get_attribute("open") is None
                    page.reload()
                    archive = page.locator(".activity-archive")
                    count_before_open = sum("/activity?" in url for url in requests)
                    archive.get_by_text("Research activity", exact=True).click()
                    archive.get_by_text("Answer saved", exact=True).wait_for(timeout=5000)
                    assert sum("/activity?" in url for url in requests) == count_before_open + 1
                    recent = archive.locator("[data-activity-recent] li")
                    assert recent.count() == 5
                    older = archive.locator("[data-activity-older]")
                    assert older.is_visible()
                    older.locator("summary").click()
                    assert "Question queued" in older.inner_text()
                    assert "Retrieved original source text" in archive.inner_text()
                    assert "Could not retrieve source" in archive.inner_text()
                    archive.locator("[data-activity-searches] summary").click()
                    assert "example.org" in archive.inner_text()
                    assert query_two[:QUERY_CHARACTERS] in archive.inner_text()
                    assert "private=omitted" not in archive.inner_text()
                    assert "Private transport detail" not in archive.inner_text()
                    assert "The documented synthetic count is seven." not in archive.inner_text()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    assert errors == []
                    screenshot(page, f"research-activity-saved-{width}.png")
        assert sorted(calls["search"]) == sorted([query_one, query_two])
        assert len(calls["read"]) == 2
        assert [call[0] for call in model.calls] == ["research", "research", "research", "answer"]
    finally:
        release_model.set()
        release_search.set()
        release_retrieval.set()
        app.extensions["research_activity"].close()
