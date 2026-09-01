"""PRODUCT-PATH-REGRESSION: exact SearchOS Component Analyst evidence sets.

Classification: one N=2 success proof is a durable ``semantic_lane`` guard for
the SearchOS receiver and RunKernel admission seam; the remaining mutation
matrix stays ``phase_focus`` because it is a detailed custody contract.  This
is not a ``fast_pr`` sentinel: it drives the complete local ordinary product
path and intentionally costs several seconds.  It can be demoted only if that
ordinary receiver/admission path is retired; it can be expanded only with a
new exact-set consumer contract.

Proof class: offline_product_path_proof. Surface: SearchOS's ordered material
handoff, receiver verification, Component Analyst safe packet, scheduler
dispatch, and RunKernel admission. The fixture uses only deterministic local
transports; it never invokes a provider, model, search, or READ service.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, Mapping

import pytest

import core.ordinary_multicomponent_synthesis_runtime as multicomponent
import core.pipeline_orchestrator as pipeline_orchestrator
import tests.helpers.offline_ordinary_pipeline as offline_pipeline
from core.component_analyst_evidence_set import (
    ComponentAnalystEvidenceSetError,
    build_component_analyst_evidence_set,
    component_analyst_evidence_set_members_for_aliases,
    component_analyst_evidence_set_model_projection,
    validate_component_analyst_evidence_set,
)
from core.evidence_ledger import EvidenceCandidate
from core.multicomponent_component_admission import component_analyst_input_packet
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_SYSTEM_PROMPTS,
)
from core.quantitative_specialist_product_activation import (
    build_component_quantitative_source_catalog,
    source_bound_quantitative_calculation_adapter,
)
from core.run_kernel import RunKernel, RunKernelTransitionError
from core.searchos_slice_a_product_runtime import SEARCHOS_JUDGMENT_SYSTEM_PROMPT
from tests.fixtures.component_analyst_evidence_sets import (
    component_analyst_evidence_set_fixture,
)
from tests.helpers.offline_ordinary_pipeline import (
    PostRetirementOrdinaryPipelineHarness,
    run_post_retirement_ordinary_pipeline,
)


def _second_read_decision(payload: Mapping[str, Any]) -> str:
    """Return one lawful extra READ request for Component 2's exact slot."""

    authorized = dict(payload.get("authorized_request") or payload)
    contract = dict(payload.get("decision_contract") or {})
    actions = dict(contract.get("actions") or {})
    action_contract = dict(actions["REQUEST_READ_PAGE"])
    options = [
        dict(item)
        for item in authorized.get("candidate_use_options") or ()
        if isinstance(item, Mapping)
    ]
    custody_refs = [
        dict(item)
        for item in authorized.get("read_custody_refs") or ()
        if isinstance(item, Mapping)
    ]
    assert options and custody_refs
    decision: dict[str, Any] = {
        "schema_version": contract["decision_schema_version"],
        "action": "REQUEST_READ_PAGE",
        "candidate_use_option_id": str(
            dict(options[0]["candidate_use_option_ref"])[
                "candidate_use_option_id"
            ]
        ),
        "reason": "offline second exact current material for Component 2",
    }
    for output_field, request_path in dict(
        contract.get("copy_exactly_from_authorized_request") or {}
    ).items():
        if request_path == "slot_ref.slot_id":
            decision[output_field] = dict(authorized["slot_ref"])["slot_id"]
        else:
            decision[output_field] = authorized[request_path]
    if action_contract["read_custody_assessments_mode"] == (
        "required_exact_if_current_custody_else_absent"
    ):
        decision["read_custody_assessments"] = [
            {
                "read_custody_material_id": item["read_custody_material_id"],
                "reason_code": "required_information_absent",
            }
            for item in custody_refs
        ]
    return json.dumps(decision)


