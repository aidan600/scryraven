# AG-95D Recovery Dispatch Sanity Audit And Cleanup Target Sweep

Status: PASS. Offline audit only. No live ScryRaven/proplex provider, model,
search, retrieval, secret, `.env`, DB row, raw provider payload, raw prompt,
private log, cache, full raw trace, local output packet, or private artifact
access was used.

> AG-95E follow-up: The AG-68/AG-69 fixture debt ranked in this audit has been
> modernized. Source-class dispatch assertions in those fixtures now route
> through `run_source_class_recovery_dispatch()` and canonical
> `authority_lifecycle.recovery_action`; checkpoint/spine assertions are kept as
> diagnostic compatibility coverage.
> AG-95F follow-up: ControllerLoopSpine source-class traces now carry explicit
> diagnostic/compatibility demotion markers; old keys remain for compatibility.

## 1. Verdict

PASS. AG-95C preserved source-class recovery dispatch behavior and clarified the
runtime owner: `SourceClassRecoveryRunner` dispatches source-class recovery from
canonical `authority_lifecycle.recovery_action`, not from
`ControllerLoopSpine`, `ControllerRecoveryDecision`, admission booleans,
source-class lifecycle eligibility booleans, report/export fields, or diagnostic
projections. The runner still preserves the AG-75 provider-review path when no
canonical source-class recovery action is active. The main cleanup blocker is
not runtime dispatch; it is stale AG-68/AG-69 test scaffolding and older docs
that still describe direct `authorized_spine_action` executor gating.

## 2. AG-95C Sanity Matrix

Positive dispatch: `tests/test_ag95d_recovery_dispatch_sanity_audit.py` proves
an unmet official/current/legal obligation with approved canonical recovery
action, pending execution state, existing query/depth/provider prerequisites,
and callable search dispatches exactly once. A second runner call blocks on the
already-attempted canonical state.

Canonical absence blocks: the same matrix proves source-class recovery does not
dispatch when `authority_lifecycle.recovery_action` is absent, even when legacy
eligibility, official admission, ControllerLoopSpine, ControllerRecoveryDecision,
report/export, and diagnostic-looking fields all point toward recovery.

Canonical denial blocks: parametrized negative controls prove no dispatch when
recovery is not required, action type is not `recover_missing_source_class`, the
action is not approved, execution state is blocked, or recovery was already
attempted.

Mechanical executor checks: runner/executor checks still block missing
`process_search_queries`, missing providers, missing executor queries, missing
executor search depth, invalid envelopes, and unexpected provider roles. These
paths now use mechanical runner/executor skip reasons and do not rebuild or
enforce `ControllerRecoveryDecision`.

Demoted surfaces cannot authorize/veto: ControllerLoopSpine, ControllerRecoveryDecision,
official admission booleans, source-class lifecycle booleans, report/export
fields, and diagnostics cannot authorize source-class recovery without the
canonical action. ControllerRecoveryDecision also cannot veto an approved
canonical source-class recovery action; it is recorded as diagnostic-only.

Provider-review path remains protected: AG-75 provider/search allocation review
still works when no canonical source-class recovery action is active. It remains
bounded to the existing provider/search profile and does not become
source-class recovery dispatch authority.

## 3. Remaining Dirty Dishes Ranked

