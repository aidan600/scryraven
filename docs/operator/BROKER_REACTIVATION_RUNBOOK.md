# Broker Reactivation Runbook

Status: local operator guidance for the private ScryRaven provider-proxy broker.
This is documentation only; it does not authorize committing private broker
files, tokens, provider keys, `.env` contents, raw prompts, raw provider
payloads, raw model responses, private logs, DB rows, cache rows, or full traces.

The durable broker doctrine is intentionally small:

- The broker is not ScryRaven authority.
- The broker is not a validation-profile governor.
- The broker is not job-id policy.
- The broker is a tiny private key-holding provider proxy.

Known local broker script:

```text
C:\Users\aidan\ScryRavenLiveBroker\scryraven_live_broker.py
```

Known local broker URL:

```text
http://127.0.0.1:8765/run
```

Tracked generic provider-proxy client:

```text
scripts/request_provider_proxy_broker.py
```

Preferred one-run local operator helper:

```text
scripts/run_provider_proxy_broker_once.py
```

Detailed reusable flow:

```text
docs/operator/GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md
```

Public non-secret private-broker template:

```text
docs/examples/scryraven_live_broker_private_template.py
```

Required local environment variable for the client shell:

```text
SCRYRAVEN_BROKER_TOKEN
```

The one-run helper generates this token automatically for the private broker
subprocess and the tracked client. The token is temporary, is not a permanent
secret, and must not be pasted into chat or committed.

## Broker Contract

The tracked client posts a generic provider request:

```json
{
  "request_kind": "generic_provider_proxy_request",
  "provider": "serper",
  "operation": "search",
  "query": "<string>",
  "max_results": 5,
  "raw_provider_payload_retained": false,
  "raw_search_response_retained": false
}
```

The private broker may enforce only durable generic safety:

- local token required;
- loopback only;
- supported provider;
- supported operation;
- bounded `max_results`;
- no raw payload return;
- no shell commands;
- no arbitrary file access;
- no secrets printed.

The private broker must not require or govern:

- job-id allowlists;
- AG phase names;
- validation profiles;
- ScryRaven roadmap awareness;
- RunKernel awareness;
- EvidenceLedger awareness;
- citation, Sufficiency, FAP, or Author awareness.

The broker response must contain only sanitized provider results with these
fields:

```text
title
url or link
domain
snippet
date or published_or_observed_date
rank or result_rank
call_index or provider_call_index
provider_extracted_text
provider_extracted_text_sanitized
provider_extracted_text_bounded
provider_extracted_text_char_count
provider_extracted_text_digest
provider_extracted_content_type
raw_provider_payload_retained: false
raw_search_response_retained: false
```

Broker output is not source custody, evidence, citation eligible, or
source-obligation satisfaction. Bounded `provider_extracted_text`, when present,
is sanitized provider record material only. Only a downstream product path, under
its own licensed custody, readability, and candidate-fit gates, may convert that
material into source-bound custody.

For Tavily, provider-extracted page material may cross the private
broker-to-client boundary only as bounded provider record material and must be
written by the tracked client as `provider_extracted_text`, not `raw_content`.

## Preferred One-Run Helper

For a separately licensed trusted-local provider call, prefer the reusable
helper. It starts the private broker on `127.0.0.1:8765`, generates a temporary
broker token, loads the selected provider key, currently `SERPER_API_KEY` or
`TAVILY_API_KEY`, from the current process or explicit local operator env files
without printing it, delegates to the generic client, writes sanitized output
under `output/`, and stops the broker subprocess afterward.

```powershell
py scripts\run_provider_proxy_broker_once.py `
  --provider serper `
  --operation search `
  --query "<trusted-local approved query>" `
  --max-results 5 `
  --output output\<sanitized-provider-proxy-response>.json `
  --broker-url http://127.0.0.1:8765/run `
  --private-broker-path C:\Users\aidan\ScryRavenLiveBroker\scryraven_live_broker.py `
  --env-file C:\Users\aidan\ScryRavenLiveBroker\.env `
  --confirm-provider-call
```

Use the lower-level client command only when the private broker is already
running in a token-loaded shell.

## Manual Restart Broker

Run from a private PowerShell shell that already has the broker token and
provider credentials loaded. Do not paste tokens or provider keys into chat or
commit them.

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

py C:\Users\aidan\ScryRavenLiveBroker\scryraven_live_broker.py
```

