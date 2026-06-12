# AG-95E Stale Dispatch Doctrine And Fixture Cleanup

Status: implemented as offline fixture, static-guard, and documentation cleanup.
No live ScryRaven/proplex provider, model, search, retrieval, secret, `.env`, DB
row, raw provider payload, raw prompt, private log, cache, full raw trace, local
output packet, or private artifact access was used.

> AG-95F follow-up: ControllerLoopSpine source-class trace packets now carry
> explicit demotion metadata:
> `source_class_spine_trace_role=diagnostic_compatibility`,
> `source_class_spine_dispatch_authority=false`, and
> `source_class_runner_dispatch_authority=authority_lifecycle.recovery_action`.
> The old source-class spine keys remain compatibility diagnostics, not runner
> dispatch authority.

## Current Doctrine

The current authority chain remains:

```text
RunAuthorityContract
-> EvidenceLedger
-> SearchJudgment
-> SufficiencyJudgment
-> FinalAnswerPacket
-> AuthorExecutor
```

For source-class recovery dispatch after AG-95C:

```text
AuthorityLifecycle.recovery_action
-> SourceClassRecoveryRunner
-> SourceClassRecoveryExecutor
```

`ControllerLoopSpine`, `authorized_spine_action`, official/canonical admission
booleans, lifecycle eligibility booleans, reports, exports, and
`ControllerRecoveryDecision` may explain compatibility state. They do not
authorize source-class runner dispatch. `pipeline_orchestrator.py` remains a
coordination shell that calls bounded executors and attaches traces; it is not
the domain authority owner.

## Search Classification

The AG-95E sweep searched repo-visible `.py` and `.md` files, excluding output,
data, caches, virtualenv, and other generated/local artifact areas. Terms
searched: `authorized_spine_action`, `ControllerLoopSpine`,
`ControllerRecoveryDecision`, `controller_recovery_decision`,
`controller_recovery_executor_allows_attempt`,
`build_controller_recovery_decision`, `RECOVER_MISSING_SOURCE_CLASS`,
`Controller decides`, `orchestrator executes`, `orchestrator decides`,
`orchestrator authority`, `Controller-owned`, `controller-owned`,
`source_class_executor_dispatched`,
`source_class_recovery_executor_dispatch_not_authorized`,
`run_source_class_recovery_dispatch`, and
`authority_lifecycle.recovery_action`.

| Hit family | Classification | AG-95E action |
| --- | --- | --- |
| `core/source_class_recovery_runner.py`, `core/source_class_recovery_executor.py`, `core/retrieval_dispatch_runtime.py`, `core/pipeline_orchestrator.py` runner callsite | Current runtime code that remains valid. The runner consumes `authority_lifecycle.recovery_action`; `ControllerRecoveryDecision` remains only for diagnostic/provider-review compatibility when no canonical source-class action is active. | Runtime behavior left unchanged. |
| `core/controller_loop_spine.py` source-class `source_class_executor_dispatched` and `authorized_dispatch` fields | Current runtime compatibility/diagnostic code that remains valid for wider loop-spine traces, but not runner authority. | Runtime behavior left unchanged; tests/docs now label source-class runner dispatch as canonical lifecycle-owned. |
| `core/controller_recovery_decision.py`, provider allocation modules, visibility/export modules | Current runtime compatibility code that remains valid for provider-review allocation and diagnostics. Not source-class executor authorization. | Runtime behavior left unchanged; docs route source-class dispatch away from this as authority. |
| Primary AG-68/AG-69 fixtures: `tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py`, `tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py`, `tests/test_authority_lifecycle_execution_ag69c.py` | Stale test/fixture scaffolding. They directly gated executor calls by `authorized_spine_action`. | Modernized to call `run_source_class_recovery_dispatch()` with canonical `authority_lifecycle.recovery_action`; checkpoint refresh and lifecycle sync coverage preserved. |
| `tests/test_controller_loop_spine.py` | Current test that remains valid for non-source-class loop-spine lanes, with stale source-class dispatch wording in one static guard. | Updated the static guard name/assertions to protect canonical runner dispatch while preserving conflict spine authorization checks. |
| `tests/test_ag94h_e_authority_lifecycle_source_class_parity_audit.py` | Current test with stale helper parameter. | Removed unused `authorized_spine_action` helper argument as bonus cleanup. |
| `tests/test_ag74f_recovery_runner_extraction.py`, `tests/test_ag94h_c_recovery_executor_dispatch_authorization_audit.py`, `tests/test_ag94h_e_authority_lifecycle_source_class_parity_audit.py`, `tests/test_ag95d_recovery_dispatch_sanity_audit.py` | Current and historical tests that remain valid after AG-95C/AG-95E. | Left runtime assertions intact except the bonus stale parameter removal; AG-95D remains the canonical negative-control matrix. |
| Older AG-20 through AG-77 source-class/controller tests | Historical or compatibility tests, mostly validating old lanes, constants, or non-source-class behavior. | Preserved. Do not bulk rewrite unless a future phase opens that specific lane. |
| Current guidance: `docs/codex/CODEX_GUIDANCE_MAP.md`, `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md`, `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md` | Current-looking guidance requiring correction/supersession. | Added AG-95E source-class dispatch routing and legacy-playbook status notes. |
| Historical/current-ish docs: AG-68E, AG-69F, AG-74F, AG-79C, AG-79D, AG-94H-C, AG-94H-D, AG-94H-E, AG-94H-F, AG-95A | Historical docs that must be preserved but can mislead as current source-class dispatch doctrine. | Added short AG-95E supersession banners; body history left intact. |
| AG-95C and AG-95D docs | Current source-class dispatch doctrine and audit history. | AG-95D updated with AG-95E follow-up result; AG-95C remains the canonical dispatch consolidation record. |
| `docs/architecture/historical/**` | Historical docs. | Not touched beyond search classification. |
| Product/local artifact hits | Output/local artifacts or out-of-scope product docs for this phase. | Not touched. |
| `orchestrator decides` | False positive/no matches in scoped search. | No action. |

