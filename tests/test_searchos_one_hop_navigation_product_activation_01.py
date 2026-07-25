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
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_SYSTEM_PROMPTS,
    safe_packet_digest,
)
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
                            "source_obligation_candidate_ids": ["obligation:official_current"],
                            "distinct_need_justification": ("The required component needs direct official support."),
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


def _install_navigation_model(
    monkeypatch: pytest.MonkeyPatch,
    *,
    analyst_status: str = "supported",
    dprime_status: str = "supported",
    replay_qualification: bool = False,
) -> dict[str, Any]:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent
    from core import pipeline_orchestrator as orchestrator
    from core import searchos_slice_a_product_runtime as product_runtime

    capture: dict[str, Any] = {
        "final_material_ledger_projections": [],
        "judgment_system_prompts": [],
        "qualification_authorizations": [],
        "ledger_before_content": [],
    }
    original = PostRetirementOrdinaryPipelineHarness.ask_model
    original_judgment_authorization = RunKernel.authorize_searchos_judgment
    original_ledger_authorization = RunKernel.authorize_evidence_ledger_reduction
    original_receiver = orchestrator.execute_ordinary_semantic_or_multicomponent_handoff_from_scope
    original_sufficiency = orchestrator.execute_sufficiency_judgment_handoff_from_scope
    original_final_material = orchestrator.build_final_material_runtime_handoff_from_scope
    original_content_builder = multicomponent.build_sanitized_content_reference_from_passage

    def ask_model(
        self: OfflineOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if system_prompt in {
            SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
            product_runtime._NAVIGATION_JUDGMENT_SYSTEM_PROMPT,
        }:
            self._record_model_call(system_prompt, kwargs)
            capture["judgment_system_prompts"].append(system_prompt)
            payload = json.loads(prompt)
            inputs = self.__dict__.setdefault("navigation_model_inputs", [])
            inputs.append(deepcopy(payload))
            request = dict(payload["authorized_request"])
            contract = dict(payload["decision_contract"])
            custody_refs = list(request.get("read_custody_refs") or ())
            materials = list(payload.get("read_custody_materials") or ())
            navigation_materials = [
                dict(item) for item in materials if dict(item).get("origin") == "searchos_navigation"
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
                        dict(request["candidate_use_options"][0])["candidate_use_option_ref"]
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
                        self.run_kernel.state.searchos_state["slots_by_id"][slot_id]["candidate_option_dispositions"]
                    )
                    self.__dict__["post_navigation_legal_actions"] = list(request["legal_actions"])
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
                        "read_custody_refs": [dict(item["read_custody_ref"]) for item in navigation_materials],
                        "reason": "The linked page contains the decisive fact.",
                    }
            elif navigation_options:
                already_navigated = any(
                    item.get("action") == "REQUEST_NAVIGATE_BREADCRUMB" and item.get("slot_id") == common["slot_id"]
                    for item in self.__dict__.get("navigation_decisions", [])
                )
                if self.read_assessment_decision == "NAVIGATE_THEN_UNRESOLVED" and already_navigated:
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
                        "navigation_candidate_ref": dict(dict(navigation_options[0])["navigation_candidate_ref"]),
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
                    "support_status": analyst_status,
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [] if analyst_status == "supported" else ["unsupported fixture"],
                }
            )
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_DPRIME]:
            self._record_model_call(system_prompt, kwargs)
            return json.dumps(
                {
                    "validation_status": dprime_status,
                    "reasons": ["Offline component D-prime fixture."],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [] if dprime_status == "supported" else ["unsupported fixture"],
                }
            )
        return original(self, prompt, system_prompt, **kwargs)

    def capture_receiver(run_kernel: RunKernel, *args: Any, **kwargs: Any) -> Any:
        run_kernel.navigation_ledger_before_receiver = run_kernel.state.evidence_ledger.to_projection().to_dict()
        try:
            result = original_receiver(run_kernel, *args, **kwargs)
        except Exception as exc:
            run_kernel.navigation_receiver_errors = [str(exc)]
            raise
        run_kernel.navigation_ledger_after_receiver = run_kernel.state.evidence_ledger.to_projection().to_dict()
        return result

    def capture_judgment_authorization(run_kernel: RunKernel, *args: Any, **kwargs: Any) -> Any:
        try:
            return original_judgment_authorization(run_kernel, *args, **kwargs)
        except Exception as exc:
            run_kernel.navigation_authorization_errors = [str(exc)]
            raise

    def capture_ledger_authorization(run_kernel: RunKernel, *args: Any, **kwargs: Any) -> Any:
        inputs = dict(kwargs.get("inputs") or {})
        if str(inputs.get("qualification_id") or "").startswith("searchos_custody_qualification:"):
            capture["qualification_authorizations"].append(deepcopy(inputs))
        return original_ledger_authorization(run_kernel, *args, **kwargs)

    def capture_content_builder(*args: Any, **kwargs: Any) -> Any:
        run_kernel = capture.get("qualification_kernel")
        if run_kernel is not None:
            capture["ledger_before_content"].append(
                deepcopy(run_kernel.state.evidence_ledger.to_projection().to_dict())
            )
        return original_content_builder(*args, **kwargs)

    if replay_qualification:
        original_qualifier = multicomponent._qualify_searchos_read_material_after_component_dprime

        def replay_qualifier(*args: Any, **kwargs: Any) -> Any:
            run_kernel = kwargs["run_kernel"]
            capture["qualification_kernel"] = run_kernel
            candidate_id = original_qualifier(*args, **kwargs)
            before = deepcopy(run_kernel.state.evidence_ledger.to_projection().to_dict())
            assert original_qualifier(*args, **kwargs) == candidate_id
            after = deepcopy(run_kernel.state.evidence_ledger.to_projection().to_dict())
            capture["qualification_replay_projections"] = (before, after)
            return candidate_id

        monkeypatch.setattr(
            multicomponent,
            "_qualify_searchos_read_material_after_component_dprime",
            replay_qualifier,
        )
    else:
        original_qualifier = multicomponent._qualify_searchos_read_material_after_component_dprime

        def capture_qualifier(*args: Any, **kwargs: Any) -> Any:
            capture["qualification_kernel"] = kwargs["run_kernel"]
            capture["qualification_bindable"] = kwargs["bindable"]
            capture["qualification_dprime"] = deepcopy(kwargs["dprime_artifact"])
            return original_qualifier(*args, **kwargs)

        monkeypatch.setattr(
            multicomponent,
            "_qualify_searchos_read_material_after_component_dprime",
            capture_qualifier,
        )

    def capture_sufficiency(run_kernel: RunKernel, runtime_scope: Any, **kwargs: Any) -> Any:
        run_kernel.navigation_sufficiency_ledger_input = deepcopy(runtime_scope["evidence_ledger_projection"])
        return original_sufficiency(run_kernel, runtime_scope, **kwargs)

    def capture_final_material(*args: Any, **kwargs: Any) -> Any:
        handoff = kwargs.get("final_evidence_handoff")
        if handoff is not None:
            capture["final_material_ledger_projections"].append(deepcopy(handoff.evidence_ledger_projection))
        return original_final_material(*args, **kwargs)

    monkeypatch.setattr(PostRetirementOrdinaryPipelineHarness, "ask_model", ask_model)
    monkeypatch.setattr(
        RunKernel,
        "authorize_searchos_judgment",
        capture_judgment_authorization,
    )
    monkeypatch.setattr(
        RunKernel,
        "authorize_evidence_ledger_reduction",
        capture_ledger_authorization,
    )
    monkeypatch.setattr(
        multicomponent,
        "build_sanitized_content_reference_from_passage",
        capture_content_builder,
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
    parent_markdown: str = PARENT_MARKDOWN,
) -> tuple[Any, Any]:
    offline_planner = SearchPlannerModelAdapter(
        ask_model=lambda *_args, **_kwargs: json.dumps(_official_requirement_planner_payload()),
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
            PARENT_URL: parent_markdown,
            CHILD_URL: CHILD_MARKDOWN,
            SIBLING_URL: "Sibling archive material.",
        },
        read_assessment_decision=decision_mode,
        analyst_response=f"The exact linked source establishes {LINKED_FACT}.",
        raw_author_response=(
            f"Alpha's official requirement is that its launch color is {LINKED_FACT}. [[1]]({CHILD_URL})"
        ),
        deps_overrides=overrides,
        harness_sink=harness_sink,
    )


