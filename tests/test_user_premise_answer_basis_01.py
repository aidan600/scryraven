"""Offline contract checks for user-stipulated Answer derivations."""

import json
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest
from test_research_loop import answer, decision, no_fetch, request, search

from core.exa_transport import DiscoveryCandidate
from scryraven.research import AnswerDecision, RunError, RunLimits, run
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore


class RecordingModel:
    """Capture each exact call packet before the correction loop changes it."""

    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def __call__(self, stage, prompt, packet, schema):
        self.calls.append((stage, prompt, deepcopy(packet), schema))
        output = next(self.outputs)
        return output if isinstance(output, str) else json.dumps(output)


def no_acquisition(*args, **kwargs):
    pytest.fail("Unexpected external acquisition")


def answers(model):
    return [call for call in model.calls if call[0] == "answer"]


@pytest.mark.parametrize(("question", "posture", "prose"), [
    (
        "Use an equal 80% passenger load factor for both aircraft and ignore belly cargo revenue. "
        "Does that establish a real-world advantage or only an illustrative scenario?",
        "supported",
        "Under your equal-load and no-cargo assumptions, this is only an illustrative "
        "scenario; those inputs alone establish no real-world cost advantage.",
    ),
    (
        "Assume 60 million Btu useful heat, 90% AFUE, $1.20 per therm, $0.18 per kWh, "
        "and seasonal COP 2.5. What are the operating costs, excluding capital and emissions?",
        "partial",
        "Under your assumptions, gas costs about $800 and the heat pump about $1,266 "
        "per year. This does not establish emissions or capital costs.",
    ),
])
def test_empty_evidence_user_premises_answer_keeps_inputs_non_evidentiary(question, posture, prose):
    model = RecordingModel(decision("answer"),
                           answer(prose, posture, support_basis="user_premises"))

    result = run(question, model=model, search=no_acquisition, fetch=no_acquisition)

    assert [call[0] for call in model.calls] == ["research", "answer"]
    assert answers(model)[0][2]["question"] == question
    assert answers(model)[0][2]["evidence"] == []
    assert result.posture == posture and result.answer == prose
    assert result.evidence == result.selected_evidence == result.citations == result.citation_uses == ()
    accepted = [event for event in result.trace if event["action"] == "answer_decision"]
    assert len(accepted) == 1 and accepted[0]["decision"]["support_basis"] == "user_premises"
    assert result.trace[-1]["budget"]["external_attempts"] == 0


def test_answer_decision_requires_explicit_basis():
    with pytest.raises(ValueError):
        AnswerDecision.model_validate(answer("Unable.", "unable") | {"support_basis": None})


def test_evidence_basis_with_citation_keeps_ordinary_selection_and_no_extra_call():
    model = RecordingModel(
        decision(), decision("answer", ["E1"]),
        answer("The publication states seven. [E1]", support_basis="evidence"),
    )

    result = run("What value does the publication state?", model=model,
                 search=search, fetch=no_fetch)

    assert len(answers(model)) == 1
    assert result.posture == "supported" and result.answer == "The publication states seven. [1]"
    assert len(result.citations) == 1 and result.selected_evidence == result.citations[0].materials
    assert result.trace[-1]["budget"]["semantic_attempts"] == 3


def test_evidence_basis_omission_retains_same_contract_correction():
    model = RecordingModel(
        decision(), decision("answer", ["E1"]),
        answer("REJECTED PROSE with no citation.", support_basis="evidence"),
        answer("The publication states seven. [E1]", support_basis="evidence"),
    )

    result = run("What value does the publication state?", model=model,
                 search=search, fetch=no_fetch)

    first, second = answers(model)
    assert first[1] == second[1] and first[3] == second[3]
    assert first[2]["question"] == second[2]["question"]
    assert first[2]["evidence"] == second[2]["evidence"]
    assert second[2]["output_correction"]["code"] == "missing_citation"
    assert "REJECTED PROSE" not in json.dumps(second[2])
    assert len(answers(model)) == 2
    assert result.answer == "The publication states seven. [1]"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4


def test_user_premises_basis_with_evidence_is_rejected_under_same_answer_contract():
    rejected = answer("REJECTED PROSE claims the source agrees.", support_basis="user_premises")
    model = RecordingModel(
        decision(), decision("answer", ["E1"]), rejected,
        answer("The publication states seven. [E1]", support_basis="evidence"),
    )

    result = run("What value does the publication state?", model=model,
                 search=search, fetch=no_fetch)

    first, second = answers(model)
    assert first[1] == second[1] and first[3] == second[3]
    assert first[2]["question"] == second[2]["question"]
    assert first[2]["evidence"] == second[2]["evidence"]
    assert second[2]["output_correction"]["code"] == "basis_user_premises_has_evidence"
    assert "REJECTED PROSE" not in json.dumps(second[2])
    assert result.answer == "The publication states seven. [1]"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4


