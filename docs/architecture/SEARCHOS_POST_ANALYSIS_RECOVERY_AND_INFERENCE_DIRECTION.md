# SearchOS Post-Analysis Recovery And Inference Direction

Status: current approved direction
Authority: canonical:searchos-post-analysis-recovery-and-inference-direction
Default-read: no
Applies-to: post-analysis SearchOS recovery, derived-component recovery, stopping convergence, inference direction, and legacy recovery convergence
Does-not-authorize: implementation, live calls, provider claims, or activation of planned capabilities
Verified-against-runtime: 323ed6982aa131cda0dfe7c9bded9aad68f327a1

## Status Classification

This document uses the following status classes:

- **INSTALLED**: ordinary runtime behavior or retained executable legacy
  behavior exists at the verified baseline.
- **NEXT BUILD**: Internal PR A of the current parent checkpoint.
- **NEAR-TERM DIRECTION**: Internal PR B, which follows and consumes Internal
  PR A.
- **DEFERRED**: direction intentionally outside both internal PRs.
- **RETIRED AFTER REPLACEMENT**: authority or machinery that may be removed
  only after its canonical replacement is proved.

The parent roadmap checkpoint is
`SEARCHOS-GAP-RECOVERY-AND-STOP-CONVERGENCE-01`. It contains exactly two
ordered internal implementation PRs. Those PR boundaries are not separate
roadmap phases, and this governance document is not a product phase or an
installed capability.

## 1. Scope And Non-Goals

This document governs:

- post-analysis existing-component recovery;
- Analyst-derived component recovery;
- append-only SearchOS recovery cycles;
- whole-run stopping convergence;
- recovery generation depth;
- semantic inference preservation; and
- legacy authority retirement.

It explicitly excludes general nonzero inferred-component admission, recursive
navigation, provider/depth calibration, new providers, Map or Crawl, social
specialization, conversation, UI, compatibility rename, and live validation.
Those exclusions receive no implementation or live-call authority here.

## 2. Installed Current State

**INSTALLED:** first-wave SearchOS, initial and iterative SearchJudgment,
candidate READ, one-hop breadcrumb navigation, and the SearchOS semantic
handoff are ordinary product behavior. Component Analyst and component
D-prime, synthesis D-prime, ComponentCoverage, EvidenceLedger, Sufficiency,
FinalAnswerPacket, Author, ContractAmendment, and the component graph are also
installed owners or mechanics.

The installed path can retain SearchOS slots, action and query histories,
custody, local action budgets, and terminal reasons. SearchJudgment can select
current semantic handoff, exact candidate READ, an admitted QueryPlan follow-up,
one bounded breadcrumb, or unresolved handoff. READ and navigation custody may
reach the existing component Analyst / D-prime / RunKernel admission path.

**NOT INSTALLED:** canonical post-analysis SearchOS recovery cycles, a
whole-run recovery lease, and `recovery_generation_depth` policy. In
particular, the installed state does not yet represent recovery-purpose
identity, cycle ordinal, immutable prior-slot linkage to a new recovery slot,
or cumulative recovery expenditure across cycles.

## 3. Installed Legacy And Parallel Surfaces

The installed legacy reality has distinct classifications:

- **FORWARD_DEAD_CONFIRMED:** AG-92B has no forward ordinary execution after
  active SearchOS takes control. Its compatibility consumer is inert under the
  canonical owner gate, and its remaining Sufficiency dependency is inert
  vocabulary. Physical files, direct tests, and compatibility plumbing still
  exist.
- **INSTALLED LEGACY / GATED:** old component-gap and ordinary source-class
  recovery surfaces retain compatibility, test, state, or isolated executable
  mechanics. They are forward-dead or gated on the ordinary SearchOS path, but
  they have not all been physically removed.
- **INSTALLED LEGACY / EXECUTABLE:** one bounded dynamic derived-component
  recovery remains executable. It begins with a Scrutineer missing-component
  proposal, deterministically constructs a component and ContractAmendment,
  and uses a separate recovery planner/acquisition lane. Its amendment,
  graph-reentry, selective-recomputation, and downstream mechanics are useful;
  its proposal and recovery authority are not the approved future model.

