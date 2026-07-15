# AG-94G Orchestrator Authority Strangler Map

Status: implemented as an offline architecture cleanup, authority inventory, and
one small behavior-preserving projection extraction.

Maintenance update: legacy Economist ordinary execution was retired at
`7bbfff0f604096e3437bfdadc3dd8b81ec56b57c`. This update changes the Economist
callsite/debt disposition below; it does not reopen AG-94G's historical scope.

Validation boundary: repo-visible files, static inspection, focused tests, and
offline checks only. No live ScryRaven/proplex provider, model, search,
retrieval, secret, `.env`, DB row, raw provider payload, raw prompt, private log,
cache, full raw trace, local output packet, or private artifact access was used.

## Executive Verdict

`core/pipeline_orchestrator.py` is still behavior-bearing. It is not sacred, not
architecture-successful because untouched, and not a default protected surface.
It is a coordination shell with remaining authority debt and is now explicitly a
target surface for bounded strangulation phases.

The RunAuthority chain is still the target state:

```text
RunAuthorityContract -> EvidenceLedger -> SearchJudgment -> SufficiencyJudgment
-> FinalAnswerPacket -> AuthorExecutor
```

The orchestrator should coordinate lifecycle order, call bounded executors, and
forward canonical state. It should not own policy. This phase updated current
guidance to use licensed, closed, target, historical, and safety-sensitive
surface vocabulary, created this inventory, and moved exactly one pure
post-Author source telemetry helper out of the orchestrator.

## Why "Orchestrator Untouched" Became Harmful Doctrine

Earlier phases often recorded `core/pipeline_orchestrator.py` line delta `0` as
a scope-control fact. That was useful when product behavior, prompts,
provider/search behavior, citations, Author prose, persistence, or live behavior
were closed. It became harmful when future prompts started reading "untouched"
as architecture success.

The accurate doctrine is:

- Untouched because closed this phase: acceptable scope control.
- Touched because licensed target surface: acceptable when the brief opens it.
- Untouched but still architectural debt: common for ordinary product phases.
- Target surface for strangulation: expected in orchestrator cleanup phases.

## Current RunAuthority Target State

RunKernel / RunAuthority owns run-level meaning and canonical state. Bounded
executors acquire observations, call providers only when licensed, assemble
projections, persist records, or render outputs. Trace/export/report observe
canonical state and must not re-decide it.

`pipeline_orchestrator.py` should eventually be thin glue:

1. authorize a RunKernel action;
2. call the named bounded executor or adapter;
3. reduce the observation into canonical state;
4. pass canonical projections to the next consumer;
5. build trace/export/report outputs from canonical state.

## Current Orchestrator Debt Summary

At the Economist retirement checkpoint, the orchestrator has 4,124 physical
lines. It still contains:

- provider/model/search execution wrappers and callsites;
- retrieval stop/continue decisions through a compatibility controller;
- controller loop spine dispatch arbitration;
- source-class/authoritative-source recovery admission and dispatch handoff;
- weak-corpus recovery scheduling;
- conflict-resolution retrieval scheduling;
- targeted and ordinary continuation gates;
- supplemental search, Scrutineer/remediation, and Linkup callsites;
- passive legacy Economist handoff and trace compatibility data, but no
  ordinary Economist execution callsite;
- Author/final-answer prompt-adjacent assembly callsites;
- trace/export/session/report packaging;
- compatibility mirrors into RunController state.

Those are not all equally wrong. Some are already delegated; some are necessary
temporary compatibility islands; some are safety-sensitive product/runtime
callsite surfaces that should be changed only in dedicated licensed phases.

## Authority Inventory Table

Buckets:

1. Already delegated.
2. Should move to canonical authority.
3. Should become dumb adapter/handoff.
4. Temporary compatibility island.
5. Provider/model/search execution callsite.
6. Trace/export/report observer.

