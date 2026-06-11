# AG-94C Authority Doctrine / Detritus Audit

Status: audit complete
Phase type: static doctrine and code-path audit
Validation boundary: repo-visible files, grep/static inventory, focused doc checks
Live validation: not run
Provider/model/search calls: not run
Runtime behavior change: none

## Executive Verdict

The current runtime authority doctrine is coherent but still easy to misread
because the repository contains a long Controller-era paper trail and active
compatibility lanes whose names still say "controller" or "orchestrator".

The implemented authority baseline is:

```text
RunAuthorityContract -> EvidenceLedger -> SearchJudgment -> SufficiencyJudgment
-> FinalAnswerPacket -> AuthorExecutor
```

`RunKernel` is the accountable run-level owner for the canonical chain.
Executors and adapters do bounded work. Reducers commit canonical observations
into `RunState`, `EvidenceLedger`, and `FinalAnswerPacket` state. Trace, export,
report, and projection surfaces should render canonical state or clearly marked
compatibility facts; they must not re-decide run authority.

No blocking authority contradiction was found that should interrupt the next
product-behavior lane. The next product lane can remain official-source
acquisition quality, unless a later phase chooses to demote one of the active
compatibility islands first.

The highest doctrine risk is not a missing RunAuthority chain. It is stale
Controller-language in current-looking docs plus active compatibility modules
whose historical names can make future implementers read compatibility lanes as
the canonical authority.

## Actual Current Authority Map

| Runtime concern | Current owner | Runtime consumer | Audit classification |
| --- | --- | --- | --- |
| Run-level action authorization and canonical run state | `core/run_kernel.py` | `pipeline_orchestrator.py`, bounded runtimes, reducers | canonical RunAuthority owner |
| Contract/source obligation synthesis | `RunKernel.RunAuthorityContract` via `core/run_authority_contract*` | `EvidenceLedger`, `QueryPlan` hints, final packet adapter | canonical RunAuthority owner |
| Evidence custody and source obligations | `core/evidence_ledger.py` | Search judgment, sufficiency judgment, final packet adapter | canonical RunAuthority owner |
| Iterative source-gap search judgment | `RunKernel.RunAuthoritySearchJudgment` | `core/run_authority_search_judgment_consumers.py`, authoritative-source action lane | canonical owner consumed through compatibility lane |
| Final answer sufficiency judgment | `RunKernel.RunAuthoritySufficiencyJudgment` | Final answer packet runtime adapter | canonical RunAuthority owner |
| Final answer packet and Author input | `RunKernel.FinalAnswerPacket` | `core/author_execution_runtime.py` | canonical RunAuthority owner |
| Author model execution | `RunKernel.AuthorExecutor` | Author executor and post-author projection | bounded RunKernel-authorized executor |
| Source-class recovery dispatch | RunAuthority SearchJudgment partly, plus authoritative-source/source-class compatibility lifecycle | Source-class recovery runner | RunAuthority-subordinated compatibility lane with active legacy authority |
| Retrieval stop/continue | `core/retrieval_stop_controller.py` under a RunKernel checkpoint action | retrieval loop scheduling | legacy active compatibility authority under RunKernel checkpoint |
| Controller loop spine dispatch arbitration | `core/controller_loop_spine.py` | source-class, weak-corpus, conflict, targeted continuation dispatch | legacy active compatibility authority |
| RunController state | `core/run_controller.py` | trace fragments and compatibility records | passive mirror / compatibility record |
| Trace/export/report projections | `session_output_projection`, `runtime_trace_projection_assembly`, visibility/report modules | execution trace, JSONL output, diagnostics | trace/export/report observer |

## Vocabulary Count Summary

Commands run:

```powershell
$terms = @('controller','Controller','orchestrator','Orchestrator','RunKernel','RunAuthority','authority','lifecycle','projection','export','report','decision','decide')
$scopes = @(@{name='core_py'; path='core'; glob='*.py'}, @{name='tests_py'; path='tests'; glob='*.py'}, @{name='docs_md'; path='docs'; glob='*.md'})
foreach ($scope in $scopes) {
  foreach ($term in $terms) {
    (rg -o -g $scope.glob --fixed-strings $term $scope.path | Measure-Object).Count
  }
}
```

