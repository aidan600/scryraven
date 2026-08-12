# SearchOS First-Wave And Iterative-Judgment Cutover

Status: current
Authority: canonical:searchos-slice-a-installed-runtime
Default-read: no
Applies-to: accepted-contract-derived QueryPlan discovery jobs, ordinary initial and iterative SearchOS judgment, factual binding, clarification, governed READ, follow-up DISCOVER, semantic handoff, and Slice A readiness
Does-not-authorize: live calls, direct known-URL READ, DISCOVER-content custody, recursive navigation, comprehensive recovery, final stopping, provider-policy calibration, or FAP/Author redesign
Verified-against-runtime: 96413c9a1f901dc191ecc94e6330014841ee4dda
Update-trigger: merged change to the ordinary SearchOS Slice A state machine, candidate continuity, material-entry boundary, semantic receiver, or readiness terminal

## Responsibility And Product Boundary

The installed unified front half extends
`SEARCHOS-FIRST-WAVE-AND-ITERATIVE-JUDGMENT-CUTOVER-01` without creating a
second controller. It replaces overlapping initial recon and post-result
decision paths with one neutral, model-owned SearchJudgment state under
RunKernel. The ordinary product path is:

```text
accepted AnswerContract
-> SearchWorkPlan
-> QueryPlan job + component/semantic-slot lineage
-> first DISCOVER wave, or typed no-dispatch clarification
-> immutable SearchOS revision 1
-> RunKernel-owned SearchJudgment
-> one exact authorized action
-> canonical execution and observation
-> re-judgment or governed semantic handoff
```

The cutover is consumed by the ordinary CLI/backend pipeline. It is not an
alternate harness or a trace-only authority. RunKernel owns canonical state,
action authorization, observation reduction, budget accounting, readiness, and
the required-needs block. The orchestrator only sequences those owners.

SearchWorkPlan and QueryProduction remain temporary carriers for Phase 3; they
do not own job derivation, provider selection, factual binding, or
clarification.

## QueryPlan Job And Initial-Posture Contract

QueryPlan owns exactly three provider-neutral discovery job tokens:

```text
orientation
standard_discovery
deep_discovery
```

Initial posture is derived only from the accepted AnswerContract. Stable slots
start `standard_discovery`; unresolved material factual slots of the supported
identity/currentness/document-lineage kinds start `orientation`; and slots with
`user_confirmation_required=true` create typed clarification with no QueryPlan
dispatch item. `deep_discovery` is an iterative escalation, not an initial
Planner choice. Each item binds the exact accepted component and semantic slot.
No job token names a provider.

`core.routing` remains the sole provider owner. Orientation maps through the
existing lightweight-disambiguation qualifier, standard work through ordinary
route derivation, and deep work through the existing
`general_deep_requested` authorization/blocking policy. QueryPlan, prompts,
adapters, environment variables, and SearchJudgment cannot choose a provider
brand or alter provider preference/economics policy.

## Closed Action Vocabulary

The non-navigation SearchJudgment actions are:

```text
HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION
REQUEST_READ_PAGE
PROPOSE_FOLLOWUP_QUERY
PROPOSE_INTERPRETATION_BINDING
REQUIRE_CLARIFICATION
HANDOFF_UNRESOLVED
```

The separately installed one-hop navigation request additionally permits
`REQUEST_NAVIGATE_BREADCRUMB` under its existing eligibility boundary.

Every decision is bound to the current slot, request, candidate window or READ
custody, policy snapshot, and judgment request digest. Exact-object validation
rejects malformed, wrapped, stale, unknown, or out-of-window output. There is no
deterministic semantic fallback. Model failure, invalid nomination, exhausted
budget, and unresolved handoff remain distinct canonical slot postures and
cannot claim satisfaction.

RunKernel authorizes and retains only a reference/digest judgment request. A
separate transient `searchos_judgment_model_input_v1` validates and combines
that request with the current accepted component question, source-obligation
semantics, exact SearchWorkPlan requirement, bounded directional candidate
context, and bounded sanitized text from each exact current READ packet. The
transient text and prompt are not written to RunKernel state, actions,
projections, execution traces, or persisted output.

