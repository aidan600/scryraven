from __future__ import annotations

from core.canonical_technical_docs_policy import (
    is_canonical_technical_documentation_context,
    is_explicit_academic_literature_request,
)
from core.prompts import DEFAULT_SYSTEM
from tests import test_source_hierarchy_answer_contract_invariants_ag57a as ag57a


def test_ag57b_router_prompt_keeps_canonical_docs_distinct_from_academic() -> None:
    router_prompt = DEFAULT_SYSTEM["router"].casefold()

    assert "academic benchmark literature" in router_prompt
    assert "for the user's requested claim" in router_prompt
    assert "documented performance behavior" in router_prompt
    assert "independent academic benchmark evidence" in router_prompt
    assert "canonical/official/project documentation" in router_prompt
    assert "arxiv, benchmarks, or empirical studies" not in router_prompt


def test_ag57b_researcher_prompt_uses_docs_terms_for_canonical_behavior() -> None:
    researcher_prompt = DEFAULT_SYSTEM["researcher"].casefold()

    assert "canonical technical docs" in researcher_prompt
    assert "behavior, configuration/options, reference semantics" in researcher_prompt
    assert "release behavior, documented performance behavior, and tradeoffs" in (
        researcher_prompt
    )
    assert "official/reference/canonical documentation" in researcher_prompt
    assert "do not add paper, arxiv, or academic-literature terms" in (
        researcher_prompt
    )
    assert "do not add study terms unless" in researcher_prompt
    assert "independent academic benchmark evidence" in researcher_prompt


def test_ag57b_policy_positive_cases_are_canonical_docs_oriented() -> None:
    canonical_queries = [
        "official documentation PostgreSQL MVCC concurrency tradeoffs",
        "reference documentation SQLite WAL mode tradeoffs",
        "official documentation Python dataclasses field default behavior",
        "reference docs MDN Fetch API credentials behavior",
    ]

    for query in canonical_queries:
        assert is_canonical_technical_documentation_context(
            query,
            required_source_classes=("primary_source_documents",),
        )
        assert not is_explicit_academic_literature_request(query)


def test_ag57b_explicit_academic_controls_remain_academic() -> None:
    academic_queries = [
        "Find peer-reviewed PostgreSQL MVCC performance studies.",
        "Give me an academic literature review on SQLite WAL benchmarks.",
        "Find arXiv papers about database concurrency.",
    ]

    for query in academic_queries:
        assert is_explicit_academic_literature_request(query)
        assert not is_canonical_technical_documentation_context(
            query,
            required_source_classes=("primary_source_documents",),
        )


def test_ag57b_conceptual_explainer_does_not_force_canonical_docs() -> None:
    query = "Explain why compound interest matters for beginners."

    assert not is_explicit_academic_literature_request(query)
    assert not is_canonical_technical_documentation_context(
        query,
        required_source_classes=("reputable_secondary",),
    )


def test_ag57b_mixed_canonical_academic_gap_remains_strict_xfail() -> None:
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