| Region | Bucket | Current behavior and owner | Desired owner / migration target | Risk / authority / changed | Future phase or kill condition |
| --- | --- | --- | --- | --- | --- |
| imports, compatibility re-exports, module constants, lines 1-326 | 3 | Orchestrator imports many executors, helpers, controllers, and compatibility re-exports; owner is the orchestrator module namespace. | Keep only lifecycle glue imports; move compatibility re-exports to owned modules or explicit public compat module. | Low/medium; not directly authority-bearing, but import surface hides ownership; changed: no. | Kill when tests no longer import helper aliases from `pipeline_orchestrator.py`. |
| `_clean_query`, lines 335-343 | 2 | Normalizes query text used by query paths; owner is orchestrator utility. | QueryPlan / query production adapter. | Medium; authority-bearing because it can alter query identity; changed: no. | Move only with exact query string parity tests. |
| `_compact_runtime_strings`, lines 356-373 | 3 | Normalizes bounded trace/controller fact lists. | Shared adapter helper near lifecycle projection code. | Low; adapter-only; changed: no. | Move when targeted/continuation helper is extracted. |
| targeted retrieval source-fit helpers, lines 375-692 | 4 | Builds targeted retrieval lifecycle facts from AnswerContract, source-class, weak-corpus, conflict, and retrieval-stop facts. Current owner is orchestrator plus `targeted_retrieval_controller.py`. | `targeted_retrieval_controller.py` or a controller-loop spine adapter fed by canonical SearchJudgment/EvidenceLedger facts. | Medium/high; authority-bearing because it classifies which lane owns path and whether targeted retrieval may proceed; changed: no. | Kill when targeted retrieval reads a canonical recovery permission object and no longer needs orchestrator-local ownership synthesis. |
| authoritative source checkpoint refresh guard, lines 695-737 | 4 | Allows a stale non-terminal checkpoint to be refreshed when official/canonical recovery is admitted. Owner is orchestrator-local helper. | SearchJudgment consumer / authoritative-source action lane under RunKernel checkpoint state. | High; authority-bearing checkpoint mutation; changed: no. | Move with tests proving weak-corpus, terminal stop, and official recovery admission parity. |
| conflict resolution lifecycle builder, lines 739-792 | 4 | Assembles conflict-resolution controller input from AnswerContract evidence state. | `conflict_resolution_controller.py` or a RunAuthority conflict-posture adapter. | Medium; authority-bearing because it can admit conflict retrieval; changed: no. | Kill when Sufficiency/SearchJudgment owns conflict retrieval admission inputs directly. |
| `_extract_year`, depth helpers, lines 794-830 | 2 / 5 | Extracts year and chooses retrieval/supplemental search depth. Owner is orchestrator utility. | QueryPlan / ProviderPlan / retrieval scheduler. | High for depth helpers; authority-bearing search-depth policy; changed: no. | Dedicated provider/search-depth authority phase with parity tests. |
| weak-corpus seed query builder, lines 832-943 | 4 | Builds deterministic weak-corpus recovery query seeds. | `weak_corpus_controller.py` or QueryPlan recovery-query producer. | High; authority-bearing query generation; changed: no. | Move only after weak-corpus recovery query identity parity tests. |
| pre-Analyst aliases, lines 944-955 | 3 | Compatibility aliases to analyst runtime helpers. | Analyst runtime module direct imports by consumers. | Low; not authority-bearing by itself; changed: no. | Remove when compatibility imports stop targeting orchestrator. |
| final answer source telemetry helper, removed from lines 954-984 and moved to `post_author_output_projection.py` | 6 | Computes source IDs cited in final report and divergence from quantitative packet source IDs. | `post_author_output_projection.py` trace/projection observer. | Low; observer-only; changed: yes. | Done. Keep as projection-only helper; no runtime consumer should read it as authority. |
| `_pipeline_timing_payload`, lines 957-1008 | 6 | Builds timing telemetry. | Runtime trace/session projection module. | Low; observer-only; changed: no. | Move if timing projection helper grows or duplicates output logic. |
| `run_pipeline` wrapper, lines 1014-1082 | 1 | Public entrypoint, logging start/failure, calls `_run_pipeline_inner`. | Remain coordination wrapper. | Low; not policy-bearing; changed: no. | Keep. |
| config/dependency unpack, cost wrappers, RunKernel init, lines 1084-1211 | 3 / 5 | Unpacks config, wraps model/embed/search/linkup calls for cost accounting, initializes RunKernel. | Dependency/cost adapter plus RunKernel run-start helper. | Medium; wrappers are execution callsites but mostly mechanical; changed: no. | Extract wrappers only with no-live-call unit tests and call-kwarg parity. |
| context measurement helper, lines 1212-1248 | 6 | Records prompt/evidence context sizes. | Context measurement adapter. | Low; observer-only unless used to gate runtime; changed: no. | Keep observer-only; move with projection cleanup. |
| route request and RunAuthorityContract, lines 1306-1365 | 1 / 5 | RunKernel authorizes route and contract synthesis; bounded executors call model only through supplied dependency. | RunKernel and routing/contract runtimes. | Medium/high due model callsite; authority delegated; changed: no. | Keep callsite until route/contract runtime lifecycle helper exists. |
| policy state and session title, lines 1367-1422 | 2 / 5 | Loads policy thresholds and calls model for title generation. | Policy module and title-generation bounded executor. | Medium; title is product output metadata; policy thresholds can affect behavior; changed: no. | Separate metadata/title helper with tests; do not alter title prompt or provider. |
| query production and query admission, lines 1424-1539 | 1 / 5 | RunKernel authorizes query production and QueryPlan admission; runtime returns query identity, depth, providers, and routing facts. | QueryPlan / query production runtime. | High due provider/query/depth behavior, but delegated; changed: no. | Keep; future query-authority phase may further thin locals. |
| retrieval state initialization, embedding, ProviderPlan env checks, lines 1541-1626 | 5 | Initializes retrieval accumulators, embeds query, computes available providers from env presence. | ProviderPlan / retrieval scheduler / RunKernel action helper. | High; provider/search/embedding behavior; changed: no. | Dedicated provider plan extraction with env and call-kwarg parity. |
| retrieval stop shadow and checkpoint decision helpers, lines 1628-1715 | 4 | Builds retrieval stop snapshot, authorizes checkpoint, calls retrieval stop controller, records trace. | RunAuthority SearchJudgment/RunState stop action or `retrieval_stop_controller.py` as subordinated executor. | High; authority-bearing stop/continue; changed: no. | First recommended strangler target: make retrieval stop consume canonical SearchJudgment/RunState stop posture and demote local helper to adapter. |
| weak-corpus timing checkpoint helper, lines 1717-1863 | 4 | Rebuilds source-class, conflict, AnswerContract, and checkpoint facts before weak-corpus timing decisions. | EvidenceLedger/SearchJudgment checkpoint adapter. | High; authority-bearing compatibility island; changed: no. | Kill after weak-corpus recovery and source-class recovery share a canonical recovery admission object. |
| retrieval batch dispatch and continuation gates, lines 1865-2610 | 4 | Builds evaluator, expander, and scout continuation pregates, checkpoint traces, targeted retrieval traces, and batch dispatch authorization. | Controller loop spine should become a bounded adapter fed by canonical RunState/SearchJudgment. | High; authority-bearing dispatch and query continuation; changed: no. | Move one gate family at a time; keep provider/query behavior unchanged. |
| main retrieval loop scheduling and execution, lines 2612-2758 | 5 | Authorizes main retrieval pass, schedules provider/depth/query execution, executes search, embeds chunks, merges/ranks evidence, and handles disambiguation retry. | Retrieval scheduler/executor plus QueryPlan/ProviderPlan canonical owners. | High; provider/search/depth/ranking/filtering authority; changed: no. | Closed until a dedicated retrieval/provider/search authority phase with parity fixtures. |
| weak-corpus recovery block, lines 2759-2892 | 4 / 5 | Builds weak-corpus recovery queries, controller decision, controller loop spine authorization, and schedules recovery search. | WeakCorpus controller subordinated to RunAuthority source obligations and QueryPlan recovery queries. | High; authority-bearing and search-call scheduling; changed: no. | Kill when weak-corpus can no longer own the path ahead of unsatisfied stronger authority obligations. |
| post-recovery stop and scout/expander/evaluator model loop, lines 2893-3256 | 4 / 5 | Runs scout, expander, gap evaluator, retrieval stop decisions, and continuation scheduling. | Bounded executors under QueryPlan/SearchJudgment/RunState. | High; model/search/query behavior; changed: no. | Dedicated continuation-loop strangler; no prompt/provider/depth change allowed. |
| budget stop, lines 3258-3290 | 4 | Applies retrieval stop controller at iteration budget exhaustion. | RunState/SearchJudgment stop posture. | Medium/high; authority-bearing stop path; changed: no. | Migrate with retrieval stop target phase. |
| pre-recovery source-class telemetry, EvidenceLedger reduction, AnswerContract compatibility, SearchJudgment, lines 3298-3505 | 1 / 3 / 4 | Reduces contract/ledger facts, builds compatibility AnswerContract, executes SearchJudgment. | EvidenceLedger and SearchJudgment own canonical decisions; AnswerContract should become compatibility-only adapter. | Medium; mixed delegated and compatibility authority; changed: no. | Demote AnswerContract fallback after canonical coverage tests. |
| authoritative-source action, conflict lifecycle, checkpoint refresh, controller spine, and recovery dispatch, lines 3506-3787 | 4 / 5 | Consumes SearchJudgment through authoritative-source action adapter, updates source-class lifecycle, conflict lifecycle, checkpoint/spine, then runs source-class and conflict retrieval executors. | SearchJudgment/EvidenceLedger recovery permission plus bounded source-class/conflict executors. | High; authority-bearing dispatch and search execution; changed: no. | Second recommended target after retrieval stop: source-class recovery dispatch permission. |
| final evidence bundle and EvidenceLedger final reductions, lines 3788-3821 | 1 / 2 / 3 | Builds final evidence bundle and reduces final evidence into EvidenceLedger. | EvidenceLedger and FinalAnswerPacket, with final evidence selection in owned bundle builder. | Medium; final evidence identity affects citations and Author input; changed: no. | Keep callsite until FinalAnswerPacket can consume a canonical final-evidence selection object directly. |
| Linkup callsite and retired Economist compatibility region, current post-AG-94G surface | 5 / 4 / 6 | Independently gates and calls Linkup. Ordinary Economist gating, preflight, execution, dependency reads, and the quantitative-preflight Author note are retired. Passive legacy handoff/trace fields remain fixed to a non-running posture. | Linkup bounded retrieval executor; post-retirement topology census for any remaining legacy Economist compatibility owner. | High for Linkup provider behavior; low/medium for passive compatibility data; Economist ordinary execution changed: yes, retired at `7bbfff0`. | Keep Linkup parity. Inventory compatibility consumers before any later field or implementation cleanup; do not build a replacement here. |
| quantitative telemetry and fallback directive, current post-retirement surface | 2 / 6 | Builds high-stakes quantitative diagnostics and passive legacy Economist compatibility telemetry. The former preflight-generated Author fallback note is absent. | Quantitative diagnostics owners plus trace/export observers; no Economist runtime owner is installed. | Medium; diagnostics can look authoritative even though they do not execute or route the Economist; changed: yes. | Keep passive/non-authoritative; classify consumers in the post-retirement topology census. |
| Analyst runtime stage, lines 4074-4148 | 1 / 5 | Builds Analyst prefix/slice and calls bounded Analyst runtime stage. | Analyst runtime executor. | High due model/prompt behavior; delegated but callsite remains; changed: no. | Keep until Analyst executor consumes packetized inputs. |
| legacy review, synthesis evaluator, Scrutineer/remediation, supplemental search, lines 4150-4173 | 4 / 5 | Calls legacy review runtime, which may run model/search supplemental and Scrutineer/remediation behavior. | Dedicated Scrutineer/supplemental executors subordinated to RunAuthority. | High; provider/model/search/final-context behavior; changed: no. | Closed for this phase; future supplemental lane demotion. |
| Author evidence attachment, recency notes, prompt assembly, lines 4175-4213 | 2 / 5 | Attaches Author evidence, computes recency notes, builds prompt assembly before sufficiency/packet. | FinalAnswerPacket and AuthorExecutor. | High; Author/citation/prose surface; changed: no. | Move only when packet owns all Author-visible posture and tests prove prompt parity. |
| SufficiencyJudgment, lines 4214-4270 | 1 / 5 | Builds sufficiency input with adapter, authorizes and executes RunAuthority SufficiencyJudgment. | RunKernel.RunAuthoritySufficiencyJudgment. | Medium/high due optional smart model; authority delegated; changed: no. | Keep as lifecycle glue; no local sufficiency policy should be added. |
| FinalAnswerPacket and AuthorExecutor, lines 4272-4360 | 1 / 5 | Prepares packet, derives Author payload, authorizes and executes Author. | RunKernel.FinalAnswerPacket and RunKernel.AuthorExecutor. | High due Author model call; authority delegated; changed: no except telemetry helper import. | Keep as lifecycle glue; no local Author policy. |
| useful content, failure card, weak failure gate, answer outcome, lines 4362-4465 | 2 / 4 | Classifies answer displayability and weak/failure gate output after Author. | SufficiencyJudgment/FinalAnswerPacket plus weak-failure compatibility adapter. | Medium; final output posture; changed: no. | Demote after canonical packet owns displayable/insufficient posture. |
| session payload, RunController mirror, stage ledger, lines 4466-4547 | 6 / 3 | Builds session payload, mirrors controller state, records stage ledger provider/query facts. | Session/output projection and trace/export observers. | Medium; observer, but persistence shape sensitive; changed: no. | Move only with session/trace shape parity. |
| post-author source-class projection, official bridge, post-final EvidenceLedger reduction, lines 4548-4687 | 4 / 6 | Recomputes source-class telemetry, applies official source bridge, records recommendation, reduces post-final obligations. | EvidenceLedger observer adapter and source-class visibility projection. | Medium/high; mostly observer but can look authoritative; changed: no. | Add diagnostic-only markers; eventually require canonical ledger state for post-final projections. |
| post-author trace/output packaging, persistence side effects, outcome return, lines 4688-4730 | 1 / 6 | Delegates trace packaging, output packaging, persistence side effects, KB context, and RunOutcome assembly. | Projection/export/persistence helpers. | High for persistence shape, low for helper ownership; changed: no. | Keep side-effect order local until persistence parity tests cover full return path. |

