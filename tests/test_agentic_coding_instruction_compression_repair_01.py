"""Static guards for the vendor-neutral coding-agent instruction contract.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: future phase execution that reaches its
named ordinary consumer without shadow workflow machinery.
Runtime consumer: coding agents reading root and routed repository guidance.
Why ordinary product-path work cannot be done directly: this REPAIR is limited
to repo-visible instruction integrity; runtime Python is closed.
Integration deadline: AG-MULTICOMPONENT-ORDINARY-END-TO-END-SYNTHESIS-01.
Exit condition: replace only with equal-or-stronger static guards over the
canonical instruction owners.
Why this is not a shadow product path: Markdown is inspected; no alternate
ScryRaven execution path is created.
Forbidden interpretation: passing does not prove runtime behavior, live
validation, citation behavior, or product correctness.

Test path: tests/test_agentic_coding_instruction_compression_repair_01.py
Proof class: docs_only.
Validation bucket: phase_focus.
Surface guarded: coding-agent instruction ownership and publication posture.
Runtime/product path guarded: repo-doc operating system only.
Expected cost: local text reads, under one second.
Promotion posture: remain phase_focus.
Demotion/retirement condition: an equal-or-stronger docs posture guard replaces it.
Why not fast_pr: detailed doctrine repair guard, not ordinary runtime PR tax.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
CODEX = ROOT / "docs" / "codex"
PLAYBOOK = CODEX / "ARCHITECTURE_GROOVE_PLAYBOOK.md"
PROFILE = CODEX / "AGENTIC_CODING_OPERATING_PROFILE.md"
TEMPLATE = CODEX / "PHASE_BRIEF_TEMPLATE.md"
ADDENDA = CODEX / "PHASE_BRIEF_ADDENDA.md"
GUIDANCE = CODEX / "CODEX_GUIDANCE_MAP.md"
PUBLICATION = CODEX / "CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md"
NEXT = "AG-MULTICOMPONENT-DYNAMIC-GRAPH-RECOVERY-01"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collapsed(path: Path) -> str:
    return " ".join(_read(path).split())


def test_root_is_compressed_vendor_neutral_and_human_controlled() -> None:
    text = _read(AGENTS)
    lower = text.casefold()
    collapsed = " ".join(lower.split())

    assert len(text.splitlines()) < 170
    for vendor_or_selector in (
        "gpt-",
        "claude",
        "cursor",
        "fable",
        "model_reasoning_effort",
        "xhigh",
        "extra high",
        "ultra",
    ):
        assert vendor_or_selector not in lower

    assert "human operator selects the actual model" in collapsed
    assert "must not force or silently escalate" in collapsed
    assert "reasoning level never expands scope, permissions" in collapsed
    assert "publication authority" in collapsed
    assert "private-data access" in collapsed


def test_outcome_sizing_and_long_task_contract_are_durable() -> None:
    combined = "\n".join(_read(path) for path in (AGENTS, PLAYBOOK))
    collapsed = " ".join(combined.split())

    for phrase in (
        "A PR may be large when it implements one coherent product outcome",
        "Do not split solely because",
        "Small PRs remain valid and desirable",
        "Outcome:",
        "Constraints:",
        "Verification:",
        "review the entire diff",
        "final skeptical-maintainer review",
    ):
        assert phrase in combined or phrase in collapsed


def test_profile_is_advisory_and_delegation_is_single_writer_first() -> None:
    text = _read(PROFILE)
    lower = text.casefold()
    collapsed = " ".join(lower.split())

    for profile in ("ROUTINE", "DEEP", "INTENSIVE", "DELEGATED"):
        assert profile in text
    for mapping in ("Medium", "High", "Extra High", "Ultra"):
        assert mapping in text

    assert "human operator selects" in collapsed
    assert "does not force or silently escalate" in collapsed
    assert "independent from sandbox and publication permissions" in collapsed
    assert "main agent is the sole architectural integrator and default writer" in collapsed
    assert "read-heavy exploration" in collapsed
    assert "parallel edits to overlapping files are forbidden" in collapsed


def test_phase_template_is_compact_and_conditional_detail_is_routed() -> None:
    template = _read(TEMPLATE)
    addenda = _read(ADDENDA)

    assert len(template.splitlines()) < 120
    assert "PHASE_BRIEF_ADDENDA.md" in template
    assert "Outcome:" in template
    assert "Constraints:" in template
    assert "Verification:" in template
    assert "Publication authorization:" in template
    for heading in (
        "Proof-only leash",
        "Live-validation license",
        "New harness or non-product scaffold",
        "High-custody migration inventory",
        "Delegated execution",
    ):
        assert heading in addenda


def test_publication_compatibility_is_preserved_without_reasoning_coupling() -> None:
    root = _read(AGENTS)
    publication = _read(PUBLICATION)
    collapsed = " ".join(publication.split())

    assert "CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md" in root
    for setting in (
        'approval_policy = "on-request"',
        'approvals_reviewer = "auto_review"',
        'sandbox_mode = "workspace-write"',
        'sandbox = "elevated"',
        "network_access = true",
    ):
        assert setting in publication
    assert "model_reasoning_effort" not in publication
    assert "Reasoning/intelligence selection is independent" in collapsed
    assert "Phase-end push and draft-PR creation require explicit phase authorization" in collapsed
    assert "Do not merge, rebase, force-push, delete branches" in collapsed


def test_current_product_checkpoint_remains_canonical() -> None:
    for path in (GUIDANCE, PLAYBOOK):
        assert NEXT in _read(path), path.name


def test_guidance_map_stays_a_compact_resolvable_router() -> None:
    text = _read(GUIDANCE)

    assert len(text.splitlines()) < 200
    assert "## Current Productization Posture" not in text
    assert "Historical roadmap baseline" not in text

    targets = re.findall(r"\[[^]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)", text)
    assert targets
    for target in targets:
        assert (GUIDANCE.parent / target).resolve().is_file(), target


def test_convergence_replaces_fixed_red_cycle_stopping() -> None:
    profile = _collapsed(PROFILE).casefold()
    root = _collapsed(AGENTS).casefold()

    for phrase in (
        "failure count",
        "failed node ids",
        "causal classification",
        "shrinking, flat, or expanding",
        "next bounded correction",
        "red focused test is diagnostic information",
        "flat or expanding for two consecutive focused cycles",
        "do not use a fixed maximum red-cycle count",
    ):
        assert phrase in profile
    assert "stop on divergence" in root
    assert "do not stop merely because tests remain red" in root


def test_causal_cluster_and_stronger_validator_rules_are_bounded() -> None:
    profile = _collapsed(PROFILE).casefold()

    for phrase in (
        "bounded producer, schema, reducer, consumer, and focused test path",
        "newly touched file is not automatically an unrelated surface",
        "preserve a stronger validator",
        "instead of weakening validation solely",
        "another product responsibility",
        "genuine architecture decision",
    ):
        assert phrase in profile


def test_checkpoints_are_coherent_and_cannot_masquerade_as_completion() -> None:
    profile = _collapsed(PROFILE).casefold()
    playbook = _collapsed(PLAYBOOK).casefold()

    for phrase in (
        "before affected-lane, full-suite, or baseline-parity validation",
        "require a reviewable local commit",
        "last coherent checkpoint clean",
        "exact reported unresolved edit",
        "checkpoint is not phase completion",
        "never use one to hide incoherence or bypass exact-diff",
    ):
        assert phrase in profile
    assert "checkpointing does not claim completion" in playbook


def test_surface_licensing_and_workflow_scale_are_explicit() -> None:
    profile = _collapsed(PROFILE).casefold()
    addenda = _read(ADDENDA)

    for phrase in (
        "name the producer, authority transition or reducer, downstream consumer",
        "permits only directly necessary files",
        "never unrelated product systems",
        "rigid file allowlists only for genuinely tiny",
        "do not force intensive ceremony onto tiny work",
        "substantial phases use the standard convergence-and-checkpoint workflow posture",
        "the intensive agent execution profile additionally expects multiple coherent milestones",
    ):
        assert phrase in profile
    assert "## Large-phase execution posture" in addenda
    assert "Agent execution profile: ROUTINE | DEEP | INTENSIVE | DELEGATED" in addenda
    assert "Large-phase workflow posture:" in addenda
    assert "Execution profile: STANDARD | INTENSIVE" not in addenda


def test_validation_jobs_and_acceptance_owner_are_separate_and_stable() -> None:
    playbook = _collapsed(PLAYBOOK).casefold()

    for phrase in (
        "implementation, affected-lane validation, publication, full-suite or baseline-parity validation, and final review as separate jobs",
        "do not immediately repeat the broad run",
        "do not rerun the full suite after every isolated correction",
        "one strategy/review chat owns the active phase acceptance target",
        "approve merge, request one focused fix, reject or revert, or stop for architectural decision",
    ):
        assert phrase in playbook


def test_safety_stops_and_checkpoint_nonpermissions_remain_explicit() -> None:
    profile = _collapsed(PROFILE).casefold()
    combined = " ".join((_collapsed(AGENTS), profile, _collapsed(PUBLICATION))).casefold()

    for phrase in (
        "live calls",
        "secrets",
        "private data",
        "destructive git",
        "unrelated product systems",
        "publication permission",
        "product correctness",
        "do not merge, rebase, force-push, delete branches",
    ):
        assert phrase in combined
