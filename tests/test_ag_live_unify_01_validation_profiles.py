from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.cap_enforcement import RunCapPolicy
from core.search_work_query_shape_runtime import _assess_structured_multicomponent_shape
from core.validation_profiles import (
    AG_LIVE_DISAMBIG,
    AG_LIVE_MULTI_COMPONENT,
    AG_LIVE_N2_PRODUCT_FRONTIER_Q1,
    AG_LIVE_N2_PRODUCT_FRONTIER_Q2,
    AG_LIVE_N2_Q1_SUBJECT_BUDGET,
    AG_LIVE_N2_Q1_TWO_OFFICIAL_SOURCES_LENGTH,
    AG_LIVE_N2_Q2_SHARED_OFFICIAL_SOURCE_DATES,
    AG_LIVE_N2_Q2_SUBJECT_BUDGET,
    AG_LIVE_S1_PRODUCT_CONVERGENCE,
    AG_LIVE_SMOKE,
    AG_LIVE_SOURCE_CUSTODY,
    BROKER_PRIVATE_ADAPTER,
    DIRECT_HUMAN_PRIVATE_SHELL,
    MAX_INITIAL_SELECTED_SUBJECTS,
    MULTI_COMPONENT_DOCS_DOMAINS,
    N2_Q1_OFFICIAL_DOMAINS,
    N2_Q1_TWO_OFFICIAL_SOURCES_LENGTH,
    N2_Q2_OFFICIAL_DOMAINS,
    N2_Q2_SHARED_OFFICIAL_SOURCE_DATES,
    VALIDATION_PROFILES,
    get_validation_profile,
    validation_profile_names,
)
from scripts import ag_live_bound_01_support as support
from scripts import request_live_validation_broker as broker_client

ROOT = Path(__file__).resolve().parents[1]


def test_profile_registry_contains_required_ag_live_profiles() -> None:
    assert set(VALIDATION_PROFILES) == {
        AG_LIVE_SMOKE,
        AG_LIVE_SOURCE_CUSTODY,
        AG_LIVE_MULTI_COMPONENT,
        AG_LIVE_DISAMBIG,
        AG_LIVE_S1_PRODUCT_CONVERGENCE,
        AG_LIVE_N2_PRODUCT_FRONTIER_Q1,
        AG_LIVE_N2_PRODUCT_FRONTIER_Q2,
    }
    for profile in VALIDATION_PROFILES.values():
        assert profile.purpose
        assert profile.proof_target
        if profile.name == AG_LIVE_SOURCE_CUSTODY:
            assert profile.allowed_invocation_modes == ()
        else:
            assert profile.allowed_invocation_modes
        assert profile.cap_policy.as_requested_dict()
        assert profile.expected_packet_criteria
        assert profile.live_status in {
            "succeeded_once_direct_human_private_shell",
            "not_run",
            "retired_non_executable",
        }
        assert profile.packet_schema == "ag_live_bound_01_bounded_product_runner_v1"
        assert profile.cap_policy_surface == "RunConfig.cap_policy"
        assert profile.source_custody_policy_surface == (
            "ValidationProfile.source_custody_policy_non_executable_expectation"
        )


def test_ag_live_smoke_maps_to_direct_human_runner_behavior() -> None:
    profile = get_validation_profile(AG_LIVE_SMOKE)
    assert profile.supports_direct_runner()
    assert DIRECT_HUMAN_PRIVATE_SHELL in profile.allowed_invocation_modes
    assert BROKER_PRIVATE_ADAPTER in profile.allowed_invocation_modes
    assert profile.primary_query == support.PRIMARY_QUERY
    assert profile.backup_query == support.BACKUP_QUERY
    assert profile.required_mode == support.REQUIRED_MODE
    assert tuple(profile.required_include_domains) == (support.REQUIRED_DOMAIN,)
    assert profile.cap_policy.as_requested_dict() == support.PLANNED_CAPS
    assert profile.cap_policy.as_requested_dict() == {
        "max_scryraven_runs": 1,
        "max_retries": 0,
    }
    assert profile.cap_policy.max_search_dispatches is None
    assert profile.cap_policy.max_fetch_read_operations is None
    assert profile.cap_policy.max_author_model_calls is None
    assert profile.cap_policy.max_smart_search_judgment_model_calls is None
    assert profile.cap_policy.max_retries == 0
    compatibility_policy = profile.cap_policy.to_run_cap_policy()
    default_policy = RunCapPolicy()
    assert compatibility_policy.max_search_dispatches == (
        default_policy.max_search_dispatches
    )
    assert compatibility_policy.max_fetch_read_operations == (
        default_policy.max_fetch_read_operations
    )
    assert compatibility_policy.max_author_model_calls == (
        default_policy.max_author_model_calls
    )
    assert compatibility_policy.max_smart_search_judgment_model_calls == (
        default_policy.max_smart_search_judgment_model_calls
    )
    assert compatibility_policy.max_retries == 0
    assert profile.current_evidence.startswith("Succeeded once")


