"""No-live generic supported-query relation planning dry run.

This module consumes the MVP supported-query-class boundary and emits one
deterministic relation-plan packet for conservative single-fact lookups. It does
not answer, search, fetch/read, call models, adjudicate source authority, create
D-prime support, create FAP/Author material, or claim product correctness.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.dprime_analyst_relation_intake_runtime import (
    DPRIME_ANALYST_RELATION_INTAKE_SCHEMA_VERSION,
    DPRIME_ANALYST_RELATION_INTAKE_SURFACE,
)
from core.mvp_supported_query_class_boundary import (
    MVP_SUPPORTED_QUERY_CLASS_ID,
    MVP_SUPPORTED_QUERY_CLASS_LABEL,
    MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF,
    MVP_SUPPORTED_QUERY_CLASS_VERSION,
    build_mvp_supported_query_class_boundary_profile,
)
from core.product_model_route_config import MVP_QUERY_PLAN_STATUS_FLAG
from core.source_authority_posture_packet import (
    SOURCE_AUTHORITY_POSTURE_PHASE,
    SOURCE_AUTHORITY_SOURCE_CLASS_GOVERNMENT_OR_PUBLIC_AGENCY,
    SOURCE_AUTHORITY_SOURCE_CLASS_LEGAL_OR_REGULATORY,
    SOURCE_AUTHORITY_SOURCE_CLASS_OFFICIAL_OR_SOURCE_OF_RECORD,
)

GENERIC_QUERY_TO_RELATION_PLANNING_PHASE = (
    "GENERIC-QUERY-TO-RELATION-PLANNING-01"
)
GENERIC_QUERY_TO_RELATION_PLANNING_SCHEMA_VERSION = (
    "generic_query_to_relation_planning_v1"
)
MVP_QUERY_PLANNING_OUTPUT_DIR = Path("output") / "mvp_query_plan_01"
MVP_QUERY_PLAN_PACKET_NAME = "generic_query_plan_status_packet.json"

PLANNING_STATUS_PLANNED = "planned"
PLANNING_STATUS_BLOCKED = "blocked"
PLANNER_TYPE = "deterministic_conservative_no_model"
PASS_DECISION = "PASS"

BLOCKED_GENERIC_QUERY_PLANNING_UNSUPPORTED_QUERY_CLASS = (
    "BLOCKED_GENERIC_QUERY_PLANNING_UNSUPPORTED_QUERY_CLASS"
)
BLOCKED_GENERIC_QUERY_PLANNING_HARD_EXCLUSION = (
    "BLOCKED_GENERIC_QUERY_PLANNING_HARD_EXCLUSION"
)
BLOCKED_GENERIC_QUERY_PLANNING_MULTI_COMPONENT = (
    "BLOCKED_GENERIC_QUERY_PLANNING_MULTI_COMPONENT"
)
BLOCKED_GENERIC_QUERY_PLANNING_SOURCE_AUTHORITY_CONTRACT_MISSING = (
    "BLOCKED_GENERIC_QUERY_PLANNING_SOURCE_AUTHORITY_CONTRACT_MISSING"
)
BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE = (
    "BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE"
)

SOURCE_AUTHORITY_POSTURE_REQUIREMENT_ID = (
    "source-authority-posture-requirement:single-source-of-record-fact"
)
RAW_PRIVATE_RETENTION_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_source_content_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}
CLOSED_SURFACE_FLAGS = {
    "answer_created": False,
    "evidence_acquired": False,
    "live_calls_made": False,
    "provider_call_made": False,
    "search_call_made": False,
    "fetch_read_call_made": False,
    "model_calls_made": False,
    "source_authority_adjudicated": False,
    "source_authority_posture_created": False,
    "source_class_adapter_implemented": False,
    "social_review_analysis_opened": False,
    "multi_component_planning_opened": False,
    "runkernel_dag_scheduling_opened": False,
    "budget_lease_created": False,
    "dprime_live_review_opened": False,
    "final_answer_packet_created": False,
    "author_behavior_changed": False,
    "product_correctness_claimed": False,
    "friend_level_mvp_claimed": False,
    "general_supported_query_mvp_claimed": False,
}
EXPLICIT_NONCLAIMS = (
    "no answer is produced",
    "no live provider/search/fetch/read/retrieval call is made",
    "no model call is made",
    "source-authority posture is only a future Analyst-owned requirement by reference",
    "no actual source-authority posture over evidence is created",
    "no source-obligation satisfaction is claimed",
    "no D-prime support, SemanticObservation, ComponentCoverage, FAP, or Author material is created",
    "no multi-component planning, RunKernel DAG scheduling, or budget lease is implemented",
    "product correctness remains unclaimed",
    "ScryRaven is not friend-level MVP or a general supported-query MVP",
)

_FACT_KIND_MARKERS = {
    "fee": (
        "fee",
        "filing fee",
        "renewal fee",
        "cost",
        "price",
        "charge",
    ),
    "deadline": (
        "deadline",
        "due date",
        "filing deadline",
    ),
    "requirement": (
        "requirement",
        "requirements",
        "required",
        "must",
    ),
    "status": (
        "status",
        "availability",
        "open or closed",
    ),
    "current_value": (
        "amount",
        "value",
        "rate",
        "maximum",
        "limit",
        "threshold",
        "wage base",
    ),
}
_CURRENTNESS_MARKERS = (
    "current",
    "currently",
    "latest",
    "today",
    "now",
    "official",
    "effective",
)
_QUESTION_PREFIXES = (
    r"^what\s+is\s+the\s+",
    r"^what\s+is\s+",
    r"^what's\s+the\s+",
    r"^what's\s+",
    r"^how\s+much\s+is\s+the\s+",
    r"^how\s+much\s+is\s+",
    r"^when\s+is\s+the\s+",
    r"^when\s+is\s+",
)
_PRIVATE_VALUE_MARKERS = (
    "api_key",
    "authorization:",
    "bearer ",
    "password",
    "private_sentinel",
    "raw_prompt",
    "raw_provider",
    "secret",
    "sk-",
    "token",
)
_ALLOWED_RAW_PRIVATE_KEYS = frozenset(RAW_PRIVATE_RETENTION_FLAGS) | {
    "raw_private_retention_flags",
}


@dataclass(frozen=True, slots=True)
class GenericQueryPlanningGate:
    """Deterministic conservative gate result for one user-style query."""

    supported: bool
    blocker_code: str | None = None
    blocker_detail: str | None = None
    hard_exclusion_category: str | None = None
    fact_kind: str | None = None


@dataclass(frozen=True, slots=True)
class GenericQueryPlanStatusResult:
    """CLI-safe result for the product-facing query-plan dry run."""

    decision: str
    output: str
    packet: Mapping[str, Any]
    packet_path: Path

    @property
    def return_code(self) -> int:
        return 0 if self.decision == PASS_DECISION else 2


class GenericQueryRelationPlanningError(ValueError):
    """Raised when deterministic planning must fail closed."""

    def __init__(
        self,
        blocker_code: str,
        detail: str,
        *,
        hard_exclusion_category: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.blocker_code = blocker_code
        self.detail = detail
        self.hard_exclusion_category = hard_exclusion_category


def build_generic_query_relation_plan(
    query: str,
) -> dict[str, Any]:
    """Build one conservative relation plan for a supported-class query."""

    sanitized_query = _normalize_query(query)
    gate = _gate_supported_query(sanitized_query)
    if not gate.supported:
        raise GenericQueryRelationPlanningError(
            gate.blocker_code or BLOCKED_GENERIC_QUERY_PLANNING_UNSUPPORTED_QUERY_CLASS,
            gate.blocker_detail
            or "The deterministic gate could not reduce the query into the supported class.",
            hard_exclusion_category=gate.hard_exclusion_category,
        )
    if (
        SOURCE_AUTHORITY_POSTURE_PHASE
        != MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF
    ):
        raise GenericQueryRelationPlanningError(
            BLOCKED_GENERIC_QUERY_PLANNING_SOURCE_AUTHORITY_CONTRACT_MISSING,
            "Supported-query boundary source-authority contract ref is unavailable.",
        )

    profile = build_mvp_supported_query_class_boundary_profile()
    component_text = _component_text(sanitized_query)
    fact_kind = gate.fact_kind or _detect_fact_kind(sanitized_query) or "current_value"
    identity_digest = _digest_json(
        {
            "phase": GENERIC_QUERY_TO_RELATION_PLANNING_PHASE,
            "profile_id": MVP_SUPPORTED_QUERY_CLASS_ID,
            "sanitized_query": sanitized_query,
            "component_text": component_text,
            "fact_kind": fact_kind,
        }
    )
    slug = _slug(component_text)
    plan_id = f"generic-relation-plan:{identity_digest[:20]}"
    component_id = f"component:{slug}:{identity_digest[:12]}"
    source_obligation_id = f"obligation:{slug}:{identity_digest[12:24]}"
    search_requirement_id = f"searchreq:{slug}:{identity_digest[24:36]}"
    claim_under_test = (
        f"Determine the {component_text} from an official/source-of-record source."
    )
    source_obligation_text = (
        f"Find an official or source-of-record source that states the {component_text}."
    )
    search_requirement_text = (
        f"Search for official current source-of-record material for the {component_text}."
    )
    source_authority_requirement = _source_authority_posture_requirement()
    component = {
        "component_id": component_id,
        "component_text": component_text,
        "component_type": "single_source_of_record_fact_lookup",
        "fact_kind": fact_kind,
        "claim_under_test": claim_under_test,
        "source_obligation_ids": [source_obligation_id],
        "search_requirement_ids": [search_requirement_id],
        "source_authority_posture_requirement_ids": [
            SOURCE_AUTHORITY_POSTURE_REQUIREMENT_ID
        ],
        "component_digest": identity_digest,
        "answer_created": False,
        "component_coverage_bound": False,
    }
    source_obligation = {
        "source_obligation_id": source_obligation_id,
        "source_obligation_text": source_obligation_text,
        "expected_source_use_requirement": "authority",
        "source_authority_posture_requirement_id": (
            SOURCE_AUTHORITY_POSTURE_REQUIREMENT_ID
        ),
        "satisfaction_claimed": False,
    }
    search_requirement = {
        "search_requirement_id": search_requirement_id,
        "search_requirement_text": search_requirement_text,
        "search_query_seeds": _search_query_seeds(
            sanitized_query=sanitized_query,
            component_text=component_text,
            fact_kind=fact_kind,
        ),
        "search_dispatched": False,
        "live_calls_made": False,
    }
    packet = {
        "schema_version": GENERIC_QUERY_TO_RELATION_PLANNING_SCHEMA_VERSION,
        "phase_name": GENERIC_QUERY_TO_RELATION_PLANNING_PHASE,
        "mode": "BUILD",
        "planning_status": PLANNING_STATUS_PLANNED,
        "decision": PASS_DECISION,
        "planner_type": PLANNER_TYPE,
        "ordinary_entrypoint": "python -m proplex",
        "status_flag": MVP_QUERY_PLAN_STATUS_FLAG,
        "runtime_consumer": (
            "core.generic_query_to_relation_planning.build_generic_query_plan_status_output"
        ),
        "packet_id": f"generic-query-plan-packet:{identity_digest[:20]}",
        "plan_id": plan_id,
        "sanitized_query": sanitized_query,
        "query_retained": True,
        "unsupported_query_retained": False,
        "supported_query_class_id": MVP_SUPPORTED_QUERY_CLASS_ID,
        "supported_query_class_boundary": _boundary_metadata(profile),
        "source_authority_posture_contract_ref": SOURCE_AUTHORITY_POSTURE_PHASE,
        "source_authority_posture_requirement": source_authority_requirement,
        "actual_source_authority_posture_created": False,
        "actual_source_authority_posture_required_later": True,
        "answer_created": False,
        "live_calls_made": False,
        "model_calls_made": False,
        "product_correctness_claimed": False,
        "friend_level_mvp_claimed": False,
        "general_supported_query_mvp_claimed": False,
        "component_count": 1,
        "component_id": component_id,
        "component_text": component_text,
        "fact_kind": fact_kind,
        "claim_under_test": claim_under_test,
        "components": [component],
        "source_obligation_count": 1,
        "source_obligation_id": source_obligation_id,
        "source_obligation_text": source_obligation_text,
        "source_obligations": [source_obligation],
        "search_requirement_count": 1,
        "search_requirement_id": search_requirement_id,
        "search_requirement_text": search_requirement_text,
        "search_requirements": [search_requirement],
        "search_query_seeds": list(search_requirement["search_query_seeds"]),
        "dprime_relation_intake_candidate": _dprime_relation_intake_candidate(
            component_id=component_id,
            component_text=component_text,
            claim_under_test=claim_under_test,
            source_obligation_id=source_obligation_id,
            source_obligation_text=source_obligation_text,
            search_requirement_id=search_requirement_id,
            search_requirement_text=search_requirement_text,
            source_authority_requirement=source_authority_requirement,
            relation_plan_id=plan_id,
        ),
        "future_component_work_node_candidate": _future_component_work_node_candidate(
            node_digest=identity_digest,
            parent_plan_id=plan_id,
            component_id=component_id,
            search_requirement_id=search_requirement_id,
            source_obligation_id=source_obligation_id,
        ),
        "caveats": [
            "Planning is deterministic and conservative.",
            "Unsupported or ambiguous queries fail closed before relation planning.",
            "The packet is planning metadata only; no evidence has been acquired.",
        ],
        "explicit_nonclaims": list(EXPLICIT_NONCLAIMS),
        "raw_private_retention_flags": dict(RAW_PRIVATE_RETENTION_FLAGS),
        "closed_surface_flags": dict(CLOSED_SURFACE_FLAGS),
    }
    packet["packet_digest"] = _digest_json(packet)
    return validate_generic_query_relation_plan(packet)


def validate_generic_query_relation_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a planned single-relation packet and return a safe copy."""

    safe = _safe_mapping(plan)
    if safe.get("schema_version") != GENERIC_QUERY_TO_RELATION_PLANNING_SCHEMA_VERSION:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "schema mismatch")
    if safe.get("phase_name") != GENERIC_QUERY_TO_RELATION_PLANNING_PHASE:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "phase mismatch")
    if safe.get("planning_status") != PLANNING_STATUS_PLANNED:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "status mismatch")
    if safe.get("planner_type") != PLANNER_TYPE:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "planner mismatch")
    if safe.get("supported_query_class_id") != MVP_SUPPORTED_QUERY_CLASS_ID:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "class id mismatch")
    boundary = _safe_mapping(safe.get("supported_query_class_boundary"))
    if boundary.get("profile_id") != MVP_SUPPORTED_QUERY_CLASS_ID:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "boundary missing")
    if safe.get("source_authority_posture_contract_ref") != SOURCE_AUTHORITY_POSTURE_PHASE:
        _blocked(
            BLOCKED_GENERIC_QUERY_PLANNING_SOURCE_AUTHORITY_CONTRACT_MISSING,
            "source-authority contract missing",
        )
    requirement = _safe_mapping(safe.get("source_authority_posture_requirement"))
    if requirement.get("contract_ref") != SOURCE_AUTHORITY_POSTURE_PHASE:
        _blocked(
            BLOCKED_GENERIC_QUERY_PLANNING_SOURCE_AUTHORITY_CONTRACT_MISSING,
            "source-authority requirement missing",
        )
    if requirement.get("analyst_owned") is not True:
        _blocked(
            BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE,
            "source authority must remain Analyst-owned",
        )
    if requirement.get("planner_must_not_decide_authority") is not True:
        _blocked(
            BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE,
            "planner source-authority boundary missing",
        )
    _require_false(
        safe,
        (
            "actual_source_authority_posture_created",
            "answer_created",
            "live_calls_made",
            "model_calls_made",
            "product_correctness_claimed",
            "friend_level_mvp_claimed",
            "general_supported_query_mvp_claimed",
        ),
    )
    if safe.get("query_retained") is not True:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "query not retained")
    if not _clean_text(safe.get("sanitized_query"), limit=500):
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "query missing")
    if _bounded_int(safe.get("component_count")) != 1:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_MULTI_COMPONENT, "component count")
    if _bounded_int(safe.get("source_obligation_count")) != 1:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "obligation count")
    if _bounded_int(safe.get("search_requirement_count")) != 1:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "search count")
    dprime = _safe_mapping(safe.get("dprime_relation_intake_candidate"))
    if dprime.get("answer_created") is not False or dprime.get("evidence_acquired") is not False:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "D-prime closed flag")
    future = _safe_mapping(safe.get("future_component_work_node_candidate"))
    if future.get("budget_lease_created") is not False:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "budget lease opened")
    if future.get("runkernel_scheduler_authorized") is not False:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "scheduler opened")
    _require_false_flags(_safe_mapping(safe.get("raw_private_retention_flags")))
    _require_false_flags(_safe_mapping(safe.get("closed_surface_flags")))
    _reject_forbidden_material(safe)
    expected_digest = _digest_json({k: v for k, v in safe.items() if k != "packet_digest"})
    if safe.get("packet_digest") != expected_digest:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "packet digest mismatch")
    return _json_safe(safe)


