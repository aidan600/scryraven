from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import ag_fixture_dogfood_integration_01 as dogfood  # noqa: E402

PHASE = "AG-LOCAL-DRYRUN-QUERY-TO-AUTHORPROSE-01"
PROOF_CLASS = "offline product-path dry-run proof plus phase-focused integration tests"
PRODUCT_PROGRESS_TYPE = "ordinary-query dry-run product-path integration"
PRODUCT_PATH_AFFECTED = (
    "local offline dry-run path only; no live installed product behavior yet"
)
DEFAULT_OUTPUT_DIR = ROOT / "output" / "ag_local_dryrun_query_to_authorprose_01"
DEFAULT_QUERY = "What is the official current permit threshold for the example program?"
MANDATORY_NEXT_CHECKPOINT = (
    "tightly scoped limited live validation phase only if this ordinary-query "
    "dry-run is honest and reviewable"
)
OLD_PATH_TREATMENT = (
    "Old Author/FAP/follow-up/sufficiency/AG-89D/AG-91K/AG-92C/AG-96/"
    "pipeline/offline bridge surfaces remain legacy/passive/historical or closed."
)
EXPLICIT_NON_PROOFS = [
    "live provider, broker, model, search, fetch/read, or retrieval calls",
    "real source acquisition quality",
    "real-source fetch/read survival",
    "messy-live-evidence semantic support",
    "citation rendering",
    "citation eligibility in user-visible output",
    "source-obligation satisfaction",
    "installed product behavior",
    "product correctness",
    "product-quality Author prose",
    "natural-language query understanding by a model",
]

SCENARIO_ALIASES = {
    "full_supported": "01_full_supported",
    "01_full_supported": "01_full_supported",
    "partial_unresolved": "02_partial_unresolved",
    "partial": "02_partial_unresolved",
    "02_partial_unresolved": "02_partial_unresolved",
    "contested_weak": "03_contested_weak_evidence",
    "contested": "03_contested_weak_evidence",
    "03_contested_weak_evidence": "03_contested_weak_evidence",
}


class LocalDryRunError(ValueError):
    """Raised when ordinary-query dry-run packet generation is unsafe."""


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    scenario_id: str
    cli_name: str
    title: str
    scenario_kind: str
    description: str
    include_optional_context_component: bool = False
    full_supported_specialist_and_scrutineer: bool = False
    contested_specialist: bool = False
    author_policy: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class GeneratedDryRunPacket:
    scenario_id: str
    json_path: Path
    markdown_path: Path
    packet: dict[str, Any]


SCENARIOS = {
    "01_full_supported": ScenarioSpec(
        scenario_id="01_full_supported",
        cli_name="full_supported",
        title="Full Supported Query",
        scenario_kind="full_supported",
        description=(
            "A user-style query enters SearchPlanner, receives deterministic "
            "offline support, and reaches full-ready hardened FAP plus "
            "AuthorProse."
        ),
        full_supported_specialist_and_scrutineer=True,
    ),
    "02_partial_unresolved": ScenarioSpec(
        scenario_id="02_partial_unresolved",
        cli_name="partial_unresolved",
        title="Partial Unresolved Query",
        scenario_kind="partial_or_unresolved",
        description=(
            "A user-style query enters SearchPlanner with an optional context "
            "component before initial contract acceptance; only the primary "
            "component receives deterministic offline support."
        ),
        include_optional_context_component=True,
    ),
    "03_contested_weak_evidence": ScenarioSpec(
        scenario_id="03_contested_weak_evidence",
        cli_name="contested_weak",
        title="Contested Weak Query",
        scenario_kind="contested_weak_or_conflicting",
        description=(
            "A user-style query receives deterministic offline candidate/"
            "content custody, but weak or stale Specialist posture preserves a "
            "contested answer through FAP and AuthorProse."
        ),
        contested_specialist=True,
        author_policy={"uncertainty_profile": "contested_first"},
    ),
}


