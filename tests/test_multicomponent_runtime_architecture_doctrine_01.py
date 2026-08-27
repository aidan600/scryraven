"""PRODUCT-PATH-REGRESSION: canonical multi-component doctrine posture.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: installed bounded default ordinary
multi-component answer path through hosted component parallel dispatch.
Runtime consumer: repo-visible architecture doctrine and Codex phase guidance.
Integration deadline: none; the bounded path is installed.
Exit condition: replace only with an equal-or-stronger guard over installed
component validation, synthesis, recovery, scheduling, and finalization.
Why this is not a shadow product path: it reads Markdown only and creates no
query, graph, semantic output, admission, readiness, packet, or prose.
Forbidden interpretation: passing is not runtime multi-component behavior,
live validation, citation/source-obligation satisfaction, or correctness.

Test path/node id: tests/test_multicomponent_runtime_architecture_doctrine_01.py
Proof class: installed product architecture static posture.
Validation bucket: phase_focus.
Surface guarded: canonical bounded multi-component architecture.
Runtime/product path guarded: docs consumed by future product phases; no runtime.
Expected cost: local Markdown reads only, well under one second.
Promotion posture: remain phase_focus.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "architecture"
CODEX = ROOT / "docs" / "codex"

CANONICAL = ARCH / "MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md"
ANALYSTOS = ARCH / "ANALYSTOS_OPERATING_MODEL.md"
CURRENT_STATE = ARCH / "SCRYRAVEN_CURRENT_STATE.md"
SEMANTIC_LOOP = ARCH / "RUN_CONTRACT_SEMANTIC_LOOP.md"
DAG = ARCH / "RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md"
WORKBENCH = ARCH / "CROSS_COMPONENT_ANALYST_WORKBENCH.md"
DPRIME = ARCH / "DPRIME_ARCHITECTURE.md"
FAP_AUTHOR = ARCH / "FAP_AUTHOR_BOUNDARY.md"
GUIDANCE = CODEX / "CODEX_GUIDANCE_MAP.md"
PLAYBOOK = CODEX / "ARCHITECTURE_GROOVE_PLAYBOOK.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collapsed(path: Path) -> str:
    return " ".join(_read(path).split())


def test_canonical_owner_has_current_metadata_and_supported_boundary() -> None:
    text = _read(CANONICAL)
    collapsed = _collapsed(CANONICAL)
    assert "Status: current" in text
    assert "Authority: canonical:bounded-multicomponent-runtime" in text
    assert "Default-read: no" in text
    assert "ordinary-bounded-multicomponent-factual-synthesis-v1" in text
    assert "Nonqualifying requests continue through the existing general multipart fallback" in collapsed
    assert "INSTALLED EXECUTABLE TOPOLOGY != SELECTED ANALYSTOS TARGET" in text
    assert ANALYSTOS.name in text
    assert "Mode:" not in text
    assert "Verdict target:" not in text


def test_direct_and_qualifying_lanes_are_selected_before_semantic_output() -> None:
    text = _collapsed(CANONICAL)
    for phrase in (
        "Lane selection occurs before canonical semantic production",
        "Direct ordinary lane",
        "Qualifying bounded multi-component lane",
        "component Analyst proposal",
        "Component Analyst case + self-audit",
        "Cross-Component Analyst synthesis proposal",
        "synthesis D-prime validation",
        "full Scrutineer challenge when triggered",
        "Sufficiency / FinalAnswerPacket / Author / RunOutcome",
        "Component finals are not handed to Author for ungoverned glue",
    ):
        assert phrase in text


def test_roles_remain_separate_and_shortcuts_are_closed() -> None:
    text = _collapsed(CANONICAL)
    for role in (
        "Component Analyst",
        "Cross-Component Analyst",
        "Synthesis D-prime",
        "Full Scrutineer",
        "RunKernel",
        "Sufficiency",
        "FinalAnswerPacket",
        "Author",
    ):
        assert role in text
    for phrase in (
        "D-prime verifies the claim.",
        "Scrutineer attacks the case.",
        "Validate or admit its proposal",
        "Invent synthesis",
        "Manufacture semantic output",
        "Generate, repair, validate, or reinterpret claims or synthesis",
        "Create synthesis, glue unadmitted outputs",
    ):
        assert phrase in text


def test_graph_and_answer_contract_boundaries_are_current() -> None:
    text = _collapsed(CANONICAL)
    for phrase in (
        "acyclic, n-capable in durable shape, serial-compatible",
        "bounded synthesis-of-synthesis",
        "Component and synthesis nodes are first-class",
        "synthesis-to-synthesis edges",
        "An empty edge set does not prove semantic independence",
        "an obligation the run owes the user",
        "A synthesis node does not automatically become an AnswerContract component",
        "ComponentWorkGraph V1 is the installed ordinary graph",
        "V0 graph compatibility implementation has been retired",
    ):
        assert phrase in text


def test_current_bounded_envelope_and_role_caps_are_exact() -> None:
    text = _read(CANONICAL)
    for phrase in (
        "Initial component nodes | 2–5",
        "Total component nodes after recovery | at most 5",
        "Synthesis nodes | 1–4",
        "Maximum synthesis depth | 2",
        "Missing-component recovery | at most 1",
        "Graph/AnswerContract amendment rounds | at most 1",
        "Component Analyst | 5",
        "Cross-Component Analyst | 3",
        "Synthesis D-prime | 8",
        "Scrutineer | 3",
    ):
        assert phrase in text


def test_recovery_is_bounded_and_selective() -> None:
    text = _collapsed(CANONICAL)
    for phrase in (
        "one recovery may add exactly one missing component",
        "re-enters ordinary research",
        "stales the affected synthesis closure",
        "carries forward exact unaffected admitted synthesis",
        "recomputes affected synthesis in topological order",
        "one fresh whole-case Scrutineer review",
        "do not reuse a prior validation or admission as direct authority for a new revision",
    ):
        assert phrase in text


def test_scheduler_lease_and_concurrency_invariants_are_visible() -> None:
    text = _collapsed(CANONICAL)
    for phrase in (
        "Every semantic call is RunKernel-scheduler-governed",
        "fixed ordinary CLI/UI product composition injects the S1 quantitative Specialist registry and execution policy and uses Scheduler V3",
        "Generic closed-default and no-need runs remain V2-compatible",
        "Component Analyst input packets include the repository-owned model-visible quantitative proposal contract and bounded `component_evidence`, but never a `quantitative_source_catalog`",
        "component contract binds the exact component target and `component_evidence`",
        "synthesis contract binds the same-artifact `synthesis_key` rule",
        "proposal is a sibling of ordinary component fields or `synthesis_proposals`",
        "graph admission does not upgrade them",
        "source material exists only in the execution catalog",
        "original Component Analyst packet and its resume binding stay catalog-free",
        "not retained in canonical graph, scheduler, work, result, log, or trace projections",
        "Cross input binding is reproofed unconditionally",
        "checks the existing initialization or recovery packet-digest authority",
        "Missing, incomplete, malformed, cross-run, stale, or inconsistent authority fails before reduction",
        "No packet, contract, catalog, source text, claim text, or complete candidate is newly retained or exported",
        "two-hop proof from each admitted component claim",
        "exact contiguous next batch",
        "Batch grant, cancellation, dispatch spend, and child-action publication are atomic",
        "predispatch cancellation returns an exact reservation",
        "Postdispatch failure and stale rejection remain spent",
        "zero active leases",
        "width 2 for canonical OpenAI/OpenRouter hosted providers",
        "Local and unsupported/conservative providers use width 1",
        "recovery, selective recomputation, and all graph-bound work remain serial",
        "physical completion order cannot choose canonical order",
    ):
        assert phrase in text


def test_phase5a_transport_privacy_sampling_and_cost_are_explicit() -> None:
    text = _collapsed(CANONICAL)
    for phrase in (
        "Installed Phase 5A Transport Contract",
        "each child makes at most one provider request",
        "SDK retries are disabled",
        "unsupported identities normalize conservatively to width 1 and fail closed with zero provider requests",
        "OpenRouter and Local chat requests use repository-owned temperature `0.3`",
        "OpenAI Responses requests omit temperature",
        "caller-authored temperature is rejected before a provider request",
        "raw prompts, raw model responses, raw provider payloads, credentials, private URLs, headers",
        "Workers never receive `CostAccumulator`",
        "Provider-attempt accounting remains separate from product cost accounting",
        "exactly once on the main thread before artifact reduction",
    ):
        assert phrase in text


def test_finalization_blocked_behavior_and_nonproofs_remain_narrow() -> None:
    text = _collapsed(CANONICAL)
    for phrase in (
        "Graph admission alone is not product completion",
        "FAP cannot create synthesis",
        "Author cannot glue missing or unadmitted component output",
        "sanitized non-Author terminal `RunOutcome`",
        "Malformed or unrelated invariant/infrastructure failures remain errors",
        "does not prove arbitrary-query support",
        "installed quantitative product contract is owned by",
    ):
        assert phrase in text


def test_companion_docs_crosslink_and_temporal_owners_stay_separate() -> None:
    for path in (CURRENT_STATE, SEMANTIC_LOOP, DAG, WORKBENCH, DPRIME, FAP_AUTHOR, GUIDANCE, PLAYBOOK):
        assert CANONICAL.name in _read(path), path.name

    current = _collapsed(CURRENT_STATE)
    assert "MC-P1-ORDINARY" in current
    assert "MC-P5A-STRICT-ONE-SHOT" in current
    assert "ordinary Sufficiency, FinalAnswerPacket, Author, RunOutcome" in current

    guidance = _read(GUIDANCE)
    assert "SCRYRAVEN_CURRENT_STATE.md" in guidance
    assert "CURRENT_ROADMAP.md" in guidance
    assert "canonical:bounded-multicomponent-runtime" in guidance
