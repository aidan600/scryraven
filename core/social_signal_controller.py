"""Pure offline controller adapter for social-signal checks."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from core.social_signal_schema import (
    AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL,
    SocialSignalPacket,
    build_author_safe_social_signal_digest,
    validate_social_signal_packet,
)

SOCIAL_SIGNAL_ACTION_NAME = "request_social_signal_check"
SOCIAL_SIGNAL_EVIDENCE_CLASS = "social_signal_perception"

ANSWER_CONTRACT_SOCIAL_STATUSES = frozenset(
    {
        "checked",
        "not_applicable",
        "provider_unavailable",
        "invalid_packet",
        "blocked",
    }
)


class SocialSignalRelevance(str, Enum):
    """Answer-contract-compatible social-signal relevance values."""

    IRRELEVANT = "irrelevant"
    RELEVANT_OPTIONAL = "relevant_optional"
    CENTRAL = "central"


class SocialSignalControllerStatus(str, Enum):
    """Stable passive adapter outcomes."""

    CHECKED = "checked"
    NOT_APPLICABLE = "not_applicable"
    NOT_REQUESTED = "not_requested"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_PACKET = "invalid_packet"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class SocialSignalControllerInput:
    """Passive controller facts for deciding a social-signal check."""

    query: str
    mode: str = "Balanced"
    social_signal_relevance: SocialSignalRelevance | str | None = SocialSignalRelevance.IRRELEVANT
    explicit_social_signal_requested: bool = False
    social_provider_configured: bool = False
    api_enabled: bool = False
    packet_or_none: SocialSignalPacket | Mapping[str, Any] | None = None
    platform_allowlist: Sequence[str] = ()
    platform_denylist: Sequence[str] = ()
    fixture_packets_allowed: bool = True
    raw_storage_allowed: bool = False
    context_reasons: Sequence[str] = ()


@dataclass(frozen=True)
class SocialSignalControllerDecision:
    """Answer-contract-facing decision without runtime side effects."""

    action_name: str
    status: str
    social_signal_status: str
    stable_reason_code: str
    reasons: tuple[str, ...] = ()
    social_signal_summary: str | None = None
    author_digest_or_none: dict[str, Any] | None = None
    packet_valid: bool = False
    side_packet_allowed: bool = False
    evidence_class: str = SOCIAL_SIGNAL_EVIDENCE_CLASS
    sampled_platforms: tuple[str, ...] = ()
    may_support_factual_claims: bool = False
    ordinary_evidence_registry_merge_allowed: bool = False
    raw_packet_to_author_allowed: bool = False
    raw_comments_to_author_allowed: bool = False
    provider_call_allowed: bool = False
    live_api_call_allowed: bool = False
    factual_evidence_sufficiency_changed: bool = False
    official_or_primary_evidence_satisfied: bool = False
    official_source_repair_interaction_allowed: bool = False
    weak_evidence_repair_interaction_allowed: bool = False
    extra: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["author_digest_or_none"] = deepcopy(self.author_digest_or_none)
        data["extra"] = deepcopy(dict(self.extra))
        return data


def decide_social_signal_controller(
    controller_input: SocialSignalControllerInput,
) -> SocialSignalControllerDecision:
    """Return the passive social-signal decision for answer-contract handoff."""

    relevance = _coerce_relevance(controller_input.social_signal_relevance)
    explicit = bool(controller_input.explicit_social_signal_requested)
    packet_supplied = controller_input.packet_or_none is not None
    context_reasons = _copy_string_tuple(controller_input.context_reasons)

    if relevance is SocialSignalRelevance.IRRELEVANT and not explicit:
        return _decision(
            status=SocialSignalControllerStatus.NOT_APPLICABLE.value,
            social_signal_status="not_applicable",
            stable_reason_code="social_relevance_irrelevant",
            reasons=("social_relevance_irrelevant", *context_reasons),
            relevance=relevance,
        )

    if _is_fast_mode(controller_input.mode) and (
        relevance is SocialSignalRelevance.CENTRAL or explicit
    ):
        return _decision(
            status=SocialSignalControllerStatus.BLOCKED.value,
            social_signal_status="blocked",
            stable_reason_code="fast_mode_blocked",
            reasons=("fast_mode_blocked", *context_reasons),
            relevance=relevance,
        )

    if packet_supplied:
        return _decision_from_packet(controller_input, relevance, context_reasons)

    if relevance is SocialSignalRelevance.RELEVANT_OPTIONAL and not explicit:
        return _decision(
            status=SocialSignalControllerStatus.NOT_REQUESTED.value,
            social_signal_status="not_applicable",
            stable_reason_code="social_signal_not_requested",
            reasons=("social_signal_not_requested", *context_reasons),
            relevance=relevance,
        )

    if not controller_input.social_provider_configured:
        return _decision(
            status=SocialSignalControllerStatus.PROVIDER_UNAVAILABLE.value,
            social_signal_status="provider_unavailable",
            stable_reason_code="social_provider_not_configured",
            reasons=("social_provider_not_configured", *context_reasons),
            relevance=relevance,
        )

    if not controller_input.api_enabled:
        return _decision(
            status=SocialSignalControllerStatus.BLOCKED.value,
            social_signal_status="blocked",
            stable_reason_code="api_disabled",
            reasons=("api_disabled", *context_reasons),
            relevance=relevance,
        )

    return _decision(
        status=SocialSignalControllerStatus.PROVIDER_UNAVAILABLE.value,
        social_signal_status="provider_unavailable",
        stable_reason_code="social_provider_not_configured",
        reasons=("social_provider_not_configured", *context_reasons),
        relevance=relevance,
    )


def decide_social_signal_check(
    controller_input: SocialSignalControllerInput,
) -> SocialSignalControllerDecision:
    """Compatibility alias for the passive controller action vocabulary."""

    return decide_social_signal_controller(controller_input)


def _decision_from_packet(
    controller_input: SocialSignalControllerInput,
    relevance: SocialSignalRelevance,
    context_reasons: tuple[str, ...],
) -> SocialSignalControllerDecision:
    if not controller_input.fixture_packets_allowed:
        return _decision(
            status=SocialSignalControllerStatus.BLOCKED.value,
            social_signal_status="blocked",
            stable_reason_code="fixture_packet_not_allowed",
            reasons=("fixture_packet_not_allowed", *context_reasons),
            relevance=relevance,
        )

    validation = validate_social_signal_packet(controller_input.packet_or_none)
    if not validation.valid or validation.packet is None:
        reasons = _copy_string_tuple(
            ("packet_validation_failed",)
            + tuple(validation.reasons)
            + tuple(context_reasons)
        )
        return _decision(
            status=SocialSignalControllerStatus.INVALID_PACKET.value,
            social_signal_status="invalid_packet",
            stable_reason_code="packet_validation_failed",
            reasons=reasons,
            relevance=relevance,
            packet_valid=False,
        )

    packet = validation.packet
    sampled_platforms = _copy_string_tuple(packet.platforms_sampled)
    platform_block_reason = _platform_block_reason(
        sampled_platforms,
        allowlist=controller_input.platform_allowlist,
        denylist=controller_input.platform_denylist,
    )
    if platform_block_reason:
        return _decision(
            status=SocialSignalControllerStatus.BLOCKED.value,
            social_signal_status="blocked",
            stable_reason_code="platform_not_allowed",
            reasons=(platform_block_reason, *context_reasons),
            relevance=relevance,
            packet_valid=True,
            sampled_platforms=sampled_platforms,
        )

    if packet.raw_storage_allowed and not controller_input.raw_storage_allowed:
        return _decision(
            status=SocialSignalControllerStatus.BLOCKED.value,
            social_signal_status="blocked",
            stable_reason_code="raw_storage_not_allowed",
            reasons=("raw_storage_not_allowed", *context_reasons),
            relevance=relevance,
            packet_valid=True,
            sampled_platforms=sampled_platforms,
        )

    digest = build_author_safe_social_signal_digest(packet)
    return _decision(
        status=SocialSignalControllerStatus.CHECKED.value,
        social_signal_status="checked",
        stable_reason_code="social_signal_checked",
        reasons=("social_signal_checked", *context_reasons),
        relevance=relevance,
        author_digest_or_none=digest,
        packet_valid=True,
        side_packet_allowed=True,
        sampled_platforms=sampled_platforms,
    )


def _decision(
    *,
    status: str,
    social_signal_status: str,
    stable_reason_code: str,
    reasons: Sequence[str],
    relevance: SocialSignalRelevance,
    author_digest_or_none: Mapping[str, Any] | None = None,
    packet_valid: bool = False,
    side_packet_allowed: bool = False,
    sampled_platforms: Sequence[str] = (),
) -> SocialSignalControllerDecision:
    if social_signal_status not in ANSWER_CONTRACT_SOCIAL_STATUSES:
        raise ValueError(f"Unsupported social_signal_status: {social_signal_status}")
    digest = deepcopy(dict(author_digest_or_none)) if author_digest_or_none else None
    return SocialSignalControllerDecision(
        action_name=SOCIAL_SIGNAL_ACTION_NAME,
        status=status,
        social_signal_status=social_signal_status,
        stable_reason_code=stable_reason_code,
        reasons=_copy_string_tuple(reasons),
        social_signal_summary=_summary(
            relevance=relevance,
            social_signal_status=social_signal_status,
            stable_reason_code=stable_reason_code,
            digest=digest,
        ),
        author_digest_or_none=digest,
        packet_valid=packet_valid,
        side_packet_allowed=side_packet_allowed,
        sampled_platforms=_copy_string_tuple(sampled_platforms),
    )


def _summary(
    *,
    relevance: SocialSignalRelevance,
    social_signal_status: str,
    stable_reason_code: str,
    digest: Mapping[str, Any] | None,
) -> str:
    pieces = [
        f"social_signal_relevance={relevance.value}",
        f"status={social_signal_status}",
        f"reason={stable_reason_code}",
    ]
    if digest:
        pieces.append(f"label={AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL}")
    return "; ".join(pieces)


def _platform_block_reason(
    sampled_platforms: Sequence[str],
    *,
    allowlist: Sequence[str],
    denylist: Sequence[str],
) -> str | None:
    sampled = _normalized_set(sampled_platforms)
    allowed = _normalized_set(allowlist)
    denied = _normalized_set(denylist)
    if denied and sampled & denied:
        return "platform_not_allowed"
    if allowed and not sampled <= allowed:
        return "platform_not_allowed"
    return None


def _coerce_relevance(value: SocialSignalRelevance | str | None) -> SocialSignalRelevance:
    if isinstance(value, SocialSignalRelevance):
        return value
    raw_value = getattr(value, "value", value)
    try:
        return SocialSignalRelevance(
            str(raw_value or SocialSignalRelevance.IRRELEVANT.value).casefold()
        )
    except ValueError:
        return SocialSignalRelevance.IRRELEVANT


def _is_fast_mode(mode: str | None) -> bool:
    return str(mode or "").strip().casefold() == "fast"


def _normalized_set(values: Sequence[str]) -> set[str]:
    return {str(value).strip().casefold() for value in values if str(value).strip()}


def _copy_string_tuple(values: Sequence[Any]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split())
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    return tuple(out)


__all__ = [
    "ANSWER_CONTRACT_SOCIAL_STATUSES",
    "SOCIAL_SIGNAL_ACTION_NAME",
    "SOCIAL_SIGNAL_EVIDENCE_CLASS",
    "SocialSignalControllerDecision",
    "SocialSignalControllerInput",
    "SocialSignalControllerStatus",
    "SocialSignalRelevance",
    "decide_social_signal_check",
    "decide_social_signal_controller",
]
