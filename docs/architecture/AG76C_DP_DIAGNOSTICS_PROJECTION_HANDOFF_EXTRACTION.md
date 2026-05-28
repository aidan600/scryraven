# AG-76C-DP Diagnostics / Projection Handoff Extraction

Date: 2026-05-28

## Scope And Non-Goals

AG-76C-DP is an Architecture Groove / Prove Mode extraction phase for the
recovered/source-class diagnostics and projection consumer handoff still living
in `core/pipeline_orchestrator.py`.

The licensed scope is parity-preserving extraction only:

- move recovered/source-class diagnostics/projection input assembly out of the
  orchestrator;
- preserve trace, export, and projection field names;
- keep projection/export helpers observer-only;
- keep runtime answer behavior, final evidence behavior, Author behavior, and
  citation behavior unchanged.

This phase does not change Controller decision behavior, provider routing,
provider selection/depth/escalation, new providers, Linkup policy, query
strategy, retrieval ranking/filtering, source-class/currentness classification,
candidate-fit semantics, final evidence selection semantics, final-answer prose,
Author prompts, citation formatting, citation selection, Scrutineer, Economist,
follow-up behavior, live validation, IRS-specific hardcoding, raw/private data
handling, or broad `pipeline_orchestrator.py` domain logic.

## AG-76C-CS Prerequisite Verification

Current local `main` contained AG-76C-CS / PR #27 before implementation:

```text
22facfe Merge pull request #27 from aidan600/codex/ag76c-cs-runner-owned-recovered-candidate-stream
aff12c1 Extract runner-owned recovered candidate stream
```

Required AG-76C-CS artifacts were present:

- `docs/architecture/AG76C_CS_RUNNER_OWNED_RECOVERED_CANDIDATE_STREAM.md`
- `core/source_class_recovery_candidate_stream.py`
- `tests/test_ag76c_cs_runner_owned_candidate_stream.py`

`core.recovered_evidence_visibility.recovered_evidence_selection_candidates(...)`
delegates to
`core.source_class_recovery_candidate_stream.runner_owned_recovered_candidate_stream(...)`.

`core/pipeline_orchestrator.py` no longer performs inline
`retrieval_stage == "source_class_recovery"` scans for diagnostics/projection
handoff. It consumed `source_class_recovery_passage_candidates(...)` before this
phase.

Current local `main` also contained AG-76C-FE / PR #26 before implementation:

```text
341d524 Merge pull request #26 from aidan600/codex/ag76c-fe-final-evidence-bundle-extraction
5fa7814 Update AG-69 guards for final evidence builder
ec56a49 Extract final evidence bundle builder
```

Required AG-76C-FE artifacts were present:

- `core/final_evidence_bundle_builder.py`
- `docs/architecture/AG76C_FE_FINAL_EVIDENCE_BUNDLE_EXTRACTION.md`
- `tests/test_ag76c_final_evidence_bundle_builder.py`

## Old Handoff Block Moved

Before AG-76C-DP, `pipeline_orchestrator.py` locally:

- called `source_class_recovery_passage_candidates(all_passages=all_passages)`;
- conditionally called `build_recovery_source_quality_diagnostics(...)`;
- updated `active_source_class_recovery_lifecycle` with the diagnostics payload;
- later rebuilt the same recovered/source-class passage list for
  `attach_passive_runtime_projection_traces(...)`.

AG-76C-DP moved that recovered/source-class diagnostics/projection input
assembly behind `core.source_class_recovery_projection_handoff`.

## New Helper Contract

New module:

```text
core.source_class_recovery_projection_handoff
```

New contracts:

- `SourceClassRecoveryProjectionHandoff`
- `build_source_class_recovery_projection_handoff(...)`

The helper mechanically gathers recovered/source-class passage candidates and
the existing recovery-source quality diagnostics payload. It does not retrieve,
route, rank, classify, evaluate fit, decide source sufficiency, choose final
evidence, decide retry/stop/provider allocation, modify AnswerContract posture,
write final answer text, alter Author behavior, or format/select citations.

