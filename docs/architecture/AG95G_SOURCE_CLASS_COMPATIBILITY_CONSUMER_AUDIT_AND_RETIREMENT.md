# AG-95G Source-Class Compatibility Consumer Audit And Retirement

Status: historical consumer-audit step superseded by AG-95I.

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

AG-95G removed the orchestrator read of the old ControllerLoopSpine
source-class dispatch key and deleted duplicate AG68/AG69 assertions where
canonical lifecycle/runner checks already proved dispatch. It intentionally left
focused ControllerLoopSpine compatibility tests for the next packet diet.

AG-95I is that follow-up. Use
`docs/architecture/AG95I_CONTROLLER_LOOP_SPINE_PACKET_FIELD_DIET.md` for the
current inventory, field-retirement list, preserved shared active-gate
compatibility, and next cleanup phase.