Existing source hierarchy and currentness belong to EvidenceLedger, query
nonredundancy belongs to QueryPlan, and final partial, insufficient, exhausted,
and blocked posture belongs to Sufficiency. No AG-92B helper is presumed
mandatory to port. A legacy predicate may be retained or adapted only if an
implementation trace proves a genuinely missing canonical behavior.

The phrase “recovery is installed” is therefore too broad, and “recovery is
uninstalled” is false. Canonical post-analysis SearchOS recovery is not
installed; legacy derived-component recovery is executable; older
existing-gap routes are forward-dead or gated and retain residual surfaces.

## 4. Authority Doctrine

| Owner | Canonical responsibility | Prohibited authority |
| --- | --- | --- |
| Scrutineer | Supervisory and adversarial review; identify defects, contradictions, unsupported reasoning, unresolved nodes, and exact findings for Analyst. | Authoring components or ContractAmendments; deciding that a child must exist; writing recovery queries; initiating retrieval; admitting support or inference. |
| Analyst | Decide whether an existing component lacks evidence or a genuinely new child is needed; propose component facts, direct claims, derived claims, and explicit relationships. | Admitting its own proposal, dispatching retrieval, or creating a parallel graph or truth lane. |
| Component D-prime | Independently validate component-level support or challenge against admitted evidence and relationships. | Acting as Analyst, admitting canonical state, or authorizing search. |
| Synthesis D-prime | Independently validate cross-component synthesis and inference relationships over admitted component and dependency refs. | Inventing synthesis, components, premises, or evidence. |
| Specialists | Produce bounded subordinate analysis or validation artifacts through installed Specialist custody. | Creating a second class of truth, admitting claims, or bypassing Analyst, D-prime, or canonical admission. |
| ContractAmendment admission/application | Independently validate and apply proposed contract changes while preserving exact current-contract, component, dependency, and parent lineage. | Becoming a second amendment family or accepting self-admitted Analyst output. |
| RunKernel | Root run authority; bind current canonical refs, admit or reject recovery purposes and amendments, grant whole-run leases, reduce observations, and administer canonical state and budgets. | Becoming a second semantic thinker, retrieval implementation, or final-answer judge. |
| SearchOS | Own search/acquisition/navigation cycle state and report slot, cycle, expenditure, exhaustion, blocker, and lawful-novel-work facts. | Reactivating terminal slots or independently deciding whole-run final posture. |
| QueryPlan | Sole owner of exact query identity, admission, ordering, lineage, and material query equivalence. | Deciding recovery-purpose novelty or admitting semantic support. |
| EvidenceLedger | Own source custody, source hierarchy, currentness, and requirement/custody facts. | Deciding component support or final readiness. |
| ComponentCoverage | Own current component and source-obligation coverage facts derived from canonical semantic admission. | Authorizing retrieval or whole-run finalization. |
| Sufficiency | Decide the whole-run final posture from current admitted coverage, custody, blockers, and terminal recovery-cycle aggregates. | Performing SearchOS work, admitting evidence, or writing final prose. |
| FinalAnswerPacket | Package only current Sufficiency-authorized, Author-safe material and exact lineage. | Reassessing support, inventing recovery, or synthesizing new claims. |
| Author | Render prose from FinalAnswerPacket under installed constraints. | Research, retrieval, admission, calculation, support judgment, or stopping decisions. |

RunKernel remains the root administrative authority and enforces the
Sufficiency result. “Sufficiency owns final posture” does not grant Sufficiency
work dispatch, evidence admission, or independent run-state mutation.

## 5. Existing-Component Recovery Authorization Basis

No new gap packet or schema family is currently required. A lossless canonical
authorization basis can be formed from existing references:

```text
current accepted AnswerContract ref
+ exact component ref
+ exact source-obligation ref
+ latest canonical ComponentCoverage ref
  or an explicit deterministic canonical-absence fact
+ EvidenceLedger requirement and custody facts
+ current terminal SearchOS slot ref
```

Canonical absence must be an explicit, digestible fact. It must not be inferred
from an unstated missing record. These facts already reach Sufficiency but do
not currently authorize post-analysis recovery. Internal PR A must connect the
existing gap basis to RunKernel recovery admission and a new append-only
SearchOS slot revision without inventing a second gap authority.

