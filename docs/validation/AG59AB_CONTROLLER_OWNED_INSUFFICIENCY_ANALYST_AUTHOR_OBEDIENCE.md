# AG-59AB Controller-Owned Insufficiency and Analyst/Author Obedience

## Phase Purpose

AG-59AB makes Controller/AnswerContract source-insufficiency ownership visible
in the public handoff and narrows Analyst/Author prompt obedience to that
controller-authorized posture.

## Licensed Coupled Surface

Opened:

- `AnswerContractFulfillment` / `ControllerHandoff` source-obligation fields;
- source-class fulfillment warnings for official/current/canonical gaps;
- Analyst and Author prompt obedience text;
- offline tests for insufficiency posture, citation-laundering, leakage, and
  negative controls.

Closed:

- provider routing, provider selection, provider depth, and provider
  integration;
- retrieval strategy, source ranking, and filtering redesign;
- Economist behavior, code-execution rules, quantitative packet boundaries, and
  Analyst-skip behavior;
- Scrutineer and follow-up behavior;
- weak-corpus recovery policy;
- broad citation-system or final-answer rewrites;
- `core/pipeline_orchestrator.py`;
- live validation and private/generated artifacts.

## Ownership Rule

The Controller and AnswerContract own required source classes, evidence
sufficiency, fulfillment/partial/unfulfilled source obligations, stop reason,
and final answer posture. Analyst may synthesize only inside that posture.
Author may format and cite only inside that posture.

Citation requirements do not authorize citing weak, off-topic, secondary,
community, or social evidence as if it satisfies official/current/canonical,
primary, or legal claims.

## Handoff And Prompt Changes

`AnswerContractFulfillment` now exposes:

- `source_obligation_status`;
- `unfulfilled_source_classes`;
- `partial_source_classes`.

Canonical documentation gaps (`primary_source_documents`) and current
specs/availability gaps are included in the source-class fulfillment surface,
with Analyst/Author warnings when secondary-only evidence leaves the required
class unfulfilled or partial.

The Analyst prompt now says ControllerHandoff / answer-contract partial,
insufficient, or unfulfilled source-obligation posture limits synthesis. The
Author prompt now preserves the same posture and blocks citation-laundering.

## Tests Added

Added:

- `tests/test_ag59ab_controller_owned_insufficiency_analyst_author_obedience.py`

Coverage:

- official/current secondary-only evidence produces partial controller posture;
- canonical documentation secondary-only evidence is not laundered as
  fulfilled;
- Analyst obedience text prevents confident synthesis outside controller
  posture;
- Author obedience text preserves insufficiency and citation-fit caveats;
- weak/no-good evidence keeps insufficient posture without invented facts;
- ordinary conceptual explainers remain sufficient with reputable secondary
  evidence;
- explicit academic requests remain academic;
- canonical docs remain canonical-source-oriented;
- AG-57A mixed canonical plus academic strict xfail remains preserved;
- public handoff leakage guards remain in force;
- protected prompt/orchestrator surfaces stay narrow.

## Mixed Canonical Plus Academic Status

The mixed obligation shape remains unresolved by design:

```text
What do the docs say, and what do studies show?
```

AG-59AB does not add multi-source obligation modeling and preserves the AG-57A
strict xfail.

## Validation Decision

No live validation was used.

Offline tests are sufficient because this phase changes deterministic handoff
projection and repo-tracked Analyst/Author prompt-obedience text only. Live
ProPlex/provider/model/search runs remain closed.

## Next Recommended Surface

If further failures appear, keep the next phase in Controller/AnswerContract
handoff consumption or explicit product modeling for mixed independent source
obligations. Do not open provider routing/depth, retrieval ranking/filtering,
Economist, Scrutineer, follow-up, weak-corpus policy, broad citation behavior,
or broad final-answer behavior from AG-59AB alone.
