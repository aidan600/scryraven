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
Proof class: STATIC_CONTRACT_PROOF / documentation-only.
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
VALIDATION_BUCKETS = CODEX / "VALIDATION_BUCKETS.md"
CI_ERGONOMICS = CODEX / "CI_VALIDATION_ERGONOMICS.md"
PROOF_GATE = CODEX / "PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md"
ROADMAP = ROOT / "docs" / "roadmap" / "CURRENT_ROADMAP.md"
CURSOR_PHASE = CODEX / "CURSOR_LOCAL_WINDOWS_PHASE_EXECUTION_RULE.md"
COMMAND_HYGIENE = ROOT / ".cursor" / "rules" / "scryraven-command-hygiene.mdc"
CURSORIGNORE = ROOT / ".cursorignore"


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


def test_temporal_owners_replace_workflow_roadmap_copying() -> None:
    guidance = _read(GUIDANCE)
    playbook = _read(PLAYBOOK)

    assert "../architecture/SCRYRAVEN_CURRENT_STATE.md" in guidance
    assert "../roadmap/CURRENT_ROADMAP.md" in guidance
    assert "docs/architecture/SCRYRAVEN_CURRENT_STATE.md" in playbook
    assert "docs/roadmap/CURRENT_ROADMAP.md" in playbook
    assert "This playbook owns workflow, not the product roadmap" in playbook


def test_guidance_map_stays_a_compact_resolvable_router() -> None:
    text = _read(GUIDANCE)

    assert len(text.splitlines()) < 200
    assert "## Current Productization Posture" not in text
    assert "Historical roadmap baseline" not in text

    targets = re.findall(r"\[[^]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)", text)
    assert targets
    for target in targets:
        assert (GUIDANCE.parent / target).resolve().is_file(), target