## Input Contract

`build_source_class_recovery_projection_handoff(...)` accepts:

- `all_passages`;
- `final_top_evidence`;
- `final_source_class_counts`.

These are already-computed runtime facts. The helper does not read provider
payloads, prompts, DB rows, logs, caches, secrets, output packets, or live
sources.

## Output Contract

The helper returns `SourceClassRecoveryProjectionHandoff` with:

- `recovered_source_class_passages`: the same ordered list produced by
  `source_class_recovery_passage_candidates(...)`;
- `recovery_source_quality_diagnostics`: the exact payload previously produced
  by `build_recovery_source_quality_diagnostics(...)`, or `{}` when the old
  orchestrator branch would not have updated lifecycle diagnostics.

## Trace And Export Field Parity Rules

AG-76C-DP preserves existing field names and packet names. The helper does not
rename or deprecate:

- recovered/source-class diagnostics fields;
- authority candidate passport projection fields;
- ControllerEvidenceLedger projection fields;
- official/canonical recovery visibility export fields;
- final evidence and final-answer source telemetry fields.

Trace/projection/export helpers continue to consume the same values they
received before the extraction.

## Observer-Only Boundary

Trace/projection/export layers observe. The new helper only prepares facts for
diagnostics and passive projection consumers. It does not become a hidden
decision owner.

Decision ownership remains unchanged:

- `ControllerRecoveryDecision` owns retry/stop/provider-review posture;
- `ControllerEvidenceLedger` owns custody/disposition interpretation;
- `AnswerContract` owns obligation/posture state;
- AuthorityLifecycle and recovered-evidence visibility own current fit/selection
  semantics;
- `core.final_evidence_bundle_builder` owns mechanical final evidence packaging.

## Protected Surfaces Kept Closed

AG-76C-DP kept closed:

- provider routing, provider selection, provider depth, provider escalation,
  provider swaps, new providers, and Linkup policy;
- query strategy and source-constraint repair;
- retrieval ranking/filtering behavior;
- source-class/currentness classifier behavior;
- candidate-fit semantics;
- final evidence selection semantics;
- final answer behavior;
- Author behavior and Author prompt semantics;
- citation formatting and citation selection;
- prompt behavior;
- follow-up behavior;
- Scrutineer and Economist behavior;
- live validation;
- direct IRS hardcoding;
- raw/private data, DB rows, caches, logs, secrets, full traces, and output
  packets.

## Remaining Orchestrator Responsibilities

`pipeline_orchestrator.py` remains responsible for:

- computing existing runtime facts;
- invoking Controller-approved source-class recovery execution;
- passing already-computed facts to observer/projection helpers;
- updating lifecycle state with the returned diagnostics payload;
- invoking passive runtime projection attachment;
- preserving final answer, Author, citation, provider, search, query,
  classifier, fit, and final evidence behavior.

It no longer owns the recovered/source-class diagnostics/projection handoff
assembly block.

## Remaining Projection And Export Responsibilities

Projection/export helpers remain responsible for:

- attaching passive runtime projections to `execution_trace`;
- mirroring projection packets into the evidence integration checkpoint where
  existing helpers already do so;
- exporting sanitized official/canonical recovery visibility facts;
- observing ledger/passport/provider-result visibility without changing runtime
  decisions.

They do not decide source sufficiency, final evidence, Author behavior, citation
behavior, provider allocation, or query strategy.

## Line-Count Delta

`core/pipeline_orchestrator.py` line count:

- before AG-76C-DP: 6972
- after AG-76C-DP: 6969
- delta: -3

## Behavior Parity Evidence

New AG-76C-DP tests prove:

- helper output matches the old diagnostics payload and projection inputs;
- empty recovered/source-class streams preserve the old no-update shape;
- passive runtime projection output is unchanged for
  `authority_candidate_passport_projection`, `controller_evidence_ledger`, and
  `official_canonical_recovery_visibility_export`;
