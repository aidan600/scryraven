"""PRODUCT-PATH-REGRESSION: bounded ordinary dynamic graph recovery."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

import core.multicomponent_dynamic_recovery_runtime as recovery_runtime
import core.ordinary_multicomponent_synthesis_runtime as multicomponent_runtime
import core.pipeline as product_pipeline
import core.pipeline_orchestrator as orchestrator
from core.component_work_graph_v1 import (
    component_work_graph_v1_resynthesis_from_cross_component_artifact,
    cross_component_input_packet,
    graph_with_recovered_component,
    graph_with_scrutineer,
    reduce_component_work_graph_v1,
    scrutineer_input_packet,
)
from core.component_work_node import component_work_node_v1_from_admitted_component
from core.cost_accounting import CostAccumulator
from core.evidence_ledger import EvidenceLedger
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.multicomponent_component_admission import (
    component_analyst_input_packet,
    component_dprime_input_packet,
    execute_multicomponent_component_admission,
)
from core.multicomponent_dynamic_recovery_runtime import (
    apply_recovered_component_amendment,
    build_recovered_component_amendment,
    execute_recovery_acquisition,
)
from core.multicomponent_role_runtime import (
    ROLE_SCRUTINEER,
    MulticomponentRoleRuntimeError,
    execute_multicomponent_role_call,
    safe_packet_digest,
)
from core.multicomponent_sufficiency_consumption_runtime import (
    build_multicomponent_graph_consumption,
)
from core.ordinary_multicomponent_synthesis_runtime import (
    _accepted_contract_ref,
    _evidence_input,
    _semantic_material,
)
from core.protocols import NullStatusWriter
from core.run_kernel import Observation, RunKernelTransitionError, RunStageStatus
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
from tests.test_multicomponent_component_work_graph_v1 import (
    _flat_graph,
    _structured_graph,
    _validate_synthesis,
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


def _challenged_graph_with_missing_component_proposal(
    *,
    include_proposal: bool = True,
    scope_posture: str = (
        "required_to_fulfill_existing_accepted_user_obligation"
    ),
    proposal_target_key: str | None = None,
    kernel_graph: tuple[object, dict] | None = None,
):
    kernel, graph = kernel_graph or _flat_graph(
        caveats=("A filing-route rule remains material.",)
    )
    graph = _validate_synthesis(
        kernel,
        graph,
        graph["synthesis_topological_order"][0],
    )
    scrutiny_input = scrutineer_input_packet(graph)
    target = next(
        item
        for item in scrutiny_input["challenge_target_catalog"]
        if item["target_kind"] == "synthesis"
    )
    response = {
        "challenge_status": "challenged",
        "reasons": ["The filing-route synthesis omits a necessary rule."],
        "challenge_targets": [
            {
                "target_kind": target["target_kind"],
                "target_key": proposal_target_key or target["target_key"],
            }
        ],
        "missing_component_proposals": [
            {
                "proposal_key": "bonus_paper_rule",
                "component_label": "Bonus filing route",
                "component_question": (
                    "Must an applicant claiming the income bonus file on paper?"
                ),
                "necessity_reason": (
                    "The accepted filing-route explanation is incomplete without it."
                ),
                "target_kind": target["target_kind"],
                "target_key": target["target_key"],
                "relationship_to_accepted_synthesis_directive": (
                    "It supplies the missing branch of the accepted combined result."
                ),
                "scope_posture": scope_posture,
                "bounded_search_hints": ["bonus paper application rule"],
                "source_requirement_hints": ["official program rule"],
                "caveats": ["Fictional offline scenario only."],
                "nonclaims": ["No general filing rule is claimed."],
            }
        ] if include_proposal else [],
        "caveats": [],
        "nonclaims": [],
    }
    artifact = execute_multicomponent_role_call(
        run_kernel=kernel,
        role=ROLE_SCRUTINEER,
        input_packet=scrutiny_input,
        ask_model=lambda *_args, **_kwargs: json.dumps(response),
        clean_json_response=lambda value: value,
        provider="offline",
        model="fixture",
        base_url="http://offline.invalid/v1",
        api_key="",
        use_reasoning=False,
        logical_evaluation_key="full-case",
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="scrutiny",
        graph_candidate=graph_with_scrutineer(
            graph,
            scrutineer_artifact=artifact,
        ),
    )
    return kernel, graph


DYNAMIC_NORTHSTAR_QUERY = """For the fictional Northstar Home-Energy Rebate:
- What is the base rebate?
- Who qualifies for the income-based bonus?
- Can an ordinary applicant file online?
- What identifier must every applicant include?

Then explain how bonus eligibility changes the filing route and what an
eligible applicant should do."""

DYNAMIC_NORTHSTAR_REPORT = """Northstar Home-Energy Rebate

