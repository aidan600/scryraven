"""MVP supported-query-class boundary contract.

This module is data/contract only. It does not classify natural-language
queries, plan relations, adjudicate source authority, call providers, or open
the live answer path for arbitrary user input.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

MVP_SUPPORTED_QUERY_CLASS_ID = "mvp-current-source-of-record-single-fact-v1"
MVP_SUPPORTED_QUERY_CLASS_VERSION = "1"
MVP_SUPPORTED_QUERY_CLASS_LABEL = "current source-of-record single-fact lookup"
MVP_SUPPORTED_QUERY_CLASS_NEXT_MILESTONE = "GENERIC-QUERY-TO-RELATION-PLANNING-01"
MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF = (
    "ANALYST-SOURCE-AUTHORITY-POSTURE-PACKET-01"
)

MVP_SUPPORTED_QUERY_CLASS_HARD_EXCLUSIONS = (
    "broad research synthesis",
    "broad product comparison/reliability questions",
    "social/review sentiment as authority",
    "medical, legal, financial, or safety advice",
    "subjective recommendations",
    "private/personal data questions",
    "multi-hop inference or speculative claims",
    "multi-component synthesis",
    "arbitrary query planning or natural-language query classification",
    "questions requiring source-class adapters not yet built",
    "Analyst source-authority posture beyond the simple source-of-record boundary",
    "Scrutineer expansion",
    "Author/FAP redesign",
)

MVP_SUPPORTED_QUERY_CLASS_FUTURE_ROADMAP = (
    "ANALYST-SOURCE-AUTHORITY-POSTURE-PACKET-01",
    "COMPONENT-MODEL-ROLE-ROUTING-MATRIX-01",
    "FAP-OUTPUT-INSPECTION-AND-RENDERING-CONTRACT-01",
)

MVP_SUPPORTED_QUERY_CLASS_EXPLICIT_NONCLAIMS = (
    "arbitrary query answering",
    "arbitrary query planning",
    "natural-language query classification",
    "query-to-relation planning",
    "friend-level MVP readiness",
    "general supported-query MVP readiness",
    "product correctness",
    "source-authority adjudication beyond source-of-record expectation",
    "social/review evidence analysis",
    "broad product comparison or reliability analysis",
)

MVP_SUPPORTED_QUERY_CLASS_PROFILE = {
    "profile_id": MVP_SUPPORTED_QUERY_CLASS_ID,
    "profile_version": MVP_SUPPORTED_QUERY_CLASS_VERSION,
    "short_label": MVP_SUPPORTED_QUERY_CLASS_LABEL,
    "human_description": (
        "A current public factual lookup with one answer component, a "
        "source-of-record or official/primary source expectation, and a compact "
        "answer that can be traced to source-bound evidence."
    ),
    "supported_query_shape": [
        "asks for one current factual value, status, requirement, deadline, or fee",
        "expects a public source-of-record, official, primary, or authority-bearing source",
        "has one answer component or can be safely reduced to one answer component by a later planner",
        "requires source display and caveat/nonclaim output",
        "does not require broad synthesis, advice, personal data, or multi-hop interpretation",
    ],
    "required_source_obligation_posture": [
        "source-of-record, official, primary, or authority-bearing source expected",
        "source display required when answer-path material is consumed",
        "caveat and nonclaim output required",
        "source-bound evidence trace required before product answer output can claim support",
        "source-authority adjudication remains future work beyond this simple boundary",
    ],
    "answer_shape": [
        "one compact answer component",
        "source display when available",
        "explicit caveats and nonclaims",
        "product correctness remains unclaimed",
    ],
    "hard_exclusions": list(MVP_SUPPORTED_QUERY_CLASS_HARD_EXCLUSIONS),
    "open_future_dependencies": [
        MVP_SUPPORTED_QUERY_CLASS_NEXT_MILESTONE,
        *MVP_SUPPORTED_QUERY_CLASS_FUTURE_ROADMAP,
    ],
    "source_authority_posture_contract_ref": (
        MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF
    ),
    "source_authority_posture_contract_role": (
        "Analyst-owned posture contract for future query-to-relation planning; "
        "not consumed by the current fixed-query boundary."
    ),
    "explicit_nonclaims": list(MVP_SUPPORTED_QUERY_CLASS_EXPLICIT_NONCLAIMS),
    "conceptual_examples": [
        "current adult U.S. passport book renewal fee by mail",
        "current UK passport renewal fee",
        "current filing fee for a specific public office or court",
        "current official deadline or requirement stated by a source-of-record",
    ],
    "canonical_fixed_dogfood_example": {
        "query": "What is the current adult U.S. passport book renewal fee by mail?",
        "example_only": True,
        "architecture_definition": False,
        "posture": (
            "canonical fixed dogfood vector for the class concept, not "
            "arbitrary-query support and not the architecture definition"
        ),
    },
    "next_implementation_phase": MVP_SUPPORTED_QUERY_CLASS_NEXT_MILESTONE,
    "future_roadmap_preserved": list(MVP_SUPPORTED_QUERY_CLASS_FUTURE_ROADMAP),
}

_ALLOWED_BOUNDARY_STATUSES = frozenset(
    {
        "fixed_dogfood_example_only",
        "unsupported_query_blocked_before_boundary_entry",
    }
)
_REQUIRED_FALSE_STATUS_FLAGS = (
    "arbitrary_query_planning_supported",
    "natural_language_query_classifier_supported",
    "query_to_relation_planning_supported",
    "friend_level_mvp_claimed",
    "general_supported_query_mvp_claimed",
    "product_correctness_claimed",
    "source_authority_posture_supported",
    "social_review_authority_supported",
    "broad_product_comparison_supported",
)
_REQUIRED_HARD_EXCLUSION_MARKERS = (
    "social/review sentiment as authority",
    "broad product comparison/reliability questions",
    "medical, legal, financial, or safety advice",
    "arbitrary query planning",
    "multi-component synthesis",
    "private/personal data",
)


def build_mvp_supported_query_class_boundary_profile() -> dict[str, Any]:
    """Return a fresh copy of the supported-query-class boundary profile."""

    return validate_mvp_supported_query_class_boundary_profile(
        deepcopy(MVP_SUPPORTED_QUERY_CLASS_PROFILE)
    )


def validate_mvp_supported_query_class_boundary_profile(
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the durable profile shape and return a plain dict copy."""

    safe = dict(profile)
    if safe.get("profile_id") != MVP_SUPPORTED_QUERY_CLASS_ID:
        raise ValueError("MVP supported-query-class profile id mismatch.")
    if safe.get("profile_version") != MVP_SUPPORTED_QUERY_CLASS_VERSION:
        raise ValueError("MVP supported-query-class profile version mismatch.")
    if safe.get("short_label") != MVP_SUPPORTED_QUERY_CLASS_LABEL:
        raise ValueError("MVP supported-query-class profile label mismatch.")
    if safe.get("next_implementation_phase") != MVP_SUPPORTED_QUERY_CLASS_NEXT_MILESTONE:
        raise ValueError("MVP supported-query-class next phase mismatch.")
    if (
        safe.get("source_authority_posture_contract_ref")
        != MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF
    ):
        raise ValueError(
            "MVP supported-query-class source-authority contract ref mismatch."
        )
    hard_exclusions = _string_list(safe.get("hard_exclusions"))
    _validate_required_hard_exclusions(hard_exclusions)
    canonical = _mapping(safe.get("canonical_fixed_dogfood_example"))
    if canonical.get("example_only") is not True:
        raise ValueError("canonical dogfood example must be example-only.")
    if canonical.get("architecture_definition") is not False:
        raise ValueError("canonical dogfood example must not define architecture.")
    if not _string_list(safe.get("supported_query_shape")):
        raise ValueError("MVP supported-query-class profile needs query shape.")
    if not _string_list(safe.get("required_source_obligation_posture")):
        raise ValueError("MVP supported-query-class profile needs source posture.")
    return deepcopy(safe)