- `pipeline_orchestrator.py` no longer owns the moved handoff block;
- the new helper does not import or call protected provider/search/query,
  Author, final-answer, citation, Scrutineer, Economist, raw-payload, or secret
  surfaces.

Focused command:

```text
py -m pytest tests/test_ag76c_dp_diagnostics_projection_handoff.py -q --basetemp C:\tmp\ag76c-dp-pytest -o cache_dir=C:\tmp\ag76c_dp_pytest_cache
4 passed
```

Additional focused checks:

```text
py -m ruff check core/pipeline_orchestrator.py core/source_class_recovery_projection_handoff.py tests/test_ag76c_dp_diagnostics_projection_handoff.py
All checks passed!

py -m pytest tests/test_ag76c_dp_diagnostics_projection_handoff.py tests/test_ag76c_cs_runner_owned_candidate_stream.py tests/test_ag76c_final_evidence_bundle_builder.py -q --basetemp C:\tmp\ag76c-dp-core-pytest -o cache_dir=C:\tmp\ag76c_dp_core_cache
19 passed

py -m pytest tests/test_runtime_trace_projection_assembly_ag46c.py tests/test_official_canonical_recovery_visibility_export_ag50c.py -q --basetemp C:\tmp\ag76c-dp-projection-pytest -o cache_dir=C:\tmp\ag76c_dp_projection_cache
25 passed

py -m pytest tests/test_controller_diagnostics_trace_contract.py -q --basetemp C:\tmp\ag76c-dp-controller-pytest-2 -o cache_dir=C:\tmp\ag76c_dp_controller_cache_2
7 passed

py -m pytest tests/test_ag75c_local_authority_gate_retirement.py -q --basetemp C:\tmp\ag76c-dp-ag75c-pytest -o cache_dir=C:\tmp\ag76c_dp_ag75c_cache
4 passed
```

`git diff --check` passed. Protected-surface grep matches were expected
historical/doc/test closed-surface assertions or unchanged orchestrator legacy
surface references; the new helper itself had no protected-surface matches.

No live validation was run. No live provider/model/search calls were run. No
local output packet was created.

## Demolition Ledger

| item | result |
| --- | --- |
| Old diagnostics/projection handoff block targeted | Local recovered/source-class passage diagnostics/projection prep in `pipeline_orchestrator.py` around `source_class_recovery_passage_candidates(...)`, `build_recovery_source_quality_diagnostics(...)`, and `attach_passive_runtime_projection_traces(...)`. |
| New helper/module contract | `core.source_class_recovery_projection_handoff.build_source_class_recovery_projection_handoff(...)` returns candidate passages and exact diagnostics payload. |
| Old orchestrator handoff code | Subordinated to the new helper; duplicate projection stream construction deleted. |
| Trace/export field parity tests | `test_ag76c_dp_runtime_projection_matches_legacy_recovered_passages`. |
| Final evidence/final answer/citation parity evidence | Existing AG-76C-FE tests remain the final evidence parity guard; no final answer, Author, or citation code was touched. |
| Remaining orchestrator responsibilities | Runtime fact computation, lifecycle update with helper output, projection attachment call, persistence/outcome packaging. |
| Remaining projection/export responsibilities | Passive projection/export attachment and sanitized observer packets only. |
| Next deletion target | AG-76C-BD burn-down review should inspect remaining projection/export observer duplication and remaining `pipeline_orchestrator.py` compatibility plumbing around runtime trace assembly. |
| Net complexity impact | Small reduction in orchestrator handoff logic; new helper creates a named observer-only boundary for the next burn-down review. |
| `pipeline_orchestrator.py` line-count delta | -3 lines. |
| Should AG-76C-BD open next? | Yes. |

## AG-76C-BD Recommendation

AG-76C-BD burn-down review should open next. The next review should focus on the
remaining runtime trace assembly and projection/export observer plumbing still
coordinated by `pipeline_orchestrator.py`, without opening Controller decision,
provider/search/query/classifier/fit/final-answer/Author/citation surfaces.
