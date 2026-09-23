"""Offline custody, local reading and navigation contracts; no semantic judgment."""

import json
from functools import partial

import pytest

from core import exa_transport, linkup_transport, serper_transport
from core.exa_transport import DiscoveryCandidate, ExaTransportError, FetchedMaterial
from core.linkup_transport import LinkupTransportError
from core.serper_transport import SerperTransportError
from scryraven.acquisition import FIND_RESULT_LIMIT, AcquisitionError, AcquisitionLibrary
from scryraven.sources import Evidence, exact_view

URL = "https://example.test/specification"


def no_external():
    raise AssertionError("No external request was expected")


def request(library, kind, **kwargs):
    return library.execute({"kind": kind, **kwargs}, before_external=lambda: None)


def test_search_admits_only_actual_material_and_catalog_has_no_bodies():
    body = "  A retained source passage.\n"
    leads = [DiscoveryCandidate("Rules", URL, body, context_kind="provider_highlights"),
             DiscoveryCandidate("Other", URL + "/nav", "Generated summary", context_kind="summary"),
             DiscoveryCandidate("Omitted", URL + "/huge", "Omitted", 100, "provider_highlights"),
             DiscoveryCandidate("Bad", "javascript:bad", "untrusted")]
    order = []
    library = AcquisitionLibrary(search=lambda query: order.append(query) or leads)
    result = library.execute({"kind": "search", "query": "current rules"},
                             before_external=lambda: order.append("before"))
    assert order == ["before", "current rules"]
    assert result["status"] == "ok" and result["material_ids"] == ["E1"]
    assert result["new_acquisition_ids"] == ["E1"] and result["external"] and not result["local"]
    assert library.acquisitions == [Evidence("E1", URL, "Rules", body, "provider_highlights")]
    assert len(library.catalog()["candidates"]) == 3
    assert body not in json.dumps(library.catalog()) and not library.exposed
    library.expose(["E1"])
    assert library.catalog()["materials"][0]["exposed"]


def test_duplicate_material_reuses_identity_but_changed_same_url_preserves_versions():
    bodies = iter(["First source wording.", "First source wording.", "Revised source wording."])
    library = AcquisitionLibrary(search=lambda q: [DiscoveryCandidate("Title", URL, next(bodies),
                                                                       context_kind="provider_highlights")])
    first, duplicate, revised = [request(library, "search", query="scope") for _ in range(3)]
    assert first["material_ids"] == duplicate["material_ids"] == ["E1"]
    assert duplicate["new_acquisition_ids"] == []
    assert revised["material_ids"] == ["E2"]
    assert [item.source_id for item in library.acquisitions] == ["E1", "E1"]
    assert library.acquisitions[0].content == "First source wording."


def test_links_become_readable_only_after_exact_material_exposure():
    allowed = "https://example.test/manual%20file.pdf"
    hidden = "https://example.test/hidden"
    body = f'[Manual](/manual file.pdf "manual")\n\nHidden: {hidden}'
    parent = Evidence("E1", URL, "Index", body)
    fetches = []
    library = AcquisitionLibrary((parent,), fetch=lambda url: fetches.append(url) or FetchedMaterial(url, "Manual body"))
    assert request(library, "read", target=allowed)["code"] == "unobserved_url"
    end = body.index("\n\n")
    read = library.execute({"kind": "read", "target": "E1", "mode": "local", "start_char": 0, "end_char": end},
                           before_external=no_external)
    library.expose(read["material_ids"])
    assert request(library, "read", target=hidden)["code"] == "unobserved_url"
    assert request(library, "read", target=allowed)["status"] == "ok"
    assert fetches == [allowed]


def test_question_urls_are_explicit_navigation_and_unobserved_urls_do_not_fetch():
    fetches = []
    library = AcquisitionLibrary(fetch=lambda url: fetches.append(url) or FetchedMaterial(url, "Source body"))
    library.allow_question_urls(f"What does [{URL}]({URL}) say? Also https://user:password@example.test/")  # pragma: allowlist secret -- synthetic URL rejection
    assert request(library, "read", target=URL)["status"] == "ok"
    assert request(library, "read", target=URL + "/invented")["code"] == "unobserved_url"
    assert fetches == [URL]
    assert len(library.catalog()["candidates"]) == 1


