"""Authorized semantic role execution for ordinary multi-component synthesis.

Transports return role-only semantic JSON.  This module assigns every
repository identity/digest and binds the result to the exact RunKernel action
and safe input packet before reduction.
"""

from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from threading import get_ident
from typing import Any, Callable, Mapping, Sequence

from core.analyst_query_resolution_proposal import (
    AnalystQueryResolutionProposalError,
    normalize_local_query_resolution_candidate,
)
from core.cap_enforcement import RunCapExceeded

SUPPORTED_QUERY_CLASS = "ordinary-bounded-multicomponent-factual-synthesis-v1"

ROLE_COMPONENT_ANALYST = "component_analyst"
ROLE_COMPONENT_ANALYST_RESUME = "component_analyst_resume"
ROLE_COMPONENT_DPRIME = "component_dprime"
ROLE_CROSS_COMPONENT_ANALYST = "cross_component_analyst"
ROLE_SYNTHESIS_DPRIME = "synthesis_dprime"
ROLE_SCRUTINEER = "scrutineer"
SELECTIVE_CROSS_COMPONENT_SCHEMA = "selective_affected_synthesis_v1"
SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT = (
    "You are ScryRaven's selective Cross-Component Analyst. Propose exactly the "
    "licensed affected synthesis keys in the supplied topological order. Each "
    "proposal must use the separate component_inputs, affected_synthesis_inputs, "
    "and preserved_synthesis_inputs namespaces. Preserved synthesis keys are "
    "read-only boundary inputs and must not be re-proposed. Return "
    "synthesis_proposals only. Do not validate, admit, dispatch research, change "
    "unaffected synthesis, copy canonical refs, or write final prose."
)

ROLE_SYSTEM_PROMPTS = {
    ROLE_COMPONENT_ANALYST: (
        "You are ScryRaven's component Analyst. Use only the supplied bounded "
        "component evidence, quantitative_source_catalog, and "
        "quantitative_specialist_proposal_contract. Return one top-level JSON "
        "object with case_posture; lawful claim_text when any; evidence_analysis or warrant; "
        "caveats, nonclaims, contradictions, uncertainty, confidence, "
        "missing_evidentiary_premise, unresolved_need, calculation_need, blockers, "
        "and self_audit, plus optional query_resolution_proposals and "
        "specialist_need_proposal namespaces. case_posture must be exactly supported, "
        "supported_with_caveats, unsupported, blocked, unresolved, missing_premise, "
        "or bounded_calculation_needed. Do not return legacy support_status; it is "
        "offline-fixture compatibility only. Explain what evidence establishes and, "
        "when material, what it does not establish; self_audit must check overreach. "
        "Use arrays of strings for caveats, nonclaims, contradictions, and blockers. "
        "Outside optional proposal namespaces, never return code-owned IDs, refs, "
        "revisions, digests, URLs, field paths, runtime bindings, authority claims, "
        "or raw/private material; code binds mechanics deterministically. "
        "query_resolution_proposals is optional and proposal-only: include it "
        "only when every candidate is complete and uses exact immutable refs "
        "present in the supplied input; otherwise omit it. "
        "When this exact component claim materially depends on a supported "
        "deterministic calculation, you may add one sibling "
        "specialist_need_proposal conforming exactly to the supplied contract. "
        "Include the supplied specialist_need_proposal_v1 schema_version; do "
        "not omit, default, alias, or add proposal fields. Copy all supplied "
        "fixed capability and schema values exactly, use only "
        "source_local_key component_evidence and exact supplied "
        "source_numeric_literal text, and omit the proposal when the contract "
        "cannot be satisfied. Include "
        "the proposed derived literal in claim_text, but it has no authority until "
        "exact calculator claim_alignment and this case's bounded self-audit. Use required only "
        "when the claim cannot be validated without it; use optional only for "
        "nonessential precision or explanation. Do not consume the one Specialist "
        "unit for arithmetic that belongs only to later cross-component synthesis. "
        "Propose only; do not validate, admit, synthesize across components, "
        "authorize search, dispatch research, or write final answer prose."
    ),
    ROLE_COMPONENT_ANALYST_RESUME: (
        "You are ScryRaven's component Analyst resuming one exact prior "
        "component case after a bounded Specialist handoff. Use only the "
        "supplied prior case, exact component/evidence input, and handoff. "
        "Return the same robust case schema: case_posture; lawful claim_text "
        "when any; evidence_analysis or warrant; caveats, nonclaims, "
        "contradictions, uncertainty, confidence, missing_evidentiary_premise, "
        "unresolved_need, calculation_need, blockers, and self_audit. "
        "case_posture must be exactly supported, supported_with_caveats, "
        "unsupported, blocked, unresolved, missing_premise, or "
        "bounded_calculation_needed. The supplied handoff is not automatic "
        "support: reassess its exact bounded result and state what it does not "
        "establish where material. self_audit must check overreach. Do not "
        "return legacy support_status; it is offline-fixture compatibility only. "
        "Do not make a new Specialist proposal, admit anything, create runtime "
        "IDs, refs, revisions, digests, or bindings, route providers, search, "
        "or write final answer prose."
    ),
    ROLE_COMPONENT_DPRIME: (
        "You are ScryRaven's legacy-recovery component D-prime. Validate only the nominated "
        "component Analyst claim against its exact bounded evidence and scope. "
        "When specialist_need_handoff is present, a completed quantitative result "
        "supports the nominated claim only when its exact calculated value, "
        "operator, unit, source lineage, assumptions, caveats, and claim_alignment "
        "all support that claim; execution success alone is insufficient and any "
        "non-exact alignment must not be clean support. Return validation_status, "
        "reasons, caveats, nonclaims, and blockers. Do not create or replace the "
        "claim, calculate a substitute, authorize the capability, admit it, "
        "authorize search or dispatch research, or write final prose."
    ),
    ROLE_CROSS_COMPONENT_ANALYST: (
        "You are ScryRaven's Cross-Component Analyst. Propose bounded semantic "
        "relationships and synthesis from the supplied current component refs, "
        "deterministic component_01/component_02/... quantitative source aliases, "
        "quantitative_specialist_proposal_contract, and request directive. Return "
        "one top-level object containing synthesis_proposals, optional "
        "query_resolution_proposals, and, only when needed, "
        "one sibling specialist_need_proposal conforming exactly to the supplied "
        "contract. The Specialist proposal is not nested inside a synthesis "
        "proposal. Include the supplied specialist_need_proposal_v1 "
        "schema_version; do not omit, default, alias, or add proposal fields. "
        "Copy all supplied fixed capability and schema values exactly. "
        "Each synthesis proposal has a "
        "local synthesis_key, claim_text, relationship_type, component_inputs, "
        "synthesis_inputs, caveats, nonclaims, and blockers. You may add one "
        "source_bound_quantitative_calculation specialist_need_proposal only when "
        "the nominated synthesis materially depends on supported arithmetic across "
        "current admitted component claims. Use only supplied aliases and exact "
        "literals that occur in each selected admitted claim and are traceable to "
        "its underlying current component evidence; never submit component/node/"
        "graph IDs, refs, revisions, digests, URLs, or field paths. Use required "
        "only when synthesis cannot be validated without it and optional only for "
        "nonessential precision or explanation. Omit the Specialist proposal when "
        "the supplied contract cannot be satisfied. Do not validate or admit your "
        "proposals, authorize search, dispatch research, or write final prose."
    ),
    ROLE_SYNTHESIS_DPRIME: (
        "You are ScryRaven's synthesis D-prime. Validate only the nominated "
        "synthesis against the exact current admitted upstream refs. When "
        "specialist_need_handoff is present, a completed quantitative result "
        "supports the nominated synthesis only when its exact calculated value, "
        "operator, unit, two-hop source lineage, assumptions, caveats, and "
        "claim_alignment all support it; execution success alone is insufficient "
        "and non-exact alignment must not be clean support. Return validation_status, "
        "reasons, caveats, nonclaims, and blockers. Do not invent or replace "
        "synthesis, calculate a substitute, authorize the capability, admit state, "
        "authorize search or dispatch research, or render."
    ),
    ROLE_SCRUTINEER: (
        "You are ScryRaven's full Scrutineer. Adversarially challenge the supplied "
        "validated case. Return challenge_status, reasons, challenge_targets, "
        "caveats, and nonclaims. Each challenge target "
        "may contain only target_kind and the safe local target_key supplied in the "
        "catalog. You may challenge exact supplied state and provide optional context, "
        "but you must not author query-resolution proposals, child or premise semantics, "
        "amendment operations, recovery purpose, query text, inferred relationships, "
        "or canonical admission. "
        "Do not copy canonical IDs, revisions, digests, or refs; create first-pass "
        "synthesis; replace claims; admit state; dispatch research; or render final prose."
    ),
}

