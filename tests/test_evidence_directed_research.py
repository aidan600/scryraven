"""Source-bearing scripts exercise the ordinary loop and custody, not model judgment."""

from types import SimpleNamespace

import pytest
from test_research_first_resumable import packet, reply, results, scripted, stages, tool
from test_research_loop import Script, answer, decision, request

from core import exa_transport, linkup_transport
from core.transport import FetchedMaterial
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore


@pytest.fixture
def sources(monkeypatch):
    """Run both real Search adapters against synthetic responses at the HTTP seam."""
    exa, lexical, bodies, searches, reads = {}, {}, {}, [], []

    def respond(url, *, json, **_kwargs):
        searches.append((url, json))
        if url == exa_transport.EXA_SEARCH_URL:
            rows = exa[json["query"]]
        else:
            assert url == linkup_transport.LINKUP_SEARCH_URL
            rows = lexical[json["q"]]
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
            "results": rows, "answer": "Fixture-only generated response, never source material.",
        })

    def fetch(url):
        reads.append(url)
        return FetchedMaterial(url, bodies[url])

    monkeypatch.setenv("EXA_API_KEY", "synthetic-offline-key")
    monkeypatch.setenv("LINKUP_API_KEY", "synthetic-offline-key")
    monkeypatch.setattr(exa_transport, "post_provider_request", respond)
    monkeypatch.setattr(linkup_transport, "post_provider_request", respond)
    return SimpleNamespace(exa=exa, lexical=lexical, bodies=bodies,
                           searches=searches, reads=reads, fetch=fetch)


def publication(path, title, highlight=None):
    return {"url": f"https://example.test/{path}", "title": title,
            "highlights": [highlight] if highlight else []}


def originals(material):
    return {row["id"]: row["content"] for row in material["evidence"]}


def citations(result):
    return [(item.acquisition, item.content) for cite in result.citations for item in cite.materials]


def exa_dispatches(sources):
    return {body["query"]: (body["objective"], body["type"])
            for endpoint, body in sources.searches if endpoint == exa_transport.EXA_SEARCH_URL}


def test_poe_discovery_replaces_an_old_assumption_and_reads_the_discovered_original(sources):
    query = "Player-tested sources comparing profitable farms in Path of Exile 3.30."
    objective = "Discover applicable 3.30 options and compare returns at different investments."
    patch = "In this fixture, 3.30 replaced Scarabs with Threads. The 3.29 Scarab guide no longer applies."
    trials = ("In the fixture's 3.30 trials, low-investment Harvest averaged 3 units per hour. "
              "Higher-investment Blight averaged 5 units per hour under the same price snapshot.")
    report = publication("poe/trials", "Fixture player trials")
    sources.exa[query] = [publication("poe/patch", "Fixture patch notes", patch), report]
    sources.bodies[report["url"]] = trials
    initial = "Check whether the familiar 3.29 methods still apply; discover current alternatives."
    revised = "The 3.30 patch replaces Scarabs [E1]; the trial comparison remains to be read."
    final = "The Scarab method is out of scope [E1]; compare Harvest and Blight at their stated investments [E2]."

    def read_trials(material):
        assert material["research_briefing"] == initial
        assert originals(material) == {"E1": patch}
        assert report["url"] in {row["url"] for row in material["catalog"]["candidates"]}
        return decision(refs=["E1"], briefing=revised, requests=[request("read", target="C2")])

    def handoff(material):
        assert material["research_briefing"] == revised
        assert originals(material) == {"E1": patch, "E2": trials}
        return decision("return", ["E1", "E2"], briefing=final)

    def write(material):
        assert material["research_briefing"] == final
        assert originals(material) == {"E1": patch, "E2": trials}
        return answer("Scarabs were replaced. [E1] Harvest and Blight yielded 3 and 5 units per hour "
                      "respectively under the test conditions, with different investment levels. [E2]")

    model = Script(decision(briefing=initial, requests=[request(query=query, objective=objective)]),
                   read_trials, handoff, write)
    result = ResearchSession(model=model, fetch=sources.fetch).ask(
        "What are the most profitable ways to farm currency in Path of Exile 3.30?")
    assert exa_dispatches(sources) == {query: (objective, "lite")}
    assert sources.reads == [report["url"]]
    assert citations(result) == [("provider_highlights", patch), ("fetched_source", trials)]
    assert result.trace[-1]["budget"]["external_attempts"] == 2


