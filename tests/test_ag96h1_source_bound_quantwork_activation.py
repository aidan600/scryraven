from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

from core.final_answer_packet import FinalAnswerReadinessStatus
from core.run_authority_sufficiency import RunSufficiencyDecision
from tests.test_ag96g3_g4_final_answer_closure_e2e import (
    QUERY_BY_COMPONENT,
    REQS,
    _candidate,
    _contract,
    _payload_authority,
    _search_work_for_components,
    _spine,
)

ROOT = Path(__file__).resolve().parents[1]


def _numeric_record(
    *,
    source_id: int = 801,
    candidate_id: str = "candidate-numeric-a",
    numeric_facts: Any,
    source_class: str = "sourced_numeric_values",
    source_tier: str = "official",
    query: str | None = None,
) -> dict[str, Any]:
    return {
        **_candidate(
            query=query or QUERY_BY_COMPONENT["component-numeric"],
            source_class=source_class,
            source_tier=source_tier,
            url=f"https://stats.example.gov/source-{source_id}",
            title=f"Numeric source {source_id}",
            source_id=source_id,
            eligible=source_tier in {"official", "primary", "canonical"},
        ),
        "candidate_id": candidate_id,
        "numeric_facts": numeric_facts,
    }


def _quant_unit(
    *,
    required_variables: tuple[str, ...],
    calculation_kind: str,
    units: Mapping[str, str] | None = None,
    high_stakes: bool = False,
) -> dict[str, Any]:
    return {
        "quant_unit_id": "quant-unit-numeric",
        "component_ids": ["component-numeric"],
        "target_metric": calculation_kind,
        "required_variables": list(required_variables),
        "source_bound_values_needed": list(required_variables),
        "allowed_calculations": [calculation_kind],
        "high_stakes_quant": high_stakes,
        "direct_use_eligible": True,
        "metadata": {
            "source_obligation_ids": ["obligation-source-bound-numeric"],
            "variable_units": dict(units or {}),
        },
    }


