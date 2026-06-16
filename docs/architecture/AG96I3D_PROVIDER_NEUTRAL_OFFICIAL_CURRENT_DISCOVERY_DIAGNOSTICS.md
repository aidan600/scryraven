# AG-96I3D Provider-neutral Official/current Discovery Diagnostics

## Status

AG-96I3D adds an offline diagnostic layer for provider-shaped search result
sets. It answers, without live calls:

```text
Given the result set a provider surface returned, what official/current
candidates were visible, which candidate would the authorized job select, why,
and under which acquisition mode?
```

The implementation is:

```text
core.followup_provider_result_set_diagnostics
```

The AG-96I3B live-validation harness now consumes this helper after a result set
has already been acquired. The helper does not call providers, route providers,
mutate queries, fetch/read pages, call models, activate AuthorExecutor, admit
evidence, or alter citation/product behavior.

## Why First Discovery Cannot Use `includeDomains=["irs.gov"]`

`includeDomains=["irs.gov"]` is not valid for first discovery proof because it
hands the provider a source-specific answer corridor before the authority chain
has earned one. That proves only that a provider can search inside a domain the
runtime already supplied; it does not prove that the provider surface can
discover an official/current candidate from the authorized query.

AG-96I3D keeps the first proof mode domain-neutral:

```text
job first -> provider second -> diagnostics always
```

The authorized job may require an official/current candidate, but the provider
adapter must not silently convert that obligation into a hard provider filter.
Domain constraints are represented only as diagnostic inputs, and only a
separate upstream authority decision can make a hard corridor earned.

## Acquisition Modes

### `discovery_unconstrained`

The provider-shaped result set is interpreted as the output of the user query or
RunKernel-authorized query without source-specific domain constraints. This is
the first proof mode for whether a provider surface can discover official/current
candidates without being handed the domain.

If a source-specific `includeDomains` or domain constraint appears in this mode,
the diagnostic marks it invalid:

```text
domain_constraint_status=invalid_unearned_domain_constraint
first_failure_layer=domain_constraint_authority
```

### `soft_authority_hint`

Generic official/current obligations and likely-authority hints may be recorded
for diagnostics or query labeling, but they do not become hard provider filters.
This mode can explain why a result set was being reviewed for official/current
fitness while preserving the provider-neutral discovery boundary.

### `hard_corridor_domain_constrained`

Domain constraints are valid only when an explicit upstream authority decision is
present. Without that decision, the diagnostic marks the posture invalid:

```text
domain_constraint_status=invalid_missing_authority_decision
first_failure_layer=hard_corridor_authority_decision_missing
```

With an explicit authority decision, the diagnostic records:

```text
domain_constraint_status=earned_domain_constraint
authority_decision_present=true
```

This remains a diagnostic state only in AG-96I3D. No live call is made and no
provider adapter synthesizes the authority decision internally.

## Diagnostic Contract

The packet records provider and job identity, acquisition mode, sanitized query
identity, result counts, sanitized ranked results, official/current candidate
counts, selected-candidate fields, failure layer, domain-constraint status,
authority-decision posture, bridge-only posture, and raw/private redaction
posture.

Each sanitized result keeps only:

- rank;
- URL;
- title;
- domain;
- source tier and class;
- currentness signal;
- candidate fit status;
- provider name;
- acquisition mode;
- rejection or selection reason.

Raw snippets, raw page text, provider payloads, prompts, model outputs, API keys,
`.env` values, private logs, DB/cache rows, and full traces are not retained.

## Candidate Selection

For `official_current_candidate_acquisition` in
`discovery_unconstrained` mode, diagnostics inspect the sanitized result set and
select the highest-ranked official/current candidate if one is present. A
secondary bridge result at rank 1 does not block selection of an official/current
candidate at rank 2.

If no official/current candidate exists, the diagnostic records:

```text
selected_candidate_rank=null
selected_candidate_reason=provider_result_set_lacked_official_current_candidate
bridge_only=true
```

Scout and bridge-hint jobs record hints only. Even if an official-looking result
is present, those jobs do not satisfy the official/current obligation and do not
invoke downstream official/current execution.

Provider identity is recorded but does not drive special-case success. There is
no provider-specific branch such as "if Brave" or source-specific branch such as
"if IRS".

## Why This Prevents First-result Waste

The brokered Brave summary after AG-96I3C showed five non-official bridge-hint
results and no official/.gov candidate. AG-96I3D makes that failure layer
explicit without treating the first result as evidence:

```text
provider_result_set_lacked_official_current_candidate
```

When an official/current result appears below a secondary bridge result, the
diagnostic selects the official/current candidate by rank among satisfying
candidates. When no satisfying candidate appears, it preserves bridge-only
posture rather than upgrading a secondary result into evidence.

This lets later phases compare provider surfaces fairly: each provider can be
judged by the official/current candidates visible in its own unconstrained
result set before any earned hard corridor is applied.

## Preparation for Later Brokered Comparison

AG-96I3D does not run brokered live validation. It prepares for a later
explicitly authorized phase by defining a stable offline contract that can be
fed with sanitized broker outputs from Brave, Tavily, Linkup, Exa, or other
provider surfaces.

A later brokered comparison can run one or more authorized provider jobs, pass
their sanitized result sets through the same diagnostic helper, and compare:

- whether official/current candidates were visible;
- how many were visible;
- which rank was selected;
- whether bridge-only posture remained;
- whether any domain constraint was earned or invalid.

That comparison still must keep provider payloads, snippets, secrets, `.env`,
private logs, DB/cache rows, and full traces outside the repo.

## Evidence Boundary

These diagnostics do not make final evidence. Official/current selection in the
result-set diagnostic is candidate-level observation only. Final evidence still
requires canonical custody through the existing answer authority chain:

```text
RunAuthorityContract
-> EvidenceLedger
-> SufficiencyJudgment
-> FinalAnswerPacket
-> AuthorExecutor
```

Fetch/read/admission remains a later, separately authorized step. A selected
candidate is not citation-eligible merely because it was visible in a provider
result set.

## Validation

Offline tests cover:

- unconstrained discovery refusing source-specific domain constraints;
- rank 1 secondary / rank 2 official-current selection;
- no official/current result bridge-only posture;
- multiple official candidates with first satisfying candidate selection;
- official but currentness-unclear results not being over-upgraded;
- scout/bridge jobs recording hints only;
- hard-corridor diagnostics requiring explicit authority decisions;
- raw/private payload stripping;
- static guards against provider direct calls and pipeline-orchestrator domain
  logic.

No live validation was run for this phase.
