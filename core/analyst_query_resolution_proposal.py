"""Shared Analyst-owned query-resolution proposal and arbitration authority.

Component Analyst and Cross-Component Analyst emit bounded local candidates.
This module binds those candidates to their exact role artifact and recorded
contract/graph inputs.  It does not admit an amendment, create SearchOS work,
admit graph relationships, or select between nonidentical semantic proposals.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping, Sequence

ANALYST_QUERY_RESOLUTION_PROPOSAL_SCHEMA_VERSION = "analyst_query_resolution_proposal_v1"
ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY = "analyst_query_resolution_proposal"

CLASS_EXISTING_COMPONENT_GAP = "existing_component_gap"
CLASS_SEARCHED_PREMISE = "searched_premise"
CLASS_INFERRED_CONCLUSION = "inferred_conclusion"
ALLOWED_CLASSIFICATIONS = frozenset(
    {
        CLASS_EXISTING_COMPONENT_GAP,
        CLASS_SEARCHED_PREMISE,
        CLASS_INFERRED_CONCLUSION,
    }
)
ALLOWED_ORIGINATING_ROLES = frozenset({"component_analyst", "cross_component_analyst"})
PROPOSAL_LIFECYCLE_STATUSES = frozenset(
    {
        "pending",
        "consumed",
        "ambiguous",
        "rejected",
        "superseded_stale",
        "exact_replay",
    }
)

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "cache",
        "cookie",
        "db_row",
        "env",
        "full_prompt",
        "full_trace",
        "logs",
        "model_response",
        "password",
        "private_log",
        "provider_payload",
        "raw_model_response",
        "raw_prompt",
        "raw_provider_payload",
        "raw_search_response",
        "raw_source_text",
        "secret",
        "token",
    }
)


class AnalystQueryResolutionProposalError(ValueError):
    """Raised when proposal content, lineage, replay, or arbitration is invalid."""


def _clean_text(value: Any, *, limit: int = 800) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] or None


def _token(value: Any, *, limit: int = 180) -> str | None:
    return _clean_text(value, limit=limit)


def _local_key(value: Any) -> str:
    text = _token(value, limit=80) or ""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,79}", text):
        raise AnalystQueryResolutionProposalError("query-resolution proposal requires a bounded local key")
    return text


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return list(value)
    return []


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AnalystQueryResolutionProposalError(f"{label} must be a mapping")
    return deepcopy(dict(value))


def _safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=1600)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key in sorted(value, key=str):
            key = _token(raw_key, limit=120)
            if not key:
                continue
            normalized_key = key.casefold()
            if normalized_key != "raw_private_retained" and (
                normalized_key.startswith("raw_") or normalized_key in _SENSITIVE_KEYS
            ):
                raise AnalystQueryResolutionProposalError(
                    f"query-resolution proposal contains forbidden private field {key}"
                )
            result[key] = _safe(value[raw_key], depth=depth + 1)
        return result
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_safe(item, depth=depth + 1) for item in list(value)[:80]]
    return _clean_text(value, limit=300)


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _required_text(mapping: Mapping[str, Any], key: str, *, limit: int = 800) -> str:
    text = _clean_text(mapping.get(key), limit=limit)
    if not text:
        raise AnalystQueryResolutionProposalError(f"query-resolution proposal requires {key}")
    return text


def _required_choice(
    mapping: Mapping[str, Any],
    key: str,
    choices: frozenset[str],
) -> str:
    value = _token(mapping.get(key))
    if value not in choices:
        raise AnalystQueryResolutionProposalError(f"query-resolution proposal {key} is invalid")
    return value


def _text_list(
    value: Any,
    *,
    label: str,
    nonempty: bool = False,
    canonical_sorted: bool = False,
) -> list[str]:
    values: list[str] = []
    for item in _sequence(value):
        text = _token(item)
        if text:
            values.append(text)
    if len(values) != len(set(values)):
        raise AnalystQueryResolutionProposalError(f"{label} must contain unique refs")
    if nonempty and not values:
        raise AnalystQueryResolutionProposalError(f"{label} must be nonempty")
    if canonical_sorted and values != sorted(values):
        raise AnalystQueryResolutionProposalError(f"{label} must use canonical sorted order")
    return values


def _ref_list(
    value: Any,
    *,
    label: str,
    nonempty: bool = False,
    canonical_sorted: bool = False,
) -> list[dict[str, Any]]:
    refs = [_mapping(item, label) for item in _sequence(value)]
    identities = [_digest(_safe(ref)) for ref in refs]
    if len(identities) != len(set(identities)):
        raise AnalystQueryResolutionProposalError(f"{label} must contain unique refs")
    if nonempty and not refs:
        raise AnalystQueryResolutionProposalError(f"{label} must be nonempty")
    if canonical_sorted and identities != sorted(identities):
        raise AnalystQueryResolutionProposalError(f"{label} must use canonical sorted order")
    return [_safe(ref) for ref in refs]


def _component_ref_list(
    value: Any,
    *,
    label: str,
    nonempty: bool = False,
) -> list[dict[str, Any]]:
    refs = _ref_list(
        value,
        label=label,
        nonempty=nonempty,
        canonical_sorted=True,
    )
    if any(
        not all(
            _token(ref.get(key))
            for key in (
                "component_id",
                "component_revision",
                "component_digest",
            )
        )
        for ref in refs
    ):
        raise AnalystQueryResolutionProposalError(f"{label} requires exact component id, revision, and digest")
    return refs


def normalize_local_query_resolution_candidate(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize one model-authored local candidate without granting authority."""

    candidate = _mapping(value, "query-resolution candidate")
    classification = _token(candidate.get("classification"))
    if classification not in ALLOWED_CLASSIFICATIONS:
        raise AnalystQueryResolutionProposalError("query-resolution proposal classification is invalid")
    local_proposal_key = _local_key(candidate.get("local_proposal_key"))
    local_target_key = _local_key(candidate.get("local_target_key"))
    common = {
        "classification": classification,
        "local_proposal_key": local_proposal_key,
        "local_target_key": local_target_key,
        "assumptions": _text_list(
            candidate.get("assumptions"),
            label="assumptions",
        ),
        "caveats": _text_list(candidate.get("caveats"), label="caveats"),
        "prohibited_upgrades": _text_list(
            candidate.get("prohibited_upgrades"),
            label="prohibited_upgrades",
        ),
    }
    if "answer_target_ref" in candidate and classification != CLASS_INFERRED_CONCLUSION:
        raise AnalystQueryResolutionProposalError(
            "singular answer_target_ref is not allowed in the common proposal envelope"
        )

    if classification == CLASS_EXISTING_COMPONENT_GAP:
        payload = {
            **common,
            "current_component_ref": _safe(
                _mapping(
                    candidate.get("current_component_ref"),
                    "current_component_ref",
                )
            ),
            "affected_answer_target_refs": _ref_list(
                candidate.get("affected_answer_target_refs"),
                label="affected_answer_target_refs",
                canonical_sorted=True,
            ),
            "source_obligation_ref": _safe(
                _mapping(
                    candidate.get("source_obligation_ref"),
                    "source_obligation_ref",
                )
            ),
            "current_coverage_or_gap_ref": _safe(
                _mapping(
                    candidate.get("current_coverage_or_gap_ref"),
                    "current_coverage_or_gap_ref",
                )
            ),
            "why_no_new_component_required": _required_text(
                candidate,
                "why_no_new_component_required",
            ),
        }
    elif classification == CLASS_SEARCHED_PREMISE:
        normalized_premise_identity = _required_text(
            candidate,
            "normalized_premise_identity",
            limit=240,
        )
        if normalized_premise_identity != normalized_premise_identity.casefold():
            raise AnalystQueryResolutionProposalError("searched premise normalized_premise_identity must be normalized")
        source_obligation_specification = _safe(
            _mapping(
                candidate.get("source_obligation_specification"),
                "source_obligation_specification",
            )
        )
        if any(
            not _token(source_obligation_specification.get(key))
            for key in ("candidate_id", "obligation_kind", "strictness")
        ):
            raise AnalystQueryResolutionProposalError(
                "searched premise source_obligation_specification requires "
                "candidate_id, obligation_kind, and strictness"
            )
        payload = {
            **common,
            "normalized_premise_identity": normalized_premise_identity,
            "answer_target_refs": _component_ref_list(
                candidate.get("answer_target_refs"),
                label="answer_target_refs",
                nonempty=True,
            ),
            "parent_component_refs": _component_ref_list(
                candidate.get("parent_component_refs"),
                label="parent_component_refs",
                nonempty=True,
            ),
            "current_dependency_component_refs": _component_ref_list(
                candidate.get("current_dependency_component_refs"),
                label="current_dependency_component_refs",
            ),
            "premise_semantics": _required_text(
                candidate,
                "premise_semantics",
            ),
            "user_facing_label": _required_text(
                candidate,
                "user_facing_label",
                limit=240,
            ),
            "user_facing_question": _required_text(
                candidate,
                "user_facing_question",
                limit=500,
            ),
            "acceptance_criteria": _text_list(
                candidate.get("acceptance_criteria"),
                label="acceptance_criteria",
                nonempty=True,
            ),
            "requirement_posture": _required_choice(
                candidate,
                "requirement_posture",
                frozenset({"required", "conditional", "optional"}),
            ),
            "materiality": _required_choice(
                candidate,
                "materiality",
                frozenset({"material", "non_material"}),
            ),
            "partial_answer_policy": _required_choice(
                candidate,
                "partial_answer_policy",
                frozenset(
                    {
                        "qualify_visible_gap",
                        "block_if_required_unsatisfied",
                        "allow_if_optional_only",
                    }
                ),
            ),
            "mandatory_caveats": _text_list(
                candidate.get("mandatory_caveats"),
                label="mandatory_caveats",
            ),
            "source_obligation_specification": source_obligation_specification,
            "necessity_rationale": _required_text(
                candidate,
                "necessity_rationale",
            ),
            "why_current_premises_insufficient": _required_text(
                candidate,
                "why_current_premises_insufficient",
            ),
            "searchability_material_need_posture": _required_text(
                candidate,
                "searchability_material_need_posture",
                limit=240,
            ),
            "recovery_generation": _safe(
                _mapping(
                    candidate.get("recovery_generation"),
                    "recovery_generation",
                )
            ),
        }
        depth = payload["recovery_generation"].get("depth")
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
            raise AnalystQueryResolutionProposalError(
                "searched premise recovery_generation.depth must be a positive integer"
            )
        if not _token(payload["recovery_generation"].get("parent_ref")):
            raise AnalystQueryResolutionProposalError("searched premise recovery_generation requires parent_ref")
    else:
        if any(
            key in candidate
            for key in (
                "source_obligation_ref",
                "source_obligation_specification",
                "recovery_generation",
            )
        ):
            raise AnalystQueryResolutionProposalError(
                "inferred conclusion cannot create source obligations or searched generations"
            )
        support_kind = _token(candidate.get("support_kind"))
        if support_kind != "inferred":
            raise AnalystQueryResolutionProposalError("inferred conclusion support_kind must be inferred")
        depth = candidate.get("proposed_semantic_inference_depth")
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
            raise AnalystQueryResolutionProposalError(
                "inferred conclusion requires a positive semantic inference depth"
            )
        payload = {
            **common,
            "answer_target_ref": _safe(
                _mapping(
                    candidate.get("answer_target_ref"),
                    "answer_target_ref",
                )
            ),
            "current_admitted_premise_node_refs": _ref_list(
                candidate.get("current_admitted_premise_node_refs"),
                label="current_admitted_premise_node_refs",
                nonempty=True,
                canonical_sorted=True,
            ),
            "relationship_type": _required_text(
                candidate,
                "relationship_type",
                limit=240,
            ),
            "proposed_conclusion": _required_text(
                candidate,
                "proposed_conclusion",
                limit=1200,
            ),
            "support_kind": "inferred",
            "proposed_semantic_inference_depth": depth,
            "current_graph_ref": _safe(_mapping(candidate.get("current_graph_ref"), "current_graph_ref")),
            "existing_specialist_handoff_refs": _ref_list(
                candidate.get("existing_specialist_handoff_refs"),
                label="existing_specialist_handoff_refs",
                canonical_sorted=True,
            ),
        }
    return _safe(payload)