def _numeric_spine(
    *,
    records: Any,
    quant_units: list[Mapping[str, Any]],
    contract: Mapping[str, Any] | None = None,
    final_evidence_records: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return _spine(
        contract or _contract(REQS["numeric"]),
        candidate_queries=[QUERY_BY_COMPONENT["component-numeric"]],
        retrieval_records=records,
        final_evidence_records=final_evidence_records,
        search_work_projection=_search_work_for_components("component-numeric"),
        quant_work_units=quant_units,
    )


def test_direct_source_bound_numeric_value_extracts_and_clears_unknown() -> None:
    record = _numeric_record(
        numeric_facts=[
            {"variable": "taxable_wage_base", "value": 176100, "unit": "USD"}
        ],
    )
    result = _numeric_spine(
        records=[record],
        quant_units=[
            _quant_unit(
                required_variables=("taxable_wage_base",),
                calculation_kind="identity",
                units={"taxable_wage_base": "USD"},
            )
        ],
    )
    authority = _payload_authority(result)

    assert result["quant_packets"][0]["extraction_status"] == "succeeded"
    assert result["quant_packets"][0]["calculation_status"] == "succeeded"
    assert result["judgment"].decision is RunSufficiencyDecision.READY_DIRECT
    assert result["judgment"].source_bound_numeric_unknowns == ()
    assert authority["source_bound_numeric_resolutions"][0]["calculation_result"][
        "value"
    ] == 176100
    assert authority["source_bound_numeric_unknowns"] == []
    assert authority["behavior_boundary_flags"]["quant_extraction_executed"] is True
    assert authority["behavior_boundary_flags"]["calculation_executed"] is True
    assert authority["behavior_boundary_flags"]["arbitrary_code_execution_used"] is False
    assert authority["citation_eligible_source_ids"] == [801]


def test_whitelisted_ratio_difference_and_percent_change_succeed() -> None:
    record = _numeric_record(
        numeric_facts=[
            {"variable": "old_value", "value": 100, "unit": "USD"},
            {"variable": "new_value", "value": 125, "unit": "USD"},
        ],
    )

    cases = {
        "ratio": 0.8,
        "difference": -25,
        "percent_change": 25,
    }
    for calculation, expected in cases.items():
        result = _numeric_spine(
            records=[record],
            quant_units=[
                _quant_unit(
                    required_variables=("old_value", "new_value"),
                    calculation_kind=calculation,
                    units={"old_value": "USD", "new_value": "USD"},
                )
            ],
        )
        assert result["quant_packets"][0]["calculation_status"] == "succeeded"
        assert result["quant_packets"][0]["calculation_result"]["value"] == expected
        assert result["judgment"].source_bound_numeric_unknowns == ()


def test_final_evidence_only_numeric_value_does_not_satisfy_without_ledger_custody() -> None:
    final_only = _numeric_record(
        source_id=802,
        candidate_id="candidate-final-only",
        numeric_facts=[{"variable": "rate", "value": 9.5, "unit": "percent"}],
    )
    result = _numeric_spine(
        records=[],
        final_evidence_records=[final_only],
        quant_units=[
            _quant_unit(
                required_variables=("rate",),
                calculation_kind="identity",
                units={"rate": "percent"},
            )
        ],
    )

    assert result["quant_packets"][0]["extraction_status"] == "unresolved"
    assert result["judgment"].decision is RunSufficiencyDecision.SOURCE_BOUND_NUMERIC_UNKNOWN
    assert _payload_authority(result)["source_bound_numeric_unknowns"]


def test_aggregate_only_numeric_source_counts_do_not_satisfy() -> None:
    result = _numeric_spine(
        records={"source_tier_counts": {"official": 3}},
        quant_units=[
            _quant_unit(
                required_variables=("rate",),
                calculation_kind="identity",
                units={"rate": "percent"},
            )
        ],
    )

    assert result["ledger"]["candidate_count"] == 0
    assert result["quant_packets"][0]["calculation_status"] != "succeeded"
    assert result["judgment"].source_bound_numeric_unknowns


def test_lower_tier_context_numeric_value_cannot_satisfy_strict_requirement() -> None:
    record = _numeric_record(
        source_id=803,
        candidate_id="candidate-context",
        numeric_facts=[{"variable": "rate", "value": 9.5, "unit": "percent"}],
        source_class="reputable_secondary",
        source_tier="secondary",
    )
    result = _numeric_spine(
        records=[record],
        quant_units=[
            _quant_unit(
                required_variables=("rate",),
                calculation_kind="identity",
                units={"rate": "percent"},
            )
        ],
    )

    assert result["quant_packets"][0]["extraction_status"] == "unresolved"
    assert result["judgment"].source_bound_numeric_unknowns
    assert _payload_authority(result)["citation_eligible_source_ids"] == []


def test_missing_variable_and_ambiguous_values_keep_unknown_posture() -> None:
    missing = _numeric_spine(
        records=[
            _numeric_record(
                numeric_facts=[{"variable": "old_value", "value": 10, "unit": "USD"}]
            )
        ],
        quant_units=[
            _quant_unit(
                required_variables=("old_value", "new_value"),
                calculation_kind="difference",
                units={"old_value": "USD", "new_value": "USD"},
            )
        ],
    )
    ambiguous = _numeric_spine(
        records=[
            _numeric_record(
                source_id=804,
                candidate_id="candidate-rate-a",
                numeric_facts=[{"variable": "rate", "value": 9.5, "unit": "percent"}],
            ),
            _numeric_record(
                source_id=805,
                candidate_id="candidate-rate-b",
                numeric_facts=[{"variable": "rate", "value": 10.0, "unit": "percent"}],
            ),
        ],
        quant_units=[
            _quant_unit(
                required_variables=("rate",),
                calculation_kind="identity",
                units={"rate": "percent"},
            )
        ],
    )

    assert missing["quant_packets"][0]["unresolved_values"][0]["variable"] == "new_value"
    assert missing["judgment"].source_bound_numeric_unknowns
    assert ambiguous["quant_packets"][0]["extraction_status"] == "conflict"
    assert "ambiguous_or_conflicting_numeric_values" in ambiguous["quant_packets"][0][
        "blocked_reasons"
    ]
    assert ambiguous["judgment"].source_bound_numeric_unknowns


def test_unit_mismatch_and_non_whitelisted_calculation_block_execution() -> None:
    mismatch = _numeric_spine(
        records=[
            _numeric_record(
                numeric_facts=[
                    {"variable": "old_value", "value": 100, "unit": "USD"},
                    {"variable": "new_value", "value": 125, "unit": "percent"},
                ]
            )
        ],
        quant_units=[
            _quant_unit(
                required_variables=("old_value", "new_value"),
                calculation_kind="difference",
                units={"old_value": "USD", "new_value": "USD"},
            )
        ],
    )
    blocked = _numeric_spine(
        records=[
            _numeric_record(
                numeric_facts=[
                    {"variable": "old_value", "value": 100, "unit": "USD"},
                    {"variable": "new_value", "value": 125, "unit": "USD"},
                ]
            )
        ],
        quant_units=[
            _quant_unit(
                required_variables=("old_value", "new_value"),
                calculation_kind="cagr",
                units={"old_value": "USD", "new_value": "USD"},
            )
        ],
    )

    assert "unit_mismatch" in mismatch["quant_packets"][0]["blocked_reasons"]
    assert mismatch["judgment"].source_bound_numeric_unknowns
    assert blocked["quant_packets"][0]["calculation_status"] == "blocked"
    assert "calculation_kind_not_whitelisted" in blocked["quant_packets"][0][
        "blocked_reasons"
    ]
    assert blocked["judgment"].source_bound_numeric_unknowns


def test_high_stakes_quant_missing_exact_value_fails_closed_partial() -> None:
    result = _numeric_spine(
        records=[
            _numeric_record(
                numeric_facts=[{"variable": "old_value", "value": 100, "unit": "USD"}]
            )
        ],
        quant_units=[
            _quant_unit(
                required_variables=("old_value", "new_value"),
                calculation_kind="difference",
                units={"old_value": "USD", "new_value": "USD"},
                high_stakes=True,
            )
        ],
    )

    assert result["quant_packets"][0]["high_stakes_quant"] is True
    assert "high_stakes_quant_requires_exact_values" in result["quant_packets"][0][
        "blocked_reasons"
    ]
    assert result["packet"].readiness_status is FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED
    assert _payload_authority(result)["source_bound_numeric_unknowns"]


def test_resolved_and_unresolved_quant_outputs_reach_author_payload() -> None:
    resolved = _numeric_spine(
        records=[
            _numeric_record(
                numeric_facts=[{"variable": "rate", "value": 9.5, "unit": "percent"}]
            )
        ],
        quant_units=[
            _quant_unit(
                required_variables=("rate",),
                calculation_kind="identity",
                units={"rate": "percent"},
            )
        ],
    )
    unresolved = _numeric_spine(
        records=[
            _numeric_record(
                numeric_facts=[{"variable": "other_rate", "value": 9.5, "unit": "percent"}]
            )
        ],
        quant_units=[
            _quant_unit(
                required_variables=("rate",),
                calculation_kind="identity",
                units={"rate": "percent"},
            )
        ],
    )

    resolved_authority = _payload_authority(resolved)
    unresolved_authority = _payload_authority(unresolved)
    assert resolved_authority["source_bound_numeric_resolutions"]
    assert "Source-bound numeric resolved values:" in resolved["payload"].prompt
    assert unresolved_authority["source_bound_numeric_unknowns"]
    assert "Source-bound numeric unknowns:" in unresolved["payload"].prompt


def test_unresolved_quant_packet_reports_extraction_without_calculation() -> None:
    result = _numeric_spine(
        records=[
            _numeric_record(
                numeric_facts=[{"variable": "other_rate", "value": 9.5, "unit": "percent"}]
            )
        ],
        quant_units=[
            _quant_unit(
                required_variables=("rate",),
                calculation_kind="identity",
                units={"rate": "percent"},
            )
        ],
    )
    flags = _payload_authority(result)["behavior_boundary_flags"]

    assert result["quant_packets"][0]["extraction_status"] == "unresolved"
    assert flags["quant_extraction_executed"] is True
    assert flags["calculation_executed"] is False
    assert flags["arbitrary_code_execution_used"] is False


def test_no_quant_packet_preserves_false_quant_behavior_flags() -> None:
    record = _numeric_record(
        numeric_facts=[{"variable": "rate", "value": 9.5, "unit": "percent"}]
    )
    result = _numeric_spine(records=[record], quant_units=[])
    flags = _payload_authority(result)["behavior_boundary_flags"]

    assert result["quant_packets"] == ()
    assert flags["quant_extraction_executed"] is False
    assert flags["calculation_executed"] is False
    assert flags["arbitrary_code_execution_used"] is False


def test_numeric_success_does_not_upgrade_unrelated_official_obligation() -> None:
    record = _numeric_record(
        numeric_facts=[{"variable": "rate", "value": 9.5, "unit": "percent"}]
    )
    unrelated_official = {
        "requirement_id": "run-contract:unrelated-official-fee",
        "requirement_kind": "official_current",
        "strictness": "required",
        "required_source_class": "official_fee_schedule",
        "component_id": "component-fee",
        "source_obligation_id": "obligation-official-fee",
        "provider_job_id": "provider-official-fee",
    }
    result = _numeric_spine(
        contract=_contract(REQS["numeric"], unrelated_official),
        records=[record],
        quant_units=[
            _quant_unit(
                required_variables=("rate",),
                calculation_kind="identity",
                units={"rate": "percent"},
            )
        ],
    )
    authority = _payload_authority(result)

    assert authority["source_bound_numeric_resolutions"]
    assert result["judgment"].decision is not RunSufficiencyDecision.READY_DIRECT
    assert any(
        item.get("requirement_kind") == "official_current"
        for item in authority["missing_source_obligations"]
    )


def test_quant_packet_redacts_raw_private_material() -> None:
    record = _numeric_record(
        numeric_facts=[
            {
                "variable": "rate",
                "value": 9.5,
                "unit": "percent",
                "raw_text": "RAW_TEXT_SENTINEL",
            }
        ],
    )
    record.update(
        {
            "raw_prompt": "RAW_PROMPT_SENTINEL",
            "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
            "raw_model_response": "RAW_MODEL_SENTINEL",
            "full_text": "FULL_TEXT_SENTINEL",
            "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
            "token": "TOKEN_SENTINEL",
            "db_row": "DB_ROW_SENTINEL",
            "full_trace": "FULL_TRACE_SENTINEL",
        }
    )
    result = _numeric_spine(
        records=[record],
        quant_units=[
            _quant_unit(
                required_variables=("rate",),
                calculation_kind="identity",
                units={"rate": "percent"},
            )
        ],
    )
    encoded = json.dumps(
        {
            "packets": result["quant_packets"],
            "judgment": result["judgment"].to_projection(),
            "packet": result["packet"].to_dict(),
            "authority": result["payload"].authority_payload,
        },
        sort_keys=True,
    )

    for sentinel in (
        "RAW_TEXT_SENTINEL",
        "RAW_PROMPT_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "RAW_MODEL_SENTINEL",
        "FULL_TEXT_SENTINEL",
        "SECRET_SENTINEL",
        "TOKEN_SENTINEL",
        "DB_ROW_SENTINEL",
        "FULL_TRACE_SENTINEL",
    ):
        assert sentinel not in encoded


def test_static_guards_keep_quant_runtime_bounded_and_search_work_passive() -> None:
    runtime_path = ROOT / "core" / "quant_work_unit_runtime.py"
    runtime_source = runtime_path.read_text(encoding="utf-8")
    runtime_imports = _imports(runtime_path)
    forbidden_imports = {
        "subprocess",
        "os",
        "core.search_providers",
        "core.search_work_provider_job_execution",
        "core.provider_job_evidence_ledger_bridge",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.pipeline_orchestrator",
        "core.author_execution_runtime",
    }
    forbidden_tokens = (
        "eval(",
        "exec(",
        "ask_model",
        "search_providers",
        "subprocess",
        "format_citation",
    )

    assert runtime_imports.isdisjoint(forbidden_imports)
    for token in forbidden_tokens:
        assert token not in runtime_source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "quant_work_unit_runtime" not in pipeline_source
    assert "source_bound_numeric_resolutions" not in pipeline_source

    search_work_source = (ROOT / "core" / "search_work_plan.py").read_text(
        encoding="utf-8"
    )
    assert "executes_calculations\": False" in search_work_source
    assert "build_quant_work_unit_packets" not in search_work_source

    final_packet_source = (ROOT / "core" / "final_answer_packet.py").read_text(
        encoding="utf-8"
    )
    assert "format_citation" not in final_packet_source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