def test_lawrence_precise_lookup_and_a_reopened_retained_source_followup(sources, tmp_path):
    query = "Horse counts in production accounts for Lawrence of Arabia (1962)."
    objective = "Establish what the production records counted and their filming scope."
    production = ("The fixture's production ledger records 750 horses supplied for the Almería shoot. "
                  "Other locations are outside this ledger.")
    scene = "In the fixture's scene report, the Aqaba sequence used 450 of the Almería horses."
    sources.exa[query] = [publication("lawrence/ledger", "Fixture production ledger", production),
                          publication("lawrence/scene", "Fixture scene report", scene)]

    def sufficient(material):
        assert originals(material) == {"E1": production, "E2": scene}
        return decision("return", ["E1"], briefing="The Almería count is documented; other locations are uncounted.")

    model = Script(decision(requests=[request(query=query, objective=objective)]), sufficient,
                   answer("The Almería shoot used 750 horses according to the ledger. [E1]",
                          "partial", missing="The all-location production total."))
    store = SQLiteSessionStore(tmp_path / "lawrence.sqlite3")
    session = ResearchSession.create(store=store, model=model, fetch=sources.fetch)
    first = session.ask("How many horses were used in filming Lawrence of Arabia (1962)?")
    assert first.posture == "partial"
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]

    def reuse(material):
        assert originals(material) == {"E1": production}
        assert material["research_briefing"] is None
        return decision(requests=[request("find", query="Aqaba")],
                        briefing="Find the scene count in the retained sources.")

    def found_scene(material):
        assert originals(material) == {"E2": scene}
        return decision("return", ["E2"], briefing="The Aqaba scene was a subset of the Almería total.")

    followup = Script(reuse, found_scene, answer("The scene report records 450 horses for the Aqaba scene. [E2]"))
    reopened = ResearchSession.open(session.session_id, store=store, model=followup, fetch=sources.fetch)
    second = reopened.ask("How many of those horses were in the Aqaba scene?")
    assert exa_dispatches(sources) == {query: (objective, "lite")}
    assert len(sources.searches) == 1 and not sources.reads
    assert second.trace[-1]["budget"]["external_attempts"] == 0
    assert [call[0] for call in followup.calls] == ["research", "research", "answer"]
    assert citations(first) == [("provider_highlights", production)]
    assert citations(second) == [("provider_highlights", scene)]
    assert reopened.turns[0] == session.turns[0]


def test_caterpillar_targets_opinion_and_statute_with_separate_custody(sources):
    case = "How did Caterpillar Inc. v. Lewis, 519 U.S. 61 (1996), apply 28 U.S.C. § 1447(c)?"
    statute = '"28 U.S.C." "1447(c)" remand'
    case_need = "Locate the Court's own treatment of the timing defect."
    statute_need = "Identify the operative removal and remand language."
    opinion = ("In this fixture opinion, the absence of diversity at removal was cured before judgment; "
               "the Court did not undo the final judgment.")
    provision = "Fixture statutory text requires remand if subject-matter jurisdiction is absent before final judgment."
    url = "https://example.test/caterpillar/statute"
    snippet = "Navigation lead; this snippet does not contain the operative provision."
    sources.exa[case] = [publication("caterpillar/opinion", "Fixture U.S. Reports opinion", opinion)]
    sources.lexical[statute] = [{"type": "text", "url": url, "name": "Fixture code index", "content": snippet}]
    sources.bodies[url] = provision

    def read_statute(material):
        assert originals(material) == {"E1": opinion}
        assert any(row.get("context") == snippet for row in material["catalog"]["candidates"])
        assert material["acquisition_history"][1]["request"] == {"query": statute, "objective": statute_need}
        return decision(refs=["E1"], requests=[request("read", target="C2")],
                        briefing="The case is available; read the identified code page for the governing text.")

    def handoff(material):
        assert originals(material) == {"E1": opinion, "E2": provision}
        return decision("return", ["E1", "E2"], briefing="Preserve removal versus final judgment timing.")

    model = Script(decision(requests=[request(query=case, objective=case_need),
                                      request("search_lexical", query=statute, objective=statute_need)]),
                   read_statute, handoff,
                   answer("The provision applies before judgment. [E2] The Court left the judgment in place "
                          "because the defect had been cured by then. [E1]"))
    result = ResearchSession(model=model, fetch=sources.fetch).ask(case)
    assert exa_dispatches(sources) == {case: (case_need, "lite")}
    endpoint, body = sources.searches[1]
    assert endpoint == linkup_transport.LINKUP_SEARCH_URL
    assert (body["q"], body["depth"], body["outputType"]) == (statute, "fast", "searchResults")
    assert "objective" not in body and sources.reads == [url]
    assert citations(result) == [("fetched_source", provision), ("provider_highlights", opinion)]


