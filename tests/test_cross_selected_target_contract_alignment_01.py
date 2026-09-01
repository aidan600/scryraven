"""Offline proof for the selected target Cross semantic contract alignment.

Test path/node id: this module's tests
Proof class: OFFLINE_COMPONENT_PROOF
Validation bucket: phase_focus
Surface guarded: Cross semantic normalization and role-artifact hygiene
High-custody or closed-this-phase surface: D-prime and downstream synthesis stay closed
Runtime/product path guarded: experimental branch-only direct Cross boundary
Expected cost: bounded in-memory normalization and fake one-shot transport, under 10s
Promotion posture: exploratory proof only; not a fast_pr sentinel
Demotion/retirement condition: replace with ordinary product-path coverage after
the separately authorized convergence phase.
Why not fast_pr: this is a phase-local architecture proof on an experimental branch.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

from core.multicomponent_role_runtime import (
    ROLE_CROSS_COMPONENT_ANALYST,
    MulticomponentRoleRuntimeError,
    _normalize_semantic_output,
    execute_multicomponent_role_call,
    safe_packet_digest,
)
from core.run_kernel import RunKernel
from core.strict_one_shot_model_transport import (
    wrap_text_callable_as_strict_one_shot_transport,
)

RUN_ID = "cross-target-contract-run"
REQUEST_ID = "cross-target-contract-request"
SELF_AUDIT = (
    "I checked that the relationship stays within the exact admitted components "
    "and retains their material caveats, nonclaims, and blockers."
)


def _proposal(
    key: str,
    *,
    component_inputs: list[str] | None = None,
    synthesis_inputs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "synthesis_key": key,
        "claim_text": f"The supplied components establish relationship {key}.",
        "relationship_type": "bounded_relationship",
        "component_inputs": component_inputs or ["component_01", "component_02"],
        "synthesis_inputs": synthesis_inputs or [],
        "caveats": ["Only the supplied current component cases are considered."],
        "nonclaims": ["This does not establish whole-answer sufficiency."],
        "blockers": [],
    }


def _payload(proposals: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "synthesis_proposals": proposals,
        "self_audit": SELF_AUDIT,
    }


def _cross_packet() -> dict[str, Any]:
    return {
        "accepted_contract_ref": {
            "contract_id": "contract:cross-target",
            "contract_digest": "contract-digest",
        },
        "requested_synthesis_directive": "Relate the two current components.",
        "component_nodes": [
            {"component_id": "component:A"},
            {"component_id": "component:B"},
        ],
    }


def _execute(payload: dict[str, Any], *, packet: dict[str, Any] | None = None) -> dict[str, Any]:
    return execute_multicomponent_role_call(
        run_kernel=RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID),
        role=ROLE_CROSS_COMPONENT_ANALYST,
        input_packet=packet or _cross_packet(),
        strict_one_shot_transport=wrap_text_callable_as_strict_one_shot_transport(
            lambda *_args, **_kwargs: json.dumps(payload),
            canonical_provider="OpenAI",
            model="offline-cross-fixture",
        ),
        clean_json_response=lambda value: value,
        provider="OpenAI",
        model="offline-cross-fixture",
        use_reasoning=False,
        logical_evaluation_key="cross-target-contract",
    )


def test_one_and_multiple_proposals_retain_required_self_audit() -> None:
    one = _normalize_semantic_output(
        ROLE_CROSS_COMPONENT_ANALYST,
        _payload([_proposal("S1")]),
    )
    multiple = _normalize_semantic_output(
        ROLE_CROSS_COMPONENT_ANALYST,
        _payload(
            [
                _proposal("S1"),
                _proposal(
                    "S2",
                    component_inputs=["component_02"],
                    synthesis_inputs=["S1"],
                ),
            ]
        ),
    )

    assert [item["synthesis_key"] for item in one["synthesis_proposals"]] == ["S1"]
    assert [item["synthesis_key"] for item in multiple["synthesis_proposals"]] == [
        "S1",
        "S2",
    ]
    assert one["self_audit"] == SELF_AUDIT
    assert multiple["self_audit"] == SELF_AUDIT
    assert "uncertainty" not in one


@pytest.mark.parametrize("audit", [None, "", "   \n\t  ", True, 7, {}])
def test_missing_blank_or_non_string_self_audit_fails_closed(audit: Any) -> None:
    payload = _payload([_proposal("S")])
    if audit is None:
        payload.pop("self_audit")
    else:
        payload["self_audit"] = audit

    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="requires self_audit",
    ):
        _normalize_semantic_output(ROLE_CROSS_COMPONENT_ANALYST, payload)


def test_zero_proposals_is_lawful_without_manufactured_synthesis_output() -> None:
    normalized = _normalize_semantic_output(
        ROLE_CROSS_COMPONENT_ANALYST,
        _payload([]),
    )

    assert normalized == {
        "synthesis_proposals": [],
        "self_audit": SELF_AUDIT,
    }
    assert not {
        "synthesis_artifact",
        "synthesis_nodes",
        "relationship_admissions",
        "dprime_work",
        "scrutineer_work",
    } & set(normalized)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("non_array", "must be an array"),
        ("missing_claim", "requires claim, relationship, and inputs"),
        ("missing_relationship", "requires claim, relationship, and inputs"),
        ("missing_inputs", "requires claim, relationship, and inputs"),
        ("invalid_key", "synthesis_key must be a bounded local label"),
    ],
)
def test_existing_malformed_proposal_fields_still_fail_closed(
    mutation: str,
    message: str,
) -> None:
    payload: dict[str, Any] = _payload([_proposal("S")])
    if mutation == "non_array":
        payload["synthesis_proposals"] = "not-an-array"
    else:
        proposal = payload["synthesis_proposals"][0]
        if mutation == "missing_claim":
            proposal.pop("claim_text")
        elif mutation == "missing_relationship":
            proposal.pop("relationship_type")
        elif mutation == "missing_inputs":
            proposal["component_inputs"] = []
        else:
            proposal["synthesis_key"] = "not a local key"

    with pytest.raises(MulticomponentRoleRuntimeError, match=message):
        _normalize_semantic_output(ROLE_CROSS_COMPONENT_ANALYST, payload)


def test_duplicate_synthesis_keys_still_fail_closed() -> None:
    with pytest.raises(MulticomponentRoleRuntimeError, match="duplicate synthesis_key"):
        _normalize_semantic_output(
            ROLE_CROSS_COMPONENT_ANALYST,
            _payload([_proposal("S"), _proposal("S")]),
        )


def test_self_audit_prose_cannot_mint_runtime_authority() -> None:
    payload = _payload([_proposal("S")])
    payload["self_audit"] = (
        "I named artifact_id, graph_ref, and input_packet_digest only while "
        "checking overreach; this prose does not create those authorities."
    )
    packet = _cross_packet()

    artifact = _execute(payload, packet=deepcopy(packet))
    semantic_output = artifact["semantic_output"]

    assert artifact["input_packet_digest"] == safe_packet_digest(packet)
    assert semantic_output["synthesis_proposals"][0]["component_inputs"] == [
        "component:A",
        "component:B",
    ]
    assert set(semantic_output) == {"synthesis_proposals", "self_audit"}
    assert not {
        "artifact_id",
        "graph_ref",
        "input_packet_digest",
    } & set(semantic_output)