def test_user_premises_basis_requires_empty_source_readings():
    invalid = answer("Under your assumptions, the arithmetic is conditional.",
                     support_basis="user_premises")
    invalid["source_readings"] = [{"evidence_ref": "E1", "passages": ["Imaginary passage"]}]
    model = RecordingModel(
        decision("answer"), invalid,
        answer("Under your assumptions, the arithmetic is conditional.",
               support_basis="user_premises"),
    )

    result = run("Assume one plus one equals two for this scenario.", model=model,
                 search=no_acquisition, fetch=no_acquisition)

    assert len(answers(model)) == 2
    assert answers(model)[1][2]["output_correction"]["code"] == "basis_user_premises_has_readings"
    assert result.posture == "supported" and result.selected_evidence == ()


def test_user_premises_basis_cannot_emit_a_fabricated_evidence_alias():
    model = RecordingModel(
        decision("answer"),
        answer("Scenario calculation. [E1]", support_basis="user_premises"),
    )

    with pytest.raises(RunError) as caught:
        run("Assume one plus one equals two for this scenario.", model=model,
            search=no_acquisition, fetch=no_acquisition)

    assert caught.value.stage == "citations"
    assert caught.value.code == "invalid_citation_reference"


def test_none_basis_rejects_supported_memory_answer_then_allows_unable():
    question = "What is the maximum allowed weight of a ten-pin bowling ball?"
    model = RecordingModel(
        decision("answer"),
        answer("An unsupported factual claim from memory.", support_basis="none"),
        answer("I need an applicable rules source to establish that limit.",
               "unable", support_basis="none"),
    )

    result = run(question, model=model, search=no_acquisition, fetch=no_acquisition)

    assert len(answers(model)) == 2
    assert answers(model)[1][2]["output_correction"]["code"] == "basis_none_requires_unable"
    assert answers(model)[1][2]["question"] == question
    assert answers(model)[1][2]["evidence"] == []
    assert result.posture == "unable" and result.citations == ()
    assert result.trace[-1]["budget"]["semantic_attempts"] == 3


def test_evidence_basis_without_packet_cannot_finalize_external_fact():
    model = RecordingModel(decision("answer"),
                           answer("A purported factual answer.", support_basis="evidence"),
                           answer("I need an applicable source to establish this.",
                                  "unable", support_basis="none"))

    result = run("What is the maximum allowed weight of a ten-pin bowling ball?",
                 model=model, search=no_acquisition, fetch=no_acquisition)

    assert len(answers(model)) == 2
    assert answers(model)[1][2]["output_correction"]["code"] == "basis_evidence_missing_packet"
    assert result.posture == "unable" and result.selected_evidence == result.citations == ()


def test_basis_correction_stays_within_existing_semantic_limit():
    model = RecordingModel(
        decision("answer"),
        answer("Unsupported.", support_basis="none"),
        answer("Still unsupported.", support_basis="none"),
    )

    result = run("What is an external fact?", model=model,
                 search=no_acquisition, fetch=no_acquisition,
                 limits=RunLimits(semantic_attempts=3))

    assert len(answers(model)) == 2
    assert result.posture == "unable" and result.stop_reason == "not_established"
    assert result.answer == "I couldn't complete a source-validated answer for this request."
    assert result.trace[-1]["budget"]["semantic_attempts"] == 3
    assert len([event for event in result.trace
                if event.get("code") == "basis_none_requires_unable"]) == 2


def test_terminal_bound_does_not_promote_inconsistent_supported_answer():
    model = RecordingModel(
        decision(),
        answer("Under your stipulated values, the gas cost is $800/year; the external "
               "emissions comparison remains unknown.",
               "supported", missing="What are the applicable emissions factors?",
               support_basis="user_premises"),
    )

    result = run("Assume 60 million Btu useful heat, 90% AFUE, and $1.20/therm.",
                 model=model, search=lambda query: [], fetch=no_acquisition,
                 limits=RunLimits(semantic_attempts=2))

    assert [call[0] for call in model.calls] == ["research", "answer"]
    assert result.posture == "unable" and result.stop_reason == "not_established"
    assert result.answer == "I couldn't complete a source-validated answer for this request."
    assert result.selected_evidence == result.citations == ()
    assert any(event.get("code") == "supported_with_missing_information"
               for event in result.trace)


