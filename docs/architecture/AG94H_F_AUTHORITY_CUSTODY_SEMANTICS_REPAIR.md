# AG-94H-F Authority Custody Semantics Repair And Simplification

## Executive Verdict

AG-94H-F repairs the authority satisfaction rule for source-class recovery:
legacy aggregate/status observability is no longer authority-satisfying control
truth. Required authority is satisfied only by explicit custody-backed proof.

The new shared predicate is
`core/authority_custody_satisfaction.py::authority_custody_satisfaction_for_source_class`.
Both opened runtime consumers now use it:

- `core/authoritative_source_action.py::_evidence_fits_for_source_classes()`
- `core/official_canonical_recovery_execution_admission.py::_authority_evidence_fits_for_source_class()`

## AG-94H-E Finding Being Repaired

AG-94H-E found that the live-shaped AG-94H-D blocker was caused by legacy
aggregate leakage. `source_class_satisfaction_status=satisfied_strong` and
positive `source_class_strong_satisfaction_counts` were being converted into
`AuthorityEvidenceFit.authoritative(...)`.

That caused authority lifecycle to report recovery as not needed while the
source-class recovery lifecycle correctly showed an unresolved official/current
gap, approved recovery action, and executable queries.

## Exact Bad Behavior Removed

The repair removes control authority from aggregate-only fields:

- `source_class_satisfaction_status=satisfied_strong`
- `source_class_strong_satisfaction_counts > 0`
- `final_evidence_official_or_canonical_count > 0`
- `final_citation_official_or_canonical_count > 0`
- final selected authority evidence counts without selected evidence identity
- source survival aggregate counts
- source-tier/source-domain aggregate survival diagnostics
- any official/canonical count without candidate/passport/selected custody

These fields can remain visible as diagnostics, but they no longer create
authority-satisfying fits.

## New Authority Satisfaction Rule

A required source class is satisfied enough to block recovery only when the
runtime-visible state contains custody-backed proof for that required class.

If proof is ambiguous, missing, aggregate-only, weak-only, secondary-only, or
paired with a legacy custody gap, the class is treated as unsatisfied for
authority control. The system should prefer bounded recovery or insufficiency
over false satisfaction.

## What Counts As Custody Proof

The shared helper accepts only explicit custody evidence, such as:

- selected authority evidence in ControllerEvidenceLedger with a concrete
  candidate/evidence identity and matching required source class;
- authority lifecycle selected authority evidence with `satisfies_authority`
  and a concrete evidence identity;
- an authority candidate passport for the required source class with
  `satisfies_authority=true`, readable candidate state, and final accepted or
  promoted authority disposition;
- official-current custody projection records with accepted or partially
  accepted candidate identity;
- FinalAnswerPacket source-obligation satisfaction only when it carries
  satisfied candidate identity through custody.

## What No Longer Counts As Custody Proof

The helper deliberately rejects:

- aggregate `satisfied_strong` status without candidate identity;
- positive source-class strong counts without selected candidate custody;
- final evidence/citation official/canonical counts without selected custody;
- final selected authority evidence count alone;
- source survival aggregate counts;
- weak or secondary-only source-class statuses;
- ControllerEvidenceLedger `legacy_gap_observed` paired with aggregate-only
  final evidence/citation survival.

Trace-safe demotion reasons include:

- `aggregate_status_demoted_no_custody`
- `aggregate_count_demoted_no_custody`
- `legacy_gap_blocks_aggregate_satisfaction`
- `candidate_passport_custody_satisfied`
- `selected_authority_evidence_satisfied`
- `official_current_custody_satisfied`
- `no_authority_custody_proof`

## Why This Simplifies Authority

Before AG-94H-F, two local consumers independently interpreted legacy aggregate
fields as authority satisfaction. The new helper gives those consumers one
custody-aware predicate and demotes the old status/count path to diagnostics.

The old aggregate path is not wrapped or force-overridden. It is removed from
the authority-satisfying decision.

## Why This Is Not A Provider/Search/Query Repair

This phase does not change provider selection, provider order, search depth,
query generation, query text, ranking, returned-source classification, prompts,
Author behavior, final-answer behavior, citations, package names, CLI names,
environment names, database names, or session names.

The repair changes only the authority predicate used to decide whether existing
evidence is sufficient to block required source-class recovery.

## Diagnostics-Only Legacy Observability

Legacy aggregate/status fields are still useful review signals. They can show
that some older path believed official/canonical material survived, or that
legacy source-class recovery classified a bucket as strong.

They are not proof that a selected, represented, readable, accepted authority
candidate exists. They remain diagnostics, not custody truth.

## How This Enables AG-94H-D Dispatch

For the AG-94H-E live-shaped fixture, aggregate-only strong observability no
longer fulfills the legal/current official authority requirements. The authority
lifecycle now sees a missing requirement, finds recovery queries, and allows
required recovery when no hard blocker is present.

That lets ControllerRecoveryDecision subordinate the legacy gap for one bounded
recovery attempt, ControllerLoopSpine authorize `RECOVER_MISSING_SOURCE_CLASS`,
and the source-class recovery runner reach the executor entrypoint.

## Tests/Checks Run

Focused offline checks run during AG-94H-F:

- `py -m pytest -q tests/test_ag94h_e_authority_lifecycle_source_class_parity_audit.py`
- `py -m pytest -q tests/test_official_canonical_recovery_execution_admission_ag50b.py`
- `py -m pytest -q tests/test_ag94h_c_recovery_executor_dispatch_authorization_audit.py`
- `py -m pytest -q tests/test_authority_lifecycle_execution_ag69c.py`
- `py -m pytest -q tests/test_authority_lifecycle_projection_control_ag69e.py`
- `py -m pytest -q tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py`
- `py -m pytest -q tests/test_ag94b_cli_official_current_recovery_trace_custody.py`
- `py -m pytest -q tests/test_ag94d_official_source_acquisition_quality.py`
- `py -m pytest -q tests/test_ag94e_generic_official_authority_acquisition_benchmark.py`

## Closed Surfaces Preserved

Closed surfaces preserved:

- no live provider/model/search/retrieval calls;
- no provider routing, order, selection, or swap changes;
- no search depth or budget changes;
- no query generation or query text changes;
- no ranking, filtering, or source-classification overhaul;
- no Author, final-answer, or citation behavior changes;
- no package, CLI, env, database, or session rename;
- no broad `pipeline_orchestrator.py` rewrite;
- no Denmark, EU, food, TSA, IRS, or other source-specific hardcoding.

## Recommended Next Validation

After merge only, run exactly one live rerun of `food_regulatory_non_us`.

Success signal:

- `authority_lifecycle_required_recovery_allowed=true`
- `source_class_recovery_eligible=true`
- `controller_recovery_retry_allowed=true` or
  `allowed_executor_action=execute_existing_recovery_action`
- authorized dispatch reaches `RECOVER_MISSING_SOURCE_CLASS`
- `source_class_recovery_execution_attempted=true` or the authority lifecycle
  executor entrypoint is reached

Stop after one run and classify the next blocker.
