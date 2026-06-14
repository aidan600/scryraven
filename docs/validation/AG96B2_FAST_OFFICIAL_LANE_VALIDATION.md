# AG-96B2 Fast Official Lane Validation

## 1. Status and scope

Status: offline validation and live-gated design only.

AG-96B2 validates the AG-96B1 Fast official lane with repo-tracked fixtures and
test-only fakes. It makes no runtime behavior changes, runs no live validation,
and performs no ScryRaven/proplex/scryraven provider, model, search, retrieval,
or credential-backed calls.

Licensed surfaces:

- Offline eval fixtures for Fast official lane behavior.
- Offline tests around `core.fast_official_lane` and the source-class recovery
  executor's injected `process_search_queries` boundary.
- Documentation for a later explicitly approved live-gated Fast official lane
  dogfood packet.

Closed surfaces:

- Runtime provider routing, provider selection, provider depth, provider swaps,
  new provider integrations, and live validation.
- Balanced and Deep runtime follow-up loops.
- Final-answer, citation, Author prompt/prose, EvidenceLedger, and
  FinalAnswerPacket behavior.
- Source-specific official resolvers and hard-coded agency URLs in runtime code.
- `core/pipeline_orchestrator.py`.

## 2. What AG-96B1 changed

AG-96B1 added `core.fast_official_lane` as a narrow Fast-mode recipe helper for
hard-corridor official/current acquisition. The helper owns budgeted provider
job sequencing and trace metadata, not evidence admission or answer behavior.

The runtime consumer is `execute_source_class_recovery_action`, which now builds
a Fast official lane plan when the source-class recovery lifecycle is already in
Fast mode, has an official/current obligation, has hard-corridor official domain
constraints, and is executing the existing `source_class_recovery` provider
role.

The implemented Fast recipe is:

1. Run one direct official candidate attempt through the existing injected
   `process_search_queries` executor boundary.
2. Evaluate candidate fit through the existing recovered-evidence visibility
   path.
3. If candidate fit passes, skip retry.
4. If candidate fit rejects with `official_candidate_not_answer_bearing`, extract
   at most concrete bridge hints from sanitized provider diagnostics.
5. Run one bounded retry from one concrete bridge hint when available.
6. Evaluate retry candidates through the same recovered-evidence
   visibility/candidate-fit path.
7. Fail closed when the recipe is exhausted or no concrete bridge hint exists.

Bridge hints remain bridge-only:

```text
bridge_only=true
citation_eligible=false
final_evidence_eligible=false
```

They may point the recipe toward a canonical official source, but they do not
satisfy official/current evidence, final citation, or final answer obligations.

## 3. What AG-96B2 validates offline

AG-96B2 validates the following representative scenarios with fakes only:

| Scenario | Fixture posture | Expected lane behavior | Expected custody/admission behavior |
| --- | --- | --- | --- |
| Direct answer-bearing official candidate | The first synthetic official candidate contains the required answer-bearing text. | Fast hard-corridor lane is used, direct attempt is used, candidate fit passes, bridge retry is not consumed. | Final evidence admission remains possible through the existing recovered-evidence visibility path. |
| Generic official candidate with concrete bridge hint | The direct candidate is official/current but generic; diagnostics contain a concrete official title/URL hint. | Candidate fit rejects with `official_candidate_not_answer_bearing`; one bridge hint is recorded; one retry is consumed; retry candidate can pass. | The bridge hint remains citation-ineligible and final-evidence-ineligible; only the retry candidate can pass via recovered-evidence visibility. |
| Generic official candidate with no concrete bridge hint | The direct candidate is generic and diagnostics contain no URL/title/query hint. | Candidate fit rejects; no retry runs; retry posture records skipped/no concrete bridge hint. | Result remains insufficient and fail-closed. |
| Retry exhaustion | Direct candidate rejects; one concrete bridge retry runs; retry candidate also rejects. | One retry is consumed; lane records `recipe_exhausted_fail_closed`; no third search occurs. | No final evidence is selected. |
| Bridge snippet / secondary claim laundering guard | Diagnostics contain only a snippet/claim, without official URL/title/query hint. | No concrete bridge hint is extracted and no retry is run. | Snippet text creates no final evidence or citation support. |
| Existing provider role boundaries | Synthetic plans and diagnostics represent Linkup, Brave, Exa, and Tavily roles. | Linkup `searchResults` is a candidate surface; Linkup sourcedAnswer/deep is not selected by Fast; Brave is scout/bridge-only; Exa is semantic/constrained candidate capability, not universal fallback; Tavily remains a possible direct candidate surface. | Provider answer/deep/scout material remains bridge/context unless canonical custody later admits an official source. |
| Corridor preservation | Hard corridor has official constraints; non-hard corridor lacks constraints. | Hard corridor is usable; soft/discovery posture is not silently hard-forced; discovery is not converted into a U.S. federal shortcut. | Domain constraints remain corridor-owned and do not create evidence by themselves. |
| Ownership boundary | Static checks inspect helper, executor, and orchestrator imports. | Fast lane owns recipe metadata; executor calls the existing recovered-evidence visibility path; orchestrator does not own candidate-fit behavior. | EvidenceLedger and FinalAnswerPacket custody remain untouched. |

Expected trace fields include:

