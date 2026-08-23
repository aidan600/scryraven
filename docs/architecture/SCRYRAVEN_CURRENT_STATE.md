# ScryRaven Current State

Status: current
Authority: canonical:current-installed-state
Default-read: yes
Applies-to: current ordinary product implementation and explicit nonproofs
Does-not-authorize: live calls, arbitrary-query claims, roadmap execution, or closed-surface changes
Runtime-audit-through: 969e3085922d10985d406bac1d620d459e2731c6
Update-trigger: merged change to installed product behavior, supported boundaries, evidence classification, or explicit nonproofs

## Purpose And Source-Of-Truth Rule

This document is the sole repository owner of temporal installed-state truth.
Code and focused tests remain the executable authority; when they disagree with
this summary, treat the summary as stale and repair it. `Runtime-audit-through`
identifies the latest runtime commit whose installed behavior was substantively
reviewed; documentation-only, test-only, or workflow-only merges do not make
that anchor stale. Deep architecture owners define contracts and rationale,
while the roadmap owns the current strategic decision gate. Neither makes a
capability installed merely by describing it.

## Supported Ordinary Entrypoints And Query Boundary

The public CLI is the current supported executable interface. Both
`python -m scryraven` and the compatible `python -m proplex` entrypoint consume
the backend pipeline and the installed path described below. Bounded
multi-component behavior applies only to the named query class
`ordinary-bounded-multicomponent-factual-synthesis-v1`. The ordinary SearchOS
semantic receiver nevertheless uses the direct Component Analyst case /
RunKernel admission chain for N=1 through the accepted component envelope;
SearchJudgment does not select a second semantic lane. Non-SearchOS
compatibility
surfaces retain their established direct behavior. The ordinary CLI/backend
composition no longer injects or executes the legacy Economist callable.

PR #541 merged on 2026-08-06 at
`c742da77d4daa02d7cf5012ddc32da2b8cb5bc39`. Physical attempt/cost envelope
enforcement is installed merged product state, and the public CLI requires one
complete explicit per-run `--bounded-run-authorization` file to activate it.
`public-cli-v1` remains removed; no reusable mode profiles exist. Two historical
bounded Q1 ordinary-product runs on the answer-bearing READ repair branch are
recorded below. The first crossed the repaired SearchOS handoff and stopped
safely at Component Analyst output validation. The second crossed Component
Analyst support, deterministic admission, ComponentCoverage, Sufficiency, and
FinalAnswerPacket readiness and invoked Author, then stopped at the now-retired
post-Author quantitative semantic gate. A prior post-repair licensed Q1 run
entered ordinary `run_pipeline()` but its explicit zero SmartSearchJudgment cap
blocked the first planned SmartSearchJudgment action at configuration, before
Component Analyst, FAP, or Author. The subsequent cap-contract confirmation
run reached SearchOS, Component Analyst, admission, ComponentCoverage,
Sufficiency, and FAP, then stopped at the FAP/source-obligation boundary with
no citation-eligible source and no Author call. The installed FAP/Author
boundary no longer uses the retired gate; all of these observations remain
bounded evidence, not broad live-validation proof.


That downstream synthesis-class boundary does not limit initial semantic
planning. Ordinary initial semantic planning uses the selected fast-model
SearchPlanner. Its model-visible input is the complete normalized user utterance
within the 12,000-character input bound, requested mode, and bounded safe
context; runtime IDs, contract references, closed-surface flags, provider
selection, and downstream carrier state are not model-visible. The model authors
only the discriminated `direct_simple | components` semantic proposal: genuine
component needs and sparse source, freshness, dependency, support, uncertainty,
caveat, normalization, or calculation exceptions. Deterministic code owns rich
compatibility construction, IDs, bindings, mode ceilings, initial query copies,
and compiler-owned mechanical identity. Five components is a ceiling, not a target.

One deterministic query-shape assessment now qualifies explicit bullet,
contiguous numbered, and bounded repeated-imperative requests containing two
through five distinct factual components plus a separated request-level
synthesis directive. It preserves component order and the exact directive
through AnswerContract, scheduler context, and Cross-Component Analyst input.
Malformed or ambiguous structured candidates remain unselected, and the
existing general multipart fallback remains separate and does not grant route
eligibility. Fast, Balanced, and Deep consume this same parser and route
pipeline.

That deterministic query-shape assessment is compatibility/observability for
the model-owned initial proposal and remains a downstream qualifier for the
separately bounded synthesis class. It does not add, remove, rewrite, collapse,
or replace model-proposed initial semantic components or query strategies.

The legacy Streamlit shell, its home-page UI, and saved-thread Streamlit
follow-up are not ordinary product consumption. The retained `ui/` source is
reference and migration material pending separately licensed physical cleanup,
and `app.py` is a fail-closed retirement tombstone. No current UI framework is
selected. Future UI work must consume transport-neutral application services;
future conversation and follow-up product work must likewise be transport-neutral
and explicitly activated.

Nothing here proves real-world model quality or arbitrary-query downstream
multi-component synthesis, and no provider, search, retrieval, or
live-validation license is widened.

## Bounded Q1 Ordinary-Product Evidence

Two historical Q1 ordinary-product observations, one post-repair cap-limited
Q1 run, and one post-contract Q1 product confirmation for
`N1-ANSWER-BEARING-ANALYST-SUPPORT-AND-GOLDEN-LANE-CONVERGENCE-01` are current
evidence, not a general reliability claim.

```text
Run 1 ID: 2276bba3-7f11-4f26-9fdc-61dd1070c1a3
Run 2 ID: dc186ce3-c09c-404e-bf97-ab9298f36370
Each:     PRODUCT runs=1, retries=0, search=1, read=1,
          smart SearchJudgment calls=2
```

Run 1 safe projection:

```text
bounded_read_selection_count          = 1
bounded_read_digest_bound_count       = 1
searchos_exit                         = SEMANTIC_HANDOFF
semantic_handoff_present              = true
component_receiver_selected           = true
component_analyst_case_present        = false
component_analyst_failure:
  role = component_analyst
  failure_kind = output_validation_failure
  settlement_posture = failed_spent
```

Run 1 live-proved that accepted current semantic need now guides the existing
single-contiguous-window selector, that the selected bounded text is
digest-bound in custody, and that SearchJudgment seals the semantic handoff.
It stopped safely at the Component Analyst output-validation boundary.

After the bounded Component Analyst prompt repair, historical Run 2 reached:

```text
furthest_product_stage = final_answer_packet_ready
Author model calls      = 1
final failure type      = QuantitativeFinalizationAuthorityError
safe failure reasons    = unsupported_quantitative_surface,
                          unauthorized_quantitative_proposition
```

`final_answer_packet_ready` and an authorized Author call are downstream of the
installed Component Analyst artifact, exact deterministic admission,
ComponentCoverage, and Sufficiency gates; the second observation therefore
live-proved that historical Q1 crossed that corridor. It did not prove successful
Author finalization: the generated answer was rejected before a successful
RunOutcome, and the sanitized packet retained no final answer or citations.

The durable defect-chain classification is:

```text
FIRST_PROVEN_CATEGORY = A
ADDITIONAL_IN_CORRIDOR_DEFECTS = C, B
FINAL_REMAINING_CATEGORY = NONE
HISTORICAL_STOP_OWNER =
  retired post-Author quantitative semantic gate
```

The additional Category C defect was deterministic admission's generic safe
mapping truncating an allowed 2,000-character bounded excerpt to 800 characters,
which broke its declared content digest; exact bounded-text handling now
preserves the installed limit and fails closed on digest disagreement. The
Category B repair changed only the existing Component Analyst role contract,
not role topology or admission authority.

The A/B/C/D Analyst-corridor taxonomy is exhausted. Run 2 proved the accepted
Component Analyst case, deterministic admission, ComponentCoverage, Sufficiency,
FinalAnswerPacket readiness, and Author invocation before the historical
`QuantitativeFinalizationAuthorityError` stopped candidate prose. Its safe reason
codes, `unsupported_quantitative_surface` and
`unauthorized_quantitative_proposition`, identify where the retired evaluator
stopped; they do not identify whether FAP packaging, Author meaning, or parser
recognition was at fault.

The one licensed post-repair Q1 run was not a FAP/Author result. Its sanitized
structural packet records one `run_pipeline()` call, one search dispatch, zero
observed SmartSearchJudgment calls, zero Author calls, zero retries, no answer,
and no citations. The `run_pipeline` cap policy rejected the first planned
SmartSearchJudgment action at configuration because
`max_smart_search_judgment_model_calls=0`, with safe classification
`cap_overflow`. No Component Analyst, Coverage, Sufficiency, FAP, or Author
projection became available. This consumes the one licensed run; it neither
validates nor falsifies the selected FAP/Author boundary.

The post-contract Q1 product confirmation run
(`0c0fef74-a741-449e-bb73-acf4424bd848`) used the repaired AG-LIVE-SMOKE cap
contract and records:

```text
PRODUCT runs                  = 1
retries                       = 0
search dispatches             = 1
READ operations               = 1
SmartSearchJudgment calls     = 2
Component Analyst calls       = 1
Component admission           = YES
ComponentCoverage             = supported
Sufficiency                   = ready_with_caveats
FAP                           = blocked
missing source obligations    = 3
citation-eligible source IDs  = 0
Author calls                  = 0
supported cited answer        = NO
RunOutcome                    = blocked
failure classification        = blocked_final_answer_packet
```

The packet reached the ordinary product path through a sealed SearchOS
semantic handoff, answer-bearing READ custody, Component Analyst support, and
deterministic admission. FAP then remained blocked because the current packet
had three unsatisfied required source obligations; no citation-eligible source
was available for the final authority boundary. This is the first genuine
post-repair product frontier for the phase, owned by the FAP/source-obligation
handoff rather than the cap contract or the broker harness. No retry, backup
query, alternate provider/model, Specialist, D-prime, Cross, synthesis, or
Author call was made.

The installed final boundary is now:

```text
admitted source-explicit or Specialist numeric authority
-> FAP structured preflight (final semantic-authority boundary)
-> Author (final semantic actor)
-> mechanical citation/output finalization
-> RunOutcome
```

