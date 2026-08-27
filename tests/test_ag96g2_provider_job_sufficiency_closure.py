from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from core.evidence_ledger_lifecycle import (
    reduce_provider_job_evidence_into_evidence_ledger,
    reduce_run_contract_requirements_into_evidence_ledger,
)
from core.final_answer_packet import FinalAnswerReadinessStatus
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgmentInput,
    SufficiencyPosture,
)
from core.run_authority_sufficiency_runtime import (
    execute_sufficiency_judgment_handoff_from_scope,
)
from core.run_authority_sufficiency_validation import (
    build_deterministic_sufficiency_judgment,
)
from core.run_kernel import RunKernel

ROOT = Path(__file__).resolve().parents[1]


def _requirement(
    requirement_id: str,
    *,
    kind: str,
    source_class: str,
    source_tier: str | None = None,
    currentness: str | None = None,
    component_id: str | None = None,
    source_obligation_id: str | None = None,
    provider_job_id: str | None = None,
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "requirement_kind": kind,
        "strictness": "required",
        "required_source_class": source_class,
        "required_source_tier": source_tier,
        "required_currentness": currentness,
        "component_id": component_id,
        "source_obligation_id": source_obligation_id,
        "provider_job_id": provider_job_id,
    }


def _contract(*requirements: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": "ag96g2-contract",
        "selected_template_ids": ["ag96g2"],
        "source_requirements": [
            {key: value for key, value in item.items() if key != "provider_job_id"} for item in requirements
        ],
        "final_posture_policy": {
            "partial_allowed_if": "some required obligations remain missing",
            "mandatory_caveats": [
                "missing_source_custody_must_be_caveated",
            ],
            "prohibited_upgrades": [
                "do_not_upgrade_missing_official_current_custody",
            ],
        },
    }


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
    }


def _record(
    *,
    execution_id: str,
    component_id: str,
    provider_job_id: str,
    provider_job_kind: str,
    obligation_id: str,
    query: str,
) -> dict[str, Any]:
    return {
        "execution_id": execution_id,
        "component_id": component_id,
        "provider_job_id": provider_job_id,
        "provider_job_kind": provider_job_kind,
        "source_obligation_ids": [obligation_id],
        "query_plan_item_ids": [f"query-plan-item-{provider_job_id}"],
        "authorized_queries": [query],
        "dispatch_refs": [f"dispatch-{provider_job_id}"],
        "execution_status": "admitted",
        "execution_owner": "existing_retrieval_loop",
        "handoff_to_existing_retrieval_loop": True,
        "source_obligations_satisfied": False,
        "official_current_custody_satisfied": False,
        "quant_extraction_executed": False,
        "calculation_executed": False,
        "evidence_refs": [],
    }


