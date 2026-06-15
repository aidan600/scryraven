from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.evidence_ledger import EvidenceLedger, SourceRequirementStatus
from core.evidence_ledger_lifecycle import (
    reduce_provider_job_evidence_into_evidence_ledger,
)
from core.provider_job_evidence_ledger_bridge import (
    PROVIDER_JOB_EVIDENCE_LEDGER_BRIDGE_TRACE_KEY,
    build_provider_job_evidence_ledger_observation,
)
from core.run_kernel import EVIDENCE_LEDGER_STAGE, RunKernel

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "core" / "provider_job_evidence_ledger_bridge.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


def _search_work_projection() -> dict[str, Any]:
    return {
        "trace_key": "query_plan_work_shadow_projection",
        "components": [
            {"component_id": "component-fee"},
            {"component_id": "component-legal"},
            {"component_id": "component-api"},
            {"component_id": "component-numeric"},
        ],
        "source_obligations_by_component": {
            "component-fee": [
                {
                    "obligation_id": "obligation-official-fee",
                    "kind": "official_current",
                    "strictness": "required",
                    "required_source_class": "official_current_rules",
                    "required_currentness": "current",
                }
            ],
            "component-legal": [
                {
                    "obligation_id": "obligation-legal-deadline",
                    "kind": "legal_current_primary",
                    "strictness": "required",
                    "required_source_class": "legal_or_regulatory_text",
                    "required_currentness": "current",
                }
            ],
            "component-api": [
                {
                    "obligation_id": "obligation-api-docs",
                    "kind": "canonical_documentation",
                    "strictness": "required",
                    "required_source_class": "primary_source_documents",
                }
            ],
            "component-numeric": [
                {
                    "obligation_id": "obligation-source-bound-numeric",
                    "kind": "source_bound_numeric",
                    "strictness": "required",
                    "required_source_class": "sourced_numeric_values",
                }
            ],
        },
        "provider_jobs_by_component": {
            "component-fee": [
                {
                    "work_id": "provider-official-fee",
                    "work_kind": "official_candidate_acquisition",
                    "source_obligation_ids": ["obligation-official-fee"],
                    "executes_runtime_work": False,
                }
            ],
            "component-legal": [
                {
                    "work_id": "provider-legal-currentness",
                    "work_kind": "conflict_currentness_check",
                    "source_obligation_ids": ["obligation-legal-deadline"],
                    "executes_runtime_work": False,
                }
            ],
            "component-api": [
                {
                    "work_id": "provider-api-canonical",
                    "work_kind": "canonical_extraction",
                    "source_obligation_ids": ["obligation-api-docs"],
                    "executes_runtime_work": False,
                }
            ],
            "component-numeric": [
                {
                    "work_id": "provider-numeric-extract",
                    "work_kind": "fetch_read_extract",
                    "source_obligation_ids": ["obligation-source-bound-numeric"],
                    "executes_runtime_work": False,
                }
            ],
        },
    }


def _execution_record(
    *,
    execution_id: str,
    component_id: str,
    provider_job_id: str,
    provider_job_kind: str,
    obligation_id: str,
    query: str,
    status: str = "admitted",
) -> dict[str, Any]:
    return {
        "execution_id": execution_id,
        "component_id": component_id,
        "provider_job_id": provider_job_id,
        "provider_job_kind": provider_job_kind,
        "source_obligation_ids": [obligation_id],
        "query_plan_item_ids": [f"query-plan-item-{provider_job_id}"],
        "authorized_queries": [query] if status == "admitted" else [],
        "execution_status": status,
        "execution_owner": "existing_retrieval_loop",
        "handoff_to_existing_retrieval_loop": status == "admitted",
        "source_obligations_satisfied": False,
        "official_current_custody_satisfied": False,
        "quant_extraction_executed": False,
        "calculation_executed": False,
        "evidence_refs": [],
    }


