"""PRODUCT-PATH-REGRESSION: generic product provider acquisition adapter.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: generic single-relation live dogfood
product-owned provider acquisition.
Runtime consumer: proplex.mvp_single_relation_live_dogfood_run.
Why ordinary product-path work cannot be done directly: offline validation must
replace Tavily/Serper provider callables to avoid live provider calls and
credential access.
Integration deadline: current phase.
Exit condition: keep while this product-owned adapter feeds the ordinary generic
single-relation product runner, or replace with a broader product-provider
runtime guard.
Why this is not a shadow product path: tests exercise the adapter consumed by
the ordinary runner and verify the same sanitized envelope that the runner
reduces.
Forbidden interpretation: adapter PASS is not live validation, source custody,
evidence, citation eligibility, source-obligation satisfaction, D-prime support,
FAP/Author output, or product correctness.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from core.fetch_read_content_reference import FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS
from core.generic_product_provider_acquisition import (
    BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE,
    BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE,
    BRAVE_SCOUT_PROVIDER,
    EXA_EXTRACTION_PROVIDER,
    LINKUP_EXTRACTION_PROVIDER,
    PRODUCT_PROVIDER_ACQUISITION_RESPONSE_KIND,
    PROVIDER_EXTRACTED_SOURCE_TEXT_MAX_CHARS,
    ProductProviderAcquisitionRequest,
    build_generic_product_provider_acquisition_runner,
)
from core.source_of_record_recovery_provider_config import (
    SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE,
)


def test_tavily_product_provider_results_normalize_raw_content(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []
    extracted_text = "USCIS lists the current Form N-400 paper filing fee as $760."

    def fake_tavily(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        calls.append(kwargs)
        return (
            [
                {
                    "title": "USCIS Form N-400 Filing Fee",
                    "url": "https://www.uscis.gov/forms/filing-fees",
                    "domain": "uscis.gov",
                    "snippet": "Current filing fee table.",
                    "raw_content": extracted_text,
                }
            ],
            [],
        )

    output_path = tmp_path / "provider.json"
    runner = build_generic_product_provider_acquisition_runner(
        tavily_product_provider_callable=fake_tavily,
    )

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="What is the current USCIS Form N-400 paper filing fee?",
            provider="tavily",
            max_results=5,
        )
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    record = payload["results"][0]

    assert result.return_code == 0
    assert result.provider_calls_attempted == 1
    assert result.provider_calls_completed == 1
    assert calls[0]["query"] == "What is the current USCIS Form N-400 paper filing fee?"
    assert calls[0]["max_results"] == 5
    assert calls[0]["search_depth"] == "basic"
    assert payload["request_kind"] == PRODUCT_PROVIDER_ACQUISITION_RESPONSE_KIND
    assert payload["provider"] == "tavily"
    assert payload["raw_provider_payload_retained"] is False
    assert payload["raw_search_response_retained"] is False
    assert record["title"] == "USCIS Form N-400 Filing Fee"
    assert record["url"] == "https://www.uscis.gov/forms/filing-fees"
    assert record["domain"] == "www.uscis.gov"
    assert record["provider_extracted_text"] == extracted_text
    assert record["provider_extracted_text_bounded"] is True
    assert record["provider_extracted_text_sanitized"] is True
    assert record["provider_extracted_text_char_count"] == len(extracted_text)
    assert record["provider_extracted_text_digest"] == _provider_text_digest(
        extracted_text
    )
    assert record["provider_extracted_source_text_digest"] == _provider_text_digest(
        extracted_text
    )
    assert record["provider_extracted_content_type"] == "text/html"
    assert record["raw_provider_payload_retained"] is False
    assert record["raw_search_response_retained"] is False
    assert "raw_content" not in record


def test_linkup_search_results_normalize_as_url_bound_extracted_content(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []
    extracted_text = "USCIS fee schedule says Form N-400 paper filing fee is $760."

    def fake_linkup(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        calls.append(kwargs)
        return (
            [
                {
                    "title": "USCIS Filing Fees",
                    "url": "https://www.uscis.gov/forms/filing-fees",
                    "snippet": "Fee schedule.",
                    "raw_content": extracted_text,
                }
            ],
            [],
        )

    output_path = tmp_path / "linkup-provider.json"
    runner = build_generic_product_provider_acquisition_runner(
        linkup_product_provider_callable=fake_linkup,
    )

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="USCIS N-400 paper filing fee",
            provider=LINKUP_EXTRACTION_PROVIDER,
            acquisition_provider_role=SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE,
            max_results=5,
            include_domains=("uscis.gov",),
            source_of_record_domain_constraints=("uscis.gov",),
        )
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    record = payload["results"][0]

    assert result.return_code == 0
    assert calls == [
        {
            "query": "USCIS N-400 paper filing fee",
            "depth": "standard",
            "output_type": "searchResults",
            "intent": "general",
            "max_results": 5,
            "include_domains": ["uscis.gov"],
        }
    ]
    assert payload["provider"] == "linkup"
    assert payload["provider_role"] == SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE
    assert payload["acquisition_provider_role"] == (
        SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE
    )
    assert record["provider_extracted_text"] == extracted_text
    assert record["provider_extracted_text_sanitized"] is True
    assert record["provider_extracted_text_bounded"] is True
    assert record["raw_provider_payload_retained"] is False
    assert record["raw_search_response_retained"] is False


def test_linkup_sourced_answer_is_not_admitted_as_extracted_content(
    tmp_path: Path,
) -> None:
    def fake_linkup(**_kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        return (
            [
                {
                    "title": "USCIS Filing Fees",
                    "url": "https://www.uscis.gov/forms/filing-fees",
                    "snippet": "Provider-written answer text.",
                    "raw_content": "Provider answer prose says the answer is $760.",
                    "_linkup_sourced_answer": True,
                }
            ],
            [],
        )

    output_path = tmp_path / "linkup-sourced-answer.json"
    runner = build_generic_product_provider_acquisition_runner(
        linkup_product_provider_callable=fake_linkup,
    )

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="USCIS N-400 paper filing fee",
            provider=LINKUP_EXTRACTION_PROVIDER,
        )
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    record = payload["results"][0]

    assert result.return_code == 0
    assert "provider_extracted_text" not in record
    assert "provider_extracted_text_digest" not in record
    assert payload["domain_constraints_satisfy_source_obligation"] is False
    assert payload["domain_constraints_citation_eligible"] is False


def test_exa_text_results_normalize_as_url_bound_extracted_content(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []
    extracted_text = "USCIS Form N-400 paper filing fee appears in this fee table."

    def fake_exa(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        calls.append(kwargs)
        return (
            [
                {
                    "title": "Fee Schedule",
                    "url": "https://www.uscis.gov/g-1055",
                    "snippet": "Fee schedule text.",
                    "raw_content": extracted_text,
                }
            ],
            [],
        )

    output_path = tmp_path / "exa-provider.json"
    runner = build_generic_product_provider_acquisition_runner(
        exa_product_provider_callable=fake_exa,
    )

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="USCIS N-400 paper filing fee",
            provider=EXA_EXTRACTION_PROVIDER,
            include_domains=("uscis.gov",),
        )
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    record = payload["results"][0]

    assert result.return_code == 0
    assert calls == [
        {
            "query": "USCIS N-400 paper filing fee",
            "intent": "general",
            "max_results": 5,
            "include_domains": ["uscis.gov"],
        }
    ]
    assert payload["provider"] == "exa"
    assert record["provider_extracted_text"] == extracted_text
    assert record["provider_extracted_content_type"] == "text/html"
    assert record["provider_extracted_source_text_digest"] == _provider_text_digest(
        extracted_text
    )


def test_tavily_product_provider_preserves_source_digest_above_fetch_window_cap(
    tmp_path: Path,
) -> None:
    prefix = "Agency fee schedule background. " * 120
    answer = "The current filing fee is $42 for this synthetic source. "
    suffix = "Additional sanitized provider-extracted source text. " * 120
    extracted_text = " ".join(f"{prefix}{answer}{suffix}".split())
    assert len(extracted_text) > FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS
    assert len(extracted_text) < PROVIDER_EXTRACTED_SOURCE_TEXT_MAX_CHARS

    def fake_tavily(**_kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        return (
            [
                {
                    "title": "Official Fee Schedule",
                    "url": "https://fees.agency.gov/current",
                    "snippet": "Official current fee schedule.",
                    "raw_content": extracted_text,
                }
            ],
            [],
        )

    output_path = tmp_path / "provider-long.json"
    runner = build_generic_product_provider_acquisition_runner(
        tavily_product_provider_callable=fake_tavily,
    )

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="official current fee schedule",
            provider="tavily",
            max_results=5,
        )
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    record = payload["results"][0]

    assert result.return_code == 0
    assert record["provider_extracted_text"] == extracted_text
    assert record["provider_extracted_text_char_count"] == len(extracted_text)
    assert record["provider_extracted_text_digest"] == _provider_text_digest(
        extracted_text
    )
    assert record["provider_extracted_source_text_digest"] == _provider_text_digest(
        extracted_text
    )
    assert record["provider_extracted_text_bounded"] is True
    assert record["provider_extracted_text_sanitized"] is True
    assert record["raw_provider_payload_retained"] is False
    assert record["raw_search_response_retained"] is False


def test_neutral_domain_constraints_map_inside_current_tavily_adapter(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_tavily(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        calls.append(kwargs)
        return (
            [
                {
                    "title": "Official Fee Schedule",
                    "url": "https://fees.agency.gov/current",
                    "snippet": "Official current fee schedule.",
                    "raw_content": "Official fee schedule lists the current fee as 42.",
                }
            ],
            [],
        )

    output_path = tmp_path / "provider-domain-constraints.json"
    runner = build_generic_product_provider_acquisition_runner(
        tavily_product_provider_callable=fake_tavily,
    )

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="official current fee schedule",
            provider="tavily",
            acquisition_provider_role="extraction_provider",
            domain_constraints=("www.fees.agency.gov",),
            include_domains=("fees.agency.gov",),
            source_of_record_domain_constraints=("fees.agency.gov",),
            exclude_domains=("example-law.invalid",),
        )
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert result.return_code == 0
    assert calls[0]["include_domains"] == ["fees.agency.gov"]
    assert calls[0]["exclude_domains"] == ["example-law.invalid"]
    assert payload["acquisition_provider_role"] == "extraction_provider"
    assert payload["domain_constraints"] == ["fees.agency.gov"]
    assert payload["include_domains"] == ["fees.agency.gov"]
    assert payload["source_of_record_domain_constraints"] == ["fees.agency.gov"]
    assert payload["domain_constraints_acquisition_only"] is True
    assert payload["domain_constraints_create_source_authority"] is False
    assert payload["domain_constraints_satisfy_source_obligation"] is False
    assert payload["domain_constraints_citation_eligible"] is False
    assert payload["domain_constraints_claim_correctness"] is False


def test_serper_scout_results_normalize_without_extracted_text(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_scout(**kwargs: Any) -> list[dict[str, Any]]:
        calls.append(kwargs)
        return [
            {
                "title": "USCIS Form N-400 Filing Fee",
                "url": "https://www.uscis.gov/forms/filing-fees",
                "domain": "uscis.gov",
                "snippet": "Directionality only scout result.",
                "position": 2,
                "date": "2026-07-03",
            }
        ]

    output_path = tmp_path / "scout.json"
    runner = build_generic_product_provider_acquisition_runner(
        scout_product_provider_callable=fake_scout,
    )

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="What is the current filing fee for the form?",
            provider="serper",
            max_results=5,
        )
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    record = payload["results"][0]

    assert result.return_code == 0
    assert calls == [
        {
            "provider": "serper",
            "query": "What is the current filing fee for the form?",
            "max_results": 5,
        }
    ]
    assert payload["provider"] == "serper"
    assert record["title"] == "USCIS Form N-400 Filing Fee"
    assert record["result_rank"] == 2
    assert record["published_or_observed_date"] == "2026-07-03"
    assert record["raw_provider_payload_retained"] is False
    assert record["raw_search_response_retained"] is False
    assert not any(key.startswith("provider_extracted") for key in record)


def test_brave_scout_results_normalize_without_extracted_text(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_scout(**kwargs: Any) -> list[dict[str, Any]]:
        calls.append(kwargs)
        return [
            {
                "title": "USCIS Fee Schedule",
                "url": "https://www.uscis.gov/forms/filing-fees",
                "snippet": "Scout directionality only.",
                "raw_content": "Scout output must not become extracted content.",
            }
        ]

    output_path = tmp_path / "brave-scout.json"
    runner = build_generic_product_provider_acquisition_runner(
        scout_product_provider_callable=fake_scout,
    )

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="USCIS N-400 paper filing fee",
            provider=BRAVE_SCOUT_PROVIDER,
            acquisition_provider_role="source_of_record_recovery_scout_provider",
        )
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    record = payload["results"][0]

    assert result.return_code == 0
    assert calls == [
        {
            "provider": "brave",
            "query": "USCIS N-400 paper filing fee",
            "max_results": 5,
        }
    ]
    assert payload["provider"] == "brave"
    assert record["url"] == "https://www.uscis.gov/forms/filing-fees"
    assert not any(key.startswith("provider_extracted") for key in record)


def test_missing_tavily_credential_fails_closed_without_secret_leak(
    tmp_path: Path,
) -> None:
    def missing_tavily(**_kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        raise RuntimeError("TAVILY_API_KEY is not set; secret-value-not-retained")

    output_path = tmp_path / "missing.json"
    runner = build_generic_product_provider_acquisition_runner(
        tavily_product_provider_callable=missing_tavily,
    )

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="What is the current USCIS Form N-400 paper filing fee?",
            provider="tavily",
        )
    )

    assert result.return_code == 2
    assert result.provider_calls_attempted == 1
    assert result.provider_calls_completed == 0
    assert result.blocker == (
        BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE
    )
    assert result.detail == (
        "TAVILY_API_KEY is unavailable for tavily product provider acquisition."
    )
    assert "secret-value" not in str(result.detail)
    assert not output_path.exists()


def test_missing_serper_credential_fails_closed_without_secret_leak(
    tmp_path: Path,
) -> None:
    def missing_scout(**_kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError("SERPER_API_KEY is not set; secret-value-not-retained")

    output_path = tmp_path / "missing-scout.json"
    runner = build_generic_product_provider_acquisition_runner(
        scout_product_provider_callable=missing_scout,
    )

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="What is the current filing fee for the form?",
            provider="serper",
        )
    )

    assert result.return_code == 2
    assert result.provider_calls_attempted == 1
    assert result.provider_calls_completed == 0
    assert result.blocker == (
        BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE
    )
    assert result.detail == (
        "SERPER_API_KEY is unavailable for serper product provider acquisition."
    )
    assert "secret-value" not in str(result.detail)
    assert not output_path.exists()


def test_unsupported_product_provider_route_fails_closed(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "unsupported.json"
    runner = build_generic_product_provider_acquisition_runner()

    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=tmp_path,
            output_path=output_path,
            query="What is the current filing fee?",
            provider="unsupported-provider",
        )
    )

    assert result.return_code == 2
    assert result.provider_calls_attempted == 0
    assert result.provider_calls_completed == 0
    assert result.blocker == BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE
    assert result.detail == (
        "unsupported-provider is not available for generic product provider "
        "acquisition."
    )
    assert not output_path.exists()


def _provider_text_digest(text: str) -> str:
    encoded = json.dumps(
        {"provider_extracted_text": text},
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(encoded.encode("utf-8")).hexdigest()
