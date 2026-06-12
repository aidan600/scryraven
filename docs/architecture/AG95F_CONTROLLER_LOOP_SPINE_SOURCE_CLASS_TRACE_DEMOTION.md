# AG-95F ControllerLoopSpine Source-Class Trace Demotion

Status: implemented as offline trace, test, static-guard, and documentation
cleanup. No live ScryRaven/proplex provider, model, search, retrieval, secret,
`.env`, DB row, raw provider payload, raw prompt, private log, cache, full raw
trace, local output packet, or private artifact access was used.

## Current Doctrine

Source-class recovery dispatch remains:

```text
AuthorityLifecycle.recovery_action
-> SourceClassRecoveryRunner
-> SourceClassRecoveryExecutor
```

`ControllerLoopSpine` source-class fields are retained only as diagnostic
compatibility output for older trace/test consumers. They are not runner
dispatch authority.

## Demoted Trace Contract

ControllerLoopSpine source-class trace packets now expose explicit demotion
metadata beside the older compatibility keys:

- `source_class_spine_trace_role=diagnostic_compatibility`
- `source_class_spine_dispatch_authority=false`
- `source_class_runner_dispatch_authority=authority_lifecycle.recovery_action`

The old `source_class_executor_dispatched`, `executor_dispatched`,
`official_canonical_dispatch_fallback`, `executed_action_name`, and
`authorized_dispatch` surfaces remain compatibility diagnostics. They can
explain what the spine would have represented in the older ControllerLoopSpine
era, but they must not be consumed as source-class runner authorization.

## Runtime Boundaries Preserved

- `SourceClassRecoveryRunner` still reads canonical
  `authority_lifecycle.recovery_action`.
- `SourceClassRecoveryExecutor` remains the bounded executor.
- Provider routing/selection/depth, query generation/text, ranking/filtering,
  Author/final answer/citation behavior, persistence, and live-call behavior
  were not changed.
- `ControllerLoopSpine` still owns non-source-class checkpoint arbitration where
  currently licensed, including weak-corpus, conflict-resolution, terminal-stop,
  and bounded targeted-retrieval compatibility traces.

## Cleanup

The ControllerLoopSpine module docstring and source-class tests were relabeled
so the remaining source-class trace fields read as compatibility diagnostics
rather than current dispatch ownership. A focused AG-95F static guard protects
the demotion markers and the runner's canonical authority read.
