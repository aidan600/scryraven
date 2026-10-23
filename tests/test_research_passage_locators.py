"""Literal/whitespace locator mechanics only; no live cause or quality claim."""
import json
from datetime import datetime, timezone

import pytest
from pdf_fixtures import text_pdf

from scryraven.acquisition import AcquisitionLibrary
from scryraven.answer_library import AnswerLibrary
from scryraven.documents import SessionDocument, document_text_view, document_views, prepare_pdf
from scryraven.errors import RunError
from scryraven.research import ExactPassage, _research_return_selection, _research_selection, _ResearchSelectionError
from scryraven.results import resolve_citations
from scryraven.sources import Evidence, exact_view


def owned(data):
    prepared = prepare_pdf("report.pdf", "application/pdf", data)
    return SessionDocument(
        "D1", prepared.filename, prepared.media_type, prepared.byte_length, prepared.sha256,
        datetime.now(timezone.utc).isoformat(), prepared.page_count, prepared.text_character_count,
        prepared.textless_page_count, prepared.pages, prepared.original_pdf,
    )


def no_external(*args, **kwargs):
    pytest.fail("Locator mechanics must not acquire or infer")


def library(*items):
    return AcquisitionLibrary(items, search=no_external, fetch=no_external, lexical_search=no_external)


@pytest.mark.parametrize("original,locator,expected", [
    ("Prefix.\nValue \r\n\t 7; measured\tunits.\nTail.", "Value 7; measured units.",
     "Value \r\n\t 7; measured\tunits."),
    ("Prefix. Value\u00a0\u20037 units. Tail.", "Value 7 units.", "Value\u00a0\u20037 units."),
    ("Prefix. Value\n7 units. Tail.", " \tValue  7\tunits.\n", "Value\n7 units."),
])
def test_whitespace_only_locator_returns_original_span_bytes(original, locator, expected):
    parent = Evidence("E1", "https://example.org/report", "Report", original)
    lib = library(parent)
    owner = AnswerLibrary(lib, [], attention_characters=100)
    refs = _research_selection([ExactPassage(ref="E1", text=locator)], lib, {"E1"})
    view = lib.materials[refs[0]]
    start = original.index(expected)
    assert view == exact_view(parent, start, start + len(expected))
    assert view.content.encode() == expected.encode() and view.content != locator
    assert lib.acquisitions == [parent] and lib.exposed == set() and owner.refs == []
    result = owner.deliver(refs)
    assert result["evidence"] == [view.material()]
    assert result["text_characters_returned"] == len(expected)
    assert result["text_characters_remaining"] == 100 - len(expected)


def test_unique_literal_match_keeps_fastpath_despite_another_whitespace_variant():
    parent = Evidence("E1", "https://example.org/report", "Report", "Value 7. Then Value\t7.")
    lib = library(parent)
    refs = _research_selection([ExactPassage(ref="E1", text="Value 7.")], lib, {"E1"})
    assert lib.materials[refs[0]] == exact_view(parent, 0, len("Value 7."))


@pytest.mark.parametrize("locator", ["value 7; measured units.", "Value 7, measured units.",
                                      "Value 8; measured units.", "Value 7; modeled units.",
                                      "Value7; measured units.", "Value 7; measured unit.", " \t\n"])
def test_case_punctuation_word_and_join_changes_are_not_normalized(locator):
    parent = Evidence("E1", "https://example.org/report", "Report", "Value\n7; measured\tunits.")
    lib = library(parent)
    with pytest.raises(_ResearchSelectionError) as rejected:
        _research_selection([ExactPassage(ref="E1", text=locator)], lib, {"E1"})
    assert rejected.value.reason == "passage_not_found"
    assert list(lib.materials) == ["E1"] and lib.exposed == set()


@pytest.mark.parametrize("text,locator", [("Value\n7. Then Value\t7.", "Value 7."),
                                         ("Exact. Exact.", "Exact."), ("aaaa", "aaa")])
