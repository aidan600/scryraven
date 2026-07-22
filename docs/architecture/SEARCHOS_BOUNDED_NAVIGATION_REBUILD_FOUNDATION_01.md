# SearchOS bounded-navigation rebuild foundation 01

Status: Candidate replacement foundation.

Disposition: closed; inactive; foundation-only; not ordinary-product installed;
not Slice B complete.

Mode: BUILD

## Outcome

This phase adds one compact, bounded breadcrumb-navigation foundation beneath
the existing SearchOS iterative-judgment owner. It does not install navigation
in `searchos_slice_a_product_runtime.py`, does not execute a destination, and
does not claim Slice B completion.

The foundation has three durable navigation concepts:

1. `NavigationOption`, subordinate to canonical SearchOS state.
2. A compact admitted navigation edge, also subordinate to SearchOS state.
3. An opaque destination-binding reference whose exact URL is held only by one
   nonserializable, run-local `EphemeralNavigationLocatorStore`.

RunKernel owns one authorization and one URL-free observation transition:
`SEARCHOS_NAVIGATION_SELECT` to `SEARCHOS_NAVIGATION_SELECTED`. Authorization
checks only canonical envelope authority. The bounded executor alone resolves
the exact locator and returns facts without mutation or charge. The canonical
reducer never receives the locator store or an exact URL.

Admission increments the existing per-slot READ nomination count once,
increments the bounded navigation-selection count once, and appends one edge.
Authority-integrity rejection has zero count deltas and marks the slot stale.
Ordinary unavailability has zero count deltas and returns the slot to ordinary
judgment; a missing or mismatched binding retires that option revision.

## Constraints and closed surfaces

- The ordinary Slice A consumer remains navigation-free and unchanged.
- Exact destinations, query text, provider payloads, prompts, and raw traces are
  not canonical SearchOS state.
- Query-bearing destinations, host changes, unsafe ports, ancestor cycles,
  stale revisions, exhausted leashes, and missing parent custody fail closed.
- Navigation execution and new READ custody creation remain closed.
- No live provider, model, search, fetch/read, retrieval, browser, or
  secrets-backed call is part of this phase.
- No top-level `RunState` field is added.

## Proof and exception leash

Proof class: `COMPONENT_HARNESS_PROOF` plus structural/offline contract tests.
Actual app delta: none; the ordinary product consumer remains closed.

This inactive foundation is the phase-licensed exception to the ordinary
consumer rule. It proves ownership, bounded state, deterministic transition
deltas, replay-stable references, and locator separation. It does not prove
destination execution, acquisition, custody admission, answer improvement,
ordinary app reachability, or production correctness.

The mandatory next BUILD checkpoint must connect the admitted selection to an
explicitly authorized destination-execution and existing READ-custody path,
then install the behavior in the named ordinary consumer. Until then, this
foundation must remain opt-in and inactive.

## Rejected PR 514 comparison

Reference-only review of PR 514 contributed narrowly isolated normalization,
supported Markdown-link extraction, label sanitization, and adversarial test
cases. This rebuild does not port its retained navigation state, second
top-level authority shape, overlay/registry machinery, acquisition path,
custody path, execution path, or product-installation claims. PR 514 remains
unchanged.

## Verification classification

`tests/test_searchos_bounded_navigation_foundation_01.py` is phase-focus
component-harness coverage. Direct SearchOS judgment, READ custody, RunKernel,
Slice A policy/state/replay, `fast_pr`, and `semantic_search_lane` are affected
offline regression surfaces. This phase adds no test to a permanent bucket
manifest.