The base rebate is $1,200. The income bonus is available at or below $60,000
household income. An applicant claiming the income-based bonus must submit the
paper application, while an ordinary applicant who is not claiming the bonus
may file online. Every application must include the Northstar program account
number. The filing distinction is limited to the fictional Northstar rules
supplied for this answer."""


class DynamicNorthstarHarness(OfflineOrdinaryPipelineHarness):
    def __init__(
        self,
        tmp_path: Path,
        *,
        readable_recovery: bool = True,
        broadening_proposal: bool = False,
    ) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=DYNAMIC_NORTHSTAR_QUERY,
            core_topic="Northstar Home-Energy Rebate",
            primary_entity="Northstar",
            researcher_queries=(
                "Northstar base rebate amount",
                "Northstar income-based bonus qualification",
                "Northstar ordinary applicant online filing",
                "Northstar application account number requirement",
            ),
            raw_author_response=(
                DYNAMIC_NORTHSTAR_REPORT
                if readable_recovery and not broadening_proposal
                else (
                    "The base rebate, income threshold, and ordinary online "
                    "route are supported, but the bonus filing rule remains "
                    "unresolved, so no combined filing recommendation is available."
                )
            ),
            logger_name="test_dynamic_multicomponent_northstar",
        )
        self.readable_recovery = readable_recovery
        self.broadening_proposal = broadening_proposal

    def ask_model(self, prompt: str, system_prompt: str, **kwargs):
        from core.multicomponent_role_runtime import (
            ROLE_SYSTEM_PROMPTS,
            SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT,
        )

        if system_prompt in ROLE_SYSTEM_PROMPTS.values() or system_prompt == (
            SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT
        ):
            self.model_calls.append(
                {
                    "system_prompt": system_prompt,
                    "provider": kwargs.get("provider"),
                    "model": kwargs.get("model"),
                    "stream": bool(kwargs.get("stream")),
                }
            )
            payload = json.loads(prompt)
            if system_prompt == ROLE_SYSTEM_PROMPTS["component_analyst"]:
                question = str(
                    payload.get("component_ref", {}).get("user_facing_question")
                    or ""
                ).casefold()
                if "base rebate" in question:
                    claim = "The Northstar base rebate is $1,200."
                elif "income" in question and "paper" not in question:
                    claim = (
                        "The income bonus is available at or below $60,000 "
                        "household income."
                    )
                elif "online" in question:
                    claim = (
                        "An ordinary applicant not claiming the income bonus may file online."
                    )
                elif "account number" in question or "identifier" in question:
                    claim = (
                        "Every application must include the Northstar program "
                        "account number."
                    )
                elif "paper" in question:
                    claim = (
                        "Applicants claiming the income-based bonus must submit "
                        "the paper application."
                    )
                else:
                    raise AssertionError(f"unexpected component question: {question}")
                return json.dumps(
                    {
                        "claim_text": claim,
                        "support_status": "supported",
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS["component_dprime"]:
                return json.dumps(
                    {
                        "validation_status": "supported",
                        "reasons": ["The exact bounded evidence supports the claim."],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS["cross_component_analyst"]:
                nodes = payload.get("component_nodes", [])
                by_question = {
                    str(item.get("component_question") or "").casefold(): str(
                        item["component_id"]
                    )
                    for item in nodes
                }
                income = next(
                    value for key, value in by_question.items() if "income" in key
                )
                base = next(
                    value for key, value in by_question.items() if "base rebate" in key
                )
                online = next(
                    value for key, value in by_question.items() if "online" in key
                )
                account = next(
                    value
                    for key, value in by_question.items()
                    if "account number" in key or "identifier" in key
                )
                paper = next(
                    (
                        value
                        for key, value in by_question.items()
                        if "paper" in key
                    ),
                    None,
                )
                if paper is None:
                    return json.dumps(
                        {
                            "synthesis_proposals": [
                                {
                                    "synthesis_key": "benefit_summary",
                                    "claim_text": (
                                        "The base rebate and income threshold define "
                                        "the verified two-part Northstar benefit."
                                    ),
                                    "relationship_type": "benefit_conjunction",
                                    "component_inputs": [base, income],
                                    "synthesis_inputs": [],
                                    "caveats": [],
                                    "nonclaims": [],
                                    "blockers": [],
                                },
                                {
                                    "synthesis_key": "filing_route",
                                    "claim_text": (
                                        "Ordinary non-bonus applicants may file online, "
                                        "but the route for bonus claimants is not established."
                                    ),
                                    "relationship_type": "conditional_filing_route",
                                    "component_inputs": [online, account],
                                    "synthesis_inputs": [],
                                    "caveats": [
                                        "The bonus-claimant filing rule is not established."
                                    ],
                                    "nonclaims": [],
                                    "blockers": [],
                                },
                                {
                                    "synthesis_key": "applicant_guidance",
                                    "claim_text": (
                                        "Applicants should combine the benefit facts "
                                        "with the currently known filing route."
                                    ),
                                    "relationship_type": "guided_conjunction",
                                    "component_inputs": [],
                                    "synthesis_inputs": [
                                        "benefit_summary",
                                        "filing_route",
                                    ],
                                    "caveats": [
                                        "The bonus-claimant filing route is unresolved."
                                    ],
                                    "nonclaims": [],
                                    "blockers": [],
                                },
                            ]
                        }
                    )
                return json.dumps(
                    {
                        "synthesis_proposals": [
                            {
                                "synthesis_key": "filing_route",
                                "claim_text": (
                                    "Income-bonus claimants must use the paper application; "
                                    "ordinary non-bonus applicants may file online."
                                ),
                                "relationship_type": "conditional_filing_route",
                                "component_inputs": [online, account, paper],
                                "synthesis_inputs": [],
                                "caveats": [],
                                "nonclaims": [
                                    "No filing rule outside the fictional program is claimed."
                                ],
                                "blockers": [],
                            }
                        ]
                    }
                )
            if system_prompt == SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT:
                recovered = payload["current_recovered_component_ref"][
                    "component_id"
                ]
                licensed = [
                    item["component_id"]
                    for item in payload["licensed_current_component_refs"]
                ]
                boundary_by_key = {
                    item["synthesis_key"]: item
                    for item in payload["preserved_boundary_synthesis_catalog"]
                }
                benefit_claim = boundary_by_key["benefit_summary"]["claim_text"]
                if "verified two-part Northstar benefit" not in benefit_claim:
                    raise AssertionError(
                        "selective fixture did not receive preserved semantics"
                    )
                return json.dumps(
                    {
                        "synthesis_proposals": [
                            {
                                "synthesis_key": "filing_route",
                                "claim_text": (
                                    "Income-bonus claimants must use the paper application; "
                                    "ordinary non-bonus applicants may file online."
                                ),
                                "relationship_type": "conditional_filing_route",
                                "component_inputs": [*licensed, recovered],
                                "affected_synthesis_inputs": [],
                                "preserved_synthesis_inputs": [],
                                "caveats": [],
                                "nonclaims": [
                                    "No filing rule outside the fictional program is claimed."
                                ],
                                "blockers": [],
                            },
                            {
                                "synthesis_key": "applicant_guidance",
                                "claim_text": (
                                    f"Using {benefit_claim}, applicants should follow "
                                    "the applicable online-or-paper filing route."
                                ),
                                "relationship_type": "guided_conjunction",
                                "component_inputs": [],
                                "affected_synthesis_inputs": ["filing_route"],
                                "preserved_synthesis_inputs": ["benefit_summary"],
                                "caveats": [],
                                "nonclaims": [],
                                "blockers": [],
                            },
                        ]
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS["synthesis_dprime"]:
                return json.dumps(
                    {
                        "validation_status": "supported",
                        "reasons": ["All nominated upstream inputs are admitted."],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS["scrutineer"]:
                paper_present = any(
                    "paper"
                    in str(item.get("claim_text") or "").casefold()
                    for item in payload.get("component_refs", [])
                )
                if paper_present:
                    return json.dumps(
                        {
                            "challenge_status": "passed",
                            "reasons": [
                                "The fresh filing-route synthesis includes both branches."
                            ],
                            "challenge_targets": [],
                            "missing_component_proposals": [],
                            "caveats": [],
                            "nonclaims": [],
                        }
                    )
                target = next(
                    item
                    for item in payload["challenge_target_catalog"]
                    if item["target_kind"] == "synthesis"
                    and item["semantic_material"].get("synthesis_key")
                    == "filing_route"
                )
                return json.dumps(
                    {
                        "challenge_status": "challenged",
                        "reasons": [
                            "The practical filing-route explanation omits the bonus rule."
                        ],
                        "challenge_targets": [
                            {
                                "target_kind": "synthesis",
                                "target_key": target["target_key"],
                            }
                        ],
                        "missing_component_proposals": [
                            {
                                "proposal_key": "bonus_paper_application_rule",
                                "component_label": "Bonus filing requirement",
                                "component_question": (
                                    "Must an applicant claiming the income-based bonus "
                                    "submit a paper application?"
                                ),
                                "necessity_reason": (
                                    "The accepted filing-route explanation is incomplete "
                                    "and potentially misleading without this rule."
                                ),
                                "target_kind": "synthesis",
                                "target_key": target["target_key"],
                                "relationship_to_accepted_synthesis_directive": (
                                    "It supplies the missing bonus branch of the accepted "
                                    "filing-route explanation."
                                ),
                                "scope_posture": (
                                    "new_or_broadened_user_intent"
                                    if self.broadening_proposal
                                    else "required_to_fulfill_existing_accepted_user_obligation"
                                ),
                                "bounded_search_hints": [
                                    "Northstar income bonus paper application rule"
                                ],
                                "source_requirement_hints": [
                                    "official current program rule"
                                ],
                                "caveats": ["Fictional Northstar scenario only."],
                                "nonclaims": [
                                    "No general application rule is proposed."
                                ],
                            }
                        ],
                        "caveats": [],
                        "nonclaims": [],
                    }
                )
        return super().ask_model(prompt, system_prompt, **kwargs)

    def process_search_queries(
        self,
        queries,
        intent,
        complexity,
        search_depth,
        results_per_query,
        *_args,
        **kwargs,
    ):
        self.search_calls.append(
            {
                "queries": list(queries),
                "provider_role": kwargs.get("provider_role"),
                "search_providers": list(kwargs.get("search_providers") or []),
            }
        )
        if kwargs.get("provider_role") == "multicomponent_recovery_diagnostic":
            diagnostics = kwargs.get("provider_diagnostics")
            if isinstance(diagnostics, list):
                diagnostics.append(
                    {
                        "provider": "tavily",
                        "provider_role": kwargs.get("provider_role"),
                    }
                )
            if not self.readable_recovery:
                return []
            return [
                {
                    "source_id": 204,
                    "title": "Northstar bonus claimant paper application rule",
                    "url": "https://northstar.example/bonus-paper-rule",
                    "text": (
                        "Applicants claiming the income-based bonus must submit "
                        "the paper application."
                    ),
                    "score": 1.0,
                    "credibility": 4,
                    "source_tier": "primary",
                    "source_class": "legal_or_regulatory_text",
                    "currentness_signal": "current",
                    "readable_status": "readable",
                    "disposition": "accepted",
                    "eligible_for_stronger_obligation": True,
                    "query_ref": str(queries[0]),
                    "_provider": "tavily",
                }
            ]
        passages = self.build_search_passages()
        seen_urls = kwargs.get("seen_urls")
        if seen_urls is not None:
            for passage in passages:
                seen_urls.add(passage["url"])
        return passages

    def build_search_passages(self):
        facts = (
            (
                201,
                "Northstar base rebate $1,200",
                "The Northstar Home-Energy Rebate base rebate is $1,200.",
                "sourced_numeric_values",
                "Northstar base rebate amount",
                "official",
            ),
            (
                202,
                "Northstar income bonus threshold",
                "The income bonus is available at or below $60,000 household income.",
                "sourced_numeric_values",
                "Northstar income-based bonus qualification",
                "official",
            ),
            (
                203,
                "Northstar ordinary online filing",
                "An ordinary applicant not claiming the income bonus may file online.",
                "primary_source_documents",
                "Northstar ordinary applicant online filing",
                "official",
            ),
            (
                207,
                "Northstar account number requirement",
                "Every application must include the Northstar program account number.",
                "primary_source_documents",
                "Northstar application account number requirement",
                "official",
            ),
            (
                205,
                "Northstar program primary literature",
                "The fictional Northstar record documents the rebate program.",
                "academic_primary_literature",
                "Northstar academic primary literature",
                "primary",
            ),
            (
                206,
                "Northstar primary legal record",
                "The fictional current Northstar legal record establishes the program.",
                "legal_or_regulatory_text",
                "Northstar legal primary source",
                "primary",
            ),
        )
        return [
            {
                "source_id": source_id,
                "title": title,
                "url": f"https://northstar.example/rule-{source_id}",
                "text": text,
                "score": 1.0 - index * 0.01,
                "credibility": 4,
                "source_tier": source_tier,
                "source_class": source_class,
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
                "query_ref": query_ref,
                "_provider": "tavily",
            }
            for index, (
                source_id,
                title,
                text,
                source_class,
                query_ref,
                source_tier,
            ) in enumerate(
                facts
            )
        ]


class RealRecoveryDispatcherNorthstarHarness(DynamicNorthstarHarness):
    """Keep initial fixture custody but use the real product dispatcher for recovery."""

    def process_search_queries(
        self,
        queries,
        intent,
        complexity,
        search_depth,
        results_per_query,
        *args,
        **kwargs,
    ):
        if kwargs.get("provider_role") == "multicomponent_recovery_diagnostic":
            self.search_calls.append(
                {
                    "queries": list(queries),
                    "provider_role": kwargs.get("provider_role"),
                    "search_providers": list(
                        kwargs.get("search_providers") or []
                    ),
                    "real_dispatcher": True,
                }
            )
            return product_pipeline.process_search_queries(
                queries,
                intent,
                complexity,
                search_depth,
                results_per_query,
                *args,
                **kwargs,
            )
        return super().process_search_queries(
            queries,
            intent,
            complexity,
            search_depth,
            results_per_query,
            *args,
            **kwargs,
        )


def test_scrutineer_proposal_reduces_to_one_exact_recovery_authorization() -> None:
    kernel, graph = _challenged_graph_with_missing_component_proposal()

    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )

    authorization = kernel.state.projections[action.stage]
    assert authorization["canonical_state"] is True
    assert authorization["proposal_key"] == "bonus_paper_rule"
    assert authorization["target_kind"] == "synthesis"
    assert authorization["target_key"] == "synthesis_01"
    assert authorization["graph_digest"] == graph["graph_digest"]
    assert authorization["recovery_authorization_action_count"] == 1
    assert authorization["recovery_authorization_observation_count"] == 1
    assert authorization["automatic_amendment_authority_class"] == (
        "required_to_fulfill_existing_accepted_user_obligation"
    )


def test_recovery_rejects_missing_wrong_target_forged_and_cross_run_proposals() -> None:
    kernel, _graph = _challenged_graph_with_missing_component_proposal(
        include_proposal=False
    )
    with pytest.raises(
        RunKernelTransitionError,
        match="exactly one canonical proposal",
    ):
        kernel.authorize_multicomponent_missing_component_recovery(
            proposal_key="bonus_paper_rule"
        )

    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="challenge target",
    ):
        _challenged_graph_with_missing_component_proposal(
            proposal_target_key="wrong_target"
        )

    kernel, graph = _challenged_graph_with_missing_component_proposal()
    completed_stage = graph["scrutineer_ref"]["authorized_action_ref"]["stage"]
    forged = deepcopy(kernel.state.projections[completed_stage])
    forged["semantic_output"]["missing_component_proposals"][0][
        "component_question"
    ] = "A forged replacement question"
    kernel.state.projections[completed_stage] = forged
    with pytest.raises(
        RunKernelTransitionError,
        match="exact completed Scrutineer artifact",
    ):
        kernel.authorize_multicomponent_missing_component_recovery(
            proposal_key="bonus_paper_rule"
        )

    kernel, _graph = _challenged_graph_with_missing_component_proposal()
    kernel.state.run_id = "cross-run"
    with pytest.raises(RunKernelTransitionError, match="cross-run"):
        kernel.authorize_multicomponent_missing_component_recovery(
            proposal_key="bonus_paper_rule"
        )


def test_recovery_duplicate_second_round_and_scope_broadening_fail_closed() -> None:
    kernel, _graph = _challenged_graph_with_missing_component_proposal()
    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    with pytest.raises(RunKernelTransitionError, match="second.*round"):
        kernel.authorize_multicomponent_missing_component_recovery(
            proposal_key="bonus_paper_rule"
        )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    kernel.state.initial_answer_contract_projection = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
    }
    apply_recovered_component_amendment(run_kernel=kernel)
    with pytest.raises((RunKernelTransitionError, ValueError)):
        apply_recovered_component_amendment(run_kernel=kernel)

    broadened, _graph = _challenged_graph_with_missing_component_proposal(
        scope_posture="new_or_broadened_user_intent"
    )
    broadened_action = (
        broadened.authorize_multicomponent_missing_component_recovery(
            proposal_key="bonus_paper_rule"
        )
    )
    broadened.reduce(
        Observation.from_action(
            broadened_action,
            observation_type=broadened_action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    broadened_authorization = broadened.state.projections[
        broadened_action.stage
    ]
    assert broadened_authorization["search_authorized"] is False
    assert broadened_authorization[
        "automatic_amendment_authority_class"
    ] is None


def test_recovery_amendment_posture_cannot_bypass_exact_authority_inputs() -> None:
    kernel, _graph = _challenged_graph_with_missing_component_proposal()
    recovery = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            recovery,
            observation_type=recovery.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    kernel.state.initial_answer_contract_projection = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
    }
    _component, record = build_recovered_component_amendment(run_kernel=kernel)
    admission = kernel.authorize_contract_amendment_admission(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        parent_contract_digest=record.parent_contract_digest,
        parent_contract_version=record.parent_contract_version,
    )

    with pytest.raises(
        RunKernelTransitionError,
        match="requires exact recovery authority",
    ):
        kernel.reduce(
            Observation.from_action(
                admission,
                observation_type=admission.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={"contract_amendment_record": record.to_dict()},
            )
        )
    assert kernel.state.contract_amendment_admission_history == []


def test_pre_amendment_graph_fails_closed_against_current_contract() -> None:
    kernel, graph = _challenged_graph_with_missing_component_proposal()
    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    kernel.state.initial_answer_contract_projection = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
    }
    apply_recovered_component_amendment(run_kernel=kernel)
    current = kernel.state.current_answer_contract
    consumption = build_multicomponent_graph_consumption(
        graph,
        current_contract_version=current["accepted_contract_version"],
        current_contract_digest=current["accepted_contract_digest"],
    )

    assert consumption["graph_contract_current"] is False
    assert consumption["graph_ready_for_synthesis"] is False
    assert consumption["admitted_synthesis_entries"] == []


def test_component_cap_rejects_recovery_before_authorization() -> None:
    kernel, graph = _structured_graph()
    kernel, _graph = _challenged_graph_with_missing_component_proposal(
        kernel_graph=(kernel, graph)
    )
    assert len(graph["component_nodes"]) == 5
    with pytest.raises(RunKernelTransitionError, match="component cap"):
        kernel.authorize_multicomponent_missing_component_recovery(
            proposal_key="bonus_paper_rule"
        )


def test_recovery_authority_applies_one_versioned_add_component_amendment() -> None:
    kernel, _graph = _challenged_graph_with_missing_component_proposal()
    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    kernel.state.initial_answer_contract_projection = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
    }

    result = apply_recovered_component_amendment(run_kernel=kernel)

    initial = kernel.state.initial_answer_contract
    current = kernel.state.current_answer_contract
    assert current["accepted_contract_version"] != initial["accepted_contract_version"]
    assert current["accepted_contract_digest"] != initial["accepted_contract_digest"]
    assert current["previous_contract_digest"] == initial["accepted_contract_digest"]
    assert len(current["accepted_answer_component_refs"]) == 3
    assert result.component_ref["component_id"].startswith("component:recovered:")
    assert result.component_ref["lifecycle_status"] == "pending"
    assert len(kernel.state.contract_amendment_admission_history) == 1
    assert len(kernel.state.contract_amendment_application_history) == 1
    assert result.amendment_admission["user_confirmation_posture"] == (
        "required_to_fulfill_existing_accepted_user_obligation"
    )
    assert kernel.state.initial_answer_contract == initial


def test_recovery_reenters_ordinary_offline_acquisition_and_evidence_ledger() -> None:
    kernel, _graph = _challenged_graph_with_missing_component_proposal()
    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    kernel.state.initial_answer_contract_projection = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
    }
    amendment = apply_recovered_component_amendment(run_kernel=kernel)
    calls: list[list[str]] = []

    def execute_search(queries, *_args, **_kwargs):
        calls.append(list(queries))
        return [
            {
                "title": "Northstar bonus paper rule",
                "url": "https://northstar.example/paper-rule",
                "text": (
                    "Applicants claiming the income-based bonus must submit "
                    "the paper application."
                ),
                "readable_status": "readable",
                "currentness_signal": "current",
                "source_class": "primary_source_documents",
                "source_tier": "official",
                "_provider": "tavily",
            }
        ]

    acquisition = execute_recovery_acquisition(
        run_kernel=kernel,
        runtime_scope={
            "deps": SimpleNamespace(process_search_queries=execute_search),
            "intent": "general",
            "complexity": "medium",
            "search_depth": "basic",
        },
        component_ref=amendment.component_ref,
    )

    assert acquisition.acquired is True, json.dumps(
        {
            "projection": acquisition.projection,
            "ledger": kernel.state.evidence_ledger.to_projection().to_dict(),
        },
        sort_keys=True,
    )
    assert len(calls) == 1
    assert acquisition.bindable is not None
    assert "paper application" in acquisition.bindable.passage["text"]
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    source_id = amendment.component_ref["source_obligation_candidate_ids"][0]
    requirement = next(
        item
        for item in ledger["source_requirements"]
        if item["requirement_id"] == source_id.replace("-", "_")
    )
    assert requirement["status"] == "satisfied"
    assert acquisition.projection["ordinary_acquisition_attempt_count"] == 1
    assert acquisition.projection["direct_semantic_producer_used"] is False


def test_recovered_component_uses_typed_analyst_dprime_and_runkernel_admission() -> None:
    kernel, _graph = _challenged_graph_with_missing_component_proposal()
    kernel.state.initial_answer_contract.update(
        {
            "parent_question_meaning_record_id": "qmr:northstar-recovery",
            "parent_question_meaning_record_digest": "qmr-digest-northstar-recovery",
        }
    )
    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    kernel.state.initial_answer_contract_projection = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
    }
    amendment = apply_recovered_component_amendment(run_kernel=kernel)

    def execute_search(*_args, **_kwargs):
        return [
            {
                "title": "Northstar bonus paper rule",
                "url": "https://northstar.example/paper-rule",
                "text": (
                    "Applicants claiming the income-based bonus must submit "
                    "the paper application."
                ),
                "readable_status": "readable",
                "currentness_signal": "current",
                "source_class": "primary_source_documents",
                "source_tier": "official",
                "_provider": "tavily",
            }
        ]

    acquisition = execute_recovery_acquisition(
        run_kernel=kernel,
        runtime_scope={
            "deps": SimpleNamespace(process_search_queries=execute_search),
            "intent": "general",
            "complexity": "medium",
            "search_depth": "basic",
        },
        component_ref=amendment.component_ref,
    )
    assert acquisition.bindable is not None
    component_id = str(amendment.component_ref["component_id"])
    analyst_input = component_analyst_input_packet(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        accepted_contract=kernel.state.current_answer_contract,
        component_ref=amendment.component_ref,
        evidence_input=_evidence_input(acquisition.bindable),
    )
    analyst = execute_multicomponent_role_call(
        run_kernel=kernel,
        role="component_analyst",
        input_packet=analyst_input,
        ask_model=lambda *_args, **_kwargs: json.dumps(
            {
                "claim_text": (
                    "Applicants claiming the income-based bonus must submit "
                    "the paper application."
                ),
                "support_status": "supported",
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            }
        ),
        clean_json_response=lambda value: value,
        provider="offline",
        model="fixture",
        base_url="http://offline.invalid/v1",
        api_key="",
        use_reasoning=False,
        logical_evaluation_key=component_id,
    )
    dprime_input = component_dprime_input_packet(
        analyst_artifact=analyst,
        analyst_input_packet=analyst_input,
    )
    dprime = execute_multicomponent_role_call(
        run_kernel=kernel,
        role="component_dprime",
        input_packet=dprime_input,
        ask_model=lambda *_args, **_kwargs: json.dumps(
            {
                "validation_status": "supported",
                "reasons": ["The exact bounded evidence supports the claim."],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            }
        ),
        clean_json_response=lambda value: value,
        provider="offline",
        model="fixture",
        base_url="http://offline.invalid/v1",
        api_key="",
        use_reasoning=False,
        logical_evaluation_key=component_id,
    )
    observation, content_refs, coverage = _semantic_material(
        run_kernel=kernel,
        component_ref=amendment.component_ref,
        bindable=acquisition.bindable,
        analyst_artifact=analyst,
        dprime_artifact=dprime,
        query="Northstar filing route",
    )
    admitted = execute_multicomponent_component_admission(
        run_kernel=kernel,
        component_id=component_id,
        analyst_artifact=analyst,
        dprime_artifact=dprime,
        analyst_input_packet=analyst_input,
        semantic_observation=observation,
        sanitized_content_references=content_refs,
        component_coverage_record=coverage,
    )

    assert admitted["admission_status"] == "admitted"
    assert admitted["accepted_contract_version"] == (
        kernel.state.current_answer_contract["accepted_contract_version"]
    )
    assert admitted["accepted_contract_digest"] == (
        kernel.state.current_answer_contract["accepted_contract_digest"]
    )
    assert admitted["analyst_finding_ref"]["role"] == "component_analyst"
    assert admitted["dprime_validation_ref"]["role"] == "component_dprime"
    assert len(kernel.state.semantic_observation_admission_history) == 1
    assert len(kernel.state.component_coverage_history) == 1


def test_graph_identity_advances_and_pre_recovery_synthesis_becomes_noncurrent() -> None:
    kernel, graph = _challenged_graph_with_missing_component_proposal()
    initial_graph_id = graph["graph_id"]
    initial_graph_revision = graph["graph_revision"]
    initial_synthesis_ids = {item["node_id"] for item in graph["synthesis_nodes"]}
    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    kernel.state.initial_answer_contract_projection = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
    }
    amendment = apply_recovered_component_amendment(run_kernel=kernel)
    component = amendment.component_ref
    component_id = str(component["component_id"])
    claim = "Applicants claiming the income bonus must use paper."
    admission = {
        "schema_version": "multicomponent_component_admission_ref_v1",
        "owner": "RunKernel.MulticomponentComponentAdmission",
        "canonical_state": True,
        "run_id": kernel.state.run_id,
        "request_id": kernel.state.request_id,
        "action_id": "action:recovered-component-admission",
        "accepted_contract_version": kernel.state.current_answer_contract[
            "accepted_contract_version"
        ],
        "accepted_contract_digest": kernel.state.current_answer_contract[
            "accepted_contract_digest"
        ],
        "component_id": component_id,
        "component_revision": component["component_revision"],
        "component_digest": component["component_digest"],
        "admission_status": "admitted",
        "current": True,
        "stale": False,
        "analyst_finding_ref": {
            "role": "component_analyst",
            "artifact_id": "artifact:recovered-analyst",
            "artifact_digest": "digest:recovered-analyst",
        },
        "dprime_validation_ref": {
            "role": "component_dprime",
            "artifact_id": "artifact:recovered-dprime",
            "artifact_digest": "digest:recovered-dprime",
        },
        "admitted_claim_ref": {
            "claim_id": "claim:recovered-paper-rule",
            "claim_text": claim,
            "claim_digest": "digest:recovered-paper-rule",
        },
        "semantic_observation_ref": {
            "observation_id": "observation:recovered-paper-rule",
            "observation_digest": "digest:observation:recovered-paper-rule",
        },
        "component_coverage_ref": {
            "coverage_record_id": "coverage:recovered-paper-rule",
            "coverage_record_digest": "digest:coverage:recovered-paper-rule",
            "coverage_state": "satisfied",
        },
        "evidence_refs": [],
        "required_caveats": [],
        "preserved_nonclaims": [],
        "blocker_refs": [],
    }
    aggregate = kernel.state.projections["multicomponent_component_admission"]
    aggregate["component_admission_refs"].append(admission)
    recovered_node = component_work_node_v1_from_admitted_component(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        accepted_component_ref=component,
        component_admission_ref=admission,
    )
    recovery_ref = kernel.state.projections[action.stage]
    application = kernel.state.contract_amendment_application_projection
    application_ref = {
        "owner": application.get("owner"),
        "application_digest": application["application_digest"],
        "authorized_action_id": application.get("authorized_action_id"),
        "amendment_record_id": application.get("amendment_record_id"),
    }
    contract_ref = _accepted_contract_ref(kernel.state.current_answer_contract)
    amended = graph_with_recovered_component(
        graph,
        recovered_component_node=recovered_node,
        current_contract_ref=contract_ref,
        recovery_authorization_ref=recovery_ref,
        amendment_application_ref=application_ref,
    )
    amended = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="graph_amendment",
        graph_candidate=amended,
    )

    assert amended["graph_id"] == initial_graph_id
    assert amended["graph_revision"] == initial_graph_revision + 1
    assert amended["graph_status"] == "stale_synthesis"
    assert amended["synthesis_nodes"] == []
    assert amended["edges"] == []
    assert {
        item["node_id"] for item in amended["stale_synthesis_history"]
    } == initial_synthesis_ids
    assert all(
        item["current"] is False and item["stale"] is True
        for item in amended["stale_synthesis_history"]
    )

    cross_input = cross_component_input_packet(
        component_nodes=amended["component_nodes"],
        accepted_contract_ref=contract_ref,
        requested_synthesis_directive=amended["requested_synthesis_directive"],
    )
    component_ids = [item["component_id"] for item in amended["component_nodes"]]
    evaluation_key = f"graph-v1:revision:{amended['graph_revision']}"
    cross = execute_multicomponent_role_call(
        run_kernel=kernel,
        role="cross_component_analyst",
        input_packet=cross_input,
        ask_model=lambda *_args, **_kwargs: json.dumps(
            {
                "synthesis_proposals": [
                    {
                        "synthesis_key": "fresh_route",
                        "claim_text": (
                            "Bonus claimants use paper; ordinary applicants may file online."
                        ),
                        "relationship_type": "conditional_filing_route",
                        "component_inputs": component_ids,
                        "synthesis_inputs": [],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                ]
            }
        ),
        clean_json_response=lambda value: value,
        provider="offline",
        model="fixture",
        base_url="http://offline.invalid/v1",
        api_key="",
        use_reasoning=False,
        logical_evaluation_key=evaluation_key,
    )
    fresh = component_work_graph_v1_resynthesis_from_cross_component_artifact(
        amended,
        accepted_contract_ref=contract_ref,
        cross_component_artifact=cross,
    )
    fresh = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="resynthesis_structure",
        graph_candidate=fresh,
        role_evaluation_key=evaluation_key,
    )

    assert fresh["graph_id"] == initial_graph_id
    assert fresh["graph_revision"] == amended["graph_revision"] + 1
    assert fresh["whole_graph_resynthesis_rounds"] == 1
    assert len(fresh["synthesis_nodes"]) == 1
    assert fresh["synthesis_nodes"][0]["node_id"] not in initial_synthesis_ids


def _forbid_direct_semantic_producer(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError(
            "qualifying dynamic Northstar run cannot use direct semantic authority"
        )

    monkeypatch.setattr(
        multicomponent_runtime,
        "execute_ordinary_semantic_producer_handoff_from_scope",
        forbidden,
    )


def test_dynamic_northstar_ordinary_pipeline_recovers_and_answers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_direct_semantic_producer(monkeypatch)
    harness = DynamicNorthstarHarness(tmp_path)
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
                current_date="2026-07-11",
                session_id="dynamic-northstar-session",
                run_id="dynamic-northstar-run",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )
    except Exception as exc:
        kernel = captured.get("semantic_run_kernel") or captured.get("run_kernel")
        sufficiency = captured.get("sufficiency_projection") or {}
        graph = (
            kernel.state.projections.get(
                "multicomponent_component_work_graph_v1"
            )
            if kernel is not None
            else {}
        )
        current_contract = (
            kernel.state.current_answer_contract if kernel is not None else {}
        )
        pytest.fail(
            json.dumps(
                {
                    "error": str(exc),
                    "sufficiency": {
                        key: sufficiency.get(key)
                        for key in (
                            "decision",
                            "final_answer_posture",
                            "final_answer_allowed",
                            "missing_required_obligations",
                            "unresolved_required_obligations",
                            "readiness_reasons",
                            "limitations",
                            "multicomponent_graph_consumption",
                        )
                    },
                    "graph": {
                        key: graph.get(key)
                        for key in (
                            "graph_id",
                            "graph_revision",
                            "accepted_contract_version",
                            "accepted_contract_digest",
                            "status",
                            "current",
                            "stale",
                            "whole_graph_resynthesis_rounds",
                            "accounting",
                        )
                    },
                    "current_contract": {
                        key: current_contract.get(key)
                        for key in (
                            "accepted_contract_version",
                            "accepted_contract_digest",
                        )
                    },
                },
                sort_keys=True,
            )
        )

    kernel = captured["run_kernel"]
    graph = kernel.state.projections["multicomponent_component_work_graph_v1"]
    authorization = kernel.state.projections[
        "multicomponent_missing_component_recovery_authorization"
    ]
    recovery = kernel.state.projections["multicomponent_dynamic_recovery"]
    canonical_outcome = kernel.state.projections[
        "multicomponent_recovery_outcome"
    ]
    assert authorization["target_kind"] == "synthesis"
    assert authorization["target_key"] == "synthesis_02"
    assert authorization["recovery_authorization_action_count"] == 1
    assert len(kernel.state.contract_amendment_admission_history) == 1
    assert len(kernel.state.contract_amendment_application_history) == 1
    assert len(kernel.state.current_answer_contract_history) == 1
    assert kernel.state.initial_answer_contract["accepted_contract_digest"] != (
        kernel.state.current_answer_contract["accepted_contract_digest"]
    )
    assert recovery["status"] == "acquired"
    assert recovery["ordinary_acquisition_attempt_count"] == 1
    assert recovery["direct_semantic_producer_used"] is False
    assert canonical_outcome["owner"] == "RunKernel.MulticomponentRecoveryOutcome"
    assert canonical_outcome["canonical_state"] is True
    assert canonical_outcome["trace_only"] is False
    assert canonical_outcome["recovery_disposition"] == "acquired"
    assert canonical_outcome["observed_provider_identities"] == ["tavily"]
    assert canonical_outcome["graph_digest"] == graph["graph_digest"]
    assert canonical_outcome["component_admission_ref"]["component_id"].startswith(
        "component:recovered:"
    )
    assert kernel.state.projections[
        "multicomponent_recovery_outcome_history"
    ]["outcomes"] == [canonical_outcome]
    assert len(
        [
            call
            for call in harness.search_calls
            if call.get("provider_role") == "multicomponent_recovery_diagnostic"
        ]
    ) == 1
    assert len(graph["component_nodes"]) == 5
    assert len(graph["stale_synthesis_history"]) == 2
    assert all(
        item["current"] is False and item["stale"] is True
        for item in graph["stale_synthesis_history"]
    )
    assert graph["automatic_recovery_rounds"] == 1
    assert graph["graph_amendment_rounds"] == 1
    assert graph["component_research_reentry_rounds"] == 1
    assert graph["whole_graph_resynthesis_rounds"] == 0
    assert graph["selective_recomputation_rounds"] == 1
    assert graph["affected_synthesis_count"] == 2
    assert graph["preserved_synthesis_count"] == 1
    assert graph["recomputed_synthesis_count"] == 2
    assert graph["carry_forward_count"] == 1
    assert graph["graph_id"] == authorization["graph_id"]
    assert graph["graph_revision"] > authorization["graph_revision"]
    assert graph["accepted_contract_ref"]["accepted_contract_digest"] == (
        kernel.state.current_answer_contract["accepted_contract_digest"]
    )
    assert graph["graph_status"] == "ready"
    assert [item["status"] for item in graph["synthesis_nodes"]] == [
        "admitted",
        "admitted",
        "admitted",
    ]
    assert graph["logical_accounting"] == {
        "component_analyst_evaluations": 5,
        "component_dprime_evaluations": 5,
        "cross_component_analyst_evaluations": 2,
        "synthesis_dprime_evaluations": 5,
        "scrutineer_evaluations": 2,
    }
    assert graph["physical_call_accounting"] == {
        "component_analyst_calls": 5,
        "component_dprime_calls": 5,
        "cross_component_analyst_calls": 2,
        "synthesis_dprime_calls": 5,
        "scrutineer_calls": 2,
    }
    sufficiency = captured["sufficiency_projection"]
    assert sufficiency["final_answer_allowed"] is True
    assert sufficiency["multicomponent_graph_consumption"][
        "graph_contract_current"
    ] is True
    packet = captured["packet_handoff"].packet
    assert len(packet.direct_component_entries) == 5
    assert len(packet.admitted_synthesis_entries) == 3, json.dumps(
        {
            "decision": sufficiency.get("decision"),
            "posture": sufficiency.get("final_answer_posture"),
            "missing": sufficiency.get("missing_required_obligations"),
            "partial": sufficiency.get("partial_required_obligations"),
            "reasons": sufficiency.get("readiness_reasons"),
            "graph": sufficiency.get("multicomponent_graph_consumption"),
            "ledger_requirements": kernel.state.evidence_ledger.to_projection()
            .to_dict()
            .get("source_requirements"),
        },
        sort_keys=True,
    )
    assert captured["author_handoff_called"] is True
    normalized = " ".join(outcome.report.split())
    assert "$1,200" in normalized
    assert "at or below $60,000" in normalized
    assert "paper application" in normalized
    assert "may file online" in normalized
    assert "account number" in normalized
    assert any(
        "verified two-part Northstar benefit" in str(item.get("claim_text") or "")
        for item in packet.admitted_synthesis_entries
    )
    assert harness.forbidden_live_calls == []


def test_dynamic_northstar_terminal_blocker_uses_ordinary_finalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_direct_semantic_producer(monkeypatch)
    harness = DynamicNorthstarHarness(tmp_path, readable_recovery=False)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_SUFFICIENCY, HANDOFF_PACKET, HANDOFF_AUTHOR),
    )

    try:
        outcome = orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-07-11",
                session_id="dynamic-northstar-blocked-session",
                run_id="dynamic-northstar-blocked-run",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )
    except Exception as exc:
        kernel = captured.get("run_kernel")
        pytest.fail(
            json.dumps(
                {
                    "error": str(exc),
                    "sufficiency": captured.get("sufficiency_projection"),
                    "canonical_outcome": (
                        kernel.state.projections.get(
                            "multicomponent_recovery_outcome"
                        )
                        if kernel is not None
                        else None
                    ),
                    "authorization": (
                        kernel.state.projections.get(
                            "multicomponent_missing_component_recovery_authorization"
                        )
                        if kernel is not None
                        else None
                    ),
                },
                sort_keys=True,
            )
        )

    kernel = captured["run_kernel"]
    graph = kernel.state.projections["multicomponent_component_work_graph_v1"]
    recovery = kernel.state.projections["multicomponent_dynamic_recovery"]
    canonical_outcome = kernel.state.projections[
        "multicomponent_recovery_outcome"
    ]
    assert recovery["status"] == "blocked"
    assert recovery["ordinary_acquisition_attempt_count"] == 1
    assert canonical_outcome["recovery_disposition"] == "blocked_no_candidates"
    assert canonical_outcome["ordinary_acquisition_attempt_count"] == 1
    assert canonical_outcome["observed_provider_identities"] == ["tavily"]
    assert canonical_outcome["graph_digest"] == graph["graph_digest"]
    assert "fetch_read_content_packet_ref" not in canonical_outcome
    assert "evidence_ledger_reduction_ref" not in canonical_outcome
    assert "component_admission_ref" not in canonical_outcome
    assert len(kernel.state.contract_amendment_application_history) == 1
    assert len(graph["component_nodes"]) == 4
    assert all(
        "recovered" not in str(item["component_id"])
        for item in graph["component_nodes"]
    )
    assert graph["graph_status"] == "challenged_synthesis"
    consumption = captured["sufficiency_projection"][
        "multicomponent_graph_consumption"
    ]
    assert consumption["graph_contract_current"] is False
    assert consumption["admitted_synthesis_entries"] == []
    assert captured["packet_handoff_called"] is True
    assert captured["author_handoff_called"] is True
    assert "unresolved" in " ".join(outcome.report.split()).casefold()
    assert len(
        [
            call
            for call in harness.search_calls
            if call.get("provider_role") == "multicomponent_recovery_diagnostic"
        ]
    ) == 1


def test_dynamic_northstar_scope_broadening_requires_confirmation_without_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_direct_semantic_producer(monkeypatch)
    harness = DynamicNorthstarHarness(tmp_path, broadening_proposal=True)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_SUFFICIENCY, HANDOFF_PACKET, HANDOFF_AUTHOR),
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-11",
            session_id="dynamic-northstar-confirmation-session",
            run_id="dynamic-northstar-confirmation-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    kernel = captured["run_kernel"]
    recovery = kernel.state.projections["multicomponent_dynamic_recovery"]
    canonical_outcome = kernel.state.projections[
        "multicomponent_recovery_outcome"
    ]
    assert recovery["status"] == "blocked"
    assert recovery["requires_user_confirmation"] is True
    assert recovery["ordinary_acquisition_attempt_count"] == 0
    assert canonical_outcome["recovery_disposition"] == (
        "blocked_requires_user_confirmation"
    )
    assert canonical_outcome["ordinary_acquisition_attempt_count"] == 0
    assert canonical_outcome["observed_provider_identities"] == []
    assert "amendment_record_id" not in canonical_outcome
    assert "ordinary_search_planner_ref" not in canonical_outcome
    assert kernel.state.current_answer_contract == {}
    assert kernel.state.contract_amendment_application_history == []
    assert not any(
        call.get("provider_role") == "multicomponent_recovery_diagnostic"
        for call in harness.search_calls
    )
    assert captured["packet_handoff_called"] is True
    assert captured["author_handoff_called"] is True
    assert "unresolved" in " ".join(outcome.report.split()).casefold()


def test_real_ordinary_dispatcher_recovers_northstar_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_direct_semantic_producer(monkeypatch)
    harness = RealRecoveryDispatcherNorthstarHarness(tmp_path)
    provider_calls: list[dict[str, object]] = []

    def tavily_stub(query: str, **kwargs):
        provider_calls.append({"query": query, "kwargs": dict(kwargs)})
        return (
            [
                {
                    "title": "Northstar bonus claimant paper application rule",
                    "url": "https://www.irs.gov/northstar-fictional-paper-rule",
                    "raw_content": (
                        "The fictional Northstar program rule states that an "
                        "applicant claiming the income-based bonus must submit "
                        "the paper application. This bounded text is deliberately "
                        "long enough to travel through the ordinary snippet "
                        "construction path without any live provider call."
                    ),
                    "snippet": (
                        "Northstar income-bonus claimants must submit the paper "
                        "application."
                    ),
                    "credibility": 4,
                    "source_class": "legal_or_regulatory_text",
                    "currentness_signal": "current",
                    "eligible_for_stronger_obligation": True,
                }
            ],
            [],
        )

    monkeypatch.setattr(product_pipeline, "search_web_results", tavily_stub)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-11",
            session_id="dynamic-northstar-real-dispatch-session",
            run_id="dynamic-northstar-real-dispatch-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    kernel = captured["run_kernel"]
    canonical = kernel.state.projections["multicomponent_recovery_outcome"]
    graph = kernel.state.projections["multicomponent_component_work_graph_v1"]
    assert len(provider_calls) == 1
    assert "paper" in str(provider_calls[0]["query"]).casefold()
    assert canonical["observed_provider_identities"] == ["tavily"]
    assert canonical["search_result_candidate_packet_ref"]["candidate_count"] == 1
    assert canonical["fetch_read_content_packet_ref"]["packet_id"]
    assert canonical["evidence_ledger_reduction_ref"]["action_id"]
    assert canonical["evidence_ledger_reduction_ref"]["observation_id"]
    assert canonical["component_admission_ref"]["component_id"].startswith(
        "component:recovered:"
    )
    assert graph["graph_status"] == "ready"
    assert len(graph["component_nodes"]) == 5
    assert captured["author_handoff_called"] is True
    normalized = " ".join(outcome.report.split())
    assert "$1,200" in normalized
    assert "at or below $60,000" in normalized
    assert "paper application" in normalized
    assert "may file online" in normalized


def test_real_ordinary_dispatcher_empty_result_reaches_canonical_terminal_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_direct_semantic_producer(monkeypatch)
    harness = RealRecoveryDispatcherNorthstarHarness(
        tmp_path,
        readable_recovery=False,
    )
    provider_calls: list[str] = []

    def empty_tavily_stub(query: str, **_kwargs):
        provider_calls.append(query)
        return [], []

    monkeypatch.setattr(
        product_pipeline,
        "search_web_results",
        empty_tavily_stub,
    )
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-11",
            session_id="dynamic-northstar-real-empty-session",
            run_id="dynamic-northstar-real-empty-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    kernel = captured["run_kernel"]
    canonical = kernel.state.projections["multicomponent_recovery_outcome"]
    graph = kernel.state.projections["multicomponent_component_work_graph_v1"]
    assert len(provider_calls) == 1
    assert canonical["recovery_disposition"] == "blocked_no_candidates"
    assert canonical["ordinary_acquisition_attempt_count"] == 1
    assert canonical["observed_provider_identities"] == ["tavily"]
    assert canonical["search_result_candidate_packet_ref"]["candidate_count"] == 0
    assert "fetch_read_content_packet_ref" not in canonical
    assert "component_admission_ref" not in canonical
    assert len(graph["component_nodes"]) == 4
    assert all(
        "recovered" not in str(item["component_id"])
        for item in graph["component_nodes"]
    )
    assert graph["graph_status"] == "challenged_synthesis"
    assert captured["sufficiency_projection"]["decision"] == (
        "partial_answer_authorized"
    )
    assert captured["author_handoff_called"] is True
    assert "unresolved" in " ".join(outcome.report.split()).casefold()


def test_same_source_class_unrelated_obligation_remains_unsatisfied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_direct_semantic_producer(monkeypatch)
    harness = DynamicNorthstarHarness(tmp_path)
    unrelated_id = "source_obligation:unrelated:legal_filing_record"
    original_promote = recovery_runtime._promote_recovery_candidate_custody

    def promote_with_unrelated_requirement(*, run_kernel, **kwargs):
        payload = {
            "observation_id": (
                f"{run_kernel.state.run_id}:unrelated-same-class-obligation"
            ),
            "observation_source": "test_exact_unrelated_source_obligation",
            "requirements": [
                {
                    "requirement_id": unrelated_id,
                    "requirement_kind": "bounded_current_source_support",
                    "origin_ref": "unrelated_exact_source_obligation",
                    "component_id": "component:unrelated:filing-record",
                    "source_obligation_id": unrelated_id,
                    "run_id": run_kernel.state.run_id,
                    "request_id": run_kernel.state.request_id,
                    "answer_contract_version": run_kernel.state.current_answer_contract[
                        "accepted_contract_version"
                    ],
                    "answer_contract_digest": run_kernel.state.current_answer_contract[
                        "accepted_contract_digest"
                    ],
                    "required_source_class": "legal_or_regulatory_text",
                    "required_evidence_material_type": "answer_bearing_content",
                }
            ],
            "candidates": [],
            "requirement_links": [],
        }
        action = run_kernel.authorize_evidence_ledger_reduction(
            inputs={
                "observation_source": payload["observation_source"],
                "candidate_count": 0,
                "requirement_count": 1,
            }
        )
        run_kernel.reduce(
            execute_evidence_ledger_reduction_action(
                action,
                payload=payload,
            ).observation
        )
        return original_promote(run_kernel=run_kernel, **kwargs)

    monkeypatch.setattr(
        recovery_runtime,
        "_promote_recovery_candidate_custody",
        promote_with_unrelated_requirement,
    )
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-11",
            session_id="dynamic-northstar-unrelated-session",
            run_id="dynamic-northstar-unrelated-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    kernel = captured["run_kernel"]
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirements = {
        item["requirement_id"]: item
        for item in ledger["source_requirements"]
    }
    recovered_id = next(
        requirement_id
        for requirement_id in requirements
        if requirement_id.startswith("source_obligation:recovered:")
    )
    recovered = requirements[recovered_id]
    unrelated = requirements[unrelated_id]
    assert recovered["required_source_class"] == unrelated["required_source_class"]
    assert recovered["status"] == "satisfied"
    assert recovered["linked_candidate_ids"]
    assert unrelated["status"] == "unsatisfied"
    assert unrelated["linked_candidate_ids"] == []
    assert not set(recovered["linked_candidate_ids"]) & set(
        unrelated["linked_candidate_ids"]
    )
    missing_ids = {
        item["requirement_id"]
        for item in captured["sufficiency_projection"][
            "missing_required_obligations"
        ]
    }
    assert unrelated_id in missing_ids


def _run_terminal_northstar_with_sufficiency_mutation(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate,
    suffix: str,
):
    _forbid_direct_semantic_producer(monkeypatch)
    harness = DynamicNorthstarHarness(tmp_path, readable_recovery=False)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    captured_sufficiency = orchestrator.execute_sufficiency_judgment_handoff_from_scope

    def mutate_before_sufficiency(run_kernel, runtime_scope, **kwargs):
        mutate(run_kernel)
        return captured_sufficiency(run_kernel, runtime_scope, **kwargs)

    monkeypatch.setattr(
        orchestrator,
        "execute_sufficiency_judgment_handoff_from_scope",
        mutate_before_sufficiency,
    )
    outcome = None
    error = None
    try:
        outcome = orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-07-11",
                session_id=f"dynamic-northstar-negative-{suffix}-session",
                run_id=f"dynamic-northstar-negative-{suffix}-run",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )
    except orchestrator.PipelineError as exc:
        error = exc
    return outcome, error, captured


def test_adapter_trace_status_and_attempt_count_cannot_change_partial_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forge_trace(run_kernel):
        trace = run_kernel.state.projections["multicomponent_dynamic_recovery"]
        trace["status"] = "acquired"
        trace["ordinary_acquisition_attempt_count"] = 999
        trace["final_answer_authority"] = True

    outcome, error, captured = _run_terminal_northstar_with_sufficiency_mutation(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        mutate=forge_trace,
        suffix="trace-ignored",
    )
    assert error is None
    assert outcome is not None
    assert captured["sufficiency_projection"]["decision"] == (
        "partial_answer_authorized"
    )
    assert captured["author_handoff_called"] is True


@pytest.mark.parametrize("posture", ["forged_adapter", "missing_canonical"])
def test_adapter_projection_or_missing_canonical_cannot_authorize_partial_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    posture: str,
) -> None:
    def remove_canonical(run_kernel):
        run_kernel.state.projections.pop("multicomponent_recovery_outcome")
        if posture == "forged_adapter":
            run_kernel.state.projections["multicomponent_dynamic_recovery"] = {
                "owner": "OrdinaryMulticomponent.DynamicRecoveryAdapter",
                "canonical_state": True,
                "trace_only": False,
                "final_answer_authority": True,
                "status": "blocked",
                "ordinary_acquisition_attempt_count": 1,
                "direct_semantic_producer_used": False,
            }

    outcome, error, captured = _run_terminal_northstar_with_sufficiency_mutation(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        mutate=remove_canonical,
        suffix=posture,
    )
    assert outcome is None
    assert isinstance(error, orchestrator.PipelineError)
    assert captured["sufficiency_projection"]["final_answer_allowed"] is False


@pytest.mark.parametrize(
    ("case", "field", "replacement"),
    [
        ("cross-run", "run_id", "forged-other-run"),
        ("wrong-request", "request_id", "forged-other-request"),
        (
            "wrong-recovery-digest",
            "recovery_authorization_digest",
            "forged-recovery-digest",
        ),
        ("wrong-proposal-digest", "proposal_digest", "forged-proposal-digest"),
        (
            "wrong-contract-version",
            "current_answer_contract_version",
            "forged-contract-version",
        ),
        (
            "wrong-contract-digest",
            "current_answer_contract_digest",
            "forged-contract-digest",
        ),
        ("wrong-graph-id", "graph_id", "forged-graph-id"),
        ("wrong-graph-revision", "graph_revision", 999),
        ("wrong-graph-digest", "graph_digest", "forged-graph-digest"),
        (
            "wrong-graph-contract-version",
            "graph_answer_contract_version",
            "forged-graph-contract-version",
        ),
        (
            "wrong-graph-contract-digest",
            "graph_answer_contract_digest",
            "forged-graph-contract-digest",
        ),
        (
            "diagnostic-role-as-provider",
            "observed_provider_identities",
            ["multicomponent_recovery_diagnostic"],
        ),
    ],
)
def test_stale_or_cross_bound_canonical_outcome_cannot_authorize_partial_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    field: str,
    replacement,
) -> None:
    def forge_canonical(run_kernel):
        canonical = run_kernel.state.projections[
            "multicomponent_recovery_outcome"
        ]
        canonical[field] = replacement
        canonical["outcome_digest"] = safe_packet_digest(
            {
                key: value
                for key, value in canonical.items()
                if key != "outcome_digest"
            }
        )

    outcome, error, captured = _run_terminal_northstar_with_sufficiency_mutation(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        mutate=forge_canonical,
        suffix=case,
    )
    assert outcome is None
    assert isinstance(error, orchestrator.PipelineError)
    assert captured["sufficiency_projection"]["final_answer_allowed"] is False


def test_evidence_ledger_rejects_conflicting_exact_recovery_lineage() -> None:
    ledger = EvidenceLedger()
    base = {
        "requirement_id": "source_obligation:recovered:exact-lineage",
        "requirement_kind": "bounded_current_source_support",
        "component_id": "component:recovered:exact-lineage",
        "source_obligation_id": "source_obligation:recovered:exact-lineage",
        "run_id": "run:exact-lineage",
        "request_id": "request:exact-lineage",
        "answer_contract_version": "contract:2",
        "answer_contract_digest": "contract-digest:2",
        "recovery_authorization_id": "recovery:exact-lineage",
        "recovery_authorization_digest": "recovery-digest:exact-lineage",
    }
    ledger.reduce_observation(
        {
            "observation_id": "lineage:initial",
            "observation_source": "test",
            "requirements": [base],
        }
    )
    with pytest.raises(ValueError, match="component_id"):
        ledger.reduce_observation(
            {
                "observation_id": "lineage:conflict",
                "observation_source": "test",
                "requirements": [
                    {
                        **base,
                        "component_id": "component:unrelated:same-class",
                    }
                ],
            }
        )
