Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I2I_FOLLOWUP_RUNKERNEL_MAINTAINABILITY_AUDIT).

# AG-96I2I Follow-up RunKernel Maintainability Audit

## Status

AG-96I2I is a maintainability-only follow-up to AG-96I2A through AG-96I2H.
It opens no product behavior and makes no live provider, search, retrieval,
fetch/read, model, AuthorExecutor, citation-rendering, or final-answer-display
calls.

The fixture-only spine remains:

```text
followup_authorization_state
-> followup_execution_state
-> followup_evidence_intake_state
-> EvidenceLedger projection
-> followup_sufficiency_recheck_state
-> sufficiency_judgment_projection
-> followup_final_answer_packet_state
-> final_answer_packet / final_answer_authority_projection
-> followup_author_gate_state
-> followup_author_observation_state
```

## Authority Boundary

RunKernel remains the owner for canonical follow-up run-state transitions.

RunKernel still:

- authorizes every follow-up fixture action;
- checks whether prior canonical state exists before opening the next fixture
  seam;
- rejects duplicate stage consumption;
- calls reducer helpers from inside `RunKernel.reduce`;
- commits canonical state into `RunState`;
- appends follow-up projection history;
- updates `RunState.projections`;
- owns the EvidenceLedger, SufficiencyJudgment, FinalAnswerPacket, Author gate,
  and Author observation handoff points.

The extracted helpers do not authorize actions, mutate `RunState`, decide
product behavior, decide provider/search/model behavior, or own policy.

## What Was Extracted

Added `core.followup_runkernel_reducers` for mechanical reducer support:

- follow-up closed-surface false-flag tuples;
- `require_followup_flags_false`;
- follow-up action/observation binding validators;
- `followup_sealed_candidate`;
- follow-up EvidenceLedger fixture-intake observation and outcome derivation;
- follow-up projection builders for authorization, fixture execution, evidence
  intake, sufficiency recheck, FinalAnswerPacket preparation, Author gate, and
  Author observation;
- the fixture FinalAnswerPacket authority projection builder.

Added `tests.helpers.followup_fixture_spine` for repeated test setup:

- shared balanced checkpoint fixture;
- shared sanitized fixture payload;
- shared through-Author-gate fixture spine runner;
- shared projection/history and boundary flag helpers for the end-to-end spine
  tests.

## What Was Deleted

Deleted the equivalent private helper bodies from `core/run_kernel.py` after the
new helper module covered them:

- `_require_followup_flags_false`;
- follow-up binding validators;
- follow-up EvidenceLedger fixture-intake derivation helpers;
- follow-up token/source-class helper functions;
- repeated inline follow-up projection dictionaries.

Deleted duplicated local fixture-spine setup from:

- `tests/test_ag96i2g_followup_fixture_spine.py`;
- `tests/test_ag96i2h_followup_author_observation.py`.

No adversarial spoofing/binding tests, runtime state fields, public exports,
closed-surface guards, or authority-boundary docs were deleted.

## What Stayed In RunKernel

The `authorize_followup_*` methods stayed in RunKernel. They contain the
yes/no/now-next authority checks and canonical input assembly that should remain
near the current `RunState`.

The reducer branches stayed in RunKernel. They still decide whether an
observation can be reduced, call the canonical record rebuilders, translate
helper failures into `RunKernelTransitionError`, and perform the final
state/projection/history commits.

The EvidenceLedger, SufficiencyJudgment, FinalAnswerPacket, Author gate, and
Author observation state assignments stayed in RunKernel because moving those
commits would split canonical ownership.

## Line-Count And Complexity Notes

Starting line count for `core/run_kernel.py`: 3,927 lines.

After extraction line count for `core/run_kernel.py`: 2,695 lines.

RunKernel delta: -1,232 lines.

The remaining follow-up reducer code is still long, but it now reads as stage
flow plus authority checks and commits instead of embedding every binding,
projection, and fixture-ledger helper inline. The extracted helper module is
large by design, but it is intentionally mechanical and has no RunKernel or
RunState write path.

## Behavior Preservation

The AG-96I2A-H behavior remains fixture-only:

- AG-96I2A authorization sealing remains non-executable;
- AG-96I2B fixture execution remains bound to the sealed candidate;
- AG-96I2C EvidenceLedger intake remains the only opened mutation seam;
- AG-96I2D sufficiency recheck derives from canonical intake and ledger state;
- AG-96I2E FinalAnswerPacket preparation derives from canonical state;
- AG-96I2F Author gate consumes packet authority while keeping Author closed;
- AG-96I2H Author observation derives compliance from packet/gate authority and
  sanitized observed output facts;
- Author execution, model calls, citation rendering, product answer behavior,
  provider/search/retrieval/fetch/read, and live validation remain closed.

## Remaining Debt

RunKernel still carries substantial follow-up authorization input assembly. That
assembly intentionally stayed because it is closer to authority than projection
formatting. A later phase may extract tiny canonical-input builders if it can
prove the builders are pure and RunKernel remains the only authorizing caller.

Older AG-96I2C-F focused tests still have local fixture setup. They were left
alone because those files contain stage-specific adversarial mutations and the
local setup keeps the spoofing context readable.

## Recommended Next Phase

Do not open Author execution or product answer activation by implication.

Recommended next phase:

```text
AG-96I2J — Follow-up fixture spine focused-test fixture helper diet
```

That phase should only consolidate remaining AG-96I2C-F test setup where it
improves readability, and should keep adversarial mutation tests explicit.

## AG-96I2J Follow-up Result

AG-96I2J completed that focused-test helper diet:
[AG96I2J_FOLLOWUP_FOCUSED_TEST_FIXTURE_HELPER_DIET.md](AG96I2J_FOLLOWUP_FOCUSED_TEST_FIXTURE_HELPER_DIET.md).

Result: the older AG-96I2C-F focused tests now share fixture-only stage-through
setup through `tests.helpers.followup_fixture_spine`, while spoofing,
binding-mismatch, closed-surface, and stage-specific mutation logic remains
local in the tests that explain it. Runtime files did not change, and RunKernel
authority did not move.