def _run_mixed_cardinality_case(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    support_mode: Literal["first", "both", "reverse_both", "unknown"],
    receiver_mutation: Literal["missing", "extra", "stale", "cross"] | None = None,
) -> tuple[
    Any,
    PostRetirementOrdinaryPipelineHarness,
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Drive the ordinary two-component path with Component 2 receiving B,C."""

    class _MixedCardinalityHarness(PostRetirementOrdinaryPipelineHarness):
        def ask_model(
            self, prompt: str, system_prompt: str, **kwargs: Any
        ) -> str:
            response = super().ask_model(prompt, system_prompt, **kwargs)
            if system_prompt.startswith(SEARCHOS_JUDGMENT_SYSTEM_PROMPT):
                payload = json.loads(prompt)
                authorized = dict(payload.get("authorized_request") or payload)
                component = dict(
                    dict(payload.get("active_need") or {}).get("component")
                    or {}
                )
                custody_refs = list(authorized.get("read_custody_refs") or ())
                options = list(authorized.get("candidate_use_options") or ())
                if (
                    component.get("component_id") == "component-2"
                    and len(custody_refs) == 1
                    and options
                    and "REQUEST_READ_PAGE"
                    in set(authorized.get("legal_actions") or ())
                ):
                    return _second_read_decision(payload)
                return response
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
                payload = json.loads(prompt)
                component = dict(payload.get("component_ref") or {})
                if component.get("component_id") != "component-2":
                    return response
                aliases = [
                    str(dict(member).get("local_evidence_alias") or "")
                    for member in dict(
                        payload.get("component_evidence_set") or {}
                    ).get("members")
                    or ()
                    if str(dict(member).get("local_evidence_alias") or "")
                ]
                result = json.loads(response)
                result["supporting_evidence_aliases"] = (
                    aliases
                    if support_mode == "both"
                    else list(reversed(aliases))
                    if support_mode == "reverse_both"
                    else ["component_evidence_unknown"]
                    if support_mode == "unknown"
                    else [aliases[0]]
                )
                return json.dumps(result)
            return response

    monkeypatch.setattr(
        offline_pipeline,
        "PostRetirementOrdinaryPipelineHarness",
        _MixedCardinalityHarness,
    )
    packet_contexts: list[dict[str, Any]] = []
    admission_calls: list[dict[str, Any]] = []
    original_initialize = RunKernel.initialize_multicomponent_graph_scheduler
    original_admission = multicomponent.execute_multicomponent_component_admission
    original_receiver = (
        pipeline_orchestrator.execute_ordinary_semantic_or_multicomponent_handoff_from_scope
    )

    def capture_initialize(self: Any, **kwargs: Any) -> Any:
        result = original_initialize(self, **kwargs)
        packet_contexts.append(
            {
                "packets": deepcopy(
                    dict(kwargs["component_analyst_input_packets"])
                ),
                "evidence_sets": deepcopy(
                    dict(kwargs["component_analyst_evidence_sets"])
                ),
            }
        )
        return result

    def capture_admission(**kwargs: Any) -> Any:
        admission_calls.append(
            {
                "component_id": kwargs["component_id"],
                "semantic_observation": deepcopy(
                    kwargs.get("semantic_observation")
                ),
                "sanitized_content_references": deepcopy(
                    kwargs.get("sanitized_content_references") or []
                ),
            }
        )
        return original_admission(**kwargs)

    def mutate_receiver(
        run_kernel: Any,
        runtime_scope: Mapping[str, Any],
        **kwargs: Any,
    ) -> Any:
        if (
            receiver_mutation is None
            or kwargs.get("allow_searchos_component_receiver") is not True
        ):
            return original_receiver(run_kernel, runtime_scope, **kwargs)
        result = runtime_scope["searchos_slice_a_result"]
        materials = [
            deepcopy(dict(item)) for item in result.searchos_semantic_material
        ]
        component_one = [
            item
            for item in materials
            if item["searchos_slot_ref"]["component_id"] == "component-1"
        ]
        component_two = [
            item
            for item in materials
            if item["searchos_slot_ref"]["component_id"] == "component-2"
        ]
        assert len(component_one) == 1
        assert len(component_two) == 2
        if receiver_mutation == "missing":
            materials.remove(component_two[-1])
        elif receiver_mutation == "extra":
            materials.append(deepcopy(component_two[-1]))
        elif receiver_mutation == "stale":
            component_two[-1]["bounded_text_digest"] = "0" * 64
        elif receiver_mutation == "cross":
            materials[materials.index(component_two[-1])] = deepcopy(component_one[0])
        else:  # pragma: no cover - the literal type closes this branch
            raise AssertionError(receiver_mutation)
        return original_receiver(
            run_kernel,
            {
                **dict(runtime_scope),
                "searchos_slice_a_result": replace(
                    result,
                    searchos_semantic_material=tuple(materials),
                ),
            },
            **kwargs,
        )

    monkeypatch.setattr(
        RunKernel,
        "initialize_multicomponent_graph_scheduler",
        capture_initialize,
    )
    monkeypatch.setattr(
        multicomponent,
        "execute_multicomponent_component_admission",
        capture_admission,
    )
    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
        mutate_receiver,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="Compare Alpha and Beta current official operating rates.",
        core_topic="Alpha and Beta operating rates",
        primary_entity="Alpha",
        query_type="comparison",
        router_entities=("Alpha", "Beta"),
        researcher_queries=(
            "Alpha current official operating rate",
            "Beta current official operating rate",
        ),
    )
    return outcome, harness, packet_contexts, admission_calls


def test_searchos_exact_mixed_cardinality_reaches_component_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness, packet_contexts, admission_calls = _run_mixed_cardinality_case(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        support_mode="first",
    )

    assert outcome.terminal_status in {"completed", "blocked"}
    assert len(packet_contexts) == 1
    context = packet_contexts[0]
    packets = context["packets"]
    evidence_sets = context["evidence_sets"]
    assert set(packets) == set(evidence_sets) == {"component-1", "component-2"}
    assert [
        member["local_evidence_alias"]
        for member in evidence_sets["component-1"]["members"]
    ] == ["component_evidence_01"]
    assert [
        member["local_evidence_alias"]
        for member in evidence_sets["component-2"]["members"]
    ] == ["component_evidence_01", "component_evidence_02"]
    assert len(packets["component-1"]["component_evidence_set"]["members"]) == 1
    component_two_model_members = packets["component-2"][
        "component_evidence_set"
    ]["members"]
    assert [item["local_evidence_alias"] for item in component_two_model_members] == [
        "component_evidence_01",
        "component_evidence_02",
    ]
    assert all("evidence_ref_id" not in item for item in component_two_model_members)
    assert all("bounded_text_digest" not in item for item in component_two_model_members)
    assert harness.model_system_prompts.count(
        ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]
    ) == 2

    admitted_by_component = {
        item["component_id"]: item for item in admission_calls
    }
    assert set(admitted_by_component) == {"component-1", "component-2"}
    component_two_observation = admitted_by_component["component-2"][
        "semantic_observation"
    ]
    component_two_refs = [
        member["code_binding"]["evidence_ref_id"]
        for member in evidence_sets["component-2"]["members"]
    ]
    assert component_two_observation["evidence_refs"] == [component_two_refs[0]]
    assert [
        item["evidence_ref_id"]
        for item in admitted_by_component["component-2"][
            "sanitized_content_references"
        ]
    ] == [component_two_refs[0]]


def test_component_analyst_can_nominate_both_exact_members(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _outcome, _harness, packet_contexts, admission_calls = (
        _run_mixed_cardinality_case(
            tmp_path=tmp_path,
            monkeypatch=monkeypatch,
            support_mode="both",
        )
    )

    component_two_set = packet_contexts[0]["evidence_sets"]["component-2"]
    expected_refs = [
        member["code_binding"]["evidence_ref_id"]
        for member in component_two_set["members"]
    ]
    component_two_admission = next(
        item for item in admission_calls if item["component_id"] == "component-2"
    )
    assert component_two_admission["semantic_observation"]["evidence_refs"] == (
        expected_refs
    )
    assert [
        item["evidence_ref_id"]
        for item in component_two_admission["sanitized_content_references"]
    ] == expected_refs


def test_reversed_lawful_support_aliases_reach_admission_in_canonical_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _outcome, _harness, packet_contexts, admission_calls = (
        _run_mixed_cardinality_case(
            tmp_path=tmp_path,
            monkeypatch=monkeypatch,
            support_mode="reverse_both",
        )
    )

    component_two_set = packet_contexts[0]["evidence_sets"]["component-2"]
    expected_refs = [
        member["code_binding"]["evidence_ref_id"]
        for member in component_two_set["members"]
    ]
    component_two_admission = next(
        item for item in admission_calls if item["component_id"] == "component-2"
    )
    assert component_two_admission["semantic_observation"]["evidence_refs"] == (
        expected_refs
    )
    assert [
        item["evidence_ref_id"]
        for item in component_two_admission["sanitized_content_references"]
    ] == expected_refs


def test_reversed_lawful_support_aliases_rebind_in_canonical_member_order() -> None:
    _kernel, _packets, evidence_sets, _contract = (
        _scheduler_inputs_with_exact_sets()
    )
    component_two_set = evidence_sets["component-2"]
    aliases = [
        member["local_evidence_alias"]
        for member in component_two_set["members"]
    ]

    selected = component_analyst_evidence_set_members_for_aliases(
        component_two_set,
        list(reversed(aliases)),
    )
    assert [member["local_evidence_alias"] for member in selected] == aliases


@pytest.mark.parametrize(
    ("aliases", "message"),
    (
        (["component_evidence_unknown"], "unknown supplied member"),
        (
            ["component_evidence_01", "component_evidence_01"],
            "repeat one supplied member",
        ),
        ([], "aliases are missing"),
    ),
)
def test_component_analyst_support_alias_membership_rejects_unknown_duplicate_and_empty(
    aliases: list[str],
    message: str,
) -> None:
    _kernel, _packets, evidence_sets, _contract = (
        _scheduler_inputs_with_exact_sets()
    )
    with pytest.raises(ComponentAnalystEvidenceSetError, match=message):
        component_analyst_evidence_set_members_for_aliases(
            evidence_sets["component-2"],
            aliases,
        )


def test_unknown_component_analyst_alias_fails_closed_before_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness, packet_contexts, admission_calls = _run_mixed_cardinality_case(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        support_mode="unknown",
    )

    assert packet_contexts
    assert outcome.terminal_status == "blocked"
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST] in harness.model_system_prompts
    assert all(item["component_id"] != "component-2" for item in admission_calls)


@pytest.mark.parametrize("mutation", ("missing", "extra", "stale", "cross"))
def test_multimaterial_receiver_rejects_missing_extra_stale_and_cross_component_members(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: Literal["missing", "extra", "stale", "cross"],
) -> None:
    outcome, harness, packet_contexts, admission_calls = _run_mixed_cardinality_case(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        support_mode="first",
        receiver_mutation=mutation,
    )

    assert outcome.terminal_status == "blocked"
    assert not packet_contexts
    assert not admission_calls
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST] not in harness.model_system_prompts


def _scheduler_inputs_with_exact_sets() -> tuple[
    RunKernel, dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]
]:
    kernel = RunKernel.start(
        run_id="multimaterial-scheduler-run",
        request_id="multimaterial-scheduler-request",
    )
    components = [
        {
            "component_id": "component-1",
            "component_revision": "1",
            "component_digest": "component-1-digest",
            "user_facing_label": "Component 1",
            "user_facing_question": "What does material A establish?",
            "mandatory_caveats": [],
            "prohibited_upgrades": [],
        },
        {
            "component_id": "component-2",
            "component_revision": "1",
            "component_digest": "component-2-digest",
            "user_facing_label": "Component 2",
            "user_facing_question": "What do materials B and C establish?",
            "mandatory_caveats": [],
            "prohibited_upgrades": [],
        },
    ]
    contract = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": kernel.state.run_id,
        "request_id": kernel.state.request_id,
        "accepted_contract_version": "v1",
        "accepted_contract_digest": "multimaterial-contract-digest",
        "parent_question_meaning_record_id": "qmr:multimaterial",
        "parent_question_meaning_record_digest": "qmr:multimaterial-digest",
        "accepted_answer_component_count": 2,
        "accepted_answer_component_refs": components,
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": "Relate the exact components.",
        },
    }
    kernel.state.initial_answer_contract = deepcopy(contract)
    kernel.state.initial_answer_contract_projection = {"accepted": True}
    evidence_sets = {
        "component-1": component_analyst_evidence_set_fixture(
            {
                "evidence_ref_id": "evidence:a",
                "bounded_text": "Material A states 10 USD.",
            }
        ),
        "component-2": component_analyst_evidence_set_fixture(
            {
                "evidence_ref_id": "evidence:b",
                "bounded_text": "Material B states 20 USD.",
            },
            {
                "evidence_ref_id": "evidence:c",
                "bounded_text": "Material C states 30 USD.",
            },
        ),
    }
    for evidence_set in evidence_sets.values():
        for member in evidence_set["members"]:
            candidate_id = member["code_binding"]["evidence_ref_id"]
            kernel.state.evidence_ledger.candidates[candidate_id] = EvidenceCandidate(
                candidate_id=candidate_id,
                readable_status="readable",
            )
    packets = {
        component["component_id"]: component_analyst_input_packet(
            run_id=kernel.state.run_id,
            request_id=kernel.state.request_id,
            accepted_contract=contract,
            component_ref=component,
            component_evidence_set=evidence_sets[component["component_id"]],
        )
        for component in components
    }
    return kernel, packets, evidence_sets, contract


def _rebuild_evidence_set_with_candidate_fact(
    evidence_set: Mapping[str, Any],
    *,
    member_index: int,
    field: str,
    value: Any,
) -> dict[str, Any]:
    """Create one newly valid exact set with a changed retained snapshot fact."""

    sources: list[dict[str, Any]] = []
    for index, member in enumerate(evidence_set["members"]):
        candidate_record = deepcopy(member["candidate_record"])
        if index == member_index:
            candidate_record[field] = value
        sources.append(
            {
                "evidence_ref_id": member["code_binding"]["evidence_ref_id"],
                "passage": deepcopy(member["passage"]),
                "candidate_record": candidate_record,
            }
        )
    return build_component_analyst_evidence_set(sources)


def test_retained_qualification_fact_mutation_rejects_before_scheduler_dispatch(
) -> None:
    """Reject a real later qualification input before Analyst support dispatch.

    ``eligible_for_stronger_obligation`` is consumed after Analyst support by
    the SearchOS custody qualification reducer.  The pre-repair base accepted
    this mutation because its digest did not include the retained candidate
    snapshot.  It must now fail at the evidence-set boundary.
    """

    kernel, packets, evidence_sets, _contract = _scheduler_inputs_with_exact_sets()
    component_two_set = evidence_sets["component-2"]
    base_digest = component_two_set["evidence_set_digest"]

    component_two_set["members"][0]["candidate_record"][
        "eligible_for_stronger_obligation"
    ] = True

    assert component_two_set["evidence_set_digest"] == base_digest
    with pytest.raises(
        ComponentAnalystEvidenceSetError,
        match="canonical order or identity is altered",
    ):
        validate_component_analyst_evidence_set(component_two_set)
    with pytest.raises(
        RunKernelTransitionError,
        match="canonical order or identity is altered",
    ):
        kernel.initialize_multicomponent_graph_scheduler(
            component_analyst_input_packets=packets,
            component_analyst_evidence_sets=evidence_sets,
            requested_synthesis_directive="Relate the exact components.",
        )
    assert "multicomponent_graph_scheduler" not in kernel.state.projections


def test_scheduler_reconstruction_preserves_exact_order_and_rejects_reorder(
) -> None:
    kernel, packets, evidence_sets, _contract = _scheduler_inputs_with_exact_sets()
    kernel.initialize_multicomponent_graph_scheduler(
        component_analyst_input_packets=packets,
        component_analyst_evidence_sets=evidence_sets,
        requested_synthesis_directive="Relate the exact components.",
    )
    retained = kernel.state.multicomponent_scheduler_context
    assert retained["component_analyst_input_packets"] == packets
    assert retained["component_analyst_evidence_sets"] == evidence_sets

    reordered_kernel, reordered_packets, reordered_sets, _contract = (
        _scheduler_inputs_with_exact_sets()
    )
    original_members = reordered_sets["component-2"]["members"]
    reordered_sets["component-2"] = build_component_analyst_evidence_set(
        [
            {
                "evidence_ref_id": member["code_binding"]["evidence_ref_id"],
                "passage": member["passage"],
                "candidate_record": member["candidate_record"],
            }
            for member in reversed(original_members)
        ]
    )
    with pytest.raises(
        RunKernelTransitionError,
        match="component packet is not current canonical input",
    ):
        reordered_kernel.initialize_multicomponent_graph_scheduler(
            component_analyst_input_packets=reordered_packets,
            component_analyst_evidence_sets=reordered_sets,
            requested_synthesis_directive="Relate the exact components.",
        )


def test_digest_coverage_keeps_model_projection_and_n1_shape_unchanged() -> None:
    _kernel, packets, evidence_sets, contract = _scheduler_inputs_with_exact_sets()
    original_set = evidence_sets["component-2"]
    changed_set = _rebuild_evidence_set_with_candidate_fact(
        original_set,
        member_index=0,
        field="eligible_for_stronger_obligation",
        value=True,
    )
    assert changed_set["evidence_set_digest"] != original_set["evidence_set_digest"]
    assert (
        component_analyst_evidence_set_model_projection(changed_set)
        == component_analyst_evidence_set_model_projection(original_set)
    )
    changed_packet = component_analyst_input_packet(
        run_id=packets["component-2"]["run_binding"]["run_id"],
        request_id=packets["component-2"]["run_binding"]["request_id"],
        accepted_contract=contract,
        component_ref=contract["accepted_answer_component_refs"][1],
        component_evidence_set=changed_set,
    )
    assert changed_packet == packets["component-2"]
    model_projection = changed_packet["component_evidence_set"]
    assert "evidence_set_digest" not in model_projection
    assert all(
        not {"evidence_ref_id", "candidate_record", "passage"}.intersection(member)
        for member in model_projection["members"]
    )
    model_safe_text = json.dumps(model_projection, sort_keys=True)
    assert all(
        internal_name not in model_safe_text
        for internal_name in (
            "candidate_custody_ref",
            "code_binding",
            "evidence_ref_id",
            "evidence_set_digest",
            "bounded_text_digest",
            "candidate_record",
            "passage",
        )
    )

    one_member_set = evidence_sets["component-1"]
    assert validate_component_analyst_evidence_set(one_member_set) == one_member_set
    assert component_analyst_evidence_set_model_projection(one_member_set)[
        "member_count"
    ] == 1


def test_specialist_component_aliases_bind_each_exact_member_and_reject_unknown(
) -> None:
    _kernel, packets, evidence_sets, _contract = _scheduler_inputs_with_exact_sets()
    component_packet = packets["component-2"]
    evidence_set = evidence_sets["component-2"]
    catalog = build_component_quantitative_source_catalog(
        component_ref=component_packet["component_ref"],
        component_evidence_set=evidence_set,
        include_material=True,
    )
    expected_aliases = [
        member["local_evidence_alias"] for member in evidence_set["members"]
    ]
    assert component_packet["quantitative_specialist_proposal_contract"][
        "allowed_source_local_keys"
    ] == expected_aliases
    assert [
        catalog[alias]["source_local_key"] for alias in expected_aliases
    ] == expected_aliases
    assert [
        catalog[alias]["evidence_ref"]["evidence_ref_id"]
        for alias in expected_aliases
    ] == [
        member["code_binding"]["evidence_ref_id"]
        for member in evidence_set["members"]
    ]

    result = source_bound_quantitative_calculation_adapter(
        {
            "bounded_question": "Calculate only from supplied local sources.",
            "canonical_target_ref": {
                "target_kind": "component",
                "target_key": "component-2",
                "target_revision": "1",
                "target_digest": "component-2-digest",
            },
            "capability_request": {
                "request_kind": "source_bound_calculation",
                "calculation_kind": "sum",
                "formula_label": "bounded sum",
                "expected_output_unit": "USD",
                "expected_precision_posture": "exact_as_reported",
                "operands": [
                    {
                        "local_operand_key": "b",
                        "source_local_key": "component_evidence_unknown",
                        "source_numeric_literal": "20 USD",
                        "operand_role": "term",
                    },
                    {
                        "local_operand_key": "c",
                        "source_local_key": expected_aliases[1],
                        "source_numeric_literal": "30 USD",
                        "operand_role": "term",
                    },
                ],
                "claim_binding": {
                    "proposed_result_literal": "50 USD",
                    "literal_occurrence": None,
                    "expected_result_unit": "USD",
                },
                "assumptions": [],
                "caveats": [],
            },
            "quantitative_source_catalog": catalog,
            "nominated_claim": {
                "claim_text": "The sum is 50 USD.",
                "claim_digest": "claim-digest",
                "claim_source": "component_analyst_proposal",
            },
        }
    )
    assert result["execution_posture"].startswith("blocked")
    assert result["blockers"] == ["unknown_source_local_key"]
