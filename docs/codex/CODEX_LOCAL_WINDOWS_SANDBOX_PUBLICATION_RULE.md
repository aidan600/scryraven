# Codex Local Windows Sandbox Publication Rule

Status: Codex-visible publication guidance for local Windows ScryRaven phases.

## Preferred Local Codex Config

```toml
default_permissions = ":workspace"

[windows]
sandbox = "unelevated"
sandbox_private_desktop = false

[sandbox_workspace_write]
network_access = true
```

## Operating Rule

Use the workspace sandbox for implementation, tests, inspection, and file edits.

Git metadata and publication commands require approval for the exact command
being run. Exact-command approvals may include:

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
