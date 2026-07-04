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

from core.generic_product_provider_acquisition import (
    BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE,
    BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE,
    PRODUCT_PROVIDER_ACQUISITION_RESPONSE_KIND,
    ProductProviderAcquisitionRequest,
    build_generic_product_provider_acquisition_runner,
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
    assert record["provider_extracted_content_type"] == "text/html"
    assert record["raw_provider_payload_retained"] is False
    assert record["raw_search_response_retained"] is False
    assert "raw_content" not in record


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
            provider="exa",
        )
    )

    assert result.return_code == 2
    assert result.provider_calls_attempted == 0
    assert result.provider_calls_completed == 0
    assert result.blocker == BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE
    assert result.detail == (
        "exa is not available for generic product provider acquisition."
    )
    assert not output_path.exists()


def _provider_text_digest(text: str) -> str:
    encoded = json.dumps(
        {"provider_extracted_text": text},
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(encoded.encode("utf-8")).hexdigest()