def test_cap_requests_match_selected_profile_authority_exactly() -> None:
    smoke = get_validation_profile(AG_LIVE_SMOKE)
    smoke_caps = smoke.cap_policy.as_requested_dict()
    assert support.validate_caps_requested(
        smoke_caps,
        profile_name=AG_LIVE_SMOKE,
    ).as_requested_dict() == smoke_caps

    with pytest.raises(
        support.AgLiveBoundPreflightError,
        match="not declared by selected profile",
    ):
        support.validate_caps_requested(
            {
                **smoke_caps,
                "max_smart_search_judgment_model_calls": 2,
            },
            profile_name=AG_LIVE_SMOKE,
        )

    convergence = get_validation_profile(AG_LIVE_S1_PRODUCT_CONVERGENCE)
    convergence_caps = convergence.cap_policy.as_requested_dict()
    accepted = support.validate_caps_requested(
        convergence_caps,
        profile_name=AG_LIVE_S1_PRODUCT_CONVERGENCE,
    )
    assert accepted.as_requested_dict() == convergence_caps
    assert accepted.to_run_cap_policy().max_search_dispatches == (
        convergence.cap_policy.max_search_dispatches
    )
    assert accepted.to_run_cap_policy().max_fetch_read_operations == (
        convergence.cap_policy.max_fetch_read_operations
    )
    assert accepted.to_run_cap_policy().max_author_model_calls == (
        convergence.cap_policy.max_author_model_calls
    )
    assert accepted.to_run_cap_policy().max_smart_search_judgment_model_calls == (
        convergence.cap_policy.max_smart_search_judgment_model_calls
    )


def test_future_profiles_and_retired_source_custody_are_not_live_proof() -> None:
    assert get_validation_profile(AG_LIVE_S1_PRODUCT_CONVERGENCE).live_status == "not_run"
    assert get_validation_profile(AG_LIVE_MULTI_COMPONENT).live_status == "not_run"
    assert get_validation_profile(AG_LIVE_DISAMBIG).live_status == "not_run"
    source_custody = get_validation_profile(AG_LIVE_SOURCE_CUSTODY)
    assert source_custody.live_status == "retired_non_executable"
    assert source_custody.supports_direct_runner() is False
    assert AG_LIVE_SOURCE_CUSTODY not in validation_profile_names()
    assert "historical expectation only" in source_custody.expected_packet_criteria
    assert source_custody.source_custody_policy is not None
    assert source_custody.source_custody_policy.as_requested_dict() == {
        "require_official_full_fetch_read": True,
        "max_forced_fetch_reads": 1,
        "preferred_domains": ["docs.python.org"],
        "required_source_class": "primary_source_documents",
        "required_source_tier": "official",
        "required_currentness": "current",
        "requirement_id": "ag-live-source-custody:official-doc-full-read",
        "required_evidence_material_type": "full_page_fetched",
        "admission_reason": "source_custody_policy_full_fetch_read",
    }
    multi_component = get_validation_profile(AG_LIVE_MULTI_COMPONENT)
    assert multi_component.primary_query is not None
    assert "PostgreSQL" in multi_component.primary_query
    assert "MongoDB" in multi_component.primary_query
    assert multi_component.required_include_domains == MULTI_COMPONENT_DOCS_DOMAINS
    assert multi_component.subject_budget is not None
    assert multi_component.subject_budget.as_requested_dict() == {
        "subject_budget_enabled": True,
        "max_initial_selected_subjects": MAX_INITIAL_SELECTED_SUBJECTS,
        "subject_budget_scope": "initial_independent_subjects_only",
        "applies_to_internal_followups": False,
        "same_source_evidence_allowed": False,
        "subject_selection_source": (
            "existing_component_order_or_existing_searchwork_order"
        ),
        "followup_budget_policy": (
            "internal_followups_governed_by_existing_mode_and_resource_caps"
        ),
        "policy_status": "planned_not_run_not_live_licensed",
    }
    assert any(
        "selected initial subjects/components are capped at up to five" in criterion
        for criterion in multi_component.expected_packet_criteria
    )
    disambig = get_validation_profile(AG_LIVE_DISAMBIG)
    assert any(
        "no provider bake-off" in criterion
        for criterion in disambig.expected_packet_criteria
    )


