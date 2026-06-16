from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ag96i3e_brokered_provider_neutral_discovery_validation.py"


def test_runner_refuses_live_provider_without_confirmation(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner_module()

    result = runner.main(
        [
            "--provider",
            "brave",
            "--query",
            "official current discovery",
            "--job-id",
            "ag96i3e-brave-discovery-once",
            "--output",
            "output/ag96i3e_missing_confirmation.json",
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "--confirm-live-provider-call" in captured.err
    assert runner.LIVE_SPEND_WARNING not in captured.out


def test_runner_refuses_unsupported_provider(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner_module()

    result = runner.main(
        [
            "--provider",
            "exa",
            "--query",
            "official current discovery",
            "--job-id",
            "ag96i3e-exa-discovery-once",
            "--output",
            "output/ag96i3e_exa.json",
            "--confirm-live-provider-call",
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "refusing unsupported provider surface" in captured.err
    assert "search_and_contents" in captured.err


def test_runner_refuses_output_outside_ignored_output(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner_module()

    result = runner.main(
        [
            "--provider",
            "fixture",
            "--query",
            "offline fixture official current discovery smoke",
            "--job-id",
            "ag96i3e-offline-fixture-smoke",
            "--output",
            str(ROOT / "docs" / "ag96i3e_packet.json"),
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "outside ignored repo output/" in captured.err


def test_runner_refuses_max_results_below_one(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner_module()

    result = runner.main(
        [
            "--provider",
            "fixture",
            "--query",
            "offline fixture official current discovery smoke",
            "--job-id",
            "ag96i3e-offline-fixture-smoke",
            "--output",
            "output/ag96i3e_fixture_zero_max_results.json",
            "--max-results",
            "0",
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "below 1" in captured.err


def test_live_provider_refuses_max_results_over_cap_before_config_or_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _load_runner_module()

    monkeypatch.setattr(
        runner,
        "_provider_config_available",
        lambda _provider: pytest.fail("max-results cap must be checked first"),
    )
    monkeypatch.setattr(
        runner,
        "_dispatch_provider",
        lambda *_args, **_kwargs: pytest.fail("over-cap request must not dispatch"),
    )

    result = runner.main(
        [
            "--provider",
            "brave",
            "--query",
            "official current discovery",
            "--job-id",
            "ag96i3e-brave-discovery-once",
            "--output",
            "output/ag96i3e_over_cap.json",
            "--max-results",
            str(runner.MAX_RESULTS_LIMIT + 1),
            "--confirm-live-provider-call",
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert f"above {runner.MAX_RESULTS_LIMIT}" in captured.err
    assert runner.LIVE_SPEND_WARNING not in captured.out


def test_fixture_mode_respects_max_results_cap(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner_module()

    result = runner.main(
        [
            "--provider",
            "fixture",
            "--query",
            "offline fixture official current discovery smoke",
            "--job-id",
            "ag96i3e-offline-fixture-smoke",
            "--output",
            "output/ag96i3e_fixture_over_cap.json",
            "--max-results",
            str(runner.MAX_RESULTS_LIMIT + 1),
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert f"above {runner.MAX_RESULTS_LIMIT}" in captured.err


def test_fixture_cli_smoke_writes_same_sanitized_packet_shape(tmp_path: Path) -> None:
    output_relative = f"output/ag96i3e_offline_fixture_smoke_{tmp_path.name}.json"
    output_path = ROOT / output_relative
    if output_path.exists():
        output_path.unlink()
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--provider",
                "fixture",
                "--query",
                "offline fixture official current discovery smoke",
                "--job-id",
                "ag96i3e-offline-fixture-smoke",
                "--output",
                output_relative,
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "This command may spend exactly one live provider/search call" not in result.stdout
        packet = json.loads(output_path.read_text(encoding="utf-8"))
        _assert_ag96i3e_packet_shape(packet, provider="fixture")
        assert packet["live_validation_run"] is False
        assert packet["fixture_mode"] is True
        assert packet["provider_search_call_count"] == 0
        assert packet["fetch_read_attempt_count"] == 0
        assert packet["model_call_count"] == 0
        assert packet["author_executor_call_count"] == 0
        diagnostics = packet["provider_result_set_diagnostics"]
        assert diagnostics["selected_candidate_rank"] == 2
        assert diagnostics["selected_candidate_domain"] == "ftc.gov"
        assert diagnostics["bridge_only"] is False
    finally:
        if output_path.exists():
            output_path.unlink()


def test_fixture_mode_requires_no_provider_config_or_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner_module()

    monkeypatch.setattr(
        runner,
        "_provider_config_available",
        lambda _provider: pytest.fail("fixture mode must not check provider config"),
    )
    monkeypatch.setattr(
        runner,
        "_dispatch_provider",
        lambda *_args, **_kwargs: pytest.fail("fixture mode must not call provider"),
    )

    packet = runner.build_validation_packet(
        provider="fixture",
        query="offline fixture official current discovery smoke",
        job_id="ag96i3e-offline-fixture-smoke",
        max_results=5,
        raw_results=runner._fixture_results(),
        provider_search_call_count=0,
        fixture_mode=True,
    )

    assert packet["fixture_mode"] is True
    assert packet["provider_search_call_count"] == 0


def test_live_provider_missing_config_exits_before_warning(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _load_runner_module()

    monkeypatch.setattr(runner, "_provider_config_available", lambda _provider: False)
    monkeypatch.setattr(
        runner,
        "_dispatch_provider",
        lambda *_args, **_kwargs: pytest.fail("missing config must not dispatch"),
    )

    result = runner.main(
        [
            "--provider",
            "brave",
            "--query",
            "official current discovery",
            "--job-id",
            "ag96i3e-brave-discovery-once",
            "--output",
            "output/ag96i3e_missing_config.json",
            "--confirm-live-provider-call",
        ]
    )
    captured = capsys.readouterr()

    assert result == 3
    assert "provider config is missing" in captured.err
    assert runner.LIVE_SPEND_WARNING not in captured.out


@pytest.mark.parametrize(
    ("provider", "raw_results", "selected_domain"),
    [
        (
            "brave",
            [
                {
                    "title": "Bridge explanation",
                    "url": "https://example.com/current-bridge",
                    "description": "raw brave description must be stripped",
                },
                {
                    "title": "SEC current official filing rule 2026",
                    "url": "https://www.sec.gov/rules/current-filing-rule-2026",
                    "snippet": "raw brave snippet must be stripped",
                },
            ],
            "sec.gov",
        ),
        (
            "tavily",
            [
                {
                    "title": "Vendor guide",
                    "url": "https://vendor.example/current-guide",
                    "content": "raw tavily content must be stripped",
                    "raw_content": "raw tavily body must be stripped",
                },
                {
                    "title": "FDA current official guidance 2026",
                    "url": "https://www.fda.gov/regulatory-information/current-guidance-2026",
                    "raw_content": "raw tavily official body must be stripped",
                },
            ],
            "fda.gov",
        ),
        (
            "linkup",
            [
                {
                    "name": "Consultant summary",
                    "url": "https://consultant.example/summary",
                    "content": "raw linkup content must be stripped",
                },
                {
                    "name": "DOL current official wage rule 2026",
                    "url": "https://www.dol.gov/agencies/whd/current-wage-rule-2026",
                    "content": "raw linkup official content must be stripped",
                },
            ],
            "dol.gov",
        ),
    ],
)
def test_mocked_provider_shapes_produce_same_diagnostic_schema(
    provider: str,
    raw_results: list[dict[str, Any]],
    selected_domain: str,
) -> None:
    runner = _load_runner_module()

    packet = runner.build_validation_packet(
        provider=provider,
        query="Find the current official rule for the fixture scenario.",
        job_id=f"ag96i3e-{provider}-discovery-once",
        max_results=5,
        raw_results=raw_results,
        provider_search_call_count=1,
    )

    _assert_ag96i3e_packet_shape(packet, provider=provider)
    diagnostics = packet["provider_result_set_diagnostics"]
    assert diagnostics["schema_version"] == (
        "ag96i3d_provider_neutral_result_set_diagnostics_v1"
    )
    assert diagnostics["selected_candidate_rank"] == 2
    assert diagnostics["selected_candidate_domain"] == selected_domain
    assert diagnostics["first_failure_layer"] == "none"
    assert diagnostics["bridge_only"] is False


def test_rank_one_secondary_rank_two_official_selects_official() -> None:
    runner = _load_runner_module()

    packet = runner.build_validation_packet(
        provider="brave",
        query="Find the current official rule for the fixture scenario.",
        job_id="ag96i3e-brave-discovery-once",
        max_results=5,
        raw_results=[
            {
                "title": "Secondary explanation",
                "url": "https://example.org/current-explainer",
            },
            {
                "title": "USCIS current official fee rule 2026",
                "url": "https://www.uscis.gov/forms/filing-fees/current-2026",
            },
        ],
        provider_search_call_count=1,
    )

    diagnostics = packet["provider_result_set_diagnostics"]
    assert diagnostics["selected_candidate_rank"] == 2
    assert diagnostics["selected_candidate_domain"] == "uscis.gov"
    assert diagnostics["bridge_only"] is False


def test_no_official_result_remains_bridge_only() -> None:
    runner = _load_runner_module()

    packet = runner.build_validation_packet(
        provider="linkup",
        query="Find the current official rule for the fixture scenario.",
        job_id="ag96i3e-linkup-discovery-once",
        max_results=5,
        raw_results=[
            {
                "name": "Vendor guide",
                "url": "https://vendor.example/current-guide",
                "content": "raw linkup content must be stripped",
            },
        ],
        provider_search_call_count=1,
    )

    diagnostics = packet["provider_result_set_diagnostics"]
    assert diagnostics["selected_candidate_rank"] is None
    assert diagnostics["bridge_only"] is True
    assert diagnostics["selected_candidate_reason"] == (
        "provider_result_set_lacked_official_current_candidate"
    )


def test_raw_snippets_content_and_payload_placeholders_are_stripped() -> None:
    runner = _load_runner_module()

    packet = runner.build_validation_packet(
        provider="tavily",
        query="Find the current official rule for the fixture scenario.",
        job_id="ag96i3e-tavily-discovery-once",
        max_results=5,
        raw_results=[
            {
                "title": "FDA current official guidance 2026",
                "url": "https://www.fda.gov/regulatory-information/current-guidance-2026",
                "snippet": "raw snippet blocked marker",
                "content": "raw content blocked marker",
                "raw_content": "raw body blocked marker",
                "text": "raw text blocked marker",
                "payload": {"raw_payload": "blocked payload marker"},
            },
        ],
        provider_search_call_count=1,
    )

    serialized = json.dumps(packet, sort_keys=True)
    for forbidden in (
        "raw snippet blocked marker",
        "raw content blocked marker",
        "raw body blocked marker",
        "raw text blocked marker",
        "blocked payload marker",
    ):
        assert forbidden not in serialized


def test_discovery_unconstrained_rejects_domain_constraints_if_internal_api_is_misused() -> None:
    runner = _load_runner_module()

    with pytest.raises(ValueError, match="forbids include/domain constraints"):
        runner.build_validation_packet(
            provider="brave",
            query="Find the current official rule for the fixture scenario.",
            job_id="ag96i3e-brave-discovery-once",
            max_results=5,
            raw_results=[],
            provider_search_call_count=1,
            include_domains=["irs.gov"],
        )


def test_provider_call_budget_cannot_exceed_one() -> None:
    runner = _load_runner_module()
    budget = runner.ProviderCallBudget()

    budget.mark_provider_search_call()
    with pytest.raises(RuntimeError, match="provider search call budget exceeded"):
        budget.mark_provider_search_call()


def test_closed_surface_counts_and_flags_stay_zero() -> None:
    runner = _load_runner_module()

    packet = runner.build_validation_packet(
        provider="fixture",
        query="offline fixture official current discovery smoke",
        job_id="ag96i3e-offline-fixture-smoke",
        max_results=5,
        raw_results=runner._fixture_results(),
        provider_search_call_count=0,
        fixture_mode=True,
    )

    assert packet["fetch_read_attempt_count"] == 0
    assert packet["model_call_count"] == 0
    assert packet["author_executor_call_count"] == 0
    flags = packet["closed_surface_flags"]
    assert flags["fetch_read_invoked"] is False
    assert flags["model_called"] is False
    assert flags["author_executor_invoked"] is False
    assert flags["citation_behavior_changed"] is False
    assert flags["product_answer_behavior_changed"] is False


def test_static_guard_no_pipeline_orchestrator_domain_logic_or_irs_branching() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    imports = _imports(SCRIPT)
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.author_execution_runtime",
        "core.followup_final_answer_packet_runtime",
        "core.citation_source_handoff_contract",
        "openai",
        "dotenv",
    }
    assert imports.isdisjoint(forbidden_imports)
    for forbidden in (
        "includeDomains",
        "include_domains=[\"irs.gov\"]",
        "irs.gov",
        "AuthorExecutor",
        "FinalAnswerPacket",
        "format_citation",
        "load_dotenv",
        "dotenv_values",
    ):
        assert forbidden not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3e_brokered_provider_neutral_discovery_validation" not in pipeline_source
    assert "provider_result_set_lacked_official_current_candidate" not in pipeline_source


def _assert_ag96i3e_packet_shape(packet: dict[str, Any], *, provider: str) -> None:
    assert packet["schema_version"] == (
        "ag96i3e_brokered_provider_neutral_discovery_validation_v1"
    )
    assert packet["phase_id"] == "AG-96I3E"
    assert packet["provider"] == provider
    assert packet["live_budget"] == {
        "max_provider_search_calls": 1,
        "max_results_limit": 10,
        "max_fetch_read_attempts": 0,
        "max_model_calls": 0,
        "max_author_executor_calls": 0,
        "retries_allowed": False,
    }
    assert packet["provider_result_set_diagnostics"]["record_type"] == (
        "provider_neutral_official_current_result_set_diagnostics"
    )
    assert packet["provider_result_set_diagnostics"]["domain_constraint_status"] == (
        "not_present"
    )
    assert packet["provider_result_set_diagnostics"]["authority_decision_present"] is False
    assert packet["evidence_boundary"]["selected_candidates_are_final_evidence"] is False
    assert packet["evidence_boundary"]["selected_candidates_are_citation_eligible"] is False


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _load_runner_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "ag96i3e_brokered_provider_neutral_discovery_validation",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
