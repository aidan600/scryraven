from __future__ import annotations

import inspect
import json
from types import SimpleNamespace
from typing import Any

import pytest

import core.pipeline as pipeline
import core.retrieval as retrieval
from core.cap_enforcement import RunCapPolicy
from core.evidence_ledger import EvidenceLedger
from core.final_answer_packet import SourceObligationStatus
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.run_authority_contract_templates import (
    CANONICAL_TECHNICAL_DOCS,
    build_deterministic_contract,
)
from core.run_config import RunConfig
from core.validation_profiles import AG_LIVE_SOURCE_CUSTODY
from scripts import ag_live_bound_01_support as support

_DOC_URL = "https://docs.python.org/3/library/math.html#math.isclose"
_OFF_POLICY_OFFICIAL_URL = "https://official.example.org/current-rules"
_CANONICAL_DOCS_REQUIREMENT_ID = "run_contract:canonical_docs"
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


def _official_search_result() -> dict[str, Any]:
    return {
        "title": "math.isclose docs",
        "url": _DOC_URL,
        "domain": "docs.python.org",
        "credibility": 1,
        "snippet": _SNIPPET,
    }


def _off_policy_official_search_result() -> dict[str, Any]:
    return {
        "title": "Current official rules",
        "url": _OFF_POLICY_OFFICIAL_URL,
        "domain": "official.example.org",
        "credibility": 1,
        "snippet": "Official current rules say the answer is stable. " * 8,
        "raw_content": "Official current rules say the answer is stable. " * 8,
        "source_tier": "official",
    }


