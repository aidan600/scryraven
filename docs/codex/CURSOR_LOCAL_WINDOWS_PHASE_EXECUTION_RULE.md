# Cursor Local Windows Phase Execution Rule

Status: Canonical owner for disposable Cursor local Windows phase execution.

This rule owns phase topology, workspace visibility, repository-edit boundaries,
command approvals, Windows-safe editing, external artifacts, and deterministic
phase close. It does not authorize live calls, private-data access, or product
changes.

## Phase topology and visibility

Use a short filesystem slug and this sibling layout:

```text
%USERPROFILE%\sr-phases\<short-phase-slug>\
  worktree\
  cache\
  tmp\
  evidence\
  final\
```

Set `PhaseRoot` to the slug directory and derive the absolute `Worktree`,
`Cache`, `Tmp`, `Evidence`, and `Final` paths from `PhaseRoot`, never from
`Worktree`. The worktree must be outside the main repository and outside every
path excluded by `.cursorignore`. Open `Worktree` as the Cursor project root and
confirm direct editor tools can read it. Cache, temporary files, evidence, final
packets, and product outputs belong in the sibling paths, never in the Git
worktree.

## Editing and command boundaries

Use direct editor or patch tools for every repository edit. If those tools
cannot see the worktree, stop and report the visibility failure; do not use
PowerShell, Python, Shell, or another command as a replacement repository
editor. Avoid text-mode whole-file rewrites that could alter Windows line
endings. Prefer small direct patches that preserve the existing line endings.

Keep inspection, editing, validation, commit, publication, and cleanup as
separate operations and commands. Commands must be single-purpose. Before an
unavoidable command approval, provide this short human-readable envelope:

```text
Purpose:
Command posture: READ-ONLY | LOCAL WRITE | GIT MUTATION | REMOTE MUTATION
Files read:
Files written:
Network:
Secrets/private data:
Git-history mutation:
Destructive operations:
```

Never recommend broad **Always Run** or persistent approval for PowerShell,
Python, Shell, Git, or GitHub commands. Request approval only for the exact
bounded command that needs it.

## External validation and product output

Configure tools so all generated artifacts remain outside `Worktree`. A
representative Python validation posture is:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:RUFF_CACHE_DIR = Join-Path $Cache 'ruff'

py -m pytest -q <focused-tests> `
  -p no:cacheprovider `
  --basetemp (Join-Path $Tmp 'pytest')
```

Product or evaluation commands must use an existing supported output control
pointing beneath `Evidence` or `Final`. A command that would default to
`Worktree\output` must not run until redirected. Do not invent a new product
environment variable to redirect it.

## Deterministic phase close

After the phase PR merges, use the repository-owned merged-phase cleanup command
rather than reconstructing an ad-hoc PowerShell cleanup sequence. See
[Post-merge local phase cleanup](ARCHITECTURE_GROOVE_PLAYBOOK.md#post-merge-local-phase-cleanup)
and [Windows Sandbox Publication Rule](CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md).

Pre-cleanup operator checklist remains:

1. Finish or stop all phase commands.
2. Record the expected Git status and final commit.
3. Re-root Cursor and terminal working directories away from `Worktree`.
4. Confirm the exact reviewed head, phase branch, and phase root before invoking
   `scripts/cleanup_merged_phase.ps1`.
5. Troubleshoot only from the helper's safe blocker output. Do not improvise with
   force removal, long-path deletion, process killing, reset, clean, `-D`, or
   `worktree remove --force`.
