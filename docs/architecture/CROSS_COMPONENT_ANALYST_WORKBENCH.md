# Cross-Component Analyst Workbench

Status: current supporting Workbench and provenance reference.
Authority: none as selected-target architecture.
Default-read: no

This document records **INSTALLED** Boundary B consumption, durable
proposal-only Workbench rules, and **HISTORICAL** V0 design/phase-planning
material from retired compatibility implementations. Installed bounded
multi-component execution lives in
[MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md).
Selected AnalystOS target topology, including Cross consumption, belongs only to
[AnalystOS Operating Model](ANALYSTOS_OPERATING_MODEL.md). This document does
not define a second target architecture and does not define D-prime as the
selected or future required consumption path.

Durable current Workbench rules:

- proposal-only / no self-admission;
- no raw packet mega-prompt;
- no direct retrieval dispatch;
- no Author glue;
- compact component refs;
- RunKernel authority.

Mode: REPAIR.

Phase: `MULTICOMPONENT-CROSS-COMPONENT-ANALYST-DOCTRINE-01`.

Verdict target: NO-BUT-JUSTIFIED.

The original phase was a docs/process REPAIR with no app delta. It was justified
because it prevents fake graph scheduling, parallel Analyst drift,
D-prime-as-Analyst, direct retrieval dispatch, FAP synthesis, and Author glue
before the next Build checkpoint: `COMPONENTWORKGRAPH-V0-NOEXEC-CONTRACT-01`.

That checkpoint and the subsequent V0 contract sequence were historically
merged. Their compatibility implementations have been retired; the sequence
remains **HISTORICAL** provenance, not ordinary product consumption or
selected-target architecture. Phase 1
`AG-MULTICOMPONENT-ORDINARY-END-TO-END-SYNTHESIS-01` now installs the separate
ordinary V1 product path. SearchOS Boundary B now consumes its typed
query-resolution proposals.

## Installed Boundary B Consumption

Cross-Component Analyst may emit the shared
`analyst_query_resolution_proposal_v1` only from its exact current graph and
contract input. It may propose a searched premise or an inferred conclusion,
but it cannot admit either. Deterministic arbitration permits mutation only for
one exact noncompeting winner and is independent of list, arrival, scheduling,
and confidence order. Exact replay identity remains bound to the originating
artifact and recorded parent state.

For a searched-premise winner, ContractAmendment v2 and RunKernel own contract
mutation; SearchOS retrieves direct evidence for the premise; **INSTALLED:**
Component Analyst forms the self-audited direct-support case and RunKernel
admits the exact current support state directly; and Graph V1 schedules a
fresh affected-only Cross-Component Analyst pass. Cross-Component Analyst then
proposes the exact target-mapped
relationship; **INSTALLED:** synthesis D-prime validates it; RunKernel admits
the exact current graph/synthesis state. SearchOS and Scrutineer do not author
inference. The installed semantic ceilings are depth 1 in Fast/Balanced and
depth 2 in Deep. Selected recovery and Cross consumption belong only to
[AnalystOS Operating Model](ANALYSTOS_OPERATING_MODEL.md).

The original V0 doctrine in this document did not itself implement the
Workbench. **INSTALLED** ordinary V1 now consumes Cross-Component Analyst,
ComponentWorkGraph, synthesis D-prime, graph admission, scheduling, bounded
recovery/inference, FAP, Author, and multi-component answering through their
current canonical owners. Live validation and arbitrary-query coverage remain
nonproofs.

The Workbench contract alone is not a producer. Ordinary N>=2 product work needs
a real dedicated configured-SmartModel Cross-Component Analyst call. That role
may propose first-class synthesis nodes and semantic edges over admitted
component/synthesis refs. It may not validate its own proposal as a separate
review authority, canonically admit graph state, dispatch recovery, or render
answer prose. **INSTALLED:** a separate configured-SmartModel synthesis D-prime
validates; full Scrutineer challenges when triggered; RunKernel alone admits or
authorizes recovery. That installed D-prime consumer is not selected-target
doctrine.