@pytest.mark.parametrize("link", [
    "[Manual](https://example.test/manual_(revised_(2026)).pdf)",
    '[Manual](/manual_(revised_(2026)).pdf "A title with a ) mark")',
    r"[Manual](/manual_\(revised_\(2026\)\).pdf)",
    '<a href="/manual_(revised_(2026)).pdf">Manual</a>',
    "Read this (https://example.test/manual_(revised_(2026)).pdf).",
])
def test_exposed_link_parentheses_preserve_the_whole_target_without_truncated_candidates(link):
    expected = "https://example.test/manual_%28revised_%282026%29%29.pdf"
    source = Evidence("E1", URL, "Index", link)
    library = AcquisitionLibrary((source,))
    library.expose(["E1"])
    assert {item["url"] for item in library.catalog()["candidates"]} == {URL, expected}
    assert request(library, "read", target="https://example.test/manual_(revised_", mode="local")["code"] == "unobserved_url"


def test_question_link_parentheses_are_registered_with_the_same_complete_identity():
    library = AcquisitionLibrary()
    library.allow_question_urls("Read [the article](https://example.test/Example_(history)).")
    assert [item["url"] for item in library.catalog()["candidates"]] == ["https://example.test/Example_%28history%29"]


def test_retained_highlight_can_be_read_locally_or_acquired_as_full_source():
    highlight = Evidence("E1", URL, "Title", "Extracted passage", "provider_highlights")
    fetches = []
    library = AcquisitionLibrary((highlight,), fetch=lambda url: fetches.append(url) or FetchedMaterial(url, "Full passage context"))
    local = library.execute({"kind": "read", "target": "E1", "mode": "local"}, before_external=no_external)
    assert local["material_ids"] == ["E1"]
    automatic = library.execute({"kind": "read", "target": "E1"}, before_external=no_external)
    assert automatic["material_ids"] == ["E1"] and automatic["local"] and fetches == []
    full = request(library, "read", target="E1", mode="full")
    assert full["material_ids"] == ["E2"] and fetches == [URL]
    assert library.acquisitions[1].source_id == "E1"
    reused_full = library.execute({"kind": "read", "target": "E1", "mode": "full"}, before_external=no_external)
    assert reused_full["material_ids"] == ["E2"] and reused_full["local"]
    unchanged_highlight = library.execute({"kind": "read", "target": "E1"}, before_external=no_external)
    assert unchanged_highlight["material_ids"] == ["E1"]
    repeated = library.execute({"kind": "read", "target": "C1"}, before_external=no_external)
    assert repeated["material_ids"] == ["E2"] and repeated["local"]


def test_refresh_keeps_old_bytes_and_exact_old_views_and_url_uses_latest():
    old = Evidence("E1", URL, "Title", "Old source body.")
    library = AcquisitionLibrary((old,), fetch=lambda url: FetchedMaterial(url, "Revised source body."))
    old_view = request(library, "read", target="E1", start_char=0, end_char=3)["material_ids"][0]
    refreshed = request(library, "read", target="E1", mode="refresh")
    assert refreshed["material_ids"] == ["E2"] and library.materials[old_view].content == "Old"
    assert library.acquisitions[0] == old and library.acquisitions[1].source_id == "E1"
    assert request(library, "read", target="E1")["material_ids"] == ["E1"]
    assert request(library, "read", target="E1", mode="full")["material_ids"] == ["E2"]
    assert request(library, "read", target=URL)["material_ids"] == ["E2"]
    assert request(library, "read", target=old_view)["material_ids"] == [old_view]


