"""PRODUCT-PATH-REGRESSION: SearchOS one-hop ordinary-product activation.

Proof class: offline_product_path_proof. Validation bucket: phase_focus. Surface:
SearchJudgment navigation selection, READ/EvidenceLedger custody, semantic component
admission, and final-answer consumption. High-custody surface: acquisition and
EvidenceLedger-to-SearchOS custody. Runtime path: ordinary offline ``run_pipeline``
with response-only model/provider fakes. Expected cost: under five seconds.
Promotion posture: remain phase_focus; this detail is not fast_pr tax. Retirement:
replace only when a later licensed recursive-navigation product path supersedes the
one-hop boundary. Why not fast_pr: it is a detailed multi-owner custody regression.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.acquisition_adapters import AcquisitionTransports
from core.multicomponent_role_runtime import ROLE_COMPONENT_ANALYST, ROLE_SYSTEM_PROMPTS
from core.run_kernel import RunKernel, RunKernelTransitionError
from core.search_planner_model_adapter import SearchPlannerModelAdapter
from core.searchos_navigation_runtime import (
    EphemeralNavigationLocatorStore,
    NavigationOption,
    NavigationRuntimeError,
)
from core.searchos_slice_a_product_runtime import (
    SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
    build_searchos_judgment_decision_contract_v1,
)
from tests.helpers.offline_ordinary_pipeline import (
    OfflineOrdinaryPipelineHarness,
    PostRetirementOrdinaryPipelineHarness,
    run_post_retirement_ordinary_pipeline,
)

PARENT_URL = "https://alpha.gov/root"
CHILD_URL = "https://alpha.gov/decisive"
SIBLING_URL = "https://alpha.gov/sibling"
LINKED_FACT = "CERULEAN RAVEN"
PARENT_MARKDOWN = (
    "NAVIGATION_PARENT_TRANSIENT_914. General background does not answer the "
    "request. [launch protocol](/decisive) [archive](/sibling)"
)
CHILD_MARKDOWN = (
    f"Alpha's official requirement is that its launch color is {LINKED_FACT}. "
    "[deeper material that must not be extracted](/depth-two)"
)


class TrackingLocatorStore(EphemeralNavigationLocatorStore):
    instances: list["TrackingLocatorStore"] = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.discarded = False
        self.__class__.instances.append(self)

    def discard_all(self) -> None:
        super().discard_all()
        self.discarded = True


def _official_requirement_planner_payload() -> dict[str, Any]:
    return {
        "question_meaning_summary": "Identify Alpha's official launch-color requirement.",
        "requested_output": "A direct answer grounded in official evidence.",
        "semantic_slots": [
            {
                "slot_id": "slot:alpha-launch-color",
                "slot_kind": "configuration",
                "status": "explicit",
                "candidate_values": ["Alpha launch color"],
                "selected_value": "Alpha launch color",
                "materiality": "material",
            }
        ],
        "answer_components": [
            {
                "component_id": "component-1",
                "component_revision": "1",
                "user_facing_label": "Alpha launch color",
                "user_facing_question": "What is Alpha's official launch-color requirement?",
                "requirement_posture": "required",
                "acceptance_criteria": ["Direct official source support."],
                "semantic_slot_ids": ["slot:alpha-launch-color"],
                "source_obligation_candidate_ids": ["obligation:official_current"],
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "dependency_component_ids": [],
                "materiality": "material",
            }
        ],
        "source_obligation_candidates": [
            {
                "candidate_id": "obligation:official_current",
                "obligation_kind": "official_current",
                "component_candidate_ids": ["component-1"],
                "strictness": "required",
            }
        ],
        "component_search_requirements": [
            {
                "component_id": "component-1",
                "requirement_id": "requirement:alpha-launch-color",
                "requirement_summary": "Find Alpha's official launch-color requirement.",
                "source_obligation_candidate_ids": ["obligation:official_current"],
                "metadata": {
                    "query_strategy_candidates": [
                        {
                            "strategy_id": "strategy:alpha-launch-color:primary",
                            "component_id": "component-1",
                            "candidate_kind": "primary",
                            "candidate_query_text": "Alpha official requirements launch color",
                            "requested_role": "official_bias",
                            "source_obligation_candidate_ids": [
                                "obligation:official_current"
                            ],
                            "distinct_need_justification": (
                                "The required component needs direct official support."
                            ),
                            "recon_requirement": {
                                "posture": "not_needed",
                                "unresolved_dimension_ids": [],
                                "candidate_queries": [],
                                "required_for_truthful_targeting": False,
                            },
                        }
                    ],
                    "provider_name_neutral": True,
                },
            }
        ],
        "material_ambiguity_posture": "none",
        "mandatory_caveats": [],
        "prohibited_upgrades": ["Do not treat planning material as evidence."],
        "normalization_obligations": [],
        "assumptions": [],
        "unsupported_or_deferred_outputs": [],
    }


def _install_tracking_store(monkeypatch: pytest.MonkeyPatch) -> None:
    from core import searchos_slice_a_product_runtime as product_runtime

    TrackingLocatorStore.instances.clear()
    monkeypatch.setattr(
        product_runtime.navigation_runtime,
        "EphemeralNavigationLocatorStore",
        TrackingLocatorStore,
    )


def _capture_extraction(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from core import searchos_slice_a_product_runtime as product_runtime

    calls: list[str] = []
    original = product_runtime.navigation_runtime.admit_navigation_options_from_markdown

    def capture(*args: Any, **kwargs: Any) -> Any:
        calls.append(str(kwargs["markdown_text"]))
        return original(*args, **kwargs)

    monkeypatch.setattr(
        product_runtime.navigation_runtime,
        "admit_navigation_options_from_markdown",
        capture,
    )
    return calls


def _install_navigation_model(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from core import pipeline_orchestrator as orchestrator

    capture: dict[str, Any] = {"final_material_ledger_projections": []}
    original = PostRetirementOrdinaryPipelineHarness.ask_model
    original_judgment_authorization = RunKernel.authorize_searchos_judgment
    original_receiver = orchestrator.execute_ordinary_semantic_or_multicomponent_handoff_from_scope
    original_sufficiency = orchestrator.execute_sufficiency_judgment_handoff_from_scope
    original_final_material = orchestrator.build_final_material_runtime_handoff_from_scope

    def ask_model(
        self: OfflineOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if system_prompt.startswith(SEARCHOS_JUDGMENT_SYSTEM_PROMPT):
            self._record_model_call(system_prompt, kwargs)
            payload = json.loads(prompt)
            inputs = self.__dict__.setdefault("navigation_model_inputs", [])
            inputs.append(deepcopy(payload))
            request = dict(payload["authorized_request"])
            contract = dict(payload["decision_contract"])
            custody_refs = list(request.get("read_custody_refs") or ())
            materials = list(payload.get("read_custody_materials") or ())
            navigation_materials = [
                dict(item)
                for item in materials
                if dict(item).get("origin") == "searchos_navigation"
            ]
            navigation_options = list(request.get("navigation_options") or ())
            common = {
                "schema_version": contract["decision_schema_version"],
                "judgment_request_id": request["judgment_request_id"],
                "judgment_request_digest": request["judgment_request_digest"],
                "slot_id": dict(request["slot_ref"])["slot_id"],
            }
            assessments = [
                {
                    "reviewed_custody_ref": ref,
                    "material_disposition": "read_insufficient",
                    "reason_code": "linked_fact_not_yet_selected",
                }
                for ref in custody_refs
            ]
            if not custody_refs:
                decision = {
                    **common,
                    "action": "REQUEST_READ_PAGE",
                    "candidate_use_option_ref": dict(
                        dict(request["candidate_use_options"][0])[
                            "candidate_use_option_ref"
                        ]
                    ),
                    "reason": "Read the admitted parent candidate.",
                }
            elif navigation_materials:
                self.__dict__["navigation_ledger_at_semantic_handoff"] = (
                    self.run_kernel.state.evidence_ledger.to_projection().to_dict()
                )
                if self.read_assessment_decision == "NAVIGATION_INSUFFICIENT":
                    slot_id = dict(request["slot_ref"])["slot_id"]
                    self.__dict__["dispositions_before_navigation_assessment"] = deepcopy(
                        self.run_kernel.state.searchos_state["slots_by_id"][slot_id][
                            "candidate_option_dispositions"
                        ]
                    )
                    self.__dict__["post_navigation_legal_actions"] = list(
                        request["legal_actions"]
                    )
                    decision = {
                        **common,
                        "action": "HANDOFF_UNRESOLVED",
                        "reason": "Fixture preserves the assessed open need.",
                        "read_custody_assessments": assessments,
                    }
                else:
                    decision = {
                        **common,
                        "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                        "read_custody_refs": [
                            dict(item["read_custody_ref"])
                            for item in navigation_materials
                        ],
                        "reason": "The linked page contains the decisive fact.",
                    }
            elif navigation_options:
                already_navigated = any(
                    item.get("action") == "REQUEST_NAVIGATE_BREADCRUMB"
                    and item.get("slot_id") == common["slot_id"]
                    for item in self.__dict__.get("navigation_decisions", [])
                )
                if (
                    self.read_assessment_decision == "NAVIGATE_THEN_UNRESOLVED"
                    and already_navigated
                ):
                    decision = {
                        **common,
                        "action": "HANDOFF_UNRESOLVED",
                        "reason": "The selected destination failed without retry.",
                        "read_custody_assessments": assessments,
                    }
                else:
                    self.__dict__["navigation_selection_input"] = deepcopy(payload)
                    decision = {
                        **common,
                        "action": "REQUEST_NAVIGATE_BREADCRUMB",
                        "navigation_candidate_ref": dict(
                            dict(navigation_options[0])["navigation_candidate_ref"]
                        ),
                        "reason": "Select the exact current breadcrumb reference.",
                        "read_custody_assessments": assessments,
                    }
            else:
                if self.read_assessment_decision == "NAVIGATE_TO_HANDOFF":
                    decision = {
                        **common,
                        "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                        "read_custody_refs": custody_refs,
                        "reason": "The existing READ custody satisfies this obligation.",
                    }
                else:
                    decision = {
                        **common,
                        "action": "HANDOFF_UNRESOLVED",
                        "reason": "The selected destination failed without retry.",
                        "read_custody_assessments": assessments,
                    }
            self.__dict__.setdefault("navigation_decisions", []).append(decision)
            return json.dumps(decision)
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            self._record_model_call(system_prompt, kwargs)
            assert LINKED_FACT in prompt
            return json.dumps(
                {
                    "claim_text": f"Alpha's official requirement is that its launch color is {LINKED_FACT}.",
                    "support_status": "supported",
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                }
            )
        return original(self, prompt, system_prompt, **kwargs)

    def capture_receiver(run_kernel: RunKernel, *args: Any, **kwargs: Any) -> Any:
        run_kernel.navigation_ledger_before_receiver = (
            run_kernel.state.evidence_ledger.to_projection().to_dict()
        )
        try:
            result = original_receiver(run_kernel, *args, **kwargs)
        except Exception as exc:
            run_kernel.navigation_receiver_errors = [str(exc)]
            raise
        run_kernel.navigation_ledger_after_receiver = (
            run_kernel.state.evidence_ledger.to_projection().to_dict()
        )
        return result

    def capture_judgment_authorization(
        run_kernel: RunKernel, *args: Any, **kwargs: Any
    ) -> Any:
        try:
            return original_judgment_authorization(run_kernel, *args, **kwargs)
        except Exception as exc:
            run_kernel.navigation_authorization_errors = [str(exc)]
            raise

    def capture_sufficiency(run_kernel: RunKernel, runtime_scope: Any, **kwargs: Any) -> Any:
        run_kernel.navigation_sufficiency_ledger_input = deepcopy(
            runtime_scope["evidence_ledger_projection"]
        )
        return original_sufficiency(run_kernel, runtime_scope, **kwargs)

    def capture_final_material(*args: Any, **kwargs: Any) -> Any:
        handoff = kwargs.get("final_evidence_handoff")
        if handoff is not None:
            capture["final_material_ledger_projections"].append(
                deepcopy(handoff.evidence_ledger_projection)
            )
        return original_final_material(*args, **kwargs)

    monkeypatch.setattr(PostRetirementOrdinaryPipelineHarness, "ask_model", ask_model)
    monkeypatch.setattr(
        RunKernel,
        "authorize_searchos_judgment",
        capture_judgment_authorization,
    )
    monkeypatch.setattr(
        orchestrator,
        "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
        capture_receiver,
    )
    monkeypatch.setattr(
        orchestrator,
        "execute_sufficiency_judgment_handoff_from_scope",
        capture_sufficiency,
    )
    monkeypatch.setattr(
        orchestrator,
        "build_final_material_runtime_handoff_from_scope",
        capture_final_material,
    )
    return capture


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    decision_mode: str = "NAVIGATE_TO_HANDOFF",
    deps_overrides: Mapping[str, Any] | None = None,
    harness_sink: list[Any] | None = None,
    query: str = "What is Alpha's current official launch-color requirement?",
) -> tuple[Any, Any]:
    offline_planner = SearchPlannerModelAdapter(
        ask_model=lambda *_args, **_kwargs: json.dumps(
            _official_requirement_planner_payload()
        ),
        provider="offline-response-only",
        model="offline-search-planner",
        enabled=True,
        licensed=True,
    )
    overrides = {"search_planner_adapter": offline_planner}
    overrides.update(dict(deps_overrides or {}))
    return run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Deep",
        query_type="product",
        query=query,
        core_topic=query.rstrip("?"),
        primary_entity="Alpha",
        researcher_queries=["Alpha current official launch color requirement"],
        evidence_rows=[
            {
                "title": "Alpha official launch-color index",
                "url": PARENT_URL,
                "text": "Directional index context without the requested fact.",
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
            },
        ],
        read_content_by_url={
            PARENT_URL: PARENT_MARKDOWN,
            CHILD_URL: CHILD_MARKDOWN,
            SIBLING_URL: "Sibling archive material.",
        },
        read_assessment_decision=decision_mode,
        analyst_response=f"The exact linked source establishes {LINKED_FACT}.",
        raw_author_response=(
            f"Alpha's official requirement is that its launch color is {LINKED_FACT}. "
            f"[[1]]({CHILD_URL})"
        ),
        deps_overrides=overrides,
        harness_sink=harness_sink,
    )


def test_navigation_request_authority_preserves_ordinary_contract() -> None:
    ordinary = build_searchos_judgment_decision_contract_v1()
    navigation = build_searchos_judgment_decision_contract_v1(
        navigation_enabled=True
    )
    assert hashlib.sha256(SEARCHOS_JUDGMENT_SYSTEM_PROMPT.encode()).hexdigest() == (
        "a03ef82d195ddb696a31f8c262060499c0ca38a8ea38449f04e443d426a1d9d6"  # pragma: allowlist secret
    )
    assert ordinary["decision_contract_digest"] == (
        "92e38d5899702c24bd83f3e144bc2218e43d90a26d9270af306649fb45873e00"  # pragma: allowlist secret
    )
    assert ordinary["decision_schema_version"] == "searchos_judgment_decision_v1"
    assert "REQUEST_NAVIGATE_BREADCRUMB" not in ordinary["actions"]
    assert "navigation_candidate_ref" not in ordinary["allowed_output_fields"]
    nav_action = navigation["actions"]["REQUEST_NAVIGATE_BREADCRUMB"]
    assert navigation["decision_schema_version"] == (
        "searchos_navigation_judgment_decision_v1"
    )
    assert "navigation_candidate_ref" in navigation["allowed_output_fields"]
    assert nav_action["required_fields"][-1] == "navigation_candidate_ref"
    assert set(nav_action["authorship_forbidden"]) == {
        "urls",
        "destination_bindings",
        "providers",
        "routes",
        "alternate_refs",
    }


def test_one_hop_navigation_reaches_component_and_final_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_tracking_store(monkeypatch)
    runtime_capture = _install_navigation_model(monkeypatch)
    extraction_calls = _capture_extraction(monkeypatch)
    outcome, harness = _run(tmp_path, monkeypatch)

    assert LINKED_FACT not in PARENT_MARKDOWN and LINKED_FACT in CHILD_MARKDOWN
    assert all(
        slot["posture"] == "semantically_handed_off"
        for slot in harness.run_kernel.state.searchos_state["slots_by_id"].values()
    ), json.dumps({
        "slots": [
            {
                "id": slot["slot_id"],
                "posture": slot["posture"],
                "reason": slot["latest_reason"],
                "custody_origins": [
                    custody.get("origin") for custody in slot["custody_refs"]
                ],
            }
            for slot in harness.run_kernel.state.searchos_state[
                "slots_by_id"
            ].values()
        ],
        "decisions": [
            (item["slot_id"], item["action"])
            for item in getattr(harness, "navigation_decisions", [])
        ],
        "inputs": [
            (
                item["authorized_request"]["slot_ref"]["slot_id"],
                [
                    material.get("origin")
                    for material in item["read_custody_materials"]
                ],
            )
            for item in getattr(harness, "navigation_model_inputs", [])
        ],
        "authorization_errors": getattr(
            harness.run_kernel, "navigation_authorization_errors", []
        ),
        "receiver_failure": outcome.execution_trace["searchos_slice_a"].get(
            "component_receiver_failure"
        ),
    }, sort_keys=True, default=str)
    assert harness.searchos_product_result.semantic_handoffs, json.dumps(
        {
            "state": harness.run_kernel.state.searchos_state,
            "decisions": getattr(harness, "navigation_decisions", []),
            "inputs": getattr(harness, "navigation_model_inputs", []),
            "authorization_errors": getattr(
                harness.run_kernel, "navigation_authorization_errors", []
            ),
        },
        sort_keys=True,
        default=str,
    )
    assert LINKED_FACT in outcome.report, json.dumps(
        {
            "report": outcome.report,
            "semantic_outcomes": outcome.execution_trace["searchos_slice_a"][
                "semantic_outcomes_by_slot"
            ],
            "component_receiver_failure": outcome.execution_trace[
                "searchos_slice_a"
            ].get("component_receiver_failure"),
            "receiver_errors": getattr(
                harness.run_kernel, "navigation_receiver_errors", []
            ),
            "materials": harness.searchos_product_result.searchos_semantic_material,
            "admission": harness.run_kernel.state.projections.get(
                "multicomponent_component_admission"
            ),
            "projection_keys": sorted(harness.run_kernel.state.projections),
        },
        sort_keys=True,
        default=str,
    )
    assert any(LINKED_FACT in prompt for prompt in harness.author_prompts)
    assert harness.read_transport_calls == [PARENT_URL, CHILD_URL]
    result = harness.searchos_product_result
    material = list(harness.searchos_semantic_material_before_pipeline_consumption)
    assert len(material) == 1
    assert material[0]["_provider"] == "searchos_read_custody"
    admitted = harness.run_kernel.state.projections[
        "multicomponent_component_admission"
    ]["component_admission_refs"][0]
    evidence_ids = {item["evidence_ref_id"] for item in admitted["evidence_refs"]}
    assert admitted["admission_status"] == "admitted"
    canonical_candidate_id = material[0]["source_id"]
    assert material[0]["candidate_id"] == canonical_candidate_id
    assert material[0]["searchos_evidence_ledger_candidate_id"] == (
        canonical_candidate_id
    )
    assert canonical_candidate_id in evidence_ids
    kernel = harness.run_kernel
    semantic_admission = kernel.state.semantic_observation_admission_history[-1]
    assert semantic_admission["evidence_refs"] == [canonical_candidate_id]
    assert semantic_admission["content_refs"] == [
        f"content:component-1:{canonical_candidate_id}"
    ]
    assert semantic_admission["content_ref_records"][0]["content_ref_id"] == (
        semantic_admission["content_refs"][0]
    )
    coverage = kernel.state.component_coverage_history[-1]
    assert coverage["content_reference_bindings"][0]["evidence_ref_id"] == (
        canonical_candidate_id
    )
    assert kernel.state.initial_answer_contract
    assert kernel.state.current_answer_contract == {}
    before_requirements = {
        item["requirement_id"]
        for item in kernel.navigation_ledger_before_receiver["source_requirements"]
    }
    after_requirements = {
        item["requirement_id"]: item
        for item in kernel.navigation_ledger_after_receiver["source_requirements"]
    }
    navigation_requirement_ids = {
        requirement_id
        for requirement_id in after_requirements
        if requirement_id.startswith("searchos_semantic_requirement:")
    }
    assert not navigation_requirement_ids & before_requirements
    assert len(navigation_requirement_ids) == 1
    navigation_requirement_id = next(iter(navigation_requirement_ids))
    assert after_requirements[navigation_requirement_id]["status"] == "satisfied"
    assert canonical_candidate_id in after_requirements[navigation_requirement_id][
        "linked_candidate_ids"
    ]
    before_candidates = {
        item["candidate_id"]: item
        for item in harness.navigation_ledger_at_semantic_handoff[
            "candidate_records"
        ]
    }
    after_candidates = {
        item["candidate_id"]: item
        for item in kernel.navigation_ledger_after_receiver["candidate_records"]
    }
    assert before_candidates[canonical_candidate_id]["fact_disposition"] == "observed"
    assert after_candidates[canonical_candidate_id]["fact_disposition"] == "accepted"
    assert set(after_candidates) == set(before_candidates)
    sufficiency_requirements = {
        item["requirement_id"]: item
        for item in kernel.navigation_sufficiency_ledger_input["source_requirements"]
    }
    assert sufficiency_requirements[navigation_requirement_id] == (
        after_requirements[navigation_requirement_id]
    )
    assert runtime_capture["final_material_ledger_projections"][-1] == (
        kernel.navigation_ledger_after_receiver
    )
    assert kernel.state.sufficiency_judgment_projection["final_answer_allowed"] is True
    assert kernel.state.sufficiency_judgment_projection["missing_required_obligations"] == [], json.dumps(
        kernel.state.sufficiency_judgment_projection["missing_required_obligations"],
        sort_keys=True,
    )
    assert outcome.execution_trace["searchos_slice_a"]["readiness_projection"][
        "all_required_slots_slice_a_ready"
    ] is True

    state = harness.run_kernel.state.searchos_state
    options = [
        NavigationOption.from_dict(item)
        for item in state["navigation"]["options_by_id"].values()
    ]
    assert len(options) == 2
    assert max(option.child_depth for option in options) == 1
    assert {option.disposition for option in options} == {"custodied", "selectable"}
    assert extraction_calls == [PARENT_MARKDOWN]
    assert CHILD_MARKDOWN not in extraction_calls
    assert all(option.child_depth <= 1 for option in options)
    selection_input = harness.navigation_selection_input
    navigation_decisions = harness.navigation_decisions
    assert [item["action"] for item in navigation_decisions] == [
        "REQUEST_READ_PAGE",
        "REQUEST_NAVIGATE_BREADCRUMB",
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
    ]
    assert navigation_decisions[1]["navigation_candidate_ref"] == (
        selection_input["authorized_request"]["navigation_options"][0][
            "navigation_candidate_ref"
        ]
    )
    assert CHILD_URL not in json.dumps(selection_input, sort_keys=True)
    assert CHILD_URL not in json.dumps(state, sort_keys=True)

    retained = {
        "state": state,
        "product_result": result,
        "outcome": outcome,
        "projections": harness.run_kernel.state.projections,
    }
    serialized = json.dumps(retained, sort_keys=True, default=str)
    assert PARENT_MARKDOWN not in serialized
    assert "navigation_source_markdown" not in serialized
    assert len(TrackingLocatorStore.instances) == 1
    store = TrackingLocatorStore.instances[0]
    assert store.discarded and store.staged_count == store.committed_count == 0


def test_navigation_insufficiency_does_not_invent_discovery_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_capture = _install_navigation_model(monkeypatch)
    outcome, harness = _run(
        tmp_path,
        monkeypatch,
        decision_mode="NAVIGATION_INSUFFICIENT",
    )
    del outcome
    state = harness.run_kernel.state.searchos_state
    assert not hasattr(harness.run_kernel, "navigation_ledger_before_receiver")
    assert "multicomponent_component_admission" not in harness.run_kernel.state.projections
    assert runtime_capture["final_material_ledger_projections"] == []
    slot = next(iter(state["slots_by_id"].values()))
    before = harness.dispositions_before_navigation_assessment
    assert slot["candidate_option_dispositions"] == before
    assert "" not in slot["candidate_option_dispositions"]
    assert all(
        record.get("candidate_use_option_id")
        for record in slot["candidate_option_dispositions"].values()
    )
    option = next(
        NavigationOption.from_dict(item)
        for item in state["navigation"]["options_by_id"].values()
        if dict(item).get("disposition") == "custodied"
    )
    assert option.disposition == "custodied" and not option.active_selection_ref
    assert "PROPOSE_FOLLOWUP_QUERY" in harness.post_navigation_legal_actions
    assert "HANDOFF_UNRESOLVED" in harness.post_navigation_legal_actions


def test_returned_destination_failure_continues_without_retry_or_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_navigation_model(monkeypatch)
    transport_calls: list[str] = []

    def transport(payload: dict[str, Any]) -> dict[str, Any]:
        requested = payload.get("urls")
        url = str(requested[0]) if isinstance(requested, list) else str(requested)
        transport_calls.append(url)
        if url == PARENT_URL:
            return {"results": [{"url": url, "raw_content": PARENT_MARKDOWN}], "failed_results": []}
        return {"results": [], "failed_results": [{"url": url, "error": "offline destination failure"}]}

    outcome, harness = _run(
        tmp_path,
        monkeypatch,
        decision_mode="NAVIGATE_THEN_UNRESOLVED",
        deps_overrides={
            "searchos_read_acquisition_transports": AcquisitionTransports(
                tavily_extract=transport
            )
        },
    )
    state = harness.run_kernel.state.searchos_state
    slot = next(iter(state["slots_by_id"].values()))
    option = next(
        NavigationOption.from_dict(item)
        for item in state["navigation"]["options_by_id"].values()
    )
    assert transport_calls == [PARENT_URL, CHILD_URL]
    assert option.disposition == "destination_failed"
    assert slot["posture"] == "unresolved_handoff"
    assert outcome.execution_trace["searchos_slice_a"]["provider_calls_attempted"] == 2
    assert harness.searchos_product_result.provider_calls_attempted == 2
    assert outcome.failure_card


def test_post_ledger_invariant_propagates_and_discards_locator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_tracking_store(monkeypatch)
    _install_navigation_model(monkeypatch)
    original = RunKernel.authorize_searchos_read_custody_admission

    def reject_navigation(
        self: RunKernel,
        *,
        custody_material_ref: Mapping[str, Any],
        reason: str = "admit_post_read_evidence_ledger_custody_for_rejudgment",
    ) -> Any:
        if custody_material_ref.get("origin") == "searchos_navigation":
            candidate_id = custody_material_ref["evidence_ledger_candidate_id"]
            candidates = {
                item["candidate_id"]
                for item in self.state.evidence_ledger.to_projection().to_dict()[
                    "candidate_records"
                ]
            }
            physical = (
                self.state.evidence_ledger
                .to_fetch_read_candidate_custody_projection()[
                    "fetch_read_candidate_custody_records"
                ]
            )
            assert candidate_id in candidates
            assert [item["candidate_id"] for item in physical] == [candidate_id]
            raise RunKernelTransitionError("synthetic post-ledger SearchOS rejection")
        return original(self, custody_material_ref=custody_material_ref, reason=reason)

    monkeypatch.setattr(
        RunKernel,
        "authorize_searchos_read_custody_admission",
        reject_navigation,
    )
    harnesses: list[Any] = []
    with pytest.raises(
        NavigationRuntimeError,
        match="navigation_custody_committed_searchos_admission_failed",
    ):
        _run(tmp_path, monkeypatch, harness_sink=harnesses)
    harness = harnesses[0]
    ledger = harness.run_kernel.state.evidence_ledger.to_fetch_read_candidate_custody_projection()
    assert any(item.get("attempted_url") == CHILD_URL for item in ledger["fetch_read_candidate_custody_records"])
    slot = next(iter(harness.run_kernel.state.searchos_state["slots_by_id"].values()))
    assert slot["posture"] == "stale_or_invalid"
    option = next(
        NavigationOption.from_dict(item)
        for item in harness.run_kernel.state.searchos_state["navigation"]["options_by_id"].values()
    )
    assert option.disposition != "destination_failed"
    assert harness.read_transport_calls == [PARENT_URL, CHILD_URL]
    store = TrackingLocatorStore.instances[0]
    assert store.discarded and store.staged_count == store.committed_count == 0
