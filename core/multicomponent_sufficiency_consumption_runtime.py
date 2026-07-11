"""Ordinary Sufficiency consumption of canonical ComponentWorkGraph V1 state."""

from __future__ import annotations

from typing import Any, Mapping

from core.component_work_graph_v1 import (
    COMPONENT_WORK_GRAPH_V1_OWNER,
    GRAPH_STATUS_READY,
    GRAPH_STATUS_READY_WITH_CAVEATS,
    validate_component_work_graph_v1,
)


class MulticomponentSufficiencyConsumptionError(ValueError):
    """Raised when Graph V1 state is not canonical enough for Sufficiency."""


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _unique_text(values: list[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        text = " ".join(str(value or "").strip().split())
        if text and text not in out:
            out.append(text[:1000])
    return out


def build_multicomponent_graph_consumption(
    graph_state: Mapping[str, Any] | None,
    *,
    current_contract_version: str | None = None,
    current_contract_digest: str | None = None,
) -> dict[str, Any]:
    """Project only current, RunKernel-admitted output candidates."""

    if not graph_state:
        return {}
    graph = validate_component_work_graph_v1(graph_state)
    if (
        graph.get("owner") != COMPONENT_WORK_GRAPH_V1_OWNER
        or graph.get("canonical_state") is not True
    ):
        raise MulticomponentSufficiencyConsumptionError(
            "Sufficiency requires canonical RunKernel Graph V1 state"
        )
    contract_ref = _mapping(graph.get("accepted_contract_ref"))
    graph_contract_current = not (
        current_contract_version
        and current_contract_digest
        and (
            contract_ref.get("accepted_contract_version")
            != current_contract_version
            or contract_ref.get("accepted_contract_digest")
            != current_contract_digest
        )
    )

    direct_entries: list[dict[str, Any]] = []
    limitations: list[str] = []
    caveats: list[Any] = []
    nonclaims: list[Any] = []
    for node in graph["component_nodes"]:
        admitted = node.get("admission_status") in {
            "admitted",
            "admitted_with_caveats",
        }
        current = node.get("current") is True and node.get("stale") is not True
        graph_eligible = (
            node.get("direct_output_eligible") is True
            and node.get("component_id") in graph.get("direct_output_component_ids", ())
            and graph.get("graph_output_suppressed") is not True
        )
        claim = _mapping(node.get("admitted_claim_ref"))
        if admitted and current and graph_eligible and claim.get("claim_text"):
            direct_entries.append(
                {
                    "entry_kind": "direct_component",
                    "component_id": node.get("component_id"),
                    "component_label": node.get("component_label"),
                    "component_question": node.get("component_question"),
                    "claim_id": claim.get("claim_id"),
                    "claim_text": claim.get("claim_text"),
                    "claim_digest": claim.get("claim_digest"),
                    "admission_status": node.get("admission_status"),
                    "current": True,
                    "stale": False,
                    "semantic_observation_ref": _mapping(
                        node.get("semantic_observation_ref")
                    ),
                    "component_coverage_ref": _mapping(
                        node.get("component_coverage_ref")
                    ),
                    "evidence_refs": list(node.get("evidence_refs") or ()),
                    "required_caveats": list(
                        node.get("required_caveats") or ()
                    ),
                    "preserved_nonclaims": list(
                        node.get("preserved_nonclaims") or ()
                    ),
                }
            )
            caveats.extend(node.get("required_caveats") or ())
            nonclaims.extend(node.get("preserved_nonclaims") or ())
        else:
            limitations.append(
                f"Component {node.get('component_id')} omitted: "
                f"{node.get('admission_status') or 'not admitted'} or not currently "
                "eligible under Graph V1 challenge posture."
            )

    graph_ready = graph_contract_current and graph.get("graph_status") in {
        GRAPH_STATUS_READY,
        GRAPH_STATUS_READY_WITH_CAVEATS,
    }
    synthesis_entries: list[dict[str, Any]] = []
    for node in graph["synthesis_nodes"]:
        admitted = node.get("status") == "admitted"
        current = node.get("current") is True and node.get("stale") is not True
        graph_output_allowed = (
            graph_contract_current
            and graph.get("graph_output_suppressed") is not True
        )
        if graph_output_allowed and admitted and current:
            synthesis_entries.append(
                {
                    "entry_kind": "admitted_synthesis",
                    "synthesis_key": node.get("synthesis_key"),
                    "synthesis_depth": node.get("synthesis_depth"),
                    "claim_text": node.get("claim_text"),
                    "claim_id": _mapping(node.get("synthesis_claim_ref")).get(
                        "claim_id"
                    ),
                    "claim_digest": _mapping(
                        node.get("synthesis_claim_ref")
                    ).get("claim_digest"),
                    "relationship_type": node.get("relationship_type"),
                    "status": "admitted",
                    "current": True,
                    "stale": False,
                    "input_node_refs": list(node.get("input_node_refs") or ()),
                    "dprime_validation_ref": _mapping(
                        node.get("dprime_validation_ref")
                    ),
                    "scrutineer_ref": _mapping(node.get("scrutineer_ref")),
                    "runkernel_admission_ref": _mapping(
                        node.get("runkernel_admission_ref")
                    ),
                    "required_caveats": list(
                        node.get("required_caveats") or ()
                    ),
                    "preserved_nonclaims": list(
                        node.get("preserved_nonclaims") or ()
                    ),
                }
            )
            caveats.extend(node.get("required_caveats") or ())
            nonclaims.extend(node.get("preserved_nonclaims") or ())
        else:
            limitations.append(
                f"Synthesis {node.get('synthesis_key')} omitted: "
                f"{node.get('status') or 'not admitted'} under graph posture "
                f"{graph.get('graph_status')}."
            )

    if not graph_contract_current:
        limitations.insert(
            0,
            "Combined synthesis is unavailable because Graph V1 is bound to a prior AnswerContract version.",
        )
    elif not graph_ready and not synthesis_entries:
        limitations.insert(
            0,
            f"Combined synthesis is unavailable because Graph V1 posture is "
            f"{graph.get('graph_status')}.",
        )
    elif not graph_ready:
        limitations.insert(
            0,
            f"Only unaffected admitted synthesis remains available under Graph V1 "
            f"posture {graph.get('graph_status')}.",
        )
    return {
        "schema_version": "multicomponent_sufficiency_consumption_v1",
        "owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "source_owner": graph.get("owner"),
        "source_canonical_state": True,
        "supported_query_class": graph.get("supported_query_class"),
        "graph_id": graph.get("graph_id"),
        "graph_revision": graph.get("graph_revision"),
        "graph_digest": graph.get("graph_digest"),
        "graph_readiness_status": graph.get("graph_status"),
        "graph_contract_current": graph_contract_current,
        "graph_contract_version": contract_ref.get("accepted_contract_version"),
        "graph_contract_digest": contract_ref.get("accepted_contract_digest"),
        "graph_ready_for_synthesis": graph_ready,
        "direct_component_entries": direct_entries,
        "admitted_synthesis_entries": synthesis_entries,
        "limitations": _unique_text(limitations),
        "mandatory_caveats": _unique_text(caveats),
        "preserved_nonclaims": _unique_text(nonclaims),
        "direct_component_entry_count": len(direct_entries),
        "admitted_synthesis_entry_count": len(synthesis_entries),
        "omitted_synthesis_entry_count": len(graph["synthesis_nodes"])
        - len(synthesis_entries),
        "ordinary_sufficiency_decision_created": True,
        "final_answer_packet_created": False,
        "author_output_created": False,
    }


__all__ = [
    "MulticomponentSufficiencyConsumptionError",
    "build_multicomponent_graph_consumption",
]
