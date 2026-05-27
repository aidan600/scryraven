"""Tests for generic source tier classification."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.source_classifier import classify_source


def test_official_project_domain() -> None:
    assert classify_source("https://docs.python.org/3/library/os.html") == "official"


def test_official_financial_regulator_sec_gov() -> None:
    assert classify_source("https://www.sec.gov/Archives/edgar/data/320193/") == "official"


def test_official_government_domains() -> None:
    assert classify_source("https://www.epa.gov/greenvehicles") == "official"
    assert classify_source("https://courts.ca.gov/selfhelp-care-court") == "official"
    assert classify_source("https://www.dhcs.ca.gov/services/Pages/CARE-Act.aspx") == "official"


def test_company_primary_tesla_domains() -> None:
    assert classify_source("https://www.tesla.com/investor-relations") == "official"
    assert classify_source("https://ir.tesla.com/#quarterly-disclosure") == "official"


def test_official_financial_archive_with_report_context() -> None:
    assert (
        classify_source(
            "https://www.annualreports.com/HostedData/AnnualReportArchive/a/"
            "NASDAQ_AAPL_2023.pdf",
        )
        == "official"
    )


def test_investor_relations_subdomain_requires_matching_source_context() -> None:
    assert (
        classify_source(
            "https://investor.contoso.com/financials/annual-reports/default.aspx",
            title="Contoso annual reports",
            source_context="Contoso Corporation",
        )
        == "official"
    )
    assert (
        classify_source(
            "https://ir.contoso.com/sec-filings/default.aspx",
            title="SEC filings",
            source_context="Different Company",
        )
        == "unknown"
    )


def test_known_investor_filing_cdn_with_reporting_context() -> None:
    assert (
        classify_source(
            "https://s201.q4cdn.com/123456789/files/doc_financials/2024/ar/"
            "contoso-2024-annual-report.pdf",
        )
        == "official"
    )


def test_social_reddit_url() -> None:
    assert (
        classify_source("https://www.reddit.com/r/learnpython/comments/abc123/title/")
        == "social_or_forum"
    )


def test_trusted_community_wikipedia() -> None:
    assert (
        classify_source(
            "https://en.wikipedia.org/wiki/Python_(programming_language)",
        )
        == "trusted_community"
    )


def test_reputable_news_domains_are_secondary_not_official() -> None:
    for url in (
        "https://www.cbsnews.com/news/california-governor-election/",
        "https://apnews.com/article/california-election-2026",
        "https://www.politico.com/news/2026/05/01/california-governor",
    ):
        assert classify_source(url) == "secondary"


def test_academic_and_scientific_domains_are_secondary_not_official() -> None:
    for url in (
        "https://arxiv.org/abs/2401.00001",
        "https://www.nature.com/articles/s41586-024-00001-0",
        "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567/",
    ):
        assert classify_source(url) == "secondary"


def test_policy_research_nonprofit_is_secondary_not_official_government() -> None:
    assert (
        classify_source("https://theicct.org/publication/global-ev-market-monitor/")
        == "secondary"
    )


def test_low_trust_commercial_rmt_style_url() -> None:
    assert (
        classify_source(
            "https://deals.example-shop.example/buy-in-game-gold-fast-delivery",
        )
        == "low_trust_commercial"
    )


def test_unknown_generic_blog() -> None:
    assert (
        classify_source(
            "https://www.someblog.com/2024/05/local-market-report.html",
            title="Quarterly outlook for regional suppliers",
        )
        == "unknown"
    )


def test_arbitrary_cdn_not_official_even_with_reporting_context() -> None:
    assert (
        classify_source(
            "https://d111111abcdef8.cloudfront.net/files/doc_financials/2024/"
            "annual-report.pdf",
            title="Annual report",
        )
        == "unknown"
    )


def test_generic_finance_and_stock_pages_not_official() -> None:
    assert (
        classify_source(
            "https://www.marketwatch.com/investing/stock/cost/financials",
            title="Costco financials",
        )
        == "unknown"
    )
    assert (
        classify_source(
            "https://finance.example-blog.com/stocks/cost-analysis",
            title="Annual report analysis",
        )
        == "unknown"
    )


def test_academic_and_biomedical_domains_not_official_finance() -> None:
    assert (
        classify_source(
            "https://arxiv.org/abs/2401.00001",
            title="Retail profitability preprint",
        )
        == "secondary"
    )
    assert (
        classify_source(
            "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            title="Biomedical index record",
        )
        == "secondary"
    )


def test_content_mill_title_snippet() -> None:
    assert (
        classify_source(
            "https://www.someblog.com/long-tail-keyword-article",
            title="Widget maintenance: everything you need to know",
            snippet="Quick tips and affiliate disclosure at the bottom.",
        )
        == "content_mill"
    )


def test_social_not_overridden_by_commercial_path_on_same_host() -> None:
    # Host rule wins; do not treat Reddit as official or as "blocked" elsewhere.
    assert (
        classify_source(
            "https://reddit.com/r/example/comments/x/buy-in-game-gold-discussion",
        )
        == "social_or_forum"
    )


def test_trusted_host_not_downgraded_by_mill_like_title() -> None:
    assert (
        classify_source(
            "https://en.wikipedia.org/wiki/Marketing",
            title="Everything you need to know (draft essay)",
        )
        == "trusted_community"
    )