Missing quantitative lineage blocks FAP before Author. Once FAP authorizes
Author, a retained quantitative prose evaluator can report diagnostics but cannot
change Author output, citation authority, canonical state, RunOutcome, or product
success. This changes no upstream SearchOS, Component Analyst, Coverage,
Sufficiency, citation-eligibility, or Specialist ownership.

The earlier accepted Q1 run (`90c035c6-8f53-438e-96e6-0a6e63895221`) and
bounded SearchOS pulse (`45f3319b-9b43-4dcc-ba81-2d1d12f40a77`) remain
historical provenance only. The two historical observations and cap-limited
post-repair observation do not generalize to all Q1 repetitions, Q2-Q6,
arbitrary queries, broad SearchOS reliability, acquisition completeness, or
product correctness.

### Frozen-handoff observation

The Q1 product run used persistence suppression. Its sanitized output packet
retained safe summary, digest, and presence information, but not the canonical
live state required to replay downstream analysis, including the full current
RunKernel state, accepted AnswerContract, SearchOS semantic handoff, READ
custody/material, EvidenceLedger bindings, and downstream authority context.

A later downstream-only observation therefore correctly classified
`FROZEN_HANDOFF_NOT_AVAILABLE`. That result means the proposed replay
experiment could not lawfully run; it does not mean missing replay persistence
is the product blocker. Replay infrastructure is not the next product phase.

### Current product frontier

The installed Q1 product shape is:

```text
SearchOS -> Component Analyst -> admission -> Coverage -> Sufficiency
-> FAP structured quantitative preflight -> Author -> mechanics -> RunOutcome
```

The retained historical Q1 observation predates that boundary repair. Offline
ordinary proof now reaches the shown path with direct-source numeric authority,
one Author call, cited success, no Specialist, no Component D-prime, no Cross or
synthesis semantic call, no Scrutineer, and no post-Author semantic gate. The
N=1 direct-admission topology correctly does not require a Component D-prime
call. The prior cap-limited post-repair live run exhausted its licensed attempt
at the
`run_pipeline` SmartSearchJudgment cap before Component Analyst. The new
post-contract live run traversed the FAP boundary but did not authorize Author
because required source obligations were unsatisfied. It is not a supported
cited answer and does not establish broad live-product reliability.

## Operator Doorman Boundary

Operator doorman infrastructure is not ordinary product runtime. ScryRaven
product modules do not call `scripts/run_brokered_command_once.py`. Normal
human local use continues through the normal CLI and local configuration path
with no doorman. The credentialed command launcher exists for LLM-controlled
trusted local execution of whole-product or component/test/evaluator commands
that need the private environment. The `GENERIC-PROVIDER-EXECUTION-BROKER-V2`
marker describes only the specialized explicit-provider/evaluator RPC
mechanism; its provider matrix and mechanical request fuse are not general
product or doorman policy. See
[Brokered Command Session Operator Flow](../operator/BROKERED_COMMAND_SESSION_OPERATOR_FLOW.md).

## Installed Capability Table

The identifiers below are documentation sentinels, not runtime flags or public
configuration.

| Marker | Installed behavior for the supported class |
| --- | --- |
| `MC-P1-ORDINARY` | **Installed:** A current Component Analyst case feeds direct RunKernel component admission; ComponentWorkGraph V1, Cross-Component Analyst, synthesis D-prime, and the full Scrutineer posture when triggered feed canonical graph/synthesis admission. The result is consumed by ordinary Sufficiency, FinalAnswerPacket, Author, RunOutcome, and CLI-visible output, with safe blocked non-Author terminal behavior where required. **Selected target:** the synthesis D-prime ordinary model call is retired per [AnalystOS Operating Model](ANALYSTOS_OPERATING_MODEL.md). |
| `MC-P2-DYNAMIC-RECOVERY` | One bounded missing-component recovery may amend the AnswerContract, re-enter ordinary research, admit the recovered component, and resume the governed graph. |
| `MC-P3-SELECTIVE-RECOMPUTE` | Recovery invalidates and recomputes only the affected synthesis closure while exact unaffected admitted synthesis is carried forward under new deterministic authority. |
| `MC-P4-SCHEDULER-LEASES` | RunKernel owns semantic-work scheduling and exact work/budget leases, including grant-first dispatch, pretransport spend commitment, cancellation accounting, and terminal zero-active-lease enforcement. |
| `MC-P5A-HOSTED-W2` | Scheduler V2 permits hosted OpenAI/OpenRouter initial Component Analyst width 2. Local and unsupported/conservative execution remain width 1. Batch grant, cancellation, dispatch spend, and child-action publication are atomic; transport-only workers may overlap, while canonical reduction remains deterministic on the main thread. |
| `MC-P5A-STRICT-ONE-SHOT` | Provider-faithful transport is strict one-shot: at most one provider request per child, no SDK retry, and no endpoint, provider, or model fallback. Unsupported providers fail closed with zero requests. |
| `MC-P5A-SAMPLING-COMPAT` | OpenRouter and Local chat transport internally own temperature `0.3`; OpenAI Responses omits temperature; caller-authored temperature is rejected. |
| `MC-P5A-MAIN-THREAD-COST` | Response-bearing model cost is recorded on the main thread before deterministic canonical reduction. |
| `SPECIALIST-S0-GENERIC` | Component Analyst, Cross-Component Analyst, and full Scrutineer may emit one exact candidate mapping under `specialist_need_proposal_v1`. Generic S0 rejects missing/stale schema, unknown envelope/target fields, raw/private material, authority claims, aliases, recursion, and invalid posture before RunKernel admission; it never normalizes them into validity. RunKernel alone binds a valid candidate to current authority. Invalid candidates retain only a bounded receipt and create no Specialist work or derived authority; required/unclassified cases block while optional cases contribute nothing. Closed defaults register and enable no product capability. |
| `SPECIALIST-S1-QUANTITATIVE` | The ordinary CLI composes one fixed product registry/policy for `specialist.source_bound_calculation` on the named bounded multi-component class. Component and ordinary Cross-Component Analyst receive exact contract `quantitative_specialist_proposal_contract.v2`; before work creation the current contract instance, role input/artifact, target, source aliases, fixed fields, and capability request are re-proved and validated. Malformed proposals create no work, spend, lease, batch, dispatch, result, handoff, or downstream Specialist authority. Required malformed needs block dependent claims; optional malformed needs permit only independently supported continuation. Valid behavior remains one serial unit with component-before-synthesis priority, deterministic execution, canonical `result_unit`, and current semantic-case or synthesis-D-prime custody. |
| `QUANT-FINALIZATION-CONTAINMENT` | FAP is the final semantic-authority boundary and Author is the final semantic actor. Direct source-explicit propositions and exact completed S1 propositions remain eligible only through complete source or Specialist lineage and the applicable current Component Analyst case or synthesis validation. Generic semantic admission alone grants no numeric authority. Missing arithmetic, conversion, unit, precision, sign, scale, percentage, rate, subject, result, source, Specialist, or currentness authority blocks FAP before Author. The retained natural-language quantitative evaluator is diagnostic only: ordinary `AuthorExecutor`, deterministic `AuthorProseFinalization`, and the guarded follow-up response finalizer do not use it as a post-Author accepted-prose gate, and it cannot cause sentence surgery or automatic Author retry. |
| `PROVIDER-CAPABILITY-ROUTING` | `core.routing` owns one deterministic capability catalog and code-owned route policy. Ordinary DISCOVER consumes completed ProviderPlan decisions. `retrieval.DiscoverySourceResultIdentity` and `retrieval.DiscoveryResultMaterialStore` preserve bounded provider-result occurrence truth before chunking/ranking; existing ranking and selection populate the canonical ordinary `RunKernel.SearchResultCandidatePacket` with zero separate candidate-URL transport. Candidate selection remains a nontrigger. The post-selection RunKernel controller and typed Linkup/Tavily adapters remain installed for a future independent material-need producer. Focused Extract, Map, Crawl, and general Linkup Deep remain PRODUCT-blocked with exact controller blockers. |
| `GENERIC-PROVIDER-EXECUTION-BROKER-V2` | One tracked loopback-only broker consumes the versioned explicit-route `scryraven_provider_execution_request_v2` / response family. It supports Serper and Tavily `search.query` plus OpenAI `model.generate`; only the broker child parses the private environment file, while session tokens stay out of argv and the generic client persists safe completion, exact cache/reasoning/usage accounting, elapsed time, and output digest/length rather than output text. Caller/evaluator owns route selection, exact reasoning-effort authorization, prompts/query, retries/timeouts/caps, pricing, cost ceilings, interpretation, and durable sanitization. Incomplete generation is published as `REVIEW_REQUIRED / INCOMPLETE_GENERATION` before parser or semantic scoring and stops later calls. The job/profile bouncer is fail-closed, and new AnalystOS addenda select the provider-neutral brokered model-origination transport rather than the direct OpenAI fallback. |
| `SEARCHPLANNER-BOUNDARY-INTEGRITY` | `SEARCHPLANNER-SPARSE-UNCERTAINTY-AWARE-PLANNING-01` installs one fail-closed ordinary language shared by prompt and validator: `direct_simple | components`. The model-visible descriptor is the compact sufficient projection of that language: `direct_simple` may omit `source`/`freshness`/`caveat`, while `components` requires a nonempty `components` array and forbids those three top-level fields. The deterministic validator remains the exhaustive enforcement owner. Empty optional material must be omitted. Strict JSON parsing still rejects duplicate/nonfinite material, while the deterministic compiler alone constructs and revalidates the rich compatibility state. Mechanical IDs, runtime/contract references, provider authority, exact query/recon programs, evidence, and accepted state are forbidden model output. Closed privacy-safe M02 subtypes distinguish forbidden-surface, branch-field-set, omission-contract, type/enum/bound, and cross-field families without exposing raw model text. |
| `SEARCHOS-QUERY-CONVERGENCE` | The ordinary selected-fast-model SearchPlanner reaches RunKernel initial AnswerContract acceptance through the sparse validator and deterministic compiler. `direct_simple` becomes one required direct component; sparse components retain genuine semantic differences and compiler-owned ordinal identity. QueryPlan consumes the accepted AnswerContract directly and derives exactly one provider-neutral `orientation`, `standard_discovery`, or no-dispatch clarification posture from the accepted component/semantic-slot state, and every admitted item carries component/slot lineage. `deep_discovery` is available only as a typed in-loop escalation. SearchWorkPlan and QueryProduction are retired as ordinary semantic/query carriers. The ordinary ScoutDisambiguation, PlannerRevision, and routine initial PlannerRevision ContractAmendment lane is retired with no fallback. |
| `SEARCHOS-SLICE-A-CUTOVER` | `SEARCHOS-FIRST-WAVE-AND-ITERATIVE-JUDGMENT-CUTOVER-01` now owns one unified RunKernel SearchJudgment across initial and iterative `orientation`, `standard_discovery`, and `deep_discovery` work. Immutable revision 1, exact zero-result orientation lineage, and append-only iteration sets feed slot-local windows and cursors. SearchJudgment may propose exact follow-up work, READ, a bounded factual InterpretationBinding, clarification, semantic handoff, navigation where separately eligible, or honest unresolved state. RunKernel admits `searchos_interpretation_binding_v1` append-only and exposes a planning-only effective semantic-slot view without mutating the accepted AnswerContract or creating evidence, support, coverage, satisfaction, or citation authority. Exact candidate READ retains existing custody meaning. Required slots that do not reach current semantic admission produce the typed Slice A required-needs block and the existing safe blocked non-Author product terminal. |
| `SEARCHOS-ONE-HOP-NAVIGATION` | PR #517 installs bounded one-hop breadcrumb navigation and the qualification/source-truth path. Fresh candidate-origin READ custody may expose safe same-site URL-free navigation refs; one selected destination reuses the existing navigation, acquisition, FetchRead, EvidenceLedger, SearchOS custody, semantic, Sufficiency, FinalAnswerPacket, and Author owners. |
| `SEARCHOS-EXISTING-GAP-RECOVERY` | `SEARCHOS-EXISTING-GAP-RECOVERY-AND-STOP-FOUNDATION-01` installs canonical SearchOS as the sole ordinary SearchOS authority for one required existing-component/source-obligation recovery cycle per whole run in Fast, Balanced, and Deep. A typed post-analysis gap basis and materially novel evidence purpose grant one exact lease; the prior slot stays byte-identical and a new append-only SearchOS slot reuses QueryPlan, SEARCH, READ/custody, navigation, same-component Analyst case reassessment, direct RunKernel admission, and ComponentCoverage. Exact replay admits no new work. The lease closes as recovered or exhausted-insufficient, and ordinary Sufficiency remains the only final stopping authority. Scrutineer input, derived-component recovery, ContractAmendment, graph mutation, Specialist execution, and general inference remain excluded. |
| `SEARCHOS-BOUNDARY-B-CONVERGENCE` | Boundary B is installed through the ordinary consumer. Component Analyst or Cross-Component Analyst may emit the shared typed query-resolution proposal; deterministic arbitration selects only an exact noncompeting proposal. A searched-premise winner reuses ContractAmendment v2, the same whole-run SearchOS lease/cycle owner, QueryPlan, acquisition/custody, ComponentCoverage, Graph V1 reproof, and affected-only resynthesis. SearchOS searches the missing premise but never authors or admits inference. Target-mapped Graph V1 inference is bounded to semantic depth 1 in Fast/Balanced and 2 in Deep. Sufficiency, FAP, Author, RunOutcome, and CLI output consume only current admitted direct or inferred posture. The former ordinary dynamic-recovery runtime is deleted and has zero ordinary reachability. |
| `SEARCHOS-ANALYSTOS-OFFLINE-GATE` | PR #521 installs the reusable seven-scenario fictional SearchOS/AnalystOS ordinary-path gate. It proves direct closure, one searched-premise recovery, depth-two reconstruction, nested recovery with fresh whole-case reconciliation, root-query retention against a distractor, honest nonclosure, exact nested semantic-role artifact custody, atomic action bookkeeping, defensive proposal custody/replay, and exact action/observation sequence closure under the installed Fast 0 / Balanced 1 / Deep 2 serial searched-generation limits. |
| `ANALYSTOS-EVALUATION-RESPONSIBILITY-SPLIT` | Model-origination validation now has separate owners for observation of the canonical ordinary SearchPlanner boundary, deterministic mechanical rules, provider-neutral teacher-free semantic judgment, experiment identity and calibrated attribution, non-overriding coordination, and passive sanitized reporting. The legacy evaluator retains only call-manifest, command-identity, authorization-validation, and zero-live planning compatibility; its combined execute, scoring, causal-classification, and reporting authority is retired. The ordinary product path and its prompt, schema, parser, validator, runtime projection, and initial acceptance behavior are unchanged. |

