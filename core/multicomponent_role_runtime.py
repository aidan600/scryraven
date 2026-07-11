"""Authorized semantic role execution for ordinary multi-component synthesis.

Transports return role-only semantic JSON.  This module assigns every
repository identity/digest and binds the result to the exact RunKernel action
and safe input packet before reduction.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

SUPPORTED_QUERY_CLASS = "ordinary-bounded-multicomponent-factual-synthesis-v1"

ROLE_COMPONENT_ANALYST = "component_analyst"
ROLE_COMPONENT_DPRIME = "component_dprime"
ROLE_CROSS_COMPONENT_ANALYST = "cross_component_analyst"
ROLE_SYNTHESIS_DPRIME = "synthesis_dprime"
ROLE_SCRUTINEER = "scrutineer"

ROLE_SYSTEM_PROMPTS = {
    ROLE_COMPONENT_ANALYST: (
        "You are ScryRaven's component Analyst. Use only the supplied bounded "
        "component evidence. Return one JSON object with claim_text, "
        "support_status, caveats, nonclaims, and blockers. Propose only; do not "
        "validate, admit, synthesize across components, dispatch research, or "
        "write final answer prose."
    ),
    ROLE_COMPONENT_DPRIME: (
        "You are ScryRaven's component D-prime. Validate only the nominated "
        "component Analyst claim against its exact bounded evidence and scope. "
        "Return validation_status, reasons, caveats, nonclaims, and blockers. "
        "Do not create or replace the claim, admit it, dispatch research, or "
        "write final prose."
    ),
    ROLE_CROSS_COMPONENT_ANALYST: (
        "You are ScryRaven's Cross-Component Analyst. Propose bounded semantic "
        "relationships and synthesis from the supplied current component refs "
        "and request directive. Return synthesis_proposals only, each with a "
        "local synthesis_key, claim_text, relationship_type, component_inputs, "
        "synthesis_inputs, caveats, nonclaims, and blockers. Do not validate or "
        "admit your proposals, dispatch research, or write final prose."
    ),
    ROLE_SYNTHESIS_DPRIME: (
        "You are ScryRaven's synthesis D-prime. Validate only the nominated "
        "synthesis against the exact current admitted upstream refs. Return "
        "validation_status, reasons, caveats, nonclaims, and blockers. Do not "
        "invent or replace synthesis, admit state, dispatch research, or render."
    ),
    ROLE_SCRUTINEER: (
        "You are ScryRaven's full Scrutineer. Adversarially challenge the supplied "
        "validated case. Return challenge_status, reasons, challenge_targets, "
        "missing_component_proposals, caveats, and nonclaims. Each challenge target "
        "may contain only target_kind and the safe local target_key supplied in the "
        "catalog. A missing-component proposal is a separate sibling object with a "
        "local proposal_key, component_label, component_question, necessity_reason, "
        "target_kind, target_key, relationship_to_accepted_synthesis_directive, "
        "scope_posture, bounded_search_hints, source_requirement_hints, caveats, and "
        "nonclaims. Use scope_posture required_to_fulfill_existing_accepted_user_obligation "
        "only when the component is subordinate and necessary to fulfill the supplied "
        "accepted synthesis directive; otherwise use new_or_broadened_user_intent. "
        "Do not copy canonical IDs, revisions, digests, or refs; create first-pass "
        "synthesis; replace claims; admit state; dispatch research; or render final prose."
    ),
}

_ROLE_STATUSES = {
    ROLE_COMPONENT_ANALYST: {"supported", "supported_with_caveats", "unsupported", "blocked"},
    ROLE_COMPONENT_DPRIME: {"supported", "supported_with_caveats", "unsupported", "challenged", "blocked"},
    ROLE_SYNTHESIS_DPRIME: {"supported", "supported_with_caveats", "unsupported", "challenged", "blocked", "ambiguous"},
    ROLE_SCRUTINEER: {"passed", "passed_with_caveats", "challenged", "blocked"},
}

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "action_id",
        "observation_id",
        "run_id",
        "request_id",
        "proposal_id",
        "validation_id",
        "challenge_id",
        "component_id",
        "edge_id",
        "graph_id",
        "node_id",
        "node_revision",
        "graph_revision",
        "revision",
        "canonical_state",
        "admission_status",
        "runkernel_action",
        "runkernel_observation",
        "final_answer_packet",
        "fap_authority",
        "author_authority",
    }
)
_FORBIDDEN_MATERIAL_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "db_row",
        "env",
        "full_prompt",
        "full_trace",
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


class MulticomponentRoleRuntimeError(ValueError):
    """Raised when an authorized semantic role fails closed."""


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _clean_text(value: Any, *, limit: int = 800) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return list(value)
    return []


def _text_list(value: Any, *, limit: int = 360) -> list[str]:
    out: list[str] = []
    for item in _safe_sequence(value):
        text = _clean_text(item, limit=limit)
        if text and text not in out:
            out.append(text)
    return out[:20]


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=2000)
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item, depth=depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:80]]
    return _clean_text(value, limit=300)


def _digest(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def reject_model_authority_claims(value: Mapping[str, Any]) -> None:
    keys = _collect_keys(value)
    forbidden = keys & (_FORBIDDEN_AUTHORITY_KEYS | _FORBIDDEN_MATERIAL_KEYS)
    forbidden.update(key for key in keys if key.endswith("_digest"))
    forbidden.update(key for key in keys if key.startswith("runkernel_"))
    if forbidden:
        raise MulticomponentRoleRuntimeError(
            "semantic role output claimed repository authority or unsafe material: "
            + ", ".join(sorted(forbidden))
        )


def _parse_role_output(
    raw: Any,
    *,
    clean_json_response: Callable[[str], str] | None,
) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        parsed = dict(raw)
    else:
        text = str(raw or "")
        if clean_json_response is not None:
            text = clean_json_response(text)
        parsed_value = json.loads(text)
        if not isinstance(parsed_value, Mapping):
            raise MulticomponentRoleRuntimeError(
                "semantic role output must be one JSON object"
            )
        parsed = dict(parsed_value)
    reject_model_authority_claims(parsed)
    return parsed


def _local_key(value: Any) -> str:
    text = _clean_text(value, limit=40) or ""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", text):
        raise MulticomponentRoleRuntimeError("synthesis_key must be a bounded local label")
    return text


def _normalize_semantic_output(role: str, output: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(output)
    if role == ROLE_COMPONENT_ANALYST:
        claim_text = _clean_text(payload.get("claim_text"), limit=1000)
        status = _normalize_key(payload.get("support_status"))
        if not claim_text or status not in _ROLE_STATUSES[role]:
            raise MulticomponentRoleRuntimeError(
                "component Analyst output requires claim_text and valid support_status"
            )
        return {
            "claim_text": claim_text,
            "support_status": status,
            "caveats": _text_list(payload.get("caveats")),
            "nonclaims": _text_list(payload.get("nonclaims")),
            "blockers": _text_list(payload.get("blockers")),
        }
    if role in {ROLE_COMPONENT_DPRIME, ROLE_SYNTHESIS_DPRIME}:
        if _clean_text(payload.get("claim_text")) or _clean_text(
            payload.get("replacement_claim")
        ):
            raise MulticomponentRoleRuntimeError(
                "D-prime cannot create or replace the nominated claim"
            )
        status = _normalize_key(payload.get("validation_status"))
        if status not in _ROLE_STATUSES[role]:
            raise MulticomponentRoleRuntimeError("D-prime validation_status invalid")
        return {
            "validation_status": status,
            "reasons": _text_list(payload.get("reasons")),
            "caveats": _text_list(payload.get("caveats")),
            "nonclaims": _text_list(payload.get("nonclaims")),
            "blockers": _text_list(payload.get("blockers")),
        }
    if role == ROLE_CROSS_COMPONENT_ANALYST:
        proposals: list[dict[str, Any]] = []
        for raw_proposal in _safe_sequence(payload.get("synthesis_proposals")):
            proposal = _safe_mapping(raw_proposal)
            key = _local_key(proposal.get("synthesis_key"))
            claim_text = _clean_text(proposal.get("claim_text"), limit=1200)
            relationship_type = _normalize_key(proposal.get("relationship_type"))
            component_inputs = _text_list(proposal.get("component_inputs"), limit=160)
            synthesis_inputs = [
                _local_key(item) for item in _safe_sequence(proposal.get("synthesis_inputs"))
            ]
            if not claim_text or not relationship_type or not (
                component_inputs or synthesis_inputs
            ):
                raise MulticomponentRoleRuntimeError(
                    "cross-component proposal requires claim, relationship, and inputs"
                )
            proposals.append(
                {
                    "synthesis_key": key,
                    "claim_text": claim_text,
                    "relationship_type": relationship_type,
                    "component_inputs": component_inputs,
                    "synthesis_inputs": synthesis_inputs,
                    "caveats": _text_list(proposal.get("caveats")),
                    "nonclaims": _text_list(proposal.get("nonclaims")),
                    "blockers": _text_list(proposal.get("blockers")),
                }
            )
        if not 1 <= len(proposals) <= 4:
            raise MulticomponentRoleRuntimeError(
                "Cross-Component Analyst must propose one to four synthesis nodes"
            )
        if len({item["synthesis_key"] for item in proposals}) != len(proposals):
            raise MulticomponentRoleRuntimeError("duplicate synthesis_key")
        return {"synthesis_proposals": proposals}
    if role == ROLE_SCRUTINEER:
        status = _normalize_key(payload.get("challenge_status"))
        if status not in _ROLE_STATUSES[role]:
            raise MulticomponentRoleRuntimeError("Scrutineer challenge_status invalid")
        challenge_targets: list[dict[str, str]] = []
        for raw_target in _safe_sequence(payload.get("challenge_targets")):
            target = _safe_mapping(raw_target)
            if set(target) != {"target_kind", "target_key"}:
                raise MulticomponentRoleRuntimeError(
                    "Scrutineer challenge target must contain only target_kind and target_key"
                )
            target_kind = _normalize_key(target.get("target_kind"))
            if target_kind not in {"component", "synthesis", "edge", "subgraph", "graph"}:
                raise MulticomponentRoleRuntimeError(
                    "Scrutineer challenge target kind invalid"
                )
            challenge_targets.append(
                {
                    "target_kind": target_kind,
                    "target_key": _local_key(target.get("target_key")),
                }
            )
        if len({(item["target_kind"], item["target_key"]) for item in challenge_targets}) != len(
            challenge_targets
        ):
            raise MulticomponentRoleRuntimeError("duplicate Scrutineer challenge target")
        legacy_synthesis_keys = [
            _local_key(item)
            for item in _safe_sequence(payload.get("challenged_synthesis_keys"))
        ]
        if len(set(legacy_synthesis_keys)) != len(legacy_synthesis_keys):
            raise MulticomponentRoleRuntimeError("duplicate challenged_synthesis_key")
        if challenge_targets and legacy_synthesis_keys:
            raise MulticomponentRoleRuntimeError(
                "Scrutineer cannot mix typed and legacy challenge targets"
            )
        if status in {"passed", "passed_with_caveats"} and challenge_targets:
            raise MulticomponentRoleRuntimeError(
                "passing Scrutineer posture cannot select challenge targets"
            )
        if status in {"challenged", "blocked"} and not (
            challenge_targets or legacy_synthesis_keys
        ):
            raise MulticomponentRoleRuntimeError(
                "challenged or blocked Scrutineer posture requires a target"
            )
        missing_component_proposals: list[dict[str, Any]] = []
        for raw_proposal in _safe_sequence(
            payload.get("missing_component_proposals")
        ):
            proposal = _safe_mapping(raw_proposal)
            proposal_key = _local_key(proposal.get("proposal_key"))
            component_label = _clean_text(
                proposal.get("component_label"), limit=240
            )
            component_question = _clean_text(
                proposal.get("component_question"), limit=600
            )
            necessity_reason = _clean_text(
                proposal.get("necessity_reason"), limit=800
            )
            target_kind = _normalize_key(proposal.get("target_kind"))
            target_key = _local_key(proposal.get("target_key"))
            relationship = _clean_text(
                proposal.get("relationship_to_accepted_synthesis_directive"),
                limit=800,
            )
            scope_posture = _normalize_key(proposal.get("scope_posture"))
            if not all(
                (
                    component_label,
                    component_question,
                    necessity_reason,
                    relationship,
                )
            ):
                raise MulticomponentRoleRuntimeError(
                    "Scrutineer missing-component proposal requires bounded semantic fields"
                )
            if target_kind not in {
                "component",
                "synthesis",
                "edge",
                "subgraph",
                "graph",
            }:
                raise MulticomponentRoleRuntimeError(
                    "Scrutineer missing-component proposal target kind invalid"
                )
            if scope_posture not in {
                "required_to_fulfill_existing_accepted_user_obligation",
                "new_or_broadened_user_intent",
            }:
                raise MulticomponentRoleRuntimeError(
                    "Scrutineer missing-component proposal scope posture invalid"
                )
            if (target_kind, target_key) not in {
                (item["target_kind"], item["target_key"])
                for item in challenge_targets
            }:
                raise MulticomponentRoleRuntimeError(
                    "Scrutineer missing-component proposal must bind a challenge target"
                )
            missing_component_proposals.append(
                {
                    "proposal_key": proposal_key,
                    "component_label": component_label,
                    "component_question": component_question,
                    "necessity_reason": necessity_reason,
                    "target_kind": target_kind,
                    "target_key": target_key,
                    "relationship_to_accepted_synthesis_directive": relationship,
                    "scope_posture": scope_posture,
                    "bounded_search_hints": _text_list(
                        proposal.get("bounded_search_hints"), limit=300
                    ),
                    "source_requirement_hints": _text_list(
                        proposal.get("source_requirement_hints"), limit=240
                    ),
                    "caveats": _text_list(proposal.get("caveats")),
                    "nonclaims": _text_list(proposal.get("nonclaims")),
                }
            )
        if len(missing_component_proposals) > 1:
            raise MulticomponentRoleRuntimeError(
                "Scrutineer may propose at most one missing component"
            )
        if len(
            {item["proposal_key"] for item in missing_component_proposals}
        ) != len(missing_component_proposals):
            raise MulticomponentRoleRuntimeError(
                "duplicate Scrutineer missing-component proposal key"
            )
        if status in {"passed", "passed_with_caveats"} and (
            missing_component_proposals
        ):
            raise MulticomponentRoleRuntimeError(
                "passing Scrutineer posture cannot propose a missing component"
            )
        normalized_scrutineer = {
            "challenge_status": status,
            "reasons": _text_list(payload.get("reasons")),
            "caveats": _text_list(payload.get("caveats")),
            "nonclaims": _text_list(payload.get("nonclaims")),
        }
        if "challenge_targets" in payload:
            normalized_scrutineer["challenge_targets"] = challenge_targets
        if "challenged_synthesis_keys" in payload:
            normalized_scrutineer["challenged_synthesis_keys"] = legacy_synthesis_keys
        if "missing_component_proposals" in payload:
            normalized_scrutineer["missing_component_proposals"] = (
                missing_component_proposals
            )
        return normalized_scrutineer
    raise MulticomponentRoleRuntimeError(f"unknown semantic role: {role}")


def validate_multicomponent_role_artifact(
    value: Mapping[str, Any],
    *,
    expected_role: str | None = None,
) -> dict[str, Any]:
    artifact = _safe_mapping(value)
    if artifact.get("schema_version") != "multicomponent_semantic_role_artifact_v1":
        raise MulticomponentRoleRuntimeError("semantic role artifact schema mismatch")
    role = _normalize_key(artifact.get("role"))
    if role not in ROLE_SYSTEM_PROMPTS or (expected_role and role != expected_role):
        raise MulticomponentRoleRuntimeError("semantic role artifact role mismatch")
    for key in (
        "artifact_id",
        "artifact_digest",
        "run_id",
        "request_id",
        "input_packet_digest",
    ):
        if not _clean_text(artifact.get(key), limit=180):
            raise MulticomponentRoleRuntimeError(f"semantic role artifact requires {key}")
    action_ref = _safe_mapping(artifact.get("authorized_action_ref"))
    if not action_ref.get("action_id") or not action_ref.get("observation_type"):
        raise MulticomponentRoleRuntimeError("semantic role artifact action binding missing")
    if artifact.get("logical_evaluations") != 1 or artifact.get("physical_calls") != 1:
        raise MulticomponentRoleRuntimeError("semantic role accounting must be explicit")
    normalized_output = _normalize_semantic_output(
        role,
        _safe_mapping(artifact.get("semantic_output")),
    )
    normalized = {**artifact, "role": role, "semantic_output": normalized_output}
    declared = normalized.pop("artifact_digest")
    expected = _digest(normalized)
    normalized["artifact_digest"] = declared
    if declared != expected:
        raise MulticomponentRoleRuntimeError("semantic role artifact digest mismatch")
    return _json_safe(normalized)


def execute_multicomponent_role_call(
    *,
    run_kernel: Any,
    role: str,
    input_packet: Mapping[str, Any],
    ask_model: Callable[..., Any],
    clean_json_response: Callable[[str], str] | None,
    provider: str,
    model: str,
    base_url: str,
    api_key: str,
    use_reasoning: bool,
    logical_evaluation_key: str,
) -> dict[str, Any]:
    """Authorize, execute, parse, bind, and reduce one semantic role call."""

    normalized_role = _normalize_key(role)
    if normalized_role not in ROLE_SYSTEM_PROMPTS:
        raise MulticomponentRoleRuntimeError("unknown semantic role")
    safe_input = _json_safe(input_packet)
    if not isinstance(safe_input, Mapping):
        raise MulticomponentRoleRuntimeError("semantic role input must be a mapping")
    input_digest = _digest(safe_input)
    action = run_kernel.authorize_multicomponent_role_call(
        role=normalized_role,
        input_packet_digest=input_digest,
        logical_evaluation_key=logical_evaluation_key,
    )
    raw = ask_model(
        json.dumps(safe_input, sort_keys=True),
        ROLE_SYSTEM_PROMPTS[normalized_role],
        provider=provider,
        model=model,
        effort="high",
        base_url=base_url,
        api_key=api_key,
        require_json=True,
        use_reasoning=use_reasoning,
    )
    semantic_output = _normalize_semantic_output(
        normalized_role,
        _parse_role_output(raw, clean_json_response=clean_json_response),
    )
    artifact_core = {
        "schema_version": "multicomponent_semantic_role_artifact_v1",
        "role": normalized_role,
        "artifact_id": f"{normalized_role}:{action.action_id}",
        "run_id": action.run_id,
        "request_id": run_kernel.state.request_id,
        "input_packet_digest": input_digest,
        "logical_evaluation_key": logical_evaluation_key,
        "logical_evaluations": 1,
        "physical_calls": 1,
        "configured_model_route": {
            "provider": provider,
            "model": model,
            "role": "SmartModel",
        },
        "authorized_action_ref": {
            "action_id": action.action_id,
            "stage": action.stage,
            "sequence": action.sequence,
            "observation_type": action.expected_observation_type.value,
        },
        "semantic_output": semantic_output,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
    }
    artifact = {**artifact_core, "artifact_digest": _digest(artifact_core)}

    from core.run_kernel import Observation, RunStageStatus

    observation = Observation.from_action(
        action,
        observation_type=action.expected_observation_type,
        status=RunStageStatus.COMPLETED,
        payload={"semantic_role_artifact": artifact},
    )
    run_kernel.reduce(observation)
    return validate_multicomponent_role_artifact(
        artifact,
        expected_role=normalized_role,
    )


def role_artifact_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    artifact = validate_multicomponent_role_artifact(value)
    return {
        "schema_version": artifact["schema_version"],
        "role": artifact["role"],
        "artifact_id": artifact["artifact_id"],
        "artifact_digest": artifact["artifact_digest"],
        "run_id": artifact["run_id"],
        "request_id": artifact["request_id"],
        "input_packet_digest": artifact["input_packet_digest"],
        "logical_evaluation_key": artifact["logical_evaluation_key"],
        "logical_evaluations": 1,
        "physical_calls": 1,
        "authorized_action_ref": dict(artifact["authorized_action_ref"]),
    }


def safe_packet_digest(value: Mapping[str, Any]) -> str:
    """Return the canonical digest used to bind safe role input packets."""

    return _digest(_json_safe(value))


__all__ = [
    "ROLE_COMPONENT_ANALYST",
    "ROLE_COMPONENT_DPRIME",
    "ROLE_CROSS_COMPONENT_ANALYST",
    "ROLE_SCRUTINEER",
    "ROLE_SYNTHESIS_DPRIME",
    "ROLE_SYSTEM_PROMPTS",
    "SUPPORTED_QUERY_CLASS",
    "MulticomponentRoleRuntimeError",
    "execute_multicomponent_role_call",
    "reject_model_authority_claims",
    "role_artifact_ref",
    "safe_packet_digest",
    "validate_multicomponent_role_artifact",
]
