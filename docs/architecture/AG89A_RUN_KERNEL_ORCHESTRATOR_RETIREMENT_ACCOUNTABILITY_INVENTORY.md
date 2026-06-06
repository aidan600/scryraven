# AG-89A Run Kernel / Orchestrator Retirement + Accountability Inventory

Status: architecture inventory / migration charter; docs-only; no runtime behavior change; no live validation

Branch: `ag-89a-run-kernel-accountability-inventory`

## 1. Purpose and non-goals

AG-89A creates a repo-visible migration charter for moving ScryRaven from `core/pipeline_orchestrator.py` plus Controller-shaped oversight toward a RunAuthority / RunKernel state machine with bounded executors, canonical RunState, Evidence Ledger custody, and trace derived from authoritative state.

The core thesis is deliberately narrower than "make the Controller bigger":

> The problem is not orchestrator versus Controller. The target is no orchestrator brain: one accountable RunAuthority state machine, bounded executors, canonical state transitions, and trace derived from state.

AG-89A exists to make AG-89B/C/D/E hard to fake. It inventories answer-shaping authority, duplicate owners, fossilized authority, and trace-like mirrors before implementation phases are allowed to add or move behavior.

Non-goals and closed surfaces for this phase:

- AG-89A does not implement runtime behavior.
- AG-89A does not change prompts, provider/search behavior, retrieval ranking/filtering, Author behavior, cache behavior, ProjectSource retrieval, or orchestrator runtime logic.
- AG-89A does not change query generation/finalization behavior, citation behavior, Controller/AnswerContract runtime shape, or model/provider selection.
- AG-89A does not add new passive handoff contracts.
- AG-89A does not add trace-only wrappers.
- AG-89A does not add telemetry unless it directly supports a deletion/elevation decision. This document adds none.
- AG-89A does not run live validation, provider calls, model calls, or search calls.

## 2. Target RunKernel / RunAuthority model

Target plain-language model:

- **RunAuthority owns lifecycle, contract state, next authorized action, state reduction, and final outcome.** It is the only component that may decide what action happens next, whether a requirement is satisfied, whether evidence is sufficient, whether the run may stop, and what final packet is ready for Author consumption.
- **Executors perform one bounded authorized action and return observations/artifacts.** An executor may search, fetch, embed, rank within a delegated primitive, evaluate a bounded packet, format a compatibility payload, or call an existing provider only when the authorized action permits it.
- **Executors do not decide next action, sufficiency, citation eligibility, final evidence, final posture, or Author instructions.** Those decisions must be recorded as RunAuthority decisions over canonical state.
- **`run_pipeline(...)` remains temporarily as a compatibility shell.** During migration, it may continue to host old callsites and adapters, but the target shape is that it dispatches authorized actions and reduces observations, not that it owns answer policy.
- **The retired orchestrator owns no lifecycle policy, query mutation, source custody, evidence selection, citation eligibility, final-answer posture, or Author instructions.** Remaining orchestrator-local branches must either become bounded executor logic, be bypassed by an authoritative packet, or be deleted/demoted.
- **Trace/projection/export serializes canonical state and must not become a second policy layer.** Trace is evidence for review; it is not an alternate decision engine.

## 3. Small shared vocabulary for AG-89B/C

This vocabulary is intentionally small. It is not a framework cathedral for every future lane.

- **RunState** — the canonical, append/reduce state for a run: request identity, current contract obligations, authoritative query/source/evidence/citation/final-packet records, budget state, current status, and final outcome. Trace must be a projection of this state where possible.
- **RunAuthority decision** — an accountable state transition that records the decision value, decision reason, required inputs, affected state fields, and next authorized action or terminal posture.
- **AuthorizedAction** — one bounded action the RunAuthority permits an executor to perform. It names the action type, scope, inputs, budget/provider permissions, expected observation shape, and stop/return condition.
- **Observation** — the executor's returned facts/artifacts from one authorized action. Observations may contain candidates, errors, unreadability, result identities, counts, snippets, costs, and timing, but they do not decide next action.
- **DecisionReason** — durable reason vocabulary explaining why a transition happened: for example `required_official_current_source_missing`, `candidate_identity_missing`, `budget_exhausted`, `requirement_satisfied`, or `stop_insufficient_authorized`.
- **EvidenceLedger / CustodyRecord** — authoritative custody record for source/evidence candidates and requirements. It records candidate identity, requirement linkage, disposition, rejection/drop reason, observation references, and whether aggregate-only information is insufficient for custody.
- **FinalPacket readiness** — authoritative declaration that the run has enough final evidence, citation eligibility, posture, caveats, and Author inputs to produce the final answer, or that insufficiency/failure posture is authorized.

