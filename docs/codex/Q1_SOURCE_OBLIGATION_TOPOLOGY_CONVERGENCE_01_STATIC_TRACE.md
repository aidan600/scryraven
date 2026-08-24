# Q1 source-obligation topology static trace

Scope: the bounded Q1 convergence lane only. This trace records identifiers,
enum kinds, ownership, and status transport; it contains no source content,
URLs, prompts, provider payloads, or model output.

## Authoritative owner trace

| Stage | Owner | Q1 obligation effect |
| --- | --- | --- |
| Query-shape assessment | `core/search_work_query_shape_runtime.py` | Creates the passive query-shape assessment and component/source-obligation candidate topology. |
| Question meaning | `core/ordinary_semantic_producer_runtime.py::build_question_meaning_record_from_search_work_plan` and `core/semantic_contract_foundation.py::QuestionMeaningRecord.from_query_shape_assessment` | Carries candidate refs into the QMR. |
| Accepted answer contract | `core/initial_answer_contract_acceptance_runtime.py::build_initial_answer_contract_acceptance_state` | Accepts exact candidate IDs once as `accepted_source_obligation_refs`, preserving kind and component ownership. |
| SearchOS qualification | `core/ordinary_multicomponent_synthesis_runtime.py::_evidence_ledger_requirement_kind_for_accepted_source_obligation` | Maps the accepted component obligation kind to its EvidenceLedger kind and reduces the component-owned qualified requirement. |
| Run contract | `core/run_authority_contract_templates.py` and `core/evidence_ledger.py::build_evidence_ledger_observation_from_run_contract` | Reduces the independently owned required canonical-documentation requirement into the ledger. |
| Ledger qualification | `core/evidence_ledger.py` | Holds exact requirement IDs, component/source-obligation IDs, structured source posture, candidate bindings, and satisfaction status. |
| Coverage and Sufficiency | `core/run_authority_sufficiency_validation.py::build_deterministic_sufficiency_judgment` | Carries each exact ledger-backed obligation into `missing`, `partial`, or `satisfied` assessments and then `final_packet_inputs`. |
| FAP | `core/final_answer_runtime_adapter.py::build_final_answer_packet` and `core/final_answer_packet_runtime.py::prepare_final_answer_packet_author_handoff_from_scope` | Consumes canonical current kernel ledger state and preserves exact requirement identity through FAP/Author handoff. |

## Observed Q1 topology

The first brokered PRODUCT packet exposed these two accepted, independently
owned records. Both were satisfied by the same opaque candidate binding.

| Semantic obligation kind | Owner | EvidenceLedger requirement kind | Live status |
| --- | --- | --- | --- |
| `canonical_documentation` | component | `canonical` | satisfied |
| `canonical_documentation` | run contract | `canonical` | satisfied |

The component record is the QMR/accepted-answer-contract direct-support
obligation. The run-contract record is the independently template-owned
canonical-docs requirement for current technical behavior. Their matching kind
does not authorize identity coalescing: they have distinct opaque IDs and
owners. A single candidate may satisfy both; no source-count or URL-diversity
rule is implied.

The prior provider-like regression modeled `official_current` at component
scope plus the run-contract `canonical_documentation` row. It remains useful
for that source path, but it is not live-topology equivalent. The added exact
Q1 offline regression models the observed component-plus-run-contract
`canonical_documentation` shape without changing query-shape or currentness
policy.

## Mismatch classification

**Category: A — transport/binding loss.**

The authoritative ledger already held both exact satisfied rows. The old
Sufficiency projection emitted component-owned ledger rows only when missing,
dropping a satisfied component-owned requirement. It also allowed a legacy
AnswerContract source-class compatibility summary with no canonical obligation
identity to become a new missing FAP obligation. The FAP adapter then merged
records by source class/status rather than canonical identity.

The legacy `reputable_secondary` summary was not an accepted QMR obligation,
a RunContract requirement, or an exact EvidenceLedger-owned component
requirement. It is therefore not a third semantic obligation and is
diagnostic-only whenever authoritative topology exists.

## Currentness posture