def build_mvp_supported_query_class_boundary_status(
    *,
    status: str = "fixed_dogfood_example_only",
    fixed_query_example: bool = True,
    product_path_slice: str = "fixed_dogfood_slice",
    product_path_consumed: bool | None = None,
) -> dict[str, Any]:
    """Build product-visible status metadata for current MVP dogfood packets."""

    profile = build_mvp_supported_query_class_boundary_profile()
    boundary_status = {
        "profile_id": MVP_SUPPORTED_QUERY_CLASS_ID,
        "profile_version": MVP_SUPPORTED_QUERY_CLASS_VERSION,
        "profile_label": MVP_SUPPORTED_QUERY_CLASS_LABEL,
        "status": status,
        "product_path_slice": str(product_path_slice),
        "product_path_consumed": product_path_consumed,
        "fixed_query_example": fixed_query_example,
        "canonical_fixed_dogfood_example": deepcopy(
            profile["canonical_fixed_dogfood_example"]
        ),
        "supported_query_shape": deepcopy(profile["supported_query_shape"]),
        "required_source_obligation_posture": deepcopy(
            profile["required_source_obligation_posture"]
        ),
        "answer_shape": deepcopy(profile["answer_shape"]),
        "hard_exclusions": deepcopy(profile["hard_exclusions"]),
        "explicit_nonclaims": deepcopy(profile["explicit_nonclaims"]),
        "arbitrary_query_planning_supported": False,
        "natural_language_query_classifier_supported": False,
        "query_to_relation_planning_supported": False,
        "friend_level_mvp_claimed": False,
        "general_supported_query_mvp_claimed": False,
        "product_correctness_claimed": False,
        "source_authority_posture_supported": False,
        "source_authority_posture_contract_ref": (
            MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF
        ),
        "social_review_authority_supported": False,
        "broad_product_comparison_supported": False,
        "next_milestone": MVP_SUPPORTED_QUERY_CLASS_NEXT_MILESTONE,
        "future_roadmap_preserved": deepcopy(
            profile["future_roadmap_preserved"]
        ),
    }
    return validate_mvp_supported_query_class_boundary_status(boundary_status)