## 6. Append-Only Recovery-Cycle Transition

The approved transition is:

```text
immutable prior terminal slot
-> admitted materially novel recovery purpose
-> whole-run recovery lease
-> new SearchOS slot revision
-> existing SearchJudgment / QueryPlan / SEARCH / READ / navigation
-> semantic reassessment
-> new coverage or honest terminal posture
```

The old terminal slot remains immutable. It is never reactivated. A new slot
revision represents the new cycle and links to the immutable prior slot.
Purpose identity is admitted before executable work.

The whole-run recovery lease is distinct from local SearchOS action
reservations, per-slot budgets, and query/read/navigation limits. Prior action,
query, navigation, custody, failure, and expenditure histories remain
cumulative across cycles. No counter resets when a recovery slot is created.

Versioning the existing `RunKernel.SearchOSIterativeJudgment` state, action,
and observation vocabulary is expected and licensed in Internal PR A. A
parallel `RecoveryController`, separate recovery graph, standalone recovery
domain, or second SearchJudgment is prohibited.

## 7. Recovery-Purpose Novelty

Recovery-purpose novelty asks whether another recovery cycle is materially
warranted. Query novelty asks whether exact proposed query work is materially
nonredundant. They are separate decisions.

The intended recovery-purpose identity may bind facts such as:

- accepted-contract ref;
- component ref;
- source-obligation ref;
- canonical coverage or explicit gap fact ref;
- prior terminal slot or cycle ref;
- intended evidence delta;
- source classes and obligations already tried;
- failed or exhausted acquisition refs;
- navigation and source history; and
- current policy boundary.

This list identifies required information without freezing a final schema,
class, field, action, or observation name. Only after RunKernel admits the
purpose does SearchJudgment nominate executable work. QueryPlan remains the
sole owner of exact query identity, query admission, and material query
equivalence; recovery code must not duplicate its equivalence logic.

## 8. Whole-Run Stopping

SearchOS reports component, slot, and cycle facts: terminal posture,
expenditure, exhaustion, blockers, and whether lawful materially novel work
remains. The terminal recovery-cycle aggregate becomes an input to the existing
Sufficiency owner. SearchOS does not decide the final answer posture.

`HANDOFF_UNRESOLVED` and a terminal slot posture are not automatically
whole-run `INSUFFICIENT` decisions. They are facts for semantic reassessment
and Sufficiency, which maps the whole run as follows:

| Sufficiency result | Installed whole-run posture |
| --- | --- |
| `SATISFIED` | Ready direct or ready with caveats. |
| `PARTIAL` | Partial answer authorized. |
| `INSUFFICIENT` | Insufficient evidence, including recovery required but exhausted. |
| `BLOCKED` | Finalization blocked or another installed blocked posture. |

Internal PR A adds the missing terminal SearchOS recovery-cycle aggregate to
the existing Sufficiency input. It does not add a new stopping judge.

## 9. Analyst-Derived Component Flow

The approved near-term path is:

```text
Scrutineer finding, when applicable
-> Analyst decides whether a child is required
-> Analyst proposes the child component facts
-> independent ContractAmendment admission/application
-> the child's first Internal PR A SearchOS cycle
-> direct semantic support
-> existing graph reproof and selective resynthesis
-> Sufficiency
```

Analyst does not admit its proposal. Scrutineer may point Analyst to an exact
finding but does not author the component, amendment, query, or recovery
authorization. ContractAmendment application must preserve exact dependency
and parent lineage, including `dependency_component_ids`. The existing
ContractAmendment family and Graph V1 are reused, not replaced.

## 10. Unified Inference Direction

ScryRaven has one intended inference path:

```text
admitted premises
-> Analyst proposes a derived claim and explicit relationship
-> optional specialist artifacts provide bounded analysis or validation
-> D-prime independently validates
-> canonical authority admits or rejects
-> one component graph and one downstream coverage system
```

A directly supported component is admitted from evidence about that component
and has inference depth zero. An inference-supported component depends on
admitted premises and an independently validated relationship. Semantic
inference depth is the longest inference chain supporting the component:

```text
A and B directly supported: depth 0
A + B -> C: C depth 1
C + E -> D: D depth 2
```

A directly supported depth-zero child may later serve as a premise in a
higher-level inference. That does not change the child's own support depth.
Specialist assistance remains subordinate and does not create a deterministic,
analytical, or specialist-specific truth pipeline.

## 11. Recovery Generation Depth

Recovery generation depth counts generations of new components that recovery
may add:

```text
Fast:     0
Balanced: 1
Deep:     2
```

**NEAR-TERM DIRECTION:** this policy is not installed. Internal PR B must add a
narrow mode-bound extension to the existing SearchOS policy owner.

Recovery generation depth is independent from semantic
`max_inference_depth`, which measures the longest premise relationship chain
supporting one component. During Internal PR B, newly recovered components are
limited to direct support: allowed support is direct,
`max_inference_depth` is zero, and actual observation `inference_depth` is
zero. That is a temporary activation boundary, not permanent architecture.

## 12. PR A Boundary: Parent Checkpoint And Internal Implementation Boundary A

Parent checkpoint:

```text
SEARCHOS-GAP-RECOVERY-AND-STOP-CONVERGENCE-01
```

Internal PR A working name:

```text
SEARCHOS-EXISTING-GAP-RECOVERY-AND-STOP-FOUNDATION-01
```

**NEXT BUILD:** Internal PR A implements:

```text
existing admitted component remains unsupported
-> canonical gap basis
-> recovery-purpose admission
-> whole-run recovery lease
-> immutable prior slot plus new purpose-bound SearchOS slot revision
-> existing judgment / QueryPlan / retrieval / navigation
-> semantic reassessment
-> new ComponentCoverage or honest terminal posture
-> Sufficiency decides the whole run
```

Its merge condition is that canonical SearchOS is the only executable
existing-component and source-obligation recovery authority on an ordinary
SearchOS run. Any legacy route that could execute competing existing-gap
recovery on that path must be cut off or subordinated. No dual execution,
fallback, or competing controller may survive canonical activation.

Internal PR A keeps closed Analyst output changes, new-component proposals,
ContractAmendment mutation, component-graph mutation, Scrutineer behavior,
specialist behavior, and general inferred support. Internal PR A and Internal
PR B must not be combined because those protected authority surfaces give them
different rollback boundaries.

Internal PR A need not physically delete every already-forward-dead file, inert
compatibility consumer, direct legacy test, or historical helper. Broad dead
code deletion is not its merge gate. Such surfaces receive no new callers,
fallbacks, or compatibility investment.

## 13. PR B Boundary: Internal Implementation Boundary B

Internal PR B working name:

```text
SEARCHOS-DERIVED-COMPONENT-RECOVERY-AND-AUTHORITY-CONVERGENCE-01
```

**NEAR-TERM DIRECTION:** Internal PR B follows and consumes Internal PR A:

```text
parent cannot be established
-> Analyst proposes child
-> independent amendment admission/application
-> parent/dependency lineage preserved
-> child receives its first Internal PR A SearchOS cycle
-> direct evidence supports child
-> component D-prime and canonical component admission
-> graph reproof and selective resynthesis
-> final result changes
```

Internal PR B owns the Analyst proposal connection, recovery-generation-depth
policy, direct-support-only recovered-child boundary, Scrutineer authority
correction, dynamic planner/builder retirement, and remaining legacy
convergence. It replaces the active Scrutineer/deterministic
derived-component authority after the Analyst-originated replacement product
chain succeeds.

Reverting Internal PR B must leave Internal PR A useful and intact. No third
implementation PR may be created merely for convenience. A later
deletion-focused cleanup is permitted only for remaining dead machinery and is
outside the parent checkpoint unless needed to eliminate competing executable
authority.

## 14. Legacy Retirement Sequence

Retirement is triggered by replacement proof, not a date or desired line
count. Authority convergence and physical deletion are distinct:

- authority convergence means one executable ordinary recovery owner, no
  fallback, no dual execution, no competing controller, and no legacy route
  selected after canonical activation;
- physical deletion removes code that is already unreachable.

