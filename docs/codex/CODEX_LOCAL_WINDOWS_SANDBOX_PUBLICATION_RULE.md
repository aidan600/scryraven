# Codex Local Windows Sandbox Publication Rule

Status: Codex-visible publication guidance for local Windows ScryRaven phases.

## Preferred Local Codex Config

The publication compatibility contract is the sandbox and approval posture
below. Model and reasoning/intelligence selection is a separate human choice and
is intentionally absent from this example.

```toml
approval_policy = "on-request"
approvals_reviewer = "auto_review"
sandbox_mode = "workspace-write"

[windows]
sandbox = "elevated"
sandbox_private_desktop = false

[sandbox_workspace_write]
network_access = true
```

The UI may show this as Custom / Workspace write. Custom is expected because
this combination does not match a simple preset. Do not mix this posture with
`default_permissions`. The old permission-profile / `default_permissions` style
and current `sandbox_mode` / `sandbox_workspace_write` style should not be
combined in one config.

This posture was first verified by local edit/delete, Git metadata, push
dry-run, and draft PR publication probes. It was then confirmed by real
ScryRaven phase PR #275, which edited, tested, committed, pushed, opened a draft
PR, passed CI, merged, and cleaned locally.

This still is not Full Access. Prompt-level hard stops still apply.

Reasoning/intelligence selection is independent from sandbox and publication
permissions. A task-profile or reasoning recommendation does not alter access,
scope, live-call authority, private-data access, or publication authority. The
human operator selects the actual setting; the repository does not force or
silently escalate it.

## Operating Rule

Use the workspace sandbox for implementation, tests, inspection, and file edits.

Git metadata and publication commands should use exact approved commands or
whatever the current UI auto-review safely permits. Phase-end push and draft-PR
creation require explicit phase authorization. Exact-command approvals may
include:

```text
git fetch origin --prune
git switch main
git switch -c <branch>
git add <specific paths>
git commit -m "<message>"
git push origin HEAD:<branch>
gh pr create ...
```

Do not request Full Access for ordinary ScryRaven implementation phases.

Do not request blanket approval or "do not ask again" for publication commands
unless the user explicitly changes workflow.

If an exact approved Git or publication command fails, stop and report the exact
command, exit code, and output.

Do not start auth repair, ACL repair, SSH-key setup, OAuth/device-flow
scripting, or sandbox surgery during implementation phases.

Do not merge, rebase, force-push, delete branches, destructively clean, mutate
`main`, or repair auth/ACL/sandbox during implementation. If the existing
publication path fails, report the exact failure rather than attempting
authentication, ACL, SSH, OAuth, or sandbox repair.