| Term | `core/*.py` | `tests/*.py` | `docs/*.md` |
| --- | ---: | ---: | ---: |
| `controller` | 1172 | 1889 | 737 |
| `Controller` | 1115 | 689 | 905 |
| `orchestrator` | 200 | 712 | 1015 |
| `Orchestrator` | 33 | 0 | 109 |
| `RunKernel` | 102 | 81 | 87 |
| `RunAuthority` | 72 | 7 | 133 |
| `authority` | 1310 | 710 | 907 |
| `lifecycle` | 1289 | 1695 | 508 |
| `projection` | 1275 | 1398 | 668 |
| `export` | 266 | 508 | 493 |
| `report` | 668 | 884 | 421 |
| `decision` | 1522 | 1395 | 585 |
| `decide` | 114 | 152 | 129 |

Focused current-guidance counts:

| File | Controller terms | RunAuthority terms | Authority terms | Projection/export terms |
| --- | ---: | ---: | ---: | ---: |
| `docs/codex/CODEX_GUIDANCE_MAP.md` | 4 | 2 | 4 | 0 |
| `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md` | 2 | 7 | 21 | 8 |
| `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md` | 39 | 0 | 14 | 15 |
| `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md` | 1 | 1 | 4 | 0 |
| `docs/architecture/AG92D_RUNAUTHORITY_POSTACTIVATION_AUDIT.md` | 10 | 33 | 44 | 50 |
| `docs/architecture/AG92E_RUNAUTHORITY_TARGETED_CONSOLIDATION.md` | 0 | 3 | 6 | 8 |

Command summary: vocabulary is still numerically Controller-heavy because of
historical docs, tests, and compatibility modules. The current Codex guidance
already points AG-89+ work toward RunAuthority, but current-looking architecture
docs still carry older Controller doctrine.

## Classification Table By File / Module

