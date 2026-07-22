# SearchOS First-Wave And Iterative-Judgment Cutover

Status: current
Authority: canonical:searchos-slice-a-installed-runtime
Default-read: no
Applies-to: ordinary post-first-DISCOVER SearchOS judgment, governed READ, follow-up DISCOVER, semantic handoff, and Slice A readiness
Does-not-authorize: live calls, direct known-URL READ, DISCOVER-content custody, navigation, comprehensive recovery, final stopping, provider-policy changes, or FAP/Author redesign
Verified-against-runtime: 4431ff46ed1e8367b124f596ccc04e90040217b6
Update-trigger: merged change to the ordinary SearchOS Slice A state machine, candidate continuity, material-entry boundary, semantic receiver, or readiness terminal

## Responsibility And Product Boundary

`SEARCHOS-FIRST-WAVE-AND-ITERATIVE-JUDGMENT-CUTOVER-01` installs Slice A of
`SEARCHOS-ITERATIVE-NAVIGATION-AND-RETRIEVAL-JUDGMENT-01`. It replaces the
overlapping ordinary post-result decision paths with one neutral,
model-owned SearchJudgment state under RunKernel. The ordinary product path is:

```text
accepted AnswerContract
-> SearchWorkPlan
-> admitted initial QueryPlan wave
-> exactly one first DISCOVER wave
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

## Closed Action Vocabulary

The only SearchJudgment actions are:

```text
HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION
REQUEST_READ_PAGE
PROPOSE_FOLLOWUP_QUERY
HANDOFF_UNRESOLVED
```

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
all four actions. Every output copies request ID, request digest, and slot ID
and supplies an action and bounded reason. A non-semantic-handoff action after
READ must assess every exact current custody ref as `read_insufficient` with
the three-field assessment shape. Semantic handoff instead carries a nonempty
exact custody selection and no assessments. Follow-up query text is authored
only by `PROPOSE_FOLLOWUP_QUERY` and remains independently validated by
QueryPlan. The decision contract, like the bounded material and prompt, is a
transient model-call aid; only non-content digests may cross the durable
boundary.

`HANDOFF_UNRESOLVED` is a slot-level open-need record. It is not rewritten as
`STOP_INSUFFICIENT` and does not authorize recovery or final stopping.

## First-Wave Boundary And Retired Forward Authorities

The first admitted QueryPlan wave is the only provider wave that may run before
SearchJudgment. After its results exist, evaluator, expander, utilization or
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

Provider selection, depth, routing, and adapter mechanics remain unchanged.
QueryPlan compares the exact proposed text with every admitted executable query
using the neutral pure query-cleaning and token-Jaccard rule shared with the
established 0.7 redundancy threshold. Equivalent text is rejected before
DISCOVER; genuinely distinct text is admitted unchanged.

## Immutable Candidate State And Append-Only Continuity

`searchos_revision_1_candidate_state_v1` is created immediately after the first
admitted DISCOVER wave. It freezes the initial QueryPlan and discovery identity
snapshots, selected candidate refs, bounded material refs, selection facts, and
overflow facts. Its bytes and digest do not change.

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
`REQUEST_READ_PAGE` is omitted while semantic handoff, follow-up query, and
unresolved handoff remain available.

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
slot, and shared capacity is separately audited. Navigation, post-Analyst
re-entry, known-URL READ, comprehensive recovery, and whole-run stopping fields
remain closed.

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

## Slice A Delivery Boundary And Nonproofs

At its own runtime checkpoint, Slice A did not complete the parent iterative-
navigation checkpoint. The following were not installed by Slice A:

- Slice B breadcrumb extraction, selection, cycle control, and navigation;
- DISCOVER-attached readable-source custody or support eligibility;
- direct current-need known-URL binding;
- Focused Extract, Map, Crawl, provider Deep/Research activation;
- post-Analyst SearchOS re-entry and comprehensive gap recovery;
- final whole-run stopping policy and AG-92B recovery/stopping retirement;
- permanent policy calibration or provider-policy changes;
- Sufficiency, FinalAnswerPacket, Author, or evidence-meaning redesign.

This is a Slice A boundary record, not the temporal installed-state owner.
Internal Slice B breadcrumb navigation was subsequently installed by
`SEARCHOS-BOUNDED-BREADCRUMB-NAVIGATION-BUILD-01`; [ScryRaven Current
State](SCRYRAVEN_CURRENT_STATE.md) owns that current truth. The other listed
surfaces remain closed unless the current-state owner says otherwise.

Offline response-only fixtures prove product-path composition and authority
boundaries. They do not prove live provider/model quality, arbitrary-query
quality, calibrated limits, navigation, comprehensive recovery, or overall
product correctness, and they authorize no live or secrets-backed call.
