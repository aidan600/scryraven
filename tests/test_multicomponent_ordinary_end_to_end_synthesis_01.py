"""PRODUCT-PATH-REGRESSION: ordinary Northstar synthesis reaches CLI output."""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import Any

import pytest

import core.ordinary_multicomponent_synthesis_runtime as multicomponent_runtime
import core.pipeline_orchestrator as orchestrator
from core.component_work_graph_v1 import COMPONENT_WORK_GRAPH_V1_STAGE
from core.cost_accounting import CostAccumulator
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
)
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_kernel import ActionType, RunKernel
from tests.fixtures.component_analyst_evidence_sets import (
    component_analyst_evidence_set_fixture,
)
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    HANDOFF_SUFFICIENCY,
    OfflineOrdinaryPipelineHarness,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)

NORTHSTAR_QUERY = """For the fictional Northstar Home-Energy Rebate:
- What is the base rebate amount?
- What is the application deadline?
- Who qualifies for the income-based bonus?
- Must bonus applicants use the paper application?
- Can ordinary applicants file online?

Then explain how bonus eligibility changes the filing route and what an
eligible applicant should do."""

NORTHSTAR_DIRECTIVE = (
    "Then explain how bonus eligibility changes the filing route and what an eligible applicant should do."
)

NUMBERED_NORTHSTAR_DIRECTIVE = (
    "Compare how bonus eligibility changes the filing route, calculate the "
    "difference between the values, and convert both values to USD."
)

NUMBERED_NORTHSTAR_QUERY = f"""For the fictional Northstar Home-Energy Rebate:
1. What is the base rebate?
2. What is the application closing date?
3. Who qualifies for the income-based bonus?
4. Must bonus applicants use the paper application?
5. Can ordinary applicants file online?
6. {NUMBERED_NORTHSTAR_DIRECTIVE}"""

IMPERATIVE_NORTHSTAR_DIRECTIVE = (
    "then explain how bonus eligibility changes the filing route and what an eligible applicant should do."
)

IMPERATIVE_NORTHSTAR_QUERY = f"""For the fictional Northstar Home-Energy Rebate:
Find the base rebate amount; determine the application deadline; identify who
qualifies for the income-based bonus; state whether bonus applicants must use
the paper application; report whether ordinary applicants can file online;
{IMPERATIVE_NORTHSTAR_DIRECTIVE}"""

