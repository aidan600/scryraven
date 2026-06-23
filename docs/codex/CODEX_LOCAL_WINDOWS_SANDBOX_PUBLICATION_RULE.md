# Codex Local Windows Sandbox Publication Rule

Status: Codex-visible publication guidance for local Windows ScryRaven phases.

## Preferred Local Codex Config

```toml
model_reasoning_effort = "xhigh"
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

## Operating Rule

Use the workspace sandbox for implementation, tests, inspection, and file edits.

Git metadata and publication commands should use exact approved commands or
whatever the current UI auto-review safely permits. Exact-command approvals may
include:

```text
git fetch origin --prune
git switch main
git switch -c <branch>
git add <specific paths>
git commit -m "<message>"
git push origin HEAD:<branch>
gh pr create ...
git branch -D <temporary-branch>
```

Do not request Full Access for ordinary ScryRaven implementation phases.

Do not request blanket approval or "do not ask again" for publication commands
unless the user explicitly changes workflow.

If an exact approved Git or publication command fails, stop and report the exact
command, exit code, and output.

Do not start auth repair, ACL repair, SSH-key setup, OAuth/device-flow
scripting, or sandbox surgery during implementation phases.

Do not merge, rebase, force-push, destructively clean, or repair
auth/ACL/sandbox during implementation.
