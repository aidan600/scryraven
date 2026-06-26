from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

import core.pipeline as pipeline
from core.cap_enforcement import RunCapExceeded, RunCapPolicy
from core.evidence_ledger import EvidenceLedger
from core.final_answer_packet import SourceObligationStatus
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.run_config import RunConfig, SourceCustodyPolicy
from core.validation_profiles import AG_LIVE_SOURCE_CUSTODY, get_validation_profile
from scripts import ag_live_bound_01_support as support

_DOC_URL = "https://docs.python.org/3/library/math.html#math.isclose"
_FULL_TEXT = (
    "Official Python documentation says math.isclose has default values for "
    "rel_tol and abs_tol. "
    * 20
)
_SNIPPET = (
    "Official Python documentation snippet says rel_tol defaults to 1e-09 and "
    "abs_tol defaults to 0.0. "
    * 4
)


def _cap_policy(*, max_fetch_read_operations: int = 1) -> RunCapPolicy:
    return RunCapPolicy(
        max_search_dispatches=2,
        max_fetch_read_operations=max_fetch_read_operations,
        max_author_model_calls=1,
        max_smart_search_judgment_model_calls=0,
        max_retries=0,
    )


def _custody_policy() -> SourceCustodyPolicy:
    return SourceCustodyPolicy(
        require_official_full_fetch_read=True,
        max_forced_fetch_reads=1,
        preferred_domains=("docs.python.org",),
        required_source_class="primary_source_documents",
        required_source_tier="official",
        required_currentness="current",
        requirement_id="ag-src-custody-01:official-doc-full-read",
    )


def _official_search_result() -> dict[str, Any]:
    return {
        "title": "math.isclose docs",
        "url": _DOC_URL,
        "domain": "docs.python.org",
        "credibility": 1,
        "snippet": _SNIPPET,
        "raw_content": _SNIPPET,
    }


