"""Controller-owned follow-up initial-state contract.

This module is deliberately passive and deterministic. It copies prior
report/session/evidence/posture references and the new follow-up query into a
Controller-owned initial state, then makes the narrowly licensed follow-up
saved-context reuse decision. It does not call providers, run search, route
models, build final answers, select citations, persist sessions, run the
Economist/Scrutineer, change DB schema, cache, or perform live validation.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.authoritative_source_obligations import (
    ACADEMIC_LITERATURE,
    LEGAL_OR_REGULATORY_TEXT,
    OFFICIAL_CURRENT_RULES,
    PRIMARY_SOURCE_DOCUMENTS,
    REPUTABLE_SECONDARY,
    SECONDARY,
    SOCIAL_OR_FORUM,
    SOURCED_NUMERIC_VALUES,
    TRUSTED_COMMUNITY,
    AuthoritativeSourceObligationState,
    AuthorityEvidenceFit,
    AuthorityRequirement,
    AuthorityStatus,
)
from core.canonical_technical_docs_policy import (
    ACADEMIC_LITERATURE_DOMAINS,
    is_canonical_technical_documentation_context,
    is_explicit_academic_literature_request,
)
from core.source_classifier import classify_source, normalize_source_domain

FOLLOWUP_INITIAL_STATE_SCHEMA_VERSION = "AG76D-FU.v1"
FOLLOWUP_INITIAL_STATE_TRACE_KEY = "followup_initial_controller_state"

_REUSE_SUFFICIENT = "reuse_as_sufficient_context"
_REUSE_BACKGROUND = "reuse_as_background_only"
_REUSE_NOT_SUFFICIENT = "do_not_reuse_as_sufficient"

_DATE_BOUND_RE = re.compile(
    r"\b(?:19|20)\d{2}\b"
    r"|\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2},?\s+(?:19|20)\d{2}\b"
    r"|\bq[1-4]\s+(?:19|20)\d{2}\b",
    re.IGNORECASE,
)
_LEGAL_CURRENT_TERMS = (
    "law",
    "legal",
    "regulation",
    "regulatory",
    "statute",
    "court",
    "compliance",
)
_CURRENT_RULE_TERMS = (
    "eligibility",
    "fee",
    "guidance",
    "policy",
    "requirement",
    "rule",
    "status",
    "threshold",
)
_QUANTITATIVE_FOLLOWUP_TERMS = (
    "amount",
    "compare",
    "comparison",
    "cost",
    "defect rate",
    "fee",
    "metric",
    "number",
    "numeric",
    "percentage",
    "rate",
    "revenue",
    "threshold",
)
_AUTHORITY_BOUND_SOURCE_CLASSES = frozenset(
    {
        "current_primary_or_official",
        "legal_or_regulatory_text",
        "official_current_rules",
        "primary_source_documents",
        "sourced_numeric_values",
    }
)
_FOLLOWUP_KERNEL_SOURCE_CLASS_MAP = {
    "academic_literature": ACADEMIC_LITERATURE,
    "current_primary_or_official": OFFICIAL_CURRENT_RULES,
    "legal_or_regulatory_text": LEGAL_OR_REGULATORY_TEXT,
    "official_current_rules": OFFICIAL_CURRENT_RULES,
    "primary_source_documents": PRIMARY_SOURCE_DOCUMENTS,
    "sourced_numeric_values": SOURCED_NUMERIC_VALUES,
}
_FOLLOWUP_CONTEXT_CLASS_BY_TIER = {
    "news": REPUTABLE_SECONDARY,
    "reputable_secondary": REPUTABLE_SECONDARY,
    "secondary": SECONDARY,
    "social": SOCIAL_OR_FORUM,
    "social_or_forum": SOCIAL_OR_FORUM,
    "trusted_community": TRUSTED_COMMUNITY,
    "community": TRUSTED_COMMUNITY,
}
_STOPWORDS = {
    "about",
    "again",
    "also",
    "and",
    "are",
    "does",
    "from",
    "give",
    "have",
    "into",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
}
_SOURCE_CLASS_TO_STRONGER_TYPE = {
    "academic_literature": "academic",
    "legal_or_regulatory_text": "legal_current_primary",
    "official_current_rules": "official_current",
    "primary_source_documents": "canonical",
    "sourced_numeric_values": "source_bound_quantitative",
}


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _hash_payload(value: Any) -> str:
    return sha256(repr(deepcopy(value)).encode("utf-8", errors="replace")).hexdigest()


def _hash_text(value: Any) -> str:
    return sha256(str(value or "").encode("utf-8", errors="replace")).hexdigest()


def _state_ref(value: Any | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return _copy_mapping(value)
    for attr in (
        "to_controller_state",
        "to_trace_fragment",
        "execution_trace_fragment",
        "to_trace",
    ):
        if hasattr(value, attr):
            result = getattr(value, attr)()
            if isinstance(result, Mapping):
                if attr == "to_trace_fragment" and len(result) == 1:
                    only = next(iter(result.values()))
                    if isinstance(only, Mapping):
                        return _copy_mapping(only)
                return _copy_mapping(result)
    return {"ref_type": type(value).__name__}


def _normalized_prompt(prompt: str | None) -> str:
    if not prompt:
        return ""
    return " ".join(str(prompt).casefold().split())


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    for needle in needles:
        if re.fullmatch(r"[a-z0-9]+", needle):
            if re.search(rf"\b{re.escape(needle)}\b", text):
                return True
        elif needle in text:
            return True
    return False


def detect_freshness_cue(prompt: str | None) -> str:
    text = _normalized_prompt(prompt)
    if not text:
        return "none"
    if _contains_any(text, ("latest", "newest", "most recent")):
        return "latest"
    if _contains_any(
        text,
        (
            "current",
            "currently",
            "right now",
            "today",
            "now",
            "as of now",
            "up to date",
            "up-to-date",
        ),
    ):
        return "current"
    if _contains_any(text, ("still true", "still accurate", "still valid", "still the case", "is that still")):
        return "still_true"
    if _contains_any(text, ("new since", "since then", "since the report", "since this was written", "since last")):
        return "new_since"
    if _DATE_BOUND_RE.search(text):
        return "date_bound"
    return "none"


def detect_source_constraint_type(prompt: str | None) -> str:
    text = _normalized_prompt(prompt)
    if not text:
        return "none"
    if _contains_any(text, ("peer-reviewed", "peer reviewed", "journal only", "academic sources")):
        return "peer_reviewed"
    if _contains_any(
        text,
        (
            "official sources",
            "official only",
            "primary sources",
            "primary source",
            "first-party",
            "first party",
            "sec filing",
            "10-k",
            "10-q",
        ),
    ):
        return "official_or_primary"
    if _contains_any(text, ("only from", "using only", "use only", "limit to", "restrict to", "from sources")):
        return "explicit_constraint"
    return "none"


def detect_contradiction_cue(prompt: str | None) -> bool:
    text = _normalized_prompt(prompt)
    if not text:
        return False
    return _contains_any(
        text,
        (
            "contradict",
            "contradicts",
            "contradiction",
            "contradictory",
            "contrary",
            "counterexample",
            "counter evidence",
            "opposing",
            "refute",
            "rebut",
            "challenge that",
            "evidence against",
            "disprove",
            "debunk",
        ),
    )


def has_named_anchor(prompt: str | None) -> bool:
    if not prompt:
        return False
    question_words = {"What", "Which", "Who", "When", "Where", "Why", "How", "Does", "Do", "Is", "Are", "Can"}
    for match in re.finditer(r"\b[A-Z][A-Za-z0-9&.'-]*\b", str(prompt)):
        if match.group(0) not in question_words:
            return True
    return False


def detect_ambiguity_cue(prompt: str | None) -> bool:
    text = _normalized_prompt(prompt)
    if not text or has_named_anchor(prompt):
        return False
    return _contains_any(
        text,
        (
            "the other one",
            "the other",
            "that one",
            "this one",
            "the former",
            "the latter",
            "which one",
            "what about it",
            "what about them",
        ),
    )


def _dedupe_ordered(values: Sequence[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return tuple(out)


def detect_followup_required_source_classes(prompt: str | None) -> tuple[str, ...]:
    text = _normalized_prompt(prompt)
    if not text:
        return ()

    classes: list[str] = []
    if is_explicit_academic_literature_request(text):
        classes.append("academic_literature")
        return _dedupe_ordered(classes)

    source_constraint = detect_source_constraint_type(text)
    freshness_cue = detect_freshness_cue(text)
    has_freshness = freshness_cue != "none"
    has_current_rule_terms = _contains_any(text, _CURRENT_RULE_TERMS)
    has_legal_terms = _contains_any(text, _LEGAL_CURRENT_TERMS)
    has_quantitative_terms = _contains_any(text, _QUANTITATIVE_FOLLOWUP_TERMS)

    if is_canonical_technical_documentation_context(
        text,
        required_source_classes=("primary_source_documents",),
    ) or _contains_any(
        text,
        (
            "official docs",
            "official documentation",
            "canonical docs",
            "reference docs",
            "documentation say",
        ),
    ):
        classes.append("primary_source_documents")

    if has_legal_terms and (has_freshness or source_constraint != "none"):
        classes.append("legal_or_regulatory_text")

    if (
        (has_freshness and has_current_rule_terms)
        or (source_constraint == "official_or_primary" and has_current_rule_terms)
    ):
        classes.append("official_current_rules")

    if has_quantitative_terms and (
        "compare" in text
        or "comparison" in text
        or "metric" in text
        or "rate" in text
        or "number" in text
        or "numeric" in text
    ):
        classes.append("sourced_numeric_values")

    return _dedupe_ordered(classes)


def _passage_source_class_set(passage: Mapping[str, Any]) -> set[str]:
    classes: set[str] = set()
    declared = str(passage.get("source_class") or "").strip()
    if declared and declared not in _AUTHORITY_BOUND_SOURCE_CLASSES:
        classes.add(declared)

    url = str(passage.get("url") or "")
    title = str(passage.get("title") or "")
    snippet = str(passage.get("text") or passage.get("snippet") or "")
    tier = str(passage.get("source_tier") or "").strip().casefold()
    if not tier:
        tier = classify_source(url, title=title, snippet=snippet)
    is_official_tier = tier == "official"

    if is_official_tier:
        classes.update(
            {
                "current_primary_or_official",
                "legal_or_regulatory_text",
                "official_current_rules",
            }
        )
        doc_text = f"{url} {title} {snippet}"
        if _contains_any(
            _normalized_prompt(doc_text),
            (
                "docs",
                "documentation",
                "manual",
                "reference",
                "api",
                "specification",
            ),
        ):
            classes.add("primary_source_documents")
        if declared == "sourced_numeric_values":
            classes.add("sourced_numeric_values")

    domain = normalize_source_domain(url)
    if domain in ACADEMIC_LITERATURE_DOMAINS or any(
        domain.endswith("." + academic_domain)
        for academic_domain in ACADEMIC_LITERATURE_DOMAINS
    ):
        classes.add("academic_literature")

    return classes


def _followup_authority_requirement_for_source_class(
    source_class: str,
    *,
    requirement_id: str | None = None,
) -> AuthorityRequirement | None:
    key = str(source_class or "").strip().casefold()
    active_id = requirement_id or key
    if key == "official_current_rules":
        return AuthorityRequirement.official_current(active_id)
    if key == "primary_source_documents":
        return AuthorityRequirement.canonical_project_doc(active_id)
    if key in {"legal_or_regulatory_text", "current_primary_or_official"}:
        return AuthorityRequirement.legal_current_primary(active_id)
    if key == "academic_literature":
        return AuthorityRequirement.academic_literature(active_id)
    if key == "sourced_numeric_values":
        return AuthorityRequirement.source_bound_numeric(active_id)
    return None


def _followup_context_class_for_passage(passage: Mapping[str, Any]) -> str:
    tier = str(passage.get("source_tier") or "").strip().casefold()
    if not tier:
        tier = classify_source(
            str(passage.get("url") or ""),
            title=str(passage.get("title") or ""),
            snippet=str(passage.get("text") or passage.get("snippet") or ""),
        )
    return _FOLLOWUP_CONTEXT_CLASS_BY_TIER.get(tier, REPUTABLE_SECONDARY)


def _followup_required_authority_slots(
    required_classes: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    slots: list[tuple[str, str]] = []
    for required_class in required_classes:
        if required_class == "sourced_numeric_values":
            slots.extend(
                (
                    ("sourced_numeric_values", "sourced_numeric_values:1"),
                    ("sourced_numeric_values", "sourced_numeric_values:2"),
                )
            )
        else:
            slots.append((required_class, required_class))
    return tuple(slots)


def evaluate_followup_saved_context_authority(
    *,
    passages: Sequence[Mapping[str, Any]],
    required_classes: tuple[str, ...],
) -> AuthoritativeSourceObligationState:
    requirements = tuple(
        requirement
        for required_class, requirement_id in _followup_required_authority_slots(
            required_classes
        )
        for requirement in (
            _followup_authority_requirement_for_source_class(
                required_class,
                requirement_id=requirement_id,
            ),
        )
        if requirement is not None
    )
    if not requirements:
        return AuthoritativeSourceObligationState.evaluate(())

    fits: list[AuthorityEvidenceFit] = []
    numeric_requirement_index = 0
    for index, passage in enumerate(passages):
        passage_classes = _passage_source_class_set(passage)
        evidence_id = f"saved_context:{index}"
        for requirement in requirements:
            required_class = requirement.requirement_id.split(":", 1)[0]
            authority_class = _FOLLOWUP_KERNEL_SOURCE_CLASS_MAP.get(required_class)
            if required_class == "sourced_numeric_values":
                continue
            if required_class in passage_classes and authority_class:
                fits.append(
                    AuthorityEvidenceFit.authoritative(
                        requirement.requirement_id,
                        evidence_id,
                        authority_class,
                    )
                )
                continue
            fits.append(
                AuthorityEvidenceFit.lower_tier_context(
                    requirement.requirement_id,
                    evidence_id,
                    _followup_context_class_for_passage(passage),
                )
            )
        if "sourced_numeric_values" in passage_classes:
            numeric_requirement_index += 1
            target_requirement_id = f"sourced_numeric_values:{numeric_requirement_index}"
            if any(item.requirement_id == target_requirement_id for item in requirements):
                fits.append(
                    AuthorityEvidenceFit.authoritative(
                        target_requirement_id,
                        evidence_id,
                        SOURCED_NUMERIC_VALUES,
                    )
                )
        elif str(passage.get("source_class") or "") == "sourced_numeric_values":
            for requirement in requirements:
                if requirement.requirement_id.startswith("sourced_numeric_values:"):
                    fits.append(
                        AuthorityEvidenceFit.lower_tier_context(
                            requirement.requirement_id,
                            evidence_id,
                            _followup_context_class_for_passage(passage),
                        )
                    )
    return AuthoritativeSourceObligationState.evaluate(requirements, fits)


def saved_context_satisfies_required_classes(
    passages: Sequence[Mapping[str, Any]],
    required_classes: tuple[str, ...],
) -> bool:
    state = evaluate_followup_saved_context_authority(
        passages=passages,
        required_classes=required_classes,
    )
    if not state.requirements:
        return True
    return all(
        state.satisfaction_for(requirement.requirement_id).status
        is AuthorityStatus.FULFILLED
        for requirement in state.requirements
    )


def _keyword_query_from_prompt(prompt: str, suffix: tuple[str, ...]) -> str:
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", prompt.casefold())
        if len(token) > 2 and token not in _STOPWORDS
    ]
    selected = tokens[: max(1, 9 - len(suffix))]
    query_tokens = selected + list(suffix)
    return " ".join(query_tokens[:9])


def build_source_obligation_followup_queries(
    prompt: str,
    required_classes: tuple[str, ...],
    *,
    max_queries: int,
) -> list[str]:
    suffix_by_class = {
        "official_current_rules": ("current", "official", "rule"),
        "legal_or_regulatory_text": ("current", "legal", "primary", "source"),
        "primary_source_documents": ("official", "docs"),
        "academic_literature": ("peer", "reviewed", "evidence"),
        "sourced_numeric_values": ("sourced", "metric"),
    }
    queries: list[str] = []
    for required_class in required_classes:
        suffix = suffix_by_class.get(required_class, ("source", "evidence"))
        queries.append(_keyword_query_from_prompt(prompt, suffix))
    return list(_dedupe_ordered(queries))[:max(1, max_queries)]


def source_obligation_reason(required_classes: tuple[str, ...]) -> str:
    if not required_classes:
        return ""
    if required_classes == ("academic_literature",):
        return "explicit_academic_followup"
    if "sourced_numeric_values" in required_classes:
        return "source_bound_quantitative_followup"
    if "primary_source_documents" in required_classes:
        return "canonical_docs_followup"
    if set(required_classes) & {"official_current_rules", "legal_or_regulatory_text"}:
        return "current_official_or_legal_followup"
    return "source_bound_followup"


def build_source_obligation_note(
    *,
    required_classes: tuple[str, ...],
    status: str,
    reason: str,
    reuse_decision: str | None = None,
) -> str:
    if not required_classes:
        return ""
    classes = ", ".join(required_classes)
    decision = f" Saved-context decision: {reuse_decision}." if reuse_decision else ""
    note = (
        "Follow-up source-obligation note: "
        f"required source classes: {classes}. "
        f"Status: {status}. Reason: {reason}.{decision} "
    )
    if status == "saved_context_insufficient":
        note += (
            "The saved context is insufficient for this new obligation. "
            "The Controller-owned follow-up initial state treats saved context "
            "as background only for this new obligation. Use newly gathered "
            "evidence if it satisfies the required class. If new evidence is "
            "unavailable or still missing, preserve the insufficiency posture "
            "instead of answering confidently. Do not cite stale, secondary, "
            "community, social, weak, or off-topic saved sources as satisfying "
            "official/current/canonical/legal/source-bound claims. "
        )
    if "primary_source_documents" in required_classes:
        note += "This is a canonical/official source-obligation. "
    if "sourced_numeric_values" in required_classes:
        note += (
            "This is a source-bound numeric obligation; do not fill missing "
            "metrics, and keep unsupported/model-derived values distinct from "
            "sourced facts. "
        )
    return note.strip()


def _prior_evidence_refs(passages: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    refs: list[dict[str, Any]] = []
    for index, passage in enumerate(passages or (), 1):
        text = str(passage.get("text") or passage.get("snippet") or "")
        url = str(passage.get("url") or "")
        refs.append(
            {
                "position": index,
                "title": passage.get("title"),
                "url": url,
                "source_id": passage.get("source_id"),
                "source_tier": passage.get("source_tier"),
                "source_class": passage.get("source_class"),
                "domain": normalize_source_domain(url),
                "text_hash": _hash_text(text) if text else None,
                "text_length": len(text),
                "raw_text_included": False,
            }
        )
    return tuple(refs)


def _prior_source_refs(passages: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    seen: set[str] = set()
    refs: list[dict[str, Any]] = []
    for evidence_ref in _prior_evidence_refs(passages):
        url = str(evidence_ref.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        refs.append(
            {
                "url": url,
                "title": evidence_ref.get("title"),
                "source_id": evidence_ref.get("source_id"),
                "source_tier": evidence_ref.get("source_tier"),
                "source_class": evidence_ref.get("source_class"),
                "domain": evidence_ref.get("domain"),
            }
        )
    return tuple(refs)


def _detect_followup_intent(query: str) -> str:
    if detect_ambiguity_cue(query):
        return "ambiguous_reference"
    if detect_contradiction_cue(query):
        return "contradiction_or_counterevidence"
    source_constraint = detect_source_constraint_type(query)
    if source_constraint != "none":
        return f"source_constrained:{source_constraint}"
    freshness = detect_freshness_cue(query)
    if freshness != "none":
        return f"freshness:{freshness}"
    return "continuation_or_clarification"


@dataclass(frozen=True)
class PriorReportReference:
    available: bool
    report_hash: str | None = None
    report_length: int = 0
    session_id: str | None = None
    run_id: str | None = None
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": self.controller_owned,
            "available": self.available,
            "report_hash": self.report_hash,
            "report_length": self.report_length,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "raw_report_included": False,
        }


@dataclass(frozen=True)
class PriorEvidenceReference:
    evidence_refs: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    source_refs: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    ledger_ref: dict[str, Any] = field(default_factory=dict)
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": self.controller_owned,
            "prior_evidence_refs": deepcopy(list(self.evidence_refs)),
            "prior_source_refs": deepcopy(list(self.source_refs)),
            "prior_evidence_count": len(self.evidence_refs),
            "prior_source_count": len(self.source_refs),
            "prior_ledger_ref": deepcopy(self.ledger_ref),
        }


@dataclass(frozen=True)
class PriorAnswerContractReference:
    answer_contract_ref: dict[str, Any] = field(default_factory=dict)
    posture_ref: dict[str, Any] = field(default_factory=dict)
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": self.controller_owned,
            "prior_answer_contract_ref": deepcopy(self.answer_contract_ref),
            "prior_posture_ref": deepcopy(self.posture_ref),
            "prior_answer_contract_available": bool(self.answer_contract_ref),
            "prior_posture_available": bool(self.posture_ref),
        }


@dataclass(frozen=True)
class FollowUpIntentDescriptor:
    query_hash: str
    query_length: int
    intent: str
    freshness_cue_type: str
    source_constraint_type: str
    contradiction_cue_detected: bool
    ambiguity_cue_detected: bool
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": self.controller_owned,
            "new_followup_query_hash": self.query_hash,
            "new_followup_query_length": self.query_length,
            "new_followup_intent": self.intent,
            "freshness_cue_type": self.freshness_cue_type,
            "source_constraint_type": self.source_constraint_type,
            "contradiction_cue_detected": self.contradiction_cue_detected,
            "ambiguity_cue_detected": self.ambiguity_cue_detected,
            "raw_followup_query_included": False,
        }


@dataclass(frozen=True)
class SavedContextReuseDecision:
    saved_context_available: bool
    reuse_decision: str
    reason: str
    saved_context_source_sufficient: bool | str
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": self.controller_owned,
            "saved_context_available": self.saved_context_available,
            "saved_context_reuse_decision": self.reuse_decision,
            "saved_context_reuse_reason": self.reason,
            "saved_context_source_sufficient": self.saved_context_source_sufficient,
        }


@dataclass(frozen=True)
class RefreshedSourceObligationDescriptor:
    required_source_classes: tuple[str, ...] = field(default_factory=tuple)
    source_obligation_status: str = "not_required"
    source_obligation_reason: str = ""
    source_obligation_note: str = ""
    refreshed_source_obligations: bool = False
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": self.controller_owned,
            "refreshed_source_obligations": self.refreshed_source_obligations,
            "required_source_classes": list(self.required_source_classes),
            "source_obligation_status": self.source_obligation_status,
            "source_obligation_reason": self.source_obligation_reason,
            "source_obligation_note_hash": _hash_text(self.source_obligation_note) if self.source_obligation_note else None,
            "source_obligation_note_length": len(self.source_obligation_note),
            "raw_source_obligation_note_included": False,
        }


@dataclass(frozen=True)
class StrongerObligationDetectionDescriptor:
    new_stronger_obligation_detected: bool
    new_stronger_obligation_types: tuple[str, ...] = field(default_factory=tuple)
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": self.controller_owned,
            "new_stronger_obligation_detected": self.new_stronger_obligation_detected,
            "new_stronger_obligation_types": list(self.new_stronger_obligation_types),
        }


@dataclass(frozen=True)
class FollowUpPromptContextDescriptor:
    prompt_context_hash: str | None = None
    prompt_context_length: int = 0
    prompt_context_includes_prior_report_ref: bool = False
    prompt_context_includes_prior_evidence_refs: bool = False
    prompt_context_requires_refreshed_obligations: bool = False
    controller_owned: bool = True

    def with_prompt_context(self, prompt_context: str) -> "FollowUpPromptContextDescriptor":
        return FollowUpPromptContextDescriptor(
            prompt_context_hash=_hash_text(prompt_context),
            prompt_context_length=len(prompt_context or ""),
            prompt_context_includes_prior_report_ref=self.prompt_context_includes_prior_report_ref,
            prompt_context_includes_prior_evidence_refs=self.prompt_context_includes_prior_evidence_refs,
            prompt_context_requires_refreshed_obligations=self.prompt_context_requires_refreshed_obligations,
        )

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": self.controller_owned,
            "prompt_context_hash": self.prompt_context_hash,
            "prompt_context_length": self.prompt_context_length,
            "prompt_context_includes_prior_report_ref": self.prompt_context_includes_prior_report_ref,
            "prompt_context_includes_prior_evidence_refs": self.prompt_context_includes_prior_evidence_refs,
            "prompt_context_requires_refreshed_obligations": self.prompt_context_requires_refreshed_obligations,
            "raw_prompt_context_included": False,
        }


@dataclass(frozen=True)
class FollowUpExecutionEnvelope:
    needs_search: bool
    followup_queries: tuple[str, ...]
    required_source_classes: tuple[str, ...]
    source_obligation_status: str
    source_obligation_reason: str
    source_obligation_note: str
    saved_context_source_sufficient: bool | str
    saved_context_reuse_decision: str
    refreshed_source_obligations: bool
    new_stronger_obligation_detected: bool


@dataclass(frozen=True)
class FollowUpInitialControllerState:
    prior_report_ref: PriorReportReference
    prior_evidence_ref: PriorEvidenceReference
    prior_answer_contract_ref: PriorAnswerContractReference
    followup_intent: FollowUpIntentDescriptor
    saved_context_reuse: SavedContextReuseDecision
    refreshed_obligations: RefreshedSourceObligationDescriptor
    stronger_obligation_detection: StrongerObligationDetectionDescriptor
    prompt_context: FollowUpPromptContextDescriptor
    schema_version: str = FOLLOWUP_INITIAL_STATE_SCHEMA_VERSION
    controller_owned: bool = True
    provider_search_query_behavior_changed: bool = False
    author_final_answer_citation_behavior_changed: bool = False
    economist_behavior_changed: bool = False
    scrutineer_behavior_changed: bool = False
    db_session_schema_changed: bool = False
    cache_behavior_changed: bool = False
    live_behavior_changed: bool = False

    def to_trace(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "controller_owned": self.controller_owned,
            "prior_report": self.prior_report_ref.to_trace(),
            "prior_evidence": self.prior_evidence_ref.to_trace(),
            "prior_answer_contract": self.prior_answer_contract_ref.to_trace(),
            "followup_intent": self.followup_intent.to_trace(),
            "saved_context_reuse": self.saved_context_reuse.to_trace(),
            "refreshed_source_obligations": self.refreshed_obligations.to_trace(),
            "new_stronger_obligation": self.stronger_obligation_detection.to_trace(),
            "prompt_context": self.prompt_context.to_trace(),
            "trace_visibility": {
                "prior_context_reuse_visible": True,
                "refreshed_obligation_requirement_visible": True,
                "saved_context_sufficiency_decision_visible": True,
            },
            "closed_surface_non_changes": {
                "provider_search_query_behavior_changed": self.provider_search_query_behavior_changed,
                "author_final_answer_citation_behavior_changed": self.author_final_answer_citation_behavior_changed,
                "economist_behavior_changed": self.economist_behavior_changed,
                "scrutineer_behavior_changed": self.scrutineer_behavior_changed,
                "db_session_schema_changed": self.db_session_schema_changed,
                "cache_behavior_changed": self.cache_behavior_changed,
                "live_behavior_changed": self.live_behavior_changed,
            },
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {FOLLOWUP_INITIAL_STATE_TRACE_KEY: self.to_trace()}

    def with_prompt_context(self, prompt_context: str) -> "FollowUpInitialControllerState":
        return FollowUpInitialControllerState(
            prior_report_ref=self.prior_report_ref,
            prior_evidence_ref=self.prior_evidence_ref,
            prior_answer_contract_ref=self.prior_answer_contract_ref,
            followup_intent=self.followup_intent,
            saved_context_reuse=self.saved_context_reuse,
            refreshed_obligations=self.refreshed_obligations,
            stronger_obligation_detection=self.stronger_obligation_detection,
            prompt_context=self.prompt_context.with_prompt_context(prompt_context),
        )


def build_followup_initial_controller_state(
    *,
    query: str,
    session: Mapping[str, Any] | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    prior_answer_contract_ref: Any | None = None,
    prior_posture_ref: Any | None = None,
    prior_ledger_ref: Any | None = None,
) -> FollowUpInitialControllerState:
    session_map = _copy_mapping(session)
    top_passages = tuple(session_map.get("top_passages") or ())
    report = str(session_map.get("report") or "")
    active_session_id = session_id or session_map.get("session_id")
    active_run_id = run_id or session_map.get("run_id") or session_map.get("last_run_id")
    available_answer_contract = (
        prior_answer_contract_ref
        or session_map.get("answer_contract_ref")
        or session_map.get("last_answer_contract")
        or session_map.get("answer_contract")
    )
    available_posture = (
        prior_posture_ref
        or session_map.get("posture_ref")
        or session_map.get("last_posture")
        or session_map.get("controller_posture")
    )
    available_ledger = (
        prior_ledger_ref
        or session_map.get("ledger_ref")
        or session_map.get("controller_ledger_ref")
        or session_map.get("controller_ledger")
    )

    required_classes = detect_followup_required_source_classes(query)
    new_stronger_types = tuple(
        _SOURCE_CLASS_TO_STRONGER_TYPE[item]
        for item in required_classes
        if item in _SOURCE_CLASS_TO_STRONGER_TYPE
    )
    stronger_detected = bool(new_stronger_types)
    saved_context_available = bool(report or top_passages)
    saved_context_source_sufficient: bool | str = "not_required"
    source_status = "not_required"
    source_reason = ""
    reuse_reason = "no_new_stronger_obligation"
    reuse_decision = _REUSE_SUFFICIENT if saved_context_available else _REUSE_BACKGROUND

    if required_classes:
        saved_context_source_sufficient = saved_context_satisfies_required_classes(
            top_passages,
            required_classes,
        )
        source_reason = source_obligation_reason(required_classes)
        if saved_context_source_sufficient:
            source_status = "saved_context_sufficient"
            reuse_decision = _REUSE_SUFFICIENT
            reuse_reason = "saved_context_contains_required_source_classes"
        else:
            source_status = "saved_context_insufficient"
            reuse_decision = _REUSE_BACKGROUND
            reuse_reason = "new_stronger_obligation_requires_refreshed_source_obligations"
    elif not saved_context_available:
        reuse_decision = _REUSE_BACKGROUND
        reuse_reason = "no_saved_context_available"

    obligation_note = build_source_obligation_note(
        required_classes=required_classes,
        status=source_status,
        reason=source_reason,
        reuse_decision=reuse_decision,
    )

    prompt_context_descriptor = FollowUpPromptContextDescriptor(
        prompt_context_includes_prior_report_ref=bool(report),
        prompt_context_includes_prior_evidence_refs=bool(top_passages),
        prompt_context_requires_refreshed_obligations=bool(
            stronger_detected and not (saved_context_source_sufficient is True)
        ),
    )

    return FollowUpInitialControllerState(
        prior_report_ref=PriorReportReference(
            available=bool(report),
            report_hash=_hash_text(report) if report else None,
            report_length=len(report),
            session_id=str(active_session_id) if active_session_id else None,
            run_id=str(active_run_id) if active_run_id else None,
        ),
        prior_evidence_ref=PriorEvidenceReference(
            evidence_refs=_prior_evidence_refs(top_passages),
            source_refs=_prior_source_refs(top_passages),
            ledger_ref=_state_ref(available_ledger),
        ),
        prior_answer_contract_ref=PriorAnswerContractReference(
            answer_contract_ref=_state_ref(available_answer_contract),
            posture_ref=_state_ref(available_posture),
        ),
        followup_intent=FollowUpIntentDescriptor(
            query_hash=_hash_text(query),
            query_length=len(query or ""),
            intent=_detect_followup_intent(query),
            freshness_cue_type=detect_freshness_cue(query),
            source_constraint_type=detect_source_constraint_type(query),
            contradiction_cue_detected=detect_contradiction_cue(query),
            ambiguity_cue_detected=detect_ambiguity_cue(query),
        ),
        saved_context_reuse=SavedContextReuseDecision(
            saved_context_available=saved_context_available,
            reuse_decision=reuse_decision,
            reason=reuse_reason,
            saved_context_source_sufficient=saved_context_source_sufficient,
        ),
        refreshed_obligations=RefreshedSourceObligationDescriptor(
            required_source_classes=required_classes,
            source_obligation_status=source_status,
            source_obligation_reason=source_reason,
            source_obligation_note=obligation_note,
            refreshed_source_obligations=bool(required_classes),
        ),
        stronger_obligation_detection=StrongerObligationDetectionDescriptor(
            new_stronger_obligation_detected=stronger_detected,
            new_stronger_obligation_types=new_stronger_types,
        ),
        prompt_context=prompt_context_descriptor,
    )


def execute_followup_initial_state_handoff(
    *,
    state: FollowUpInitialControllerState,
    prompt: str,
    needs_search: bool,
    followup_queries: Sequence[str],
    max_queries: int,
) -> FollowUpExecutionEnvelope:
    next_needs_search = bool(needs_search)
    next_queries = list(followup_queries or [])
    required_classes = state.refreshed_obligations.required_source_classes
    if (
        required_classes
        and state.saved_context_reuse.saved_context_source_sufficient is not True
        and not next_needs_search
    ):
        next_needs_search = True
        if not next_queries:
            next_queries = build_source_obligation_followup_queries(
                prompt,
                required_classes,
                max_queries=max_queries,
            )
    return FollowUpExecutionEnvelope(
        needs_search=next_needs_search,
        followup_queries=tuple(next_queries[: max(1, max_queries)]),
        required_source_classes=required_classes,
        source_obligation_status=state.refreshed_obligations.source_obligation_status,
        source_obligation_reason=state.refreshed_obligations.source_obligation_reason,
        source_obligation_note=state.refreshed_obligations.source_obligation_note,
        saved_context_source_sufficient=state.saved_context_reuse.saved_context_source_sufficient,
        saved_context_reuse_decision=state.saved_context_reuse.reuse_decision,
        refreshed_source_obligations=state.refreshed_obligations.refreshed_source_obligations,
        new_stronger_obligation_detected=state.stronger_obligation_detection.new_stronger_obligation_detected,
    )


def prompt_context_metadata(
    *,
    state: FollowUpInitialControllerState,
    prompt_context: str,
) -> FollowUpInitialControllerState:
    return state.with_prompt_context(prompt_context)
