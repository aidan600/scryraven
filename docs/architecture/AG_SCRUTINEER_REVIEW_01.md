# AG-SCRUTINEER-REVIEW-01

Status: completed implementation posture for the first useful Scrutineer MVP.

Proof class: `component_harness_proof`.

Product path affected: RunKernel-reduced Scrutineer review state over Analyst
work product, SemanticObservation admission posture, ComponentCoverage posture,
FollowupSearchIntent refs, and follow-up remediation results. No live provider,
broker, retrieval, fetch/read, model, Sufficiency, FinalAnswerPacket, Author,
citation, source-obligation satisfaction, `current_answer_contract` mutation, or
product correctness path is opened.

## Result

`AG-SCRUTINEER-REVIEW-01` introduces Scrutineer as a supervisory review/sign-off layer for Analyst work product.
It is not product authority.
The Scrutineer red-teams whether Analyst support is actually backed by admitted
SemanticObservation and custody, whether ComponentCoverage overclaims, and
whether currentness, contradiction, scope, weak-source-class, missing-component,
or failed-remediation issues remain.

The canonical state is one RunKernel-reduced Scrutineer review record and
projection. The record captures review outcome, issue refs, sign-off posture,
contested posture, mode posture, and closed downstream surface flags. It is not
a new proposal packet and does not shadow the Analyst packet.

## Review Behavior

Scrutineer can perform an initial review and final verification around
remediation. A clean review can return `signed_off` for the
Analyst work product when support findings, admitted SemanticObservation refs,
and ComponentCoverage lineage line up. That sign-off is only Analyst work
sign-off: final-answer sign-off and product correctness remain false.

When material defects remain, Scrutineer returns `remediation_required`,
`contested`, or `blocked` and names issue kinds such as
`unsupported_analyst_claim`, `missing_semantic_observation_admission`,
`coverage_overclaim`, `currentness_unresolved`,
`contradiction_unresolved`, `scope_mismatch`, `missing_component_coverage`,
`followup_required`, `followup_attempt_unresolved`, or `lineage_mismatch`.

If a matching FollowupSearchIntent proposal exists, Scrutineer may point to its
proposal ref as a remediation candidate. Scrutineer does not authorize search
and does not run remediation. Follow-up authorization remains RunKernel-owned
through `AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01`.

After fixture-backed remediation re-enters through SearchResultCandidatePacket,
FetchReadContentPacket, EvidenceLedger, EvidenceRelativeAnalysisPacket,
SemanticObservation admission, and ComponentCoverage, Scrutineer can run final
verification. If the issue is resolved, it returns `signed_off`. If support is
still weak, unreadable, stale, contradictory, or insufficient, contested posture must be preserved
for future FAP/Author rather than smoothed away.

## Mode Posture

Fast has no Scrutineer in MVP. A Fast invocation without explicit override
returns `not_applicable`.

Balanced uses Scrutineer on red flags. When Scrutineer finds material blockers
in Balanced, the review records that a remediation loop should be reserved if
budget permits, but it still does not spend or authorize budget.

Deep requires Scrutineer later and should reserve more post-Scrutineer
remediation budget, but full Deep orchestration is not implemented by this
phase.

## Boundaries

Scrutineer does not create search authorization, query bundles,
SearchResultCandidatePacket, FetchReadContentPacket, EvidenceLedger custody,
SemanticObservation admission, ComponentCoverage, Sufficiency, FinalAnswerPacket
state, Author input, citations, source-obligation satisfaction, live calls,
broker calls, retrieval, model calls, product correctness, or contract mutation.

The next likely phase after Scrutineer was source-bound calculation Specialist MVP,
now completed by `AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01`.
