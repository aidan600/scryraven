"""Reusable deterministic corpus for sparse SearchPlanner Phase-1 semantics."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

VALID_SPARSE_PLANNER_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "minimal_direct_simple",
        "query": "What is the capital of France?",
        "mode": "Balanced",
        "proposal": {"disposition": "direct_simple"},
    },
    {
        "case_id": "official_source_direct_simple",
        "query": "official Python math.isclose default values",
        "mode": "Balanced",
        "proposal": {
            "disposition": "direct_simple",
            "source": {"kind": "canonical_documentation"},
        },
    },
    {
        "case_id": "freshness_direct_simple",
        "query": "What is the current Northstar filing deadline?",
        "mode": "Balanced",
        "proposal": {
            "disposition": "direct_simple",
            "freshness": "current as of 2026-08-11",
        },
    },
    {
        "case_id": "two_direct_components",
        "query": ("Using the fictional Northstar certificate and registry records, report both current facts."),
        "mode": "Balanced",
        "proposal": {
            "disposition": "components",
            "components": [
                {"key": "certificate", "need": "Report the current certificate status"},
                {"key": "registry", "need": "Report the current registry designation"},
            ],
        },
    },
    {
        "case_id": "supporting_premise_and_inferred_target",
        "query": "Determine the filing route from the signed dispatch premise.",
        "mode": "Deep",
        "proposal": {
            "disposition": "components",
            "components": [
                {
                    "key": "premise",
                    "need": "Establish the signed dispatch premise",
                    "purpose": "supporting_premise",
                    "source": {"kind": "official_current", "strictness": "required"},
                },
                {
                    "key": "target",
                    "need": "Determine the filing route",
                    "support": "inferred",
                    "depends_on": ["premise"],
                },
            ],
        },
    },
    {
        "case_id": "factual_identity_uncertainty",
        "query": "recent Galloway controversy",
        "mode": "Balanced",
        "proposal": {
            "disposition": "components",
            "components": [
                {
                    "key": "subject",
                    "need": "Identify the current controversy and the relevant Galloway",
                    "freshness": "recent and current",
                    "uncertainties": [
                        {
                            "kind": "entity",
                            "status": "unresolved",
                            "candidates": ["Scott Galloway", "George Galloway"],
                        }
                    ],
                }
            ],
        },
    },
    {
        "case_id": "resolved_identity_alias",
        "query": "Use the current Northstar identity, also known as Meridian.",
        "mode": "Balanced",
        "proposal": {
            "disposition": "components",
            "components": [
                {
                    "need": "Report the current Northstar identity",
                    "uncertainties": [
                        {
                            "kind": "entity",
                            "status": "explicit",
                            "candidates": ["Northstar", "Meridian"],
                            "selected": "Northstar",
                        }
                    ],
                }
            ],
        },
    },
    {
        "case_id": "true_user_intent_ambiguity",
        "query": "Tell me about Mercury",
        "mode": "Balanced",
        "proposal": {
            "disposition": "components",
            "components": [
                {
                    "key": "mercury",
                    "need": "Explain the intended Mercury subject",
                    "uncertainties": [
                        {
                            "kind": "entity",
                            "status": "ambiguous",
                            "candidates": ["planet", "element", "automobile brand"],
                            "user_confirmation_required": True,
                        }
                    ],
                }
            ],
        },
    },
    {
        "case_id": "nonstandard_processing_semantics",
        "query": "Calculate and normalize the fictional per-passenger-mile posture.",
        "mode": "Deep",
        "proposal": {
            "disposition": "components",
            "components": [
                {
                    "need": "Determine the per-passenger-mile posture",
                    "normalization": "Normalize both records to passenger-miles",
                    "calculation": "Combine the two accepted expense records",
                }
            ],
        },
    },
)


INVALID_SPARSE_PLANNER_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "missing_disposition", "proposal": {}, "expected_subtype": "type_enum_or_bound"},
    {
        "case_id": "unknown_disposition",
        "proposal": {"disposition": "other"},
        "expected_subtype": "type_enum_or_bound",
    },
    {
        "case_id": "direct_simple_plus_components",
        "proposal": {"disposition": "direct_simple", "components": [{"need": "x"}]},
        "expected_subtype": "branch_field_set",
    },
    {
        "case_id": "direct_simple_plus_dependency",
        "proposal": {"disposition": "direct_simple", "depends_on": ["x"]},
        "expected_subtype": "branch_field_set",
    },
    {
        "case_id": "direct_simple_plus_inference",
        "proposal": {"disposition": "direct_simple", "support": "inferred"},
        "expected_subtype": "branch_field_set",
    },
    {
        "case_id": "direct_simple_plus_uncertainty",
        "proposal": {
            "disposition": "direct_simple",
            "uncertainties": [{"kind": "entity", "status": "unresolved"}],
        },
        "expected_subtype": "branch_field_set",
    },
    {
        "case_id": "direct_simple_plus_calculation",
        "proposal": {"disposition": "direct_simple", "calculation": "add values"},
        "expected_subtype": "branch_field_set",
    },
    {
        "case_id": "old_rich_administrative_output",
        "proposal": {"question_meaning_summary": "old", "answer_components": []},
        "expected_subtype": "forbidden_surface",
    },
    {
        "case_id": "model_runtime_identity",
        "proposal": {
            "disposition": "components",
            "components": [{"need": "x", "component_id": "component:01"}],
        },
        "expected_subtype": "forbidden_surface",
    },
    {
        "case_id": "provider_selection",
        "proposal": {
            "disposition": "components",
            "components": [{"need": "x", "provider": "ExampleProvider"}],
        },
        "expected_subtype": "forbidden_surface",
    },
    {
        "case_id": "unsafe_private_material",
        "proposal": {
            "disposition": "components",
            "components": [{"need": "x", "raw_prompt": "private"}],
        },
        "expected_subtype": "forbidden_surface",
    },
    {
        "case_id": "inferred_without_dependency",
        "proposal": {
            "disposition": "components",
            "components": [{"need": "infer x", "support": "inferred"}],
        },
        "expected_subtype": "cross_field_condition",
    },
    {
        "case_id": "components_plus_top_level_source",
        "proposal": {
            "disposition": "components",
            "source": {"kind": "official_current"},
            "components": [{"need": "x"}],
        },
        "expected_subtype": "branch_field_set",
    },
    {
        "case_id": "empty_optional_freshness",
        "proposal": {"disposition": "direct_simple", "freshness": ""},
        "expected_subtype": "omission_contract",
    },
    {
        "case_id": "empty_components_array",
        "proposal": {"disposition": "components", "components": []},
        "expected_subtype": "branch_field_set",
    },
    {
        "case_id": "empty_uncertainties_array",
        "proposal": {
            "disposition": "components",
            "components": [{"need": "x", "uncertainties": []}],
        },
        "expected_subtype": "omission_contract",
    },
)


def valid_case(case_id: str) -> dict[str, Any]:
    return deepcopy(next(case for case in VALID_SPARSE_PLANNER_CASES if case["case_id"] == case_id))


__all__ = [
    "INVALID_SPARSE_PLANNER_CASES",
    "VALID_SPARSE_PLANNER_CASES",
    "valid_case",
]
