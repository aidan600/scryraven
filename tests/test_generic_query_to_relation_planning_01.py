"""PRODUCT-PATH-REGRESSION: generic query-to-relation planning dry run.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --mvp-query-plan-status
Runtime consumer: proplex.__main__ ->
core.generic_query_to_relation_planning.build_generic_query_plan_status_output
Why ordinary product-path work cannot be done directly: this is the ordinary
CLI dry-run path for supported-query relation planning, while live provider,
model, search, fetch/read, D-prime review, FAP, and Author surfaces remain
closed in this phase.
Integration deadline: current phase.
Exit condition: keep while the MVP supported-query planning dry-run flag exists,
or replace with the later live single-relation dogfood product-path guard.
Why this is not a shadow product path: the tests call the new default-off CLI
entrypoint and its runtime consumer; they do not create an alternate answer path.
Forbidden interpretation: this is not arbitrary query answering, generic live
answering, source-authority adjudication, D-prime support, source-obligation
satisfaction, FAP/Author output, product correctness, or friend-level/general
MVP readiness.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest

from core.generic_query_to_relation_planning import (
    BLOCKED_GENERIC_QUERY_PLANNING_HARD_EXCLUSION,
    BLOCKED_GENERIC_QUERY_PLANNING_MULTI_COMPONENT,
    GENERIC_QUERY_TO_RELATION_PLANNING_PHASE,
    MVP_QUERY_PLAN_PACKET_NAME,
    MVP_QUERY_PLAN_STATUS_FLAG,
    build_generic_query_plan_status_output,
    build_generic_query_relation_plan,
)
from core.mvp_supported_query_class_boundary import MVP_SUPPORTED_QUERY_CLASS_ID
from core.product_model_route_config import (
    MVP_DEMO_FLAG,
    MVP_LIVE_DOGFOOD_RUN_FLAG,
    MVP_LIVE_DOGFOOD_STATUS_FLAG,
    PRODUCT_STATUS_DRY_RUN_FLAGS,
    initialize_product_model_route_config,
)
from core.source_authority_posture_packet import SOURCE_AUTHORITY_POSTURE_PHASE
from proplex.mvp_friend_shareable_output import DEFAULT_MVP_QUERY, MVP_COMPONENT_ID

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "generic_query_to_relation_planning.py"
SMALL_CLAIMS_QUERY = (
    "What is the current filing fee for small claims in Example County?"
)


def test_supported_passport_query_creates_single_relation_plan(
    tmp_path: Path,
) -> None:
    result = build_generic_query_plan_status_output(
        query=DEFAULT_MVP_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_query_plan_01",
        run_id="passport-plan",
    )

    packet = _load_packet(result.packet_path)

    assert result.return_code == 0
    assert packet["planning_status"] == "planned"
    assert packet["phase_name"] == GENERIC_QUERY_TO_RELATION_PLANNING_PHASE
    assert packet["supported_query_class_id"] == MVP_SUPPORTED_QUERY_CLASS_ID
    assert packet["supported_query_class_boundary"]["profile_id"] == (
        MVP_SUPPORTED_QUERY_CLASS_ID
    )
    assert packet["source_authority_posture_contract_ref"] == (
        SOURCE_AUTHORITY_POSTURE_PHASE
    )
    requirement = packet["source_authority_posture_requirement"]
    assert requirement["contract_ref"] == SOURCE_AUTHORITY_POSTURE_PHASE
    assert requirement["analyst_owned"] is True
    assert requirement["planner_must_not_decide_authority"] is True
    assert requirement["expected_source_use_requirement"] == "authority"
    assert requirement["actual_source_authority_posture_created"] is False
    assert packet["actual_source_authority_posture_created"] is False
    assert "recommended_source_use" not in json.dumps(packet, sort_keys=True)
    assert packet["component_count"] == 1
    assert packet["source_obligation_count"] == 1
    assert packet["search_requirement_count"] == 1
    assert packet["component_id"] != MVP_COMPONENT_ID
    assert packet["component_id"].startswith("component:")
    assert packet["source_obligation_id"].startswith("obligation:")
    assert packet["search_requirement_id"].startswith("searchreq:")
    assert packet["answer_created"] is False
    assert packet["live_calls_made"] is False
    assert packet["model_calls_made"] is False
    assert packet["product_correctness_claimed"] is False
    assert "relation plan produced" in result.output
    assert "No answer produced: true" in result.output
    assert "Live/model calls made: false" in result.output


def test_supported_non_passport_query_proves_passport_is_not_architecture(
    tmp_path: Path,
) -> None:
    passport = build_generic_query_relation_plan(DEFAULT_MVP_QUERY)
    packet = build_generic_query_plan_status_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_query_plan_01",
        run_id="small-claims-plan",
    ).packet
    serialized = json.dumps(packet, sort_keys=True).casefold()

    assert packet["planning_status"] == "planned"
    assert packet["fact_kind"] == "fee"
    assert packet["component_count"] == 1
    assert packet["component_id"] != passport["component_id"]
    assert packet["plan_id"] != passport["plan_id"]
    assert "passport" not in serialized
    assert "example county" in serialized
    canonical = packet["supported_query_class_boundary"][
        "canonical_fixed_dogfood_example"
    ]
    assert canonical["example_only"] is True
    assert canonical["architecture_definition"] is False


def test_relation_plan_emits_dprime_and_future_component_node_candidates() -> None:
    packet = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)

    binding = packet["component_answer_type_binding_ref"]
    dprime = packet["dprime_relation_intake_candidate"]
    assert dprime["target_runtime_surface"] == (
        "core.dprime_analyst_relation_intake_runtime"
    )
    assert dprime["component_id"] == packet["component_id"]
    assert dprime["claim_under_test"] == packet["claim_under_test"]
    assert dprime["source_obligation_id"] == packet["source_obligation_id"]
    assert dprime["search_requirement_id"] == packet["search_requirement_id"]
    assert dprime["relation_plan_id"] == packet["plan_id"]
    assert dprime["answer_created"] is False
    assert dprime["evidence_acquired"] is False
    assert dprime["support_claimed"] is False
    assert dprime["component_answer_type_binding_ref"]["binding_digest"] == (
        binding["binding_digest"]
    )

    future = packet["future_component_work_node_candidate"]
    assert future["node_id"].startswith("component-work-node-candidate:")
    assert future["parent_plan_id"] == packet["plan_id"]
    assert future["component_id"] == packet["component_id"]
    assert future["component_type"] == "single_source_of_record_fact_lookup"
    assert future["dependency_ids"] == []
    assert future["search_requirement_ids"] == [packet["search_requirement_id"]]
    assert future["source_obligation_requirement_ids"] == [
        packet["source_obligation_id"]
    ]
    assert future["budget_lease_created"] is False
    assert future["runkernel_scheduler_authorized"] is False
    assert future["component_work_node_implemented"] is False
    assert future["component_work_graph_implemented"] is False


def test_fee_query_creates_non_authority_component_answer_type_binding() -> None:
    packet = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)

    binding = packet["component_answer_type_binding"]
    binding_ref = packet["component_answer_type_binding_ref"]
    assert binding["component_id"] == packet["component_id"]
    assert binding["component_digest"] == packet["components"][0]["component_digest"]
    assert binding["component_text"] == packet["component_text"]
    assert binding["source_obligation_id"] == packet["source_obligation_id"]
    assert binding["source_obligation_text"] == packet["source_obligation_text"]
    assert binding["fact_kind"] == "fee"
    assert binding["requested_answer_type"] == "fee_amount_current_standard_value"
    assert binding["claim_under_test"] == packet["claim_under_test"]
    assert binding["expected_value_shape"] == "currency_amount"
    assert binding["expected_value_token_kinds"] == ["currency"]
    assert binding_ref["binding_digest"] == binding["binding_digest"]
    assert packet["components"][0]["component_answer_type_binding_ref"] == binding_ref
    assert packet["source_obligations"][0]["component_answer_type_binding_ref"] == (
        binding_ref
    )
    for adjacent in (
        "filing_mode",
        "waiver_eligibility",
        "reduced_fee_eligibility",
        "online_discount",
        "process_instructions",
    ):
        assert adjacent in binding["adjacent_claim_exclusions"]
    assert binding["adjacent_claims_do_not_satisfy_requested_answer_type"] is True
    assert binding["raw_private_retention_flags"] == {
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "raw_source_content_retained": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "private_logs_retained": False,
        "db_cache_rows_retained": False,
        "full_trace_retained": False,
    }
    assert binding["evidence_admitted"] is False
    assert binding["source_obligation_satisfied"] is False
    assert binding["citation_eligibility_created"] is False
    assert binding["sufficiency_readiness_created"] is False
    assert binding["final_answer_packet_created"] is False
    assert binding["author_output_created"] is False
    assert binding["product_correctness_claimed"] is False


def test_answer_type_binding_keeps_adjacent_fact_kinds_distinguishable() -> None:
    fee = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)[
        "component_answer_type_binding"
    ]
    deadline = build_generic_query_relation_plan(
        "What is the current filing deadline for Example County license renewal?"
    )["component_answer_type_binding"]
    requirement = build_generic_query_relation_plan(
        "What is the current filing requirement for Example County small claims?"
    )["component_answer_type_binding"]

    assert fee["requested_answer_type"] == "fee_amount_current_standard_value"
    assert fee["expected_value_shape"] == "currency_amount"
    assert "filing_mode" in fee["adjacent_claim_exclusions"]
    assert "waiver_eligibility" in fee["adjacent_claim_exclusions"]
    assert "reduced_fee_eligibility" in fee["adjacent_claim_exclusions"]
    assert "online_discount" in fee["adjacent_claim_exclusions"]
    assert deadline["requested_answer_type"] == "deadline_date"
    assert deadline["expected_value_shape"] == "date_or_date_range"
    assert "eligibility_description" in deadline["adjacent_claim_exclusions"]
    assert "historical_dates" in deadline["adjacent_claim_exclusions"]
    assert requirement["requested_answer_type"] == "requirement_action"
    assert requirement["expected_value_shape"] == "requirement_statement"
    assert "fee_amount" in requirement["adjacent_claim_exclusions"]
    assert "unrelated_eligibility" in requirement["adjacent_claim_exclusions"]


@pytest.mark.parametrize(
    ("query", "blocker", "category"),
    [
        (
            "How does this Honda compare to competitors?",
            BLOCKED_GENERIC_QUERY_PLANNING_HARD_EXCLUSION,
            "product_comparison_or_recommendation",
        ),
        (
            "What does Reddit say about this paint?",
            BLOCKED_GENERIC_QUERY_PLANNING_HARD_EXCLUSION,
            "social_review_aggregation",
        ),
        (
            "What is the current cost per passenger mile for a Boeing 777?",
            BLOCKED_GENERIC_QUERY_PLANNING_HARD_EXCLUSION,
            "calculation_or_normalization",
        ),
        (
            "What is the current fee and deadline for Example County small claims?",
            BLOCKED_GENERIC_QUERY_PLANNING_MULTI_COMPONENT,
            "multi_component",
        ),
    ],
)
def test_unsupported_queries_block_without_retaining_text(
    tmp_path: Path,
    query: str,
    blocker: str,
    category: str,
) -> None:
    result = build_generic_query_plan_status_output(
        query=query,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_query_plan_01",
        run_id=f"blocked-{category}",
    )
    packet = _load_packet(result.packet_path)
    serialized = json.dumps(packet, sort_keys=True)

    assert result.return_code == 2
    assert packet["planning_status"] == "blocked"
    assert packet["query"] == "unsupported query (not retained)"
    assert packet["unsupported_query_retained"] is False
    assert packet["blocker_code"] == blocker
    assert packet["hard_exclusion_category"] == category
    assert packet["relation_plan_created"] is False
    assert packet["dprime_relation_intake_candidate_created"] is False
    assert packet["future_component_work_node_candidate_created"] is False
    assert packet["answer_created"] is False
    assert packet["live_calls_made"] is False
    assert packet["model_calls_made"] is False
    assert packet["product_correctness_claimed"] is False
    assert query not in serialized
    assert query not in result.output
    assert query not in str(result.packet_path)
    assert query not in packet["packet_id"]
    assert query not in packet["packet_digest"]
    assert "blocked before relation planning" in result.output
    assert "Unsupported query text retained: false" in result.output


def test_cli_supported_dry_run_writes_packet_without_api_keys() -> None:
    output_subdir = f"output/test_generic_query_plan_cli/{uuid.uuid4().hex}"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proplex",
            MVP_QUERY_PLAN_STATUS_FLAG,
            "--query",
            SMALL_CLAIMS_QUERY,
            "--mvp-output-dir",
            output_subdir,
        ],
        cwd=ROOT,
        env=_no_key_env(),
        capture_output=True,
        text=True,
        timeout=45,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Decision: relation plan produced" in proc.stdout
    assert "OPENAI_API_KEY is required" not in proc.stderr
    packet = _single_cli_packet(output_subdir)
    assert packet["planning_status"] == "planned"
    assert packet["supported_query_class_id"] == MVP_SUPPORTED_QUERY_CLASS_ID
    assert packet["live_calls_made"] is False
    assert packet["model_calls_made"] is False


def test_cli_unsupported_dry_run_returns_two_without_retaining_text() -> None:
    query = "What does Reddit say about this paint?"
    output_subdir = f"output/test_generic_query_plan_cli/{uuid.uuid4().hex}"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proplex",
            MVP_QUERY_PLAN_STATUS_FLAG,
            "--query",
            query,
            "--mvp-output-dir",
            output_subdir,
        ],
        cwd=ROOT,
        env=_no_key_env(),
        capture_output=True,
        text=True,
        timeout=45,
    )

    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "Decision: blocked before relation planning" in proc.stdout
    assert "Unsupported query text retained: false" in proc.stdout
    assert query not in proc.stdout
    assert "OPENAI_API_KEY is required" not in proc.stderr
    packet = _single_cli_packet(output_subdir)
    assert packet["planning_status"] == "blocked"
    assert packet["unsupported_query_retained"] is False
    assert query not in json.dumps(packet, sort_keys=True)


def test_query_plan_flag_skips_dotenv_and_preempts_model_key_validation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = 0

    def fake_dotenv() -> bool:
        nonlocal calls
        calls += 1
        return True

    initialized = initialize_product_model_route_config(
        [MVP_QUERY_PLAN_STATUS_FLAG, "--query", SMALL_CLAIMS_QUERY],
        load_dotenv_func=fake_dotenv,
        environ={},
    )
    assert initialized.dotenv_skipped_for_status_dry_run is True
    assert initialized.dotenv_helper_invoked is False
    assert calls == 0

    cli = importlib.import_module("proplex.__main__")
    captured: dict[str, Any] = {}

    def fail_key_validation(**_kwargs: Any) -> list[str]:
        raise AssertionError("query plan status must not validate model keys")

    def fake_status(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return type("FakeResult", (), {"return_code": 0, "output": "fake plan"})()

    monkeypatch.setattr(cli, "_build_logger", lambda _verbose: None)
    monkeypatch.setattr(cli, "missing_required_api_keys", fail_key_validation)
    monkeypatch.setattr(cli, "build_generic_query_plan_status_output", fake_status)

    rc = cli.main([MVP_QUERY_PLAN_STATUS_FLAG, "--query", SMALL_CLAIMS_QUERY])

    assert rc == 0
    assert captured["query"] == SMALL_CLAIMS_QUERY
    assert "fake plan" in capsys.readouterr().out


def test_existing_mvp_status_flags_remain_registered() -> None:
    assert MVP_DEMO_FLAG in PRODUCT_STATUS_DRY_RUN_FLAGS
    assert MVP_LIVE_DOGFOOD_RUN_FLAG in PRODUCT_STATUS_DRY_RUN_FLAGS
    assert MVP_LIVE_DOGFOOD_STATUS_FLAG in PRODUCT_STATUS_DRY_RUN_FLAGS
    assert MVP_QUERY_PLAN_STATUS_FLAG in PRODUCT_STATUS_DRY_RUN_FLAGS


def test_planning_module_has_no_live_or_model_call_surface() -> None:
    imported, called = _module_static_shape(MODULE_PATH)
    forbidden_imports = {
        "dotenv",
        "openai",
        "requests",
        "httpx",
        "subprocess",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "proplex.mvp_live_dogfood_run",
    }
    forbidden_calls = {
        "ask_model",
        "dispatch_retrieval",
        "fetch_page",
        "fetch_public_url_once",
        "fetch_url",
        "process_search_queries",
        "read_url",
        "retrieve",
        "run_dprime_model_review_assessment",
        "run_pipeline",
        "run_provider_proxy_helper_once",
        "search_web",
    }

    assert imported.isdisjoint(forbidden_imports)
    assert called.isdisjoint(forbidden_calls)


def _load_packet(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def _single_cli_packet(output_subdir: str) -> dict[str, Any]:
    packets = list((ROOT / output_subdir).glob(f"*/{MVP_QUERY_PLAN_PACKET_NAME}"))
    assert len(packets) == 1
    return _load_packet(packets[0])


def _no_key_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "BRAVE_API_KEY",
        "TAVILY_API_KEY",
        "LINKUP_API_KEY",
        "EXA_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        env.pop(key, None)
    env["PYTHON_DOTENV_DISABLED"] = "1"
    return env


def _module_static_shape(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    return imported, called
