# D-prime architecture

Status: Updated through DPRIME-MULTI-SOURCE-ANALYST-AND-SCRUTINY-01.
Mode: BUILD.
This overview documents implemented product-consumed D-prime authority. It does
not license live/model/provider/search/fetch/read/retrieval calls,
multi-component support aggregation, full Scrutineer remediation,
Economist/Specialist expansion, or product correctness.

## Purpose

D-prime is ScryRaven's bounded evidence-relative model-review lane. It lets the
product smart model review custody-bound bounded source material against a
specific answer component and source obligation. Model review itself does not
create admitted support, citations, readiness, answer prose, or correctness; the
ordinary RunKernel/product path must consume each later authority surface.

D-prime exists to make evidence-relative semantic review inspectable without
letting custody, bounded content, model agreement, or validation ceremony become
support-bearing product state.

## Why D-prime exists

D-prime replaces this unsafe pattern:

```text
deterministic parser says yes
+ model says yes
= support
```

with this bounded authority chain:

```text
deterministic code frames and validates the review object
+ a licensed model performs bounded evidence-relative judgment
+ deterministic validators check schema, references, lineage, and output
+ RunKernel alone admits, rejects, or challenges support-bearing state
```

The deterministic parts do not understand broad natural-language evidence by
themselves. The model review does not own product authority. RunKernel remains
the only owner of support-bearing admission, rejection, or challenge.

## Current authority chain

Current implemented product-consumed D-prime status flow:

```text
generic single-relation Analyst intake
-> relation-derived component/source/evidence refs
-> source/evidence custody and readability
-> EvidenceFramePreflight
-> NegativeControlProfile
-> DPrimeOneShotProviderBoundary / DPrimeOneShotModelReviewAdapter
-> one-shot model review
-> EvidenceRelativeSupportAssessment
-> SupportProposalValidationResult
-> ValidatedSupportProposal candidate
-> RunKernelSupportProposalAdmissionRequest ready
-> optional one-component multi-source relation posture and narrow deterministic
   Scrutineer gate may admit compatible sources into the same support bundle
   before answer-path consumption
-> RunKernel-owned admission decision made for admitted relation(s)
-> ordinary D-prime RunKernel/product accepted/current contract authority
-> SemanticObservation materialized/admitted for compatible relation(s)
-> ComponentCoverage bound through existing RunKernel coverage authority
-> source-obligation authority consumed
-> citation eligibility / citation-source handoff authority consumed
-> SufficiencyReadiness consumed
-> hardened final answer packet consumed
-> Author/answer output consumed
-> citation/source display consumed
-> optional RunKernel-owned D-prime follow-up search re-entry can loop back
   through ordinary search before second-pass D-prime support
-> product correctness remains unclaimed
```

The chain is surfaced through `DPrimeStatusPayload` in
`proplex.live_semantic_coverage_status`. The current single-lane admitted path
targets a `PASS` status only when each authority surface above is consumed by
the ordinary status path.

After DPRIME-GENERIC-ANALYST-INTAKE-AND-RELATIONS-01, the ordinary product
status path builds and consumes a generic single-relation D-prime Analyst intake
from the user query, one answer component, one source-obligation lane, and one
retained bounded content/source relation. The intake is lineage only. Product
status derives the component and source-obligation refs from it before D-prime
preflight/model review and before the support bundle, answer path, and optional
follow-up loop consume the relation. This does not add multi-component handling.

After DPRIME-MULTI-SOURCE-ANALYST-AND-SCRUTINY-01, the ordinary product status
path may consume additional generic single-relation D-prime inputs for the same
answer component and source-obligation lane. The multi-source runtime aggregates
source count, support-bearing relations, caveats, currentness, and contradiction
posture, then routes that posture through a narrow deterministic Scrutineer
gate. Compatible sources are admitted/materialized through the existing
RunKernel/SemanticObservation path and are bound into the existing support
bundle, source/citation handoff, FAP, Author, and citation/source display path.
Contradiction, currentness conflict, missing gate, unsupported overclaim, or
source-laundering posture blocks before ComponentCoverage and answer-path
consumption. This does not add multi-component aggregation, full Scrutineer
remediation, Economist/Specialist routing, live validation, or a product
correctness claim.

