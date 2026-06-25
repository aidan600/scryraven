# AG-SEM-TXN-CLEAN-01 Test Helper Audit

Status: implementation and focused-fix audit for semantic producer atomicity.
This work used offline repository inspection and deterministic tests only. It
did not run live provider, model, search, retrieval, fetch, DB, cache,
private-log, full-trace, or generated private-artifact validation.

## Scope

AG-SEM-TXN-CLEAN-01 moves the ordinary semantic producer handoff from a
multi-reducer mutation sequence into a single RunKernel-owned atomic commit
boundary. RunKernel owns authorization, lifecycle status, final RunState
mutation, and success/failure observations. The pure staging and validation
bulk lives in `core/semantic_producer_bundle_commit_runtime.py`.

The runtime consumer remains the ordinary product path: accepted contract,
semantic observations, and component coverage are consumed by semantic
sufficiency, which gates search judgment, QueryPlan behavior, final answer
packet readiness, and Author execution.

## Test Lane Inventory

| File | Lane recommendation | Owner/surface protected | Durable invariant | Action | Reason |
| --- | --- | --- | --- | --- | --- |
| `tests/test_ag_sem_11_ordinary_semantic_producer_vertical_slice.py` | `phase_focus`, then `semantic_lane` candidate | Ordinary semantic producer, RunKernel atomic commit, semantic sufficiency handoff | Producer calls one atomic bundle commit; staging failures leave no accepted contract, observations, coverage, FAP, or Author state; RunKernel owns commit/apply while helper owns staging | Keep phase focus; later merge selected atomic guards into semantic lane | Detailed seam proof is too specific for `fast_pr`, but it is the best semantic producer regression suite. |
| `tests/test_ag_sem_09_sufficiency_semantic_consumption.py` | `semantic_lane` | Semantic sufficiency consumer | Coverage must match accepted contract version/digest and component digest; stale/orphan coverage is treated as missing coverage | Promote stale/orphan coverage test to semantic lane | This is a durable consumer invariant independent of the transaction implementation. |
| `tests/test_ag_sem_multi_01_ordinary_multipart_semantic_expansion.py` | `semantic_lane` | Multipart ordinary semantic producer and semantic sufficiency | Required components receive bounded observations/coverage; missing multipart coverage creates semantic gaps | Keep, then merge duplicate static guards with AG-SEM-11 guard | Product coverage is useful; repeated closed-surface guards should be consolidated. |
| `tests/test_ag_sem_11c_ordinary_semantic_producer_second_fixture.py` | `semantic_lane`; optional `author_lane` subset | Second ordinary semantic producer fixture, final packet/Author adjacency | Semantic producer remains fixture-agnostic and closed-surface safe while later finalization can proceed only after sufficiency | Keep product fixture; defer Author-specific assertions to `author_lane` if split | Useful breadth fixture; some static closed-surface checks overlap other AG-SEM files. |
| `tests/test_ag_sem_prod_02_broader_ordinary_semantic_production.py` | `semantic_lane`; `full_offline` candidate | Broader ordinary semantic production product path | Semantic production works beyond toy fixtures without changing provider/search/retrieval or Author prose | Keep in semantic lane; consider full offline only if runtime cost grows acceptable | Guards broad product shape, but not cheap enough for `fast_pr`. |
| `tests/test_ag_gap_01_offline_product_path.py` | `semantic_search_lane` | Offline product path gap handling | Semantic gaps block finalization and do not activate retrieval execution query-list changes | Keep; do not merge into producer tests | This proves downstream gap behavior rather than producer construction. |
| `tests/test_runauthority_iterative_search_judgment_ag92b.py` | `semantic_search_lane` | RunAuthority SearchJudgment consumer | Semantic missing assessments remain gaps and do not become direct-answer readiness | Keep as search-judgment consumer proof | Protects the consumer of semantic facts, not the producer. |
| `tests/test_search_work_query_plan_consumption_ag96e2.py` | `semantic_search_lane` | QueryPlan/SearchWorkPlan consumption | Semantic gaps stay query-planning facts without causing retrieval execution behavior changes | Keep as QueryPlan consumer proof | Adjacent to AG-GAP-01 but protects a different consumer. |
| `tests/test_ag_sem_05_initial_answer_contract_acceptance.py` | `semantic_lane` | Single-stage accepted contract reducer | Passive QMR acceptance remains valid outside bundle commit | Keep; do not merge into bundle tests | The atomic helper reuses this reducer, so its unit tests remain canonical. |
| `tests/test_ag_sem_06_semantic_observation_admission.py` | `semantic_lane` | Single-stage SemanticObservation admission reducer | Observation/content digest, accepted-contract binding, and custody checks stay canonical | Keep; do not merge into bundle tests | The bundle helper stages through this reducer and should not duplicate its full unit proof. |
| `tests/test_ag_sem_07_component_coverage_reduction.py` | `semantic_lane` | Single-stage ComponentCoverage reduction reducer | Coverage digest, observation refs, evidence custody, and component bindings stay canonical | Keep; do not merge into bundle tests | Bundle atomicity depends on this reducer while preserving its standalone authority. |
| `tests/buckets/fast_pr.txt` | `fast_pr` | Cheap PR sentinels | Tiny default PR confidence remains broad and quick | Leave unchanged | AG-SEM transaction tests are detailed phase/lane proofs, not broad sentinels. |