def _run_search(
    monkeypatch: pytest.MonkeyPatch,
    *,
    source_custody_policy: SourceCustodyPolicy | None = None,
    cap_policy: RunCapPolicy | None = None,
    fetch_page: Any | None = None,
) -> list[dict[str, Any]]:
    search_calls: list[str] = []

    def fake_search_web_results(query: str, **_kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        search_calls.append(query)
        return [_official_search_result()], []

    monkeypatch.setattr(pipeline, "search_web_results", fake_search_web_results)
    if fetch_page is not None:
        monkeypatch.setattr(pipeline, "fetch_page", fetch_page)

    passages = pipeline.process_search_queries(
        ["python math isclose docs"],
        "general",
        "medium",
        "basic",
        1,
        ["docs.python.org"],
        [],
        None,
        set(),
        set(),
        "offline-embed-provider",
        "offline-embed-model",
        None,
        lambda *_args, **_kwargs: [],
        lambda *_args, **_kwargs: [],
        search_providers=["tavily"],
        cap_policy=cap_policy,
        source_custody_policy=source_custody_policy,
    )
    assert search_calls == ["python math isclose docs"]
    return passages


def test_policy_disabled_preserves_official_snippet_without_forced_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetch_called = False

    def fail_fetch(_item: Any) -> None:
        nonlocal fetch_called
        fetch_called = True
        raise AssertionError("policy-disabled run should not fetch")

    passages = _run_search(monkeypatch, fetch_page=fail_fetch)

    assert fetch_called is False
    assert passages
    assert passages[0]["url"] == _DOC_URL
    assert passages[0]["source_tier"] == "official"
    assert passages[0]["evidence_material_type"] == "snippet_only"
    assert passages[0]["snippet_only"] is True
    assert "source_custody_requirement_id" not in passages[0]


def test_policy_enabled_forces_one_allowlisted_official_fetch_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap_policy = _cap_policy(max_fetch_read_operations=1)
    fetch_urls: list[str] = []

    def fake_fetch_page(item_tuple: Any) -> dict[str, Any]:
        _index, item = item_tuple
        fetch_urls.append(item["url"])
        assert item["_source_custody_policy_forced_fetch_read"] is True
        assert item["source_class"] == "primary_source_documents"
        return {
            "title": item["title"],
            "url": item["url"],
            "domain": item["domain"],
            "credibility": item["credibility"],
            "text": _FULL_TEXT,
            "rrf_score": 0.0,
            "_provider": item.get("_provider", ""),
            "source_tier": item["source_tier"],
            "source_class": item["source_class"],
            "currentness_signal": item["currentness_signal"],
            "source_custody_requirement_id": item["source_custody_requirement_id"],
            "required_source_class": item["required_source_class"],
            "required_source_tier": item["required_source_tier"],
            "required_currentness": item["required_currentness"],
            "required_evidence_material_type": item[
                "required_evidence_material_type"
            ],
            "eligible_for_stronger_obligation": item[
                "eligible_for_stronger_obligation"
            ],
            "source_custody_admission_reason": item[
                "source_custody_admission_reason"
            ],
        }

    passages = _run_search(
        monkeypatch,
        source_custody_policy=_custody_policy(),
        cap_policy=cap_policy,
        fetch_page=fake_fetch_page,
    )

    assert fetch_urls == [_DOC_URL]
    assert cap_policy.fetch_read_operations == 1
    assert passages
    passage = passages[0]
    assert passage["evidence_material_type"] == "full_page_fetched"
    assert passage["full_page_fetched"] is True
    assert passage["snippet_only"] is False
    assert passage["source_class"] == "primary_source_documents"
    assert passage["source_custody_requirement_id"] == (
        "ag-src-custody-01:official-doc-full-read"
    )
    assert passage["required_evidence_material_type"] == "full_page_fetched"


def test_policy_enabled_cap_exhaustion_blocks_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap_policy = _cap_policy(max_fetch_read_operations=0)
    fetch_called = False

    def fail_fetch(_item: Any) -> None:
        nonlocal fetch_called
        fetch_called = True
        raise AssertionError("cap exhaustion should block before fetch_page")

    with pytest.raises(RunCapExceeded, match="fetch_read_operations cap exceeded"):
        _run_search(
            monkeypatch,
            source_custody_policy=_custody_policy(),
            cap_policy=cap_policy,
            fetch_page=fail_fetch,
        )

    assert fetch_called is False
    assert cap_policy.fetch_read_operations == 0


def _ledger_projection(*, material_type: str) -> dict[str, Any]:
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        {
            "observation_id": f"ag-src-custody-01:{material_type}",
            "observation_source": "ag_src_custody_01_test",
            "requirements": [
                {
                    "requirement_id": "ag-src-custody-01:official-doc-full-read",
                    "requirement_kind": "canonical",
                    "required_source_class": "primary_source_documents",
                    "required_source_tier": "official",
                    "required_currentness": "current",
                    "required_evidence_material_type": "full_page_fetched",
                }
            ],
            "candidates": [
                {
                    "candidate_id": "candidate:python-docs",
                    "url": _DOC_URL,
                    "title": "math.isclose docs",
                    "domain": "docs.python.org",
                    "source_tier": "official",
                    "source_class": "primary_source_documents",
                    "currentness_signal": "current",
                    "evidence_material_type": material_type,
                    "readable_status": "readable",
                    "fetchable_status": "fetchable",
                    "disposition": "accepted",
                    "record_kind": "fact",
                    "eligible_for_stronger_obligation": True,
                    "final_evidence_eligible": True,
                }
            ],
            "requirement_links": [
                {
                    "requirement_id": "ag-src-custody-01:official-doc-full-read",
                    "candidate_id": "candidate:python-docs",
                    "link_reason": "source_custody_policy_full_fetch_read",
                    "link_status": "accepted",
                }
            ],
        }
    )
    return ledger.to_projection().to_dict()


def _final_evidence(*, material_type: str) -> list[dict[str, Any]]:
    return [
        {
            "source_id": 1,
            "url": _DOC_URL,
            "title": "math.isclose docs",
            "text": f"[{material_type}] body must not serialize",
            "source_tier": "official",
            "source_class": "primary_source_documents",
            "evidence_material_type": material_type,
            "full_page_fetched": material_type == "full_page_fetched",
            "snippet_only": material_type == "snippet_only",
        }
    ]


def test_snippet_only_official_citation_remains_custody_insufficient() -> None:
    packet = build_final_answer_packet(
        run_id="ag-src-custody-snippet",
        final_evidence=_final_evidence(material_type="snippet_only"),
        source_obligation_projection=_ledger_projection(material_type="snippet_only"),
        evidence_sufficient=True,
    )

    assert packet.source_obligations
    assert packet.source_obligations[0].status is (
        SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED
    )
    assert packet.official_current_custody_summary["unsatisfied_source_classes"] == [
        "primary_source_documents"
    ]
    assert "official_current_unsatisfied:primary_source_documents" in (
        packet.mandatory_caveats
    )


