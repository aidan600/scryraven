# AG-ORDINARY-LIVE-MAIN-RUNKERNEL-COVERAGE-INTEGRATION-01

Mode: REPAIR

## Product-Facing Progress

This phase moves ordinary `core.pipeline_orchestrator.run_pipeline` closer to a
usable-answer verdict of YES by placing accepted answer component refs,
SemanticObservation admission history, and ComponentCoverage history/projection
on the main RunKernel under the default-disabled
`enable_ordinary_live_main_runkernel_coverage` flag.

Product-facing progress type: product-path repair.  The reviewable output delta
is the `ordinary_live_main_runkernel_coverage` execution trace plus main
RunKernel state whose ComponentCoverage `answer_component_id`, revision, and
digest exactly match a main accepted answer component.

Actual consumer seam: `core.pipeline_orchestrator.run_pipeline` consumes
`core.ordinary_live_main_runkernel_coverage_runtime`.

Callsite posture: in this phase the helper runs after normal post-author output
packaging has produced the execution trace.  Its ComponentCoverage is main
RunKernel state and readiness-compatible input for the next checkpoint, but it
does not feed SufficiencyReadiness, FinalAnswerPacket, Author, citation, or
answer-text behavior in this phase.

Existing machinery reused:

- ordinary live candidate handoff
- ordinary live source custody
- EvidenceRelativeAnalysisPacket construction
- SemanticObservation admission bridge
- RunKernel-owned ComponentCoverage reduction

New machinery introduced: only a default-disabled runtime helper, config flag,
trace projection, docs, and product-path regression tests.

Old path treatment: #362/#363/#364/#365 child-path behavior remains unchanged
when the new flag is disabled.  The #365 blocker is resolved only for the new
flagged main path and is reported as `legacy_365_blocker_resolved`.

Why this is not reinventing an existing surface: the helper composes existing
reducers and helpers.  It does not create a new coverage schema, alternate
RunKernel state store, projection rehydration path, or shadow product path.

## Target Surface

Target surface: ordinary live source coverage in `run_pipeline`, specifically
the placement of accepted answer component refs, SemanticObservation admission,
and ComponentCoverage on the main RunKernel.

High-custody surface: RunKernel canonical semantic state and coverage reduction.
The phase changes this only through existing authorization and `RunKernel.reduce`
calls.

Closed-this-phase surface: SufficiencyReadiness, FinalAnswerPacket, Author,
AuthorProse, citation rendering, source-obligation satisfaction, answer text,
product correctness, live provider/search/broker/fetch/model calls, raw provider
payloads, raw prompts, and raw/bounded source text in trace output.

## Validation Posture

provider/search calls: 0
broker calls: 0
fetch/model/retrieval calls: 0
live validation: not run

Closed Surfaces:

- no SufficiencyReadiness reduction
- no FinalAnswerPacket creation
- no Author or AuthorProse invocation
- no citation eligibility or rendering
- no source-obligation satisfaction
- no answer text or product correctness claim
- no direct RunKernel state mutation outside existing reducers
- no projection-to-RunKernel rehydration
- no `scripts/ag_*` import or call from product code

Explicit Non-Proofs:

- this does not prove answer correctness
- this does not prove citation rendering
- this does not prove source-obligation satisfaction
- this does not prove AuthorProse behavior
- this does not make old child-owned coverage readiness-compatible
- this does not run live providers or live fetch/read

Next product-path checkpoint: AG-ORDINARY-LIVE-ENTRYPOINT-VISIBILITY-01.
