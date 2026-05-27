"""Pure offline conflict-state production for runtime answer contracts.

The producer is intentionally narrow. It consumes sanitized evidence passages
and contract context, recognizes only explicit effective-date claim tension,
and emits compact conflict facts. It does not call providers, models, prompts,
retrieval, routing, persistence, storage, or orchestration code.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Protocol

CONFLICT_STATE_SCHEMA_VERSION = "conflict_state_ag40_v1"

_MAX_TEXT = 500
_MAX_NOTE = 220
_MAX_REFS = 6
_MAX_QUERIES = 2
_MAX_CLAIMS = 4
_CENTRAL = "central"
_NOT_CENTRAL = "not_central"
_QUERY_SOURCE_NONE = "none"
_QUERY_SOURCE_DETERMINISTIC = "deterministic_claim_pair"
_CONFIDENCE_LOW = "low"
_CONFIDENCE_MEDIUM = "medium"
_CONFIDENCE_HIGH = "high"
_ALLOWED_CENTRALITY = frozenset(
    {_CENTRAL, "supporting", "peripheral", _NOT_CENTRAL, "unknown"}
)
_ALLOWED_CONFIDENCE = frozenset(
    {_CONFIDENCE_LOW, _CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH}
)
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "final_answer",
        "full_trace",
        "password",
        "private_output",
        "prompt",
        "provider_payload",
        "raw_log",
        "raw_logs",
        "raw_payload",
        "raw_provider_payload",
        "raw_prompt",
        "raw_trace",
        "secret",
        "token",
    }
)
_CENTRAL_TERMS = frozenset(
    {
        "current",
        "date",
        "effective",
        "eligibility",
        "official",
        "requirement",
        "requirements",
        "rule",
        "rules",
    }
)
_STALE_TERMS = re.compile(r"\b(archived|obsolete|older|outdated|previous|stale|superseded)\b", re.I)
_DATE_PATTERN = r"([A-Z][a-z]+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2})"
_EFFECTIVE_DATE_PATTERNS = (
    re.compile(rf"\beffective date(?: is|:)?\s+{_DATE_PATTERN}\b", re.I),
    re.compile(rf"\btakes effect on\s+{_DATE_PATTERN}\b", re.I),
    re.compile(rf"\beffective\s+{_DATE_PATTERN}\b", re.I),
)


class BoundedConflictClassifier(Protocol):
    """Optional offline classifier hook.

    Implementations must be deterministic and bounded. The default producer
    never calls a live model; when no classifier is supplied, this hook is
    simply absent and the deterministic producer fails closed where needed.
    """

    def classify(self, producer_input: "ConflictStateProducerInput") -> "ConflictState":
        ...


@dataclass(frozen=True)
class ConflictClaim:
    """A compact, JSON-safe factual claim extracted from sanitized evidence."""

    claim_id: str
    normalized_claim: str
    value: str | None = None
    attribute: str | None = None
    subject: str | None = None
    source_refs: tuple[str, ...] = ()
    source_classes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", _clean_text(self.claim_id, limit=80))
        object.__setattr__(
            self,
            "normalized_claim",
            _clean_text(self.normalized_claim, limit=160),
        )
        object.__setattr__(
            self,
            "value",
            _clean_optional_text(self.value, limit=80),
        )
        object.__setattr__(
            self,
            "attribute",
            _clean_optional_text(self.attribute, limit=80),
        )
        object.__setattr__(
            self,
            "subject",
            _clean_optional_text(self.subject, limit=120),
        )
        object.__setattr__(
            self,
            "source_refs",
            _copy_string_tuple(self.source_refs, cap=_MAX_REFS, limit=80),
        )
        object.__setattr__(
            self,
            "source_classes",
            _copy_string_tuple(self.source_classes, cap=_MAX_REFS, limit=80),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "normalized_claim": self.normalized_claim,
            "value": self.value,
            "attribute": self.attribute,
            "subject": self.subject,
            "source_refs": list(self.source_refs),
            "source_classes": list(self.source_classes),
        }


@dataclass(frozen=True)
class ConflictState:
    """Sanitized producer output consumed by the runtime answer contract."""

    schema_version: str = CONFLICT_STATE_SCHEMA_VERSION
    conflicts_present: bool = False
    conflict_notes: tuple[str, ...] = ()
    claims_in_tension: tuple[ConflictClaim, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    centrality_to_contract: str = _NOT_CENTRAL
    resolving_query_candidates: tuple[str, ...] = ()
    resolving_query_source: str = _QUERY_SOURCE_NONE
    resolving_query_provenance: tuple[str, ...] = ()
    confidence: str = _CONFIDENCE_LOW
    safe_to_dispatch_resolve_conflict: bool = False
    blockers: tuple[str, ...] = ()
    ordinary_next_queries: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        claims = _dedupe_claims(self.claims_in_tension)
        refs = _copy_string_tuple(self.evidence_refs, cap=_MAX_REFS, limit=80)
        if not refs:
            refs = _copy_string_tuple(
                tuple(ref for claim in claims for ref in claim.source_refs),
                cap=_MAX_REFS,
                limit=80,
            )
        centrality = _clean_enum(
            self.centrality_to_contract,
            allowed=_ALLOWED_CENTRALITY,
            default=_NOT_CENTRAL,
        )
        confidence = _clean_enum(
            self.confidence,
            allowed=_ALLOWED_CONFIDENCE,
            default=_CONFIDENCE_LOW,
        )
        query_candidates = _copy_string_tuple(
            self.resolving_query_candidates,
            cap=_MAX_QUERIES,
            limit=180,
        )
        blockers = _copy_string_tuple(self.blockers, cap=8, limit=80)
        safe = _is_safe_to_dispatch(
            conflicts_present=bool(self.conflicts_present),
            claims=claims,
            refs=refs,
            centrality=centrality,
            query_candidates=query_candidates,
            confidence=confidence,
            blockers=blockers,
        )
        if not safe and self.safe_to_dispatch_resolve_conflict:
            blockers = _merge_string_tuples(blockers, ("producer_failed_closed",))
        object.__setattr__(
            self,
            "schema_version",
            _clean_text(self.schema_version, limit=80) or CONFLICT_STATE_SCHEMA_VERSION,
        )
        object.__setattr__(
            self,
            "conflict_notes",
            _copy_string_tuple(self.conflict_notes, cap=4, limit=_MAX_NOTE),
        )
        object.__setattr__(self, "claims_in_tension", claims)
        object.__setattr__(self, "evidence_refs", refs)
        object.__setattr__(self, "centrality_to_contract", centrality)
        object.__setattr__(self, "resolving_query_candidates", query_candidates)
        object.__setattr__(
            self,
            "resolving_query_source",
            _clean_text(self.resolving_query_source, limit=80) or _QUERY_SOURCE_NONE,
        )
        object.__setattr__(
            self,
            "resolving_query_provenance",
            _copy_string_tuple(self.resolving_query_provenance, cap=4, limit=120),
        )
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "safe_to_dispatch_resolve_conflict", safe)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(
            self,
            "ordinary_next_queries",
            _copy_string_tuple(self.ordinary_next_queries, cap=8, limit=180),
        )
        object.__setattr__(self, "metadata", _json_safe_mapping(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "conflicts_present": bool(self.conflicts_present),
            "conflict_notes": list(self.conflict_notes),
            "claims_in_tension": [
                claim.to_dict() for claim in self.claims_in_tension
            ],
            "evidence_refs": list(self.evidence_refs),
            "centrality_to_contract": self.centrality_to_contract,
            "resolving_query_candidates": list(self.resolving_query_candidates),
            "resolving_query_source": self.resolving_query_source,
            "resolving_query_provenance": list(self.resolving_query_provenance),
            "confidence": self.confidence,
            "safe_to_dispatch_resolve_conflict": bool(
                self.safe_to_dispatch_resolve_conflict
            ),
            "blockers": list(self.blockers),
            "ordinary_next_queries": list(self.ordinary_next_queries),
            "metadata": _json_safe_mapping(self.metadata),
        }


@dataclass(frozen=True)
class ConflictStateProducerInput:
    """Sanitized ordinary runtime evidence/context for conflict production."""

    query: str
    core_topic: str | None = None
    primary_entity: str | None = None
    current_date: str | None = None
    final_top_evidence: Sequence[Mapping[str, Any]] = ()
    source_tier_counts: Mapping[str, Any] = field(default_factory=dict)
    source_domain_telemetry: Mapping[str, Any] = field(default_factory=dict)
    source_class_observability: Mapping[str, Any] = field(default_factory=dict)
    answer_contract_family: str | None = None
    must_satisfy: Sequence[Any] = ()
    required_source_classes: Sequence[Any] = ()
    fulfilled_contract_items: Sequence[Any] = ()
    partial_contract_items: Sequence[Any] = ()
    unfulfilled_contract_items: Sequence[Any] = ()
    ordinary_next_queries: Sequence[Any] = ()
    allow_resolving_query_candidates: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "query", _clean_text(self.query, limit=240))
        object.__setattr__(
            self,
            "core_topic",
            _clean_optional_text(self.core_topic, limit=160),
        )
        object.__setattr__(
            self,
            "primary_entity",
            _clean_optional_text(self.primary_entity, limit=120),
        )
        object.__setattr__(
            self,
            "current_date",
            _clean_optional_text(self.current_date, limit=40),
        )
        object.__setattr__(
            self,
            "source_tier_counts",
            _json_safe_mapping(self.source_tier_counts),
        )
        object.__setattr__(
            self,
            "source_domain_telemetry",
            _json_safe_mapping(self.source_domain_telemetry),
        )
        object.__setattr__(
            self,
            "source_class_observability",
            _json_safe_mapping(self.source_class_observability),
        )
        object.__setattr__(
            self,
            "answer_contract_family",
            _clean_optional_text(self.answer_contract_family, limit=80),
        )
        object.__setattr__(
            self,
            "must_satisfy",
            _copy_string_tuple(self.must_satisfy, cap=12, limit=160),
        )
        object.__setattr__(
            self,
            "required_source_classes",
            _copy_string_tuple(self.required_source_classes, cap=12, limit=120),
        )
        object.__setattr__(
            self,
            "fulfilled_contract_items",
            _copy_string_tuple(self.fulfilled_contract_items, cap=12, limit=160),
        )
        object.__setattr__(
            self,
            "partial_contract_items",
            _copy_string_tuple(self.partial_contract_items, cap=12, limit=160),
        )
        object.__setattr__(
            self,
            "unfulfilled_contract_items",
            _copy_string_tuple(self.unfulfilled_contract_items, cap=12, limit=160),
        )
        object.__setattr__(
            self,
            "ordinary_next_queries",
            _copy_string_tuple(self.ordinary_next_queries, cap=8, limit=180),
        )
        object.__setattr__(self, "metadata", _json_safe_mapping(self.metadata))


def build_conflict_state(
    producer_input: ConflictStateProducerInput,
    *,
    classifier: BoundedConflictClassifier | None = None,
) -> ConflictState:
    """Build a conservative conflict state from sanitized runtime evidence."""

    if classifier is not None:
        return classifier.classify(producer_input)

    claims = _extract_effective_date_claims(producer_input)
    metadata_only = _metadata_only_source_class_signal(producer_input)
    claim_pair = _first_tension_pair(claims)
    ordinary_next_queries = _copy_string_tuple(producer_input.ordinary_next_queries)

    if claim_pair is None:
        return ConflictState(
            conflicts_present=False,
            blockers=(
                ("metadata_only_signal",)
                if metadata_only
                else ("no_claim_pair",)
            ),
            ordinary_next_queries=ordinary_next_queries,
            metadata={
                "producer": _QUERY_SOURCE_DETERMINISTIC,
                "candidate_claim_count": len(claims),
            },
        )

    claim_a, claim_b = claim_pair
    refs = _copy_string_tuple(
        tuple(claim_a.source_refs) + tuple(claim_b.source_refs),
        cap=_MAX_REFS,
        limit=80,
    )
    stale_blocker = _stale_secondary_superseded_by_current_official(
        producer_input,
        claim_a,
        claim_b,
    )
    centrality = _centrality_for_conflict(producer_input, claim_a, claim_b)
    confidence = _confidence_for_conflict(claim_a, claim_b, stale_blocker)
    queries = (
        _resolving_queries_for_claim_pair(producer_input, claim_a, claim_b)
        if producer_input.allow_resolving_query_candidates
        else ()
    )
    blockers = _producer_blockers(
        refs=refs,
        centrality=centrality,
        queries=queries,
        confidence=confidence,
        stale_blocker=stale_blocker,
    )
    note = _conflict_note(claim_a, claim_b)
    query_source = _QUERY_SOURCE_DETERMINISTIC if queries else _QUERY_SOURCE_NONE
    provenance = (
        (
            f"{_QUERY_SOURCE_DETERMINISTIC}:{claim_a.claim_id}:{claim_b.claim_id}",
        )
        if queries
        else ()
    )
    return ConflictState(
        conflicts_present=True,
        conflict_notes=(note,),
        claims_in_tension=(claim_a, claim_b),
        evidence_refs=refs,
        centrality_to_contract=centrality,
        resolving_query_candidates=queries,
        resolving_query_source=query_source,
        resolving_query_provenance=provenance,
        confidence=confidence,
        blockers=blockers,
        ordinary_next_queries=ordinary_next_queries,
        metadata={
            "producer": _QUERY_SOURCE_DETERMINISTIC,
            "candidate_claim_count": len(claims),
        },
    )


def project_conflict_state_to_runtime_facts(
    conflict_state: ConflictState,
) -> dict[str, Any]:
    """Project producer output into RuntimeAnswerContractFacts fields."""

    runtime_conflict_present = (
        bool(conflict_state.conflicts_present)
        and conflict_state.centrality_to_contract == _CENTRAL
    )
    return {
        "conflicts_present": runtime_conflict_present,
        "conflict_notes": conflict_state.conflict_notes,
        "resolving_queries": (
            conflict_state.resolving_query_candidates
            if conflict_state.safe_to_dispatch_resolve_conflict
            else ()
        ),
    }


def _copy_string_tuple(
    value: Sequence[Any] | None,
    *,
    cap: int | None = None,
    limit: int = 200,
) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in value or ():
        text = _clean_text(item, limit=limit)
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
        if cap is not None and len(out) >= cap:
            break
    return tuple(out)


def _merge_string_tuples(*values: Sequence[Any] | None) -> tuple[str, ...]:
    merged: list[Any] = []
    for value in values:
        merged.extend(value or ())
    return _copy_string_tuple(merged)


def _clean_text(value: Any, *, limit: int) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def _clean_optional_text(value: Any, *, limit: int) -> str | None:
    text = _clean_text(value, limit=limit)
    return text or None


def _clean_enum(value: Any, *, allowed: frozenset[str], default: str) -> str:
    text = _clean_text(value, limit=80).casefold()
    return text if text in allowed else default


def _is_sensitive_key(key: Any) -> bool:
    text = str(key or "").strip().casefold()
    return text.startswith("raw_") or text in _SENSITIVE_KEYS


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(item) for item in value]
    return str(value)


def _json_safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, item in deepcopy(dict(value or {})).items():
        if _is_sensitive_key(key):
            continue
        out[str(key)] = _json_safe_value(item)
    return out


def _dedupe_claims(claims: Sequence[ConflictClaim]) -> tuple[ConflictClaim, ...]:
    out: list[ConflictClaim] = []
    seen: set[tuple[str | None, str | None, str | None, tuple[str, ...]]] = set()
    for claim in claims:
        normalized = claim if isinstance(claim, ConflictClaim) else None
        if normalized is None:
            continue
        key = (
            normalized.subject.casefold() if normalized.subject else None,
            normalized.attribute.casefold() if normalized.attribute else None,
            normalized.value.casefold() if normalized.value else None,
            tuple(ref.casefold() for ref in normalized.source_refs),
        )
        if key in seen:
            continue
        out.append(normalized)
        seen.add(key)
        if len(out) >= _MAX_CLAIMS:
            break
    return tuple(out)


def _is_safe_to_dispatch(
    *,
    conflicts_present: bool,
    claims: tuple[ConflictClaim, ...],
    refs: tuple[str, ...],
    centrality: str,
    query_candidates: tuple[str, ...],
    confidence: str,
    blockers: tuple[str, ...],
) -> bool:
    if not conflicts_present:
        return False
    if len(claims) < 2 or len(refs) < 2:
        return False
    if centrality != _CENTRAL:
        return False
    if not query_candidates:
        return False
    if confidence not in {_CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH}:
        return False
    return not blockers


def _source_ref(passage: Mapping[str, Any], index: int) -> str:
    source_id = passage.get("source_id") or index
    return _clean_text(f"source:{source_id}", limit=80)


def _source_class(passage: Mapping[str, Any]) -> str:
    source_class = passage.get("source_class") or passage.get("source_tier")
    text = _clean_text(source_class, limit=80).casefold()
    if text == "official":
        return "official_current_rules"
    if text in {"secondary", "trusted_community"}:
        return "reputable_secondary"
    return text or "unknown"


def _extract_effective_date_value(text: str) -> str | None:
    for pattern in _EFFECTIVE_DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            return _clean_text(match.group(1), limit=80)
    return None


def _explicit_claim_from_metadata(
    passage: Mapping[str, Any],
) -> tuple[str, str, str] | None:
    attribute = _clean_text(
        passage.get("conflict_claim_attribute") or passage.get("claim_attribute"),
        limit=80,
    ).casefold()
    value = _clean_text(
        passage.get("conflict_claim_value") or passage.get("claim_value"),
        limit=80,
    )
    subject = _clean_text(
        passage.get("conflict_claim_subject") or passage.get("claim_subject"),
        limit=120,
    )
    if attribute == "effective_date" and value and subject:
        return subject, attribute, value
    return None


def _extract_effective_date_claims(
    producer_input: ConflictStateProducerInput,
) -> tuple[ConflictClaim, ...]:
    claims: list[ConflictClaim] = []
    default_subject = (
        producer_input.primary_entity
        or producer_input.core_topic
        or producer_input.query
    )
    for index, passage in enumerate(producer_input.final_top_evidence or (), start=1):
        if not isinstance(passage, Mapping):
            continue
        metadata_claim = _explicit_claim_from_metadata(passage)
        text = _clean_text(
            f"{passage.get('title') or ''} {passage.get('text') or ''}",
            limit=_MAX_TEXT,
        )
        if metadata_claim is None:
            value = _extract_effective_date_value(text)
            subject = default_subject
            attribute = "effective_date"
        else:
            subject, attribute, value = metadata_claim
        if not value:
            continue
        source_ref = _source_ref(passage, index)
        source_class = _source_class(passage)
        claim_id = f"claim:{len(claims) + 1}"
        claims.append(
            ConflictClaim(
                claim_id=claim_id,
                normalized_claim=f"{subject} {attribute} {value}",
                value=value,
                attribute=attribute,
                subject=subject,
                source_refs=(source_ref,),
                source_classes=(source_class,),
            )
        )
    return tuple(claims)


def _first_tension_pair(
    claims: Sequence[ConflictClaim],
) -> tuple[ConflictClaim, ConflictClaim] | None:
    for idx, left in enumerate(claims):
        if not left.value or not left.attribute or not left.subject:
            continue
        for right in claims[idx + 1 :]:
            if not right.value or not right.attribute or not right.subject:
                continue
            same_subject = left.subject.casefold() == right.subject.casefold()
            same_attribute = left.attribute.casefold() == right.attribute.casefold()
            different_value = left.value.casefold() != right.value.casefold()
            if same_subject and same_attribute and different_value:
                return left, right
    return None


def _metadata_only_source_class_signal(
    producer_input: ConflictStateProducerInput,
) -> bool:
    telemetry = producer_input.source_class_observability
    missing = telemetry.get("missing_expected_source_classes")
    gap_candidates = telemetry.get("source_class_gap_candidates")
    status = telemetry.get("source_class_satisfaction_status")
    if missing or gap_candidates:
        return True
    if isinstance(status, Mapping):
        return any(
            str(item or "").casefold() in {"expected_but_only_secondary", "unsatisfied"}
            for item in status.values()
        )
    return False


def _passage_for_ref(
    producer_input: ConflictStateProducerInput,
    source_ref: str,
) -> Mapping[str, Any] | None:
    ref_id = source_ref.removeprefix("source:")
    for index, passage in enumerate(producer_input.final_top_evidence or (), start=1):
        if not isinstance(passage, Mapping):
            continue
        if str(passage.get("source_id") or index) == ref_id:
            return passage
    return None


def _claim_is_stale_secondary(
    producer_input: ConflictStateProducerInput,
    claim: ConflictClaim,
) -> bool:
    if "reputable_secondary" not in claim.source_classes:
        return False
    for source_ref in claim.source_refs:
        passage = _passage_for_ref(producer_input, source_ref)
        if passage is None:
            continue
        text = _clean_text(
            f"{passage.get('title') or ''} {passage.get('text') or ''}",
            limit=_MAX_TEXT,
        )
        if _STALE_TERMS.search(text):
            return True
    return False


def _stale_secondary_superseded_by_current_official(
    producer_input: ConflictStateProducerInput,
    claim_a: ConflictClaim,
    claim_b: ConflictClaim,
) -> bool:
    official_current = any(
        "official_current_rules" in claim.source_classes
        for claim in (claim_a, claim_b)
    )
    stale_secondary = any(
        _claim_is_stale_secondary(producer_input, claim)
        for claim in (claim_a, claim_b)
    )
    return official_current and stale_secondary


def _centrality_for_conflict(
    producer_input: ConflictStateProducerInput,
    claim_a: ConflictClaim,
    claim_b: ConflictClaim,
) -> str:
    context = " ".join(
        (
            producer_input.query,
            producer_input.core_topic or "",
            producer_input.answer_contract_family or "",
            " ".join(producer_input.must_satisfy),
            " ".join(producer_input.required_source_classes),
            " ".join(producer_input.unfulfilled_contract_items),
            claim_a.subject or "",
            claim_b.subject or "",
            claim_a.attribute or "",
        )
    ).casefold()
    terms = set(re.findall(r"[a-z][a-z0-9_]+", context))
    if "effective_date" in context and (
        terms & _CENTRAL_TERMS
    ) and ("current" in terms or "official" in terms or "rule" in terms or "rules" in terms):
        return _CENTRAL
    return _NOT_CENTRAL


def _confidence_for_conflict(
    claim_a: ConflictClaim,
    claim_b: ConflictClaim,
    stale_blocker: bool,
) -> str:
    if stale_blocker:
        return _CONFIDENCE_LOW
    classes = set(claim_a.source_classes) | set(claim_b.source_classes)
    if "official_current_rules" in classes and "reputable_secondary" in classes:
        return _CONFIDENCE_MEDIUM
    return _CONFIDENCE_LOW


def _resolving_queries_for_claim_pair(
    producer_input: ConflictStateProducerInput,
    claim_a: ConflictClaim,
    claim_b: ConflictClaim,
) -> tuple[str, ...]:
    subject = claim_a.subject or claim_b.subject
    attribute = (claim_a.attribute or claim_b.attribute or "").replace("_", " ")
    if not subject or not attribute:
        return ()
    base = _clean_text(
        f"{subject} official current {attribute} {claim_a.value} {claim_b.value}",
        limit=180,
    )
    regulator = _clean_text(
        f"{subject} regulator filing current {attribute}",
        limit=180,
    )
    return _copy_string_tuple((base, regulator), cap=_MAX_QUERIES, limit=180)


def _producer_blockers(
    *,
    refs: tuple[str, ...],
    centrality: str,
    queries: tuple[str, ...],
    confidence: str,
    stale_blocker: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if len(refs) < 2:
        blockers.append("insufficient_evidence_refs")
    if centrality != _CENTRAL:
        blockers.append("not_central_to_contract")
    if not queries:
        blockers.append("no_resolving_query_candidates")
    if confidence == _CONFIDENCE_LOW:
        blockers.append("low_confidence")
    if stale_blocker:
        blockers.append("stale_secondary_superseded_by_current_official")
    return tuple(blockers)


def _conflict_note(claim_a: ConflictClaim, claim_b: ConflictClaim) -> str:
    attribute = (claim_a.attribute or "claim").replace("_", " ")
    subject = claim_a.subject or claim_b.subject or "the requested subject"
    return _clean_text(
        f"{subject} {attribute} conflicts across evidence: "
        f"{claim_a.value} vs {claim_b.value}",
        limit=_MAX_NOTE,
    )


__all__ = [
    "BoundedConflictClassifier",
    "CONFLICT_STATE_SCHEMA_VERSION",
    "ConflictClaim",
    "ConflictState",
    "ConflictStateProducerInput",
    "build_conflict_state",
    "project_conflict_state_to_runtime_facts",
]
