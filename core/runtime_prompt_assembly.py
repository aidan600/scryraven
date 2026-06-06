"""Prompt construction helpers extracted from the pipeline orchestrator.

These helpers are intentionally mechanical string builders.  They do not call
models/providers/search, choose providers, select evidence, rank retrieval,
format citations, or make policy decisions.  AG-90C keeps prompt text behavior
closed while moving bounded prompt assembly out of the orchestrator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.nutrition_author_notes import _format_nutrition_partial_evidence_author_note


@dataclass(frozen=True, slots=True)
class AnalystCachedPrefixAssembly:
    """Analyst cached-prefix prompt fragment and quant-packet telemetry delta."""

    prefix: str
    evidence_slice: list[Any]
    quant_packet_handoff: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ScrutineerPromptAssembly:
    """Scrutineer system/user prompt pair plus the existing flag limit."""

    flag_limit: int
    system_prompt: str
    user_prompt: str


@dataclass(frozen=True, slots=True)
class AuthorPromptAssembly:
    """Final Author prompt and appended Author notes."""

    prompt: str
    author_notes: str


def evidence_slice_for_analyst(
    *,
    final_top_evidence: Sequence[Any],
    economist_ran: bool,
    report_type: str,
    quant_report_types: Sequence[Any],
) -> list[Any]:
    """Return the same Analyst evidence slice previously built inline."""

    # Bug: report_type is a plain lowercase string (from router JSON + .lower()), but
    # QUANT_REPORT_TYPES may contain Enum members in some invocation paths (e.g. via
    # proplex/__main__.py). A direct `in` check silently returns False on an Enum set,
    # so the 40-chunk cap never triggers. Normalize both sides to str.lower() to fix.
    if not economist_ran and str(report_type).lower() in {
        str(rt).lower() for rt in quant_report_types
    }:
        return list(final_top_evidence[:40])
    return list(final_top_evidence)


def build_analyst_cached_prefix(
    *,
    final_top_evidence: Sequence[Any],
    economist_ran: bool,
    report_type: str,
    quant_report_types: Sequence[Any],
    current_date: str,
    query: str,
    linkup_block: str,
    economist_safety_telemetry: Mapping[str, Any],
    format_analyst_quant_packet_section: Any,
    missing_target_metric_fallback_directive: str,
) -> AnalystCachedPrefixAssembly:
    """Build the Analyst stable prompt prefix without changing its text."""

    sliced = evidence_slice_for_analyst(
        final_top_evidence=final_top_evidence,
        economist_ran=economist_ran,
        report_type=report_type,
        quant_report_types=quant_report_types,
    )
    slim_block = "\n\n".join(
        f"[Source {p['source_id']}] {p['title']}\nURL: {p['url']}\nExcerpt: {p['text'][:1200]}"
        for p in sliced
    )
    prefix = (
        f"<evidence_block>\n{slim_block}\n</evidence_block>\n\n"
        f"Today is {current_date}.\nUser's Original Prompt: {query}\n"
    )
    if linkup_block:
        prefix += linkup_block
    analyst_quant_packet_section, analyst_quant_packet_handoff = (
        format_analyst_quant_packet_section(economist_safety_telemetry)
    )
    if analyst_quant_packet_section:
        prefix += analyst_quant_packet_section
    if missing_target_metric_fallback_directive:
        prefix += missing_target_metric_fallback_directive
    return AnalystCachedPrefixAssembly(
        prefix=prefix,
        evidence_slice=sliced,
        quant_packet_handoff=dict(analyst_quant_packet_handoff),
    )


def build_analyst_prompt(
    *,
    analyst_cached_prefix: str,
    intent: str,
    analyst_effort: str,
    estimate_from_priors: bool = False,
) -> str:
    """Build the Analyst prompt suffix used for normal or priors-framed review."""

    if estimate_from_priors:
        return (
            analyst_cached_prefix
            + f"Context: '{intent}' search requiring '{analyst_effort}' depth.\n"
            "Produce structured bullets per system prompt."
        )
    return (
        analyst_cached_prefix
        + f"Context: '{intent}' search requiring '{analyst_effort}' depth.\nExecute the Evaluation Process."
    )


def build_expander_prompt(
    *,
    query: str,
    core_topic: str,
    diverse_top_evidence: Sequence[Mapping[str, Any]],
) -> str:
    """Build the component-query expander prompt."""

    chunk_summaries = "\n".join(
        f"- [{p['title']}]: {p['text'][:200]}" for p in diverse_top_evidence[:12]
    )
    return (
        f"User query: {query}\n"
        f"Core topic: {core_topic}\n\n"
        f"Initial evidence chunks (summaries):\n{chunk_summaries}\n\n"
        "Identify the most critical component data that is missing."
    )


def build_synthesis_evaluator_prompt(*, query: str, analysis: str) -> str:
    """Build the synthesis completeness evaluator prompt."""

    return (
        f"Original query: {query}\n\nAnalyst synthesis:\n{analysis}\n\n"
        "Execute the synthesis evaluation."
    )


def build_scrutineer_prompt(
    *,
    intent: str,
    default_scrutineer_system: str,
    final_top_evidence: Sequence[Any],
    unique_source_urls: Mapping[str, Any],
    analysis: str,
) -> ScrutineerPromptAssembly:
    """Build the Scrutineer system prompt and audit input."""

    flag_limit = 8 if intent == "news" else 6
    system_prompt = default_scrutineer_system.replace("{flag_limit}", str(flag_limit))
    user_prompt = (
        f"This synthesis was produced from a corpus of {len(final_top_evidence)} source chunks "
        f"drawn from {len(unique_source_urls)} unique URLs. Attribution in the synthesis reflects "
        f"editorial choices about what to cite, not the total available evidence.\n\n"
        f"Analyst synthesis to audit:\n\n{analysis}"
    )
    return ScrutineerPromptAssembly(
        flag_limit=flag_limit,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def build_scrutineer_remediation_prompt(
    *,
    current_date: str,
    core_topic: str,
    past_searches: Sequence[str],
    search_flags: Sequence[Mapping[str, Any]],
) -> str:
    """Build the remediation-query prompt for high-severity Scrutineer flags."""

    flag_lines = "\n".join(
        f"- [{f.get('category')}] {f.get('challenge')}" for f in search_flags
    )
    return (
        f"Today is {current_date}.\nCore topic: {core_topic}\n\n"
        "ALREADY SEARCHED (do not repeat or paraphrase these):\n"
        + "\n".join(f"- {q}" for q in past_searches)
        + f"\n\nAn auditor flagged these specific concerns in a research synthesis:\n{flag_lines}\n\n"
        "Generate 1-2 targeted search queries to find evidence that would resolve these concerns.\n"
        "These queries MUST be meaningfully different from the already-searched list above.\n"
        "If the flagged concern cannot be resolved with a novel query, return an empty array.\n"
        "Queries must be under 10 words. Terse keywords only. No natural language.\n"
        'Return JSON: {"queries": ["query1"]}'
    )


def build_scrutineer_author_block(
    *,
    scrutineer_flags: Sequence[Mapping[str, Any]],
) -> str:
    """Build the final Author-only Scrutineer audit block."""

    high_ct = len(
        [f for f in scrutineer_flags if f.get("severity", "").lower() == "high"]
    )
    med_ct = len(
        [f for f in scrutineer_flags if f.get("severity", "").lower() == "medium"]
    )
    scrutineer_block = (
        f"SCRUTINEER AUDIT — {len(scrutineer_flags)} flag(s) "
        f"({high_ct} high, {med_ct} medium):\n"
    )
    for i, flag in enumerate(scrutineer_flags, 1):
        scrutineer_block += (
            f"\n[{i}] {flag.get('severity', '').upper()} | {flag.get('category', '')}\n"
            f"  Passage: \"{flag.get('passage', '')}\"\n"
            f"  Challenge: {flag.get('challenge', '')}\n"
        )
    scrutineer_block += (
        "\n\nAUTHOR DIRECTIVE: For HIGH flags — hedge, omit, or explicitly note uncertainty. "
        "For MEDIUM flags — add a caveat. LOW flags are advisory. "
        "Do not reference an 'audit', 'scrutineer', or 'reviewer' in your output. "
        "Resolve the flag in the prose silently.\n\n"
    )
    return scrutineer_block


def build_author_prompt(
    *,
    current_date: str,
    query: str,
    tier_instruction: str,
    recency_notes: str,
    complexity: str,
    corpus_weak: bool,
    estimate_from_priors_author: bool,
    relevance_low: bool,
    analysis: str,
    primary_entity: str,
    core_topic: str,
    author_evidence_block: str,
    ordered_sources: Sequence[str],
    nutrition_lookup_telemetry: Mapping[str, Any],
    quant_retrieval_sufficiency_telemetry: Mapping[str, Any],
    final_top_evidence: Sequence[Mapping[str, Any]],
    format_nutrition_partial_evidence_author_note: Any,
    author_notes: str,
    scrutineer_flags: Sequence[Mapping[str, Any]],
    image_context: str,
) -> AuthorPromptAssembly:
    """Build the final Author prompt with exact legacy string concatenation."""

    prompt = (
        f"Today is {current_date}.\nUser's Original Prompt: {query}\n\n"
        f"{tier_instruction}\n\n"
    )
    if recency_notes:
        prompt += recency_notes + "\n\n"
    if complexity != "low" and (not corpus_weak or estimate_from_priors_author) and not relevance_low:
        prompt += f"Analysis:\n{analysis}\n\n"
    if (corpus_weak and not estimate_from_priors_author) or relevance_low:
        prompt += f"Main subject (target): {primary_entity or core_topic}\n"

    prompt += f"Precision Evidence (for accurate citations):\n{author_evidence_block}\n\n"

    if complexity != "low" and (not corpus_weak or estimate_from_priors_author) and not relevance_low:
        prompt += f"Sources:\n{chr(10).join(ordered_sources)}\n\n"

    nutrition_partial_note = format_nutrition_partial_evidence_author_note(
        nutrition_lookup_telemetry=nutrition_lookup_telemetry,
        quant_retrieval_sufficiency_telemetry=quant_retrieval_sufficiency_telemetry,
        final_top_evidence=final_top_evidence,
    )
    if nutrition_partial_note:
        author_notes += nutrition_partial_note

    if author_notes:
        prompt += f"{author_notes}\n\n"

    if complexity == "high" and scrutineer_flags and (not corpus_weak or estimate_from_priors_author) and not relevance_low:
        prompt += build_scrutineer_author_block(scrutineer_flags=scrutineer_flags)

    prompt += f"Write the final markdown report based on the adaptive guidelines.{image_context}"
    return AuthorPromptAssembly(prompt=prompt, author_notes=author_notes)


def select_author_system_prompt(
    *,
    default_system: Mapping[str, str],
    corpus_weak: bool,
    estimate_from_priors_author: bool,
) -> tuple[str, str]:
    """Return the existing Author system prompt text and key."""

    author_system = default_system["author"]
    author_system_prompt_key = "author"
    if corpus_weak:
        if estimate_from_priors_author:
            candidate_author_key = "author_estimate_from_priors"
            author_system = default_system.get(
                candidate_author_key,
                default_system["author"],
            )
            author_system_prompt_key = (
                candidate_author_key if candidate_author_key in default_system else "author"
            )
        else:
            candidate_author_key = "author_corpus_weak"
            author_system = default_system.get(
                candidate_author_key,
                default_system["author"],
            )
            author_system_prompt_key = (
                candidate_author_key if candidate_author_key in default_system else "author"
            )
    return author_system, author_system_prompt_key


def build_image_context(
    *,
    image_mode: str,
    collected_images: Sequence[str],
    corpus_weak: bool,
    estimate_from_priors_author: bool,
) -> str:
    """Build the exact Author image-context prompt fragment."""

    image_context = ""
    if image_mode in ("required", "contextual") and collected_images:
        valid_images = [
            url
            for url in collected_images
            if url.startswith("http")
            and any(
                ext in url.lower()
                for ext in (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                    ".gif",
                    ".avif",
                    "images?",
                    "format=jpg",
                    "format=png",
                )
            )
            and len(url) < 600
        ]
        if valid_images:
            image_list = list(valid_images)[:5]
            image_block = "\n".join(f"- {url}" for url in image_list)
            if image_mode == "required":
                image_context = (
                    f"\n\nAVAILABLE IMAGES:\n{image_block}\n\n"
                    "IMAGE RULES: The user explicitly requested visual content. Embed 2-3 of the best "
                    "images prominently near the beginning of your report using markdown: "
                    "![description](url). Ensure they are central to the answer. "
                    "Only embed an image if the URL or source indicates it is highly relevant to the "
                    "specific subject. Do not use generic or unrelated images."
                )
            else:
                image_context = (
                    f"\n\nAVAILABLE IMAGES:\n{image_block}\n\n"
                    "IMAGE RULES: Embed 1-2 contextually relevant images using markdown: "
                    "![description](url). Place images near the content they illustrate. "
                    "Only embed an image if the URL or source indicates it is highly relevant to "
                    "the specific subject. Do not use generic or unrelated images."
                )
    if corpus_weak and not estimate_from_priors_author:
        image_context = ""
    return image_context


def build_author_tier_instruction(
    *,
    complexity: str,
    corpus_weak: bool,
    estimate_from_priors_author: bool,
    relevance_low: bool,
) -> str:
    """Return the legacy tier instruction selected for the Author prompt."""

    tier_instructions = {
        "low": (
            "TIER: FAST. You are working from unanalyzed search snippets. Do not synthesize competing "
            "claims into a single assertion — present them as reported. Cap confidence language. "
            "Prefer ‘reportedly,’ ‘according to,’ ‘as of [date]’ over "
            "declarative present-tense claims. The absence of an analyst pass means unresolved "
            "conflicts in the evidence should remain visible rather than being collapsed into a single "
            "verdict. Provide a direct opening answer followed by no more than 3-4 short supporting "
            "sentences. No headers. No sources section at the end (use inline citations only). "
            "Tone: direct answer, not a report."
        ),
        "medium": (
            "TIER: BALANCED. Write a structured brief. Use H3 headers for sections, narrative "
            "paragraphs, and a Sources list at the end. For queries that compare two or more entities "
            "across measurable dimensions, include a markdown table summarizing the key metrics before "
            "the narrative sections."
        ),
        "high": (
            "TIER: DEEP. Write a dense, detailed intelligence report. Match the density of the "
            "analysis. Use H3 headers for multiple subsections, detailed cross-source synthesis, and "
            "a Sources list at the end. Use markdown tables to effectively structure comparative data "
            "or dense metrics."
        ),
    }
    thin_body = (corpus_weak and not estimate_from_priors_author) or relevance_low
    if thin_body:
        thin = (
            "TIER: THIN — Retrieved pages are a poor match to the user’s main subject. "
            "Entire output under ~200 words, at most 2-3 short paragraphs, no H3, no table, "
            "no long digests of off-topic material."
        )
        if relevance_low and not (corpus_weak and not estimate_from_priors_author):
            thin = (
                "TIER: THIN — Source–topic match is weak (low utilization). Use Fast-style brevity even though "
                "the run is Balanced/Deep: at most 2-3 short paragraphs, no H3, no table, no long structured report. "
                "State limits clearly; do not pad with generic sections."
            )
        tier_instructions = {"low": thin, "medium": thin, "high": thin}
    return tier_instructions[complexity]


def build_analyst_cached_prefix_from_scope(v: Mapping[str, Any]) -> AnalystCachedPrefixAssembly:
    """Compatibility wrapper over the orchestrator runtime scope; not serialized."""

    return build_analyst_cached_prefix(
        final_top_evidence=v["final_top_evidence"],
        economist_ran=v["economist_ran"],
        report_type=v["report_type"],
        quant_report_types=v["QUANT_REPORT_TYPES"],
        current_date=v["current_date"],
        query=v["query"],
        linkup_block=v["linkup_block"],
        economist_safety_telemetry=v["economist_safety_telemetry"],
        format_analyst_quant_packet_section=v["_format_analyst_quant_packet_section"],
        missing_target_metric_fallback_directive=v[
            "missing_target_metric_fallback_directive"
        ],
    )


def build_author_prompt_from_scope(v: Mapping[str, Any]) -> AuthorPromptAssembly:
    """Compatibility wrapper over the orchestrator runtime scope; not serialized."""

    return build_author_prompt(
        current_date=v["current_date"],
        query=v["query"],
        tier_instruction=build_author_tier_instruction(
            complexity=v["complexity"],
            corpus_weak=v["corpus_weak"],
            estimate_from_priors_author=v["_efp_author"],
            relevance_low=v["_relevance_low"],
        ),
        recency_notes=v["recency_notes"],
        complexity=v["complexity"],
        corpus_weak=v["corpus_weak"],
        estimate_from_priors_author=v["_efp_author"],
        relevance_low=v["_relevance_low"],
        analysis=v["analysis"],
        primary_entity=v["primary_entity"],
        core_topic=v["core_topic"],
        author_evidence_block=v["author_evidence_block"],
        ordered_sources=v["ordered_sources"],
        nutrition_lookup_telemetry=v["nutrition_lookup_telemetry"],
        quant_retrieval_sufficiency_telemetry=v[
            "quant_retrieval_sufficiency_telemetry"
        ],
        final_top_evidence=v["author_evidence"],
        format_nutrition_partial_evidence_author_note=_format_nutrition_partial_evidence_author_note,
        author_notes=v["author_notes"],
        scrutineer_flags=v["scrutineer_flags"],
        image_context=v["image_context"],
    )


@dataclass(frozen=True, slots=True)
class EconomistPreflightPromptAssembly:
    """Economist numerical-anchor preflight prompts."""

    entities: list[str]
    system_prompt: str
    user_prompt: str


@dataclass(frozen=True, slots=True)
class UnsupportedRetrievalPromptAssembly:
    """Unsupported-retrieval analysis directive and Author note."""

    analysis: str
    author_note_append: str


def build_economist_preflight_prompt(
    *,
    entities_list: Sequence[str] | None,
    primary_entity: str,
    core_topic: str,
    final_top_evidence: Sequence[Mapping[str, Any]],
) -> EconomistPreflightPromptAssembly | None:
    """Build the Economist preflight user/system prompts, or None if no entities."""

    entities = [str(e).strip() for e in (entities_list or []) if str(e).strip()]
    if not entities and primary_entity:
        entities = [primary_entity.strip()]
    if not entities and core_topic:
        entities = [str(core_topic).strip()[:200]]
    if not entities:
        return None
    evidence_corpus = "\n\n".join(
        f"[Source {p.get('source_id', '?')}] {p.get('title', '')}\n"
        f"URL: {p.get('url', '')}\n"
        f"Excerpt: {(p.get('text', '') or '')[:1200]}"
        for p in final_top_evidence
    )
    system_prompt = (
        "You classify evidence only. Respond with one JSON object only, no markdown or prose. "
        "Keys must match the entity names provided by the user. "
        "Decisions must be based only on the evidence text in the user message — never on recalled facts."
    )
    user_prompt = (
        "For each entity listed, decide whether a numerical anchor exists for that entity "
        "in the evidence below.\n\n"
        "A numerical anchor does NOT need to come from a formal dataset or financial filing. "
        "Any specific figure (e.g., '$4,500/hour', '10 cents per seat mile', '207 MWh per day') "
        "appearing explicitly in the evidence text qualifies as true. "
        "Do not recall figures from your training data — only evaluate what is present in the provided evidence.\n\n"
        "Examples of qualifying anchors when explicitly in the text: dollar amounts, cents per unit, percentages, "
        "hourly rates, energy per day, seat-mile costs, and similar concrete numbers tied to the entity or its context.\n"
        "Map to `true` only if such a figure appears verbatim in the excerpts below for that entity (or clear same-sentence "
        "attribution). Map to `false` if no specific number appears in the evidence for that entity, or if you would be "
        "relying on memory rather than the text.\n\n"
        "CRITICAL: You must evaluate cross-entity anchor coverage strictly. Map an entity to `true` ONLY if the evidence contains an independent, explicitly stated numerical anchor that applies SPECIFICALLY to that asset at its declared capacity. Do NOT map an entity to `true` if the only available numbers belong to a different capacity tier or a different model within the same family.\n\n"
        'Answer with a JSON object (one key per entity, boolean values only):\n{"<entity_name>": true/false, ...}\n'
        "Return JSON only, no prose.\n\n"
        "Entities:\n"
        + "\n".join(f"- {e}" for e in entities)
        + "\n\nEvidence:\n"
        + (evidence_corpus if evidence_corpus.strip() else "(none)")
    )
    return EconomistPreflightPromptAssembly(
        entities=entities,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def build_unsupported_retrieval_prompt_fragments(
    *,
    analyst_skip_reason: str | None,
    pre_analyst_gate_signals: Sequence[str],
    pre_gate_failure_card_reason: str | None,
) -> UnsupportedRetrievalPromptAssembly:
    """Build the unsupported-retrieval Analyst directive and Author note append."""

    analysis = (
        "UNSUPPORTED_RETRIEVAL_DIRECTIVE:\n"
        f"- Skip reason: {analyst_skip_reason}.\n"
        "- The retrieved corpus does not plausibly support the requested claim.\n"
        "- Do not infer, estimate, or invent missing facts, numeric changes, patch notes, "
        "pricing details, policy details, or release details.\n"
        "- Author should give a concise no-evidence or unsupported-evidence answer using only "
        "the precision evidence and should explicitly name the retrieval limitation."
    )
    signal_text = ", ".join(pre_analyst_gate_signals) if pre_analyst_gate_signals else "none"
    author_note_append = (
        "\n\nNOTE FOR AUTHOR - UNSUPPORTED RETRIEVAL FAST PATH:\n"
        f"Analyst was skipped before expensive analysis because: {analyst_skip_reason}. "
        f"Gate signals: {signal_text}. "
        "Write a concise no-evidence / unsupported-evidence answer. Use the retrieved "
        "precision evidence only to explain the limit; do not invent missing facts, numeric "
        "changes, patch notes, pricing details, or policy details.\n"
    )
    if pre_gate_failure_card_reason:
        author_note_append += f"Failure-card context: {pre_gate_failure_card_reason}\n"
    return UnsupportedRetrievalPromptAssembly(
        analysis=analysis,
        author_note_append=author_note_append,
    )