The shared parser keeps factual numeric assertions inspectable when they appear
under source/reference headings, in Markdown bullets, brackets, accounting
parentheses, compact currency or compact currency-rate forms, or bounded
hyphenated-cardinal forms. Only rows matching a bounded affirmative
reference-only grammar are omitted; ambiguous reference-noun rows remain
inspectable. Numeric-looking nontransport surfaces that the bounded exact parser
does not normalize, including factual word ordinals and unconsumed superscript
or subscript digits, receive an enum-only unsupported marker and fail closed.
Accounting currency parentheses retain a negative sign posture rather than
collapsing to positive.

## Current Ordinary Multi-Component Flow

For a qualifying request, the ordinary entrypoint selects the bounded class,
derives component work, and runs Component Analyst cases under RunKernel-owned
scheduler leases. The ordinary CLI product composition uses Scheduler V3;
generic closed-default and no-need runs remain V2-compatible. RunKernel directly
admits current component cases;
Cross-Component Analyst proposes synthesis or one typed query-resolution
proposal; synthesis D-prime validates exact relationships; and RunKernel admits
canonical graph/synthesis state. An arbitration-selected searched-premise
proposal may trigger bounded SearchOS recovery and selective recomputation.
Fresh current-state Cross-Component Analyst reconciliation runs whenever
recovered or newly inferred upstream authority makes a previously blocked
target derivable, before another recovery decision is allowed.
The resulting admitted state
continues through ordinary Sufficiency, FinalAnswerPacket, Author, RunOutcome,
and CLI output, or reaches the safe blocked non-Author terminal when required.

Hosted width-2 overlap is limited to eligible initial component transport.
Canonical mutation, graph reduction, synthesis, recovery, selective
recomputation, Scrutineer, Sufficiency, FinalAnswerPacket, and Author remain
serial on the main product thread.

In the fixed ordinary product composition, typed quantitative Specialist work
is inserted between its originating proposal and the applicable D-prime review.
It remains serial on the main thread, consumes no semantic-envelope unit, and
has no admission or answer authority. Exact Scrutineer synthesis-leaf
remediation requires fresh synthesis D-prime and fresh Scrutineer review. A
failed predispatch reconstruction retains no input or result, returns its
reservation with zero spent units, and exposes one typed handoff. Optional
failure remains visible to D-prime and continues; required failure leaves the
handoff pending because D-prime does not run, then reaches the existing safe
non-Author terminal.

The installed quantitative adapter accepts only exact selected literals from
transient component or synthesis catalogs. Synthesis operands require proof
through the admitted component claim to the same literal in underlying current
component evidence. Decimal arithmetic, unit/precision derivation, and exact
claim alignment are deterministic. Estimates, arbitrary formulas, conversions,
number invention, and acquisition remain unsupported.

The model-visible quantitative proposal contract is versioned and digest-bound;
the same declarative field, operator, and bound facts are consumed by runtime
validation before Specialist work creation. The parsed proposal must supply the
exact generic instance schema and is retained only transiently; unknown fields,
fixed-value drift, target/source mismatch, and malformed requests are not
softened. Missing source posture is not treated favorably, and component
admission cannot upgrade underlying evidence. Contract, full catalog, and source
material retention remains closed outside the transient role/adapter scope.

At finalization, FinalAnswerPacket projects current numeric authority by claim,
not as a global value/unit allowlist. FAP is the final semantic-authority
boundary: it structurally checks required source/Specialist/currentness,
Component Analyst or applicable validation, value/unit/sign/scale/precision,
and citation lineage before deriving Author input. Ordinary Author receives
fixed no-calculation/no-conversion instructions and FAP-authorized material, but
may paraphrase naturally without parser-specific wording requirements.

Author is the final semantic actor. Candidate prose is not buffered solely for a
post-Author quantitative semantic check. Deterministic AuthorProse relies on
the earlier structured hardened-FAP check, and the guarded follow-up finalizer
has no accepted-prose semantic-gate authority. The retained parser/validator is
an evaluation diagnostic only; it cannot alter FAP, Author output, citations,
canonical state, RunOutcome, or trigger a model retry.

No Specialist capability, operator, proposal policy, budget, route,
acquisition behavior, provider/model selection, synthesis architecture, or
follow-up product activation changed as part of this boundary repair.

The guarded follow-up response-finalization capability remains installed
internal supporting machinery; its availability does not establish ordinary
saved-thread product consumption. The old saved-thread Streamlit follow-up path
through `ui.pages_followup` and `core.followup` is legacy and retired from
ordinary product use. It is not a current consumer of the guarded finalizer or
a shared accepted-prose validator: no shared accepted-prose validator remains
as final-answer authority. Any future conversation or follow-up activation must
consume the FAP/Author boundary through transport-neutral application services
and must be explicitly activated.

The hardened `SufficiencyReadiness -> HardenedFinalAnswerPacket ->
AuthorProseFinalization` route preserves two component-scoped quantitative
authority classes. Hardened direct source-explicit numeric authority requires
exact current component, semantic-observation, content, coverage,
evidence-custody, proposition-fingerprint, and complete literal-signature
binding. Completed component S1 authority preserves the installed capability
and version, result and handoff identities and digests, canonical component
target, exact claim-material binding, canonical `result_unit` and precision,
and terminal consumption by the current Component Analyst case and direct
RunKernel component admission. Generic semantic admission alone remains
nonauthority for arithmetic, conversion, aggregation, comparison, or same-value
proposition reuse. Invalid or incomplete numeric lineage blocks hardened FAP
before AuthorProse state construction; generated prose is not reparsed as a
semantic acceptance condition.

