"""Exact source-index mechanics shared by ordinary acquisition."""
from scryraven.sources import PACKET_CHARACTERS, Evidence, SourceIndex

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
