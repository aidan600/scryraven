Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96A0_DOGFOOD_SEARCH_COST_METRICS).

# AG-96A0 Dogfood Search-Cost Metrics

Status: implemented as sanitized diagnostics-only report/trace instrumentation.

## Goal

Expose dogfood-visible search-efficiency metrics so official-source hit rate can
be judged per search without changing provider routing, query generation,
ranking, filtering, evidence selection, citation behavior, Author prose, or live
behavior.

## Sources Of Truth

- `execution_trace.mode`: run mode.
- `execution_trace.latency_seconds` or `execution_trace.timing.latency_seconds`:
  wall time.
- `execution_trace.cost.cost_by_phase` and `execution_trace.cost.calls_by_phase`:
  model/embedding cost and call totals, excluding search phases.
- `execution_trace.provider_diagnostics`: provider, role, logical attempt count,
  query count, result count, and accepted URL count.
- official/canonical visibility export: candidate, final evidence, and final
  citation counts.

## Available Metrics

- mode.
- wall time seconds.
- total LLM/model calls when phase-level cost call counts are present.
- total LLM/model cost when phase-level cost totals are present.
- search provider calls total.
- search provider calls by provider.
- search provider calls by role.
- retrieval/query variant count by role.
- provider result count.
- accepted URL count.
- official/canonical candidate count.
- final official/canonical evidence count.
- final official/canonical citation count.

## Unavailable Metrics

- search provider dollar cost remains unavailable because provider unit cost is
  not observable from sanitized diagnostics.
- LLM/model calls or cost are marked unavailable when only aggregate totals are
  visible and model/search separation cannot be derived.

## Privacy Boundary

The dogfood section is built only from existing sanitized in-memory trace fields.
It does not include raw provider payloads, raw prompts, secrets, environment
variables, DB rows, caches, private logs, local output packets, or full raw
traces. Provider diagnostics query previews are not rendered in the dogfood
metrics section.

## Next Dogfood Command

Run the next authorized local dogfood with the existing CLI shape, for example:

```powershell
py -m proplex "<authorized dogfood query>" --mode Balanced --output output\ag96a0_dogfood_report.md
```

Do not run live validation unless a follow-up phase explicitly scopes provider,
model, search budget, redaction, packet path, and stop conditions.