## 4. Definition of governing

A surface is **governing** if changing it can alter any of the following:

- what action happens next;
- query/source identity;
- what evidence enters the answer;
- whether evidence is sufficient;
- which citations are eligible;
- what confidence/posture/caveat is allowed;
- what Author is instructed to say;
- final answer posture.

Controller-visible, trace-visible, prompt-visible, and governing are different categories:

- A Controller-visible surface may expose a decision or handoff without owning it.
- A trace-visible surface may be review evidence only.
- A prompt-visible surface can shape output even if it is not represented as Controller state.
- A governing surface changes answer outcomes and therefore needs a single accountable owner.

## 5. Answer-shaping decision inventory owner/collapse matrix

Classification vocabulary:

- **governing** — currently able to alter answer-shaping outcomes.
- **adapter** — behavior-preserving bridge that should not decide policy.
- **trace-only** — observer/projection/export; should not govern runtime behavior.
- **prompt-only** — prompt/prose semantics that govern by instruction text rather than canonical state.
- **fossilized** — old logic still governing because earlier phases protected it, not because it is the desired long-term owner.
- **unknown-with-evidence** — evidence exists, but repo inspection was insufficient to classify ownership confidently without implementation or forbidden live/private data.

| Decision surface | Current governing owner | Desired owner | Duplicate owners or mirrors | Code/doc surface | Protected status | Current behavior class | Target action | First implementation phase | Parity risk | Stop condition or needed follow-up evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| user intent / routing | Router model plus orchestrator runtime overrides | RunAuthority-owned request/route state reduced from router observation | Router query-preparation contract mirrors runtime posture | `core/pipeline_orchestrator.py` pre-retrieval routing; `core/router_query_preparation_contract.py`; AG-79D protected legacy list | Protected high-custody route behavior | governing | collapse | AG-89C | High: route changes alter retrieval and prompts | Need fixture parity for router output, retry, nutrition override, academic/news overrides |
| query generation | Researcher prompt or recon-rewritten query branch | Authoritative QueryPlan action and observation | Router query contract stores finalized/current queries | `core/pipeline_orchestrator.py` researcher/recon branches; AG-76D-RQ | Protected prompt/provider behavior | governing / prompt-only | collapse | AG-89C | High: search identity changes | Need offline fixtures proving same generated query list is admitted to QueryPlan without changing prompts |
| query finalization | Local `_finalize_retrieval_queries` wrapper over `finalize_retrieval_queries` | Authoritative QueryPlan reducer | Router query-preparation runtime posture mirrors `finalized_queries`/`current_queries` | `core/pipeline_orchestrator.py`; `core/query_planning.py` | Protected legacy query behavior | fossilized governing | collapse | AG-89C | High: de-dupe/anchor/max truncation affect sources | Need split fixtures for anchoring, de-dupe, official bias, max length |
| recon rewrite | Brave recon plus recon rewriter prompt mutates initial query identity and canonical subject | QueryPlan authority with recon as bounded observation/action | Provider diagnostics and router-query trace observe it | `core/pipeline_orchestrator.py`; AG-79D protected legacy | Protected legacy behavior | fossilized governing / prompt-only | collapse | AG-89C | High: entity/query identity changes | Need no-live fixture replaying recon observation into same rewritten queries |
| entity correction / disambiguation retry | Recon canonical subject, entity list mutation, low-utilization disambiguation retry | QueryPlan authority plus retrieval-continuation decision | Disambiguation query telemetry and retrieval stop/continuation traces observe | `core/pipeline_orchestrator.py`; `core/query_planning.py`; AG-79D | Protected legacy behavior | fossilized governing | collapse | AG-89C | High: changes target subject and retry admission | Need fixture for canonical-subject insertion and retry query identity |
| recency merge | Orchestrator local merge prepends year/news query | QueryPlan authority | Router query-preparation contract mirrors `recency_merge_used` and `recency_query` | `core/pipeline_orchestrator.py`; `core/query_planning.py`; AG-79D | Protected legacy behavior | fossilized governing | collapse | AG-89C | Medium-high: query ordering/source freshness changes | Need fixture for `should_merge_recency_queries`, year extraction, ordering |
| official-bias insertion | `finalize_retrieval_queries` / `official_bias_phrase` from query-planning utilities | QueryPlan authority, with source-obligation requirement owned by RunAuthority | Router query-preparation contract observes `official_bias_requested`; source obligation bridge observes later | `core/pipeline_orchestrator.py`; `core/query_planning.py`; `core/official_source_obligation_bridge.py` | Protected legacy behavior | fossilized governing | collapse | AG-89C, seeded by AG-89B | High: official source acquisition path changes | Need separate custody requirement from query-string bias; do not let aggregate counts satisfy custody |
| query ordering | Orchestrator list ordering after recon/researcher/finalization/recency/continuation | QueryPlan authority | `queries_by_iteration`, router query contract, trace wrappers | `core/pipeline_orchestrator.py` | Protected legacy behavior | fossilized governing | collapse | AG-89C | Medium-high: provider result set changes | Need ordered QueryPlan fixtures per route/iteration |
| provider plan / search depth | Orchestrator strategy/complexity config and `choose_retrieval_search_depth`; some Controller handoffs expose boundaries | RunAuthority budget/provider authorization, QueryPlan input where query-related | Targeted retrieval lifecycle marks provider/search-depth boundaries as orchestrator-owned | `core/pipeline_orchestrator.py`; AG-79B/AG-79D targeted retrieval docs | Protected where no Controller handoff supplies it | fossilized governing | collapse | AG-89C / later | High: provider calls and depth alter corpus | Need exact map of provider/depth callsites before activation; no provider calls in charter |
| retrieval continuation | Controller continuation gates for scout/expander/evaluator ordinary branches, with orchestrator scheduling | RunAuthority next-action decision | Loop-spine traces and ordinary continuation candidates mirror | `core/pipeline_orchestrator.py`; AG-76D-RL; AG-79D | Partly transferred, behavior-preserving | governing / adapter | keep-with-reason | later | Medium: continuation can alter actions | Keep only until RunAuthority state machine absorbs loop; retirement trigger is canonical AuthorizedAction scheduler |
| recovery admission | Controller recovery decisions and orchestrator execution/admission branches | RunAuthority recovery AuthorizedAction | Recovery lifecycle traces, execution-admission traces | `core/pipeline_orchestrator.py`; source-class/weak/conflict lifecycle modules | Partly transferred | governing / adapter | collapse | AG-89B / AG-89E | Medium-high | Need ensure admission is not duplicated by source-specific branches after custody state exists |
| source-class recovery | Controller/source-class recovery lifecycle plus executor, orchestrator plumbing | RunAuthority action with EvidenceLedger requirement linkage | Source-class recommendation/checkpoint traces | `core/source_class_recovery_lifecycle.py`; `core/source_class_recovery_executor.py`; `core/pipeline_orchestrator.py` | Partly active Controller-owned seam | governing / adapter | keep-with-reason | AG-89B / later | Medium | True executor-like acquisition can stay; retirement trigger is ledger custody replacing aggregate-only summaries |
| official/current source custody | Aggregate retrieval summaries, source-class recovery traces, AnswerContract/source-obligation bridge; no durable candidate custody for all misses | RunAuthority EvidenceLedger / CustodyRecord | Official-source bridge, source-fit telemetry, provider diagnostics, validation summaries | `core/official_source_obligation_bridge.py`; `core/pipeline_orchestrator.py`; AG-71A; AG-82B | High-custody, not permanent | unknown-with-evidence / fossilized governing | collapse | AG-89B | High: final answer can cite/omit official source | Need per-candidate identity/disposition; aggregate counts cannot satisfy custody |
| weak-corpus gate | Controller weak-failure gate plus corpus heuristics/utilization in orchestrator | RunAuthority sufficiency/stop decision | Weak-corpus lifecycle traces and AnswerContract handoff | `core/pipeline_orchestrator.py`; AG-76D-WG; AG-79D | Partly transferred | governing | collapse | AG-89D / AG-89E | High: final posture and retry/stop change | Need prove one sufficiency owner; no duplicate author caveats from trace |
| conflict posture | Controller conflict arbitration for conflict labels/posture with runtime evidence state | FinalAnswerPacket authority | Conflict state projection and AnswerContract mirror | `core/pipeline_orchestrator.py`; AG-77B/C/D; AG-79D | Partly transferred | governing | collapse | AG-89D | High: caveats/final posture | Need final packet fixture for direct conflict claims and citation-bound conflict evidence |
| indirect-inference posture | Minimal indirect-inference contract and Author presentation posture | FinalAnswerPacket authority | AnswerContract/Author notes mirror | AG-78B/C/D/E/F docs; `core/pipeline_orchestrator.py` | Partly transferred | governing / prompt-only | collapse | AG-89D | Medium-high | Need packet records claim posture and mandatory caveats before Author prompt |
| retrieval ranking/filtering | Orchestrator/evidence utilities choose top chunks, utilization, diverse top evidence | EvidenceLedger observations plus FinalAnswerPacket final evidence selector | Final evidence bundle and registry mirror observe | `core/pipeline_orchestrator.py`; `core/final_evidence_bundle_builder.py`; AG-79D | Protected legacy behavior | fossilized governing | collapse | AG-89D | High: evidence entering answer changes | Need deterministic fixture freezing final evidence input/output before moving owner |
| final evidence selection | Final evidence bundle builder and orchestrator refresh after remediation | FinalAnswerPacket authority | Evidence registry mirror, citation handoff, Analyst/Author handoffs | `core/final_evidence_bundle_builder.py`; `core/evidence_registry_mirror.py`; `core/pipeline_orchestrator.py`; AG-76C-FE | Protected selection behavior, Controller-visible identity | fossilized governing | collapse | AG-89D | High | Need single final packet to replace bundle + registry + handoff mirrors |
| citation eligibility | Citation/source handoff identity plus legacy final evidence/source filtering | FinalAnswerPacket authority | Citation-source handoff trace and Author evidence block | `core/citation_source_handoff_contract.py`; `core/pipeline_orchestrator.py`; AG-76D-CIT | Partly Controller-visible; behavior protected | governing / adapter | collapse | AG-89D | High: citations and source list change | Need fixture for eligible source IDs and rejected evidence reasons |
| citation formatting | Author prompt/source list and citation helpers | FinalAnswerPacket for eligibility; Author executor for formatting only | Citation telemetry/export observes | `core/pipeline_orchestrator.py`; citation utilities | Protected product behavior | fossilized governing / prompt-only | demote | AG-89D | Medium | Need distinguish eligibility from display formatting; formatting can remain executor if no eligibility policy |
| Analyst handoff | Analyst prompt/path and Controller-owned handoff identity | FinalAnswerPacket / analysis action under RunAuthority | Analyst/Author handoff contracts mirror refs | `core/pipeline_orchestrator.py`; AG-76D-AA | Protected prompt behavior, Controller-visible identity | governing / prompt-only | collapse | AG-89D | Medium-high | Need packet that decides analysis inputs; prompt text remains closed unless later licensed |
| Author posture/prose | Orchestrator-built Author prompt, notes, tier instructions, scrutineer block, recency notes | FinalAnswerPacket for posture/caveats/inputs; Author as prose executor | AnswerContract/Author handoff mirrors | `core/pipeline_orchestrator.py`; AG-78E; AG-79D | Protected prompt/prose behavior | prompt-only governing / fossilized | collapse | AG-89D | High: final answer changes | Need final packet parity: same instructions emitted from packet without prompt text changes |
| failure/insufficiency posture | Weak/failure gates, pre-analyst gates, Author notes, Controller stop decisions | RunAuthority terminal state + FinalAnswerPacket insufficiency posture | AnswerContract and trace flags observe | `core/pipeline_orchestrator.py`; AG-59AB; AG-76D-WG | Partly transferred | governing | collapse | AG-89D | High | Need one terminal insufficiency owner and fixture for Author obedience |
| follow-up source obligations | Follow-up source obligation initial state and bridge | RunAuthority requirement state | AnswerContract/source obligation bridge mirrors | AG-76D-FU; `core/official_source_obligation_bridge.py`; `core/pipeline_orchestrator.py` | Partly transferred | governing / adapter | collapse | AG-89B / AG-89D | Medium-high | Need ledger linkage from obligation to candidate custody and final packet |
| Scrutineer/remediation behavior | Orchestrator calls Scrutineer, may authorize remediation search and resynthesis | RunAuthority action; Scrutineer executor returns observation only | Scrutineer runtime handoff traces observe identity | `core/pipeline_orchestrator.py`; `core/scrutineer_remediation_runtime_handoff.py`; AG-76D-SCR | Runtime protected beyond trace identity | fossilized governing / prompt-only | collapse | AG-89D / AG-89E | High: can add evidence and change Author directives | Need split remediation search admission, evidence addition, and Author caveats into final packet decisions |
| synthesis-evaluator supplemental-search behavior | Orchestrator synthesis evaluator can trigger supplemental search | RunAuthority action and QueryPlan continuation | Supplemental-search runtime handoff traces observe identity | `core/pipeline_orchestrator.py`; `core/synthesis_evaluator_supplemental_search_runtime_handoff.py`; AG-76D-SES | Runtime protected beyond trace identity | fossilized governing | collapse | AG-89C / AG-89E | High: can add sources and affect sufficiency | Need authoritative next-action record for supplemental queries and stop reasons |
| trace/projection/export wrappers | Trace/projection/export helpers assemble runtime facts and compatibility payloads | Projection from canonical RunState | Many handoff fragments and aggregate diagnostics can be mistaken for authority | `core/pipeline_orchestrator.py`; AG-76C-DP/RT/OP; AG-79D | Trace-only unless explicitly consumed | trace-only / adapter | delete / demote | AG-89E | Low if after B/C/D; high if deleted before authority exists | Need classify each trace key as state-derived, independent aggregate, or authority candidate |