The current hardened FinalAnswerPacket owner packages component entries only.
It does not project synthesis entries and does not install a hardened synthesis
sidecar. Ordinary synthesis-origin S1 authority remains owned by the ordinary
ComponentWorkGraph / synthesis D-prime / ordinary FinalAnswerPacket path.

Cross input reproof is unconditional. The ordinary caller may prove the exact
transient packet directly; RunKernel independently reconstructs it from current
scheduler-owned component Analyst packets and their existing scheduler
authority digest. Missing or stale reconstruction authority fails before graph
reduction, and no packet, contract, catalog, or source material is newly
retained or exported.

## Component-Gap Recovery Eligibility And Custody

This section describes the retained non-SearchOS compatibility component-gap
route. It is not ordinary SearchOS existing-gap authority. On a SearchOS run the
installed canonical lease described below owns required existing-component and
source-obligation recovery, and this compatibility route is gated out.

Every supported mode now resolves the recovery-related slice of one shared
mode-policy envelope. The installed values are temporary compatibility values,
not permanent mode design: `Balanced` preserves the existing one-cycle,
offline-only, existing-candidate-query eligibility; `Fast` is recovery-closed in
this phase; and `Deep` is recovery-closed pending a later explicit mode-policy
decision. Unsupported modes resolve the same envelope shape with
`mode_supported=false` and fail closed. No permanent mode budget was selected.
This contained recovery posture was installed at
`ffd6796e37fac468c826afd29767aafe1e235f41` and remains unchanged by the later
Specialist proposal-admission repair.

Every resolved envelope enters the same mode-neutral coordinator and recovery
primitive. Closed Fast and Deep values return an unrecorded non-applicable
result before adapter invocation, so they create no component-gap recovery
history or projection; unsupported mode returns an unrecorded blocked result.
Eligible Balanced execution requires an explicitly composed offline adapter.
The primitive then uses RunKernel authorization and admits recovered evidence
and component coverage through RunKernel's canonical EvidenceLedger and semantic
component-coverage state. Only the canonically committed recovered passages
return to the orchestrator. Initial and post-recovery final evidence,
selected-authority Author evidence, and Author prompt material consume the same
ordinary typed materialization handoff and its existing mechanical owners;
recovery supplies none of those authority fields. Sufficiency runs again from
the current canonical state before FAP can package material, and Author can run
only from the resulting FAP payload.

The supported ordinary CLI composition still supplies no adapter for this
retained compatibility route. It therefore cannot complete that legacy recovery
cycle. This does not limit the canonical SearchOS existing-gap lease now
installed for all three supported profiles. No live recovery composition,
accepted contract amendment, or derived-component authority is installed here.

## Retired Legacy Economist Ordinary Execution

Legacy Economist execution is retired from the ordinary CLI/backend product
path. The ordinary orchestrator no longer gates, preflights, schedules, or calls
the Economist, and current dependency composition does not inject
`run_economist_step`. Configuring `OPENAI_API_KEY` does not restore that path.
The former quantitative-preflight Author note is likewise absent. That
retirement did not itself change Linkup acquisition; current Linkup
`searchResults` eligibility is now owned by the later provider-capability
routing foundation below. The separate provider-synthesis precision path is
retired.

The `RunDeps.run_economist_step` field remains optional and unread as an
isolated compatibility shape. The legacy implementation, its direct
source-binding and code-execution safety tests, retained Streamlit references,
and passive handoff/trace fields remain repository-visible legacy material.
Ordinary traces identify retirement explicitly, keep `economist_ran` false and
`economist_seconds` zero, and do not produce an Economist packet. Those fields
are compatibility data, not a dormant execution route or future authority.

This retirement installs no replacement economic Specialist. The existing S1
`specialist.source_bound_calculation` capability remains the only installed
bounded quantitative Specialist: it performs deterministic calculations from
exact selected source literals inside the named bounded multi-component class.
It does not provide broad economic analysis, arbitrary formulas, estimates,
acquisition, or general quantitative reasoning.

## Installed Acquisition Routing, Control, And Adapter Runtime

Runtime/test commit `6fbca602afac5a00bb6bafa2a6888b6ec31d5065`
installs the canonical ordinary provider-result handoff while preserving the
initial-discovery transport retirement at
`48a309124764d813cf27081bf5871d5a9612db79`. The current chain is:

PR #507's network-attestation code is inactive after the PR #508 revert. The
current tree is the post-PR-#506 foundation: PRs #503 through #506 remain
active. No DNS snapshot, connected-address, redirect-chain, or mandatory final/
canonical-URL acceptance requirement from the reverted change governs the
ordinary product.

```text
QueryPlan and authorized item
-> ProviderPlan record and completed DISCOVER route
-> deterministic retrieval action and provider call
-> retrieval.DiscoverySourceResultIdentity before dedup/chunk/rank
-> retrieval.DiscoveryResultMaterialStore
-> existing chunking, RRF/relevance, URL filtering, and selection
-> ordinary RunKernel.SearchExecutorHandoff revision 1
-> RunKernel.SearchResultCandidatePacket revision 1
```

`retrieval.DiscoverySourceResultIdentity` owns immutable occurrence identity.
Each admitted returned position binds the exact run/request, QueryPlan/item,
query digest/role, retrieval role/iteration/action, ProviderPlan/record/route,
provider operation, pre-dispatch call ordinal, original provider-result rank,
normalized URL/domain/date, and material ref/digest/class. It is created before
URL deduplication, passage chunking, relevance ranking, or candidate selection
and contains no provider text or raw payload.

`retrieval.DiscoveryResultMaterialStore` owns run-local bounded provider
material. It retains one occurrence record even when URLs duplicate. Existing
ranking and RRF choose the representative; `provider_result_rank` remains the
provider's original returned position, relevance/chunk score remains the
existing ranker's fact, and `selected_candidate_rank` is final selection order.
Duplicate occurrences keep distinct identity/material lineage and contribute up
to eight refs plus total, overflow, and full-sequence digest.

Provider-call ordinals are reserved before concurrent submission, and result
reduction follows submission order rather than completion order. Exact bounds
are 5/6/8 admitted results per provider call for Fast/Balanced/Deep, 80
identities per run, 4,096 canonical bytes per identity, 20,000 material
characters per occurrence, 8 contributor refs, 220 title characters, 500
snippet characters, 8/20/40 selected candidates, and a 16 KiB reference-only
RunKernel projection. The compact projection retains at most eight selected
refs plus overflow facts and a digest covering the full selected order. It
contains no provider text, passage chunks, embeddings, or raw payload.

Revision 1 is the immutable initial ordinary post-DISCOVER selection after
initial AnswerContract and QueryPlan admission but before
source-class/conflict recovery and synthesis. The packet therefore carries the
exact active AnswerContract ref. Candidate records remain provenance-only and
do not copy singular component or source-obligation authority. Authorized
SearchJudgment follow-up results retain truthful identities and enter separate
append-only iteration candidate sets; raw-store visibility and later recovery
cannot mutate revision 1.

The ordinary `RunKernel.SearchExecutorHandoff` origin is
`ordinary_query_provider`, with execution mode
`post_discovery_reference_handoff_only`. It reuses the existing owner and binds
QueryPlan/ProviderPlan membership, retrieval action refs, the identity-set ref,
and selected result refs after provider work has completed. It does not create
a provider call or recreate SearchPlanner tasks. The existing
`RunKernel.SearchResultCandidatePacket` owner consumes that exact handoff and
material/identity refs under the same ordinary origin. Packet and handoff
digests, the digest of ordered candidate-record digests, selected-input digest,
identity set, full selected-ref digest, and current plan/contract membership are
rederived at authorization and reduction.
Stale, mutated, duplicate-replay, unknown-field, raw/private, or authority-
bearing input fails closed.

Unflagged Fast, Balanced, and Deep CLI/backend composition reaches the ordinary
packet and persists it through canonical trace and JSONL state. The affected
scalar telemetry retains SQLite parity; SQLite does not store the full packet.
This origin does not use `live_search_validation`; the default-disabled
structured/live-validation branch remains separate. A QueryPlan
`orientation` item now reaches this same ordinary occurrence/material/packet
chain through `core.routing`'s existing
`DISCOVER(lightweight_disambiguation)` qualifier. That route currently selects
Serper when available, but the QueryPlan item names only the provider-neutral
job class. Its result remains bounded non-evidence direction and acquires no
special Scout authority.

Provider-returned title, snippet, excerpt/summary, URL, and scalar source/date
metadata remain DISCOVER output labeled `provider_returned_snippet` or
`provider_returned_excerpt`. They are not fetched/read page content,
EvidenceLedger custody, verified source text, citations, or source-obligation
satisfaction. Telemetry has these meanings:

- returned, within-call-limit, and call-overflow counts describe provider
  response cardinality before and after the mode cap;
- identity-created, invalid-URL, run-cap-overflow, and identity-byte-overflow
  counts describe occurrence admission;
- duplicate-URL counts record duplicate occurrences without discarding their
  identities/material; contributor overflow is separately counted;
- material retained characters and truncation counts describe only bounded
  provider-returned material;
- `candidate_packets_created` and `selected_candidates_handed_off` describe the
  ordinary revision-1 handoff; and
- `discover_candidate_urls_admitted` counts provider-result URL admission,
  while `urls_fetched` counts actual separate exact-URL transports and remains
  zero for this path.

| Capability | Adapter installed | Deterministically recognized by post-discovery control | Current ordinary disposition |
| --- | --- | --- | --- |
| DISCOVER | yes | outside this post-discovery controller | existing ProviderPlan/scheduler/dispatch consumers plus canonical ordinary candidate packet; zero separate candidate-URL transport |
| READ | yes | yes | neutral RunKernel SearchJudgment may nominate only an exact current admitted candidate-use option; shared obligation IDs retain canonical multi-component lineage; existing Linkup Fetch/Tavily Extract routing reaches terminal receipt and EvidenceLedger custody; same-URL nominations reuse physical custody; direct known-URL READ remains closed |
| FOCUSED_EXTRACT | yes | yes | `focused_extract_requester_not_installed`; no current exact pre-acquisition focus producer |
| MAP_SITE | yes | yes | `map_candidate_reentry_not_installed`; no PRODUCT route or transport |
| CRAWL_SITE | yes | yes | `crawl_page_custody_not_installed`; no PRODUCT route or transport |
| General Linkup Deep | mechanical support yes | premium sequential need recognized | `premium_sequential_acquisition_not_licensed` |
| Scrutineer Deep | yes | separate existing authority | preserve existing bounded consumer |
| PROVIDER_SYNTHESIS | disabled | no | blocked |