## Capability Inventory / Reuse-First Gate

| Surface | Existing owner module/doc | Current status | Action | Why not duplicate | Tests/guards |
| --- | --- | --- | --- | --- | --- |
| ComponentWorkNode V0 | `core/component_work_node.py`; `tests/test_component_work_node_01.py` | Current product-path projection / typed review contract over one component lane. | REUSE | It already preserves per-component refs and explicitly rejects graph/scheduler/budget/FAP/Author/correctness claims. | `tests/test_component_work_node_01.py` guards single-component shape, false closed-downstream flags, raw/private false posture, and no multi-component claims. |
| Per-component Analyst Workbench | `docs/architecture/ANALYST_WORKBENCH_FULL_SLICE.md`; `core/analyst_workbench_runtime.py`; `core/current_source_analyst_finding_proposal.py` | Proposal-only product-consumed Workbench for current-source single-fact lane. | ADAPT BY DOCTRINE | Cross-component Workbench must extend proposal-only posture, not create a second Analyst system. | Workbench runtime and report checks preserve proposal-only candidate roles, gaps, D-prime dossier refs, and no search dispatch. |
| Component D-prime compatibility | `docs/architecture/DPRIME_ARCHITECTURE.md`; `core/multicomponent_role_runtime.py` | Retained only for the explicit legacy SearchOS recovery corridor; it has no ordinary component producer or consumer. | RETAIN AS COMPATIBILITY ONLY | The installed ordinary component path is Component Analyst self-audit followed by direct RunKernel admission; see [AnalystOS Operating Model](ANALYSTOS_OPERATING_MODEL.md). | RunKernel and Slice-A tests guard direct admission and reject ordinary Component-D-prime execution. |
| Same-component multi-source posture | `core/dprime_multi_source_analyst_scrutiny_runtime.py`; `tests/test_dprime_multi_source_analyst_and_scrutiny_01.py` | One component, one source-obligation lane only; rejects cross-component misuse. | REUSE AS NEGATIVE BOUNDARY | Do not mistake multi-source for multi-component. | Multi-source guards require one answer component and one source-obligation lane and reject multi-component synthesis claims. |
| Follow-up / recovery re-entry | `core/runkernel_followup_search_reentry_ordinary_search_runtime.py`; `tests/test_runkernel_followup_search_reentry_using_ordinary_search_01.py` | RunKernel-owned ordinary search re-entry for one D-prime follow-up need. | REUSE / GENERALIZE BY DOCTRINE ONLY | Future cross-component recovery requests must enter RunKernel authorization and ordinary search, not a new retrieval path. | Follow-up re-entry guards D-prime need as non-dispatch, RunKernel authorization, ordinary search reuse, and no live/provider calls in offline proof. |
| RunKernel / AnswerContract / contract mutation | `docs/architecture/RUN_CONTRACT_SEMANTIC_LOOP.md`; `core/run_kernel.py` | Root authority and typed contract mutation owner. | REUSE | Graph and synthesis admission must be RunKernel-owned. | Semantic-loop and RunKernel tests guard admission, reducer ownership, accepted/current contract mutation, and no worker-owned authority. |
| SufficiencyReadiness / FAP / Author | `docs/architecture/FAP_AUTHOR_BOUNDARY.md`; `docs/architecture/RUN_CONTRACT_SEMANTIC_LOOP.md` | Downstream packaging/rendering only. | KEEP CLOSED | They must not synthesize or glue component outputs. | FAP and Author doctrine guard readiness consumption, constrained packaging, constrained prose, no evidence interpretation, and no product-correctness claim. |

## 1. Historical Architecture Verdict

**HISTORICAL** phase verdict from
`MULTICOMPONENT-CROSS-COMPONENT-ANALYST-DOCTRINE-01`. This is provenance, not a
current selected-target Architecture Verdict and not a "smallest safe next
architecture step."

