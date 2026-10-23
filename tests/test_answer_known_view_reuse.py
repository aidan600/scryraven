"""Research reuse of one prior exact owner item, without new citation authority."""
import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from pdf_fixtures import text_pdf

from scryraven.acquisition import AcquisitionLibrary
from scryraven.answer_library import AnswerLibrary, _available_exact_view
from scryraven.documents import SessionDocument, document_text_view, document_views, prepare_pdf
from scryraven.errors import RunError
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
    pytest.fail("Known-view reuse must not acquire or infer")


def owner(parent, known, *selections, attention=128_000):
    library = AcquisitionLibrary([parent], search=no_external, fetch=no_external,
                                 lexical_search=no_external)
    for item in (*known, *selections):
        library.materials[item.id] = item
    refs = [item.id for item in known]
    return AnswerLibrary(library, refs, attention_characters=attention)


@pytest.mark.parametrize("acquisition", ["fetched_source", "provider_highlights"])
@pytest.mark.parametrize("whole", [False, True])
def test_one_prior_exact_item_reuses_contained_view_without_new_membership(acquisition, whole):
    parent = Evidence("E1", "https://example.org/report", "Report",
                      "Hidden prefix. Exact evidence. Hidden suffix.", acquisition)
    known = parent if whole else exact_view(parent, 7, 38)
    selected = exact_view(parent, 15, 30)
    local = owner(parent, [known], selected)
    before_refs, before_exposure, before_remaining = list(local.refs), set(local.library.exposed), local.remaining

    plan = local.delivery_plan([selected.id])
    assert plan["deliverable_ids"] == [] and plan["text_characters_returned"] == 0
    assert local.refs == before_refs and local.library.exposed == before_exposure
    result = local.deliver([selected.id])
    assert result["evidence"] == [] and result["omitted_material_ids"] == []
    assert result["already_available_material_ids"] == [known.id]
    assert result["already_available_selections"] == [
        {"selected_material_id": selected.id, "available_material_id": known.id}]
    assert result["text_characters_remaining"] == before_remaining
    assert local.refs == before_refs and local.library.exposed == before_exposure
    assert selected.id not in local.refs and selected.id not in local.library.exposed

    with pytest.raises(RunError, match="invalid_citation_reference"):
        resolve_citations(f"New alias [{selected.id}]", [known], [parent], [])
    _, citations, _ = resolve_citations(f"Known original [{known.id}]", [known], [parent], [])
    assert citations[0].materials == (known,)


def test_actual_prefix_shape_reuses_22403_chars_from_prior_24000_view():
    parent = Evidence("E1", "https://example.org/order", "Order", "Exact source. " * 2500)
    known, selected = exact_view(parent, 0, 24_000), exact_view(parent, 0, 22_403)
    local = owner(parent, [known], selected)
    before = local.remaining
    result = local.deliver([selected.id])
    assert result["text_characters_returned"] == 0 and result["text_characters_remaining"] == before
    assert result["already_available_material_ids"] == [known.id]
    assert result["already_available_selections"][0]["selected_material_id"] == selected.id


def test_same_id_behavior_remains_navigation_without_new_mapping():
    parent = Evidence("E1", "https://example.org/report", "Report", "Exact source text.")
    known = exact_view(parent, 0, 12)
    local = owner(parent, [known])
    result = local.deliver([known.id, known.id])
    assert result["evidence"] == [] and result["already_available_material_ids"] == [known.id]
    assert result["omitted_material_ids"] == [] and "already_available_selections" not in result


def test_contained_navigation_and_same_id_share_one_actual_known_identity():
    parent = Evidence("E1", "https://example.org/report", "Report", "Exact source text.")
    known, selected = exact_view(parent, 0, 14), exact_view(parent, 2, 8)
    local = owner(parent, [known], selected)
    result = local.deliver([selected.id, known.id, selected.id])
    assert result["already_available_material_ids"] == [known.id]
    assert result["already_available_selections"] == [
        {"selected_material_id": selected.id, "available_material_id": known.id}]


@pytest.mark.parametrize("ranges,selected_range", [
    ([(0, 10)], (8, 18)),              # Partially new text.
    ([(0, 10), (10, 20)], (0, 20)),   # Adjacent views do not combine.
    ([(0, 12), (8, 20)], (0, 20)),    # Overlapping views do not combine.
    ([(0, 8), (12, 20)], (0, 20)),    # Gapped views do not combine.
])
def test_new_or_cross_view_range_is_returned_and_charged_whole(ranges, selected_range):
    parent = Evidence("E1", "https://example.org/report", "Report", "0123456789abcdefghij")
    known = [exact_view(parent, *span) for span in ranges]
    selected = exact_view(parent, *selected_range)
    local = owner(parent, known, selected)
    before = local.remaining
    result = local.deliver([selected.id])
    assert result["evidence"] == [selected.material()]
    assert result["text_characters_returned"] == len(selected.content)
    assert result["text_characters_remaining"] == before - len(selected.content)
    assert result["already_available_material_ids"] == []
    assert "already_available_selections" not in result


def test_same_url_canonical_source_and_identical_text_do_not_replace_another_version():
    first = Evidence("E1", "https://example.org/report", "Version one", "Exact unchanged words.")
    second = Evidence("E2", first.url, "Version two", first.content, source_id="E1")
    selected = exact_view(second, 0, 12)
    library = AcquisitionLibrary([first, second], search=no_external, fetch=no_external)
    library.materials[selected.id] = selected
    local = AnswerLibrary(library, [first.id])
    before = local.remaining
    result = local.deliver([selected.id])
    assert result["evidence"] == [selected.material()]
    assert result["already_available_material_ids"] == []
    assert result["text_characters_remaining"] == before - len(selected.content)