Every transient input also carries a versioned
`searchos_judgment_decision_contract_v1`. It identifies the roles of the
authorized request, active need, directional DISCOVER contexts, and current
READ materials; enumerates the validator's allowed output fields; and gives the
exact required, forbidden, copied-ref, and conditional assessment fields for
all applicable actions. Every output copies request ID, request digest, and slot ID
and supplies an action and bounded reason. A non-semantic-handoff action after
READ must assess every exact current custody ref as `read_insufficient` with
the three-field assessment shape. Semantic handoff carries a nonempty exact
custody selection and no assessments. Factual binding carries only the exact
five-field proposal and current basis refs. Clarification carries no query,
provider, evidence, support, or contract-mutation payload. Follow-up query text
and job class are authored only by `PROPOSE_FOLLOWUP_QUERY` and remain
independently validated by QueryPlan. The decision contract, like the bounded
material and prompt, is a transient model-call aid; only non-content digests
may cross the durable boundary.

`HANDOFF_UNRESOLVED` is a slot-level open-need record. It is not rewritten as
`STOP_INSUFFICIENT` and does not authorize recovery or final stopping.

## InterpretationBinding And Clarification

`PROPOSE_INTERPRETATION_BINDING` is legal only for an unresolved material
factual slot already declared in the accepted AnswerContract, with no user
confirmation requirement. The proposal must select one declared candidate and
name exact current candidate-use or READ-custody basis refs. RunKernel alone
builds and append-only admits `searchos_interpretation_binding_v1`. Exact replay
is a no-op; identity collision, conflicting second binding, stale basis, changed
component or semantic-slot scope, new component/source-obligation scope, and
evidence/support/coverage/satisfaction/citation claims fail closed.

The accepted AnswerContract remains immutable. The
`searchos_effective_semantic_slot_view_v1` joins accepted meaning and an
admitted binding only for acquisition planning; it does not mutate canonical
requested meaning or create downstream truth authority. Semantic handoff is
illegal while required binding remains unresolved.

`REQUIRE_CLARIFICATION` records one component/semantic-slot-local terminal
posture. An initially confirmation-required slot reaches the same typed posture
without dispatch or model/provider work. Clarification on one component does
not stop independent stable or factual-orientation peers in the shared
worklist.

## First-Wave Boundary And Retired Forward Authorities

The first admitted QueryPlan job wave is the only provider wave that may run
before SearchJudgment. A clarification-only run has no wave, ProviderPlan, or
provider call. After results exist, evaluator, expander, utilization or
disambiguation retry, weak-corpus recovery, source-class recovery, and AG-92B
full SearchJudgment cannot propose or dispatch the next query on the forward
ordinary Slice A path. Their residual code remains compatibility or deferred
roadmap material, not a co-owner.
Retained component-gap recovery and direct semantic compatibility invariants are
tested through their isolated owner seams; retired-forward success fixtures stay
explicitly skipped and do not count as SearchOS product-path proof.

Post-first-wave query text may be created only by:

```text
SearchJudgment exact follow-up proposal
-> deterministic schema, scope, lineage, bounds, and nonredundancy checks
-> exact QueryPlan continuation admission
-> RunKernel-authorized ordinary DISCOVER routing and dispatch
```

Provider selection and adapter mechanics remain owned by the existing routing
and dispatch surfaces. The job class is an explicit routing input; it does not
grant provider authority. Deep work is either admitted by current policy or
returns the current typed authorization block.
QueryPlan compares the exact proposed text with every admitted executable query
using the neutral pure query-cleaning and token-Jaccard rule shared with the
established 0.7 redundancy threshold. Equivalent text is rejected before
DISCOVER; genuinely distinct text is admitted unchanged.

Legal job transitions are slot-local: orientation may refine orientation once;
standard discovery may continue standard or request deep; and deep may remain
deep. One slot's follow-up never resets a peer slot's candidate ancestry,
budget, or cursor.

## Immutable Candidate State And Append-Only Continuity

