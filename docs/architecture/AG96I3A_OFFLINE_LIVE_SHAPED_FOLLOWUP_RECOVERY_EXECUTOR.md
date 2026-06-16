# AG-96I3A Offline Live-shaped Follow-up Recovery Executor

## Status

AG-96I3A opens one offline live-shaped follow-up recovery executor seam for:

```text
provider_job_kind=official_current_candidate_acquisition
```

The phase remains offline. No live provider, search, retrieval, fetch/read,
model, AuthorExecutor, citation-rendering, product final-answer, app dogfood,
secret, `.env`, DB, cache, raw prompt, raw provider payload, raw text, private
log, full trace, or ignored output-packet surface was opened.

## What Was Opened

Runtime opened:

- `ActionType.FOLLOWUP_PROVIDER_JOB_EXECUTE`;
- `ObservationType.FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED`;
- `core.followup_provider_job_execution_runtime`;
- `RunKernel.authorize_followup_provider_job_execution(...)`;
- the existing `followup_execution_state`, `followup_execution_projection`, and
  `followup_execution_history` lane, now versioned by `execution_mode`;
- the existing follow-up EvidenceLedger intake path for
  `bounded_provider_job_offline` execution state.

The new execution mode is:

```text
bounded_provider_job_offline
```

It is deliberately distinct from the older `fixture_only` execution mode and
from a future `bounded_provider_job_live` mode.

## What Remains Closed

The adapter does not call or import live provider/search/retrieval/fetch/read
surfaces, provider routing, query generation, query mutation, retrieval ranking,
source-class recovery policy, `pipeline_orchestrator.py`, Author execution,
citation rendering, product final-answer activation, subprocess execution, DB
or cache readers, `.env` accessors, raw payload readers, `requests`, or
`openai`.

The canonical flags remain closed:

```text
provider_execution_licensed=false
live_provider_call_executed=false
search_executed=false
retrieval_executed=false
fetch_executed=false
model_called=false
live_validation_not_run=true
offline_live_shaped_execution=true
adapter_result_injected=true
```

## Why This Is Offline Live-shaped

The new adapter consumes the same kind of RunKernel-authorized action that a
future live executor can consume, and it emits sanitized candidate-level
observations shaped like provider-job execution results. In AG-96I3A, those
results are injected fake/sanitized payloads in tests. The adapter never reaches
out to providers, search, retrieval, fetch/read, models, or Author surfaces.

This proves the authority and custody seam without claiming that live provider
execution occurred.

## One Answer Contract

AG-96I3A does not introduce a follow-up answer contract. Recovery execution is a
bounded continuation under the same `RunAuthorityContract`, the same
EvidenceLedger, the same `SufficiencyJudgment` doctrine, and the same
FinalAnswerPacket authority path.

The adapter returns observations only. It cannot mark evidence satisfied,
sufficiency ready, packet ready, citation eligible, Author activated, or product
answer behavior changed.

## RunKernel Authority

RunKernel owns the continuation decision and all canonical transitions:

```text
followup_authorization_state
-> FOLLOWUP_PROVIDER_JOB_EXECUTE action
-> adapter observation
-> canonical followup_execution_state
-> followup_evidence_intake_state
-> EvidenceLedger
-> SufficiencyJudgment
-> FinalAnswerPacket
```

The provider-job reducer validates action binding, sealed-candidate binding,
provider-job kind, expected source classes, query/ref binding, budget facts, and
closed-surface claims before committing state. Canonical execution state is
derived from the authorized action inputs plus sanitized adapter observation;
high-custody claims from the observation are rejected or overwritten.

## Query/ref Authorization

The executor must not invent query text. It requires either
`authorized_query_ref` or sanitized `authorized_query` from canonical sealed
candidate state.

Small optional propagation was added from follow-up deliberation gaps through
authorization sealing:

```text
GapAssessment
-> FollowupAuthorizationCandidate
-> FollowupAuthorizationSeal
-> RunKernel action inputs
```

Caller inputs cannot override canonical query/ref fields during execution
authorization. If neither field exists on the sealed candidate, authorization
fails closed before adapter execution.

## Budget Denial

RunKernel checks the existing follow-up budget decision before authorizing the
offline provider-job action. The minimal required debits are:

- provider calls;
- fetch reservations;
- read-unit reservations;
- cost points;
- follow-up rounds.

If any required budget field is exhausted or not authorized, RunKernel rejects
authorization and the adapter is not invoked. Observation-supplied budget facts
cannot spoof the canonical budget debit or remaining authority.

## EvidenceLedger Continuation

The existing follow-up EvidenceLedger intake remains the downstream consumer.
For `bounded_provider_job_offline`, intake derives candidates and requirements
from RunKernel-owned execution state, not from caller-supplied ledger payloads.

Accepted candidate facts include:

- URL, title, and domain;
- source tier and source class;
- currentness, readability, and fetchability signals;
- provider name and adapter result id;
- component, source-obligation, and requirement ids;
- sealed candidate id and provider job kind;
- authorized query ref or sanitized query.

Official/current candidates can satisfy official/current obligations only after
EvidenceLedger intake. Wrong-class, stale, unreadable, aggregate-only,
no-result, bridge-only, and adapter-error records do not become final evidence
or citation eligible.

## Allowlist

The only provider job kind allowed in AG-96I3A is:

```text
official_current_candidate_acquisition
```

Rejected job kinds include:

- `legal_current_primary_acquisition`;
- `canonical_doc_acquisition`;
- `source_bound_numeric_extraction_calculation_support`;
- `conflict_currentness_check`;
- `fetch_read_extract`;
- `semantic_recall`;
- `direct_candidate_search`;
- `scout_disambiguation`;
- `bridge_hint_discovery`;
- `provider_answer_context`.

This keeps the first executor seam narrow enough to prove custody and authority
without importing legal interpretation, numeric extraction, routing policy,
query generation, retrieval ranking, or product-answer behavior.

## AG-96I3B Next

AG-96I3B should add the first explicitly budgeted live validation gate for this
same provider-job seam. It should keep the same answer contract and downstream
path, authorize at most one official/current live-shaped run, preserve the
redaction plan, and stop on missing config, budget denial, closed-surface claim,
raw/private payload exposure, or any need for query generation, routing policy,
ranking, Author execution, citation rendering, or product final-answer changes.