@pytest.mark.parametrize("changes", [
    {"source_id": "E9"}, {"url": "https://example.org/other"},
    {"content": "Altered text"}, {"range_basis": "acquired_highlight"},
])
def test_identity_text_or_coordinate_basis_mismatch_is_not_known_coverage(changes):
    parent = Evidence("E1", "https://example.org/report", "Report", "Exact source text.")
    selected = exact_view(parent, 0, 12)
    # These deliberately inconsistent candidates are not production acquisitions.
    # The pure comparison must still decline to treat them as prior exact text.
    inconsistent = replace(selected, **changes)
    assert _available_exact_view(inconsistent, [parent]) is None


def test_whole_material_is_not_replaced_by_prior_view_even_when_text_covers_all():
    parent = Evidence("E1", "https://example.org/report", "Report", "Exact source text.")
    known = exact_view(parent, 0, len(parent.content))
    local = owner(parent, [known])
    before = local.remaining
    result = local.deliver([parent.id])
    assert result["evidence"] == [parent.material()]
    assert result["text_characters_remaining"] == before - len(parent.content)
    assert "already_available_selections" not in result


def test_newly_chosen_packet_item_does_not_supply_coverage_for_another_new_item():
    parent = Evidence("E1", "https://example.org/report", "Report", "Exact source text.")
    first, nested = exact_view(parent, 0, 14), exact_view(parent, 2, 8)
    local = owner(parent, [], first, nested)
    result = local.deliver([first.id, nested.id])
    assert result["evidence"] == [first.material(), nested.material()]
    assert result["text_characters_returned"] == len(first.content) + len(nested.content)
    assert result["already_available_material_ids"] == []
    assert "already_available_selections" not in result


def test_covered_view_preserves_capacity_for_new_text_and_reports_only_real_omissions():
    parent = Evidence("E1", "https://example.org/report", "Report", "p" * 50_000)
    known, covered = exact_view(parent, 0, 24_000), exact_view(parent, 0, 22_403)
    fresh, omitted = exact_view(parent, 24_000, 24_005), exact_view(parent, 24_005, 24_011)
    local = owner(parent, [known], covered, fresh, omitted, attention=24_005)
    result = local.deliver([covered.id, fresh.id, omitted.id])
    assert result["evidence"] == [fresh.material()]
    assert result["omitted_material_ids"] == [omitted.id]
    assert result["already_available_material_ids"] == [known.id]
    assert result["text_characters_returned"] == 5 and result["text_characters_remaining"] == 0
    assert local.refs == [known.id, fresh.id] and covered.id not in local.library.exposed


def test_known_navigation_still_works_at_zero_remaining_attention():
    parent = Evidence("E1", "https://example.org/report", "Report", "Exact source text.")
    selected = exact_view(parent, 0, 12)
    local = owner(parent, [parent], selected, attention=len(parent.content))
    result = local.deliver([selected.id])
    assert result["evidence"] == [] and result["text_characters_remaining"] == 0
    assert result["omitted_material_ids"] == []
    assert result["already_available_material_ids"] == [parent.id]


def test_local_explicit_reread_still_returns_and_charges_contained_exact_text():
    parent = Evidence("E1", "https://example.org/report", "Report", "Exact source text.")
    known = exact_view(parent, 0, 14)
    local = owner(parent, [known])
    before = local.remaining
    result = local("library_read", json.dumps({
        "target": parent.id, "focus": "", "start_char": 2, "end_char": 8}))
    selected = exact_view(parent, 2, 8)
    assert result["evidence"] == [selected.material()]
    assert result["text_characters_remaining"] == before - 6
    assert local.refs == [known.id, selected.id]


def test_whole_large_highlight_safety_survives_covered_navigation_before_it():
    first = Evidence("E1", "https://example.org/first", "First", "Known exact source text.")
    large = Evidence("E2", "https://example.org/large", "Large", "h" * 65_536, "provider_highlights")
    selected = exact_view(first, 0, 12)
    library = AcquisitionLibrary([first, large], search=no_external, fetch=no_external)
    library.materials[selected.id] = selected
    local = AnswerLibrary(library, [first.id])
    before = local.remaining
    result = local.deliver([selected.id, large.id])
    assert result["evidence"] == [large.material()]
    assert result["text_characters_returned"] == 65_536
    assert result["text_characters_remaining"] == before - 65_536
    assert result["omitted_material_ids"] == []


def test_document_reuse_keeps_actual_document_page_filename_and_exact_text_identity():
    document = owned(text_pdf(["Unseen first page.", "Known exact document statement. Tail."]))
    known = document_views(document, 0, document.text_character_count)[1]
    selected = document_text_view(document, known.start_char + 6, known.start_char + 20)
    library = AcquisitionLibrary(documents=[document], search=no_external, fetch=no_external)
    library.materials.update({known.id: known, selected.id: selected})
    local = AnswerLibrary(library, [known.id])
    before = local.remaining
    result = local.deliver([selected.id])
    assert result["evidence"] == [] and result["text_characters_remaining"] == before
    assert result["already_available_material_ids"] == [known.id]
    assert selected.id not in local.refs and selected.id not in library.exposed
    assert _available_exact_view(replace(selected, filename="another.pdf"), [known]) is None
    assert _available_exact_view(replace(selected, page_start=1, page_end=1), [known]) is None
    other = replace(selected, id="D2@0:14", source_id="D2", parent_id="D2", document_id="D2",
                    start_char=0, end_char=14)
    assert _available_exact_view(other, [known]) is None
