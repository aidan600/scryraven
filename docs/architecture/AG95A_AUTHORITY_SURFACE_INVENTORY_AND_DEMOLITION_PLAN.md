# AG-95A Authority Surface Inventory And Demolition Plan

Status: superseded historical inventory.

Status note, AG-95E: source-class dispatch authority is
`authority_lifecycle.recovery_action`; this file is historical doctrine, not
runner authority.

AG-95A was the broad demolition map for source-class recovery and final-custody
authority debt after AG-94H. Its useful current guidance has been absorbed into
the RunAuthority guide, AG-95C through AG-95M, and the compact AG-95N/O/P
burn-down note. Keep this file as a routing stub rather than a long competing
inventory.

Current source-class dispatch authority:

```text
AuthorityLifecycle.recovery_action
-> SourceClassRecoveryRunner
-> SourceClassRecoveryExecutor
```

Current final-answer authority direction:

```text
FinalEvidenceBundle
-> FinalAnswerPacket
-> AuthorExecutor
-> post-Author projections observing packet/bundle state
```

Retained compatibility surfaces are not current doctrine:

- ControllerRecoveryDecision remains only for diagnostic/provider-review
  compatibility until a canonical provider-review action exists.
- ControllerLoopSpine remains shared compatibility arbitration for non-retired
  lanes; source-class runner dispatch must not read it as authority.
- Trace/export/report/projection helpers observe canonical state and must not
  manufacture recovery decisions, source-obligation satisfaction, final answer
  readiness, or citation custody.

SCRY-02 active naming inventory remains unchanged: `proplex`, `python -m
proplex`, `PROPLEX_*`, `proplex.db`, and `proplex_*` state keys are active
compatibility names; historical ProPlex/FauxPlex/Foplex references remain
history, not current public naming.

Use `docs/architecture/AG95N_O_P_FINAL_AUTHORITY_VISIBILITY_RECOVERY_DECISION_PROJECTION_BURNDOWN.md`
for the current AG-95N/O/P outcome and next target.
