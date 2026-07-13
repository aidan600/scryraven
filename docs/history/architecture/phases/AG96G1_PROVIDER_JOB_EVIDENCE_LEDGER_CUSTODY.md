Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96G1_PROVIDER_JOB_EVIDENCE_LEDGER_CUSTODY).

# AG-96G1 Provider-Job EvidenceLedger Custody

## Status

AG-96G1 connects AG-96F1 provider-job execution handoff records to
RunKernel-owned EvidenceLedger candidate custody.

This phase is evidence-custody only. It does not change QueryPlan admission,
query text generation, provider routing, provider selection, search depth,
retrieval execution, retrieval ranking/filtering, prompts, citations, Author
behavior, final answers, SearchJudgment, SufficiencyJudgment, QuantWorkUnit
extraction/calculation, or live validation.

## Why G1 Follows F1

AG-96F1 made the SearchWork-to-retrieval handoff traceable:

```text
SearchWork component
-> source obligation
-> provider-job hint
-> QueryPlan admitted query
-> provider-job execution record
-> existing retrieval/search handoff
```

That still stopped before EvidenceLedger. The missing G1 step is candidate
custody:

```text
SearchWork component
-> source obligation
-> provider-job execution record
-> QueryPlan admitted query
-> retrieved source candidate
-> EvidenceLedger candidate custody record
-> source requirement / custody gap projection
```

Provider-job execution records explain why an existing query was handed to the
retrieval loop. G1 explains whether already-returned retrieval/search records can
be represented as candidate-level EvidenceLedger observations for the source
obligations carried by that provider-job handoff.

## Bridge Shape

`core/provider_job_evidence_ledger_bridge.py` is a pure bridge. It consumes only
already-computed, trace-safe facts:

- AG-96F1 provider-job execution handoff records;
- QueryPlan trace metadata and current authorized query strings;
- SearchWork projection/source obligations;
- existing sanitized retrieval/search passage or result records.

It emits a sanitized EvidenceLedger observation payload with:

- source requirements derived from source obligations;
- candidate records derived from existing retrieval/search outputs;
- conservative requirement links;
- explicit custody gaps when linking is not trace-safe;
- component, source-obligation, provider-job, QueryPlan item, and execution refs;
- no-behavior-change flags.

The bridge does not call providers, search, retrieval, fetch, prompts, models,
citation formatting, final-answer code, or QuantWorkUnit calculation paths.

## Requirement Mapping

Provider-job source obligations become EvidenceLedger source requirements with
stable ids derived from component id, source-obligation id, and provider-job id.

Known strict obligations map conservatively:

| SearchWork obligation | EvidenceLedger requirement class |
| --- | --- |
| `official_current` | `official_current_rules` |
| `legal_current_primary` | `legal_or_regulatory_text` |
| `canonical_documentation` | `primary_source_documents` |
| `source_bound_numeric` | `sourced_numeric_values` |

Currentness is preserved when visible, and official/current or legal/current
requirements record `current` currentness when no more specific safe value is
available.

## Candidate Mapping

Only existing sanitized retrieval/search outputs may become candidates.
Candidate records may include stable candidate id, URL, title, domain,
provider name, retrieval pass or dispatch ref, query ref, source tier, source
class, currentness, readability, and fetchability signals.

Raw page text, raw prompts, raw provider payloads, raw model responses, secrets,
tokens, DB rows, caches, private logs, full traces, full text, raw text, and
snippets are redacted or omitted.

## Link Rules

The bridge links a candidate to a requirement only when there is a defensible
trace-safe relation, such as the same authorized query, same provider-job
execution record, same retrieval dispatch ref, or QueryPlan provider-job
metadata.

For official/current, legal/current-primary, canonical-documentation, and
source-bound numeric requirements, the candidate must also have source fit from
already-available metadata. Lower-tier, stale, contextual, social, community, or
aggregate-only material is not linked as satisfying evidence for strict
requirements. When the bridge cannot link safely, it records a custody gap
instead of guessing.

## Aggregate Counts Remain Insufficient

Aggregate source-tier counts can show that something like an official source was
seen, but they do not provide candidate identity, URL, title, source fit,
readability, currentness, or query/provider-job lineage.

Therefore aggregate-only evidence remains insufficient for official/current,
legal/current-primary, canonical-documentation, and source-bound numeric
requirements. EvidenceLedger continues to mark aggregate-only paths as custody
gaps rather than source-obligation satisfaction.

## Reduction Path

Runtime reduction uses the existing RunKernel EvidenceLedger action path:

```text
provider-job G1 bridge payload
-> execute_evidence_ledger_reduction_action(...)
-> RunKernel.reduce(...)
-> RunState.evidence_ledger
-> RunKernel.EvidenceLedger projection
```

The bridge is not a parallel ledger authority. It creates an observation for the
existing EvidenceLedger reducer. Runtime trace exposes a compact projection with
bridge ran/created flags, counts, official-current custody posture when
available, and no-behavior-change flags.

## Deferred Behavior

G1 does not select final evidence, declare final answer readiness, change
citations, change Author behavior, change prompts, judge sufficiency, execute
retrieval, or perform source-bound numeric extraction/calculation.

SearchJudgment, SufficiencyJudgment, FinalAnswerPacket, citation selection, and
Author behavior remain downstream and unchanged.