def _target_refs(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    classification = candidate["classification"]
    if classification == CLASS_EXISTING_COMPONENT_GAP:
        refs = candidate.get("affected_answer_target_refs") or []
        if refs:
            return list(refs)
        return [candidate["current_component_ref"]]
    if classification == CLASS_SEARCHED_PREMISE:
        return list(candidate["answer_target_refs"])
    return [candidate["answer_target_ref"]]


def bind_analyst_query_resolution_proposal(
    *,
    role_artifact: Mapping[str, Any],
    local_candidate: Mapping[str, Any],
    question_meaning_record_ref: Mapping[str, Any],
    parent_contract_ref: Mapping[str, Any],
    parent_graph_ref: Mapping[str, Any] | None,
    scrutineer_finding_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind one local Analyst candidate to exact immutable role-input lineage."""

    artifact = _mapping(role_artifact, "role_artifact")
    role = _token(artifact.get("role"))
    if role not in ALLOWED_ORIGINATING_ROLES:
        raise AnalystQueryResolutionProposalError("query-resolution proposals may originate only from Analyst roles")
    required_artifact_fields = (
        "artifact_id",
        "artifact_digest",
        "input_packet_digest",
        "logical_evaluation_key",
        "run_id",
        "request_id",
    )
    if any(not _token(artifact.get(key)) for key in required_artifact_fields):
        raise AnalystQueryResolutionProposalError("originating Analyst artifact lineage is incomplete")
    recorded_contract = _safe(artifact.get("accepted_contract_ref") or {})
    if recorded_contract != _safe(parent_contract_ref):
        raise AnalystQueryResolutionProposalError("proposal parent contract does not match the Analyst role input")
    recorded_graph = _safe(artifact.get("graph_ref") or {})
    supplied_graph = _safe(parent_graph_ref or {})
    if recorded_graph != supplied_graph:
        raise AnalystQueryResolutionProposalError("proposal parent graph does not match the Analyst role input")

    candidate = normalize_local_query_resolution_candidate(local_candidate)
    if candidate["classification"] == CLASS_INFERRED_CONCLUSION:
        if candidate["current_graph_ref"] != supplied_graph:
            raise AnalystQueryResolutionProposalError(
                "inferred conclusion current_graph_ref is not the exact role-input graph"
            )
    targets = _target_refs(candidate)
    target_set_digest = _digest({"target_refs": targets})
    replay_identity = {
        "role_artifact_id": artifact["artifact_id"],
        "role_artifact_digest": artifact["artifact_digest"],
        "role_artifact_input_digest": artifact["input_packet_digest"],
        "role_artifact_logical_key": artifact["logical_evaluation_key"],
        "local_proposal_key": candidate["local_proposal_key"],
        "classification": candidate["classification"],
        "parent_contract_ref": _safe(parent_contract_ref),
        "parent_graph_ref": supplied_graph or {"graph_absent": True},
        "target_ref_set_digest": target_set_digest,
    }
    stable_replay_key = "aqrp:" + _digest(replay_identity)
    core = {
        "schema_version": ANALYST_QUERY_RESOLUTION_PROPOSAL_SCHEMA_VERSION,
        "stable_replay_key": stable_replay_key,
        "classification": candidate["classification"],
        "originating_analyst_role": role,
        "role_artifact_ref": {
            "artifact_id": artifact["artifact_id"],
            "artifact_digest": artifact["artifact_digest"],
            "input_packet_digest": artifact["input_packet_digest"],
            "logical_evaluation_key": artifact["logical_evaluation_key"],
        },
        "local_proposal_key": candidate["local_proposal_key"],
        "local_target_key": candidate["local_target_key"],
        "run_id": artifact["run_id"],
        "request_id": artifact["request_id"],
        "question_meaning_record_ref": _safe(question_meaning_record_ref),
        "parent_contract_ref": _safe(parent_contract_ref),
        "parent_graph_ref": supplied_graph or None,
        "parent_graph_explicitly_absent": not bool(supplied_graph),
        "target_ref_set_digest": target_set_digest,
        "variant_payload": candidate,
        "scrutineer_finding_ref": (_safe(scrutineer_finding_ref) if scrutineer_finding_ref else None),
        "proposal_only": True,
        "canonical_state": False,
        "raw_private_retained": False,
    }
    proposal_digest = _digest(core)
    proposal_id = "analyst-query-resolution-proposal:" + proposal_digest[:24]
    return {
        **core,
        "proposal_id": proposal_id,
        "proposal_digest": proposal_digest,
    }


def validate_bound_analyst_query_resolution_proposal(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    proposal = _mapping(value, "bound query-resolution proposal")
    if proposal.get("schema_version") != ANALYST_QUERY_RESOLUTION_PROPOSAL_SCHEMA_VERSION:
        raise AnalystQueryResolutionProposalError("query-resolution proposal schema mismatch")
    if proposal.get("proposal_only") is not True or proposal.get("canonical_state") is not False:
        raise AnalystQueryResolutionProposalError(
            "query-resolution proposal must remain noncanonical proposal-only state"
        )
    if proposal.get("raw_private_retained") is not False:
        raise AnalystQueryResolutionProposalError("query-resolution proposal cannot retain raw or private material")
    core = dict(proposal)
    proposal_id = _token(core.pop("proposal_id", None))
    proposal_digest = _token(core.pop("proposal_digest", None), limit=96)
    recomputed = _digest(core)
    if proposal_digest != recomputed:
        raise AnalystQueryResolutionProposalError("query-resolution proposal digest does not match content")
    if proposal_id != "analyst-query-resolution-proposal:" + recomputed[:24]:
        raise AnalystQueryResolutionProposalError("query-resolution proposal id does not match content")
    normalize_local_query_resolution_candidate(_mapping(proposal.get("variant_payload"), "variant_payload"))
    return _safe(proposal)


def replay_before_currentness(
    *,
    proposal: Mapping[str, Any],
    replay_history: Sequence[Mapping[str, Any]] = (),
    current_contract_ref: Mapping[str, Any],
    current_graph_ref: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Resolve exact replay or identity conflict before checking parent staleness."""

    normalized = validate_bound_analyst_query_resolution_proposal(proposal)
    stable_key = normalized["stable_replay_key"]
    for raw_entry in replay_history:
        entry = _mapping(raw_entry, "proposal replay history entry")
        prior = _mapping(entry.get("proposal"), "proposal replay history proposal")
        if prior.get("stable_replay_key") != stable_key:
            continue
        prior = validate_bound_analyst_query_resolution_proposal(prior)
        if prior["proposal_digest"] != normalized["proposal_digest"]:
            raise AnalystQueryResolutionProposalError("query-resolution proposal stable replay identity conflict")
        return {
            "status": "exact_replay",
            "proposal": prior,
            "downstream_refs": _safe(entry.get("downstream_refs") or {}),
            "mutation_permitted": False,
        }

    if normalized["parent_contract_ref"] != _safe(current_contract_ref):
        raise AnalystQueryResolutionProposalError("stale query-resolution proposal parent contract")
    recorded_graph = normalized.get("parent_graph_ref") or {}
    if recorded_graph != _safe(current_graph_ref or {}):
        raise AnalystQueryResolutionProposalError("stale query-resolution proposal parent graph")
    return {
        "status": "current_unapplied",
        "proposal": normalized,
        "downstream_refs": {},
        "mutation_permitted": True,
    }


def arbitrate_analyst_query_resolution_proposals(
    proposals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Collapse exact duplicates and fail closed on semantic alternatives."""

    normalized = sorted(
        (validate_bound_analyst_query_resolution_proposal(proposal) for proposal in proposals),
        key=lambda item: (
            str(item.get("proposal_digest") or ""),
            str(item.get("proposal_id") or ""),
        ),
    )
    if not normalized:
        return {
            "status": "no_resolution_proposal",
            "selected_proposal": None,
            "proposal_refs": [],
            "mutation_permitted": False,
        }
    scope_keys = {
        _digest(
            {
                "run_id": proposal["run_id"],
                "parent_contract_ref": proposal["parent_contract_ref"],
                "parent_graph_ref": proposal.get("parent_graph_ref") or {"graph_absent": True},
                "target_ref_set_digest": proposal["target_ref_set_digest"],
            }
        )
        for proposal in normalized
    }
    if len(scope_keys) != 1:
        raise AnalystQueryResolutionProposalError(
            "proposal arbitration requires one exact run/parent/target/role-input state"
        )
    content_by_digest: dict[str, list[dict[str, Any]]] = {}
    for proposal in normalized:
        content_digest = _digest(
            {
                "classification": proposal["classification"],
                "variant_payload": proposal["variant_payload"],
                "question_meaning_record_ref": proposal["question_meaning_record_ref"],
            }
        )
        content_by_digest.setdefault(content_digest, []).append(proposal)
    refs = sorted(
        [
            {
                "proposal_id": proposal["proposal_id"],
                "proposal_digest": proposal["proposal_digest"],
                "stable_replay_key": proposal["stable_replay_key"],
            }
            for proposal in normalized
        ],
        key=lambda item: (
            str(item["proposal_digest"]),
            str(item["proposal_id"]),
            str(item["stable_replay_key"]),
        ),
    )
    arbitration_identity = "aqrp-arbitration:" + _digest(
        {
            "scope_key": next(iter(scope_keys)),
            "normalized_content_digests": sorted(content_by_digest),
            "proposal_refs": refs,
        }
    )
    if len(content_by_digest) > 1:
        return {
            "status": "ambiguous_resolution_proposals",
            "selected_proposal": None,
            "proposal_refs": refs,
            "arbitration_identity": arbitration_identity,
            "mutation_permitted": False,
            "contract_amendment_permitted": False,
            "searchos_permitted": False,
            "inferred_relationship_admission_permitted": False,
        }
    normalized_content_digest = next(iter(content_by_digest))
    selected = content_by_digest[normalized_content_digest][0]
    return {
        "status": (
            "one_unique_resolution_proposal"
            if len(normalized) == 1
            else "byte_equivalent_resolution_proposals_collapsed"
        ),
        "selected_proposal": selected,
        "proposal_refs": refs,
        "normalized_content_digest": normalized_content_digest,
        "collapsed_proposal_identity": ("aqrp-collapsed:" + normalized_content_digest),
        "arbitration_identity": arbitration_identity,
        "mutation_permitted": True,
    }


def selected_proposals_for_role_artifact(
    *,
    registry: Mapping[str, Any],
    role_artifact: Mapping[str, Any],
    classification: str | None = None,
) -> list[dict[str, Any]]:
    """Return arbitration winners owned by one exact Analyst artifact."""

    artifact_id = str(role_artifact.get("artifact_id") or "")
    artifact_digest = str(role_artifact.get("artifact_digest") or "")
    selected: list[dict[str, Any]] = []
    for arbitration in registry.get("arbitrations") or ():
        if not isinstance(arbitration, Mapping) or arbitration.get("mutation_permitted") is not True:
            continue
        proposal = arbitration.get("selected_proposal")
        if not isinstance(proposal, Mapping):
            continue
        proposal_artifact = proposal.get("role_artifact_ref")
        if not isinstance(proposal_artifact, Mapping):
            continue
        if (
            proposal_artifact.get("artifact_id") != artifact_id
            or proposal_artifact.get("artifact_digest") != artifact_digest
            or (classification is not None and proposal.get("classification") != classification)
        ):
            continue
        selected.append(deepcopy(dict(proposal)))
    return selected


__all__ = [
    "ALLOWED_CLASSIFICATIONS",
    "ALLOWED_ORIGINATING_ROLES",
    "ANALYST_QUERY_RESOLUTION_PROPOSAL_SCHEMA_VERSION",
    "ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY",
    "CLASS_EXISTING_COMPONENT_GAP",
    "CLASS_INFERRED_CONCLUSION",
    "CLASS_SEARCHED_PREMISE",
    "PROPOSAL_LIFECYCLE_STATUSES",
    "AnalystQueryResolutionProposalError",
    "arbitrate_analyst_query_resolution_proposals",
    "bind_analyst_query_resolution_proposal",
    "normalize_local_query_resolution_candidate",
    "replay_before_currentness",
    "selected_proposals_for_role_artifact",
    "validate_bound_analyst_query_resolution_proposal",
]