| File/module | Category | Finding |
| --- | --- | --- |
| `core/run_kernel.py` | canonical RunAuthority owner | Owns authorized actions, canonical state projections, reducers, and final Author gating. |
| `core/run_authority_contract.py` | canonical RunAuthority owner | Defines contract schema and source requirements. |
| `core/run_authority_contract_runtime.py` | bounded RunKernel-authorized executor | Executes contract synthesis and returns reducer observation. |
| `core/run_authority_contract_validation.py` | bounded executor support | Validates/sanitizes contract outputs; no provider/search authority by itself. |
| `core/run_authority_search_judgment.py` | canonical RunAuthority owner | Defines SearchJudgment decision vocabulary and input. |
| `core/run_authority_search_judgment_runtime.py` | bounded RunKernel-authorized executor | Executes deterministic/smart judgment under a RunKernel action. |
| `core/run_authority_search_judgment_adapter.py` | bounded RunKernel-authorized executor | Adapter that assembles already-computed facts; docstring correctly says it does not decide policy. |
| `core/run_authority_search_judgment_consumers.py` | RunAuthority-subordinated compatibility lane | Consumes canonical SearchJudgment and promotes/blocks legacy source-class recovery facts. |
| `core/run_authority_sufficiency.py` | canonical RunAuthority owner | Defines SufficiencyJudgment and final-answer posture fields. |
| `core/run_authority_sufficiency_runtime.py` | bounded RunKernel-authorized executor | Executes sufficiency judgment and emits observation. |
| `core/run_authority_sufficiency_adapter.py` | bounded RunKernel-authorized executor | Adapter that assembles finalization facts; no direct sufficiency decision. |
| `core/run_authority_projection_refs.py` | canonical reference helper | Validates compact refs to canonical search/sufficiency projections. |
| `core/evidence_ledger.py` | canonical RunAuthority owner | Owns source custody, obligations, gaps, and subordinate official/current custody projections. |
| `core/evidence_ledger_runtime.py` | bounded RunKernel-authorized executor | Builds ledger observations for reduction. |
| `core/evidence_ledger_lifecycle.py` | bounded RunKernel-authorized executor | Wraps repeated EvidenceLedger authorize/execute/reduce callsites. |
| `core/final_answer_packet.py` | canonical RunAuthority owner | Owns final evidence/citation eligibility and Author payload shape. |
| `core/final_answer_packet_runtime.py` | bounded RunKernel-authorized executor | Prepares packet and payload under RunKernel authorization. |
| `core/final_answer_runtime_adapter.py` | RunAuthority-subordinated compatibility lane | Bridges AnswerContract/legacy fields into packet while honoring canonical sufficiency when present. |
| `core/final_answer_runtime_assembly.py` | RunAuthority-subordinated compatibility lane | Compatibility shell for packet and citation/source handoffs; uses ledger when available. |
| `core/author_execution_runtime.py` | bounded RunKernel-authorized executor | Executes Author from canonical packet payload and returns sanitized observation. |
| `core/pipeline_orchestrator.py` | coordination shell with active compatibility islands | Coordinates the chain; still contains retrieval loop, compatibility gates, provider/model execution callsites, and lifecycle handoffs. |
| `core/run_controller.py` | passive mirror / compatibility record | Docstring and implementation are passive records/serialization. |
| `core/controller_state_mirror.py` | passive mirror / compatibility record | Records metadata into RunController state. |
| `core/controller_loop_spine.py` | legacy active compatibility authority | Authorizes at most one bounded executor from legacy checkpoint/lifecycle facts. |
| `core/retrieval_stop_controller.py` | legacy active compatibility authority | Computes stop/continue decisions under RunKernel checkpoint; still active runtime decision logic. |
| `core/authoritative_source_action.py` | RunAuthority-subordinated compatibility lane | Consumes SearchJudgment but still arbitrates authoritative-source/source-class recovery admission. |
| `core/authoritative_source_action_orchestrator_adapter.py` | bounded adapter | Collects sanitized orchestrator facts and calls the named action seam. |
| `core/source_class_recovery_controller.py` | legacy active compatibility authority | Source-class recovery lifecycle controller retained for compatibility. |
| `core/source_class_recovery_controller_mirror.py` | passive mirror / compatibility record | Mirrors source-class recovery recommendation into controller state. |
| `core/weak_corpus_controller.py` | legacy active compatibility authority | Decides weak-corpus recovery; later consumed by sufficiency as upstream fact. |
| `core/conflict_resolution_controller.py` | legacy active compatibility authority | Decides conflict-resolution retrieval lane. |
| `core/targeted_retrieval_controller.py` | legacy active compatibility authority | Builds targeted-retrieval lifecycle facts used by loop spine. |
| `core/session_output_projection.py` | trace/export/report observer | Serializes already-computed facts; includes legacy source-survival counts. |
| `core/runtime_trace_projection_assembly.py` | trace/export/report observer | Attaches passive projection traces; can refresh old ControllerEvidenceLedger visibility from trace/final evidence. |
| `core/runtime_trace_export_attachment.py` | trace/export/report observer | Attaches compatibility payloads for reports/output packets. |
| `core/official_canonical_recovery_visibility_export.py` | trace/export/report observer | Builds diagnostic visibility/export fields from whitelisted facts; includes derived failure-layer labels. |
| `core/post_author_output_projection.py` | trace/export/report observer with compatibility handoff building | Builds post-author compatibility trace/output; checks local packet does not diverge from RunKernel state. |
| `proplex/__main__.py` | naming compatibility surface | Legacy CLI entrypoint retained; not authority debt. |
| `scryraven/__main__.py` | public project entrypoint shim | Delegates to `proplex.__main__.main`; compatibility bridge. |
| `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md` | current documentation | Correct default for AG-89+; updated in this phase with AG-94C baseline. |
| `docs/codex/CODEX_GUIDANCE_MAP.md` | current documentation | Correct routing; updated in this phase with AG-94C audit link. |
| `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md` | current documentation | Correctly says RunAuthority supersedes Controller for AG-89+ work. |
| `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md` | stale or historical documentation for AG-89+ | Useful only when a phase explicitly selects legacy Controller maintenance. |
| `docs/architecture/AG92D_RUNAUTHORITY_POSTACTIVATION_AUDIT.md` | current-ish historical documentation | Accurate post-activation checkpoint; superseded by this AG-94C doctrine audit for current routing. |
| `docs/architecture/AG92E_RUNAUTHORITY_TARGETED_CONSOLIDATION.md` | current-ish historical documentation | Accurate consolidation note; not full current doctrine. |
| `docs/architecture/SCRYRAVEN_CURRENT_STATE.md` | misleading current documentation | Name implies current state but content is mostly Controller-era status; route future authority work away from it unless explicitly refreshing it. |
| `docs/architecture/AG74*` through `AG79*` Controller docs | stale or historical documentation | Preserve as history; do not delete or bulk rewrite. |
| `docs/validation/AG69F_CONTROLLER_LIFECYCLE_FORCED_CORRIDOR_VALIDATION.md` | stale or historical documentation | Historical validation note, not current doctrine. |
| `docs/product/AG81B_R1_ANSWER_WORTHINESS_AND_GOLDEN_EXAMPLES.md` | stale doctrine reference in product doc | Contains an old "Controller-owned handoff phase" recommendation; not a current authority guide. |

