"""Synthetic scope states protect the interface/instructions, not model judgment."""

import json

import pytest
from test_v2 import Script, answer, decision, no_fetch, request, search

from core.exa_transport import DiscoveryCandidate
from scryraven.v2 import ANSWER_PROMPT, RESEARCH_PROMPT, ResearchDecision, run


def finding(statement, *refs):
    return {"statement": statement, "evidence_refs": list(refs)}


@pytest.mark.parametrize(("question", "sources", "observed", "inferred", "text"), [
    (
        "What is the official value?",
        ["The official value is seven."],
        [finding("The authority states that the value is seven.", "E1")], [],
        "The official value is seven. [E1]",
    ),
    (
        "May a visitor enter after closing?",
        ["Visitors must leave at closing unless accompanied by authorized staff."],
        [finding("The rule requires visitors to leave at closing, except with authorized staff.", "E1")],
        [finding("A visitor may remain after closing when accompanied by authorized staff.", "E1")],
        "Only when accompanied by authorized staff. [E1]",
    ),
    (
        "Can this object's modification time distinguish its two versions?",
        ["The two object versions were written within the same second.",
         "This object's modification timestamp has one-second resolution."],
        [finding("The versions were written within one second.", "E1"),
         finding("This timestamp records only whole seconds.", "E2")],
        [finding("This timestamp alone cannot distinguish these two versions.", "E1", "E2")],
        "These versions share the timestamp's one-second interval, so it cannot distinguish them. [E1][E2]",
    ),
], ids=["direct-fact", "qualified-rule", "technical-synthesis"])
def test_requested_scope_states_need_no_extra_inference_cycle(question, sources, observed, inferred, text):
    proposal = decision("answer", [f"E{i}" for i in range(1, len(sources) + 1)])
    proposal["understanding"].update(observed=observed, inferred=inferred)
    model = Script(decision(), proposal, answer(text))
    result = run(question, model=model, fetch=no_fetch, search=lambda query: [
        DiscoveryCandidate("Public source", f"https://example.org/{i}", content,
                           context_kind="provider_highlights")
        for i, content in enumerate(sources, 1)
    ])
    assert result.posture == "supported"
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert result.trace[-1]["budget"]["external_attempts"] == 1
    recorded = [e["decision"] for e in result.trace if e["action"] == "research_decision"][-1]
    assert recorded == proposal
    assert len(result.citations) == len(sources)


def reception_state():
    return dict(
        interpretation="Characterize update reception during its first month.",
        observed=[finding("One day-two forum post praises the campaign and criticizes progression.", "E1"),
                  finding("One journalist calls the update a success and reports high launch activity.", "E2")],
        inferred=[finding("The reviewed material includes campaign praise and progression criticism.", "E1", "E2")],
        still_needed=["Evidence connecting these selected early observations to overall first-month reception."],
        last_route_result="Selected early reactions and secondary characterization only.",
    )


def reception_search(query):
    return [
        DiscoveryCandidate("Forum", "https://example.org/forum",
                           "Day two: I enjoyed the campaign but disliked progression.", context_kind="provider_highlights"),
        DiscoveryCandidate("Article", "https://example.org/article",
                           "The reviewer calls the update a success. Launch activity was high.", context_kind="provider_highlights"),
    ]


def test_missing_bridge_can_constrain_a_narrowed_answer_without_crossing_fresh_boundary():
    proposal = decision("answer", ["E1", "E2"])
    proposal.update(understanding=reception_state(), answer_scope="narrowed",
                    scope_limit="Selected early observations only; overall first-month reception is unestablished.")
    model = Script(decision(), proposal, answer(
        "The supplied day-two post praises the campaign and criticizes progression. [E1] "
        "The article's success judgment is the reviewer's view. [E2] "
        "Overall first-month player sentiment is not established.", "partial"))
    result = run("How was the update received in its first month?", model=model,
                 search=reception_search, fetch=no_fetch)
    assert result.posture == "partial"
    assert len(model.calls) == 3
    packet = model.calls[-1][2]
    # Only actual source material crosses, not even a proposed scope to preserve.
    assert set(packet) == {"question", "current_date", "conversation_context", "phase",
                           "evidence", "acquisition_limitations", "budget"}
    assert "first-month reception is unestablished" not in json.dumps(packet)
    assert [e["content"] for e in packet["evidence"]] == [c.context for c in reception_search("")]
    assert "Overall first-month player sentiment is not established." in result.answer


