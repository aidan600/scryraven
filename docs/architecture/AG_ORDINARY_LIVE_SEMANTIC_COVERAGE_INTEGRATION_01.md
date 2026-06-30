# AG-ORDINARY-LIVE-SEMANTIC-COVERAGE-INTEGRATION-01

Status: active ordinary product-path repair phase.

Mode: REPAIR.

Repair verdict target: YES.

## Named Defect

PR #362 made ordinary `core.pipeline_orchestrator.run_pipeline(...)` own the
candidate handoff seam, and PR #363 made ordinary `run_pipeline` own the source
custody seam through `FetchReadContentPacket` / `SanitizedContentReference` and
EvidenceLedger candidate/content custody.

The ordinary product path still did not own the next proven seam:

```text
EvidenceLedger custody + bounded sanitized source content
-> EvidenceRelativeAnalysisPacket
-> SemanticObservation admission
-> ComponentCoverage reduction
```

## Repair

`run_pipeline` now has a default-disabled semantic coverage continuation guarded
by:

```text
enable_ordinary_live_semantic_coverage
```

When candidate handoff, source custody, and semantic coverage are all enabled,
`run_pipeline` passes the in-memory `OrdinaryLiveSourceCustodyResult` into
`core.ordinary_live_semantic_coverage_runtime`. The helper builds and validates
one `EvidenceRelativeAnalysisPacket`, admits at most one SemanticObservation
through the existing bridge, and reduces at most one ComponentCoverage record
through existing RunKernel/reducer authority.

This is product-path integration rather than a sidecar harness because the
runtime consumer is ordinary `run_pipeline`. Product code does not import or
call `scripts/ag_*`.

## Authority Boundary

`core.pipeline_orchestrator.py` remains a narrow compatibility shell and
callsite. It does not implement semantic support rules, EvidenceRelative packet
construction, SemanticObservation admission internals, ComponentCoverage
construction, citations, Sufficiency, FAP, Author behavior, answer text, or
product correctness.

Authority remains:

```text
RunKernel authorization
-> existing builders/validators
-> existing reducers
-> canonical RunKernel state
```

Execution trace projections are review surfaces only. Packets remain handoff
records only and do not impersonate RunKernel state.

## Bounded Child RunKernel

This phase reuses the bounded child RunKernel introduced by #362 and extended by
#363.

- Parent run lineage: the child records `parent_run_id` and
  `parent_request_id` from ordinary `run_pipeline`.
- Owner: `ordinary_live_candidate_handoff_run_kernel`.
- Lifetime: in memory for one `run_pipeline` invocation.
- State owned by the child after this phase: candidate handoff, source custody,
  EvidenceLedger candidate/content custody, EvidenceRelativeAnalysisPacket
  lineage, SemanticObservation admission, and ComponentCoverage reduction.
- State not owned by the child: SufficiencyReadiness, FinalAnswerPacket,
  Author/AuthorProse, citation rendering, source-obligation satisfaction,
  answer text, and product correctness.
- Why the main RunKernel cannot own this state yet: coverage is still bound to
  the bounded child candidate/source-custody component rather than a main answer
  readiness component.
- Temporary debt: yes.
- Consolidation path:
  `AG-ORDINARY-LIVE-AUTHORITY-CONSOLIDATION-AND-READINESS-PRECONDITION-01`.

This repair must not bless the child RunKernel as a permanent mini-god.

## Component Identity

The coverage record produced by this phase is child-component support:

```text
coverage_is_final_answer_component_support = false
readiness_build_precondition_met = false
readiness_blocker_if_any = "coverage_not_bound_to_main_answer_readiness_component"
```

The mandatory next checkpoint is therefore authority/component alignment before
readiness, FAP, Author, or AuthorProse work.

## Opened Surfaces

- narrow `core.pipeline_orchestrator.run_pipeline` callsite/config wiring;
- `core.ordinary_live_semantic_coverage_runtime`;
- default-disabled `RunConfig.enable_ordinary_live_semantic_coverage`;
- existing EvidenceRelativeAnalysisPacket builder/validator;
- existing SemanticObservation admission bridge;
- existing ComponentCoverage record and RunKernel reducer machinery;
- focused offline tests;
- safe execution trace projection: `ordinary_live_semantic_coverage`.

## Closed Surfaces

- provider routing/provider selection changes;
- retrieval/ranking/filtering changes;
- prompt behavior;
- live provider/search/broker/fetch/model calls;
- retrieval diagnostics as semantic/source authority;
- source-obligation satisfaction;
- citation eligibility/rendering;
- SufficiencyReadiness;
- FinalAnswerPacket;
- Author/AuthorProse;
- answer text or product correctness claims;
- secrets, `.env`, raw provider payloads, raw prompts, logs, caches, DB rows,
  full traces, raw HTML, raw headers, raw cookies, and raw page text.

## Live Budget

- provider/search calls: 0
- broker calls: 0
- live fetch/read calls: 0
- model calls: 0
- retrieval calls by the semantic coverage seam: 0
- raw payload retention: false
- retries: 0

## Default-Disabled Behavior

With semantic coverage disabled, ordinary behavior is unchanged. With candidate
handoff and source custody enabled but semantic coverage disabled, #363 behavior
is unchanged. With all three gates enabled, `run_pipeline` consumes the in-memory
source-custody result and attempts semantic coverage.

## Explicit Non-Proofs

- no live provider/search/broker/fetch/model call;
- no final-answer readiness;
- no citation eligibility or citation rendering;
- no source-obligation satisfaction;
- no SufficiencyReadiness;
- no FinalAnswerPacket;
- no Author or AuthorProse behavior;
- no answer text;
- no answer correctness or product correctness.

## Mandatory Next Checkpoint

Because coverage is reduced only on the bounded child candidate/source-custody
component, the next checkpoint is:

```text
AG-ORDINARY-LIVE-AUTHORITY-CONSOLIDATION-AND-READINESS-PRECONDITION-01
```

Likely mode: REPAIR. Do not jump to Sufficiency/FAP/AuthorProse until coverage
is bound to a readiness-compatible ordinary answer component, and do not claim
source-obligation or citation posture without an explicitly licensed phase.