## Active Compatibility Islands And Desired Owners

| Island | Current owner | Desired owner | Kill condition |
| --- | --- | --- | --- |
| Retrieval stop/continue | `retrieval_stop_controller.py` plus orchestrator helper | RunState/SearchJudgment stop posture with controller as subordinated executor | Runtime retrieval loop reads canonical stop posture; old helper becomes trace adapter or is deleted. |
| Controller loop spine | `controller_loop_spine.py` plus orchestrator trace assembly | RunKernel action authorization and SearchJudgment-derived recovery permission | Spine no longer arbitrates between source-class, weak-corpus, conflict, and targeted retrieval from trace packets. |
| Source-class / authoritative-source recovery | SearchJudgment consumers plus source-class lifecycle/action adapters | EvidenceLedger/SearchJudgment recovery permission and bounded source-class executor | Source-class dispatch does not depend on orchestrator-local AnswerContract/checkpoint synthesis. |
| Weak-corpus recovery | `weak_corpus_controller.py` plus orchestrator query seeds/scheduling | Sufficiency/SearchJudgment/QueryPlan recovery posture | Weak corpus cannot preempt stronger unsatisfied source obligations and recovery queries are QueryPlan-owned. |
| Conflict-resolution retrieval | `conflict_resolution_controller.py` plus orchestrator AnswerContract adapter | RunAuthority conflict posture and bounded conflict executor | Conflict retrieval admission reads canonical conflict posture rather than compatibility AnswerContract facts. |
| Targeted retrieval | `targeted_retrieval_controller.py` plus orchestrator ownership synthesis | QueryPlan/SearchJudgment continuation permission | Targeted retrieval lifecycle input no longer requires orchestrator-local lane ownership reconstruction. |
| Supplemental lanes | legacy review runtime, Scrutineer/remediation, synthesis evaluator | Dedicated bounded executors subordinated to canonical sufficiency/final packet state | Supplemental search and remediation cannot alter final context without a canonical RunAuthority handoff. |
| Legacy Economist compatibility data | optional `RunDeps` field, Economist handoff contract, Analyst/post-Author projection, trace/session fields | No current execution owner; post-retirement census must identify every actual compatibility consumer before cleanup | Ordinary composition and orchestrator remain unable to invoke the Economist; any later cleanup is separately licensed. |
| Post-author compatibility projections | post-author/session/runtime trace projection helpers plus orchestrator source-class recomputation | Trace/export/report observers derived from EvidenceLedger/FinalAnswerPacket | Projections cannot rebuild source obligation/final posture from trace-local facts. |

