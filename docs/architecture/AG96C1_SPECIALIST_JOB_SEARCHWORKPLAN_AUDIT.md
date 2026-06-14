# AG-96C1 Specialist Job and SearchWorkPlan Role Audit

## 1. Status and scope

Status: static architecture audit/design only.

This document audits legacy specialist units and adjacent helpers under the
current RunKernel / RunAuthority / SearchWorkPlan doctrine. It does not change
runtime behavior, prompt behavior, provider/model/search routing, retrieval,
ranking, citation behavior, Author behavior, or mode policy. It does not
implement SearchWorkPlan, QuantWorkUnit, Analyst, Scrutineer, or Author runtime
changes.

No provider, model, search, retrieval, or live ScryRaven/proplex call was run for
this audit. No live validation was run. The audit uses repo-tracked files only;
it does not assume uncommitted Project Sources, secrets, `.env`, raw provider
payloads, raw prompts beyond repo-tracked prompt templates, DB rows, private
logs, caches, full raw traces, or local output packets.

## 2. Current doctrine summary

Durable doctrine after AG-96C0:

- All modes are governed by RunKernel / RunAuthority.
- Modes control reasoning depth, follow-up authority, and budget shape.
- Query components control breadth.
- Source obligations control evidence requirements.
- Providers are selected by job.
- Executors are bounded workers, not authority owners.
- Official/current behavior is a source obligation and search constraint, not a
  mode-specific executor family.
- Final authority remains with the canonical chain:
  `RunAuthorityContract -> EvidenceLedger -> SearchJudgment ->
  SufficiencyJudgment -> FinalAnswerPacket -> AuthorExecutor`.

The durable question is not whether legacy names deserve preservation. The
durable question is which capability the name was trying to provide, whether the
capability is still needed, and where it belongs under RunKernel,
SearchWorkPlan, EvidenceLedger, SearchJudgment, SufficiencyJudgment,
FinalAnswerPacket, or a bounded executor.

## 3. Capability inventory

| Capability | Still needed? | Durable home |
| --- | --- | --- |
| Query-shape classification | Yes | RunAuthorityContract / SearchWorkPlan query_shape |
| Component decomposition | Yes | SearchWorkPlan components |
| Search query planning | Yes | SearchWorkPlan provider_jobs plus QueryPlan admission |
| Scout/disambiguation/query-shaping | Yes as a job, not as durable agent identity | SearchWorkPlan query_shape/components/provider_jobs |
| Direct candidate search | Yes | SearchWorkPlan provider_jobs, with candidates admitted through canonical evidence flow |
| Semantic recall | Yes | SearchWorkPlan provider_jobs, candidate-only until fetched/read/admitted |
| Official/current acquisition | Yes | Source obligations plus provider_jobs and EvidenceLedger custody |
| Quantitative source-bound math planning | Yes | SearchWorkPlan quant_work_units tied to source obligations |
| Deterministic calculation request/validation | Yes | QuantWorkUnit / QuantValidator bounded by source-bound values |
| Assumption tracking | Yes | RunAuthorityContract obligations, EvidenceLedger, FinalAnswerPacket caveats |
| Evidence synthesis | Yes | Bounded synthesis_jobs over admitted/available material |
| Sufficiency/gap detection | Yes | SearchJudgment and SufficiencyJudgment |
| Remediation/follow-up authorization | Yes | RunAuthority / SearchJudgment / SearchWorkPlan follow_up_authority |
| Adversarial audit / red-team / claim challenge | Yes, especially for Deep | SearchWorkPlan audit_jobs plus bounded audit executor |
| Citation/evidence eligibility | Yes | EvidenceLedger and FinalAnswerPacket |
| Final answer expression | Yes | AuthorExecutor consuming FinalAnswerPacket-derived payload |

## 4. Legacy unit audit

### Scout

Files inspected: `core/scout.py`, `core/prompts.py`,
`core/pipeline_orchestrator.py`, `core/query_plan_runtime_adapter.py`,
`tests/test_scout.py`, and
`tests/test_scout_continuation_spine_gate_ag45c.py`.