`searchos_revision_1_candidate_state_v1` is created immediately after the first
admitted DISCOVER wave. It freezes the initial QueryPlan and discovery identity
snapshots, selected candidate refs, bounded material refs, selection facts, and
overflow facts. Its bytes and digest do not change.

When an initial all-orientation wave returns zero useful identities, revision 1
instead binds an exact `searchos_zero_result_initial_discover_wave_v1` carrying
the QueryPlan, ProviderPlan, route, retrieval action, and zero-identity lineage.
It creates no candidate, READ, support, or satisfaction authority. The same
worklist and judgment owner may admit one orientation refinement within policy;
a second empty result reaches honest unresolved or exhausted state.

Each admitted follow-up wave creates
`searchos_iteration_candidate_set_v1`. The set binds its iteration and parent,
active slot, exact QueryPlan item, ProviderPlan and route facts, retrieval
actions, ordered provider-result occurrences, identity delta, selected
candidates, bounded material refs, selection/overflow facts, and zero-useful
posture. Each set has a stable digest and replay identity.

The append-only validator proves separately that:

```text
the initial QueryPlan snapshot is an exact prefix of the current QueryPlan

and

initial identities + ordered admitted identity deltas = current identities
```

It rejects revision mutation, missing or reordered iteration sets, stale parent
refs, duplicate deltas, and identities visible only in the raw discovery store.
An exact follow-up QueryPlan item's `searchos_slot_ref` is rebound through the
current SearchOS slot, accepted component, SearchWork requirement, and canonical
source-obligation snapshot; URL equality alone cannot reconstruct authority.

## Candidate-Use Options And Windows

Model-visible acquisition choices aggregate by current slot plus normalized
URL. That pair owns a stable option ID/digest. Repeated discoveries create a new
immutable lineage snapshot without changing the stable option identity or its
disposition. Each snapshot retains the complete ordered, exact candidate-state
origin, candidate, QueryPlan item, iteration-set, provider-result occurrence,
and source-material refs. A binding permanently retains the candidate-state ref
that admitted it; later waves never rewrite earlier origins.

`searchos_candidate_use_window_v1` exposes at most twelve ordered options and
records the ordinal, retained and remaining counts, the digest of the full
eligible set, and whether another window is available. Already custodied,
read-insufficient, invalid, or declined options may advance the deterministic
window without a query, provider dispatch, acquisition proposal, or READ-budget
charge. Exhaustion remains unresolved; it never becomes successful completion.
When the final window has no unread option but current custody exists,
SearchJudgment still judges the active need and bounded custody material;
`REQUEST_READ_PAGE` is omitted while the slot's applicable factual binding,
clarification, semantic handoff, follow-up query, and unresolved actions remain
available.

## Policy And Judgment Budget

`searchos_policy_profile_v1` is the sole code-owned policy surface. RunKernel
records one immutable per-run snapshot. Fast, Balanced, and Deep use the same
state machine and provisional profile-specific maximum leashes. The fixed
cross-profile bounds are eight active slots and twelve visible options per
window. Prompts, adapters, and environment variables cannot override policy.

Before a round starts, RunKernel reserves capacity for every participating
required slot. A logical call is charged only when it begins. Pre-call rejection
returns a reservation; a failed model call consumes its charge but creates no
successful capacity. Required-slot reserves cannot be consumed by an earlier
slot, and shared capacity is separately audited. Post-Analyst re-entry,
direct known-URL READ, comprehensive recovery, and whole-run stopping fields
remain outside this front-half policy; their existing separately owned behavior
is unchanged.

## Material Authority And Legal READ Path

First-wave and iterative DISCOVER material is
`directional_candidate_context`. It may guide candidate triage, retrieval
judgment, query refinement, and READ nomination. It cannot independently create
FetchReadContentPacket, readable-source custody, a support-bearing Analyst
proposal, D-prime support, SemanticObservation, ComponentCoverage,
source-obligation satisfaction, citations, Sufficiency, FinalAnswerPacket, or
Author input.

The only Slice A support-proposal-eligible material is
`read_custody_material` produced through:

