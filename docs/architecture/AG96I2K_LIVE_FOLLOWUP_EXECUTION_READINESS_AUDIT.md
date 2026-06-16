# AG-96I2K Live Follow-up Execution Readiness Audit

## Status

AG-96I2K is a docs-only readiness audit for the first real bounded internal
follow-up execution seam after the AG-96I2A through AG-96I2J fixture spine.

No runtime code changed. No live ScryRaven/proplex/scryraven provider, model,
search, retrieval, fetch/read, AuthorExecutor, citation-rendering, product
final-answer, app dogfood, secret, `.env`, DB, cache, raw trace, raw prompt, raw
provider payload, private log, or local output-packet surface was opened.

Recommendation: the smallest viable first live follow-up job kind is
`official_current_candidate_acquisition`, implemented first as an offline
live-shaped recovery executor/adapter plugged into the existing
RunKernel-authorized follow-up spine in AG-96I3A, with actual live validation
deferred to a later explicitly budgeted phase.

## AG-96I3A Follow-up Result

AG-96I3A implemented the recommended offline live-shaped seam:
[AG96I3A_OFFLINE_LIVE_SHAPED_FOLLOWUP_RECOVERY_EXECUTOR.md](AG96I3A_OFFLINE_LIVE_SHAPED_FOLLOWUP_RECOVERY_EXECUTOR.md).

The implementation adds RunKernel-owned
`FOLLOWUP_PROVIDER_JOB_EXECUTE` / `FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED`
vocabulary for `official_current_candidate_acquisition`, reuses the existing
`followup_execution_state` lane with
`execution_mode=bounded_provider_job_offline`, and feeds the existing
EvidenceLedger intake, SufficiencyJudgment recheck, and FinalAnswerPacket path.
It remains offline: provider/search/retrieval/fetch/read/model, Author,
citation-rendering, product-answer, and live-validation surfaces stayed closed.

## 1. Current Fixture Spine Summary

The current follow-up fixture spine is:

```text
FollowupDeliberationCheckpoint
-> RunKernel followup_authorization_state
-> fixture-only followup_execution_state
-> fixture-only followup_evidence_intake_state
-> RunKernel EvidenceLedger
-> fixture-only followup_sufficiency_recheck_state
-> RunKernel SufficiencyJudgment
-> fixture-only followup_final_answer_packet_state
-> RunKernel FinalAnswerPacket / final_answer_authority_projection
-> fixture-only followup_author_gate_state
-> fixture-only followup_author_observation_state
```

The important property is not that every record exists. The important property
is that RunKernel authorizes each step, reduces each observation, validates
binding against prior canonical state, and re-derives high-custody downstream
state instead of trusting adapter payload claims.

Current fixture execution proves the intended authority shape but not live
provider/search behavior. `core.followup_execution_runtime` accepts only
`fixture_only` execution, requires an explicit sanitized fixture payload, and
records no provider/search/retrieval/fetch/model execution. RunKernel rejects
fixture observations that claim live calls, provider dispatch, EvidenceLedger
admission before intake, sufficiency recheck before the recheck stage,
FinalAnswerPacket activation before the packet stage, Author activation,
citation rendering, product-answer changes, or live validation.

## 2. Three Different Follow-up Meanings

Fixture follow-up execution is the current AG-96I2A-J test/runtime proof. It
uses sealed RunKernel follow-up candidates and sanitized fixture result payloads
to exercise canonical authorization, observation, EvidenceLedger intake,
SufficiencyJudgment recheck, FinalAnswerPacket preparation, Author gate, and
Author observation paths without calling external systems.

Real internal follow-up search is the future in-run behavior this audit targets.
It means that, during a single answer, RunKernel authorizes a bounded provider,
search, retrieval, fetch, or read job because first-pass evidence is
insufficient. The job returns sanitized candidate/read observations that can
enter EvidenceLedger custody, re-run sufficiency, and constrain downstream packet
and Author-gate behavior. It is not yet implemented for follow-up.

