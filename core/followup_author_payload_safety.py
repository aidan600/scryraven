from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.followup_deliberation import safe_json
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.followup_fixture_boundaries import followup_closed_surface_boundary_flags

_FALSE_SAFE_SUFFIXES = ("allowed", "called", "created", "included", "ready", "retained")


def safe_mapping(value: Any) -> dict[str, Any]:
    return safe_json(dict(value)) if isinstance(value, Mapping) else {}


def safe_mapping_sequence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return []
    return [safe_mapping(item) for item in value if isinstance(item, Mapping)]


def safe_string_sequence(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def projection_digest(value: Mapping[str, Any]) -> str:
    return followup_projection_digest(safe_mapping(value))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PermissionError(message)


def reject_caller_controlled_inputs(inputs, *, caller_controlled_keys, context_label, closed_surface_rejector, check_raw_keys=False) -> None:
    raw_inputs = dict(inputs) if isinstance(inputs, Mapping) else {}
    action_inputs = safe_mapping(raw_inputs)
    for key in (raw_inputs if check_raw_keys else action_inputs):
        if str(key or "").casefold() in caller_controlled_keys:
            raise PermissionError(f"{context_label} cannot accept caller-supplied {key!r}")
    closed_surface_rejector(action_inputs)


def updated_with_mutation(value: Mapping[str, Any], mutation: Mapping[str, Any]) -> dict[str, Any]:
    return safe_json({**safe_mapping(value), **safe_mapping(mutation)})


def boundary_flags_from_tokens(tokens: Sequence[str]) -> dict[str, bool]:
    flags = followup_closed_surface_boundary_flags()
    for token in tokens:
        marker = token[:1]
        require(marker in {"+", "-"}, f"invalid boundary flag token {token!r}")
        flags[token[1:]] = marker == "+"
    return flags


def reject_closed_surface_payload(value, *, false_fields, allowed_key_tokens, closed_key_parts, closed_string_parts, context_label, old_ready_status_policy=None) -> None:
    false_field_set = set(false_fields)
    allowed_key_set = set(allowed_key_tokens)

    def reject(item) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                token = str(key or "").casefold()
                false_safe = child is False and (
                    token in false_field_set or token.endswith(_FALSE_SAFE_SUFFIXES)
                )
                if false_safe:
                    continue
                if token not in allowed_key_set and any(part in token for part in closed_key_parts):
                    raise PermissionError(f"{context_label} cannot retain {key!r}")
                reject(child)
        elif isinstance(item, str):
            lowered = item.casefold()
            if any(token in lowered for token in closed_string_parts):
                raise PermissionError(f"{context_label} contains closed text")
            old_ready = (old_ready_status_policy == "contains" and "author_input_ready" in lowered) or (
                old_ready_status_policy == "exact" and lowered == "author_input_ready"
            )
            if old_ready:
                raise PermissionError(f"{context_label} cannot use old ready status")
        elif isinstance(item, Sequence) and not isinstance(item, bytes):
            for child in item:
                reject(child)

    reject(value)


def validate_closed_flags(state: Mapping[str, Any], *, true_fields, false_fields, boundary_flags, context_label) -> None:
    payload = safe_mapping(state)
    for field in true_fields:
        require(payload.get(field) is True, f"{context_label} requires {field}=True")
    for field in false_fields:
        require(payload.get(field) is False, f"{context_label} requires {field}=False")
    flags = safe_mapping(payload.get("behavior_boundary_flags"))
    if flags:
        expected_flags = boundary_flags() if callable(boundary_flags) else boundary_flags
        for field, expected in expected_flags.items():
            require(flags.get(field) is expected, f"{context_label} boundary {field} mismatch")


def projection_from_record_mutation(current_value, record_state, context, mutation_field, expected_mutation_fields, current_digest_field, mutation_mismatch_message, stale_message, projection_update_validator) -> dict[str, Any]:
    value = safe_mapping(current_value)
    record = safe_mapping(record_state)
    mutation = safe_mapping(record.get(mutation_field))
    require(set(mutation) == set(expected_mutation_fields), mutation_mismatch_message)
    require(projection_digest(value) == record.get(current_digest_field), stale_message)
    updated = updated_with_mutation(value, mutation)
    projection_update_validator(value, updated, record, context)
    return safe_json(updated)


def validate_projection_update(before, updated, record, context, *, allowed_mutation_fields, phase_label, ref_field, ref_label, author_payload_ref_status) -> None:
    changed = {key for key in set(before) | set(updated) if before.get(key) != updated.get(key)}
    require(changed <= set(allowed_mutation_fields), f"{phase_label} {context} changed non-{phase_label} fields")
    require(
        safe_mapping(updated.get("author_payload_ref")) == safe_mapping(before.get("author_payload_ref")),
        f"{phase_label} {context} must not change author_payload_ref",
    )
    require(
        safe_mapping(updated.get("author_payload_ref")).get("status") == author_payload_ref_status,
        f"{phase_label} {context} must keep author_payload_ref deferred",
    )
    require(
        safe_mapping(updated.get(ref_field)) == safe_mapping(record.get(ref_field)),
        f"{phase_label} {context} {ref_label} mismatch",
    )


def validate_packet_projection_base(packet, authority, u1_state, context_label, author_payload_ref_status, author_input_refs_status, packet_authority_ref_mismatch_message, u1_ref_mismatch_message) -> tuple[dict[str, Any], dict[str, Any]]:
    legacy_payload_ref = safe_mapping(packet.get("author_payload_ref"))
    authority_payload_ref = safe_mapping(authority.get("author_payload_ref"))
    author_input_refs = safe_mapping(packet.get("author_input_refs"))
    require(packet.get("owner") == "RunKernel.FinalAnswerPacket", f"{context_label} packet owner")
    require(packet.get("canonical_state") is True, f"{context_label} packet canonical")
    require(packet.get("readiness_status") == "blocked", f"{context_label} packet must be blocked")
    require(packet.get("final_answer_allowed") is False, f"{context_label} final answer closed")
    require(packet.get("answer_ready") is False, f"{context_label} answer not ready")
    require(authority.get("canonical_state") is True, f"{context_label} authority canonical")
    require(
        legacy_payload_ref.get("status") == author_payload_ref_status,
        f"{context_label} requires deferred author_payload_ref",
    )
    require(legacy_payload_ref.get("status") != "author_input_ready", f"{context_label} rejects ready ref")
    require(legacy_payload_ref == authority_payload_ref, packet_authority_ref_mismatch_message)
    require(legacy_payload_ref == safe_mapping(u1_state.get("author_payload_ref")), u1_ref_mismatch_message)
    require(
        author_input_refs.get("status") == author_input_refs_status,
        f"{context_label} requires U1 author_input_refs",
    )
    return legacy_payload_ref, author_input_refs


def validate_packet_authority_currentness(packet, authority, source_state, packet_digest_field, authority_digest_field, packet_message, authority_message) -> None:
    require(projection_digest(packet) == source_state.get(packet_digest_field), packet_message)
    require(projection_digest(authority) == source_state.get(authority_digest_field), authority_message)


def validate_no_existing_prefixed_fields(packet, authority, fields, prefix, packet_message, authority_message) -> None:
    for key in fields:
        if key.startswith(prefix):
            require(not packet.get(key), packet_message)
            require(not authority.get(key), authority_message)


def validate_expected_action_fields(action, expected, fields, context_label) -> None:
    for key in fields:
        require(action.get(key) == expected.get(key), f"{context_label} action {key} mismatch")