Historical verdict:

```text
Cross-Component Analyst Workbench doctrine/docs first.
No graph code yet.
No two-node proof yet.
No FAP / Author / source display yet.
```

Why that historical phase blocked fake graph authority:

- The risk was not lack of graph code. It was the wrong graph story:
  `component A final + component B final + component C final -> Author glues`.
- Current code already had a same-component, multi-source lane and a
  `ComponentWorkNode` V0 projection over one component lane. Treating that as
  multi-component execution would launder a single-lane proof into graph
  authority.
- Multi-component work needed one proposal-only cross-component synthesis layer
  between per-component lanes and RunKernel graph admission.
- The doctrine had to preserve RunKernel ownership of authorization, admission,
  reduction, contract mutation, and follow-up/recovery re-entry.

The durable rejected path remains:

```text
component A final
+ component B final
+ component C final
-> Author glues
```

Do not treat the historical V0 sequence, installed synthesis D-prime, or this
old verdict as selected-target architecture. Selected Cross consumption is owned
only by [AnalystOS Operating Model](ANALYSTOS_OPERATING_MODEL.md).

## 2. Layer Responsibilities (Installed Historical Table)

The table below records **installed** and historical phase boundaries. Selected
target consumption is defined in
[AnalystOS Operating Model](ANALYSTOS_OPERATING_MODEL.md). Separate D-prime is
not the selected or future required validation path.

| Surface | May propose? | May validate? | May admit? | May render? | May request more search/recovery? | Must not do |
| --- | --- | --- | --- | --- | --- | --- |
| RunKernel | No semantic claim proposal by itself. It may create authority actions and reducers. | Yes, structural/admission validation and reducer gating. | Yes. It owns admission, rejection, challenge, recovery authorization, and contract mutation. | No. | Yes, by authorizing bounded ordinary search/recovery work from proposal refs. | Must not become an orchestrator brain, LLM thinker, Author, or direct provider/search bypass. |
| AnswerContract | No. It records accepted obligations, statuses, and refs. | No independent validation. | No. Mutation is admitted through RunKernel. | No. | No. | Must not mutate itself, synthesize across components, or substitute for RunKernel admission. |
| ComponentWorkGraph | V0 no-execution graph may carry proposed/admitted refs only. | No independent validation. | No. | No. | No. It may carry recovery request refs produced elsewhere and admitted by RunKernel. | Must not schedule, dispatch search, run nodes, create budget leases, execute parallelism, synthesize, or feed Author directly. |
| ComponentWorkNode | No. It projects one component lane. | It may validate its own typed ref shape only. | No. | No. | No. | Must not merge components, collapse source-obligation lanes, create graph/scheduler/budget/FAP/Author/source-display/citation/product-correctness claims, or treat candidate/fetch-read refs as support. |
| Per-component Analyst Workbench | Yes, proposal-only findings, candidate roles, gaps, and dossier refs for one component lane. | No authority validation. | No. | No. | It may propose gaps/recovery needs only. | Must not dispatch search, admit evidence, satisfy source obligations, decide Sufficiency, create FAP/Author output, or claim correctness. |
| Per-component D-prime compatibility (**no ordinary consumer**) | Retained only as a bounded compatibility contract. Ordinary component meaning is the Component Analyst case plus deterministic RunKernel admission. | No ordinary component validation. | No. RunKernel admits. | No. | No ordinary recovery request. | Must not re-enter the ordinary component path, become a second review authority, authorize search, or admit support. |
| Cross-Component Analyst Workbench | Yes, proposal-only synthesis claims, consistency/dependency findings, missing-component proposals, contradiction posture, and recovery proposal refs. | Self-audit only as part of case construction in selected target. | No. | No. | It may propose cross-component recovery or missing-component needs only. | Must not admit evidence, canonically validate its own synthesis, replace RunKernel, collapse component refs into an untraceable summary, launch search, create a second Analyst system, or feed Author directly. |
| Synthesis D-prime validation (**installed; selected retirement**) | It may emit validation/challenge/follow-up-need refs about a proposed synthesis claim. | Yes, cross-component synthesis validation over component refs and dependency refs when installed. | No. RunKernel admits. | No. | It may emit a need/challenge only. | Must not become Cross-Component Analyst, invent evidence, drop caveats, resolve dependencies by itself, dispatch search, or package final prose. |
| SufficiencyReadiness | No synthesis proposal. | Yes, readiness reduction after admitted refs exist, under RunKernel ownership. | No evidence or synthesis admission. | No. | It may preserve follow-up-required or blocked posture only. | Must not synthesize component outputs, dispatch search, create FAP, render prose, or claim product correctness. |
| FAP | No. | No evidence/synthesis validation. | No. | It packages, but does not render prose. | No. | Must not synthesize, glue component finals, decide source authority, drop caveats, dispatch search, or create new claims. |
| Author | No. | No. | No. | Yes, constrained prose from hardened FAP only when opened by a later phase. | No. | Must not glue component outputs, reinterpret evidence, resolve conflicts, decide source authority, drop caveats, infer missing context, dispatch search, or upgrade weak support. |
| Retrieval / follow-up re-entry | No independent proposal. It consumes proposal refs from Workbench/Analyst surfaces. | It validates authorization conditions only where RunKernel owns the loop. | RunKernel admits/authorizes. | No. | Yes, only as RunKernel-authorized ordinary search/recovery work. | Must not create a new retrieval path, bypass ordinary search, dispatch from Analyst/FAP/Author/ComponentWorkGraph, or run live calls without explicit live license. |