def test_ordinary_checkout_is_default_and_worktrees_are_opt_in() -> None:
    assert CURSOR_PHASE.is_file()
    root = _collapsed(AGENTS).casefold()
    playbook = _collapsed(PLAYBOOK).casefold()
    publication = _collapsed(PUBLICATION).casefold()
    worktree_rule = _collapsed(CURSOR_PHASE).casefold()
    guidance = _collapsed(GUIDANCE).casefold()
    hygiene = _collapsed(COMMAND_HYGIENE).casefold()
    addenda = _collapsed(ADDENDA).casefold()

    ordinary_owners = " ".join((root, playbook, publication, hygiene))
    for requirement in (
        r"c:\users\aidan\scryraven",
        "clean current `main`",
        "one feature branch",
        "same checkout",
    ):
        assert requirement in ordinary_owners

    for requirement in (
        "opt-in",
        "explicitly licensed",
        "outside every path excluded by `.cursorignore`",
        "direct editor or patch tools for every repository edit",
        "do not use powershell, python, shell, or another command as a replacement repository editor",
        "no automatic close or cleanup operation",
        "worktree removal or branch deletion requires separate, explicit maintainer authorization",
    ):
        assert requirement in worktree_rule

    assert "explicit dedicated cursor worktree exception" in addenda
    assert "explicitly opts into a dedicated worktree" in addenda
    assert "does not fill out this addendum" in addenda
    assert "optional cursor local windows worktree rule" in guidance
    assert "optional cursor local windows worktree rule" in hygiene

    retired_helper_stem = "_".join(("cleanup", "merged", "phase"))
    retired_helper_names = tuple(f"{retired_helper_stem}.{suffix}" for suffix in ("py", "ps1"))
    active_owners = "\n".join(
        _read(path)
        for path in (AGENTS, PLAYBOOK, PUBLICATION, GUIDANCE, CURSOR_PHASE, ADDENDA, COMMAND_HYGIENE)
    ).casefold()
    for retired_name in retired_helper_names:
        assert retired_name not in active_owners
        assert not (ROOT / "scripts" / retired_name).exists()
    assert "sr-phases" not in active_owners

    for safety in (
        "do not merge, rebase, force-push, delete branches",
        "generated, private, and transient data",
        "explicit phase authorization",
        "live calls",
    ):
        assert safety in " ".join((root, publication, hygiene))

    cursorignore_bytes = CURSORIGNORE.read_bytes()

    if cursorignore_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        cursorignore_text = cursorignore_bytes.decode("utf-16")
    else:
        cursorignore_text = cursorignore_bytes.decode("utf-8-sig")

    cursorignore_entries = {
        line.strip()
        for line in cursorignore_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "output/" in cursorignore_entries
    assert "cursor" not in _read(AGENTS).casefold()


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


def test_validation_consequences_and_hosted_ci_handoff_are_explicit() -> None:
    validation = _collapsed(VALIDATION_BUCKETS).casefold()
    ci = _collapsed(CI_ERGONOMICS).casefold()
    playbook = _collapsed(PLAYBOOK).casefold()

    for consequence in ("handoff_gate", "merge_gate", "diagnostic_only"):
        assert consequence in validation
    assert "full-suite collection guard" in ci
    assert "tiny execution-sentinel manifest" in ci
    assert "hosted asynchronous ci must not be classified as a handoff gate" in validation
    assert "candidate-only broad run against a known-red or unattributed baseline" in validation
    assert "not automatically a merge gate" in validation
    assert "exactly one hosted-ci status lookup" in playbook
    assert "run not yet visible in the single authorized snapshot" in playbook
    assert "strategy/review owns later hosted-ci inspection" in playbook
    for forbidden_action in (
        "do not run `gh run watch`",
        "sleep while waiting for ci",
        "poll repeatedly",
        "dispatch duplicate workflows",
    ):
        assert forbidden_action in playbook
    assert "take exactly one hosted-ci status snapshot and return immediately" in ci


def test_cloud_tasks_use_exact_clean_sha_without_branch_or_remote_assumptions() -> None:
    playbook = _collapsed(PLAYBOOK)

    for phrase in (
        "exact `git rev-parse HEAD` plus empty `git status --short` are authoritative",
        "Branch name is diagnostic only",
        "absence of `origin` or any Git remote is acceptable",
        "do not require `main`, `work`, detached HEAD",
        "`<NEW_MAIN_MERGE_SHA>` must not be launched",
        "stop and request a fresh checkout",
    ):
        assert phrase in playbook


def test_execution_surfaces_are_command_level_and_bound_product_claims() -> None:
    proof = _collapsed(PROOF_GATE)

    for surface in ("PRODUCT", "OPERATOR", "VALIDATION", "LEGACY"):
        assert f"`{surface}`" in proof
    assert "exact command or invoked branch, not merely the Python module" in proof
    assert 'python -m scryraven "<query>"' in proof
    assert 'python -m proplex "<query>"' in proof
    assert "Only PRODUCT execution can independently establish" in proof
    assert "Human-readable OPERATOR output is not ordinary product output" in proof
    assert "validation root itself is not a user product entrypoint" in proof
    assert "A LEGACY surface cannot establish current product behavior" in proof
    assert "Execution surface class:" in proof
    assert "Claim forbidden:" in proof


def test_roadmap_has_one_current_decision_gate() -> None:
    roadmap = _collapsed(ROADMAP)

    assert "Completed Proof: Post-Retirement Product Topology" in roadmap
    assert "Completed Repair: Validation and Execution-Surface Ergonomics Closure" in roadmap
    assert roadmap.count("## Active Decision Gate:") == 1
    assert "## Active Decision Gate: ANALYSTOS COMPONENT-PATH REPLACEMENT" in roadmap
    assert roadmap.count("## Active Next:") == 0
    assert "The current implementation phase is direct component-path replacement" in roadmap
    assert "This gate does not reopen topology selection" in roadmap
    assert "lawful SearchOS N=1 handoff" in roadmap
    assert "strong Component Analyst case/self-audit" in roadmap
    assert "direct RunKernel component admission" in roadmap


def test_product_evidence_harness_and_testing_rules_are_durable() -> None:
    agents = _collapsed(AGENTS)
    playbook = _collapsed(PLAYBOOK)
    proof = _collapsed(PROOF_GATE)
    addenda = _collapsed(ADDENDA)

    for phrase in (
        "No more than three consecutive merged implementation PRs",
        "After one non-product infrastructure PR",
        "Two failed attempts in the same preparation, authorization, launcher, workspace, or harness-consumption layer",
        "require architectural review before a third attempt",
        "Bounded fixes may continue inside one tracked phase",
        "third near-identical phase",
    ):
        assert phrase in agents
        assert phrase in playbook

    for level in ("Whole product:", "Front half:", "Back half:"):
        assert level in proof
    for evidence_class in (
        "STATIC_CONTRACT_PROOF",
        "OFFLINE_COMPONENT_PROOF",
        "OFFLINE_PRODUCT_PATH_PROOF",
        "MODEL_IN_THE_LOOP_COMPONENT_PROOF",
        "LIVE_COMPONENT_PROOF",
        "ORDINARY_CLI_PRODUCT_PROOF",
        "FULL_PRODUCT_PROOF",
    ):
        assert evidence_class in proof

    for field in (
        "Observed failure or approved hard prerequisite:",
        "Exact unresolved distinction:",
        "Existing owners already tried:",
        "Demonstrated observability or reproducibility gap:",
        "Production-owned boundary injected or observed:",
        "Named immediate consumer:",
        "Why the dependency cannot reasonably be completed in the consumer phase:",
        "Decision the harness will make:",
        "Duplicate-observation check:",
        "Maximum infrastructure PRs before consumption:",
        "Durable ownership, integration, replacement, or removal condition:",
        "Mandatory next supported-product checkpoint:",
        "Forbidden interpretation:",
    ):
        assert field in proof
        assert field in addenda

    assert "named consumer uses it -> evidence is produced -> a product or architecture decision changes" in proof