Current implementation: Scout is an active, prompt-era model helper for selected
report types. `run_scout` builds a bounded evidence block from early chunks,
calls `ask_model` with the configured fast provider/model, requires JSON, and
returns directed queries or `None`. The orchestrator can run it on the first
iteration for registered report types and, if it returns directed queries, sends
those queries through QueryPlan finalization and retrieval-stop/continuation
gates before any continuation search is scheduled. It does not itself execute
search, retrieve evidence, admit evidence, select citations, write the final
answer, or decide final sufficiency.

Calls: it calls a model through `ask_model`. It does not directly call search,
retrieval, or providers beyond the model provider selected by its caller.

Current owner/authority posture: active legacy helper; candidate query-shaping
worker only. Query identity/order is subordinated to QueryPlan. Continuation is
gated by the current retrieval-stop/RunKernel path, not by Scout alone.

Apparent intended capability: disambiguation, query shaping, normalization, and
component discovery for report types that benefit from early specialist routing.

Capability still needed: yes. The named Scout agent is not the durable concept;
the job remains useful.

Target future owner: SearchWorkPlan `query_shape`, `components`, and
`provider_jobs`, with QueryPlan admission for query identity/order while QueryPlan
remains the active runtime authority.

Bounded executor needed? Possibly, but only as a query-shaping or
disambiguation worker selected by job. The durable unit should be a job/capability
label, not a separate Scout authority.

Must not own authority over source truth, evidence admission, citation
eligibility, sufficiency, follow-up/remediation authorization, provider policy,
or final-answer readiness.

Recommended future posture: fold the Scout job into SearchWorkPlan and retire
Scout as a named agent/executor after an accepted design. Until then, leave the
current compatibility behavior in place.

### Researcher / query generator

Files inspected: `core/query_production_runtime.py`, `core/query_plan.py`,
`core/query_plan_runtime_adapter.py`, `core/prompts.py`,
`core/pipeline_orchestrator.py`, and `tests/test_query_production_ag91i.py`.

Current implementation: query production is already partly authority-collapsed.
RunKernel authorizes query production, the runtime helper may produce candidate
queries from the researcher prompt or a recon rewrite path, and QueryPlan
admission owns final query identity/order. Tests assert that raw prompts, model
responses, and provider payloads are not stored in RunKernel state, and that
QueryPlan owns query ordering.

Calls: it can call a model through `ask_model`. The recon path can call a Brave
reconnaissance function when available and authorized by the runtime inputs. It
does not admit final evidence, decide sufficiency, select citations, or write the
answer.

Current owner/authority posture: RunKernel owns query-production authorization;
QueryPlan owns query admission/order. Researcher/recon outputs are candidate
inputs.

Apparent intended capability: search query planning, disambiguating entity names,
and converting routing posture into search-ready candidate queries.

Capability still needed: yes.

Target future owner: SearchWorkPlan construction for `query_shape`,
`components`, `provider_jobs`, and budget shape; QueryPlan or its successor
continues to admit executable query identity/order until SearchWorkPlan is
implemented.

Bounded executor needed? Yes, a candidate query generator or recon rewriter can
remain useful.

Must not own authority over provider policy, source obligations, follow-up
authorization, evidence admission, citation eligibility, or final sufficiency.

Recommended future posture: keep as bounded candidate production; rename or fold
into SearchWorkPlan jobs when the passive SearchWorkPlan contract exists.

### Expander / evaluator / synthesis evaluator

Files inspected: `core/prompts.py`, `core/pipeline_orchestrator.py`,
`core/runtime_prompt_assembly.py`, `core/query_plan_runtime_adapter.py`,
`core/legacy_review_runtime_stage.py`,
`core/synthesis_evaluator_supplemental_search_handoff_contract.py`,
`core/synthesis_evaluator_supplemental_search_runtime_handoff.py`,
`tests/test_evaluator_continuation_spine_gate_ag44c.py`, and
`tests/test_ag76d_ses_synthesis_evaluator_supplemental_search_handoff_contract.py`.

Current implementation: Expander and Evaluator are active prompt-era gap/query
helpers in the retrieval loop. Expander proposes component continuation queries
after first-pass evidence; Evaluator can propose follow-up queries when Expander
does not fire. Both feed QueryPlan finalization and continuation gates before
search is scheduled. The synthesis evaluator is a later legacy review helper
over Analyst prose that can request supplemental queries; its handoff contract
packages already-computed supplemental-search facts without behavior changes.