def validate_generic_query_plan_status_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Validate planned or blocked query-plan status packets."""

    safe = _safe_mapping(packet)
    if safe.get("planning_status") == PLANNING_STATUS_PLANNED:
        return validate_generic_query_relation_plan(safe)
    if safe.get("planning_status") != PLANNING_STATUS_BLOCKED:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "unknown status")
    if safe.get("schema_version") != GENERIC_QUERY_TO_RELATION_PLANNING_SCHEMA_VERSION:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "schema mismatch")
    if safe.get("phase_name") != GENERIC_QUERY_TO_RELATION_PLANNING_PHASE:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "phase mismatch")
    if safe.get("query") != "unsupported query (not retained)":
        _blocked(
            BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE,
            "unsupported query text retained",
        )
    if safe.get("unsupported_query_retained") is not False:
        _blocked(
            BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE,
            "unsupported query retention flag invalid",
        )
    if safe.get("relation_plan_created") is not False:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "plan created")
    if safe.get("dprime_relation_intake_candidate_created") is not False:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "D-prime candidate")
    if safe.get("future_component_work_node_candidate_created") is not False:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "node candidate")
    _require_false(
        safe,
        (
            "answer_created",
            "live_calls_made",
            "model_calls_made",
            "product_correctness_claimed",
        ),
    )
    _require_false_flags(_safe_mapping(safe.get("raw_private_retention_flags")))
    _require_false_flags(_safe_mapping(safe.get("closed_surface_flags")))
    _reject_forbidden_material(safe)
    expected_digest = _digest_json({k: v for k, v in safe.items() if k != "packet_digest"})
    if safe.get("packet_digest") != expected_digest:
        _blocked(BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE, "packet digest mismatch")
    return _json_safe(safe)


def build_generic_query_plan_status_output(
    *,
    query: str,
    repo_root: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> GenericQueryPlanStatusResult:
    """Write a sanitized planning or blocker packet and return CLI text."""

    root = Path(repo_root).resolve()
    run_id = _run_id(run_id)
    run_dir = _run_output_dir(
        root,
        output_dir or MVP_QUERY_PLANNING_OUTPUT_DIR,
        run_id,
    )
    packet_path = run_dir / MVP_QUERY_PLAN_PACKET_NAME
    try:
        packet = build_generic_query_relation_plan(query)
    except GenericQueryRelationPlanningError as exc:
        packet = _blocked_packet(
            run_id=run_id,
            blocker_code=exc.blocker_code,
            blocker_detail=exc.detail,
            hard_exclusion_category=exc.hard_exclusion_category,
        )
    packet = validate_generic_query_plan_status_packet(packet)
    _write_json(packet_path, packet)
    output = format_generic_query_plan_status_output(packet, packet_path=packet_path)
    return GenericQueryPlanStatusResult(
        decision=str(packet["decision"]),
        output=output,
        packet=packet,
        packet_path=packet_path,
    )


def format_generic_query_plan_status_output(
    packet: Mapping[str, Any],
    *,
    packet_path: Path,
) -> str:
    """Render compact CLI text for the query-plan status dry run."""

    status = str(packet.get("planning_status") or "")
    class_id = str(packet.get("supported_query_class_id") or MVP_SUPPORTED_QUERY_CLASS_ID)
    if status == PLANNING_STATUS_PLANNED:
        return "\n".join(
            [
                "ScryRaven MVP query plan status",
                "Decision: relation plan produced",
                f"Question: {packet.get('sanitized_query')}",
                f"Supported-query class: {class_id}",
                "No answer produced: true",
                "Live/model calls made: false",
                (
                    "Source-authority posture: future Analyst-owned requirement "
                    f"by reference ({packet.get('source_authority_posture_contract_ref')})."
                ),
                f"Review packet: {_display_path(packet_path)}",
            ]
        )
    return "\n".join(
        [
            "ScryRaven MVP query plan status blocked",
            "Decision: blocked before relation planning",
            f"Supported-query class: {class_id}",
            "Unsupported query text retained: false",
            "No answer/live/model/correctness: true",
            f"Blocker: {packet.get('blocker_code')}",
            f"Review packet: {_display_path(packet_path)}",
        ]
    )


def _gate_supported_query(query: str) -> GenericQueryPlanningGate:
    lowered = query.casefold()
    if not query:
        return GenericQueryPlanningGate(
            supported=False,
            blocker_code=BLOCKED_GENERIC_QUERY_PLANNING_UNSUPPORTED_QUERY_CLASS,
            blocker_detail="An empty query cannot enter the supported query class.",
            hard_exclusion_category="empty_query",
        )
    hard = _hard_exclusion_category(lowered)
    if hard:
        return GenericQueryPlanningGate(
            supported=False,
            blocker_code=BLOCKED_GENERIC_QUERY_PLANNING_HARD_EXCLUSION,
            blocker_detail=(
                "The query matches a hard exclusion for the current supported "
                "source-of-record single-fact boundary."
            ),
            hard_exclusion_category=hard,
        )
    if _looks_multi_component(lowered):
        return GenericQueryPlanningGate(
            supported=False,
            blocker_code=BLOCKED_GENERIC_QUERY_PLANNING_MULTI_COMPONENT,
            blocker_detail=(
                "The query appears to require multiple components or multi-hop "
                "planning, which is closed in this phase."
            ),
            hard_exclusion_category="multi_component",
        )
    fact_kind = _detect_fact_kind(lowered)
    if fact_kind is None:
        return GenericQueryPlanningGate(
            supported=False,
            blocker_code=BLOCKED_GENERIC_QUERY_PLANNING_UNSUPPORTED_QUERY_CLASS,
            blocker_detail=(
                "The conservative deterministic gate did not find a supported "
                "current value/status/requirement/deadline/fee shape."
            ),
            hard_exclusion_category="unsupported_query_shape",
        )
    if not any(marker in lowered for marker in _CURRENTNESS_MARKERS):
        return GenericQueryPlanningGate(
            supported=False,
            blocker_code=BLOCKED_GENERIC_QUERY_PLANNING_UNSUPPORTED_QUERY_CLASS,
            blocker_detail=(
                "The supported class requires a current or official source-of-record "
                "lookup shape."
            ),
            hard_exclusion_category="currentness_missing",
        )
    return GenericQueryPlanningGate(supported=True, fact_kind=fact_kind)


def _hard_exclusion_category(lowered: str) -> str | None:
    if any(
        marker in lowered
        for marker in (
            "reddit",
            "forum",
            "forums",
            "review",
            "reviews",
            "social media",
            "twitter",
            "facebook",
            "yelp",
            "glassdoor",
            "what does social",
            "what do people say",
        )
    ):
        return "social_review_aggregation"
    if any(
        marker in lowered
        for marker in (
            "compare",
            "competitor",
            "competitors",
            "versus",
            " vs ",
            "better than",
            "best ",
            "reliable",
            "reliability",
            "should i buy",
            "recommend",
            "recommendation",
        )
    ):
        return "product_comparison_or_recommendation"
    if any(
        marker in lowered
        for marker in (
            "diagnose",
            "symptom",
            "treatment",
            "dosage",
            "medical advice",
            "legal advice",
            "should i sue",
            "can i legally",
            "financial advice",
            "should i invest",
            "portfolio",
            "is it safe",
            "safety advice",
        )
    ):
        return "advice_or_safety_sensitive"
    if any(
        marker in lowered
        for marker in (
            "my ssn",
            "my social security number",
            "my account",
            "my password",
            "my address",
            "my email",
            "private data",
            "personal data",
            "personal information",
            "api key",
            "secret",
            "token",
        )
    ):
        return "private_or_personal_data"
    if any(
        marker in lowered
        for marker in (
            "calculate",
            "normalize",
            "convert",
            "adjusted for inflation",
            "per capita",
            "average of",
            "median",
            "sum of",
            "total of",
        )
    ):
        return "calculation_or_normalization"
    if any(
        marker in lowered
        for marker in (
            "why ",
            "forecast",
            "predict",
            "speculate",
            "what will",
            "would happen",
            "multi-hop",
        )
    ):
        return "broad_synthesis_or_speculation"
    return None


def _looks_multi_component(lowered: str) -> bool:
    if any(
        marker in lowered
        for marker in (
            " for each ",
            " list all ",
            " both ",
            " multiple ",
            " two different ",
            " fee and deadline",
            " fee and requirement",
            " deadline and fee",
            " requirements and deadline",
            ";",
        )
    ):
        return True
    fact_hits = sum(
        1
        for markers in _FACT_KIND_MARKERS.values()
        if any(marker in lowered for marker in markers)
    )
    return " and " in lowered and fact_hits > 1


def _detect_fact_kind(lowered: str) -> str | None:
    for fact_kind, markers in _FACT_KIND_MARKERS.items():
        if any(marker in lowered for marker in markers):
            return fact_kind
    return None


def _component_text(query: str) -> str:
    text = query.rstrip("?! .")
    for pattern in _QUESTION_PREFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:260] if text else "current source-of-record fact"


def _search_query_seeds(
    *,
    sanitized_query: str,
    component_text: str,
    fact_kind: str,
) -> list[str]:
    seeds = [
        sanitized_query,
        f"official current {component_text}",
        f"source of record {component_text} {fact_kind}",
    ]
    out: list[str] = []
    seen: set[str] = set()
    for seed in seeds:
        clean = _clean_text(seed, limit=220)
        key = clean.casefold() if clean else ""
        if clean and key not in seen:
            seen.add(key)
            out.append(clean)
    return out


def _source_authority_posture_requirement() -> dict[str, Any]:
    return {
        "requirement_id": SOURCE_AUTHORITY_POSTURE_REQUIREMENT_ID,
        "contract_ref": SOURCE_AUTHORITY_POSTURE_PHASE,
        "analyst_owned": True,
        "planner_must_not_decide_authority": True,
        "expected_source_use_requirement": "authority",
        "expected_source_class_family": [
            SOURCE_AUTHORITY_SOURCE_CLASS_OFFICIAL_OR_SOURCE_OF_RECORD,
            SOURCE_AUTHORITY_SOURCE_CLASS_GOVERNMENT_OR_PUBLIC_AGENCY,
            SOURCE_AUTHORITY_SOURCE_CLASS_LEGAL_OR_REGULATORY,
        ],
        "actual_source_authority_posture_created": False,
        "actual_source_authority_posture_required_later": True,
        "evidence_acquired": False,
    }


def _dprime_relation_intake_candidate(
    *,
    component_id: str,
    component_text: str,
    claim_under_test: str,
    source_obligation_id: str,
    source_obligation_text: str,
    search_requirement_id: str,
    search_requirement_text: str,
    source_authority_requirement: Mapping[str, Any],
    relation_plan_id: str,
) -> dict[str, Any]:
    return {
        "candidate_kind": "dprime_relation_intake_candidate",
        "target_runtime_surface": DPRIME_ANALYST_RELATION_INTAKE_SURFACE,
        "target_schema_version": DPRIME_ANALYST_RELATION_INTAKE_SCHEMA_VERSION,
        "compatibility_status": "candidate_only_no_evidence",
        "component_id": component_id,
        "component_text": component_text,
        "claim_under_test": claim_under_test,
        "source_obligation_id": source_obligation_id,
        "source_obligation_text": source_obligation_text,
        "search_requirement_id": search_requirement_id,
        "search_requirement_text": search_requirement_text,
        "source_authority_posture_requirement_ref": source_authority_requirement[
            "requirement_id"
        ],
        "relation_plan_id": relation_plan_id,
        "answer_created": False,
        "evidence_acquired": False,
        "support_claimed": False,
        "source_obligation_satisfaction_claimed": False,
        "citation_authority_claimed": False,
        "lineage_only": True,
    }


def _future_component_work_node_candidate(
    *,
    node_digest: str,
    parent_plan_id: str,
    component_id: str,
    search_requirement_id: str,
    source_obligation_id: str,
) -> dict[str, Any]:
    return {
        "node_id": f"component-work-node-candidate:{node_digest[:20]}",
        "parent_plan_id": parent_plan_id,
        "component_id": component_id,
        "component_type": "single_source_of_record_fact_lookup",
        "dependency_ids": [],
        "search_requirement_ids": [search_requirement_id],
        "source_obligation_requirement_ids": [source_obligation_id],
        "source_authority_posture_requirement_ids": [
            SOURCE_AUTHORITY_POSTURE_REQUIREMENT_ID
        ],
        "budget_lease_created": False,
        "runkernel_scheduler_authorized": False,
        "output_packet_refs": [],
        "blocker_refs": [],
        "raw_private_retention_flags": dict(RAW_PRIVATE_RETENTION_FLAGS),
        "component_work_node_implemented": False,
        "component_work_graph_implemented": False,
        "metadata_candidate_only": True,
    }


def _boundary_metadata(profile: Mapping[str, Any]) -> dict[str, Any]:
    canonical = _safe_mapping(profile.get("canonical_fixed_dogfood_example"))
    return {
        "profile_id": MVP_SUPPORTED_QUERY_CLASS_ID,
        "profile_version": MVP_SUPPORTED_QUERY_CLASS_VERSION,
        "profile_label": MVP_SUPPORTED_QUERY_CLASS_LABEL,
        "boundary_module": "core.mvp_supported_query_class_boundary",
        "consumed_by_planner": True,
        "product_path_slice": "generic_query_to_relation_planning_dry_run",
        "supported_query_shape": list(_safe_sequence(profile.get("supported_query_shape"))),
        "hard_exclusions": list(_safe_sequence(profile.get("hard_exclusions"))),
        "source_authority_posture_contract_ref": SOURCE_AUTHORITY_POSTURE_PHASE,
        "canonical_fixed_dogfood_example": {
            "example_only": canonical.get("example_only") is True,
            "architecture_definition": canonical.get("architecture_definition") is True,
        },
    }


def _blocked_packet(
    *,
    run_id: str,
    blocker_code: str,
    blocker_detail: str,
    hard_exclusion_category: str | None,
) -> dict[str, Any]:
    boundary = {
        "profile_id": MVP_SUPPORTED_QUERY_CLASS_ID,
        "profile_version": MVP_SUPPORTED_QUERY_CLASS_VERSION,
        "profile_label": MVP_SUPPORTED_QUERY_CLASS_LABEL,
        "boundary_module": "core.mvp_supported_query_class_boundary",
        "status": "unsupported_query_blocked_before_relation_planning",
    }
    packet = {
        "schema_version": GENERIC_QUERY_TO_RELATION_PLANNING_SCHEMA_VERSION,
        "phase_name": GENERIC_QUERY_TO_RELATION_PLANNING_PHASE,
        "mode": "BUILD",
        "planning_status": PLANNING_STATUS_BLOCKED,
        "decision": blocker_code,
        "planner_type": PLANNER_TYPE,
        "ordinary_entrypoint": "python -m proplex",
        "status_flag": MVP_QUERY_PLAN_STATUS_FLAG,
        "packet_id": f"generic-query-plan-blocker:{_clean_run_id(run_id)}",
        "run_id": _clean_run_id(run_id),
        "query": "unsupported query (not retained)",
        "unsupported_query_retained": False,
        "supported_query_class_id": MVP_SUPPORTED_QUERY_CLASS_ID,
        "supported_query_class_boundary": boundary,
        "source_authority_posture_contract_ref": SOURCE_AUTHORITY_POSTURE_PHASE,
        "blocker_code": blocker_code,
        "blocker_detail": blocker_detail,
        "hard_exclusion_category": hard_exclusion_category,
        "relation_plan_created": False,
        "relation_plan": None,
        "dprime_relation_intake_candidate_created": False,
        "future_component_work_node_candidate_created": False,
        "component_count": 0,
        "source_obligation_count": 0,
        "search_requirement_count": 0,
        "answer_created": False,
        "live_calls_made": False,
        "model_calls_made": False,
        "product_correctness_claimed": False,
        "raw_private_retention_flags": dict(RAW_PRIVATE_RETENTION_FLAGS),
        "closed_surface_flags": dict(CLOSED_SURFACE_FLAGS),
        "explicit_nonclaims": list(EXPLICIT_NONCLAIMS),
    }
    packet["packet_digest"] = _digest_json(packet)
    return packet


def _run_output_dir(root: Path, output_dir: str | Path, run_id: str) -> Path:
    raw = Path(output_dir)
    if not raw.is_absolute():
        raw = root / raw
    output_root = (root / "output").resolve()
    resolved = raw.resolve()
    try:
        resolved.relative_to(output_root)
    except ValueError as exc:
        raise ValueError("MVP query planning output dir must stay under output/") from exc
    target = resolved / _clean_run_id(run_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _blocked(blocker_code: str, detail: str) -> None:
    raise GenericQueryRelationPlanningError(blocker_code, detail)


def _reject_forbidden_material(value: Any) -> None:
    keys = _collect_keys(value)
    forbidden: list[str] = []
    for key in sorted(keys):
        if key in _ALLOWED_RAW_PRIVATE_KEYS:
            if key != "raw_private_retention_flags" and not _all_key_values_false(
                value,
                key,
            ):
                forbidden.append(key)
            continue
        if key.startswith("raw_") or key in {
            "api_key",
            "authorization",
            "bounded_text",
            "cache_row",
            "cookie",
            "db_row",
            "env",
            "full_trace",
            "headers",
            "model_response",
            "page_content",
            "page_text",
            "password",
            "private_log",
            "prompt",
            "provider_payload",
            "secret",
            "token",
            "unbounded_text",
        }:
            forbidden.append(key)
    if forbidden:
        _blocked(
            BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE,
            "packet contains raw/private fields: " + ", ".join(forbidden),
        )
    markers = sorted(_private_value_markers(value))
    if markers:
        _blocked(
            BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE,
            "packet contains private-looking values: " + ", ".join(markers),
        )


def _private_value_markers(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for item in value.values():
            found.update(_private_value_markers(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_private_value_markers(item))
    elif isinstance(value, str):
        lowered = value.casefold()
        for marker in _PRIVATE_VALUE_MARKERS:
            if marker in lowered:
                found.add(marker)
    return found


def _require_false(packet: Mapping[str, Any], keys: Sequence[str]) -> None:
    for key in keys:
        if packet.get(key) is not False:
            _blocked(
                BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE,
                f"{key} must remain false",
            )


def _require_false_flags(flags: Mapping[str, Any]) -> None:
    for key, value in flags.items():
        if value is not False:
            _blocked(
                BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE,
                f"{key} must remain false",
            )


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


def _all_key_values_false(value: Any, normalized_key: str) -> bool:
    values = list(_normalized_key_values(value, normalized_key))
    return bool(values) and all(item is False for item in values)


def _normalized_key_values(value: Any, normalized_key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_key(key) == normalized_key:
                found.append(item)
            found.extend(_normalized_key_values(item, normalized_key))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.extend(_normalized_key_values(item, normalized_key))
    return found


def _normalize_query(value: Any) -> str:
    return _clean_text(value, limit=500) or ""


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _bounded_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed >= 0 else 0


def _slug(value: str) -> str:
    text = value.casefold()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80].strip("-") or "single-source-of-record-fact"


def _clean_run_id(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in "-_:" else "-" for ch in value.strip())
    return text[:120] or f"mvp-query-plan-{uuid.uuid4().hex[:12]}"


def _run_id(value: str | None) -> str:
    return _clean_run_id(value) if value else f"mvp-query-plan-{uuid.uuid4().hex[:12]}"


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


__all__ = [
    "BLOCKED_GENERIC_QUERY_PLANNING_HARD_EXCLUSION",
    "BLOCKED_GENERIC_QUERY_PLANNING_MULTI_COMPONENT",
    "BLOCKED_GENERIC_QUERY_PLANNING_OUTPUT_HYGIENE",
    "BLOCKED_GENERIC_QUERY_PLANNING_SOURCE_AUTHORITY_CONTRACT_MISSING",
    "BLOCKED_GENERIC_QUERY_PLANNING_UNSUPPORTED_QUERY_CLASS",
    "GENERIC_QUERY_TO_RELATION_PLANNING_PHASE",
    "GENERIC_QUERY_TO_RELATION_PLANNING_SCHEMA_VERSION",
    "MVP_QUERY_PLANNING_OUTPUT_DIR",
    "MVP_QUERY_PLAN_PACKET_NAME",
    "MVP_QUERY_PLAN_STATUS_FLAG",
    "GenericQueryPlanStatusResult",
    "GenericQueryRelationPlanningError",
    "build_generic_query_plan_status_output",
    "build_generic_query_relation_plan",
    "format_generic_query_plan_status_output",
    "validate_generic_query_plan_status_packet",
    "validate_generic_query_relation_plan",
]