Real internal follow-up search is not a separate answer authority. The answer
contract remains the same RunAuthorityContract for the same user request. The
first acquisition pass attempts to satisfy it; EvidenceLedger, SearchJudgment,
and SufficiencyJudgment identify remaining gaps; follow-up/recovery execution is
a bounded continuation under that same contract; observations feed the same
EvidenceLedger; sufficiency recheck evaluates the same contract; and
FinalAnswerPacket remains the Author-facing authority.

Conversational user follow-up is a later user turn, such as "what about
California?" or "is that still true today?" It needs a separate Follow-up Turn
Contract that decides whether prior evidence can be reused, whether the scope or
time window changed, and whether a new or amended RunAuthorityContract is
needed. That surface remains out of scope for AG-96I2K and should not be
implemented by the internal search seam.

## 3. Candidate First Live Follow-up Job Kinds

`official_current_candidate_acquisition`
: Best first target. It maps cleanly from `official_current_gap` to
`official_current_rules` / `official_government`, is already the default
follow-up fixture case, has high user value, and has strong negative-control
tests for lower-tier or wrong-source-class material.

`legal_current_primary_acquisition`
: Similar custody mechanics, but higher stakes and more ambiguity. Legal and
regulatory text can require jurisdiction, effective date, hierarchy, and
interpretive posture decisions. It should follow after official/current proves
the execution seam.

`canonical_doc_acquisition`
: Good custody mapping for technical or primary documents, but less uniform
currentness pressure and broader source identity rules. It is viable after the
official/current lane proves candidate identity and source-fit controls.

`source_bound_numeric_extraction_calculation_support`
: Valuable but not first. It requires custody plus extraction/calculation
authority. Existing AG-96G2/G3/G4 docs deliberately keep source-bound numeric
custody separate from numeric value resolution.

`conflict_currentness_check`
: Useful but too ambiguous for the first live seam because it implies comparing
multiple sources, resolving currentness conflicts, and possibly needing Deep
reconciliation posture.

`fetch_read_extract`
: Too dependent on a known candidate URL or prior source identity. It is a good
second seam after live candidate acquisition creates a candidate to fetch/read.

Other `ProviderJobKind` values such as `direct_candidate_search`,
`semantic_recall`, `scout_disambiguation`, `bridge_hint_discovery`, and
`provider_answer_context` are broader, weaker, or bridge-only. They do not give
as tight a first custody invariant as official/current candidate acquisition.

## 4. Recommended First Live Job Kind

Recommended first target:

```text
official_current_candidate_acquisition
```

AG-96I3A should not immediately run live calls. It should add a live-shaped,
offline-testable recovery executor/adapter for exactly this job kind, with
dependency injection or recorded sanitized adapter outputs. The adapter should
plug into the existing RunKernel-authorized follow-up spine and feed the same
EvidenceLedger. Actual live validation should remain a later phase with an
explicit budget.

## 5. Rationale

This target has the best combination of minimal surface area and real user
value:

- It is already emitted by the follow-up gap taxonomy for `official_current_gap`.
- The current fixture spine defaults to this case and already maps it into
  EvidenceLedger requirement classes.
- Success and failure are easy to define: official/current source candidate
  acquired, no result, wrong source class, bridge-only/context-only, or adapter
  error.
- EvidenceLedger custody is straightforward: candidate identity, URL, title,
  domain, source tier/class, currentness, fetch/readability signals, provider
  job refs, component id, source-obligation id, requirement id, and sealed
  candidate id.
- Negative controls are strong: reputable-secondary, aggregate-only,
  bridge-only, stale, unreadable, or spoofed-source-class observations must not
  satisfy an official/current obligation.
- It does not require Author prose, citation rendering, final product answer
  activation, QuantWorkUnit extraction, calculation, legal interpretation, or
  conflict reconciliation.

## 6. Existing Code Surfaces Inspected

Follow-up authority spine:

- `core/run_kernel.py`
- `core/followup_deliberation.py`
- `core/followup_authorization_runtime.py`
- `core/followup_execution_runtime.py`
- `core/followup_evidence_intake_runtime.py`
- `core/followup_sufficiency_recheck_runtime.py`
- `core/followup_final_answer_packet_runtime.py`
- `core/followup_author_gate_runtime.py`
- `core/followup_author_observation_runtime.py`
- `core/followup_runkernel_reducers.py`
- `tests/helpers/followup_fixture_spine.py`
- AG-96I1 and AG-96I2A-J docs and focused tests.

Provider/search/retrieval/fetch surfaces:

- `core/search_work_official_current_handoff.py`
- `core/search_work_provider_job_execution.py`
- `core/provider_job_evidence_ledger_bridge.py`
- `core/retrieval_dispatch_runtime.py`
- `core/retrieval_batch_dispatch.py`
- `core/source_class_recovery_executor.py`
- `core/retrieval.py`
- `core/search_providers.py`
- `core/official_canonical_recovery_candidate_acquisition.py`
- AG-96D0/D2/D3, AG-96E1/E2, AG-96F1, AG-96G1/G2/G3-G4 docs.
- AG-71A, AG-72V, and AG-73C validation docs for official/current live-boundary
  lessons.

## 7. Existing Surfaces That Might Be Reused

Reuse directly:

- `ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION` from
  `core.followup_deliberation`.
- Existing RunKernel `AuthorizedAction` and `Observation` binding pattern.
- Follow-up sealed-candidate fields: authorization consumption id, candidate id,
  provider job kind, component id, source-obligation id, requirement ids,
  expected custody update, planned budget debit, and fallback posture.
- Existing follow-up EvidenceLedger intake, sufficiency recheck,
  FinalAnswerPacket, Author gate, and Author observation downstream shape once a
  live-shaped execution record can present sanitized candidate facts.
- Existing source-class mappings in `followup_evidence_intake_runtime` and
  `followup_runkernel_reducers`.
- `provider_job_evidence_ledger_bridge` candidate and requirement vocabulary for
  URL/title/domain/source-class/currentness/fetchability/readability custody.
- `retrieval_dispatch_runtime.RecordedRetrievalDispatch` as a reference for
  explicit provider/query/depth/result-count call envelopes.

Reuse only as reference or bounded adapter input:

- `search_work_provider_job_execution` records, because they are trace-safe
  handoff records, not a provider executor.
- SearchWork provider-job vocabulary, with an explicit translation guard. The
  SearchWork lane uses names such as `official_candidate_acquisition`, while the
  follow-up spine uses `official_current_candidate_acquisition`; AG-96I3A should
  bind the follow-up enum directly and not rely on accidental string
  compatibility.
- `retrieval.py` result/fetch field names, because the functions themselves
  perform network fetches and expose raw text internally.
- `search_providers.py` provider wrappers, because they read environment keys
  and call external APIs.

## 8. Surfaces That Must Remain Closed

AG-96I3A should keep these closed unless a later phase explicitly relicenses
them:

- live provider/model/search/retrieval/fetch/read calls;
- provider routing, provider selection, provider swap, provider depth, and
  search-depth policy changes;
- query generation or query mutation;
- retrieval ranking/filtering;
- source-class recovery runner retry policy and Fast official lane behavior;
- source-bound numeric extraction and calculation;
- legal interpretation/reconciliation behavior;
- AuthorExecutor invocation;
- Author prompt/prose generation;
- citation formatting/rendering;
- product final-answer activation;
- conversational Follow-up Turn Contract;
- broad `core/pipeline_orchestrator.py` domain logic;
- secrets, `.env`, raw provider payloads, raw prompts, raw text, DB rows,
  caches, full traces, private logs, ignored local output packets.

## 9. Proposed AG-96I3A Continuation Flow

The AG-96I3A flow should be a continuation under the existing answer contract:

```text
same RunAuthorityContract
-> first acquisition pass leaves an official/current gap
-> EvidenceLedger/SearchJudgment/SufficiencyJudgment expose remaining gap
-> FollowupDeliberationCheckpoint names bounded recovery candidate
-> RunKernel seals candidate and authorizes one recovery executor/adapter
-> adapter returns sanitized observation
-> same EvidenceLedger consumes observation
-> same SufficiencyJudgment doctrine rechecks the same contract
-> same FinalAnswerPacket remains Author-facing authority
```

No separate follow-up answer contract, parallel sufficiency doctrine, competing
packet system, or adapter-owned answer authority should be introduced.

RunKernel authorization:

```text
RunKernel.followup_authorization_state
+ sealed candidate with provider_job_kind=official_current_candidate_acquisition
+ explicit pre-authorized query/ref or recorded sanitized execution fixture
+ budget check
-> RunKernel.authorize_followup_provider_job_execution(...)
-> AuthorizedAction
```

RunKernel must remain the owner of the yes/no continuation decision under the
same answer contract. It should check the current authorization state, sealed
candidate, mode, provider job kind, expected source classes, closed downstream
surfaces, and planned budget. It should fail closed if no pre-authorized
query/ref is present. The executor must not invent query text.

Executor/adapter:

```text
AuthorizedAction
+ injected provider/search/fetch/read adapter dependency
+ no-live fake/recorded sanitized result in AG-96I3A tests
-> FollowupProviderJobExecutionObservation
```

The first real recovery executor/adapter should be an official/current
candidate-acquisition adapter. It should consume only authorized inputs and
return sanitized candidate-level facts. For AG-96I3A, it should be live-shaped
but offline: tests provide fake adapter outputs instead of real network calls.
In a later live phase, the same adapter boundary can call provider/search/fetch/
read tools as executors, not as authority owners.

Observation payload shape:

```text
followup_provider_job_execution_state:
  schema_version
  owner: FollowupProviderJobExecutionRuntime
  canonical_state: false
  run_id/checkpoint_id/action_id
  followup_authorization_consumption_id
  sealed_candidate_id
  provider_job_kind: official_current_candidate_acquisition
  component_id
  source_obligation_id
  requirement_ids
  expected_source_classes
  authorized_query_ref or authorized_query
  execution_mode
  provider_execution_licensed
  budget_debit_applied
  provider/search/fetch/read budget counters used
  result_status
  sanitized_candidate_summary:
    url
    title
    domain
    source_tier
    source_class
    currentness_signal
    readable_status
    fetchable_status
    provider_name
    retrieval_pass_id or adapter_result_id
  bridge_only
  adapter_error_code
  behavior_boundary_flags
  redaction_posture
```

Reducer validation:

RunKernel should reduce the observation into canonical follow-up execution state
only after validating the action binding, the sealed candidate binding,
job-kind allowlist, budget facts, execution mode, expected source classes, and
no closed-surface flags. Spoofed observations must not be able to claim
source-obligation satisfaction, final evidence satisfaction, citation
eligibility, Author activation, product-answer behavior, query generation,
provider routing changes, or live validation.

EvidenceLedger intake:

The existing `authorize_followup_evidence_intake` path should remain the next
consumer if AG-96I3A can safely extend it to accept a new live-shaped execution
mode. If a small adapter-specific mode is needed, it must still call the same
canonical EvidenceLedger API and must not create a follow-up ledger. The intake
record should derive requirements and candidates from RunKernel-owned execution
state, not from caller-supplied ledger payloads.

SufficiencyJudgment recheck:

After EvidenceLedger intake, the existing follow-up sufficiency recheck path
should consume the updated EvidenceLedger projection against the same answer
contract. Official/current success can improve readiness only through
EvidenceLedger custody and SufficiencyJudgment. No adapter may mark sufficiency
directly.

FinalAnswerPacket:

The existing follow-up packet path should continue to derive packet evidence,
mandatory caveats, prohibited upgrades, missing obligations, citation
eligibility metadata, and Author-facing authority from canonical
SufficiencyJudgment and EvidenceLedger state. It should not create a competing
follow-up packet system.

Author gate:

The existing Author gate should continue to consume FinalAnswerPacket authority
while keeping Author execution, prompt/prose generation, citation rendering, and
product answer activation closed unless a later phase explicitly opens them.

## 10. Proposed AG-96I3A State or Record Additions

Needed:

- new action and observation vocabulary, probably
  `FOLLOWUP_PROVIDER_JOB_EXECUTE` and
  `FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED`, rather than overloading the
  fixture-only action name. This vocabulary must be RunKernel-owned
  continuation vocabulary, not a separate answer authority or answer contract;
- `followup_provider_job_execution_state/projection/history` or a carefully
  versioned successor to `followup_execution_state` that can distinguish
  `fixture_only` from `bounded_provider_job_offline` and later
  `bounded_provider_job_live`, while still feeding the same EvidenceLedger and
  downstream RunKernel states;
- execution result status taxonomy for live-shaped outputs:
  `candidate_acquired`, `no_result`, `wrong_source_class`, `bridge_only`,
  `adapter_error`, `budget_denied`, `closed_surface_denied`;
- explicit budget record fields:
  planned debit, authorized debit, applied debit, remaining budget projection,
  provider call count, search call count, fetch count, read-unit count;
- `authorized_query_ref` and, only if already safely available, sanitized
  `authorized_query`. If no query/ref exists, AG-96I3A should fail closed rather
  than generate one;
- sanitized candidate summary fields compatible with EvidenceLedger custody.

Not needed for the first target:

- Author output fields;
- citation-rendered fields;
- product answer fields;
- separate answer-contract fields;
- separate sufficiency-doctrine fields;
- separate packet-system fields;
- numeric extraction/calculation fields;
- legal interpretation fields;
- provider-routing policy fields beyond recording the injected adapter/provider
  name used by the authorized seam.

## 11. Proposed AG-96I3A Tests

Positive fixture/live-shaped execution:

- sealed Balanced `official_current_candidate_acquisition` candidate plus
  fake adapter result reduces into canonical provider-job execution state with
  `candidate_acquired`, official/current source metadata, budget facts, and no
  product activation.

Provider execution binding:

- mismatched candidate id, authorization consumption id, component id,
  source-obligation id, requirement id, provider job kind, expected source
  classes, authorized query ref, or action id is rejected by RunKernel.

Budget denial:

- exhausted provider calls, fetches, read units, cost points, or follow-up rounds
  prevents authorization or reduces as denied without calling the adapter.

Closed-surface denial:

- attempts to set provider routing changed, query generation changed, ranking
  changed, prompt changed, citation changed, Author invoked, product answer
  changed, live validation run, or raw/private payload retained fail closed.

Spoofed observation rejection:

- adapter observation cannot spoof EvidenceLedger admission, source-obligation
  satisfaction, final evidence satisfaction, citation eligibility,
  SufficiencyJudgment readiness, FinalAnswerPacket readiness, or Author
  activation.

EvidenceLedger custody:

- accepted official/current candidate becomes an EvidenceLedger candidate only
  through RunKernel-authorized intake and records the sealed candidate,
  provider-job, component, obligation, requirement, query/ref, and sanitized
  candidate lineage in the same EvidenceLedger used by the first pass.

Source-class mismatch:

- reputable-secondary, social/forum, aggregate-only, stale, unreadable, or
  wrong-class candidates are recorded as rejected/contextual and do not satisfy
  official/current requirements.

No product-answer activation:

- after execution, intake, recheck, packet preparation, gate, and optional
  fixture Author observation, AuthorExecutor remains uninvoked, final text is
  not retained, citation rendering is unchanged, and product answer behavior is
  not activated.

Static guards:

- the new follow-up recovery adapter must not import
  `pipeline_orchestrator`, Author prompt/executor modules, citation renderers,
  raw provider payload readers, `.env` loaders, DB/cache readers, or live
  provider modules in tests that are meant to be offline.

## 12. Proposed Later Live Validation Plan

