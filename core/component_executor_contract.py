"""Offline ComponentSearchPlan to component-aware search-work contract.

This module is executor-side only. It accepts already-safe structured component
search plans and summarizes component scorekeeping without calling models,
providers, search, fetch/read, retrieval, Author, or citation machinery.

``ComponentPlan`` remains the backward-compatible input name from
AG-COMPONENT-EXECUTOR-CONTRACT-01. ``ComponentSearchPlan`` is the clearer
subordinate alias: both names describe component-scoped search planning input
owned under RunKernel / AnswerContractAuthorityMap, never top-level answer
authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

COMPONENT_PLAN_SCHEMA_VERSION = "component_plan_executor_contract_v1"
COMPONENT_EXECUTOR_CONTRACT_SCHEMA_VERSION = "component_executor_contract_ag_component_01_v1"
COMPONENT_SCOREKEEPING_SCHEMA_VERSION = "component_scorekeeping_ag_component_01_v1"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output",
        "output_artifact",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_trace",
        "secret",
        "secrets",
        "token",
    }
)
_SENSITIVE_KEY_FRAGMENTS = ("api_key", "password", "secret", "token")


class PlannerSource(str, Enum):
    CHEAP_STRUCTURED_PLANNER = "cheap_structured_planner"
    DISAMBIGUATION_REVISED_PLANNER = "disambiguation_revised_planner"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"
    OFFLINE_FIXTURE = "offline_fixture"


class AmbiguityStatus(str, Enum):
    CLEAR = "clear"
    NEEDS_DISAMBIGUATION = "needs_disambiguation"
    DISAMBIGUATED = "disambiguated"
    UNRESOLVED = "unresolved"


class FreshnessKind(str, Enum):
    STABLE_DOCS = "stable_docs"
    CURRENT = "current"
    RECENT = "recent"
    HISTORICAL = "historical"
    USER_SPECIFIED = "user_specified"
    UNSPECIFIED = "unspecified"


class SourceClass(str, Enum):
    OFFICIAL_DOCS = "official_docs"
    PRIMARY_SOURCE = "primary_source"
    DOCUMENTATION = "documentation"
    NEWS = "news"
    COMMUNITY = "community"
    MIXED = "mixed"
    UNSPECIFIED = "unspecified"


class SearchIntentPurpose(str, Enum):
    OFFICIAL_DOC_LOOKUP = "official_doc_lookup"
    DEFAULT_VALUE_LOOKUP = "default_value_lookup"
    DISAMBIGUATION = "disambiguation"
    CURRENTNESS_CHECK = "currentness_check"
    GENERAL_LOOKUP = "general_lookup"


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    kind: FreshnessKind | str
    recency_window: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _coerce_enum(FreshnessKind, self.kind, FreshnessKind.UNSPECIFIED))
        object.__setattr__(self, "recency_window", _clean_text(self.recency_window, limit=120))

    @property
    def applies_recent_only_filter(self) -> bool:
        return self.kind in {FreshnessKind.RECENT, FreshnessKind.CURRENT} and bool(self.recency_window)

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "kind": self.kind.value,
                "recency_window": self.recency_window,
                "applies_recent_only_filter": self.applies_recent_only_filter,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> "FreshnessPolicy":
        source = _mapping(payload)
        return cls(
            kind=source.get("kind") or FreshnessKind.UNSPECIFIED.value,
            recency_window=_clean_text(source.get("recency_window"), limit=120),
        )


@dataclass(frozen=True, slots=True)
class SourceRequirement:
    source_class: SourceClass | str
    citation_required: bool = False
    fetch_read_required: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_class", _coerce_enum(SourceClass, self.source_class, SourceClass.UNSPECIFIED))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_class": self.source_class.value,
            "citation_required": bool(self.citation_required),
            "fetch_read_required": bool(self.fetch_read_required),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> "SourceRequirement":
        source = _mapping(payload)
        return cls(
            source_class=source.get("source_class") or SourceClass.UNSPECIFIED.value,
            citation_required=bool(source.get("citation_required", False)),
            fetch_read_required=bool(source.get("fetch_read_required", False)),
        )


@dataclass(frozen=True, slots=True)
class SearchIntent:
    query_text: str
    purpose: SearchIntentPurpose | str
    freshness_policy: FreshnessPolicy = field(default_factory=lambda: FreshnessPolicy(FreshnessKind.UNSPECIFIED))
    allowed_domains: tuple[str, ...] | None = None
    safe_query_template: str | None = None

    def __post_init__(self) -> None:
        if not _clean_text(self.query_text, limit=300):
            raise ValueError("search intent requires query_text")
        object.__setattr__(self, "query_text", _clean_text(self.query_text, limit=300) or "")
        object.__setattr__(
            self,
            "purpose",
            _coerce_enum(SearchIntentPurpose, self.purpose, SearchIntentPurpose.GENERAL_LOOKUP),
        )
        object.__setattr__(self, "allowed_domains", _domain_tuple_or_none(self.allowed_domains))
        object.__setattr__(self, "safe_query_template", _clean_text(self.safe_query_template, limit=300))

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "query_text": self.query_text,
                "safe_query_template": self.safe_query_template,
                "purpose": self.purpose.value,
                "freshness_policy": self.freshness_policy.to_dict(),
                "allowed_domains": list(self.allowed_domains) if self.allowed_domains is not None else None,
                "executes_search": False,
                "provider_selected": False,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SearchIntent":
        source = _mapping(payload)
        return cls(
            query_text=str(source.get("query_text") or source.get("safe_query_template") or ""),
            safe_query_template=_clean_text(source.get("safe_query_template"), limit=300),
            purpose=source.get("purpose") or SearchIntentPurpose.GENERAL_LOOKUP.value,
            freshness_policy=FreshnessPolicy.from_dict(source.get("freshness_policy")),
            allowed_domains=_domain_tuple_or_none(source.get("allowed_domains")),
        )


@dataclass(frozen=True, slots=True)
class SuccessCriteria:
    evidence_required: bool = True
    citation_required: bool = True
    answer_value_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_required": bool(self.evidence_required),
            "citation_required": bool(self.citation_required),
            "answer_value_required": bool(self.answer_value_required),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> "SuccessCriteria":
        source = _mapping(payload)
        return cls(
            evidence_required=bool(source.get("evidence_required", True)),
            citation_required=bool(source.get("citation_required", True)),
            answer_value_required=bool(source.get("answer_value_required", True)),
        )


@dataclass(frozen=True, slots=True)
class ComponentPlanComponent:
    component_id: str
    label: str
    answer_target: str
    source_requirement: SourceRequirement
    search_intents: tuple[SearchIntent, ...]
    aliases: tuple[str, ...] = ()
    entity_type: str = "unspecified"
    expected_answerable: bool = True
    allowed_domains: tuple[str, ...] | None = None
    disambiguation_status: AmbiguityStatus | str = AmbiguityStatus.CLEAR
    success_criteria: SuccessCriteria = field(default_factory=SuccessCriteria)

    def __post_init__(self) -> None:
        if not _clean_token(self.component_id):
            raise ValueError("component plan component requires component_id")
        if not _clean_text(self.label):
            raise ValueError("component plan component requires label")
        if not _clean_text(self.answer_target):
            raise ValueError("component plan component requires answer_target")
        if not self.search_intents:
            raise ValueError("component plan component requires at least one search intent")
        object.__setattr__(self, "component_id", _clean_token(self.component_id) or "")
        object.__setattr__(self, "label", _clean_text(self.label, limit=180) or "")
        object.__setattr__(self, "answer_target", _clean_text(self.answer_target, limit=180) or "")
        object.__setattr__(self, "aliases", _text_tuple(self.aliases))
        object.__setattr__(self, "entity_type", _clean_token(self.entity_type) or "unspecified")
        object.__setattr__(self, "allowed_domains", _domain_tuple_or_none(self.allowed_domains))
        object.__setattr__(
            self,
            "disambiguation_status",
            _coerce_enum(AmbiguityStatus, self.disambiguation_status, AmbiguityStatus.UNRESOLVED),
        )
        object.__setattr__(self, "search_intents", tuple(self.search_intents))

    def planned_search_terms(self) -> tuple[str, ...]:
        terms: list[str] = []
        for intent in self.search_intents:
            if intent.query_text not in terms:
                terms.append(intent.query_text)
        return tuple(terms)

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "component_id": self.component_id,
                "label": self.label,
                "aliases": list(self.aliases),
                "entity_type": self.entity_type,
                "answer_target": self.answer_target,
                "expected_answerable": bool(self.expected_answerable),
                "source_requirement": self.source_requirement.to_dict(),
                "allowed_domains": list(self.allowed_domains) if self.allowed_domains is not None else None,
                "disambiguation_status": self.disambiguation_status.value,
                "search_intents": [intent.to_dict() for intent in self.search_intents],
                "success_criteria": self.success_criteria.to_dict(),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ComponentPlanComponent":
        source = _mapping(payload)
        return cls(
            component_id=str(source.get("component_id") or ""),
            label=str(source.get("label") or ""),
            aliases=_text_tuple(source.get("aliases")),
            entity_type=str(source.get("entity_type") or "unspecified"),
            answer_target=str(source.get("answer_target") or ""),
            expected_answerable=bool(source.get("expected_answerable", True)),
            source_requirement=SourceRequirement.from_dict(source.get("source_requirement")),
            allowed_domains=_domain_tuple_or_none(source.get("allowed_domains")),
            disambiguation_status=source.get("disambiguation_status") or AmbiguityStatus.UNRESOLVED.value,
            search_intents=tuple(
                SearchIntent.from_dict(item)
                for item in source.get("search_intents") or ()
                if isinstance(item, Mapping)
            ),
            success_criteria=SuccessCriteria.from_dict(source.get("success_criteria")),
        )


@dataclass(frozen=True, slots=True)
class ComponentPlan:
    """Backward-compatible subordinate component-search planning input."""

    plan_id: str
    planner_source: PlannerSource | str
    user_query_digest: str
    ambiguity_status: AmbiguityStatus | str
    freshness_policy: FreshnessPolicy
    components: tuple[ComponentPlanComponent, ...]
    schema_version: str = COMPONENT_PLAN_SCHEMA_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.plan_id):
            raise ValueError("component plan requires plan_id")
        if not _clean_token(self.user_query_digest, limit=180):
            raise ValueError("component plan requires user_query_digest")
        if not self.components:
            raise ValueError("component plan requires at least one component")
        if len(self.components) > 5:
            raise ValueError("component plan supports at most five initial components")
        component_ids = [component.component_id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("component plan component_id values must be unique")
        object.__setattr__(
            self,
            "planner_source",
            _coerce_enum(PlannerSource, self.planner_source, PlannerSource.DETERMINISTIC_FALLBACK),
        )
        object.__setattr__(
            self,
            "ambiguity_status",
            _coerce_enum(AmbiguityStatus, self.ambiguity_status, AmbiguityStatus.UNRESOLVED),
        )
        object.__setattr__(self, "components", tuple(self.components))

    def planned_component_ids(self) -> tuple[str, ...]:
        return tuple(component.component_id for component in self.components)

    def planned_query_terms(self) -> tuple[str, ...]:
        terms: list[str] = []
        for component in self.components:
            for term in component.planned_search_terms():
                if term not in terms:
                    terms.append(term)
        return tuple(terms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": _clean_token(self.plan_id),
            "planner_source": self.planner_source.value,
            "user_query_digest": _clean_token(self.user_query_digest, limit=180),
            "ambiguity_status": self.ambiguity_status.value,
            "freshness_policy": self.freshness_policy.to_dict(),
            "components": [component.to_dict() for component in self.components],
            "metadata": _json_safe(self.metadata),
            "raw_private_material_serialized": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ComponentPlan":
        source = _mapping(payload)
        return cls(
            plan_id=str(source.get("plan_id") or ""),
            planner_source=source.get("planner_source") or PlannerSource.DETERMINISTIC_FALLBACK.value,
            user_query_digest=str(source.get("user_query_digest") or ""),
            ambiguity_status=source.get("ambiguity_status") or AmbiguityStatus.UNRESOLVED.value,
            freshness_policy=FreshnessPolicy.from_dict(source.get("freshness_policy")),
            components=tuple(
                ComponentPlanComponent.from_dict(item)
                for item in source.get("components") or ()
                if isinstance(item, Mapping)
            ),
            schema_version=str(source.get("schema_version") or COMPONENT_PLAN_SCHEMA_VERSION),
            metadata=dict(source.get("metadata") or {}),
        )


ComponentSearchPlan = ComponentPlan
ComponentSearchPlanComponent = ComponentPlanComponent


def build_component_executor_contract_projection(component_plan: ComponentPlan) -> dict[str, Any]:
    """Return subordinate component-search planning projections."""

    scorekeeping = summarize_component_scorekeeping(component_plan)
    return {
        "schema_version": COMPONENT_EXECUTOR_CONTRACT_SCHEMA_VERSION,
        "component_plan": component_plan.to_dict(),
        "planned_query_terms_by_component": {
            component.component_id: [
                _planned_term(component.component_id, intent)
                for intent in component.search_intents
            ]
            for component in component_plan.components
        },
        "component_scorekeeping": scorekeeping,
        "behavior_boundary_flags": {
            "model_planner_called": False,
            "query_text_generated_from_model": False,
            "provider_selected": False,
            "search_executed": False,
            "fetch_read_executed": False,
            "retrieval_behavior_changed": False,
            "author_called": False,
            "partial_answer_readiness_changed": False,
            "caps_profile_changed": False,
        },
    }


def summarize_component_scorekeeping(
    component_plan: ComponentPlan,
    *,
    searched_component_ids: Sequence[str] = (),
    fetched_component_ids: Sequence[str] = (),
    evidence_bound_component_ids: Sequence[str] = (),
    citation_bound_component_ids: Sequence[str] = (),
    source_obligation_satisfied_component_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Summarize component status without upgrading planned presence to success."""

    planned_ids = component_plan.planned_component_ids()
    searched = _normalized_id_set(searched_component_ids)
    fetched = _normalized_id_set(fetched_component_ids)
    evidence_bound = _normalized_id_set(evidence_bound_component_ids)
    citation_bound = _normalized_id_set(citation_bound_component_ids)
    source_satisfied = _normalized_id_set(source_obligation_satisfied_component_ids)
    entries = [
        _scorekeeping_entry(
            component,
            searched=component.component_id in searched,
            fetched=component.component_id in fetched,
            evidence_bound=component.component_id in evidence_bound,
            citation_bound=component.component_id in citation_bound,
            source_obligation_satisfied=component.component_id in source_satisfied,
        )
        for component in component_plan.components
    ]
    full_success_ids = [
        entry["component_id"]
        for entry in entries
        if entry["full_component_success"] is True
    ]
    partial_semantic_coverage_ids = [
        entry["component_id"]
        for entry in entries
        if entry["partial_semantic_coverage"] is True
    ]
    return {
        "schema_version": COMPONENT_SCOREKEEPING_SCHEMA_VERSION,
        "planned_component_count": len(planned_ids),
        "expected_component_count": len(planned_ids),
        "searched_component_count": _count_present(planned_ids, searched),
        "unsearched_component_ids": _missing_ids(planned_ids, searched),
        "fetched_component_count": _count_present(planned_ids, fetched),
        "unfetched_component_ids": _missing_ids(planned_ids, fetched),
        "evidence_bound_component_count": _count_present(planned_ids, evidence_bound),
        "evidence_unbound_component_ids": _missing_ids(planned_ids, evidence_bound),
        "citation_bound_component_count": _count_present(planned_ids, citation_bound),
        "citation_unbound_component_ids": _missing_ids(planned_ids, citation_bound),
        "source_obligation_satisfied_component_count": _count_present(planned_ids, source_satisfied),
        "source_obligation_unsatisfied_component_ids": _missing_ids(planned_ids, source_satisfied),
        "full_component_success_count": len(full_success_ids),
        "full_component_success_component_ids": full_success_ids,
        "full_component_success": len(full_success_ids) == len(planned_ids),
        "partial_semantic_coverage_component_ids": partial_semantic_coverage_ids,
        "semantic_partial_coverage_observed": bool(partial_semantic_coverage_ids),
        "planned_component_presence_is_user_safe_partial_answer": False,
        "partial_user_answer_candidate": False,
        "author_called": False,
        "components": entries,
    }