## Helper And Module Inventory

| Helper/module | Owner/surface | Overlapping helpers found | Consolidation performed in this PR | Consolidation deferred | Suggested AG-TEST-CONSOLIDATE-01 action |
| --- | --- | --- | --- | --- | --- |
| `core/semantic_producer_bundle_commit_runtime.py` | Pure staging/validation for semantic producer bundle commit | `core/ordinary_semantic_producer_runtime.py` preflight dry-run helpers; AG-SEM-05/06/07 reducer builders | Extracted payload normalization, component count checks, accepted-contract staging, observation staging, coverage staging, duplicate ID/digest checks, and staged commit dict construction out of RunKernel | Could later share a small builder for component payload serialization with producer/test helpers | Keep as runtime helper; add direct unit tests only if future staging behavior grows beyond current product-path tests. |
| `core/run_kernel.py` | Authority owner and final RunState mutation owner | Existing single-stage semantic reducer reduce branches | Retained only action/observation enum values, authorization, lifecycle checks, final apply, success/failure observation recording, and status updates for bundle commit | RunKernel still contains many other stage-specific reducers unrelated to this phase | Do not expand here; future phases should extract similar pure staging helpers before adding large reducer bodies. |
| `core/ordinary_semantic_producer_runtime.py` | Ordinary producer payload construction and product-path handoff | `_dry_run_accepted_contract`, `_dry_run_admission_projection`, `_dry_run_coverage_state`; test payload helpers | Replaced individual `run_kernel.reduce(...)` calls with one `commit_semantic_producer_bundle(...)` call | Preflight helpers still duplicate some staging shape intentionally to fail before mutation | Keep preflight until a later phase can share non-mutating proposal validation without widening runtime behavior. |
| `core/sufficiency_semantic_state_consumption_runtime.py` | Semantic sufficiency consumer | Coverage history projection and semantic ref projection logic | Added contract/component identity match before treating coverage as present | Could factor coverage identity predicates into a tiny shared helper if more consumers appear | Keep local for now; promote stale/orphan consumer tests to semantic lane. |
| `tests/helpers/offline_ordinary_pipeline.py` | Shared offline product-path harness and live-call scrubber | Repeated fixture harnesses in AG-SEM-11, AG-SEM-11C, AG-SEM-PROD-02 | No code consolidation performed; inspected as shared harness | Fixture-specific classes still repeat search passage setup and static guards | Consolidate fixture setup only in AG-TEST-CONSOLIDATE-01; avoid changing runtime tests during semantic atomicity work. |
| `tests/test_ag_sem_11_ordinary_semantic_producer_vertical_slice.py` helper functions | Phase-specific semantic producer harness and failure injection | Similar helpers in AG-SEM-MULTI-01 and second/broader fixture tests | Added direct atomic failure helper and structural RunKernel/helper split guard | Static closed-surface/callsite assertions overlap several AG-SEM product tests | Merge static guards into one semantic structural test file; keep failure-injection helpers near AG-SEM-11. |

## Consolidation Decisions

Performed in this PR:

- Moved semantic bundle staging/validation bulk from RunKernel to
  `core/semantic_producer_bundle_commit_runtime.py`.
- Kept RunKernel as the semantic bundle authority owner and final state mutation
  owner.
- Updated static guards to prove the helper/RunKernel split and the producer's
  single atomic handoff shape.
- Expanded stale/orphan coverage consumer proof so coverage identity mismatches
  count as missing coverage.

Deferred:

- Merging repeated product-fixture static guards across AG-SEM-11,
  AG-SEM-11C, AG-SEM-MULTI-01, and AG-SEM-PROD-02.
- Sharing producer preflight dry-run builders with the new staging helper.
- Promoting any phase-detail test into `fast_pr`.
- Running live/provider/model/search/fetch validation.

## Recommended Next Actions

For AG-TEST-CONSOLIDATE-01:

1. Create a `semantic_lane` bucket containing AG-SEM-05/06/07 unit reducers,
   AG-SEM-09 consumer tests, and the AG-SEM-11 ordinary/multipart/broader
   product-path tests.
2. Create a `semantic_search_lane` bucket for AG-GAP-01, SearchJudgment, and
   QueryPlan semantic gap consumers.
3. Extract repeated AG-SEM closed-surface/static-callsite guards into one
   structural test file.
4. Leave `fast_pr` unchanged unless one cheap broad semantic sentinel is
   intentionally selected later.

## AG-TEST-CONSOLIDATE-01 Update

Status: implemented as validation-infrastructure work only. No product runtime
behavior change, live validation, provider/model/search/fetch/retrieval calls,
secrets, raw prompts, provider payloads, DB/cache rows, private logs, full
traces, or generated private artifacts were required.

### Lanes Created

- `tests/buckets/semantic_lane.txt` now owns durable semantic producer,
  reducer, sufficiency, component coverage, semantic projection, and structural
  guard validation.
- `tests/buckets/semantic_search_lane.txt` now owns durable SearchJudgment and
  QueryPlan consumers of semantic missing assessments and semantic component
  gaps.
- `fast_pr` stayed unchanged. These lanes are not default PR tax because they
  are domain sweeps rather than tiny broad sentinels.

### Test Routing Decisions

| File or node | Lane | Owner/surface | Reason |
| --- | --- | --- | --- |
| `tests/test_ag_sem_05_initial_answer_contract_acceptance.py` | `semantic_lane` | RunKernel initial answer contract reducer | Canonical accepted-contract construction remains a durable semantic reducer contract. |
| `tests/test_ag_sem_06_semantic_observation_admission.py` | `semantic_lane` | RunKernel SemanticObservation reducer | Observation admission, content reference custody, digest, and contract binding are durable semantic reducer contracts. |
| `tests/test_ag_sem_07_component_coverage_reduction.py` | `semantic_lane` | RunKernel ComponentCoverageRecord reducer | Coverage digest, component binding, evidence custody, and source-obligation state are durable semantic reducer contracts. |
| `tests/test_ag_sem_09_sufficiency_semantic_consumption.py` | `semantic_lane` | RunAuthority sufficiency semantic consumer | Semantic facts, version-bound coverage identity, blocker repair, ledger-qualified coverage, and projection integrity are durable semantic consumption contracts. |
| `tests/test_ag_sem_11_ordinary_semantic_producer_vertical_slice.py` | `semantic_lane` | Ordinary semantic producer and RunKernel atomic commit | Producer activation, preflight skips, atomic bundle commit, and failure/no-orphan-state behavior are durable semantic producer contracts. |
| `tests/test_semantic_lane_structural_guards.py` | `semantic_lane` | Semantic validation structure | Consolidated static guards cover authority boundaries, import/callsite limits, fixture-label leakage, and closed runtime surfaces. |
| `tests/test_ag_sem_11c_ordinary_semantic_producer_second_fixture.py::test_second_fixture_missing_evidence_skips_without_orphan_semantic_state` | `semantic_lane` | Second ordinary producer fixture | Missing evidence must skip without orphan semantic state; the positive Author/FAP-heavy fixture stays phase-focused. |
| `tests/test_ag_sem_multi_01_ordinary_multipart_semantic_expansion.py::test_component_cap_exceeded_skips_semantic_production_closed` | `semantic_lane` | Multipart ordinary semantic producer | Component caps must fail closed without semantic state; Author/FAP-heavy multipart assertions stay phase-focused. |
| `tests/test_ag_gap_01_offline_product_path.py` | `semantic_search_lane` | Offline product semantic gap path | Semantic gaps become version-bound query authority without changing retrieval execution. |
| `tests/test_runauthority_iterative_search_judgment_ag92b.py` | `semantic_search_lane` | RunAuthority SearchJudgment | Semantic missing assessments and component-gap identity remain search-judgment facts. |
| `tests/test_search_work_query_plan_consumption_ag96e2.py` | `semantic_search_lane` | QueryPlan/SearchWorkPlan consumer | SearchJudgment component-gap authority tags existing queries without introducing provider/search/fetch execution behavior. |