At that point a validator-valid proposal candidate and a lineage-only
`RunKernelSupportProposalAdmissionRequest` may exist. When the RunKernel-owned
decision runtime reports `admitted`, the ordinary D-prime status chain creates
and consumes an in-memory `RunKernel` product authority surface from
`core.dprime_ordinary_contract_authority_runtime`. That surface establishes
accepted/current answer-contract authority through the RunKernel-owned
`dprime_current_answer_contract_authority` reducer, then passes the RunKernel to
the existing SemanticObservation materialization runtime.

The retained `current_answer_contract_ref` / digest on the candidate and
fetch/read packets is lineage only. It is not an accepted/current
answer-contract authority surface and must not be inflated into one; the new
surface treats retained refs/digests as lineage checks and records
RunKernel/product authority separately.

After DPRIME-EVIDENCE-SUPPORT-BUNDLE-01, the ordinary product status path also
consumes the admitted D-prime `SemanticObservation` through existing
RunKernel-owned `ComponentCoverage` reduction. The coverage state is
`supported_with_caveats`, not source-obligation authority by itself: retained
source-obligation ids remain lineage until consumed by the narrow RunKernel-owned
source-obligation authority surface in
`core.dprime_source_obligation_citation_authority_runtime`.

After DPRIME-SUPPORT-BUNDLE-COMPLETION-01, the same ordinary product status path
then consumes RunKernel-owned D-prime source-obligation authority and
citation-source handoff authority. This completes the D-prime evidence-support
bundle for the source/component relation. Direct use of that support bundle by
itself still does not create readiness, FAP, Author/answer text, citation
rendering, live calls, or product correctness.

After DPRIME-SINGLE-LANE-ANSWER-PATH-01, the ordinary product status path
consumes that completed support bundle through
`core.dprime_single_lane_answer_path_runtime`. The bridge consumes
`SufficiencyReadiness`, a hardened final answer packet, Author/answer output,
and a RunKernel-owned citation/source display for the current single D-prime
lane. Product correctness remains unclaimed.

After RUN-KERNEL-FOLLOWUP-SEARCH-REENTRY-USING-ORDINARY-SEARCH-01, the
ordinary product status path can optionally consume a D-prime non-support or
challenge judgment as a follow-up need. D-prime emits the need only; it does not
own loop authorization, budget, state, provider dispatch, or search execution.
`core.runkernel_followup_search_reentry_ordinary_search_runtime` converts that
need into the existing `FollowupSearchIntentPacket`, reduces RunKernel-owned
follow-up search authorization, then reuses ordinary `SearchPlanner`,
`SearchExecutorHandoff`, live-search-validation, `SearchResultCandidatePacket`,
and fetch/read packet seams. The resulting bounded sanitized evidence is fed
back into a second D-prime review and then into the existing support-bundle and
single-lane answer path only if the second pass validates support and RunKernel
admits it.

This follow-up re-entry path is default-off and offline/fixture-backed in the
current phase. It performs no live/provider/search/fetch/read/retrieval calls,
does not create a new search subsystem, and does not make a product correctness
claim.

## Current implemented product path

Implemented and consumed by the ordinary dry-run status path:

- `EvidenceFramePreflight` from `core.dprime_evidence_frame_preflight`.
- `NegativeControlProfile` from `core.dprime_negative_control_profile`.
- `DPrimeOneShotProviderBoundary` from
  `core.dprime_one_shot_provider_boundary`.
- `DPrimeOneShotModelReviewAdapter` from
  `core.dprime_one_shot_model_review_adapter`.
- Product smart one-shot transport in
  `core.dprime_product_smart_one_shot_transport`; see
  [DPRIME_PRODUCT_MODEL_ROUTE_CONFIG_BOUNDARY.md](DPRIME_PRODUCT_MODEL_ROUTE_CONFIG_BOUNDARY.md).
- `EvidenceRelativeSupportAssessment` schema and deterministic validation in
  `core.dprime_assessment_validation`.
- `SupportProposalValidationResult`, `ValidatedSupportProposal`,
  `RunKernelSupportProposalAdmissionRequest`, and `DPrimeStatusPayload` in
  `core.dprime_support_proposal_schema`.
