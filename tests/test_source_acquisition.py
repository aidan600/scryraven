"""Surviving evidence promises through the ordinary application, with scripted owners."""
import json

import pytest
from test_walking_skeleton import Model, analysis, author, done, orient, read, relevance, search_for

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven.research import RunError, run
from scryraven.sources import PACKET_CHARACTERS, Evidence, SourceIndex, SourcePackets, exact_view

URL = "https://example.test/standard"
QUESTION = "What pressure does the standard specify, and under what conditions?"
PASSAGE = "The setpoint is 12 kPa, with a range of 11–13 kPa (high confidence), only while idle."


def use(*refs):
    return "research", {"action": "use_material", "query": "", "candidate_refs": list(refs),
                        "revised_answer_needs": None, "summary": "Select the actual applicable source passage.",
                        "search_hypothesis": None, "context_needed": None}


def verdict(text=PASSAGE, *, refs=("E1",), anchors=None, decision="supported", gap=None):
    reply = analysis(decision, refs=refs, next_need=gap)[1]
    reply["coverage"][0]["need"] = QUESTION
    reply["coverage"][0]["findings"] = [{
        "text": text, "support_refs": list(refs),
        "anchors": anchors if anchors is not None else [{"evidence_ref": refs[0], "quote": text}],
    }] if refs else []
    return "analyst", reply


def lead(content=PASSAGE):
    return DiscoveryCandidate("Standard", URL, content, context_kind="provider_highlights")


def no_fetch(url):
    raise AssertionError(f"Unnecessary acquisition of {url}")


def test_sufficient_provider_material_reaches_analyst_author_and_citations_without_fetch():
    model = Model(orient(QUESTION), search_for(), use("C1"), verdict(), author(PASSAGE + " [E1]"))
    result = run(QUESTION, model=model, search=lambda q: [lead()], fetch=no_fetch)
    assert len(model.calls) == 5
    assert result.selected_evidence[0].content == PASSAGE
    assert result.selected_evidence[0].acquisition == "provider_highlights"
    assert f"[Standard]({URL})" in result.answer
    assert model.calls[-1][1]["coverage"][0]["findings"][0]["anchors"] == [{"evidence_ref": "E1", "quote": PASSAGE}]
    assert model.calls[-1][1]["evidence"] == model.calls[-2][1]["evidence"]


def test_context_gap_acquires_same_url_once_preserving_excerpt_and_source_identity():
    excerpt = "The setpoint is 12 kPa."
    reads = []
    model = Model(
        orient(QUESTION), search_for(), use("C1"),
        verdict(excerpt, decision="research_needed", gap="The operating condition and range remain missing."),
        read("C1"), relevance("E2"), verdict(), author(PASSAGE + " [E1]"),
    )

    def fetch(url):
        reads.append(url)
        return FetchedMaterial(url, PASSAGE)

    result = run(QUESTION, model=model, search=lambda q: [lead(excerpt)], fetch=fetch)
    assert reads == [URL]
    assert [item.content for item in result.evidence] == [excerpt, PASSAGE]
    assert {item.source_id for item in result.evidence} == {"E1"}
    submitted = [m for s, m in model.calls if s == "analyst"][-1]["evidence"]
    assert len(submitted) == 1 and submitted[0]["id"] == "E1"
    assert [item["content"] for item in submitted[0]["materials"]] == [excerpt, PASSAGE]
    assert len(result.selected_evidence) == 2


def test_navigation_and_omission_notices_cannot_be_selected_as_material():
    model = Model(orient(QUESTION), search_for(), use("C1", "C2"), done(),
                  analysis("unable", refs=()), author("The available research did not establish the rule."))
    result = run(QUESTION, model=model, search=lambda q: [
        DiscoveryCandidate("Rule: 12 kPa", URL, "title and metadata only"),
        DiscoveryCandidate("Omitted", URL + "/omitted", "omission notice", 90000, "provider_highlights"),
    ], fetch=no_fetch)
    assert not result.evidence
    assert len([e for e in result.trace if e["action"] == "material_rejected"]) == 2


def test_new_same_url_highlights_are_immutable_material_versions_not_new_sources():
    first = "The setpoint is 12 kPa."
    batches = iter([[lead(first)], [lead(PASSAGE)]])
    model = Model(orient(QUESTION), search_for(), use("C1"),
                  verdict(first, decision="research_needed", gap="Range and condition missing."),
                  search_for("range and condition"), use("C2"), verdict(), author(PASSAGE + " [E1]"))
    result = run(QUESTION, model=model, search=lambda q: next(batches), fetch=no_fetch)
    assert [e.content for e in result.evidence] == [first, PASSAGE]
    assert len({e.source_id for e in result.evidence}) == 1
    assert len([m for s, m in model.calls if s == "analyst"][-1]["evidence"]) == 1