## Licensed / Closed / Target / Historical Glossary

- **Licensed surface:** allowed for this phase. The brief names the surface,
  scope, expected behavior, tests, and validation boundary.
- **Closed surface:** out of scope for this phase. Closed is a phase boundary,
  not a claim that the surface is architecturally complete.
- **Target surface:** intentionally being reduced, moved, simplified, or deleted
  over time. `core/pipeline_orchestrator.py` is a target surface for
  orchestrator-strangulation phases.
- **Historical surface:** preserved as record, not current doctrine.
- **Safety-sensitive surface:** high-custody behavior that needs explicit scope,
  such as provider/model routing, search depth, query behavior, prompts,
  citation behavior, Author prose, persistence shape, live validation, and
  secrets/private artifacts.

The legacy word "protected" should not mean sacred. It may remain in historical
docs or safety contexts, but current guidance should prefer licensed, closed,
target, historical, or safety-sensitive when those words are clearer.

## Presentability Audit Findings

Current-looking or easy-to-misread docs inspected:

| Document | Finding | Action this phase | Remaining risk |
| --- | --- | --- | --- |
| `docs/architecture/SCRYRAVEN_CURRENT_STATE.md` | Current-sounding filename previously contained a long Controller-era rollup and "orchestrator untouched" language. | Replaced with a short current-state redirect stub. Moved old body to `docs/history/architecture/SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md`. | Low; old text is preserved under a clearly historical path. |
| `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md` | Legacy Controller-handoff playbook can look like current default doctrine. | Added AG-94G vocabulary note and target-surface warning. | Body remains intentionally legacy. |
| `docs/product/AG81B_R1_ANSWER_WORTHINESS_AND_GOLDEN_EXAMPLES.md` | Product defect taxonomy still names Controller/AnswerContract as future defect owners. | Added authority-routing note. | Body remains product-useful but not current authority routing. |
| `docs/architecture/AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md` | Correct input audit, but records `pipeline_orchestrator.py` line delta `0` and older protected wording. | Added AG-94G clarification note. | Historical body remains unchanged. |
| AG74 through AG79 Controller/orchestrator docs | Historical phase records, many with Controller-era doctrine and "untouched" guards. | Left alone. | Historical only; current guidance now routes through RunAuthority and AG94G. |