NORTHSTAR_REPORT = """Northstar Home-Energy Rebate

The Northstar base rebate is $1,200. The Northstar application deadline is
October 31, 2027. The income bonus is available at or below $60,000. A
qualifying applicant seeking that bonus should file the paper application
because bonus claimants must use paper. Online filing is available only to
applicants who are not claiming the bonus."""


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class NorthstarHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path, *, query: str = NORTHSTAR_QUERY) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=query,
            core_topic="Northstar Home-Energy Rebate",
            primary_entity="Northstar",
            researcher_queries=(
                "Northstar base rebate amount",
                "Northstar application deadline",
                "Northstar income-based bonus qualification",
                "Northstar bonus applicant paper application",
                "Northstar ordinary applicant online filing",
            ),
            raw_author_response=NORTHSTAR_REPORT,
            read_content_by_url={
                "https://northstar.example/rule-101": ("The Northstar Home-Energy Rebate base rebate is $1,200."),
                "https://northstar.example/rule-102": ("Northstar applications are due October 31, 2027."),
                "https://northstar.example/rule-103": ("The Northstar income bonus is available at or below $60,000."),
                "https://northstar.example/rule-104": (
                    "Applicants claiming the Northstar income bonus must use the paper application."
                ),
                "https://northstar.example/rule-105": (
                    "Applicants not claiming the Northstar income bonus may file online."
                ),
            },
            logger_name="test_multicomponent_northstar",
        )
        self.role_input_packets: list[dict[str, Any]] = []

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt in ROLE_SYSTEM_PROMPTS.values():
            payload = json.loads(prompt)
            self.role_input_packets.append({"system_prompt": system_prompt, "input_packet": payload})
            self.model_calls.append(
                {
                    "system_prompt": system_prompt,
                    "stream": bool(kwargs.get("stream")),
                    "provider": kwargs.get("provider"),
                    "model": kwargs.get("model"),
                    "use_reasoning": kwargs.get("use_reasoning"),
                }
            )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
                question = str(payload.get("component_ref", {}).get("user_facing_question") or "").casefold()
                claim = self._component_claim(question)
                aliases = [
                    str(dict(member).get("local_evidence_alias") or "")
                    for member in (
                        dict(payload.get("component_evidence_set") or {}).get(
                            "members"
                        )
                        or ()
                    )
                    if str(dict(member).get("local_evidence_alias") or "")
                ]
                return json.dumps(
                    {
                        "case_posture": "supported",
                        "supporting_evidence_aliases": aliases[:1],
                        "claim_text": claim,
                        "evidence_analysis": (
                            "The exact bounded component evidence supports this claim."
                        ),
                        "self_audit": (
                            "The case does not extend beyond the supplied component evidence."
                        ),
                        "caveats": [],
                        "nonclaims": [],
                        "contradictions": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
                component_ids = self._component_ids(payload)
                return json.dumps(
                    {
                        "synthesis_proposals": [
                            {
                                "synthesis_key": "E",
                                "claim_text": (
                                    "Applicants who qualify for the income bonus and seek it "
                                    "must use the paper application."
                                ),
                                "relationship_type": "eligibility_and_filing_requirement",
                                "component_inputs": [
                                    component_ids["income"],
                                    component_ids["paper"],
                                ],
                                "synthesis_inputs": [],
                                "caveats": [],
                                "nonclaims": [],
                                "blockers": [],
                            },
                            {
                                "synthesis_key": "S",
                                "claim_text": (
                                    "A qualifying applicant seeking the bonus should "
                                    "file on paper; online filing is available only to "
                                    "applicants not claiming the bonus."
                                ),
                                "relationship_type": "conditional_filing_route",
                                "component_inputs": [component_ids["online"]],
                                "synthesis_inputs": ["E"],
                                "caveats": [],
                                "nonclaims": [],
                                "blockers": [],
                            },
                        ],
                        "self_audit": (
                            "The offline filing relationships stay within the exact "
                            "admitted component cases and retain their limitations."
                        ),
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SYNTHESIS_DPRIME]:
                return json.dumps(
                    {
                        "validation_status": "supported",
                        "reasons": ["All nominated upstream inputs are admitted."],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER]:
                return json.dumps(
                    {
                        "challenge_status": "passed",
                        "reasons": ["The full two-level filing case is coherent."],
                        "challenged_synthesis_keys": [],
                        "caveats": [],
                        "nonclaims": [],
                    }
                )
        return super().ask_model(prompt, system_prompt, **kwargs)

    @staticmethod
    def _component_claim(question: str) -> str:
        if "base rebate" in question:
            return "The Northstar base rebate is $1,200."
        if "deadline" in question or "application closing" in question:
            return "The Northstar application deadline is October 31, 2027."
        if "income" in question:
            return "The income bonus is available at or below $60,000."
        if "paper" in question:
            return "Applicants claiming the income bonus must use the paper application."
        if "online" in question:
            return "Applicants not claiming the income bonus may file online."
        raise AssertionError(f"unexpected Northstar component question: {question}")

    @staticmethod
    def _component_ids(payload: dict[str, Any]) -> dict[str, str]:
        found: dict[str, str] = {}
        for node in payload.get("component_nodes", []):
            question = str(node.get("component_question") or "").casefold()
            component_id = str(node["component_id"])
            if "income" in question:
                found["income"] = component_id
            if "paper" in question:
                found["paper"] = component_id
            if "online" in question:
                found["online"] = component_id
        assert set(found) == {"income", "paper", "online"}
        return found

    def build_search_passages(self) -> list[dict[str, Any]]:
        facts = (
            (
                101,
                "Northstar base rebate amount $1,200",
                "The Northstar Home-Energy Rebate base rebate is $1,200.",
                "official_current_rules",
                "Northstar base rebate amount",
            ),
            (
                102,
                "Northstar application deadline October 31 2027",
                "Northstar applications are due October 31, 2027.",
                "official_current_rules",
                '"Northstar Home-Energy Rebate" Northstar application deadline',
            ),
            (
                103,
                "Northstar income bonus threshold $60,000",
                "The Northstar income bonus is available at or below $60,000.",
                "official_current_rules",
                "Northstar income-based bonus qualification",
            ),
            (
                104,
                "Northstar bonus claimant paper application rule",
                "Applicants claiming the Northstar income bonus must use the paper application.",
                "official_current_rules",
                "Northstar bonus applicant paper application",
            ),
            (
                105,
                "Northstar non-bonus online filing rule",
                "Applicants not claiming the Northstar income bonus may file online.",
                "official_current_rules",
                "Northstar ordinary applicant online filing",
            ),
            (
                106,
                "Northstar program primary literature record",
                "The Northstar program record documents the rebate design.",
                "academic_primary_literature",
                "Northstar academic primary literature",
            ),
            (
                107,
                "Northstar primary legal program record",
                "The current Northstar primary legal record establishes the program.",
                "legal_or_regulatory_text",
                "Northstar legal primary source",
            ),
        )
        return [
            {
                "source_id": source_id,
                "title": title,
                "url": f"https://northstar.example/rule-{source_id}",
                "text": text,
                "score": 1.0 - (index * 0.01),
                "credibility": 4,
                "source_tier": ("primary" if source_id == 107 else "academic" if source_id == 106 else "official"),
                "source_class": source_class,
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
                "query_ref": query_ref,
                "_provider": "offline_fake_search",
            }
            for index, (source_id, title, text, source_class, query_ref) in enumerate(facts)
        ]


def _forbid_direct_semantic_producer(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("qualifying Northstar run must not execute the direct semantic producer")

    monkeypatch.setattr(
        multicomponent_runtime,
        "execute_ordinary_semantic_producer_handoff_from_scope",
        forbidden,
    )


def _role_call_count(harness: NorthstarHarness, role: str) -> int:
    system_prompt = ROLE_SYSTEM_PROMPTS[role]
    return sum(call.get("system_prompt") == system_prompt for call in harness.model_calls)


def _assert_northstar_product_state(
    *,
    captured: dict[str, Any],
    harness: NorthstarHarness,
    outcome: Any,
    expected_directive: str = NORTHSTAR_DIRECTIVE,
) -> None:
    kernel = captured["run_kernel"]
    graph = kernel.state.projections[COMPONENT_WORK_GRAPH_V1_STAGE]
    assert len(kernel.state.semantic_observation_admission_history) == 5
    assert len(kernel.state.component_coverage_history) == 5
    assert len(graph["component_nodes"]) == 5
    assert len(graph["synthesis_nodes"]) == 2
    assert graph["maximum_synthesis_depth"] == 2
    assert graph["scrutineer_required"] is True
    assert graph["scrutineer_status"] == "passed"
    assert graph["graph_status"] == "ready"
    assert graph["requested_synthesis_directive"] == expected_directive
    assert (
        kernel.state.initial_answer_contract["question_meaning_metadata"]["requested_synthesis_directive"]
        == expected_directive
    )
    assert [node["status"] for node in graph["synthesis_nodes"]] == [
        "admitted",
        "admitted",
    ]
    synthesis_input_ids = {ref["node_id"] for node in graph["synthesis_nodes"] for ref in node["input_node_refs"]}
    assert graph["component_nodes"][0]["node_id"] not in synthesis_input_ids
    assert graph["component_nodes"][1]["node_id"] not in synthesis_input_ids

    expected_role_counts = {
        ROLE_COMPONENT_ANALYST: 5,
        ROLE_CROSS_COMPONENT_ANALYST: 1,
        ROLE_SYNTHESIS_DPRIME: 2,
        ROLE_SCRUTINEER: 1,
    }
    assert {role: _role_call_count(harness, role) for role in expected_role_counts} == expected_role_counts
    assert graph["logical_accounting"] == {
        "component_analyst_evaluations": 5,
        "cross_component_analyst_evaluations": 1,
        "synthesis_dprime_evaluations": 2,
        "scrutineer_evaluations": 1,
    }
    assert graph["physical_call_accounting"] == {
        "component_analyst_calls": 5,
        "cross_component_analyst_calls": 1,
        "synthesis_dprime_calls": 2,
        "scrutineer_calls": 1,
    }

    actions = list(kernel.state.issued_actions.values())
    graph_structure_sequence = next(
        action.sequence
        for action in actions
        if action.action_type is ActionType.MULTICOMPONENT_GRAPH_REDUCE
        and action.inputs.get("operation") == "structure"
    )
    for component_node in graph["component_nodes"]:
        component_id = component_node["component_id"]
        analyst_sequence = next(
            action.sequence
            for action in actions
            if action.action_type is ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE
            and action.inputs.get("logical_evaluation_key") == component_id
        )
        admission_sequence = next(
            action.sequence
            for action in actions
            if action.action_type is ActionType.MULTICOMPONENT_COMPONENT_ADMISSION_REDUCE
            and action.inputs.get("component_id") == component_id
        )
        assert analyst_sequence < admission_sequence < graph_structure_sequence
        assert component_node["component_analyst_case_ref"]["role"] == ROLE_COMPONENT_ANALYST
        assert "dprime_validation_ref" not in component_node
    e_admission_sequence = next(
        action.sequence
        for action in actions
        if action.action_type is ActionType.MULTICOMPONENT_GRAPH_REDUCE
        and action.inputs.get("operation") == "synthesis_admission"
        and action.inputs.get("synthesis_key") == "E"
    )
    s_validation_sequence = next(
        action.sequence
        for action in actions
        if action.action_type is ActionType.MULTICOMPONENT_SYNTHESIS_DPRIME_EXECUTE
        and action.inputs.get("logical_evaluation_key") == "S"
    )
    graph_finalize_sequence = next(
        action.sequence
        for action in actions
        if action.action_type is ActionType.MULTICOMPONENT_GRAPH_REDUCE and action.inputs.get("operation") == "finalize"
    )
    sufficiency_sequence = next(
        action.sequence for action in actions if action.action_type is ActionType.SUFFICIENCY_JUDGMENT_DECIDE
    )
    packet_sequence = next(
        action.sequence for action in actions if action.action_type is ActionType.FINAL_ANSWER_PACKET_PREPARE
    )
    author_sequence = next(action.sequence for action in actions if action.action_type is ActionType.AUTHOR_EXECUTE)
    assert e_admission_sequence < s_validation_sequence
    assert graph_finalize_sequence < sufficiency_sequence < packet_sequence < author_sequence

    sufficiency = captured["sufficiency_projection"]
    packet = captured["packet_handoff"].packet
    payload = captured["packet_handoff"].author_payload
    assert sufficiency["final_answer_allowed"] is True
    assert sufficiency["multicomponent_graph_consumption"]["graph_digest"] == graph["graph_digest"]
    assert len(packet.direct_component_entries) == 5
    assert len(packet.admitted_synthesis_entries) == 2, json.dumps(
        {
            key: sufficiency.get(key)
            for key in (
                "decision",
                "final_answer_posture",
                "missing_required_obligations",
                "partial_obligations",
                "unresolved_conflicts",
                "source_bound_numeric_unknowns",
                "weak_or_thin_evidence",
                "readiness_reasons",
            )
        },
        sort_keys=True,
    )
    assert payload is not None
    assert "Approved admitted synthesis" in payload.prompt
    assert "A qualifying applicant seeking the bonus should file on paper" in payload.prompt
    assert captured["author_handoff_called"] is True
    legacy_role_prompts = {
        DEFAULT_SYSTEM["analyst"],
        DEFAULT_SYSTEM["synth_evaluator"],
        DEFAULT_SYSTEM["scrutineer"],
    }
    assert not any(call.get("system_prompt") in legacy_role_prompts for call in harness.model_calls)
    assert outcome.report == NORTHSTAR_REPORT
    normalized_report = " ".join(outcome.report.split())
    assert "$1,200" in normalized_report
    assert "October 31, 2027" in normalized_report
    assert "at or below $60,000" in normalized_report
    assert "file the paper application" in normalized_report
    assert "not claiming the bonus" in normalized_report
    assert harness.search_calls
    initial_search_queries = harness.search_calls[0]["queries"]
    query_plan_projection = kernel.state.projections["query_plan_admission"]
    admission = query_plan_projection["initial_query_admission"]
    assert initial_search_queries == admission["immediate_dispatch_queries"]
    assert len(initial_search_queries) == 5
    assert len(set(initial_search_queries)) == 5
    admitted_items = [
        item
        for item in query_plan_projection["query_plan_ref"]["items"]
        if item.get("status") == "finalized" and item.get("metadata", {}).get("accepted_component_ref")
    ]
    assert [item["authorized_query"] for item in admitted_items] == (initial_search_queries)
    assert query_plan_projection["small_global_initial_query_cap_applied"] is False
    assert query_plan_projection["post_result_followup_dispatched"] is False
    assert harness.forbidden_live_calls == []


def test_northstar_ordinary_pipeline_reaches_runoutcome_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_direct_semantic_producer(monkeypatch)
    harness = NorthstarHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    try:
        outcome = orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-07-10",
                session_id="northstar-session",
                run_id="northstar-run",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )
    except multicomponent_runtime.OrdinaryMulticomponentRuntimeError as exc:
        ledger = captured["semantic_run_kernel"].state.evidence_ledger.to_projection().to_dict()
        provider_jobs = captured["semantic_runtime_scope"].get(
            "provider_job_execution_handoff",
            {},
        )
        diagnostic = {
            "error": str(exc),
            "provider_jobs": [
                {
                    key: item.get(key)
                    for key in (
                        "component_id",
                        "provider_job_id",
                        "provider_job_kind",
                        "authorized_queries",
                        "dispatch_refs",
                    )
                }
                for item in provider_jobs.get("provider_job_execution_records", [])
            ],
            "source_requirements": [
                {
                    key: item.get(key)
                    for key in (
                        "requirement_id",
                        "requirement_kind",
                        "status",
                        "origin_ref",
                        "linked_candidate_ids",
                    )
                }
                for item in ledger.get("source_requirements") or ()
            ],
            "requirement_links": [
                {key: item.get(key) for key in ("requirement_id", "candidate_id", "status")}
                for item in ledger.get("requirement_links") or ()
            ],
            "custody_gaps": [
                {key: item.get(key) for key in ("requirement_id", "gap_type", "reason")}
                for item in ledger.get("custody_gaps") or ()
            ],
            "candidate_ids": [item.get("candidate_id") for item in ledger.get("candidate_records") or ()],
        }
        pytest.fail(json.dumps(diagnostic, sort_keys=True))

    _assert_northstar_product_state(
        captured=captured,
        harness=harness,
        outcome=outcome,
    )


@pytest.mark.parametrize(
    ("case_id", "query", "expected_directive", "expected_syntax_kind"),
    [
        (
            "numbered",
            NUMBERED_NORTHSTAR_QUERY,
            NUMBERED_NORTHSTAR_DIRECTIVE,
            "numbered_interrogative",
        ),
        (
            "imperative",
            IMPERATIVE_NORTHSTAR_QUERY,
            IMPERATIVE_NORTHSTAR_DIRECTIVE,
            "imperative_clauses",
        ),
    ],
)
def test_numbered_and_imperative_northstar_queries_reach_same_governed_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case_id: str,
    query: str,
    expected_directive: str,
    expected_syntax_kind: str,
) -> None:
    _forbid_direct_semantic_producer(monkeypatch)
    harness = NorthstarHarness(tmp_path, query=query)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    scheduler_directives_before_release: list[str] = []
    real_release_scheduler_context = RunKernel.release_multicomponent_scheduler_transient_context

    def tracked_release_scheduler_context(run_kernel: RunKernel) -> None:
        scheduler_directives_before_release.append(
            str(run_kernel.state.multicomponent_scheduler_context.get("requested_synthesis_directive") or "")
        )
        real_release_scheduler_context(run_kernel)

    monkeypatch.setattr(
        RunKernel,
        "release_multicomponent_scheduler_transient_context",
        tracked_release_scheduler_context,
    )

    try:
        outcome = orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-07-10",
                session_id=f"northstar-{case_id}-session",
                run_id=f"northstar-{case_id}-run",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )
    except multicomponent_runtime.OrdinaryMulticomponentRuntimeError as exc:
        kernel = captured["semantic_run_kernel"]
        ledger = kernel.state.evidence_ledger.to_projection().to_dict()
        pytest.fail(
            json.dumps(
                {
                    "error": str(exc),
                    "search_calls": harness.search_calls,
                    "answer_components": (kernel.state.initial_answer_contract or {}).get("answer_components"),
                    "source_requirements": ledger.get("source_requirements"),
                    "requirement_links": ledger.get("requirement_links"),
                    "candidate_records": ledger.get("candidate_records"),
                },
                sort_keys=True,
            )
        )

    _assert_northstar_product_state(
        captured=captured,
        harness=harness,
        outcome=outcome,
        expected_directive=expected_directive,
    )
    kernel = captured["run_kernel"]
    question_meaning_record = kernel.state.search_planner_proposal_projection["question_meaning_record"]
    assessment_metadata = question_meaning_record["metadata"]
    accepted = kernel.state.initial_answer_contract
    cross_inputs = [
        item["input_packet"]
        for item in harness.role_input_packets
        if item["system_prompt"] == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
    ]
    assert len(cross_inputs) == 1
    assert len(scheduler_directives_before_release) == 1

    directive_values = [
        question_meaning_record["metadata"]["requested_synthesis_directive"],
        accepted["question_meaning_metadata"]["requested_synthesis_directive"],
        scheduler_directives_before_release[0],
        cross_inputs[0]["requested_synthesis_directive"],
    ]
    assert directive_values == [expected_directive] * len(directive_values)
    assert assessment_metadata["structured_route_posture"] == "QUALIFIED"
    assert assessment_metadata["structured_route_syntax_kind"] == expected_syntax_kind
    assert assessment_metadata["route_qualification_behavior_changed"] is True
    assert assessment_metadata["query_plan_behavior_changed"] is False
    assert assessment_metadata["provider_search_behavior_changed"] is False

    component_questions = [item["user_facing_question"] for item in question_meaning_record["answer_components"]]
    assert len(component_questions) == 5
    assert all(expected_directive not in question for question in component_questions)
    for expected_fragment, question in zip(
        ("base rebate", "application", "income", "paper", "online"),
        component_questions,
    ):
        assert expected_fragment in question.casefold()
    assert [item["component_id"] for item in question_meaning_record["answer_components"]] == [
        f"component-{index}" for index in range(1, 6)
    ]
    assert len(accepted["accepted_answer_component_refs"]) == 5
    component_refs = {item["component_id"]: item for item in accepted["accepted_answer_component_refs"]}
    first_source_ids = set(component_refs["component-1"].get("source_obligation_candidate_ids", []))
    assert "obligation:source_bound_numeric" not in first_source_ids
    assert "obligation:legal_current_primary" not in first_source_ids
    assert "obligation:conflict_resolution" not in first_source_ids
    assert any(
        item["candidate_id"] == "obligation:legal_current_primary"
        for item in question_meaning_record["source_obligation_candidate_refs"]
    )
    assert not any(action.action_type.value.startswith("specialist") for action in kernel.state.issued_actions.values())


def test_northstar_thin_proplex_main_prints_ordinary_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_direct_semantic_producer(monkeypatch)
    harness = NorthstarHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_SUFFICIENCY, HANDOFF_PACKET, HANDOFF_AUTHOR),
    )
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    cli = importlib.import_module("proplex.__main__")
    monkeypatch.setattr(cli, "_build_logger", lambda _verbose: logging.getLogger("northstar-cli"))
    monkeypatch.setattr(cli, "missing_required_api_keys", lambda **_kwargs: [])
    monkeypatch.setattr(
        cli,
        "append_official_canonical_recovery_diagnostics_section",
        lambda report, _trace: report,
    )
    cli_outcome: dict[str, Any] = {}

    def actual_offline_pipeline(
        config: Any,
        _deps: Any,
        _status: Any,
        _accumulator: Any,
    ) -> Any:
        outcome = orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=config.query,
                current_date="2026-07-10",
                session_id="northstar-cli-session",
                run_id="northstar-cli-run",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )
        cli_outcome["value"] = outcome
        return outcome

    monkeypatch.setattr(cli, "run_pipeline", actual_offline_pipeline)

    assert cli.main([NORTHSTAR_QUERY, "--mode", "Balanced"]) == 0
    stdout = capsys.readouterr().out
    normalized_stdout = " ".join(stdout.split())
    assert "$1,200" in normalized_stdout
    assert "October 31, 2027" in normalized_stdout
    assert "at or below $60,000" in normalized_stdout
    assert "should file the paper application" in normalized_stdout
    assert "not claiming the bonus" in normalized_stdout
    _assert_northstar_product_state(
        captured=captured,
        harness=harness,
        outcome=cli_outcome["value"],
    )