## 3. Retrieval And Recovery Loop (Historical Installed Posture)

Recovery may originate from Workbench gaps, Analyst/Cross dependency gaps, or
**INSTALLED** D-prime challenges. Selected recovery return belongs only to
[AnalystOS Operating Model](ANALYSTOS_OPERATING_MODEL.md); this loop is
installed/historical posture, not a second target architecture.

The loop posture is:

1. Per-component recovery proposals are allowed.
2. Cross-component recovery proposals are allowed.
3. Missing component proposals are allowed.
4. Workbench and Analyst propose only.
5. **INSTALLED:** synthesis D-prime validation may still execute for genuine
   N>=2 work. Ordinary component D-prime has no consumer. That remaining
   synthesis consumer is not selected-target doctrine.
6. RunKernel authorizes, admits, reduces, mutates contract state, and records
   terminal blocker posture.
7. Analyst must not directly dispatch search.
8. FAP and Author must not dispatch search.
9. ComponentWorkGraph must not directly dispatch search.
10. Recovery re-enters through RunKernel-owned ordinary search and existing
    candidate/fetch-read/custody/analysis/admission seams when a later phase
    licenses execution.

Loops are bounded by:

- mode;
- parent budget;
- component budget;
- recovery attempts;
- missing-component caps;
- duplicate-work checks;
- logical depth;
- terminal blockers;
- explicit live-call licenses when live work is requested.

Logical concurrency is not runtime parallelism. A graph may represent independent
components, blocked dependencies, and serial-compatible ordering without opening
parallel execution. Local-model constraints require serial-compatible execution:
any future graph admission or Workbench path must be runnable in serial form even
if later provider/model capacity allows parallelism.

## 4. Minimum Viable Cross-Component Analyst Workbench

Minimum viable Cross-Component Analyst Workbench is a proposal-only synthesis
surface over compact component refs.

It must answer:

- Are component outputs consistent?
- Does one component constrain another?
- Does one component make another stale, insufficient, overbroad, or not
  applicable?
- Is there a missing component?
- Is there a cross-component contradiction?
- Is there an unresolved dependency?
- What synthesis claim is being proposed?
- What component refs support that synthesis claim?
- What evidence/source refs must be revisited?

It may produce:

- proposed synthesis claim refs;
- component-dependency refs;
- consistency/contradiction posture refs;
- missing-component proposal refs;
- unresolved-dependency refs;
- recovery proposal refs;
- caveat/nonclaim refs.

**INSTALLED** Workbench packets may still carry synthesis D-prime dossier refs.
Those refs are installed/historical packet fields, not a requirement of the
minimum viable future Cross artifact.

It must not:

- admit evidence;
- claim correctness;
- render final prose;
- replace RunKernel;
- collapse component refs into an untraceable summary;
- launch search;
- create a second Analyst system beside the existing Analyst Workbench;
- treat component finals as Author-ready prose;
- become component finals glued by FAP or Author;
- treat multi-source posture as multi-component synthesis.

The Workbench extends the current Analyst Workbench posture by doctrine: it
keeps proposal-only behavior, compact dossier refs, and no dispatch. It does not
fork an alternate Analyst authority path.

## 5. Installed Synthesis D-prime And Retired Ordinary Component D-prime

**INSTALLED** ordinary product execution no longer uses a separate per-component
D-prime consumer. Component meaning is the current Component Analyst case plus
deterministic RunKernel admission.

**INSTALLED** synthesis D-prime still performs cross-component synthesis
validation over component refs and dependency refs. Dual ordinary D-prime is
not installed-target architecture. Selected Cross consumption is owned only by
[AnalystOS Operating Model](ANALYSTOS_OPERATING_MODEL.md).

**COMPATIBILITY** per-component D-prime may remain as a bounded contract with no
ordinary work producer. It is not the ordinary evidence-relative support path.

**INSTALLED** synthesis D-prime asks whether component A plus component B
support synthesis claim S without inventing evidence, dropping caveats, erasing
blockers, or changing component scope. It validates the Workbench synthesis
proposal against component refs, dependency refs, caveats, contradiction
posture, missing evidence, and RunKernel refs.

**INSTALLED** synthesis D-prime may produce:

- supported/partially-supported/unsupported synthesis validation refs;
- contradiction/challenge refs;
- missing-dependency refs;
- caveat-preservation refs;
- follow-up-need refs for RunKernel consideration.

**INSTALLED** synthesis D-prime must not become the Cross-Component Analyst. It
does not invent the synthesis claim, select missing components, rewrite
component outputs, authorize search, admit support, reduce contract state,
package FAP, or write Author prose.

## 6. Historical ComponentWorkGraph V0 No-Execution Shape

**HISTORICAL** `ComponentWorkGraph` V0 is a no-execution, no-scheduler,
no-runtime-parallelism contract shape. It may carry typed refs, digests,
statuses, counts, and closed-surface flags only. These V0 fields describe the
merged historical contract, not required fields of a future selected-target
graph.

Minimum historical V0 fields:

- graph id;
- parent run id/ref;
- user query ref;
- supported query class;
- answer contract ref;
- component node refs;
- dependency edges;
- blocking dependencies;
- recovery request refs;
- missing component proposal refs;
- Cross-Component Analyst refs;
- synthesis proposal refs;
- D-prime synthesis validation refs (**HISTORICAL/INSTALLED** packet field, not
  a selected-target graph requirement);
- RunKernel admission refs;
- graph status;
- closed downstream flags;
- raw/private false flags;
- nonclaims.

Raw content is forbidden. A graph must not carry raw provider payloads, raw
search responses, raw source text, raw prompts, raw model responses, DB/cache
rows, private logs, caches, local output packets, or full traces. It must use
typed refs, digests, statuses, counts, and explicit false flags.

Closed downstream flags must include, at minimum:

- graph did not execute nodes;
- graph did not schedule runtime work;
- graph did not create budget leases;
- graph did not dispatch search;
- graph did not call providers/models/fetch/read/retrieval;
- graph did not admit evidence;
- graph did not create SufficiencyReadiness;
- graph did not create FAP;
- graph did not create Author output;
- graph did not render citations;
- graph did not claim product correctness.

## 7. Context Management