def test_ambiguous_normalized_or_literal_locations_are_rejected(text, locator):
    parent = Evidence("E1", "https://example.org/report", "Report", text)
    lib = library(parent)
    with pytest.raises(_ResearchSelectionError) as rejected:
        _research_selection([ExactPassage(ref="E1", text=locator)], lib, {"E1"})
    assert rejected.value.reason == "passage_ambiguous"
    assert list(lib.materials) == ["E1"]


def test_normalized_locator_cannot_return_original_span_larger_than_packet():
    parent = Evidence("E1", "https://example.org/report", "Report", "Value" + " " * 32_000 + "7.")
    lib = library(parent)
    with pytest.raises(_ResearchSelectionError) as rejected:
        _research_selection([ExactPassage(ref="E1", text="Value 7.")], lib, {"E1"})
    assert rejected.value.reason == "selection_exceeds_packet"
    assert list(lib.materials) == ["E1"] and lib.exposed == set()


def test_parent_version_quote_can_select_within_one_exposed_view_only():
    parent = Evidence("E1", "https://example.org/report", "Report",
                      "Hidden prefix. Exposed Value\n7. Hidden suffix.")
    lib = library(parent)
    start = parent.content.index("Exposed")
    end = parent.content.index(" Hidden suffix")
    exposed = exact_view(parent, start, end)
    lib.materials[exposed.id] = exposed
    before_exposure = set(lib.exposed)
    refs = _research_selection([ExactPassage(ref="E1", text="Value 7.")], lib, {exposed.id})
    view = lib.materials[refs[0]]
    expected_start = parent.content.index("Value")
    assert view == exact_view(parent, expected_start, end)
    assert lib.exposed == before_exposure and "E1" not in {exposed.id}
    owner = AnswerLibrary(lib, [])
    assert owner.refs == []
    owner.deliver(refs)
    assert owner.refs == [view.id] and parent.id not in owner.refs and exposed.id not in owner.refs
    with pytest.raises(RunError, match="invalid_citation_reference"):
        resolve_citations("Hidden parent remainder [E1@0:7]", [view], [parent], [])
    _, citations, _ = resolve_citations("The selected fact [E1]", [view], [parent], [])
    assert citations[0].materials == (view,)  # Canonical alias still means only the returned view.


def test_document_parent_locator_preserves_exposed_page_and_not_other_pages():
    document = owned(text_pdf(["Unseen first page.", "Value 7.", "Unseen last page."]))
    pages = document_views(document, 0, document.text_character_count)
    lib = AcquisitionLibrary(documents=(document,), search=no_external, fetch=no_external, lexical_search=no_external)
    visible = pages[1]
    lib.materials[visible.id] = visible
    refs = _research_selection([ExactPassage(ref="D1", text="Value\t7.")], lib, {visible.id})
    view = lib.materials[refs[0]]
    assert view == document_text_view(document, view.start_char, view.end_char)
    assert view.content == "Value 7." and view.parent_id == view.source_id == "D1"
    assert view.page_start == view.page_end == 2 and view.filename == "report.pdf" and view.range_basis is None
    assert "D1" not in lib.materials and lib.exposed == set()
    before = dict(lib.materials)
    with pytest.raises(_ResearchSelectionError) as rejected:
        _research_selection([ExactPassage(ref="D1", text="Unseen last page.")], lib, {visible.id})
    assert rejected.value.reason == "passage_range_unexposed" and lib.materials == before


@pytest.mark.parametrize("views", [[(0, 5), (5, 10)], [(0, 5), (6, 10)]])
def test_two_adjacent_or_gapped_views_do_not_grant_a_cross_view_quote(views):
    parent = Evidence("E1", "https://example.org/report", "Report", "Alpha Beta")
    lib = library(parent)
    exposed = set()
    for start, end in views:
        item = exact_view(parent, start, end)
        lib.materials[item.id] = item
        exposed.add(item.id)
    before = dict(lib.materials)
    with pytest.raises(_ResearchSelectionError) as rejected:
        _research_selection([ExactPassage(ref="E1", text="Alpha Beta")], lib, exposed)
    assert rejected.value.reason == "passage_range_unexposed"
    assert lib.materials == before and lib.exposed == set()


