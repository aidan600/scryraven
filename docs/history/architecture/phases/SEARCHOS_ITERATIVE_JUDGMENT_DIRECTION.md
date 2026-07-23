# SearchOS Iterative Judgment Direction

Status: approved architecture direction; BUILD not yet authorized
Authority: approved:searchos-iterative-judgment-direction
Responsibility: canonical forward direction for first-wave cutover, iterative result admission, the single SearchJudgment owner, semantic-evaluation handoff, navigation sequencing, budget/mode policy, and legacy-authority retirement
Applies to: `SEARCHOS-ITERATIVE-NAVIGATION-AND-RETRIEVAL-JUDGMENT-01` and its architecture-only convergence record
Repository owner: `docs/architecture/SEARCHOS_ITERATIVE_JUDGMENT_DIRECTION.md`
Project Source role: durable external context mirror; once the repository copy exists, the repository copy controls on conflict
Update trigger: maintainer changes the canonical owner, first-wave boundary, action vocabulary, iterative candidate continuity, navigation sequencing, adjustable policy doctrine, or legacy retirement direction
Non-trigger: implementation of a subordinate slice that conforms to this direction
Does-not-authorize: BUILD, live calls, provider/model policy changes, roadmap reordering, or claims that planned behavior is installed

## 1. Purpose

ScryRaven will converge its overlapping post-result retrieval mechanisms into one canonical SearchOS judgment system.

This is intentionally a new replacement implementation, but it must become the **only** forward ordinary post-result semantic authority. It is not a fourth surviving system.

```text
RunKernel
└── SearchOS
    ├── SearchPlanner
    ├── QueryPlan
    ├── SearchJudgment
    ├── routing
    ├── provider adapters
    └── EvidenceLedger custody
```

RunKernel remains root authority. SearchOS is the search, acquisition, navigation, and recovery subsystem. SearchJudgment is the model-owned semantic decision-maker inside SearchOS.

## 2. Current systems and disposition

### Narrow READ assessment

Disposition: **SUBORDINATE, REUSE, THEN RETIRE AS A STANDALONE OWNER**.

Reuse:

- exact component / source-obligation / candidate bindings;
- shared-obligation representation;
- mandatory model judgment;
- strict output validation;
- no deterministic semantic fallback;
- RunKernel action and reduction pattern;
- acquisition proposal conversion;
- same-URL custody reuse.

Its READ-specific module and state do not become the permanent SearchOS manager. READ becomes one action branch of the neutral iterative SearchJudgment owner.

### AG-92B full SearchJudgment

Disposition: **ISOLATE, USE AS REFERENCE, THEN SELECTIVELY REPLACE OR RETIRE**.

It may contribute useful concepts or mechanically correct helpers, but it does not bind the new design. Its deterministic-first judgment, deterministic fallback, older topology, and bundled recovery/stopping semantics are not adopted by default.

Its remaining recovery/stopping behavior is addressed during `SEARCHOS-GAP-RECOVERY-AND-STOP-CONVERGENCE-01`.

### Legacy evaluator / expander loop

Disposition: **REMOVE ORDINARY MODEL AUTHORITY DURING THE FIRST CUTOVER**.

The new SearchJudgment model becomes the sole semantic proposer of follow-up query text. Reuse only neutral deterministic machinery where correct:

- normalization;
- redundancy checks;
- QueryPlan continuation admission;
- scheduling and DISCOVER execution;
- result identity and iteration lineage.

Any answer path connected only through the legacy passage loop must be reviewed as a migration or retirement surface rather than preserved automatically.

## 3. Canonical first-wave cutover

The new authority begins after the first admitted query wave, not after the legacy retrieval loop has already decided whether to continue.

```text
accepted AnswerContract
→ SearchWorkPlan
→ initial QueryPlan wave
→ first DISCOVER only
→ immutable revision-1 candidate packet
→ canonical iterative SearchJudgment
→ authorized next action
```

