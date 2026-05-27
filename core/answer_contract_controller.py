"""Pure answer-contract controller spine.

This module defines the AG-1 answer-contract loop shape without calling
providers, models, prompts, storage, retrieval, or orchestration code. Runtime
stages can adapt existing decisions into these records while preserving their
current ownership boundaries.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from typing import Any, Mapping, Sequence

from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    RetrievalStopDecision,
)
from core.run_controller import RunController
from core.source_class_recovery_controller import (
    SourceClassRecoveryControllerDecision,
    SourceClassRecoveryDecision,
)
from core.weak_corpus_controller import (
    WeakCorpusRecoveryControllerDecision,
    WeakCorpusRecoveryDecision,
)

ANSWER_CONTRACT_SCHEMA_VERSION = "answer_contract_v1"
ANSWER_CONTRACT_FULFILLMENT_SCHEMA_VERSION = "answer_contract_fulfillment_v1"


class AnswerContractFamily(str, Enum):
    """Answer-contract family taxonomy v1."""

    DEVELOPING_EVENT_ORIENTATION = "developing_event_orientation"
    CURRENT_OFFICIAL_RULES = "current_official_rules"
    LEGAL_OR_REGULATORY_PRIMARY_TEXT = "legal_or_regulatory_primary_text"
    RECOMMENDATION_DECISION_SUPPORT = "recommendation_decision_support"
    QUANTITATIVE_COMPARISON_OR_MODEL = "quantitative_comparison_or_model"
    CONCEPTUAL_EXPLAINER = "conceptual_explainer"
    HISTORICAL_OR_ARCHIVAL_ANSWER = "historical_or_archival_answer"
    SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER = "social_media_or_social_sentiment_answer"
    WEAK_EVIDENCE_OR_NO_GOOD_EVIDENCE_ANSWER = "weak_evidence_or_no_good_evidence_answer"


ANSWER_CONTRACT_FAMILY_DESCRIPTIONS: dict[AnswerContractFamily, str] = {
    AnswerContractFamily.DEVELOPING_EVENT_ORIENTATION: (
        "Identify what is happening, what is known, what is unsettled, and give a directional picture."
    ),
    AnswerContractFamily.CURRENT_OFFICIAL_RULES: (
        "Explain current rules, eligibility, policy, or requirements using official/current sources when appropriate."
    ),
    AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT: (
        "Explain what a law, order, filing, regulation, agency text, or legal source says, distinguishing text from interpretation."
    ),
    AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT: (
        "Help choose among options using constraints, tradeoffs, specs, current availability, reviews, and social/user-experience signals where relevant."
    ),
    AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL: (
        "Identify variables, units, assumptions, calculations, and uncertainty."
    ),
    AnswerContractFamily.CONCEPTUAL_EXPLAINER: (
        "Explain a topic coherently using reputable evidence without over-chasing primary sources unless claims require them."
    ),
    AnswerContractFamily.HISTORICAL_OR_ARCHIVAL_ANSWER: (
        "Reconstruct what happened or what a source said using primary/archival material where appropriate plus secondary context."
    ),
    AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER: (
        "Answer questions explicitly about social media, user sentiment, public reaction, adoption, controversy, or social momentum."
    ),
    AnswerContractFamily.WEAK_EVIDENCE_OR_NO_GOOD_EVIDENCE_ANSWER: (
        "Give a responsible answer posture when good evidence is unavailable or insufficient."
    ),
}


class SocialSignalRelevance(str, Enum):
    """How social evidence should participate in the contract."""

    IRRELEVANT = "irrelevant"
    RELEVANT_OPTIONAL = "relevant_optional"
    CENTRAL = "central"


class ScrutineerRelevance(str, Enum):
    """How Scrutineer review should participate in the contract."""

    NOT_RELEVANT = "not_relevant"
    RELEVANT_OPTIONAL = "relevant_optional"
    CENTRAL = "central"


class AnswerControllerActionName(str, Enum):
    """Controller action vocabulary v1."""

    DIAGNOSE_QUESTION = "diagnose_question"
    SET_OR_UPDATE_ANSWER_CONTRACT = "set_or_update_answer_contract"
    INSPECT_EVIDENCE_STATE = "inspect_evidence_state"
    IDENTIFY_MISSING_INFORMATION = "identify_missing_information"
    GENERATE_TARGETED_QUERIES = "generate_targeted_queries"
    RETRIEVE_TARGETED = "retrieve_targeted"
    RECOVER_WEAK_CORPUS = "recover_weak_corpus"
    RECOVER_MISSING_SOURCE_CLASS = "recover_missing_source_class"
    RESOLVE_CONFLICT = "resolve_conflict"
    DECOMPOSE_QUANTITATIVE_QUESTION = "decompose_quantitative_question"
    REQUEST_SOCIAL_SIGNAL_CHECK = "request_social_signal_check"
    RUN_SCRUTINEER_REVIEW = "run_scrutineer_review"
    STOP_SUFFICIENT = "stop_sufficient"
    STOP_INSUFFICIENT_WITH_CAVEAT = "stop_insufficient_with_caveat"
    HANDOFF_TO_ANALYST = "handoff_to_analyst"
    ASK_USER_CLARIFICATION = "ask_user_clarification"


class AnswerControllerStopReason(str, Enum):
    """Stable controller stop reasons for AG-1 stop-policy scaffolding."""

    CONTINUE = "continue"
    EVIDENCE_SUFFICIENT = "evidence_sufficient"
    MAX_ITERATIONS = "max_iterations"
    MAX_RECOVERY_ATTEMPTS = "max_recovery_attempts"
    NO_USEFUL_NEW_QUERY = "no_useful_new_query"
    REDUNDANT_NEXT_QUERY = "redundant_next_query"
    CONFLICT_UNRESOLVED = "conflict_unresolved_caveat"
    OFFICIAL_OR_PRIMARY_UNAVAILABLE = "official_or_primary_unavailable_after_targeted_attempt"
    WEAK_CORPUS_UNRESOLVED = "weak_corpus_unresolved"
    MARGINAL_VALUE_LOW = "marginal_value_low"


_FAMILY_DEFAULTS: dict[AnswerContractFamily, dict[str, Any]] = {
    AnswerContractFamily.DEVELOPING_EVENT_ORIENTATION: {
        "must_satisfy": (
            "identify known facts",
            "identify unsettled points",
            "give a directional reading with caveats",
        ),
        "should_satisfy": ("include current official or primary updates when available",),
        "optional_checks": ("conflict check",),
        "evidence_classes_needed": ("current_primary_or_official", "reputable_secondary"),
        "stop_conditions": ("directionally useful evidence found", "no useful new query"),
        "answer_posture_if_fulfilled": "directional answer with uncertainty markers",
        "answer_posture_if_partial": "partial developing-event orientation with clear unknowns",
    },
    AnswerContractFamily.CURRENT_OFFICIAL_RULES: {
        "must_satisfy": (
            "identify the current official rule or policy",
            "separate official requirements from interpretation",
        ),
        "should_satisfy": ("note effective dates or version when available",),
        "optional_checks": ("secondary explainer cross-check",),
        "evidence_classes_needed": ("official_current_rules",),
        "stop_conditions": (
            "official/current source found",
            "official/current source unavailable after targeted attempt",
        ),
        "answer_posture_if_fulfilled": "answer from official/current evidence",
        "answer_posture_if_partial": "answer with official-evidence caveat",
    },
    AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT: {
        "must_satisfy": (
            "identify relevant primary legal or regulatory text",
            "distinguish text from interpretation",
        ),
        "should_satisfy": ("include jurisdiction, issuer, or filing context",),
        "optional_checks": ("secondary legal commentary only as context",),
        "evidence_classes_needed": ("legal_or_regulatory_text", "official_current_rules"),
        "stop_conditions": (
            "primary text found",
            "primary text unavailable after targeted attempt",
        ),
        "answer_posture_if_fulfilled": "primary-text-grounded explanation",
        "answer_posture_if_partial": "partial legal/regulatory explanation with caveat",
    },
    AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT: {
        "must_satisfy": (
            "identify decision criteria",
            "compare tradeoffs against user constraints",
        ),
        "should_satisfy": ("use current availability/specs when relevant",),
        "optional_checks": ("social or user-experience signal if useful",),
        "evidence_classes_needed": ("current_specs_or_availability", "reputable_reviews"),
        "stop_conditions": ("tradeoff picture is useful", "no useful new query"),
        "answer_posture_if_fulfilled": "recommendation with tradeoffs",
        "answer_posture_if_partial": "qualified recommendation with evidence gaps",
    },
    AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL: {
        "must_satisfy": (
            "identify variables and units",
            "state assumptions",
            "separate sourced values from calculations",
        ),
        "should_satisfy": ("quantify uncertainty or sensitivity where possible",),
        "optional_checks": ("ask clarification if variables cannot be inferred",),
        "evidence_classes_needed": ("sourced_numeric_values", "calculation_assumptions"),
        "stop_conditions": ("needed variables and assumptions identified", "missing variables are explicit"),
        "answer_posture_if_fulfilled": "bounded quantitative answer with assumptions",
        "answer_posture_if_partial": "partial quantitative answer with missing variables",
    },
    AnswerContractFamily.CONCEPTUAL_EXPLAINER: {
        "must_satisfy": (
            "explain the core concept accurately",
            "use reputable evidence for factual claims",
        ),
        "should_satisfy": ("include examples or distinctions when helpful",),
        "optional_checks": ("primary source check only when claims require it",),
        "evidence_classes_needed": ("reputable_secondary",),
        "stop_conditions": ("concept is sufficiently grounded", "no central evidence gap"),
        "answer_posture_if_fulfilled": "clear explanation",
        "answer_posture_if_partial": "clear explanation with limited-evidence caveat",
    },
    AnswerContractFamily.HISTORICAL_OR_ARCHIVAL_ANSWER: {
        "must_satisfy": (
            "reconstruct the relevant historical facts",
            "use primary or archival material where appropriate",
        ),
        "should_satisfy": ("include secondary context for interpretation",),
        "optional_checks": ("date/version check",),
        "evidence_classes_needed": ("primary_or_archival", "reputable_secondary"),
        "stop_conditions": ("historical record is sufficiently reconstructed", "archival source unavailable after targeted attempt"),
        "answer_posture_if_fulfilled": "historical reconstruction with source context",
        "answer_posture_if_partial": "partial historical reconstruction with gaps",
    },
    AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER: {
        "must_satisfy": (
            "identify the social signal being asked about",
            "separate social sentiment from factual authority",
        ),
        "should_satisfy": ("summarize adoption, controversy, or public reaction if available",),
        "optional_checks": ("treat social provider availability as a stable skip status",),
        "evidence_classes_needed": ("social_signal",),
        "stop_conditions": ("social signal checked or provider unavailable", "social signal not treated as authority"),
        "answer_posture_if_fulfilled": "social-signal answer with authority caveat",
        "answer_posture_if_partial": "partial answer noting social signal unavailable",
    },
    AnswerContractFamily.WEAK_EVIDENCE_OR_NO_GOOD_EVIDENCE_ANSWER: {
        "must_satisfy": (
            "state that strong evidence is unavailable",
            "identify what evidence would improve the answer",
        ),
        "should_satisfy": ("offer a cautious directional answer only if justified",),
        "optional_checks": ("avoid false precision",),
        "evidence_classes_needed": ("stronger_independent_evidence",),
        "stop_conditions": ("better evidence cannot be found under caps", "caveat is more honest than another loop"),
        "answer_posture_if_fulfilled": "responsible insufficient-evidence answer",
        "answer_posture_if_partial": "weak-evidence answer with explicit gaps",
    },
}

_OFFICIAL_OR_PRIMARY_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_or_archival",
    }
)

_SOURCE_CLASS_FULFILLMENT_CLASSES = frozenset(
    {
        "legal_or_regulatory_text",
        "official_current_rules",
        "current_primary_or_official",
        "current_specs_or_availability",
        "primary_or_archival",
        "primary_source_documents",
        "social_signal",
    }
)

_SOURCE_CLASS_SATISFYING_ALIASES: dict[str, frozenset[str]] = {
    "legal_or_regulatory_text": frozenset(
        {"legal_or_regulatory_text", "official_current_rules"}
    ),
    "official_current_rules": frozenset({"official_current_rules"}),
    "current_primary_or_official": frozenset(
        {
            "current_primary_or_official",
            "official_current_rules",
            "legal_or_regulatory_text",
        }
    ),
    "primary_or_archival": frozenset(
        {
            "primary_or_archival",
            "primary_source_documents",
            "archival_primary_text",
            "historical_legal_text",
            "legal_or_regulatory_text",
        }
    ),
    "primary_source_documents": frozenset({"primary_source_documents"}),
    "current_specs_or_availability": frozenset(
        {"current_specs_or_availability", "official_current_rules"}
    ),
    "social_signal": frozenset({"social_signal"}),
}

_SOURCE_CLASS_ITEM_TERMS: dict[str, tuple[str, ...]] = {
    "legal_or_regulatory_text": (
        "filing",
        "jurisdiction",
        "law",
        "legal",
        "primary",
        "regulatory",
        "regulation",
        "rule text",
        "statute",
        "tax credit",
        "text",
    ),
    "official_current_rules": (
        "current",
        "deadline",
        "effective",
        "eligibility",
        "official",
        "policy",
        "requirement",
        "rule",
        "tax credit",
        "version",
    ),
    "current_primary_or_official": (
        "current",
        "known facts",
        "official",
        "primary",
        "settled",
        "unsettled",
        "updates",
    ),
    "primary_or_archival": (
        "archival",
        "historical",
        "material",
        "primary",
        "record",
        "reconstruct",
        "source",
    ),
    "primary_source_documents": (
        "behavior",
        "canonical",
        "configuration",
        "documentation",
        "docs",
        "manual",
        "official",
        "project",
        "reference",
        "release",
    ),
    "current_specs_or_availability": (
        "availability",
        "available",
        "current",
        "price",
        "pricing",
        "spec",
        "specs",
        "version",
    ),
    "social_signal": (
        "adoption",
        "controversy",
        "public reaction",
        "sentiment",
        "social",
        "user",
    ),
}

_SOCIAL_SIGNAL_SATISFIED_STATUSES = frozenset({"checked", "not_applicable"})

_PROTECTED_HANDOFF_MARKERS = (
    "controller_diagnostics",
    "planned_vs_observed",
    "task_ledger",
    "quantitative_packet",
    "quantitative_packet_v1",
    "economist_v1",
    "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY",
    "## QUANTITATIVE FRAMEWORK",
    "QUANTITATIVE FRAMEWORK (MODEL-DERIVED",
    "ECONOMIST FRAMEWORK",
    "source_bound_values",
    "calculations_requested",
    "provider_diagnostics",
    "provider_attempts_by_role",
    "provider_payload",
    "raw_provider",
    "raw_prompt",
    "raw_evidence",
    "raw evidence dump",
    "raw prompt",
    "raw_internal",
    "full_trace",
    "internal diagnostics",
    ".env",
    "secret",
    "local packet",
)

_QUANTITATIVE_REPORT_TYPES = frozenset(
    {
        "quantitative_comparison",
        "comparative_analysis",
        "benchmark",
        "cost_analysis",
        "unit_economics",
    }
)
_QUANTITATIVE_QUERY_TYPES = frozenset({"comparison", "quantitative_comparison"})
_NEWS_QUERY_TYPES = frozenset({"news", "current_events", "event"})
_EXPLICIT_SOCIAL_TERMS = frozenset(
    {
        "social media",
        "social sentiment",
        "social signal",
        "reddit",
        "twitter",
        "public reaction",
        "what people are saying",
        "what users are saying",
        "user sentiment",
    }
)
_SOCIAL_PLATFORM_TERMS = frozenset(
    {
        "bluesky",
        "x",
        "twitter",
        "reddit",
        "mastodon",
        "threads",
    }
)
_SOCIAL_SIGNAL_CONTEXT_TERMS = frozenset(
    {
        "adoption",
        "among journalists",
        "among users",
        "controversy",
        "momentum",
        "overtaking",
        "public reaction",
        "sentiment",
        "switching",
        "user base",
        "users are saying",
    }
)
_HISTORICAL_TERMS = frozenset(
    {
        "archive",
        "archival",
        "changed over time",
        "original requirement",
        "original requirements",
        "original rule",
        "original rules",
        "original text",
        "phase down",
        "phase down rules",
        "phase down requirements",
        "phase down require",
        "past requirements",
        "what happened in",
        "when did",
    }
)
_LEGAL_OR_REGULATORY_TERMS = frozenset(
    {
        "ai act",
        "agency guidance",
        "court order",
        "enforcement",
        "federal rules",
        "filing",
        "irs",
        "law",
        "legal",
        "regulation",
        "regulatory",
        "statute",
        "tax credit",
    }
)
_CURRENT_OFFICIAL_TERMS = frozenset(
    {
        "application requirements",
        "current official",
        "current policy",
        "current rules",
        "eligibility",
        "official requirements",
        "official rules",
    }
)
_CURRENT_LEGAL_RULE_CUES = frozenset(
    {
        "as of now",
        "as of today",
        "claiming",
        "compliance",
        "deadline",
        "deadlines",
        "effective date",
        "effective dates",
        "eligibility",
        "enforcement milestone",
        "enforcement milestones",
        "legal status",
        "limits",
        "obligation",
        "obligations",
        "requirement",
        "requirements",
        "rules",
        "timeline",
    }
)
_LEGAL_PRIMARY_TEXT_CUES = frozenset(
    {
        "legal text",
        "primary text",
        "regulatory text",
        "rule text",
        "statutory text",
        "text says",
        "what do the rules say",
        "what does the law say",
        "what does the regulation say",
        "what does the statute say",
    }
)
_DEVELOPING_STATUS_CUES = frozenset(
    {
        "announced today",
        "breaking",
        "breaking news",
        "currently happening",
        "happening with",
        "latest news",
        "new article",
        "news story",
        "policy story",
        "reported today",
        "story about",
        "unsettled",
        "what is happening",
        "what remains uncertain",
    }
)
_CONCEPTUAL_EXPLAINER_CUES = frozenset(
    {
        "basic idea",
        "conceptual",
        "explain",
        "high level",
        "overview",
        "primer",
        "what is",
        "why",
    }
)
_RECOMMENDATION_TERMS = frozenset(
    {
        "best",
        "buy",
        "buying",
        "choose",
        "choosing",
        "decision criteria",
        "help me decide",
        "practical tradeoffs",
        "recommend",
        "reviews",
        "should i",
        "tradeoffs",
        "user experience evidence",
        "which should",
        "which tool",
    }
)
_CHOICE_RECOMMENDATION_TERMS = frozenset(
    {
        "buy",
        "buying",
        "choose",
        "choosing",
        "compare options",
        "decision criteria",
        "help me decide",
        "practical tradeoffs",
        "recommend",
        "recommendation",
        "should i buy",
        "tradeoffs",
        "which should",
        "which tool",
    }
)


def _coerce_family(value: AnswerContractFamily | str) -> AnswerContractFamily:
    if isinstance(value, AnswerContractFamily):
        return value
    try:
        return AnswerContractFamily(str(value))
    except ValueError:
        return AnswerContractFamily.CONCEPTUAL_EXPLAINER


def _coerce_social(value: SocialSignalRelevance | str | None) -> SocialSignalRelevance:
    if isinstance(value, SocialSignalRelevance):
        return value
    try:
        return SocialSignalRelevance(str(value))
    except ValueError:
        return SocialSignalRelevance.IRRELEVANT


def _coerce_scrutineer(
    value: ScrutineerRelevance | str | None,
) -> ScrutineerRelevance:
    if isinstance(value, ScrutineerRelevance):
        return value
    try:
        return ScrutineerRelevance(str(value))
    except ValueError:
        return ScrutineerRelevance.NOT_RELEVANT


def _copy_string_tuple(value: Sequence[Any] | None) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in value or ():
        text = " ".join(str(item or "").strip().split())
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _normalized_search_text(*values: Any) -> str:
    raw = " ".join(str(value or "") for value in values).casefold()
    normalized = "".join(char if char.isalnum() else " " for char in raw)
    return " ".join(normalized.split())


def _has_any_term(text: str, terms: Sequence[str]) -> bool:
    padded_text = f" {text} "
    for term in terms:
        normalized = _normalized_search_text(term)
        if normalized and f" {normalized} " in padded_text:
            return True
    return False


def _is_choice_recommendation_query(query_text: str) -> bool:
    return _has_any_term(query_text, _CHOICE_RECOMMENDATION_TERMS)


def _is_conceptual_explainer_query(query_text: str) -> bool:
    return _has_any_term(query_text, _CONCEPTUAL_EXPLAINER_CUES)


def _is_developing_status_query(query_text: str) -> bool:
    return _has_any_term(query_text, _DEVELOPING_STATUS_CUES)


def _official_current_legal_family(
    *,
    query_text: str,
    haystack: str,
) -> AnswerContractFamily | None:
    has_legal_domain = _has_any_term(haystack, _LEGAL_OR_REGULATORY_TERMS)
    has_current_official_domain = _has_any_term(haystack, _CURRENT_OFFICIAL_TERMS)
    has_rule_or_obligation_goal = _has_any_term(query_text, _CURRENT_LEGAL_RULE_CUES)
    has_primary_text_goal = _has_any_term(query_text, _LEGAL_PRIMARY_TEXT_CUES)

    if has_legal_domain and (has_rule_or_obligation_goal or has_primary_text_goal):
        return AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
    if has_current_official_domain and has_rule_or_obligation_goal:
        return AnswerContractFamily.CURRENT_OFFICIAL_RULES
    return None


def _enum_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _safe_handoff_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            key_lower = key.casefold()
            if any(marker.casefold() in key_lower for marker in _PROTECTED_HANDOFF_MARKERS):
                continue
            out[key] = _safe_handoff_value(raw_value)
        return out
    if isinstance(value, (list, tuple, set)):
        return [_safe_handoff_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        if any(marker.casefold() in value.casefold() for marker in _PROTECTED_HANDOFF_MARKERS):
            return "[redacted protected material]"
        return value
    return deepcopy(value)


@dataclass(frozen=True)
class EvidenceReference:
    """Compact safe evidence reference for contract fulfillment."""

    reference: str
    source_class: str | None = None
    summary: str | None = None
    supports: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _safe_handoff_value(
            {
                "reference": self.reference,
                "source_class": self.source_class,
                "summary": self.summary,
                "supports": list(self.supports),
            }
        )


@dataclass(frozen=True)
class AnswerContract:
    """Inspectable answer obligations drafted by Router and revised by Controller."""

    family: AnswerContractFamily
    user_intent_interpretation: str
    answer_goal: str
    must_satisfy: tuple[str, ...]
    should_satisfy: tuple[str, ...] = ()
    optional_checks: tuple[str, ...] = ()
    evidence_classes_needed: tuple[str, ...] = ()
    social_signal_relevance: SocialSignalRelevance = SocialSignalRelevance.IRRELEVANT
    scrutineer_relevance: ScrutineerRelevance = ScrutineerRelevance.NOT_RELEVANT
    stop_conditions: tuple[str, ...] = ()
    answer_posture_if_fulfilled: str = "direct answer"
    answer_posture_if_partial: str = "answer with caveats"
    schema_version: str = ANSWER_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return _safe_handoff_value(payload)


@dataclass(frozen=True)
class ContractRevision:
    """One controller-captured revision to the active answer contract."""

    iteration: int
    reason: str
    prior_family: AnswerContractFamily
    revised_family: AnswerContractFamily
    changes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _safe_handoff_value(
            {
                "iteration": self.iteration,
                "reason": self.reason,
                "prior_family": self.prior_family.value,
                "revised_family": self.revised_family.value,
                "changes": self.changes,
            }
        )


@dataclass(frozen=True)
class AnswerControllerActionResult:
    """Controller action decision result shape v1."""

    action_name: AnswerControllerActionName
    reason: str
    preconditions: tuple[str, ...] = ()
    contract_items_affected: tuple[str, ...] = ()
    approved_queries_or_none: tuple[str, ...] | None = None
    skip_reason_or_none: str | None = None
    stable_reason_code: str = "unspecified"
    iteration: int = 0
    next_state_delta: dict[str, Any] = field(default_factory=dict)

    @property
    def approved(self) -> bool:
        return self.skip_reason_or_none is None

    def to_dict(self) -> dict[str, Any]:
        return _safe_handoff_value(
            {
                "action_name": self.action_name.value,
                "reason": self.reason,
                "preconditions": list(self.preconditions),
                "contract_items_affected": list(self.contract_items_affected),
                "approved_queries_or_none": (
                    None
                    if self.approved_queries_or_none is None
                    else list(self.approved_queries_or_none)
                ),
                "skip_reason_or_none": self.skip_reason_or_none,
                "stable_reason_code": self.stable_reason_code,
                "iteration": self.iteration,
                "next_state_delta": self.next_state_delta,
            }
        )


@dataclass(frozen=True)
class EvidenceStateSummary:
    """Compact evidence snapshot consumed by the answer-contract controller."""

    evidence_available: bool = False
    evidence_sufficient: bool = False
    source_classes_present: tuple[str, ...] = ()
    source_classes_missing: tuple[str, ...] = ()
    fulfilled_obligations: tuple[str, ...] = ()
    partial_obligations: tuple[str, ...] = ()
    unfulfilled_obligations: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    approved_targeted_queries: tuple[str, ...] = ()
    prior_queries: tuple[str, ...] = ()
    next_queries: tuple[str, ...] = ()
    next_query_redundant: bool = False
    weak_corpus: bool = False
    weak_corpus_reason: str | None = None
    conflicts_present: bool = False
    conflict_notes: tuple[str, ...] = ()
    resolving_queries: tuple[str, ...] = ()
    quantitative_variables_needed: tuple[str, ...] = ()
    quantitative_assumptions_needed: tuple[str, ...] = ()
    social_provider_configured: bool = False
    social_signal_status: str | None = None
    scrutineer_requested: bool = False
    scrutineer_needed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _safe_handoff_value(asdict(self))


@dataclass(frozen=True)
class AnswerControllerCaps:
    """Hard caps for the AG-1 controller stop layer."""

    max_iterations: int = 3
    max_recovery_attempts: int = 1
    max_live_runs: int = 0
    max_provider_calls: int | None = None
    elapsed_time_target_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarginalValueJudgment:
    """LLM marginal-value judgment shape; AG-1 never calls an LLM to fill it."""

    likely_change_answer_posture: bool
    missing_information_central: bool
    current_evidence_directionally_useful: bool
    caveat_more_honest_than_more_retrieval: bool
    public_rationale: str

    def to_dict(self) -> dict[str, Any]:
        return _safe_handoff_value(asdict(self))


@dataclass(frozen=True)
class AnswerControllerStopDecision:
    """Three-layer controller stop decision."""

    should_stop: bool
    reason: AnswerControllerStopReason
    public_rationale: str
    final_answer_posture: str
    hard_cap_triggered: str | None = None
    structured_checks: tuple[str, ...] = ()
    marginal_value_judgment: MarginalValueJudgment | None = None

    def to_dict(self) -> dict[str, Any]:
        return _safe_handoff_value(
            {
                "should_stop": self.should_stop,
                "reason": self.reason.value,
                "public_rationale": self.public_rationale,
                "final_answer_posture": self.final_answer_posture,
                "hard_cap_triggered": self.hard_cap_triggered,
                "structured_checks": list(self.structured_checks),
                "marginal_value_judgment": (
                    None
                    if self.marginal_value_judgment is None
                    else self.marginal_value_judgment.to_dict()
                ),
            }
        )


@dataclass
class AnswerControllerState:
    """Mutable AG-1 controller loop state for one answer contract."""

    active_contract: AnswerContract
    evidence_state_summary: EvidenceStateSummary = field(default_factory=EvidenceStateSummary)
    missing_information: list[str] = field(default_factory=list)
    action_history: list[AnswerControllerActionResult] = field(default_factory=list)
    recovery_attempts: dict[str, int] = field(default_factory=dict)
    stop_state: AnswerControllerStopDecision | None = None
    contract_revisions: list[ContractRevision] = field(default_factory=list)
    fulfillment_handoff_draft: AnswerContractFulfillment | None = None
    iteration: int = 1
    caps: AnswerControllerCaps = field(default_factory=AnswerControllerCaps)

    def __post_init__(self) -> None:
        self.missing_information = list(
            _copy_string_tuple(
                tuple(self.missing_information)
                + self.evidence_state_summary.missing_information
            )
        )
        self.recovery_attempts = {
            "recover_weak_corpus": int(self.recovery_attempts.get("recover_weak_corpus", 0)),
            "recover_missing_source_class": int(
                self.recovery_attempts.get("recover_missing_source_class", 0)
            ),
            **{
                key: int(value)
                for key, value in self.recovery_attempts.items()
                if key not in {"recover_weak_corpus", "recover_missing_source_class"}
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return _safe_handoff_value(
            {
                "active_contract": self.active_contract.to_dict(),
                "evidence_state_summary": self.evidence_state_summary.to_dict(),
                "missing_information": list(self.missing_information),
                "action_history": [item.to_dict() for item in self.action_history],
                "recovery_attempts": dict(self.recovery_attempts),
                "stop_state": None if self.stop_state is None else self.stop_state.to_dict(),
                "contract_revisions": [item.to_dict() for item in self.contract_revisions],
                "fulfillment_handoff_draft": (
                    None
                    if self.fulfillment_handoff_draft is None
                    else self.fulfillment_handoff_draft.to_dict()
                ),
                "iteration": self.iteration,
                "caps": self.caps.to_dict(),
            }
        )


@dataclass(frozen=True)
class AnswerContractFulfillment:
    """Compact safe handoff artifact for Analyst/Author-facing downstream stages."""

    fulfilled_items: tuple[str, ...]
    partial_items: tuple[str, ...]
    unfulfilled_items: tuple[str, ...]
    evidence_used: tuple[EvidenceReference, ...] = ()
    actions_taken: tuple[dict[str, Any], ...] = ()
    actions_skipped_and_why: tuple[dict[str, Any], ...] = ()
    contract_revisions: tuple[ContractRevision, ...] = ()
    stop_reason: str | None = None
    final_answer_posture: str = "answer with caveats"
    source_obligation_status: str = "not_evaluated"
    unfulfilled_source_classes: tuple[str, ...] = ()
    partial_source_classes: tuple[str, ...] = ()
    warnings_to_Analyst_or_Author: tuple[str, ...] = ()
    social_signal_summary: str | None = None
    evidence_integration_checkpoint: dict[str, Any] | None = None
    schema_version: str = ANSWER_CONTRACT_FULFILLMENT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "fulfilled_items": list(self.fulfilled_items),
            "partial_items": list(self.partial_items),
            "unfulfilled_items": list(self.unfulfilled_items),
            "evidence_used": [item.to_dict() for item in self.evidence_used],
            "actions_taken": list(self.actions_taken),
            "actions_skipped_and_why": list(self.actions_skipped_and_why),
            "contract_revisions": [
                item.to_dict() for item in self.contract_revisions
            ],
            "stop_reason": self.stop_reason,
            "final_answer_posture": self.final_answer_posture,
            "source_obligation_status": self.source_obligation_status,
            "unfulfilled_source_classes": list(self.unfulfilled_source_classes),
            "partial_source_classes": list(self.partial_source_classes),
            "warnings_to_Analyst_or_Author": list(
                self.warnings_to_Analyst_or_Author
            ),
            "social_signal_summary": self.social_signal_summary,
        }
        if self.evidence_integration_checkpoint is not None:
            payload["evidence_integration_checkpoint"] = (
                self.evidence_integration_checkpoint
            )
        return _safe_handoff_value(payload)


ControllerHandoff = AnswerContractFulfillment


def build_answer_contract(
    *,
    family: AnswerContractFamily | str,
    user_intent_interpretation: str,
    answer_goal: str,
    must_satisfy: Sequence[Any] | None = None,
    should_satisfy: Sequence[Any] | None = None,
    optional_checks: Sequence[Any] | None = None,
    evidence_classes_needed: Sequence[Any] | None = None,
    social_signal_relevance: SocialSignalRelevance | str | None = None,
    scrutineer_relevance: ScrutineerRelevance | str | None = None,
    stop_conditions: Sequence[Any] | None = None,
    answer_posture_if_fulfilled: str | None = None,
    answer_posture_if_partial: str | None = None,
) -> AnswerContract:
    """Build an AnswerContract from explicit values plus family defaults."""
    contract_family = _coerce_family(family)
    defaults = _FAMILY_DEFAULTS[contract_family]
    if social_signal_relevance is None:
        social_signal_relevance = (
            SocialSignalRelevance.CENTRAL
            if contract_family is AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER
            else SocialSignalRelevance.RELEVANT_OPTIONAL
            if contract_family is AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT
            else SocialSignalRelevance.IRRELEVANT
        )
    if scrutineer_relevance is None:
        scrutineer_relevance = ScrutineerRelevance.NOT_RELEVANT

    return AnswerContract(
        family=contract_family,
        user_intent_interpretation=user_intent_interpretation,
        answer_goal=answer_goal,
        must_satisfy=_copy_string_tuple(must_satisfy or defaults["must_satisfy"]),
        should_satisfy=_copy_string_tuple(should_satisfy or defaults["should_satisfy"]),
        optional_checks=_copy_string_tuple(optional_checks or defaults["optional_checks"]),
        evidence_classes_needed=_copy_string_tuple(
            evidence_classes_needed or defaults["evidence_classes_needed"]
        ),
        social_signal_relevance=_coerce_social(social_signal_relevance),
        scrutineer_relevance=_coerce_scrutineer(scrutineer_relevance),
        stop_conditions=_copy_string_tuple(stop_conditions or defaults["stop_conditions"]),
        answer_posture_if_fulfilled=(
            str(answer_posture_if_fulfilled)
            if answer_posture_if_fulfilled
            else str(defaults["answer_posture_if_fulfilled"])
        ),
        answer_posture_if_partial=(
            str(answer_posture_if_partial)
            if answer_posture_if_partial
            else str(defaults["answer_posture_if_partial"])
        ),
    )


def _router_family_from_metadata(
    *,
    query: str,
    intent: str | None,
    report_type: str | None,
    query_type: str | None,
) -> AnswerContractFamily:
    query_text = _normalized_search_text(query)
    haystack = _normalized_search_text(query, intent, report_type, query_type)
    report = str(report_type or "").strip().casefold()
    qtype = str(query_type or "").strip().casefold()
    intent_value = str(intent or "").strip().casefold()

    social_platform_signal = _has_any_term(
        query_text,
        _SOCIAL_PLATFORM_TERMS,
    ) and _has_any_term(query_text, _SOCIAL_SIGNAL_CONTEXT_TERMS)
    if _has_any_term(haystack, _EXPLICIT_SOCIAL_TERMS) or social_platform_signal:
        return AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER
    if intent_value == "historical" or _has_any_term(query_text, _HISTORICAL_TERMS):
        return AnswerContractFamily.HISTORICAL_OR_ARCHIVAL_ANSWER
    if intent_value == "recommendation" or _is_choice_recommendation_query(query_text):
        return AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT
    official_current_legal_family = _official_current_legal_family(
        query_text=query_text,
        haystack=haystack,
    )
    if (
        official_current_legal_family is not None
        and not _is_developing_status_query(query_text)
    ):
        return official_current_legal_family
    if intent_value == "news" or qtype in _NEWS_QUERY_TYPES:
        return AnswerContractFamily.DEVELOPING_EVENT_ORIENTATION
    if official_current_legal_family is not None:
        return official_current_legal_family
    if _has_any_term(haystack, _CURRENT_OFFICIAL_TERMS):
        return AnswerContractFamily.CURRENT_OFFICIAL_RULES
    if _has_any_term(haystack, _LEGAL_OR_REGULATORY_TERMS) and not _is_conceptual_explainer_query(
        query_text
    ):
        return AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
    if intent_value == "recommendation" or _has_any_term(query_text, _RECOMMENDATION_TERMS):
        return AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT
    if report in _QUANTITATIVE_REPORT_TYPES or qtype in _QUANTITATIVE_QUERY_TYPES:
        return AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL
    return AnswerContractFamily.CONCEPTUAL_EXPLAINER


def draft_answer_contract_from_router_metadata(
    *,
    query: str,
    intent: str | None = None,
    report_type: str | None = None,
    query_type: str | None = None,
    mode: str | None = None,
    core_topic: str | None = None,
) -> AnswerContract:
    """Draft an initial contract from already-produced Router metadata.

    This is a behavior-preserving adapter seam. It does not alter router prompts
    or routing decisions, and ``mode`` only appears in the inspectable intent.
    """
    family = _router_family_from_metadata(
        query=query,
        intent=intent,
        report_type=report_type,
        query_type=query_type,
    )
    topic = core_topic or query
    intent_parts = [f"Question: {query}"]
    if topic != query:
        intent_parts.append(f"Resolved topic: {topic}")
    if mode:
        intent_parts.append(f"Mode: {mode}")
    if report_type:
        intent_parts.append(f"Router report_type: {report_type}")
    if query_type:
        intent_parts.append(f"Router query_type: {query_type}")
    return build_answer_contract(
        family=family,
        user_intent_interpretation="; ".join(intent_parts),
        answer_goal=f"Answer the user's question about {topic}",
    )


def revise_answer_contract(
    contract: AnswerContract,
    *,
    iteration: int,
    reason: str,
    **changes: Any,
) -> tuple[AnswerContract, ContractRevision]:
    """Return a revised contract plus a compact revision record."""
    allowed = {
        "family",
        "user_intent_interpretation",
        "answer_goal",
        "must_satisfy",
        "should_satisfy",
        "optional_checks",
        "evidence_classes_needed",
        "social_signal_relevance",
        "scrutineer_relevance",
        "stop_conditions",
        "answer_posture_if_fulfilled",
        "answer_posture_if_partial",
    }
    normalized: dict[str, Any] = {}
    for key, value in changes.items():
        if key not in allowed:
            continue
        if key == "family":
            normalized[key] = _coerce_family(value)
        elif key == "social_signal_relevance":
            normalized[key] = _coerce_social(value)
        elif key == "scrutineer_relevance":
            normalized[key] = _coerce_scrutineer(value)
        elif key in {
            "must_satisfy",
            "should_satisfy",
            "optional_checks",
            "evidence_classes_needed",
            "stop_conditions",
        }:
            normalized[key] = _copy_string_tuple(value)
        else:
            normalized[key] = str(value)
    revised = replace(contract, **normalized)
    revision = ContractRevision(
        iteration=max(0, int(iteration or 0)),
        reason=str(reason),
        prior_family=contract.family,
        revised_family=revised.family,
        changes={key: _enum_value(value) for key, value in normalized.items()},
    )
    return revised, revision


def build_answer_controller_state(
    contract: AnswerContract,
    *,
    evidence_state_summary: EvidenceStateSummary | None = None,
    caps: AnswerControllerCaps | None = None,
    iteration: int = 1,
) -> AnswerControllerState:
    """Build the AG-1 controller state wrapper for a contract."""
    return AnswerControllerState(
        active_contract=contract,
        evidence_state_summary=evidence_state_summary or EvidenceStateSummary(),
        caps=caps or AnswerControllerCaps(),
        iteration=max(0, int(iteration or 0)),
    )


def _contract_items_for_classes(
    contract: AnswerContract,
    source_classes: Sequence[str],
) -> tuple[str, ...]:
    affected: list[str] = []
    missing = {item.casefold() for item in source_classes}
    for item in contract.must_satisfy + contract.should_satisfy:
        text = item.casefold().replace(" ", "_")
        if any(source_class in text or source_class.replace("_", " ") in item.casefold() for source_class in missing):
            affected.append(item)
    if not affected:
        affected.extend(contract.evidence_classes_needed)
    return _copy_string_tuple(affected)


def _source_class_is_satisfied(
    source_class: str,
    evidence: EvidenceStateSummary,
) -> bool:
    normalized = str(source_class or "").casefold()
    present = {item.casefold() for item in evidence.source_classes_present}
    if normalized == "social_signal":
        status = str(evidence.social_signal_status or "not_checked").casefold()
        return "social_signal" in present or status in _SOCIAL_SIGNAL_SATISFIED_STATUSES
    aliases = _SOURCE_CLASS_SATISFYING_ALIASES.get(
        normalized,
        frozenset({normalized}),
    )
    return bool(present & aliases)


def _source_class_fulfillment_gaps(
    contract: AnswerContract,
    evidence: EvidenceStateSummary,
) -> tuple[str, ...]:
    explicit = _copy_string_tuple(evidence.source_classes_missing)
    required = _copy_string_tuple(
        source_class
        for source_class in contract.evidence_classes_needed
        if str(source_class or "").casefold() in _SOURCE_CLASS_FULFILLMENT_CLASSES
    )
    derived = (
        tuple(
            source_class
            for source_class in required
            if not _source_class_is_satisfied(source_class, evidence)
        )
        if evidence.evidence_sufficient
        else ()
    )
    social_gap = (
        ("social_signal",)
        if (
            contract.social_signal_relevance is SocialSignalRelevance.CENTRAL
            and not _source_class_is_satisfied("social_signal", evidence)
        )
        else ()
    )
    return _copy_string_tuple(tuple(explicit) + tuple(derived) + social_gap)


def _source_class_related_fulfillment_items(
    contract: AnswerContract,
    source_class_gaps: Sequence[str],
    *,
    fulfilled: Sequence[str] = (),
) -> tuple[str, ...]:
    affected: list[str] = []
    candidates = _copy_string_tuple(
        tuple(contract.must_satisfy)
        + tuple(contract.should_satisfy)
        + tuple(fulfilled)
    )
    for source_class in _copy_string_tuple(source_class_gaps):
        normalized = source_class.casefold()
        terms = _SOURCE_CLASS_ITEM_TERMS.get(normalized, ())
        if not terms:
            continue
        for item in candidates:
            text = item.casefold()
            if any(term in text for term in terms):
                affected.append(item)
    return _copy_string_tuple(affected)


def _source_class_gap_warnings(
    source_class_gaps: Sequence[str],
    evidence: EvidenceStateSummary,
) -> tuple[str, ...]:
    gaps = {item.casefold() for item in _copy_string_tuple(source_class_gaps)}
    warnings: list[str] = []
    if gaps & {"legal_or_regulatory_text", "official_current_rules"}:
        warnings.append("official/current legal evidence missing or secondary-only")
    if "current_primary_or_official" in gaps:
        warnings.append("official/current primary evidence missing or secondary-only")
    if "primary_or_archival" in gaps:
        warnings.append("primary/archival source not found")
    if "primary_source_documents" in gaps:
        warnings.append("canonical/official documentation missing or secondary-only")
    if "current_specs_or_availability" in gaps:
        warnings.append("current specs/availability evidence missing or secondary-only")
    if "social_signal" in gaps:
        status = str(evidence.social_signal_status or "provider_unavailable")
        warnings.append(f"social signal unavailable/{status}")
    return _copy_string_tuple(warnings)


def _source_obligation_status(
    source_class_gaps: Sequence[str],
    evidence: EvidenceStateSummary,
) -> str:
    gaps = _copy_string_tuple(source_class_gaps)
    if not gaps:
        return "fulfilled" if evidence.evidence_sufficient else "not_evaluated"
    if evidence.source_classes_present:
        return "partial"
    return "unfulfilled"


def _calibrate_fulfillment_for_source_classes(
    contract: AnswerContract,
    evidence: EvidenceStateSummary,
    *,
    fulfilled: Sequence[str],
    partial: Sequence[str],
    unfulfilled: Sequence[str],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    source_class_gaps = _source_class_fulfillment_gaps(contract, evidence)
    if not source_class_gaps:
        return (
            _copy_string_tuple(fulfilled),
            _copy_string_tuple(partial),
            _copy_string_tuple(unfulfilled),
            (),
        )

    related_items = _source_class_related_fulfillment_items(
        contract,
        source_class_gaps,
        fulfilled=fulfilled,
    )
    blocked = {item.casefold() for item in related_items + source_class_gaps}
    calibrated_fulfilled = tuple(
        item for item in _copy_string_tuple(fulfilled) if item.casefold() not in blocked
    )
    calibrated_partial = _copy_string_tuple(tuple(partial) + tuple(related_items))
    unfulfilled_text = " ".join(_copy_string_tuple(unfulfilled)).casefold()
    new_gap_items = tuple(
        source_class
        for source_class in source_class_gaps
        if source_class.casefold() not in unfulfilled_text
        and source_class.replace("_", " ").casefold() not in unfulfilled_text
    )
    calibrated_unfulfilled = _copy_string_tuple(
        tuple(unfulfilled) + new_gap_items
    )
    return (
        calibrated_fulfilled,
        calibrated_partial,
        calibrated_unfulfilled,
        source_class_gaps,
    )


def _queries_for_missing_classes(
    contract: AnswerContract,
    missing_source_classes: Sequence[str],
) -> tuple[str, ...]:
    base = contract.answer_goal or contract.user_intent_interpretation
    return tuple(
        f"{base} {source_class.replace('_', ' ')}"
        for source_class in _copy_string_tuple(missing_source_classes)[:2]
    )


def _stop_action(
    *,
    action_name: AnswerControllerActionName,
    reason: str,
    stable_reason_code: str,
    iteration: int,
    posture: str,
    contract_items_affected: Sequence[str] = (),
    preconditions: Sequence[str] = (),
) -> AnswerControllerActionResult:
    return AnswerControllerActionResult(
        action_name=action_name,
        reason=reason,
        preconditions=_copy_string_tuple(preconditions),
        contract_items_affected=_copy_string_tuple(contract_items_affected),
        stable_reason_code=stable_reason_code,
        iteration=iteration,
        next_state_delta={
            "stop_state": {
                "reason": stable_reason_code,
                "final_answer_posture": posture,
            }
        },
    )


def decide_answer_controller_stop(
    state: AnswerControllerState,
    *,
    marginal_value_judgment: MarginalValueJudgment | None = None,
) -> AnswerControllerStopDecision:
    """Evaluate hard caps, structured checks, and optional marginal value."""
    contract = state.active_contract
    evidence = state.evidence_state_summary
    structured_checks: list[str] = []

    if state.iteration >= state.caps.max_iterations and not evidence.evidence_sufficient:
        return AnswerControllerStopDecision(
            should_stop=True,
            reason=AnswerControllerStopReason.MAX_ITERATIONS,
            public_rationale="The controller reached the iteration cap before resolving the central evidence gap.",
            final_answer_posture=contract.answer_posture_if_partial,
            hard_cap_triggered="max_iterations",
            structured_checks=("evidence_not_sufficient",),
            marginal_value_judgment=marginal_value_judgment,
        )

    total_recovery_attempts = sum(state.recovery_attempts.values())
    if (
        total_recovery_attempts >= state.caps.max_recovery_attempts
        and (evidence.source_classes_missing or evidence.weak_corpus)
        and not evidence.evidence_sufficient
    ):
        reason = (
            AnswerControllerStopReason.OFFICIAL_OR_PRIMARY_UNAVAILABLE
            if set(evidence.source_classes_missing) & _OFFICIAL_OR_PRIMARY_CLASSES
            else AnswerControllerStopReason.MAX_RECOVERY_ATTEMPTS
        )
        return AnswerControllerStopDecision(
            should_stop=True,
            reason=reason,
            public_rationale="A targeted recovery attempt was already spent and the unresolved evidence gap remains central.",
            final_answer_posture=contract.answer_posture_if_partial,
            hard_cap_triggered="max_recovery_attempts",
            structured_checks=("recovery_attempt_spent",),
            marginal_value_judgment=marginal_value_judgment,
        )

    if evidence.evidence_sufficient:
        structured_checks.append("evidence_sufficient")
        return AnswerControllerStopDecision(
            should_stop=True,
            reason=AnswerControllerStopReason.EVIDENCE_SUFFICIENT,
            public_rationale="The evidence state satisfies the central answer contract obligations.",
            final_answer_posture=contract.answer_posture_if_fulfilled,
            structured_checks=tuple(structured_checks),
            marginal_value_judgment=marginal_value_judgment,
        )

    if evidence.next_query_redundant:
        return AnswerControllerStopDecision(
            should_stop=True,
            reason=AnswerControllerStopReason.REDUNDANT_NEXT_QUERY,
            public_rationale="The next candidate query is redundant with already-attempted retrieval.",
            final_answer_posture=contract.answer_posture_if_partial,
            structured_checks=("redundant_next_query",),
            marginal_value_judgment=marginal_value_judgment,
        )

    if (
        not evidence.approved_targeted_queries
        and not evidence.next_queries
        and not evidence.resolving_queries
        and not evidence.evidence_sufficient
    ):
        return AnswerControllerStopDecision(
            should_stop=True,
            reason=AnswerControllerStopReason.NO_USEFUL_NEW_QUERY,
            public_rationale="No non-redundant targeted query is available for the remaining evidence gap.",
            final_answer_posture=contract.answer_posture_if_partial,
            structured_checks=("no_useful_new_query",),
            marginal_value_judgment=marginal_value_judgment,
        )

    if marginal_value_judgment is not None and (
        marginal_value_judgment.caveat_more_honest_than_more_retrieval
        or not marginal_value_judgment.likely_change_answer_posture
    ):
        return AnswerControllerStopDecision(
            should_stop=True,
            reason=AnswerControllerStopReason.MARGINAL_VALUE_LOW,
            public_rationale=marginal_value_judgment.public_rationale,
            final_answer_posture=contract.answer_posture_if_partial,
            structured_checks=("marginal_value_low",),
            marginal_value_judgment=marginal_value_judgment,
        )

    return AnswerControllerStopDecision(
        should_stop=False,
        reason=AnswerControllerStopReason.CONTINUE,
        public_rationale="A targeted controller action may still change the answer posture.",
        final_answer_posture=contract.answer_posture_if_partial,
        structured_checks=("continue_available",),
        marginal_value_judgment=marginal_value_judgment,
    )


def decide_answer_controller_action(
    state: AnswerControllerState,
) -> AnswerControllerActionResult:
    """Choose the next pure controller action for the current contract state."""
    contract = state.active_contract
    evidence = state.evidence_state_summary
    iteration = state.iteration

    stop_decision = decide_answer_controller_stop(state)
    if stop_decision.should_stop and stop_decision.reason is AnswerControllerStopReason.EVIDENCE_SUFFICIENT:
        return _stop_action(
            action_name=AnswerControllerActionName.STOP_SUFFICIENT,
            reason=stop_decision.public_rationale,
            stable_reason_code=stop_decision.reason.value,
            iteration=iteration,
            posture=stop_decision.final_answer_posture,
            contract_items_affected=evidence.fulfilled_obligations or contract.must_satisfy,
            preconditions=stop_decision.structured_checks,
        )

    if (
        contract.social_signal_relevance is SocialSignalRelevance.CENTRAL
        and evidence.social_signal_status not in {"checked", "not_applicable"}
    ):
        return AnswerControllerActionResult(
            action_name=AnswerControllerActionName.REQUEST_SOCIAL_SIGNAL_CHECK,
            reason="The answer contract requires social signal context, but AG-1 has no social provider integration.",
            preconditions=("explicit_social_signal_contract",),
            contract_items_affected=("social_signal",),
            approved_queries_or_none=None,
            skip_reason_or_none="social_provider_not_integrated_ag1",
            stable_reason_code="social_provider_not_integrated_ag1",
            iteration=iteration,
            next_state_delta={
                "social_signal_status": "provider_unavailable",
                "missing_information": ["social signal evidence unavailable in AG-1"],
            },
        )

    if (
        contract.family is AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL
        and (evidence.quantitative_variables_needed or evidence.quantitative_assumptions_needed)
    ):
        affected = evidence.quantitative_variables_needed + evidence.quantitative_assumptions_needed
        return AnswerControllerActionResult(
            action_name=AnswerControllerActionName.DECOMPOSE_QUANTITATIVE_QUESTION,
            reason="The quantitative contract needs explicit variables, units, and assumptions before answer synthesis.",
            preconditions=("quantitative_contract",),
            contract_items_affected=affected,
            approved_queries_or_none=None,
            stable_reason_code="quantitative_variables_or_assumptions_missing",
            iteration=iteration,
            next_state_delta={"missing_information": list(affected)},
        )

    if evidence.weak_corpus:
        if state.recovery_attempts.get("recover_weak_corpus", 0) < state.caps.max_recovery_attempts:
            queries = evidence.next_queries or evidence.approved_targeted_queries or (
                f"{contract.answer_goal} stronger independent evidence",
            )
            return AnswerControllerActionResult(
                action_name=AnswerControllerActionName.RECOVER_WEAK_CORPUS,
                reason=evidence.weak_corpus_reason or "The evidence corpus is too weak for the contract.",
                preconditions=("weak_corpus", "recovery_attempt_available"),
                contract_items_affected=contract.evidence_classes_needed,
                approved_queries_or_none=_copy_string_tuple(queries),
                stable_reason_code="weak_corpus_needs_stronger_evidence",
                iteration=iteration,
                next_state_delta={
                    "recover_weak_corpus_attempted": True,
                    "missing_information": ["stronger independent evidence"],
                },
            )
        return _stop_action(
            action_name=AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
            reason="The weak corpus remains unresolved after the allowed recovery attempt.",
            stable_reason_code=AnswerControllerStopReason.WEAK_CORPUS_UNRESOLVED.value,
            iteration=iteration,
            posture=contract.answer_posture_if_partial,
            contract_items_affected=contract.evidence_classes_needed,
            preconditions=("weak_corpus", "recovery_attempt_cap"),
        )

    if evidence.conflicts_present:
        if evidence.resolving_queries and state.iteration < state.caps.max_iterations:
            return AnswerControllerActionResult(
                action_name=AnswerControllerActionName.RESOLVE_CONFLICT,
                reason="Conflicting evidence is central enough to seek a resolving source before caveating.",
                preconditions=("conflicting_evidence", "resolving_query_available"),
                contract_items_affected=evidence.conflict_notes or contract.must_satisfy,
                approved_queries_or_none=evidence.resolving_queries,
                stable_reason_code="conflict_requires_resolution",
                iteration=iteration,
                next_state_delta={"missing_information": list(evidence.conflict_notes)},
            )
        return _stop_action(
            action_name=AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
            reason="Conflicting evidence remains without a useful resolving query.",
            stable_reason_code=AnswerControllerStopReason.CONFLICT_UNRESOLVED.value,
            iteration=iteration,
            posture=contract.answer_posture_if_partial,
            contract_items_affected=evidence.conflict_notes or contract.must_satisfy,
            preconditions=("conflicting_evidence",),
        )

    missing_source_classes = tuple(
        source_class
        for source_class in contract.evidence_classes_needed
        if source_class in evidence.source_classes_missing
    ) or evidence.source_classes_missing
    if missing_source_classes:
        if state.recovery_attempts.get("recover_missing_source_class", 0) < state.caps.max_recovery_attempts:
            queries = (
                evidence.approved_targeted_queries
                or evidence.next_queries
                or _queries_for_missing_classes(contract, missing_source_classes)
            )
            return AnswerControllerActionResult(
                action_name=AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS,
                reason="A required evidence/source class is missing from the contract state.",
                preconditions=("missing_source_class", "recovery_attempt_available"),
                contract_items_affected=_contract_items_for_classes(
                    contract,
                    missing_source_classes,
                ),
                approved_queries_or_none=_copy_string_tuple(queries),
                stable_reason_code="missing_required_source_class",
                iteration=iteration,
                next_state_delta={
                    "recover_missing_source_class_attempted": True,
                    "missing_information": list(missing_source_classes),
                },
            )
        return _stop_action(
            action_name=AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
            reason="The required source class remains missing after the allowed targeted attempt.",
            stable_reason_code=AnswerControllerStopReason.OFFICIAL_OR_PRIMARY_UNAVAILABLE.value,
            iteration=iteration,
            posture=contract.answer_posture_if_partial,
            contract_items_affected=_contract_items_for_classes(contract, missing_source_classes),
            preconditions=("missing_source_class", "recovery_attempt_cap"),
        )

    if contract.scrutineer_relevance is ScrutineerRelevance.CENTRAL or evidence.scrutineer_needed:
        return AnswerControllerActionResult(
            action_name=AnswerControllerActionName.RUN_SCRUTINEER_REVIEW,
            reason="The answer contract marks Scrutineer review as central.",
            preconditions=("scrutineer_contract_need",),
            contract_items_affected=contract.must_satisfy,
            stable_reason_code="scrutineer_contract_need",
            iteration=iteration,
        )

    if evidence.next_query_redundant:
        return _stop_action(
            action_name=AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
            reason="The next query would repeat already-attempted retrieval.",
            stable_reason_code=AnswerControllerStopReason.REDUNDANT_NEXT_QUERY.value,
            iteration=iteration,
            posture=contract.answer_posture_if_partial,
            contract_items_affected=contract.must_satisfy,
            preconditions=("redundant_next_query",),
        )

    if evidence.approved_targeted_queries or evidence.next_queries:
        queries = evidence.approved_targeted_queries or evidence.next_queries
        return AnswerControllerActionResult(
            action_name=AnswerControllerActionName.RETRIEVE_TARGETED,
            reason="A non-redundant targeted query is available for the remaining contract gap.",
            preconditions=("targeted_query_available",),
            contract_items_affected=contract.must_satisfy,
            approved_queries_or_none=queries,
            stable_reason_code="targeted_query_available",
            iteration=iteration,
        )

    return _stop_action(
        action_name=AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
        reason=stop_decision.public_rationale,
        stable_reason_code=stop_decision.reason.value,
        iteration=iteration,
        posture=stop_decision.final_answer_posture,
        contract_items_affected=contract.must_satisfy,
        preconditions=stop_decision.structured_checks,
    )


def apply_answer_controller_action_result(
    state: AnswerControllerState,
    action_result: AnswerControllerActionResult,
) -> AnswerControllerState:
    """Apply a pure action result to a copied controller state."""
    updated = deepcopy(state)
    updated.action_history.append(deepcopy(action_result))
    updated.iteration = max(updated.iteration, action_result.iteration)
    delta = action_result.next_state_delta

    if delta.get("recover_weak_corpus_attempted"):
        updated.recovery_attempts["recover_weak_corpus"] = (
            updated.recovery_attempts.get("recover_weak_corpus", 0) + 1
        )
    if delta.get("recover_missing_source_class_attempted"):
        updated.recovery_attempts["recover_missing_source_class"] = (
            updated.recovery_attempts.get("recover_missing_source_class", 0) + 1
        )
    if "missing_information" in delta:
        updated.missing_information = list(
            _copy_string_tuple(updated.missing_information + list(delta["missing_information"]))
        )
    if "stop_state" in delta:
        stop_payload = _copy_mapping(delta["stop_state"])
        reason = AnswerControllerStopReason(str(stop_payload.get("reason") or "continue"))
        updated.stop_state = AnswerControllerStopDecision(
            should_stop=reason is not AnswerControllerStopReason.CONTINUE,
            reason=reason,
            public_rationale=action_result.reason,
            final_answer_posture=str(
                stop_payload.get("final_answer_posture")
                or updated.active_contract.answer_posture_if_partial
            ),
            structured_checks=action_result.preconditions,
        )
    return updated


def _actions_taken_and_skipped(
    action_history: Sequence[AnswerControllerActionResult],
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    taken: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for action in action_history:
        payload = {
            "action_name": action.action_name.value,
            "reason": action.reason,
            "stable_reason_code": action.stable_reason_code,
            "iteration": action.iteration,
        }
        if action.skip_reason_or_none is None:
            if action.approved_queries_or_none is not None:
                payload["approved_query_count"] = len(action.approved_queries_or_none)
            taken.append(payload)
        else:
            payload["skip_reason"] = action.skip_reason_or_none
            skipped.append(payload)
    return tuple(taken), tuple(skipped)


def build_answer_contract_fulfillment(
    state: AnswerControllerState,
    *,
    evidence_used: Sequence[EvidenceReference] | None = None,
    warnings_to_Analyst_or_Author: Sequence[str] | None = None,
) -> AnswerContractFulfillment:
    """Build the compact safe fulfillment / ControllerHandoff artifact."""
    contract = state.active_contract
    evidence = state.evidence_state_summary
    if evidence.evidence_sufficient:
        fulfilled = evidence.fulfilled_obligations or contract.must_satisfy
        partial: tuple[str, ...] = ()
        unfulfilled: tuple[str, ...] = ()
    else:
        fulfilled = evidence.fulfilled_obligations
        partial = evidence.partial_obligations
        unfulfilled = evidence.unfulfilled_obligations or _copy_string_tuple(
            tuple(evidence.source_classes_missing)
            + tuple(evidence.missing_information)
            + tuple(state.missing_information)
        )
    fulfilled, partial, unfulfilled, source_class_gaps = (
        _calibrate_fulfillment_for_source_classes(
            contract,
            evidence,
            fulfilled=fulfilled,
            partial=partial,
            unfulfilled=unfulfilled,
        )
    )

    actions_taken, actions_skipped = _actions_taken_and_skipped(state.action_history)
    stop_reason = None if state.stop_state is None else state.stop_state.reason.value
    final_posture = (
        state.stop_state.final_answer_posture
        if state.stop_state is not None
        else contract.answer_posture_if_fulfilled
        if evidence.evidence_sufficient
        else contract.answer_posture_if_partial
    )
    if source_class_gaps and evidence.evidence_sufficient:
        final_posture = contract.answer_posture_if_partial
    social_summary: str | None = None
    if contract.social_signal_relevance is not SocialSignalRelevance.IRRELEVANT:
        status = evidence.social_signal_status or "not_checked"
        if (
            contract.social_signal_relevance is SocialSignalRelevance.CENTRAL
            and not evidence.social_provider_configured
            and status == "not_checked"
        ):
            status = "provider_unavailable"
        if any(
            action.action_name is AnswerControllerActionName.REQUEST_SOCIAL_SIGNAL_CHECK
            and action.skip_reason_or_none
            for action in state.action_history
        ):
            status = "provider_unavailable"
        social_summary = (
            f"social_signal_relevance={contract.social_signal_relevance.value}; status={status}"
        )
    warnings = _copy_string_tuple(
        tuple(warnings_to_Analyst_or_Author or ())
        + tuple(_source_class_gap_warnings(source_class_gaps, evidence))
    )
    source_status = _source_obligation_status(source_class_gaps, evidence)

    return AnswerContractFulfillment(
        fulfilled_items=_copy_string_tuple(fulfilled),
        partial_items=_copy_string_tuple(partial),
        unfulfilled_items=_copy_string_tuple(unfulfilled),
        evidence_used=tuple(evidence_used or ()),
        actions_taken=actions_taken,
        actions_skipped_and_why=actions_skipped,
        contract_revisions=tuple(state.contract_revisions),
        stop_reason=stop_reason,
        final_answer_posture=final_posture,
        source_obligation_status=source_status,
        unfulfilled_source_classes=_copy_string_tuple(source_class_gaps),
        partial_source_classes=(
            _copy_string_tuple(source_class_gaps)
            if source_status == "partial"
            else ()
        ),
        warnings_to_Analyst_or_Author=warnings,
        social_signal_summary=social_summary,
    )


def controller_action_from_source_class_recovery_decision(
    decision: SourceClassRecoveryDecision,
    *,
    iteration: int,
    contract_items_affected: Sequence[str] = (),
) -> AnswerControllerActionResult:
    """Map existing source-class recovery into the AG-1 action vocabulary."""
    approved = decision.decision is SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
    return AnswerControllerActionResult(
        action_name=AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS,
        reason=decision.reason or decision.decision.value,
        preconditions=("source_class_recovery_controller_decision",),
        contract_items_affected=_copy_string_tuple(
            contract_items_affected or decision.missing_expected_source_classes
        ),
        approved_queries_or_none=decision.queries if approved else None,
        skip_reason_or_none=None if approved else decision.reason or decision.decision.value,
        stable_reason_code=(
            "missing_required_source_class"
            if approved
            else decision.reason
            or decision.decision.value
        ),
        iteration=iteration,
        next_state_delta={
            "recover_missing_source_class_attempted": approved,
            "missing_information": list(decision.missing_expected_source_classes),
        },
    )


def controller_action_from_weak_corpus_recovery_decision(
    decision: WeakCorpusRecoveryDecision,
    *,
    iteration: int,
    contract_items_affected: Sequence[str] = (),
) -> AnswerControllerActionResult:
    """Map existing weak-corpus recovery into the AG-1 action vocabulary."""
    approved = decision.decision is WeakCorpusRecoveryControllerDecision.RUN_WEAK_CORPUS_RECOVERY
    return AnswerControllerActionResult(
        action_name=AnswerControllerActionName.RECOVER_WEAK_CORPUS,
        reason=decision.reason,
        preconditions=("weak_corpus_recovery_controller_decision",),
        contract_items_affected=_copy_string_tuple(
            contract_items_affected or ("stronger_independent_evidence",)
        ),
        approved_queries_or_none=decision.queries if approved else None,
        skip_reason_or_none=None if approved else decision.reason,
        stable_reason_code="weak_corpus_first_pass" if approved else decision.reason,
        iteration=iteration,
        next_state_delta={
            "recover_weak_corpus_attempted": approved,
            "missing_information": ["stronger independent evidence"],
        },
    )


def controller_action_from_retrieval_stop_decision(
    decision: RetrievalStopDecision,
    *,
    iteration: int,
) -> AnswerControllerActionResult:
    """Map existing retrieval-stop decisions into the AG-1 stop/action vocabulary."""
    if decision.decision is RetrievalStopControllerDecision.CONTINUE_RETRIEVAL:
        return AnswerControllerActionResult(
            action_name=AnswerControllerActionName.RETRIEVE_TARGETED,
            reason=decision.reason,
            preconditions=("retrieval_stop_controller_continue",),
            approved_queries_or_none=decision.next_queries,
            stable_reason_code=decision.reason,
            iteration=iteration,
        )
    if decision.decision is RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS:
        return AnswerControllerActionResult(
            action_name=AnswerControllerActionName.STOP_SUFFICIENT,
            reason=decision.reason,
            preconditions=("retrieval_stop_controller_sufficient",),
            stable_reason_code=AnswerControllerStopReason.EVIDENCE_SUFFICIENT.value,
            iteration=iteration,
            next_state_delta={
                "stop_state": {
                    "reason": AnswerControllerStopReason.EVIDENCE_SUFFICIENT.value,
                    "final_answer_posture": "answer from sufficient evidence",
                }
            },
        )
    stable_reason = (
        AnswerControllerStopReason.REDUNDANT_NEXT_QUERY.value
        if decision.decision is RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES
        else AnswerControllerStopReason.NO_USEFUL_NEW_QUERY.value
    )
    return AnswerControllerActionResult(
        action_name=AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
        reason=decision.reason,
        preconditions=("retrieval_stop_controller_stop",),
        approved_queries_or_none=None,
        stable_reason_code=stable_reason,
        iteration=iteration,
        next_state_delta={
            "stop_state": {
                "reason": stable_reason,
                "final_answer_posture": "answer with caveats",
            }
        },
    )


def attach_answer_controller_state(
    controller: RunController,
    state: AnswerControllerState,
    *,
    fulfillment: AnswerContractFulfillment | None = None,
) -> RunController:
    """Attach AG-1 state to the passive RunController without trace side effects."""
    controller.state.answer_contract = state.active_contract.to_dict()
    controller.state.answer_contract_evidence_state_summary = (
        state.evidence_state_summary.to_dict()
    )
    controller.state.answer_contract_missing_information = list(state.missing_information)
    controller.state.answer_contract_action_history = [
        action.to_dict() for action in state.action_history
    ]
    controller.state.answer_contract_recovery_attempts = dict(state.recovery_attempts)
    controller.state.answer_contract_stop_state = (
        None if state.stop_state is None else state.stop_state.to_dict()
    )
    controller.state.answer_contract_revisions = [
        revision.to_dict() for revision in state.contract_revisions
    ]
    controller.state.answer_contract_fulfillment_handoff = (
        None if fulfillment is None else fulfillment.to_dict()
    )
    return controller


__all__ = [
    "ANSWER_CONTRACT_FAMILY_DESCRIPTIONS",
    "ANSWER_CONTRACT_FULFILLMENT_SCHEMA_VERSION",
    "ANSWER_CONTRACT_SCHEMA_VERSION",
    "AnswerContract",
    "AnswerContractFamily",
    "AnswerContractFulfillment",
    "AnswerControllerActionName",
    "AnswerControllerActionResult",
    "AnswerControllerCaps",
    "AnswerControllerState",
    "AnswerControllerStopDecision",
    "AnswerControllerStopReason",
    "ControllerHandoff",
    "ContractRevision",
    "EvidenceReference",
    "EvidenceStateSummary",
    "MarginalValueJudgment",
    "ScrutineerRelevance",
    "SocialSignalRelevance",
    "apply_answer_controller_action_result",
    "attach_answer_controller_state",
    "build_answer_contract",
    "build_answer_contract_fulfillment",
    "build_answer_controller_state",
    "controller_action_from_retrieval_stop_decision",
    "controller_action_from_source_class_recovery_decision",
    "controller_action_from_weak_corpus_recovery_decision",
    "decide_answer_controller_action",
    "decide_answer_controller_stop",
    "draft_answer_contract_from_router_metadata",
    "revise_answer_contract",
]
