from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.validation_profiles import (
    AG_LIVE_DISAMBIG,
    AG_LIVE_MULTI_COMPONENT,
    AG_LIVE_SMOKE,
    AG_LIVE_SOURCE_CUSTODY,
    BROKER_PRIVATE_ADAPTER,
    DIRECT_HUMAN_PRIVATE_SHELL,
    VALIDATION_PROFILES,
    get_validation_profile,
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
    }
    for profile in VALIDATION_PROFILES.values():
        assert profile.purpose
        assert profile.proof_target
        assert profile.allowed_invocation_modes
        assert profile.cap_policy.as_requested_dict()
        assert profile.expected_packet_criteria
        assert profile.live_status in {
            "succeeded_once_direct_human_private_shell",
            "not_run",
        }
        assert profile.packet_schema == "ag_live_bound_01_bounded_product_runner_v1"
        assert profile.cap_policy_surface == "RunConfig.cap_policy"


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
    assert profile.current_evidence.startswith("Succeeded once")


def test_future_profiles_are_not_marked_as_live_proof() -> None:
    assert get_validation_profile(AG_LIVE_SOURCE_CUSTODY).live_status == "not_run"
    assert get_validation_profile(AG_LIVE_MULTI_COMPONENT).live_status == "not_run"
    assert get_validation_profile(AG_LIVE_DISAMBIG).live_status == "not_run"
    source_custody = get_validation_profile(AG_LIVE_SOURCE_CUSTODY)
    assert "fetch_read_operations > 0" in source_custody.expected_packet_criteria
    multi_component = get_validation_profile(AG_LIVE_MULTI_COMPONENT)
    assert any(
        "both answer components" in criterion
        for criterion in multi_component.expected_packet_criteria
    )
    disambig = get_validation_profile(AG_LIVE_DISAMBIG)
    assert any(
        "no provider bake-off" in criterion
        for criterion in disambig.expected_packet_criteria
    )


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
    payload = broker_client._build_profile_request_payload(
        "ag-live-smoke-once",
        AG_LIVE_SMOKE,
    )

    assert payload["job_id"] == "ag-live-smoke-once"
    assert payload["confirm_live"] is True
    assert payload["request_kind"] == "approved_validation_profile"
    profile_request = payload["profile_request"]
    assert profile_request["validation_profile"] == AG_LIVE_SMOKE
    assert profile_request["cap_policy"]["surface"] == "RunConfig.cap_policy"
    assert profile_request["cap_policy"]["values"] == get_validation_profile(
        AG_LIVE_SMOKE
    ).cap_policy.as_requested_dict()
    assert "command" not in json.dumps(payload).casefold()
    assert "dotenv" not in json.dumps(payload).casefold()


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