def _handoff(*records: Mapping[str, Any]) -> dict[str, Any]:
    active = list(records) or [
        _record(
            execution_id="provider-job-execution:official",
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
        "provider_job_execution_record_count": len(active),
        "provider_job_execution_records": active,
    }


def _candidate(
    *,
    query: str,
    source_class: str,
    source_tier: str,
    currentness: str | None = "current",
    disposition: str = "accepted",
    eligible: bool = True,
) -> dict[str, Any]:
    return {
        "url": f"https://example.gov/{source_class}",
        "title": f"{source_class} candidate",
        "query_ref": query,
        "source_tier": source_tier,
        "source_class": source_class,
        "currentness_signal": currentness,
        "readable_status": "readable",
        "fetchable_status": "fetchable",
        "disposition": disposition,
        "eligible_for_stronger_obligation": eligible,
    }


def _kernel_with_contract_and_provider_job_ledger(
    contract: Mapping[str, Any],
    *,
    handoff: Mapping[str, Any] | None = None,
    retrieval_records: Any = None,
) -> tuple[RunKernel, dict[str, Any]]:
    kernel = RunKernel.start(run_id="ag96g2", request_id="request")
    kernel.state.run_contract_projection = dict(contract)
    reduce_run_contract_requirements_into_evidence_ledger(
        run_kernel=kernel,
        run_id="ag96g2",
        run_contract_projection=contract,
        observation_id_suffix="contract",
        authorization_observation_source="ag96g2_contract",
    )
    reduced = reduce_provider_job_evidence_into_evidence_ledger(
        run_kernel=kernel,
        run_id="ag96g2",
        provider_job_execution_handoff=handoff or _handoff(),
        query_plan_trace={"items": []},
        current_authorized_queries=[
            "official current filing fee",
            "legal deadline appeal rule",
            "API parameter documentation",
            "numeric rate amount source",
        ],
        retrieval_records=retrieval_records
        if retrieval_records is not None
        else [
            _candidate(
                query="official current filing fee",
                source_class="official_current_rules",
                source_tier="official",
            )
        ],
        search_work_projection=_search_work_projection(),
    )
    return kernel, reduced["evidence_ledger_projection"]


def _judgment(
    contract: Mapping[str, Any],
    ledger: Mapping[str, Any],
    *,
    final_evidence_count: int = 1,
) -> Any:
    return build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection=contract,
            evidence_ledger_projection=ledger,
            answer_contract_projection={},
            source_obligation_projection=ledger,
            final_evidence_facts={
                "final_evidence_count": final_evidence_count,
                "author_evidence_count": final_evidence_count,
                "citation_eligible_candidate_count": final_evidence_count,
                "quant_extraction_executed": False,
                "calculation_executed": False,
            },
        )
    )


def test_single_skeleton_contract_falls_back_to_unambiguous_provider_job_custody() -> None:
    contract = _contract(
        _requirement(
            "run-contract:official_current_rules",
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
        )
    )
    ledger = {
        "candidate_count": 1,
        "requirement_count": 1,
        "source_requirements": [
            {
                "requirement_id": (
                    "provider_job_requirement:component-fee:obligation-official-fee:provider-official-fee"
                ),
                "requirement_kind": "official_current",
                "required_source_class": "official_current_rules",
                "required_source_tier": "official",
                "required_currentness": "current",
                "status": "satisfied",
                "linked_candidate_ids": ["candidate-official-fee"],
            }
        ],
    }

    judgment = _judgment(contract, ledger)

    assert judgment.required_obligations_satisfied is False
    assert not judgment.satisfied_obligations
    assert len(judgment.missing_required_obligations) == 1


def test_ref_mismatch_does_not_use_official_current_class_fallback() -> None:
    contract = _contract(
        _requirement(
            "run-contract:official_fee",
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
            component_id="component-fee",
            source_obligation_id="obligation-official-fee",
            provider_job_id="provider-official-fee",
        ),
        _requirement(
            "run-contract:official-deadline",
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
            component_id="component-deadline",
            source_obligation_id="obligation-official-deadline",
            provider_job_id="provider-official-deadline",
        ),
    )
    ledger = {
        "candidate_count": 1,
        "requirement_count": 1,
        "source_requirements": [
            {
                "requirement_id": (
                    "provider_job_requirement:component-fee:obligation-official-fee:provider-official-fee"
                ),
                "requirement_kind": "official_current",
                "required_source_class": "official_current_rules",
                "required_source_tier": "official",
                "required_currentness": "current",
                "status": "satisfied",
                "linked_candidate_ids": ["candidate-official-fee"],
            }
        ],
    }

    judgment = _judgment(contract, ledger)

    assert not judgment.satisfied_obligations
    assert {item.component_id for item in judgment.missing_required_obligations} == {
        "component_fee",
        "component_deadline",
    }
    assert judgment.required_obligations_satisfied is False
    assert judgment.decision is RunSufficiencyDecision.PARTIAL_ANSWER_AUTHORIZED