COMPONENT_ANALYST_CASE_POSTURES = frozenset(
    {
        "supported",
        "supported_with_caveats",
        "unsupported",
        "blocked",
        "unresolved",
        "missing_premise",
        "bounded_calculation_needed",
    }
)
COMPONENT_ANALYST_SUPPORTING_CASE_POSTURES = frozenset(
    {"supported", "supported_with_caveats"}
)
_LEGACY_SUPPORT_STATUS_BY_COMPONENT_ANALYST_CASE_POSTURE = {
    "supported": "supported",
    "supported_with_caveats": "supported_with_caveats",
    "unsupported": "unsupported",
    "blocked": "blocked",
    "unresolved": "blocked",
    "missing_premise": "blocked",
    "bounded_calculation_needed": "blocked",
}

_ROLE_STATUSES = {
    ROLE_COMPONENT_ANALYST: COMPONENT_ANALYST_CASE_POSTURES,
    ROLE_COMPONENT_ANALYST_RESUME: COMPONENT_ANALYST_CASE_POSTURES,
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
        "_runtime_legacy_fixture_compatibility",
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


@dataclass(frozen=True, slots=True)
class PreparedMulticomponentTransportCall:
    """Immutable transient worker input; never retained in canonical state."""

    schema_version: str
    batch_index: int
    batch_id: str
    batch_digest: str
    work_id: str
    work_digest: str
    lease_id: str
    lease_digest: str
    action_id: str
    action_sequence: int
    role: str
    logical_evaluation_key: str
    input_packet: Mapping[str, Any] = field(repr=False, compare=False)
    input_packet_digest: str
    output_schema_variant: str | None
    provider: str
    model: str
    use_reasoning: bool
    strict_one_shot_transport: Callable[..., Any] = field(repr=False, compare=False)
    clean_json_response: Callable[[str], str] | None = field(
        default=None, repr=False, compare=False
    )
    effort: str = "medium"
    raw_retention: bool = False


@dataclass(frozen=True, slots=True)
class SafeMulticomponentWorkerResult:
    """Pure normalized worker outcome with no canonical artifact authority."""

    schema_version: str
    batch_index: int
    batch_id: str
    batch_digest: str
    work_id: str
    work_digest: str
    lease_id: str
    lease_digest: str
    action_id: str
    action_sequence: int
    role: str
    logical_evaluation_key: str
    input_packet_digest: str
    output_schema_variant: str | None
    provider: str
    model: str
    normalized_semantic_output: Mapping[str, Any] | None
    specialist_need_proposal_present: bool
    specialist_need_proposal_candidate: Mapping[str, Any] | None
    failure_kind: str | None
    transport_submitted: bool
    transport_started: bool
    transport_completed: bool
    provider_request_attempt_count: int
    worker_thread_id: int | None
    duration_seconds: float
    provider_response_received: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    usage_observed: bool = False
    usage_estimated: bool = False
    raw_prompt_retained: bool = False
    raw_model_response_retained: bool = False
    raw_provider_payload_retained: bool = False
    exception_text_retained: bool = False


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
    ordinary_output = dict(parsed)
    ordinary_output.pop("specialist_need_proposal", None)
    # Query-resolution candidates must copy exact immutable contract, graph,
    # component, and node refs from the role input.  Their dedicated
    # normalizer validates and sanitizes that proposal-only namespace below;
    # the ordinary semantic-output authority guard must not misclassify those
    # copied digests as model-created repository authority.
    ordinary_output.pop("query_resolution_proposals", None)
    reject_model_authority_claims(ordinary_output)
    return parsed


def _specialist_need_candidate(
    payload: Mapping[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    if "specialist_need_proposal" not in payload:
        return False, None
    candidate = payload.get("specialist_need_proposal")
    if not isinstance(candidate, Mapping):
        raise MulticomponentRoleRuntimeError(
            "specialist_need_proposal must be one exact JSON mapping"
        )
    return True, deepcopy(dict(candidate))


def _local_key(value: Any) -> str:
    text = _clean_text(value, limit=40) or ""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", text):
        raise MulticomponentRoleRuntimeError("synthesis_key must be a bounded local label")
    return text


def _with_specialist_need(
    normalized: dict[str, Any], payload: Mapping[str, Any]
) -> dict[str, Any]:
    """Keep parsed proposal candidates out of retained role artifacts."""

    del payload
    return normalized


def _with_query_resolution_candidates(
    normalized: dict[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if "query_resolution_proposals" not in payload:
        return normalized
    proposals: list[dict[str, Any]] = []
    try:
        for raw in _safe_sequence(payload.get("query_resolution_proposals")):
            proposals.append(
                normalize_local_query_resolution_candidate(
                    _safe_mapping(raw)
                )
            )
    except AnalystQueryResolutionProposalError as exc:
        raise MulticomponentRoleRuntimeError(str(exc)) from exc
    if len(proposals) > 5:
        raise MulticomponentRoleRuntimeError(
            "Analyst may emit at most five query-resolution proposals"
        )
    target_keys = [proposal["local_target_key"] for proposal in proposals]
    if len(target_keys) != len(set(target_keys)):
        raise MulticomponentRoleRuntimeError(
            "Analyst may emit at most one query-resolution proposal per local target key"
        )
    return {**normalized, "query_resolution_proposals": proposals}


def _normalize_component_analyst_case(
    payload: Mapping[str, Any], *, resume: bool
) -> dict[str, Any]:
    declared_posture = _normalize_key(payload.get("case_posture"))
    if not declared_posture:
        raise MulticomponentRoleRuntimeError(
            "component Analyst output requires a valid case_posture"
        )
    if declared_posture not in COMPONENT_ANALYST_CASE_POSTURES:
        raise MulticomponentRoleRuntimeError(
            "component Analyst case_posture is invalid"
        )
    declared_status = _normalize_key(payload.get("support_status"))
    expected_support_status = (
        _LEGACY_SUPPORT_STATUS_BY_COMPONENT_ANALYST_CASE_POSTURE[declared_posture]
    )
    if declared_status and declared_status != expected_support_status:
        raise MulticomponentRoleRuntimeError(
            "component Analyst support_status disagrees with case_posture"
        )
    case_posture = declared_posture

    claim_text = _clean_text(payload.get("claim_text"), limit=1000)
    evidence_analysis = _clean_text(payload.get("evidence_analysis"), limit=1600)
    warrant = _clean_text(payload.get("warrant"), limit=1600)
    self_audit = _clean_text(
        payload.get("self_audit") or payload.get("overreach_check"), limit=1200
    )

    if case_posture in COMPONENT_ANALYST_SUPPORTING_CASE_POSTURES:
        if not claim_text:
            raise MulticomponentRoleRuntimeError(
                "supporting component Analyst case requires claim_text"
            )
        if not (evidence_analysis or warrant):
            raise MulticomponentRoleRuntimeError(
                "supporting component Analyst case requires evidence_analysis or warrant"
            )
        if not self_audit:
            raise MulticomponentRoleRuntimeError(
                "supporting component Analyst case requires self_audit"
            )

    contradictions = list(
        dict.fromkeys(
            [
                *_text_list(payload.get("contradictions")),
                *_text_list(payload.get("material_alternatives")),
            ]
        )
    )
    normalized: dict[str, Any] = {
        "case_posture": case_posture,
        # Code-derived compatibility alias for out-of-scope consumers.
        # Model-authored support_status never substitutes for case_posture.
        "support_status": expected_support_status,
        "caveats": _text_list(payload.get("caveats")),
        "nonclaims": _text_list(payload.get("nonclaims")),
        "contradictions": contradictions,
        "blockers": _text_list(payload.get("blockers")),
    }
    semantic_text_fields = (
        ("claim_text", claim_text),
        ("evidence_analysis", evidence_analysis),
        ("warrant", warrant),
        ("uncertainty", _clean_text(payload.get("uncertainty"), limit=800)),
        ("confidence", _clean_text(payload.get("confidence"), limit=160)),
        (
            "missing_evidentiary_premise",
            _clean_text(payload.get("missing_evidentiary_premise"), limit=1000),
        ),
        ("unresolved_need", _clean_text(payload.get("unresolved_need"), limit=1000)),
        ("calculation_need", _clean_text(payload.get("calculation_need"), limit=1000)),
        ("self_audit", self_audit),
    )
    for key, value in semantic_text_fields:
        if value:
            normalized[key] = value
    if resume and "specialist_need_proposal" in payload:
        raise MulticomponentRoleRuntimeError(
            "component Analyst resume cannot propose another Specialist need"
        )
    return _with_specialist_need(
        _with_query_resolution_candidates(normalized, payload), payload
    )


def _normalize_semantic_output(
    role: str,
    output: Mapping[str, Any],
    *,
    output_schema_variant: str | None = None,
) -> dict[str, Any]:
    payload = _safe_mapping(output)
    if role in {ROLE_COMPONENT_ANALYST, ROLE_COMPONENT_ANALYST_RESUME}:
        return _normalize_component_analyst_case(
            payload,
            resume=role == ROLE_COMPONENT_ANALYST_RESUME,
        )
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
            if output_schema_variant == SELECTIVE_CROSS_COMPONENT_SCHEMA:
                if "synthesis_inputs" in proposal:
                    raise MulticomponentRoleRuntimeError(
                        "selective Cross proposal cannot use the full-graph synthesis namespace"
                    )
                affected_inputs = [
                    _local_key(item)
                    for item in _safe_sequence(
                        proposal.get("affected_synthesis_inputs")
                    )
                ]
                preserved_inputs = [
                    _local_key(item)
                    for item in _safe_sequence(
                        proposal.get("preserved_synthesis_inputs")
                    )
                ]
                if set(affected_inputs) & set(preserved_inputs):
                    raise MulticomponentRoleRuntimeError(
                        "selective Cross synthesis input namespaces must be disjoint"
                    )
                synthesis_inputs = []
            else:
                if "affected_synthesis_inputs" in proposal or (
                    "preserved_synthesis_inputs" in proposal
                ):
                    raise MulticomponentRoleRuntimeError(
                        "ordinary Cross proposal cannot use selective namespaces"
                    )
                synthesis_inputs = [
                    _local_key(item)
                    for item in _safe_sequence(proposal.get("synthesis_inputs"))
                ]
                affected_inputs = []
                preserved_inputs = []
            if not claim_text or not relationship_type or not (
                component_inputs
                or synthesis_inputs
                or affected_inputs
                or preserved_inputs
            ):
                raise MulticomponentRoleRuntimeError(
                    "cross-component proposal requires claim, relationship, and inputs"
                )
            normalized_proposal = {
                    "synthesis_key": key,
                    "claim_text": claim_text,
                    "relationship_type": relationship_type,
                    "component_inputs": component_inputs,
                    "caveats": _text_list(proposal.get("caveats")),
                    "nonclaims": _text_list(proposal.get("nonclaims")),
                    "blockers": _text_list(proposal.get("blockers")),
            }
            if output_schema_variant == SELECTIVE_CROSS_COMPONENT_SCHEMA:
                normalized_proposal.update(
                    {
                        "affected_synthesis_inputs": affected_inputs,
                        "preserved_synthesis_inputs": preserved_inputs,
                    }
                )
            else:
                normalized_proposal["synthesis_inputs"] = synthesis_inputs
            proposals.append(normalized_proposal)
        if not 1 <= len(proposals) <= 4:
            raise MulticomponentRoleRuntimeError(
                "Cross-Component Analyst must propose one to four synthesis nodes"
            )
        if len({item["synthesis_key"] for item in proposals}) != len(proposals):
            raise MulticomponentRoleRuntimeError("duplicate synthesis_key")
        return _with_specialist_need(
            _with_query_resolution_candidates(
                {"synthesis_proposals": proposals},
                payload,
            ),
            payload,
        )
    if role == ROLE_SCRUTINEER:
        if "query_resolution_proposals" in payload:
            raise MulticomponentRoleRuntimeError(
                "Scrutineer cannot author query-resolution proposals"
            )
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
        return _with_specialist_need(normalized_scrutineer, payload)
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
    schema_variant = _clean_text(
        artifact.get("output_schema_variant"), limit=80
    )
    if schema_variant and not (
        role == ROLE_CROSS_COMPONENT_ANALYST
        and schema_variant == SELECTIVE_CROSS_COMPONENT_SCHEMA
    ):
        raise MulticomponentRoleRuntimeError(
            "semantic role artifact schema variant is invalid"
        )
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
        output_schema_variant=schema_variant,
    )
    normalized = {**artifact, "role": role, "semantic_output": normalized_output}
    declared = normalized.pop("artifact_digest")
    expected = _digest(normalized)
    normalized["artifact_digest"] = declared
    if declared != expected:
        raise MulticomponentRoleRuntimeError("semantic role artifact digest mismatch")
    return _json_safe(normalized)


def prepare_multicomponent_transport_call(
    *,
    action: Any,
    input_packet: Mapping[str, Any],
    strict_one_shot_transport: Callable[..., Any],
    clean_json_response: Callable[[str], str] | None,
    provider: str,
    model: str,
    use_reasoning: bool,
    effort: str = "medium",
) -> PreparedMulticomponentTransportCall:
    """Bind one committed child action to its exact transient transport input."""

    from core.multicomponent_graph_scheduling import (
        MULTICOMPONENT_PREPARED_TRANSPORT_CALL_SCHEMA_VERSION,
    )
    from core.strict_one_shot_model_transport import (
        normalize_canonical_model_provider,
    )

    inputs = _safe_mapping(getattr(action, "inputs", {}))
    safe_input = _json_safe(input_packet)
    if not isinstance(safe_input, Mapping):
        raise MulticomponentRoleRuntimeError("prepared transport input must be a mapping")
    input_digest = _digest(safe_input)
    required = (
        "batch_id",
        "batch_digest",
        "work_id",
        "work_digest",
        "lease_id",
        "lease_digest",
        "role",
        "logical_evaluation_key",
    )
    if (
        any(not inputs.get(key) for key in required)
        or inputs.get("input_packet_digest") != input_digest
        or inputs.get("specialist_handoff_digest")
        != _safe_mapping(safe_input.get("specialist_need_handoff")).get(
            "handoff_digest"
        )
        or int(inputs.get("batch_index") if inputs.get("batch_index") is not None else -1)
        < 0
    ):
        raise MulticomponentRoleRuntimeError(
            "prepared transport does not match committed child action"
        )
    if not callable(strict_one_shot_transport):
        raise MulticomponentRoleRuntimeError(
            "prepared transport requires a strict one-shot SmartModel transport"
        )
    canonical_provider = normalize_canonical_model_provider(provider)
    return PreparedMulticomponentTransportCall(
        schema_version=MULTICOMPONENT_PREPARED_TRANSPORT_CALL_SCHEMA_VERSION,
        batch_index=int(inputs["batch_index"]),
        batch_id=str(inputs["batch_id"]),
        batch_digest=str(inputs["batch_digest"]),
        work_id=str(inputs["work_id"]),
        work_digest=str(inputs["work_digest"]),
        lease_id=str(inputs["lease_id"]),
        lease_digest=str(inputs["lease_digest"]),
        action_id=str(action.action_id),
        action_sequence=int(action.sequence),
        role=str(inputs["role"]),
        logical_evaluation_key=str(inputs["logical_evaluation_key"]),
        input_packet=deepcopy(dict(safe_input)),
        input_packet_digest=input_digest,
        output_schema_variant=_clean_text(inputs.get("output_schema_variant"), limit=80),
        provider=canonical_provider,
        model=str(model or ""),
        use_reasoning=bool(use_reasoning),
        effort=str(effort or "medium"),
        strict_one_shot_transport=strict_one_shot_transport,
        clean_json_response=clean_json_response,
    )


def _bounded_worker_usage_facts(transport_result: Any) -> dict[str, Any]:
    provider_response_received = bool(
        getattr(transport_result, "provider_response_received", False)
    )
    if not provider_response_received:
        return {
            "provider_response_received": False,
            "input_tokens": 0,
            "output_tokens": 0,
            "usage_observed": False,
            "usage_estimated": False,
        }
    return {
        "provider_response_received": True,
        "input_tokens": max(0, int(getattr(transport_result, "input_tokens", 0) or 0)),
        "output_tokens": max(0, int(getattr(transport_result, "output_tokens", 0) or 0)),
        "usage_observed": bool(getattr(transport_result, "usage_observed", False)),
        "usage_estimated": bool(getattr(transport_result, "usage_estimated", False)),
    }


def execute_prepared_multicomponent_transport(
    prepared: PreparedMulticomponentTransportCall,
) -> SafeMulticomponentWorkerResult:
    """Execute transport plus pure parsing/normalization with bounded failures."""

    from core.multicomponent_graph_scheduling import (
        MULTICOMPONENT_SAFE_WORKER_RESULT_SCHEMA_VERSION,
    )
    from core.strict_one_shot_model_transport import (
        StrictOneShotModelTransportResult,
        normalize_canonical_model_provider,
    )

    started_at = time.perf_counter()
    thread_id = get_ident()
    attempt_count = 0
    usage_facts = {
        "provider_response_received": False,
        "input_tokens": 0,
        "output_tokens": 0,
        "usage_observed": False,
        "usage_estimated": False,
    }
    result_provider = normalize_canonical_model_provider(prepared.provider)
    specialist_candidate_present = False
    specialist_candidate: dict[str, Any] | None = None
    try:
        system_prompt = (
            SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT
            if prepared.output_schema_variant == SELECTIVE_CROSS_COMPONENT_SCHEMA
            else ROLE_SYSTEM_PROMPTS[prepared.role]
        )
        transport_result = prepared.strict_one_shot_transport(
            json.dumps(prepared.input_packet, sort_keys=True),
            system_prompt,
            provider=prepared.provider,
            model=prepared.model,
            effort=prepared.effort,
            require_json=True,
            use_reasoning=prepared.use_reasoning,
        )
        if not isinstance(transport_result, StrictOneShotModelTransportResult):
            raise MulticomponentRoleRuntimeError(
                "strict one-shot transport returned an invalid result type"
            )
        attempt_count = int(transport_result.provider_request_attempt_count or 0)
        if attempt_count not in {0, 1}:
            raise MulticomponentRoleRuntimeError(
                "strict one-shot transport reported an invalid provider attempt count"
            )
        usage_facts = _bounded_worker_usage_facts(transport_result)
        result_provider = normalize_canonical_model_provider(
            transport_result.canonical_provider
        )
        if result_provider != normalize_canonical_model_provider(prepared.provider):
            normalized = None
            failure_kind = "provider_identity_mismatch"
        elif transport_result.return_code != 0:
            normalized = None
            failure_kind = "model_transport_failure"
        else:
            parsed_output = _parse_role_output(
                transport_result.output_text,
                clean_json_response=prepared.clean_json_response,
            )
            if (
                prepared.role == ROLE_COMPONENT_ANALYST_RESUME
                and "specialist_need_proposal" in parsed_output
            ):
                raise MulticomponentRoleRuntimeError(
                    "component Analyst resume cannot propose another Specialist need"
                )
            specialist_candidate_present, specialist_candidate = (
                _specialist_need_candidate(parsed_output)
            )
            normalized = _normalize_semantic_output(
                prepared.role,
                parsed_output,
                output_schema_variant=prepared.output_schema_variant,
            )
            failure_kind = None
    except RunCapExceeded:
        raise
    except Exception as exc:
        normalized = None
        failure_kind = (
            "output_validation_failure"
            if isinstance(exc, (MulticomponentRoleRuntimeError, json.JSONDecodeError))
            else "model_transport_failure"
        )
        if failure_kind == "provider_identity_mismatch":
            pass
    return SafeMulticomponentWorkerResult(
        schema_version=MULTICOMPONENT_SAFE_WORKER_RESULT_SCHEMA_VERSION,
        batch_index=prepared.batch_index,
        batch_id=prepared.batch_id,
        batch_digest=prepared.batch_digest,
        work_id=prepared.work_id,
        work_digest=prepared.work_digest,
        lease_id=prepared.lease_id,
        lease_digest=prepared.lease_digest,
        action_id=prepared.action_id,
        action_sequence=prepared.action_sequence,
        role=prepared.role,
        logical_evaluation_key=prepared.logical_evaluation_key,
        input_packet_digest=prepared.input_packet_digest,
        output_schema_variant=prepared.output_schema_variant,
        provider=result_provider,
        model=prepared.model,
        normalized_semantic_output=normalized,
        specialist_need_proposal_present=specialist_candidate_present,
        specialist_need_proposal_candidate=specialist_candidate,
        failure_kind=failure_kind,
        transport_submitted=True,
        transport_started=True,
        transport_completed=True,
        provider_request_attempt_count=attempt_count,
        worker_thread_id=thread_id,
        duration_seconds=max(0.0, time.perf_counter() - started_at),
        **usage_facts,
    )


def failed_unstarted_multicomponent_worker_result(
    prepared: PreparedMulticomponentTransportCall,
    *,
    failure_kind: str,
    transport_submitted: bool = False,
    transport_started: bool = False,
    transport_completed: bool = False,
) -> SafeMulticomponentWorkerResult:
    """Create a bounded main-thread result for executor/submission failure."""

    from core.multicomponent_graph_scheduling import (
        MULTICOMPONENT_SAFE_WORKER_RESULT_SCHEMA_VERSION,
    )
    from core.strict_one_shot_model_transport import normalize_canonical_model_provider

    return SafeMulticomponentWorkerResult(
        schema_version=MULTICOMPONENT_SAFE_WORKER_RESULT_SCHEMA_VERSION,
        batch_index=prepared.batch_index,
        batch_id=prepared.batch_id,
        batch_digest=prepared.batch_digest,
        work_id=prepared.work_id,
        work_digest=prepared.work_digest,
        lease_id=prepared.lease_id,
        lease_digest=prepared.lease_digest,
        action_id=prepared.action_id,
        action_sequence=prepared.action_sequence,
        role=prepared.role,
        logical_evaluation_key=prepared.logical_evaluation_key,
        input_packet_digest=prepared.input_packet_digest,
        output_schema_variant=prepared.output_schema_variant,
        provider=normalize_canonical_model_provider(prepared.provider),
        model=prepared.model,
        normalized_semantic_output=None,
        specialist_need_proposal_present=False,
        specialist_need_proposal_candidate=None,
        failure_kind=str(failure_kind or "failed_submission")[:100],
        transport_submitted=transport_submitted,
        transport_started=transport_started,
        transport_completed=transport_completed,
        provider_request_attempt_count=0,
        worker_thread_id=None,
        duration_seconds=0.0,
    )


def reduce_multicomponent_worker_result(
    *,
    run_kernel: Any,
    action: Any,
    result: SafeMulticomponentWorkerResult,
    observed_batch_max_in_flight: int,
) -> dict[str, Any] | None:
    """Construct and reduce canonical artifact authority on the main thread."""

    from core.multicomponent_graph_scheduling import (
        LEASE_FAILED,
        LEASE_STALE,
        MULTICOMPONENT_SAFE_WORKER_RESULT_SCHEMA_VERSION,
        MULTICOMPONENT_SCHEDULER_STAGE,
    )
    from core.run_kernel import Observation, RunStageStatus
    from core.strict_one_shot_model_transport import (
        normalize_canonical_model_provider,
    )

    inputs = _safe_mapping(getattr(action, "inputs", {}))
    expected = {
        "batch_index": inputs.get("batch_index"),
        "batch_id": inputs.get("batch_id"),
        "batch_digest": inputs.get("batch_digest"),
        "work_id": inputs.get("work_id"),
        "work_digest": inputs.get("work_digest"),
        "lease_id": inputs.get("lease_id"),
        "lease_digest": inputs.get("lease_digest"),
        "action_id": action.action_id,
        "action_sequence": action.sequence,
        "role": inputs.get("role"),
        "logical_evaluation_key": inputs.get("logical_evaluation_key"),
        "input_packet_digest": inputs.get("input_packet_digest"),
        "output_schema_variant": inputs.get("output_schema_variant"),
    }
    if result.schema_version != MULTICOMPONENT_SAFE_WORKER_RESULT_SCHEMA_VERSION or any(
        getattr(result, key) != value for key, value in expected.items()
    ):
        raise MulticomponentRoleRuntimeError(
            "safe worker result does not match its exact child action"
        )
    transport_facts = {
        "transport_submitted": result.transport_submitted,
        "transport_started": result.transport_started,
        "transport_completed": result.transport_completed,
        "provider_request_attempt_count": max(
            0, min(1, int(result.provider_request_attempt_count or 0))
        ),
        "observed_batch_max_in_flight": max(0, int(observed_batch_max_in_flight)),
    }
    scheduler = _safe_mapping(
        run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
    )
    scheduler_provider = normalize_canonical_model_provider(
        scheduler.get("configured_provider_class")
    )
    if result.failure_kind:
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.FAILED,
                payload={
                    "lease_settlement": LEASE_FAILED,
                    "failure_kind": result.failure_kind,
                    **transport_facts,
                },
            )
        )
        return None
    if (
        scheduler_provider
        and normalize_canonical_model_provider(result.provider) != scheduler_provider
    ):
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.FAILED,
                payload={
                    "lease_settlement": LEASE_FAILED,
                    "failure_kind": "provider_identity_mismatch",
                    **transport_facts,
                },
            )
        )
        return None
    if not run_kernel.multicomponent_work_lease_is_current(result.lease_id):
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.FAILED,
                payload={
                    "lease_settlement": LEASE_STALE,
                    "failure_kind": "semantic_authority_changed_after_dispatch",
                    **transport_facts,
                },
            )
        )
        return None
    artifact_core = {
        "schema_version": "multicomponent_semantic_role_artifact_v1",
        "role": result.role,
        "artifact_id": f"{result.role}:{action.action_id}",
        "run_id": action.run_id,
        "request_id": run_kernel.state.request_id,
        "input_packet_digest": result.input_packet_digest,
        "logical_evaluation_key": result.logical_evaluation_key,
        "logical_evaluations": 1,
        "physical_calls": 1,
        "configured_model_route": {
            "provider": scheduler_provider or normalize_canonical_model_provider(result.provider),
            "model": result.model,
            "role": "SmartModel",
        },
        "authorized_action_ref": {
            "action_id": action.action_id,
            "stage": action.stage,
            "sequence": action.sequence,
            "observation_type": action.expected_observation_type.value,
        },
        "semantic_output": deepcopy(dict(result.normalized_semantic_output or {})),
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
    }
    for key in (
        "batch_id",
        "batch_digest",
        "batch_index",
        "descriptor_digest",
        "lease_id",
        "lease_digest",
        "work_id",
        "work_digest",
        "grant_action_ref",
        "dispatch_action_ref",
        "accepted_contract_ref",
        "graph_ref",
        "target_kind",
        "component_id",
        "synthesis_key",
        "node_ref",
        "recovery_authorization_ref",
        "contract_amendment_admission_ref",
        "contract_amendment_application_ref",
        "selective_closure_ref",
        "scheduler_revision_at_grant",
        "output_schema_variant",
    ):
        artifact_core[key] = _json_safe(inputs.get(key))
    artifact = {**artifact_core, "artifact_digest": _digest(artifact_core)}
    validate_multicomponent_role_artifact(artifact, expected_role=result.role)
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={
                "semantic_role_artifact": artifact,
                **transport_facts,
            },
        )
    )
    return validate_multicomponent_role_artifact(artifact, expected_role=result.role)