Legacy evaluator/expander and deterministic recovery paths must not independently authorize pre-judgment continuation in the ordinary SearchOS path.

## 4. Canonical iterative action vocabulary

The initial closed action set is:

```text
HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION
REQUEST_READ_PAGE
PROPOSE_FOLLOWUP_QUERY
HANDOFF_UNRESOLVED
```

### HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION

Selects exact component/source-obligation-bound material for the existing semantic pipeline:

```text
SearchJudgment selection
→ bounded exact material handoff
→ Component Analyst proposal
→ component D-prime validation
→ RunKernel semantic admission
```

SearchJudgment does not create support, coverage, satisfaction, citations, Sufficiency, FinalAnswerPacket, or Author authority.

### REQUEST_READ_PAGE

Nominates one exact currently eligible unread binding. The same action covers the first source and later alternative candidates; iteration history distinguishes them.

### PROPOSE_FOLLOWUP_QUERY

Nominates one exact bounded, materially nonredundant query for one active unmet need.

Multiple sequential follow-up queries are allowed within budget:

```text
query
→ inspect
→ read if justified
→ re-judge
→ another materially distinct query if still required
```

The model proposes exact query text. Deterministic code validates identity, scope, bounds, and nonredundancy. QueryPlan alone admits executable query identity and order.

### HANDOFF_UNRESOLVED

Records a still-open component/source-obligation need for later recovery/stopping convergence. It is not a claim of satisfaction and not a whole-run stop decision.

## 5. Follow-up DISCOVER result admission

Revision 1 remains immutable. Follow-up results require an append-only canonical admission path.

Preferred direction:

```text
SearchOSIterationCandidateSetV1
```

Each admitted iteration candidate set should bind:

- iteration identity;
- parent revision-1 packet or prior iteration-set ref;
- exact QueryPlan continuation item ref;
- ProviderPlan / route / retrieval action refs;
- ordered provider-result occurrence refs;
- identity-set growth facts;
- selected candidate refs;
- bounded candidate material refs;
- active component/source-obligation slot refs;
- selection and overflow facts;
- stable digest and replay identity.

The loop becomes:

```text
model-owned follow-up query proposal
→ deterministic validation
→ QueryPlan admission
→ DISCOVER route and execution
→ provider-result occurrence identities/material
→ authorized ranking and selection
→ immutable iteration candidate-set admission
→ slot/candidate binding derivation
→ next SearchJudgment iteration
```

Required invariants:

- revision-1 bytes and digest never change;
- legitimate QueryPlan append-only growth does not make historical lineage falsely stale;
- stale or unrelated results cannot enter an iteration set;
- raw discovery-store entries cannot bypass authorized ranking and selection;
- repeated normalized URLs retain new contributor/query lineage while reusing existing custody;
- zero useful results produce a typed iteration outcome;
- candidate-wave limits are explicit at limit minus one, limit, and limit plus one.

## 6. Navigation

Navigation is a SearchOS tool, not a separate authority system.

It means selecting one exact outbound URL discovered inside an already read source, then separately reading it.

```text
READ source
→ extract exact outbound breadcrumb candidates
→ SearchJudgment selects one justified URL
→ NAVIGATE records the candidate lineage
→ READ_PAGE fetches the selected URL
```

Navigation requires additional substrate:

- outbound-link extraction;
- source-to-link lineage;
- navigation candidate contract;
- exact URL selection;
- visited-set and cycle detection;
- depth and breadth limits;
- domain/scope behavior;
- mandatory separate READ before custody or semantic use.

Keep the canonical roadmap checkpoint name, but implement it as two internal slices:

```text
A. first-wave and iterative-retrieval-judgment cutover
B. bounded breadcrumb navigation
```

The roadmap checkpoint is complete only after both unless the maintainer explicitly moves navigation later.

## 7. Analyst re-entry

SearchJudgment reasons about whether the required material has been obtained. Analyst reasons about what the material establishes.