- RunKernel-owned D-prime admission decisions in
  `core.dprime_runkernel_admission_runtime`.
- RunKernel/SemanticObservation-owned materialization boundary for admitted
  D-prime decisions in
  `core.dprime_semantic_observation_materialization_runtime`.
- RunKernel/ComponentCoverage-owned support-bundle attempt in
  `core.dprime_evidence_support_bundle_runtime`, consumed by ordinary product
  status, which binds ComponentCoverage, consumes source-obligation authority,
  and consumes citation-source handoff authority.
- RunKernel-owned D-prime source-obligation and citation-source handoff
  authority in `core.dprime_source_obligation_citation_authority_runtime`.
- Product-status consumed single-lane answer path in
  `core.dprime_single_lane_answer_path_runtime`, which consumes the completed
  D-prime support bundle into `SufficiencyReadiness`, a hardened final answer
  packet, Author/answer output, and citation/source display without live calls
  or product correctness claims.
- Product-status consumed D-prime follow-up search re-entry in
  `core.runkernel_followup_search_reentry_ordinary_search_runtime`, which
  consumes D-prime follow-up needs through RunKernel-owned authorization and the
  ordinary SearchPlanner/SearchExecutorHandoff/live-search-validation candidate
  path before second-pass D-prime support.
- Product-status consumed generic single-relation Analyst intake in
  `core.dprime_analyst_relation_intake_runtime`, which preserves query,
  component, source-obligation, source identity, and evidence lineage only.
- Product-status consumed one-component multi-source Analyst posture and narrow
  deterministic Scrutineer challenge gate in
  `core.dprime_multi_source_analyst_scrutiny_runtime`.

The real model-review route is strict one-shot product smart transport when
licensed. Tests also exercise injected/fake callables for offline product-path
regression without proving live validation or product correctness.

## Authority split

```text
EvidenceLedger / retained custody surfaces:
  own source/evidence custody and source posture

D-prime model review:
  proposes evidence-relative meaning or follow-up need only

D-prime proposal validation:
  creates a pre-admission proposal candidate only

RunKernel:
  sole owner of support-bearing admission, rejection, or challenge

SemanticObservation:
  records admitted evidence-relative meaning only after admission

ComponentCoverage:
  records admitted component support/binding only after admission

Single-lane answer-path bridge:
  consumes ComponentCoverage/source-obligation/citation-source handoff into
  SufficiencyReadiness, hardened final answer packet, Author/answer output, and
  citation/source display for the current single D-prime lane

RunKernel follow-up re-entry:
  owns loop authorization, budget, ordinary search reuse, and evidence re-entry
  when a D-prime need requires additional bounded evidence

Generic single-relation Analyst intake:
  is lineage-only and current product-consumed input to existing D-prime
  authority surfaces

One-component multi-source Analyst posture and narrow Scrutineer gate:
  aggregate same-lane generic relations and may permit compatible additional
  source materializations into the existing product path

Product correctness / multi-component / full Scrutineer remediation / Economist:
  remain downstream and closed until separately licensed
```

## Allowed outputs

D-prime may produce:

- generic single-relation Analyst intake refs/digests with query, component,
  source-obligation, source identity, and evidence lineage only;
- bounded review input references;
- assessment result/status;
- support relation classification;
- qualifiers and missing qualifiers;
- scope, currentness, and contradiction checks;
- abstention, non-support, or challenge recommendation;
- validator-valid assessment refs;
- `ValidatedSupportProposal` candidate refs;
- `RunKernelSupportProposalAdmissionRequest` refs with proposal id/digest,
  validation status/digest, request status, and request digest;
- product-visible materialization-input blocker after a RunKernel-owned
  admitted D-prime decision reaches the SemanticObservation boundary without an
  existing authorized accepted/current answer-contract surface.
- RunKernel-owned `ComponentCoverage` refs/status/digest from the D-prime
  support-bundle runtime after admitted `SemanticObservation`;
- RunKernel-owned D-prime source-obligation authority refs/status/digest after
  bound `ComponentCoverage`;
- RunKernel-owned citation eligibility / citation-source handoff authority
  refs/status/digest after source-obligation authority;
- single-lane `SufficiencyReadiness` refs/status/digest after the completed
  evidence-support bundle;
