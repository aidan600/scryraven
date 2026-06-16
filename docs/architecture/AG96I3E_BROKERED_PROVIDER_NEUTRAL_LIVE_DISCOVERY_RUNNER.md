# AG-96I3E Brokered Provider-neutral Live Discovery Runner

## Status

AG-96I3E adds a repo-tracked runner that a private broker can invoke later to
make one provider-neutral official/current discovery attempt and feed the
sanitized result set through the AG-96I3D diagnostics contract.

The runner is:

```text
scripts/ag96i3e_brokered_provider_neutral_discovery_validation.py
```

This phase adds the runner only. No live validation was run, no private broker
was started, and no Brave, Tavily, Linkup, Exa, OpenAI, fetch/read, model,
Author, citation, EvidenceLedger, Sufficiency, FinalAnswerPacket, or product
answer behavior was invoked.

## Runner Boundary

The runner accepts an explicit provider surface, query, broker job id, ignored
`output/` packet path, and `--max-results`. Live provider mode refuses to run
unless the operator passes:

```text
--confirm-live-provider-call
```

Immediately before a real provider call the runner prints exactly:

```text
This command may spend exactly one live provider/search call.
```

The live budget is fixed:

```json
{
  "max_provider_search_calls": 1,
  "max_fetch_read_attempts": 0,
  "max_model_calls": 0,
  "max_author_executor_calls": 0,
  "retries_allowed": false
}
```

The runner writes only sanitized packets under ignored repo `output/` paths. It
refuses non-`output/` destinations even if another gitignore rule would ignore
the path.

## Offline Smoke Mode

The runner also supports:

```text
--provider fixture
```

Fixture mode performs zero provider calls, requires no provider config, does not
read `.env`, does not start or call the broker, and writes the same AG-96I3E
packet shape. Fixture packets mark:

```json
{
  "live_validation_run": false,
  "fixture_mode": true,
  "provider_search_call_count": 0,
  "fetch_read_attempt_count": 0,
  "model_call_count": 0,
  "author_executor_call_count": 0
}
```

The fixture result set still flows through
`build_official_current_discovery_diagnostics`, so CLI path safety, packet
shape, redaction, rank selection, bridge-only posture, and diagnostics schema
can be exercised offline.

Example offline smoke command:

```powershell
py scripts\ag96i3e_brokered_provider_neutral_discovery_validation.py `
  --provider fixture `
  --query "offline fixture official current discovery smoke" `
  --job-id ag96i3e-offline-fixture-smoke `
  --output output\ag96i3e_offline_fixture_smoke_packet.json
```

## Later Broker Invocation

A private broker may later allowlist one job at a time and invoke the runner as
a child process. Example shapes:

```powershell
py scripts\ag96i3e_brokered_provider_neutral_discovery_validation.py `
  --provider brave `
  --query "<authorized provider-neutral query>" `
  --job-id ag96i3e-brave-discovery-once `
  --output output\ag96i3e_brave_discovery_once_packet.json `
  --max-results 5 `
  --confirm-live-provider-call
```

```powershell
py scripts\ag96i3e_brokered_provider_neutral_discovery_validation.py `
  --provider tavily `
  --query "<authorized provider-neutral query>" `
  --job-id ag96i3e-tavily-discovery-once `
  --output output\ag96i3e_tavily_discovery_once_packet.json `
  --max-results 5 `
  --confirm-live-provider-call
```

```powershell
py scripts\ag96i3e_brokered_provider_neutral_discovery_validation.py `
  --provider linkup `
  --query "<authorized provider-neutral query>" `
  --job-id ag96i3e-linkup-discovery-once `
  --output output\ag96i3e_linkup_discovery_once_packet.json `
  --max-results 5 `
  --confirm-live-provider-call
```

The broker, one-shot token, provider configuration, `.env`, provider keys, raw
payloads, raw snippets, page text, private logs, DB/cache rows, and full traces
remain outside the repository.

## Provider Support

Supported live provider surfaces:

- `brave`: existing `brave_reconnaissance` wrapper.
- `tavily`: existing `search_web_results` wrapper, called through its wrapped
  single-call function to avoid retry behavior.
- `linkup`: existing `search_linkup_results` wrapper, called through its wrapped
  single-call function to avoid retry behavior.

Deferred provider surface:

- `exa`: current wrapper uses `search_and_contents` with text retrieval, so this
  phase does not treat it as an unambiguous single search-only provider call.

No new provider dependencies were added.

## Why Discovery Remains Unconstrained

AG-96I3E always feeds diagnostics with:

```text
acquisition_mode=discovery_unconstrained
provider_job_kind=official_current_candidate_acquisition
authority_decision_present=false
```

It passes no `includeDomains` and no source-specific domain constraints.
`discovery_unconstrained` exists to prove whether a provider surface can discover
official/current candidates from the authorized query without being handed a
domain corridor first. Adding `includeDomains` in this mode would make the
result a corridor proof, not a discovery proof.

## Later Provider Comparison

A later explicitly authorized operator step can compare provider surfaces by
running one allowlisted job per provider and reviewing the same AG-96I3D fields:

- whether official/current candidates were visible;
- candidate rank and selected domain;
- bridge-only posture;
- failure layer;
- invalid or absent domain constraints;
- redaction posture and zero closed-surface counts.

This comparison should avoid search tuning or overfitting. Do not use one
provider run to mutate query text, add source-specific corridors, change product
routing, or alter retrieval ranking/filtering. Compare the provider surfaces
against the same provider-neutral query and diagnostics contract.

## Packet Shape

The sanitized packet includes:

- `phase_id: AG-96I3E`;
- `job_id`, `provider`, and `query`;
- fixed live budget;
- provider/search, fetch/read, model, and Author counts;
- `provider_result_set_diagnostics`;
- redaction posture;
- closed-surface flags;
- evidence boundary notes.

Raw snippets, raw content, raw provider payloads, keys, prompts, model outputs,
DB/cache rows, private logs, page text, and full traces are not retained.

Selected candidates are diagnostic observations only. Final evidence still
requires a later, separately authorized fetch/read/admission phase before any
candidate can become citation eligible or flow to final answer behavior.