def _scorekeeping_entry(
    component: ComponentPlanComponent,
    *,
    searched: bool,
    fetched: bool,
    evidence_bound: bool,
    citation_bound: bool,
    source_obligation_satisfied: bool,
) -> dict[str, Any]:
    criteria = component.success_criteria
    answer_value_bound = False
    full_success = (
        (not criteria.evidence_required or evidence_bound)
        and (not criteria.citation_required or citation_bound)
        and (not component.source_requirement.fetch_read_required or fetched)
        and source_obligation_satisfied
        and (not criteria.answer_value_required or answer_value_bound)
    )
    partial_semantic_coverage = searched and not full_success
    return {
        "component_id": component.component_id,
        "label": component.label,
        "answer_target": component.answer_target,
        "searched": searched,
        "fetched": fetched,
        "evidence_bound": evidence_bound,
        "citation_bound": citation_bound,
        "source_obligation_satisfied": source_obligation_satisfied,
        "answer_value_bound": answer_value_bound,
        "full_component_success": full_success,
        "partial_semantic_coverage": partial_semantic_coverage,
        "partial_user_answer_ready": False,
    }


def _planned_term(component_id: str, intent: SearchIntent) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "query_text": intent.query_text,
        "purpose": intent.purpose.value,
        "freshness_policy": intent.freshness_policy.to_dict(),
        "allowed_domains": list(intent.allowed_domains or ()),
        "executes_search": False,
    }