## Naming Ambiguity Inventory

No package, CLI, env, database, session, or compatibility symbol rename was
performed.

| Name / surface | Classification | Current status | Action |
| --- | --- | --- | --- |
| ScryRaven | public-facing canonical name | README, AGENTS, docs, `scryraven` package use it. | Keep. |
| repo `aidan600/scryraven` | public-facing canonical repo | Matches public project identity. | Keep. |
| `scryraven/__main__.py` and `python -m scryraven` | public-facing canonical CLI shim | Delegates to `proplex.__main__`. | Keep; do not rename internals in this phase. |
| ProPlex | historical/private and compatibility name | Present in historical docs, `proplex` package, README compatibility notes, validation docs. | Historical or internal compatibility acceptable; future rename candidate. |
| FauxPlex / FauxPlexity | historical private names | Present in historical docs. | Historical only; do not touch. |
| `proplex` package and `python -m proplex` | internal compatibility acceptable | Required by existing CLI/tests and compatibility docs. | Do not touch yet. |
| `PROPLEX_*` env vars | internal compatibility acceptable | Present in CLI env aliases, tests, `core/db.py`, docs. | Do not touch yet. |
| `proplex.db` and `proplex_*` state keys | internal compatibility acceptable | Present as DB/session/state compatibility naming. | Do not touch yet. |
| `core/prompts.py` docstring "Prompt bundles for ProPlex" | public/presentability confusing | Current-looking code comment still says ProPlex. | Future dedicated compatibility rename/presentability phase. |
| Historical validation docs using ProPlex live commands | historical only | Preserve as validation history. | Do not rewrite wholesale. |