def _run_search(
    monkeypatch: pytest.MonkeyPatch,
    *,
    complexity: str = "medium",
    search_results: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    search_calls: list[str] = []
    selected_results = search_results or [_official_search_result()]

    def fake_search_web_results(query: str, **_kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        search_calls.append(query)
        return selected_results, []

    monkeypatch.setattr(pipeline, "search_web_results", fake_search_web_results)

    passages = pipeline.process_search_queries(
        ["python math isclose docs"],
        "general",
        complexity,
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
    )
    assert search_calls == ["python math isclose docs"]
    return passages


def test_discovery_preserves_provider_snippet_without_source_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    passages = _run_search(monkeypatch)

    assert passages
    assert passages[0]["url"] == _DOC_URL
    assert passages[0]["source_tier"] == "official"
    assert passages[0]["evidence_material_type"] == "snippet_only"
    assert passages[0]["discovery_material_type"] == "provider_returned_snippet"
    assert passages[0]["snippet_only"] is True
    assert passages[0]["full_page_fetched"] is False
    assert passages[0]["product_fetch_read_executed"] is False
    assert passages[0]["separate_exact_url_transport_performed"] is False
    assert passages[0]["provider_internal_acquisition_unobserved"] is True
    assert "source_custody_requirement_id" not in passages[0]


def test_deep_discovery_uses_provider_excerpt_without_full_page_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _official_search_result()
    result.update({"credibility": 5, "raw_content": _FULL_TEXT})
    passages = _run_search(
        monkeypatch,
        complexity="high",
        search_results=[result],
    )

    assert passages
    passage = passages[0]
    assert passage["evidence_material_type"] == "snippet_only"
    assert passage["discovery_material_type"] == "provider_returned_excerpt"
    assert passage["provider_returned"] is True
    assert passage["full_page_fetched"] is False
    assert passage["snippet_only"] is True
    assert passage["separate_exact_url_transport_performed"] is False
    assert "[FULL_PAGE]" not in passage["text"]


def test_domain_targeting_does_not_create_preselection_fetch_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap_policy = _cap_policy(max_fetch_read_operations=1)
    original_classify_source = pipeline.classify_source

    def fake_classify_source(url: str, *args: Any, **kwargs: Any) -> str:
        if url == _OFF_POLICY_OFFICIAL_URL:
            return "official"
        return original_classify_source(url, *args, **kwargs)

    monkeypatch.setattr(pipeline, "classify_source", fake_classify_source)

    passages = _run_search(
        monkeypatch,
        complexity="high",
        search_results=[_off_policy_official_search_result()],
    )

    assert cap_policy.fetch_read_operations == 0
    assert passages
    passage = passages[0]
    assert passage["url"] == _OFF_POLICY_OFFICIAL_URL
    assert passage["source_tier"] == "official"
    assert passage["evidence_material_type"] == "snippet_only"
    assert passage["discovery_material_type"] == "provider_returned_excerpt"
    assert passage["snippet_only"] is True
    assert passage["full_page_fetched"] is False
    assert passage["separate_exact_url_transport_performed"] is False
    assert "_source_custody_policy_forced_fetch_read" not in passage
    assert "source_custody_requirement_id" not in passage
    assert "eligible_for_stronger_obligation" not in passage
    assert passage.get("required_evidence_material_type") != "full_page_fetched"


def test_historical_discovery_fetch_policy_and_helpers_are_retired() -> None:
    cap_policy = _cap_policy(max_fetch_read_operations=0)

    parameters = inspect.signature(pipeline.process_search_queries).parameters
    assert "source_custody_policy" not in parameters
    assert "cap_policy" not in parameters
    assert not hasattr(pipeline, "fetch_page")
    assert not hasattr(retrieval, "fetch_page")
    assert not hasattr(retrieval, "fetch_url_text")
    assert not hasattr(RunConfig(query="offline"), "source_custody_policy")
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


def _canonical_docs_contract_projection() -> dict[str, Any]:
    return build_deterministic_contract(
        query=support.PRIMARY_QUERY,
        mode=support.REQUIRED_MODE,
        selected_template_ids=(CANONICAL_TECHNICAL_DOCS,),
    ).to_projection()


def _canonical_docs_ledger_projection(
    *,
    material_type: str = "full_page_fetched",
    candidate_source_tier: str = "official",
    candidate_source_class: str = "primary_source_documents",
    requirement_id: str = _CANONICAL_DOCS_REQUIREMENT_ID,
    requirement_kind: str = "canonical",
    required_source_class: str = "primary_source_documents",
    required_source_tier: str = "canonical",
) -> dict[str, Any]:
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        {
            "observation_id": (
                f"ag-src-custody-02b:{requirement_id}:{material_type}:"
                f"{candidate_source_tier}:{candidate_source_class}"
            ),
            "observation_source": "ag_src_custody_02b_test",
            "requirements": [
                {
                    "requirement_id": requirement_id,
                    "requirement_kind": requirement_kind,
                    "required_source_class": required_source_class,
                    "required_source_tier": required_source_tier,
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
                    "source_tier": candidate_source_tier,
                    "source_class": candidate_source_class,
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
        }
    )
    return ledger.to_projection().to_dict()


def _source_requirement_status(
    projection: dict[str, Any],
    requirement_id: str,
) -> str:
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] == requirement_id:
            return requirement["status"]
    raise AssertionError(f"missing source requirement {requirement_id}")


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


@pytest.mark.parametrize("candidate_source_tier", ["official", "primary"])
def test_official_project_docs_satisfy_canonical_docs_run_contract_after_full_fetch(
    candidate_source_tier: str,
) -> None:
    projection = _canonical_docs_ledger_projection(
        candidate_source_tier=candidate_source_tier,
    )

    assert _source_requirement_status(projection, _CANONICAL_DOCS_REQUIREMENT_ID) == (
        "satisfied"
    )

    packet = build_final_answer_packet(
        run_id=f"ag-src-custody-02b-{candidate_source_tier}",
        final_evidence=_final_evidence(material_type="full_page_fetched"),
        source_obligation_projection=projection,
        run_contract_projection=_canonical_docs_contract_projection(),
        evidence_sufficient=True,
    )

    assert packet.source_obligations
    assert all(
        obligation.status is SourceObligationStatus.SATISFIED
        for obligation in packet.source_obligations
    )
    assert "missing_canonical_docs_must_be_caveated" not in packet.mandatory_caveats
    assert "source_obligations_missing_or_unsatisfied" not in packet.readiness_reasons


def test_snippet_only_official_docs_do_not_satisfy_canonical_docs_requirement() -> None:
    projection = _canonical_docs_ledger_projection(material_type="snippet_only")

    assert _source_requirement_status(projection, _CANONICAL_DOCS_REQUIREMENT_ID) == (
        "unsatisfied"
    )

    packet = build_final_answer_packet(
        run_id="ag-src-custody-02b-snippet",
        final_evidence=_final_evidence(material_type="snippet_only"),
        source_obligation_projection=projection,
        run_contract_projection=_canonical_docs_contract_projection(),
        evidence_sufficient=True,
    )

    assert any(
        obligation.status is not SourceObligationStatus.SATISFIED
        for obligation in packet.source_obligations
    )
    assert "missing_canonical_docs_must_be_caveated" in packet.mandatory_caveats


def test_official_tier_source_class_mismatch_does_not_satisfy_canonical_docs() -> None:
    projection = _canonical_docs_ledger_projection(
        candidate_source_class="official_current_rules",
    )

    assert _source_requirement_status(projection, _CANONICAL_DOCS_REQUIREMENT_ID) == (
        "unsatisfied"
    )


def test_official_tier_does_not_satisfy_non_canonical_docs_canonical_requirement() -> None:
    projection = _canonical_docs_ledger_projection(
        requirement_id="run_contract:non_canonical_primary_requirement",
        requirement_kind="canonical",
    )

    assert _source_requirement_status(
        projection,
        "run_contract:non_canonical_primary_requirement",
    ) == "unsatisfied"


def test_exact_canonical_tier_still_satisfies_canonical_docs_requirement() -> None:
    projection = _canonical_docs_ledger_projection(candidate_source_tier="canonical")

    assert _source_requirement_status(projection, _CANONICAL_DOCS_REQUIREMENT_ID) == (
        "satisfied"
    )


def test_canonical_docs_contract_without_ledger_admission_keeps_caveat() -> None:
    packet = build_final_answer_packet(
        run_id="ag-src-custody-02b-without-ledger",
        final_evidence=_final_evidence(material_type="full_page_fetched"),
        run_contract_projection=_canonical_docs_contract_projection(),
        evidence_sufficient=True,
    )

    assert any(
        obligation.status is not SourceObligationStatus.SATISFIED
        for obligation in packet.source_obligations
    )
    assert "missing_canonical_docs_must_be_caveated" in packet.mandatory_caveats


def test_retained_historical_packet_reports_full_material_and_satisfied_custody() -> None:
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
    context = support.PreflightContext(
        root=support.Path(__file__).resolve().parents[1],
        profile_name=AG_LIVE_SOURCE_CUSTODY,
        query=support.PRIMARY_QUERY,
        query_lock="historical_non_executable_fixture",
        mode=support.REQUIRED_MODE,
        include_domains=[support.REQUIRED_DOMAIN],
        output_path=support.Path(__file__).resolve().parents[1]
        / "output"
        / "ag_src_custody_01_packet.json",
        caps=support.AgLiveBoundCaps(),
        run_id="ag-src-custody-validation",
        confirm_live_product_run=True,
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
        "ValidationProfile.source_custody_policy_non_executable_expectation"
    )
    assert not hasattr(run_config, "source_custody_policy")
    product_path = packet["source_custody_policy_product_path"]
    assert product_path["policy_enabled"] is False
    assert product_path["product_policy_constructible"] is False
    assert packet["validation_observability"]["source_material_summary"][
        "evidence_material_type_by_cited_url"
    ] == {_DOC_URL: "full_page_fetched"}

    rendered = json.dumps(packet, sort_keys=True)
    assert "body must not serialize" not in rendered
    assert '"raw_prompt":' not in rendered
    assert '"provider_payload":' not in rendered
    assert '"execution_trace":' not in rendered
    support.reject_forbidden_packet(packet)