Calls: Expander, Evaluator, and synthesis evaluator can call models. The legacy
review runtime can lead to supplemental search only through existing QueryPlan,
provider-plan, retrieval, and Analyst rerun paths. The handoff contract/runtime
handoff only package already-computed facts.

Current owner/authority posture: active legacy helpers for candidate gaps and
candidate follow-up queries; passive handoff representation for supplemental
search facts. Durable follow-up authority is not supposed to belong to these
helpers.

Apparent intended capability: component decomposition, gap detection, supplemental
query planning, and evidence-synthesis QA.

Capability still needed: yes.

Target future owner: SearchWorkPlan components/provider_jobs for planned breadth;
SearchJudgment and SufficiencyJudgment for gap and continuation decisions.

Bounded executor needed? Yes, but only as gap-signal or synthesis-QA workers over
bounded inputs.

Must not own authority over final sufficiency, remediation authorization,
provider/depth policy, evidence admission, citation eligibility, or final answer
readiness.

Recommended future posture: fold Expander/Evaluator/Synthesis Evaluator jobs
into SearchWorkPlan, SearchJudgment, and SufficiencyJudgment; keep passive
compatibility handoffs until the legacy runtime is retired.

### Economist

Files inspected: `core/pipeline.py`, `core/pipeline_orchestrator.py`,
`core/prompts.py`, `core/economist_handoff_contract.py`,
`core/analyst_runtime_stage.py`,
`tests/test_ag76d_eco_controller_owned_economist_handoff_contract.py`, and
`tests/test_economist_static_code_execution_guard.py`.

Current implementation: the active Economist path is a quantitative model helper
for selected quantitative report types. It performs a preflight, calls the
Economist prompt when numeric anchors appear usable, validates a structured
`economist_v1` packet, blocks model-generated code execution, and may run
deterministic shadow calculations only when source-bound schema conditions are
met. The Economist handoff contract is passive and explicitly packages
already-computed facts without prompts, providers, retrieval, code execution,
policy changes, Analyst bypass, Author bypass, citation changes, or final-answer
behavior.

Calls: the active step can call a model. It does not call search or retrieval.
It does not execute model-generated code. The handoff contract does not call
models, providers, search, retrieval, or calculation code.

Current owner/authority posture: active bounded quantitative helper plus passive
handoff. It is not final evidence authority and must pass through Analyst and
final packet/Author boundaries.

Apparent intended capability: source-bound numeric extraction, assumption
tracking, deterministic calculation requests, and quantitative consistency
support.

Capability still needed: yes.

Target future owner: SearchWorkPlan `quant_work_units` tied to components and
source obligations; EvidenceLedger for source-bound value custody; a future
QuantPlanner / QuantValidator for bounded calculation planning and validation.

Bounded executor needed? Yes, likely renamed away from Economist toward
QuantWorkUnit, QuantPlanner, or QuantValidator.

Must not fabricate numeric values, bypass Analyst or Author, execute arbitrary
code, select final evidence/citations, decide final numeric answer posture, or
override missing source-bound obligations.

Recommended future posture: redesign/rename as subordinate quantitative work
units under SearchWorkPlan and source-bound evidence custody. Leave current
runtime behavior unchanged until a dedicated accepted design.

### Analyst

Files inspected: `core/analyst_runtime_stage.py`, `core/prompts.py`,
`core/pipeline_orchestrator.py`, `core/economist_handoff_contract.py`,
`core/module_registry.py`, and `tests/test_ag90f_analyst_runtime_stage.py`.

Current implementation: Analyst is an active model synthesis stage. The runtime
stage extraction performs pre-Analyst gates, handles unsupported-retrieval
fallbacks, preserves Economist output as shadow quantitative material, builds the
Analyst prompt, and calls `ask_model` with injected runtime dependencies. The
stage does not select providers, perform search, retrieve, mutate queries, rank
final evidence, format citations, or assemble Author prose.

Calls: it calls a model through `ask_model`. It does not directly call search,
retrieval, provider routing, citation formatting, or Author execution.