def test_six_component_near_miss_does_not_select_typed_lane() -> None:
    from core.ordinary_multicomponent_synthesis_runtime import (
        ordinary_multicomponent_path_selected,
    )
    from core.run_kernel import RunKernel

    kernel = RunKernel.start(run_id="run:six-near-miss", request_id="request:six")
    kernel.state.initial_answer_contract = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": kernel.state.run_id,
        "request_id": kernel.state.request_id,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "digest-six",
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": "Explain the combined filing sequence.",
        },
        "accepted_answer_component_refs": [
            {
                "component_id": f"component:{index}",
                "component_revision": "1",
                "component_digest": f"digest-{index}",
                "user_facing_label": f"Fact {index}",
                "user_facing_question": f"What is fact {index}?",
            }
            for index in range(1, 7)
        ],
    }
    assert ordinary_multicomponent_path_selected(kernel) is False


def test_query_shaped_metadata_alone_does_not_enable_custody_gap_exception() -> None:
    from core.multicomponent_component_admission import (
        _typed_lane_custody_gap_exception_authorized,
    )
    from core.ordinary_semantic_producer_runtime import (
        source_requirement_ids_for_component_candidate,
    )

    near_miss = {
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": "Explain the combined filing sequence.",
        },
        "accepted_answer_component_refs": [
            {
                "component_id": f"component:{index}",
                "component_revision": "1",
                "component_digest": f"digest-{index}",
            }
            for index in range(1, 7)
        ],
    }
    assert _typed_lane_custody_gap_exception_authorized(near_miss) is False

    # Direct ordinary producer default remains false: historical provider-job gaps
    # continue to block requirement selection outside the typed lane.
    ledger = {
        "source_requirements": [
            {
                "requirement_id": "provider_job_requirement:job-1",
                "status": "satisfied",
                "linked_candidate_ids": ["evidence:1"],
                "source_obligation_candidate_ids": ["provider_job_requirement:job-1"],
            }
        ],
        "custody_gaps": [
            {
                "requirement_id": "provider_job_requirement:job-1",
                "candidate_id": "evidence:1",
                "gap_type": "provider_job_historical",
            }
        ],
    }
    assert (
        source_requirement_ids_for_component_candidate(
            ledger,
            evidence_ref_id="evidence:1",
            source_obligation_candidate_ids=("provider_job_requirement:job-1",),
        )
        == ()
    )
    assert source_requirement_ids_for_component_candidate(
        ledger,
        evidence_ref_id="evidence:1",
        source_obligation_candidate_ids=("provider_job_requirement:job-1",),
        ignore_satisfied_provider_job_historical_gaps=True,
    ) == ("provider_job_requirement:job-1",)