def test_large_parent_can_be_focused_repeatedly_without_refetch_or_expansion_cap():
    body = "# Identity\nThe manual applies during idle operation.\n\n" + (
        "# Unrelated context\n" + "Old equipment history. " * 300 + "\n\n") * 10
    body += "# Calibration\nThe zephyr calibration threshold is 18.\n\n"
    body += ("Other material. " * 3000)
    parent = Evidence("E1", URL, "Manual", body)
    library = AcquisitionLibrary((parent,))
    for focus in ["identity idle", "zephyr calibration", "idle operation", "zephyr threshold"]:
        result = library.execute({"kind": "read", "target": "E1", "focus": focus}, before_external=no_external)
        assert result["status"] == "ok" and result["local"]
        selected = [library.materials[ref] for ref in result["material_ids"]]
        assert all(item.acquisition == "targeted_view" for item in selected)
        assert sum(len(item.content) for item in selected) <= 32_000
        assert all(item == exact_view(parent, item.start_char, item.end_char) for item in selected)
        if "zephyr" in focus:
            assert any("threshold is 18" in item.content for item in selected)
    assert library.acquisitions == [parent]


def test_explicit_large_range_delivers_every_exact_character_in_bounded_source_order():
    body = "\n".join(f"Line {index:05d}: exact Unicode source λ🙂 remains unchanged." for index in range(5000))
    parent = Evidence("E1", URL, "Long source", body)
    library = AcquisitionLibrary((parent,))
    start, end = 17, len(body) - 31
    result = library.execute({"kind": "read", "target": "E1", "start_char": start, "end_char": end},
                             before_external=no_external)
    assert result["status"] == "ok" and result["local"] and not result["external"]
    chunks = [library.materials[ref] for ref in result["material_ids"]]
    assert len(chunks) > 1 and all(0 < len(item.content) <= 32_000 for item in chunks)
    assert chunks[0].start_char == start and chunks[-1].end_char == end
    assert all(left.end_char == right.start_char for left, right in zip(chunks, chunks[1:]))
    assert "".join(item.content for item in chunks) == body[start:end]
    assert all(item == exact_view(parent, item.start_char, item.end_char) for item in chunks)
    assert library.acquisitions == [parent]


@pytest.mark.parametrize("mode", ["auto", "local"])
def test_exact_view_target_with_focus_preserves_the_requested_material(mode):
    body = "Requested exact passage.\n\n" + "Unrelated passage. " * 4000 + "Distinct remote term."
    parent = Evidence("E1", URL, "Long source", body)
    library = AcquisitionLibrary((parent,))
    view_ref = request(library, "read", target="E1", start_char=0, end_char=24)["material_ids"][0]
    result = library.execute({"kind": "read", "target": view_ref, "mode": mode, "focus": "Distinct remote term"},
                             before_external=no_external)
    assert result["material_ids"] == [view_ref]
    assert library.materials[view_ref].content == body[:24]
    changed = library.execute({"kind": "read", "target": view_ref, "mode": mode, "focus": "Distinct remote term",
                               "start_char": len(body) - 21, "end_char": len(body)}, before_external=no_external)
    assert changed["material_ids"] == [f"E1@{len(body) - 21}:{len(body)}"]


@pytest.mark.parametrize("bounds", [{"start_char": -1, "end_char": 3}, {"start_char": 3, "end_char": 2},
                                     {"start_char": 0, "end_char": 99}, {"start_char": True, "end_char": 2},
                                     {"start_char": 0}])
def test_invalid_exact_ranges_never_enter_materials(bounds):
    library = AcquisitionLibrary((Evidence("E1", URL, "Title", "Exact text"),))
    result = library.execute({"kind": "read", "target": "E1", **bounds}, before_external=no_external)
    assert result["status"] == "error" and result["code"] == "invalid_exact_range"
    assert list(library.materials) == ["E1"]