Current owner/authority posture: bounded synthesis worker over available
runtime material. It may surface uncertainty or candidate gaps in prose, but
canonical gap and final-readiness authority belongs elsewhere.

Apparent intended capability: evidence synthesis, source weighting, temporal
reasoning, and structured analytic assessment before final expression.

Capability still needed: yes.

Target future owner: SearchWorkPlan `synthesis_jobs` for bounded synthesis work;
SearchJudgment/SufficiencyJudgment for gaps and final readiness; FinalAnswerPacket
for Author-visible final authority.

Bounded executor needed? Yes.

Must not own source-gap/search/remediation authority, source admission, citation
eligibility, final-answer readiness, provider/depth policy, or Author posture.

Recommended future posture: keep as bounded synthesis executor over admitted or
otherwise explicitly scoped material. Refine boundaries so any Analyst gap signal
is advisory to SearchJudgment/SufficiencyJudgment rather than self-authorizing.

### Scrutineer

Files inspected: `core/prompts.py`, `core/runtime_prompt_assembly.py`,
`core/legacy_review_runtime_stage.py`,
`core/scrutineer_remediation_handoff_contract.py`,
`core/scrutineer_remediation_runtime_handoff.py`,
`core/module_registry.py`, and
`tests/test_ag76d_scr_scrutineer_remediation_handoff_contract.py`.

Current implementation: Scrutineer is an active high-complexity legacy audit
helper that critiques Analyst prose. The prompt explicitly states that it sees
only the Analyst output, not the underlying sources. The legacy review runtime
can convert certain high-severity searchable flags into remediation queries,
then send those queries through existing novelty filtering, QueryPlan,
provider-plan, retrieval, evidence rebuilding, and Analyst rerun paths. The
Scrutineer remediation handoff contract/runtime handoff are passive
representations of already-computed facts.

Calls: the active Scrutineer path calls a model. The remediation path can lead to
search only through existing authorized runtime paths. Passive handoff helpers do
not call models, providers, search, or retrieval.

Current owner/authority posture: active legacy adversarial prose-review helper
plus passive remediation fact packaging. Its current view is too narrow for a
durable source/evidence audit because it primarily sees Analyst prose rather
than the final answer, admitted evidence, obligations, and assumptions.

Apparent intended capability: adversarial audit, red-team review, overreach
detection, temporal drift detection, single-source challenge, and remediation
signal generation.

Capability still needed: yes, especially for Deep.

Target future owner: SearchWorkPlan `audit_jobs` plus RunAuthority
follow-up/remediation authorization; EvidenceLedger, SearchJudgment,
SufficiencyJudgment, and FinalAnswerPacket remain the authority surfaces for
source/evidence/finality.

Bounded executor needed? Yes, likely redesigned as AdversarialAudit,
ClaimChallenge, or AssumptionRedTeam over final answer draft or packet posture,
admitted evidence, source obligations, assumptions, and quantitative work units.

Must not manufacture false balance, create open-ended remediation loops, admit
evidence, decide citation eligibility, override sufficiency, or own follow-up
authority.

Recommended future posture: redesign as a bounded Deep-oriented audit job. Keep
the passive handoff as compatibility until the redesign exists.

### Author

Files inspected: `core/prompts.py`, `core/runtime_prompt_assembly.py`,
`core/final_answer_packet.py`, `core/final_answer_packet_runtime.py`,
`core/final_answer_runtime_assembly.py`,
`core/author_execution_runtime.py`, `core/module_registry.py`,
`tests/test_final_answer_packet_ag89d.py`, and
`tests/test_final_answer_author_runkernel_ag91k.py`.

Current implementation: Author is an active final-expression model call
authorized through RunKernel. FinalAnswerPacket prepares the packet-derived
Author payload, including citation eligibility, missing obligations, mandatory
caveats, prohibited upgrades, and the packet authority block. AuthorExecutor
validates payload/action alignment, calls the Author model, streams or buffers
the result, applies the existing quantitative consistency guard, and reduces a
compact observation back into RunKernel.

Calls: AuthorExecutor calls a model. The packet/runtime assembly helpers package
already-computed packet and prompt data. These helpers do not call search or
retrieval and should not select evidence.