def test_single_component_contract_remains_outside_typed_lane() -> None:
    from core.ordinary_multicomponent_synthesis_runtime import (
        ordinary_multicomponent_path_selected,
    )
    from core.run_kernel import RunKernel

    kernel = RunKernel.start(run_id="run:single", request_id="request:single")
    kernel.state.initial_answer_contract = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": kernel.state.run_id,
        "request_id": kernel.state.request_id,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "digest-single",
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": "Summarize the one fact.",
        },
        "accepted_answer_component_refs": [
            {
                "component_id": "component:1",
                "component_revision": "1",
                "component_digest": "digest-1",
                "user_facing_label": "Fact 1",
                "user_facing_question": "What is fact 1?",
            }
        ],
    }
    assert ordinary_multicomponent_path_selected(kernel) is False


def test_component_admission_rejects_forged_role_artifacts_and_claim_drift() -> None:
    from core.multicomponent_component_admission import (
        MulticomponentComponentAdmissionError,
        component_analyst_input_packet,
        execute_multicomponent_component_admission,
        stage_multicomponent_component_admission,
    )
    from core.multicomponent_role_runtime import (
        ROLE_COMPONENT_ANALYST,
        safe_packet_digest,
    )
    from core.run_kernel import RunKernel

    run_id = "run:admission-forge"
    request_id = "request:admission-forge"
    component_id = "component:1"
    component_ref = {
        "component_id": component_id,
        "component_revision": "1",
        "component_digest": "component-digest-1",
        "user_facing_label": "Fact 1",
        "user_facing_question": "What is fact 1?",
    }
    accepted = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": run_id,
        "request_id": request_id,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-digest",
        "parent_question_meaning_record_id": "qmr:1",
        "parent_question_meaning_record_digest": "qmr-digest",
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": "Explain the combined result.",
        },
        "accepted_answer_component_refs": [component_ref],
    }
    evidence_input = {
        "evidence_status": "available",
        "evidence_ref_id": "evidence:1",
        "bounded_text": "Fact 1 is supported.",
        "candidate_custody_ref": {"candidate_id": "cand-1"},
    }
    component_evidence_set = component_analyst_evidence_set_fixture(
        evidence_input
    )
    analyst_input = component_analyst_input_packet(
        run_id=run_id,
        request_id=request_id,
        accepted_contract=accepted,
        component_ref=component_ref,
        component_evidence_set=component_evidence_set,
    )

    def _artifact(role: str, semantic_output: dict, input_packet: dict) -> dict:
        core = {
            "schema_version": "multicomponent_semantic_role_artifact_v1",
            "role": role,
            "artifact_id": f"artifact:{role}:forged",
            "run_id": run_id,
            "request_id": request_id,
            "input_packet_digest": safe_packet_digest(input_packet),
            "logical_evaluation_key": component_id,
            "logical_evaluations": 1,
            "physical_calls": 1,
            "configured_model_route": {
                "provider": "offline",
                "model": "fixture",
                "role": "SmartModel",
            },
            "authorized_action_ref": {
                "action_id": f"action:{role}",
                "stage": f"stage:{role}",
                "sequence": 1,
                "observation_type": f"{role}_completed",
            },
            "semantic_output": semantic_output,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
        }
        return {**core, "artifact_digest": safe_packet_digest(core)}

    analyst = _artifact(
        ROLE_COMPONENT_ANALYST,
        {
            "case_posture": "supported",
            "support_status": "supported",
            "supporting_evidence_aliases": ["component_evidence_01"],
            "claim_text": "Fact 1 is supported.",
            "evidence_analysis": "The exact bounded evidence supports Fact 1.",
            "self_audit": "The case does not extend beyond Fact 1.",
            "caveats": [],
            "nonclaims": [],
            "contradictions": [],
            "blockers": [],
        },
        analyst_input,
    )
    observation = {
        "observation_id": "observation:1",
        "observation_digest": "observation-digest",
        "claim_or_value": "A different forged claim.",
        "evidence_refs": ["evidence:1"],
        "answer_component_id": component_id,
    }
    with pytest.raises(
        MulticomponentComponentAdmissionError,
        match="Analyst-nominated claim",
    ):
        stage_multicomponent_component_admission(
            action_id="action:admission",
            run_id=run_id,
            request_id=request_id,
            accepted_contract=accepted,
            evidence_ledger_projection={},
            semantic_observation_admission_history=[],
            component_coverage_history=[],
            component_id=component_id,
            analyst_artifact=analyst,
            analyst_input_packet=analyst_input,
            component_evidence_set=component_evidence_set,
            semantic_observation=observation,
            sanitized_content_references=[
                {
                    "content_ref_id": "content:1",
                    "evidence_ref_id": "evidence:1",
                    "content_digest": "content-digest",
                }
            ],
            component_coverage_record={
                "record_id": "coverage:1",
                "record_digest": "coverage-digest",
            },
        )

    kernel = RunKernel.start(run_id=run_id, request_id=request_id)
    kernel.state.initial_answer_contract = accepted
    kernel.state.initial_answer_contract_projection = {"canonical_state": True}
    with pytest.raises(
        MulticomponentComponentAdmissionError,
        match="exact completed RunKernel Analyst case",
    ):
        execute_multicomponent_component_admission(
            run_kernel=kernel,
            component_id=component_id,
            analyst_artifact=analyst,
            analyst_input_packet=analyst_input,
            component_evidence_set=component_evidence_set,
            semantic_observation=None,
            sanitized_content_references=[],
            component_coverage_record=None,
        )