Future rename work needs a dedicated compatibility phase with CLI/env/DB/session
aliases, docs, tests, and deprecation policy. It should not be bundled with
orchestrator strangulation.

## Code Extraction Performed

Performed exactly one extraction:

- Moved `_extract_final_answer_source_ids()` and
  `_final_answer_source_citation_telemetry()` from
  `core/pipeline_orchestrator.py` to `core/post_author_output_projection.py`.
- Kept `_final_answer_source_citation_telemetry` imported into
  `pipeline_orchestrator.py` so existing compatibility imports and tests still
  resolve.
- Preserved behavior: given the same final report text and quantitative packet
  source IDs, the helper returns the same sorted cited-source IDs, packet-only
  source IDs, divergence boolean, and shadow-mode marker.

This is a trace/projection observer extraction. It does not move provider,
model, search, retrieval, query, ranking/filtering, citation selection, Author
prose, final answer behavior, persistence shape, package names, CLI names, env
vars, or DB/session names.

Pipeline line delta: `core/pipeline_orchestrator.py` changed from 4,760 lines to
4,730 lines on this branch, with `git diff --numstat` showing 1 insertion and
31 deletions for a net `-30` lines.

First recommended next extraction target: retrieval stop/continue
subordination. It is behavior-bearing, has a bounded controller module, already
uses a RunKernel checkpoint, and can be attacked with focused parity tests. Do
not start with provider/search execution, Author/final-answer prompt assembly,
or the full controller loop spine.

