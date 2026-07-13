Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG10_SOURCE_CLASS_FULFILLMENT_CONSISTENCY).

# AG-10 Source-Class Fulfillment Consistency

Status: offline calibration revision implemented; targeted tests passed.

Scope: calibrate compact answer-contract fulfillment so required source-class
gaps cannot be hidden by a generic sufficient-evidence posture. This phase did
not change live behavior, provider routing, provider selection, retrieval depth,
source ranking/filtering, prompt semantics, persistence schema, social provider
integration, or downstream handoff design.

## Design Revision

- Compact fulfillment now computes source-class gaps before rendering fulfilled,
  partial, and unfulfilled handoff items.
- Explicit missing source-class telemetry is always respected. Required
  legal/current, official/current, current primary/official, primary/archival,
  and central social classes are also checked when evidence is otherwise marked
  sufficient.
- Source-dependent obligations are moved out of `fulfilled_items` and into
  `partial_items` when the needed source class is missing, secondary-only, or
  unavailable.
- Missing source classes are added to `unfulfilled_items` unless an existing
  unfulfilled item already names the same source-class gap.
- Compact warnings now flag official/current legal gaps, current primary or
  official gaps, missing primary/archival sources, and unavailable social signal.
- Runtime handoff now treats `source_class_satisfaction_status` values of
  `expected_but_only_secondary` and `unsatisfied` as compact missing-class
  signals for fulfillment calibration.

## Targeted Coverage

Added AG-10 tests for:

- Legal/current official answers with secondary-only evidence becoming partial,
  with legal/current source classes unfulfilled.
- Legal/current official answers with official evidence remaining fulfillable.
- Recommendation with a legal/tax constraint preserving recommendation family
  while marking the legal source-class constraint partial/unfulfilled.
- Historical/archival answers with secondary-only evidence marking
  `primary_or_archival` partial/unfulfilled.
- Bread calorie-density from user-provided values remaining fulfilled and
  quantitative.
- Explicit social/sentiment questions with no social provider keeping
  `provider_unavailable` and `social_signal` unfulfilled.

## Promotion Decision

AG-10 supports AG-11 moving to an active official/current source-class recovery
pilot, but only as a bounded pilot with the existing protected-surface limits:
no prompt rewrites, no provider routing or selection changes, no persistence
schema changes, and no downstream handoff redesign. The pilot should continue
to prove behavior preservation while testing whether calibrated handoff gaps can
drive official/current recovery safely.

## Consumer / Decision / Deletion Criteria

Consumer: AG-10 phase review and AG-11 active official/current recovery pilot
planning.

Decision: whether compact fulfillment is consistent enough to let official/current
source-class gaps inform a bounded active recovery pilot.

Deletion criteria: this note may be superseded after AG-11 records either a
successful bounded active pilot or an explicit decision to keep recovery passive.