def test_query_shape_six_explicit_components_do_not_bypass_planning_authority() -> None:
    from core.search_work_query_shape_runtime import (
        DeterministicSearchWorkRuntimeInput,
        build_deterministic_search_work_runtime_records,
    )

    preview = "\n".join(
        [
            "For the fictional Northstar Home-Energy Rebate:",
            "- What is the base rebate amount?",
            "- What is the application deadline?",
            "- Who qualifies for the income-based bonus?",
            "- Must bonus applicants use the paper application?",
            "- Can ordinary applicants file online?",
            "- What is the appeal deadline?",
            "",
            "Then explain how bonus eligibility changes the filing route.",
        ]
    )
    records = build_deterministic_search_work_runtime_records(
        DeterministicSearchWorkRuntimeInput(
            contract_id="contract:six",
            run_contract_projection={"contract_id": "contract:six"},
            route_facts={},
            requested_mode="Balanced",
            selected_depth="standard",
            safe_query_preview=preview,
        )
    )
    assert len(records.query_shape_assessment.component_candidates) == 6
    assert records.query_shape_assessment.metadata.get("explicit_factual_component_list") is False
    assert records.query_shape_assessment.metadata.get("structured_route_posture") == "AMBIGUOUS"
    assert records.query_shape_assessment.metadata.get("requested_synthesis_directive") is None