def validate_mvp_supported_query_class_boundary_status(
    boundary_status: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate product packet metadata for the supported-query-class boundary."""

    safe = dict(boundary_status)
    if safe.get("profile_id") != MVP_SUPPORTED_QUERY_CLASS_ID:
        raise ValueError("MVP supported-query-class status profile id mismatch.")
    if safe.get("profile_version") != MVP_SUPPORTED_QUERY_CLASS_VERSION:
        raise ValueError("MVP supported-query-class status profile version mismatch.")
    if safe.get("profile_label") != MVP_SUPPORTED_QUERY_CLASS_LABEL:
        raise ValueError("MVP supported-query-class status label mismatch.")
    if safe.get("status") not in _ALLOWED_BOUNDARY_STATUSES:
        raise ValueError("MVP supported-query-class status value is unsupported.")
    if not isinstance(safe.get("fixed_query_example"), bool):
        raise ValueError("MVP supported-query-class fixed_query_example must be bool.")
    for key in _REQUIRED_FALSE_STATUS_FLAGS:
        if safe.get(key) is not False:
            raise ValueError(f"MVP supported-query-class status must keep {key}=false.")
    if safe.get("next_milestone") != MVP_SUPPORTED_QUERY_CLASS_NEXT_MILESTONE:
        raise ValueError("MVP supported-query-class status next milestone mismatch.")
    if (
        safe.get("source_authority_posture_contract_ref")
        != MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF
    ):
        raise ValueError(
            "MVP supported-query-class source-authority contract ref mismatch."
        )
    hard_exclusions = _string_list(safe.get("hard_exclusions"))
    _validate_required_hard_exclusions(hard_exclusions)
    canonical = _mapping(safe.get("canonical_fixed_dogfood_example"))
    if canonical.get("example_only") is not True:
        raise ValueError("status canonical dogfood example must be example-only.")
    if canonical.get("architecture_definition") is not False:
        raise ValueError("status canonical dogfood example must not define architecture.")
    if not str(safe.get("product_path_slice") or "").strip():
        raise ValueError("MVP supported-query-class status needs product_path_slice.")
    return deepcopy(safe)


def _validate_required_hard_exclusions(hard_exclusions: list[str]) -> None:
    joined = "\n".join(hard_exclusions).casefold()
    missing = [
        marker
        for marker in _REQUIRED_HARD_EXCLUSION_MARKERS
        if marker.casefold() not in joined
    ]
    if missing:
        raise ValueError(
            "MVP supported-query-class hard exclusions missing: "
            + ", ".join(missing)
        )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "MVP_SUPPORTED_QUERY_CLASS_EXPLICIT_NONCLAIMS",
    "MVP_SUPPORTED_QUERY_CLASS_FUTURE_ROADMAP",
    "MVP_SUPPORTED_QUERY_CLASS_HARD_EXCLUSIONS",
    "MVP_SUPPORTED_QUERY_CLASS_ID",
    "MVP_SUPPORTED_QUERY_CLASS_LABEL",
    "MVP_SUPPORTED_QUERY_CLASS_NEXT_MILESTONE",
    "MVP_SUPPORTED_QUERY_CLASS_PROFILE",
    "MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF",
    "MVP_SUPPORTED_QUERY_CLASS_VERSION",
    "build_mvp_supported_query_class_boundary_profile",
    "build_mvp_supported_query_class_boundary_status",
    "validate_mvp_supported_query_class_boundary_profile",
    "validate_mvp_supported_query_class_boundary_status",
]
