"""Static guards for the canonical documentation truth spine.

Test path: tests/test_docs_canonical_truth_spine_01.py
Proof class: STATIC_CONTRACT_PROOF / documentation-only.
Validation bucket: phase_focus.
Surface guarded: temporal owners, concern owners, routing, and stale-doctrine
exclusion.
Runtime/product path guarded: repository guidance only; no runtime behavior.
Expected cost: local text reads, under one second.
Promotion posture: remain phase_focus.
Why not fast_pr: detailed documentation-owner repair guard.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARCH = DOCS / "architecture"
HISTORICAL_ARCH = DOCS / "history" / "architecture"
GUIDANCE = DOCS / "codex" / "CODEX_GUIDANCE_MAP.md"
PROOF_GATE = DOCS / "codex" / "PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md"
CURRENT_STATE = ARCH / "SCRYRAVEN_CURRENT_STATE.md"
ROADMAP = DOCS / "roadmap" / "CURRENT_ROADMAP.md"
SEARCHPLANNER_TRACKER = DOCS / "roadmap" / "SEARCHPLANNER_REPAIR_TRACKER.md"
TECH_DEBT = DOCS / "TECH_DEBT_REGISTER.md"
DISCOVER_HANDOFF_BRIEF = DOCS / "roadmap" / "DISCOVER_RESULT_CANDIDATE_HANDOFF_CONVERGENCE_01.md"
QUERY_CONVERGENCE_BRIEF = (
    DOCS / "roadmap" / "SEARCHOS_QUERY_STRATEGY_AND_RECON_CONVERGENCE_01.md"
)
EXACT_URL_BRIEF = DOCS / "roadmap" / "EXACT_URL_ACQUISITION_AND_FINAL_CUSTODY_CONVERGENCE_01.md"
CENSUS = ARCH / "PROVIDER_OFFERINGS_ADAPTER_AND_LEGACY_DOCTRINE_CENSUS.md"
PROVIDER_ROUTING = ARCH / "PROVIDER_CAPABILITY_AND_ACQUISITION_ROUTING.md"
ACQUISITION_CONTROL = ARCH / "RUNKERNEL_POST_DISCOVERY_ACQUISITION_CONTROL.md"
SEARCHOS = ARCH / "SEARCHOS_OPERATING_MODEL.md"
SEARCHOS_RECOVERY_DIRECTION = (
    ARCH / "SEARCHOS_POST_ANALYSIS_RECOVERY_AND_INFERENCE_DIRECTION.md"
)
SEARCHOS_ITERATIVE_DIRECTION_ACTIVE = ARCH / "SEARCHOS_ITERATIVE_JUDGMENT_DIRECTION.md"
SEARCHOS_ITERATIVE_DIRECTION_HISTORICAL = (
    HISTORICAL_ARCH / "phases" / "SEARCHOS_ITERATIVE_JUDGMENT_DIRECTION.md"
)
HISTORICAL_ARCH_INDEX = HISTORICAL_ARCH / "INDEX.md"
SEARCHOS_SLICE_A = ARCH / "SEARCHOS_FIRST_WAVE_AND_ITERATIVE_JUDGMENT_CUTOVER.md"
QUARANTINE = ARCH / "AG_CURRENT_PATH_QUARANTINE_01.md"
ORCHESTRATOR_STRANGLER = ARCH / "AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md"
ECONOMIST_SAFETY = DOCS / "architecture_safety_contract.md"
ECONOMIST_TELEMETRY_POLICY = DOCS / "economist_shadow_telemetry_promotion_policy.md"
CONCERN_OWNERS = {
    "canonical:dprime-role-contract": ARCH / "DPRIME_ARCHITECTURE.md",
    "canonical:run-contract-semantic-loop": ARCH / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    "canonical:component-dag-scheduling-concurrency": (ARCH / "RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md"),
    "canonical:fap-author-boundary": ARCH / "FAP_AUTHOR_BOUNDARY.md",
    "canonical:bounded-multicomponent-runtime": (ARCH / "MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md"),
    "canonical:specialist-graph-substrate": ARCH / "SPECIALIST_GRAPH_SUBSTRATE.md",
    "canonical:quantitative-specialist-product-activation": (ARCH / "AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md"),
    "canonical:quantitative-finalization-containment": (ARCH / "AG_S1_QUANTITATIVE_FINALIZATION_CONTAINMENT_01.md"),
    "canonical:searchos-post-analysis-recovery-and-inference-direction": (
        SEARCHOS_RECOVERY_DIRECTION
    ),
}
DEFAULT_SPINE = (GUIDANCE, CURRENT_STATE, ROADMAP)
MARKERS = (
    "MC-P1-ORDINARY",
    "MC-P2-DYNAMIC-RECOVERY",
    "MC-P3-SELECTIVE-RECOMPUTE",
    "MC-P4-SCHEDULER-LEASES",
    "MC-P5A-HOSTED-W2",
    "MC-P5A-STRICT-ONE-SHOT",
    "MC-P5A-SAMPLING-COMPAT",
    "MC-P5A-MAIN-THREAD-COST",
    "SPECIALIST-S0-GENERIC",
    "SPECIALIST-S1-QUANTITATIVE",
    "QUANT-FINALIZATION-CONTAINMENT",
    "PROVIDER-CAPABILITY-ROUTING",
    "SEARCHOS-QUERY-CONVERGENCE",
    "SEARCHOS-SLICE-A-CUTOVER",
    "SEARCHPLANNER-BOUNDARY-INTEGRITY",
)
QUANT_FINALIZATION_RUNTIME_SHA = "4e095c7db287ab29fbe748bdd5c24cf4f2545e15"  # pragma: allowlist secret
QUANT_LINEAGE_RUNTIME_SHA = "bba0d16313944b742251298b4fc929b4ceb55d76"  # pragma: allowlist secret
STRUCTURED_ROUTE_RUNTIME_SHA = "e39ab69fcba2c34bdf0ac9adfd2f3ce39dbaad64"  # pragma: allowlist secret
SCOUT_RETIREMENT_RUNTIME_SHA = "af87f5387fb5cd11a36c56754ee719400bb1bf0b"  # pragma: allowlist secret
PROVIDER_ROUTING_RUNTIME_SHA = "193c5caabe1f97da534f0e601d410acb98d3cdea"  # pragma: allowlist secret
ACQUISITION_CONTROL_RUNTIME_SHA = "48a309124764d813cf27081bf5871d5a9612db79"  # pragma: allowlist secret
INITIAL_DISCOVERY_RETIREMENT_RUNTIME_SHA = ACQUISITION_CONTROL_RUNTIME_SHA
DISCOVER_HANDOFF_RUNTIME_SHA = "6fbca602afac5a00bb6bafa2a6888b6ec31d5065"  # pragma: allowlist secret
UNIFIED_SEARCHOS_RUNTIME_SHA = "96413c9a1f901dc191ecc94e6330014841ee4dda"  # pragma: allowlist secret
QUERY_CONVERGENCE_RUNTIME_SHA = "2d346a73251f28a1187fb2958028db51117bf0c0"  # pragma: allowlist secret
READ_SOURCE_CUSTODY_RUNTIME_SHA = "39573c29bc2394e798e507fc795d70197da20f10"  # pragma: allowlist secret
SEARCHOS_SLICE_A_RUNTIME_SHA = "4431ff46ed1e8367b124f596ccc04e90040217b6"  # pragma: allowlist secret
SEARCHOS_RECOVERY_RUNTIME_SHA = "540141acaaaf041bda303edd62211dd6a11958bc"  # pragma: allowlist secret
CURRENT_STATE_RUNTIME_SHA = UNIFIED_SEARCHOS_RUNTIME_SHA
HISTORICAL_SEARCH_EXECUTOR_RECORD = (
    "Historical merge-stable SearchExecutor record: PR #330 / "
    "AG-SEARCH-EXECUTOR-HANDOFF-01; handoff consumes current_answer_contract "
    "when present; Scout/revision material is search direction only; handoff "
    "creates search task records and a search work packet; no live "
    "search/provider/fetch/read/retrieval calls were run; no "
    "EvidenceLedger/citations/source-obligation satisfaction; next "
    "implementation gate after AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01 is "
    "AG-LIVE-XAXIS-VALIDATION-01A."
)
SPECIALIST_ADMISSION_RUNTIME_SHA = "72251c126770e41a9b52105d860154d1cfef811b"  # pragma: allowlist secret
LEGACY_ECONOMIST_RETIREMENT_RUNTIME_SHA = "7bbfff0f604096e3437bfdadc3dd8b81ec56b57c"  # pragma: allowlist secret
QUANT_CONTAINMENT_RUNTIME_SHA = "5e6fa705e0e7e13662c7860dcb5bea573b8ac0c2"  # pragma: allowlist secret
S1_RUNTIME_SHA = "4232c4570908065adf589ec2b44be695f82fce56"  # pragma: allowlist secret


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collapsed(path: Path) -> str:
    return " ".join(_read(path).split())


def _links(path: Path) -> list[Path]:
    targets = re.findall(r"\[[^]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)", _read(path))
    return [(path.parent / target).resolve() for target in targets]


def test_guidance_links_resolve() -> None:
    links = _links(GUIDANCE)
    assert links
    for target in links:
        assert target.is_file(), target


def test_temporal_authorities_are_unique_and_owned_by_truth_type() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    for authority, owner in (
        ("canonical:current-installed-state", CURRENT_STATE),
        ("canonical:current-roadmap", ROADMAP),
    ):
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]
        text = _read(owner)
        assert "Status: current" in text
        assert "Default-read: yes" in text

    current = _read(CURRENT_STATE)
    roadmap = _read(ROADMAP)
    runtime_anchor = f"Runtime-audit-through: {CURRENT_STATE_RUNTIME_SHA}"
    assert current.count(runtime_anchor) == 1
    assert "Verified-against-runtime:" not in current
    assert "Runtime-audit-through:" not in roadmap
    assert "Verified-against-runtime:" not in roadmap


def test_concern_authorities_are_unique_current_and_default_no() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    for authority, owner in CONCERN_OWNERS.items():
        text = _read(owner)
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]
        assert "Status: current" in text
        assert "Default-read: no" in text
        assert len(re.findall(r"^Verified-against-runtime: [0-9a-f]{40}$", text, re.MULTILINE)) == 1


def test_quantitative_finalization_inventory_does_not_overclaim_saved_thread() -> None:
    current = _read(CURRENT_STATE)
    containment = _read(CONCERN_OWNERS["canonical:quantitative-finalization-containment"])

    assert "Every active accepted-prose route" not in current
    assert "every active accepted-prose finalization route" not in containment
    assert "## Active Finalization Route Inventory" not in containment
    assert "## Guarded Finalization Consumer Inventory" in containment
    for consumer in (
        "AuthorExecutor",
        "AuthorProseFinalization",
        "follow-up response finalizer",
    ):
        assert consumer in current
        assert consumer in containment
    for text in (current, containment):
        normalized = " ".join(text.split())
        assert "internal supporting machinery" in normalized
        assert "does not establish" in normalized
        assert "saved-thread product consumption" in normalized
        assert "ui.pages_followup" in normalized
        assert "core.followup" in normalized
        assert "retired from ordinary product use" in normalized
        assert "not a current consumer" in normalized
        assert "shared accepted-prose validator" in normalized
    assert "future follow-up activation" in containment


def test_quarantine_is_narrow_routed_support_not_temporal_authority() -> None:
    text = _read(QUARANTINE)
    assert "Status: supporting" in text
    assert "Authority: routed-support" in text
    assert "Default-read: no" in text
    assert "not an installed-state registry or a roadmap" in text
    assert "contains no broad product-state registry" in text
    assert "canonical:current-installed-state" not in text
    assert "canonical:current-roadmap" not in text

    temporal_routes = _read(GUIDANCE).split("## Phase Operation", maxsplit=1)[0]
    assert QUARANTINE.name not in temporal_routes


def test_guidance_routes_to_exact_concern_owners() -> None:
    guidance = _read(GUIDANCE)
    for authority, owner in CONCERN_OWNERS.items():
        assert f"`{authority}`" in guidance
        assert owner.name in guidance
    assert "await D1 repair" not in guidance
    assert "implementation-status sections" not in guidance


def test_searchos_target_owner_is_unique_routed_and_nonactivating() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    normalized = _collapsed(SEARCHOS)
    authority = "Authority: canonical:searchos-operating-model"

    assert [path for path in markdown if authority in _read(path)] == [SEARCHOS]
    for phrase in (
        "Status: current architecture; unified front-half Phases 1-2 installed",
        "Default-read: no",
        "SearchOS architecture and SearchOS-facing provider, acquisition, navigation, and recovery work",
        "Does-not-authorize: implementation, live calls, provider claims, or activation of planned capabilities",
        "ScryRaven is a research application",
        "ScryRaven's search, source-acquisition, navigation, and recovery subsystem",
        "RunKernel / RunAuthority is the root authority for a run",
        "Sufficiency decides whole-run readiness and final posture from canonical facts",
        "RunKernel consumes and enforces that decision",
        "Sufficiency does not independently mutate or terminate run state",
        "minimum shared search result",
        "Direction material",
        "Search-result material",
        "Read-source material",
        "Navigation material",
        "`DISCOVER job_class=orientation`",
        "`DISCOVER job_class=standard_discovery`",
        "`DISCOVER job_class=deep_discovery`",
        "`RECON` and `SEARCH` may remain compatibility implementation terms",
        "they are not separate durable pipelines or competing query authorities",
        "Cheap orientation is represented only by `DISCOVER job_class=orientation` inside the unified acquisition loop",
        "Linkup Fetch and Tavily Extract are peer implementations",
        "Adaptive retrieval is approved but uninstalled",
        "The provider owns DNS",
        "No SearchOS infrastructure may be added merely",
    ):
        assert phrase in normalized
    assert "**`RECON`**: non-evidence direction" not in normalized

    guidance = _read(GUIDANCE)
    assert SEARCHOS.name in guidance
    assert "A narrow search task does not require all three supporting documents" in _collapsed(GUIDANCE)
    for target in _links(SEARCHOS):
        assert target.is_file(), target


def test_searchos_recovery_direction_is_durable_routed_and_predecessor_is_historical() -> None:
    guidance = _collapsed(GUIDANCE)
    operating_model = _collapsed(SEARCHOS)
    direction = _collapsed(SEARCHOS_RECOVERY_DIRECTION)
    historical_index = _read(HISTORICAL_ARCH_INDEX)

    authority = (
        "Authority: "
        "canonical:searchos-post-analysis-recovery-and-inference-direction"
    )
    active_claimants = [
        path for path in ARCH.rglob("*.md") if authority in _read(path)
    ]
    assert active_claimants == [SEARCHOS_RECOVERY_DIRECTION]
    assert "Status: current installed convergence doctrine" in direction
    assert "Default-read: no" in direction
    assert f"Verified-against-runtime: {SEARCHOS_RECOVERY_RUNTIME_SHA}" in direction

    assert SEARCHOS_SLICE_A.name in guidance
    assert SEARCHOS_RECOVERY_DIRECTION.name in guidance
    assert SEARCHOS_ITERATIVE_DIRECTION_ACTIVE.name not in guidance
    assert "Installed QueryPlan job classes, first-wave and iterative SearchJudgment" in guidance
    assert "Installed Boundary A existing-gap recovery" in guidance

    assert SEARCHOS_SLICE_A.name in operating_model
    assert SEARCHOS_RECOVERY_DIRECTION.name in operating_model
    assert SEARCHOS_ITERATIVE_DIRECTION_ACTIVE.name not in operating_model

    for phrase in (
        "## Durable North Star",
        "one component graph",
        "one inference pipeline",
        "one admission chain",
        "one SearchJudgment owner",
        "one whole-run stopping authority",
        "SearchOS retrieves missing premises",
        "Sufficiency owns whole-run posture",
        "Recovery cycles are append-only",
        "Recovery generation depth is distinct from semantic inference depth",
        "Checkpoint-appendix expiry: completed with SEARCHOS-GAP-RECOVERY-AND-STOP-CONVERGENCE-01",
        "## Post-Checkpoint Steady-State Architecture",
        "## Current Checkpoint Implementation Appendix",
        "This appendix records the completed implementation boundaries",
        "It is not the durable identity of the subsystem",
    ):
        assert phrase in direction

    assert not SEARCHOS_ITERATIVE_DIRECTION_ACTIVE.exists()
    assert SEARCHOS_ITERATIVE_DIRECTION_HISTORICAL.is_file()
    assert SEARCHOS_ITERATIVE_DIRECTION_HISTORICAL.name in historical_index
    assert (
        "`docs/architecture/SEARCHOS_ITERATIVE_JUDGMENT_DIRECTION.md`"
        in historical_index
    )

    for path in (GUIDANCE, SEARCHOS, ROADMAP, SEARCHOS_RECOVERY_DIRECTION, SEARCHOS_SLICE_A):
        for target in _links(path):
            assert target.is_file(), (path, target)


def test_active_technical_debt_register_is_unique_routed_and_nonactivating() -> None:
    assert TECH_DEBT.is_file()

    markdown = tuple(DOCS.rglob("*.md"))
    normalized = _collapsed(TECH_DEBT)
    authority = "Authority: canonical:active-technical-debt-register"
    assert [path for path in markdown if authority in _read(path)] == [TECH_DEBT]

    for phrase in (
        "Status: current",
        "Default-read: no",
        "Next-ID: TD-0004",
        "canonical active-only inventory",
        "sole owner of priority and phase order",
        "IDs are monotonic and never reused",
        "TD-0001 — Provider-routing fixture availability drift",
        "TD-0002 — Analyst Workbench injected-runner availability drift",
        "Does-not-authorize: implementation, priority, roadmap sequencing, live calls, provider changes, or scope expansion",
    ):
        assert phrase in normalized

    guidance = _read(GUIDANCE)
    assert TECH_DEBT.name in guidance
    assert "Active confirmed technical debt, duplicate check, or debt-resolution disposition" in guidance
    default_read = guidance.split("## Smallest Default Read Path", maxsplit=1)[1].split(
        "## Temporal Owners", maxsplit=1
    )[0]
    assert TECH_DEBT.name not in default_read
    assert "Do not read it for every ordinary implementation task" in _collapsed(GUIDANCE)

    proof_gate = _read(PROOF_GATE)
    assert "Technical-debt register disposition:" in proof_gate
    assert "Discovery does not authorize repair" in proof_gate


def test_repaired_contracts_exclude_active_roadmap_and_obsolete_status() -> None:
    forbidden = (
        "recommended next phase",
        "recommended next build",
        "next implementation gate",
        "post-merge next gate",
        "## current roadmap",
        "## historical second-half roadmap",
        "await d1 repair",
    )
    for path in CONCERN_OWNERS.values():
        text = _collapsed(path).casefold()
        if path == CONCERN_OWNERS["canonical:run-contract-semantic-loop"]:
            text = text.replace(HISTORICAL_SEARCH_EXECUTOR_RECORD.casefold(), "")
        for phrase in forbidden:
            assert phrase not in text, (path, phrase)

    dprime = _collapsed(CONCERN_OWNERS["canonical:dprime-role-contract"])
    assert "ordinary bounded multi-component path consumes both component D-prime and synthesis D-prime" in dprime
    assert "Review and admission alone do not prove" in dprime
    assert "approved general ordinary component Analyst" not in dprime

    semantic_path = CONCERN_OWNERS["canonical:run-contract-semantic-loop"]
    semantic_text = _read(semantic_path)
    semantic = _collapsed(semantic_path)
    assert semantic_text.count(HISTORICAL_SEARCH_EXECUTOR_RECORD) == 1
    assert "PR #" not in semantic_text.replace(HISTORICAL_SEARCH_EXECUTOR_RECORD, "")
    assert "Workers propose. RunKernel authorizes and reduces." in semantic

    dag = _collapsed(CONCERN_OWNERS["canonical:component-dag-scheduling-concurrency"])
    assert "ComponentWorkGraph V1 is installed" in dag
    assert "future shape" not in dag.casefold()
    assert "next BUILD must install ordinary consumption" not in dag

    fap = _collapsed(CONCERN_OWNERS["canonical:fap-author-boundary"])
    assert "When FAP readiness is blocked, Author does not run." in fap
    assert "generic D-prime admission is not numeric rendering authority" in fap
    assert "future answer rendering" not in fap.casefold()

    containment = _collapsed(CONCERN_OWNERS["canonical:quantitative-finalization-containment"])
    assert "The two authority kinds are" in containment
    assert "Generic admission is not an authority kind." in containment
    assert "`admitted_quantitative_claim`" not in containment


def test_hardened_quantitative_component_boundary_is_current_and_narrow() -> None:
    containment = _collapsed(CONCERN_OWNERS["canonical:quantitative-finalization-containment"])
    current = _collapsed(CURRENT_STATE)

    for text in (containment, current):
        for phrase in (
            "preserves two component-scoped quantitative authority classes",
            "exact current component, semantic-observation, content, coverage, evidence-custody, proposition-fingerprint, and complete literal-signature binding",
            "installed capability and version, result and handoff identities and digests, canonical component target, exact claim-material binding, canonical `result_unit` and precision",
            "terminal consumption by the applicable component D-prime",
            "Generic D-prime admission alone remains nonauthority",
            "fails atomically on unsupported quantitative prose",
            "packages component entries only",
            "does not project synthesis entries",
            "does not install a hardened synthesis sidecar",
            "No live validation was performed.",
            "No acquisition-completeness repair was performed.",
            "No hardened synthesis path was activated.",
        ):
            assert phrase in text

    assert "No provider or model changed." in containment
    assert "Current real-model SearchPlanner behavior remains unproved." in current
    assert "`SEARCHPLANNER-BOUNDARY-INTEGRITY`" in current

    assert "No route-qualification repair was performed." in containment
    assert "Arbitrary-query decomposition and broad route qualification remain unproved." in current

    for phrase in (
        "No new Specialist capability was added.",
        "Broad live correctness, answer quality, and production stability remain unproved.",
        "Ordinary synthesis-origin S1 authority remains owned by the ordinary ComponentWorkGraph / synthesis D-prime / ordinary FinalAnswerPacket path.",
    ):
        assert phrase in containment
        assert phrase in current
    assert "No S1 proposal or invocation policy expanded." in containment
    assert (
        "No S1 capability, route eligibility, budget, scheduling order, recursion, or parallelism expanded." in current
    )


def test_structured_route_qualification_is_current_and_narrow() -> None:
    owner = _collapsed(CONCERN_OWNERS["canonical:bounded-multicomponent-runtime"])
    current = _collapsed(CURRENT_STATE)
    roadmap = _collapsed(ROADMAP)

    for phrase in (
        "One deterministic query-shape owner",
        "bounded bullet lists",
        "contiguous numbered lists",
        "bounded repeated imperative clauses",
        "two through five distinct factual components",
        "request-level synthesis directive",
        "general multipart fallback",
        "Fast, Balanced, and Deep use the same parser and route pipeline",
        "does not establish arbitrary-query decomposition",
    ):
        assert phrase in owner

    for phrase in (
        "One deterministic query-shape assessment",
        "preserves component order and the exact directive",
        "existing general multipart fallback remains separate",
        "Fast, Balanced, and Deep consume this same parser and route pipeline",
    ):
        assert phrase in current

    assert "No route-qualification repair was performed." not in current
    assert "Completed Repair: STRUCTURED-LIST-ROUTE-QUALIFICATION-REPAIR-01" in roadmap
    assert "Active Decision Gate: SearchOS Carrier Consolidation + Product Proof" in roadmap


def test_current_state_has_all_installed_capability_markers() -> None:
    current = _read(CURRENT_STATE)
    for marker in MARKERS:
        assert current.count(f"`{marker}`") == 1


def test_mode_policy_recovery_custody_is_installed_and_narrow() -> None:
    current = _collapsed(CURRENT_STATE)
    roadmap = _collapsed(ROADMAP)
    strangler = _collapsed(ORCHESTRATOR_STRANGLER)

    for text in (current, roadmap, strangler):
        assert (
            "ffd6796e37fac468c826afd29767aafe1e235f41"  # pragma: allowlist secret
            in text
        )
        assert "mode-policy envelope" in text
        assert "temporary compatibility values" in text
        assert "Balanced" in text
        assert "Fast" in text
        assert "Deep" in text
        assert "unsupported mode" in text.casefold()
        assert "mode-neutral" in text
        assert "no live recovery" in text.casefold()
        assert "Deep pass-through" not in text
        assert "Fast`, `Deep`, and unsupported modes return no policy" not in text

    assert "no recovery adapter" in roadmap
    assert "supported ordinary CLI composition still supplies no adapter" in current

    for phrase in (
        "Every supported mode now resolves the recovery-related slice of one shared mode-policy envelope",
        "Fast` is recovery-closed in this phase",
        "Deep` is recovery-closed pending a later explicit mode-policy decision",
        "Unsupported modes resolve the same envelope shape",
        "No permanent mode budget was selected",
        "Every resolved envelope enters the same mode-neutral coordinator and recovery primitive",
        "Closed Fast and Deep values return an unrecorded non-applicable result",
        "RunKernel's canonical EvidenceLedger and semantic component-coverage state",
        "same ordinary typed materialization handoff",
        "Sufficiency runs again from the current canonical state before FAP",
        "No live recovery composition",
    ):
        assert phrase in current

    for phrase in (
        "recovery returns no final-evidence, source-list, FinalAnswerPacket, or Author-material fields",
        "Every supported mode resolves the same recovery-related mode-policy envelope shape",
        "Fast is closed in this phase",
        "Deep is closed pending a later explicit mode-policy decision",
        "This does not claim that the whole orchestrator is authority-free",
        "Post-recovery material must match current RunKernel state",
        "an incomplete shared handoff fails closed",
        "neither invokes the adapter nor records recovery history or a recovery projection",
        "These values are not permanent product design",
        "Other `locals()` consumers",
        "broader final-custody convergence remain unresolved",
    ):
        assert phrase in strangler

    assert "Completed Repair: Mode-Policy Recovery Authority Containment" in roadmap
    assert "Completed Repair: SPECIALIST-PROPOSAL-INSTANCE-ADMISSION-HARDENING-01" in roadmap
    assert "Completed Repair: STRUCTURED-LIST-ROUTE-QUALIFICATION-REPAIR-01" in roadmap
    assert "Active Decision Gate: SearchOS Carrier Consolidation + Product Proof" in roadmap
    assert "No live recovery" in roadmap


def test_provider_capability_routing_owner_is_current_installed_and_narrow() -> None:
    routing = _read(PROVIDER_ROUTING)
    normalized = _collapsed(PROVIDER_ROUTING)
    markdown = tuple(DOCS.rglob("*.md"))

    authority = "Authority: canonical:provider-capability-acquisition-routing"
    assert [path for path in markdown if authority in _read(path)] == [PROVIDER_ROUTING]
    for phrase in (
        "Status: current",
        "Default-read: yes",
        f"Verified-against-runtime: {UNIFIED_SEARCHOS_RUNTIME_SHA}",
        "`core.routing` is the sole provider-capability policy owner",
        "exactly one selected provider or blocks with zero transport",
        "Fallback candidates remain descriptive",
        "never dispatch after provider failure",
        "Linkup `standard/searchResults`",
        "Exa `neural_with_text/searchResults`",
        "Serper Web Search",
        "Brave Web Search",
        "Fast, Balanced, or Deep mode",
        "Scrutineer Deep remains separate and unchanged",
        "Provider synthesis remains disabled",
        "Linkup Fetch",
        "Tavily Extract",
        "Tavily Map",
        "Tavily Crawl",
        "SearchOS Operating Model",
        "social interpretation",
        "No live provider, model, search, fetch, map, crawl, or retrieval call",
    ):
        assert phrase in normalized

    for capability in (
        "`DISCOVER`",
        "`READ`",
        "`FOCUSED_EXTRACT`",
        "`MAP_SITE`",
        "`CRAWL_SITE`",
        "`PROVIDER_SYNTHESIS`",
    ):
        assert capability in routing
    assert "Linkup-only remains valid" in normalized
    assert "mode; high complexity" in normalized


def test_acquisition_runtime_convergence_truth_is_consistent_across_spine() -> None:
    routing = _collapsed(PROVIDER_ROUTING)
    census = _collapsed(CENSUS)
    current = _collapsed(CURRENT_STATE)
    roadmap = _collapsed(ROADMAP)

    assert PROVIDER_ROUTING_RUNTIME_SHA in census
    assert f"Verified-against-runtime: {READ_SOURCE_CUSTODY_RUNTIME_SHA}" in _read(
        ACQUISITION_CONTROL
    )
    assert f"Verified-against-runtime: {UNIFIED_SEARCHOS_RUNTIME_SHA}" in _read(
        PROVIDER_ROUTING
    )
    current_owner = _read(CURRENT_STATE)
    roadmap_owner = _read(ROADMAP)
    assert f"Runtime-audit-through: {CURRENT_STATE_RUNTIME_SHA}" in current_owner
    assert "Runtime-audit-through:" not in roadmap_owner
    assert "Verified-against-runtime:" not in roadmap_owner
    assert f"Runtime/test commit `{ACQUISITION_CONTROL_RUNTIME_SHA}`" in _read(ROADMAP)

    for text in (routing, census, current):
        for phrase in (
            "DISCOVER",
            "READ",
            "FOCUSED_EXTRACT",
            "MAP_SITE",
            "CRAWL_SITE",
            "General Linkup Deep",
            "Scrutineer Deep",
            "PROVIDER_SYNTHESIS",
        ):
            assert phrase in text
        assert "selected-candidate" in text
        assert "Linkup Fetch" in text
        assert "Tavily Extract" in text
        assert "provider synthesis remains disabled" in text.casefold()

    for phrase in (
        "FOCUSED_EXTRACT | yes | yes | `focused_extract_requester_not_installed`",
        "MAP_SITE | yes | yes | `map_candidate_reentry_not_installed`",
        "CRAWL_SITE | yes | yes | `crawl_page_custody_not_installed`",
        "General Linkup Deep | mechanical support yes | premium sequential need recognized",
    ):
        assert phrase in current

    assert "process_search_queries(search_providers=None)" in routing
    assert "performs zero transport" in routing
    assert (
        "Provider-failure fallback and navigation beyond the installed one-hop "
        "boundary are not installed"
        in current
    )
    assert "ordinary-product consumption of focused extraction" in census
    for phrase in (
        "one boolean provider-availability snapshot",
        "provider preferences cannot create availability",
        "marks the existing fetch/read cap exactly once",
        "rendering posture is explicit",
        "remain unknown instead of being synthesized",
    ):
        assert phrase in roadmap
    assert "provider_reported_url" in routing
    assert "read_provider_reported_url_mismatch" in routing
    assert "provider-neutral DISCOVER qualifier" in routing
    assert "RunCapExceeded" in routing

    assert roadmap.count("## Active Next:") == 0
    assert roadmap.count("## Blocked Next:") == 0
    assert "## Active Decision Gate: SearchOS Carrier Consolidation + Product Proof" in roadmap
    for stale in (
        "## Active Next: KNOWN-URL-READ-FOUNDATION-01",
        "### TAVILY-EXTRACT-AND-MAP-ADAPTERS-01",
        "### TAVILY-BOUNDED-CRAWL-ADAPTER-01",
        "### LINKUP-DEEP-SEQUENTIAL-ACQUISITION-01",
        "### ACQUISITION-ROUTING-CLOSURE-01 If Required",
    ):
        assert stale not in roadmap


def test_discovery_retirement_and_candidate_handoff_truth_is_consistent() -> None:
    current = _collapsed(CURRENT_STATE)
    routing = _collapsed(PROVIDER_ROUTING)
    acquisition = _collapsed(ACQUISITION_CONTROL)
    loop = _collapsed(CONCERN_OWNERS["canonical:run-contract-semantic-loop"])
    roadmap = _collapsed(ROADMAP)
    handoff = _collapsed(DISCOVER_HANDOFF_BRIEF)
    exact_url = _collapsed(EXACT_URL_BRIEF)

    for owner in (
        CURRENT_STATE,
        PROVIDER_ROUTING,
        ACQUISITION_CONTROL,
        CONCERN_OWNERS["canonical:run-contract-semantic-loop"],
        ROADMAP,
        DISCOVER_HANDOFF_BRIEF,
        EXACT_URL_BRIEF,
    ):
        assert INITIAL_DISCOVERY_RETIREMENT_RUNTIME_SHA in _read(owner)

    for phrase in (
        "zero separate candidate-URL transport",
        "provider_returned_snippet",
        "provider_returned_excerpt",
        "`AcquisitionNeedProposalV1`",
        "core.pipeline._apply_source_custody_fetch_read_policy",
        "core.retrieval.fetch_page",
        "fetch_url_text",
        "`retrieval.DiscoverySourceResultIdentity` owns immutable occurrence identity",
        "`retrieval.DiscoveryResultMaterialStore` owns run-local bounded provider material",
        "`RunKernel.SearchResultCandidatePacket` owner consumes that exact handoff",
        "does not use `live_search_validation`",
    ):
        assert phrase in current
    assert "selected-candidate nontrigger" in routing.casefold()
    assert "no exact-URL cap charge" in acquisition
    assert "opens a candidate source URL" in loop
    assert "`discover_candidate_urls_admitted` counts provider-result" in _read(CURRENT_STATE)
    assert "`urls_fetched` counts actual separate exact-URL" in _read(CURRENT_STATE)
    assert "`total_urls_fetched` / `urls_fetched`" not in _read(CURRENT_STATE)
    assert "## Completed Build: INITIAL-DISCOVERY-SELECTIVE-FETCH-RETIREMENT-01" in _read(ROADMAP)
    assert "Status: completed Build" in _read(DISCOVER_HANDOFF_BRIEF)
    assert DISCOVER_HANDOFF_RUNTIME_SHA in _read(DISCOVER_HANDOFF_BRIEF)
    assert "canonical ordinary-origin revision-1 packet" in handoff
    assert "No shadow planner" in _read(DISCOVER_HANDOFF_BRIEF)
    assert "zero candidate-page or exact-URL transport" in handoff
    assert "SEARCHOS-QUERY-STRATEGY-AND-RECON-CONVERGENCE-01" in roadmap
    assert "Status: superseded before implementation" in _read(EXACT_URL_BRIEF)
    assert "Superseded-by: SEARCHOS-OPERATING-MODEL-AND-ROADMAP-REALIGNMENT-01" in _read(EXACT_URL_BRIEF)
    assert DISCOVER_HANDOFF_RUNTIME_SHA in _read(EXACT_URL_BRIEF)
    assert "Canonical ordinary DISCOVER now populates revision 1" in exact_url
    assert "post-selection READ and FOCUSED_EXTRACT material" in exact_url
    assert "one to twenty exact URLs" in exact_url
    assert "The producer may propose only; RunKernel must derive the capability" in exact_url
    assert "URL presence, or free-form tool instructions" in exact_url
    assert "READ and activated Focused Extract" in exact_url
    assert "Focused Extract remains a separate future checkpoint" not in exact_url
    assert "If exact focus requires a distinct semantic producer, model-visible proposal" in exact_url
    assert "rather than weakening the controller or fabricating focus" in exact_url
    assert "Initial DISCOVER material remains provider-returned" in exact_url
    assert "must not fetch candidate pages" in exact_url
    assert "does not yet populate" not in exact_url
    assert "remains blocked until" not in exact_url
    assert "SQLite does not store the full packet" in handoff

    roadmap_folded = roadmap.casefold()
    handoff_index = roadmap_folded.index("## completed build: discover-result-candidate-handoff-convergence-01")
    query_index = roadmap_folded.index(
        "## completed build: searchos-query-strategy-and-recon-convergence-01"
    )
    read_index = roadmap_folded.index(
        "## completed build: searchos-read-source-and-custody-01"
    )
    slice_a_index = roadmap_folded.index(
        "## completed build: searchos-first-wave-and-iterative-judgment-cutover-01"
    )
    navigation_index = roadmap_folded.index(
        "## completed build: searchos-one-hop-navigation-product-activation-01"
    )
    active_index = roadmap_folded.index(
        "## active decision gate: searchos carrier consolidation + product proof"
    )
    assert (
        handoff_index
        < query_index
        < read_index
        < slice_a_index
        < navigation_index
        < active_index
    )
    assert "existing front- or back-half localization" in roadmap
    assert "Map may be inserted later as an optional navigation plugin" in roadmap
    assert "Exact-candidate READ, custody, and governed component semantic handoff are installed" in current
    assert "PR #517 one-hop breadcrumb navigation" in current
    assert "One canonical required existing-gap post-analysis cycle" in current


def test_searchos_slice_a_is_installed_and_navigation_remains_active() -> None:
    current = _collapsed(CURRENT_STATE)
    roadmap = _collapsed(ROADMAP)
    brief = _collapsed(QUERY_CONVERGENCE_BRIEF)

    assert QUERY_CONVERGENCE_BRIEF.is_file()
    assert "Status: completed Build" in brief
    assert f"Runtime/test commit: {QUERY_CONVERGENCE_RUNTIME_SHA}" in brief
    for phrase in (
        "SEARCHOS-QUERY-STRATEGY-AND-RECON-CONVERGENCE-01",
        "SearchPlanner proposals remain passive",
        "Ordinary initial semantic planning uses the selected fast-model SearchPlanner",
        "The model authors only the discriminated `direct_simple | components` semantic proposal",
        "DeterministicSearchPlannerAdapter` is an explicit validation-only fixture",
        "The typed `search_planner_adapter` `RunDeps` seam is the ordinary initial-model injection point",
        "Retained Scout and PlannerRevision dependency fields and modules are legacy/evaluation compatibility only",
        "ordinary `run_pipeline()` no longer reads them or accepts them in initial convergence",
        "Invalid JSON, schema, component/query structure, selected-model configuration, or model-call failure stops before proposal acceptance",
        "Future large-document support must enter this model boundary through bounded safe supplied-context references or summaries",
        "A transient, non-retained call wrapper supplies the current run's configured local base URL, OpenRouter key, `CostAccumulator`, and `search_planner` cost phase",
        "The existing underlying model-helper retry and endpoint-fallback policy is unchanged",
        "RunKernel initial AnswerContract acceptance",
        "SearchWorkPlan",
        "QueryPlan remains the sole exact executable-query authority",
        "searchos_initial_query_allocation_policy_v1",
        "one primary target",
        "two admitted initial candidates",
        "one immediate dispatch per accepted required component",
        "legacy global low/medium/high `2 / 2 / 3` values are not preserved",
        "The sparse ordinary language cannot author recon posture, dimensions, queries, Scout invocation, or PlannerRevision invocation",
        "The ordinary convergence API has no Scout or PlannerRevision adapter inputs",
        "initial planning has no routine PlannerRevision ContractAmendment caller or fallback",
        "Search-assisted factual resolution now belongs solely to QueryPlan job lineage",
        "No live provider, model, search, recon, fetch/read, or retrieval call was made",
    ):
        assert phrase in current

    for phrase in (
        "Required component count: 5",
        "Exactly one logical bounded initial planner invocation is made",
        "Planner transport matrix: selected OpenAI provider/model; exact OpenRouter key; exact Local base URL",
        "Planner cost accounting: 1 search_planner phase model-call entry; 0 double-counted entries",
        "Planner connection retention: 0 credential, endpoint, or accumulator objects in governed retained surfaces",
        "SEARCHOS-REQUIRED-SCOUT-ORDINARY-COMPOSITION-01",
        "The ordinary provider-neutral Scout adapter maps each authorized candidate",
        "Semantic interpretation of Scout hints and revision of the plan remains model-driven",
        "not semantic quality on arbitrary real-world requests",
        "Messy narrated one-intent request: 1 model-proposed and accepted component",
        "Invalid/unavailable model fixtures: 0 QueryPlan admissions; 0 search dispatches; 0 deterministic or legacy fallbacks",
        "Injected typed path: response-only planner -> Scout direction -> revision -> QueryPlan -> first offline search",
        "Primary queries admitted: 5",
        "later SearchJudgment",
        "No global `N + 5` research cap",
        "Technical-debt register disposition: No change",
        "SEARCHOS-READ-SOURCE-AND-CUSTODY-01",
        "Census ordinary and compatibility webpage-opening callsites",
        "response-only Linkup/Tavily offline fixtures",
        "Avoid DNS snapshots",
    ):
        assert phrase in brief

    assert "Superseded Build: SEARCHOS-REQUIRED-SCOUT-ORDINARY-COMPOSITION-01" in roadmap
    assert "Completed Build: SEARCHOS-QUERY-STRATEGY-AND-RECON-CONVERGENCE-01" in roadmap
    assert "Completed Build: SEARCHOS-READ-SOURCE-AND-CUSTODY-01" in roadmap
    assert "Completed Build: SEARCHOS-FIRST-WAVE-AND-ITERATIVE-JUDGMENT-CUTOVER-01" in roadmap
    assert "Completed Build: SEARCHOS-ONE-HOP-NAVIGATION-PRODUCT-ACTIVATION-01" in roadmap
    assert "## Active Decision Gate: SearchOS Carrier Consolidation + Product Proof" in roadmap
    assert "Phase 1 - Sparse uncertainty-aware planning" in roadmap
    assert "Phase 2 - Unified iterative acquisition" in roadmap
    assert "Phase 3 - Carrier consolidation + product proof" in roadmap
    assert "SEARCHOS-OPERATING-MODEL.md" not in _read(QUERY_CONVERGENCE_BRIEF)


def test_provider_offerings_census_is_current_complete_and_records_installed_routing() -> None:
    census = _read(CENSUS)
    normalized = _collapsed(CENSUS)

    for phrase in (
        "Status: current decision census",
        "Authority: owner-approved provider acquisition target doctrine",
        f"Verified-against-runtime: {PROVIDER_ROUTING_RUNTIME_SHA}",
        "Vendor-documentation-checked: 2026-07-16",
        "Vendor offered",
        "Adapter installed",
        "Ordinary enabled",
        "Ordinary reachable",
        "Authority granted",
        "## 2. Dated external offerings",
        "## 3. Consolidated required census matrix",
        "### 3.1 Offered, installed, enabled, reachable, and authoritative are separate",
        "## 4. Current adapter matrix",
        "## 5. Current ordinary-consumer matrix",
        "## 6. Current authority matrix",
        "## 7. Legacy-doctrine disposition matrix",
        "## 8. Linkup standard/deep decision",
        "## 9. Provider-synthesis closure",
        "## 10. Owner-approved target constellation",
        "## 11. Installation profiles and capability overlays",
        "## 12. Current sequencing owner",
        "## 14. Nonproofs",
        "## 15. Principal proof classification",
        "RETAIN",
        "REPLACE",
        "RETIRE",
        "DEFER_PENDING_PROOF",
        "Linkup `sourcedAnswer` precision context",
        "Tavily source-of-record default",
        "Phantom Tavily fallback",
        "Exa automatic general fan-out",
        "DISCOVER(lightweight_disambiguation)",
        "DISCOVER(independent_index)",
        "Source-of-record requirement",
        "current ordinary DISCOVER consumers; ProviderPlan, scheduling, and dispatch",
        "INSTALLED_FOUNDATION",
        "Minimal: Linkup",
        "Practical: Linkup + Serper",
        "Research: Linkup + Serper + Exa + Tavily",
        "Diversity: Linkup + Serper + Exa + Tavily + Brave",
        "Linkup-only remains valid",
        "Comparative proof may revise policy but is not required to select the target",
    ):
        assert phrase in census

    for provider in ("Linkup", "Tavily", "Exa", "Serper", "Brave"):
        assert provider in census
    for basis in (
        "CURRENT_RUNTIME",
        "CURRENT_TEST",
        "CURRENT_CANONICAL_DOC",
        "HISTORICAL_DOC",
        "OWNER_DECISION",
        "DATED_VENDOR_DOCUMENTATION",
        "INFERENCE",
    ):
        assert basis in census

    assert "completed semantic Scout and ordinary provider-synthesis retirement" in normalized
    assert "acquisition-runtime adapter convergence" in normalized
    assert "ordinary precision violation closed" in census
    assert "No ordinary authority or reachability" in census
    assert "Default disabled optional premium escalation" in census
    assert "Deep mode and complexity never authorize it" in census
    assert "Provider synthesis prohibition" in census
    assert "improved answer quality" in census
    assert "## 13. Unresolved decisions and live-proof register" in census
    assert "provider synthesis remains disabled" in census
    assert "Profile labels create no authority" in census
    assert "do not create automatic provider fan-out" in census
    assert PROVIDER_ROUTING_RUNTIME_SHA in census
    assert "OWNER_SELECTED_TARGET_NOT_INSTALLED" not in census
    assert "General and domain-targeted discovery are Linkup `standard/searchResults` first" in normalized

    roadmap = _read(ROADMAP)
    assert roadmap.count("## Active Next:") == 0
    assert roadmap.count("## Blocked Next:") == 0
    assert "## Active Decision Gate: SearchOS Carrier Consolidation + Product Proof" in roadmap
    assert "## Completed Repair: PROVIDER-CAPABILITY-ROUTING-FOUNDATION-01" in roadmap
    assert "Linkup `standard/searchResults` first" in roadmap

    historical_links = _links(CENSUS)
    assert historical_links
    for target in historical_links:
        assert target.is_file(), target


def test_current_roadmap_tracks_maintainer_remediation_sequence() -> None:
    roadmap = _read(ROADMAP)
    normalized = _collapsed(ROADMAP)
    s0 = roadmap.index("## Installed Foundation: S0")
    s1 = roadmap.index("## Installed Product Activation: S1")
    streamlit = roadmap.index("## Completed Remediation: Legacy Streamlit Ordinary-Product Retirement")
    economist = roadmap.index("## Completed Remediation: Legacy Economist Ordinary-Execution Retirement")
    census = roadmap.index("## Completed Proof: Post-Retirement Product Topology and Orchestrator Authority Census")
    validation_repair = roadmap.index("## Completed Repair: Validation and Execution-Surface Ergonomics Closure")
    mode_policy = roadmap.index("## Completed Repair: Mode-Policy Recovery Authority Containment")
    proposal = roadmap.index("## Completed Repair: SPECIALIST-PROPOSAL-INSTANCE-ADMISSION-HARDENING-01")
    structured_route = roadmap.index("## Completed Repair: STRUCTURED-LIST-ROUTE-QUALIFICATION-REPAIR-01")
    provider_census = roadmap.index("## Completed Audit: Provider Offerings, Adapter, and Legacy-Doctrine Census")
    scout_retirement = roadmap.index("## Completed Repair: LEGACY-SEMANTIC-SCOUT-ORDINARY-EXECUTION-RETIREMENT-01")
    provider = roadmap.index("## Completed Repair: PROVIDER-CAPABILITY-ROUTING-FOUNDATION-01")
    acquisition_runtime = roadmap.index("## Completed Repair: ACQUISITION-RUNTIME-READ-AND-ADAPTER-CONVERGENCE-01")
    acquisition_control = roadmap.index("## Completed Build: RUNKERNEL-ACQUISITION-CONTROL-FOUNDATION-01")
    discovery_retirement = roadmap.index("## Completed Build: INITIAL-DISCOVERY-SELECTIVE-FETCH-RETIREMENT-01")
    candidate_handoff = roadmap.index("## Completed Build: DISCOVER-RESULT-CANDIDATE-HANDOFF-CONVERGENCE-01")
    convergence = roadmap.index(
        "## Active Decision Gate: SearchOS Carrier Consolidation + Product Proof"
    )
    assert (
        s0
        < s1
        < streamlit
        < economist
        < census
        < validation_repair
        < mode_policy
        < proposal
        < structured_route
        < provider_census
        < scout_retirement
        < provider
        < acquisition_runtime
        < acquisition_control
        < discovery_retirement
        < candidate_handoff
        < convergence
    )
    assert "CLI/UI product composition" not in roadmap
    assert "fixed ordinary CLI product composition" in normalized
    assert "## Active Next: Separately Licensed Comparative Live Validation" not in roadmap
    assert "## Active Next: MODE-POLICY-RECOVERY-AUTHORITY-CONTAINMENT-01" not in roadmap
    assert roadmap.count("## Active Next:") == 0
    assert roadmap.count("## Blocked Next:") == 0
    assert "no product Specialist activation" in roadmap
    assert "Quantitative Specialist ordinary product activation is installed" in roadmap
    assert "fail-closed" in roadmap
    assert "reference and migration material only" in normalized
    assert "Saved-thread Streamlit follow-up is not a current product path" in normalized
    assert "Offline proof does not authorize live work" in normalized
    assert "This roadmap grants no live license" in normalized
    assert "transport-neutral conversation persistence" in roadmap
    assert "follow-up application service" in roadmap
    assert "intentional delivery adapter" in roadmap
    assert "must not be restored as a Streamlit callback" in normalized
    assert "No replacement UI framework has been selected" in normalized
    assert "claims that planned capabilities are installed" in roadmap
    assert "read-only, offline census" in normalized
    assert "without repairing, replacing, activating, or retiring" in normalized
    assert "changed no production runtime behavior" in normalized
    assert "provider offerings, adapter, and legacy-doctrine census" in (normalized.casefold())
    assert "target decisions, not completed runtime changes" in normalized
    assert "provider synthesis disabled" in normalized
    assert PROVIDER_ROUTING_RUNTIME_SHA in roadmap
    assert "deep/sourcedAnswer" in normalized
    assert "MODE-POLICY-RECOVERY-AUTHORITY-CONTAINMENT-01" in roadmap
    assert "Specialist Proposal-Instance Admission Hardening" in roadmap
    assert "This roadmap grants no live license" in normalized
    for marker in MARKERS:
        if marker != "PROVIDER-CAPABILITY-ROUTING":
            assert marker not in roadmap


def test_searchos_phase3_gate_and_searchplanner_record_are_exclusive() -> None:
    roadmap_raw = _read(ROADMAP)
    roadmap = _collapsed(ROADMAP)
    tracker = _collapsed(SEARCHPLANNER_TRACKER)
    current = _collapsed(CURRENT_STATE)

    active_gates = re.findall(
        r"^## Active Decision Gate: .+$",
        roadmap_raw,
        re.MULTILINE,
    )
    assert active_gates == [
        "## Active Decision Gate: SearchOS Carrier Consolidation + Product Proof"
    ]
    assert "Runtime-audit-through:" not in roadmap
    assert "Verified-against-runtime:" not in roadmap

    for transient in (
        "documentation truth-spine repair",
        "Project Source synchronization",
        "## Immediate Successor",
        "## Product-pulse safety sequence",
    ):
        assert transient not in roadmap

    for phrase in (
        "Option C modified into a unified iterative loop",
        "Phases 1 and 2 are installed at runtime/test checkpoint",
        "Phase 3 remains the selected next target",
        "Ordinary initial and iterative acquisition no longer executes",
        "`SearchWorkPlan` and `QueryProduction` remain temporary ordinary compatibility carriers pending Phase 3",
        "one RunKernel component worklist",
        "QueryPlan exact query + provider-neutral job class + component/slot lineage",
        "InterpretationBinding, clarification, semantic handoff, or honest blocker",
        "direct_simple | components",
        "Installed Phase 2 - Unified iterative acquisition",
        "supported-product evidence",
        "existing front- or back-half localization",
        "smallest owning repair",
        "another product pulse",
        "evidence-triggered front- or back-half optimization",
        "comparative provider/query calibration when warranted",
        "mode/provider policy selection",
        "MVP live shakeout and hardening",
        "release readiness",
        "No more than three consecutive merged implementation PRs",
        "After one non-product infrastructure PR",
        "confirmed capability gap",
        "deferred, evidence-triggered",
        "not an ordinary-product blocker",
        "approved hard prerequisite",
    ):
        assert phrase in roadmap

    for phrase in (
        "Status: completed repair record",
        "Phase-selection authority: none",
        "Repairs through PR #539 are complete",
        "Real-model SearchPlanner behavior remains unproved",
        "Future SearchPlanner component evaluation is evidence-triggered",
        "The current strategic decision gate belongs exclusively to",
    ):
        assert phrase in tracker

    for phrase in (
        "The installed result is organized by durable capability, not PR chronology",
        "Installed evaluator and validation infrastructure is not real-model component proof",
        "Current real-model SearchPlanner behavior remains unproved",
        "Current ordinary-CLI live product behavior remains unproved",
        "OPERATOR/VALIDATION surface",
    ):
        assert phrase in current


def test_semantic_scout_and_provider_synthesis_retirement_is_current_and_narrow() -> None:
    current = _collapsed(CURRENT_STATE)
    census = _collapsed(CENSUS)
    roadmap = _read(ROADMAP)

    for phrase in (
        "Legacy semantic Scout ordinary execution is retired",
        "does not select a Scout prompt, make a Scout model call, create Scout QueryPlan candidates",
        "scout_directed_continuation",
        "scout_continuation",
        "Evaluator, expander, generic QueryPlan admission",
        "Ordinary Linkup provider synthesis is also retired",
        "provider-written answers cannot enter ordinary Analyst input",
        "generic acquisition continues to reject `sourcedAnswer`",
        "Scrutineer-authorized `deep/searchResults` remediation, remains unchanged",
        "This repair installed no provider-capability routing",
        "No live validation was performed",
    ):
        assert phrase in current

    for phrase in (
        SCOUT_RETIREMENT_RUNTIME_SHA,
        "RETIRE — completed ordinary retirement",
        "No ordinary authority or reachability",
        "No ordinary prompt/model call, query candidate, gate selection, or retrieval dispatch remains",
        "ordinary precision violation closed",
        "lower-level `deep/sourcedAnswer` helper remains explicitly nonordinary",
        "Generic QueryPlan admission, RunKernel continuation authority, retrieval-stop policy",
        "Provider-capability routing foundation",
        "live provider, model, search, fetch/read or complete-app behavior",
    ):
        assert phrase in census

    assert roadmap.count("## Active Next:") == 0
    assert roadmap.count("## Blocked Next:") == 0
    assert "## Completed Repair: LEGACY-SEMANTIC-SCOUT-ORDINARY-EXECUTION-RETIREMENT-01" in roadmap
    assert "## Active Decision Gate: SearchOS Carrier Consolidation + Product Proof" in roadmap
    assert "## Active Next: LEGACY-SEMANTIC-SCOUT-ORDINARY-EXECUTION-RETIREMENT-01" not in roadmap
    assert roadmap.index("## Completed Repair: PROVIDER-CAPABILITY-ROUTING-FOUNDATION-01") < roadmap.index(
        "## Active Decision Gate: SearchOS Carrier Consolidation + Product Proof"
    )
    for noninstalled in (
        "provider-failure retry",
        "general Linkup Deep",
        "live-call authority",
    ):
        assert noninstalled in roadmap


def test_legacy_economist_ordinary_execution_retirement_is_current_and_narrow() -> None:
    current = _collapsed(CURRENT_STATE)
    roadmap = _collapsed(ROADMAP)
    strangler = _collapsed(ORCHESTRATOR_STRANGLER)
    safety = _collapsed(ECONOMIST_SAFETY)
    telemetry = _collapsed(ECONOMIST_TELEMETRY_POLICY)

    for text in (strangler, safety, telemetry):
        assert LEGACY_ECONOMIST_RETIREMENT_RUNTIME_SHA in text

    for phrase in (
        "ordinary CLI/backend composition no longer injects or executes",
        "ordinary orchestrator no longer gates, preflights, schedules, or calls",
        "current Linkup `searchResults` eligibility is now owned by the later provider-capability routing foundation",
        "passive handoff/trace fields remain repository-visible legacy material",
        "installs no replacement economic Specialist",
        "specialist.source_bound_calculation",
    ):
        assert phrase in current

    assert "Completed Remediation: Legacy Economist Ordinary-Execution Retirement" in roadmap
    assert "Completed Proof: Post-Retirement Product Topology" in roadmap
    assert "Completed Repair: Mode-Policy Recovery Authority Containment" in roadmap
    assert "Completed Repair: SPECIALIST-PROPOSAL-INSTANCE-ADMISSION-HARDENING-01" in roadmap
    assert "Completed Repair: STRUCTURED-LIST-ROUTE-QUALIFICATION-REPAIR-01" in roadmap
    assert "Active Decision Gate: SearchOS Carrier Consolidation + Product Proof" in roadmap
    assert "answer-producing paths" in roadmap
    assert "remaining orchestrator authority islands" in roadmap

    assert "no ordinary Economist execution callsite" in strangler
    assert "Legacy Economist compatibility data" in strangler
    assert "legacy pre-retirement safety contract" in safety
    assert "not a description of a current ordinary Economist stage" in safety
    assert "Economist code execution is categorically prohibited" in safety
    assert "No direct Economist-to-Author handoff" in safety
    assert "legacy/superseded Phase 10 policy note" in telemetry
    assert "no Economist runtime stage" in telemetry
    assert "do not represent a dormant runtime" in telemetry


def test_quantitative_specialist_has_one_current_owner_and_installed_boundaries() -> None:
    owner = CONCERN_OWNERS["canonical:quantitative-specialist-product-activation"]
    text = _collapsed(owner)
    current = _collapsed(CURRENT_STATE)
    for phrase in (
        "Installed runtime class: quantitative-specialist-product-activation-s1",
        "specialist.source_bound_calculation",
        "source_bound_numeric_literal_parser.v1",
        "two-hop proof",
        "component calculation priority before a later synthesis calculation",
        "legacy RunKernel calculation reducer remains compatibility support only",
        "quantitative_specialist_proposal_contract.v2",
        "specialist_need_proposal_v1",
        "Capability-request validation now occurs at admission",
        "required invalid proposal blocks its dependent claim",
        "optional invalid proposal contributes zero authority",
        "The same declarative facts build the model-visible contract and drive runtime proposal/request validation",
        "structured candidate record as primary and passage metadata as an exact fallback",
        "Missing facts remain `unknown`",
        "authoritative_current_clear",
        "contested_source_posture",
        "incomplete_lineage",
        "identical nonmaterial fields and `posture_digest`",
        "Component D-prime receives the exact ordinary component input without it",
        "full source catalogs, source material, and complete candidate records are absent from canonical RunKernel projections",
        "`docs/roadmap/CURRENT_ROADMAP.md`",
        "do not authorize live validation",
        "do not select work",
        "do not establish live correctness",
    ):
        assert phrase in text
    assert "next roadmap checkpoint" not in text.casefold()
    assert "Ordinary quantitative Specialist graph activation" not in current
    assert "Estimates, arbitrary formulas, conversions" in current


def test_multicomponent_owner_guards_phase5a_transport_contract() -> None:
    text = _collapsed(CONCERN_OWNERS["canonical:bounded-multicomponent-runtime"])
    for phrase in (
        "each child makes at most one provider request",
        "SDK retries are disabled",
        "endpoint, provider, and model fallback or switching are forbidden",
        "temperature `0.3`",
        "OpenAI Responses requests omit temperature",
        "caller-authored temperature is rejected",
        "Workers never receive `CostAccumulator`",
        "exactly once on the main thread before artifact reduction",
        "Provider-attempt accounting remains separate from product cost accounting",
    ):
        assert phrase in text


def test_project_sources_are_external_not_repository_paths() -> None:
    guidance = _read(GUIDANCE)
    assert "Project Sources are external context, not repository files" in guidance
    for path in (*DEFAULT_SPINE, *CONCERN_OWNERS.values()):
        text = _read(path)
        assert not re.search(r"\[[^]]*Project Sources?[^]]*\]\([^)]+\)", text)
        assert not re.search(r"Project Sources?[^\n]*`[^`]+\.md`", text)


def test_default_spine_does_not_link_to_historical_or_superseded_docs() -> None:
    for source in DEFAULT_SPINE:
        for target in _links(source):
            text = _read(target).casefold()
            assert "status: historical" not in text, (source, target)
            assert "status: superseded" not in text, (source, target)
