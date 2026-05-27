from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.followup import FollowUpDeps, run_followup, run_web_retrieval
from core.prompts import DEFAULT_SYSTEM
from tests import test_source_hierarchy_answer_contract_invariants_ag57a as ag57a

_ROOT = Path(__file__).resolve().parents[1]

FU_PARAMS = {
    "max_queries": 3,
    "search_depth": "advanced",
    "max_results": 3,
    "top_passage_count": 2,
}


SECONDARY_RULE_PASSAGE = {
    "url": "https://analysis.example/current-threshold-explainer",
    "title": "Secondary eligibility threshold explainer",
    "text": "A secondary explainer summarizes an older threshold without official text.",
    "source_tier": "secondary",
}

COMMUNITY_DOCS_PASSAGE = {
    "url": "https://stackoverflow.com/questions/123/postgresql-mvcc",
    "title": "Community discussion of PostgreSQL MVCC",
    "text": "Community answers discuss MVCC behavior but do not quote official docs.",
    "source_tier": "trusted_community",
}

SECONDARY_DECLARED_OFFICIAL_RULE_PASSAGE = {
    **SECONDARY_RULE_PASSAGE,
    "source_class": "official_current_rules",
}

COMMUNITY_DECLARED_CANONICAL_DOCS_PASSAGE = {
    **COMMUNITY_DOCS_PASSAGE,
    "source_class": "primary_source_documents",
}

ALPHA_ONLY_NUMERIC_PASSAGE = {
    "url": "https://alpha.example/fy2025-defects",
    "title": "Alpha FY2025 defect rate",
    "text": "Alpha reported a fiscal 2025 defect rate of 2.1 percent.",
    "source_tier": "official",
    "source_class": "sourced_numeric_values",
}

SECONDARY_DECLARED_NUMERIC_PASSAGE = {
    "url": "https://analysis.example/fy2025-defects",
    "title": "Secondary FY2025 defect rate summary",
    "text": "A secondary article repeats Alpha defect-rate claims.",
    "source_tier": "secondary",
    "source_class": "sourced_numeric_values",
}

OFFICIAL_RULE_PASSAGE = {
    "url": "https://agency.gov/current-threshold",
    "title": "Official current threshold",
    "text": "The agency states the current eligibility threshold is 42 units.",
    "source_tier": "official",
    "source_class": "official_current_rules",
}

ACADEMIC_PASSAGE = {
    "url": "https://arxiv.org/abs/2601.00001",
    "title": "Empirical study of database concurrency",
    "text": "A preprint reports empirical benchmark evidence.",
    "source_tier": "secondary",
    "source_class": "academic_literature",
}

CONCEPT_PASSAGE = {
    "url": "https://secondary.example/compound-interest",
    "title": "Compound interest overview",
    "text": "Compound interest grows because interest earns additional interest over time.",
    "source_tier": "secondary",
}

FRESH_OFFICIAL_PASSAGE = {
    "url": "https://agency.gov/rules/current-threshold",
    "title": "Fresh official current rule",
    "text": "Fresh official evidence for the current rule.",
    "source_tier": "official",
    "source_class": "official_current_rules",
    "score": 0.95,
}

FRESH_DOCS_PASSAGE = {
    "url": "https://www.postgresql.org/docs/current/mvcc-intro.html",
    "title": "PostgreSQL official MVCC documentation",
    "text": "Official documentation describes MVCC behavior.",
    "source_tier": "official",
    "source_class": "primary_source_documents",
    "score": 0.94,
}

OFFICIAL_DOCS_PASSAGE = {
    "url": "https://www.postgresql.org/docs/current/mvcc-intro.html",
    "title": "PostgreSQL official MVCC documentation",
    "text": "Official documentation describes MVCC behavior.",
    "source_tier": "official",
    "source_class": "primary_source_documents",
}

FRESH_NUMERIC_PASSAGE = {
    "url": "https://beta.example/fy2025-defects",
    "title": "Beta FY2025 defect rate",
    "text": "Beta reported a fiscal 2025 defect rate of 3.4 percent.",
    "source_tier": "official",
    "source_class": "sourced_numeric_values",
    "score": 0.93,
}