def execute_multicomponent_role_call(
    *,
    run_kernel: Any,
    role: str,
    input_packet: Mapping[str, Any],
    strict_one_shot_transport: Callable[..., Any],
    clean_json_response: Callable[[str], str] | None,
    provider: str,
    model: str,
    use_reasoning: bool,
    logical_evaluation_key: str,
    output_schema_variant: str | None = None,
    lease_id: str | None = None,
    searchos_recovery_cycle_ref: Mapping[str, Any] | None = None,
    effort: str = "medium",
) -> dict[str, Any]:
    """Authorize, execute, parse, bind, and reduce one semantic role call."""

    from core.strict_one_shot_model_transport import (
        StrictOneShotModelTransportResult,
        normalize_canonical_model_provider,
    )

    normalized_role = _normalize_key(role)
    if normalized_role not in ROLE_SYSTEM_PROMPTS:
        raise MulticomponentRoleRuntimeError("unknown semantic role")
    schema_variant = _clean_text(output_schema_variant, limit=80)
    if schema_variant and not (
        normalized_role == ROLE_CROSS_COMPONENT_ANALYST
        and schema_variant == SELECTIVE_CROSS_COMPONENT_SCHEMA
    ):
        raise MulticomponentRoleRuntimeError(
            "semantic role output schema variant is invalid"
        )
    safe_input = _json_safe(input_packet)
    if not isinstance(safe_input, Mapping):
        raise MulticomponentRoleRuntimeError("semantic role input must be a mapping")
    if not callable(strict_one_shot_transport):
        raise MulticomponentRoleRuntimeError(
            "semantic role transport requires a strict one-shot SmartModel transport"
        )
    input_digest = _digest(safe_input)
    specialist_handoff_digest = _safe_mapping(
        safe_input.get("specialist_need_handoff")
    ).get("handoff_digest")
    canonical_provider = normalize_canonical_model_provider(provider)
    from core.multicomponent_graph_scheduling import (
        LEASE_FAILED,
        LEASE_STALE,
        MULTICOMPONENT_SCHEDULER_STAGE,
    )

    scheduler_projection = _safe_mapping(
        run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
    )
    scheduler_active = (
        scheduler_projection.get("status") == "active"
        and not bool(searchos_recovery_cycle_ref)
    )
    recovery_active = bool(searchos_recovery_cycle_ref)
    if searchos_recovery_cycle_ref:
        if lease_id:
            raise MulticomponentRoleRuntimeError(
                "SearchOS recovery role authority cannot combine with a "
                "scheduler lease"
            )
        action = run_kernel.authorize_multicomponent_role_call(
            role=normalized_role,
            input_packet_digest=input_digest,
            logical_evaluation_key=logical_evaluation_key,
            specialist_handoff_digest=specialist_handoff_digest,
            searchos_recovery_cycle_ref=searchos_recovery_cycle_ref,
        )
    elif scheduler_active:
        if not lease_id:
            raise MulticomponentRoleRuntimeError(
                "scheduler-active semantic transport requires an exact lease"
            )
        action = run_kernel.prepare_multicomponent_role_dispatch(
            lease_id=lease_id,
            role=normalized_role,
            input_packet_digest=input_digest,
            logical_evaluation_key=logical_evaluation_key,
            output_schema_variant=schema_variant,
            specialist_handoff_digest=specialist_handoff_digest,
        )
    else:
        if lease_id:
            raise MulticomponentRoleRuntimeError(
                "caller-authored lease is forbidden without scheduler authority"
            )
        action = run_kernel.authorize_multicomponent_role_call(
            role=normalized_role,
            input_packet_digest=input_digest,
            logical_evaluation_key=logical_evaluation_key,
            specialist_handoff_digest=specialist_handoff_digest,
        )
    system_prompt = (
        SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT
        if schema_variant == SELECTIVE_CROSS_COMPONENT_SCHEMA
        else ROLE_SYSTEM_PROMPTS[normalized_role]
    )
    from core.run_kernel import Observation, RunStageStatus

    try:
        transport_result = strict_one_shot_transport(
            json.dumps(safe_input, sort_keys=True),
            system_prompt,
            provider=canonical_provider,
            model=model,
            effort=effort,
            require_json=True,
            use_reasoning=use_reasoning,
        )
        if not isinstance(transport_result, StrictOneShotModelTransportResult):
            raise MulticomponentRoleRuntimeError(
                "strict one-shot transport returned an invalid result type"
            )
        if (
            normalize_canonical_model_provider(transport_result.canonical_provider)
            != canonical_provider
        ):
            raise MulticomponentRoleRuntimeError("provider_identity_mismatch")
        if transport_result.return_code != 0:
            raise MulticomponentRoleRuntimeError("model_transport_failure")
        semantic_output = _normalize_semantic_output(
            normalized_role,
            _parse_role_output(
                transport_result.output_text,
                clean_json_response=clean_json_response,
            ),
            output_schema_variant=schema_variant,
        )
    except RunCapExceeded:
        raise
    except Exception as exc:
        if scheduler_active or recovery_active:
            failure_kind = (
                "model_transport_failure"
                if not isinstance(exc, MulticomponentRoleRuntimeError)
                else "invalid_role_output"
            )
            if str(exc) == "provider_identity_mismatch":
                failure_kind = "provider_identity_mismatch"
            elif str(exc) == "model_transport_failure":
                failure_kind = "model_transport_failure"
            run_kernel.reduce(
                Observation.from_action(
                    action,
                    observation_type=action.expected_observation_type,
                    status=RunStageStatus.FAILED,
                    payload={
                        **({"lease_settlement": LEASE_FAILED} if scheduler_active else {}),
                        "failure_kind": failure_kind,
                    },
                )
            )
        raise
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
            "provider": canonical_provider,
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
    if scheduler_active:
        for key in (
            "lease_id",
            "lease_digest",
            "work_id",
            "work_digest",
            "grant_action_ref",
            "dispatch_action_ref",
            "accepted_contract_ref",
            "graph_ref",
            "target_kind",
            "component_id",
            "synthesis_key",
            "node_ref",
            "recovery_authorization_ref",
            "contract_amendment_admission_ref",
            "contract_amendment_application_ref",
            "selective_closure_ref",
            "scheduler_revision_at_grant",
            "output_schema_variant",
        ):
            artifact_core[key] = _json_safe(action.inputs.get(key))
    elif normalized_role == ROLE_CROSS_COMPONENT_ANALYST:
        artifact_core["accepted_contract_ref"] = _json_safe(
            safe_input.get("accepted_contract_ref")
            or safe_input.get("current_contract_ref")
        )
        artifact_core["graph_ref"] = _json_safe(
            safe_input.get("graph_ref")
        )
    if schema_variant:
        artifact_core["output_schema_variant"] = schema_variant
    artifact = {**artifact_core, "artifact_digest": _digest(artifact_core)}

    try:
        validate_multicomponent_role_artifact(
            artifact,
            expected_role=normalized_role,
        )
    except Exception:
        if scheduler_active or recovery_active:
            run_kernel.reduce(
                Observation.from_action(
                    action,
                    observation_type=action.expected_observation_type,
                    status=RunStageStatus.FAILED,
                    payload={
                        **({"lease_settlement": LEASE_FAILED} if scheduler_active else {}),
                        "failure_kind": "artifact_validation_failure",
                    },
                )
            )
        raise
    if scheduler_active and not run_kernel.multicomponent_work_lease_is_current(
        str(lease_id)
    ):
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.FAILED,
                payload={
                    "lease_settlement": LEASE_STALE,
                    "failure_kind": "semantic_authority_changed_after_dispatch",
                },
            )
        )
        raise MulticomponentRoleRuntimeError(
            "semantic role result rejected because its lease authority is stale"
        )
    observation = Observation.from_action(
        action,
        observation_type=action.expected_observation_type,
        status=RunStageStatus.COMPLETED,
        payload={"semantic_role_artifact": artifact},
    )
    try:
        run_kernel.reduce(observation)
    except Exception:
        if (
            action.action_id not in run_kernel.state.reduced_action_ids
            and run_kernel.state.next_observation_sequence == action.sequence
        ):
            run_kernel.reduce(
                Observation.from_action(
                    action,
                    observation_type=action.expected_observation_type,
                    status=RunStageStatus.FAILED,
                    payload={
                        **(
                            {"lease_settlement": LEASE_FAILED}
                            if scheduler_active
                            else {}
                        ),
                        "failure_kind": (
                            "semantic_role_observation_reduction_failure"
                        ),
                    },
                )
            )
        raise
    return validate_multicomponent_role_artifact(
        artifact,
        expected_role=normalized_role,
    )


