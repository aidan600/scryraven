"""Deterministic D-prime negative-control profile registry.

The profile is validation configuration for future model-reviewed D-prime
assessment work. It is not evidence, not semantic support, not a model result,
and not a RunKernel support admission decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Any, Mapping, Sequence

DPRIME_NEGATIVE_CONTROL_PROFILE_SCHEMA_VERSION = (
    "dprime_negative_control_profile_v1"
)
DPRIME_NEGATIVE_CONTROL_PROFILE_PHASE = "DPRIME-NEGATIVE-CONTROL-PROFILE-01"
DPRIME_NEGATIVE_CONTROL_PROFILE_ID = (
    "dprime-negative-control-profile:official-current-retained-lane:v1"
)
DPRIME_NEGATIVE_CONTROL_PROFILE_QUERY_CLASS = "official_current_fact_lookup"
DPRIME_NEGATIVE_CONTROL_PROFILE_RETAINED_LANE = (
    "retained-official-current-single-relation-lane"
)
DPRIME_NEGATIVE_CONTROL_PROFILE_INTEGRATION_DEADLINE = (
    "before D-prime model-reviewed assessment work"
)
DPRIME_NEGATIVE_CONTROL_PROFILE_FAIL_CLOSED_POLICY = (
    "missing, weak, support-like, or mismatched mandatory controls fail closed "
    "and block validation before model review"
)

NEGATIVE_CONTROL_PROFILE_STATUS_AVAILABLE = "available"
NEGATIVE_CONTROL_PROFILE_STATUS_FAILED = "failed"
NEGATIVE_CONTROL_PROFILE_STATUS_MISSING = "missing"

MANDATORY_CONTROL_IDS = (
    "same_lane_unrelated_official_text_no_support",
    "custody_lineage_bounded_content_alone_no_support",
    "correct_source_wrong_component_no_support",
    "correct_value_wrong_effective_date_currentness_no_direct_current_support",
    "correct_topic_missing_answer_bearing_proposition_abstain",
    "contradictory_source_text_challenge_not_weak_support",
    "model_rationale_without_selector_proposition_component_mapping_reject",
    "preflight_pass_plus_model_abstention_fail_closed",
    "model_yes_plus_absent_or_failed_preflight_fail_closed",
    "manual_reviewer_assertion_only_reject",
    "structured_extractor_unrecognized_free_text_abstain",
    "llm_generated_preflight_not_deterministic_preflight",
)

FAIL_CLOSED_EXPECTED_OUTCOMES = frozenset(
    {
        "reject",
        "abstain",
        "challenge_recommended",
        "block_validation",
        "fail_closed",
        "not_support",
    }
)
_SUPPORT_LIKE_OR_VAGUE_OUTCOMES = frozenset(
    {
        "accept",
        "admit",
        "allowed",
        "handled",
        "maybe_support",
        "pass",
        "pass_validation",
        "passed",
        "support",
        "supported",
        "weak_support",
    }
)
_MANDATORY_CLOSED_SURFACE_FLAG_KEYS = (
    "model_review_licensed",
    "assessment_created",
    "validated_support_proposal_created",
    "run_kernel_support_admission_request_created",
    "semantic_observation_created",
    "component_coverage_bound",
    "citation_eligibility_claimed",
    "source_obligation_satisfaction_claimed",
    "answer_text_created",
    "product_correctness_claimed",
)
_DEFAULT_CLOSED_SURFACE_FLAGS = {
    key: False for key in _MANDATORY_CLOSED_SURFACE_FLAG_KEYS
}
_CONTROL_STATUS_OWNER = "deterministic_negative_control_profile_validator"
_CONTROL_PHASE_REQUIRED_BEFORE = "DPRIME-MODEL-REVIEW-01"
_DEFAULT_CLOSED_SURFACES = (
    "model review",
    "EvidenceRelativeSupportAssessment",
    "ValidatedSupportProposal",
    "RunKernel support admission",
    "SemanticObservation",
    "ComponentCoverage",
    "citation eligibility",
    "source-obligation satisfaction",
    "answer text",
    "product correctness",
)

_DEFAULT_CONTROL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "control_id": "same_lane_unrelated_official_text_no_support",
        "purpose": (
            "Ensure same-lane official but answer-unrelated bounded text cannot "
            "support the component."
        ),
        "risk_prevented": "lane, URL, or source-class laundering into support",
        "input_shape_or_fixture_kind": "same_lane_unrelated_official_bounded_text",
        "expected_outcome": "not_support",
    },
    {
        "control_id": "custody_lineage_bounded_content_alone_no_support",
        "purpose": "Ensure custody, lineage, and bounded content are not support.",
        "risk_prevented": "custody metadata becoming semantic support",
        "input_shape_or_fixture_kind": "custody_lineage_only_retained_content",
        "expected_outcome": "not_support",
    },
    {
        "control_id": "correct_source_wrong_component_no_support",
        "purpose": "Reject support when the source is valid but maps to a different component.",
        "risk_prevented": "cross-component support leakage",
        "input_shape_or_fixture_kind": "official_source_wrong_component_mapping",
        "expected_outcome": "reject",
    },
    {
        "control_id": (
            "correct_value_wrong_effective_date_currentness_no_direct_current_support"
        ),
        "purpose": (
            "Require a currentness challenge when a value is correct for the "
            "wrong effective date."
        ),
        "risk_prevented": "stale value accepted as direct current support",
        "input_shape_or_fixture_kind": "correct_value_wrong_effective_date",
        "expected_outcome": "challenge_recommended",
    },
    {
        "control_id": "correct_topic_missing_answer_bearing_proposition_abstain",
        "purpose": "Abstain when topic fit exists but the answer-bearing proposition is absent.",
        "risk_prevented": "topic match treated as proposition support",
        "input_shape_or_fixture_kind": "topic_match_without_answer_proposition",
        "expected_outcome": "abstain",
    },
    {
        "control_id": "contradictory_source_text_challenge_not_weak_support",
        "purpose": "Treat contradiction as a challenge, never weak support.",
        "risk_prevented": "contradictory evidence softened into support",
        "input_shape_or_fixture_kind": "contradictory_source_text",
        "expected_outcome": "challenge_recommended",
    },
    {
        "control_id": (
            "model_rationale_without_selector_proposition_component_mapping_reject"
        ),
        "purpose": (
            "Reject model rationale that lacks selector, proposition, and "
            "component mapping."
        ),
        "risk_prevented": "free-form rationale replacing structured validation",
        "input_shape_or_fixture_kind": "model_rationale_missing_required_mapping",
        "expected_outcome": "reject",
    },
    {
        "control_id": "preflight_pass_plus_model_abstention_fail_closed",
        "purpose": "Fail closed when preflight passes but future model review abstains.",
        "risk_prevented": "abstention treated as support or readiness",
        "input_shape_or_fixture_kind": "preflight_pass_model_abstention",
        "expected_outcome": "fail_closed",
    },
    {
        "control_id": "model_yes_plus_absent_or_failed_preflight_fail_closed",
        "purpose": "Fail closed when model yes appears without passed deterministic preflight.",
        "risk_prevented": "model assertion bypassing deterministic preflight",
        "input_shape_or_fixture_kind": "model_yes_missing_or_failed_preflight",
        "expected_outcome": "fail_closed",
    },
    {
        "control_id": "manual_reviewer_assertion_only_reject",
        "purpose": "Reject manual assertion without required structured support material.",
        "risk_prevented": "human assertion becoming support authority",
        "input_shape_or_fixture_kind": "manual_reviewer_assertion_only",
        "expected_outcome": "reject",
    },
    {
        "control_id": "structured_extractor_unrecognized_free_text_abstain",
        "purpose": "Abstain on unrecognized free text from a structured extractor.",
        "risk_prevented": "unparsed extractor text treated as validation",
        "input_shape_or_fixture_kind": "unrecognized_extractor_free_text",
        "expected_outcome": "abstain",
    },
    {
        "control_id": "llm_generated_preflight_not_deterministic_preflight",
        "purpose": "Block validation when preflight is generated by an LLM.",
        "risk_prevented": "nondeterministic preflight replacing deterministic gate",
        "input_shape_or_fixture_kind": "llm_generated_preflight",
        "expected_outcome": "block_validation",
    },
)


class DPrimeNegativeControlProfileError(ValueError):
    """Raised when profile construction attempts a forbidden upgrade."""


@dataclass(frozen=True, slots=True)
class NegativeControl:
    """One mandatory future validator challenge in the profile registry."""

    control_id: str
    purpose: str
    risk_prevented: str
    input_shape_or_fixture_kind: str
    expected_outcome: str
    status_owner: str = _CONTROL_STATUS_OWNER
    phase_required_before: str = _CONTROL_PHASE_REQUIRED_BEFORE
    closed_surfaces: Sequence[str] = field(default_factory=lambda: _DEFAULT_CLOSED_SURFACES)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> NegativeControl:
        safe = _safe_mapping(payload)
        return cls(
            control_id=_clean_text(safe.get("control_id"), limit=160) or "",
            purpose=_clean_text(safe.get("purpose"), limit=500) or "",
            risk_prevented=_clean_text(safe.get("risk_prevented"), limit=500) or "",
            input_shape_or_fixture_kind=(
                _clean_text(safe.get("input_shape_or_fixture_kind"), limit=260)
                or ""
            ),
            expected_outcome=_clean_text(safe.get("expected_outcome"), limit=160)
            or "",
            status_owner=_clean_text(safe.get("status_owner"), limit=160)
            or _CONTROL_STATUS_OWNER,
            phase_required_before=(
                _clean_text(safe.get("phase_required_before"), limit=160)
                or _CONTROL_PHASE_REQUIRED_BEFORE
            ),
            closed_surfaces=_text_tuple(safe.get("closed_surfaces"), limit=160),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "purpose": self.purpose,
            "risk_prevented": self.risk_prevented,
            "input_shape_or_fixture_kind": self.input_shape_or_fixture_kind,
            "expected_outcome": self.expected_outcome,
            "status_owner": self.status_owner,
            "phase_required_before": self.phase_required_before,
            "closed_surfaces": list(_text_tuple(self.closed_surfaces, limit=160)),
        }


@dataclass(frozen=True, slots=True)
class NegativeControlProfile:
    """Complete deterministic negative-control profile, not support."""

    profile_id: str
    profile_digest: str
    phase: str
    query_class: str
    retained_lane: str
    required_control_ids: Sequence[str]
    expected_outcomes: Mapping[str, str]
    fail_closed_policy: str
    integration_deadline: str
    closed_surface_flags: Mapping[str, bool]
    controls: Sequence[NegativeControl] = field(default_factory=tuple)
    product_correctness_claimed: bool = False
    model_success_claimed: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.product_correctness_claimed is not False:
            raise DPrimeNegativeControlProfileError(
                "NegativeControlProfile cannot claim product correctness"
            )
        if self.model_success_claimed is not False:
            raise DPrimeNegativeControlProfileError(
                "NegativeControlProfile cannot claim model success"
            )
        _reject_forbidden_payload(
            self.metadata,
            context="NegativeControlProfile.metadata",
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> NegativeControlProfile:
        safe = _safe_mapping(payload)
        return cls(
            profile_id=_clean_text(safe.get("profile_id"), limit=260) or "",
            profile_digest=_clean_text(safe.get("profile_digest"), limit=128) or "",
            phase=_clean_text(safe.get("phase"), limit=160) or "",
            query_class=_clean_text(safe.get("query_class"), limit=160) or "",
            retained_lane=_clean_text(safe.get("retained_lane"), limit=260) or "",
            required_control_ids=_text_tuple(
                safe.get("required_control_ids"),
                limit=200,
            ),
            expected_outcomes=_string_mapping(safe.get("expected_outcomes")),
            fail_closed_policy=(
                _clean_text(safe.get("fail_closed_policy"), limit=500) or ""
            ),
            integration_deadline=(
                _clean_text(safe.get("integration_deadline"), limit=260) or ""
            ),
            closed_surface_flags=_safe_mapping(safe.get("closed_surface_flags")),
            controls=tuple(
                NegativeControl.from_mapping(item)
                for item in _safe_sequence(safe.get("controls"))
                if isinstance(item, Mapping)
            ),
            product_correctness_claimed=(
                safe.get("product_correctness_claimed") is True
            ),
            model_success_claimed=safe.get("model_success_claimed") is True,
            metadata=_safe_mapping(safe.get("metadata")),
        )

    def to_dict(
        self,
        *,
        include_controls: bool = True,
        include_profile_digest: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": DPRIME_NEGATIVE_CONTROL_PROFILE_SCHEMA_VERSION,
            "record_kind": "NegativeControlProfile",
            "profile_id": self.profile_id,
            "phase": self.phase,
            "query_class": self.query_class,
            "retained_lane": self.retained_lane,
            "required_control_ids": list(
                _text_tuple(self.required_control_ids, limit=200)
            ),
            "expected_outcomes": dict(self.expected_outcomes),
            "fail_closed_policy": self.fail_closed_policy,
            "integration_deadline": self.integration_deadline,
            "closed_surface_flags": dict(self.closed_surface_flags),
            "product_correctness_claimed": False,
            "model_success_claimed": False,
            "metadata": dict(self.metadata),
        }
        if include_profile_digest:
            payload["profile_digest"] = self.profile_digest
        if include_controls:
            payload["controls"] = [control.to_dict() for control in self.controls]
        return _without_empty(payload)


@dataclass(frozen=True, slots=True)
class NegativeControlProfileValidation:
    """Deterministic profile validation status for product consumption."""

    profile_status: str
    profile_ref: Mapping[str, Any] = field(default_factory=dict)
    blocker_detail: str | None = None
    errors: Sequence[str] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.profile_status == NEGATIVE_CONTROL_PROFILE_STATUS_AVAILABLE

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "profile_status": self.profile_status,
                "profile_ref": dict(self.profile_ref),
                "blocker_detail": self.blocker_detail,
                "errors": list(_text_tuple(self.errors, limit=500)),
            }
        )


def build_default_negative_control_profile() -> NegativeControlProfile:
    """Build the complete default D-prime negative-control profile."""

    controls = tuple(_control_from_definition(item) for item in _DEFAULT_CONTROL_DEFINITIONS)
    return build_negative_control_profile(controls=controls)


def build_negative_control_profile(
    *,
    controls: Sequence[NegativeControl],
    profile_id: str = DPRIME_NEGATIVE_CONTROL_PROFILE_ID,
    phase: str = DPRIME_NEGATIVE_CONTROL_PROFILE_PHASE,
    query_class: str = DPRIME_NEGATIVE_CONTROL_PROFILE_QUERY_CLASS,
    retained_lane: str = DPRIME_NEGATIVE_CONTROL_PROFILE_RETAINED_LANE,
    required_control_ids: Sequence[str] = MANDATORY_CONTROL_IDS,
    fail_closed_policy: str = DPRIME_NEGATIVE_CONTROL_PROFILE_FAIL_CLOSED_POLICY,
    integration_deadline: str = DPRIME_NEGATIVE_CONTROL_PROFILE_INTEGRATION_DEADLINE,
    closed_surface_flags: Mapping[str, bool] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> NegativeControlProfile:
    """Build a profile and assign its stable digest."""

    expected_outcomes = {
        control.control_id: control.expected_outcome for control in controls
    }
    profile = NegativeControlProfile(
        profile_id=profile_id,
        profile_digest="",
        phase=phase,
        query_class=query_class,
        retained_lane=retained_lane,
        required_control_ids=tuple(required_control_ids),
        expected_outcomes=expected_outcomes,
        fail_closed_policy=fail_closed_policy,
        integration_deadline=integration_deadline,
        closed_surface_flags=dict(closed_surface_flags or _DEFAULT_CLOSED_SURFACE_FLAGS),
        controls=tuple(controls),
        metadata=_safe_mapping(metadata),
    )
    return replace(profile, profile_digest=profile_digest(profile))


def validate_negative_control_profile(
    profile: Mapping[str, Any] | NegativeControlProfile | None,
) -> NegativeControlProfileValidation:
    """Validate profile completeness and fail-closed outcomes."""

    if profile is None:
        return NegativeControlProfileValidation(
            profile_status=NEGATIVE_CONTROL_PROFILE_STATUS_MISSING,
            blocker_detail="D-prime negative-control profile is missing",
        )
    try:
        candidate = _coerce_profile(profile)
    except (DPrimeNegativeControlProfileError, TypeError, ValueError) as exc:
        return NegativeControlProfileValidation(
            profile_status=NEGATIVE_CONTROL_PROFILE_STATUS_FAILED,
            blocker_detail=f"D-prime negative-control profile failed validation: {exc}",
            errors=(str(exc),),
        )

    errors = _profile_validation_errors(candidate)
    ref = negative_control_profile_ref(candidate)
    if errors:
        detail = (
            "D-prime negative-control profile failed validation: "
            + "; ".join(errors[:3])
        )
        return NegativeControlProfileValidation(
            profile_status=NEGATIVE_CONTROL_PROFILE_STATUS_FAILED,
            profile_ref=ref,
            blocker_detail=detail,
            errors=tuple(errors),
        )
    return NegativeControlProfileValidation(
        profile_status=NEGATIVE_CONTROL_PROFILE_STATUS_AVAILABLE,
        profile_ref=ref,
    )


def negative_control_profile_ref(
    profile: Mapping[str, Any] | NegativeControlProfile,
) -> dict[str, Any]:
    """Return the CLI-safe profile ref without controls or raw material."""

    candidate = _coerce_profile(profile)
    return _without_empty(
        {
            "profile_id": candidate.profile_id,
            "profile_digest": candidate.profile_digest,
            "phase": candidate.phase,
            "query_class": candidate.query_class,
            "retained_lane": candidate.retained_lane,
            "required_control_count": len(MANDATORY_CONTROL_IDS),
            "control_count": len(candidate.controls),
            "status_owner": _CONTROL_STATUS_OWNER,
        }
    )


def profile_digest(profile: NegativeControlProfile) -> str:
    """Return the stable digest for the safe profile configuration."""

    return _digest_json(profile.to_dict(include_profile_digest=False))


def _profile_validation_errors(profile: NegativeControlProfile) -> list[str]:
    errors: list[str] = []
    payload = profile.to_dict()
    try:
        _reject_forbidden_payload(payload, context="NegativeControlProfile")
    except DPrimeNegativeControlProfileError as exc:
        errors.append(str(exc))

    if profile.profile_id != DPRIME_NEGATIVE_CONTROL_PROFILE_ID:
        errors.append("profile_id does not match the default D-prime profile")
    if profile.phase != DPRIME_NEGATIVE_CONTROL_PROFILE_PHASE:
        errors.append("phase does not match D-prime negative-control phase")
    if not profile.query_class:
        errors.append("query_class is missing")
    if not profile.retained_lane:
        errors.append("retained_lane is missing")
    if not profile.fail_closed_policy or "fail" not in profile.fail_closed_policy:
        errors.append("fail_closed_policy must explicitly fail closed")
    if not profile.integration_deadline:
        errors.append("integration_deadline is missing")

    required_ids = _text_tuple(profile.required_control_ids, limit=200)
    if required_ids != MANDATORY_CONTROL_IDS:
        missing = sorted(set(MANDATORY_CONTROL_IDS) - set(required_ids))
        if missing:
            errors.append("required_control_ids missing mandatory controls: " + ", ".join(missing))
        else:
            errors.append("required_control_ids must match mandatory controls in stable order")

    controls_by_id: dict[str, NegativeControl] = {}
    duplicate_ids: list[str] = []
    for control in profile.controls:
        if control.control_id in controls_by_id:
            duplicate_ids.append(control.control_id)
        controls_by_id[control.control_id] = control
    if duplicate_ids:
        errors.append("duplicate control ids: " + ", ".join(sorted(duplicate_ids)))

    missing_controls = sorted(set(MANDATORY_CONTROL_IDS) - set(controls_by_id))
    if missing_controls:
        errors.append("missing mandatory controls: " + ", ".join(missing_controls))

    unexpected_controls = sorted(set(controls_by_id) - set(MANDATORY_CONTROL_IDS))
    if unexpected_controls:
        errors.append("unexpected controls: " + ", ".join(unexpected_controls))

    expected_outcomes = _string_mapping(profile.expected_outcomes)
    for control_id in MANDATORY_CONTROL_IDS:
        control = controls_by_id.get(control_id)
        declared_outcome = _clean_text(expected_outcomes.get(control_id), limit=160)
        if control is None:
            continue
        errors.extend(_control_validation_errors(control))
        if declared_outcome != control.expected_outcome:
            errors.append(f"{control_id} expected_outcomes mapping mismatch")

    for control_id in sorted(set(expected_outcomes) - set(MANDATORY_CONTROL_IDS)):
        errors.append(f"unexpected expected_outcomes control: {control_id}")

    errors.extend(_closed_surface_flag_errors(profile.closed_surface_flags))

    declared_digest = _clean_text(profile.profile_digest, limit=128)
    expected_digest = profile_digest(profile)
    if not declared_digest:
        errors.append("profile_digest is missing")
    elif declared_digest != expected_digest:
        errors.append("profile_digest mismatch")
    return errors


def _control_validation_errors(control: NegativeControl) -> list[str]:
    errors: list[str] = []
    for field_name, value in (
        ("control_id", control.control_id),
        ("purpose", control.purpose),
        ("risk_prevented", control.risk_prevented),
        ("input_shape_or_fixture_kind", control.input_shape_or_fixture_kind),
        ("expected_outcome", control.expected_outcome),
        ("status_owner", control.status_owner),
        ("phase_required_before", control.phase_required_before),
    ):
        if not _clean_text(value, limit=500):
            errors.append(f"{control.control_id or '<missing>'} {field_name} is missing")

    outcome = _normalize_key(control.expected_outcome)
    if outcome in _SUPPORT_LIKE_OR_VAGUE_OUTCOMES or outcome not in (
        {_normalize_key(item) for item in FAIL_CLOSED_EXPECTED_OUTCOMES}
    ):
        errors.append(
            f"{control.control_id} has non-fail-closed expected_outcome: "
            f"{control.expected_outcome}"
        )
    if control.status_owner != _CONTROL_STATUS_OWNER:
        errors.append(f"{control.control_id} status_owner is not deterministic")
    if control.phase_required_before != _CONTROL_PHASE_REQUIRED_BEFORE:
        errors.append(f"{control.control_id} phase_required_before is not model review")
    if not _text_tuple(control.closed_surfaces, limit=160):
        errors.append(f"{control.control_id} closed_surfaces is missing")
    return errors


def _closed_surface_flag_errors(flags: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    safe = _safe_mapping(flags)
    for key in _MANDATORY_CLOSED_SURFACE_FLAG_KEYS:
        if key not in safe:
            errors.append(f"closed_surface_flags missing {key}")
        elif safe.get(key) is not False:
            errors.append(f"closed_surface_flags must keep {key} false")
    return errors


def _control_from_definition(payload: Mapping[str, Any]) -> NegativeControl:
    return NegativeControl(
        control_id=str(payload["control_id"]),
        purpose=str(payload["purpose"]),
        risk_prevented=str(payload["risk_prevented"]),
        input_shape_or_fixture_kind=str(payload["input_shape_or_fixture_kind"]),
        expected_outcome=str(payload["expected_outcome"]),
    )


def _coerce_profile(
    profile: Mapping[str, Any] | NegativeControlProfile,
) -> NegativeControlProfile:
    if isinstance(profile, NegativeControlProfile):
        return profile
    if hasattr(profile, "to_dict"):
        profile = profile.to_dict()
    if not isinstance(profile, Mapping):
        raise TypeError("D-prime negative-control profile must be a mapping")
    return NegativeControlProfile.from_mapping(profile)


_RAW_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "bounded_text",
        "cache_row",
        "cookie",
        "cookies",
        "db_row",
        "env",
        "full_prompt",
        "full_text",
        "header",
        "headers",
        "html",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_html",
        "raw_model_response",
        "raw_page",
        "raw_page_content",
        "raw_page_text",
        "raw_prompt",
        "raw_provider_payload",
        "raw_search_response",
        "raw_text",
        "secret",
        "secrets",
        "token",
        "unbounded_text",
    }
)
_DANGEROUS_TRUE_KEYS = frozenset(
    {
        "answer_text_created",
        "assessment_created",
        "citation_eligibility_claimed",
        "component_coverage_bound",
        "component_coverage_created",
        "final_answer_packet_created",
        "model_review_licensed",
        "model_success",
        "model_success_claimed",
        "product_correctness",
        "product_correctness_claimed",
        "run_kernel_support_admission_request_created",
        "semantic_observation_created",
        "source_obligation_satisfaction_claimed",
        "validated_support_proposal_created",
    }
)


def _reject_forbidden_payload(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    raw_private = sorted(keys & _RAW_PRIVATE_KEYS)
    if raw_private:
        raise DPrimeNegativeControlProfileError(
            f"{context} includes raw/private fields: " + ", ".join(raw_private)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise DPrimeNegativeControlProfileError(
            f"{context} attempts forbidden authority upgrade: "
            + ", ".join(dangerous)
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(normalized)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _string_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, str] = {}
    for key, item in value.items():
        clean_key = _clean_text(key, limit=200)
        clean_value = _clean_text(item, limit=200)
        if clean_key and clean_value:
            out[clean_key] = clean_value
    return out


def _text_tuple(value: Any, *, limit: int = 160) -> tuple[str, ...]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return (text,) if text else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    return value


__all__ = [
    "DPRIME_NEGATIVE_CONTROL_PROFILE_ID",
    "DPRIME_NEGATIVE_CONTROL_PROFILE_PHASE",
    "DPRIME_NEGATIVE_CONTROL_PROFILE_SCHEMA_VERSION",
    "DPrimeNegativeControlProfileError",
    "FAIL_CLOSED_EXPECTED_OUTCOMES",
    "MANDATORY_CONTROL_IDS",
    "NEGATIVE_CONTROL_PROFILE_STATUS_AVAILABLE",
    "NEGATIVE_CONTROL_PROFILE_STATUS_FAILED",
    "NEGATIVE_CONTROL_PROFILE_STATUS_MISSING",
    "NegativeControl",
    "NegativeControlProfile",
    "NegativeControlProfileValidation",
    "build_default_negative_control_profile",
    "build_negative_control_profile",
    "negative_control_profile_ref",
    "profile_digest",
    "validate_negative_control_profile",
]
