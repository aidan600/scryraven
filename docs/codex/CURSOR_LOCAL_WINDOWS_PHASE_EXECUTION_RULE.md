# Optional Cursor Local Windows Worktree Rule

Status: Opt-in safety owner for an explicitly licensed dedicated Cursor worktree.

The ordinary ScryRaven workspace is `C:\Users\aidan\ScryRaven`: clean current
`main` followed by one feature branch in the same checkout. This rule applies
only when a phase brief or maintainer explicitly licenses a dedicated worktree.
It does not create such a license or authorize live calls, private-data access,
product changes, publication, or branch deletion.

## Worktree location and visibility

The explicit phase license must name the dedicated worktree path. Do not infer
or invent a canonical parent or directory layout. The path must be outside the
ordinary checkout and outside every path excluded by `.cursorignore`. Open the
worktree as the Cursor project root and confirm direct editor tools can read it.

Generated artifacts do not belong in the Git worktree. Use the repository's
existing output controls and external cache and temporary paths. If the phase
also licenses evidence or final packets, place them in its explicitly named
external locations. Do not create directory ceremony that the phase does not
need.

## Editing and command boundaries

Use direct editor or patch tools for every repository edit. If those tools
cannot see the worktree, stop and report the visibility failure; do not use
PowerShell, Python, Shell, or another command as a replacement repository
editor. Avoid text-mode whole-file rewrites that could alter Windows line
endings. Prefer small direct patches that preserve the existing line endings.

Keep inspection, editing, validation, commit, and publication as
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

Configure tools so all generated artifacts remain outside the worktree. With
explicit external cache and temporary paths, a representative Python validation
posture is:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:RUFF_CACHE_DIR = Join-Path $ExternalCache 'ruff'

py -m pytest -q <focused-tests> `
  -p no:cacheprovider `
  --basetemp (Join-Path $ExternalTmp 'pytest')
```

Product or evaluation commands must use an existing supported output control
pointing to the explicitly licensed external location. A command that would
default to the worktree's `output` directory must not run until redirected. Do
not invent a new product environment variable to redirect it.

## Phase close

This exception defines no automatic close or cleanup operation. After merge,
follow the ordinary post-merge safety posture in the
[Windows Sandbox Publication Rule](CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md).
Any worktree removal or branch deletion requires separate, explicit maintainer
authorization. Never improvise with force removal, process killing, reset,
clean, `-D`, or `worktree remove --force`.
