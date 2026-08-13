"""Deterministic SearchWork query-shape and contract-resolution runtime.

This module derives AG-96C QueryShapeAssessment and ContractResolutionRecord
objects from safe post-contract runtime facts only. It does not generate query
text, select providers, execute search/retrieval, assemble prompts, or mutate
QueryPlan behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from core.query_shape_contract_resolution import (
    AssessmentConfidence,
    AssessmentPosture,
    ComponentCandidate,
    ContractResolutionRecord,
    EffectiveContractKind,
    FollowUpDepthPosture,
    ModeMismatchPosture,
    OutputPosture,
    ProviderJobCandidate,
    ProviderJobKind,
    QueryShapeAssessment,
    QueryShapeKind,
    SearchMode,
    SourceObligationCandidate,
    StopConditionKind,
    StopEscalateRefusePosture,
)
from core.semantic_contract_foundation import (
    SourceObligationKind,
    SourceObligationStrictness,
)

QUERY_SHAPE_RUNTIME_HELPER = "ag96e1_deterministic_query_shape_runtime"

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
_CURRENT_MARKERS = frozenset(
    {
        "current",
        "currently",
        "latest",
        "today",
        "now",
        "2026",
        "deadline",
        "fee",
        "fees",
        "rate",
        "rates",
        "threshold",
        "version",
    }
)
_OFFICIAL_MARKERS = frozenset(
    {
        "official",
        "government",
        "agency",
        "irs",
        "ssa",
        "uscis",
        "sec",
        "fda",
        "regulator",
        "regulated",
    }
)
_LEGAL_MARKERS = frozenset(
    {
        "law",
        "legal",
        "regulation",
        "regulatory",
        "statute",
        "deadline",
        "court",
        "jurisdiction",
        "compliance",
        "appeal",
        "tax",
    }
)
_CANONICAL_DOC_MARKERS = frozenset(
    {
        "api",
        "sdk",
        "parameter",
        "parameters",
        "docs",
        "documentation",
        "changelog",
        "release notes",
        "manual",
        "spec",
        "reference",
    }
)
_NUMERIC_MARKERS = frozenset(
    {
        "numeric",
        "number",
        "amount",
        "fee",
        "fees",
        "rate",
        "rates",
        "threshold",
        "percentage",
        "calculated",
        "calculation",
        "formula",
    }
)
_CONFLICT_MARKERS = frozenset(
    {
        "compare",
        "versus",
        " vs ",
        " vs. ",
        "conflict",
        "conflicting",
        "disagree",
        "reconcile",
        "reconciliation",
        "different sources",
    }
)
_STRUCTURED_COMPONENT_MINIMUM = 2
_STRUCTURED_COMPONENT_MAXIMUM = 5
_STRUCTURED_RETRIEVAL_VERBS = (
    "find",
    "identify",
    "determine",
    "state",
    "report",
    "locate",
)
_STRUCTURED_DIRECTIVE_VERBS = (
    "compare",
    "calculate",
    "compute",
    "convert",
    "explain",
    "show",
    "relate",
)
_STRUCTURED_INTERROGATIVE_VERBS = (
    "what",
    "who",
    "when",
    "where",
    "which",
    "must",
    "can",
    "does",
    "do",
    "is",
    "are",
    "how",
)
_RETRIEVAL_VERB_PATTERN = "(?:" + "|".join(_STRUCTURED_RETRIEVAL_VERBS) + ")"
_DIRECTIVE_VERB_PATTERN = "(?:" + "|".join(_STRUCTURED_DIRECTIVE_VERBS) + ")"
_INTERROGATIVE_VERB_PATTERN = (
    "(?:" + "|".join(_STRUCTURED_INTERROGATIVE_VERBS) + ")"
)
_NUMBERED_MARKER_RE = re.compile(
    r"(?<!\S)(?P<number>\d{1,2})(?P<punct>[.)])\s+"
)
_BULLET_MARKER_RE = re.compile(r"(?<!\S)(?P<punct>[-*])\s+")
_TRAILING_DIRECTIVE_BOUNDARY_RE = re.compile(
    rf"(?<=[.!?])\s+(?=(?:then\s+)?{_DIRECTIVE_VERB_PATTERN}\b)",
    flags=re.IGNORECASE,
)
_IMPERATIVE_SENTENCE_BOUNDARY_RE = re.compile(
    rf"(?<=[.!?])\s+(?=(?:{_RETRIEVAL_VERB_PATTERN}|"
    rf"(?:then\s+)?{_DIRECTIVE_VERB_PATTERN})\b)",
    flags=re.IGNORECASE,
)
_BOUNDED_CONTEXTUAL_PREAMBLE_RE = re.compile(
    r"^for\s+the\s+fictional\s+"
    r"[a-z0-9][a-z0-9 '&()/.,-]{0,160}:$",
    flags=re.IGNORECASE,
)


class _StructuredRoutePosture(str, Enum):
    QUALIFIED = "QUALIFIED"
    NOT_STRUCTURED = "NOT_STRUCTURED"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True, slots=True)
class _StructuredMulticomponentShape:
    posture: _StructuredRoutePosture
    component_items: tuple[str, ...] = ()
    requested_synthesis_directive: str | None = None
    syntax_kind: str | None = None
    newly_licensed_route_form: bool = False


@dataclass(frozen=True, slots=True)
class DeterministicSearchWorkRuntimeInput:
    """Safe inputs for deterministic SearchWorkPlan record construction."""

    contract_id: str
    run_contract_projection: Mapping[str, Any]
    route_facts: Mapping[str, Any]
    requested_mode: str | None = None
    selected_depth: str | None = None
    safe_query_preview: str | None = None
    current_date_ref: str | Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class DeterministicSearchWorkRuntimeRecords:
    """Valid AG-96C records produced by the deterministic runtime path."""

    query_shape_assessment: QueryShapeAssessment
    contract_resolution: ContractResolutionRecord
    fallback_reason: str | None = None

    @property
    def used_real_path(self) -> bool:
        return self.fallback_reason is None


def build_deterministic_search_work_runtime_records(
    runtime_input: DeterministicSearchWorkRuntimeInput,
) -> DeterministicSearchWorkRuntimeRecords:
    """Build real deterministic AG-96C query-shape and contract records."""

    contract = _safe_mapping(runtime_input.run_contract_projection)
    route_facts = _safe_mapping(runtime_input.route_facts)
    safe_preview = _clean_text(runtime_input.safe_query_preview, limit=1000)
    text = _text_blob(
        safe_preview,
        route_facts.get("intent"),
        route_facts.get("report_type"),
        route_facts.get("query_type"),
        route_facts.get("core_topic"),
        route_facts.get("primary_entity"),
        contract.get("question_type"),
        contract.get("claim_type"),
        *(contract.get("selected_template_ids") or ()),
    )
    requested_mode = _coerce_search_mode(
        runtime_input.requested_mode
        or runtime_input.selected_depth
        or contract.get("selected_depth")
    )
    structured_shape = _assess_structured_multicomponent_shape(safe_preview or "")
    requirement_obligations = _obligations_from_contract_requirements(contract)
    inferred_obligations = _inferred_obligation_kinds(text)
    obligation_kinds = _ordered_obligation_kinds(
        requirement_obligations + inferred_obligations
    )
    components = _component_specs(
        text=text,
        safe_preview=safe_preview,
        route_facts=route_facts,
        obligation_kinds=obligation_kinds,
        structured_shape=structured_shape,
    )
    obligation_candidates = _source_obligation_candidates(
        obligation_kinds=obligation_kinds,
        components=components,
        contract=contract,
        text=text,
    )
    provider_candidates = _provider_job_candidates(obligation_candidates, text=text)
    component_candidates = _component_candidates(
        components=components,
        obligation_candidates=obligation_candidates,
        provider_candidates=provider_candidates,
        route_facts=route_facts,
    )
    query_shape_kinds = _query_shape_kinds(
        text=text,
        component_count=len(component_candidates),
        obligation_kinds=obligation_kinds,
        contract=contract,
    )
    assessment = QueryShapeAssessment(
        assessment_id=f"assessment:{runtime_input.contract_id}:ag96e1",
        requested_mode=requested_mode,
        query_shape_kinds=query_shape_kinds,
        assessment_confidence=AssessmentConfidence.MEDIUM,
        assessment_posture=AssessmentPosture.DETERMINISTIC_SIGNAL_ONLY,
        component_candidates=component_candidates,
        source_obligation_candidates=obligation_candidates,
        provider_job_candidates=provider_candidates,
        first_pass_evidence_needed={
            "answer_bearing_source_custody": bool(obligation_candidates),
            "official_or_currentness_confirmation": any(
                kind
                in {
                    SourceObligationKind.OFFICIAL_CURRENT,
                    SourceObligationKind.LEGAL_CURRENT_PRIMARY,
                    SourceObligationKind.CANONICAL_DOCUMENTATION,
                    SourceObligationKind.SOURCE_BOUND_NUMERIC,
                }
                for kind in obligation_kinds
            ),
            "conflict_or_currentness_confirmation": (
                SourceObligationKind.CONFLICT_RESOLUTION in obligation_kinds
                or QueryShapeKind.TIME_SENSITIVE in query_shape_kinds
            ),
        },
        deterministic_signals=_deterministic_signals(query_shape_kinds, obligation_kinds),
        ambiguity_notes=_ambiguity_notes(text),
        normalization_notes=_normalization_notes(component_candidates),
        stop_condition_candidates=_stop_conditions(obligation_kinds, query_shape_kinds),
        metadata={
            "phase": "AG-96E1",
            "helper": QUERY_SHAPE_RUNTIME_HELPER,
            "implements_query_shape_classifier": True,
            "safe_structured_inputs_only": True,
            "safe_preview_used": bool(safe_preview),
            "behavior_changed": False,
            "query_plan_behavior_changed": False,
            "provider_search_behavior_changed": False,
            "structured_route_posture": structured_shape.posture.value,
            "structured_route_syntax_kind": structured_shape.syntax_kind,
            "newly_licensed_route_form": (
                structured_shape.newly_licensed_route_form
            ),
            "route_qualification_behavior_changed": (
                structured_shape.posture is _StructuredRoutePosture.QUALIFIED
                and structured_shape.newly_licensed_route_form
            ),
            "explicit_factual_component_list": (
                structured_shape.posture is _StructuredRoutePosture.QUALIFIED
            ),
            "requested_synthesis_directive": (
                structured_shape.requested_synthesis_directive
                if structured_shape.posture is _StructuredRoutePosture.QUALIFIED
                else None
            ),
        },
    ).require_valid()
    resolution = _contract_resolution(
        contract_id=runtime_input.contract_id,
        requested_mode=requested_mode,
        selected_depth=runtime_input.selected_depth or contract.get("selected_depth"),
        query_shape_kinds=query_shape_kinds,
        obligation_kinds=obligation_kinds,
    )
    return DeterministicSearchWorkRuntimeRecords(
        query_shape_assessment=assessment,
        contract_resolution=resolution,
    )


def _component_specs(
    *,
    text: str,
    safe_preview: str | None,
    route_facts: Mapping[str, Any],
    obligation_kinds: Sequence[SourceObligationKind],
    structured_shape: _StructuredMulticomponentShape,
) -> tuple[dict[str, Any], ...]:
    preview = safe_preview or _clean_text(route_facts.get("core_topic"), limit=220)
    raw_parts = (
        structured_shape.component_items
        if structured_shape.posture is _StructuredRoutePosture.QUALIFIED
        else _split_multipart(preview or "")
    )
    if not raw_parts:
        raw_parts = (preview or _clean_text(route_facts.get("primary_entity"), limit=160) or "primary lookup",)
    specs: list[dict[str, Any]] = []
    for index, part in enumerate(raw_parts, start=1):
        part_text = _clean_text(part, limit=220) or f"component {index}"
        part_blob = _text_blob(part_text)
        specs.append(
            {
                "component_id": f"component-{index}",
                "subquestion": _subquestion(part_text),
                "text": part_blob,
                "obligation_kinds": _component_obligation_kinds(
                    part_blob,
                    obligation_kinds,
                ),
            }
        )
    return tuple(specs)


def _assess_structured_multicomponent_shape(
    preview: str,
) -> _StructuredMulticomponentShape:
    """Classify only explicit bounded structures that can authorize the lane."""

    text = _clean_text(preview, limit=1000) or ""
    if not text:
        return _not_structured_shape()

    numbered_matches = tuple(_NUMBERED_MARKER_RE.finditer(text))
    bullet_matches = tuple(_BULLET_MARKER_RE.finditer(text))
    if numbered_matches and bullet_matches:
        return _ambiguous_structured_shape()
    if numbered_matches:
        if not _is_bounded_contextual_preamble(
            text[: numbered_matches[0].start()]
        ):
            return _ambiguous_structured_shape()
        numbers = tuple(int(match.group("number")) for match in numbered_matches)
        punctuation = {match.group("punct") for match in numbered_matches}
        if numbers != tuple(range(1, len(numbers) + 1)) or len(punctuation) != 1:
            return _ambiguous_structured_shape()
        return _assess_structured_item_sequence(
            _marked_items(text, numbered_matches),
            syntax_family="numbered",
        )
    if bullet_matches:
        if not _is_bounded_contextual_preamble(
            text[: bullet_matches[0].start()]
        ):
            return _ambiguous_structured_shape()
        punctuation = {match.group("punct") for match in bullet_matches}
        if len(punctuation) != 1:
            return _ambiguous_structured_shape()
        return _assess_structured_item_sequence(
            _marked_items(text, bullet_matches),
            syntax_family="bullet",
        )

    imperative_sequence = _bounded_imperative_clause_items(text)
    if imperative_sequence is None:
        return _not_structured_shape()
    imperative_preamble, imperative_items = imperative_sequence
    if not _is_bounded_contextual_preamble(imperative_preamble):
        return _ambiguous_structured_shape()
    return _assess_structured_item_sequence(
        imperative_items,
        syntax_family="imperative_clauses",
    )


def _marked_items(
    text: str,
    matches: Sequence[re.Match[str]],
) -> tuple[str, ...]:
    return tuple(
        text[match.end() : matches[index + 1].start()].strip()
        if index + 1 < len(matches)
        else text[match.end() :].strip()
        for index, match in enumerate(matches)
    )


def _bounded_imperative_clause_items(
    text: str,
) -> tuple[str, tuple[str, ...]] | None:
    starts_with_retrieval = re.match(
        rf"^{_RETRIEVAL_VERB_PATTERN}\b",
        text,
        flags=re.IGNORECASE,
    )
    contextual_preamble = ""
    body = text
    if starts_with_retrieval is None:
        introducer = re.search(
            rf":\s+(?={_RETRIEVAL_VERB_PATTERN}\b)",
            text,
            flags=re.IGNORECASE,
        )
        if introducer is None:
            return None
        contextual_preamble = text[: introducer.start() + 1]
        body = text[introducer.end() :]
    if ";" in body:
        items = tuple(part.strip() for part in re.split(r"\s*;\s*", body))
    else:
        items = tuple(
            part.strip() for part in _IMPERATIVE_SENTENCE_BOUNDARY_RE.split(body)
        )
    if len(items) < 2:
        return None
    return contextual_preamble, items


def _is_bounded_contextual_preamble(text: str) -> bool:
    cleaned = _clean_text(text, limit=1000) or ""
    if not cleaned:
        return True
    if len(cleaned) > 180:
        return False
    if _NUMBERED_MARKER_RE.search(cleaned) or _BULLET_MARKER_RE.search(cleaned):
        return False
    if re.search(
        rf"\b(?:{_RETRIEVAL_VERB_PATTERN}|{_DIRECTIVE_VERB_PATTERN}|"
        rf"{_INTERROGATIVE_VERB_PATTERN})\b",
        cleaned,
        flags=re.IGNORECASE,
    ):
        return False
    return bool(_BOUNDED_CONTEXTUAL_PREAMBLE_RE.fullmatch(cleaned))


def _assess_structured_item_sequence(
    items: Sequence[str],
    *,
    syntax_family: str,
) -> _StructuredMulticomponentShape:
    raw_items = list(items)
    if not raw_items or any(not item for item in raw_items):
        return _ambiguous_structured_shape()

    split_component, split_directive = _split_trailing_directive(raw_items[-1])
    if split_directive is not None:
        raw_items[-1] = split_component or ""
        raw_items.append(split_directive)
    if any(not item for item in raw_items):
        return _ambiguous_structured_shape()

    kinds = tuple(_structured_item_kind(item) for item in raw_items)
    if any(kind in {"invalid", "mixed"} for kind in kinds):
        return _ambiguous_structured_shape()
    directive_indexes = [
        index for index, kind in enumerate(kinds) if kind == "directive"
    ]
    if directive_indexes != [len(raw_items) - 1]:
        return _ambiguous_structured_shape()

    component_kinds = kinds[:-1]
    if not component_kinds or len(set(component_kinds)) != 1:
        return _ambiguous_structured_shape()
    if syntax_family == "imperative_clauses" and component_kinds[0] != "imperative":
        return _ambiguous_structured_shape()

    components = tuple(
        _clean_structured_component(item, kind=component_kinds[index])
        for index, item in enumerate(raw_items[:-1])
    )
    if any(not component for component in components):
        return _ambiguous_structured_shape()
    if not (
        _STRUCTURED_COMPONENT_MINIMUM
        <= len(components)
        <= _STRUCTURED_COMPONENT_MAXIMUM
    ):
        return _ambiguous_structured_shape()
    if len({component.casefold() for component in components}) != len(components):
        return _ambiguous_structured_shape()

    directive = _clean_text(raw_items[-1], limit=1000)
    if (
        directive is None
        or len(directive) > 360
        or _directive_contains_following_component(directive)
    ):
        return _ambiguous_structured_shape()
    component_kind = component_kinds[0]
    syntax_kind = (
        syntax_family
        if syntax_family == "imperative_clauses"
        else f"{syntax_family}_{component_kind}"
    )
    return _StructuredMulticomponentShape(
        posture=_StructuredRoutePosture.QUALIFIED,
        component_items=components,
        requested_synthesis_directive=directive,
        syntax_kind=syntax_kind,
        newly_licensed_route_form=(
            syntax_family != "bullet" or component_kind == "imperative"
        ),
    )


def _split_trailing_directive(item: str) -> tuple[str | None, str | None]:
    if _starts_with_directive(item):
        return item, None
    boundary = _TRAILING_DIRECTIVE_BOUNDARY_RE.search(item)
    if boundary is None:
        return item, None
    return item[: boundary.start()].strip(), item[boundary.end() :].strip()


def _structured_item_kind(item: str) -> str:
    cleaned = _clean_text(item, limit=500) or ""
    if _starts_with_directive(cleaned):
        return (
            "mixed"
            if _directive_contains_following_component(cleaned)
            else "directive"
        )
    if re.match(
        rf"^{_INTERROGATIVE_VERB_PATTERN}\b",
        cleaned,
        flags=re.IGNORECASE,
    ):
        if not cleaned.endswith("?") or _contains_directive_verb(cleaned):
            return "mixed"
        return "interrogative"
    if re.match(
        rf"^{_RETRIEVAL_VERB_PATTERN}\b",
        cleaned,
        flags=re.IGNORECASE,
    ):
        return "mixed" if _contains_directive_verb(cleaned) else "imperative"
    return "invalid"


def _starts_with_directive(text: str) -> bool:
    return bool(
        re.match(
            rf"^(?:then\s+)?{_DIRECTIVE_VERB_PATTERN}\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _contains_directive_verb(text: str) -> bool:
    return bool(
        re.search(
            rf"\b{_DIRECTIVE_VERB_PATTERN}\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _directive_contains_following_component(text: str) -> bool:
    return bool(
        re.search(
            rf"(?:[.!?;]\s+|,\s*and\s+|\band\s+)"
            rf"(?:then\s+)?(?:{_RETRIEVAL_VERB_PATTERN}\b|"
            rf"{_INTERROGATIVE_VERB_PATTERN}\b[^?]{{2,240}}\?)",
            text,
            flags=re.IGNORECASE,
        )
    )


def _clean_structured_component(item: str, *, kind: str) -> str:
    if kind == "interrogative":
        return _clean_question(item)
    cleaned = _clean_text(item, limit=220) or ""
    cleaned = re.sub(
        rf"^{_RETRIEVAL_VERB_PATTERN}\s+(?:the\s+)?",
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE,
    )
    return cleaned.strip(" ?.,")


def _not_structured_shape() -> _StructuredMulticomponentShape:
    return _StructuredMulticomponentShape(
        posture=_StructuredRoutePosture.NOT_STRUCTURED
    )


def _ambiguous_structured_shape() -> _StructuredMulticomponentShape:
    return _StructuredMulticomponentShape(posture=_StructuredRoutePosture.AMBIGUOUS)


def _split_multipart(preview: str) -> tuple[str, ...]:
    text = _clean_text(preview, limit=1000) or ""
    if not text:
        return ()
    explicit_questions = _explicit_question_list(text)
    if 2 <= len(explicit_questions) <= 6:
        return explicit_questions
    lower = text.casefold()
    if lower.startswith("compare ") and " and " in lower:
        body = text[8:]
        marker = " using "
        if marker in body.casefold():
            body = body[: body.casefold().index(marker)]
        pieces = _split_once_and(body)
        if len(pieces) == 2:
            return tuple(f"Compare {piece}" for piece in pieces)
    if " and how " in lower:
        left, right = text.split(" and how ", 1)
        return (_clean_question(left), _clean_question("How " + right))
    normalized = text.replace(", and ", ",").replace(";", ",")
    parts = normalized.split(",") if "," in normalized else normalized.split(" and ")
    cleaned = tuple(
        item
        for item in (_clean_question(part) for part in parts)
        if item and len(item.split()) >= 2
    )
    if len(cleaned) > 1:
        return cleaned[:6]
    return ()


def _explicit_question_list(text: str) -> tuple[str, ...]:
    """Return explicit question-list items from the existing safe query preview.

    This extends the accepted deterministic query-shape planner; it is not a
    second decomposition authority.  Only independently punctuated questions
    are admitted as components, while a trailing explanation directive remains
    request-level synthesis posture.
    """

    matches = re.findall(
        r"(?:^|\s[-*]\s+)((?:what|who|when|where|which|must|can|does|do|is|are|how)\b[^?]{2,240}\?)",
        text,
        flags=re.IGNORECASE,
    )
    return tuple(
        item
        for item in (_clean_question(match) for match in matches)
        if item and len(item.split()) >= 2
    )[:6]


def _split_once_and(text: str) -> tuple[str, ...]:
    if " and " not in text.casefold():
        return ()
    lower = text.casefold()
    index = lower.index(" and ")
    return (
        _clean_question(text[:index]),
        _clean_question(text[index + len(" and ") :]),
    )


def _clean_question(text: str) -> str:
    cleaned = _clean_text(text, limit=220) or ""
    prefixes = (
        "what are the ",
        "what is the ",
        "what are ",
        "what is ",
        "find the ",
        "find ",
    )
    lowered = cleaned.casefold()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break
    return cleaned.strip(" ?.,")


def _subquestion(part_text: str) -> str:
    text = part_text.strip()
    if text.endswith("?"):
        return text
    if text.casefold().startswith(("how ", "compare ")):
        return f"{text}."
    return f"Answer the {text} component."


def _component_obligation_kinds(
    part_text: str,
    obligation_kinds: Sequence[SourceObligationKind],
) -> tuple[SourceObligationKind, ...]:
    strict = [
        kind
        for kind in obligation_kinds
        if kind is not SourceObligationKind.REPUTABLE_SECONDARY
    ]
    local = [
        kind
        for kind in _inferred_obligation_kinds(part_text)
        if kind is not SourceObligationKind.REPUTABLE_SECONDARY
    ]
    if local:
        return tuple(kind for kind in local if kind in obligation_kinds or kind in strict)
    matched = [
        kind
        for kind in strict
        if _kind_text_match(kind, part_text)
    ]
    if matched:
        return tuple(matched)
    if len(strict) == 1:
        return tuple(strict)
    if not strict and SourceObligationKind.REPUTABLE_SECONDARY in obligation_kinds:
        return (SourceObligationKind.REPUTABLE_SECONDARY,)
    return ()


def _source_obligation_candidates(
    *,
    obligation_kinds: Sequence[SourceObligationKind],
    components: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
    text: str,
) -> tuple[SourceObligationCandidate, ...]:
    requirements = _requirements_by_kind(contract)
    candidates: list[SourceObligationCandidate] = []
    for kind in obligation_kinds:
        component_ids = tuple(
            str(component["component_id"])
            for component in components
            if kind in component.get("obligation_kinds", ())
            or (
                kind is SourceObligationKind.REPUTABLE_SECONDARY
                and not _strict_component_obligations(component)
            )
        )
        if not component_ids:
            component_ids = tuple(str(component["component_id"]) for component in components[:1])
        requirement = requirements.get(kind, {})
        strict = kind in {
            SourceObligationKind.OFFICIAL_CURRENT,
            SourceObligationKind.LEGAL_CURRENT_PRIMARY,
            SourceObligationKind.CANONICAL_DOCUMENTATION,
            SourceObligationKind.SOURCE_BOUND_NUMERIC,
            SourceObligationKind.CONFLICT_RESOLUTION,
        }
        candidates.append(
            SourceObligationCandidate(
                candidate_id=f"obligation:{kind.value}",
                obligation_id=f"ag96e1:{kind.value}",
                component_ids=component_ids,
                kind=kind,
                strictness=(
                    SourceObligationStrictness.REQUIRED
                    if strict
                    else SourceObligationStrictness.PREFERRED
                ),
                required_source_class=_required_source_class(kind, requirement),
                currentness_requirement=_currentness_requirement(kind, requirement, text),
                satisfaction_rule=_satisfaction_rule(kind, requirement),
                lower_tier_use=_lower_tier_use(kind, requirement),
                lower_tier_final_satisfaction_allowed=not strict,
                metadata={
                    "phase": "AG-96E1",
                    "deterministic_runtime": True,
                    "lower_tier_final_satisfaction_allowed": not strict,
                },
            )
        )
    return tuple(candidates)


def _provider_job_candidates(
    obligations: Sequence[SourceObligationCandidate],
    *,
    text: str,
) -> tuple[ProviderJobCandidate, ...]:
    candidates: list[ProviderJobCandidate] = []
    for obligation in obligations:
        for job_kind in _provider_job_kinds_for_obligation(obligation.kind, text):
            candidate_id = f"provider:{obligation.kind.value}:{job_kind.value}"
            candidates.append(
                ProviderJobCandidate(
                    candidate_id=candidate_id,
                    provider_job_id=f"ag96e1:{obligation.kind.value}:{job_kind.value}",
                    component_ids=obligation.component_ids,
                    job_kind=job_kind,
                    source_obligation_candidate_ids=(obligation.candidate_id,),
                    provider_name_neutral=True,
                    metadata={
                        "phase": "AG-96E1",
                        "deterministic_runtime": True,
                        "hint_only": True,
                        "executes_search": False,
                        "provider_selected": False,
                        "search_executed": False,
                    },
                )
            )
    return tuple(candidates)


def _component_candidates(
    *,
    components: Sequence[Mapping[str, Any]],
    obligation_candidates: Sequence[SourceObligationCandidate],
    provider_candidates: Sequence[ProviderJobCandidate],
    route_facts: Mapping[str, Any],
) -> tuple[ComponentCandidate, ...]:
    candidates: list[ComponentCandidate] = []
    entities = _route_entities(route_facts)
    for component in components:
        component_id = str(component["component_id"])
        obligation_ids = tuple(
            candidate.candidate_id
            for candidate in obligation_candidates
            if component_id in candidate.component_ids
        )
        provider_ids = tuple(
            candidate.candidate_id
            for candidate in provider_candidates
            if component_id in candidate.component_ids
        )
        candidates.append(
            ComponentCandidate(
                candidate_id=f"component:{component_id}",
                component_id=component_id,
                user_facing_subquestion=str(component["subquestion"]),
                entities=entities,
                source_obligation_candidate_ids=obligation_ids,
                provider_job_candidate_ids=provider_ids,
                metadata={
                    "phase": "AG-96E1",
                    "deterministic_runtime": True,
                    "multipart_candidate": len(components) > 1,
                },
            )
        )
    return tuple(candidates)


def _contract_resolution(
    *,
    contract_id: str,
    requested_mode: SearchMode,
    selected_depth: Any,
    query_shape_kinds: Sequence[QueryShapeKind],
    obligation_kinds: Sequence[SourceObligationKind],
) -> ContractResolutionRecord:
    effective_contract = _effective_contract_for_mode(requested_mode)
    mismatch = _mode_mismatch_posture(
        requested_mode=requested_mode,
        query_shape_kinds=query_shape_kinds,
        obligation_kinds=obligation_kinds,
    )
    resolution = ContractResolutionRecord(
        resolution_id=f"resolution:{contract_id}:ag96e1",
        requested_mode=requested_mode,
        effective_contract=effective_contract,
        mode_mismatch_posture=mismatch,
        allowed_follow_up_depth=_follow_up_depth_for_mode(requested_mode),
        output_posture=_output_posture_for_mode(requested_mode),
        stop_escalate_refuse_posture=_stop_posture_for_mismatch(mismatch),
        rationale=(
            "Deterministic AG-96E1 resolver maps requested Fast/Balanced/Deep "
            "to answer contracts while recording shadow-only complexity pressure."
        ),
        metadata={
            "phase": "AG-96E1",
            "helper": QUERY_SHAPE_RUNTIME_HELPER,
            "implements_contract_resolver": True,
            "selected_depth": _clean_token(selected_depth),
            "complexity_pressure_recorded": mismatch is not ModeMismatchPosture.NONE,
            "runtime_mode_mutated": False,
            "query_plan_behavior_changed": False,
        },
    )
    return resolution.require_valid()


def _mode_mismatch_posture(
    *,
    requested_mode: SearchMode,
    query_shape_kinds: Sequence[QueryShapeKind],
    obligation_kinds: Sequence[SourceObligationKind],
) -> ModeMismatchPosture:
    strict_count = sum(
        1
        for kind in obligation_kinds
        if kind
        in {
            SourceObligationKind.OFFICIAL_CURRENT,
            SourceObligationKind.LEGAL_CURRENT_PRIMARY,
            SourceObligationKind.CANONICAL_DOCUMENTATION,
            SourceObligationKind.SOURCE_BOUND_NUMERIC,
            SourceObligationKind.CONFLICT_RESOLUTION,
        }
    )
    deep_pressure = (
        QueryShapeKind.CONFLICT_LIKELY in query_shape_kinds
        or SourceObligationKind.CONFLICT_RESOLUTION in obligation_kinds
        or (QueryShapeKind.MULTIPART in query_shape_kinds and strict_count >= 2)
    )
    moderate_pressure = (
        QueryShapeKind.MULTIPART in query_shape_kinds
        or QueryShapeKind.COMPARATIVE in query_shape_kinds
        or QueryShapeKind.LEGAL_CURRENT_PRIMARY in query_shape_kinds
        or QueryShapeKind.CANONICAL_DOCUMENTATION in query_shape_kinds
        or SourceObligationKind.CONFLICT_RESOLUTION in obligation_kinds
    )
    if requested_mode is SearchMode.FAST and moderate_pressure:
        return ModeMismatchPosture.SELECTED_MODE_INSUFFICIENT
    if requested_mode is SearchMode.BALANCED and deep_pressure:
        return ModeMismatchPosture.POSSIBLE
    return ModeMismatchPosture.NONE


def _effective_contract_for_mode(mode: SearchMode) -> EffectiveContractKind:
    if mode is SearchMode.DEEP:
        return EffectiveContractKind.RESEARCH_RECONCILIATION
    if mode is SearchMode.BALANCED:
        return EffectiveContractKind.EXPLANATORY
    if mode is SearchMode.FAST:
        return EffectiveContractKind.DIRECT_CONSTRAINED
    return EffectiveContractKind.AUTO_UNRESOLVED


def _follow_up_depth_for_mode(mode: SearchMode) -> FollowUpDepthPosture:
    if mode is SearchMode.DEEP:
        return FollowUpDepthPosture.LARGER_BOUNDED_LOOP
    if mode is SearchMode.BALANCED:
        return FollowUpDepthPosture.CONDITIONAL_GAP_DRIVEN
    return FollowUpDepthPosture.NONE_OR_MINIMAL


def _output_posture_for_mode(mode: SearchMode) -> OutputPosture:
    if mode is SearchMode.DEEP:
        return OutputPosture.RESOLVED_DEPTH
    if mode is SearchMode.BALANCED:
        return OutputPosture.COMPACT_EXPLANATORY
    return OutputPosture.DIRECT


def _stop_posture_for_mismatch(
    mismatch: ModeMismatchPosture,
) -> StopEscalateRefusePosture:
    if mismatch is ModeMismatchPosture.SELECTED_MODE_INSUFFICIENT:
        return StopEscalateRefusePosture.QUALIFY_IF_UNSATISFIED
    if mismatch is ModeMismatchPosture.ESCALATE_SUGGESTED:
        return StopEscalateRefusePosture.ESCALATE_SUGGESTED
    return StopEscalateRefusePosture.STOP_WHEN_SUFFICIENT


def _query_shape_kinds(
    *,
    text: str,
    component_count: int,
    obligation_kinds: Sequence[SourceObligationKind],
    contract: Mapping[str, Any],
) -> tuple[QueryShapeKind, ...]:
    kinds: list[QueryShapeKind] = []
    if component_count > 1:
        kinds.append(QueryShapeKind.MULTIPART)
    else:
        kinds.append(QueryShapeKind.SIMPLE_LOOKUP)
    if _has_any(text, _CONFLICT_MARKERS):
        kinds.append(QueryShapeKind.COMPARATIVE)
    if SourceObligationKind.OFFICIAL_CURRENT in obligation_kinds:
        kinds.append(QueryShapeKind.OFFICIAL_CURRENT_LOOKUP)
    if SourceObligationKind.LEGAL_CURRENT_PRIMARY in obligation_kinds:
        kinds.append(QueryShapeKind.LEGAL_CURRENT_PRIMARY)
    if SourceObligationKind.CANONICAL_DOCUMENTATION in obligation_kinds:
        kinds.append(QueryShapeKind.CANONICAL_DOCUMENTATION)
    if SourceObligationKind.SOURCE_BOUND_NUMERIC in obligation_kinds:
        kinds.append(QueryShapeKind.SOURCE_BOUND_NUMERIC)
    if _has_any(text, _CURRENT_MARKERS) or _contract_has_currentness(contract):
        kinds.append(QueryShapeKind.TIME_SENSITIVE)
    if (
        SourceObligationKind.CONFLICT_RESOLUTION in obligation_kinds
        or _has_any(text, _CONFLICT_MARKERS)
        or _has_conflict_policy(contract)
    ):
        kinds.append(QueryShapeKind.CONFLICT_LIKELY)
    if (
        SourceObligationKind.SOURCE_BOUND_NUMERIC in obligation_kinds
        and QueryShapeKind.COMPARATIVE in kinds
    ):
        kinds.append(QueryShapeKind.QUANTITATIVE_COMPARISON)
    return _dedupe(kinds)


def _inferred_obligation_kinds(text: str) -> list[SourceObligationKind]:
    kinds: list[SourceObligationKind] = []
    legal = _has_any(text, _LEGAL_MARKERS) and (
        _has_any(text, _CURRENT_MARKERS) or "current" in text
    )
    canonical = _has_any(text, _CANONICAL_DOC_MARKERS)
    source_numeric = _has_any(text, _NUMERIC_MARKERS)
    official = _has_any(text, _OFFICIAL_MARKERS) and (
        _has_any(text, _CURRENT_MARKERS) or source_numeric
    )
    conflict = _has_any(text, _CONFLICT_MARKERS)
    if official:
        kinds.append(SourceObligationKind.OFFICIAL_CURRENT)
    if legal:
        kinds.append(SourceObligationKind.LEGAL_CURRENT_PRIMARY)
    if canonical:
        kinds.append(SourceObligationKind.CANONICAL_DOCUMENTATION)
    if source_numeric:
        kinds.append(SourceObligationKind.SOURCE_BOUND_NUMERIC)
    if conflict:
        kinds.append(SourceObligationKind.CONFLICT_RESOLUTION)
    if not kinds:
        kinds.append(SourceObligationKind.REPUTABLE_SECONDARY)
    return kinds


def _obligations_from_contract_requirements(
    contract: Mapping[str, Any],
) -> list[SourceObligationKind]:
    kinds: list[SourceObligationKind] = []
    for requirement in _source_requirements(contract):
        kinds.append(_source_obligation_kind(requirement))
    return kinds


def _ordered_obligation_kinds(
    values: Sequence[SourceObligationKind],
) -> tuple[SourceObligationKind, ...]:
    ordered = (
        SourceObligationKind.OFFICIAL_CURRENT,
        SourceObligationKind.LEGAL_CURRENT_PRIMARY,
        SourceObligationKind.CANONICAL_DOCUMENTATION,
        SourceObligationKind.SOURCE_BOUND_NUMERIC,
        SourceObligationKind.CONFLICT_RESOLUTION,
        SourceObligationKind.REPUTABLE_SECONDARY,
        SourceObligationKind.NO_SPECIAL_OBLIGATION,
    )
    strict = [
        kind
        for kind in ordered
        if kind in values and kind is not SourceObligationKind.REPUTABLE_SECONDARY
    ]
    if strict:
        return tuple(strict)
    if SourceObligationKind.REPUTABLE_SECONDARY in values:
        return (SourceObligationKind.REPUTABLE_SECONDARY,)
    return (SourceObligationKind.NO_SPECIAL_OBLIGATION,)


def _requirements_by_kind(
    contract: Mapping[str, Any],
) -> dict[SourceObligationKind, Mapping[str, Any]]:
    out: dict[SourceObligationKind, Mapping[str, Any]] = {}
    for requirement in _source_requirements(contract):
        out.setdefault(_source_obligation_kind(requirement), requirement)
    return out


def _source_requirements(contract: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    requirements = contract.get("source_requirements")
    if not isinstance(requirements, Sequence) or isinstance(requirements, str):
        requirements = contract.get("source_requirement_summary")
    if not isinstance(requirements, Sequence) or isinstance(requirements, str):
        return ()
    return tuple(item for item in requirements if isinstance(item, Mapping))


def _source_obligation_kind(requirement: Mapping[str, Any]) -> SourceObligationKind:
    raw = str(
        requirement.get("requirement_kind")
        or requirement.get("kind")
        or requirement.get("required_source_class")
        or requirement.get("source_class")
        or ""
    ).casefold()
    if "legal" in raw or "regulatory" in raw:
        return SourceObligationKind.LEGAL_CURRENT_PRIMARY
    if "canonical" in raw or "docs" in raw or "primary_source_documents" in raw:
        return SourceObligationKind.CANONICAL_DOCUMENTATION
    if "source_bound_numeric" in raw or "sourced_numeric" in raw or "numeric" in raw:
        return SourceObligationKind.SOURCE_BOUND_NUMERIC
    if "official" in raw or "current_rules" in raw:
        return SourceObligationKind.OFFICIAL_CURRENT
    if "conflict" in raw:
        return SourceObligationKind.CONFLICT_RESOLUTION
    if "reputable" in raw or "secondary" in raw:
        return SourceObligationKind.REPUTABLE_SECONDARY
    return SourceObligationKind.NO_SPECIAL_OBLIGATION


def _provider_job_kinds_for_obligation(
    kind: SourceObligationKind,
    text: str,
) -> tuple[ProviderJobKind, ...]:
    if kind is SourceObligationKind.OFFICIAL_CURRENT:
        return (ProviderJobKind.OFFICIAL_CANDIDATE_ACQUISITION,)
    if kind is SourceObligationKind.LEGAL_CURRENT_PRIMARY:
        return (
            ProviderJobKind.CANONICAL_EXTRACTION,
            ProviderJobKind.CONFLICT_CURRENTNESS_CHECK,
        )
    if kind is SourceObligationKind.CANONICAL_DOCUMENTATION:
        return (ProviderJobKind.CANONICAL_EXTRACTION,)
    if kind is SourceObligationKind.SOURCE_BOUND_NUMERIC:
        return (ProviderJobKind.FETCH_READ_EXTRACT,)
    if kind is SourceObligationKind.CONFLICT_RESOLUTION:
        return (ProviderJobKind.CONFLICT_CURRENTNESS_CHECK,)
    if _has_any(text, _CONFLICT_MARKERS):
        return (ProviderJobKind.CONFLICT_CURRENTNESS_CHECK,)
    return (ProviderJobKind.DIRECT_CANDIDATE_SEARCH,)


def _required_source_class(
    kind: SourceObligationKind,
    requirement: Mapping[str, Any],
) -> str | None:
    value = _clean_token(
        requirement.get("required_source_class")
        or requirement.get("source_class")
        or requirement.get("required_source_tier")
    )
    if value:
        return value
    return {
        SourceObligationKind.OFFICIAL_CURRENT: "official_current_rules",
        SourceObligationKind.LEGAL_CURRENT_PRIMARY: "legal_or_regulatory_text",
        SourceObligationKind.CANONICAL_DOCUMENTATION: "primary_source_documents",
        SourceObligationKind.SOURCE_BOUND_NUMERIC: "sourced_numeric_values",
        SourceObligationKind.CONFLICT_RESOLUTION: "conflict_reconciliation_sources",
        SourceObligationKind.REPUTABLE_SECONDARY: "reputable_secondary",
    }.get(kind)


def _currentness_requirement(
    kind: SourceObligationKind,
    requirement: Mapping[str, Any],
    text: str,
) -> str | None:
    value = _clean_token(
        requirement.get("required_currentness")
        or requirement.get("currentness_requirement")
    )
    if value:
        return value
    if kind in {
        SourceObligationKind.OFFICIAL_CURRENT,
        SourceObligationKind.LEGAL_CURRENT_PRIMARY,
        SourceObligationKind.CANONICAL_DOCUMENTATION,
    } or _has_any(text, _CURRENT_MARKERS):
        return "current"
    return None


def _satisfaction_rule(
    kind: SourceObligationKind,
    requirement: Mapping[str, Any],
) -> str | None:
    value = _clean_text(requirement.get("satisfaction_rule"), limit=260)
    if value:
        return value
    return {
        SourceObligationKind.OFFICIAL_CURRENT: "official/current source required",
        SourceObligationKind.LEGAL_CURRENT_PRIMARY: "current primary legal or regulatory source required",
        SourceObligationKind.CANONICAL_DOCUMENTATION: "canonical documentation source required",
        SourceObligationKind.SOURCE_BOUND_NUMERIC: "numeric value must be bound to a source",
        SourceObligationKind.CONFLICT_RESOLUTION: "conflicts must be preserved or reconciled",
        SourceObligationKind.REPUTABLE_SECONDARY: "reputable secondary sources may satisfy ordinary lookup",
    }.get(kind)


def _lower_tier_use(
    kind: SourceObligationKind,
    requirement: Mapping[str, Any],
) -> str | None:
    value = _clean_text(
        requirement.get("allowed_lower_tier_use")
        or requirement.get("lower_tier_use"),
        limit=220,
    )
    if value:
        return value
    if kind in {
        SourceObligationKind.OFFICIAL_CURRENT,
        SourceObligationKind.LEGAL_CURRENT_PRIMARY,
        SourceObligationKind.CANONICAL_DOCUMENTATION,
        SourceObligationKind.SOURCE_BOUND_NUMERIC,
        SourceObligationKind.CONFLICT_RESOLUTION,
    }:
        return "leads_or_context_only"
    return "may_satisfy_when_no_stronger_obligation_applies"


def _strict_component_obligations(component: Mapping[str, Any]) -> tuple[SourceObligationKind, ...]:
    return tuple(
        kind
        for kind in component.get("obligation_kinds", ())
        if kind is not SourceObligationKind.REPUTABLE_SECONDARY
    )


def _kind_text_match(kind: SourceObligationKind, text: str) -> bool:
    if kind is SourceObligationKind.OFFICIAL_CURRENT:
        return _has_any(text, _OFFICIAL_MARKERS)
    if kind is SourceObligationKind.LEGAL_CURRENT_PRIMARY:
        return _has_any(text, _LEGAL_MARKERS)
    if kind is SourceObligationKind.CANONICAL_DOCUMENTATION:
        return _has_any(text, _CANONICAL_DOC_MARKERS)
    if kind is SourceObligationKind.SOURCE_BOUND_NUMERIC:
        return _has_any(text, _NUMERIC_MARKERS)
    if kind is SourceObligationKind.CONFLICT_RESOLUTION:
        return _has_any(text, _CONFLICT_MARKERS)
    return False


def _stop_conditions(
    obligation_kinds: Sequence[SourceObligationKind],
    query_shape_kinds: Sequence[QueryShapeKind],
) -> tuple[StopConditionKind, ...]:
    out: list[StopConditionKind] = []
    strict_obligations = [
        kind
        for kind in obligation_kinds
        if kind
        in {
            SourceObligationKind.OFFICIAL_CURRENT,
            SourceObligationKind.LEGAL_CURRENT_PRIMARY,
            SourceObligationKind.CANONICAL_DOCUMENTATION,
            SourceObligationKind.SOURCE_BOUND_NUMERIC,
            SourceObligationKind.CONFLICT_RESOLUTION,
        }
    ]
    if strict_obligations:
        out.append(StopConditionKind.SOURCE_OBLIGATION_UNSATISFIED)
    if SourceObligationKind.SOURCE_BOUND_NUMERIC in obligation_kinds:
        out.append(StopConditionKind.MISSING_SOURCE_BOUND_NUMERIC_VALUES)
    if QueryShapeKind.CONFLICT_LIKELY in query_shape_kinds:
        out.append(StopConditionKind.UNRESOLVED_CONFLICT_CURRENTNESS)
    if not out:
        out.append(StopConditionKind.COMPONENT_SUFFICIENT)
    return tuple(out)


def _deterministic_signals(
    query_shape_kinds: Sequence[QueryShapeKind],
    obligation_kinds: Sequence[SourceObligationKind],
) -> tuple[str, ...]:
    return tuple(
        f"shape:{kind.value}" for kind in query_shape_kinds
    ) + tuple(f"obligation:{kind.value}" for kind in obligation_kinds)


def _ambiguity_notes(text: str) -> tuple[str, ...]:
    if " x " in text or " y " in text:
        return ("placeholder_entities_detected",)
    return ()


def _normalization_notes(
    component_candidates: Sequence[ComponentCandidate],
) -> tuple[str, ...]:
    if len(component_candidates) > 1:
        return ("obvious_multipart_components_split_deterministically",)
    return ()


def _route_entities(route_facts: Mapping[str, Any]) -> tuple[str, ...]:
    entities: list[str] = []
    for value in (
        route_facts.get("primary_entity"),
        *(route_facts.get("entities") or ()),
    ):
        text = _clean_token(value, limit=120)
        if text and text not in entities:
            entities.append(text)
    return tuple(entities[:8])


def _contract_has_currentness(contract: Mapping[str, Any]) -> bool:
    return any(
        str(requirement.get("required_currentness") or "").casefold()
        in {"current", "as_requested"}
        for requirement in _source_requirements(contract)
    )


def _has_conflict_policy(contract: Mapping[str, Any]) -> bool:
    policy = contract.get("conflict_policy")
    return isinstance(policy, Mapping) and any(
        bool(policy.get(key))
        for key in ("preserve", "arbitrate", "block_overconfident_claim")
    )


def _coerce_search_mode(value: Any) -> SearchMode:
    raw = str(value or "").strip().casefold()
    for mode in SearchMode:
        if mode.value == raw:
            return mode
    return SearchMode.UNRESOLVED


def _has_any(text: str, tokens: frozenset[str]) -> bool:
    return any(token in text for token in tokens)


def _text_blob(*values: Any) -> str:
    return " ".join(str(value or "").casefold() for value in values)


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _json_safe(dict(value or {}))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
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
            key_text = _clean_token(key, limit=100)
            if not key_text:
                continue
            normalized = key_text.casefold()
            if normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS:
                continue
            out[key_text] = _json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:80]]
    return _clean_text(value, limit=300)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _dedupe(values: Sequence[QueryShapeKind]) -> tuple[QueryShapeKind, ...]:
    seen: set[QueryShapeKind] = set()
    out: list[QueryShapeKind] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return tuple(out)


__all__ = [
    "DeterministicSearchWorkRuntimeInput",
    "DeterministicSearchWorkRuntimeRecords",
    "QUERY_SHAPE_RUNTIME_HELPER",
    "build_deterministic_search_work_runtime_records",
]