def test_user_premises_followup_reopen_uses_prior_user_question_without_evidence():
    with tempfile.TemporaryDirectory(prefix="scryraven-premise-session-") as directory:
        _exercise_premise_followup_reopen(Path(directory))


def _exercise_premise_followup_reopen(directory):
    first_question = (
        "For a scenario, take 60 million Btu useful heat, furnace AFUE 90%, gas $1.20/therm, "
        "electricity $0.18/kWh, and seasonal COP 2.5. Exclude capital and emissions."
    )
    followup_question = "Electricity is $0.10/kWh; everything else stays the same."
    first_answer = (
        "Under your stipulated inputs, gas costs $800/year and the heat pump about "
        "$1,266/year; these are conditional operating costs."
    )
    second_answer = (
        "With your new $0.10/kWh price and prior user-stipulated inputs, the heat pump "
        "costs about $703/year versus gas at $800/year. This alone does not settle emissions."
    )
    store = SQLiteSessionStore(directory / "sessions.sqlite3")
    first_model = RecordingModel(
        decision("answer"), answer(first_answer, support_basis="user_premises"),
    )
    session = ResearchSession.create(store=store, model=first_model,
                                     search=no_acquisition, fetch=no_acquisition)
    first = session.ask(first_question)
    session_id = session.session_id
    assert first.evidence == first.selected_evidence == first.citations == ()
    del session

    second_model = RecordingModel(
        decision("answer"), answer(second_answer, support_basis="user_premises"),
    )
    reopened = ResearchSession.open(session_id, store=SQLiteSessionStore(store.path),
                                    model=second_model,
                                    search=no_acquisition, fetch=no_acquisition)
    second = reopened.ask(followup_question)

    assert second.posture == "supported" and second.answer == second_answer
    assert second.evidence == second.selected_evidence == second.citations == ()
    for call in second_model.calls:
        packet = call[2]
        prior = {"question": first_question, "answer": first_answer}
        if call[0] == "research":
            prior["provenance"] = {"posture": first.posture,
                                   "stop_reason": first.stop_reason, "citations": []}
        assert packet["conversation_context"] == [prior]
        assert packet["question"] == followup_question and packet["evidence"] == []
        assert "working_understanding" not in packet or call[0] == "research"
    assert "prior assistant" in answers(second_model)[0][1].lower()
    restored = ResearchSession.open(session_id, store=SQLiteSessionStore(store.path))
    assert restored.metadata.revision == 2
    assert [turn.question for turn in restored.turns] == [first_question, followup_question]
    assert restored.acquisitions == ()
    assert all(turn.selected_evidence == () and turn.citations == () for turn in restored.turns)


def test_mixed_user_assumptions_and_external_fact_keep_evidence_basis_and_citation():
    question = "Assume ten units of demand. What follows given the documented seven-unit supply?"
    source_text = "The documented supply is seven units."
    model = RecordingModel(
        decision(), decision("answer", ["E1"]),
        answer("Under your ten-unit demand assumption, the documented seven-unit "
               "supply leaves a three-unit shortfall. [E1]", support_basis="evidence",
               readings=[{"evidence_ref": "E1", "passages": [source_text]}]),
    )

    result = run(question, model=model,
                 search=lambda query: [DiscoveryCandidate("Supply record", "https://example.org/supply",
                                                          source_text, context_kind="provider_highlights")],
                 fetch=no_fetch)

    assert result.posture == "supported"
    assert len(result.citations) == 1 and result.citations[0].materials == result.selected_evidence
    assert "three-unit shortfall. [1]" in result.answer
    assert answers(model)[0][2]["question"] == question
    assert answers(model)[0][2]["evidence"][0]["content"] == source_text


BATTERY_QUESTION = (
    "I'm thinking out loud about a backup battery and I keep changing what I care about. "
    "Don't treat this as a claim about any actual product; for this scenario just assume "
    "13.5 kWh is available to the loads, average demand is 500 W, there's no charging "
    "during the outage and ignore reserve. I'm mostly trying to figure out whether that "
    "gets through a three-day outage, because my intuition says maybe it does."
)
BATTERY_FOLLOWUP = "Actually, make the load 150 W. Everything else I was rambling about stays the same."