```text
current admitted candidate-use option
-> SearchJudgment REQUEST_READ_PAGE
-> RunKernel acquisition capability and work order
-> core.routing
-> Linkup Fetch or Tavily Extract
-> terminal receipt and custody authorization
-> FetchReadContentPacket / SanitizedContentReference
-> EvidenceLedger custody
-> SearchOS semantic-evaluation handoff
```

READ URLs come only from revision 1 or an admitted iteration candidate set.
URLs copied or inferred from free text, model rationale, obligation labels,
unadmitted metadata, arbitrary documents, logs, traces, or raw-store-only
records cannot execute. Direct known-URL READ and
`SearchOSCurrentNeedKnownUrlBindingV1` are not installed.

Same normalized URL nominations reuse one physical custody artifact while
preserving slot-specific SearchOS custody refs. A transport failure records the
one canonical attempted call, performs no provider fallback, creates no custody,
and leaves the affected slot unresolved or invalid. Custody is still not
support: Analyst proposes, D-prime validates, and RunKernel admits.

A readable page becomes `read_insufficient` only through a successful model
judgment carrying the exact reviewed custody ref and a bounded reason code.
Transport failure, route/authority block, unreadable material, stale lineage,
and invalid nomination remain distinct postures and cannot be laundered into
semantic source insufficiency.

## One N-Component Semantic Receiver

`searchos_semantic_evaluation_handoff_v1` is the only ordinary SearchOS
semantic entry. It binds current READ custody to exact accepted component and
source-obligation slots. The accepted AnswerContract and SearchWork graph—not
SearchJudgment—own component identity, dependencies, and required/optional
posture.

The bounded component receiver accepts N=1 through the admitted component
envelope:

```text
SearchOS semantic handoff
-> bounded component Analyst proposal
-> component D-prime validation
-> RunKernel component semantic admission
```

N=1 is a one-node use of the same receiver. Iterative and READ material is not
appended to `all_passages`, and the retired direct ordinary semantic producer
does not independently consume it. The typed Analyst gap seam remains available
to report missing material or dependency gaps, but Slice A cannot execute
comprehensive post-Analyst recovery.

## Slice A Readiness And Safe Product Terminal

`searchos_slice_a_readiness_v1` joins each active slot's requirement posture,
latest judgment/action history, candidate state, custody, semantic handoff,
Analyst proposal, D-prime validation, and RunKernel admission outcome. A required
slot is ready only after the entire governed semantic chain reaches current
RunKernel admission. Directional context, custody alone, Analyst alone, D-prime
without admission, failed or rejected handoff, judgment failure, exhaustion,
staleness, and unresolved handoff are not ready.

If any required slot is not ready, RunKernel records
`SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED` with exact per-slot reasons and
closed authority flags. It authorizes no query, READ, retry, recovery,
successful Sufficiency, FinalAnswerPacket, or Author. The existing safe blocked
non-Author terminal consumes this state and persists a replay-identifiable
product outcome. It remains distinguishable from comprehensive recovery,
`STOP_INSUFFICIENT`, and final whole-run stopping.

Optional slots retain their accepted AnswerContract posture. Missing or
ambiguous required-versus-optional posture fails closed.

## Closed Work And Nonproofs

This installed unified front half does not fold the Phase-3 carriers or change
downstream truth authority. The following remain closed in this work:

- recursive navigation or navigation depth beyond the separately installed
  one-hop boundary;
- DISCOVER-attached readable-source custody or support eligibility;
- direct current-need known-URL binding;
- Focused Extract, Map, Crawl, or new provider Deep/Research activation;
- changes to installed post-analysis SearchOS recovery or bounded inference;
- changes to final whole-run stopping policy;
- permanent policy calibration or provider-policy changes;
- Phase-3 folding of SearchWorkPlan, QueryProduction, rich downstream
  compatibility projection, or legacy dead carrier fields;
- Sufficiency, FinalAnswerPacket, Author, or evidence-meaning redesign.

Offline response-only fixtures prove product-path composition and authority
boundaries. They do not prove live provider/model quality, arbitrary-query
quality, real-model binding or clarification accuracy, calibrated limits,
recursive navigation, or overall product correctness, and they authorize no
live or secrets-backed call.
