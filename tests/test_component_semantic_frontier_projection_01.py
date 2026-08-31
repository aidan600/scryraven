"""N2-COMPONENT-SEMANTIC-FRONTIER-PROJECTION-01 offline proof.

Test path: tests/test_component_semantic_frontier_projection_01.py
Proof class: offline_product_path_projection_proof.
Validation bucket: phase_focus.
Surface guarded: zero-authority component frontier and bounded PRODUCT packet.
High-custody or closed-this-phase surface: SearchOS, Component Analyst, and
component-admission semantics remain unchanged.
Runtime/product path guarded: selected component lane to normal/failure packet.
Expected cost: sub-second deterministic projection and packaging fixtures.
Promotion posture: remain phase_focus until a broader durable lane subsumes it.
Demotion/retirement condition: retire with the bounded PRODUCT packet schema.
Why not fast_pr: phase-detail privacy and terminal-packaging proof.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.component_semantic_frontier_projection import (
    attach_component_semantic_frontier_to_exception,
    build_component_semantic_frontier_v1,
)
from core.component_work_graph_v1 import ComponentWorkGraphV1Error
from core.multicomponent_component_admission import (
    COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION,
)
from scripts import ag_live_bound_01_bounded_product_runner as runner
from scripts import ag_live_bound_01_support as support

ROOT = Path(__file__).resolve().parents[1]
CANARY_CLAIM = "PRIVATE-ANALYST-CLAIM-CANARY"
CANARY_TEXT = "PRIVATE-READ-BODY-CANARY"


def _accepted_contract() -> dict:
    return {
        "accepted_answer_component_refs": [
            {
                "component_id": "component-1",
                "component_digest": "1" * 64,
            },
            {
                "component_id": "component-2",
                "component_digest": "2" * 64,
            },
        ]
    }


def _searchos_state(*, handed_off: bool = True) -> dict:
    posture = "semantically_handed_off" if handed_off else "budget_exhausted"
    slots = {}
    handoff_refs = []
    for ordinal in (1, 2):
        component_id = f"component-{ordinal}"
        slot_id = f"slot-{ordinal}"
        handoff_ref = {
            "semantic_handoff_id": f"handoff-{ordinal}",
            "semantic_handoff_digest": str(ordinal) * 64,
        }
        slots[slot_id] = {
            "posture": posture,
            "slot_ref": {
                "slot_id": slot_id,
                "component_id": component_id,
                "source_obligation_id": f"obligation-{ordinal}",
            },
            "source_obligation_ref": {
                "source_obligation_id": f"obligation-{ordinal}"
            },
            "custody_refs": (
                [
                    {
                        "read_custody_material_id": f"material-{ordinal}",
                        "read_custody_material_digest": str(ordinal) * 64,
                    }
                ]
                if handed_off
                else []
            ),
            "semantic_handoff_refs": [handoff_ref] if handed_off else [],
        }
        if handed_off:
            handoff_refs.append(handoff_ref)
    return {"slots_by_id": slots, "semantic_handoff_refs": handoff_refs}


def _semantic_handoffs() -> list[dict]:
    return [
        {
            "slot_ref": {
                "slot_id": f"slot-{ordinal}",
                "component_id": f"component-{ordinal}",
            },
            "read_custody_material_refs": [
                {
                    "read_custody_material_id": f"material-{ordinal}",
                    "read_custody_material_digest": str(ordinal) * 64,
                }
            ],
        }
        for ordinal in (1, 2)
    ]


def _packet(component_id: str) -> dict:
    ordinal = component_id[-1]
    return {
        "run_binding": {"run_id": "run-1", "request_id": "request-1"},
        "component_ref": {"component_id": component_id},
        "component_evidence": {
            "evidence_status": "available",
            "evidence_ref_id": f"material-{ordinal}",
            "bounded_text": CANARY_TEXT,
            "source_class": "official_current_rules",
            "source_tier": "official",
            "currentness": "current",
            "readability_posture": "readable",
        },
    }


def _artifact(component_id: str, posture: str) -> dict:
    supporting = posture in {"supported", "supported_with_caveats"}
    return {
        "artifact_digest": component_id[-1] * 64,
        "input_packet_digest": ("a" if component_id.endswith("1") else "b")
        * 64,
        "semantic_output": {
            "case_posture": posture,
            "claim_text": CANARY_CLAIM if supporting else None,
            "caveats": ["private caveat"] if posture == "supported_with_caveats" else [],
            "blockers": ["private blocker"] if not supporting else [],
            "unresolved_need": "private unresolved need" if not supporting else None,
            "missing_evidentiary_premise": (
                "private missing premise" if not supporting else None
            ),
        },
    }


def _admission(component_id: str, posture: str) -> dict:
    supporting = posture in {"supported", "supported_with_caveats"}
    return {
        "component_id": component_id,
        "component_digest": component_id[-1] * 64,
        "case_posture": posture,
        "admission_status": (
            "admitted_with_caveats"
            if posture == "supported_with_caveats"
            else "admitted"
            if supporting
            else "unsupported"
        ),
        "component_analyst_case_ref": {
            "artifact_digest": component_id[-1] * 64,
            "input_packet_digest": (
                "a" if component_id.endswith("1") else "b"
            )
            * 64,
        },
        "admitted_claim_ref": {"claim_id": "opaque"} if supporting else {},
        "semantic_observation_ref": (
            {"observation_id": "opaque"} if supporting else {}
        ),
        "component_coverage_ref": (
            {"coverage_record_id": "opaque"} if supporting else {}
        ),
    }


def _projection(
    *,
    component_two_posture: str = "unsupported",
    mismatch: dict | None = None,
    admission_exception_class: str | None = None,
) -> dict:
    packets = {
        component_id: _packet(component_id)
        for component_id in ("component-1", "component-2")
    }
    artifacts = {
        "multicomponent_role:component_analyst:component-1": _artifact(
            "component-1", "supported"
        ),
        "multicomponent_role:component_analyst:component-2": _artifact(
            "component-2", component_two_posture
        ),
    }
    admissions = [_admission("component-1", "supported")]
    if mismatch is None:
        admissions.append(_admission("component-2", component_two_posture))
    return build_component_semantic_frontier_v1(
        accepted_contract=_accepted_contract(),
        searchos_state=_searchos_state(),
        scheduler_context={"component_analyst_input_packets": packets},
        role_artifacts=artifacts,
        component_admission_projection={"component_admission_refs": admissions},
        semantic_handoffs=_semantic_handoffs(),
        input_binding_mismatch_projection=mismatch,
        admission_exception_class=admission_exception_class,
    )


def _component(projection: dict, component_id: str) -> dict:
    return next(
        item
        for item in projection["components"]
        if item["component_id"] == component_id
    )


def _mismatch() -> dict:
    return {
        "schema_version": COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION,
        "mismatch_class": "SUPPLIED_PACKET_CHANGED",
        "first_divergent_section": "component_evidence",
        "accepted_authority_source": "current",
        "accepted_component_id": "component-2",
    }


def test_projection_distinguishes_supply_analyst_handoff_and_advanced_shapes() -> None:
    supply = build_component_semantic_frontier_v1(
        accepted_contract=_accepted_contract(),
        searchos_state=_searchos_state(handed_off=False),
        scheduler_context={},
        role_artifacts={},
        component_admission_projection={},
    )
    supply_two = _component(supply, "component-2")
    assert supply_two["semantic_handoff_present"] is False
    assert supply_two["analyst_input_packet_present"] is False
    assert supply_two["analyst_executed"] is False

    handoff_defect = _projection(
        mismatch=_mismatch(),
        admission_exception_class="MulticomponentComponentAdmissionError",
    )
    defect_two = _component(handoff_defect, "component-2")
    assert defect_two["semantic_handoff_present"] is True
    assert defect_two["analyst_input_packet_present"] is True
    assert defect_two["analyst_executed"] is True
    assert defect_two["component_admission_ref_present"] is False
    assert defect_two["admission_exception_present"] is True
    assert defect_two["input_binding_mismatch_projection_present"] is True

    analyst_non_support = _component(_projection(), "component-2")
    assert analyst_non_support["analyst_input_evidence_ref_present"] is True
    assert analyst_non_support["case_posture"] == "unsupported"
    assert analyst_non_support["claim_present"] is False
    assert analyst_non_support["admission_status"] == "unsupported"

    advanced = _component(
        _projection(component_two_posture="supported_with_caveats"),
        "component-2",
    )
    assert advanced["case_posture"] == "supported_with_caveats"
    assert advanced["admission_status"] == "admitted_with_caveats"
    assert advanced["semantic_observation_ref_present"] is True
    assert advanced["component_coverage_ref_present"] is True


def test_projection_is_non_mutating_zero_authority_and_private() -> None:
    accepted = _accepted_contract()
    searchos = _searchos_state()
    scheduler = {
        "component_analyst_input_packets": {
            component_id: _packet(component_id)
            for component_id in ("component-1", "component-2")
        }
    }
    artifacts = {
        "multicomponent_role:component_analyst:component-1": _artifact(
            "component-1", "supported"
        ),
        "multicomponent_role:component_analyst:component-2": _artifact(
            "component-2", "unsupported"
        ),
    }
    admissions = {
        "component_admission_refs": [
            _admission("component-1", "supported"),
            _admission("component-2", "unsupported"),
        ]
    }
    before = deepcopy((accepted, searchos, scheduler, artifacts, admissions))
    projected = build_component_semantic_frontier_v1(
        accepted_contract=accepted,
        searchos_state=searchos,
        scheduler_context=scheduler,
        role_artifacts=artifacts,
        component_admission_projection=admissions,
        semantic_handoffs=_semantic_handoffs(),
    )
    assert (accepted, searchos, scheduler, artifacts, admissions) == before
    serialized = json.dumps(projected, sort_keys=True)
    assert CANARY_CLAIM not in serialized
    assert CANARY_TEXT not in serialized
    assert "bounded_text" not in serialized
    assert "claim_text" not in serialized
    assert "url" not in serialized


def _stub_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_load_live_environment", lambda: None)
    monkeypatch.setattr(runner, "_validate_live_model_keys", lambda: None)
    monkeypatch.setattr(runner, "_build_live_run_deps", lambda: SimpleNamespace())
    monkeypatch.setattr(
        "core.quantitative_specialist_product_activation.compose_quantitative_specialist_product_deps",
        lambda deps: deps,
    )
    monkeypatch.setattr(
        runner,
        "_live_runtime_helpers",
        lambda: (SimpleNamespace(), SimpleNamespace()),
    )
    monkeypatch.setattr(
        runner,
        "_build_live_run_config",
        lambda context, cap_policy: SimpleNamespace(
            query=context.query,
            mode=context.mode,
            fast_provider="FixtureFastProvider",
            fast_model="fixture-fast-model",
            smart_provider="FixtureSmartProvider",
            smart_model="fixture-smart-model",
            embed_provider="FixtureEmbedProvider",
            embed_model="fixture-embed-model",
            cap_policy=cap_policy,
        ),
    )


def test_graph_terminal_failure_packet_preserves_frontier_not_component_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projection = _projection()
    exc = ComponentWorkGraphV1Error(
        "synthesis proposal depends on an unadmitted component: component-2"
    )
    attach_component_semantic_frontier_to_exception(exc, projection)
    _stub_runner(monkeypatch)
    output = Path("C:/tmp/component_semantic_frontier_failure.json")
    with patch("core.pipeline_orchestrator.run_pipeline", side_effect=exc):
        result = runner.main(
            [
                "--query",
                support.PRIMARY_QUERY,
                "--mode",
                support.REQUIRED_MODE,
                "--include-domains",
                support.REQUIRED_DOMAIN,
                "--output",
                str(output),
                "--external-output-root",
                "C:/tmp",
                "--confirm-live-product-run",
            ]
        )
    assert result == 2
    packet = json.loads(output.read_text(encoding="utf-8"))
    output.unlink(missing_ok=True)
    summaries = packet["sanitized_projection_summaries"]
    assert summaries["component_binding"] == {"available": False}
    assert summaries["component_semantic_frontier"]["available"] is True
    assert summaries["component_semantic_frontier"]["component_count"] == 2
    component_two = _component(
        summaries["component_semantic_frontier"], "component-2"
    )
    assert component_two["case_posture"] == "unsupported"
    assert component_two["admission_status"] == "unsupported"
    assert CANARY_CLAIM not in json.dumps(packet, sort_keys=True)
    assert CANARY_TEXT not in json.dumps(packet, sort_keys=True)
    support.reject_forbidden_packet(packet)


def test_success_packet_additively_projects_frontier() -> None:
    projection = _projection(component_two_posture="supported")
    outcome = SimpleNamespace(
        execution_trace={
            "component_semantic_frontier_v1": projection,
            "final_answer_packet": {},
        },
        report="",
        sources=[],
        run_id="run-1",
        session_id="request-1",
        terminal_status="completed",
    )
    profile = support.get_validation_profile(support.DEFAULT_PROFILE_NAME)
    caps = support.validate_caps_requested(
        profile.cap_policy.as_requested_dict(), profile_name=profile.name
    )
    context = support.build_preflight_context(
        root=ROOT,
        profile_name=profile.name,
        query=support.PRIMARY_QUERY,
        mode=support.REQUIRED_MODE,
        include_domains=[support.REQUIRED_DOMAIN],
        output_path=Path("C:/tmp/component_semantic_frontier_success.json"),
        caps=caps,
        run_id="run-1",
        confirm_live_product_run=True,
        approved_backup_query=False,
        external_output_root=Path("C:/tmp"),
    )
    packet = support.build_live_success_packet(
        context,
        outcome=outcome,
        cap_policy=caps.to_run_cap_policy(),
    )
    summaries = packet["sanitized_projection_summaries"]
    assert summaries["component_semantic_frontier"]["available"] is True
    assert summaries["component_binding"]["available"] is False
    support.reject_forbidden_packet(packet)
