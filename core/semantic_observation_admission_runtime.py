"""Canonical SemanticObservation admission runtime for AG-SEM-06.

This module is the second canonical semantic authority bridge. It provides the
bounded, pure helpers a RunKernel/RunAuthority-authorized reducer uses to admit
exactly one validated passive ``SemanticObservation`` proposal, with its
required sanitized content references, into canonical RunKernel-owned
observation-admission state.

It admits observations only. It does not reduce coverage, accept or apply
contract amendments, decide Sufficiency, create Author input, create a
FinalAnswerPacket, decide SearchJudgment, activate a QueryPlan/SearchWorkPlan,
authorize follow-up, change citation behavior, or perform any provider, search,
retrieval, fetch/read, or live validation behavior. Candidate caveats,
follow-up gaps, and amendment notes carried by an admitted observation remain
candidate-only: they never create coverage, amendments, or follow-up.

The helpers here are imported by ``core.run_kernel``; to keep the import graph
acyclic this module must not import ``core.run_kernel``. It reuses the AG-SEM-02
``SemanticObservation``/``SanitizedContentReference`` records and validators so
the admission digest and content-ref validation stay consistent with the
passive foundation.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.semantic_observation_foundation import (
    MAX_BOUNDED_TEXT_CHARS,
    SanitizedContentReference,
    SemanticObservation,
    validate_content_references,
)

SEMANTIC_OBSERVATION_ADMISSION_SCHEMA_VERSION = "semantic_observation_admission_ag_sem_06_v1"
SEMANTIC_OBSERVATION_ADMISSION_STAGE = "semantic_observation_admission"
SEMANTIC_OBSERVATION_ADMISSION_REASON = "semantic_observation_admission_from_authorized_passive_observation"
SEMANTIC_OBSERVATION_ADMISSION_TRACE_KEY = "semantic_observation_admission"
SEMANTIC_OBSERVATION_ADMISSION_OWNER = "RunKernel.SemanticObservationAdmission"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db_row",
        "full_trace",
        "logs",
        "model_response",
        "page_corpus",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_page",
        "raw_prompt",
        "raw_provider_payload",
        "raw_trace",
        "secret",
        "token",
        "unbounded_text",
    }
)

# Closed surfaces this admission bridge must never create or decide.
_FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "accepted_amendment",
        "author_input",
        "canonical_coverage",
        "component_coverage",
        "component_coverage_record",
        "contract_amendment_record",
        "coverage",
        "coverage_decision_applied",
        "final_answer",
        "final_answer_packet",
        "followup_activation",
        "query_plan_activation",
        "search_judgment_decision",
        "search_work_plan_activation",
        "sufficiency_decision_applied",
        "sufficiency_judgment",
    }
)

_SUPPORT_BEARING_STATUSES = frozenset({"supports", "contradicts", "qualifies"})
_ANSWER_BEARING_KINDS = frozenset({"support", "contradiction", "qualification"})

# Closed posture flags that must never arrive truthy / present-as-authority on a
# passive observation payload. Reconstructing the AG-SEM-02 record would force
# these back to their safe defaults, so they are inspected and rejected on the
# raw payload *before* reconstruction rather than silently cleaned.
_OBSERVATION_UNSAFE_POSTURE_KEYS = (
    "canonical_state",
    "coverage_decision",
    "component_satisfied",
    "final_answer_authority",
    "author_input_created",
    "runtime_behavior_changed",
    "accepted_authority",
    "accepted_contract_amendment",
    "final_answer_decision",
    "answer_decision",
    "sufficiency_decision",
    "sufficiency_judgment",
    "final_answer_packet",
    "author_input",
    "canonical_coverage",
    "component_coverage_record",
    "contract_amendment_record",
)

# Content-reference posture flags that must be safe before reconstruction. The
# retention/authority flags must never be unsafe; the bounded/sanitized/trace
# guards must never be explicitly disabled.
_CONTENT_REF_UNSAFE_IF_TRUE = (
    "accepted_authority",
    "raw_content_retained",
    "raw_provider_payload_retained",
    "raw_prompt_retained",
    "raw_model_response_retained",
    "private_logs_retained",
    "db_cache_rows_retained",
    "full_trace_retained",
    "secrets_returned",
)
_CONTENT_REF_UNSAFE_IF_DISABLED = (
    "sanitized",
    "bounded",
    "trace_only",
)

# Action-input keys that must bind the admission to the observation and the
# accepted initial answer contract.
_REQUIRED_INPUT_KEYS = (
    "semantic_observation_id",
    "semantic_observation_digest",
    "accepted_contract_digest",
    "accepted_contract_version",
    "answer_component_id",
    "component_revision",
    "component_digest",
)


class SemanticObservationAdmissionError(ValueError):
    """Raised when a passive observation cannot be admitted as canonical state."""


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if not clean_key or _is_sensitive_key(clean_key):
                continue
            if clean_key == "bounded_text":
                out[clean_key] = _clean_text(
                    value[key],
                    limit=MAX_BOUNDED_TEXT_CHARS,
                )
            else:
                out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict(), depth=depth + 1)
    return _clean_text(value, limit=300)


def _text_list(value: Any, *, limit: int = 160) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return []
    out: list[str] = []
    for item in value:
        text = _clean_token(item, limit=limit)
        if text:
            out.append(text)
    return out


def _normalize_evidence_ref(value: Any) -> str | None:
    """Normalize an evidence id into the EvidenceLedger custody identity space.

    The AG-91J EvidenceLedger casefolds candidate ids and maps hyphens/spaces to
    underscores. Custody matching here must compare in that same identity space
    so a cited ref is checked against the ledger's normalized custody ids.
    """

    token = _clean_token(value)
    if not token:
        return None
    return token.casefold().replace("-", "_").replace(" ", "_")


def _digest_json(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple):
        keys = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _reject_unsafe_observation_posture(payload: Mapping[str, Any]) -> None:
    """Reject an authority-tainted observation payload before reconstruction.

    Reconstructing the AG-SEM-02 ``SemanticObservation`` would normalize closed
    posture flags back to their safe defaults; this guard inspects the raw
    payload first so a tainted proposal is rejected rather than silently cleaned.
    """

    tainted = sorted(key for key in _OBSERVATION_UNSAFE_POSTURE_KEYS if payload.get(key))
    if tainted:
        raise SemanticObservationAdmissionError(
            "semantic observation payload carries closed authority posture: " + ", ".join(tainted)
        )


def _reject_unsafe_content_reference_posture(payload: Mapping[str, Any]) -> None:
    """Reject an authority/retention-tainted content-ref payload before reconstruction.

    Reconstructing the AG-SEM-02 ``SanitizedContentReference`` would force the
    retention/sanitization posture back to safe defaults; this guard inspects the
    raw payload first so an unsafe content ref is rejected rather than cleaned.
    """

    content_ref_id = _clean_token(payload.get("content_ref_id")) or "<unknown>"
    tainted = sorted(key for key in _CONTENT_REF_UNSAFE_IF_TRUE if payload.get(key))
    disabled = sorted(key for key in _CONTENT_REF_UNSAFE_IF_DISABLED if key in payload and not payload.get(key))
    problems = tainted + [f"{key}_disabled" for key in disabled]
    if problems:
        raise SemanticObservationAdmissionError(
            f"sanitized content reference {content_ref_id} carries unsafe retention/authority posture: "
            + ", ".join(problems)
        )


def _reconstruct_content_reference(payload: Mapping[str, Any]) -> SanitizedContentReference:
    """Rebuild a SanitizedContentReference from its sanitized ``to_dict`` payload.

    The reconstructed record recomputes its own content digest from the actual
    bounded content / structured value, so a stale or tampered ``content_digest``
    can be detected by comparing the recomputed digest against the declared one.
    """

    locator = payload.get("locator")
    locator = dict(locator) if isinstance(locator, Mapping) else {}
    try:
        return SanitizedContentReference(
            content_ref_id=payload.get("content_ref_id"),
            evidence_ref_id=payload.get("evidence_ref_id"),
            answer_component_id=payload.get("answer_component_id"),
            content_kind=payload.get("content_kind"),
            bounded_text=payload.get("bounded_text"),
            structured_value=payload.get("structured_value"),
            admitted_evidence_ref=payload.get("admitted_evidence_ref"),
            source_id=payload.get("source_id"),
            source_digest=payload.get("source_digest"),
            source_url=payload.get("source_url"),
            source_title=payload.get("source_title"),
            source_domain=payload.get("source_domain"),
            component_revision=payload.get("component_revision"),
            component_contract_digest=payload.get("component_contract_digest"),
            question_meaning_record_id=payload.get("question_meaning_record_id"),
            question_meaning_record_digest=payload.get("question_meaning_record_digest"),
            page=locator.get("page"),
            section=locator.get("section"),
            table=locator.get("table"),
            row=locator.get("row"),
            column=locator.get("column"),
            char_range_start=locator.get("char_range_start"),
            char_range_end=locator.get("char_range_end"),
            extraction_method=payload.get("extraction_method"),
            worker_kind=payload.get("worker_kind"),
            currentness=payload.get("currentness"),
            observed_at=payload.get("observed_at"),
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {},
        )
    except (ValueError, TypeError) as exc:
        raise SemanticObservationAdmissionError(f"invalid sanitized content reference payload: {exc}") from exc


def _reconstruct_observation(payload: Mapping[str, Any]) -> SemanticObservation:
    """Rebuild a SemanticObservation from its sanitized ``to_dict`` payload.

    The reconstructed record recomputes its own observation digest from the
    actual content, so a stale or tampered ``observation_digest`` can be detected
    by comparing the recomputed digest against the declared one.
    """

    try:
        return SemanticObservation(
            observation_id=payload.get("observation_id"),
            observation_kind=payload.get("observation_kind"),
            answer_component_id=payload.get("answer_component_id"),
            support_status=payload.get("support_status"),
            claim_or_value=payload.get("claim_or_value"),
            question_meaning_record_id=payload.get("question_meaning_record_id"),
            question_meaning_record_digest=payload.get("question_meaning_record_digest"),
            contract_version=payload.get("contract_version"),
            contract_digest=payload.get("contract_digest"),
            component_revision=payload.get("component_revision"),
            component_contract_digest=payload.get("component_contract_digest"),
            evidence_refs=tuple(_text_list(payload.get("evidence_refs"))),
            content_refs=tuple(_text_list(payload.get("content_refs"))),
            support_kind=payload.get("support_kind") or "direct",
            directness=payload.get("directness"),
            normalization_fit=payload.get("normalization_fit"),
            scope_fit=payload.get("scope_fit"),
            assumption_fit=payload.get("assumption_fit"),
            inference_depth=int(payload.get("inference_depth") or 0),
            contradiction_refs=tuple(_text_list(payload.get("contradiction_refs"))),
            conflicting_observation_refs=tuple(_text_list(payload.get("conflicting_observation_refs"))),
            missing_fact_notes=tuple(_text_list(payload.get("missing_fact_notes"), limit=500)),
            candidate_caveats=tuple(_text_list(payload.get("candidate_caveats"), limit=400)),
            candidate_followup_gaps=tuple(_text_list(payload.get("candidate_followup_gaps"), limit=400)),
            candidate_contract_amendment_notes=tuple(
                _text_list(payload.get("candidate_contract_amendment_notes"), limit=400)
            ),
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {},
        )
    except (ValueError, TypeError) as exc:
        raise SemanticObservationAdmissionError(f"invalid semantic observation payload: {exc}") from exc


def _accepted_component_index(accepted_contract: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for ref in accepted_contract.get("accepted_answer_component_refs") or ():
        if isinstance(ref, Mapping):
            component_id = _clean_token(ref.get("component_id"))
            if component_id:
                index[component_id] = ref
    return index


def _evidence_custody_refs(evidence_ledger_projection: Mapping[str, Any]) -> set[str]:
    """Collect the evidence ids the current EvidenceLedger projection can vouch for.

    The AG-91J EvidenceLedger projection exposes candidate-level custody through
    ``candidate_records``, ``custody_records``, ``requirement_links``, and the
    ``linked_candidate_ids`` of ``source_requirements``. An admitted observation
    or content reference may only cite evidence ids drawn from these existing
    custody refs; foreign or missing ids are rejected.
    """

    allowed: set[str] = set()
    for record in evidence_ledger_projection.get("candidate_records") or ():
        if isinstance(record, Mapping):
            candidate_id = _normalize_evidence_ref(record.get("candidate_id"))
            if candidate_id:
                allowed.add(candidate_id)
    for record in evidence_ledger_projection.get("custody_records") or ():
        if isinstance(record, Mapping):
            candidate_id = _normalize_evidence_ref(record.get("candidate_id"))
            if candidate_id:
                allowed.add(candidate_id)
    for link in evidence_ledger_projection.get("requirement_links") or ():
        if isinstance(link, Mapping):
            candidate_id = _normalize_evidence_ref(link.get("candidate_id"))
            if candidate_id:
                allowed.add(candidate_id)
    for requirement in evidence_ledger_projection.get("source_requirements") or ():
        if isinstance(requirement, Mapping):
            for candidate_id in _text_list(requirement.get("linked_candidate_ids")):
                normalized = _normalize_evidence_ref(candidate_id)
                if normalized:
                    allowed.add(normalized)
    return allowed


def _admission_content_digest_payload(state_core: Mapping[str, Any]) -> dict[str, Any]:
    lineage = dict(state_core.get("lineage") or {})
    lineage.pop("reducer_action_id", None)
    return {
        "schema_version": state_core.get("schema_version"),
        "run_id": state_core.get("run_id"),
        "request_id": state_core.get("request_id"),
        "observation_id": state_core.get("observation_id"),
        "observation_digest": state_core.get("observation_digest"),
        "accepted_contract_version": state_core.get("accepted_contract_version"),
        "accepted_contract_digest": state_core.get("accepted_contract_digest"),
        "parent_question_meaning_record_id": state_core.get("parent_question_meaning_record_id"),
        "parent_question_meaning_record_digest": state_core.get("parent_question_meaning_record_digest"),
        "answer_component_id": state_core.get("answer_component_id"),
        "component_revision": state_core.get("component_revision"),
        "component_digest": state_core.get("component_digest"),
        "evidence_refs": state_core.get("evidence_refs"),
        "content_refs": state_core.get("content_refs"),
        "observation_kind": state_core.get("observation_kind"),
        "support_status": state_core.get("support_status"),
        "support_kind": state_core.get("support_kind"),
        "directness": state_core.get("directness"),
        "claim_or_value": state_core.get("claim_or_value"),
        "normalization_fit": state_core.get("normalization_fit"),
        "scope_fit": state_core.get("scope_fit"),
        "assumption_fit": state_core.get("assumption_fit"),
        "candidate_caveats": state_core.get("candidate_caveats"),
        "candidate_followup_gaps": state_core.get("candidate_followup_gaps"),
        "candidate_contract_amendment_notes": state_core.get("candidate_contract_amendment_notes"),
        "lineage": lineage,
    }


def _require_match(condition: bool, message: str) -> None:
    if not condition:
        raise SemanticObservationAdmissionError(message)


def build_semantic_observation_admission_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any] | None,
    accepted_contract: Mapping[str, Any] | None,
    evidence_ledger_projection: Mapping[str, Any] | None,
    existing_observation_ids: Sequence[str] = (),
    existing_observation_digests: Sequence[str] = (),
    run_id: str,
    request_id: str,
) -> dict[str, Any]:
    """Validate one passive observation and build canonical admission state.

    Raises ``SemanticObservationAdmissionError`` on any binding, payload,
    custody, duplicate, or closed-surface violation. The returned mapping is
    canonical RunKernel state. This function admits the observation only; it
    never reduces coverage, amends the contract, decides Sufficiency, or creates
    Author/final-answer behavior.
    """

    clean_action_id = _clean_token(action_id, limit=200)
    if not clean_action_id:
        raise SemanticObservationAdmissionError("semantic observation admission requires an authorized action id")
    clean_run_id = _clean_token(run_id)
    clean_request_id = _clean_token(request_id)
    if not clean_run_id or not clean_request_id:
        raise SemanticObservationAdmissionError("semantic observation admission requires run_id and request_id")

    # 1. Require an accepted initial answer contract from AG-SEM-05.
    contract = _safe_mapping(accepted_contract)
    if not contract or contract.get("canonical_state") is not True:
        raise SemanticObservationAdmissionError(
            "semantic observation admission requires an accepted initial answer contract"
        )
    accepted_contract_version = _clean_token(contract.get("accepted_contract_version"))
    accepted_contract_digest = _clean_token(contract.get("accepted_contract_digest"), limit=128)
    parent_qmr_id = _clean_token(contract.get("parent_question_meaning_record_id"))
    parent_qmr_digest = _clean_token(contract.get("parent_question_meaning_record_digest"), limit=128)
    if not accepted_contract_version or not accepted_contract_digest or not parent_qmr_id or not parent_qmr_digest:
        raise SemanticObservationAdmissionError(
            "accepted initial answer contract is missing required version/digest/parent bindings"
        )
    component_index = _accepted_component_index(contract)
    if not component_index:
        raise SemanticObservationAdmissionError(
            "accepted initial answer contract has no accepted answer component refs"
        )

    # 2. Parse the passive observation proposal and its content references. The
    #    raw incoming mappings are retained so posture/retention flags can be
    #    inspected before any sensitive-key scrubbing normalizes them away.
    raw_payload = observation_payload if isinstance(observation_payload, Mapping) else {}
    if not raw_payload:
        raise SemanticObservationAdmissionError("semantic observation admission requires an observation payload")
    raw_observation_dict = raw_payload.get("semantic_observation")
    raw_observation_dict = dict(raw_observation_dict) if isinstance(raw_observation_dict, Mapping) else {}
    if not raw_observation_dict:
        raise SemanticObservationAdmissionError(
            "semantic observation admission requires a semantic_observation proposal payload"
        )
    raw_content_refs = raw_payload.get("sanitized_content_references")
    if raw_content_refs is None:
        raw_content_refs = raw_payload.get("content_references")
    raw_content_ref_dicts: list[dict[str, Any]] = []
    for ref in raw_content_refs or ():
        if isinstance(ref, Mapping):
            raw_content_ref_dicts.append(dict(ref))

    # 3. Reject authority/retention-tainted payloads *before* any scrubbing or
    #    reconstruction so closed posture flags are not silently normalized back
    #    to safe defaults (reconstruction would otherwise clean them).
    _reject_unsafe_observation_posture(raw_observation_dict)
    for ref_dict in raw_content_ref_dicts:
        _reject_unsafe_content_reference_posture(ref_dict)

    # 4. Sanitize the payloads, then re-check closed authority surfaces on the
    #    sanitized view and reconstruct records so digests recompute from content.
    payload = _safe_mapping(raw_payload)
    observation_dict = _safe_mapping(raw_observation_dict)
    content_ref_dicts: list[dict[str, Any]] = []
    for ref in raw_content_ref_dicts:
        ref_mapping = _safe_mapping(ref)
        if ref_mapping:
            content_ref_dicts.append(ref_mapping)
    forbidden = sorted(_collect_keys(payload) & _FORBIDDEN_AUTHORITY_FIELDS)
    if forbidden:
        raise SemanticObservationAdmissionError(
            "observation payload includes closed authority fields: " + ", ".join(forbidden)
        )
    observation = _reconstruct_observation(observation_dict)
    content_references = [_reconstruct_content_reference(ref) for ref in content_ref_dicts]

    if observation.passive is not True or observation.canonical_state is True:
        raise SemanticObservationAdmissionError("semantic observation must be a passive, non-canonical proposal")
    if observation.accepted_authority is True or observation.runtime_behavior_changed is True:
        raise SemanticObservationAdmissionError("semantic observation must not already be accepted authority")

    # 5. Recompute the observation digest and reject stale/tampered payloads.
    recomputed_observation_digest = observation.observation_digest
    declared_observation_digest = _clean_token(observation_dict.get("observation_digest"), limit=128)
    if declared_observation_digest and declared_observation_digest != recomputed_observation_digest:
        raise SemanticObservationAdmissionError(
            "stale observation payload: observation digest does not match payload content"
        )

    # 6. Recompute each content-reference digest and reject stale/tampered refs.
    for ref_dict, ref in zip(content_ref_dicts, content_references, strict=True):
        declared_content_digest = _clean_token(ref_dict.get("content_digest"), limit=128)
        if declared_content_digest and declared_content_digest != ref.content_digest:
            raise SemanticObservationAdmissionError(
                f"stale content reference payload: content digest does not match content for "
                f"{ref.content_ref_id}"
            )

    # 7. Validate the observation against its provided sanitized content refs
    #    using the AG-SEM-02 validators (support-bearing observations require
    #    answer-bearing content refs; missing/incompatible refs are rejected;
    #    refs must remain sanitized and bounded).
    content_validation = validate_content_references(content_references)
    if not content_validation.ok:
        raise SemanticObservationAdmissionError(
            "sanitized content references failed validation: " + "; ".join(content_validation.errors)
        )
    observation_validation = observation.validate(content_references=content_references)
    if not observation_validation.ok:
        raise SemanticObservationAdmissionError(
            "semantic observation failed validation: " + "; ".join(observation_validation.errors)
        )

    # 8. Require the issued action to bind the observation and accepted contract.
    inputs = dict(action_inputs or {})
    missing_inputs = [key for key in _REQUIRED_INPUT_KEYS if not _clean_token(inputs.get(key), limit=200)]
    if missing_inputs:
        raise SemanticObservationAdmissionError(
            "authorized action must bind: " + ", ".join(missing_inputs)
        )
    bound_request_id = _clean_token(inputs.get("request_id"))
    if bound_request_id and bound_request_id != clean_request_id:
        raise SemanticObservationAdmissionError("authorized action request_id binding does not match the request")

    _require_match(
        _clean_token(inputs.get("semantic_observation_id")) == observation.observation_id,
        "action semantic_observation_id binding does not match the observation id",
    )
    _require_match(
        _clean_token(inputs.get("semantic_observation_digest"), limit=128) == recomputed_observation_digest,
        "action semantic_observation_digest binding does not match the recomputed observation digest",
    )
    _require_match(
        _clean_token(inputs.get("accepted_contract_digest"), limit=128) == accepted_contract_digest,
        "action accepted_contract_digest binding does not match the accepted contract digest",
    )
    _require_match(
        _clean_token(inputs.get("accepted_contract_version")) == accepted_contract_version,
        "action accepted_contract_version binding does not match the accepted contract version",
    )
    _require_match(
        _clean_token(inputs.get("answer_component_id")) == observation.answer_component_id,
        "action answer_component_id binding does not match the observation component",
    )

    # 9. Validate exact accepted-contract binding on the observation.
    _require_match(
        _clean_token(observation.contract_version) == accepted_contract_version,
        "observation contract_version does not match the accepted initial answer contract version",
    )
    _require_match(
        observation.contract_digest == accepted_contract_digest,
        "observation contract_digest does not match the accepted initial answer contract digest",
    )
    _require_match(
        _clean_token(observation.question_meaning_record_id) == parent_qmr_id,
        "observation question_meaning_record_id does not match the accepted parent QMR id",
    )
    _require_match(
        observation.question_meaning_record_digest == parent_qmr_digest,
        "observation question_meaning_record_digest does not match the accepted parent QMR digest",
    )

    # 10. Validate exact component binding against the accepted component ref.
    accepted_component = component_index.get(observation.answer_component_id)
    if accepted_component is None:
        raise SemanticObservationAdmissionError(
            "observation answer_component_id is not an accepted answer component ref"
        )
    accepted_component_revision = _clean_token(accepted_component.get("component_revision"))
    accepted_component_digest = _clean_token(accepted_component.get("component_digest"), limit=128)
    _require_match(
        _clean_token(inputs.get("component_revision")) == accepted_component_revision,
        "action component_revision binding does not match the accepted component revision",
    )
    _require_match(
        _clean_token(inputs.get("component_digest"), limit=128) == accepted_component_digest,
        "action component_digest binding does not match the accepted component digest",
    )
    _require_match(
        _clean_token(observation.component_revision) == accepted_component_revision,
        "observation component_revision does not match the accepted component revision",
    )
    _require_match(
        observation.component_contract_digest == accepted_component_digest,
        "observation component_contract_digest does not match the accepted component digest",
    )

    # 11. Validate content refs against the observation and accepted component.
    content_ref_index = {ref.content_ref_id: ref for ref in content_references}
    if observation.observation_kind.value in _ANSWER_BEARING_KINDS and not observation.content_refs:
        raise SemanticObservationAdmissionError(
            "support-bearing observation requires answer-bearing content refs"
        )
    for content_ref_id in observation.content_refs:
        ref = content_ref_index.get(content_ref_id)
        if ref is None:
            raise SemanticObservationAdmissionError(
                f"observation references missing content ref {content_ref_id}"
            )
        _require_match(
            ref.answer_component_id == observation.answer_component_id,
            f"content ref {content_ref_id} component does not match the observation component",
        )
        if ref.component_revision:
            _require_match(
                _clean_token(ref.component_revision) == accepted_component_revision,
                f"content ref {content_ref_id} component_revision does not match the accepted component",
            )
        if ref.component_contract_digest:
            _require_match(
                ref.component_contract_digest == accepted_component_digest,
                f"content ref {content_ref_id} component_contract_digest does not match the accepted component",
            )
        if ref.question_meaning_record_id:
            _require_match(
                _clean_token(ref.question_meaning_record_id) == parent_qmr_id,
                f"content ref {content_ref_id} question_meaning_record_id does not match the accepted parent QMR",
            )
        if ref.question_meaning_record_digest:
            _require_match(
                ref.question_meaning_record_digest == parent_qmr_digest,
                f"content ref {content_ref_id} question_meaning_record_digest does not match the accepted parent QMR",
            )

    # 12. Validate EvidenceLedger custody refs: every cited evidence id must
    #     correspond to an existing ledger custody/candidate ref.
    allowed_evidence_refs = _evidence_custody_refs(_safe_mapping(evidence_ledger_projection))
    cited_evidence_refs: list[str] = list(observation.evidence_refs)
    for content_ref_id in observation.content_refs:
        ref = content_ref_index.get(content_ref_id)
        if ref is None:
            continue
        for candidate in (ref.evidence_ref_id, ref.admitted_evidence_ref):
            token = _clean_token(candidate)
            if token:
                cited_evidence_refs.append(token)
    if not cited_evidence_refs:
        raise SemanticObservationAdmissionError(
            "semantic observation admission requires at least one evidence custody ref"
        )
    foreign_refs = sorted(
        {ref for ref in cited_evidence_refs if _normalize_evidence_ref(ref) not in allowed_evidence_refs}
    )
    if foreign_refs:
        raise SemanticObservationAdmissionError(
            "semantic observation cites evidence refs absent from EvidenceLedger custody: "
            + ", ".join(foreign_refs)
        )

    # 13. Reject duplicate observation ids/digests (stale/replayed admissions).
    if observation.observation_id in {_clean_token(item) for item in existing_observation_ids if item}:
        raise SemanticObservationAdmissionError(
            f"semantic observation {observation.observation_id} is already admitted"
        )
    if recomputed_observation_digest in {
        _clean_token(item, limit=128) for item in existing_observation_digests if item
    }:
        raise SemanticObservationAdmissionError("semantic observation digest is already admitted")

    # 14. Build canonical, sanitized, projection-safe admission state.
    evidence_refs = sorted(set(observation.evidence_refs))
    content_ref_records = [
        {"content_ref_id": ref.content_ref_id, "content_digest": ref.content_digest}
        for ref in content_references
        if ref.content_ref_id in set(observation.content_refs)
    ]
    lineage = {
        "created_by": SEMANTIC_OBSERVATION_ADMISSION_OWNER,
        "created_from": ["passive_semantic_observation_proposal", "accepted_initial_answer_contract"],
        "reducer_action_id": clean_action_id,
        "parent_observation_digest": recomputed_observation_digest,
        "accepted_contract_digest": accepted_contract_digest,
    }
    observation_safe = observation.to_dict(include_validation=False)
    state_core: dict[str, Any] = {
        "schema_version": SEMANTIC_OBSERVATION_ADMISSION_SCHEMA_VERSION,
        "owner": SEMANTIC_OBSERVATION_ADMISSION_OWNER,
        "trace_key": SEMANTIC_OBSERVATION_ADMISSION_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "observation_id": observation.observation_id,
        "observation_digest": recomputed_observation_digest,
        "accepted_contract_version": accepted_contract_version,
        "accepted_contract_digest": accepted_contract_digest,
        "parent_question_meaning_record_id": parent_qmr_id,
        "parent_question_meaning_record_digest": parent_qmr_digest,
        "answer_component_id": observation.answer_component_id,
        "component_revision": accepted_component_revision,
        "component_digest": accepted_component_digest,
        "evidence_refs": evidence_refs,
        "content_refs": [record["content_ref_id"] for record in content_ref_records],
        "content_ref_records": content_ref_records,
        "observation_kind": observation.observation_kind.value,
        "support_status": observation.support_status.value,
        "support_kind": observation.support_kind.value,
        "directness": observation.directness.value,
        "support_bearing": observation.support_status.value in _SUPPORT_BEARING_STATUSES,
        "claim_or_value": observation_safe.get("claim_or_value"),
        "normalization_fit": observation_safe.get("normalization_fit"),
        "scope_fit": observation_safe.get("scope_fit"),
        "assumption_fit": observation_safe.get("assumption_fit"),
        "candidate_caveats": list(observation.candidate_caveats),
        "candidate_followup_gaps": list(observation.candidate_followup_gaps),
        "candidate_contract_amendment_notes": list(observation.candidate_contract_amendment_notes),
        "lineage": lineage,
        # Closed surfaces remain closed for this admission bridge.
        "coverage_created": False,
        "component_satisfied": False,
        "amendment_created": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }
    admission_digest = _digest_json(_admission_content_digest_payload(state_core))
    return {**state_core, "admission_digest": admission_digest}


def build_semantic_observation_admission_projection(
    *,
    admission_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project canonical admission state with no raw or private data."""

    return {
        "owner": SEMANTIC_OBSERVATION_ADMISSION_OWNER,
        "schema_version": admission_state.get("schema_version"),
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": admission_state.get("run_id"),
        "request_id": admission_state.get("request_id"),
        "authorized_action_id": admission_state.get("authorized_action_id"),
        "observation_id": admission_state.get("observation_id"),
        "observation_digest": admission_state.get("observation_digest"),
        "admission_digest": admission_state.get("admission_digest"),
        "accepted_contract_version": admission_state.get("accepted_contract_version"),
        "accepted_contract_digest": admission_state.get("accepted_contract_digest"),
        "parent_question_meaning_record_id": admission_state.get("parent_question_meaning_record_id"),
        "parent_question_meaning_record_digest": admission_state.get("parent_question_meaning_record_digest"),
        "answer_component_id": admission_state.get("answer_component_id"),
        "component_revision": admission_state.get("component_revision"),
        "component_digest": admission_state.get("component_digest"),
        "evidence_refs": list(admission_state.get("evidence_refs", [])),
        "content_refs": list(admission_state.get("content_refs", [])),
        "content_ref_records": [dict(record) for record in admission_state.get("content_ref_records", [])],
        "observation_kind": admission_state.get("observation_kind"),
        "support_status": admission_state.get("support_status"),
        "support_kind": admission_state.get("support_kind"),
        "directness": admission_state.get("directness"),
        "support_bearing": admission_state.get("support_bearing", False),
        "claim_or_value": admission_state.get("claim_or_value"),
        "candidate_caveats": list(admission_state.get("candidate_caveats", [])),
        "candidate_followup_gaps": list(admission_state.get("candidate_followup_gaps", [])),
        "candidate_contract_amendment_notes": list(
            admission_state.get("candidate_contract_amendment_notes", [])
        ),
        "lineage": admission_state.get("lineage", {}),
        "coverage_created": False,
        "component_satisfied": False,
        "amendment_created": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }


__all__ = [
    "SEMANTIC_OBSERVATION_ADMISSION_OWNER",
    "SEMANTIC_OBSERVATION_ADMISSION_REASON",
    "SEMANTIC_OBSERVATION_ADMISSION_SCHEMA_VERSION",
    "SEMANTIC_OBSERVATION_ADMISSION_STAGE",
    "SEMANTIC_OBSERVATION_ADMISSION_TRACE_KEY",
    "SemanticObservationAdmissionError",
    "build_semantic_observation_admission_projection",
    "build_semantic_observation_admission_state",
]
