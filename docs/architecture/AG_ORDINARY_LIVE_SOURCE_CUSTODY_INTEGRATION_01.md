# AG-ORDINARY-LIVE-SOURCE-CUSTODY-INTEGRATION-01

Status: active ordinary product-path repair phase.

Mode: REPAIR.

Repair verdict target: YES.

## Named Defect

PR #362 made ordinary `core.pipeline_orchestrator.run_pipeline(...)` own the
first live-chain handoff seam:

```text
ordinary run_pipeline
-> current contract
-> SearchExecutorHandoff
-> live_search_validation_state
-> SearchResultCandidatePacket
```

The ordinary product path still did not own the next proven seam:

```text
SearchResultCandidatePacket
-> selected source fetch/read
-> bounded sanitized content
-> FetchReadContentPacket / SanitizedContentReference
-> EvidenceLedger candidate/content custody
```

That seam had been proven in phase harnesses. This repair integrates it into
ordinary `run_pipeline` behind a default-disabled gate.

## Repair

`run_pipeline` now has a default-disabled source-custody continuation guarded by:

```text
enable_ordinary_live_source_custody
```

When `enable_ordinary_live_candidate_handoff` and
`enable_ordinary_live_source_custody` are both enabled, `run_pipeline` passes the
in-memory `SearchResultCandidatePacket` from the #362 handoff into
`core.ordinary_live_source_custody_runtime`. That helper selects the source from
the packet, consumes an injected offline/fake fetch-read dependency, applies the
existing bounded-content selector, builds and validates
`FetchReadContentPacket` / `SanitizedContentReference`, and reduces custody
through the existing RunKernel/EvidenceLedger reducer.

This is product-path integration rather than a sidecar harness because the
runtime consumer is ordinary `run_pipeline`; `scripts/ag_*` remain proof/repair
harnesses and are not imported by product code.

## Steering Boundary

`core.pipeline_orchestrator.py` remains a compatibility shell and callsite. It
does not implement source-custody policy, source selection, bounded-content
handling, packet construction, EvidenceLedger custody logic, semantic support,
citation behavior, Sufficiency, FAP, Author behavior, or answer text.

Source-custody logic lives in:

```text
core/ordinary_live_source_custody_runtime.py
```

Authority remains:

```text
RunKernel authorization
-> existing builders/validators
-> existing reducers
-> canonical RunKernel/EvidenceLedger state
```

Execution trace projections are review surfaces only. Packets remain handoff
records only and do not impersonate RunKernel state.

## Bounded Child RunKernel

This phase reuses the bounded child RunKernel introduced by #362.

- Parent run lineage: the child records `parent_run_id` and
  `parent_request_id` from ordinary `run_pipeline`.
- Owner: `ordinary_live_candidate_handoff_run_kernel`.
- Lifetime: in memory for one `run_pipeline` invocation.
- State owned by the child: front-half planner/current-contract state,
  `SearchExecutorHandoff`, `live_search_validation_state`,
  `SearchResultCandidatePacket`, `FetchReadContentPacket` /
  `SanitizedContentReference` custody lineage, and EvidenceLedger
  candidate/content custody for the selected source.
- State not owned by the child: ordinary answer semantic slots,
  SemanticObservation, ComponentCoverage, SufficiencyReadiness,
  FinalAnswerPacket, Author/AuthorProse, citation eligibility/rendering,
  source-obligation satisfaction, and answer text.
- Why the main RunKernel cannot own this state yet: the ordinary answer kernel
  does not yet own the semantic/coverage continuation that consumes this source
  custody without occupying answer semantic slots prematurely.
- Temporary debt: yes.
- Consolidation path: fold this custody state into the main ordinary RunKernel
  after `AG-ORDINARY-LIVE-SEMANTIC-COVERAGE-INTEGRATION-01` wires semantic
  support and ComponentCoverage into the ordinary path.

## Opened Surfaces

- `core.pipeline_orchestrator.run_pipeline` / `_run_pipeline_inner` as narrow
  callsite/config wiring only.
- `core.ordinary_live_source_custody_runtime`.
- Default-disabled `RunConfig` / `RunDeps` source-custody fields.
- Existing `FetchReadContentPacket` / `SanitizedContentReference`
  builder/validator.
- Existing EvidenceLedger candidate/content custody reducer.
- Offline/fake fetch-read dependency in tests.
- Safe execution trace projection:
  `ordinary_live_source_custody`.

## Closed Surfaces

- provider routing/provider selection changes;
- retrieval/ranking/filtering changes;
- prompt behavior;
- live provider/search/broker/fetch/model calls;
- retrieval diagnostics as source authority;
- semantic support;
- SemanticObservation admission;
- ComponentCoverage;
- citation eligibility/rendering;
- source-obligation satisfaction;
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
- retrieval calls by the source-custody seam: 0
- raw payload retention: false
- retries: 0

## Default-Disabled Behavior

With source custody disabled, ordinary behavior is unchanged. With candidate
handoff enabled and source custody disabled, #362 behavior is unchanged. With
both gates enabled, `run_pipeline` consumes the product-owned
`SearchResultCandidatePacket` and continues to source custody using injected
offline/fake fetch-read input.

## Explicit Non-Proofs

- no live provider/search/broker/fetch/model call;
- no SemanticObservation admission;
- no ComponentCoverage;
- no citation eligibility or citation rendering;
- no source-obligation satisfaction;
- no SufficiencyReadiness;
- no FinalAnswerPacket;
- no Author or AuthorProse behavior;
- no answer text;
- no answer correctness or product correctness.

## Mandatory Next Checkpoint

If this repair passes, the next checkpoint is:

```text
AG-ORDINARY-LIVE-SEMANTIC-COVERAGE-INTEGRATION-01
```

Likely mode: REPAIR or BUILD depending on whether ordinary source custody can
hand off directly to the existing semantic support and ComponentCoverage
machinery. Do not jump to Sufficiency/FAP/AuthorProse until ordinary product
path owns acquisition, source custody, semantic support, and ComponentCoverage.