Provider synthesis remains disabled; neither the discovery handoff nor
post-discovery acquisition creates or consumes provider-written answer
authority.

The selected-candidate packet remains provenance only. Candidate presence
alone causes no provider call, `AcquisitionNeedProposalV1`, work order, route,
exact-URL cap charge, READ, or Focused Extract. Short or missing provider
material, weak corpus, high complexity, rank, or an installed adapter does not
change the nontrigger. Only neutral SearchJudgment's exact
`REQUEST_READ_PAGE` nomination may reach FetchReadContentPacket and
EvidenceLedger custody. Custody may then enter the component semantic receiver
only through an exact SearchOS semantic-evaluation handoff; it never creates
support, coverage, or satisfaction by itself.

It remains a durable non-evidence candidate handoff before fetch/read: it is not
evidence, is not citation-eligible, and does not satisfy source obligations.

The historical AG-LIVE-XAXIS-VALIDATION-01A seam still accepts sanitized
SearchResultCandidate records only. Its provider_preference_hint is only a hint;
it creates no fetch/read, EvidenceLedger, citations, source-obligation
satisfaction, Sufficiency, FinalAnswerPacket, Author, partial-answer readiness,
or product correctness authority.

RunKernel owns post-selection SearchOS state plus proposal admission,
capability, work order, route, execution, terminal, exhaustion, custody
authorization, semantic handoff, readiness, and required-needs blocking. The
guarded executor and Linkup Fetch/Tavily Extract mechanical adapters are reached
only after a valid model nomination. Provider-failure fallback and navigation
beyond the installed one-hop boundary are not installed. Legacy ordinary-live source-custody and
main-coverage flags are not consulted, late main coverage cannot reacquire, and
the retired `AG-LIVE-SOURCE-CUSTODY` profile remains non-executable.

Historical fetch-callsite dispositions remain exact:

| Historical surface | Disposition |
| --- | --- |
| `core.pipeline.process_search_queries` selective fetch | `RETIRE`: ordinary ranking consumes provider-returned candidate material only |
| `core.pipeline._apply_source_custody_fetch_read_policy` | `RETIRE`: absent from discovery and ordinary pre-selection composition |
| `core.retrieval.fetch_page` / `fetch_url_text` and direct `requests.get` | `RETIRE`: removed with HTML parser/retry support and dependency |
| `ordinary_live_source_custody_runtime` | `ADAPT`: default-disabled/nonordinary, selected-candidate nontrigger, and explicit independent-proposal validator |
| `core.authorized_acquisition_runtime` and `core.acquisition_adapters` | `RETAIN`: canonical guarded post-selection control/mechanical transport boundary |
| provider DISCOVER adapters in `core.search_providers` | `RETAIN`: bounded provider search endpoints, never candidate URL transport targets |

Historical merge-stable SearchExecutor record: PR #330 / AG-SEARCH-EXECUTOR-HANDOFF-01; handoff consumes current_answer_contract when present; Scout/revision material is search direction only; handoff creates search task records and a search work packet; no live search/provider/fetch/read/retrieval calls were run; no EvidenceLedger/citations/source-obligation satisfaction; next implementation gate after AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01 is AG-LIVE-XAXIS-VALIDATION-01A.
That verbatim historical pre-search record is distinct from the new ordinary
post-discovery reference-only origin; its old gate clause is not current roadmap
authority.

Focused Extract, Serper evidence/custody connection, Map, Crawl, compatibility
rename, and new SearchOS evidence/final authority remain uninstalled. Serper
orientation is ordinary QueryPlan/SearchOS DISCOVER direction only and adds
none of those authorities; the former pre-QueryPlan Scout lane is retired.
Exact-candidate READ,
custody, and governed component semantic handoff are installed; custody alone
still ends before support authority. Compatibility names such as `proplex`, `python -m proplex`,
`PROPLEX_*`, `proplex.db`, and `proplex_*` remain supported. This installed
routing description makes no broad live provider, model, search, recon,
fetch/read, or retrieval reliability claim; the bounded Q1 ordinary-product
evidence is recorded above. The initial
SearchPlanner-to-QueryPlan path and initial and in-loop SearchOS judgment are
installed. PR #517 one-hop breadcrumb navigation and its
qualification/source-truth path are installed. One canonical required
existing-gap post-analysis cycle and whole-run recovery lease are installed;
derived-component recovery-generation-depth policy and recursive navigation
are not installed.
Current priority and checkpoint order belong only to [Current
Roadmap](../roadmap/CURRENT_ROADMAP.md).
The full contracts are owned by [RunKernel Post-Discovery Acquisition
Control](RUNKERNEL_POST_DISCOVERY_ACQUISITION_CONTROL.md), [Provider Capability
And Acquisition Routing](PROVIDER_CAPABILITY_AND_ACQUISITION_ROUTING.md), and
the completed [DISCOVER result candidate handoff
Build](../roadmap/DISCOVER_RESULT_CANDIDATE_HANDOFF_CONVERGENCE_01.md).

## Installed SearchOS Initial Query Strategy Convergence

`SEARCHOS-QUERY-STRATEGY-AND-RECON-CONVERGENCE-01` still owns the
product-consumed initial chain, while `SEARCHPLANNER-SPARSE-UNCERTAINTY-AWARE-PLANNING-01`
replaces its ordinary model language. SearchPlanner proposals remain passive:
the selected fast model now returns only `direct_simple` or complexity-scaled
sparse component semantics. One deterministic compiler derives labels, criteria,
materiality, mode-specific inference ceilings,
ordinal IDs and source/search compatibility records before
the existing rich validator. RunKernel initial AnswerContract acceptance remains
the sole initial acceptance owner and now preserves slot candidates, selected values,
explicit confirmation posture, and component normalization/calculation policies. Unresolved factual state does
not itself become a user-confirmation request.

The typed `search_planner_adapter` `RunDeps` seam is the ordinary initial-model
injection point. Retired Scout and PlannerRevision RunDeps fields, the inert
`core.scout` stub, and empty RunKernel Scout/Revision/SearchWorkPlan carriers
are physically absent. Ordinary `run_pipeline()` does not read or accept those
surfaces. With no explicit
planner adapter, `run_pipeline()` intentionally composes
`SearchPlannerModelAdapter` from `deps.ask_model`,
`deps.clean_json_response`, and the selected fast provider, fast model, and
reasoning posture. A transient, non-retained call wrapper supplies the current
run's configured local base URL, OpenRouter key, `CostAccumulator`, and
`search_planner` cost phase directly to the existing model helper. These
connection and accounting facts do not enter adapter fields, prompts, planner
or contract projections, QueryPlan, traces, or errors.

Ordinary composition makes exactly one logical bounded initial planner
invocation. The existing underlying model-helper retry and endpoint-fallback
policy is unchanged, so that logical invocation is not a claim of exactly one
provider request.
`DeterministicSearchPlannerAdapter` is an explicit validation-only fixture and
is not an ordinary default or failure fallback. Invalid JSON, schema,
component/query structure, selected-model configuration, or model-call failure
stops before proposal acceptance, QueryPlan
admission, or search dispatch. The legacy
Brave/recon-rewriter/researcher candidate-generation and silent `core_topic`
fallback path remains unreachable from the ordinary initial pass.

Future large-document support must enter this model boundary through bounded
safe supplied-context references or summaries. It must not redefine a
deterministic parser as semantic intake, and this phase does not implement PDF,
webpage, note, or arbitrary-document ingestion.

The ordinary front half no longer constructs SearchWorkPlan or QueryProduction
as required runtime intermediates. QueryPlan consumes the accepted AnswerContract
directly and owns compact
component, source-obligation, provider-neutral job, requirement, contract,
planner, and policy refs together with exact executable query text. QueryPlan
remains the sole
exact executable-query authority and owns text, role, order, iteration,
finalization, provider-neutral discovery job class, component/semantic-slot
lineage, and dispatch lineage. Initial posture is derived only from the accepted
AnswerContract: a stable slot becomes `standard_discovery`; an unresolved
material factual slot that does not require user confirmation becomes
`orientation`; and a confirmation-required slot creates a typed, slot-local
clarification posture with no provider dispatch. `deep_discovery` is available
only as an in-loop SearchJudgment follow-up. The ordinary first DISCOVER pass
consumes only the QueryPlan-authorized immediate jobs before `core.routing`
provider selection.

`searchos_initial_query_allocation_policy_v1` is the single code-owned tuning
owner. Its provisional defaults are one primary target, two admitted initial
candidates, and one immediate dispatch per accepted required component. Its
retained recon-ceiling field is inert ordinary compatibility and is not an
ordinary recon execution authority.
These are
soft tuning defaults, not AnswerContract or SearchPlanner schema semantics, and
are not uncontrolled user or environment overrides. A second candidate needs a
recorded distinct accepted need. Without a separate immediate-wave proof it is
preserved for later SearchJudgment and is not dispatched after results in this
phase. Exact and materially equivalent candidates are rejected while bounded
contributor lineage is retained. The legacy global low/medium/high `2 / 2 / 3`
values are not preserved as SearchOS initial-allocation product policy; existing
downstream retrieval-loop posture is unchanged and cannot truncate required
component primaries.

The sparse ordinary language cannot author recon posture, dimensions, queries,
Scout invocation, or PlannerRevision invocation. Rich Planner compatibility is
reduced to current real AnswerContract, QueryPlan, and SearchOS consumers; the
compiler no longer emits ordinary `recon_requirement` placeholders. The ordinary
convergence API has no Scout or PlannerRevision adapter inputs, the orchestrator
has no callsite for either authority, and initial planning has no routine
PlannerRevision ContractAmendment caller or fallback. The former Scout and
PlannerRevision runtime modules are deleted. Search-assisted factual resolution
now belongs solely to QueryPlan job lineage and the existing RunKernel SearchOS
worklist/judgment owner.

