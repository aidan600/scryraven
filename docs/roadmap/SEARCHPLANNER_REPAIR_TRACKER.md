# SearchPlanner Repair Tracker

## Verified merged baseline before this change

main:
3e81048e455ca812e58bb985c0a4ef6540920b4b

## Completed merged repair

- PR #536 / 3e81048e455ca812e58bb985c0a4ef6540920b4b
  seven scalar normalized-nonempty contracts

## Repair introduced by this change set

- privacy-safe predicate-level attestation
- predicate registry v1
- product-boundary observer v2
- merge SHA intentionally unavailable until the PR is merged

## Remaining after this change merges

- bounded live SearchPlanner confirmation
- targeted prompt calibration only if an exact predicate still fails

## Live-confirmation prerequisites

- predicate-attestation PR merged
- explicit bounded live-validation license

## SearchPlanner boundary definition of done

This definition of done is a target state until a valid live proposal enters runtime;
this repair does not claim that bounded live confirmation has occurred.

- strict JSON accepted
- no silent type or invalid-item conversion
- visible contract matches adapter behavior
- valid proposal can enter runtime
- invalid proposal reports an exact privacy-safe predicate ID