def test_find_uses_retained_actual_text_and_returns_exact_context_without_fetch():
    retained = (Evidence("E1", URL, "First", "The idle threshold is 18 units.\nExceptions follow."),
                Evidence("E2", URL + "/two", "Second", "The wet threshold is 12 units.", "provider_highlights"),
                Evidence("E3", URL + "/three", "Third", "Other irrelevant text."))
    library = AcquisitionLibrary(retained)
    result = library.execute({"kind": "find", "query": "threshold"}, before_external=no_external)
    assert result["status"] == "ok" and result["matching_region_count"] == 2
    assert result["material_ids"] == [f"E1@0:{len(retained[0].content)}", "E2"]
    assert library.materials[result["material_ids"][0]] == exact_view(retained[0], 0, len(retained[0].content))
    assert library.acquisitions == list(retained) and not library.exposed
    assert request(library, "find", query="threshold", scope=["E3"])["material_ids"] == []
    assert request(library, "find", query="absentword")["material_ids"] == []
    assert request(library, "find", query="threshold", scope=["E999"])["code"] == "unknown_target"


def test_find_is_bounded_with_observable_omission_and_scoped_reactivation():
    retained = tuple(Evidence(f"E{i}", f"{URL}/{i}", "Title", "Threshold applies here.") for i in range(1, 13))
    library = AcquisitionLibrary(retained)
    found = request(library, "find", query="threshold")
    assert len(found["material_ids"]) == FIND_RESULT_LIMIT
    assert found["matching_region_count"] == 12 and found["omitted_match_count"] == 12 - FIND_RESULT_LIMIT
    scoped = request(library, "find", query="threshold", scope=["E12"])
    assert scoped["material_ids"] == [f"E12@0:{len(retained[-1].content)}"]


def test_find_consolidates_overlap_without_losing_selected_source_characters():
    body = "\n\n".join("Needle matching context. " * 150 + str(index) for index in range(14))
    parent = Evidence("E1", URL, "Long source", body)
    library = AcquisitionLibrary((parent,))
    index = library._index(parent)
    ranked = index.rank("Needle")
    selected_ranges = [(index.regions[max(0, region - 1)][0],
                        index.regions[min(len(index.regions) - 1, region + 1)][1]) for region in ranked[:FIND_RESULT_LIMIT]]
    expected_characters = {position for start, end in selected_ranges for position in range(start, end)}
    found = library.execute({"kind": "find", "query": "Needle", "scope": ["E1"]}, before_external=no_external)
    views = [library.materials[ref] for ref in found["material_ids"]]
    actual_positions = [position for view in views for position in range(view.start_char, view.end_char)]
    assert set(actual_positions) == expected_characters
    assert len(actual_positions) == len(expected_characters)
    assert len(views) < FIND_RESULT_LIMIT
    assert all(0 < len(view.content) <= 32_000 and view == exact_view(parent, view.start_char, view.end_char) for view in views)
    assert found["omitted_match_count"] == len(ranked) - FIND_RESULT_LIMIT


def test_find_consolidation_keeps_same_url_versions_separate():
    body = "\n\n".join("Needle matching context. " * 100 + str(index) for index in range(8))
    parents = (Evidence("E1", URL, "Old source", body), Evidence("E2", URL, "New source", body + "Updated.", source_id="E1"))
    library = AcquisitionLibrary(parents)
    found = request(library, "find", query="Needle")
    views = [library.materials[ref] for ref in found["material_ids"]]
    assert {view.parent_id for view in views} == {"E1", "E2"}
    assert all(view == exact_view(library.materials[view.parent_id], view.start_char, view.end_char) for view in views)
    assert library.acquisitions == list(parents)


@pytest.mark.parametrize("operation", ["search", "read"])
def test_provider_exception_is_safe_and_budget_callback_exception_propagates(operation):
    def failed(*args):
        raise RuntimeError("SECRET provider payload")
    library = AcquisitionLibrary(search=failed, fetch=failed)
    library.allow_question_urls(URL)
    payload = {"kind": operation, "query": "query", "target": URL}
    result = library.execute(payload, before_external=lambda: None)
    assert result["code"] == f"{operation}_failed" and result["external"]
    assert "SECRET" not in json.dumps(result) and library.acquisitions == []
    with pytest.raises(RuntimeError, match="SECRET"):
        library.execute(payload, before_external=failed)


