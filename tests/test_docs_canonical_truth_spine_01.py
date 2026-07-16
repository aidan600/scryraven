"""Static guards for the canonical documentation truth spine.

Test path: tests/test_docs_canonical_truth_spine_01.py
Proof class: docs_only.
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
GUIDANCE = DOCS / "codex" / "CODEX_GUIDANCE_MAP.md"
CURRENT_STATE = ARCH / "SCRYRAVEN_CURRENT_STATE.md"
ROADMAP = DOCS / "roadmap" / "CURRENT_ROADMAP.md"
QUARANTINE = ARCH / "AG_CURRENT_PATH_QUARANTINE_01.md"
ORCHESTRATOR_STRANGLER = ARCH / "AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md"
ECONOMIST_SAFETY = DOCS / "architecture_safety_contract.md"
ECONOMIST_TELEMETRY_POLICY = (
    DOCS / "economist_shadow_telemetry_promotion_policy.md"
)
CONCERN_OWNERS = {
    "canonical:dprime-role-contract": ARCH / "DPRIME_ARCHITECTURE.md",
    "canonical:run-contract-semantic-loop": ARCH / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    "canonical:component-dag-scheduling-concurrency": (
        ARCH / "RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md"
    ),
    "canonical:fap-author-boundary": ARCH / "FAP_AUTHOR_BOUNDARY.md",
    "canonical:bounded-multicomponent-runtime": (
        ARCH / "MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md"
    ),
    "canonical:specialist-graph-substrate": ARCH / "SPECIALIST_GRAPH_SUBSTRATE.md",
    "canonical:quantitative-specialist-product-activation": (
        ARCH / "AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md"
    ),
    "canonical:quantitative-finalization-containment": (
        ARCH / "AG_S1_QUANTITATIVE_FINALIZATION_CONTAINMENT_01.md"
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
)
QUANT_FINALIZATION_RUNTIME_SHA = (
    "4e095c7db287ab29fbe748bdd5c24cf4f2545e15"  # pragma: allowlist secret
)
QUANT_LINEAGE_RUNTIME_SHA = (
    "bba0d16313944b742251298b4fc929b4ceb55d76"  # pragma: allowlist secret
)
CURRENT_STATE_RUNTIME_SHA = (
    "7bbfff0f604096e3437bfdadc3dd8b81ec56b57c"  # pragma: allowlist secret
)
LEGACY_ECONOMIST_RETIREMENT_RUNTIME_SHA = CURRENT_STATE_RUNTIME_SHA
QUANT_CONTAINMENT_RUNTIME_SHA = (
    "5e6fa705e0e7e13662c7860dcb5bea573b8ac0c2"  # pragma: allowlist secret
)
S1_RUNTIME_SHA = (
    "4232c4570908065adf589ec2b44be695f82fce56"  # pragma: allowlist secret
)
RUNTIME_SHA_BY_CONCERN = {
    "canonical:dprime-role-contract": QUANT_LINEAGE_RUNTIME_SHA,
    "canonical:run-contract-semantic-loop": QUANT_FINALIZATION_RUNTIME_SHA,
    "canonical:component-dag-scheduling-concurrency": S1_RUNTIME_SHA,
    "canonical:fap-author-boundary": QUANT_LINEAGE_RUNTIME_SHA,
    "canonical:bounded-multicomponent-runtime": QUANT_FINALIZATION_RUNTIME_SHA,
    "canonical:specialist-graph-substrate": S1_RUNTIME_SHA,
    "canonical:quantitative-specialist-product-activation": (
        QUANT_LINEAGE_RUNTIME_SHA
    ),
    "canonical:quantitative-finalization-containment": (
        QUANT_CONTAINMENT_RUNTIME_SHA
    ),
}


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


def test_temporal_authorities_are_unique_and_default_read() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    for authority, owner, verified_runtime in (
        (
            "canonical:current-installed-state",
            CURRENT_STATE,
            CURRENT_STATE_RUNTIME_SHA,
        ),
        (
            "canonical:current-roadmap",
            ROADMAP,
            LEGACY_ECONOMIST_RETIREMENT_RUNTIME_SHA,
        ),
    ):
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]
        assert "Status: current" in _read(owner)
        assert "Default-read: yes" in _read(owner)
        assert f"Verified-against-runtime: {verified_runtime}" in _read(owner)


def test_concern_authorities_are_unique_current_and_default_no() -> None:
    markdown = tuple(DOCS.rglob("*.md"))
    for authority, owner in CONCERN_OWNERS.items():
        text = _read(owner)
        verified_runtime = RUNTIME_SHA_BY_CONCERN[authority]
        claim = f"Authority: {authority}"
        claimants = [path for path in markdown if claim in _read(path)]
        assert claimants == [owner]
        assert "Status: current" in text
        assert "Default-read: no" in text
        assert f"Verified-against-runtime: {verified_runtime}" in text


def test_quantitative_finalization_inventory_does_not_overclaim_saved_thread() -> None:
    current = _read(CURRENT_STATE)
    containment = _read(
        CONCERN_OWNERS["canonical:quantitative-finalization-containment"]
    )

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
        for phrase in forbidden:
            assert phrase not in text, (path, phrase)

    dprime = _collapsed(CONCERN_OWNERS["canonical:dprime-role-contract"])
    assert "ordinary bounded multi-component path consumes both component D-prime and synthesis D-prime" in dprime
    assert "Review and admission alone do not prove" in dprime
    assert "approved general ordinary component Analyst" not in dprime

    semantic = _collapsed(CONCERN_OWNERS["canonical:run-contract-semantic-loop"])
    assert "PR #" not in _read(CONCERN_OWNERS["canonical:run-contract-semantic-loop"])
    assert "Workers propose. RunKernel authorizes and reduces." in semantic

    dag = _collapsed(CONCERN_OWNERS["canonical:component-dag-scheduling-concurrency"])
    assert "ComponentWorkGraph V1 is installed" in dag
    assert "future shape" not in dag.casefold()
    assert "next BUILD must install ordinary consumption" not in dag

    fap = _collapsed(CONCERN_OWNERS["canonical:fap-author-boundary"])
    assert "When FAP readiness is blocked, Author does not run." in fap
    assert "generic D-prime admission is not numeric rendering authority" in fap
    assert "future answer rendering" not in fap.casefold()

    containment = _collapsed(
        CONCERN_OWNERS["canonical:quantitative-finalization-containment"]
    )
    assert "The two authority kinds are" in containment
    assert "Generic admission is not an authority kind." in containment
    assert "`admitted_quantitative_claim`" not in containment


def test_hardened_quantitative_component_boundary_is_current_and_narrow() -> None:
    containment = _collapsed(
        CONCERN_OWNERS["canonical:quantitative-finalization-containment"]
    )
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
            "No route-qualification repair was performed.",
            "No acquisition-completeness repair was performed.",
            "No provider or model changed.",
            "No hardened synthesis path was activated.",
        ):
            assert phrase in text

    for phrase in (
        "No S1 proposal or invocation policy expanded.",
        "No new Specialist capability was added.",
        "Broad live correctness, answer quality, and production stability remain unproved.",
        "Ordinary synthesis-origin S1 authority remains owned by the ordinary ComponentWorkGraph / synthesis D-prime / ordinary FinalAnswerPacket path.",
    ):
        assert phrase in containment
        assert phrase in current


def test_current_state_has_all_installed_capability_markers() -> None:
    current = _read(CURRENT_STATE)
    for marker in MARKERS:
        assert current.count(f"`{marker}`") == 1


def test_current_roadmap_tracks_maintainer_remediation_sequence() -> None:
    roadmap = _read(ROADMAP)
    normalized = _collapsed(ROADMAP)
    s0 = roadmap.index("## Installed Foundation: S0")
    s1 = roadmap.index("## Installed Product Activation: S1")
    streamlit = roadmap.index(
        "## Completed Remediation: Legacy Streamlit Ordinary-Product Retirement"
    )
    economist = roadmap.index(
        "## Completed Remediation: Legacy Economist Ordinary-Execution Retirement"
    )
    census = roadmap.index(
        "## Completed Proof: Post-Retirement Product Topology and Orchestrator "
        "Authority Census"
    )
    validation_repair = roadmap.index(
        "## Completed Repair: Validation and Execution-Surface Ergonomics Closure"
    )
    mode_policy = roadmap.index(
        "## Active Next: MODE-POLICY-RECOVERY-AUTHORITY-CONTAINMENT-01"
    )
    proposal = roadmap.index("### Specialist Proposal-Instance Admission Hardening")
    structured_route = roadmap.index(
        "### Structured-List Route Qualification Repair"
    )
    provider = roadmap.index("### Provider Capability and Acquisition-Routing Proof")
    convergence = roadmap.index("### Bounded Final-Custody Convergence")
    live = roadmap.index("### Separately Licensed Complete-App Live Shakeout")

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
        < provider
        < convergence
        < live
    )
    assert "CLI/UI product composition" not in roadmap
    assert "fixed ordinary CLI product composition" in normalized
    assert "## Active Next: Separately Licensed Complete-App Live Shakeout" not in roadmap
    assert roadmap.count("## Active Next:") == 1
    assert "no product Specialist activation" in roadmap
    assert "Quantitative Specialist ordinary product activation is installed" in roadmap
    assert "fail-closed" in roadmap
    assert "reference and migration material only" in normalized
    assert "Saved-thread Streamlit follow-up is not a current product path" in normalized
    assert "Offline proof does not authorize live work" in normalized
    assert "this roadmap grants no live license" in normalized
    assert "transport-neutral conversation persistence" in roadmap
    assert "follow-up application service" in roadmap
    assert "intentional delivery adapter" in roadmap
    assert "must not be restored as a Streamlit callback" in normalized
    assert "No replacement UI framework has been selected" in normalized
    assert "claims that planned capabilities are installed" in roadmap
    assert "read-only, offline census" in normalized
    assert "without repairing, replacing, activating, or retiring" in normalized
    assert "changed no production runtime behavior" in normalized
    assert "Verified-against-runtime` remains unchanged" in roadmap
    assert "this roadmap grants no live license" in normalized
    for marker in MARKERS:
        assert marker not in roadmap


def test_legacy_economist_ordinary_execution_retirement_is_current_and_narrow() -> None:
    current = _collapsed(CURRENT_STATE)
    roadmap = _collapsed(ROADMAP)
    strangler = _collapsed(ORCHESTRATOR_STRANGLER)
    safety = _collapsed(ECONOMIST_SAFETY)
    telemetry = _collapsed(ECONOMIST_TELEMETRY_POLICY)

    for text in (current, roadmap, strangler, safety, telemetry):
        assert (
            "7bbfff0f604096e3437bfdadc3dd8b81ec56b57c"  # pragma: allowlist secret
            in text
        )

    for phrase in (
        "ordinary CLI/backend composition no longer injects or executes",
        "ordinary orchestrator no longer gates, preflights, schedules, or calls",
        "Independent Linkup eligibility and call arguments are unchanged",
        "passive handoff/trace fields remain repository-visible legacy material",
        "installs no replacement economic Specialist",
        "specialist.source_bound_calculation",
    ):
        assert phrase in current

    assert "Completed Remediation: Legacy Economist Ordinary-Execution Retirement" in roadmap
    assert "Completed Proof: Post-Retirement Product Topology" in roadmap
    assert "Active Next: MODE-POLICY-RECOVERY-AUTHORITY-CONTAINMENT-01" in roadmap
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
    owner = CONCERN_OWNERS[
        "canonical:quantitative-specialist-product-activation"
    ]
    text = _collapsed(owner)
    current = _collapsed(CURRENT_STATE)
    for phrase in (
        "Installed runtime class: quantitative-specialist-product-activation-s1",
        "specialist.source_bound_calculation",
        "source_bound_numeric_literal_parser.v1",
        "two-hop proof",
        "component calculation priority before a later synthesis calculation",
        "legacy RunKernel calculation reducer remains compatibility support only",
        "quantitative_specialist_proposal_contract.v1",
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
        "do not select the next phase",
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