def role_artifact_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    artifact = validate_multicomponent_role_artifact(value)
    ref = {
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
    if artifact.get("output_schema_variant"):
        ref["output_schema_variant"] = artifact["output_schema_variant"]
    return ref


def safe_packet_digest(value: Mapping[str, Any]) -> str:
    """Return the canonical digest used to bind safe role input packets."""

    return _digest(_json_safe(value))


__all__ = [
    "ROLE_COMPONENT_ANALYST",
    "ROLE_COMPONENT_ANALYST_RESUME",
    "ROLE_COMPONENT_DPRIME",
    "ROLE_CROSS_COMPONENT_ANALYST",
    "ROLE_SCRUTINEER",
    "ROLE_SYNTHESIS_DPRIME",
    "ROLE_SYSTEM_PROMPTS",
    "COMPONENT_ANALYST_CASE_POSTURES",
    "COMPONENT_ANALYST_SUPPORTING_CASE_POSTURES",
    "SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT",
    "SELECTIVE_CROSS_COMPONENT_SCHEMA",
    "SUPPORTED_QUERY_CLASS",
    "MulticomponentRoleRuntimeError",
    "PreparedMulticomponentTransportCall",
    "SafeMulticomponentWorkerResult",
    "execute_multicomponent_role_call",
    "execute_prepared_multicomponent_transport",
    "failed_unstarted_multicomponent_worker_result",
    "prepare_multicomponent_transport_call",
    "reduce_multicomponent_worker_result",
    "reject_model_authority_claims",
    "role_artifact_ref",
    "safe_packet_digest",
    "validate_multicomponent_role_artifact",
]
