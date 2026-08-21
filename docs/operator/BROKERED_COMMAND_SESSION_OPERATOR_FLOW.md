# Brokered Command Session Operator Flow

Status: current operator guidance for the credentialed local-command doorman.
This document does not authorize a live provider, model, search, or product
call. It does not inspect or paste private environment-file contents.

## Durable Purpose Of The Broker / Doorman

When used without a more specific qualifier, "broker" and "doorman" mean
operator-side secret-custody infrastructure for cases where an LLM-controlled
process must run trusted ScryRaven work without receiving private credentials
in its controlling context.

The doorman is not part of the ScryRaven product runtime. Product modules do
not import or call it.

Normal human local use needs no doorman:

```text
human invokes normal ScryRaven
-> ScryRaven loads its normal local configuration
-> ScryRaven selects providers/models/routes
-> ScryRaven performs its own calls
```

LLM-controlled whole-product use:

```text
human approves one exact argv
-> operator doorman privately supplies the environment
-> the same normal ScryRaven CLI runs unchanged
-> ScryRaven performs its own normal product behavior
```

LLM-controlled component, test, or evaluation use:

```text
human approves one exact component/test/evaluator argv
-> operator doorman privately supplies the environment
-> that trusted command runs normally
```

Running subcomponents this way is an intentional part of the doorman's purpose.
It must not require launching the entire product merely to give a component the
ordinary environment it would otherwise receive.

This credentialed-command session is the general/default operator mechanism
when an LLM-controlled process needs to run an ordinary trusted repository
command with the private environment.

The doorman owns private environment-file custody, private child environment
construction, keeping credential values out of the controlling LLM
process/context, exact structured command execution where applicable,
secret-safe return/output handling, and process cleanup.

The doorman does not own provider selection, model selection, provider
availability, search or READ selection, route selection, query policy, test
policy, module policy, command policy, retry/fallback policy, attempt/token/
dollar budgets, product authorization, SearchOS, AnalystOS, RunKernel, evidence
custody, source authority, FAP, Author, or answer authority. It does not write
or check an allowlist. It does not decide who is allowed through the door. The
human/operator or the launched ScryRaven/test/evaluation command owns whatever
authorization and policy applies to that work.

The doorman is a credential-custody boundary, not a general sandbox against
malicious code. `shell=False` and exact-value redaction do not create such a
sandbox and must not be described as one.

The explicit-provider RPC surface in
[Generic Provider-Execution Broker Operator Flow](GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md)
is a specialized sibling mechanism for one versioned provider operation. Its
provider matrix, operations, request fuse, and route attestations apply only
to that RPC mechanism. They do not define this general doorman, restrict which
credentials may exist in the private environment used here, or constrain which
providers, models, searches, reads, embeddings, or other operations ordinary
ScryRaven may choose through installed product routing.

## Active Boundary

The operator-only launcher is:

```text
scripts/run_brokered_command_once.py
```

The doorman is not imported or called by ScryRaven. There is no provider,
executable, module, or command allowlist. The human approves the exact
structured argv.

Prefer this document for whole-product, pytest, evaluation, or component
commands that need ordinary environment access. Prefer
[Generic Provider-Execution Broker Operator Flow](GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md)
only when the licensed work is one explicit provider-RPC operation through the
tracked loopback broker.

## Bounded Whole-Product Launch Warning

When an LLM-controlled bounded ScryRaven command depends on credentials stored
in the repository's private `.env`, launch it through the canonical repository
environment mode:

```powershell
py scripts\run_brokered_command_once.py `
  --repo-root <REPO-ROOT> `
  --repo-env `
  ... `
  -- `
  python -m scryraven ...