def test_skeleton_contract_does_not_fallback_when_multiple_compatible_ledgers() -> None:
    contract = _contract(
        _requirement(
            "run-contract:official_current_rules",
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
        )
    )
    ledger = {
        "candidate_count": 2,
        "requirement_count": 2,
        "source_requirements": [
            {
                "requirement_id": (
                    "provider_job_requirement:component-fee:obligation-official-fee:provider-official-fee"
                ),
                "requirement_kind": "official_current",
                "required_source_class": "official_current_rules",
                "required_source_tier": "official",
                "required_currentness": "current",
                "status": "satisfied",
                "linked_candidate_ids": ["candidate-official-fee"],
            },
            {
                "requirement_id": (
                    "provider_job_requirement:component-deadline:"
                    "obligation-official-deadline:provider-official-deadline"
                ),
                "requirement_kind": "official_current",
                "required_source_class": "official_current_rules",
                "required_source_tier": "official",
                "required_currentness": "current",
                "status": "satisfied",
                "linked_candidate_ids": ["candidate-official-deadline"],
            },
        ],
    }

    judgment = _judgment(contract, ledger)

    assert not judgment.satisfied_obligations
    assert judgment.missing_required_obligations
    assert judgment.required_obligations_satisfied is False


def test_satisfied_official_current_provider_job_custody_governs_ready_direct() -> None:
    contract = _contract(
        _requirement(
            "run-contract:official_current_rules",
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
            component_id="component-fee",
            source_obligation_id="obligation-official-fee",
            provider_job_id="provider-official-fee",
        )
    )
    _kernel, ledger = _kernel_with_contract_and_provider_job_ledger(contract)

    judgment = _judgment(contract, ledger)

    assert judgment.decision is RunSufficiencyDecision.READY_DIRECT
    assert judgment.final_answer_posture is SufficiencyPosture.DIRECT_ANSWER
    assert judgment.required_obligations_satisfied is True
    assert not judgment.missing_required_obligations
    assert judgment.satisfied_obligations[0].component_id == "component_fee"
    assert judgment.satisfied_obligations[0].source_obligation_id == ("obligation_official_fee")
    assert judgment.satisfied_obligations[0].provider_job_id is None


def test_aggregate_only_official_current_never_satisfies_custody() -> None:
    contract = _contract(
        _requirement(
            ("provider_job_requirement:component-fee:obligation-official-fee:provider-official-fee"),
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
            component_id="component-fee",
            source_obligation_id="obligation-official-fee",
            provider_job_id="provider-official-fee",
        )
    )
    ledger = {
        "candidate_count": 0,
        "requirement_count": 1,
        "source_requirements": [
            {
                "requirement_id": (
                    "provider_job_requirement:component-fee:obligation-official-fee:provider-official-fee"
                ),
                "requirement_kind": "official_current",
                "required_source_class": "official_current_rules",
                "required_source_tier": "official",
                "required_currentness": "current",
                "status": "unsatisfied",
                "reason": "aggregate_counts_cannot_satisfy_custody",
                "aggregate_counts_insufficient": True,
                "linked_candidate_ids": [],
            }
        ],
        "custody_gaps": [
            {
                "gap_type": "legacy_aggregate_only_path",
                "requirement_id": (
                    "provider_job_requirement:component-fee:obligation-official-fee:provider-official-fee"
                ),
                "reason": "aggregate count observed without candidate identity",
            }
        ],
    }

    judgment = _judgment(contract, ledger)

    assert judgment.decision is not RunSufficiencyDecision.READY_DIRECT
    assert judgment.missing_required_obligations
    assert "official_current_unsatisfied:official_current_rules" in (judgment.mandatory_caveats)
    assert "missing_source_custody_must_be_caveated" in (judgment.mandatory_caveats)
    assert not judgment.satisfied_obligations
    assert "do_not_treat_aggregate_counts_as_evidence_ledger_custody" in (judgment.prohibited_upgrades)