No currentness policy changed. The live run-contract canonical-documentation
row requires temporal posture `current`; its observed candidate-currentness
posture is `not_observed`, as is the component row's. No currentness was
inferred from source age, source title, or official/canonical status. The ledger
reports the exact canonical requirements satisfied under its existing
qualification policy; this phase neither reinterprets nor broadens that policy.
No Q1 blocker was classified as a currentness-policy failure.

## Repair boundary

The repair is limited to exact record transport and canonical identity:

- carry satisfied and partial component-owned ledger obligations alongside
  missing ones;
- treat unowned legacy class summaries as non-semantic compatibility data when
  authoritative topology is present;
- preserve FAP source-obligation records by canonical requirement identity,
  not by source class/status;
- build the safe bounded packet topology from accepted contract, run contract,
  and current kernel EvidenceLedger state.

The second brokered attempt reached a separate safe-observability transport
gap: the FAP quantitative preflight was already present in the blocked
`author_payload_ref`, which the ordinary RunKernel projection preserves, but
`build_safe_blocked_fap_summary` did not copy its closed-vocabulary summary to
the PRODUCT packet. The narrow repair projects that already-sanitized field;
it does not alter the preflight, FAP decision, or Author eligibility.

Final offline validation exposed one true Case-C mechanical duplicate in the
Sufficiency accumulator: a run-contract row already consumed through canonical
requirement and owned-obligation identity was re-added when its raw requirement
ID differed only by `-` versus `_`. The repair skips only the already-consumed
physical ledger row. It does not coalesce separately owned rows, even where
their obligation kinds match.

It does not change query-shape policy, SearchPlanner requirements, source
definitions, currentness semantics, Sufficiency/FAP standards, citation policy,
or provider behavior.

## Bounded convergence attempt ledger

All attempts used the exact Q1 query through the sanctioned brokered product
path. Only broker receipts and sanitized structural packets were inspected.

1. **Attempt 1:** target completed; both accepted canonical-documentation
   obligations were satisfied, but FAP blocked before Author.
2. **Attempt 2:** target completed; the same two obligations were satisfied.
   It proved that the first safe FAP projection omitted an already-sanitized
   quantitative preflight, which this phase repaired as observability-only
   transport.
3. **Attempt 3:** target completed with a nonzero target exit before SearchOS.
   The safe error code was `run_pipeline_search_planner_model_adapter_error`;
   no source-obligation topology or FAP packet was produced.
4. **Attempt 4:** target completed; both obligations were satisfied. FAP then
   blocked one direct-component numeric claim with the exact safe blocker code
   `missing_direct_source_binding` (four literals, no specialist declared).
   The preflight reported five authorized numeric claim rows overall. This does
   not establish a missing source-obligation or a currentness-policy failure.

The live budget is exhausted. Altering the remaining direct-source numeric
claim-matching behavior would change or extend FAP claim-binding semantics, so
it is intentionally outside this phase's licensed Case-A/Case-C repairs.

The added `test_ag89d_blocked_summary_preserves_only_safe_quantitative_preflight`
and the strengthened exact-component Sufficiency regression are classified as
`phase_focus`: they guard bounded packet projection and exact owned-obligation
transport, respectively, and are deliberately not `fast_pr` manifest
candidates.

## Final validation state

The focused obligation, EvidenceLedger, Sufficiency, FAP, exact-Q1 offline,
bounded-runner, broker/bootstrap, canonical-docs, semantic, Author, collection,
and fast-PR checks passed. `ruff`, `git diff --check`, and `pre-commit
--all-files` also passed.

Two broader offline checks remain red outside the repaired causal boundary:

- `test_sufficiency_fap_component_readiness_ag_readiness_01.py` stops before
  Sufficiency/FAP construction because its fixture accesses absent
  `search_work_plan` data (seven failures, two passes).
- the semantic-search integration gate has one case whose expected Author
  output is blocked by `missing_required_component_coverage`. It persists when
  the final Case-C accumulator repair is temporarily removed.

The repository bucket wrapper could not launch its configured Python runtime
in this Windows environment (`Access is denied`), so the corresponding
manifests were executed directly with the working `py -m pytest` path.