def test_narrative_battery_followup_selectively_changes_current_user_load():
    first_answer = (
        "Under your assumed 13.5 kWh available capacity, constant 500 W load, no "
        "charging and no reserve, runtime is 27 hours, short of a three-day outage. "
        "This is an illustrative scenario, not a claim about a product."
    )
    second_answer = (
        "With your revised 150 W load and the same user-stipulated 13.5 kWh capacity, "
        "no charging and no reserve, runtime is 90 hours, beyond three days. This "
        "remains a scenario, not an actual-product result."
    )
    model = RecordingModel(
        decision("answer"), answer(first_answer, support_basis="user_premises"),
        decision("answer"), answer(second_answer, support_basis="user_premises"),
    )
    session = ResearchSession(model=model, search=no_acquisition, fetch=no_acquisition)

    first = session.ask(BATTERY_QUESTION)
    second = session.ask(BATTERY_FOLLOWUP)

    assert [call[0] for call in model.calls] == ["research", "answer", "research", "answer"]
    assert first.answer == first_answer and second.answer == second_answer
    assert first.posture == second.posture == "supported"
    assert first.citations == second.citations == ()
    assert first.selected_evidence == second.selected_evidence == session.acquisitions == ()
    for stage, prompt, packet, _schema in model.calls[2:]:
        assert packet["question"] == BATTERY_FOLLOWUP
        prior = {"question": BATTERY_QUESTION, "answer": first_answer}
        if stage == "research":
            prior["provenance"] = {"posture": first.posture,
                                   "stop_reason": first.stop_reason, "citations": []}
        assert packet["conversation_context"] == [prior]
        assert packet["evidence"] == []
        assert "assistant" in prompt.lower() and "factual authority" in prompt.lower()
        if stage == "research":
            assert packet["working_understanding"] is None
    assert [turn.question for turn in session.turns] == [BATTERY_QUESTION, BATTERY_FOLLOWUP]


def test_user_assertion_about_aircraft_cost_routes_to_acquisition_under_research_decision():
    question = (
        "I've always thought an MD-80 costs about twice as much per passenger-mile "
        "as a 777. My dad would probably say that's a garbage comparison. "
        "Is that actually defensible?"
    )
    source_text = (
        "Comparing passenger-mile costs requires a consistent operating-cost basis, "
        "seat configuration, passenger load factor, and route distance."
    )
    route = request(query="MD-80 777 passenger-mile operating costs matched comparison")
    route["focus"] = "Find a comparable cost basis and configuration."
    final = answer(
        "The acquired excerpt says passenger-mile comparisons depend on cost basis, "
        "seating, load factor and route distance [E1]. It does not itself establish "
        "that the MD-80 is twice as costly as a 777.",
        "partial", support_basis="evidence",
    )
    final["source_readings"] = [{"evidence_ref": "E1", "passages": [source_text]}]
    model = RecordingModel(
        decision(requests=[route]), decision("answer", ["E1"]), final,
    )
    searches = []

    def synthetic_search(query):
        searches.append(query)
        return [DiscoveryCandidate("Comparison conditions", "https://example.org/compare",
                                   source_text, context_kind="provider_highlights")]

    result = run(question, model=model, search=synthetic_search, fetch=no_acquisition)

    assert searches == [route["query"]]
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert model.calls[0][2]["question"] == question
    assert model.calls[0][2]["evidence"] == []
    assert model.calls[0][2]["working_understanding"] is None
    assert result.posture == "partial" and len(result.citations) == 1
    assert result.selected_evidence == result.citations[0].materials
    assert answers(model)[0][2]["evidence"][0]["content"] == source_text
    assert "twice as costly" in result.answer


def test_prior_assistant_scenario_answer_does_not_verify_actual_product_capacity():
    first_answer = "Under your scenario inputs, 13.5 kWh at 500 W lasts 27 hours."
    second_question = "Does an actual product have 13.5 kWh available to loads?"
    route = request(query="actual product available battery capacity specification")
    model = RecordingModel(
        decision("answer"), answer(first_answer, support_basis="user_premises"),
        decision(requests=[route]), decision("answer"),
        answer("The scenario and empty search result do not verify an actual product's "
               "available capacity.", "unable", support_basis="none"),
    )
    searches = []

    def empty_search(query):
        searches.append(query)
        return []

    session = ResearchSession(model=model, search=empty_search, fetch=no_acquisition)
    first = session.ask(BATTERY_QUESTION)
    second = session.ask(second_question)

    assert searches == [route["query"]]
    assert [call[0] for call in model.calls] == ["research", "answer", "research", "research", "answer"]
    assert second.posture == "unable" and second.citations == second.selected_evidence == ()
    assert second.trace[-1]["budget"]["external_attempts"] == 1
    for call in model.calls[2:]:
        prior = {"question": BATTERY_QUESTION, "answer": first_answer}
        if call[0] == "research":
            prior["provenance"] = {"posture": first.posture,
                                   "stop_reason": first.stop_reason, "citations": []}
        assert call[2]["conversation_context"] == [prior]
        assert call[2]["evidence"] == []