def generate_query_dry_run_packets(
    *,
    query: str,
    scenario: str = "all",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> list[GeneratedDryRunPacket]:
    user_query = _normalize_query(query)
    selected = _selected_scenarios(scenario)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    generated: list[GeneratedDryRunPacket] = []
    stable_query_digest = _ordinary_query_digest(user_query)
    for spec in selected:
        packet = _build_scenario_packet(
            query=user_query,
            stable_query_digest=stable_query_digest,
            spec=spec,
        )
        filename = f"{stable_query_digest[:12]}_{spec.scenario_id}"
        json_path = target / f"{filename}.json"
        markdown_path = target / f"{filename}.md"
        dogfood._write_json(json_path, packet)
        markdown_path.write_text(_packet_markdown(packet), encoding="utf-8")
        generated.append(
            GeneratedDryRunPacket(
                scenario_id=spec.scenario_id,
                json_path=json_path,
                markdown_path=markdown_path,
                packet=packet,
            )
        )

    index = _index_packet(
        query=user_query,
        stable_query_digest=stable_query_digest,
        generated=generated,
    )
    dogfood._write_json(target / "index.json", index)
    (target / "index.md").write_text(_index_markdown(index), encoding="utf-8")
    return generated


def _build_scenario_packet(
    *,
    query: str,
    stable_query_digest: str,
    spec: ScenarioSpec,
) -> dict[str, Any]:
    chain = dogfood._supported_chain_with_candidate_packet(
        include_optional_context_component=spec.include_optional_context_component,
        user_query_text=query,
        run_id=_run_id(stable_query_digest, spec.scenario_id),
        request_id=_request_id(stable_query_digest, spec.scenario_id),
        phase=PHASE,
        proof_class=PROOF_CLASS,
        query_class="ordinary user-style query local dry-run",
        front_half_source="ordinary_query_local_dryrun_via_fixture_dogfood_helpers",
        route_ref=f"{PHASE}:{spec.scenario_id}:route",
        run_ref=f"{PHASE}:{spec.scenario_id}:run",
    )
    kernel = chain["kernel"]

    if spec.full_supported_specialist_and_scrutineer:
        dogfood._reduce_specialist_success(chain)
        dogfood._reduce_scrutineer(
            chain,
            red_flag_context=True,
            specialist_source_bound_calculation_projection=(
                kernel.state.specialist_source_bound_calculation_projection
            ),
            specialist_source_bound_calculation_history=(
                kernel.state.specialist_source_bound_calculation_history
            ),
        )
    if spec.contested_specialist:
        contested = dogfood._specialist_record(
            chain,
            calculation_kind="sum",
            inputs=[
                dogfood._specialist_input(chain, label="current", value=10),
                dogfood._specialist_input(
                    chain,
                    label="stale",
                    value=15,
                    currentness="unknown",
                    source_class="weak_secondary",
                ),
            ],
        )
        dogfood.reduce_specialist_source_bound_calculation(
            run_kernel=kernel,
            specialist_source_bound_calculation_record=contested,
        )

    dogfood._reduce_readiness_fap_author(
        kernel,
        author_policy=spec.author_policy,
    )
    return _review_packet(
        query=query,
        stable_query_digest=stable_query_digest,
        spec=spec,
        chain=chain,
    )


def _review_packet(
    *,
    query: str,
    stable_query_digest: str,
    spec: ScenarioSpec,
    chain: Mapping[str, Any],
) -> dict[str, Any]:
    kernel = chain["kernel"]
    readiness = dict(kernel.state.sufficiency_readiness_projection)
    fap = dict(kernel.state.final_answer_authority_projection)
    author = dict(kernel.state.author_prose_projection)
    planner_state = dict(kernel.state.search_planner_proposal_state)
    packet = {
        "phase": PHASE,
        "proof_class": PROOF_CLASS,
        "product_facing_progress_type": PRODUCT_PROGRESS_TYPE,
        "product_path_affected": PRODUCT_PATH_AFFECTED,
        "actual_app_delta": (
            "ScryRaven gains a local offline command that accepts an ordinary "
            "user-style query and produces reviewable JSON/Markdown "
            "AuthorProse packets through existing current-path machinery."
        ),
        "user_facing_reviewable_output_delta": (
            "A reviewer can inspect query refs, deterministic offline provider "
            "posture, current-path packet custody, SufficiencyReadiness, "
            "hardened FAP, and AuthorProse output."
        ),
        "runtime_consumer": (
            "existing current-path reducers/builders/runtimes through "
            "AuthorProseFinalization"
        ),
        "actual_consumer_seam": (
            "SearchPlanner user-query input -> initial/current contract -> "
            "SearchExecutorHandoff -> candidate/read/custody/analysis/"
            "admission/coverage -> SufficiencyReadiness -> hardened FAP -> "
            "AuthorProseFinalization"
        ),
        "original_user_query": query,
        "query_digest_ref": {
            "ordinary_query_ref": {
                "ref_kind": "ordinary_user_query_digest",
                "digest": stable_query_digest,
                "algorithm": "sha256(normalized query text only)",
            },
            "current_path_user_query_ref": planner_state.get("user_query_ref") or {},
        },
        "selected_scenario": {
            "scenario_id": spec.scenario_id,
            "cli_name": spec.cli_name,
            "scenario_kind": spec.scenario_kind,
            "title": spec.title,
            "description": spec.description,
            "mode": "Balanced",
            "run_id": kernel.state.run_id,
            "request_id": kernel.state.request_id,
        },
        "query_driven_inputs_and_refs": _query_driven_inputs(
            query=query,
            stable_query_digest=stable_query_digest,
            chain=chain,
            planner_state=planner_state,
        ),
        "deterministic_fixture_inheritance_reuse": {
            "runner_reused": "scripts/ag_fixture_dogfood_integration_01.py",
            "reused_current_path_chain": True,
            "reused_scenarios": (
                "supporting deterministic fixture materials and scenario "
                "postures are inherited; the incoming query, query digest, "
                "run id, request id, planner input, component question, and "
                "search requirement are ordinary-query driven."
            ),
            "newly_ordinary_query_driven_fields": [
                "original_user_query",
                "ordinary_query_digest",
                "SearchPlannerInput.user_query_text",
                "search_planner_proposal_state.user_query_ref",
                "answer component question",
                "component search requirement summary",
                "run_id",
                "request_id",
            ],
            "inherited_deterministic_fixture_fields": [
                "fake provider-result records",
                "sanitized readable content material",
                "Analyst support proposal fixture",
                "Specialist deterministic numeric posture",
                "Scrutineer deterministic review posture",
            ],
        },
        "fake_captured_provider_result_posture": _fake_provider_posture(kernel),
        "current_path_surfaces_consumed": dogfood._surface_consumption(
            chain,
            kernel,
        ),
        "candidate_content_custody_refs": dogfood._input_refs(chain),
        "component_coverage_summary": dogfood._coverage_summary(chain, readiness),
        "followup_scrutineer_specialist_posture": dogfood._review_specialist_posture(
            chain,
            kernel,
        ),
        "sufficiency_readiness_status": {
            "owner": readiness.get("owner"),
            "final_readiness_status": readiness.get("final_readiness_status"),
            "readiness_digest": readiness.get("readiness_digest"),
            "component_statuses": dogfood._component_statuses(readiness),
            "supported_component_refs": readiness.get("supported_component_refs")
            or [],
            "missing_component_refs": readiness.get("missing_component_refs") or [],
            "followup_required_component_refs": (
                readiness.get("followup_required_component_refs") or []
            ),
            "mandatory_caveats": readiness.get("mandatory_caveats") or [],
            "prohibited_upgrades": readiness.get("prohibited_upgrades") or [],
        },
        "hardened_final_answer_packet_status": {
            "owner": fap.get("owner"),
            "fap_status": fap.get("fap_status"),
            "packet_created": fap.get("packet_created"),
            "packet_id": fap.get("packet_id"),
            "packet_digest": fap.get("packet_digest"),
            "component_packet_entries": fap.get("component_packet_entries") or [],
            "mandatory_caveats": fap.get("mandatory_caveats") or [],
            "prohibited_upgrades": fap.get("prohibited_upgrades") or [],
        },
        "author_prose_output": {
            "owner": author.get("owner"),
            "author_prose_status": author.get("author_prose_status"),
            "fap_status": author.get("fap_status"),
            "answer_text": author.get("answer_text"),
            "answer_blocks": author.get("answer_blocks") or [],
            "supported_component_ids": author.get("supported_component_ids") or [],
            "unresolved_component_ids": author.get("unresolved_component_ids") or [],
            "must_not_answer_component_ids": (
                author.get("must_not_answer_component_ids") or []
            ),
            "source_ref_presentation": author.get("source_ref_presentation") or {},
            "mandatory_caveats": author.get("mandatory_caveats") or [],
            "prohibited_upgrades": author.get("prohibited_upgrades") or [],
            "prohibited_claims": author.get("prohibited_claims") or [],
        },
        "caveats_blockers_contested_posture": dogfood._caveat_blocker_posture(
            readiness,
            fap,
            author,
        ),
        "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
        "old_path_treatment": OLD_PATH_TREATMENT,
        "live_validation_status": (
            "not run and not licensed; fake/offline sanitized provider-result "
            "records only; no broker, live provider, model, URL fetch/read, "
            "retrieval, citation rendering, source-obligation satisfaction, "
            "or old Author execution"
        ),
        "mandatory_next_checkpoint": MANDATORY_NEXT_CHECKPOINT,
        "direct_state_mutation_avoided": True,
        "review_only_packaging_fields": [
            "phase/proof/product posture",
            "original_user_query retained for review packet inspection",
            "query-driven versus inherited-fixture classification",
            "explicit non-proofs",
            "old path treatment",
            "mandatory next checkpoint",
        ],
        "review_packet_theater_guard": {
            "review_packet_is_output_only": True,
            "manual_final_summary_assembly": False,
            "manual_author_prose_text": False,
            "actual_current_path_outputs_recorded": True,
            "core_surfaces_invoked": dogfood._invoked_surface_names(kernel),
            "old_author_runtime_called": (
                kernel.state.author_prose_projection.get("old_author_runtime_called")
            ),
            "pipeline_orchestrator_called": (
                kernel.state.author_prose_projection.get("pipeline_orchestrator_called")
            ),
        },
        "current_path_outputs": _current_path_outputs(chain, kernel),
    }
    return dogfood._json_safe(packet)


def _query_driven_inputs(
    *,
    query: str,
    stable_query_digest: str,
    chain: Mapping[str, Any],
    planner_state: Mapping[str, Any],
) -> dict[str, Any]:
    kernel = chain["kernel"]
    handoff = kernel.state.search_executor_handoff_state
    return {
        "original_user_query": query,
        "ordinary_query_digest": stable_query_digest,
        "search_planner_user_query_ref": planner_state.get("user_query_ref") or {},
        "question_meaning_summary": planner_state.get("question_meaning_summary"),
        "component_search_requirements": (
            planner_state.get("component_search_requirements") or []
        ),
        "initial_answer_contract_ref": dogfood._contract_summary(
            kernel.state.initial_answer_contract
        ),
        "current_answer_contract_ref": dogfood._contract_summary(
            kernel.state.current_answer_contract
        ),
        "search_executor_handoff_ref": {
            "handoff_id": handoff.get("handoff_id"),
            "handoff_digest": handoff.get("handoff_digest"),
            "execution_mode": handoff.get("execution_mode"),
            "contract_parent_kind": handoff.get("contract_parent_kind"),
            "provider_preference_hint": handoff.get("provider_preference_hint"),
        },
    }


def _fake_provider_posture(kernel: Any) -> dict[str, Any]:
    state = kernel.state.live_search_validation_state
    return {
        "provider_result_kind": "fake_offline_sanitized_provider_result_records",
        "selection_method": "deterministic scenario fixture selection",
        "fake_provider_used": state.get("fake_provider_used"),
        "provider_used_label": state.get("provider_used"),
        "provider_authorized_label": state.get("provider_authorized"),
        "selected_search_task_ids": state.get("selected_search_task_ids") or [],
        "candidate_count": state.get("candidate_count"),
        "broker_invoked": state.get("broker_invoked"),
        "live_provider_called": state.get("live_provider_called"),
        "raw_provider_payload_retained": state.get("raw_provider_payload_retained"),
        "raw_search_response_retained": state.get("raw_search_response_retained"),
        "real_acquisition_quality_claimed": False,
        "ranking_quality_claimed": False,
        "source_quality_claimed": False,
        "disclosure": (
            "The provider-shaped records are deterministic fake/offline/"
            "sanitized records selected by scenario; they do not imply real "
            "acquisition, ranking, or source quality."
        ),
    }


def _current_path_outputs(chain: Mapping[str, Any], kernel: Any) -> dict[str, Any]:
    outputs = dogfood._current_path_outputs(chain, kernel)
    return {
        "search_planner_proposal_state": kernel.state.search_planner_proposal_state,
        "initial_answer_contract": kernel.state.initial_answer_contract,
        "current_answer_contract": kernel.state.current_answer_contract,
        "search_executor_handoff_state": kernel.state.search_executor_handoff_state,
        "live_search_validation_state": kernel.state.live_search_validation_state,
        **outputs,
    }


def _index_packet(
    *,
    query: str,
    stable_query_digest: str,
    generated: Sequence[GeneratedDryRunPacket],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "proof_class": PROOF_CLASS,
        "product_facing_progress_type": PRODUCT_PROGRESS_TYPE,
        "original_user_query": query,
        "ordinary_query_digest": stable_query_digest,
        "packet_count": len(generated),
        "packets": [
            {
                "scenario_id": item.scenario_id,
                "json_path": str(item.json_path),
                "markdown_path": str(item.markdown_path),
                "author_prose_status": item.packet["author_prose_output"][
                    "author_prose_status"
                ],
                "sufficiency_readiness_status": item.packet[
                    "sufficiency_readiness_status"
                ]["final_readiness_status"],
                "fap_status": item.packet["hardened_final_answer_packet_status"][
                    "fap_status"
                ],
            }
            for item in generated
        ],
        "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
        "old_path_treatment": OLD_PATH_TREATMENT,
        "live_validation_status": "not run",
        "mandatory_next_checkpoint": MANDATORY_NEXT_CHECKPOINT,
    }


def _packet_markdown(packet: Mapping[str, Any]) -> str:
    scenario = packet["selected_scenario"]
    query_ref = packet["query_digest_ref"]
    readiness = packet["sufficiency_readiness_status"]
    fap = packet["hardened_final_answer_packet_status"]
    author = packet["author_prose_output"]
    posture = packet["caveats_blockers_contested_posture"]
    surfaces = "\n".join(
        f"- {item['surface']}: {item['status']}"
        for item in packet["current_path_surfaces_consumed"]
    )
    non_proofs = "\n".join(f"- {item}" for item in packet["explicit_non_proofs"])
    caveats = "\n".join(
        f"- {item}" for item in posture.get("mandatory_caveats") or ["None recorded."]
    )
    return (
        f"# {scenario['title']}\n\n"
        f"Phase: `{PHASE}`\n\n"
        f"Scenario id: `{scenario['scenario_id']}`\n\n"
        f"Original query: {packet['original_user_query']}\n\n"
        "Query digest: "
        f"`{query_ref['ordinary_query_ref']['digest']}`\n\n"
        f"Proof class: {packet['proof_class']}\n\n"
        f"Product-facing progress type: {packet['product_facing_progress_type']}\n\n"
        "## Current Path Surfaces Consumed\n\n"
        f"{surfaces}\n\n"
        "## Readiness and FAP\n\n"
        f"- SufficiencyReadiness: `{readiness['final_readiness_status']}`\n"
        f"- Hardened FAP: `{fap['fap_status']}`\n\n"
        "## AuthorProse Output\n\n"
        f"Status: `{author['author_prose_status']}`\n\n"
        f"{author['answer_text']}\n\n"
        "## Caveats / Blockers / Contested Posture\n\n"
        f"{caveats}\n\n"
        "## Explicit Non-Proofs\n\n"
        f"{non_proofs}\n\n"
        f"Mandatory next checkpoint: `{MANDATORY_NEXT_CHECKPOINT}`\n"
    )


def _index_markdown(index: Mapping[str, Any]) -> str:
    rows = "\n".join(
        "- `{scenario_id}`: {author_prose_status} / {sufficiency_readiness_status} / {fap_status}".format(
            **packet
        )
        for packet in index["packets"]
    )
    non_proofs = "\n".join(f"- {item}" for item in index["explicit_non_proofs"])
    return (
        f"# {PHASE}\n\n"
        f"Original query: {index['original_user_query']}\n\n"
        f"Ordinary query digest: `{index['ordinary_query_digest']}`\n\n"
        f"Proof class: {index['proof_class']}\n\n"
        f"Product-facing progress type: {index['product_facing_progress_type']}\n\n"
        "## Packets\n\n"
        f"{rows}\n\n"
        "## Explicit Non-Proofs\n\n"
        f"{non_proofs}\n\n"
        f"Mandatory next checkpoint: `{index['mandatory_next_checkpoint']}`\n"
    )


def _selected_scenarios(scenario: str) -> list[ScenarioSpec]:
    selected = scenario.strip()
    if selected == "all":
        return list(SCENARIOS.values())
    scenario_id = SCENARIO_ALIASES.get(selected)
    if not scenario_id:
        allowed = ", ".join(["all", *sorted(SCENARIO_ALIASES)])
        raise LocalDryRunError(f"unknown scenario {scenario!r}; expected one of {allowed}")
    return [SCENARIOS[scenario_id]]


def _normalize_query(query: str) -> str:
    normalized = " ".join(str(query or "").strip().split())
    if not normalized:
        raise LocalDryRunError("ordinary-query dry-run requires --query text")
    return normalized


def _ordinary_query_digest(query: str) -> str:
    payload = {
        "phase": PHASE,
        "normalized_user_query_text": _normalize_query(query),
    }
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _run_id(query_digest: str, scenario_id: str) -> str:
    return f"run:ag-local-dryrun-query-to-authorprose-01:{scenario_id}:{query_digest[:12]}"


def _request_id(query_digest: str, scenario_id: str) -> str:
    return (
        "request:ag-local-dryrun-query-to-authorprose-01:"
        f"{scenario_id}:{query_digest[:12]}"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate AG-LOCAL-DRYRUN-QUERY-TO-AUTHORPROSE-01 reviewable "
            "AuthorProse packets from a user-style query through the existing "
            "offline current path."
        )
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="Ordinary user-style query to bind into SearchPlanner.",
    )
    parser.add_argument(
        "--scenario",
        default="all",
        choices=("all", *sorted(SCENARIO_ALIASES)),
        help="Dry-run scenario to generate.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Ignored/local output directory for JSON and Markdown packets.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        generated = generate_query_dry_run_packets(
            query=args.query,
            scenario=args.scenario,
            output_dir=args.output_dir,
        )
    except (LocalDryRunError, dogfood.FixtureDogfoodError, ValueError, KeyError) as exc:
        print(f"refusing AG-LOCAL dry-run packet generation: {exc}", file=sys.stderr)
        return 2
    summary = {
        "phase": PHASE,
        "output_dir": str(Path(args.output_dir)),
        "packet_count": len(generated),
        "packets": [
            {
                "scenario_id": item.scenario_id,
                "json_path": str(item.json_path),
                "markdown_path": str(item.markdown_path),
            }
            for item in generated
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
