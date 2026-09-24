"""Offline exact historical reopening and mechanical Read coverage contracts."""

import tempfile
from pathlib import Path

import pytest
from test_research_loop import Script, answer, decision, request

from core.exa_transport import FetchedMaterial
from scryraven.acquisition import AcquisitionLibrary
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.sources import Evidence, exact_view

URL = "https://example.test/retained-manual"


def no_external(*args, **kwargs):
    raise AssertionError("Unexpected external I/O")


def read(library, target="E1", **kwargs):
    return library.execute({"kind": "read", "target": target, **kwargs}, before_external=no_external)


def test_persisted_historical_citation_reopens_exact_view_locally():
    body = "Preface. " + "Unselected content. " * 2400 + "The retained value is 17."
    start = len(body) - len("The retained value is 17.")
    end = len(body)
    ref = f"E1@{start}:{end}"
    first_read = request("read", query="", target="C1")
    first_read.update(start_char=start, end_char=end)
    first_model = Script(
        decision(requests=[first_read]),
        decision("answer", [ref]),
        answer(f"The value is 17. [{ref}]", readings=[
            {"evidence_ref": ref, "passages": [body[start:end]]},
        ]),
    )
    second_model = Script(
        decision(requests=[request("read", query="", target=ref, mode="local")]),
        decision("answer", [ref]),
        answer(f"The retained value remains 17. [{ref}]", readings=[
            {"evidence_ref": ref, "passages": [body[start:end]]},
        ]),
    )
    fetches = []

    def fetch(url):
        fetches.append(url)
        return FetchedMaterial(url, body)

    with tempfile.TemporaryDirectory(prefix="scryraven-read-reopen-") as directory:
        store = SQLiteSessionStore(Path(directory) / "session.sqlite3")
        session = ResearchSession.create(store=store, model=first_model, search=no_external, fetch=fetch)
        first = session.ask(f"Read {URL} for its value.")
        assert fetches == [URL]
        assert first.citations[0].number == 1
        assert first.citations[0].materials == (exact_view(session.acquisitions[0], start, end),)
        assert [item.id for item in session.acquisitions] == ["E1"]

        reopened = ResearchSession.open(session.session_id, store=store, model=second_model,
                                        search=no_external, fetch=no_external)
        assert [item.id for item in reopened.acquisitions] == ["E1"]
        second = reopened.ask("Where did that value come from?")

        assert fetches == [URL]
        assert second.trace[-1]["budget"]["external_attempts"] == 0
        assert [item.id for item in reopened.acquisitions] == ["E1"]
        assert first.citations == reopened.turns[0].citations
        assert second_model.calls[0][2]["evidence"] == [first.selected_evidence[0].material()]
        assert second_model.calls[0][2]["catalog"]["materials"][0]["id"] == "E1"
        assert second_model.calls[1][2]["evidence"][0]["id"] == ref
        assert second_model.calls[1][2]["evidence"][0]["content"] == body[start:end]
        receipt = second_model.calls[1][2]["last_route"][0]["read_receipt"]
        assert receipt["selection_mode"] == "targeted_view"
        assert receipt["ranges"] == [{"id": ref, "start_char": start, "end_char": end}]
        assert not receipt["full_body_in_packet"]


@pytest.mark.parametrize("mode", ["auto", "local"])
def test_direct_view_id_and_explicit_parent_range_reconstruct_identical_evidence(mode):
    parent = Evidence("E1", URL, "Retained manual", "abc 123 exact passage xyz")
    direct = AcquisitionLibrary((parent,))
    explicit = AcquisitionLibrary((parent,))
    ref = "E1@4:21"
    direct_result = read(direct, ref, mode=mode)
    explicit_result = read(explicit, "E1", mode=mode, start_char=4, end_char=21)
    assert direct_result["material_ids"] == explicit_result["material_ids"] == [ref]
    assert direct.materials[ref] == explicit.materials[ref] == exact_view(parent, 4, 21)
    assert direct_result["local"] and not direct_result["external"]
    assert direct.acquisitions == explicit.acquisitions == [parent]


def test_direct_view_id_uses_the_named_retained_version_of_a_source():
    old = Evidence("E1", URL, "Retained manual", "Old exact wording.")
    new = Evidence("E2", URL, "Retained manual", "New exact wording.", source_id="E1")
    library = AcquisitionLibrary((old, new), fetch=no_external)
    result = read(library, "E1@0:3", mode="local")
    assert result["material_ids"] == ["E1@0:3"]
    assert library.materials["E1@0:3"] == exact_view(old, 0, 3)
    assert library.materials["E1@0:3"].source_id == "E1"
    assert library.materials["E1@0:3"].content == "Old"
    assert read(library, "E2@0:3", mode="local")["material_ids"] == ["E2@0:3"]
    assert library.materials["E2@0:3"].content == "New"
    assert library.acquisitions == [old, new]