Live validation remains disabled in AG-96I2K and should remain disabled in
AG-96I3A unless that phase explicitly adds a live budget. A later live gate
should use:

Exact query class:

```text
official/current government numeric-rule lookup where first-pass evidence is
insufficient and the follow-up target is
official_current_candidate_acquisition
```

Recommended concrete validation query:

```text
What is the current IRS standard mileage rate for business use of a car in
2026, and what official source supports it? Keep the answer concise.
```

Max run count:

```text
1 product-path run, with no automatic retry
```

Max calls:

```text
1 follow-up provider/search call
1 fetch/read attempt for the best official-current candidate, only if the
candidate-acquisition seam explicitly authorizes fetch/read
0 model calls beyond the product path already authorized by the live gate
0 AuthorExecutor behavior changes
```

Output packet path:

```text
output/ag96i3b_live_followup_official_current_validation_packet.md
```

Redaction plan:

- commit no output packet;
- keep `output/` ignored and verify with `git check-ignore -v`;
- record only sanitized query, run id/report path, budget counters, candidate
  URL/title/domain/source-class/currentness/readability/fetchability, accepted
  EvidenceLedger posture, SufficiencyJudgment posture, packet/gate posture, and
  stop reason;
- omit raw provider payloads, raw prompts, raw text, snippets, DB rows, caches,
  private logs, full traces, secrets, tokens, and `.env` content.

Stop condition:

- stop after one run;
- stop earlier on missing key/config, adapter exception, budget denial, closed
  surface flag, raw/private payload exposure, RunKernel transition failure, or
  evidence that provider routing/query generation/ranking/prompt/final-answer
  changes are needed.

## 13. Risks And Stop Conditions

Risks:

- query generation is not currently represented as executable follow-up
  authority, so a live provider job could accidentally grow a hidden query brain;
- `source_class_recovery_executor` already performs provider calls and retry
  behavior, but reusing it wholesale would import older recovery policy into the
  follow-up seam;
- `retrieval.py` and `search_providers.py` can fetch raw text or raw provider
  payload-derived content internally, so AG-96I3A must sanitize at the adapter
  boundary and keep raw content out of committed state;
- official/current source fit can be overclaimed from domain or aggregate counts
  unless candidate identity and source-class/currentness are explicit;
- SearchWork and follow-up provider-job vocabularies are adjacent but not
  identical, so adapter binding must validate `ProviderJobKind` explicitly;
- activating FinalAnswerPacket or Author too soon would turn a recovery custody
  seam into product-answer behavior by implication;
- adding a separate follow-up contract, separate sufficiency doctrine, or
  competing packet system would split answer authority.

Stop if:

- implementing AG-96I3A requires query generation changes now;
- provider routing, provider selection, search-depth, or ranking/filtering must
  change;
- RunKernel would no longer own follow-up authorization and canonical
  transitions;
- the proposed implementation creates a separate answer contract, separate
  follow-up sufficiency doctrine, separate EvidenceLedger, or competing
  FinalAnswerPacket;
- `core/pipeline_orchestrator.py` domain logic must change;
- secrets, `.env`, raw provider payloads, raw prompts, raw text, DB/cache/private
  logs, full traces, or ignored local output packets are needed;
- the target job cannot remain `official_current_candidate_acquisition` without
  a product decision;
- product final-answer activation, Author execution, or citation rendering would
  be required to prove the seam.

## 14. Recommended AG-96I3A Phase Brief