## Protected/Closed Surfaces Kept Closed

The following safety-sensitive or closed surfaces were not changed:

- live provider/model/search/retrieval calls;
- secrets, `.env`, API keys, DB rows, raw provider payloads, raw prompts,
  private logs, caches, full raw traces, local output packets, and private
  artifacts;
- provider swap, provider integration, provider order, provider routing,
  provider selection, and provider/search depth behavior;
- query generation/finalization, recency merge, official-bias insertion,
  ranking, filtering, source selection, and retrieval loop behavior;
- Author prose, Author prompt semantics, final-answer wording, citation
  selection, citation formatting, and source-list identity;
- package, CLI, env, database, session, and `proplex` compatibility names;
- broad pipeline or orchestrator rewrite.

## Tests / Checks Run

Passed locally:

- `py -m pytest -q tests/test_ag94g_orchestrator_strangulation_guidance.py`
  - `6 passed`
- `py -m pytest -q tests/test_ag94f_r1_weak_corpus_official_authority_admission.py`
  - `18 passed`
- `py -m pytest -q tests/test_ag94e_generic_official_authority_acquisition_benchmark.py`
  - `22 passed`
- `py -m ruff check .`
  - passed
- `py -m pytest -q`
  - `2911 passed, 1 deselected, 1 xfailed`