## Stale Docs / Misleading Docs

Docs that can still lead a future implementer toward old Controller doctrine:

- `docs/architecture/SCRYRAVEN_CURRENT_STATE.md`: current-sounding filename,
  but content states "Controller decides, orchestrator executes" as the current
  model. This is misleading after RunAuthority activation.
- `docs/architecture/AG79D_TARGETED_ORCHESTRATOR_AUTHORITY_CLOSURE.md` and the
  AG-74 through AG-79 sequence: correct historical records, but not current
  authority doctrine.
- `docs/validation/AG69F_CONTROLLER_LIFECYCLE_FORCED_CORRIDOR_VALIDATION.md`:
  historical validation note that states "Controller decides. Orchestrator
  executes."
- `docs/product/AG81B_R1_ANSWER_WORTHINESS_AND_GOLDEN_EXAMPLES.md`: product
  review row still points evidence selection defects toward a Controller-owned
  handoff phase. Treat as product-history language, not current implementation
  doctrine.
- `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md`: intentionally
  legacy. Its supersession note is correct, but the body is not the default
  doctrine for AG-89+ or AG-94+ work.

Targeted guidance update made in this phase: route current authority work through
this audit and the RunAuthority guide rather than through `SCRYRAVEN_CURRENT_STATE.md`.

## Active Legacy Authority Islands

These are real runtime authority or partially runtime-governing compatibility
surfaces. Do not delete or rename them in this phase.

| Island | Current role | Why it remains |
| --- | --- | --- |
| Retrieval stop/continue controller | Stops or continues retrieval under RunKernel checkpoint actions. | Still protects existing iteration, redundancy, weak-recovery, and budget behavior. |
| Controller loop spine | Arbitrates source-class, weak-corpus, conflict, and targeted-retrieval dispatch. | Still mediates legacy lifecycle dispatch for multiple lanes. |
| Source-class/authoritative-source recovery lane | Admits official/current/canonical recovery execution. | SearchJudgment consumes into it, but acquisition/execution quality is still product-behavior work. |
| Weak-corpus recovery lane | Can schedule weak-corpus recovery searches. | Upstream fact source consumed by sufficiency; behavior remains protected. |
| Conflict-resolution retrieval lane | Can authorize resolving-query retrieval. | Still an active compatibility lane feeding conflict posture. |
| Economist, Scrutineer, and synthesis-evaluator supplemental lanes | Can affect model calls, analysis, final context, and Author directives in licensed runtime paths. | Outside this audit scope; classify as protected legacy/product behavior. |