def test_fetched_official_source_satisfies_custody_only_after_ledger_admission() -> None:
    without_admission = build_final_answer_packet(
        run_id="ag-src-custody-without-admission",
        final_evidence=_final_evidence(material_type="full_page_fetched"),
        evidence_sufficient=True,
    )
    assert without_admission.source_obligations == ()
    assert without_admission.official_current_custody_summary["available"] is False

    packet = build_final_answer_packet(
        run_id="ag-src-custody-full",
        final_evidence=_final_evidence(material_type="full_page_fetched"),
        source_obligation_projection=_ledger_projection(
            material_type="full_page_fetched"
        ),
        evidence_sufficient=True,
    )

    assert packet.source_obligations
    assert packet.source_obligations[0].status is SourceObligationStatus.SATISFIED
    assert packet.official_current_custody_summary["satisfied_source_classes"] == [
        "primary_source_documents"
    ]
    assert "official_current_unsatisfied:primary_source_documents" not in (
        packet.mandatory_caveats
    )


def test_validation_packet_reports_full_material_and_satisfied_custody() -> None:
    profile = get_validation_profile(AG_LIVE_SOURCE_CUSTODY)
    policy = _cap_policy(max_fetch_read_operations=3)
    policy.fetch_read_operations = 1
    packet_model = build_final_answer_packet(
        run_id="ag-src-custody-validation",
        final_evidence=_final_evidence(material_type="full_page_fetched"),
        source_obligation_projection=_ledger_projection(
            material_type="full_page_fetched"
        ),
        evidence_sufficient=True,
    )
    outcome = SimpleNamespace(
        report=(
            "The defaults are rel_tol=1e-09 and abs_tol=0.0. "
            "[[1]](https://docs.python.org/3/library/math.html#math.isclose)"
        ),
        top_passages=_final_evidence(material_type="full_page_fetched"),
        seen_urls=[_DOC_URL],
        execution_trace={
            "final_answer_source_ids_used": ["1"],
            "final_answer_packet": packet_model.to_dict(),
        },
    )
    context = support.build_preflight_context(
        root=support.Path(__file__).resolve().parents[1],
        profile_name=AG_LIVE_SOURCE_CUSTODY,
        query=support.PRIMARY_QUERY,
        mode=support.REQUIRED_MODE,
        include_domains=[support.REQUIRED_DOMAIN],
        output_path=support.Path(__file__).resolve().parents[1]
        / "output"
        / "ag_src_custody_01_packet.json",
        caps=support.AgLiveBoundCaps(),
        run_id="ag-src-custody-validation",
        confirm_live_product_run=True,
        approved_backup_query=False,
    )
    run_config = RunConfig(
        query=support.PRIMARY_QUERY,
        mode=support.REQUIRED_MODE,
        fast_provider="FixtureFastProvider",
        fast_model="fixture-fast-model",
        smart_provider="FixtureSmartProvider",
        smart_model="fixture-smart-model",
        embed_provider="FixtureEmbedProvider",
        embed_model="fixture-embed-model",
        source_custody_policy=profile.source_custody_policy.to_run_policy(
            include_domains=[support.REQUIRED_DOMAIN]
        ),
    )

    packet = support.build_live_success_packet(
        context,
        outcome=outcome,
        cap_policy=policy,
        run_config=run_config,
    )

    custody = packet["validation_observability"]["source_custody_summary"]
    assert custody["source_custody_expected"] is True
    assert custody["fetch_read_operations"] == 1
    assert custody["source_custody_satisfied"] is True
    assert custody["source_custody_diagnosis"] is None
    assert packet["source_custody_policy_requested"]["surface"] == (
        "RunConfig.source_custody_policy"
    )
    assert packet["validation_observability"]["source_material_summary"][
        "evidence_material_type_by_cited_url"
    ] == {_DOC_URL: "full_page_fetched"}

    rendered = json.dumps(packet, sort_keys=True)
    assert "body must not serialize" not in rendered
    assert '"raw_prompt":' not in rendered
    assert '"provider_payload":' not in rendered
    assert '"execution_trace":' not in rendered
    support.reject_forbidden_packet(packet)