def test_lower_tier_context_candidate_does_not_upgrade_strict_obligation() -> None:
    contract = _contract(
        _requirement(
            "run-contract:official_current_rules",
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
        )
    )
    _kernel, ledger = _kernel_with_contract_and_provider_job_ledger(
        contract,
        retrieval_records=[
            _candidate(
                query="official current filing fee",
                source_class="reputable_secondary",
                source_tier="secondary",
                eligible=False,
            )
        ],
    )

    judgment = _judgment(contract, ledger)

    assert judgment.decision is not RunSufficiencyDecision.READY_DIRECT
    assert judgment.missing_required_obligations
    assert not judgment.satisfied_obligations
    assert "do_not_treat_lower_tier_stale_or_off_topic_evidence_as_required_custody" in (judgment.prohibited_upgrades)


def test_legal_current_primary_candidate_satisfies_legal_obligation() -> None:
    contract = _contract(
        _requirement(
            "run-contract:legal_or_regulatory_text",
            kind="legal_primary",
            source_class="legal_or_regulatory_text",
            source_tier="primary",
            currentness="current",
        )
    )
    handoff = _handoff(
        _record(
            execution_id="provider-job-execution:legal",
            component_id="component-legal",
            provider_job_id="provider-legal-currentness",
            provider_job_kind="conflict_currentness_check",
            obligation_id="obligation-legal-deadline",
            query="legal deadline appeal rule",
        )
    )
    _kernel, ledger = _kernel_with_contract_and_provider_job_ledger(
        contract,
        handoff=handoff,
        retrieval_records=[
            _candidate(
                query="legal deadline appeal rule",
                source_class="legal_or_regulatory_text",
                source_tier="primary",
            )
        ],
    )

    judgment = _judgment(contract, ledger)

    assert judgment.required_obligations_satisfied is True
    assert judgment.satisfied_obligations[0].requirement_kind == "legal_primary"


def test_canonical_documentation_candidate_satisfies_canonical_obligation() -> None:
    contract = _contract(
        _requirement(
            "run-contract:canonical_docs",
            kind="canonical_docs",
            source_class="primary_source_documents",
            source_tier="canonical",
            currentness="current",
        )
    )
    handoff = _handoff(
        _record(
            execution_id="provider-job-execution:api",
            component_id="component-api",
            provider_job_id="provider-api-canonical",
            provider_job_kind="canonical_extraction",
            obligation_id="obligation-api-docs",
            query="API parameter documentation",
        )
    )
    _kernel, ledger = _kernel_with_contract_and_provider_job_ledger(
        contract,
        handoff=handoff,
        retrieval_records=[
            _candidate(
                query="API parameter documentation",
                source_class="primary_source_documents",
                source_tier="canonical",
            )
        ],
    )

    judgment = _judgment(contract, ledger)

    assert judgment.required_obligations_satisfied is True
    assert judgment.satisfied_obligations[0].requirement_kind == "canonical_docs"


def test_source_bound_numeric_candidate_without_extraction_remains_unknown() -> None:
    contract = _contract(
        _requirement(
            ("provider_job_requirement:component-numeric:obligation-source-bound-numeric:provider-numeric-extract"),
            kind="source_bound_numeric",
            source_class="sourced_numeric_values",
            source_tier="official",
            component_id="component-numeric",
            source_obligation_id="obligation-source-bound-numeric",
            provider_job_id="provider-numeric-extract",
        )
    )
    handoff = _handoff(
        _record(
            execution_id="provider-job-execution:numeric",
            component_id="component-numeric",
            provider_job_id="provider-numeric-extract",
            provider_job_kind="fetch_read_extract",
            obligation_id="obligation-source-bound-numeric",
            query="numeric rate amount source",
        )
    )
    _kernel, ledger = _kernel_with_contract_and_provider_job_ledger(
        contract,
        handoff=handoff,
        retrieval_records=[
            _candidate(
                query="numeric rate amount source",
                source_class="sourced_numeric_values",
                source_tier="official",
            )
        ],
    )

    judgment = _judgment(contract, ledger)

    assert judgment.satisfied_obligations
    assert judgment.source_bound_numeric_unknowns
    assert judgment.decision is RunSufficiencyDecision.SOURCE_BOUND_NUMERIC_UNKNOWN
    assert judgment.final_answer_posture is SufficiencyPosture.PARTIAL_ANSWER
    assert "do_not_present_source_bound_numeric_unknown_as_known" in (judgment.prohibited_upgrades)


