# AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01

Status: completed implementation posture for the first governed remediation
loop after `AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01`.

Proof class: `component_harness_proof`.

Product path affected: bounded RunKernel authorization and fixture-backed
reentry only. No live provider, broker, retrieval, fetch/read, model,
Sufficiency, FinalAnswerPacket, Author, citation, source-obligation
satisfaction, `current_answer_contract` mutation, or product correctness path is
opened.

## Result

`AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01` adds the first governed
remediation loop for Analyst gap follow-up search proposals.
FollowupSearchIntent remains proposal-only and cannot authorize search by
itself. RunKernel owns follow-up search authorization, reduces the authorization
observation, and records a bounded authorized work identity plus query bundle.
The authorized work identity/query bundle is not live dispatch and does not
mutate `SearchExecutorHandoff` state.

Fixture-backed reentry proves the future product path without live providers:

```text
FollowupSearchIntentPacket proposal
-> RunKernel follow-up search authorization
-> bounded authorized work identity/query bundle
-> SearchResultCandidatePacket
-> FetchReadContentPacket
-> EvidenceLedger custody
-> EvidenceRelativeAnalysisPacket
-> SemanticObservation admission bridge
-> ComponentCoverage reduction
```

The fixture path proves only that new follow-up candidate/read material can
return through existing custody, Analyst, SemanticObservation, and
ComponentCoverage reducers after RunKernel authorizes the work. It does not
prove live dispatch, source discovery quality, citation eligibility, source
obligation satisfaction, Sufficiency, FinalAnswerPacket readiness, Author input,
or product correctness.

## Authorization Policy

The new authorization reducer validates `FollowupSearchIntentPacket` lineage,
current-answer-contract digest, proposal readiness, source-class hints,
duplicate work, mode budget, logical depth, and whether new evidence is
expected. Fast has zero follow-up budget. Balanced permits two loops at logical
depth one, with a concrete unresolved blocker for the second loop. Deep permits
three loops by default, or four only with explicit extra recovery authorization.

The authorized work identity is SearchExecutorHandoff-style only so downstream
candidate packet code can preserve a stable handoff-shaped identity. It is not
an actual SearchExecutorHandoff state mutation, not a SearchWorkPlan, and not
provider dispatch.

## Reentry Posture

Fixture-backed readable material may create admitted SemanticObservation support
and then ComponentCoverage through the existing reducers. Failed, stale,
insufficient, or contradictory fixture material remains
blocked/follow-up-required/contested. Attempt status is never upgraded to
support.

No new durable packet is introduced for the authorization/reentry helper. The
helper returns compact runtime results; canonical state is RunKernel action,
observation, and projection state plus the already existing packet/reducer
surfaces.

## Boundaries

No Sufficiency/FAP/Author/citation/source-obligation satisfaction/product correctness is proved.
No provider or broker is called, no retrieval runs, no live fetch/read executes,
no model is called, and `current_answer_contract` is not mutated.

Scrutineer comes next. The follow-up loop can create support or preserve
blockers, but Scrutineer still needs to review support, conflicts, drift, and
gaps before later Sufficiency/FAP/Author work can become coherent.
