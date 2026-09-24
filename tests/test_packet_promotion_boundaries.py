"""Offline custody checks for a source-directed Research dependency."""

import pytest
from test_research_loop import Script, answer, decision, request

from core.exa_transport import DiscoveryCandidate
from scryraven.research import run


def test_identity_evidence_can_redirect_research_without_becoming_answer_authority():
    identity = "NASA and GE modified a GE Passport engine for the hybrid-electric demonstration."
    aircraft = "The demonstration aircraft uses CT7-9B turboprops."
    range_text = "The GE Passport takeoff-thrust range is 17,325–18,920 lb."
    first = decision(requests=[request(query="hybrid demonstration base engine")])
    redirect = decision(
        refs=["E1"],
        requests=[request(query="GE Passport takeoff-thrust range")],
        interpretation="The modified base engine is Passport, not the aircraft engine.",
    )
    redirect["understanding"]["established"] = [
        {"statement": "The modified base engine is GE Passport.", "evidence_refs": ["E1"]},
    ]
    redirect["understanding"]["still_needed"] = ["What range does GE give for Passport?"]
    redirect["understanding"]["last_route_result"] = "E1 identifies Passport."
    finish = decision("answer", ["E1", "E3"], interpretation="The range is established by E3.")
    model = Script(
        first,
        redirect,
        finish,
        answer(
            "NASA and GE modified the GE Passport. [E1] GE lists 17,325–18,920 lb. [E3]",
            readings=[
                {"evidence_ref": "E1", "passages": [identity]},
                {"evidence_ref": "E3", "passages": [range_text]},
            ],
        ),
    )
    queries = []

    def search(query):
        queries.append(query)
        if query == "hybrid demonstration base engine":
            return [
                DiscoveryCandidate("Modified engine", "https://example.test/identity", identity,
                                   context_kind="provider_highlights"),
                DiscoveryCandidate("Aircraft engine", "https://example.test/aircraft", aircraft,
                                   context_kind="provider_highlights"),
            ]
        if query == "GE Passport takeoff-thrust range":
            return [
                DiscoveryCandidate("Passport rating", "https://example.test/rating", range_text,
                                   context_kind="provider_highlights"),
            ]
        pytest.fail(f"Unexpected search: {query}")

    result = run(
        "What takeoff-thrust range does GE publish for the modified base engine?",
        model=model,
        search=search,
        fetch=lambda url: pytest.fail(f"Unexpected external Read: {url}"),
        context={"conversation_context": [
            {"question": "Earlier question", "answer": "I guessed the aircraft engine was CT7."},
        ]},
    )

    assert queries == ["hybrid demonstration base engine", "GE Passport takeoff-thrust range"]
    assert [call[0] for call in model.calls] == ["research", "research", "research", "answer"]
    assert {item["id"] for item in model.calls[1][2]["evidence"]} == {"E1", "E2"}
    assert model.calls[2][2]["working_understanding"] == redirect["understanding"]
    answer_packet = model.calls[-1][2]
    assert [item["id"] for item in answer_packet["evidence"]] == ["E1", "E3"]
    assert not {"working_understanding", "established", "still_needed"} & answer_packet.keys()
    assert "CT7" in answer_packet["conversation_context"][0]["answer"]
    assert all("CT7" not in item["content"] for item in answer_packet["evidence"])
    assert [item.id for item in result.selected_evidence] == ["E1", "E3"]
    assert [item.id for item in result.evidence] == ["E1", "E2", "E3"]
    assert [citation.materials[0].id for citation in result.citations] == ["E1", "E3"]
    assert result.answer.endswith("[2]")