def test_mixed_multipart_reports_satisfied_and_missing_separately() -> None:
    contract = _contract(
        _requirement(
            ("provider_job_requirement:component-fee:obligation-official-fee:provider-official-fee"),
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
            component_id="component-fee",
            source_obligation_id="obligation-official-fee",
            provider_job_id="provider-official-fee",
        ),
        _requirement(
            ("provider_job_requirement:component-legal:obligation-legal-deadline:provider-legal-currentness"),
            kind="legal_primary",
            source_class="legal_or_regulatory_text",
            source_tier="primary",
            currentness="current",
            component_id="component-legal",
            source_obligation_id="obligation-legal-deadline",
            provider_job_id="provider-legal-currentness",
        ),
    )
    _kernel, ledger = _kernel_with_contract_and_provider_job_ledger(contract)

    judgment = _judgment(contract, ledger)

    assert judgment.decision is RunSufficiencyDecision.PARTIAL_ANSWER_AUTHORIZED
    assert judgment.final_answer_posture is SufficiencyPosture.PARTIAL_ANSWER
    assert [item.component_id for item in judgment.satisfied_obligations] == ["component_fee"]
    assert {item.component_id for item in judgment.missing_required_obligations} == {"component_legal"}


def test_g1_bridge_noop_fallback_does_not_invent_satisfaction() -> None:
    contract = _contract(
        _requirement(
            ("provider_job_requirement:component-fee:obligation-official-fee:provider-official-fee"),
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
        )
    )
    _kernel, ledger = _kernel_with_contract_and_provider_job_ledger(
        contract,
        handoff={},
        retrieval_records=[],
    )

    judgment = _judgment(contract, ledger, final_evidence_count=0)

    assert judgment.required_obligations_satisfied is False
    assert judgment.missing_required_obligations
    assert not judgment.satisfied_obligations


def test_runtime_handoff_consumes_post_g1_runkernel_evidence_ledger_projection() -> None:
    contract = _contract(
        _requirement(
            "run-contract:official_current_rules",
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
            component_id="component-fee",
            source_obligation_id="obligation-official-fee",
            provider_job_id="provider-official-fee",
        )
    )
    kernel, ledger = _kernel_with_contract_and_provider_job_ledger(contract)
    runtime_scope = {
        "evidence_ledger_projection": ledger,
        "run_contract_projection": contract,
        "final_top_evidence": [{"url": "https://example.gov/rule"}],
        "scrutineer_flags": [],
        "corpus_weak": False,
        "answer_contract_projection": {},
        "author_evidence": [{"url": "https://example.gov/rule"}],
        "unique_source_urls": {"https://example.gov/rule"},
        "weak_corpus_recovery_skip_reason": None,
        "corpus_state": "healthy",
        "synth_was_insufficient": False,
        "_pre_gate_failure_card_show": False,
        "_pre_gate_failure_card_reason": None,
        "iterations_run": 1,
        "max_iterations": 3,
        "_run_controller_mirror": SimpleNamespace(state=SimpleNamespace(active_source_class_recovery_attempt_count=0)),
    }

    handoff = execute_sufficiency_judgment_handoff_from_scope(
        kernel,
        runtime_scope,
        smart_model_enabled=False,
    )

    assert handoff.projection["decision"] == RunSufficiencyDecision.READY_DIRECT.value
    assert handoff.projection["satisfied_obligations"][0]["component_id"] == ("component_fee")