```

`--repo-env` means the normalized repository root's `.env`, resolved inside the
approved operator-context doorman process. The legacy `--env-file <PRIVATE-ENV-FILE>`
form remains available for existing operator callers, but the Codex workflow
must use `--repo-env` and must not discover, stat, or pass an environment-file
path from the controlling Workspace Write process.

For an authorized credentialed command, Codex prepares the complete exact
broker-plus-target argv, requests one exact command-level escalation, and then
executes that command after the user approves it in the normal permission UI.
The user should approve the command in Codex; they should not be asked to open
PowerShell, run the broker manually, or paste its result back into the session.

Do not directly invoke:

```powershell
python -m scryraven --bounded-run-authorization ...
```

unless required provider credentials are already intentionally present in the
target process environment and the phase explicitly licenses direct execution.
Bounded CLI intentionally does not make the controlling agent parse or load the
private `.env`. Missing provider prerequisites caused by bypassing the broker
are operator/configuration failures, not PRODUCT evidence. This warning changes
launch posture only; the doorman remains responsible for secret custody and
process plumbing, not provider, route, token, attempt, dollar, or product
policy.

## Parent And Private-Child Graph

```text
operator
  -> public parent
       resolves/stats the canonical repo-root/.env (or legacy --env-file)
       without opening or parsing it
       validates absolute external output paths
       launches one private child with shell=False
  -> private child environment
       SCRYRAVEN_DOORMAN_ENV_FILE_PATH
       SCRYRAVEN_DOORMAN_NONCE
       mechanical PATH/temp roots only
  -> private child
       parses the dotenv file
       builds the ordinary target environment
       launches the exact argv with shell=False
       redacts exact secret values from captured output
       writes sanitized stdout/stderr outside the repository
  -> target command
       receives constructed environment, exact argv, and repo cwd
```

The public parent never opens the environment file and never receives raw
target stdout or stderr. Raw captured bytes exist only inside the private child
until exact-value redaction completes.

## Public Command Shape

The canonical Codex/operator shape uses the repository-local `.env`; do not
paste its contents or supply its path from an unprivileged preflight.

```powershell
py scripts\run_brokered_command_once.py `
  --repo-root <REPO-ROOT> `
  --repo-env `
  --stdout <ABSOLUTE-EXTERNAL-STDOUT> `
  --stderr <ABSOLUTE-EXTERNAL-STDERR> `
  --timeout-seconds <SECONDS> `
  [--replace-output] `
  -- `
  <exact> <argv> <tokens>...
```

The backwards-compatible operator-only alternative is the same shape with
`--env-file <PRIVATE-ENV-FILE>` in place of `--repo-env`. Exactly one of those
two environment sources is required.

Rules:

- `--` is required. Everything after it is the exact target argv.
- Every subprocess launch uses `shell=False`.
- `--stdout` and `--stderr` must be distinct absolute paths outside the
  repository. Existing files require `--replace-output`.
- The parent returns the target exit code, or `124` on bounded timeout, or `2`
  on sanitized configuration failure.
- On timeout, the private child terminates the Windows target process tree and
  still writes redacted captured output when available.

## Credential Custody

The parent resolves and stats the canonical normalized-repository `.env` (or
the legacy `--env-file` path) but never opens or parses it. The path crosses the
parent/child boundary only through the private child environment variable
`SCRYRAVEN_DOORMAN_ENV_FILE_PATH`. A one-session nonce is supplied only through
`SCRYRAVEN_DOORMAN_NONCE`.

The private child alone parses simple dotenv assignments and constructs the
target environment. Private launcher variables are removed before the target
starts. Exact values from secret-shaped names (`KEY`, `TOKEN`, `SECRET`,
`PASSWORD`, `PASSWD`, `CREDENTIAL`, `AUTH`) of sufficient length are redacted
from captured output as `[REDACTED]`. Non-secret text is preserved. Redaction
replaces exact unchanged values only; it is not a sandbox against a
deliberately malicious target.

## Fail-Closed Rules

Stop without launching the target when:

- the repository root or selected environment file is unavailable;
- the target argv separator or argv is missing;
- an output path is relative, inside the repository, identical for stdout and
  stderr, or would overwrite without `--replace-output`;
- the private child is started without the private session environment;
- timeout seconds are not positive.

Do not inspect the real private environment file, paste credentials into chat,
or route this launcher through product packages.