## 6. Duplicate-owner map

Duplicate-owner clusters are places where more than one surface can shape the same answer outcome or make a later surface appear authoritative even though another component already decided.

### Query identity cluster

- **Currently decides:** router model output, orchestrator overrides, recon rewriter, researcher prompt, `_finalize_retrieval_queries`, recency merge, disambiguation retry, and continuation/supplemental query branches.
- **Observes:** router query-preparation contract, `queries_by_iteration`, provider diagnostics, targeted retrieval traces.
- **Can override later:** recency merge can reorder; disambiguation retry can add/replace; synthesis evaluator and Scrutineer remediation can add supplemental/novel queries; recovery branches can add source-class queries.
- **Owner that should disappear first:** local query finalization/recency/official-bias authority should disappear into QueryPlan first because it is deterministic and fixtureable; prompt/model query generation can then be represented as observations without prompt changes.
- **Phase:** AG-89C, with AG-89B separating source-custody requirements from official-bias query text.

### Official/current source custody cluster

- **Currently decides:** scattered source-fit/source-class logic, aggregate provider/recovery summaries, final evidence selection, citation eligibility, and AnswerContract/source-obligation bridge posture.
- **Observes:** provider diagnostics, official-source obligation bridge trace, source-class recovery traces, validation docs, final-source telemetry.
- **Can override later:** final evidence selection can drop the candidate; citation eligibility can make it invisible; Author/failure posture can caveat or omit the obligation.
- **Owner that should disappear first:** aggregate-only custody summaries must be demoted first; a required official/current source must become a RunAuthority custody requirement with per-candidate records.
- **Phase:** AG-89B.