def test_missing_bridge_can_choose_an_ordinary_route_and_revise_the_small_state():
    route = decision(refs=["E1", "E2"], requests=[request(query="dated later-month player feedback")])
    route["understanding"] = reception_state()
    proposal = decision("answer", ["E1", "E2"])
    proposal.update(understanding=reception_state(), answer_scope="narrowed",
                    scope_limit="Reviewed early observations only.")
    model = Script(decision(), route, proposal, answer("One early post gives mixed feedback. [E1]", "partial"))
    queries = []

    def acquire(query):
        queries.append(query)
        return reception_search(query) if len(queries) == 1 else []

    run("How was the update received?", model=model, search=acquire, fetch=no_fetch)
    assert queries == ["public fact", "dated later-month player feedback"]
    assert model.calls[2][2]["working_understanding"] == reception_state()
    assert [call[0] for call in model.calls] == ["research", "research", "research", "answer"]


@pytest.mark.parametrize("field", ["observed", "inferred"])
def test_both_state_lists_require_actually_exposed_references(field):
    invalid = decision("answer", ["E1"])
    invalid["understanding"][field] = [finding("A proposition with unsupplied support.", "E99")]
    model = Script(decision(), invalid, decision("answer", ["E1"]), answer())
    run("Value?", model=model, search=search, fetch=no_fetch)
    assert model.calls[2][2]["output_correction"]["issues"]["unexposed_finding_refs"] == ["E99"]
    assert model.calls[2][2]["working_understanding"][field] == []


@pytest.mark.parametrize(("action", "scope", "limit"), [
    ("answer", None, None),
    ("answer", "requested", "A narrower period"),
    ("answer", "narrowed", None),
    ("answer", "narrowed", "   "),
    ("research", "requested", None),
    ("research", None, "A narrower period"),
])
def test_incoherent_scope_declaration_is_corrected_without_executing_it(action, scope, limit):
    invalid = decision(action, ["E1"])
    invalid.update(answer_scope=scope, scope_limit=limit)
    model = Script(decision(), invalid, decision("answer", ["E1"]), answer())
    result = run("Value?", model=model, search=search, fetch=no_fetch)
    assert model.calls[2][2]["output_correction"]["issues"]["answer_scope_shape"] is True
    assert result.trace[-1]["budget"]["external_attempts"] == 1


def test_experimental_established_schema_is_removed_without_an_adapter():
    obsolete = decision("answer")
    obsolete["understanding"]["established"] = obsolete["understanding"].pop("observed")
    obsolete["understanding"].pop("inferred")
    with pytest.raises(ValueError):
        ResearchDecision.model_validate(obsolete)


def test_scope_instructions_require_acquisition_or_narrowing_and_allow_legitimate_inference():
    # These checks protect instructions sent to the model. They do not pretend
    # Python can determine whether a population inference is justified.
    research = " ".join(RESEARCH_PROMPT.split())
    final = " ".join(ANSWER_PROMPT.split())
    assert "either obtain it when consequential and reasonably obtainable, OR abandon that inference" in research
    assert "Do not retain the broader inference as justified" in research
    assert "Remove any unsupported broader inference from inferred" in research
    assert "preserve the missing premise in still_needed" in research
    assert "An inferred item alone is not a reason to demand another source" in research
    assert "one or two observed items and no inferred items may suffice" in research
    assert "do not assert the broader conclusion and then append a caveat" in final
    assert "no source has to state the whole synthesis verbatim" in final
    assert "claim change or improvement without a meaningful comparison basis" in final
    assert "treat absent later evidence as evidence of no later change" in final
    assert "partial when useful parts or a narrower scope are supported" in final