def _inject_qualification_source_facts(monkeypatch: pytest.MonkeyPatch, **facts: Any) -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent

    original = multicomponent._qualify_searchos_read_material_after_component_dprime

    def inject(*args: Any, **kwargs: Any) -> Any:
        bindable = kwargs["bindable"]
        passage = bindable.passage
        lineage = dict(passage["searchos_qualification_lineage"])
        passage.update(facts)
        bindable.candidate_record.update(facts)
        canonical_candidate = kwargs["run_kernel"].state.evidence_ledger.candidates[bindable.evidence_ref_id]
        for key, value in facts.items():
            setattr(canonical_candidate, key, value)
        if facts.get("source_tier") == "secondary":
            canonical_candidate.domain = "secondary.example"
        if "eligible_for_stronger_obligation" not in facts:
            bindable.candidate_record["eligible_for_stronger_obligation"] = False
            canonical_candidate.eligible_for_stronger_obligation = False
        lineage["source_facts"] = {
            **dict(lineage.get("source_facts") or {}),
            **facts,
        }
        passage["searchos_qualification_lineage"] = lineage
        return original(*args, **kwargs)

    monkeypatch.setattr(
        multicomponent,
        "_qualify_searchos_read_material_after_component_dprime",
        inject,
    )


def _qualification_records(
    projection: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    observations = [
        dict(item)
        for item in projection.get("observation_refs") or ()
        if str(dict(item).get("observation_id") or "").startswith("searchos_custody_qualification:")
    ]
    custody = [
        dict(item)
        for item in projection.get("custody_records") or ()
        if str(dict(item).get("observation_id") or "").startswith("searchos_custody_qualification:")
    ]
    return observations, custody


def test_navigation_request_authority_preserves_ordinary_contract() -> None:
    ordinary = build_searchos_judgment_decision_contract_v1()
    navigation = build_searchos_judgment_decision_contract_v1(navigation_enabled=True)
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
    assert navigation["decision_schema_version"] == ("searchos_navigation_judgment_decision_v1")
    assert "navigation_candidate_ref" in navigation["allowed_output_fields"]
    assert nav_action["required_fields"][-1] == "navigation_candidate_ref"
    assert set(nav_action["authorship_forbidden"]) == {
        "urls",
        "destination_bindings",
        "providers",
        "routes",
        "alternate_refs",
    }


def test_one_hop_navigation_reaches_component_and_final_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_tracking_store(monkeypatch)
    runtime_capture = _install_navigation_model(monkeypatch)
    extraction_calls = _capture_extraction(monkeypatch)
    outcome, harness = _run(tmp_path, monkeypatch)

    assert LINKED_FACT not in PARENT_MARKDOWN and LINKED_FACT in CHILD_MARKDOWN
    assert all(
        slot["posture"] == "semantically_handed_off"
        for slot in harness.run_kernel.state.searchos_state["slots_by_id"].values()
    ), json.dumps(
        {
            "slots": [
                {
                    "id": slot["slot_id"],
                    "posture": slot["posture"],
                    "reason": slot["latest_reason"],
                    "custody_origins": [custody.get("origin") for custody in slot["custody_refs"]],
                }
                for slot in harness.run_kernel.state.searchos_state["slots_by_id"].values()
            ],
            "decisions": [(item["slot_id"], item["action"]) for item in getattr(harness, "navigation_decisions", [])],
            "inputs": [
                (
                    item["authorized_request"]["slot_ref"]["slot_id"],
                    [material.get("origin") for material in item["read_custody_materials"]],
                )
                for item in getattr(harness, "navigation_model_inputs", [])
            ],
            "authorization_errors": getattr(harness.run_kernel, "navigation_authorization_errors", []),
            "receiver_failure": outcome.execution_trace["searchos_slice_a"].get("component_receiver_failure"),
        },
        sort_keys=True,
        default=str,
    )
    assert harness.searchos_product_result.semantic_handoffs, json.dumps(
        {
            "state": harness.run_kernel.state.searchos_state,
            "decisions": getattr(harness, "navigation_decisions", []),
            "inputs": getattr(harness, "navigation_model_inputs", []),
            "authorization_errors": getattr(harness.run_kernel, "navigation_authorization_errors", []),
        },
        sort_keys=True,
        default=str,
    )
    assert LINKED_FACT in outcome.report, json.dumps(
        {
            "report": outcome.report,
            "semantic_outcomes": outcome.execution_trace["searchos_slice_a"]["semantic_outcomes_by_slot"],
            "component_receiver_failure": outcome.execution_trace["searchos_slice_a"].get("component_receiver_failure"),
            "receiver_errors": getattr(harness.run_kernel, "navigation_receiver_errors", []),
            "materials": harness.searchos_product_result.searchos_semantic_material,
            "admission": harness.run_kernel.state.projections.get("multicomponent_component_admission"),
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
    admitted = harness.run_kernel.state.projections["multicomponent_component_admission"]["component_admission_refs"][0]
    evidence_ids = {item["evidence_ref_id"] for item in admitted["evidence_refs"]}
    assert admitted["admission_status"] == "admitted"
    canonical_candidate_id = material[0]["source_id"]
    assert material[0]["candidate_id"] == canonical_candidate_id
    assert material[0]["searchos_evidence_ledger_candidate_id"] == (canonical_candidate_id)
    assert canonical_candidate_id in evidence_ids
    kernel = harness.run_kernel
    semantic_admission = kernel.state.semantic_observation_admission_history[-1]
    assert semantic_admission["evidence_refs"] == [canonical_candidate_id]
    assert semantic_admission["content_refs"] == [f"content:component-1:{canonical_candidate_id}"]
    assert semantic_admission["content_ref_records"][0]["content_ref_id"] == (semantic_admission["content_refs"][0])
    coverage = kernel.state.component_coverage_history[-1]
    assert coverage["content_reference_bindings"][0]["evidence_ref_id"] == (canonical_candidate_id)
    [qualification_authorization] = runtime_capture["qualification_authorizations"]
    qualification_id = qualification_authorization["qualification_id"]
    qualification_basis = qualification_authorization["qualification_basis"]
    assert qualification_id.startswith("searchos_custody_qualification:")
    assert len(qualification_id.rsplit(":", 1)[1]) == 64
    assert set(qualification_id.rsplit(":", 1)[1]) <= set("0123456789abcdef")
    assert qualification_id == ("searchos_custody_qualification:" + safe_packet_digest(qualification_basis))
    assert qualification_basis["identity_kind"] == "searchos_custody_qualification_v1"
    assert qualification_basis["canonical_candidate_id"] == canonical_candidate_id
    assert qualification_basis["component_ref"] == {
        key: admitted[key] for key in ("component_id", "component_revision", "component_digest")
    }
    material_lineage = material[0]["searchos_qualification_lineage"]
    assert qualification_basis["navigation_content_reference"] == (material_lineage["navigation_content_reference"])
    assert qualification_basis["fetch_read_content_packet"] == (material_lineage["fetch_read_content_packet"])
    assert qualification_basis["read_custody_ref"] == (material_lineage["read_custody_ref"])
    assert qualification_basis["slot_ref"] == material_lineage["slot_ref"]
    assert qualification_basis["semantic_handoff_ref"] == (material_lineage["semantic_handoff_ref"])
    assert len(qualification_basis["component_dprime_artifact_digest"]) == 64
    assert "url" not in json.dumps(qualification_basis, sort_keys=True).casefold()
    [pre_content_ledger] = runtime_capture["ledger_before_content"]
    pre_content_observations, pre_content_custody = _qualification_records(pre_content_ledger)
    assert [item["observation_id"] for item in pre_content_observations] == [qualification_id]
    assert pre_content_custody == [
        {
            "candidate_id": canonical_candidate_id,
            "record_kind": "fact",
            "disposition": "accepted",
            "source": "searchos_component_dprime_material_qualification",
            "requirement_id": qualification_basis["requirement_id"],
            "observation_id": qualification_id,
        }
    ]
    assert [
        item
        for item in pre_content_ledger["requirement_links"]
        if item["requirement_id"] == qualification_basis["requirement_id"]
        and item["candidate_id"] == canonical_candidate_id
    ] == [
        {
            "requirement_id": qualification_basis["requirement_id"],
            "candidate_id": canonical_candidate_id,
            "link_reason": "exact_searchos_read_custody_component_dprime_supported",
            "link_status": "accepted",
        }
    ]
    qualified_candidate = next(
        item for item in pre_content_ledger["candidate_records"] if item["candidate_id"] == canonical_candidate_id
    )
    assert qualified_candidate["source_tier"] == "official"
    assert qualified_candidate["evidence_material_type"] == "searchos_read_custody"
    assert qualified_candidate["readable_status"] == "readable"
    assert qualified_candidate["fetchable_status"] == "fetchable"
    assert qualified_candidate["eligible_for_stronger_obligation"] is True
    assert qualified_candidate["contextual_only"] is False
    assert qualified_candidate["lower_tier"] is False
    pre_qualification_candidate = next(
        item
        for item in kernel.navigation_ledger_before_receiver["candidate_records"]
        if item["candidate_id"] == canonical_candidate_id
    )
    assert qualified_candidate["final_evidence_eligible"] == (pre_qualification_candidate["final_evidence_eligible"])
    physical = kernel.state.evidence_ledger.to_fetch_read_candidate_custody_projection()[
        "fetch_read_candidate_custody_records"
    ]
    assert [item["candidate_id"] for item in physical].count(canonical_candidate_id) == 1
    assert kernel.state.initial_answer_contract
    assert kernel.state.current_answer_contract == {}
    before_requirements = {
        item["requirement_id"] for item in kernel.navigation_ledger_before_receiver["source_requirements"]
    }
    after_requirements = {
        item["requirement_id"]: item for item in kernel.navigation_ledger_after_receiver["source_requirements"]
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
    assert canonical_candidate_id in after_requirements[navigation_requirement_id]["linked_candidate_ids"]
    before_candidates = {
        item["candidate_id"]: item for item in harness.navigation_ledger_at_semantic_handoff["candidate_records"]
    }
    after_candidates = {
        item["candidate_id"]: item for item in kernel.navigation_ledger_after_receiver["candidate_records"]
    }
    assert before_candidates[canonical_candidate_id]["fact_disposition"] == "observed"
    assert after_candidates[canonical_candidate_id]["fact_disposition"] == "accepted"
    assert set(after_candidates) == set(before_candidates)
    sufficiency_requirements = {
        item["requirement_id"]: item for item in kernel.navigation_sufficiency_ledger_input["source_requirements"]
    }
    assert sufficiency_requirements[navigation_requirement_id] == (after_requirements[navigation_requirement_id])
    assert runtime_capture["final_material_ledger_projections"][-1] == (kernel.navigation_ledger_after_receiver)
    assert kernel.state.sufficiency_judgment_projection["final_answer_allowed"] is True
    assert kernel.state.sufficiency_judgment_projection["missing_required_obligations"] == [], json.dumps(
        kernel.state.sufficiency_judgment_projection["missing_required_obligations"],
        sort_keys=True,
    )
    assert (
        outcome.execution_trace["searchos_slice_a"]["readiness_projection"]["all_required_slots_slice_a_ready"] is True
    )

    state = harness.run_kernel.state.searchos_state
    options = [NavigationOption.from_dict(item) for item in state["navigation"]["options_by_id"].values()]
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
    assert (
        navigation_decisions[1]["navigation_candidate_ref"]
        == (selection_input["authorized_request"]["navigation_options"][0]["navigation_candidate_ref"])
    )
    judgment_inputs = harness.navigation_model_inputs
    judgment_prompts = runtime_capture["judgment_system_prompts"]
    assert len(judgment_inputs) == len(judgment_prompts) == len(navigation_decisions)
    assert judgment_inputs[0]["authorized_request"]["schema_version"] == ("searchos_judgment_request_v1")
    assert (
        judgment_inputs[0]["decision_contract"]["decision_contract_digest"]
        == (build_searchos_judgment_decision_contract_v1()["decision_contract_digest"])
    )
    assert judgment_prompts[0] == SEARCHOS_JUDGMENT_SYSTEM_PROMPT
    navigation_rounds = [
        (payload, prompt, decision)
        for payload, prompt, decision in zip(judgment_inputs, judgment_prompts, navigation_decisions, strict=True)
        if payload["authorized_request"]["schema_version"] == "searchos_navigation_judgment_request_v1"
    ]
    assert navigation_rounds
    for payload, prompt, decision in navigation_rounds:
        request = payload["authorized_request"]
        contract = payload["decision_contract"]
        assert request["navigation_options"]
        assert "url" not in json.dumps(request["navigation_options"]).casefold()
        expected_actions = {
            "REQUEST_READ_PAGE",
            "PROPOSE_FOLLOWUP_QUERY",
            "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
            "HANDOFF_UNRESOLVED",
            "REQUEST_NAVIGATE_BREADCRUMB",
        }
        assert set(request["legal_actions"]) <= expected_actions
        assert "REQUEST_NAVIGATE_BREADCRUMB" in request["legal_actions"]
        assert set(contract["actions"]) == expected_actions
        assert contract["decision_schema_version"] == ("searchos_navigation_judgment_decision_v1")
        assert decision["schema_version"] == contract["decision_schema_version"]
        normalized_prompt = " ".join(prompt.split())
        assert prompt != SEARCHOS_JUDGMENT_SYSTEM_PROMPT
        assert prompt.count("searchos_navigation_judgment_decision_v1") == 1
        assert (
            "Return exactly one JSON object matching searchos_navigation_judgment_decision_v1."
        ) in normalized_prompt
        assert ("Return exactly one JSON object matching searchos_judgment_decision_v1.") not in normalized_prompt
        assert all(f"- {action}" in prompt for action in expected_actions)
        assert (
            "After READ custody exists, REQUEST_READ_PAGE, "
            "PROPOSE_FOLLOWUP_QUERY, HANDOFF_UNRESOLVED, and "
            "REQUEST_NAVIGATE_BREADCRUMB must include exactly one "
            "read_insufficient assessment for every current READ custody ref, "
            "copied exactly, with the contract's exact assessment fields and "
            "disposition."
        ) in normalized_prompt
        assert (
            "Never invent or alter a URL, destination binding, authority ref, "
            "candidate ref, navigation ref, custody ref, component ref, "
            "source-obligation ref, provider choice, route, request identity, "
            "disposition, deterministic fallback, or unsupported field."
        ) in normalized_prompt
        assert (
            "REQUEST_NAVIGATE_BREADCRUMB copies exactly one current, URL-free navigation_candidate_ref"
        ) in normalized_prompt
        assert ("Exact navigation destination URLs are intentionally absent from the input.") in normalized_prompt
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


def test_empty_navigation_rounds_use_exact_ordinary_request_and_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_capture = _install_navigation_model(monkeypatch)
    outcome, harness = _run(
        tmp_path,
        monkeypatch,
        parent_markdown=(f"Alpha's official requirement is that its launch color is {LINKED_FACT}."),
    )

    assert outcome.failure_card
    assert [item["action"] for item in harness.navigation_decisions] == [
        "REQUEST_READ_PAGE",
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
    ]
    assert len(harness.navigation_model_inputs) == 2
    ordinary_contract = build_searchos_judgment_decision_contract_v1()
    for payload, prompt in zip(
        harness.navigation_model_inputs,
        runtime_capture["judgment_system_prompts"],
        strict=True,
    ):
        request = payload["authorized_request"]
        contract = payload["decision_contract"]
        assert request["schema_version"] == "searchos_judgment_request_v1"
        assert request.get("navigation_options") is None
        assert "REQUEST_NAVIGATE_BREADCRUMB" not in request["legal_actions"]
        assert contract == ordinary_contract
        assert "navigation_candidate_ref" not in contract["allowed_output_fields"]
        assert prompt == SEARCHOS_JUDGMENT_SYSTEM_PROMPT
        assert "REQUEST_NAVIGATE_BREADCRUMB" not in prompt
        assert "searchos_navigation_judgment_decision_v1" not in prompt


def test_ordinary_final_evidence_selection_does_not_upgrade_source_strength(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_capture = _install_navigation_model(monkeypatch)
    _inject_qualification_source_facts(
        monkeypatch,
        source_tier="secondary",
        source_class="reputable_secondary",
        currentness_signal="current",
        final_evidence_eligible=True,
        eligible_for_stronger_obligation=False,
    )
    outcome, harness = _run(
        tmp_path,
        monkeypatch,
        parent_markdown=(f"Alpha's launch-color requirement is reported as {LINKED_FACT}."),
    )
    kernel = harness.run_kernel
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    observations, custody = _qualification_records(ledger)

    assert len(observations) == len(custody) == 1
    candidate_id = custody[0]["candidate_id"]
    candidate = next(item for item in ledger["candidate_records"] if item["candidate_id"] == candidate_id)
    requirement = next(
        item for item in ledger["source_requirements"] if item["requirement_id"] == custody[0]["requirement_id"]
    )
    assert all(
        item["authorized_request"]["schema_version"] == "searchos_judgment_request_v1"
        and item["decision_contract"]["decision_schema_version"] == "searchos_judgment_decision_v1"
        for item in harness.navigation_model_inputs
    )
    assert candidate["source_tier"] == "secondary"
    assert candidate["source_class"] == "reputable_secondary"
    assert candidate["final_evidence_eligible"] is True
    assert candidate["eligible_for_stronger_obligation"] is False
    assert requirement["status"] == "unsatisfied"
    assert kernel.state.semantic_observation_admission_history == []
    assert kernel.state.component_coverage_history == []
    assert "multicomponent_component_admission" not in kernel.state.projections
    assert not kernel.state.sufficiency_judgment_projection.get("final_answer_allowed", False)
    assert kernel.state.final_answer_packet["final_answer_allowed"] is False
    assert kernel.state.final_answer_packet["readiness_status"] == "blocked"
    assert len(runtime_capture["final_material_ledger_projections"]) == 1
    assert harness.author_prompts == []
    assert outcome.failure_card


@pytest.mark.parametrize("canonical_eligibility", [False, True])
def test_ordinary_official_current_source_strength_remains_compatible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    canonical_eligibility: bool,
) -> None:
    runtime_capture = _install_navigation_model(monkeypatch)
    _inject_qualification_source_facts(
        monkeypatch,
        source_tier="official",
        source_class="official_current_rules",
        currentness_signal="current",
        final_evidence_eligible=False,
        eligible_for_stronger_obligation=canonical_eligibility,
    )
    _outcome, harness = _run(
        tmp_path,
        monkeypatch,
        parent_markdown=(f"Alpha's official requirement is that its launch color is {LINKED_FACT}."),
    )
    kernel = harness.run_kernel
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    observations, custody = _qualification_records(ledger)

    assert len(observations) == len(custody) == 1
    assert runtime_capture["qualification_dprime"]["semantic_output"]["validation_status"] == "supported"
    assert len(runtime_capture["qualification_authorizations"]) == 1
    candidate_id = custody[0]["candidate_id"]
    candidate = next(item for item in ledger["candidate_records"] if item["candidate_id"] == candidate_id)
    requirement = next(
        item for item in ledger["source_requirements"] if item["requirement_id"] == custody[0]["requirement_id"]
    )
    assert candidate["source_tier"] == "official"
    assert candidate["source_class"] == "official_current_rules"
    assert candidate["final_evidence_eligible"] is False
    assert candidate["eligible_for_stronger_obligation"] is True
    assert requirement["status"] == "satisfied"


@pytest.mark.parametrize(
    ("analyst_status", "dprime_status"),
    [("unsupported", "supported"), ("supported", "unsupported")],
)
def test_component_role_rejection_exhausts_recovery_without_semantic_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    analyst_status: str,
    dprime_status: str,
) -> None:
    runtime_capture = _install_navigation_model(
        monkeypatch,
        analyst_status=analyst_status,
        dprime_status=dprime_status,
    )
    outcome, harness = _run(tmp_path, monkeypatch)
    kernel = harness.run_kernel
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    physical = kernel.state.evidence_ledger.to_fetch_read_candidate_custody_projection()[
        "fetch_read_candidate_custody_records"
    ]

    [navigation_custody] = [
        item
        for slot in kernel.state.searchos_state["slots_by_id"].values()
        for item in slot["custody_refs"]
        if item.get("origin") == "searchos_navigation"
    ]
    candidate_id = navigation_custody["evidence_ledger_candidate_id"]
    assert [item["candidate_id"] for item in physical].count(candidate_id) == 1
    candidate = next(item for item in ledger["candidate_records"] if item["candidate_id"] == candidate_id)
    before_candidate = next(
        item
        for item in kernel.navigation_ledger_before_receiver["candidate_records"]
        if item["candidate_id"] == candidate_id
    )
    assert candidate == before_candidate
    assert any(
        item.get("evidence_ledger_candidate_id") == candidate_id
        for slot in kernel.state.searchos_state["slots_by_id"].values()
        for item in slot["custody_refs"]
    )
    assert _qualification_records(ledger) == ([], [])
    assert runtime_capture["qualification_authorizations"] == []
    assert kernel.state.semantic_observation_admission_history == []
    assert kernel.state.component_coverage_history == []
    component_admission = kernel.state.projections["multicomponent_component_admission"]
    assert component_admission["admitted_component_count"] == 0
    assert all(
        item["admission_status"] not in {"admitted", "admitted_with_caveats"}
        and not item.get("admitted_claim_ref")
        and not item.get("evidence_refs")
        for item in component_admission["component_admission_refs"]
    )
    assert not kernel.state.sufficiency_judgment_projection.get("final_answer_allowed", False)
    terminal = kernel.state.projections["searchos_existing_gap_recovery_terminal"]
    assert terminal["terminal_status"] == "exhausted_insufficient"
    assert terminal["coverage_gained"] is False
    assert terminal["gap_remains"] is True
    assert terminal["whole_run_lease_status"] == ("settled_exhausted_insufficient")
    assert (
        outcome.execution_trace["searchos_slice_a"]["existing_gap_recovery"]["scrutineer_recovery_input_used"] is False
    )
    assert len(runtime_capture["final_material_ledger_projections"]) == 1
    assert kernel.state.final_answer_packet["final_answer_allowed"] is False
    assert kernel.state.final_answer_packet["readiness_status"] == "blocked"
    assert harness.author_prompts == []


@pytest.mark.parametrize(
    "source_facts",
    [
        {"source_tier": "secondary", "source_class": "reputable_secondary"},
        {"contextual_only": True},
        {"lower_tier": True},
        {"currentness_signal": "stale"},
    ],
    ids=["weak", "contextual", "lower-tier", "stale"],
)
def test_supported_claim_does_not_launder_weak_or_stale_source_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_facts: Mapping[str, Any],
) -> None:
    runtime_capture = _install_navigation_model(monkeypatch)
    _inject_qualification_source_facts(monkeypatch, **source_facts)
    outcome, harness = _run(tmp_path, monkeypatch)
    kernel = harness.run_kernel
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    observations, custody = _qualification_records(ledger)

    assert len(observations) == len(custody) == 1, getattr(kernel, "navigation_receiver_errors", [])
    candidate_id = custody[0]["candidate_id"]
    candidate = next(item for item in ledger["candidate_records"] if item["candidate_id"] == candidate_id)
    assert candidate["fact_disposition"] == "accepted"
    assert candidate["eligible_for_stronger_obligation"] is False
    for key, value in source_facts.items():
        assert candidate[key] == value
    [requirement_id] = [
        item["requirement_id"]
        for item in ledger["source_requirements"]
        if item["requirement_id"].startswith("searchos_semantic_requirement:")
    ]
    requirement = next(item for item in ledger["source_requirements"] if item["requirement_id"] == requirement_id)
    assert requirement["status"] != "satisfied"
    assert kernel.state.semantic_observation_admission_history == []
    assert kernel.state.component_coverage_history == []
    assert "multicomponent_component_admission" not in kernel.state.projections
    assert not kernel.state.sufficiency_judgment_projection.get("final_answer_allowed", False)
    assert len(runtime_capture["final_material_ledger_projections"]) == 1
    assert kernel.state.final_answer_packet["final_answer_allowed"] is False
    assert kernel.state.final_answer_packet["readiness_status"] == "blocked"
    assert harness.author_prompts == []
    assert outcome.failure_card


def test_exact_qualification_replay_is_count_stable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_capture = _install_navigation_model(monkeypatch, replay_qualification=True)
    _outcome, harness = _run(tmp_path, monkeypatch)
    before, after = runtime_capture["qualification_replay_projections"]
    observations, custody = _qualification_records(after)
    qualification_id = observations[0]["observation_id"]
    requirement_id = custody[0]["requirement_id"]

    assert after == before
    assert len(observations) == len(custody) == 1
    assert sum(item["requirement_id"] == requirement_id for item in after["source_requirements"]) == 1
    assert (
        sum(
            item["candidate_id"] == custody[0]["candidate_id"]
            and item["requirement_id"] == requirement_id
            and item["link_status"] == "accepted"
            for item in after["requirement_links"]
        )
        == 1
    )
    assert custody[0]["observation_id"] == qualification_id
    physical = harness.run_kernel.state.evidence_ledger.to_fetch_read_candidate_custody_projection()[
        "fetch_read_candidate_custody_records"
    ]
    assert [item["candidate_id"] for item in physical].count(custody[0]["candidate_id"]) == 1


def test_one_physical_candidate_has_component_bound_qualification_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent

    runtime_capture = _install_navigation_model(monkeypatch)
    _outcome, harness = _run(tmp_path, monkeypatch)
    kernel = harness.run_kernel
    contract = kernel.state.initial_answer_contract
    component_one = dict(contract["accepted_answer_component_refs"][0])
    component_two = {
        **component_one,
        "component_id": "component-2",
        "component_digest": safe_packet_digest({"reuse_component": "component-2", "source": component_one}),
    }
    contract["accepted_answer_component_refs"] = [
        *contract["accepted_answer_component_refs"],
        component_two,
    ]

    slot_one = next(iter(kernel.state.searchos_state["slots_by_id"].values()))
    slot_two = deepcopy(slot_one)
    slot_two_ref = {
        **dict(slot_one["slot_ref"]),
        "slot_id": "search-judgment-read-slot:component-2:obligation:official_current",
        "component_id": "component-2",
    }
    slot_two_ref["slot_digest"] = safe_packet_digest(
        {key: value for key, value in slot_two_ref.items() if key != "slot_digest"}
    )
    navigation_custody = next(item for item in slot_one["custody_refs"] if item.get("origin") == "searchos_navigation")
    custody_two = {
        **deepcopy(navigation_custody),
        "slot_ref": slot_two_ref,
        "read_custody_material_id": (
            "searchos-read-custody:"
            + safe_packet_digest(
                {"component_id": "component-2", "candidate_id": navigation_custody["evidence_ledger_candidate_id"]}
            )[:24]
        ),
    }
    custody_two["read_custody_material_digest"] = safe_packet_digest(
        {
            "read_custody_material_id": custody_two["read_custody_material_id"],
            "slot_ref": slot_two_ref,
        }
    )
    handoff_two = {
        "semantic_handoff_id": (
            "searchos-semantic-handoff:"
            + safe_packet_digest(
                {"component_id": "component-2", "custody": custody_two["read_custody_material_digest"]}
            )[:24]
        ),
        "slot_ref": slot_two_ref,
    }
    handoff_two["semantic_handoff_digest"] = safe_packet_digest(handoff_two)
    slot_two.update(
        {
            "slot_id": slot_two_ref["slot_id"],
            "slot_ref": slot_two_ref,
            "component_ref": {
                key: component_two[key] for key in ("component_id", "component_revision", "component_digest")
            },
            "custody_refs": [custody_two],
            "posture": "semantically_handed_off",
        }
    )
    kernel.state.searchos_state["slots_by_id"][slot_two_ref["slot_id"]] = slot_two
    kernel.state.searchos_state["semantic_handoff_refs"].append(handoff_two)

    first_bindable = runtime_capture["qualification_bindable"]
    passage_two = deepcopy(first_bindable.passage)
    passage_two["searchos_slot_ref"] = slot_two_ref
    passage_two["searchos_semantic_handoff_ref"] = {
        key: handoff_two[key] for key in ("semantic_handoff_id", "semantic_handoff_digest")
    }
    lineage_two = dict(passage_two["searchos_qualification_lineage"])
    lineage_two["slot_ref"] = slot_two_ref
    lineage_two["read_custody_ref"] = {
        key: custody_two[key] for key in ("read_custody_material_id", "read_custody_material_digest")
    }
    lineage_two["semantic_handoff_ref"] = passage_two["searchos_semantic_handoff_ref"]
    passage_two["searchos_qualification_lineage"] = lineage_two
    bindable_two = type(first_bindable)(
        passage=passage_two,
        evidence_ref_id=first_bindable.evidence_ref_id,
        candidate_record=deepcopy(first_bindable.candidate_record),
    )
    dprime_two = deepcopy(runtime_capture["qualification_dprime"])
    dprime_two["artifact_digest"] = safe_packet_digest(
        {"component_id": "component-2", "source": dprime_two["artifact_digest"]}
    )

    assert (
        multicomponent._qualify_searchos_read_material_after_component_dprime(
            run_kernel=kernel,
            component_ref=component_two,
            bindable=bindable_two,
            dprime_artifact=dprime_two,
        )
        == first_bindable.evidence_ref_id
    )
    projection = kernel.state.evidence_ledger.to_projection().to_dict()
    observations, qualification_custody = _qualification_records(projection)
    requirement_ids = {item["requirement_id"] for item in qualification_custody}
    physical = kernel.state.evidence_ledger.to_fetch_read_candidate_custody_projection()[
        "fetch_read_candidate_custody_records"
    ]

    assert len(observations) == len(qualification_custody) == 2
    assert len({item["observation_id"] for item in observations}) == 2
    assert len(requirement_ids) == 2
    assert (
        sum(
            item["candidate_id"] == first_bindable.evidence_ref_id
            and item["requirement_id"] in requirement_ids
            and item["link_status"] == "accepted"
            for item in projection["requirement_links"]
        )
        == 2
    )
    assert [item["candidate_id"] for item in physical].count(first_bindable.evidence_ref_id) == 1


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
    assert len(runtime_capture["final_material_ledger_projections"]) == 1
    assert harness.run_kernel.state.final_answer_packet["final_answer_allowed"] is False
    slot = next(iter(state["slots_by_id"].values()))
    before = harness.dispositions_before_navigation_assessment
    assert slot["candidate_option_dispositions"] == before
    assert "" not in slot["candidate_option_dispositions"]
    assert all(record.get("candidate_use_option_id") for record in slot["candidate_option_dispositions"].values())
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
        deps_overrides={"searchos_read_acquisition_transports": AcquisitionTransports(tavily_extract=transport)},
    )
    state = harness.run_kernel.state.searchos_state
    slot = next(iter(state["slots_by_id"].values()))
    option = next(NavigationOption.from_dict(item) for item in state["navigation"]["options_by_id"].values())
    assert transport_calls == [PARENT_URL, CHILD_URL]
    assert option.disposition == "destination_failed"
    assert slot["posture"] == "unresolved_handoff"
    assert outcome.execution_trace["searchos_slice_a"]["provider_calls_attempted"] == 2
    assert harness.searchos_product_result.provider_calls_attempted == 2
    assert outcome.failure_card


def test_post_ledger_invariant_propagates_and_discards_locator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
                for item in self.state.evidence_ledger.to_projection().to_dict()["candidate_records"]
            }
            physical = self.state.evidence_ledger.to_fetch_read_candidate_custody_projection()[
                "fetch_read_candidate_custody_records"
            ]
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