### Evidence sufficiency / stop / recovery cluster

- **Currently decides:** Controller continuation gates, weak/failure gates, conflict lifecycle, source-class recovery lifecycle, synthesis evaluator, and orchestrator stop/retry loops.
- **Observes:** retrieval stop shadow/active telemetry, evidence integration checkpoint, loop-spine traces, AnswerContract.
- **Can override later:** Scrutineer remediation and supplemental search can reopen evidence acquisition; Author prompt can still change caveat posture.
- **Owner that should disappear first:** trace/shadow stop mirrors should be demoted after one RunAuthority next-action state exists; legacy stop/retry branches should then become action dispatch only.
- **Phase:** AG-89D for final sufficiency/posture, AG-89E for wrapper collapse.

### Final answer posture / Author instruction cluster

- **Currently decides:** AnswerContract handoff, final evidence bundle, recency author notes, weak/failure gates, conflict/indirect-inference posture, Scrutineer block, and orchestrator tier instructions.
- **Observes:** Analyst/Author handoff contracts, citation-source handoff, final evidence registry mirror, trace/export wrappers.
- **Can override later:** Author prompt assembly can override state posture through direct instructions even when the Controller-visible state says something else.
- **Owner that should disappear first:** final evidence selection/citation eligibility must collapse into a FinalAnswerPacket before prompt prose is touched; otherwise prompt-visible behavior becomes the accidental authority.
- **Phase:** AG-89D.

