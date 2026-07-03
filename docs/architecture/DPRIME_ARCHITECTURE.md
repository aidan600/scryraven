# D-prime architecture

Status: DPRIME-ARCHITECTURE-OVERVIEW-DOC-01. Mode: REPAIR. This is a
documentation-only architecture overview; it does not license product behavior,
live/model/provider/search/fetch/read/retrieval calls, or downstream support
admission.

## Purpose

D-prime is ScryRaven's bounded evidence-relative model-review lane. It lets the
product smart model review custody-bound bounded source material against a
specific answer component and source obligation, but it does not itself create
admitted support, citations, readiness, answer prose, or correctness.

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
source/evidence custody and readability
-> EvidenceFramePreflight
-> NegativeControlProfile
-> DPrimeOneShotProviderBoundary / DPrimeOneShotModelReviewAdapter
-> one-shot model review
-> EvidenceRelativeSupportAssessment
-> SupportProposalValidationResult
-> ValidatedSupportProposal candidate
-> RunKernelSupportProposalAdmissionRequest ready
-> RunKernel-owned admission decision made
-> ordinary D-prime RunKernel/product accepted/current contract authority
-> SemanticObservation materialized/admitted
-> ComponentCoverage bound through existing RunKernel coverage authority
-> source-obligation authority missing
```

The chain is surfaced through `DPrimeStatusPayload` in
`proplex.live_semantic_coverage_status`. The current stop condition is:

```text
BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_MISSING
```

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
`supported_with_caveats`, not `satisfied`: retained source-obligation ids remain
lineage only, no source-obligation satisfaction authority is consumed, and no
citation eligibility or citation-source handoff authority is created. This is
Outcome B product progress with a named blocker, not a completed support bundle.

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
  status, which binds ComponentCoverage and stops at missing source-obligation
  authority.

The real model-review route is strict one-shot product smart transport when
licensed. Tests also exercise injected/fake callables for offline product-path
regression without proving live validation or product correctness.

## Authority split

```text
EvidenceLedger / retained custody surfaces:
  own source/evidence custody and source posture

D-prime model review:
  proposes evidence-relative meaning only

D-prime proposal validation:
  creates a pre-admission proposal candidate only

RunKernel:
  sole owner of support-bearing admission, rejection, or challenge

SemanticObservation:
  records admitted evidence-relative meaning only after admission

ComponentCoverage:
  records admitted component support/binding only after admission

SufficiencyReadiness / FinalAnswerPacket / Author:
  remain downstream and closed until separately licensed
```

## Allowed outputs

D-prime may produce:

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
- RunKernel-owned `ComponentCoverage` refs/status/digest from the licensed
  D-prime support-bundle runtime after admitted `SemanticObservation`.
- product-visible missing source-obligation authority blocker after
  ComponentCoverage binding.

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
coverage authority. It must not treat that coverage as source-obligation
satisfaction, citation eligibility, answer readiness, or product correctness.

Anti-laundering rules:

- Preflight pass is not semantic support.
- Bounded content, custody, and lineage are not semantic support.
- Model-reviewed assessment is not support.
- Assessment is not proposal.
- Proposal validation is not RunKernel admission.
- `directly_supports` is not RunKernel admission.
- Proposal candidate is not admitted support.
- `ComponentCoverage` is not citation eligibility.
- Citation eligibility is not answer correctness.

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

## Current status after admission-request gate

Implemented after DPRIME-RUNKERNEL-DECISION-AUTHORITY-SURFACE-01:

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
- named fail-closed blocker after ComponentCoverage because source-obligation
  authority is not available before closed Sufficiency/FAP surfaces;
- ordinary product status reporting through `DPrimeStatusPayload`.

The current stop point is source-obligation authority missing after
ComponentCoverage binding.

Still not implemented or closed:

- source-obligation satisfaction authority;
- citation eligibility / citation-source handoff authority;
- `SufficiencyReadiness`;
- `FinalAnswerPacket`;
- Author/answer text;
- product correctness;
- optional narrow deterministic semantic extractors.

## Open downstream surfaces

Downstream support-bearing surfaces remain closed until separately licensed:

```text
RunKernel-owned admission decision
-> ordinary D-prime accepted/current answer-contract authority
-> admitted SemanticObservation
-> ComponentCoverage binding
-> source-obligation authority missing
-> citation eligibility / citation-source handoff unavailable
-> SufficiencyReadiness
-> FinalAnswerPacket
-> Author/answer text
-> product correctness
```

D-prime can make the blocker visible. It cannot skip the blocker.

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
