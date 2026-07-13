Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I3D0_BROKERED_LIVE_VALIDATION_WORKFLOW).

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

The product-owned validation profile registry is:

```text
core/validation_profiles.py
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
them. Broker output must be sanitized and written only under the repo `output/`
directory.

`output/` is ignored by the repo `.gitignore`, and the client verifies an
explicit `--output` path is both inside repo `output/` and gitignored before
writing.

## Client Behavior

The client posts only to a configured local broker URL with scheme `http` and
host `127.0.0.1`, `localhost`, or `::1`, defaulting to:

```text
http://127.0.0.1:8765/run
```

Required inputs:

- `--job-id`;
- `--profile`, defaulting to `AG-LIVE-SMOKE`;
- a token from `--token` or `SCRYRAVEN_BROKER_TOKEN`;
- `--confirm-live-provider-call`.

Before the POST, the client prints the selected profile's bounded live budget.
For the default `AG-LIVE-SMOKE` profile, that looks like:

```text
This request may spend the selected validation profile's bounded provider/model/search/fetch/read budget if accepted by the broker.
Selected validation profile budget: profile=AG-LIVE-SMOKE, max_scryraven_runs=1, max_search_dispatches=2, max_fetch_read_operations=3, max_author_model_calls=1, max_smart_search_judgment_model_calls=0, max_retries=0
```

Those cap values are profile/spec-owned, not global broker limits. Future
approved profiles may carry different caps, and the broker should enforce the
selected request's approved budget/fuse without inventing product policy.

The POST body is:

```json
{
  "job_id": "allowlisted-job-id",
  "confirm_live": true,
  "request_kind": "approved_validation_profile",
  "profile_request": {
    "validation_profile": "AG-LIVE-SMOKE",
    "approved_product_entrypoint": "scripts/ag_live_bound_01_bounded_product_runner.py",
    "query_constraints": {
      "intent": "official Python documentation exact API defaults smoke query",
      "primary_query": "...",
      "backup_query": "...",
      "mode": "Balanced",
      "include_domains": ["docs.python.org"]
    },
    "cap_policy": {
      "surface": "RunConfig.cap_policy",
      "values": {"max_scryraven_runs": 1}
    },
    "retention_posture": "sanitized_packet_only_with_ordinary_retention_suppressed",
    "packet_schema": "ag_live_bound_01_bounded_product_runner_v1",
    "expected_packet_criteria": ["..."]
  }
}
```

The token is sent only as the `X-ScryRaven-Broker-Token` header. The client does
not print the token. HTTP 4xx/5xx broker JSON is printed as broker-provided
sanitized JSON and exits nonzero. Non-JSON broker responses are replaced with a
small local error object instead of printing response text.

The broker remains responsible for credentialed private-shell invocation,
private `.env` loading, one-run fuse enforcement, and returning sanitized
results only. The broker must not own provider policy, routing/depth/order,
query generation, retrieval ranking/filtering, citation policy, semantic
sufficiency, Author behavior, or product answer policy.

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
  --profile AG-LIVE-SMOKE `
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
token in the broker header only, handles 200/400/403 JSON, refuses `.env` or
other non-`output/` paths even when gitignored, refuses non-ignored docs paths,
and statically avoids provider imports or environment-file loading.

No raw provider payloads, raw snippets, raw page text, API keys, `.env` values,
DB/cache rows, private logs, or full traces are retained by this workflow.