def test_final_packet_inputs_carry_machine_readable_posture_downstream() -> None:
    contract = _contract(
        _requirement(
            "run-contract:official_current_rules",
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
        )
    )
    _kernel, ledger = _kernel_with_contract_and_provider_job_ledger(
        contract,
        retrieval_records={"source_tier_counts": {"official": 1}},
    )
    projection = _judgment(contract, ledger).to_projection()
    packet_inputs = projection["final_packet_inputs"]
    packet = build_final_answer_packet(
        run_id="ag96g2-final-packet",
        final_evidence=[{"url": "https://example.gov/rule"}],
        run_contract_projection=contract,
        sufficiency_judgment_projection=projection,
    )

    assert packet.readiness_status is FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED
    assert packet_inputs["required_obligations_satisfied"] is False
    assert packet_inputs["missing_required_obligations"]
    assert packet_inputs["mandatory_caveats"]
    assert packet_inputs["prohibited_upgrades"]
    assert packet_inputs["readiness_status"] == "insufficient_authorized"
    assert packet_inputs["claim_postures"] == ["insufficient_evidence"]


def test_behavior_boundaries_and_redaction_are_preserved() -> None:
    contract = _contract(
        _requirement(
            "run-contract:official_current_rules",
            kind="official_current",
            source_class="official_current_rules",
            source_tier="official",
            currentness="current",
        )
    )
    contract["raw_prompt"] = "RAW_PROMPT_SENTINEL"
    contract["secret"] = "SECRET_SENTINEL"  # pragma: allowlist secret
    _kernel, ledger = _kernel_with_contract_and_provider_job_ledger(
        contract,
        retrieval_records=[
            {
                **_candidate(
                    query="official current filing fee",
                    source_class="official_current_rules",
                    source_tier="official",
                ),
                "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
                "raw_model_response": "RAW_MODEL_SENTINEL",
                "raw_text": "RAW_TEXT_SENTINEL",
                "full_text": "FULL_TEXT_SENTINEL",
                "snippets": ["SNIPPET_SENTINEL"],
                "db_row": "DB_ROW_SENTINEL",
                "token": "TOKEN_SENTINEL",
            }
        ],
    )

    projection = _judgment(contract, ledger).to_projection()
    flags = projection["final_packet_inputs"]["behavior_boundary_flags"]
    assert flags == {
        "query_text_generated": False,
        "provider_search_behavior_changed": False,
        "retrieval_behavior_changed": False,
        "prompt_behavior_changed": False,
        "citation_behavior_changed": False,
        "author_prose_behavior_changed": False,
        "arbitrary_code_execution_used": False,
        "quant_extraction_executed": False,
        "calculation_executed": False,
    }

    encoded = json.dumps(projection, sort_keys=True)
    for sentinel in (
        "RAW_PROMPT_SENTINEL",
        "SECRET_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "RAW_MODEL_SENTINEL",
        "RAW_TEXT_SENTINEL",
        "FULL_TEXT_SENTINEL",
        "SNIPPET_SENTINEL",
        "DB_ROW_SENTINEL",
        "TOKEN_SENTINEL",
    ):
        assert sentinel not in encoded


def test_static_guards_keep_g2_inside_sufficiency_and_no_provider_runtime() -> None:
    validation_imports = _imports(ROOT / "core" / "run_authority_sufficiency_validation.py")
    adapter_imports = _imports(ROOT / "core" / "run_authority_sufficiency_adapter.py")
    forbidden = {
        "core.search_providers",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.final_answer_packet",
        "core.final_answer_runtime_assembly",
        "core.author_execution_runtime",
        "core.pipeline_orchestrator",
    }

    assert validation_imports.isdisjoint(forbidden)
    assert adapter_imports.isdisjoint(forbidden)

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(encoding="utf-8")
    assert "build_deterministic_sufficiency_judgment" not in pipeline_source
    assert "SufficiencyRequirementAssessment(" not in pipeline_source
    assert "READY_DIRECT" not in pipeline_source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
