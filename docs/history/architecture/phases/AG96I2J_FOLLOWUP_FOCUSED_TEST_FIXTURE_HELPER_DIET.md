Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I2J_FOLLOWUP_FOCUSED_TEST_FIXTURE_HELPER_DIET).

# AG-96I2J Follow-up Focused-Test Fixture Helper Diet

## Status

AG-96I2J is a maintainability-only cleanup for the AG-96I2C through AG-96I2F
focused follow-up tests. It centralizes repeated fixture setup where the shared
helper makes the tests shorter and clearer, while keeping stage-specific
adversarial mutations local to the tests that explain them.

No runtime behavior was changed. No live provider, search, retrieval, fetch/read,
model, AuthorExecutor, citation-rendering, product-answer, or live-validation
surface was opened.

## Setup Centralized

`tests.helpers.followup_fixture_spine` now owns the repeated focused-test setup
helpers:

- `followup_fixture_gap` for the common source-obligation gap payload shape;
- `consume_followup_authorization`;
- `consume_followup_fixture_execution`;
- `consume_followup_evidence_intake`;
- `consume_followup_sufficiency_recheck`;
- `consume_followup_final_answer_packet`;
- `consume_followup_author_gate`;
- `run_followup_through_execution`;
- `run_followup_through_evidence_intake`;
- `run_followup_through_sufficiency_recheck`;
- `run_followup_through_final_answer_packet`.

These helpers only wrap the existing fixture-only authorize, adapter, and
`RunKernel.reduce` calls used by the tests. They do not authorize runtime
behavior, mutate canonical state independently of RunKernel, or become a product
authority surface.

## Duplicated Setup Deleted

Deleted duplicated private focused-test setup from:

- `tests/test_ag96i2c_followup_evidence_intake.py`;
- `tests/test_ag96i2d_followup_sufficiency_recheck.py`;
- `tests/test_ag96i2e_followup_final_answer_packet.py`;
- `tests/test_ag96i2f_followup_author_gate.py`.

The deleted local setup included repeated `_budget`, `_component`, `_gap`,
`_checkpoint`, `_fixture_payload`, and mechanical stage-through helpers such as
`_authorize_execute_intake`, `_through_recheck`, `_prepare_packet`,
`_through_packet`, and `_consume_gate`.

## Setup Kept Local

The following setup intentionally remains local because it makes the attack or
closed boundary easier to audit:

- cross-candidate and cross-packet binding mutations;
- spoofed observation payload edits;
- accepted-ledger payload mutation attempts;
- packet-only field mutation before Author gate consumption;
- static closed-surface guard imports, token checks, and orchestrator absence
  checks;
- exact expected `RunKernelTransitionError` matches.

AG-96I2G and AG-96I2H were intentionally left alone except for their existing
shared-helper dependency. They already consume the helper spine and contain
follow-on coverage rather than the older duplicated focused-test setup targeted
by this diet.

## Line-Count Delta

Touched test-file deltas:

| File | Before | After | Delta |
| --- | ---: | ---: | ---: |
| `tests/test_ag96i2c_followup_evidence_intake.py` | 622 | 518 | -104 |
| `tests/test_ag96i2d_followup_sufficiency_recheck.py` | 481 | 348 | -133 |
| `tests/test_ag96i2e_followup_final_answer_packet.py` | 583 | 441 | -142 |
| `tests/test_ag96i2f_followup_author_gate.py` | 533 | 356 | -177 |

Shared helper delta:

| File | Before | After | Delta |
| --- | ---: | ---: | ---: |
| `tests/helpers/followup_fixture_spine.py` | 250 | 397 | +147 |

Net result for the four focused tests is -556 lines. Net result including the
shared helper is -409 lines.

## Runtime And Authority Impact

Runtime file delta: zero.

Authority impact: none. RunKernel remains the owner of canonical follow-up state
transitions. The helper spine remains test setup only and has no runtime
consumer. It does not move or redefine EvidenceLedger, SufficiencyJudgment,
FinalAnswerPacket, Author gate, Author observation, provider, search, model,
AuthorExecutor, citation, or product-answer authority.

## Remaining Test-Maintenance Debt

Some direct adapter calls remain in the focused tests because the tests mutate
the resulting records before reduction. Extracting those calls further would hide
which binding or closed-surface field is intentionally being attacked.

The static closed-surface guard blocks still repeat forbidden import/token lists.
That repetition is acceptable for now because each focused test documents its
own phase boundary. A future cleanup could extract only transparent assertion
helpers if the local closed-surface story stays readable.

## Recommended Next Phase

Recommended next phase: live follow-up execution readiness audit.

That phase should remain separate from this fixture-helper diet and should not
open live ScryRaven/proplex calls, Author execution, citation rendering, or
product final-answer behavior unless explicitly scoped with a budget, redaction
plan, validation artifact path, and stop condition.

## AG-96I2K Follow-up Result

AG-96I2K completed the live follow-up execution readiness audit:
[AG96I2K_LIVE_FOLLOWUP_EXECUTION_READINESS_AUDIT.md](AG96I2K_LIVE_FOLLOWUP_EXECUTION_READINESS_AUDIT.md).

Result: the recommended first live-shaped follow-up target is
`official_current_candidate_acquisition`, implemented next as an offline
live-shaped recovery executor/adapter before any live validation. Runtime
files stayed closed for AG-96I2K, and live provider/search/retrieval/fetch/read,
Author, citation-rendering, and product-answer behavior remained disabled.
