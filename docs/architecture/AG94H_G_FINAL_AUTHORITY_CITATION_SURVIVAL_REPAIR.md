# AG-94H-G Final Authority Citation Survival Repair

## Executive verdict

AG-94H-G repairs the final handoff from selected official/current/legal authority
evidence to final-answer citations. When selected authority evidence is
citation-eligible and has a concrete source identity, it must be visible to the
Author evidence payload and survive as a final citation. If it cannot survive,
the answer is not treated as complete.

## AG-94H-F packet failure being repaired

The AG-94H-F live packet showed the recovery control plane working: recovery was
eligible, used, attempted, and returned official/current/legal material. The
failure happened later. Accepted/readable authority evidence existed, final
selected authority evidence existed, and final evidence included an
official/canonical item, but final official/canonical citations were zero. Weak
fallback citations could still appear in the answer, masking the unmet
official/current/legal citation obligation.

## Exact first handoff break

The first concrete break is post-Author citation observation. Selected authority
evidence can exist in the authority lifecycle and can be present in
`final_top_evidence`, but the final markdown citation telemetry only records
source ids actually emitted by the Author. Before this phase, there was no
identity-level check requiring the selected authority source id to appear in
`final_answer_source_ids_used`, and no answer-readiness guard when it did not.

There was also a smaller prompt-surface risk: the precision Author evidence
slice could omit a selected authority item even when it was present in final
evidence. That made citation survival depend on aggregate visibility instead of
an explicit selected-authority handoff.

## New citation survival rule

For official/current/legal obligations, citation-eligible selected authority
evidence must survive by identity. A source/candidate/evidence id or URL from
the selected authority record must match an Author-visible final evidence item,
and the final answer must cite the selected source id.

If the selected authority item has no citeable source identity, the run records
`selected_authority_evidence_unciteable` and blocks answer-complete posture. If
the item is citeable but not cited, the run records `citation_survival_failed`
and blocks answer-complete posture.

## Weak fallback masking guard

Weak fallback citations can still be observed as context, but they do not satisfy
the official/current/legal obligation. If selected authority evidence exists and
does not survive into the final citation list, weak fallback source ids trigger
the masking guard and the answer is treated as insufficient rather than complete.

## What changed

- Added `core.final_authority_citation_survival`, a pure sanitized projection
  and outcome guard for selected-authority citation survival.
- Repaired the Author evidence payload by appending missing selected authority
  evidence from `final_top_evidence` before Author execution.
- Added post-Author diagnostics for survived, unciteable, and not-cited selected
  authority evidence.
- Downgraded answer readiness when selected authority citation survival fails.
- Added controller ledger identity diagnostics so observed final citations must
  match selected authority evidence identity when that final citation surface is
  in scope.
- Added an offline AG-94H-G reproduction fixture with sanitized synthetic data.

## What did not change

- No live provider, model, search, or retrieval calls were added or run.
- Provider routing, provider order, search depth, query generation, source
  classification, candidate acquisition, candidate fit, and ranking were not
  changed.
- Author prose was not broadly rewritten. The change is an evidence-payload and
  completion-guard handoff.
- Aggregate/status observability remains diagnostic only and does not prove
  authority custody.
- `pipeline_orchestrator.py` was touched only for narrow wiring: Author evidence
  payload repair, post-Author survival projection, and outcome guard application.

## Tests/checks run

- `py -m pytest -q tests/test_ag94h_g_final_authority_citation_survival.py`
- `py -m pytest -q tests/test_ag94h_c_recovery_executor_dispatch_authorization_audit.py tests/test_ag94b_cli_official_current_recovery_trace_custody.py`
- `py -m pytest -q tests/test_final_answer_packet_ag89d.py tests/test_final_answer_author_runkernel_ag91k.py tests/test_ag90h_post_author_output_projection.py tests/test_ag76c_final_evidence_bundle_builder.py tests/test_ag76d_cit_controller_owned_citation_source_handoff_contract.py`
- `py -m pytest -q tests/test_ag94h_e_authority_lifecycle_source_class_parity_audit.py tests/test_official_canonical_recovery_query_acquisition_ag50a.py tests/test_official_canonical_recovery_execution_admission_ag50b.py tests/test_ag74a_controller_evidence_ledger.py tests/test_ag74b_controller_authority_disposition.py tests/test_ag74c_ledger_gated_visibility_consumer_subordination.py`
- `py -m pytest -q tests/test_ag94g_orchestrator_strangulation_guidance.py tests/test_authority_lifecycle_candidate_visibility_ag69d.py`
- `py -m ruff check .`

## Remaining risk

The repair depends on stable selected authority source identities. If a future
phase introduces a final citation format that cannot carry source ids, the
unciteable/citation-survival failure path should be extended before the answer is
allowed to complete.

## Recommended next validation

After merge only, run exactly one live rerun of `food_regulatory_non_us`.
Success signals:

- `source_class_recovery_execution_attempted=true`
- accepted and final-selected authority evidence exists
- at least one official/current/legal citation survives into the final answer
- the final answer names the official/current legal/regulatory authority
- weak fallback citations do not stand alone for the regulatory obligation