@pytest.mark.parametrize(
    ("profile_name", "query_id", "query", "domains", "subject_budget"),
    (
        (
            AG_LIVE_N2_PRODUCT_FRONTIER_Q1,
            N2_Q1_TWO_OFFICIAL_SOURCES_LENGTH,
            AG_LIVE_N2_Q1_TWO_OFFICIAL_SOURCES_LENGTH,
            N2_Q1_OFFICIAL_DOMAINS,
            AG_LIVE_N2_Q1_SUBJECT_BUDGET,
        ),
        (
            AG_LIVE_N2_PRODUCT_FRONTIER_Q2,
            N2_Q2_SHARED_OFFICIAL_SOURCE_DATES,
            AG_LIVE_N2_Q2_SHARED_OFFICIAL_SOURCE_DATES,
            N2_Q2_OFFICIAL_DOMAINS,
            AG_LIVE_N2_Q2_SUBJECT_BUDGET,
        ),
    ),
)
def test_n2_frontier_profiles_register_exact_queries_and_offline_shape(
    profile_name: str,
    query_id: str,
    query: str,
    domains: tuple[str, ...],
    subject_budget: object,
) -> None:
    profile = get_validation_profile(profile_name)

    assert profile.fixed_queries == ((query_id, query),)
    assert profile.required_include_domains == domains
    assert profile.cap_policy.as_requested_dict() == {
        "max_scryraven_runs": 1,
        "max_retries": 0,
    }
    assert profile.subject_budget == subject_budget
    assert profile.subject_budget is not None
    assert profile.subject_budget.max_initial_selected_subjects == 2

    shape = _assess_structured_multicomponent_shape(query)
    assert shape.posture.value == "QUALIFIED"
    assert shape.syntax_kind == "numbered_imperative"
    assert len(shape.component_items) == 2
    assert shape.requested_synthesis_directive is not None
    assert shape.requested_synthesis_directive.startswith("Then compare")

    context = support.build_preflight_context(
        root=ROOT,
        profile_name=profile_name,
        query=query,
        mode="Balanced",
        include_domains=list(domains),
        output_path=ROOT / "output" / f"{query_id}.sanitized.json",
        caps=support.AgLiveBoundCaps(),
        run_id=f"{query_id}-dry-run",
        confirm_live_product_run=False,
        approved_backup_query=False,
        requested_query_id=query_id,
    )
    packet = support.build_dry_run_packet(context)

    assert packet["preflight"]["query_lock"] == query_id
    assert packet["domain_allowlist"] == list(domains)
    assert packet["subject_budget_summary"]["max_initial_selected_subjects"] == 2
    support.reject_forbidden_packet(packet)


def test_runner_context_and_packet_include_profile_cap_and_schema() -> None:
    context = support.build_preflight_context(
        root=ROOT,
        profile_name=AG_LIVE_SMOKE,
        query=support.PRIMARY_QUERY,
        mode=support.REQUIRED_MODE,
        include_domains=[support.REQUIRED_DOMAIN],
        output_path=ROOT / "output" / "ag_live_unify_01_packet.json",
        caps=support.AgLiveBoundCaps(),
        run_id="ag-live-unify-test",
        confirm_live_product_run=False,
        approved_backup_query=False,
    )

    packet = support.build_dry_run_packet(context)

    assert packet["validation_profile"]["name"] == AG_LIVE_SMOKE
    assert packet["validation_profile"]["runtime_consumer"] == "run_pipeline"
    assert packet["caps_requested"] == get_validation_profile(
        AG_LIVE_SMOKE
    ).cap_policy.as_requested_dict()
    assert packet["subject_budget_summary"]["subject_budget_enabled"] is False
    support.reject_forbidden_packet(packet)


def test_direct_runner_refuses_profile_without_exact_query() -> None:
    with pytest.raises(support.AgLiveBoundPreflightError, match="not direct-runner"):
        support.build_preflight_context(
            root=ROOT,
            profile_name=AG_LIVE_DISAMBIG,
            query="Which Mercury is meant?",
            mode=support.REQUIRED_MODE,
            include_domains=[],
            output_path=ROOT / "output" / "ag_live_unify_01_disambig.json",
            caps=support.AgLiveBoundCaps(),
            run_id="ag-live-disambig-test",
            confirm_live_product_run=False,
            approved_backup_query=False,
        )


def test_broker_profile_request_uses_registry_without_arbitrary_command() -> None:
    assert broker_client.main(
        ["--job-id", "ag-live-smoke-once", "--profile", AG_LIVE_SMOKE]
    ) == 2
    source = (ROOT / "scripts" / "request_live_validation_broker.py").read_text(
        encoding="utf-8"
    )
    assert "_build_profile_request_payload" not in source
    assert "get_validation_profile" not in source
    assert "urlopen" not in source
    assert "subprocess" not in source


def test_source_custody_broker_profile_request_includes_policy_surface() -> None:
    assert broker_client.main(
        ["--job-id", "ag-live-source-custody", "--profile", AG_LIVE_SOURCE_CUSTODY]
    ) == 2
    product_path = support.source_custody_policy_product_path(
        AG_LIVE_SOURCE_CUSTODY
    )
    assert product_path["policy_enabled"] is False
    assert product_path["product_policy_constructible"] is False
    assert product_path["initial_discovery_transport_authority"] is False


def test_broker_client_static_boundary_has_no_dotenv_or_provider_imports() -> None:
    source = (ROOT / "scripts" / "request_live_validation_broker.py").read_text(
        encoding="utf-8"
    )
    imported = _imports(ROOT / "scripts" / "request_live_validation_broker.py")
    assert "dotenv" not in imported
    assert "core.pipeline_orchestrator" not in imported
    assert "load_dotenv" not in source
    assert "dotenv_values" not in source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