```text
AG-96I3A - Offline Live-shaped Follow-up Recovery Executor Adapter

Architecture Groove / Prove Mode, Path B approved.

Primary outcome:
Implement the first offline live-shaped internal follow-up recovery
executor/adapter for
provider_job_kind=official_current_candidate_acquisition, plugged into the
existing RunKernel-authorized follow-up spine, without live calls or product
answer activation.

Read:
- docs/codex/CODEX_GUIDANCE_MAP.md
- docs/codex/PHASE_BRIEF_TEMPLATE.md
- docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md
- docs/architecture/AG96I2K_LIVE_FOLLOWUP_EXECUTION_READINESS_AUDIT.md
- docs/architecture/AG96I2A_FOLLOWUP_AUTHORIZATION_SEALING.md
- docs/architecture/AG96I2B_FOLLOWUP_FIXTURE_DISPATCH.md
- docs/architecture/AG96I2C_FOLLOWUP_EVIDENCE_INTAKE.md
- docs/architecture/AG96I2D_FOLLOWUP_SUFFICIENCY_RECHECK.md
- docs/architecture/AG96I2E_FOLLOWUP_FINAL_ANSWER_PACKET.md
- docs/architecture/AG96I2F_FOLLOWUP_AUTHOR_GATE.md
- docs/architecture/AG96I2H_FOLLOWUP_AUTHOR_OBSERVATION.md
- docs/architecture/AG96G1_PROVIDER_JOB_EVIDENCE_LEDGER_CUSTODY.md
- docs/architecture/AG96G2_PROVIDER_JOB_SUFFICIENCY_CLOSURE.md
- core/run_kernel.py
- core/followup_authorization_runtime.py
- core/followup_execution_runtime.py
- core/followup_evidence_intake_runtime.py
- core/followup_runkernel_reducers.py
- core/provider_job_evidence_ledger_bridge.py
- core/retrieval_dispatch_runtime.py

In scope:
- Add RunKernel-owned authorization and reduction for one live-shaped follow-up
  recovery executor action under the same answer contract.
- Allow only `official_current_candidate_acquisition`.
- Use fake/injected sanitized adapter results in tests; no live calls.
- Require explicit pre-authorized query/ref or recorded sanitized execution
  fixture; fail closed if absent.
- Preserve or extend EvidenceLedger intake through canonical RunKernel reduction.
- Preserve downstream sufficiency, packet, Author gate, and Author observation
  closure.
- Preserve the same RunAuthorityContract, same EvidenceLedger, same
  SufficiencyJudgment doctrine, and same FinalAnswerPacket authority.
- Add focused positive, binding, budget denial, closed-surface denial, spoofed
  observation, EvidenceLedger custody, source-class mismatch, and no-product-
  activation tests.

Out of scope:
- live providers/search/retrieval/fetch/read/model calls;
- query generation or mutation;
- provider routing/selection/depth changes;
- retrieval ranking/filtering;
- source_class_recovery_executor policy reuse as follow-up authority;
- AuthorExecutor, citation rendering, product final-answer activation;
- conversational Follow-up Turn Contract;
- `pipeline_orchestrator.py` domain logic.

Runtime invariant:
RunKernel remains the owner of follow-up authorization and canonical follow-up
state transitions. Executors/adapters return observations only. There is one
answer contract, one EvidenceLedger, one SufficiencyJudgment doctrine, and one
FinalAnswerPacket authority path.

Validation:
- focused offline tests for the new seam;
- related AG-96I2 follow-up tests;
- py -m ruff check core tests;
- git diff --check.

Live validation:
Disabled. A later AG-96I3B live gate may run one official/current query with an
explicit call cap, ignored output packet, redaction plan, and stop condition.
```

## Final Audit Decision

AG-96I3A should not open arbitrary follow-up browsing. It should add one
RunKernel-owned, offline live-shaped recovery executor/adapter for
`official_current_candidate_acquisition`, with an explicit query/ref requirement
and sanitized adapter result contract. That is the smallest step that replaces
fixture-only execution shape with a real provider/search/fetch/read-compatible
executor boundary while preserving one answer contract, the same EvidenceLedger,
the same SufficiencyJudgment path, and the same FinalAnswerPacket authority.
Live calls, query generation, provider policy, Author, citations, product
answers, and conversational follow-up remain closed.

AG-96I3A has now completed that offline step. The remaining recommendation is
to keep AG-96I3B as an explicitly budgeted live-validation gate for the same
single provider-job kind, without broadening query generation, provider routing,
retrieval ranking, Author, citation, product-answer, or conversational follow-up
surfaces.
