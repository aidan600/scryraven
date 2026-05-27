"""Post-author telemetry: distinguish displayable output from evidence sufficiency."""

from __future__ import annotations

import re

from core.corpus_state import CorpusState
from core.review_flags import output_matches_refusal

ANSWER_CLASSES = frozenset(
    {
        "answered",
        "partial_answer",
        "no_evidence_found",
        "off_topic_retrieval",
        "declined_by_policy",
    }
)


def _has_sourced_substantive_answer(text: str) -> bool:
    """Heuristic: author included citable source material, not just prose."""
    t = text or ""
    if len(t.split()) < 12:
        return False
    if re.search(r"\]\(https?://", t, re.I):
        return True
    if re.search(r"\[\d+\]\s*\(?https?://", t, re.I):
        return True
    if re.search(r"^#{2,3}\s+sources\b", t, re.I | re.M):
        return True
    return False


def _declined_by_policy(text: str) -> bool:
    tl = (text or "").lower()
    if not tl.strip():
        return False
    needles = (
        "cannot comply with",
        "can't comply with",
        "policy prevents",
        "refuse to answer",
        "unable to assist with that request",
    )
    return any(n in tl for n in needles)


def _unsupported_claim_language(text: str) -> bool:
    """True when the author explicitly says retrieval does not support the requested claim."""
    tl = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if not tl:
        return False
    patterns = (
        r"\bthere is no reliable evidence\b",
        r"\bthere(?:'s| is) no (?:reliable|verified|sourced|direct|public) (?:evidence|source|sources|material)\b",
        r"\bno reliable (?:evidence|source|sources|material) (?:in|from|among) the retrieved\b",
        r"\bretrieved (?:material|evidence|sources?) (?:does not|do not|doesn't|don't) (?:show|support|establish|confirm)\b",
        r"\b(?:available|retrieved) (?:material|evidence|sources?) (?:does not|do not|doesn't|don't) (?:include|contain|provide)\b",
        r"\bno patch notes?,? (?:developer quotes?|dev quotes?|official statements?|stat deltas?)\b",
        r"\bno (?:patch notes?|developer quotes?|dev quotes?|stat deltas?|official statements?)\b",
        r"\bwould be (?:model-derived )?speculation\b",
        r"\bwould amount to speculation\b",
        r"\bany (?:numeric )?(?:forecast|answer|claim|estimate) would be .*speculation\b",
        r"\bunsupported by (?:the )?(?:retrieved|available) (?:evidence|sources?|material)\b",
        r"\bnot supported by (?:the )?(?:retrieved|available) (?:evidence|sources?|material)\b",
    )
    return any(re.search(p, tl, re.I) for p in patterns)


def classify_answer_outcome(
    report: str,
    *,
    corpus_state: str,
    corpus_weak: bool,
    useful_content: bool,
    synth_was_insufficient: bool,
    empty_entity: bool,
) -> tuple[bool, bool, str]:
    """
    Classify after Author: (response_displayable, evidence_sufficient, answer_class).

    ``evidence_sufficient`` means on-topic retrieved evidence supported a sourced answer,
    not merely that the model wrote a safe refusal or used priors.
    """
    text = (report or "").strip()
    if not text:
        return False, False, "no_evidence_found"

    response_displayable = True

    if _declined_by_policy(text):
        return response_displayable, False, "declined_by_policy"

    refusal = output_matches_refusal(text)
    unsupported_claim = _unsupported_claim_language(text)
    has_sources = _has_sourced_substantive_answer(text)
    retrieval_ok = (
        corpus_state == CorpusState.HEALTHY.value
        and not empty_entity
        and not corpus_weak
    )

    evidence_sufficient = (
        retrieval_ok
        and not refusal
        and not unsupported_claim
        and not synth_was_insufficient
        and has_sources
    )

    # answer_class
    if corpus_state == CorpusState.OFF_TOPIC.value:
        answer_class = "off_topic_retrieval"
    elif corpus_state == CorpusState.EMPTY_ENTITY.value:
        if refusal or not useful_content:
            answer_class = "no_evidence_found"
        else:
            answer_class = "partial_answer"
    elif corpus_state == CorpusState.ESTIMATE_FROM_PRIORS.value:
        evidence_sufficient = False
        if useful_content and not refusal:
            answer_class = "partial_answer"
        elif refusal:
            answer_class = "no_evidence_found"
        else:
            answer_class = "no_evidence_found"
    elif retrieval_ok:
        if refusal or unsupported_claim:
            answer_class = "no_evidence_found"
        elif evidence_sufficient:
            answer_class = "answered"
        elif useful_content:
            answer_class = "partial_answer"
        else:
            answer_class = "no_evidence_found"
    else:
        answer_class = "no_evidence_found"

    if corpus_state != CorpusState.HEALTHY.value or empty_entity:
        evidence_sufficient = False
    if corpus_state == CorpusState.HEALTHY.value and synth_was_insufficient and answer_class == "answered":
        answer_class = "partial_answer"

    if answer_class not in ANSWER_CLASSES:
        answer_class = "no_evidence_found"

    return response_displayable, evidence_sufficient, answer_class