def test_klamath_independent_initial_needs_lead_to_a_later_ecology_lookup(sources):
    removal = "2024 project records on completion of Klamath River dam removal."
    survey = "Klamath River restoration and salmon observations reported through 2025."
    telemetry = "Klamath River 2025 surveys distinguishing salmon transit from observed reproduction."
    removal_need = "Establish completed engineering work separately from ecological outcomes."
    survey_need = "Identify the ecological outcomes actually measured through 2025."
    telemetry_need = "Determine whether the sightings included evidence of reproduction."
    works = "The fixture engineering report records four removals completed in October 2024."
    sightings = "The fixture's 2025 survey reports upstream salmon sightings, without classifying reproduction."
    spawning = "The fixture's later 2025 survey confirmed spawning in monitored reaches; long-term recovery was unmeasured."
    sources.exa.update({removal: [publication("klamath/works", "Fixture completion report", works)],
                        survey: [publication("klamath/survey", "Fixture early survey", sightings)],
                        telemetry: [publication("klamath/spawning", "Fixture later survey", spawning)]})

    def investigate(material):
        assert originals(material) == {"E1": works, "E2": sightings}
        return decision(refs=["E1", "E2"], requests=[request(query=telemetry, objective=telemetry_need)],
                        briefing="Removal is established [E1], but sightings [E2] leave reproduction unresolved.")

    def finish(material):
        assert "reproduction unresolved" in material["research_briefing"]
        assert originals(material) == {"E1": works, "E2": sightings, "E3": spawning}
        return decision("return", ["E1", "E3"],
                        briefing="Removal and observed spawning are established; long-term recovery remains open.")

    model = Script(decision(requests=[request(query=removal, objective=removal_need),
                                      request(query=survey, objective=survey_need)]), investigate, finish,
                   answer("Four dams were removed in 2024. [E1] The 2025 survey found spawning in "
                          "monitored reaches, with long-term recovery still unmeasured. [E3]"))
    result = ResearchSession(model=model, fetch=sources.fetch).ask(
        "What was completed during the Klamath River dam-removal project in 2024, and what was known "
        "or still uncertain about restoration and salmon return through the end of 2025?")
    assert exa_dispatches(sources) == {removal: (removal_need, "lite"), survey: (survey_need, "auto"),
                                      telemetry: (telemetry_need, "auto")}
    assert not sources.reads
    assert citations(result) == [("provider_highlights", works), ("provider_highlights", spawning)]
    assert result.trace[-1]["budget"]["external_attempts"] == 3


def test_aircraft_cost_review_preserves_year_mile_and_denominator_limits(sources, monkeypatch):
    query = "Contemporaneous cost reports for the original Boeing 777-300 and MD-80 around 2000."
    objective = "Identify variant-specific costs and disclose the price year, mile unit and denominator."
    lead = "Fixture comparison highlights refer to the 2000 operating-cost study and its definitions."
    cost = ("Fixture study, year-2000 dollars: modeled MD-80 direct cost is 23.0156 cents per available-seat "
            "nautical mile. One nautical mile is 1.15078 statute miles in this table. The separate observed "
            "777-300ER figure is from 2020, includes overhead and uses available-seat statute miles. "
            "No original 777-300 cost or passenger load factor is listed.")
    source = publication("aircraft/study", "Fixture operating-cost study", lead)
    sources.exa[query] = [source]
    sources.bodies[source["url"]] = cost

    def after_read(payload):
        assert originals(packet(payload)) == {"E2": cost, "E1": lead}
        return reply(decision("return", ["E2"], briefing="Only the modeled MD-80 metric can be converted. "
                              "The later, different 777 variant and cost basis cannot serve as a comparator."))

    def after_calculation(payload):
        assert originals(packet(payload)) == {"E2": cost}
        assert results(payload)["miles"]["value"] == "20"
        return reply(answer("The modeled 2000 MD-80 direct cost is 20 cents per available-seat statute mile. [E2] "
                            "The later 777-300ER figure uses a different cost definition. [E2]", "partial",
                            missing="Comparable original 777-300 costs and the passenger-mile denominator."))

    model, payloads, _ = scripted(monkeypatch, [
        reply(decision(requests=[request(query=query, objective=objective)])),
        reply(decision(refs=["E1"], requests=[request("read", target="C1", mode="full")])),
        after_read,
        tool("calculate", {"expression": "23.0156 / 1.15078"}, "miles"),
        after_calculation,
    ])
    result = ResearchSession(model=model, fetch=sources.fetch).ask(
        "Compare the cost per passenger mile of an original Boeing 777-300 and an MD-80 in 2000 dollars.")
    assert stages(payloads) == ["research", "research", "research", "answer", "answer"]
    assert exa_dispatches(sources) == {query: (objective, "lite")}
    assert sources.reads == [source["url"]]
    assert result.posture == "partial" and citations(result) == [("fetched_source", cost)]