If the broker runs in a separate terminal, keep that terminal open while making
the provider-proxy request.

## Lower-Level Broker Client Command Shape

Run from the repository root in a shell that can see `SCRYRAVEN_BROKER_TOKEN`:

```powershell
py scripts\request_provider_proxy_broker.py `
  --broker-url http://127.0.0.1:8765/run `
  --provider serper `
  --operation search `
  --query "<trusted-local approved query>" `
  --max-results 5 `
  --confirm-provider-call `
  --output output\<sanitized-provider-proxy-response>.json
```

The tracked client refuses non-loopback broker URLs, missing tokens, missing
confirmation, unsupported provider/operation values, unbounded `max_results`,
output paths outside `output/`, raw/private response fields, and raw-retention
flags set to true.

Use only sanitized broker output under `output/`. Do not paste or commit tokens,
secrets, `.env` contents, provider keys, raw prompts, raw provider payloads, raw
model responses, private logs, DB rows, cache rows, or full traces.

Future task-specific harnesses must transform sanitized broker output after the
broker returns. Do not add task-specific mapping, reduction, job ids, validation
profiles, or answer policy to the broker.

## Codex Acknowledgement Template

Paste this shape to Codex after the private broker has been manually updated and
restarted for an explicitly licensed trusted-local run:

```text
Broker acknowledgement for generic provider-proxy run:

The private broker is running locally at:
http://127.0.0.1:8765/run

Broker script:
C:\Users\aidan\ScryRavenLiveBroker\scryraven_live_broker.py

Use only the tracked client:
py scripts\request_provider_proxy_broker.py --broker-url http://127.0.0.1:8765/run --provider serper --operation search --query "<trusted-local approved query>" --max-results 5 --confirm-provider-call --output output\<sanitized-provider-proxy-response>.json

Budget:
- max broker requests: operator-owned local fuse
- provider operation: serper search
- max_results: bounded by the tracked client and private broker
- retries: none unless a later phase explicitly licenses a generic retry cap

Rules:
- Do not read `.env`.
- Do not print or request secrets.
- Do not call provider APIs directly.
- Do not run search/fetch/retrieval outside the brokered provider operation.
- Do not accept arbitrary commands from the tracked client.
- Do not require job ids, AG phase names, validation profiles, RunKernel, EvidenceLedger, citation, Sufficiency, FAP, or Author state.
- Use only sanitized broker output under `output/`.
- If the broker returns token error, missing config, max-runs exhausted, unsupported provider/operation, max-results error, raw/private field error, or any provider error, fail closed and do not retry.
```

## Obsolete Pattern

The old phase/job-specific broker allowlist pattern is obsolete as durable
broker guidance. A private broker may still keep a local one-shot fuse or run
counter, but it should not key durable safety on `job_id`, AG phase names,
validation profiles, ScryRaven roadmap state, RunKernel, EvidenceLedger,
citation, Sufficiency, FAP, or Author concepts.

## Fail Closed Rules

Fail closed and do not retry when any of these are true:

- `SCRYRAVEN_BROKER_TOKEN` is missing from the shell running the tracked client.
- The broker URL is not loopback HTTP.
- The requested provider or operation is unsupported.
- `max_results` is out of bounds.
- The output path is outside `output/`.
- The broker returns token error, missing config, max-runs exhausted,
  unsupported provider/operation, or any provider error.
- The tracked sanitized output returns or implies raw provider payload
  retention, raw search response retention, raw/private fields, secrets, logs,
  DB/cache rows, prompts, full traces, or headers.
- The requested action would require direct provider API calls from Codex.
- The requested action would require reading `.env`, secrets, provider keys,
  private logs, DB/cache rows, raw prompts, raw provider payloads, raw model
  responses, or full traces.

Codex may not see `SCRYRAVEN_BROKER_TOKEN` if it runs in a different shell from
the broker or the operator terminal. If Codex cannot see the token, either run
the broker client manually from the token-loaded shell or relaunch Codex from
that shell. Do not paste the token into chat.

Private broker files are local/private operational files and should not be
committed to the ScryRaven repository.