### Trace / diagnostic / export cluster

- **Currently decides:** should decide nothing, but independent aggregate diagnostics can be mistaken for policy inputs when no canonical state owns the same fact.
- **Observes:** almost every lifecycle and handoff.
- **Can override later:** any future implementation that reads aggregate trace as state would create hidden authority.
- **Owner that should disappear first:** independent aggregate diagnostics that duplicate custody/query/evidence decisions should be folded into canonical state projection after B/C/D.
- **Phase:** AG-89E.

## 7. Fossilized-authority map

Fossilized authority means old logic still governs because it was protected during earlier phases, not because it is the desired long-term owner. Protected means high-custody, not permanent.

| Fossilized or suspected-fossilized surface | Why it is fossilized | Desired retirement path | Phase |
| --- | --- | --- | --- |
| recon rewrite | It mutates query identity/canonical subject while earlier phases protected prompt/provider behavior. | Treat recon search/model output as observations; QueryPlan reducer admits rewritten queries. | AG-89C |
| disambiguation/entity correction | It changes target entity and retry queries outside one QueryPlan owner. | QueryPlan owns canonical entity correction and disambiguation retry identity. | AG-89C |
| query finalization | Anchoring, de-dupe, official bias, and max truncation govern retrieval but remain local. | Move deterministic finalization into authoritative QueryPlan with fixtures. | AG-89C |
| recency merge | Local date/news query insertion controls freshness and ordering. | QueryPlan owns recency requirement/query mutation. | AG-89C |
| official bias insertion | Query text bias stands in for source-obligation custody. | AG-89B creates custody requirement; AG-89C moves bias into QueryPlan input. | AG-89B/C |
| query ordering | Ordering is produced by multiple branches and controls provider results. | QueryPlan records ordered authorized queries per iteration. | AG-89C |
| provider/depth choices where no Controller-owned handoff supplies them | Strategy/complexity/local helper choices still govern acquisition. | RunAuthority budget/provider authorization; QueryPlan supplies query-related provider inputs only where appropriate. | AG-89C/later |
| retrieval ranking/filtering | Top evidence and utilization filtering determine answer evidence. | EvidenceLedger observations plus FinalAnswerPacket selector. | AG-89D |
| final evidence selection | Bundle builder and orchestrator refresh after remediation decide final evidence. | FinalAnswerPacket owns final evidence and readiness. | AG-89D |
| citation formatting | Prompt/source-list formatting can blur eligibility and display. | Demote display formatting to executor; keep eligibility in FinalAnswerPacket. | AG-89D |
| prompt semantics | Prompt text can govern posture without canonical state. | FinalAnswerPacket emits mandatory posture/caveats; prompt remains prose executor input. | AG-89D |
| Author notes/prose | Recency, weak-corpus, quant, Scrutineer, and tier notes shape final answer. | Convert governing notes into FinalAnswerPacket fields; Author writes from packet. | AG-89D |
| Scrutineer/remediation behavior beyond trace identity | Remediation can add queries/evidence and alter Author directives. | RunAuthority authorizes remediation action; FinalAnswerPacket owns resulting posture. | AG-89D/E |
| synthesis-evaluator supplemental-search behavior beyond trace identity | Supplemental search can extend retrieval and evidence. | RunAuthority action plus QueryPlan continuation. | AG-89C/E |

