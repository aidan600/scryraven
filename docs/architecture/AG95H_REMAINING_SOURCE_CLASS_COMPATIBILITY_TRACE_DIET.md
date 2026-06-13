# AG-95H Remaining Source-Class Compatibility Trace Diet

Status: historical product-callsite cleanup step superseded by AG-95I.

No live ScryRaven/proplex provider, model, search, retrieval, secret, `.env`,
DB row, raw provider payload, raw prompt, private log, cache, full raw trace,
local output packet, or private artifact access was used.

## Current Routing

Source-class recovery dispatch authority remains:

```text
AuthorityLifecycle.recovery_action
-> SourceClassRecoveryRunner
-> SourceClassRecoveryExecutor
```

AG-95H removed AG68E/AG68G product-callsite assertions that had treated
ControllerLoopSpine compatibility keys as dispatch proof, and it routed the
forced-corridor helper through `SourceClassRecoveryRunner`. It deliberately left
the focused ControllerLoopSpine packet-field diet to AG-95I.

Use `docs/architecture/AG95I_CONTROLLER_LOOP_SPINE_PACKET_FIELD_DIET.md` for the
current ControllerLoopSpine packet contract and remaining shared active-gate
compatibility classification.