```text
SearchOS retrieval judgment
→ semantic-evaluation handoff
→ Analyst / D-prime / RunKernel admission

if admitted analysis exposes a real gap:
→ RunKernel re-enters the same SearchOS judgment owner
→ assigns bounded additional budget
→ search / read / navigation resumes
```

The iterative phase installs the handoff seam. Comprehensive post-analysis recovery eligibility and whole-run stopping remain the following roadmap phase.

## 8. Budget and mode policy

All adjustable SearchOS limits belong to one versioned, repository-owned policy surface, provisionally:

```text
SearchOSPolicyProfileV1
```

It should contain findable, validated dials for:

- active component/source-obligation slots;
- candidate-use options visible per slot;
- iterative rounds;
- judgment calls;
- SEARCH / DISCOVER executions;
- READ nominations;
- follow-up query nominations;
- navigation depth and breadth;
- post-Analyst re-entry;
- retained-state limits;
- Fast / Balanced / Deep provisional profiles.

The admitted run records an immutable policy snapshot and version. RunKernel leases and charges exact budgets.

Principles:

- budgets are maximum leash, not targets;
- the model should stop early when the need is met;
- every component has an explicit budget;
- no ordered slot may silently starve a later required slot;
- complete-round admission or reservations should prevent partial semantic execution when necessary;
- provisional values are adjustable during dogfooding and calibration;
- permanent mode/provider values belong to later calibration and policy-selection phases.

Fast, Balanced, and Deep use the same SearchOS vocabulary and authority chain. They differ in budget, effort, concurrency, and recovery allowance—not evidence meaning or available concepts.

## 9. Direct READ versus SEARCH

SearchJudgment chooses the provider-neutral operation required by the active need. Routing chooses the provider implementation.

When a trustworthy exact URL is already bound to the active need, SearchOS may authorize direct `READ_PAGE` without first paying for broad SEARCH.

When no exact URL is known:

```text
SEARCH
→ candidate admission
→ READ_PAGE when justified
```

Provider-specific costs and preferences belong to provider profiles and routing policy, not SearchJudgment prompts or semantic state.

## 10. Delivery sequence

### Architecture-only convergence record

First resolve and document:

- the neutral canonical SearchJudgment state;
- first-wave cutover callsite;
- follow-up iteration candidate-set contract;
- ordinary evaluator/expander removal;
- narrow READ migration and retirement;
- AG-92B isolation and later disposition;
- all hard-limit behavior;
- provisional policy owner and mode interaction.

### Internal Slice A — iterative judgment cutover

Install:

- first-wave boundary;
- one canonical SearchJudgment state;
- the four-action vocabulary;
- direct READ and sequential nonredundant query actions;
- append-only iteration candidate sets;
- semantic-evaluation handoff;
- evaluator/expander model-authority removal;
- provisional policy profiles.

### Internal Slice B — bounded breadcrumb navigation

Install navigation candidates, exact selection, cycle/depth/breadth controls, and mandatory separate READ.

### Following roadmap phase

`SEARCHOS-GAP-RECOVERY-AND-STOP-CONVERGENCE-01` owns comprehensive gap classification, Analyst-discovered recovery convergence, typed failure convergence, whole-run stopping, and AG-92B final retirement or selective replacement.

## 11. Non-negotiable invariants

```text
one forward SearchJudgment semantic owner
RunKernel admits all canonical state
QueryPlan owns exact executable query identity
routing owns provider choice
custody is not support
SearchJudgment does not validate or admit its own support claims
no deterministic semantic fallback
revision 1 remains immutable
follow-up results require canonical candidate admission
no raw discovery result bypasses selection
same-URL custody reuse preserves new lineage
modes vary budgets, not authority
no live calls without a separate license
```

## 12. Authorization posture

```text
Architecture direction: approved
Cursor Build: NOT AUTHORIZED
Codex BUILD brief: NOT AUTHORIZED
```

The next authorized task is the architecture-only convergence record for first-wave cutover and iterative candidate-state continuity.