@dataclass
class _Harness:
    evaluator_output: str
    search_passages: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        self.embedding_calls: list[dict[str, Any]] = []
        self.evaluator_calls: list[dict[str, Any]] = []
        self.search_calls: list[dict[str, Any]] = []
        self.synthesis_prompts: list[str] = []

    def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        self.embedding_calls.append({"texts": list(texts), "kwargs": dict(kwargs)})
        return [[float(index + 1), 0.0] for index, _text in enumerate(texts)]

    def compute_similarities(
        self,
        _query_embedding: list[float],
        existing_embeddings: list[list[float]],
    ) -> list[float]:
        return [1.0 for _ in existing_embeddings]

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        self.evaluator_calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "require_json": kwargs.get("require_json"),
            }
        )
        return self.evaluator_output

    def search_fn(
        self,
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        max_results: int,
        *_args: Any,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        self.search_calls.append(
            {
                "queries": list(queries),
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "max_results": max_results,
            }
        )
        return [dict(passage) for passage in self.search_passages]

    def synthesis_model_fn(self, prompt: str) -> str:
        self.synthesis_prompts.append(prompt)
        return "synthetic follow-up answer"


def _session(passages: tuple[dict[str, Any], ...], *, report: str = "Saved report.") -> dict[str, Any]:
    return {
        "report": report,
        "top_passages": [dict(passage) for passage in passages],
        "chat_messages": [
            {"role": "user", "content": "Original question."},
            {"role": "assistant", "content": "Saved answer."},
            {"role": "user", "content": "Follow-up placeholder."},
        ],
        "seen_urls": [passage["url"] for passage in passages],
        "collected_images": [],
    }


def _run_followup(
    *,
    query: str,
    passages: tuple[dict[str, Any], ...],
    evaluator_output: str = '{"can_answer": true}',
    search_passages: tuple[dict[str, Any], ...] = (),
    report: str = "Saved report.",
) -> tuple[Any, _Harness]:
    harness = _Harness(
        evaluator_output=evaluator_output,
        search_passages=search_passages,
    )
    deps = FollowUpDeps(
        embed_texts=harness.embed_texts,
        compute_similarities=harness.compute_similarities,
        search_fn=harness.search_fn,
        ask_model=harness.ask_model,
        clean_json_response=lambda value: value,
        synthesis_model_fn=harness.synthesis_model_fn,
    )
    result = run_followup(
        query=query,
        session=_session(passages, report=report),
        deps=deps,
        current_date="2026-05-26",
        follow_complexity="medium",
        fu_params=FU_PARAMS,
        intent="general",
        include_domains=[],
        exclude_domains=[],
        embed_provider="SyntheticEmbeddings",
        embed_model="synthetic-embedding-model",
        fast_provider="SyntheticEvaluator",
        fast_model="synthetic-evaluator-model",
        local_url="",
        api_key="",
        use_reasoning=False,
        chat_evaluator_prompt=DEFAULT_SYSTEM["chat_evaluator"],
        is_plausible_domain=lambda _url: True,
    )
    return result, harness


def test_ag61a_current_official_rule_followup_refreshes_secondary_saved_context() -> None:
    result, harness = _run_followup(
        query="What is the current official eligibility threshold?",
        passages=(SECONDARY_RULE_PASSAGE,),
        search_passages=(FRESH_OFFICIAL_PASSAGE,),
    )

    assert result.memory_result.needs_search is True
    assert result.memory_result.required_source_classes == ("official_current_rules",)
    assert result.memory_result.source_obligation_status == "saved_context_insufficient"
    assert result.web_result.search_ran is True
    assert len(harness.search_calls) == 1
    assert "current official rule" in " ".join(harness.search_calls[0]["queries"])
    assert "Fresh official current rule" in result.synthesis_result.prompt_used


def test_ag61a_secondary_declared_official_current_does_not_satisfy_followup() -> None:
    result, harness = _run_followup(
        query="What is the current official eligibility threshold?",
        passages=(SECONDARY_DECLARED_OFFICIAL_RULE_PASSAGE,),
    )

    assert result.memory_result.needs_search is True
    assert result.memory_result.required_source_classes == ("official_current_rules",)
    assert result.memory_result.source_obligation_status == "saved_context_insufficient"
    assert result.memory_result.saved_context_source_sufficient is False
    assert result.web_result.search_ran is True
    assert harness.search_calls


def test_ag61a_canonical_docs_followup_refreshes_community_saved_context() -> None:
    result, harness = _run_followup(
        query="What do the official PostgreSQL docs say about MVCC behavior?",
        passages=(COMMUNITY_DOCS_PASSAGE,),
        search_passages=(FRESH_DOCS_PASSAGE,),
    )

    assert result.memory_result.needs_search is True
    assert result.memory_result.required_source_classes == ("primary_source_documents",)
    assert result.memory_result.source_obligation_status == "saved_context_insufficient"
    assert result.web_result.search_ran is True
    assert harness.search_calls[0]["queries"]
    assert "official docs" in " ".join(harness.search_calls[0]["queries"])
    assert "Community discussion" in result.synthesis_result.prompt_used
    assert "canonical/official source-obligation" in result.synthesis_result.prompt_used


def test_ag61a_community_declared_canonical_docs_does_not_satisfy_followup() -> None:
    result, harness = _run_followup(
        query="What do the official PostgreSQL reference docs say about MVCC behavior?",
        passages=(COMMUNITY_DECLARED_CANONICAL_DOCS_PASSAGE,),
    )

    assert result.memory_result.needs_search is True
    assert result.memory_result.required_source_classes == ("primary_source_documents",)
    assert result.memory_result.source_obligation_status == "saved_context_insufficient"
    assert result.memory_result.saved_context_source_sufficient is False
    assert result.web_result.search_ran is True
    assert harness.search_calls


def test_ag61a_source_bound_quantitative_followup_does_not_fill_missing_metric() -> None:
    result, harness = _run_followup(
        query="Compare Alpha and Beta on fiscal 2025 defect rate.",
        passages=(ALPHA_ONLY_NUMERIC_PASSAGE,),
        search_passages=(FRESH_NUMERIC_PASSAGE,),
    )

    assert result.memory_result.needs_search is True
    assert result.memory_result.required_source_classes == ("sourced_numeric_values",)
    assert result.memory_result.source_obligation_status == "saved_context_insufficient"
    assert result.web_result.search_ran is True
    prompt = result.synthesis_result.prompt_used.casefold()
    assert "source-bound numeric obligation" in prompt
    assert "do not fill missing metrics" in prompt
    assert "unsupported/model-derived" in prompt


def test_ag61a_secondary_declared_numeric_does_not_satisfy_source_bound_comparison() -> None:
    result, harness = _run_followup(
        query="Compare Alpha and Beta on fiscal 2025 defect rate.",
        passages=(SECONDARY_DECLARED_NUMERIC_PASSAGE,),
    )

    assert result.memory_result.needs_search is True
    assert result.memory_result.required_source_classes == ("sourced_numeric_values",)
    assert result.memory_result.source_obligation_status == "saved_context_insufficient"
    assert result.memory_result.saved_context_source_sufficient is False
    assert result.web_result.search_ran is True
    assert harness.search_calls
    assert "do not fill missing metrics" in result.synthesis_result.prompt_used.casefold()


def test_ag61a_simple_clarification_uses_sufficient_saved_context_without_retrieval() -> None:
    result, harness = _run_followup(
        query="Summarize that saved finding in one sentence.",
        passages=(OFFICIAL_RULE_PASSAGE,),
    )

    assert result.memory_result.needs_search is False
    assert result.memory_result.required_source_classes == ()
    assert result.memory_result.source_obligation_status == "not_required"
    assert result.web_result.search_ran is False
    assert harness.search_calls == []


def test_ag61a_authoritative_canonical_saved_context_still_satisfies_followup() -> None:
    result, harness = _run_followup(
        query="What do the official PostgreSQL docs say about MVCC behavior?",
        passages=(OFFICIAL_DOCS_PASSAGE,),
    )

    assert result.memory_result.needs_search is False
    assert result.memory_result.required_source_classes == ("primary_source_documents",)
    assert result.memory_result.source_obligation_status == "saved_context_sufficient"
    assert result.memory_result.saved_context_source_sufficient is True
    assert result.web_result.search_ran is False
    assert harness.search_calls == []


def test_ag61a_explicit_academic_followup_remains_academic_not_canonical() -> None:
    result, harness = _run_followup(
        query="What peer-reviewed studies evaluate PostgreSQL MVCC performance?",
        passages=(COMMUNITY_DOCS_PASSAGE,),
        search_passages=(ACADEMIC_PASSAGE,),
    )

    assert result.memory_result.needs_search is True
    assert result.memory_result.required_source_classes == ("academic_literature",)
    assert "primary_source_documents" not in result.memory_result.required_source_classes
    assert result.web_result.search_ran is True
    assert "peer reviewed evidence" in " ".join(harness.search_calls[0]["queries"])


def test_ag61a_ordinary_conceptual_followup_not_over_forced_to_official() -> None:
    result, harness = _run_followup(
        query="Why does compound interest accelerate over time?",
        passages=(CONCEPT_PASSAGE,),
    )

    assert result.memory_result.needs_search is False
    assert result.memory_result.required_source_classes == ()
    assert result.memory_result.source_obligation_status == "not_required"
    assert result.web_result.search_ran is False
    assert harness.search_calls == []


def test_ag61a_preserves_insufficiency_posture_when_required_class_remains_missing() -> None:
    result, harness = _run_followup(
        query="What is the current official eligibility threshold?",
        passages=(SECONDARY_RULE_PASSAGE,),
        search_passages=(),
    )

    assert result.memory_result.needs_search is True
    assert result.web_result.search_ran is True
    assert result.web_result.new_passages == []
    assert result.memory_result.source_obligation_status == "saved_context_insufficient"
    prompt = result.synthesis_result.prompt_used
    assert "saved context is insufficient" in prompt
    assert "If new evidence is unavailable or still missing" in prompt
    assert harness.search_calls


def test_ag61a_saved_context_with_required_official_class_does_not_force_retrieval() -> None:
    result, harness = _run_followup(
        query="What is the current official eligibility threshold?",
        passages=(OFFICIAL_RULE_PASSAGE,),
    )

    assert result.memory_result.needs_search is False
    assert result.memory_result.required_source_classes == ("official_current_rules",)
    assert result.memory_result.source_obligation_status == "saved_context_sufficient"
    assert result.web_result.search_ran is False
    assert harness.search_calls == []


def test_ag61a_citation_laundering_guard_reaches_followup_synthesis_prompt() -> None:
    result, _harness = _run_followup(
        query="What do the official PostgreSQL docs say about MVCC behavior?",
        passages=(COMMUNITY_DOCS_PASSAGE,),
        search_passages=(),
    )

    prompt = result.synthesis_result.prompt_used
    assert "Do not cite stale, secondary, community, social, weak, or off-topic saved sources" in prompt
    assert "as satisfying official/current/canonical/legal/source-bound claims" in prompt


def test_ag61a_leakage_guard_redacts_protected_followup_surfaces() -> None:
    result, _harness = _run_followup(
        query="What is the current official eligibility threshold?",
        passages=(
            {
                **SECONDARY_RULE_PASSAGE,
                "text": "raw_prompt provider_payload full_trace should not leak",
            },
        ),
        report="Saved report with quantitative_packet economist_v1 local packet should not leak.",
        search_passages=(),
    )

    prompt = result.synthesis_result.prompt_used
    for marker in (
        "raw_prompt",
        "provider_payload",
        "full_trace",
        "quantitative_packet",
        "economist_v1",
        "local packet",
        "should not leak",
    ):
        assert marker not in prompt
        assert marker.casefold() not in prompt.casefold()
    assert "[redacted protected material]" in prompt


def test_ag61a_mixed_canonical_academic_xfail_remains_preserved() -> None:
    marks = getattr(
        ag57a.test_ag57a_mixed_canonical_and_academic_obligation_needs_multi_source_contract,
        "pytestmark",
        [],
    )

    xfail_marks = [mark for mark in marks if mark.name == "xfail"]
    assert len(xfail_marks) == 1
    assert xfail_marks[0].kwargs["strict"] is True
    assert "mixed canonical plus academic representation gap" in xfail_marks[0].kwargs[
        "reason"
    ]


def test_ag61a_protected_surfaces_remain_closed() -> None:
    prompts = DEFAULT_SYSTEM
    assert "follow-up source-obligation" not in prompts["router"].casefold()
    assert "follow-up source-obligation" not in prompts["researcher"].casefold()
    assert "follow-up source-obligation" not in prompts["analyst"].casefold()
    assert "follow-up source-obligation" not in prompts["author"].casefold()
    assert "follow-up source-obligation" not in prompts["economist"].casefold()
    assert "follow-up source-obligation" not in prompts["scrutineer"].casefold()

    orchestrator_source = (_ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    followup_source = (_ROOT / "core" / "followup.py").read_text(encoding="utf-8")
    retrieval_source = inspect.getsource(run_web_retrieval)

    assert "AG61A" not in orchestrator_source
    assert "select_providers(" not in followup_source
    assert "choose_supplemental_search_depth(" not in followup_source
    assert "rank_sources(" not in followup_source
    assert "search_depth" in retrieval_source