def _count_present(planned_ids: Sequence[str], observed: set[str]) -> int:
    return sum(1 for component_id in planned_ids if component_id in observed)


def _missing_ids(planned_ids: Sequence[str], observed: set[str]) -> list[str]:
    return [component_id for component_id in planned_ids if component_id not in observed]


def _normalized_id_set(values: Sequence[str]) -> set[str]:
    return {text for value in values if (text := _clean_token(value))}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _coerce_enum(enum_class: type[Enum], value: Any, default: Enum) -> Enum:
    raw = value.value if isinstance(value, Enum) else value
    for item in enum_class:
        if item.value == raw:
            return item
    return default


def _domain_tuple_or_none(value: Sequence[Any] | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    domains = _text_tuple(value, limit=120)
    return domains if domains else None


def _text_tuple(value: Sequence[Any] | None, *, limit: int = 160) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    out: list[str] = []
    for item in value:
        text = _clean_token(item, limit=limit)
        if text:
            out.append(text)
    return tuple(out)


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
    return (
        normalized.startswith("raw_")
        or normalized in _SENSITIVE_KEYS
        or any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS)
    )


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[redacted]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_token(key, limit=120)
            if not key_text or _is_sensitive_key(key_text):
                continue
            out[key_text] = _json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:120]]
    return _clean_text(value, limit=300)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


__all__ = [
    "COMPONENT_EXECUTOR_CONTRACT_SCHEMA_VERSION",
    "COMPONENT_PLAN_SCHEMA_VERSION",
    "COMPONENT_SCOREKEEPING_SCHEMA_VERSION",
    "AmbiguityStatus",
    "ComponentPlan",
    "ComponentPlanComponent",
    "ComponentSearchPlan",
    "ComponentSearchPlanComponent",
    "FreshnessKind",
    "FreshnessPolicy",
    "PlannerSource",
    "SearchIntent",
    "SearchIntentPurpose",
    "SourceClass",
    "SourceRequirement",
    "SuccessCriteria",
    "build_component_executor_contract_projection",
    "summarize_component_scorekeeping",
]