Cross-component analysis must not dump all component packets into one
mega-prompt.

The Cross-Component Analyst Workbench consumes compact `ComponentWorkNode`
outputs:

- admitted claims;
- proposed claims;
- nonclaims;
- caveats;
- contradictions;
- source roles;
- source refs;
- evidence refs;
- missing evidence;
- unresolved blockers;
- recovery history;
- D-prime refs (**INSTALLED** compact-ref vocabulary, not a selected-target
  required consumer);
- RunKernel refs;
- ComponentCoverage refs;
- source-obligation/citation-handoff refs.

More detail requires typed detail requests and RunKernel authorization. Detail
requests must name:

- requesting surface;
- component ref;
- requested detail class;
- reason the compact ref is insufficient;
- raw/private false posture;
- maximum detail budget;
- authorization/refusal status.

This keeps the Workbench from becoming a raw packet merger, prompt dump, hidden
retrieval path, or unbounded context sink.

## 8. Historical V0 Phase Sequence

This sequence is retained to explain the provenance and boundaries of the
merged V0 contracts. It is **HISTORICAL** and is not current next-step doctrine.
The ordinary Phase 1 path superseded it for the supported class. Do not read
the named V0 successors below as the current implementation gate.

### 1. MULTICOMPONENT-CROSS-COMPONENT-ANALYST-DOCTRINE-01

Mode: REPAIR.

Purpose: Define the architecture doctrine and next phase boundaries before graph
contracts or synthesis runtime are opened.

Opened surfaces: repo docs/architecture doctrine, narrow crosslinks, and
docs/static posture tests only.

Closed surfaces: Python runtime behavior, ComponentWorkGraph implementation,
Cross-Component Analyst runtime implementation, synthesis D-prime runtime,
graph admission, scheduling, runtime parallelism, budget leases, FAP, Author,
source display, citation rendering, live validation, and product correctness.

Pass condition: repo-visible doctrine blocks fake graph, fake scheduler,
parallel Workbench, D-prime-as-Analyst, FAP synthesis, Author glue, and direct
retrieval dispatch by Analyst, D-prime, FAP, Author, or ComponentWorkGraph.

Fail/stop condition: doctrine cannot define a non-parallel Cross-Component
Analyst Workbench reusing existing Workbench, D-prime, RunKernel,
ComponentWorkNode, follow-up, and FAP/Author boundaries.

Likely files: this document, `RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md`,
`ANALYST_WORKBENCH_FULL_SLICE.md`, `DPRIME_ARCHITECTURE.md`,
`RUN_CONTRACT_SEMANTIC_LOOP.md`, `CODEX_GUIDANCE_MAP.md`, and a narrow
docs/static test.

Tests/checks: docs/static posture checks only; no live validation.

Why this avoids fake graph, parallel Analyst, or Author glue: it creates no
runtime graph, names the Workbench as proposal-only adaptation of existing
Analyst posture, and keeps FAP/Author closed.

### 2. COMPONENTWORKGRAPH-V0-NOEXEC-CONTRACT-01

Mode: BUILD.

Purpose: Define a typed no-execution ComponentWorkGraph V0 contract over compact
refs after this doctrine is merged.

Opened surfaces: graph contract docs and, only if the phase explicitly licenses
it, a typed no-execution validator plus docs/static or unit guards for refs,
raw/private false flags, closed downstream flags, and nonclaims.

Closed surfaces: graph execution, scheduler, runtime parallelism, budget lease
implementation, multi-component query planning, retrieval dispatch,
Cross-Component Analyst runtime, synthesis D-prime runtime, FAP, Author, source
display, citation rendering, live validation, and product correctness.

Pass condition: graph V0 can represent component refs, dependency edges,
blockers, recovery refs, Workbench refs, synthesis D-prime refs, and RunKernel
admission refs without executing or scheduling anything.

Fail/stop condition: the contract needs executable node behavior, scheduler
policy, provider/model/search/fetch/read calls, raw content, or FAP/Author
consumption to be meaningful.