| Classification | Surface and required disposition |
| --- | --- |
| `SUBORDINATE_OR_CUT_OFF_DURING_PR_A` | Any component-gap, source-class, AG-92B, or other legacy route that could still execute competing existing-component recovery during an ordinary SearchOS run. It must become non-executable or subordinate before Internal PR A merges. |
| `FORWARD_DEAD_CONFIRMED` | AG-92B execution paths and compatibility consumers already unreachable or inert under canonical SearchOS. Preserve proof of dead status; physical deletion is not an Internal PR A merge requirement. |
| `RETIRE_AFTER_REPLACEMENT` | Forward-dead production files, compatibility-only plumbing, direct legacy behavior tests, obsolete state/action vocabulary, and historical helpers whose immediate removal would materially enlarge Internal PR A without improving executable authority convergence. |
| `RETIRE_DURING_PR_B` | Scrutineer-authored missing-component proposals, Scrutineer-originated recovery authorization, deterministic component/amendment construction, and the separate dynamic recovery planner/acquisition lane. Retire after the Analyst-originated replacement succeeds. |
| `RETAIN` | EvidenceLedger source hierarchy/currentness, QueryPlan identity/equivalence, Sufficiency terminal vocabulary/final posture, ContractAmendment mechanics, Graph V1, component and synthesis D-prime, bounded Specialist artifacts, and supervisory Scrutineer review. |

Internal PR A replacement candidates include competing AG-92B executable or
compatibility authority, old component-gap runtime/coordinator execution,
legacy ordinary source-class recovery execution, AG-92B Sufficiency vocabulary
coupling, and legacy QueryPlan component-gap consumption. The required outcome
is sole executable canonical authority, not indiscriminate deletion.

Internal PR B replacement candidates include Scrutineer missing-component
proposal authority, Scrutineer-originated recovery authorization, deterministic
dynamic component/amendment construction, and the separate dynamic recovery
planner/acquisition lane.

Physical deletion is required in the relevant implementation PR only when a
dead surface still creates an import or contract dependency, prevents truthful
validation, risks executable fallback, or is naturally small and causal to the
replacement. Some tests and state plumbing may remain until the appropriate
offline integration proof. No dual execution or fallback survives final
authority convergence.

## 15. Required Proof Classes

The two internal PRs must select concrete checks from these proof classes
without inventing test filenames in advance:

- `PRODUCT_PROOF`: the ordinary CLI/backend consumer completes the named
  product chain and the final result changes through canonical owners.
- `OWNER_CONTRACT`: each proposal, admission, custody, coverage, query, lease,
  stopping, and packaging decision is made by its named owner.
- `CONTAINMENT_GUARD`: closed surfaces remain closed, especially Internal PR
  A's Analyst/amendment/graph boundary and Internal PR B's direct-support-only
  boundary.
- `REPLAY_OR_IDEMPOTENCY`: repeated purpose, action, observation, amendment, or
  reduction input cannot duplicate work or canonical mutation.
- `HONEST_TERMINAL`: exhaustion, blockers, partial posture, insufficiency, and
  unresolved facts cannot be laundered into success.
- `LEGACY_CONVERGENCE`: the replacement product chain is the sole executable
  ordinary authority and no legacy fallback or dual execution remains.

## 16. Deferred Work

**DEFERRED:** general depth-one inferred-component admission, depth-two semantic
inference, permanent mode/provider policy, and live calibration. Comparative
provider/query calibration, permanent mode/provider selection, recursive
navigation, provider Deep/Research, Map, Crawl, social specialization,
conversation, and UI remain separately sequenced or optional work.

Internal PR B's directly supported recovered child is not proof of general
nonzero inferred support. Nothing here licenses provider, model, search, READ,
navigation, retrieval, database, secrets-backed, or other live validation.

## 17. Anti-Duplication Constitution

The following are prohibited:

- no second SearchJudgment;
- no `RecoveryController`;
- no second component graph;
- no second ContractAmendment family;
- no parallel semantic lane;
- no separate deterministic truth pipeline;
- no SearchOS-owned final-answer judge;
- no duplicate query-equivalence helper; and
- no legacy fallback after replacement proof.