| Rank | Surface / file / function | Current role | Can delete now / demote now / blocker / do not touch | Blocker | Next action | Risk | Tests needed |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | `tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py::_product_call_site_execute`; `tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py::_execute_product_callsite`; `tests/test_authority_lifecycle_execution_ag69c.py::_product_handoff_execute` | Test scaffolding only, but runtime-callsite-relevant by topic. These fixtures still gate direct executor calls with `authorized_spine_action`. | blocker | The three fixtures bundle old direct-executor callsite assumptions with checkpoint refresh, authority lifecycle execution, and parity assertions. Rewriting all three in AG-95D would exceed the audit and risk deleting useful coverage without a dedicated consolidation pass. | AG-95E: split checkpoint-refresh assertions from dispatch assertions; route dispatch assertions through `run_source_class_recovery_dispatch()` and canonical lifecycle context; delete remaining direct `authorized_spine_action` source-class executor gates. | Medium | The three named files, `tests/test_ag95d_recovery_dispatch_sanity_audit.py`, `tests/test_controller_loop_spine.py`, source-class trace/parity tests. |
| 2 | `core/controller_loop_spine.py::_build_source_class_checkpoint_gate_trace` | Compatibility/diagnostic source-class trace output. It still computes `source_class_executor_dispatched`, but the runner no longer consumes it. | blocker | AG-68/AG-69 fixtures and older docs still imply the spine owns source-class dispatch. Non-source-class spine behavior for weak-corpus, conflict, terminal stop, and targeted retrieval remains active. | After AG-95E fixture cleanup, relabel or demote source-class-specific spine output as diagnostic compatibility and keep non-source-class arbitration intact. | Medium | `tests/test_controller_loop_spine.py`, AG-68/AG-69 fixture files, AG-95D static guards. |
| 3 | `core/pipeline_orchestrator.py` recovery-dispatch block around `build_controller_loop_spine_result`, `authorized_spine_action`, `run_source_class_recovery_dispatch`, and `build_controller_recovery_decision` | Coordination shell. Source-class dispatch uses the runner; `authorized_spine_action` still gates conflict resolution and carries compatibility trace. | blocker | Provider-review allocation still requires `ControllerRecoveryDecision`; source-class spine trace still feeds diagnostics and tests. Broad orchestrator cleanup would touch unrelated target/retrieval behavior. | Keep source-class runner call as-is. Later remove source-class-specific local policy residue only after AG-95E fixture cleanup and provider-review canonization. | High | Full required recovery-dispatch set plus AG-75 provider allocation tests and controller loop spine tests. |
| 4 | `core/controller_recovery_decision.py::build_controller_recovery_decision`; `core/controller_provider_search_allocation.py::record_provider_search_allocation_if_controller_authorized` | Bounded provider-review allocation path when canonical source-class recovery is absent. | blocker | No canonical RunAuthority/QueryPlan provider-review action exists yet. Deleting this now would remove protected AG-75 review behavior. | Future provider-review allocation canonization: introduce canonical provider-review action, make runner consume it, then retire ControllerRecoveryDecision from runner input. | High | AG-75 allocation tests, AG-95D provider-review test, visibility export tests. |
| 5 | `core/official_canonical_recovery_execution_admission.py::build_official_canonical_recovery_execution_admission` and admission booleans | Admission diagnostics and input to authoritative-source/action lifecycle construction. No longer runner dispatch authority. | blocker | Authoritative-source action still uses admission to build `AuthorityLifecycle` and the compatibility source-class lifecycle. | Field diet after source-class lifecycle can construct action records directly from canonical `AuthorityLifecycle.recovery_action`. | Medium | AG-50/AG-68 admission tests, AG-94H-E parity, AG-95D demoted-field tests. |
| 6 | `core/source_class_recovery_lifecycle.py::record_source_class_recovery_lifecycle` active eligibility/action-envelope fields | Compatibility action-record producer and trace projection. No longer runner dispatch authority. | blocker | ControllerRecoveryDecision, authoritative-source action, visibility, and many tests still consume eligibility/action-envelope fields as compatibility facts. | Diet fields after AG-95E fixture cleanup and admission/lifecycle diet phase; keep action record shape until consumers are inventoried. | High | Source-class lifecycle tests, AG-68/AG-69, AG-94H-E, AG-95D. |
| 7 | `core/source_class_recovery_controller.py::build_source_class_recovery_controller_input` and `decide_source_class_recovery` | Legacy compatibility controller that prepares source-class action parameters. | blocker | Still builds queries/action envelope/provider role/search depth for compatibility action records. Query/depth/provider behavior is closed in AG-95D. | Subordinate or replace only in a dedicated lifecycle/action-record diet that proves query text, depth, provider role, and action envelope parity. | High | Source-class lifecycle/controller tests, trace tests, source-class dispatch parity tests. |
| 8 | `core/authoritative_source_action.py::build_authoritative_source_obligation_state_and_action` and `_authority_runtime_arbitration` | Current recovery composition seam that builds canonical AuthorityLifecycle plus compatibility lifecycle/action records. | do not touch yet | This is the current bridge from SearchJudgment and authoritative obligation state into canonical recovery action. Changing it risks source-class, query, and authority-obligation behavior. | Keep until stale fixtures are cleaned and a dedicated admission/lifecycle field diet is scoped. | High | AG-94H-E/F/G, source-class trace tests, AG-95D matrix. |
| 9 | `core/authority_lifecycle_runtime_arbitration.py::build_authority_runtime_arbitration` recovery fields | Canonical recovery-action owner consumed by the runner. | do not touch yet | This is the authority path AG-95C intentionally promoted. | Preserve as current owner; add no wrapper/projection. | High | AG-95D positive/negative matrix, AG-94H-E parity. |
| 10 | Stale docs: `docs/architecture/AG94H_C_RECOVERY_EXECUTOR_DISPATCH_AUTHORIZATION_AUDIT.md`, `docs/architecture/AG94H_D_RECOVERY_DISPATCH_AUTHORIZATION_REPAIR.md`, `docs/architecture/AG94H_E_AUTHORITY_LIFECYCLE_SOURCE_CLASS_PARITY_AUDIT.md`, selected AG-95A text | Historical/current-ish docs that still say runner consumes `authorized_spine_action` or ControllerLoopSpine is final source-class dispatch truth. | can demote now | They are historical phase records, so bulk rewriting would erase useful history; the risk is current-looking snippets. | Add short AG-95C/AG-95D supersession notes or route readers to this doc and AG-95C. Do not rewrite historical bodies wholesale. | Low | Docs/static grep for `authorized_spine_action` plus AG-95D doc checks. |

The only clear can-delete-now code/test hooks found in this audit were the
small stale fixture arguments removed by the bonus cleanup. No remaining runtime
source-class dispatch owner can be deleted safely in AG-95D.

## 4. Bonus Cleanup Result

Attempted: yes.

What changed: the executor's unexecutable-action skip reason was demoted from
`controller_recovery_decision_allowed_but_executor_action_unexecutable` to
`source_class_recovery_executor_action_unexecutable`, and obsolete
`authorized_spine_action` fixture arguments were removed from AG-74F, AG-75A,
and AG-94H-C runner/provider-review tests.

Net LOC impact: -11 LOC for the bonus cleanup. Runtime dispatch behavior did
not change; only a stale diagnostic label and test-only fixture hooks changed.

Blocker if no cleanup: not applicable.

## 5. AG-95E Follow-Up Result

AG-95E completed the stale test/doc cleanup recommended here.

Result: the AG-68/AG-69 fixture family no longer gates source-class executor
calls by `authorized_spine_action`. Source-class dispatch assertions route
through `run_source_class_recovery_dispatch()` and canonical
`authority_lifecycle.recovery_action`; checkpoint refresh and spine output
remain as diagnostic compatibility coverage. Current-looking AG-68/AG-69,
AG-74F, AG-79C/AG-79D, AG-94H, and AG-95A docs now carry supersession notes
instead of silently presenting the old dispatch model as current doctrine.
