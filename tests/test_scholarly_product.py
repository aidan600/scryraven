"""Publication navigation and source text travel through the ordinary session."""

from test_research_loop import Script, answer, decision, no_fetch, request

from core.scholarly_transport import PublicationMetadata, PublicationRelation, ScholarlyCandidate, ScholarlyFullText
from core.transport import FetchedMaterial
from scryraven.presentation import citation_preview_html, source_body_html
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.sources import support_text

PMC = "https://pmc.ncbi.nlm.nih.gov/articles/PMC12345/"
NOTICE = "https://pubmed.ncbi.nlm.nih.gov/12345/"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
ABSTRACT = "We exposed the animals to low oxygen and measured recovery."
BODY = "Methods\n\nThirty animals were randomly allocated.\n\nResults\n\nThe untreated group did not recover."


def scholarly_request():
    return {"kind": "search_scholarly", "query": "hypoxia recovery", "objective": "Find the original experiment."}


def find_article(_query):
    metadata = PublicationMetadata(
        doi="10.1234/oxygen", pmcid="PMC12345", authors=("Sample A", "Sample B"),
        journal="The Experimental Journal", year=2024, status="published", open_article_available=True,
        related=(PublicationRelation(kind="correction", url=NOTICE),),
    )
    return [ScholarlyCandidate(PMC, "A recovery experiment", ABSTRACT, metadata, "PMC12345")]


def test_scholarly_abstract_retains_identity_and_reopens_into_in_scope_article_read(tmp_path):
    store = SQLiteSessionStore(tmp_path / "scholarly.sqlite3")
    first_model = Script(
        decision(requests=[scholarly_request()]), decision("return", ["E1"]),
        answer("The authors measured recovery after low-oxygen exposure. [E1]"),
    )
    first = ResearchSession.create(store=store, model=first_model, search=no_fetch,
                                   fetch=no_fetch, scholarly_search=find_article)
    result = first.ask("What outcome did this hypoxia experiment measure?")
    abstract, = result.selected_evidence
    assert abstract.acquisition == "publication_abstract"
    assert abstract.content == ABSTRACT
    packet = first_model.calls[1][2]
    assert NOTICE in {row["url"] for row in packet["catalog"]["candidates"]}
    assert result.trace[-1]["budget"]["physical_acquisition_dispatches"] == 1
    assert "Publication abstract" in citation_preview_html(result.citations[0])
    assert "Correction or republication" in source_body_html(result.citations[0])

    def get_body(pmcid):
        assert pmcid == "PMC12345"
        return ScholarlyFullText(PMC, BODY, LICENSE, "published")

    model = Script(
        decision(requests=[request("read", target="E1", mode="full", focus="randomly allocated")]),
        decision("return", ["E2"]),
        {**answer("The study randomly allocated thirty animals. [E2]"), "citation_passages": [
            {"ref": "E2", "occurrence": 1, "text": "Thirty animals were randomly allocated."},
        ]},
    )
    restored = ResearchSession.open(first.session_id, store=store, model=model,
                                    fetch=no_fetch, scholarly_search=no_fetch, scholarly_fetch=get_body)
    assert restored.turns == first.turns
    result = restored.ask("How many animals were randomly allocated?")
    body, = result.selected_evidence
    assert body.source_id == abstract.source_id and body.content == BODY
    support, = result.citation_uses[0].support
    assert support_text(support, body) == "Thirty animals were randomly allocated."
    assert result.trace[-1]["budget"]["physical_acquisition_dispatches"] == 1
    html = source_body_html(result.citations[0], uses=result.citation_uses)
    assert "Open-access article text" in html
    assert "Article license" in html and "Version of record" in html
    assert "The Experimental Journal" in html and "10.1234/oxygen" in html
    assert store.load(first.session_id).state.turns[-1].citations == result.citations


def test_metadata_only_publication_is_navigation_and_cannot_validate_as_evidence():
    (lead,) = find_article("")
    model = Script(
        decision(requests=[scholarly_request()]),
        decision("return"),
        answer("The search found an entry but did not establish the result.", "unable"),
    )
    session = ResearchSession(
        model=model, fetch=no_fetch, scholarly_search=lambda _query: [
            ScholarlyCandidate(lead.url, lead.title, "", lead.publication, lead.full_text_pmcid),
        ],
    )
    result = session.ask("What was the result?")
    packet = model.calls[1][2]
    assert packet["catalog"]["candidates"][0]["publication"]["doi"] == "10.1234/oxygen"
    assert packet["evidence"] == []
    assert not result.evidence and not result.citations


def test_scholarly_extractor_cannot_substitute_text_from_a_different_publication():
    def wrong_body(_pmcid):
        return ScholarlyFullText(PMC.replace("12345", "12346"), BODY, LICENSE, "published")

    model = Script(
        decision(requests=[scholarly_request()]), decision(requests=[request("read", target="C1", mode="full")]),
        decision("return", ["E1"]), answer("The abstract says they measured recovery. [E1]"),
    )
    result = ResearchSession(model=model, fetch=no_fetch, scholarly_search=find_article,
                             scholarly_fetch=wrong_body).ask("How did they study recovery?")
    assert [item.content for item in result.evidence] == [ABSTRACT]
    timing = [row for row in result.trace if row["action"] == "acquisition_timing"]
    assert timing[1]["provider"] == "europe_pmc"
    assert timing[1]["code"] == "unusable_fetch_material"
    assert timing[1]["provider_dispatched"] is True


def test_publication_relationship_leads_are_valid_read_targets():
    result_urls = []
    def fetch(url):
        result_urls.append(url)
        return FetchedMaterial(url, "Correction: the oxygen exposure lasted ten minutes.")

    model = Script(
        decision(requests=[scholarly_request()]), decision(requests=[request("read", target=NOTICE)]),
        decision("return", ["E2"]), answer("The notice states ten minutes. [E2]"),
    )
    result = ResearchSession(model=model, fetch=fetch, scholarly_search=find_article).ask("What changed in the notice?")
    assert result_urls == [NOTICE]
    assert result.citations[0].materials[0].publication is None
