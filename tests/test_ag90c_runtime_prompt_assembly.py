from __future__ import annotations

from pathlib import Path

from core.runtime_prompt_assembly import (
    build_analyst_cached_prefix,
    build_analyst_prompt,
    build_author_prompt,
    build_economist_preflight_prompt,
    build_expander_prompt,
    build_image_context,
    build_scrutineer_prompt,
    build_scrutineer_remediation_prompt,
    build_synthesis_evaluator_prompt,
    build_unsupported_retrieval_prompt_fragments,
    evidence_slice_for_analyst,
    select_author_system_prompt,
)

ROOT = Path(__file__).resolve().parents[1]


def _evidence() -> list[dict[str, str]]:
    return [
        {
            "source_id": "S1",
            "title": "Official Filing",
            "url": "https://example.com/filing",
            "text": "Alpha reported $4,500/hour in the latest filing. " * 80,
        },
        {
            "source_id": "S2",
            "title": "Release Notes",
            "url": "https://example.com/release",
            "text": "Beta release notes mention 207 MWh per day.",
        },
    ]


def test_analyst_cached_prefix_and_prompt_exact_legacy_parity():
    def formatter(_telemetry):
        return (
            "\nQUANTITATIVE PACKET FOR ANALYST REVIEW ONLY\n",
            {"analyst_quant_packet_injected": True},
        )

    evidence = _evidence()
    assembly = build_analyst_cached_prefix(
        final_top_evidence=evidence,
        economist_ran=False,
        report_type="market",
        quant_report_types=["market"],
        current_date="2026-06-06",
        query="Compare Alpha and Beta",
        linkup_block="LINKUP BLOCK\n",
        economist_safety_telemetry={"ok": True},
        format_analyst_quant_packet_section=formatter,
        missing_target_metric_fallback_directive="MISSING TARGET METRIC\n",
    )
    slim_block = "\n\n".join(
        f"[Source {p['source_id']}] {p['title']}\nURL: {p['url']}\nExcerpt: {p['text'][:1200]}"
        for p in evidence
    )
    expected_prefix = (
        f"<evidence_block>\n{slim_block}\n</evidence_block>\n\n"
        "Today is 2026-06-06.\nUser's Original Prompt: Compare Alpha and Beta\n"
        "LINKUP BLOCK\n"
        "\nQUANTITATIVE PACKET FOR ANALYST REVIEW ONLY\n"
        "MISSING TARGET METRIC\n"
    )
    assert assembly.prefix == expected_prefix
    assert assembly.evidence_slice == evidence
    assert assembly.quant_packet_handoff == {"analyst_quant_packet_injected": True}
    assert build_analyst_prompt(
        analyst_cached_prefix=assembly.prefix,
        intent="research",
        analyst_effort="medium",
    ) == (
        expected_prefix
        + "Context: 'research' search requiring 'medium' depth.\nExecute the Evaluation Process."
    )
    assert build_analyst_prompt(
        analyst_cached_prefix=assembly.prefix,
        intent="research",
        analyst_effort="medium",
        estimate_from_priors=True,
    ) == (
        expected_prefix
        + "Context: 'research' search requiring 'medium' depth.\n"
        "Produce structured bullets per system prompt."
    )
    assert len(
        evidence_slice_for_analyst(
            final_top_evidence=list(range(45)),
            economist_ran=False,
            report_type="market",
            quant_report_types=["market"],
        )
    ) == 40


def test_expander_synthesis_scrutineer_and_remediation_prompt_exact_parity():
    evidence = _evidence()
    assert build_expander_prompt(
        query="What is missing?",
        core_topic="Alpha",
        diverse_top_evidence=evidence,
    ) == (
        "User query: What is missing?\n"
        "Core topic: Alpha\n\n"
        "Initial evidence chunks (summaries):\n"
        f"- [Official Filing]: {evidence[0]['text'][:200]}\n"
        f"- [Release Notes]: {evidence[1]['text'][:200]}\n\n"
        "Identify the most critical component data that is missing."
    )
    assert build_synthesis_evaluator_prompt(query="Q", analysis="A") == (
        "Original query: Q\n\nAnalyst synthesis:\nA\n\nExecute the synthesis evaluation."
    )
    scrutineer = build_scrutineer_prompt(
        intent="news",
        default_scrutineer_system="limit {flag_limit}",
        final_top_evidence=evidence,
        unique_source_urls={"https://example.com/filing": {}, "https://example.com/release": {}},
        analysis="Synthesis text",
    )
    assert scrutineer.flag_limit == 8
    assert scrutineer.system_prompt == "limit 8"
    assert scrutineer.user_prompt == (
        "This synthesis was produced from a corpus of 2 source chunks drawn from 2 unique URLs. "
        "Attribution in the synthesis reflects editorial choices about what to cite, not the total available evidence.\n\n"
        "Analyst synthesis to audit:\n\nSynthesis text"
    )
    assert build_scrutineer_remediation_prompt(
        current_date="2026-06-06",
        core_topic="Alpha",
        past_searches=["alpha filing", "beta release"],
        search_flags=[{"category": "TEMPORAL DRIFT", "challenge": "Need current filing"}],
    ) == (
        "Today is 2026-06-06.\nCore topic: Alpha\n\n"
        "ALREADY SEARCHED (do not repeat or paraphrase these):\n"
        "- alpha filing\n- beta release\n\n"
        "An auditor flagged these specific concerns in a research synthesis:\n"
        "- [TEMPORAL DRIFT] Need current filing\n\n"
        "Generate 1-2 targeted search queries to find evidence that would resolve these concerns.\n"
        "These queries MUST be meaningfully different from the already-searched list above.\n"
        "If the flagged concern cannot be resolved with a novel query, return an empty array.\n"
        "Queries must be under 10 words. Terse keywords only. No natural language.\n"
        'Return JSON: {"queries": ["query1"]}'
    )