No live provider, model, search, recon, fetch/read, or retrieval call was made
for this offline composition build. Existing routing and READ mechanics are
reused, but evidence, support, citation, ComponentCoverage, Sufficiency,
FinalAnswerPacket, Author, post-analysis recovery, and Specialist authority are
unchanged.

## Installed SearchOS Slice A Iterative Judgment

`SEARCHOS-FIRST-WAVE-AND-ITERATIVE-JUDGMENT-CUTOVER-01` now owns the unified
initial and iterative acquisition judgment after accepted-contract-derived
QueryPlan admission. A dispatching run freezes
`searchos_revision_1_candidate_state_v1`, initializes one RunKernel-owned
SearchOS state with an immutable policy snapshot, and makes neutral
SearchJudgment the only forward ordinary post-result semantic decision-maker.
The non-navigation decision vocabulary is current-material semantic handoff,
candidate READ, follow-up query proposal, factual InterpretationBinding
proposal, clarification, and unresolved handoff. The separately installed
one-hop navigation request additionally permits exact breadcrumb nomination.
Model output is strict,
slot-bound, window-bound, and fail-closed; no deterministic semantic substitute
or READ-specific parallel manager remains in the ordinary product path.
RunKernel's authorized judgment request is reference-only. The model receives a
separate transient validated input containing the accepted component need,
source-obligation/SearchWorkPlan semantics, bounded directional context, and
bounded sanitized content from exact current READ packets; none of that
transient prompt text is retained in canonical state or persistence.
The same transient input carries
`searchos_judgment_decision_contract_v4`, a machine-readable mirror of the
strict `searchos_judgment_decision_v1` validator's model-visible field shape.
It defines the shared action/reason fields, exact per-action compact-selection
payload and forbidden fields, and the one-per-current-custody insufficiency
assessment required for every post-READ action except exact semantic handoff
and factual binding. Compact current identities are transient model-boundary
data. The model authors semantic choice plus those compact identities. The
validator proves authorized-set uniqueness, binds the exact current
authoritative objects, and preserves the existing canonical decision shape.
The model authors the semantic insufficiency `reason_code` and current
`read_custody_material_id` correspondence. Deterministic runtime binds the
matching current custody object, records `read_insufficient`, and binds
`judgment_request_id`, `judgment_request_digest`, and the active `slot_id`
from the authorized current request; model output that authors those
mechanical identities fails closed. READ, navigation, handoff, clarification,
and interpretation slot/basis selections use compact current identities
already present on authorized objects; the runtime binds exact current refs
before reduction. The model may author a bounded query only
for `PROPOSE_FOLLOWUP_QUERY`; QueryPlan still independently admits or rejects
that exact text and its legal job transition. The contract is not canonical or
persisted.

Each physical source-obligation slot carries its exact QueryPlan item,
component, plural semantic-obligation references, and current job. One physical
discovery query may serve multiple semantic obligations without multiplying
provider work. All accepted semantic slots remain represented; all material
unresolved factual slots independently drive orientation, while stable peers
remain preserved without becoming extra discovery targets. Slot-local legal
transitions are `orientation -> orientation` once, `standard_discovery ->
standard_discovery | deep_discovery`, and `deep_discovery -> deep_discovery`.
Peer component cursors never reset when one physical slot refines, reads, or
stops, and sibling semantic obligations never disappear when another binds or
clarifies. A true user-confirmation slot starts and remains
clarification-required without suppressing dispatch for factually orientable
peers in the same component or worklist.

The canonical `semantic_obligations_by_id` map, keyed by component and accepted
semantic-slot identity, is the runtime semantic-cardinality authority. Physical
SearchOS slots contain plural obligation IDs only; no singular compatibility
field remains an authority. SearchWorkPlan and QueryProduction are retired
ordinary compatibility carriers and do not override that map.

For an eligible unresolved factual semantic obligation, SearchJudgment may
propose one candidate-backed binding. The authorized request exposes all
eligible semantic-slot refs, while the proposal selects exactly one compact
current semantic-slot identity plus compact current basis identities. The
runtime binds those to the exact current refs.
RunKernel builds, validates, and append-only admits
`searchos_interpretation_binding_v1`, with exact replay idempotence and
conflicting second binding rejection per semantic obligation. Clarification
likewise names one compact eligible semantic slot and leaves its siblings
unchanged. The accepted AnswerContract remains byte-stable.
`searchos_effective_semantic_slot_view_v1` combines each accepted slot and its
own admitted binding only for downstream acquisition planning. A binding cannot
create or change a component, semantic-slot ownership, source obligation,
evidence, support, coverage, satisfaction, citation eligibility, Sufficiency,
or answer authority.

Follow-up query text and job class are admitted unchanged through QueryPlan and
ordinary DISCOVER routing. Each result wave enters one append-only
`searchos_iteration_candidate_set_v1` with exact parent, slot, QueryPlan,
provider/route/action, occurrence, identity-delta, selected-candidate, bounded-
material, selection, overflow, and zero-useful lineage. Deterministic validation
proves the initial QueryPlan prefix and exact identity-set growth without
mutating revision 1 or trusting raw-store-only rows. Candidate-use choices
aggregate by slot plus normalized URL with one stable option identity and a
separate immutable growing lineage snapshot. Exact per-binding candidate-state
origins never change. Repeated contributors advance the snapshot while the
stable disposition survives, without consuming extra window positions or
physical READs. Completed windows advance mechanically; custody is still judged
when no unread option remains.

An initial orientation wave with zero useful identities records an exact
`searchos_zero_result_initial_discover_wave_v1` instead of manufacturing a
candidate packet. The same worklist and SearchJudgment may authorize exactly one
orientation refinement within policy; another empty result reaches typed
unresolved or budget-exhausted state. No parallel zero-result controller or
global cursor reset exists.

All DISCOVER material remains `directional_candidate_context`. It can guide
retrieval judgment but cannot create readable-source custody, support proposals,
coverage, satisfaction, citations, Sufficiency, FinalAnswerPacket, or Author
authority. Slice A READ executes only from an admitted candidate-use option
through RunKernel acquisition, existing routing/adapters, terminal receipt,
custody authorization, FetchReadContentPacket/SanitizedContentReference, and
EvidenceLedger. Direct known-URL READ is not installed. Same normalized URL
reuses custody; a failed transport records one attempt and no fallback.
Readable source insufficiency is recorded only from an exact post-READ model
assessment, never from transport, route, authority, stale-lineage, or invalid-
material failure. Follow-up queries are rejected before DISCOVER when the
neutral established query-cleaning/token-Jaccard rule finds material
equivalence; distinct model text remains unchanged.

`searchos_semantic_evaluation_handoff_v1` is the only ordinary SearchOS
semantic entry. It sends exact READ custody into the direct Component Analyst
case and RunKernel admission receiver for N=1 through the accepted component
envelope. Iterative and READ material is never appended to `all_passages` or
consumed by a second semantic lane. Candidate context and custody alone remain
non-support; the Analyst case is current-bound and RunKernel admits. A
component-wide semantic handoff gate requires every relevant
material semantic obligation to be satisfied: stable or already resolved slots
remain satisfied, an unresolved factual slot requires its own admitted binding,
and pending or confirmation-required clarification blocks handoff. The handoff
artifact preserves all semantic-obligation refs and per-slot effective views.

`searchos_slice_a_readiness_v1` joins every slot to its judgment, candidate,
custody, handoff, exact current Component Analyst case, and RunKernel admission
lineage. Every required slot must reach current semantic admission before the ordinary
downstream path may continue. Otherwise RunKernel records
`SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED` and the existing safe blocked
non-Author product terminal persists the exact unresolved reasons without
query, READ, retry, recovery, successful Sufficiency, FinalAnswerPacket, or
Author authority. This checkpoint block is not `STOP_INSUFFICIENT` or final
whole-run stopping.

Evaluator, expander, utilization/disambiguation retry, weak-corpus recovery,
source-class continuation, and AG-92B do not run after the first wave on this
forward Slice A path. AG-92B and older existing-gap routes are forward-dead or
gated there, although their compatibility, direct-test, state, and helper
surfaces have not all been physically removed. The full installed boundary is
owned by [SearchOS First-Wave And
Iterative-Judgment Cutover](SEARCHOS_FIRST_WAVE_AND_ITERATIVE_JUDGMENT_CUTOVER.md).
The installed one-hop boundary below completes bounded Slice B without
installing recursive navigation.

## Installed SearchOS Existing-Gap Recovery And Stop Foundation

After the ordinary component receiver has run, RunKernel may derive
`searchos_existing_gap_basis_v1` only for a current required SearchOS slot whose
READ material was semantically handed off but whose exact accepted component
and source obligation remain unsupported or uncovered. The basis binds the
current SearchOS state, prior terminal slot digest, exact current Component
Analyst case and RunKernel admission, current ComponentCoverage facts or an
explicit canonical absence, and a compact EvidenceLedger snapshot. Optional,
satisfied, nonterminal, ambiguous, stale, tampered, or role-unproven inputs
fail before a lease exists.

`searchos_materially_novel_recovery_purpose_v1` defines novelty as a new exact
obligation-support assessment. Changed wording, prompt content, or physical
source identity does not establish novelty. The immutable policy admits at most
one existing-gap recovery cycle across the whole run in Fast, Balanced, and
Deep. Admission leaves the prior slot byte-identical, appends one new
cycle-bound slot, extends the cumulative SearchOS budget without resetting
spent work, and grants one exact lease over existing SearchJudgment, QueryPlan,
SEARCH, READ/custody, navigation, Component Analyst, direct RunKernel admission,
and ComponentCoverage consumers. Replaying the same admitted purpose returns the
already-admitted cycle with `work_authorized=false` and no new model, search,
read, semantic, Sufficiency, packet, or Author work. Conflicting or additional
purposes fail closed.