## RunAuthority-Subordinated Compatibility Lanes

These lanes are acceptable if future phases keep them subordinate:

- `run_authority_search_judgment_consumers.py` consumes only canonical
  SearchJudgment projections and translates them into source-class recovery
  compatibility facts.
- `authoritative_source_action.py` applies SearchJudgment before/after legacy
  AnswerContract gap handling, then records a source-class lifecycle trace.
- `final_answer_runtime_adapter.py` and `final_answer_runtime_assembly.py`
  prefer EvidenceLedger/SufficiencyJudgment and keep legacy fallbacks only for
  compatibility.
- `post_author_output_projection.py` uses `_run_kernel_final_answer_ref()` to
  point post-author handoffs to RunKernel packet state and raises if the local
  packet diverges from RunKernel.
- `runtime_trace_projection_assembly.py` attaches old projection traces after
  execution; those traces must remain observer-only.

## Trace / Export / Report Re-decision Risks

No trace/export/report surface was found changing runtime behavior directly.
However, several observers derive labels or summaries from narrowed data. These
are acceptable diagnostics today, but they are future risk if a consumer starts
reading them as authority.

| Surface | Risk | Current status |
| --- | --- | --- |
| `official_canonical_recovery_visibility_export.py` | Derives `likely_next_failure_layer`, `next_failure_layer`, candidate counts, and survival labels from trace/export inputs. | Diagnostic-only export; risk is vocabulary looking authoritative. |
| `session_output_projection.py` | Recomputes legacy official/canonical source-class survival counts from telemetry maps. | Compatibility output only; not final evidence authority. |
| `runtime_trace_projection_assembly.py` | Builds old `ControllerEvidenceLedger` trace after export assembly from execution trace/final evidence. | Passive projection; should not be read as canonical EvidenceLedger. |
| `post_author_output_projection.py` | Rebuilds conflict facts and AnswerContract compatibility handoff after Author execution. | Compatibility handoff only; final packet ref guards local divergence. |
| `final_answer_runtime_assembly.py` | Falls back to legacy source-obligation telemetry if no EvidenceLedger projection is supplied. | Acceptable compatibility fallback; future guard could require canonical ledger in RunAuthority lanes. |

Recommended guard if a future phase touches these files: assert observer modules
do not import provider/search clients, do not call `ask_model`, do not mutate
RunKernel state, and do not expose derived diagnostics without an explicit
`diagnostic_only` or compatibility marker.

## Orchestrator Containment Findings

Current `core/pipeline_orchestrator.py` line count from static inventory:
`4602` lines. This phase changed it by `0` lines.

Contained coordination callsites:

- RunAuthority contract synthesis, EvidenceLedger reductions, SearchJudgment,
  SufficiencyJudgment, FinalAnswerPacket preparation, and Author execution all
  follow authorize -> execute bounded runtime -> reduce observation.
- AG-92E adapters now keep SearchJudgment and SufficiencyJudgment input
  construction out of the orchestrator.
- EvidenceLedger lifecycle helpers keep repeated reduction plumbing named and
  bounded.

Calls that still look domain-decision-shaped and should not be expanded inside
the orchestrator:

- `_decide_retrieval_loop_stop_continue(...)` wraps retrieval stop decisions.
  It is a legacy active compatibility authority under a RunKernel checkpoint.
- `_ensure_checkpoint_decision_for_weak_corpus_timing(...)` builds AnswerContract
  and evidence-integration checkpoint facts inside the orchestrator for a timing
  lane. It is compatibility logic, not canonical RunAuthority.
- The main retrieval loop still owns query execution scheduling, disambiguation
  retry, provider scheduling, weak-corpus recovery scheduling, and evidence
  filtering callsites. These are protected behavior, not AG-94C cleanup targets.
- The source-class recovery handoff uses a bounded adapter, but the downstream
  authoritative-source/source-class lane still performs active arbitration and
  execution admission.
- Final synthesis/economist/linkup/preflight and Author prompt assembly remain
  product-behavior surfaces. Do not alter them under doctrine cleanup.

