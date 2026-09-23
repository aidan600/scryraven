"""Exact source-index mechanics shared by ordinary acquisition."""
from scryraven.sources import PACKET_CHARACTERS, Evidence, SourceIndex, exact_view, rank_corpus_regions

URL = "https://example.test/standard"
QUESTION = "What pressure does the standard specify, and under what conditions?"
PASSAGE = "The setpoint is 12 kPa, with a range of 11–13 kPa (high confidence), only while idle."

def large_source():
    return Evidence("E1", URL, "Standard", "# Standard\nApplicable pressure standard.\n\n" +
                    ("# Other equipment\n" + "Unrelated mechanical history. " * 240 + "\n\n") * 25 +
                    "# Pressure operation\n" + PASSAGE + "\n\n" + "Sensor installation context. " * 150 +
                    "\n\nCaption | Pressure uncertainty\nThe stated range describes operation while idle, not while running.\n\n" +
                    ("# Appendix\n" + "Other equipment settings. " * 250 + "\n\n") * 15)



def test_large_source_packet_has_exact_bounds_and_preserves_nearby_context():
    source = large_source()
    views, metrics = SourceIndex(source).packet([QUESTION, "Pressure range conditions"], PASSAGE)
    assert sum(len(v.content) for v in views) <= PACKET_CHARACTERS < len(source.content)
    assert any(PASSAGE in view.content for view in views)
    assert "not while running" in " ".join(v.content for v in views)
    for view in views:
        assert view.content == source.content[view.start_char:view.end_char]
        assert view.source_id == source.id and view.parent_id == source.id
    assert not metrics["full_body_in_packet"]


def test_corpus_region_rank_uses_shared_statistics_and_stable_ties():
    sources = [Evidence(f"E{number}", f"{URL}/{number}", "", "amber marker") for number in range(1, 9)]
    sources.append(Evidence("E9", f"{URL}/9", "", "amber cobalt quartz marker"))
    indexes = [SourceIndex(source) for source in sources]
    first, count = rank_corpus_regions(indexes, "amber cobalt quartz")
    second, repeated_count = rank_corpus_regions(indexes, "amber cobalt quartz")
    assert count == repeated_count == 9
    assert [(index.source.id, region) for index, region in first] == [
        ("E9", 0), *((f"E{number}", 0) for number in range(1, 9))
    ]
    assert first == second


def test_corpus_region_rank_excludes_ephemeral_targeted_views():
    parent = Evidence("E1", URL, "", "amber cobalt quartz")
    view = exact_view(parent, 0, len(parent.content))
    hits, count = rank_corpus_regions([SourceIndex(parent), SourceIndex(view)], "amber cobalt")
    assert count == 1
    assert [(index.source.id, region) for index, region in hits] == [("E1", 0)]


def test_corpus_region_rank_compares_sparse_and_dense_sources_on_one_scale():
    sparse = Evidence("E1", URL, "", "\n\n".join(
        ["quasar " + "filler " * 400] + ["filler " * 400 for _ in range(19)]
    ))
    dense = Evidence("E2", f"{URL}/dense", "", "quasar " * 5)
    hits, count = rank_corpus_regions([SourceIndex(sparse), SourceIndex(dense)], "quasar")
    assert count == 2
    assert [index.source.id for index, _ in hits] == ["E2", "E1"]