The same accepted component is reassessed through the existing Component
Analyst input packet, exact unchanged Analyst system prompt and schema, its
current case output, and normal direct RunKernel component admission. It cannot
fall through the
retained Scrutineer-derived recovery path. Scrutineer may still execute its
ordinary supervisory role elsewhere, but it supplies no input or authority to
this Boundary A cycle. Boundary A does not itself create a component,
ContractAmendment, graph transition, or inference. Boundary B is a separate
installed authorization basis over the same lease/cycle owner.

The cycle produces one immutable terminal aggregate:
`recovered` when the exact same-component admission gains coverage, otherwise
`exhausted_insufficient`. The aggregate records cumulative-delta expenditure,
closes the lease, and authorizes no further existing-gap recovery. It does not
decide final sufficiency, FinalAnswerPacket, or Author execution. Ordinary
RunAuthority Sufficiency consumes the exact terminal state, remains the sole
final stopping authority, and permits downstream execution only when current
canonical coverage is sufficient. Boundary B cannot be used as a
same-component fallback.

## Installed SearchOS Boundary B Recovery And Bounded Inference

The shared `analyst_query_resolution_proposal_v1` is proposal-only. Component
Analyst and Cross-Component Analyst may emit it only within their exact role
input. Stable replay identity binds the originating artifact, normalized
variant, recorded parent contract/graph, and sorted target set. Deterministic
arbitration admits one exact winner; list order, confidence prose, scheduling
order, SearchOS, Scrutineer, and RunKernel never choose among semantic
alternatives.

A `searched_premise` winner atomically adds one supporting-premise component
and revises its exact current answer target through the existing
ContractAmendment v2 admission/application family. Replay is checked before
currentness at proposal, amendment, lease/cycle, graph, relationship,
resynthesis, and final-reduction boundaries. Exact applied-amendment replay
returns the prior record, admission, application, new-contract projection, and
graph-transition/closure authority without new work or downstream mutation.

SearchOS then retrieves only the source-bound premise. It does not author a
conclusion or inference. Direct premise support remains depth zero. Cross-
Component Analyst proposes target-mapped relationships over exact current
premise nodes; synthesis D-prime validates them; RunKernel admits them in Graph
V1. The installed semantic inference ceilings are:

| Mode | Maximum semantic inference depth | Maximum searched recovery generation |
| --- | ---: | ---: |
| Fast | 1 | 0 |
| Balanced | 1 | 1 |
| Deep | 2 | 2 |

Graph V1 reproof preserves graph identity, adds the recovered premise, and
recomputes only the affected synthesis closure. Sufficiency prefers exact
current direct fulfillment when both direct and inferred fulfillment are
valid; otherwise it may emit the typed inferred-ready posture. FAP preserves
premise, relationship, target, depth, caveat, and prohibited-upgrade lineage;
inferred entries are never projected as direct evidence. Author renders only
that packet. Offline ordinary proofs cover Fast depth-one inference with no
recovery, Balanced depth-one inference after one searched-premise cycle, and a
Deep depth-two chain whose supporting premise is itself inference-supported.

## Installed Offline SearchOS/AnalystOS Integration Gate

PR #521 installs one reusable seven-scenario fictional ordinary-product gate
over the existing Component Analyst and Cross-Component Analyst semantic work
plane. **AnalystOS** names that semantic work plane and the selected target
topology owner in
[AnalystOS Operating Model](ANALYSTOS_OPERATING_MODEL.md). It is not another
kernel, controller, graph, or canonical-state owner. Installed runtime directly
admits current Component Analyst cases and retains the separate synthesis D-prime ordinary model call until convergence retires it.

The gate proves direct closure, one searched-premise recovery, pure depth-two
reconstruction, nested recovery followed by fresh whole-case reconciliation,
root-query retention against a distractor, and honest nonclosure. Recovered or
newly inferred upstream authority that unblocks a target triggers fresh
current-state Cross-Component Analyst reconciliation before another recovery
decision. Nested semantic-role observation custody preserves exact artifact
content; semantic-role action bookkeeping becomes canonical only after
validation; proposal selection, recording, and replay use defensive custody;
and every issued RunKernel action closes before a later observation reduces.

Searched recovery remains `Fast 0 / Balanced 1 / Deep 2`, with Deep generation
2 reachable only through exact serial lineage from generation 1. No sibling,
branching, parallel-child, or multi-premise-per-generation recovery is
installed. The Balanced two-late-premise scenario lawfully reaches
`BOUNDED LIMIT` before a second amendment, query, READ, recovery cycle,
relationship admission, inferred answer, or Author call.

This deterministic gate proves that the operating system can carry valid
model-boundary semantic proposals. It does not prove that a real SearchPlanner
or Analyst model can reliably originate the correct decomposition.
Real-model origination, arbitrary-query quality, provider quality, and live
product correctness remain unproved. Offline evaluation now observes this
canonical boundary and preserves separately owned mechanical, semantic, and
attribution postures. Semantic-judge provider/model selection is not installed,
live semantic evaluation remains unlicensed, and real prompt causality remains
unproved.

## Installed SearchPlanner Evaluation And Validation Infrastructure

The installed result is organized by durable capability, not PR chronology.

The ordinary SearchPlanner boundary now has visible/enforced output-contract
parity, strict JSON parsing, strict model-visible text and collection types,
bounded scalar and `allowed_support_kinds` validation, and immutable
privacy-safe failure stage/code/rule plus field-exact predicate attestation. The
product-boundary observer consumes that canonical failure identity without
retaining prompts, responses, provider payloads, or private material.

The owner-specific evaluation stack separately owns canonical boundary
observation, deterministic mechanical validation, provider-neutral teacher-free
semantic judgment, experiment identity and calibrated attribution,
non-overriding coordination, passive sanitized reporting, authorization,
fictional scenario construction, and startup/terminal stop attestation. Scenario
construction is deterministic and has no model, provider, broker, or ordinary
pipeline dependency. Stop attestation records bounded lifecycle, child-reaping,
manifest-consumption, call-count, and cost posture even when execution stops
before a result packet.

The evaluation command retains zero-live `plan_only` and default-closed
`execute`. Execute requires an exact versioned live addendum, fictional
scenario packet, canonical command, schedule, routes, owner identities,
retention posture, and complete budget before transport construction. The
generic loopback broker is the sole non-test live transport; no default Planner
route, semantic-judge route, or final prompt variant is selected. An authorized
trial would reuse the ordinary product-built Planner prompt, cleaner, parser,
validator, runtime projection, and initial acceptance. The
variant dispatcher may replace only the authorized instruction prefix;
mechanical nonpass withholds semantic calls, while mechanical PASS permits two
arm-blind semantic passes. Stochastic evidence remains capped at
`ASSOCIATION_ONLY`.

### Real-model component proof

Installed evaluator and validation infrastructure is not real-model component
proof by itself. The bounded Q1 observations above now prove one real-model
Component Analyst artifact/admission corridor through FAP readiness, but
repeatability, broader Component Analyst quality, Cross-Component Analyst
behavior, and general SearchPlanner quality remain unproved. Broker transport,
authorization, orchestration, scenario construction, or stop attestation does
not establish arbitrary-query semantic reliability, provider quality, or broad
causal effect.

### Ordinary supported-product proof

The evaluator is an OPERATOR/VALIDATION surface, not ordinary supported-product
consumption. The historical bounded Q1 observations above traversed the ordinary
pipeline through a lawful SearchOS handoff and, on the second execution,
Component Analyst semantic-artifact origination, direct admission, Coverage,
Sufficiency, FAP readiness, and Author invocation, but the former post-Author
gate stopped the result. The current offline Q1 golden-lane proof traverses the
same ordinary consumer with `direct_source_numeric`, one Author invocation,
mechanically finalized citations, a successful RunOutcome, and an evaluator
rejection that cannot block the product. The fresh cap-contract live
confirmation traversed the same ordinary consumer through FAP, but FAP blocked
before Author with three unsatisfied source obligations and zero citation-
eligible source IDs. Neither offline proof nor this bounded live non-success
establishes repeatability, arbitrary-query support, or broad live product
behavior.
Neither offline proof nor historical live observations establish repeatability,
arbitrary-query support, or broad live product behavior.

## Installed SearchOS One-Hop Breadcrumb Navigation

`SEARCHOS-ONE-HOP-NAVIGATION-PRODUCT-ACTIVATION-01` connects ordinary
candidate-origin READ custody to the existing bounded navigation foundation.
A fresh candidate READ may expose safe same-site Markdown links as URL-free
depth-1 navigation refs. SearchJudgment may select one current compact
`navigation_candidate_id`; the runtime binds the exact current navigation ref.
The installed selection reducer, acquisition route, FetchRead, EvidenceLedger, and
SearchOS custody owners then read the selected destination. Navigation-origin
custody may re-enter the existing SearchJudgment and component semantic path,
and the canonical EvidenceLedger projection is refreshed after the selected
component receiver before Sufficiency, FinalAnswerPacket, and Author consume
it. Offline product proof reaches a final answer using a fact present only on
the selected linked page.

Navigation-origin material is never offered for link extraction. Depth greater
than one, recursive navigation, navigation-specific physical reuse, cross-slot
navigation reuse, and recursive-navigation limit calibration are not installed,
are not part of the one-hop MVP, and have no ordinary product caller. Any later
license must reuse the existing acquisition, custody, and selection owners.

## Retired Legacy Semantic Scout And Ordinary Provider Synthesis

Legacy semantic Scout ordinary execution is retired. The ordinary product does
not select a Scout prompt, make a Scout model call, create Scout QueryPlan
candidates, consult a Scout continuation gate, or schedule Scout retrieval.
The Scout-specific QueryPlan finalizer, scheduler stage
`scout_directed_continuation`, provider role `scout_continuation`, and hard-coded
`exa/linkup` override are absent from their current ordinary owners. Evaluator,
expander, generic QueryPlan admission, RunKernel continuation authority,
retrieval-stop policy, disambiguation, weak-corpus recovery, source-class
recovery, and AG-92B retain only residual or deferred compatibility surfaces
outside the forward ordinary SearchOS Slice A path; they have no post-first-wave
continuation authority there.

