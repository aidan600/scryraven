# Generic Provider-Execution Broker Operator Flow

Status: current reusable operator guidance. This document does not authorize a
live call. A phase must separately license the exact provider, operation, route,
prompt/query, timeout, retries, result/token cap, dollar ceiling, output path,
decision, and stop condition.

## Active Boundary

The sole active broker is the repository-tracked loopback server:

```text
scripts/provider_execution_broker.py
```

The preferred one-session helper is:

```text
scripts/run_provider_proxy_broker_once.py
```

The tracked generic client is:

```text
scripts/request_provider_proxy_broker.py
```

The versioned request and response families are
`scryraven_provider_execution_request_v1` and
`scryraven_provider_execution_response_v1`. Every request supplies an exact
provider and exact operation; `model.generate` also supplies the exact model.
No alias-only route is accepted.

The first-phase matrix is:

| Provider | Operation | Bounded transient output |
| --- | --- | --- |
| Serper | `search.query` | sanitized ranked search results |
| Tavily | `search.query` | sanitized ranked results and bounded provider-extracted text |
| OpenAI | `model.generate` | bounded output text plus exact input/output usage |

OpenRouter, LM Studio, Exa, LinkUp, Tavily extract/map/crawl, embeddings, and
alias-only routing remain pending.

## Credential And Session Custody

The helper normalizes and stats `--env-file` but never opens or parses it. Only
the tracked broker child receives that path. The broker process alone parses the
file and locates the credential mechanically required by the explicit provider.
The client child never receives the environment-file path or a provider
credential.

The helper generates one temporary session token. It passes the token to the
broker and client children only through separate child environments. The token
never appears in broker argv, client argv, output, exceptions, packets, or
documentation and is destroyed with the broker session.

The helper starts the broker on loopback, waits for bounded readiness, invokes
the tracked client, and stops the broker in every success or failure path. A
mechanical maximum-request fuse is session safety, not product or phase policy.

## Search Command Shape

Use a private local environment-file path. Do not paste its contents.

```powershell
py scripts\run_provider_proxy_broker_once.py `
  --provider serper `
  --operation search.query `
  --query "<EXACT-LICENSED-QUERY>" `
  --max-results 3 `
  --timeout-seconds 30 `
  --retry-cap 0 `
  --cost-ceiling-usd 0.05 `
  --output output\<sanitized-search-proof>.json `
  --env-file <PRIVATE-ENV-FILE> `
  --confirm-provider-call
```

Search output is a sanitized proof packet containing the approved result shape,
exact provider/operation attestation, physical attempt count, the
caller-authorized cost ceiling, and false raw-retention flags. It is not source
custody, evidence, citation eligibility, source-obligation satisfaction, or
answer material.

## Model Command Shape

```powershell
py scripts\run_provider_proxy_broker_once.py `
  --provider openai `
  --operation model.generate `
  --model <EXACT-MODEL> `
  --system-instructions "<BOUNDED-INSTRUCTIONS>" `
  --input-prompt "<BOUNDED-PROMPT>" `
  --reasoning-effort medium `
  --maximum-input-tokens <CALLER-CAP> `
  --max-output-tokens <CALLER-CAP> `
  --timeout-seconds <LICENSED-TIMEOUT> `
  --retry-cap 0 `
  --input-price-usd-per-million <CALLER-POLICY> `
  --output-price-usd-per-million <CALLER-POLICY> `
  --cost-ceiling-usd <CALLER-CEILING> `
  --expected-json-status <OPTIONAL-EXACT-STATUS-PROJECTION> `
  --output output\<sanitized-model-proof>.json `
  --env-file <PRIVATE-ENV-FILE> `
  --confirm-provider-call
```

The transient broker HTTP response may contain bounded `output_text`. The broker
and generic client do not log, print, cache, or persist it. The durable model
proof retains only output digest and character count, exact usage, exact
provider/model attestation, physical attempt count, caller-calculated
conservative cost, caller ceiling, an optional caller-requested parsed status
projection, and false-retention flags.

The broker returns usage and attestation only. Pricing and dollar ceilings
remain caller/evaluator owned.

## AnalystOS Evaluator Route

New AnalystOS addenda select:

```text
scripts.evaluation.brokered_model_origination_transport:create_brokered_model_origination_transport
```

The transport consumes exact `LiveAuthorization`, communicates only with the
loopback broker, requires exact usage and one-attempt attestation, calculates
cost through caller-owned policy, returns `EvaluationTransportResponse`, and
discards the broker envelope after transiently transferring model output to the
evaluator. The direct OpenAI transport is deprecated, unlicensed by default,
and has no active preparation/operator callsite.

## Fail-Closed Rules

Stop without direct fallback or retry when:

- the phase does not explicitly license the call;
- the environment file is unavailable;
- requested-provider configuration is unavailable;
- the broker URL is not loopback HTTP;
- provider, operation, model, base URL, timeout, retry, result/token cap, or
  route attestation is invalid;
- the output destination fails preflight;
- the session fuse is exhausted;
- exact model usage is missing;
- output would contain raw/private material or a true retention flag;
- completing the task would require direct provider contact, secret inspection,
  private logs, raw provider/model payloads, database/cache rows, or full
  traces.

The retired `scripts/request_live_validation_broker.py` job/profile bouncer
always fails closed and cannot dispatch.