def test_unexposed_adjacent_remainder_and_other_versions_or_parents_are_refused():
    first = Evidence("E1", "https://example.org/report", "Report", "Hidden. Value\n7. Remainder.")
    newer = Evidence("E2", first.url, "New version", first.content, source_id="E1")
    other = Evidence("E3", "https://example.org/other", "Other parent", first.content)
    lib = library(first, newer, other)
    visible = exact_view(first, first.content.index("Value"), first.content.index(" Remainder"))
    lib.materials[visible.id] = visible
    unexposed_view = exact_view(first, visible.start_char, visible.end_char - 1)
    lib.materials[unexposed_view.id] = unexposed_view
    for ref, text, reason in [("E1", "Value 7. Remainder.", "passage_range_unexposed"),
                              ("E2", "Value 7.", "passage_range_unexposed"),
                              ("E3", "Value 7.", "passage_range_unexposed"),
                              (unexposed_view.id, "Value 7", "passage_parent_unavailable")]:
        before = dict(lib.materials)
        with pytest.raises(_ResearchSelectionError) as rejected:
            _research_selection([ExactPassage(ref=ref, text=text)], lib, {visible.id})
        assert rejected.value.reason == reason and lib.materials == before


def test_whole_selection_validation_is_atomic_without_owner_authority():
    parent = Evidence("E1", "https://example.org/report", "Report", "Prefix. Value\n7. Tail.")
    lib = library(parent)
    owner = AnswerLibrary(lib, [])
    before = dict(lib.materials)
    with pytest.raises(_ResearchSelectionError) as rejected:
        _research_selection([ExactPassage(ref="E1", text="Value 7."),
                             ExactPassage(ref="E1", text="Missing generated claim")], lib, {"E1"})
    assert rejected.value.reason == "passage_not_found"
    assert lib.materials == before and owner.refs == [] and lib.exposed == set()


def test_return_selection_keeps_good_entry_with_safe_independent_limitations():
    parent = Evidence("E1", "https://example.org/report", "Report", "Prefix. Value\n7. Tail.")
    lib = library(parent)
    owner = AnswerLibrary(lib, [])
    good = ExactPassage(ref="E1", text="Value 7.")
    refs, limitations = _research_return_selection(
        [good, ExactPassage(ref="E1", text="REJECTED_GENERATED_SECRET"), "PRIVATE_REJECTED_REFERENCE", good],
        lib, {"E1"})
    expected = exact_view(parent, parent.content.index("Value"), parent.content.index(" Tail."))
    assert refs == [expected.id] and lib.materials[refs[0]] == expected
    assert limitations == [
        {"index": 1, "reference": "E1", "validation_reason": "passage_not_found"},
        {"index": 2, "reference": None, "validation_reason": "selection_reference_invalid"}]
    assert "REJECTED" not in json.dumps(limitations)
    assert owner.refs == [] and lib.exposed == set()
    assert set(lib.materials) == {parent.id, expected.id}


def test_normalization_does_not_remove_omission_markers_or_join_separate_passages():
    marker = "[Separate provider highlight; intervening context omitted]"
    parent = Evidence("E1", "https://example.org/report", "Report",
                      f"Earlier fact.\n\n{marker}\n\nLater fact.", "provider_highlights")
    lib = library(parent)
    with pytest.raises(_ResearchSelectionError) as rejected:
        _research_selection([ExactPassage(ref="E1", text="Earlier fact. Later fact.")], lib, {"E1"})
    assert rejected.value.reason == "passage_not_found" and list(lib.materials) == ["E1"]