The isolated component-gap recovery owner and retained direct semantic
producer/reducer compatibility seams remain executable for their own fail-closed,
idempotency, atomicity, contract, custody, and ledger-authority invariants.
Only fixtures whose success condition requires the retired ordinary forward
composition remain explicitly skipped; those skips are not counted as current
product-path proof.

The former ordinary legacy dynamic derived-component recovery runtime is
deleted and has no ordinary fallback. Analyst-originated Boundary B now reuses
the installed ContractAmendment, graph-reentry, and selective-recomputation
owners under canonical post-analysis SearchOS recovery.

`QUANT_REPORT_TYPES` remains an Analyst evidence-slice constant owned by
`core.pipeline`. The former inert `core.scout` stub, official-current
SearchWork shadow handoff, empty RunKernel Scout/Revision/SearchWorkPlan
state, SearchExecutor Scout/Revision ancestry, and QueryPlan recon-rewrite
vocabulary are physically deleted where they had zero supported current
consumer. Historical tests and comments were not consumers. QuestionMeaningRecord
and READ `search_work_plan_ref` names remain only where they participate in
current schema identity.

Ordinary Linkup provider synthesis is also retired. No ordinary eligibility,
call, response-processing, or Analyst-context path uses Linkup
`deep/sourcedAnswer`, so provider-written answers cannot enter ordinary Analyst
input through the former precision block. The lower-level precision helper is
retained only for named offline diagnostics and provider-error validation;
generic acquisition continues to reject `sourcedAnswer`. Ordinary Linkup
`searchResults`, including Scrutineer-authorized `deep/searchResults`
remediation, remains unchanged.

This repair installed no provider-capability routing, provider ordering, Linkup
Fetch, Tavily site acquisition, replacement semantic role, or live validation.

## Not Installed

- Calibrated provider preference/economics policy for the three QueryPlan job
  classes; the installed mapping reuses the current code-owned routing policy.
- Arbitrary-query multi-component support.
- Legacy Economist execution in ordinary CLI/backend runs.
- Legacy semantic Scout execution in ordinary CLI/backend runs.
- Ordinary Linkup provider-written answer synthesis.
- A replacement economic Specialist or broad quantitative reasoning agent.
- Social-source acquisition or a Social Awareness specialist.
- Additional product Specialists, arbitrary formulas, estimates, or unit/currency conversion.
- Adaptive provider concurrency or Local component parallelism.
- Graph-bound, synthesis, recovery, selective, or Scrutineer parallelism.
- Hardened synthesis entries or a hardened synthesis sidecar.
- Permanent Fast/Balanced/Deep graph or semantic-call budgets.
- Hosted or Local capacity characterization.
- A selected current UI framework or final UI/productization work.
- An ordinary saved-thread conversation or follow-up product workflow.
- Ordinary-product requesters for Focused Extract, Map, Crawl, or general
  Linkup Deep.
- An ordinary current-material-need producer for Focused Extract.
- Live CLI validation of READ custody or main-RunKernel coverage.
- Map topology selection, Map-to-READ/Focused re-entry, or Crawl page-level
  custody.
- Provider-failure cross-provider retry.
- SearchOS recursive breadcrumb navigation, navigation depth greater than one,
  or sibling, branching, parallel-child, or multi-premise-per-generation
  searched recovery.
- DISCOVER-attached readable-source custody or support eligibility.
- Direct current-need known-URL READ outside admitted candidate state.
- A browser or general local scraper as an ordinary product path.
- A complete PDF acquisition path; the retained pure text-layer parser alone
  does not provide one.
- OpenRouter, LM Studio, Exa, LinkUp, embeddings, Tavily extract/map/crawl, or
  alias-only routing through the generic provider-execution broker.

## Not Proved

- Two historical bounded Q1 ordinary-product runs, one offline golden-lane
  proof, and one cap-limited post-repair Q1 run are recorded above; they do not
  establish broad live validation or repeatability.
- The post-contract live confirmation is additionally recorded above; it also
  does not establish broad live validation or repeatability.
- Real-model factual InterpretationBinding selection accuracy, abstention
  quality, and false-binding rate remain unproved.
- Real-model user-clarification quality and arbitrary-query job escalation
  quality remain unproved.
- Broader real-model SearchPlanner behavior and quality remain unproved.
- Broader real-model Component Analyst quality remains unproved.
- Real-model Cross-Component Analyst behavior remains unproved.
- Real-model Component Analyst case posture and direct RunKernel component
  admission beyond the bounded Q1 observation remain unproved.
- Real-model synthesis D-prime behavior remains unproved.
- Real-model full Scrutineer behavior remains unproved.
- Supported cited Q1 completion remains unproved in live product evidence.
- Successful Author quantitative finalization for Q1 is proved offline only.
- Broad SearchOS or general-query reliability remains unproved.
- The offline SearchOS/AnalystOS gate does not prove that a real SearchPlanner
  or Component/Cross-Component Analyst reliably originates its required
  semantic decomposition.
- No acquisition-completeness repair was performed.
- Broad arbitrary-query query-strategy quality and post-result sufficiency
  judgment remain unproved.
- Arbitrary-query decomposition and broad route qualification remain unproved.
- No broader acquisition-completeness repair was performed beyond exact
  selected-page READ custody.
- Cross-provider duplicate-URL material choice and completion-order parity were
  not redesigned or claimed; deterministic offline proof covers fixed provider
  result sets and the preserved ranking mechanics.
- Live and arbitrary-query quality of the N-component SearchOS semantic handoff
  remains unproved; installed proof is bounded and offline.
- Live or arbitrary-query quality of one-hop breadcrumb navigation remains
  unproved; installed proof is bounded, response-only, and offline.
- Focused Extract ordinary product activation remains unproved.
- Map and Crawl PRODUCT dispatch remain unproved and uninstalled.
- No AnalystOS Stage A/B/C live execution was performed by the generic broker
  installation phase.
- No S1 capability, route eligibility, budget, scheduling order, recursion, or
  parallelism expanded.
- No new Specialist capability was added.
- No hardened synthesis path was activated.
- Broad live correctness, answer quality, and production stability remain
  unproved.
- Broad live end-to-end product correctness or competitive answer quality.
- Live quantitative correctness or broad quantitative reasoning quality.
- Broad ordinary quantitative or economic-analysis replacement coverage.
- Arbitrary-query readiness.
- Maximum useful hosted or Local concurrency.
- Production stability across normal user traffic.
- Social representativeness or sentiment correctness.

Installed offline architecture must not be represented as live-product
validation.

## Compatibility And Naming Notes

ScryRaven is the public project name. Compatibility names including `proplex`,
`python -m proplex`, `PROPLEX_*`, `proplex.db`, and `proplex_*` state keys remain
supported. RunKernel / RunAuthority is the current authority direction;
`core/pipeline_orchestrator.py` remains a coordination shell with authority debt,
and this document does not license changes to that surface.

## Canonical Architecture Links

- [AnalystOS operating model](ANALYSTOS_OPERATING_MODEL.md) owns the selected AnalystOS target topology, semantic-role policy, mode policy, and D-prime retirement direction.
- [Multi-component synthesis runtime architecture](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md) owns the deep installed multi-component contracts.
- [Specialist graph substrate](SPECIALIST_GRAPH_SUBSTRATE.md) owns generic Specialist proposal, registry, policy, work, result, scheduling, and validator-consumption contracts.
- [Quantitative Specialist product activation](AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md) owns the installed calculator registry/policy, model-visible proposal contract, evidence bridge/quality, source catalogs, parser, provenance, claim alignment, and handoff use.
- [D-prime architecture](DPRIME_ARCHITECTURE.md) owns installed component and synthesis D-prime role contracts; selected retirement target is in [AnalystOS Operating Model](ANALYSTOS_OPERATING_MODEL.md).
- [Run-contract semantic loop](RUN_CONTRACT_SEMANTIC_LOOP.md) owns the integrated query-to-answer proposal and reduction flow.
- [RunKernel component DAG, scheduling, and concurrency](RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md) owns graph, scheduler, lease, batch, and concurrency invariants.
- [RunKernel post-discovery acquisition control](RUNKERNEL_POST_DISCOVERY_ACQUISITION_CONTROL.md) owns post-discovery capability, work-order, route, execution, terminal, and custody authorization.
- [Provider capability and acquisition routing](PROVIDER_CAPABILITY_AND_ACQUISITION_ROUTING.md) owns provider catalog, routing policy, mechanical operation matrix, and provider-material boundaries.
- [SearchOS operating model](SEARCHOS_OPERATING_MODEL.md) owns target search, source-acquisition, navigation, and recovery architecture.
- [SearchOS post-analysis recovery and inference direction](SEARCHOS_POST_ANALYSIS_RECOVERY_AND_INFERENCE_DIRECTION.md) owns the approved existing-gap and derived-component recovery boundaries, stopping convergence, inference direction, and legacy retirement doctrine.
- [SearchOS first-wave and iterative-judgment cutover](SEARCHOS_FIRST_WAVE_AND_ITERATIVE_JUDGMENT_CUTOVER.md) owns the installed Slice A first-wave boundary, candidate continuity, neutral judgment, READ material entry, N-component handoff, and readiness terminal.
- [Cross-component Analyst Workbench](CROSS_COMPONENT_ANALYST_WORKBENCH.md) owns its concern-specific proposal contract.
- [FAP / Author boundary](FAP_AUTHOR_BOUNDARY.md) owns final packet and prose boundaries.
- [Quantitative finalization containment](AG_S1_QUANTITATIVE_FINALIZATION_CONTAINMENT_01.md) owns FAP-side numeric authority and evaluator-only diagnostics across finalization consumers.
- [RunAuthority implementation guide](../codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md) owns authority-migration procedure.

## Current Roadmap

The current strategic decision gate is owned exclusively by [Current
Roadmap](../roadmap/CURRENT_ROADMAP.md). Planned capabilities are not installed-
state claims. This owner does not select work, an acceptance slice, future
component evaluation, or another documentation phase.

## Historical Provenance

The former Controller-era rollup remains at
`docs/history/architecture/SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md`.
Completed phase records and Git history preserve the Phase 1-5A chronology and
rationale. Read them only when a current owner routes to them or a phase
explicitly targets history; they do not override this owner.
