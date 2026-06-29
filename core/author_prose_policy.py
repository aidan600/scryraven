"""Structured policy knobs for Author prose-only finalization.

The policy is deliberately small and deterministic. It changes prose shape, not
authority posture, and is safe to bind by digest in RunKernel actions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping

AUTHOR_PROSE_POLICY_SCHEMA_VERSION = "author_prose_policy_v1"
AUTHOR_PROSE_POLICY_KIND = "author_prose_policy"


class AuthorProsePolicyError(ValueError):
    """Raised when an Author prose policy cannot be normalized."""


class StyleProfile(str, Enum):
    DIRECT = "direct"
    PLAIN_ENGLISH = "plain_english"
    TECHNICAL = "technical"
    RESEARCH_NOTE = "research_note"
    EXECUTIVE_SUMMARY = "executive_summary"


class FormatProfile(str, Enum):
    PARAGRAPHS = "paragraphs"
    BULLETS = "bullets"
    ANSWER_THEN_EVIDENCE = "answer_then_evidence"
    CAVEATS_AT_END = "caveats_at_end"


class BrevityProfile(str, Enum):
    TERSE = "terse"
    NORMAL = "normal"
    DETAILED = "detailed"


class SourcePassThroughProfile(str, Enum):
    MINIMAL_REFS = "minimal_refs"
    INLINE_SOURCE_REFS = "inline_source_refs"
    EVIDENCE_SUMMARY = "evidence_summary"
    SOURCE_APPENDIX = "source_appendix"


class UncertaintyProfile(str, Enum):
    LOW_FRICTION = "low_friction"
    EXPLICIT_CAVEATS = "explicit_caveats"
    CONSERVATIVE = "conservative"
    CONTESTED_FIRST = "contested_first"


class PartialAnswerProfile(str, Enum):
    ANSWER_SUPPORTED_PARTS_FIRST = "answer_supported_parts_first"
    SEPARATE_SUPPORTED_AND_UNRESOLVED = "separate_supported_and_unresolved"
    UNRESOLVED_FIRST = "unresolved_first"


class BlockedAnswerProfile(str, Enum):
    SHORT_BLOCKED = "short_blocked"
    EXPLAIN_BLOCKER = "explain_blocker"
    EXPLAIN_NEXT_NEEDED_EVIDENCE = "explain_next_needed_evidence"


class CitationDisplayProfile(str, Enum):
    PRESERVE_REQUIREMENTS_ONLY = "preserve_requirements_only"
    SOURCE_REF_PLACEHOLDERS = "source_ref_placeholders"
    CITATION_READY_FUTURE_PHASE = "citation_ready_future_phase"


@dataclass(frozen=True, slots=True)
class AuthorProsePolicy:
    """A digestible set of prose-form knobs for AuthorProseFinalization."""

    mode: str
    style_profile: StyleProfile
    format_profile: FormatProfile
    brevity_profile: BrevityProfile
    source_pass_through_profile: SourcePassThroughProfile
    uncertainty_profile: UncertaintyProfile
    partial_answer_profile: PartialAnswerProfile
    blocked_answer_profile: BlockedAnswerProfile
    citation_display_profile: CitationDisplayProfile

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": AUTHOR_PROSE_POLICY_SCHEMA_VERSION,
            "record_kind": AUTHOR_PROSE_POLICY_KIND,
            "mode": self.mode,
            "style_profile": self.style_profile.value,
            "format_profile": self.format_profile.value,
            "brevity_profile": self.brevity_profile.value,
            "source_pass_through_profile": self.source_pass_through_profile.value,
            "uncertainty_profile": self.uncertainty_profile.value,
            "partial_answer_profile": self.partial_answer_profile.value,
            "blocked_answer_profile": self.blocked_answer_profile.value,
            "citation_display_profile": self.citation_display_profile.value,
        }


def normalize_author_prose_policy(
    policy: AuthorProsePolicy | Mapping[str, Any] | None = None,
    *,
    mode: Any = None,
) -> AuthorProsePolicy:
    """Normalize policy overrides on top of mode-aware defaults."""

    if isinstance(policy, AuthorProsePolicy):
        base = policy.to_dict()
    else:
        base = _safe_mapping(policy)

    clean_mode = _mode_label(mode or base.get("mode") or "Balanced")
    defaults = _defaults_for_mode(clean_mode)
    merged = {**defaults, **base, "mode": clean_mode}
    return AuthorProsePolicy(
        mode=clean_mode,
        style_profile=_enum_value(
            StyleProfile,
            merged.get("style_profile"),
            "style_profile",
        ),
        format_profile=_enum_value(
            FormatProfile,
            merged.get("format_profile"),
            "format_profile",
        ),
        brevity_profile=_enum_value(
            BrevityProfile,
            merged.get("brevity_profile"),
            "brevity_profile",
        ),
        source_pass_through_profile=_enum_value(
            SourcePassThroughProfile,
            merged.get("source_pass_through_profile"),
            "source_pass_through_profile",
        ),
        uncertainty_profile=_enum_value(
            UncertaintyProfile,
            merged.get("uncertainty_profile"),
            "uncertainty_profile",
        ),
        partial_answer_profile=_enum_value(
            PartialAnswerProfile,
            merged.get("partial_answer_profile"),
            "partial_answer_profile",
        ),
        blocked_answer_profile=_enum_value(
            BlockedAnswerProfile,
            merged.get("blocked_answer_profile"),
            "blocked_answer_profile",
        ),
        citation_display_profile=_enum_value(
            CitationDisplayProfile,
            merged.get("citation_display_profile"),
            "citation_display_profile",
        ),
    )


def author_prose_policy_digest(
    policy: AuthorProsePolicy | Mapping[str, Any] | None,
    *,
    mode: Any = None,
) -> str:
    normalized = normalize_author_prose_policy(policy, mode=mode)
    return _digest_json(normalized.to_dict())


def author_prose_policy_ref(
    policy: AuthorProsePolicy | Mapping[str, Any] | None,
    *,
    mode: Any = None,
) -> dict[str, Any]:
    normalized = normalize_author_prose_policy(policy, mode=mode)
    return {
        "policy_kind": AUTHOR_PROSE_POLICY_KIND,
        "schema_version": AUTHOR_PROSE_POLICY_SCHEMA_VERSION,
        "mode": normalized.mode,
        "policy_digest": author_prose_policy_digest(normalized),
        "style_profile": normalized.style_profile.value,
        "format_profile": normalized.format_profile.value,
        "brevity_profile": normalized.brevity_profile.value,
        "source_pass_through_profile": normalized.source_pass_through_profile.value,
        "uncertainty_profile": normalized.uncertainty_profile.value,
        "partial_answer_profile": normalized.partial_answer_profile.value,
        "blocked_answer_profile": normalized.blocked_answer_profile.value,
        "citation_display_profile": normalized.citation_display_profile.value,
    }


def _defaults_for_mode(mode: str) -> dict[str, str]:
    if mode == "Fast":
        return {
            "style_profile": StyleProfile.DIRECT.value,
            "format_profile": FormatProfile.PARAGRAPHS.value,
            "brevity_profile": BrevityProfile.TERSE.value,
            "source_pass_through_profile": SourcePassThroughProfile.MINIMAL_REFS.value,
            "uncertainty_profile": UncertaintyProfile.LOW_FRICTION.value,
            "partial_answer_profile": (
                PartialAnswerProfile.ANSWER_SUPPORTED_PARTS_FIRST.value
            ),
            "blocked_answer_profile": BlockedAnswerProfile.SHORT_BLOCKED.value,
            "citation_display_profile": (
                CitationDisplayProfile.PRESERVE_REQUIREMENTS_ONLY.value
            ),
        }
    if mode == "Deep":
        return {
            "style_profile": StyleProfile.RESEARCH_NOTE.value,
            "format_profile": FormatProfile.CAVEATS_AT_END.value,
            "brevity_profile": BrevityProfile.DETAILED.value,
            "source_pass_through_profile": SourcePassThroughProfile.SOURCE_APPENDIX.value,
            "uncertainty_profile": UncertaintyProfile.CONSERVATIVE.value,
            "partial_answer_profile": (
                PartialAnswerProfile.SEPARATE_SUPPORTED_AND_UNRESOLVED.value
            ),
            "blocked_answer_profile": (
                BlockedAnswerProfile.EXPLAIN_NEXT_NEEDED_EVIDENCE.value
            ),
            "citation_display_profile": (
                CitationDisplayProfile.CITATION_READY_FUTURE_PHASE.value
            ),
        }
    if mode == "Balanced":
        return {
            "style_profile": StyleProfile.PLAIN_ENGLISH.value,
            "format_profile": FormatProfile.ANSWER_THEN_EVIDENCE.value,
            "brevity_profile": BrevityProfile.NORMAL.value,
            "source_pass_through_profile": (
                SourcePassThroughProfile.EVIDENCE_SUMMARY.value
            ),
            "uncertainty_profile": UncertaintyProfile.EXPLICIT_CAVEATS.value,
            "partial_answer_profile": (
                PartialAnswerProfile.SEPARATE_SUPPORTED_AND_UNRESOLVED.value
            ),
            "blocked_answer_profile": BlockedAnswerProfile.EXPLAIN_BLOCKER.value,
            "citation_display_profile": (
                CitationDisplayProfile.SOURCE_REF_PLACEHOLDERS.value
            ),
        }
    raise AuthorProsePolicyError("Author prose policy mode must be Fast, Balanced, or Deep")


def _enum_value(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    token = _normalized_token(value)
    for item in enum_type:
        if _normalized_token(item.value) == token:
            return item
    allowed = ", ".join(item.value for item in enum_type)
    raise AuthorProsePolicyError(
        f"unsupported AuthorProsePolicy {field_name}: {value!r}; allowed: {allowed}"
    )


def _mode_label(value: Any) -> str:
    token = _normalized_token(value)
    labels = {
        "fast": "Fast",
        "balanced": "Balanced",
        "deep": "Deep",
    }
    label = labels.get(token)
    if not label:
        raise AuthorProsePolicyError("Author prose policy mode must be Fast, Balanced, or Deep")
    return label


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): item.value if isinstance(item, Enum) else item
        for key, item in value.items()
    }


def _normalized_token(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    return text.casefold().replace("-", "_").replace(" ", "_")


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "AUTHOR_PROSE_POLICY_KIND",
    "AUTHOR_PROSE_POLICY_SCHEMA_VERSION",
    "AuthorProsePolicy",
    "AuthorProsePolicyError",
    "BlockedAnswerProfile",
    "BrevityProfile",
    "CitationDisplayProfile",
    "FormatProfile",
    "PartialAnswerProfile",
    "SourcePassThroughProfile",
    "StyleProfile",
    "UncertaintyProfile",
    "author_prose_policy_digest",
    "author_prose_policy_ref",
    "normalize_author_prose_policy",
]