@pytest.mark.parametrize("target,code", [
    ("E1@-1:3", "invalid_exact_range"),
    ("E1@3:2", "invalid_exact_range"),
    ("E1@0:99", "invalid_exact_range"),
    ("E1@00:3", "invalid_exact_range"),
    ("E1@bad", "invalid_exact_range"),
    ("E1@" + "9" * 4301 + ":3", "invalid_exact_range"),
    ("E99@0:2", "unknown_target"),
])
def test_invalid_direct_view_ids_fail_without_fetch_or_material_creation(target, code):
    library = AcquisitionLibrary((Evidence("E1", URL, "Title", "Exact text"),), fetch=no_external)
    result = read(library, target, mode="local")
    assert result["status"] == "error" and result["code"] == code
    assert result["local"] and not result["external"]
    assert list(library.materials) == ["E1"]


def test_direct_view_id_cannot_use_a_highlight_as_full_parent():
    highlight = Evidence("E1", URL, "Title", "Extracted text", "provider_highlights")
    library = AcquisitionLibrary((highlight,), fetch=no_external)
    result = read(library, "E1@0:4", mode="local")
    assert result["code"] == "invalid_exact_range"
    assert list(library.materials) == ["E1"]


def test_oversized_synthetic_view_id_fails_safely_and_explicit_range_still_splits():
    parent = Evidence("E1", URL, "Long manual", "a" * 70_000)
    library = AcquisitionLibrary((parent,), fetch=no_external)
    direct = read(library, "E1@0:70000", mode="local")
    assert direct["status"] == "error" and direct["code"] == "invalid_exact_range"
    assert list(library.materials) == ["E1"]
    explicit = read(library, "E1", mode="local", start_char=0, end_char=70_000)
    assert explicit["status"] == "ok" and len(explicit["material_ids"]) == 3
    assert "".join(library.materials[ref].content for ref in explicit["material_ids"]) == parent.content


def test_invalid_explicit_range_on_reconstructed_target_leaves_no_view_behind():
    library = AcquisitionLibrary((Evidence("E1", URL, "Title", "Exact text"),))
    result = read(library, "E1@0:4", mode="local", start_char=0, end_char=99)
    assert result["code"] == "invalid_exact_range"
    assert list(library.materials) == ["E1"]


def test_small_complete_parent_and_highlights_have_honest_receipts():
    parent = Evidence("E1", URL, "Title", "The complete fetched parent.")
    library = AcquisitionLibrary((parent,))
    receipt = read(library, mode="full")["read_receipt"]
    assert receipt == {
        "selection_mode": "full_parent", "returned_characters": len(parent.content),
        "ranges": [{"id": "E1", "start_char": 0, "end_char": len(parent.content)}],
        "parent_id": "E1", "parent_characters": len(parent.content),
        "full_body_in_packet": True,
    }

    highlight = Evidence("E1", URL, "Title", "A provider highlight.", "provider_highlights")
    highlight_receipt = read(AcquisitionLibrary((highlight,)), mode="local")["read_receipt"]
    assert highlight_receipt == {
        "selection_mode": "provider_highlights", "returned_characters": len(highlight.content),
        "ranges": [],
    }


def test_large_focused_hit_miss_exact_range_and_targeted_view_receipts():
    body = "Unrelated background. " * 2200 + "Unique zephyr threshold is 17.\n" + "Further background. " * 2200
    parent = Evidence("E1", URL, "Long manual", body)
    library = AcquisitionLibrary((parent,))

    hit = read(library, focus="unique zephyr threshold")
    miss = read(library, focus="unfindablelexeme")
    for result, matched in ((hit, True), (miss, False)):
        receipt = result["read_receipt"]
        items = [library.materials[ref] for ref in result["material_ids"]]
        assert receipt["selection_mode"] == "focused_packet"
        assert receipt["lexical_match_found"] is matched
        assert receipt["parent_id"] == "E1" and receipt["parent_characters"] == len(body)
        assert receipt["returned_characters"] == sum(len(item.content) for item in items)
        assert 0 < receipt["returned_characters"] < len(body)
        assert not receipt["full_body_in_packet"]
        assert receipt["ranges"] == [
            {"id": item.id, "start_char": item.start_char, "end_char": item.end_char}
            for item in items
        ]
    assert any("Unique zephyr threshold is 17" in library.materials[ref].content
               for ref in hit["material_ids"])

    exact = read(library, start_char=100, end_char=600)
    direct = read(AcquisitionLibrary((parent,)), "E1@100:600", mode="local")
    assert exact["material_ids"] == direct["material_ids"] == ["E1@100:600"]
    for result, mode in ((exact, "exact_range"), (direct, "targeted_view")):
        receipt = result["read_receipt"]
        assert receipt["selection_mode"] == mode
        assert receipt["returned_characters"] == 500
        assert receipt["ranges"] == [{"id": "E1@100:600", "start_char": 100, "end_char": 600}]
        assert not receipt["full_body_in_packet"]

    whole_range = read(library, start_char=0, end_char=len(body))
    whole_receipt = whole_range["read_receipt"]
    assert len(whole_range["material_ids"]) > 1
    assert whole_receipt["returned_characters"] == whole_receipt["parent_characters"] == len(body)
    assert whole_receipt["full_body_in_packet"]
    assert "".join(library.materials[ref].content for ref in whole_range["material_ids"]) == body