Current owner/authority posture: bounded writer/formatter consuming a
FinalAnswerPacket-derived payload. Final evidence and citation posture are owned
by the packet, not by Author prose.

Apparent intended capability: final answer expression, formatting, tone, and
user-facing synthesis of packet-authorized content.

Capability still needed: yes.

Target future owner: FinalAnswerPacket for Author-visible authority; AuthorExecutor
for bounded writing.

Bounded executor needed? Yes.

Must not rebuild evidence authority, select citations independently, fill missing
source obligations, upgrade unsupported claims, become a hidden Analyst, or
become a hidden RunKernel.

Recommended future posture: keep as bounded writer/formatter behind
FinalAnswerPacket and RunKernel authorization.

### Adjacent answer-contract and final-answer helpers

Files inspected: `core/answer_contract_pipeline_adapter.py`,
`core/final_answer_packet.py`, `core/final_answer_packet_runtime.py`,
`core/final_answer_runtime_assembly.py`, `core/author_execution_runtime.py`,
`core/runtime_prompt_assembly.py`,
`tests/test_final_answer_packet_ag89d.py`, and
`tests/test_final_answer_author_runkernel_ag91k.py`.

Current implementation: answer-contract and final-answer helpers mostly package,
adapt, or reduce already-computed facts. `answer_contract_pipeline_adapter.py`
is passive and offline. `final_answer_runtime_assembly.py` is a bounded adapter
from already-computed runtime facts into FinalAnswerPacket/Author payloads.
`author_execution_runtime.py` is the bounded active AuthorExecutor call.

Calls: answer-contract and packet assembly helpers do not call models, search,
or retrieval. AuthorExecutor calls a model after RunKernel authorization.

Current owner/authority posture: FinalAnswerPacket is the canonical final
evidence/citation/posture packet; AuthorExecutor is bounded execution. Adjacent
adapters should stay mechanical.

Apparent intended capability: final answer readiness packaging, Author handoff,
citation eligibility projection, and post-Author observation.

Capability still needed: yes.

Target future owner: FinalAnswerPacket and RunKernel.AuthorExecutor.

Bounded executor needed? Yes for Author execution; no for passive adapters.

Must not become hidden evidence selectors, prompt-era policy owners, citation
authorities, or final-readiness authorities outside the packet/judgment chain.

Recommended future posture: keep packet and AuthorExecutor; keep adapters
mechanical and subordinate.

## 5. Required audit conclusions

| Unit | Audit conclusion |
| --- | --- |
| Scout | Confirmed with refinement: the named Scout agent/executor is likely obsolete, but the scout job remains important as disambiguation, query shaping, and component discovery. Future home should be SearchWorkPlan/RunKernel job labels and QueryPlan-style admission, not a separate authority-owning Scout. |
| Economist | Confirmed with refinement: quantitative capability remains important. Future posture should be QuantWorkUnit / QuantPlanner / QuantValidator subordinate to component plans and source-bound evidence. It must not fabricate values, bypass Analyst/Author, execute arbitrary code, or become final numeric/evidence authority. |
| Analyst | Confirmed: synthesis capability remains important. Analyst should remain a bounded synthesis worker over available/admitted material. It may surface candidate gaps, but SearchJudgment, SufficiencyJudgment, and RunAuthority must authorize follow-up and final readiness. |
| Scrutineer | Confirmed with concern: adversarial audit remains important, especially for Deep, but the current Scrutineer mostly sees Analyst prose. Future posture should be AdversarialAudit / ClaimChallenge / AssumptionRedTeam over the answer, admitted evidence, obligations, assumptions, and quantitative work units, without false balance or unbounded remediation authority. |
| Author | Confirmed: final expression remains important. Author should be a bounded writer/formatter consuming FinalAnswerPacket-derived posture. It must not rebuild evidence authority, independently select citations, fill missing obligations, or become hidden Analyst/RunKernel. |

## 6. Authority map