Likely files: `docs/architecture/CROSS_COMPONENT_ANALYST_WORKBENCH.md`,
`docs/architecture/RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md`, possible future
`core/component_work_graph.py` only if explicitly licensed, and narrow tests.

Tests/checks: docs/static guard and focused no-execution contract tests if a
typed contract is licensed.

Why this avoids fake graph, parallel Analyst, or Author glue: V0 is a ref
contract, not an executor. It carries Workbench and validation refs but cannot
run nodes, dispatch search, synthesize, or render.

### 3. CROSS-COMPONENT-SYNTHESIS-PROPOSAL-V0-01

Mode: BUILD.

Purpose: Introduce the minimum Cross-Component Analyst Workbench proposal shape
over compact ComponentWorkNode/ComponentWorkGraph refs.

Opened surfaces: proposal-only Workbench docs/contract/runtime if licensed,
compact component ref input, synthesis proposal refs, dependency refs,
missing-component proposal refs, recovery proposal refs, and D-prime synthesis
dossier refs.

Closed surfaces: synthesis validation, RunKernel admission, graph execution,
scheduling, runtime parallelism, retrieval dispatch, live calls, FAP, Author,
source display, citation rendering, and product correctness.

Pass condition: Workbench can propose consistency/dependency/contradiction/
missing-component/synthesis posture while preserving component refs and
explicitly remaining non-authority.

Fail/stop condition: Workbench needs to validate its own synthesis, admit
evidence, mutate contract state, launch search, or produce Author-ready prose.

Likely files: new Cross-Component Analyst Workbench contract/runtime only if
licensed, this doctrine, Workbench docs, D-prime docs, and narrow tests.

Tests/checks: proposal-only shape guards, no raw/private retention, no dispatch,
no admission, no FAP/Author/source-display flags.

Why this avoids fake graph, parallel Analyst, or Author glue: it adapts the
existing Workbench proposal posture and stops before synthesis validation,
RunKernel admission, or downstream packaging.

### 4. DPRIME-SYNTHESIS-VALIDATION-V0-01

Mode: BUILD.

Status: Introduced as `core.dprime_synthesis_validation` plus focused
validation guards. It remains validation-only and is not RunKernel admission,
AnswerContract mutation, graph execution, retrieval authorization, FAP, Author,
source display, citation rendering, or product correctness.

Purpose: Add synthesis D-prime validation over Cross-Component Analyst synthesis
proposal refs, component refs, dependency refs, caveats, contradictions, and
missing-evidence posture.

Opened surfaces: synthesis D-prime docs/contract/runtime if licensed,
validation refs, challenge refs, caveat-preservation refs, and follow-up-need
refs for RunKernel consideration.

Closed surfaces: Cross-Component Analyst proposal generation, RunKernel
admission, graph execution, scheduling, retrieval dispatch, live calls,
SufficiencyReadiness, FAP, Author, source display, citation rendering, and
product correctness.

Pass condition: synthesis D-prime validates whether component A plus component B
support synthesis claim S without inventing evidence, dropping caveats, erasing
blockers, or changing component scope.

Fail/stop condition: D-prime has to choose the synthesis claim, perform
Workbench analysis, authorize search, admit support, mutate contract state, or
render prose.

Files: `core/dprime_synthesis_validation.py`,
`tests/test_dprime_synthesis_validation_v0_01.py`, D-prime architecture docs,
and narrow cross-component posture docs.

Tests/checks: validation-shape guards, no Analyst replacement, no admission, no
dispatch, no FAP/Author/source-display flags.

Why this avoids fake graph, parallel Analyst, or Author glue: D-prime validates
a Workbench proposal and remains non-authority until RunKernel admission.

### 5. RUNKERNEL-COMPONENT-GRAPH-ADMISSION-V0-01

Mode: BUILD.

