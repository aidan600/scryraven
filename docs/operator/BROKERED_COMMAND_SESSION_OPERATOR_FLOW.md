# Brokered Command Session Operator Flow

Status: current operator guidance for the credentialed local-command doorman.
This document does not authorize a live provider, model, search, or product
call. It does not inspect or paste private environment-file contents.

## Active Boundary

The operator-only launcher is:

```text
scripts/run_brokered_command_once.py
```

The doorman is not imported or called by ScryRaven. It owns no provider, model,
route, test, token, cost, retry, query, SearchOS, AnalystOS, RunKernel,
evidence, or answer policy. There is no provider, executable, module, or
command allowlist. The human approves the exact structured argv.

The provider-operation HTTP broker and its operation matrix remain separate and
unchanged. Prefer
[Generic Provider-Execution Broker Operator Flow](GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md)
when the licensed work is one explicit provider operation through the tracked
loopback broker.

## Parent And Private-Child Graph

```text
operator
  -> public parent
       stats --env-file without opening or parsing it
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

Use a private local environment-file path. Do not paste its contents.

```powershell
py scripts\run_brokered_command_once.py `
  --repo-root <REPO-ROOT> `
  --env-file <PRIVATE-ENV-FILE> `
  --stdout <ABSOLUTE-EXTERNAL-STDOUT> `
  --stderr <ABSOLUTE-EXTERNAL-STDERR> `
  --timeout-seconds <SECONDS> `
  [--replace-output] `
  -- `
  <exact> <argv> <tokens>...
```

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

The parent normalizes and stats `--env-file` but never opens or parses it. The
path crosses the parent/child boundary only through the private child
environment variable `SCRYRAVEN_DOORMAN_ENV_FILE_PATH`. A one-session nonce is
supplied only through `SCRYRAVEN_DOORMAN_NONCE`.

The private child alone parses simple dotenv assignments and constructs the
target environment. Private launcher variables are removed before the target
starts. Exact values from secret-shaped names (`KEY`, `TOKEN`, `SECRET`,
`PASSWORD`, `PASSWD`, `CREDENTIAL`, `AUTH`) of sufficient length are redacted
from captured output as `[REDACTED]`. Non-secret text is preserved. Redaction
replaces exact unchanged values only; it is not a sandbox against a
deliberately malicious target.

## Fail-Closed Rules

Stop without launching the target when:

- the repository root or environment file is unavailable;
- the target argv separator or argv is missing;
- an output path is relative, inside the repository, identical for stdout and
  stderr, or would overwrite without `--replace-output`;
- the private child is started without the private session environment;
- timeout seconds are not positive.

Do not inspect the real private environment file, paste credentials into chat,
or route this launcher through product packages.