def test_author_and_preflight_prompt_exact_parity_and_system_key_selection():
    def nutrition_note(**_kwargs):
        return "NUTRITION NOTE\n"

    author = build_author_prompt(
        current_date="2026-06-06",
        query="Original question",
        tier_instruction="TIER: DEEP.",
        recency_notes="RECENCY NOTE",
        complexity="high",
        corpus_weak=False,
        estimate_from_priors_author=False,
        relevance_low=False,
        analysis="Analyst synthesis",
        primary_entity="Alpha",
        core_topic="Alpha topic",
        author_evidence_block="[1] Evidence",
        ordered_sources=["[1] Example"],
        nutrition_lookup_telemetry={},
        quant_retrieval_sufficiency_telemetry={},
        final_top_evidence=_evidence(),
        format_nutrition_partial_evidence_author_note=nutrition_note,
        author_notes="AUTHOR NOTE\n",
        scrutineer_flags=[
            {
                "severity": "high",
                "category": "TEMPORAL DRIFT",
                "passage": "Old claim",
                "challenge": "Confirm current value",
            }
        ],
        image_context="\n\nAVAILABLE IMAGES:\n- https://example.com/a.jpg",
    )
    assert author.author_notes == "AUTHOR NOTE\nNUTRITION NOTE\n"
    assert author.prompt == (
        "Today is 2026-06-06.\nUser's Original Prompt: Original question\n\n"
        "TIER: DEEP.\n\n"
        "RECENCY NOTE\n\n"
        "Analysis:\nAnalyst synthesis\n\n"
        "Precision Evidence (for accurate citations):\n[1] Evidence\n\n"
        "Sources:\n[1] Example\n\n"
        "AUTHOR NOTE\nNUTRITION NOTE\n\n\n"
        "SCRUTINEER AUDIT — 1 flag(s) (1 high, 0 medium):\n"
        "\n[1] HIGH | TEMPORAL DRIFT\n"
        "  Passage: \"Old claim\"\n"
        "  Challenge: Confirm current value\n"
        "\n\nAUTHOR DIRECTIVE: For HIGH flags — hedge, omit, or explicitly note uncertainty. "
        "For MEDIUM flags — add a caveat. LOW flags are advisory. "
        "Do not reference an 'audit', 'scrutineer', or 'reviewer' in your output. "
        "Resolve the flag in the prose silently.\n\n"
        "Write the final markdown report based on the adaptive guidelines.\n\nAVAILABLE IMAGES:\n- https://example.com/a.jpg"
    )
    image_context = build_image_context(
        image_mode="required",
        collected_images=["https://example.com/a.jpg", "ftp://example.com/b.jpg"],
        corpus_weak=False,
        estimate_from_priors_author=False,
    )
    assert "Embed 2-3" in image_context
    assert "ftp://" not in image_context
    prompt = build_economist_preflight_prompt(
        entities_list=["Alpha"],
        primary_entity="",
        core_topic="",
        final_top_evidence=_evidence(),
    )
    assert prompt is not None
    assert prompt.entities == ["Alpha"]
    assert prompt.system_prompt.startswith("You classify evidence only.")
    assert "Entities:\n- Alpha\n\nEvidence:\n[Source S1] Official Filing" in prompt.user_prompt
    unsupported = build_unsupported_retrieval_prompt_fragments(
        analyst_skip_reason="corpus_weak",
        pre_analyst_gate_signals=["low_utilization"],
        pre_gate_failure_card_reason="only off-topic chunks",
    )
    assert unsupported.analysis.startswith("UNSUPPORTED_RETRIEVAL_DIRECTIVE:")
    assert "Failure-card context: only off-topic chunks" in unsupported.author_note_append
    assert select_author_system_prompt(
        default_system={"author": "A", "author_corpus_weak": "CW"},
        corpus_weak=True,
        estimate_from_priors_author=False,
    ) == ("CW", "author_corpus_weak")


def test_runtime_prompt_assembly_helper_has_no_provider_or_model_calls_and_orchestrator_shrank():
    helper = (ROOT / "core" / "runtime_prompt_assembly.py").read_text(encoding="utf-8")
    forbidden = ["ask_model(", "process_search_queries(", "select_providers("]
    assert [token for token in forbidden if token in helper] == []
    assert "DEFAULT_SYSTEM" not in helper
    assert sum(1 for _ in (ROOT / "core" / "pipeline_orchestrator.py").open(encoding="utf-8")) <= 7126
