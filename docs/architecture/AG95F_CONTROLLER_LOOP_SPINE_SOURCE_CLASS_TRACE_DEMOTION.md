# AG-95F ControllerLoopSpine Source-Class Trace Demotion

Status: implemented as offline trace/test/doc cleanup. No live
ScryRaven/proplex provider, model, search, retrieval, secret, `.env`, DB row,
raw provider payload, raw prompt, private log, cache, full raw trace, local
output packet, or private artifact access was used.

> AG-95G follow-up: the orchestrator no longer reads
> `ControllerLoopSpineResult.source_class_executor_dispatched` while building
> targeted-retrieval ownership. The remaining source-class spine keys are
> preserved as diagnostic compatibility for named trace/test consumers.
> AG-95H follow-up: AG68E/AG68G product-callsite tests no longer assert those
> old keys directly; focused ControllerLoopSpine tests own that compatibility.

## Current Doctrine

Source-class recovery dispatch remains:

```text
AuthorityLifecycle.recovery_action
-> SourceClassRecoveryRunner
-> SourceClassRecoveryExecutor
```

`ControllerLoopSpine` source-class fields are diagnostic compatibility output
for older trace/test consumers. They are not runner dispatch authority.

## Demoted Trace Contract

ControllerLoopSpine source-class trace packets expose:

- `source_class_spine_trace_role=diagnostic_compatibility`
- `source_class_spine_dispatch_authority=false`
- `source_class_runner_dispatch_authority=authority_lifecycle.recovery_action`

Compatibility requires additive demotion markers, not key deletion: older
diagnostic consumers still expect keys such as `source_class_executor_dispatched`
and `authorized_dispatch`. Those keys may explain older spine-era state, but
must not authorize source-class runner execution.

## Runtime Boundaries Preserved

- `SourceClassRecoveryRunner` still reads
  `authority_lifecycle.recovery_action`.
- `SourceClassRecoveryExecutor` remains the bounded executor.
- Provider/search/query/ranking/Author/final-answer/citation behavior and live
  calls were not changed.
- Non-source-class ControllerLoopSpine arbitration remains out of scope.

## Cleanup

Cleanup reduced duplicated AG-95D/AG-95E doctrine and kept only one focused
AG-95F static/doc guard. This phase is demotion rather than line-count cleanup:
the compatibility keys remain intentionally additive until their consumers can
be retired.
