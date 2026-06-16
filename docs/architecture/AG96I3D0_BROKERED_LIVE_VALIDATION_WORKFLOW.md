# AG-96I3D0 Brokered Live-validation Workflow

## Status

AG-96I3D0 adds repo-tracked, non-secret support for requesting a local
brokered live-validation run. It does not run live validation, tune search,
change provider routing, change provider selection, or alter product answer
behavior.

The tracked client is:

```text
scripts/request_live_validation_broker.py
```

It is a request client only. The private broker, provider credentials, local
environment, provider payloads, raw snippets, page text, private logs, cache
rows, DB rows, and full traces remain outside the repository.

## Boundary

The intended flow is:

```text
Codex/client
  -> localhost broker with one-shot token
  -> private broker outside repo
  -> private .env read by broker only
  -> one allowlisted child validation command
  -> sanitized ignored packet/JSON response
```

Codex may request a brokered run only when a phase brief licenses live
validation with an exact job, budget, redaction posture, and stop condition.
Codex may not read `.env`, provider keys, private logs, DB/cache rows, raw
provider payloads, raw snippets, raw page text, raw prompts, model responses, or
full traces. In brokered mode Codex may not call Brave, Tavily, Linkup, Exa,
OpenAI, or any public provider directly.

Broker jobs are allowlisted by `job_id`. Broker tokens are one-shot permission
slips for the local broker; they are not provider secrets and must not be
committed, logged, or pasted into chat. Live-call budgets must be displayed
before running. Retries are forbidden unless a later phase explicitly licenses
them. Broker output must be sanitized and written only to ignored paths such as
`output/`.

`output/` is ignored by the repo `.gitignore`, and the client verifies an
explicit `--output` path with `git check-ignore` before writing.

## Client Behavior

The client posts only to the configured broker URL, defaulting to:

```text
http://127.0.0.1:8765/run
```

Required inputs:

- `--job-id`;
- a token from `--token` or `SCRYRAVEN_BROKER_TOKEN`;
- `--confirm-live-provider-call`.

Before the POST, the client prints:

```text
This request may spend one live provider/search call if accepted by the broker.
```

The POST body is:

```json
{
  "job_id": "allowlisted-job-id",
  "confirm_live": true
}
```

The token is sent only as the `X-ScryRaven-Broker-Token` header. The client does
not print the token. HTTP 4xx/5xx broker JSON is printed as broker-provided
sanitized JSON and exits nonzero. Non-JSON broker responses are replaced with a
small local error object instead of printing response text.

## Permission Profile Example

This is an example shape for a brokered live-validation phase. Keep provider
domains absent in brokered mode; only localhost broker access is allowed.

```yaml
file_system:
  - path: "."
    access: write
  - path: "**/*.env"
    access: deny
  - path: ".env"
    access: deny
network:
  allow:
    - "http://127.0.0.1:8765"
    - "http://localhost:8765"
  deny:
    - "https://api.search.brave.com"
    - "https://api.tavily.com"
    - "https://api.linkup.so"
    - "https://api.exa.ai"
    - "https://api.openai.com"
```

## Operator Checklist

1. Start the private broker outside the repo.
2. Confirm `MAX_RUNS=1`.
3. Copy one-shot token.
4. Authorize the exact `job_id` and live-call budget.
5. Run the broker client.
6. Inspect sanitized output.
7. Do not paste tokens or secrets into chat.

Example command shape:

```powershell
$env:SCRYRAVEN_BROKER_TOKEN = "<one-shot broker token>"
py scripts\request_live_validation_broker.py `
  --job-id ag96i3d0-official-current-once `
  --confirm-live-provider-call `
  --output output\ag96i3d0_broker_response.json
```

## Closed Surfaces

AG-96I3D0 keeps these surfaces closed:

- provider routing and provider behavior;
- provider selection;
- query generation or mutation;
- retrieval ranking or filtering;
- fetch/read activation;
- model calls;
- AuthorExecutor;
- citation and product answer behavior;
- `core/pipeline_orchestrator.py` domain logic;
- source-specific IRS hardcoding;
- live validation.

## Validation Posture

Tests use mocked local HTTP behavior only. They prove the client refuses missing
tokens and missing spend acknowledgement, sends the expected POST body, keeps the
token in the broker header only, handles 200/400/403 JSON, refuses non-ignored
output paths, and statically avoids provider imports or environment-file
loading.

No raw provider payloads, raw snippets, raw page text, API keys, `.env` values,
DB/cache rows, private logs, or full traces are retained by this workflow.
