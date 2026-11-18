"""Publication navigation and source text travel through the ordinary session."""

import json
from functools import partial

import pytest
from test_research_loop import Script, answer, decision, no_fetch, request
from test_scholarly_transport import JATS, Response

from core.scholarly_transport import (
    PublicationMetadata,
    PublicationRelation,
    ScholarlyCandidate,
    ScholarlyFullText,
    VenueStanding,
    fetch_scholarly,
    search_scholarly,
)
from core.transport import FetchedMaterial
from scryraven.acquisition import AcquisitionLibrary
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


@pytest.mark.parametrize("restore", [False, True], ids=["same-turn", "restored"])
def test_later_record_without_open_flag_preserves_verified_pmc_read_route(restore):
    confirmed, = find_article("")
    sparse = ScholarlyCandidate("https://doi.org/10.1234/oxygen", confirmed.title, ABSTRACT,
                                PublicationMetadata(doi="10.1234/oxygen", pmcid="PMC12345"))
    records = iter([confirmed, sparse])
    licensed = JATS.replace(b"PMC100001", b"PMC12345")
    responses = iter([licensed.replace(b"/by/", b"/by-nc/"), licensed])
    fetch_article = partial(fetch_scholarly, get=lambda _url, **_kwargs: Response(next(responses)))
    library = AcquisitionLibrary(scholarly_search=lambda _query: [next(records)],
                                 scholarly_fetch=fetch_article, fetch=no_fetch)
    for _ in range(2):
        assert library.execute(scholarly_request(), before_external=lambda: None)["status"] == "ok"
    abstracts = tuple(library.acquisitions)
    assert [item.publication.open_article_available for item in abstracts] == [True, False]
    if restore:
        library = AcquisitionLibrary(abstracts, scholarly_fetch=fetch_article, fetch=no_fetch)

    landing, = [row for row in library.catalog()["candidates"] if row["url"] == PMC]
    assert landing.get("open_article_available") is True
    read = request("read", target=landing["id"], mode="full")
    rejected = library.execute(read, before_external=lambda: None)
    assert rejected["code"] == "europe_pmc_license_unavailable"
    assert tuple(library.acquisitions) == abstracts
    accepted = library.execute(read, before_external=lambda: None)
    assert accepted["provider"] == "europe_pmc" and accepted["status"] == "ok"
    material_id, = accepted["material_ids"]
    article = library.materials[material_id]
    assert (article.url, article.open_article_license) == (PMC, LICENSE)
    assert "Sixty cultures" in article.content


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


def test_reopened_scholarly_record_can_recover_a_cookie_blocked_original(tmp_path):
    doi = "10.1234/oxygen"
    publisher = f"https://doi.org/{doi}"
    queries = []
    reads = []

    def get_record(url, *, params, **options):
        queries.append(params["query"])
        row = {"doi": doi, "pmcid": "PMC12345", "pmid": "40585390", "source": "MED",
               "title": "A recovery experiment", "abstractText": ABSTRACT}
        return Response(json.dumps({"resultList": {"result": [row]}}).encode())

    database = tmp_path / "recovery.sqlite3"
    first = ResearchSession.create(
        store=SQLiteSessionStore(database), search=no_fetch, fetch=no_fetch,
        scholarly_search=partial(search_scholarly, get=get_record),
        model=Script(decision(requests=[{**scholarly_request(), "query": doi}]),
                     decision("return", ["E1"]), answer("The experiment measured recovery. [E1]")),
    )
    first.ask(f"What did the experiment identified by {doi} measure?")
    prior_turn, = first.turns
    prior_material, = prior_turn.citations[0].materials
    assert queries == [f'DOI:"{doi}"']
    assert (prior_material.url, prior_material.content, prior_material.acquisition) == (
        publisher, ABSTRACT, "publication_abstract")

    def fetch(url):
        reads.append(url)
        if url == publisher:
            return FetchedMaterial(url, "# Cookies must be enabled\n\n"
                                   "Enable cookies for doi.org and reload this page to continue.")
        assert url == PMC
        return FetchedMaterial(url, BODY)

    def read_alternate(packet):
        failed, = packet["acquisition_history"]
        assert failed["status"] == "error" and failed["code"] == "read_access_challenge"
        assert not failed["material_ids"]
        landings = {row["url"]: row["id"] for row in packet["catalog"]["candidates"]
                    if row.get("publication", {}).get("doi") == doi}
        assert {PMC, "https://pubmed.ncbi.nlm.nih.gov/40585390/"} <= landings.keys()
        return decision(requests=[request("read", target=landings[PMC], mode="full")])

    passage = "Thirty animals were randomly allocated."
    model = Script(decision(requests=[request("read", target="E1", mode="full")]),
                   read_alternate, decision("return", ["E2"]),
                   {**answer(f"{passage} [E2]"), "citation_passages": [
                       {"ref": "E2", "occurrence": 1, "text": passage}]})
    reopened = ResearchSession.open(first.session_id, store=SQLiteSessionStore(database), model=model,
                                    search=no_fetch, fetch=fetch, scholarly_search=no_fetch, scholarly_fetch=no_fetch)
    result = reopened.ask("How many animals did that study randomly allocate?")
    assert reads == [publisher, PMC]
    assert result.trace[-1]["budget"]["physical_acquisition_dispatches"] == 2
    saved = ResearchSession.open(first.session_id, store=SQLiteSessionStore(database))
    original, recovered = saved.turns
    assert original == prior_turn
    assert [item.content for item in saved.acquisitions] == [ABSTRACT, BODY]
    citation, = recovered.citations
    material, = citation.materials
    assert citation.url == material.url == PMC
    assert material.acquisition == "fetched_source" and material.open_article_license is None
    use, = recovered.citation_uses
    support, = use.support
    assert support_text(support, material) == passage


def test_venue_classification_is_year_specific_navigation_with_one_dispatch():
    url = "https://jfp.csc.fi/jufoportal_base/en/12345"
    venue = VenueStanding(issn="0340-5443", journal="The Experimental Journal", year=2025, level=2,
                          current_panels=(11,), current_subjects=("Ecology",), url=url)
    sent = []

    def lookup(issn, year):
        sent.append((issn, year))
        return venue

    model = Script(
        decision(requests=[{"kind": "lookup_venue", "issn": "0340-5443", "year": 2025}]),
        decision("return"),
        answer("I found a register entry but cannot establish the requested study result.", "unable"),
    )
    result = ResearchSession(model=model, fetch=no_fetch, search=no_fetch, venue_lookup=lookup).ask(
        "What does the study establish?",
    )
    packet = model.calls[1][2]
    receipt, = packet["acquisition_history"]
    assert receipt["venue_standing"] == venue.model_dump(mode="json")
    assert receipt["candidate_refs"] == ["C1"]
    assert packet["catalog"]["candidates"][0]["url"] == url
    assert packet["evidence"] == [] and not result.evidence and not result.citations
    assert sent == [("0340-5443", 2025)]
    assert result.trace[-1]["budget"]["physical_acquisition_dispatches"] == 1