Containment verdict: `pipeline_orchestrator.py` is mostly a coordination shell
for the RunAuthority chain, but it still hosts active compatibility islands and
protected product-behavior callsites. Future phases should extract or demote
one island at a time rather than rewrite the file.

## Naming Debt Inventory

| Name | Classification | Action in this phase |
| --- | --- | --- |
| ScryRaven | Public project name | Keep. |
| repo `scryraven` | Public repo/package-facing name | Keep. |
| `scryraven/__main__.py` | Public CLI shim | Keep. |
| `proplex` package | Legacy compatibility package | Keep. |
| `python -m proplex` | Legacy compatibility CLI entrypoint | Keep. |
| `PROPLEX_*` env vars | Legacy compatibility env aliases | Keep. |
| `proplex.db` and `proplex_*` state keys | Legacy compatibility storage/state names | Keep. |
| Controller/Orchestrator filenames in legacy modules | Naming debt plus some authority debt | Classify only; no rename. |

Naming verdict: this is mostly compatibility naming debt. Do not rename package,
CLI, env, DB, or public API surfaces without a dedicated compatibility plan.

## Recommended Follow-up Phases

1. **AG-94D official-source acquisition quality audit**: remain on the next
   product-behavior lane unless the team wants one more architecture-only pass.
2. **Repo-doc doctrine alignment**: update or clearly front-matter
   `docs/architecture/SCRYRAVEN_CURRENT_STATE.md` so its current-sounding name
   cannot override AG-94C/RunAuthority doctrine.
3. **Trace/export/report no-redecision guard**: add static tests for
   `session_output_projection`, `runtime_trace_projection_assembly`,
   `official_canonical_recovery_visibility_export`, and
   `post_author_output_projection`.
4. **Active compatibility island demotion**: choose exactly one lane, likely
   source-class recovery dispatch or retrieval stop/continue, and demote it
   behind canonical RunAuthority state without behavior changes.
5. **Naming compatibility plan**: inventory `proplex`/`PROPLEX_*`/DB state keys
   and propose a versioned compatibility strategy. Do not execute renames in the
   same phase.

## Do Not Clean Up Yet

- Do not delete historical AG docs.
- Do not bulk rewrite Controller-era docs to erase history.
- Do not rename `proplex`, `python -m proplex`, `PROPLEX_*`, DB names, session
  keys, package names, CLI names, or public API surfaces.
- Do not rewrite `core/pipeline_orchestrator.py`.
- Do not alter provider routing, provider selection, provider depth, provider
  swaps, query generation, search behavior, ranking/filtering, citation
  behavior, prompts, Author prose, final answer behavior, package names, or env
  aliases.
- Do not inspect secrets, `.env`, DB rows, caches, raw provider payloads, raw
  prompts, private logs, full raw traces, or local output packets.
- Do not turn AG-94C into official-source acquisition quality work.

## ChatGPT Project Source Candidate Recommendation

ChatGPT Project Sources are not repo files and were not inspected or edited.
This audit found that Project Source refresh candidates are useful because the
repo still contains current-looking Controller-era docs. Upload-ready candidate
markdown files were drafted under:

```text
outputs/local_only/ag94c_project_source_candidates/
```

Those files are only candidate source text for the user to upload through
ChatGPT. They do not update ChatGPT memory automatically.

## Checks Run

- `git status --short --branch`: confirmed base branch and unrelated untracked
  `.local-setup-logs/`.
- `git rev-parse HEAD`: base commit `8a550b06d9ef0d155454aa4f12328b58aa5d0b62`.
- `rg --files` over `core`, `proplex`, `scryraven`, `tests`, and `docs` to find
  active authority/code/doc surfaces.
- Static vocabulary count command shown above.
- `rg -n` over `docs` for Controller-default and RunAuthority-default doctrine
  language.
- `rg -n` over projection/export/report modules for diagnostic decision and
  canonical-state terms.

No live calls were run. No runtime behavior changed.