- `fast_official_lane.used`;
- `direct_attempt_used`;
- `provider_jobs_planned`;
- `provider_jobs_attempted`;
- `candidate_fit_status`;
- `candidate_fit_rejection_reasons`;
- `bridge_hints`;
- `bridge_hint_count`;
- `bridge_retry_used`;
- `retry_posture`;
- `retry_candidate_fit_status`;
- `retry_candidate_fit_rejection_reasons`;
- `lane_completion_posture`;
- `linkup_sourced_answer_selected`;
- `linkup_search_results_candidate_surface`;
- `brave_bridge_only`;
- `exa_selected_by_job_capability`;
- `soft_corridor_hard_forced`;
- `discovery_corridor_us_shortcut`.

Expected refusal/fail-closed behavior:

- Generic official pages that are not answer-bearing remain rejected.
- Snippets, provider claims, and bridge diagnostics do not create citation or
  final evidence support.
- Missing concrete bridge hints skip retry.
- Exhausted retry budget stops after the second fake provider call.

## 4. Offline eval metrics

The AG-96B2 offline eval records/asserts these metrics:

- `lane_used`;
- `direct_attempt_used`;
- `candidate_fit_status`;
- `candidate_fit_rejection_reasons`;
- `bridge_hint_count`;
- `bridge_retry_used`;
- `retry_candidate_fit_status`;
- `lane_completion_posture`;
- `final_evidence_eligible_bridge_count`;
- `citation_eligible_bridge_count`;
- `total_fake_provider_calls`;
- `budget_exhausted`;
- `sufficiency_reached`.

Expected metric invariants:

- `final_evidence_eligible_bridge_count` is always `0`.
- `citation_eligible_bridge_count` is always `0`.
- Direct candidate success uses exactly one fake provider call.
- Bridge retry success uses exactly two fake provider calls.
- Retry exhaustion uses exactly two fake provider calls and records
  `recipe_exhausted_fail_closed`.
- No-concrete-hint and snippet-only cases use exactly one fake provider call and
  remain insufficient.

## 5. Live-gated dogfood design

This section is a proposal only. AG-96B2 does not authorize or run it.

### Query set

Run at most one Fast ScryRaven/proplex/scryraven run for each approved query:

1. IRS control/success case:
   "What official source currently states the 2026 U.S. business standard
   mileage rate? Answer from official/current sources and cite the official
   source."
2. USCIS hard-corridor retry candidate:
   "What official source currently states the current USCIS filing fee for Form
   N-400? Answer from official/current sources and cite the official source."
3. SSA hard-corridor retry candidate:
   "What official source currently states the Social Security taxable maximum
   wage base for 2026? Answer from official/current sources and cite the
   official source."

Optional no-answer/fail-closed control: not authorized in AG-96B2. Add only if a
later phase explicitly approves the exact query and budget.

### Maximum runs and caps

- Maximum 3 ScryRaven/proplex/scryraven runs.
- One run per query.
- No replacement runs unless infrastructure failure occurs.
- Optional replacement cap, if explicitly authorized later: 1 infrastructure
  replacement run.
- Absolute cap if replacement is authorized later: 4 total runs.
- No provider/model/search budget increase beyond current Fast defaults.
- No provider routing, provider selection, provider depth, provider swap, or new
  provider integration change.

### Output packet path

Suggested local packet directory for a later approved live run:

```text
outputs/local_validation/AG96B2_FAST_OFFICIAL_LANE_DOGFOOD_<timestamp>/
```

The packet must be local/untracked and begin with:

```text
LOCAL/UNTRACKED — DO NOT COMMIT
```

### Redaction plan

Include:

- exact query;
- final answer;
- final cited URLs;
- sanitized telemetry;
- Fast official lane trace summary;
- source-quality summary;
- unavailable-telemetry notes.

Exclude:

- `.env`;
- API keys and secrets;
- raw provider payloads;
- raw prompts;
- DB rows;
- private logs;
- caches;
- full raw traces;
- unrelated output artifacts.

### Decision the live run would make

The later live-gated dogfood would decide:

- whether AG-96B1's Fast official lane improves hard-corridor official
  acquisition behavior without citation laundering;
- whether bridge hints are present and useful in real provider diagnostics;
- whether Fast still fails closed when no answer-bearing official source
  survives canonical custody.

### Stop conditions

Stop the later live run if any of the following occurs:

- the run would exceed 3 total approved runs, or 4 total runs only if the
  infrastructure replacement cap is separately approved;
- live execution requires provider/model/search budget above current Fast
  defaults;
- live execution requires provider routing, selection, depth, or provider
  integration changes;
- live execution requires secrets or private artifacts beyond ordinary local
  environment availability;
- findings imply Balanced/Deep runtime loop work;
- findings imply final-answer, citation, Author prompt/prose, source-ranking,
  or EvidenceLedger/FinalAnswerPacket changes;
- packet redaction cannot exclude closed surfaces listed above;
- the behavior becomes a provider bake-off instead of Fast official lane
  dogfood.

## 6. Known limitations

- Offline fixtures cannot prove provider index quality.
- Offline fixtures cannot prove USCIS, SSA, or IRS live success.
- Offline fixtures cannot prove that real provider diagnostics will contain
  useful bridge hints.
- Offline fixtures validate custody boundaries only through existing local code
  paths and synthetic passages.
- Live validation remains separately gated.
- Balanced and Deep judgment-bounded loops remain deferred.

## 7. Recommended next phase

If the offline eval remains green, choose one of these next steps:

- Run the separately authorized AG-96B2 live-gated dogfood packet using the
  query set and caps above.
- Proceed to AG-96C0 design for Balanced/Deep judgment-bounded follow-up loops.

AG-96C0 should design Balanced/Deep loops as evidence-gap-driven,
judgment-bounded follow-up search under explicit budgets. AG-96C1 should
implement only the smallest reviewed runtime loop after that design review.