- hardened final answer packet refs/status/digest after readiness;
- Author/answer output text and refs/status/digest after the hardened packet;
- citation/source display refs/status/digest after Author output.
- follow-up need/status refs that show RunKernel-owned authorization, ordinary
  SearchPlanner/SearchExecutorHandoff/live-validation reuse, candidate packet
  creation, fetch/read packet creation, evidence re-entry, and second-pass
  D-prime review status.
- one-component multi-source relation-set, support-posture, and Scrutineer gate
  refs that show whether compatible additional relations were consumed or why
  the answer path was blocked before ComponentCoverage.

The pre-admission D-prime assessment/proposal/request outputs are review
material and candidate state. They are not admitted support. Only the
RunKernel/SemanticObservation-owned materialization runtime may turn a
RunKernel-owned admitted D-prime decision into admitted `SemanticObservation`
state, and only when it consumes existing authorized accepted/current
answer-contract authority from the ordinary RunKernel state path.

## Forbidden outputs and nonclaims

D-prime model review, proposal validation, and request preparation must not
produce:

- canonical evidence custody;
- admitted semantic support;
- RunKernel admission decision;
- `ComponentCoverage`;
- citation eligibility;
- source-obligation satisfaction;
- `SufficiencyReadiness`;
- `FinalAnswerPacket`;
- Author-safe claims;
- answer text;
- product correctness.

The licensed D-prime support-bundle runtime may bind `ComponentCoverage` only by
consuming an admitted D-prime `SemanticObservation` through existing RunKernel
coverage authority. It may consume source-obligation authority and
citation-source handoff authority only through the narrow D-prime RunKernel
authority surfaces. It must not treat ComponentCoverage alone, retained lineage
ids, or readiness posture as source-obligation satisfaction, citation
eligibility/handoff, answer readiness, or product correctness.

The licensed single-lane answer-path bridge may consume the completed
support-bundle output into `SufficiencyReadiness`, a hardened final answer
packet, Author/answer output, and citation/source display only through existing
RunKernel/product authority. It must not run live/model/provider/search/fetch/
read/retrieval calls, open multi-component intake, or claim product
correctness.

The licensed one-component multi-source posture may add compatible additional
source materializations to the existing support bundle only after each relation
passes the existing generic intake, preflight, model-review assessment,
proposal-validation, RunKernel admission, and SemanticObservation
materialization seams. It must not resolve contradictions by itself, remediate
claims, create a separate answer path, generalize across components, or claim
product correctness.

Anti-laundering rules:

- Preflight pass is not semantic support.
- Bounded content, custody, and lineage are not semantic support.
- Model-reviewed assessment is not support.
- Assessment is not proposal.
- Proposal validation is not RunKernel admission.
- `directly_supports` is not RunKernel admission.
- Proposal candidate is not admitted support.
- Follow-up need is not search authorization.
- Follow-up authorization is not live/provider dispatch.
- SearchResultCandidatePacket is not evidence.
- FetchReadContentPacket custody is not semantic support until second-pass
  D-prime support is validated and RunKernel admits/materializes it.
- `ComponentCoverage` is not source-obligation satisfaction.
- `ComponentCoverage` is not citation eligibility.
- Citation eligibility / citation-source handoff is not citation rendering.
- Citation eligibility / citation-source handoff is not answer correctness.
- Citation/source display is not product correctness.
- Author/answer output is not product correctness.

## Semantic support vs evidential adequacy

Semantic support asks:

```text
What does the source actually say, and does it support this component claim?
```

Evidential adequacy asks:

```text
Is the source current, representative, strong, scoped, and appropriate enough
for the answer claim?
```

Example: an old single review may support "one reviewer in 2016 reported a
negative experience." It does not support "this product is currently bad" or
"customers generally dislike it."

D-prime should preserve this distinction in support relations, qualifiers,
currentness checks, contradiction checks, and challenge recommendations.

## Negative controls

D-prime's non-negotiable negative controls are:

- same-lane unrelated official text must not produce support;
- custody, lineage, and bounded content alone must not produce support;
- correct source but wrong component must not produce support;
- correct value but wrong currentness/effective date must not produce support;
- correct topic but missing answer-bearing proposition must abstain;
- contradiction should route to contradiction/challenge, not weak support;
- model assertion without selector/proposition/component mapping must reject;
- preflight pass plus model abstention must fail closed;
- model yes plus absent or failed preflight must fail closed;
- manual reviewer assertion only must reject;
- structured extractor output over unrecognized free text must abstain;
- LLM-generated preflight must not count as deterministic preflight.

`NegativeControlProfile` is configuration and validation posture. It is not
evidence, not model success, not semantic support, and not product correctness.

## Current status after multi-source Analyst/Scrutineer gate

Implemented after DPRIME-MULTI-SOURCE-ANALYST-AND-SCRUTINY-01:

- evidence-frame preflight;
- negative-control profile;
- one-shot model-review route and adapter;
- output contract and validation;
- invalid-output fail-closed handling;
- validator-valid assessment path;
- assessment-to-proposal candidate gate;
- lineage-only `RunKernelSupportProposalAdmissionRequest` preparation;
- RunKernel-owned admitted/rejected/challenged decision status surface;
- ordinary D-prime RunKernel/product accepted/current contract authority in
  `core.dprime_ordinary_contract_authority_runtime`;
- RunKernel/SemanticObservation-owned SemanticObservation materialization
  boundary for admitted D-prime decisions only;
- RunKernel-owned ComponentCoverage binding through the D-prime support-bundle
  runtime;
- RunKernel-owned D-prime source-obligation authority consumed after bound
  ComponentCoverage;
- RunKernel-owned citation eligibility / citation-source handoff authority
  consumed after source-obligation authority;
- `SufficiencyReadiness` consumed after the completed D-prime support bundle;
- hardened final answer packet consumed after readiness;
- Author/answer output consumed after the hardened packet;
- citation/source display consumed after Author output;
- ordinary product status reporting through `DPrimeStatusPayload`;
- generic single-relation D-prime Analyst intake consumed by ordinary product
  status, D-prime preflight/model-review lineage, support bundle, single-lane
  answer path, and RunKernel-owned follow-up ordinary-search re-entry;
- optional one-component multi-source D-prime relation-set/support-posture
  refs consumed by ordinary product status;
- narrow deterministic Scrutineer gate consumed before the answer path for
  multi-source posture;
- compatible additional source observations admitted/materialized through the
  existing RunKernel/SemanticObservation path and included in ComponentCoverage,
  source/citation handoff, FAP, Author, and citation/source display;
- conflict/currentness/missing-gate multi-source posture blocked before
  ComponentCoverage and answer-path consumption.

The current product-visible single-lane path reaches `PASS` only for an
admitted D-prime decision that completes the support bundle, readiness, hardened
final answer packet, Author/answer output, and citation/source display. Product
correctness remains unclaimed. Runtime does not require the historical passport
fixture component/source ids to reach `PASS`; tests include a non-passport
single-relation fixture.

Still not implemented or closed:

- product correctness;
- multi-component analyst intake;
- multi-component support aggregation;
- full Scrutineer remediation;
- Economist/Specialist expansion;
- live/model/provider/search/fetch/read/retrieval execution inside this status
  path;
- optional narrow deterministic semantic extractors.

## Open downstream surfaces

The current single-lane path is:

```text
generic single-relation Analyst intake
-> relation-derived component/source/evidence refs
-> optional one-component multi-source relation posture and Scrutineer gate
-> RunKernel-owned admission decision
-> ordinary D-prime accepted/current answer-contract authority
-> admitted SemanticObservation
-> ComponentCoverage binding
-> source-obligation authority consumed
-> citation eligibility / citation-source handoff authority consumed
-> SufficiencyReadiness
-> hardened final answer packet
-> Author/answer output
-> citation/source display
-> product correctness remains unclaimed
```

D-prime now completes this current single lane through citation/source display.
It cannot generalize beyond the current lane, skip authority surfaces, run live
calls in this status path, or claim product correctness.

## Mode posture

Modes may change budget and behavior envelope, but not truth standards.

Fast must not mean:

- weaker support;
- custody standing in for meaning;
- Author cleaning up semantic gaps;
- lower evidence standard.

Balanced and Deep may eventually vary review depth, remediation, or challenge
policy, but they do not change who owns support authority. RunKernel remains the
admission boundary in every mode.