@pytest.mark.parametrize(("kind", "environment_name", "code"), [
    ("search", exa_transport.EXA_API_KEY_ENV, "exa_configuration_missing"),
    ("search_lexical", serper_transport.SERPER_API_KEY_ENV, "serper_configuration_missing"),
    ("read", linkup_transport.LINKUP_API_KEY_ENV, "linkup_configuration_missing"),
])
def test_missing_provider_configuration_reaches_acquisition_result(monkeypatch, kind, environment_name, code):
    monkeypatch.delenv(environment_name, raising=False)
    library = AcquisitionLibrary()
    library.allow_question_urls(URL)
    result = request(library, kind, query="source query", target=URL)
    assert result["status"] == "error" and result["code"] == code
    assert result["external"] and not result["local"]
    assert library.acquisitions == []


def test_linkup_no_readable_material_reaches_acquisition_result():
    class EmptyResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"markdown": "", "content": "   "}

    fetch = partial(linkup_transport.fetch_linkup, api_key="offline",  # pragma: allowlist secret
                    post=lambda *args, **kwargs: EmptyResponse())
    library = AcquisitionLibrary(fetch=fetch)
    library.allow_question_urls(URL)
    result = request(library, "read", target=URL)
    assert result["status"] == "error" and result["code"] == "linkup_material_unavailable"
    assert result["external"] and not result["local"]
    assert library.acquisitions == []


@pytest.mark.parametrize(("kind", "error", "expected"), [
    ("search", ExaTransportError("private provider detail"), "search_failed"),
    ("search_lexical", SerperTransportError("private provider detail"), "search_failed"),
    ("read", LinkupTransportError("private provider detail"), "read_failed"),
    ("search", RuntimeError("exa_configuration_missing"), "search_failed"),
    ("read", RuntimeError("linkup_material_unavailable"), "read_failed"),
])
def test_unknown_and_untyped_provider_errors_remain_generic(kind, error, expected):
    def fail(*args):
        raise error

    library = AcquisitionLibrary(search=fail, lexical_search=fail, fetch=fail)
    library.allow_question_urls(URL)
    result = request(library, kind, query="source query", target=URL)
    assert result["status"] == "error" and result["code"] == expected
    assert "private provider detail" not in json.dumps(result)


def test_mismatched_fetch_identity_is_never_admitted():
    library = AcquisitionLibrary(fetch=lambda url: FetchedMaterial(URL + "/wrong", "Wrong source"))
    library.allow_question_urls(URL)
    assert request(library, "read", target=URL)["code"] == "unusable_fetch_material"
    assert library.acquisitions == []


@pytest.mark.parametrize("payload", [None, {"kind": {"private": "value"}},
                                     {"kind": "read", "target": URL, "mode": []},
                                     {"kind": "read", "target": URL, "start_char": 0}])
def test_malformed_requests_are_safe_and_do_not_spend_external_allowance(payload):
    library = AcquisitionLibrary()
    library.allow_question_urls(URL)
    result = library.execute(payload, before_external=no_external)
    assert result["status"] == "error" and not result["external"]
    assert "private" not in json.dumps(result)


def test_retained_corpus_requires_contiguous_acquisition_ids_and_canonical_source():
    for retained in [(Evidence("E2", URL, "Title", "body"),),
                     (Evidence("E1", URL, "Title", "body"), Evidence("E2", URL, "Title", "new body")),
                     (exact_view(Evidence("E1", URL, "Title", "body"), 0, 2),)]:
        with pytest.raises(AcquisitionError, match="invalid_retained_acquisitions"):
            AcquisitionLibrary(retained)
    library = AcquisitionLibrary((Evidence("E1", URL, "Title", "body"),))
    with pytest.raises(AcquisitionError, match="unknown_exposure_reference"):
        library.expose(["E1", "E999"])
    assert not library.exposed
