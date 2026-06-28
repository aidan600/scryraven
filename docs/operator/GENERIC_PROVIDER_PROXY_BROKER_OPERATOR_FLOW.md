# Generic Provider-Proxy Broker Operator Flow

Status: reusable local operator guidance for one trusted-local generic
provider-proxy broker call. This document does not authorize live provider
calls by itself. A phase must separately license the query class, budget,
redaction posture, output path, and stop condition.

## Boundary

The broker is a dumb durable provider proxy:

- Policy lives in ScryRaven or the caller/harness.
- Secrets live in the private broker/operator boundary.
- The broker receives only `provider`, `operation`, `query`, and bounded
  `max_results`.
- The broker returns only sanitized provider result records.
- Raw provider payload and raw search response retention must remain false.

The broker must not know or require task ids, phase names, validation profiles,
RunKernel, EvidenceLedger, citation, Sufficiency, FAP, Author, or product-answer
policy.

## One-Run Helper

Preferred local operator command shape:

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

The helper:

- requires `--confirm-provider-call`;
- generates a temporary `SCRYRAVEN_BROKER_TOKEN` per run;
- does not print the token;
- loads `SERPER_API_KEY` from the current process or explicit local env files
  without printing it;
- starts the private broker on loopback as a subprocess;
- delegates the actual POST to `scripts/request_provider_proxy_broker.py`;
- writes only sanitized JSON under `output/`;
- stops the private broker subprocess after the request completes or fails.

The temporary broker token is an operator-local run credential, not a permanent
secret. Do not paste it into chat, docs, issues, pull requests, or committed
files.

`SERPER_API_KEY` stays private. It should be loaded only in the trusted local
operator or private broker boundary, never committed and never pasted.

## Sanitized Output

The generic client writes UTF-8 JSON without a BOM. Output must stay under
`output/` and must keep:

```json
{
  "raw_provider_payload_retained": false,
  "raw_search_response_retained": false
}
```

Allowed result fields are the generic sanitized record shape:

```text
title
url or link
domain
snippet
date or published_or_observed_date
rank or result_rank
call_index or provider_call_index
```

Any raw/private field, auth header, token, secret, log, DB/cache row, prompt,
full trace, raw provider payload, or raw search response is a fail-closed
condition.

## LIVE-RUN-01 Mapping Example

For the LIVE-RUN-01 shape, the broker helper produces generic sanitized output
only. LIVE-RUN-01 then maps that generic result list into the task-keyed
provider-results JSON expected by the harness.

Example shape:

```json
{
  "search-task:from-request-packet": [
    {
      "title": "Example Result",
      "url": "https://example.gov/current",
      "domain": "example.gov",
      "snippet": "Sanitized result snippet.",
      "result_rank": 1,
      "provider_call_index": 1
    }
  ]
}
```

Write that task-keyed provider-results JSON as UTF-8 without a BOM under
`output/`, then reduce through the task-specific harness:

```powershell
py scripts\ag_live_xaxis_validation_01a_live_run_01_harness.py `
  --reduce-sanitized-results `
  --request output\ag_live_xaxis_validation_01a_live_run_01_request.json `
  --provider-results output\<live-run-01-task-keyed-provider-results>.json `
  --execution-mode broker_live `
  --output output\ag_live_xaxis_validation_01a_live_run_01_output_packet.json
```

This mapping and reduction are task-specific. They do not belong inside the
broker and do not change the generic provider-proxy contract.

## Stop Rules

Stop without retry when any of these are true:

- the phase has not explicitly licensed live provider contact;
- the output path is outside `output/`;
- the broker URL is not loopback HTTP;
- `SERPER_API_KEY` is unavailable to the trusted local operator boundary;
- the broker returns unsupported provider/operation, token, config, cap, or
  provider errors;
- sanitized output contains raw/private fields or true raw-retention flags;
- completing the task would require direct provider calls, direct `.env`
  inspection, private logs, raw payloads, DB/cache rows, full traces, or
  task-specific broker policy.