## 8. Keep-with-reason rule

A `keep-with-reason` row is allowed only when the row identifies one of the following and gives a retirement trigger:

- **true executor logic** — the surface performs a bounded action and does not decide policy;
- **intentionally retained compatibility behavior** — the behavior remains temporarily so `run_pipeline(...)` can be a compatibility shell;
- **user-visible product behavior not ready to move** — the behavior is known to affect output and is protected until a parity packet exists;
- **unknown because code ownership could not be confidently mapped** — only allowed with concrete missing evidence.

Rows currently marked keep-with-reason:

- **Retrieval continuation:** intentionally retained compatibility behavior. It is partly Controller-owned today, but the orchestrator still schedules branches. Retirement trigger: canonical RunAuthority AuthorizedAction scheduler exists and traces are emitted from RunState rather than loop-spine/shadow mirrors.
- **Source-class recovery:** true executor-like acquisition plus compatibility behavior. The executor can remain only if it performs bounded acquisition/classification and returns observations; aggregate summaries must retire when AG-89B EvidenceLedger custody records exist.

`future review` is not a valid permanent parking label. Every retained surface must either become true executor logic, be explicitly represented in canonical state, or be scheduled for deletion/demotion/bypass.

## 9. Trace-derived-from-state classification

Migration rule:

> Trace must be emitted from canonical state records, not reconstructed from separate aggregate diagnostics when the authority needs to act on it.

Trace-like surfaces inspected in this charter:

| Trace / trace-like surface | Classification today | Risk | Migration action |
| --- | --- | --- | --- |
| Router query-preparation contract runtime posture | Assembled from runtime facts after decisions | Can be mistaken for query authority because it records finalized/current queries | Elevate/collapse into QueryPlan authority in AG-89C |
| Provider diagnostics | Independent observation/aggregate diagnostics | Aggregate counts can masquerade as source custody | Keep as executor observations; custody decisions must reference candidate IDs in AG-89B |
| Official-source obligation bridge trace | Adapter/trace over source obligations and evidence facts | Can imply obligation satisfaction without candidate custody | Elevate required official/current source into EvidenceLedger in AG-89B; bridge becomes projection |
| Retrieval stop shadow/active telemetry | Partly Controller-derived, partly runtime shadow | Duplicate stop authority/mirror risk | Fold into RunState next-action decisions after RunAuthority loop exists |
| Ordinary continuation candidate trace | Runtime candidate assembled separately | Can look like an authorized action | Replace with AuthorizedAction record or delete in AG-89E |
| Targeted retrieval lifecycle trace | Built from runtime/controller facts | Contains provider/depth boundary notes that may be mistaken for policy | Fold boundary facts into RunState; delete observer-only wrappers in AG-89E |
| Evidence integration checkpoint trace | Handoff/checkpoint assembled from evidence state | Can duplicate sufficiency/recovery decisions | Collapse into FinalAnswerPacket readiness and RunAuthority recovery decisions |
| Source-class/weak/conflict lifecycle traces | Mixed Controller-owned decisions and runtime facts | Some are real authority, some are mirrors | Preserve only decisions as RunState; observations go to ledger; wrappers fold in AG-89E |
| Final evidence registry mirror | Mirror of final evidence identity | Can be mistaken for selector | Delete/demote after FinalAnswerPacket owns final evidence |
| Citation-source handoff trace | Controller-visible identity plus legacy behavior | Mirrors eligibility/formatting boundary | Collapse citation eligibility into FinalAnswerPacket; leave display formatting as executor |
| Analyst/Author handoff trace | Mirrors refs and notes | Can hide prompt-only governance | FinalAnswerPacket must own Author inputs; handoff becomes projection |
| Scrutineer/remediation trace fragment | Runtime identity trace | The runtime branch can add evidence and Author directives | Action/observation under RunAuthority; trace-only wrapper deletion in AG-89E |
| Synthesis-evaluator supplemental-search trace fragment | Runtime identity trace | The runtime branch can add retrieval and alter sufficiency | AuthorizedAction/QueryPlan continuation, then wrapper collapse |
| Runtime trace/export compatibility payloads | Projection/export | Low direct runtime risk, high confusion risk | Serialize canonical RunState after AG-89B/C/D; delete obsolete aggregates in AG-89E |

Candidates for elevation to authority because they currently describe decisions no single authoritative state owns: official/current source custody, QueryPlan mutation/finalization, final evidence selection/citation eligibility, Author posture/caveats, and supplemental/remediation search admission.

Safe-to-fold/delete after AG-89B/C/D: observer-only handoff fragments, shadow telemetry, aggregate-only source-obligation summaries, final evidence mirrors, compatibility export payloads that duplicate canonical state, and passive wrappers that no executor consumes.

## 10. Migration charter

### AG-89B — Official/Current Source Custody as RunAuthority Action

Purpose: Make official/current source obligations accountable through a RunAuthority-owned state transition instead of aggregate-only retrieval summaries or scattered legacy authority.

Minimum migration outcome: a required official/current source is represented as a requirement; every attempted candidate has durable custody or an explicit `candidate_identity_missing` / `candidate_aggregate_only` status; aggregate counts cannot satisfy the requirement.

### AG-89C — QueryPlan Authority Collapse

Purpose: Make one QueryPlan authoritative for query identity and query mutations, including recon rewrite, entity correction, query finalization, recency merge, official/canonical bias, query ordering, and provider/depth inputs where appropriate.

Minimum migration outcome: one ordered QueryPlan record explains initial, recovery, continuation, supplemental, and remediation query identity; legacy helpers become deterministic reducers or bounded observations; trace stops reconstructing query authority.

### AG-89D — FinalAnswerPacket / Evidence-Citation Authority Collapse