@pytest.mark.parametrize("anchor", [
    {"evidence_ref": "E2", "quote": PASSAGE},
    {"evidence_ref": "E1", "quote": "The device is always safe."},
    {"evidence_ref": "E1", "quote": ""},
])
def test_anchor_must_reference_submitted_material_without_invented_words(anchor):
    model = Model(orient(QUESTION), search_for(), use("C1"), verdict(anchors=[anchor]))
    with pytest.raises(RunError, match="invalid_support_anchor"):
        run(QUESTION, model=model, search=lambda q: [lead()], fetch=no_fetch)


def test_anchors_do_not_turn_mechanical_validity_into_semantic_approval():
    # The scripted Analyst deliberately misstates correct source text. Mechanics
    # must not invent a fourth semantic checker; live fidelity is a separate axis.
    wrong = "The pressure is always safe."
    model = Model(orient(QUESTION), search_for(), use("C1"),
                  verdict(wrong, anchors=[{"evidence_ref": "E1", "quote": PASSAGE}]), author(wrong + " [E1]"))
    result = run(QUESTION, model=model, search=lambda q: [lead()], fetch=no_fetch)
    assert wrong in result.answer


def test_pdf_whitespace_anchor_resolves_to_exact_source_without_semantic_rewriting():
    source = "The range is 11–13 kPa.\n\nIt applies with\u00a0high confidence only while idle."
    copied = "The range is 11–13 kPa. It applies with high confidence only while idle."
    model = Model(orient(QUESTION), search_for(), use("C1"),
                  verdict(copied, anchors=[{"evidence_ref": "E1", "quote": copied}]), author(copied + " [E1]"))
    result = run(QUESTION, model=model, search=lambda q: [lead(source)], fetch=no_fetch)
    anchor = model.calls[-1][1]["coverage"][0]["findings"][0]["anchors"][0]
    assert anchor["quote"] == source
    assert any(e["action"] == "support_anchor_resolved" for e in result.trace)


@pytest.mark.parametrize("changed", ["low confidence", "confidence", "very high confidence"])
def test_whitespace_resolution_cannot_change_epistemic_words(changed):
    copied = PASSAGE.replace("high confidence", changed)
    model = Model(orient(QUESTION), search_for(), use("C1"),
                  verdict(anchors=[{"evidence_ref": "E1", "quote": copied}]))
    with pytest.raises(RunError, match="invalid_support_anchor"):
        run(QUESTION, model=model, search=lambda q: [lead()], fetch=no_fetch)


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


def test_whole_discussion_gap_uses_full_text_and_keeps_comment_attribution():
    question = "What are the main disagreements across this entire discussion?"
    discussion = "Alice: This worked in summer.\nBob: It failed in winter.\nCara: Neither tested wet conditions."
    model = Model(orient(question), search_for(), read("C1"), relevance("E1"),
                  verdict(discussion), author(discussion + " [E1]"))
    result = run(question, model=model, search=lambda q: [lead("Alice: This worked in summer.")],
                 fetch=lambda url: FetchedMaterial(url, discussion))
    assert result.selected_evidence[0].content == discussion
    assert result.selected_evidence[0].acquisition == "fetched_source"


def test_large_source_expands_once_without_refetch_and_never_exposes_whole_parent():
    source = large_source()
    trace = []
    packets = SourcePackets()
    packets.acquire(source, [QUESTION], PASSAGE, trace)
    assert source.id not in packets.materials
    packets.expand(source.id, "Sensor installation and operating range context", trace)
    before = dict(packets.materials)
    assert not packets.expand(source.id, "another gap", trace)
    assert packets.materials == before
    assert source.content not in json.dumps([e.material() for e in packets.materials.values()])
    with pytest.raises(ValueError):
        exact_view(source, -1, 20)


def test_ordinary_application_large_packet_flows_through_research_and_both_consumers():
    source = large_source()

    class PacketModel(Model):
        def __call__(self, stage, prompt, material, schema):
            if material.get("phase") == "relevance":
                # Scripted Research chooses the exact packet provided by production.
                # This fixture never locates passages or supplies missing source text.
                self.calls.append((stage, material))
                return json.dumps(relevance(*[e["id"] for e in material["new_evidence"]])[1])
            return super().__call__(stage, prompt, material, schema)

    model = PacketModel(orient(QUESTION), search_for(), read("C1"), verdict(), author(PASSAGE + " [E1]"))
    result = run(QUESTION, model=model, search=lambda q: [lead("Missing necessary context.")],
                 fetch=lambda url: FetchedMaterial(url, source.content))
    assert all(item.acquisition == "targeted_view" for item in result.selected_evidence)
    assert model.calls[-1][1]["evidence"] == model.calls[-2][1]["evidence"]
    assert all(e["source_body_characters"] <= PACKET_CHARACTERS for e in result.trace if e["action"] == "model_started")
