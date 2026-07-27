# Provider-Execution Broker Activation Runbook

Status: current operator guidance for the tracked loopback-only broker. This
document does not authorize live provider contact by itself.

## Installed Components

```text
scripts/provider_execution_contract.py
scripts/provider_execution_broker.py
scripts/request_provider_proxy_broker.py
scripts/run_provider_proxy_broker_once.py
scripts/evaluation/brokered_model_origination_transport.py
```

The active doctrine is one explicit-route mechanical broker:

```text
caller resolves exact provider/model route
-> tracked loopback broker
-> mechanical provider adapter
-> transient normalized response
-> caller-owned interpretation and durable sanitization
```

The broker does not own jobs, phases, profiles, commands, aliases,
fast/smart/embed selection, semantic roles, capability judgment, provider
preference, query strategy, ranking, source admission, retrieval recovery,
Sufficiency, citation, FAP, Author, or dollar policy.

## Preferred One-Session Activation

Use the helper command shape in
[Generic Provider-Execution Broker Operator Flow](GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md).
The helper:

1. preflights the sanitized output path;
2. normalizes and stats the private environment-file path without opening it;
3. generates a temporary session token;
4. starts `scripts/provider_execution_broker.py` on loopback with the
   environment-file path and token supplied only through the broker-child
   environment;
5. waits for bounded readiness;
6. starts the tracked client with the token supplied only through the
   client-child environment;
7. stops the broker in every path; and
8. emits only sanitized status and proof output.

No private broker script copy, `--private-broker-path`, or `--token` argument is
part of the active flow.

## Contract

Every authenticated POST to `/run` uses:

```json
{
  "schema_version": "1",
  "request_kind": "scryraven_provider_execution_request_v1",
  "provider": "serper",
  "operation": "search.query",
  "query": "<bounded query>",
  "max_results": 3,
  "timeout_seconds": 30,
  "retry_cap": 0,
  "raw_provider_payload_retained": false,
  "raw_request_material_retained": false,
  "raw_response_material_retained": false,
  "raw_search_response_retained": false
}
```

`model.generate` replaces search fields with exact model, bounded system/input
text, optional authorized reasoning effort, maximum output tokens, and
`store=false`. The only accepted provider base URL in this first phase is the
bounded canonical OpenAI API base.

Optional `requested_route_alias` and `resolved_route_config_digest` fields are
echo-only attestation. They never select or modify the exact provider/model
route.

Every response uses
`scryraven_provider_execution_response_v1`, exact route attestation, physical
attempt count, false-retention flags, and exactly one operation member:
sanitized `results` for search or transient `output_text` plus exact `usage` for
model generation.

## Manual Broker Process

The one-session helper is preferred. A separately licensed private operator may
start the tracked broker manually only by supplying the temporary session token,
private environment-file path, and maximum-request fuse through that broker
process's environment. None may appear in argv or be pasted into chat,
documentation, issues, commits, or pull requests.

The client process receives only the temporary token through its own process
environment. It does not receive the environment-file path or credentials.

## Retired Paths

- `scripts/request_live_validation_broker.py` is a fail-closed compatibility
  tombstone. It performs no POST, provider dispatch, child command, job lookup,
  or validation-profile lookup.
- The former external private broker implementation and public private-copy
  template are not preferred or active.
- The direct OpenAI AnalystOS transport is deprecated and unlicensed by
  default. New addenda select the brokered transport.

Historical records under `docs/history/` remain unchanged and
nonauthoritative.

## Failure Handling

On missing requested-provider configuration, make no direct call and expose no
credential name or value. Report only:

```text
requested provider
missing_configuration
private operator action: ensure the broker environment file contains
configuration for the requested provider
```

Do not repair authentication, inspect the environment file, request secrets,
fall back to direct provider contact, or retry outside the exact live license.