Status: Introduced as `core.runkernel_component_graph_admission` plus focused
validation guards. It is a RunKernel-owned ref admission contract only and is
not graph execution, scheduling, runtime parallelism, retrieval authorization,
SufficiencyReadiness, FAP, Author, source display, citation rendering, or
product correctness.

Purpose: Define RunKernel admission for no-execution ComponentWorkGraph and
synthesis validation refs.

Opened surfaces: RunKernel admission contract/runtime, admission decision refs,
blocker/challenge refs, bounded recovery authorization refs, and candidate or
accepted graph/synthesis state refs.

Closed surfaces: scheduler, runtime parallelism, budget lease implementation,
provider/model/search/fetch/read/retrieval execution, live validation,
SufficiencyReadiness expansion, FAP, Author, source display, citation rendering,
and product correctness.

Pass condition: RunKernel can admit, reject, challenge, or authorize bounded
ordinary recovery from no-execution graph/synthesis refs without executing the
graph or opening downstream rendering.

Fail/stop condition: admission requires runtime graph scheduling, direct
retrieval dispatch, live calls, FAP/Author changes, source display, citation
rendering, or product-correctness claims.

Files: `core/runkernel_component_graph_admission.py`,
`tests/test_runkernel_component_graph_admission_v0_01.py`, RunKernel
semantic-loop docs, ComponentWorkGraph docs, and narrow tests.

Tests/checks: admission-shape guards, no execution/scheduling, no direct
dispatch, no FAP/Author/source-display flags, and no raw/private retention.

Why this avoids fake graph, parallel Analyst, or Author glue: RunKernel admits
typed refs and blockers only. Execution, scheduling, readiness, packaging, and
rendering remain separate future phases.

### 6. MULTICOMPONENT-SERIAL-DRY-RUN-PLANNING-CHECKPOINT-01

Mode: BUILD.

Status: Introduced as `core.multicomponent_serial_dry_run_checkpoint` plus
focused serial-checkpoint guards. It is a review-only serial dry-run artifact
over existing ComponentWorkNode, ComponentWorkGraph, Cross-Component Analyst
Workbench, synthesis D-prime validation, and RunKernel graph/synthesis
admission refs. It is not graph execution, scheduling, runtime parallelism,
retrieval authorization, SufficiencyReadiness, FAP, Author, source display,
citation rendering, source-obligation satisfaction, friend-level MVP, or
product correctness.

Purpose: Show that a small multi-component scenario can be represented
serially, preserve component/dependency/caveat/blocker/nonclaim refs, and end in
RunKernel-admitted or honestly blocked graph/synthesis state without opening
runtime behavior.

Files: `core/multicomponent_serial_dry_run_checkpoint.py`,
`tests/test_multicomponent_serial_dry_run_planning_checkpoint_01.py`, and narrow
crosslinks in this doctrine set.

Tests/checks: serial checkpoint guards, no graph execution/scheduling/runtime
parallelism, no provider/model/search/fetch/read/retrieval calls, no
Sufficiency/FAP/Author/source-display/citation-rendering/source-obligation/
product-correctness claims, and no raw/private retention.

Why this avoids fake graph, parallel Analyst, or Author glue: the checkpoint
consumes typed refs already created by the graph, Workbench, D-prime, and
RunKernel admission contracts. It produces serial trace and review packet refs
only, and those refs are explicitly non-answer and non-rendering artifacts.

## Non-Proofs

This doctrine does not prove:

- multi-component query planning;
- ComponentWorkGraph execution;
- scheduler behavior;
- runtime parallelism;
- budget lease behavior;
- Cross-Component Analyst runtime behavior;
- synthesis D-prime runtime behavior;
- product-consumed RunKernel graph admission behavior beyond this deterministic
  ref contract;
- retrieval quality;
- live provider/model/search/fetch/read/retrieval behavior;
- source-obligation satisfaction;
- citation eligibility;
- citation rendering;
- FAP packaging;
- Author prose;
- product correctness.

No live validation is opened or claimed by this doctrine.
