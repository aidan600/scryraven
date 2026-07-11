"""PRODUCT-PATH-REGRESSION: bounded ordinary dynamic graph recovery."""

from __future__ import annotations

import json

from core.component_work_graph_v1 import (
    graph_with_scrutineer,
    reduce_component_work_graph_v1,
    scrutineer_input_packet,
)
from core.multicomponent_role_runtime import (
    ROLE_SCRUTINEER,
    execute_multicomponent_role_call,
)
from core.run_kernel import Observation, RunStageStatus
from tests.test_multicomponent_component_work_graph_v1 import (
    _flat_graph,
    _validate_synthesis,
)


def _challenged_graph_with_missing_component_proposal():
    kernel, graph = _flat_graph(caveats=("A filing-route rule remains material.",))
    graph = _validate_synthesis(kernel, graph, "E")
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
                "target_key": target["target_key"],
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
                "scope_posture": (
                    "required_to_fulfill_existing_accepted_user_obligation"
                ),
                "bounded_search_hints": ["bonus paper application rule"],
                "source_requirement_hints": ["official program rule"],
                "caveats": ["Fictional offline scenario only."],
                "nonclaims": ["No general filing rule is claimed."],
            }
        ],
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

