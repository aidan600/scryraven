"""Source tier labels on retrieval passages and execution_trace-style aggregates."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.retrieval import compute_similarities
from core.source_classifier import (
    classify_source,
    normalize_source_domain,
    source_domain_telemetry,
    source_tier_telemetry,
)


def test_source_tier_telemetry_counts_and_flags() -> None:
    passages = [
        {"url": "https://docs.python.org/3/", "source_tier": "official"},
        {"url": "https://github.com/foo/bar", "source_tier": "trusted_community"},
        {"url": "https://reddit.com/r/x", "source_tier": "social_or_forum"},
        {"url": "https://x.com/y", "source_tier": "social_or_forum"},
        {"url": "https://spam.example/rmt", "source_tier": "low_trust_commercial"},
        {"url": "https://blog.example/a", "source_tier": "content_mill"},
        {"url": "https://other.example/", "source_tier": "unknown"},
    ]
    tel = source_tier_telemetry(passages)
    assert tel["source_tier_counts"]["official"] == 1
    assert tel["source_tier_counts"]["trusted_community"] == 1
    assert tel["source_tier_counts"]["social_or_forum"] == 2
    assert tel["source_tier_counts"]["low_trust_commercial"] == 1
    assert tel["source_tier_counts"]["content_mill"] == 1
    assert tel["source_tier_counts"]["unknown"] == 1
    assert tel["official_evidence_found"] is True
    assert tel["community_signal_found"] is True
    assert tel["low_trust_sources_found"] is True
    assert tel["pollution_detected"] is True


def test_source_tier_telemetry_preserves_passive_mixed_tiers() -> None:
    passages = [
        {"url": "https://docs.python.org/3/", "source_tier": "official"},
        {"url": "https://standards.example/report", "source_tier": "secondary"},
        {"url": "https://github.com/python/cpython/issues/1", "source_tier": "trusted_community"},
        {"url": "https://reddit.com/r/python/comments/1", "source_tier": "social_or_forum"},
        {"url": "https://analysis.example/post", "source_tier": "unknown"},
        {"url": "https://blank-tier.example/post", "source_tier": ""},
    ]

    tel = source_tier_telemetry(passages)

    assert tel["source_tier_counts"] == {
        "official": 1,
        "secondary": 1,
        "trusted_community": 1,
        "social_or_forum": 1,
        "unknown": 2,
    }
    assert sum(tel["source_tier_counts"].values()) == len(passages)
    assert tel["official_evidence_found"] is True
    assert tel["community_signal_found"] is True
    assert {
        "analyst_skipped",
        "analyst_skip_reason",
        "post_retrieval_fast_path_used",
        "pre_analyst_gate_signals",
    }.isdisjoint(tel)


def test_source_tier_telemetry_empty_passages() -> None:
    tel = source_tier_telemetry([])
    assert tel["source_tier_counts"] == {}
    assert tel["official_evidence_found"] is False
    assert tel["community_signal_found"] is False
    assert tel["low_trust_sources_found"] is False
    assert tel["pollution_detected"] is False


def test_source_tier_telemetry_missing_tier_treated_as_unknown() -> None:
    tel = source_tier_telemetry([{"url": "https://a.example"}])
    assert tel["source_tier_counts"] == {"unknown": 1}
    assert tel["official_evidence_found"] is False


def test_official_financial_sources_set_official_evidence_found() -> None:
    urls = [
        "https://www.sec.gov/Archives/edgar/data/320193/",
        "https://s201.q4cdn.com/123456789/files/doc_financials/2024/ar/"
        "contoso-2024-annual-report.pdf",
        "https://investor.contoso.com/financials/annual-reports/default.aspx",
    ]
    passages = [
        {
            "url": url,
            "source_tier": classify_source(url, source_context="Contoso Corporation"),
        }
        for url in urls
    ]

    tel = source_tier_telemetry(passages)

    assert tel["source_tier_counts"] == {"official": 3}
    assert tel["official_evidence_found"] is True
    assert {
        "analyst_skipped",
        "analyst_skip_reason",
        "economist_ran",
        "economist_output_used_as_analysis",
        "quantitative_packet_validation_errors",
        "author_quant_packet_injected",
    }.isdisjoint(tel)


def test_official_like_domains_are_not_counted_as_unknown() -> None:
    urls = [
        "https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle",
        "https://courts.ca.gov/selfhelp-care-court",
        "https://www.dhcs.ca.gov/services/Pages/CARE-Act.aspx",
        "https://www.sec.gov/Archives/edgar/data/1318605/000095017025014564/",
        "https://ir.tesla.com/#quarterly-disclosure",
    ]
    passages = [
        {
            "url": url,
            "source_tier": classify_source(url, title="Official source"),
        }
        for url in urls
    ]

    tel = source_tier_telemetry(passages)

    assert tel["source_tier_counts"] == {"official": len(urls)}
    assert tel["source_tier_counts"].get("unknown", 0) == 0
    assert tel["official_evidence_found"] is True


def test_reputable_news_domains_are_not_official_evidence() -> None:
    urls = [
        "https://www.cbsnews.com/news/california-governor-election/",
        "https://apnews.com/article/california-election-2026",
        "https://www.politico.com/news/2026/05/01/california-governor",
    ]
    passages = [{"url": url, "source_tier": classify_source(url)} for url in urls]

    tel = source_tier_telemetry(passages)

    assert tel["source_tier_counts"] == {"secondary": len(urls)}
    assert tel["official_evidence_found"] is False


def test_academic_and_preprint_domains_are_not_official_evidence() -> None:
    urls = [
        "https://arxiv.org/abs/2401.00001",
        "https://www.nature.com/articles/s41586-024-00001-0",
        "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567/",
    ]
    passages = [{"url": url, "source_tier": classify_source(url)} for url in urls]

    tel = source_tier_telemetry(passages)

    assert tel["source_tier_counts"] == {"secondary": len(urls)}
    assert tel["official_evidence_found"] is False


def test_epa_passage_sets_official_evidence_found() -> None:
    url = "https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle"
    passages = [
        {
            "url": url,
            "title": "EPA vehicle greenhouse gas emissions",
            "text": "The EPA explains emissions from a typical passenger vehicle.",
            "source_tier": classify_source(
                url,
                title="EPA vehicle greenhouse gas emissions",
                snippet="The EPA explains emissions from a typical passenger vehicle.",
            ),
        }
    ]

    tel = source_tier_telemetry(passages)

    assert tel["source_tier_counts"] == {"official": 1}
    assert tel["official_evidence_found"] is True


def test_official_financial_source_telemetry_does_not_enable_analyst_skip() -> None:
    from core.corpus_state import CorpusState
    from core.pipeline_orchestrator import _pre_analyst_retrieval_gate

    tel = source_tier_telemetry(
        [
            {
                "url": "https://www.sec.gov/Archives/edgar/data/320193/",
                "source_tier": classify_source(
                    "https://www.sec.gov/Archives/edgar/data/320193/",
                ),
            }
        ]
    )

    gate = _pre_analyst_retrieval_gate(
        query="Compare Contoso FY2024 revenue with peers.",
        report_type="quantitative_comparison",
        query_type="quantitative_comparison",
        corpus_state=CorpusState.HEALTHY.value,
        corpus_weak=False,
        failure_card_show=False,
        utilization_rate_val=0.9,
        utilization_threshold=0.35,
        source_tier_counts=tel["source_tier_counts"],
        source_domain_counts={"sec.gov": 1},
        top_source_domains=[{"domain": "sec.gov", "count": 1}],
        on_domain_source_count=1,
        official_evidence_found=tel["official_evidence_found"],
        community_signal_found=tel["community_signal_found"],
    )

    assert gate == {
        "analyst_skipped": False,
        "analyst_skip_reason": None,
        "post_retrieval_fast_path_used": False,
        "pre_analyst_gate_signals": [],
    }


def test_normalize_source_domain_handles_common_url_forms() -> None:
    assert normalize_source_domain("https://www.Example.com/path?q=1") == "example.com"
    assert normalize_source_domain("docs.python.org/3/library") == "docs.python.org"
    assert normalize_source_domain("https://sub.example.com.") == "sub.example.com"
    assert normalize_source_domain("") == ""


def test_source_domain_telemetry_counts_top_domains_and_unique_count() -> None:
    passages = [
        {"url": "https://www.example.com/a"},
        {"url": "https://example.com/b"},
        {"url": "https://docs.python.org/3/"},
        {"url": "https://docs.python.org/3/library/os.html"},
        {"url": "https://reddit.com/r/python"},
        {"url": ""},
    ]

    tel = source_domain_telemetry(passages, domain_anchor="Python")
    assert tel["source_domain_counts"] == {
        "example.com": 2,
        "docs.python.org": 2,
        "reddit.com": 1,
        "unknown": 1,
    }
    assert tel["top_source_domains"][:2] == [
        {"domain": "docs.python.org", "count": 2},
        {"domain": "example.com", "count": 2},
    ]
    assert tel["unique_source_domain_count"] == 4
    assert tel["on_domain_source_count"] == 2
    assert tel["off_domain_source_count"] == 3


def test_source_domain_telemetry_exposes_off_domain_unknown_heavy_mix() -> None:
    passages = [
        {"url": "https://docs.python.org/3/"},
        {"url": "https://news.example/python-release"},
        {"url": "https://news.example/python-followup"},
        {"url": "https://forum.example/thread"},
        {"url": ""},
    ]

    tel = source_domain_telemetry(passages, domain_anchor="Python")

    assert tel["source_domain_counts"] == {
        "docs.python.org": 1,
        "news.example": 2,
        "forum.example": 1,
        "unknown": 1,
    }
    assert sum(tel["source_domain_counts"].values()) == len(passages)
    assert tel["top_source_domains"][0] == {"domain": "news.example", "count": 2}
    assert tel["on_domain_source_count"] == 1
    assert tel["off_domain_source_count"] == 3


def test_source_domain_telemetry_without_anchor_leaves_on_off_counts_zero() -> None:
    tel = source_domain_telemetry(
        [
            {"url": "https://contoso.com/pricing"},
            {"url": "https://example.net/article"},
        ]
    )
    assert tel["source_domain_counts"] == {"contoso.com": 1, "example.net": 1}
    assert tel["on_domain_source_count"] == 0
    assert tel["off_domain_source_count"] == 0


def test_classify_source_snippet_only_content_mill() -> None:
    tier = classify_source(
        "https://neutral.example/article",
        "The ultimate guide to coffee",
        "",
    )
    assert tier == "content_mill"


def test_process_search_queries_attaches_source_tier_per_chunk() -> None:
    from core.pipeline import process_search_queries

    long_snip = "paragraph one.\n\n" + ("word " * 80)
    assert len(long_snip) > 150

    def fake_results(*_a, **_k):
        return (
            [
                {
                    "title": "stdlib",
                    "url": "https://docs.python.org/3/library/os.html",
                    "snippet": long_snip,
                    "raw_content": long_snip,
                    "domain": "docs.python.org",
                    "credibility": 3,
                },
                {
                    "title": "Thread",
                    "url": "https://twitter.com/example/status/1",
                    "snippet": long_snip,
                    "raw_content": long_snip,
                    "domain": "twitter.com",
                    "credibility": 0,
                },
                {
                    "title": "Ultimate guide to foobar",
                    "url": "https://example.com/guide",
                    "snippet": long_snip,
                    "raw_content": long_snip,
                    "domain": "example.com",
                    "credibility": 1,
                },
                {
                    "title": "Listings",
                    "url": "https://example.com/path-rmt-offers",
                    "snippet": long_snip,
                    "raw_content": long_snip,
                    "domain": "example.com",
                    "credibility": 0,
                },
                {
                    "title": "OpenAI annual reports",
                    "url": "https://investor.openai.com/financials/annual-reports/default.aspx",
                    "snippet": long_snip,
                    "raw_content": long_snip,
                    "domain": "investor.openai.com",
                    "credibility": 3,
                },
            ],
            [],
        )

    qemb = [1.0, 0.0, 0.0]

    def embed_fn(texts, **_k):
        return [list(qemb) for _ in texts]

    status = MagicMock()
    with patch("core.pipeline.search_web_results", side_effect=fake_results):
        out = process_search_queries(
            ["q1"],
            "general",
            "low",
            "basic",
            6,
            [],
            [],
            qemb,
            set(),
            set(),
            "OpenAI",
            "text-embedding-3-small",
            "http://localhost",
            embed_fn,
            compute_similarities,
            status_container=status,
            search_providers=["tavily"],
            entity_hint="OpenAI",
        )

    assert len(out) >= 5
    tiers = [p.get("source_tier") for p in out]
    assert "official" in tiers
    assert "social_or_forum" in tiers
    assert "content_mill" in tiers
    assert "low_trust_commercial" in tiers
    assert any(
        p.get("url") == "https://investor.openai.com/financials/annual-reports/default.aspx"
        and p.get("source_tier") == "official"
        for p in out
    )
    tel = source_tier_telemetry(out)
    assert tel["official_evidence_found"] is True
    assert tel["community_signal_found"] is True
    assert tel["low_trust_sources_found"] is True
    assert tel["pollution_detected"] is True