## Fixture Modernization

The AG-68/AG-69 fixture family now splits what it protects:

- checkpoint refresh and stale-spine compatibility remain asserted through
  `build_controller_loop_spine_result()` and checkpoint helpers;
- source-class runner dispatch is asserted through
  `run_source_class_recovery_dispatch()` and canonical
  `authority_lifecycle.recovery_action`;
- direct calls to `execute_source_class_recovery_action()` were removed from the
  three stale product-callsite fixture helpers;
- `authorized_spine_action` helper parameters were removed from those helpers;
- no provider/model/search live calls were added. All recovery execution uses
  injected offline fake search callables.

The aggregate-satisfied fixture cases now assert the recovery queries supplied by
the lifecycle action, because canonical dispatch may use normalized action
queries instead of the older hard-coded tuple.

## Documentation Supersession Rule

Historical docs may still say "Controller decides, orchestrator executes" or
describe `authorized_spine_action` as runner dispatch authority. That text is
history. Current guidance must use:

- RunAuthority owns canonical authority;
- the orchestrator coordinates bounded executors;
- source-class recovery dispatch uses
  `authority_lifecycle.recovery_action`;
- ControllerLoopSpine source-class dispatch output is
  diagnostic/compatibility, not runner authority;
- ControllerRecoveryDecision is not source-class executor authorization.

## Bonus Cleanup

AG-95E also removed one stale `authorized_spine_action` fixture argument from
`tests/test_ag94h_e_authority_lifecycle_source_class_parity_audit.py` and
renamed the relevant controller-loop static guard to protect the canonical
source-class runner dispatch split.

## Validation

Focused offline checks:

```text
py -m pytest -q tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py tests/test_authority_lifecycle_execution_ag69c.py
py -m pytest -q tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py tests/test_authority_lifecycle_execution_ag69c.py tests/test_ag95e_stale_dispatch_doctrine_cleanup.py tests/test_controller_loop_spine.py tests/test_ag94h_e_authority_lifecycle_source_class_parity_audit.py tests/test_ag95d_recovery_dispatch_sanity_audit.py tests/test_ag74f_recovery_runner_extraction.py tests/test_ag94g_orchestrator_strangulation_guidance.py
py -m pytest -q tests
py -m ruff check .
```

Results:

- Focused AG-68/AG-69 migration set: `27 passed`.
- Expanded recovery/guidance bundle: `109 passed`.
- Repo test suite scoped to tracked tests: `2972 passed, 1 deselected, 1 xfailed`.
- Ruff: passed.

Plain `py -m pytest -q` was also attempted, but collection stopped on
pre-existing duplicate test modules under `output/local_review/...`. AG-95E did
not inspect, modify, or delete those local output artifacts; the successful
`tests/`-scoped run is the repo-visible offline validation.