| Capability | Legacy unit(s) | Current posture | Durable owner | Bounded executor needed? | Future action |
| --- | --- | --- | --- | --- | --- |
| Query-shape / disambiguation | Scout, Researcher, recon rewriter | Active candidate helpers; QueryPlan admission owns query order | SearchWorkPlan query_shape and QueryPlan/RunKernel admission | Yes, as candidate worker | Fold named jobs into SearchWorkPlan |
| Component decomposition | Expander, Scout | Active continuation-query helpers | SearchWorkPlan components | Possibly | Replace prompt-era component discovery with planned components |
| SearchWorkPlan construction | Researcher, QueryPlan, RunPlan doctrine | Not implemented as runtime class; QueryPlan and RunPlan cover partial passive/active pieces | RunKernel / SearchWorkPlan | No separate agent | Design passive SearchWorkPlan contract first |
| Quantitative planning/math | Economist | Active model helper plus passive handoff; code execution blocked | SearchWorkPlan quant_work_units and EvidenceLedger source-bound custody | Yes | Redesign as QuantWorkUnit / QuantPlanner / QuantValidator |
| Evidence synthesis | Analyst, synthesis evaluator | Active Analyst model worker; synthesis evaluator is legacy QA/follow-up signal | SearchWorkPlan synthesis_jobs, bounded Analyst worker | Yes | Keep Analyst bounded; demote synthesis evaluator to advisory job |
| Sufficiency/gap judgment | Evaluator, Expander, synthesis evaluator, Analyst signals | Legacy helpers propose gaps/queries; canonical judgments exist | SearchJudgment / SufficiencyJudgment | Advisory gap workers only | Move decisions to canonical judgments |
| Follow-up/remediation authorization | Evaluator, Expander, synthesis evaluator, Scrutineer | Active legacy paths gated by QueryPlan/retrieval-stop/runtime stages | RunAuthority / SearchJudgment / SearchWorkPlan follow_up_authority | No authority-owning executor | Make helpers propose only; judgments authorize |
| Adversarial audit | Scrutineer | Active high-complexity prose audit; passive remediation handoff | SearchWorkPlan audit_jobs plus canonical judgments | Yes | Redesign as Deep-oriented bounded audit over evidence/obligations |
| Final writing | Author | RunKernel-authorized AuthorExecutor consumes packet payload | FinalAnswerPacket / AuthorExecutor | Yes | Keep bounded writer |
| Citation/evidence eligibility | Author prompt, final answer helpers, legacy evidence bundle | Packet now owns citation eligibility and missing obligations | EvidenceLedger / FinalAnswerPacket | No | Keep Author from selecting citations independently |

## 7. SearchWorkPlan integration target

The future design target is a passive, canonical work-plan contract. This audit
does not implement it.

```text
SearchWorkPlan:
  mode_contract
  query_shape
  components
  source_obligations
  provider_jobs
  quant_work_units
  synthesis_jobs
  audit_jobs
  per_component_budget
  global_budget
  follow_up_authority
  stop/escalate/refuse_conditions
```

Integration target:

- `mode_contract` inherits depth, follow-up authority, and budget shape from
  RunAuthorityContract.
- `query_shape` captures ambiguity, entity identity, time sensitivity, numeric
  shape, official/current need, and likely component count.
- `components` define breadth. Components, not mode names, should explain why
  multiple searches or source classes are needed.
- `source_obligations` declare official/current, primary/legal, academic,
  source-bound numeric, conflict, and caveat requirements.
- `provider_jobs` select candidate acquisition jobs such as direct official
  candidate search, semantic recall, bridge answer/deep context, fetch/read, or
  canonical extraction. Provider names are subordinate to jobs.
- `quant_work_units` define source-bound numeric extraction, assumptions,
  calculation requests, deterministic validation, and unsupported-value handling.
- `synthesis_jobs` define bounded synthesis tasks over admitted or explicitly
  scoped material.
- `audit_jobs` define bounded adversarial/claim-challenge work, likely most
  important for Deep.
- `per_component_budget` and `global_budget` encode budget shape without letting
  providers or helpers invent their own run policy.
- `follow_up_authority` declares who may continue, under which gaps, and with
  which caps.
- `stop/escalate/refuse_conditions` make insufficient evidence, missing official
  custody, source-bound numeric unknowns, conflict, and refusal conditions
  explicit before Author execution.

