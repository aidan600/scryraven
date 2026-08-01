# SearchPlanner Repair Tracker

## Verified merged baseline before this change

main:
eb0a46b25939ba977bc2569a484e6ab484569934

Completed merged repairs:

- PR #531 / 7484e3c38ba210d3303dae46fd4807c4d7c828ac
  visible output-contract parity
- PR #533 / c983d25083b0f226e557f2b608679b5f633797d3
  strict JSON parser boundary
- PR #534 / a83faeca3819e672fc9cacdab827bbb0fcbad6ec
  strict model-visible text types
- PR #535 / eb0a46b25939ba977bc2569a484e6ab484569934
  allowed_support_kinds item validation

## Repair introduced by this change set

- seven scalar normalized-nonempty contracts
- prompt schema v2 to v3
- merge SHA intentionally unavailable until the PR is merged

## Remaining after this change merges

- privacy-safe predicate-level failure attestation

## Live-confirmation prerequisites

- this contract-completion PR merged
- predicate-attestation PR merged
- explicit bounded live-validation license

## SearchPlanner boundary definition of done

This definition of done is a target state; it does not claim predicate attestation is
installed or that the SearchPlanner boundary is already fully repaired.

- strict JSON accepted
- no silent type or invalid-item conversion
- visible contract matches adapter behavior
- valid proposal can enter runtime
- invalid proposal reports an exact privacy-safe predicate ID