- `py -m pre_commit run --all-files`
  - passed: merge-conflict check, EOF fixer, trailing whitespace, YAML, ruff,
    and detect-secrets

The old AG-77 through AG-86 static orchestrator guards were updated narrowly to
allow the AG-94G final-answer source telemetry extraction while still rejecting
broad or unrelated `pipeline_orchestrator.py` rewrites.

## Review Of Old "Protected Surface" Usage

Changed current guidance:

- `AGENTS.md`
- `docs/codex/CODEX_GUIDANCE_MAP.md`
- `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md`
- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- `docs/codex/EXECUTION_PLAN_TEMPLATE.md`
- `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md`

Left historical docs alone except for short supersession or routing notes:

- `docs/architecture/AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md`
- `docs/product/AG81B_R1_ANSWER_WORTHINESS_AND_GOLDEN_EXAMPLES.md`

Updated old static guards:

- AG-77 through AG-86 tests no longer encode orchestrator-untouched as the only
  acceptable success shape. They permit this named projection-helper extraction
  and continue to fail broad or unrelated orchestrator edits.

Moved stale current-looking history:

- `docs/architecture/SCRYRAVEN_CURRENT_STATE.md` is now a redirect stub.
- The old body is preserved at
  `docs/history/architecture/SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md`.

Remaining uses of "protected" are intentional when they appear in historical
phase records, safety contexts, or the glossary sentence explaining that
"protected" must not mean sacred.

## Decision Packet For Next Strangler Phase

1. Is `pipeline_orchestrator.py` still behavior-bearing?
   - Yes. It still hosts provider/model/search callsites, retrieval loop
     scheduling, stop/continue helpers, controller-spine dispatch, source-class,
     weak-corpus, conflict, supplemental, Linkup, Author-adjacent, and
     trace/session compatibility regions.
2. Which behavior-bearing island should be strangled first?
   - Retrieval stop/continue.
3. Which owner should receive it?
   - RunState/SearchJudgment stop posture under RunKernel, with
     `retrieval_stop_controller.py` demoted to a bounded executor or adapter.
4. Did this phase implement a safe extraction?
   - Yes. It moved final-answer source citation telemetry to
     `post_author_output_projection.py`.
5. What remains in `pipeline_orchestrator.py`?
   - Lifecycle coordination plus the behavior-bearing islands inventoried above.
     Economist ordinary execution is no longer one of those islands; only
     passive legacy compatibility data remains for the next census.
6. Which docs were updated to stop protecting the orchestrator by default?
   - `AGENTS.md`, Codex guidance map, RunAuthority guide, Architecture Groove
     playbook, phase/execution templates, Controller playbook note, AG94C note,
     SCRYRAVEN current-state redirect stub, historical moved copy, and AG81B-R1
     routing note.
7. Which current-looking docs remain misleading?
   - `SCRYRAVEN_CURRENT_STATE.md` no longer carries the stale body.
     `CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md` remains intentionally
     legacy. `AG81B_R1_ANSWER_WORTHINESS_AND_GOLDEN_EXAMPLES.md` remains
     product-useful but not current authority routing.
8. What naming ambiguity should be deferred to a dedicated rename phase?
   - `proplex` package, `python -m proplex`, `PROPLEX_*`, `proplex.db`,
     `proplex_*` state keys, and current-looking ProPlex docstrings/comments.
9. What should the next Codex phase do?
   - Implement a narrow retrieval-stop/continue strangler: inventory current
     consumers, introduce a canonical RunState/SearchJudgment stop posture, make
     the retrieval loop consume it, demote the old stop controller path to a
     bounded adapter, and prove no provider/search/depth/query/Author/citation
     behavior changes.
