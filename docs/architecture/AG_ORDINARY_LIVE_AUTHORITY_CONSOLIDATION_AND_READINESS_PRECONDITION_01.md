# AG-ORDINARY-LIVE-AUTHORITY-CONSOLIDATION-AND-READINESS-PRECONDITION-01

Status: active ordinary product-path authority/readiness repair phase.

Mode: REPAIR.

Repair verdict target: YES or NO-BUT-JUSTIFIED, depending on whether a safe
main-answer readiness binding exists.

## Named Defect

PR #364 made ordinary `core.pipeline_orchestrator.run_pipeline(...)` consume the
candidate/source/semantic coverage chain through a bounded child `RunKernel`.
That child coverage is real ComponentCoverage for the bounded
candidate/source-custody component, but it is not yet main ordinary answer
readiness coverage.

The recorded blocker remains:

```text
coverage_not_bound_to_main_answer_readiness_component
```

Without a canonical child-to-main component binding or transfer reducer, the
ordinary answer path must not treat #364 coverage as SufficiencyReadiness,
FinalAnswerPacket input, Author input, citation readiness, source-obligation
satisfaction, answer text, or product correctness.

## Repair

`run_pipeline` now has a default-disabled authority consolidation precondition
guarded by:

```text
enable_ordinary_live_authority_consolidation
```

When candidate handoff, source custody, semantic coverage, and consolidation
are all enabled, `run_pipeline` calls:

```text
core.ordinary_live_authority_consolidation_runtime.execute_ordinary_live_authority_consolidation
```

The helper consumes the in-memory #364 `OrdinaryLiveSemanticCoverageResult` and
the in-memory child `RunKernel`. It rejects trace/projection mappings as
authority, rejects diagnostic retrieval/provider fields as authority, never
rehydrates RunKernel state from projections, and never mutates RunKernel state.

## Outcome

This phase fails honestly with a focused blocker rather than inventing
readiness.

Current consolidation status:

```text
authority_consolidation_status = blocked_missing_main_answer_component_binding
readiness_precondition_status = not_met
readiness_blocker_if_any = main_answer_component_binding_missing
component_equivalence_posture = unknown_requires_architecture_decision
```

The main ordinary RunKernel has no readiness-compatible accepted answer
component binding at the consolidation callsite. The helper therefore cannot
prove component equivalence by canonical contract ref, component id/digest, or
contract kind. It does not bind the child coverage to main readiness by label
similarity or assertion.

The precondition/binding record is not authoritative. No binding record is
created, no future consumer currently exists, and future SufficiencyReadiness,
FAP, or Author eligibility remains false.

## Child Kernel Role

The child kernel remains temporary architecture debt.

- owner: `ordinary_live_candidate_handoff_run_kernel`
- lifetime: in memory for one `run_pipeline` invocation
- owned state: candidate handoff, source custody, EvidenceLedger candidate
  custody, EvidenceRelativeAnalysisPacket, SemanticObservation admission, and
  ComponentCoverage reduction for the bounded child component
- not owned: main answer readiness, SufficiencyReadiness, FinalAnswerPacket,
  Author/AuthorProse, citation rendering, source-obligation satisfaction,
  answer text, and product correctness

## Product-Path Posture

This is product-path integration rather than harness work because the runtime
consumer is ordinary `run_pipeline`, not a `scripts/ag_*` sidecar. Product code
does not import or call `scripts/ag_*`, and prior `output/ag_*` artifacts are
not read as runtime state.

`core.pipeline_orchestrator.py` remains a narrow shell. It only wires the
default-disabled config flag, passes the in-memory semantic coverage result and
RunKernel objects into the helper, and stores the safe projection under:

```text
ordinary_live_authority_consolidation
```

Authority logic stays in `core/ordinary_live_authority_consolidation_runtime.py`.

## Opened Surfaces

- narrow `core.pipeline_orchestrator.run_pipeline` callsite/config wiring
- `core.run_config.RunConfig.enable_ordinary_live_authority_consolidation`
- `core.ordinary_live_authority_consolidation_runtime`
- focused offline tests
- safe execution trace projection: `ordinary_live_authority_consolidation`
- this compact architecture note

## Closed Surfaces

- provider routing/provider selection changes
- retrieval/ranking/filtering changes
- prompt behavior
- live provider/search/broker/fetch/model calls
- retrieval diagnostics as source/semantic/authority input
- reading `output/ag_*` artifacts as runtime state
- projection-to-RunKernel rehydration
- direct RunKernel state mutation
- child coverage promotion to main readiness by assertion
- source-obligation satisfaction
- citation eligibility/rendering
- SufficiencyReadiness reduction
- FinalAnswerPacket creation
- Author/AuthorProse
- answer text or product correctness claims
- secrets, `.env`, raw provider payloads, raw prompts, logs, caches, DB rows,
  full traces, raw HTML, raw headers, raw cookies, and raw page text

## Live Budget

- provider/search calls: 0
- broker calls: 0
- live fetch/read calls: 0
- model calls by this seam: 0
- retrieval calls by this seam: 0
- raw payload retention: false
- retries: 0

## Explicit Non-Proofs

- no final-answer readiness
- no safe child-to-main ComponentCoverage transfer reducer
- no main answer component equivalence
- no SufficiencyReadiness, FinalAnswerPacket, Author, or AuthorProse behavior
- no citation eligibility or citation rendering
- no source-obligation satisfaction
- no answer text
- no answer correctness or product correctness
- no live validation

## Mandatory Next Checkpoint

Because this phase cannot establish readiness compatibility safely, the next
checkpoint must be a focused architecture decision or repair:

```text
AG-ORDINARY-LIVE-MAIN-COMPONENT-BINDING-AUTHORITY-DECISION-01
```

Do not jump to SufficiencyReadiness, FinalAnswerPacket, Author, or AuthorProse
until a canonical main answer component binding or child-to-main coverage
transfer reducer exists and is consumed by the intended readiness path.