Purpose: Make one final packet authoritative for final evidence, citation eligibility, claim posture, mandatory caveats, and Author inputs.

Minimum migration outcome: final evidence, citation-eligible source IDs, sufficiency/failure posture, conflict/indirect posture, mandatory caveats, and Author input refs are decided once before Author prose execution.

### AG-89E — Trace-only Wrapper Collapse / Orchestrator Simplification

Purpose: After custody, QueryPlan, and FinalAnswerPacket authority exist, fold or delete observer-only handoffs, duplicate traces, passive wrappers, and obsolete orchestrator branches.

Minimum migration outcome: `run_pipeline(...)` behaves as a compatibility shell that dispatches bounded actions and serializes RunState-derived trace, not as an orchestrator brain.

## 11. Deletion / demotion mandate

No AG-89 implementation phase counts unless it deletes, demotes, bypasses, or schedules retirement of a competing authority surface.

- More wrappers is not success.
- Fewer duplicate owners is success.
- One authoritative packet is success.
- Trace derived from canonical state is success.
- Obsolete trace-only scaffolding removed or scheduled for removal is success.

Each implementation phase must name the competing authority it eliminates or demotes. A new wrapper that leaves old governance untouched is a failed AG-89 phase unless it is paired with a concrete retirement schedule and stop condition.

## 12. AG-89B implementation seed

Official/current source custody is first because the IRS-style failure was a custody/accountability gap before it was an acquisition-quality fix. AG-89B asks: **where did the required official/current source go, and who knew?** AG-85A later asks: **how do we acquire better official/current candidates?**

AG-89B must not collapse back into aggregate counts. Aggregate counts may be observations, but they cannot masquerade as durable candidate custody, source identity, or requirement satisfaction.

Minimal durable custody statuses for AG-89B:

- `required`
- `search_attempted`
- `candidate_returned`
- `candidate_identity_missing`
- `candidate_aggregate_only`
- `candidate_unreadable`
- `candidate_rejected`
- `candidate_accepted`
- `candidate_partially_accepted`
- `candidate_superseded`
- `candidate_unavailable`
- `requirement_satisfied`
- `requirement_unsatisfied`
- `retry_authorized`
- `stop_insufficient_authorized`

`candidate_identity_missing` and `candidate_aggregate_only` are required statuses because aggregate counts cannot masquerade as durable candidate custody. If an executor reports that candidates existed but cannot provide stable candidate identity, the ledger must say so directly rather than allowing a later bridge, trace, or final evidence packet to infer custody.

AG-89B seed requirements:

- Represent official/current source need as a RunAuthority requirement, not just an AnswerContract note or retrieval summary.
- Record search attempt identity, provider role, query ref, and candidate/ref absence without storing raw provider payloads.
- Link each candidate custody record to the requirement it could satisfy.
- Preserve rejection/drop reasons through unreadable, aggregate-only, rejected, superseded, unavailable, accepted, and partially accepted paths.
- Make `requirement_satisfied` and `requirement_unsatisfied` terminal custody statuses owned by RunAuthority, not by citation formatting or Author prose.
- Permit retry only through `retry_authorized`; permit insufficient stop only through `stop_insufficient_authorized`.

## 13. Known unknowns / unknown-with-evidence rows

This phase did not read secrets, raw provider payloads, raw prompts outside repo-tracked source, DB rows, private logs, caches, full raw traces, or generated private data. It did not run live validation.

Known uncertainties that should remain `unknown-with-evidence` until a scoped implementation phase supplies fixtures or state records:

- **Official/current source custody:** repo-tracked diagnostics prove aggregate ambiguity in the IRS failure lineage, but not every live candidate identity/disposition. AG-89B must design custody for missing identity and aggregate-only evidence rather than pretending the missing data is recoverable from old traces.
- **Provider/depth ownership:** targeted retrieval docs and code expose orchestrator-owned boundaries where no Controller handoff supplies provider/depth policy, but a full callsite-by-callsite retirement map should be produced before any behavior activation.
- **Prompt semantics:** prompt-visible instructions clearly govern Author posture, citation presentation, and Scrutineer remediation, but AG-89A does not attempt prompt changes. AG-89D must separate mandatory packet posture from unchanged prompt text.
- **Trace/export wrappers:** AG-89A classifies categories, not every serialized key. AG-89E should produce a key-level deletion/fold list after AG-89B/C/D create canonical state owners.