Existing Scout, Researcher, Expander, Evaluator, Economist, Analyst,
Scrutineer, and Author labels should map into these fields as jobs or bounded
executors. They should not survive as a zoo of peer authorities.

## 8. Anti-patterns to avoid

- Preserving legacy names as sacred architecture.
- Creating a zoo of separate agents with overlapping authority.
- Scout as a separate query brain when RunKernel/SearchWorkPlan should plan
  queries.
- Analyst as source-gap, search, remediation, or final-readiness authority.
- Economist as final numeric answer authority.
- Scrutineer as open-ended adversarial agent or unlimited remediation loop.
- Author as hidden evidence selector.
- Mode-specific official executors.
- Provider identity as a proxy for evidence authority.
- Bridge-source output becoming final/citation evidence without canonical
  fetch/read/admission.
- `pipeline_orchestrator.py` as a new domain brain.

## 9. Recommended next phases

1. SearchWorkPlan data model / passive contract design.
2. Query-shape and contract-resolution design.
3. QuantWorkUnit source-bound math design.
4. Analyst/Author authority boundary refinement.
5. Scrutineer redesign for Deep-only adversarial audit.
6. Official-source validation under shared SearchWorkPlan.
7. Runtime implementation only after the relevant passive design is accepted.

## 10. Known limitations

This audit does not:

- prove official source search resilience;
- implement SearchWorkPlan;
- change `mode_policy.py`;
- change prompts;
- run live calls;
- run provider/model/search evaluations;
- decide provider selection;
- rename package, CLI, or environment names;
- retire old stages at runtime;
- change `core/pipeline_orchestrator.py`;
- delete or rewrite historical docs.

## 11. Files inspected

Primary doctrine and phase guidance inspected:
`docs/architecture/AG96C0_MODE_CONTRACT_COMPONENT_BUDGET_DOCTRINE.md`,
`docs/architecture/AG96B0_OFFICIAL_SEARCH_STACK_DOCTRINE.md`,
`docs/architecture/AG90_POST_BURNDOWN_CURRENT_STATE.md`,
`docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md`,
`docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`, and
`docs/codex/PHASE_BRIEF_TEMPLATE.md`.

Primary runtime/static surfaces inspected: `core/scout.py`, `core/prompts.py`,
`core/pipeline.py`, `core/pipeline_orchestrator.py`, `core/run_plan.py`,
`core/module_registry.py`, `core/query_production_runtime.py`,
`core/query_plan.py`, `core/query_plan_runtime_adapter.py`,
`core/run_kernel.py`, `core/run_authority_contract.py`,
`core/evidence_ledger.py`, `core/run_authority_search_judgment.py`,
`core/run_authority_sufficiency.py`, `core/analyst_runtime_stage.py`,
`core/economist_handoff_contract.py`,
`core/legacy_review_runtime_stage.py`,
`core/synthesis_evaluator_supplemental_search_handoff_contract.py`,
`core/synthesis_evaluator_supplemental_search_runtime_handoff.py`,
`core/scrutineer_remediation_handoff_contract.py`,
`core/scrutineer_remediation_runtime_handoff.py`,
`core/final_answer_packet.py`, `core/final_answer_packet_runtime.py`,
`core/final_answer_runtime_assembly.py`,
`core/author_execution_runtime.py`, `core/runtime_prompt_assembly.py`, and
`core/answer_contract_pipeline_adapter.py`.

Relevant tests inspected: `tests/test_scout.py`,
`tests/test_scout_continuation_spine_gate_ag45c.py`,
`tests/test_evaluator_continuation_spine_gate_ag44c.py`,
`tests/test_query_production_ag91i.py`,
`tests/test_ag76d_ses_synthesis_evaluator_supplemental_search_handoff_contract.py`,
`tests/test_ag76d_eco_controller_owned_economist_handoff_contract.py`,
`tests/test_economist_static_code_execution_guard.py`,
`tests/test_ag90f_analyst_runtime_stage.py`,
`tests/test_ag76d_scr_scrutineer_remediation_handoff_contract.py`,
`tests/test_final_answer_packet_ag89d.py`,
`tests/test_final_answer_author_runkernel_ag91k.py`,
`tests/test_run_plan.py`, and `tests/test_module_registry.py`.
