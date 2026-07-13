Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG_LIVE_OBSERVABILITY).

# AG-LIVE Validation Observability

Status: AG-LIVE-OBSERVE-01 packet projection contract.

AG-LIVE validation packets expose a single top-level
`validation_observability` field. The field is a sanitized projection over
existing runtime telemetry. It is not a provider router, source-custody policy,
retrieval planner, citation rule, or Author behavior change.

## Reused Surfaces

- `RunConfig` supplies public model/provider identity: fast, smart, and
  embedding provider/model names.
- `RunCapPolicy` supplies requested and observed cap counts.
- `provider_diagnostics_payload()` and
  `summarize_provider_diagnostics()` supply provider attempt summaries.
- `retrieval_pass_records` and `retrieval_loop_contract` supply retrieval pass
  counts, provider lists, stage, iteration, depth, and result-count settings.
- `FinalAnswerPacket` and final answer source telemetry supply cited source IDs,
  citation-eligible source IDs, source obligation status, and official custody
  summaries when already present.
- `RunOutcome.top_passages` and `RunOutcome.seen_urls` supply source URL and
  source-tier counts without serializing passage text.

## Packet Shape

`validation_observability` contains:

- `model_invocation_summary`
- `search_provider_summary`
- `retrieval_dispatch_summary`
- `source_material_summary`
- `source_custody_summary`
- `cap_and_retention_summary`

The projection serializes counts, IDs, URLs, provider names, model names,
bounded status fields, and diagnosis strings only. It does not serialize raw
prompts, raw model requests, raw model responses, raw provider payloads, full
execution traces, private logs, DB/cache rows, API keys, secrets, or passage
text.

## SOURCE-CUSTODY Diagnosis

For `AG-LIVE-SOURCE-CUSTODY`, a packet with official documentation citations and
`fetch_read_operations == 0` is diagnosed as:

`fetch_read_operations_zero_with_official_doc_citations`

That diagnosis does not fix source custody. It only makes the next validation
packet unambiguous enough to choose a product phase for fetch/read custody and
official source admission.