def _handoff(records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    active_records = records or [
        _execution_record(
            execution_id="provider-job-execution:1",
            component_id="component-fee",
            provider_job_id="provider-official-fee",
            provider_job_kind="official_candidate_acquisition",
            obligation_id="obligation-official-fee",
            query="official current filing fee",
        )
    ]
    return {
        "schema_version": "search_work_provider_job_execution_ag96f1_v1",
        "trace_key": "search_work_provider_job_execution_handoff",
        "provider_job_execution_record_count": len(active_records),
        "provider_job_execution_records": active_records,
        "behavior_boundary_flags": {
            "query_text_generated": False,
            "provider_search_behavior_changed": False,
            "retrieval_behavior_changed": False,
            "prompt_behavior_changed": False,
            "citation_behavior_changed": False,
            "final_answer_behavior_changed": False,
            "source_obligations_satisfied": False,
        },
    }


def _query_plan_trace() -> dict[str, Any]:
    return {
        "items": [
            {
                "item_id": "query-plan-item-provider-official-fee",
                "authorized_query": "official current filing fee",
                "status": "finalized",
                "metadata": {
                    "search_work_component_id": "component-fee",
                    "provider_job_candidate_ids": ["provider-official-fee"],
                    "source_obligation_candidate_ids": [
                        "obligation-official-fee"
                    ],
                },
            }
        ]
    }


def _projection_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    ledger = EvidenceLedger()
    ledger.reduce_observation(payload)
    return ledger.to_projection().to_dict()


def _requirement(projection: dict[str, Any], fragment: str) -> dict[str, Any]:
    for requirement in projection["source_requirements"]:
        if fragment in requirement["requirement_id"]:
            return requirement
    raise AssertionError(f"missing requirement containing {fragment}")


def test_no_provider_job_handoff_returns_noop_projection() -> None:
    result = build_provider_job_evidence_ledger_observation(
        observation_id="obs-none",
        provider_job_execution_handoff=None,
        query_plan_trace={},
        current_authorized_queries=["ordinary query"],
        retrieval_records=[],
        search_work_projection=_search_work_projection(),
    )

    assert result.observation_payload == {}
    projection = result.projection
    assert projection["trace_key"] == PROVIDER_JOB_EVIDENCE_LEDGER_BRIDGE_TRACE_KEY
    assert projection["provider_job_evidence_ledger_bridge_ran"] is False
    assert projection["evidence_ledger_observation_created"] is False
    assert projection["final_answer_behavior_changed"] is False


def test_handoff_without_retrieval_candidates_records_requirements_and_gaps() -> None:
    result = build_provider_job_evidence_ledger_observation(
        observation_id="obs-no-candidates",
        provider_job_execution_handoff=_handoff(),
        query_plan_trace=_query_plan_trace(),
        current_authorized_queries=["official current filing fee"],
        retrieval_records=[],
        search_work_projection=_search_work_projection(),
    )

    payload = result.observation_payload
    assert len(payload["requirements"]) == 1
    assert payload["candidates"] == []
    assert payload["requirement_links"] == []
    assert payload["custody_gaps"][0]["gap_type"] == "missing_candidate_identity"
    assert result.projection["custody_gap_count"] == 1


def test_matching_retrieved_source_becomes_sanitized_candidate_and_link() -> None:
    result = build_provider_job_evidence_ledger_observation(
        observation_id="obs-official",
        provider_job_execution_handoff=_handoff(),
        query_plan_trace=_query_plan_trace(),
        current_authorized_queries=["official current filing fee"],
        retrieval_records=[
            {
                "url": "https://www.irs.gov/current-rule",
                "title": "Current official rule",
                "domain": "irs.gov",
                "query_ref": "official current filing fee",
                "provider_name": "offline_fixture",
                "retrieval_pass_id": "retrieval-pass-1",
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
                "readable_status": "readable",
                "fetchable_status": "fetchable",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
            }
        ],
        search_work_projection=_search_work_projection(),
    )

    payload = result.observation_payload
    candidate = payload["candidates"][0]
    assert candidate["url"] == "https://www.irs.gov/current-rule"
    assert candidate["title"] == "Current official rule"
    assert candidate["domain"] == "irs.gov"
    assert candidate["query_ref"] == "official current filing fee"
    assert candidate["provider_name"] == "offline_fixture"
    assert candidate["retrieval_pass_id"] == "retrieval-pass-1"
    assert payload["requirements"][0]["component_id"] == "component_fee"
    assert payload["requirements"][0]["source_obligation_id"] == (
        "obligation_official_fee"
    )
    assert payload["requirements"][0]["provider_job_id"] == (
        "provider_official_fee"
    )
    assert payload["requirement_links"][0]["candidate_id"] == candidate["candidate_id"]

    projection = _projection_from_payload(dict(payload))
    requirement = _requirement(projection, "obligation_official_fee")
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value


def test_official_current_aggregate_only_and_lower_tier_do_not_satisfy() -> None:
    aggregate = build_provider_job_evidence_ledger_observation(
        observation_id="obs-aggregate",
        provider_job_execution_handoff=_handoff(),
        query_plan_trace=_query_plan_trace(),
        current_authorized_queries=["official current filing fee"],
        retrieval_records={"source_tier_counts": {"official": 3}},
        search_work_projection=_search_work_projection(),
    )
    aggregate_projection = _projection_from_payload(dict(aggregate.observation_payload))
    aggregate_req = _requirement(aggregate_projection, "obligation_official_fee")
    assert aggregate_req["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert aggregate_req["aggregate_counts_insufficient"] is True

    lower_tier = build_provider_job_evidence_ledger_observation(
        observation_id="obs-lower-tier",
        provider_job_execution_handoff=_handoff(),
        query_plan_trace=_query_plan_trace(),
        current_authorized_queries=["official current filing fee"],
        retrieval_records=[
            {
                "url": "https://example.com/context",
                "title": "Context source",
                "query_ref": "official current filing fee",
                "source_tier": "secondary",
                "source_class": "reputable_secondary",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
            }
        ],
        search_work_projection=_search_work_projection(),
    )
    lower_projection = _projection_from_payload(dict(lower_tier.observation_payload))
    lower_req = _requirement(lower_projection, "obligation_official_fee")
    assert lower_req["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert lower_req["linked_candidate_ids"] == []


def test_legal_canonical_and_source_bound_numeric_records_are_conservative() -> None:
    records = [
        _execution_record(
            execution_id="provider-job-execution:legal",
            component_id="component-legal",
            provider_job_id="provider-legal-currentness",
            provider_job_kind="conflict_currentness_check",
            obligation_id="obligation-legal-deadline",
            query="legal deadline appeal rule",
        ),
        _execution_record(
            execution_id="provider-job-execution:api",
            component_id="component-api",
            provider_job_id="provider-api-canonical",
            provider_job_kind="canonical_extraction",
            obligation_id="obligation-api-docs",
            query="API parameter documentation",
        ),
        _execution_record(
            execution_id="provider-job-execution:numeric",
            component_id="component-numeric",
            provider_job_id="provider-numeric-extract",
            provider_job_kind="fetch_read_extract",
            obligation_id="obligation-source-bound-numeric",
            query="numeric rate amount source",
        ),
    ]
    result = build_provider_job_evidence_ledger_observation(
        observation_id="obs-mixed",
        provider_job_execution_handoff=_handoff(records),
        query_plan_trace={"items": []},
        current_authorized_queries=[
            "legal deadline appeal rule",
            "API parameter documentation",
            "numeric rate amount source",
        ],
        retrieval_records=[
            {
                "url": "https://www.law.gov/rule",
                "title": "Current legal rule",
                "query_ref": "legal deadline appeal rule",
                "source_tier": "official",
                "source_class": "legal_or_regulatory_text",
                "currentness_signal": "current",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
            },
            {
                "url": "https://docs.example.com/api",
                "title": "Canonical API docs",
                "query_ref": "API parameter documentation",
                "source_tier": "canonical",
                "source_class": "primary_source_documents",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
            },
            {
                "url": "https://stats.example.gov/rate",
                "title": "Numeric rate source",
                "query_ref": "numeric rate amount source",
                "source_tier": "official",
                "source_class": "sourced_numeric_values",
                "disposition": "observed",
            },
        ],
        search_work_projection=_search_work_projection(),
    )

    payload = result.observation_payload
    requirements = {
        item["source_obligation_id"]: item for item in payload["requirements"]
    }
    assert requirements["obligation_legal_deadline"]["required_source_class"] == (
        "legal_or_regulatory_text"
    )
    assert requirements["obligation_api_docs"]["required_source_class"] == (
        "primary_source_documents"
    )
    assert requirements["obligation_source_bound_numeric"]["required_source_class"] == (
        "sourced_numeric_values"
    )
    assert len(payload["requirement_links"]) == 3
    projection = result.projection
    flags = projection["behavior_boundary_flags"]
    assert flags["quant_extraction_executed"] is False
    assert flags["calculation_executed"] is False
    assert flags["source_obligation_satisfaction_claimed_by_bridge"] is False

    ledger_projection = _projection_from_payload(dict(payload))
    numeric_req = _requirement(ledger_projection, "obligation_source_bound_numeric")
    assert numeric_req["status"] == SourceRequirementStatus.UNSATISFIED.value


def test_bridge_reduces_through_runkernel_evidence_ledger_path() -> None:
    kernel = RunKernel.start(run_id="ag96g1", request_id="request")
    reduced = reduce_provider_job_evidence_into_evidence_ledger(
        run_kernel=kernel,
        run_id="ag96g1",
        provider_job_execution_handoff=_handoff(),
        query_plan_trace=_query_plan_trace(),
        current_authorized_queries=["official current filing fee"],
        retrieval_records=[
            {
                "url": "https://www.irs.gov/current-rule",
                "title": "Current official rule",
                "query_ref": "official current filing fee",
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
            }
        ],
        search_work_projection=_search_work_projection(),
    )

    projection = reduced["evidence_ledger_projection"]
    assert projection["owner"] == "RunKernel.EvidenceLedger"
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE] == projection
    bridge_projection = reduced["provider_job_evidence_ledger_bridge_projection"]
    assert bridge_projection["provider_job_evidence_ledger_bridge_ran"] is True
    assert bridge_projection["evidence_ledger_observation_created"] is True


def test_redaction_removes_raw_private_fields() -> None:
    result = build_provider_job_evidence_ledger_observation(
        observation_id="obs-redaction",
        provider_job_execution_handoff={
            **_handoff(),
            "raw_prompt": "RAW_PROMPT_SENTINEL",
            "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
            "raw_model_response": "RAW_MODEL_SENTINEL",
            "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
            "token": "TOKEN_SENTINEL",
            "db_row": "DB_ROW_SENTINEL",
            "full_trace": "FULL_TRACE_SENTINEL",
        },
        query_plan_trace={
            **_query_plan_trace(),
            "raw_model_response": "QUERY_PLAN_RAW_MODEL_SENTINEL",
        },
        current_authorized_queries=["official current filing fee"],
        retrieval_records=[
            {
                "url": "https://www.irs.gov/current-rule",
                "title": "Current official rule",
                "query_ref": "official current filing fee",
                "source_tier": "official",
                "source_class": "official_current_rules",
                "raw_text": "RAW_TEXT_SENTINEL",
                "full_text": "FULL_TEXT_SENTINEL",
                "snippets": ["SNIPPET_SENTINEL"],
            }
        ],
        search_work_projection=_search_work_projection(),
    )

    encoded = json.dumps(result.to_dict(), sort_keys=True)
    for sentinel in (
        "RAW_PROMPT_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "RAW_MODEL_SENTINEL",
        "SECRET_SENTINEL",
        "TOKEN_SENTINEL",
        "DB_ROW_SENTINEL",
        "FULL_TRACE_SENTINEL",
        "QUERY_PLAN_RAW_MODEL_SENTINEL",
        "RAW_TEXT_SENTINEL",
        "FULL_TEXT_SENTINEL",
        "SNIPPET_SENTINEL",
    ):
        assert sentinel not in encoded


def test_static_guards_preserve_closed_surface_boundary() -> None:
    helper_imports = _imports(BRIDGE)
    forbidden_helper_imports = {
        "core.search_providers",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.prompts",
        "core.runtime_prompt_assembly",
        "core.final_answer_packet",
        "core.final_answer_runtime_assembly",
        "core.author_execution_runtime",
        "core.pipeline_orchestrator",
        "core.query_production_runtime",
    }
    assert helper_imports.isdisjoint(forbidden_helper_imports)
    helper_source = BRIDGE.read_text(encoding="utf-8")
    for token in (
        "ask_model",
        "brave_reconnaissance",
        "search_web_results",
        "search_exa_results",
        "search_linkup_results",
        "fetch_page",
        "process_search_queries",
        "format_citation",
        "FinalAnswerPacket",
        "AuthorExecutor",
    ):
        assert token not in helper_source

    forbidden_imports = {
        "core.provider_job_evidence_ledger_bridge",
        "provider_job_evidence_ledger_bridge",
    }
    for path in (
        ROOT / "core" / "search_providers.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "retrieval_scheduler.py",
        ROOT / "core" / "prompts.py",
        ROOT / "core" / "runtime_prompt_assembly.py",
        ROOT / "core" / "final_answer_packet.py",
        ROOT / "core" / "final_answer_runtime_assembly.py",
        ROOT / "core" / "author_execution_runtime.py",
    ):
        assert _imports(path).isdisjoint(forbidden_imports), path

    pipeline_source = PIPELINE.read_text(encoding="utf-8")
    assert "EvidenceCandidate(" not in pipeline_source
    assert "SourceRequirementRecord(" not in pipeline_source
    assert "provider_jobs_by_component" not in pipeline_source
    assert "source_obligations_by_component" not in pipeline_source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
