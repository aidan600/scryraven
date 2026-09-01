"""Offline proof for the initial Cross packet authority convergence.

Test path/node id: this module's three tests
Proof class: offline_product_path_projection_proof
Validation bucket: phase_focus
Surface guarded: initial Cross packet binding and Graph V1 currentness
High-custody or closed-this-phase surface: Cross semantics remain closed
Runtime/product path guarded: ordinary offline scheduler-to-Graph V1 path
Expected cost: two bounded synthetic ordinary runs, under one minute locally
Promotion posture: phase-local proof; not a fast_pr sentinel
Demotion/retirement condition: retire when the Cross authority boundary is
replaced by a single durable contract test
Why not fast_pr: the test exercises a phase-specific authority seam and uses
full ordinary multi-component synthesis setup.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import core.component_work_graph_v1 as graph_runtime
import core.ordinary_multicomponent_synthesis_runtime as multicomponent_runtime
import core.pipeline_orchestrator as orchestrator
from core.component_work_graph_v1 import (
    ComponentWorkGraphV1Error,
    cross_component_input_packet,
)
from core.cost_accounting import CostAccumulator
from core.multicomponent_role_runtime import (
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SYSTEM_PROMPTS,
    safe_packet_digest,
)
from core.protocols import NullStatusWriter
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_SEMANTIC,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)
from tests.test_multicomponent_ordinary_end_to_end_synthesis_01 import (
    NorthstarHarness,
)


def _run_northstar(
    *,
    harness: NorthstarHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, Any], Any]:
    scrub_offline_runtime(monkeypatch)
    monkeypatch.setattr(
        multicomponent_runtime,
        "execute_ordinary_semantic_producer_handoff_from_scope",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("the qualifying offline run must use the typed lane")
        ),
    )
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_SEMANTIC,),
    )
    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-10",
            session_id="cross-authority-session",
            run_id="cross-authority-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    return captured, outcome


def _first_top_level_difference(
    supplied: dict[str, Any],
    rebuilt: dict[str, Any],
) -> str | None:
    for key in supplied:
        if supplied.get(key) != rebuilt.get(key):
            return key
    for key in rebuilt:
        if key not in supplied:
            return key
    return None


def test_initial_cross_uses_one_scheduler_packet_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = NorthstarHarness(tmp_path)
    observed: dict[str, Any] = {}

    real_scheduler_packet = multicomponent_runtime._scheduler_work_input_packet

    def capture_scheduler_packet(**kwargs: Any) -> dict[str, Any]:
        packet = real_scheduler_packet(**kwargs)
        work = kwargs["work"]
        if work.get("role") == ROLE_CROSS_COMPONENT_ANALYST and not kwargs["run_kernel"].state.projections.get(
            graph_runtime.COMPONENT_WORK_GRAPH_V1_STAGE
        ):
            observed["scheduled_work_input_packet_digest"] = work.get(
                "input_packet_digest"
            )
            observed["scheduled_packet_digest"] = safe_packet_digest(packet)
        return packet

    monkeypatch.setattr(
        multicomponent_runtime,
        "_scheduler_work_input_packet",
        capture_scheduler_packet,
    )

    real_graph_builder = (
        multicomponent_runtime.component_work_graph_v1_from_cross_component_artifact
    )

    def capture_graph_builder(**kwargs: Any) -> dict[str, Any]:
        artifact = kwargs["cross_component_artifact"]
        if artifact.get("logical_evaluation_key") == "graph-v1":
            kernel = observed["kernel"]
            supplied = kwargs["transient_cross_input_packet"]
            supplied_packets = kwargs["component_analyst_input_packets"]
            state_packets = kernel.state.multicomponent_scheduler_context[
                "component_analyst_input_packets"
            ]
            rebuilt = cross_component_input_packet(
                component_nodes=kwargs["component_nodes"],
                accepted_contract_ref=kwargs["accepted_contract_ref"],
                requested_synthesis_directive=kwargs[
                    "requested_synthesis_directive"
                ],
                component_analyst_input_packets=supplied_packets,
                accepted_component_refs=kwargs["accepted_component_refs"],
                requested_mode=kwargs["requested_mode"],
            )
            observed.update(
                {
                    "supplied_cross_packet_digest": safe_packet_digest(supplied),
                    "cross_artifact_input_binding_digest": artifact.get(
                        "input_packet_digest"
                    ),
                    "post_cross_rebuilt_packet_digest": safe_packet_digest(rebuilt),
                    "first_different_top_level_key": _first_top_level_difference(
                        supplied, rebuilt
                    ),
                    "same_packet_source": supplied_packets is state_packets,
                    "same_packet_values": all(
                        supplied_packets[component_id]
                        is state_packets[component_id]
                        for component_id in state_packets
                    ),
                }
            )
        return real_graph_builder(**kwargs)

    monkeypatch.setattr(
        multicomponent_runtime,
        "component_work_graph_v1_from_cross_component_artifact",
        capture_graph_builder,
    )

    real_consume = multicomponent_runtime._consume_scheduler_selected_artifact

    def inspect_drive_context(**kwargs: Any) -> None:
        work = kwargs["work"]
        if work.get("role") == ROLE_CROSS_COMPONENT_ANALYST and not kwargs["run_kernel"].state.projections.get(
            graph_runtime.COMPONENT_WORK_GRAPH_V1_STAGE
        ):
            observed["kernel"] = kwargs["run_kernel"]
            observed["drive_context_packet_source_present"] = (
                "component_analyst_input_packets" in kwargs["drive_context"]
            )
        return real_consume(**kwargs)

    monkeypatch.setattr(
        multicomponent_runtime,
        "_consume_scheduler_selected_artifact",
        inspect_drive_context,
    )

    captured, outcome = _run_northstar(harness=harness, monkeypatch=monkeypatch)

    assert outcome.terminal_status == "completed"
    assert observed["scheduled_work_input_packet_digest"] == observed[
        "scheduled_packet_digest"
    ]
    assert observed["supplied_cross_packet_digest"] == observed[
        "scheduled_packet_digest"
    ]
    assert observed["cross_artifact_input_binding_digest"] == observed[
        "supplied_cross_packet_digest"
    ]
    assert observed["post_cross_rebuilt_packet_digest"] == observed[
        "supplied_cross_packet_digest"
    ]
    assert observed["first_different_top_level_key"] is None
    assert observed["drive_context_packet_source_present"] is False
    assert observed["same_packet_source"] is False
    assert observed["same_packet_values"] is True
    assert captured["semantic_run_kernel"].state.projections.get(
        graph_runtime.COMPONENT_WORK_GRAPH_V1_STAGE
    )


def test_initial_cross_remains_fail_closed_when_canonical_packet_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = NorthstarHarness(tmp_path)
    real_consume = multicomponent_runtime._consume_scheduler_selected_artifact

    def mutate_scheduler_authority(**kwargs: Any) -> None:
        work = kwargs["work"]
        run_kernel = kwargs["run_kernel"]
        if work.get("role") == ROLE_CROSS_COMPONENT_ANALYST and not run_kernel.state.projections.get(
            graph_runtime.COMPONENT_WORK_GRAPH_V1_STAGE
        ):
            packets = run_kernel.state.multicomponent_scheduler_context[
                "component_analyst_input_packets"
            ]
            component_id = sorted(packets)[0]
            packets[component_id]["component_ref"]["component_digest"] = (
                "offline-currentness-change"
            )
        return real_consume(**kwargs)

    monkeypatch.setattr(
        multicomponent_runtime,
        "_consume_scheduler_selected_artifact",
        mutate_scheduler_authority,
    )

    with pytest.raises(
        ComponentWorkGraphV1Error,
        match="Cross input reconstruction component packet binding mismatch",
    ):
        _run_northstar(harness=harness, monkeypatch=monkeypatch)


def test_initial_cross_binds_deterministic_component_aliases_to_current_nodes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = NorthstarHarness(tmp_path)
    original_ask_model = harness.ask_model

    def ask_model_with_local_component_aliases(
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if system_prompt != ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
            return original_ask_model(prompt, system_prompt, **kwargs)
        payload = json.loads(prompt)
        harness.role_input_packets.append(
            {"system_prompt": system_prompt, "input_packet": payload}
        )
        harness.model_calls.append(
            {
                "system_prompt": system_prompt,
                "stream": bool(kwargs.get("stream")),
                "provider": kwargs.get("provider"),
                "model": kwargs.get("model"),
                "use_reasoning": kwargs.get("use_reasoning"),
            }
        )
        return json.dumps(
            {
                "synthesis_proposals": [
                    {
                        "synthesis_key": "S",
                        "claim_text": (
                            "The first two requested Northstar facts are both "
                            "established by their admitted components."
                        ),
                        "relationship_type": "bounded_comparison",
                        "component_inputs": ["component_01", "component_02"],
                        "synthesis_inputs": [],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                ],
                "self_audit": (
                    "The offline comparison stays within the exact current "
                    "Northstar component cases."
                ),
            }
        )

    monkeypatch.setattr(harness, "ask_model", ask_model_with_local_component_aliases)

    captured, _outcome = _run_northstar(harness=harness, monkeypatch=monkeypatch)

    graph = captured["semantic_run_kernel"].state.projections[
        graph_runtime.COMPONENT_WORK_GRAPH_V1_STAGE
    ]
    component_node_ids = [
        item["node_id"] for item in graph["component_nodes"][:2]
    ]
    synthesis_node = graph["synthesis_nodes"][0]
    assert [
        item["node_id"] for item in synthesis_node["input_node_refs"]
    ] == component_node_ids