### Phase Focus And Author-Lane Candidates

The following tests stayed out of `semantic_lane` because their durable value is
Author/FAP/materialization/finalization adjacency rather than semantic-only
producer or reducer proof:

- `tests/test_ag_sem_11c_ordinary_semantic_producer_second_fixture.py::test_second_offline_fixture_reaches_semantic_sufficiency_and_fap_manifest`
- `tests/test_ag_sem_multi_01_ordinary_multipart_semantic_expansion.py::test_positive_bounded_n_multipart_semantic_path_reaches_fap_and_author`
- `tests/test_ag_sem_multi_01_ordinary_multipart_semantic_expansion.py::test_partial_missing_bounded_n_semantic_path_fails_closed_without_overclaim`
- `tests/test_ag_sem_prod_02_broader_ordinary_semantic_production.py::test_direct_canonical_spec_fact_reaches_semantic_fap_and_author_materialization`
- `tests/test_ag_sem_prod_02_broader_ordinary_semantic_production.py::test_insufficient_single_component_evidence_does_not_overclaim_semantic_coverage`

They remain phase-focused Author/FAP-adjacent candidates until a future Author
lane phase chooses whether to split semantic-only assertions from Author
payload, prompt/materialization, invocation, citation handoff, or final response
checks.

### Static Guards Consolidated

`tests/test_semantic_lane_structural_guards.py` absorbed repeated and durable
guards from AG-SEM product fixtures:

- RunKernel owns the atomic semantic bundle commit authority/apply boundary.
- `semantic_producer_bundle_commit_runtime.py` owns staging and reducer-builder
  calls for accepted contract, SemanticObservation, and ComponentCoverageRecord
  construction.
- `ordinary_semantic_producer_runtime.py` does not directly call individual
  semantic reducers or import orchestrator, Author/FAP, retrieval, provider, or
  HTTP/client surfaces.
- Semantic skip reasons remain return-only in the producer core.
- `core/pipeline_orchestrator.py` keeps only the currently licensed bounded
  ordinary semantic producer callsites.
- The semantic producer has no compensating rollback/revert paths.
- Phase fixture labels and example entities do not leak into closed runtime
  surfaces.

### Demoted Or Retired Guards

No behavioral test was retired. Duplicate static guard tests were demoted from
phase-local files because the new structural guard protects the same or broader
durable invariant:

- `test_static_guard_run_kernel_owns_atomic_semantic_commit_boundary`
- `test_static_guard_no_pre_sufficiency_semantic_bridge`
- `test_static_guard_skip_reasons_remain_return_only_in_core`
- `test_static_guard_producer_module_import_boundary`
- `test_static_guard_orchestrator_semantic_callsites_are_bounded`
- `test_static_guard_no_compensating_rollback_paths`
- `test_ag_sem_11c_static_guards_keep_second_fixture_out_of_closed_surfaces`
- `test_ag_sem_multi_01_static_closed_surface_and_import_guards`
- `test_ag_sem_prod_02_static_guards_keep_closed_surfaces_closed`

### Remaining Cleanup

- A future Author-lane cleanup can split or reroute the Author/FAP-heavy
  semantic fixture tests listed above.
- `semantic_search_lane` kept its QueryPlan/SearchJudgment structural guards in
  their existing files because they protect different consumer boundaries from
  the AG-SEM producer structural guards.
- No `fast_pr` semantic sentinel was selected in this phase.
