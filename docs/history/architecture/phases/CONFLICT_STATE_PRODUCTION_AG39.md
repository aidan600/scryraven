Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (CONFLICT_STATE_PRODUCTION_AG39).

# AG-39 Conflict-State Production Design

## Status

Design only. This note does not implement runtime behavior.

AG-37B proved that `resolve_conflict` checkpoint dispatch plumbing can execute
one bounded conflict-resolution pass when conflict facts and resolving queries
already exist. It also proved that terminal stops, source-class recovery,
weak-corpus recovery, lifecycle blockers, and the separation between ordinary
`next_queries` and conflict `resolving_queries` remain authoritative.

AG-39 answers the remaining data-production question: where should
`conflicts_present`, `conflict_notes`, and `resolving_queries` come from?

## Diagnosis

The current runtime has conflict consumers, not a conflict producer.

Existing control-plane artifacts are already in a good place:

- `RuntimeAnswerContractFacts` accepts `conflicts_present`, `conflict_notes`,
  `resolving_queries`, and ordinary `next_queries`.
- The answer-contract adapter carries those fields into
  `EvidenceStateSummary`.
- The AG-32 evidence-integration checkpoint reads `conflicts_present` and
  `conflict_resolution_available` and may recommend `resolve_conflict`.
- The AG-37B conflict lifecycle reads the same evidence-state fields and blocks
  closed on `no_conflict` or `no_resolving_queries`.
- The controller-loop spine arbitrates between source-class recovery,
  weak-corpus recovery, terminal stops, and conflict resolution.

What is missing is a small, sanitized, pre-checkpoint producer that can build a
conflict-state object from existing evidence artifacts without touching
providers, routing, search depth, prompts, persistence, protected handoffs, or
final answer generation.

The producer must not use final answer text as authority. Final-answer
contradiction diagnostics are downstream safety tools and cannot create
runtime conflict facts for AG-37B.

## Existing Artifacts

Runtime artifacts with potential disagreement signal:

| Artifact | Existing signal | Safe/stable enough? | Use in AG-40? |
| --- | --- | --- | --- |
| `final_top_evidence` / `all_passages` | Source IDs, titles, URLs, text snippets, source tiers, retrieval stage | Mostly safe as ordinary evidence already visible to synthesis, but not claim-normalized | Yes, as bounded input to a producer |
| `source_tier_telemetry` and source-domain telemetry | Official/secondary/social/unknown mix, low-trust or pollution flags | Sanitized and stable, but metadata-only | Yes, as weak deterministic flags |
| `source_class_recovery_telemetry` and observability | Missing expected source class, satisfaction status, strong source counts | Sanitized and stable, but usually gap/mismatch rather than factual contradiction | Yes, as context and blocker signal |
| `answer_contract_fulfillment_handoff` | Fulfilled, partial, unfulfilled items, warnings | Sanitized and stable | Yes, for centrality only |
| `EvidenceIntegrationSnapshot` | Conflict fields already modeled | Safe consumer shape, not a producer | No, do not make it self-source conflict |
| Retrieval-stop `next_queries` | Ordinary continuation queries | Stable but not conflict-specific | No automatic promotion to resolving queries |
| Quantitative consistency guard | Detects inconsistency between final answer text and calculation | Narrow and useful, but final-answer-derived | No producer authority for AG-39 |
| Raw traces, DB rows, provider payloads, caches, logs | May contain useful detail | Not allowed by AG-39 constraints | No |

Conclusion: the safest producer input is a sanitized evidence bundle plus
contract context, not final answer prose and not raw telemetry.

## Conflict-State Data Flow

Recommended AG-40 flow:

```text
retrieval outputs / final_top_evidence
        +
source tier/domain telemetry
        +
source-class observability
        +
answer-contract contract + fulfillment context
        |
        v
ConflictStateProducer
        |
        |  emits compact ConflictState only
        v
RuntimeAnswerContractFacts
  - conflicts_present
  - conflict_notes
  - resolving_queries
  - next_queries remains ordinary only
        |
        v
answer_contract_runtime_handoff
        |
        v
EvidenceStateSummary
        |
        v
EvidenceIntegrationSnapshot / checkpoint
        |
        v
existing AG-37B conflict lifecycle and controller-loop spine
```

The producer should run before the runtime answer-contract handoff that feeds
source-class/checkpoint/conflict lifecycle state. It should also be reusable
for the final handoff trace fragment, but only as a compact already-computed
state object.

## Candidate Producers

### 1. Evaluator Detects Contradiction In Top Evidence

Partly safe, but not sufficient by itself.

The evaluator already reasons about sufficiency and continuation, but current
runtime artifacts do not expose stable claim pairs. Letting evaluator prose
become conflict authority would blur prompt ownership and likely require prompt
changes.

Safe subset: a future sanitized evaluator side packet may feed
`ConflictState`, but AG-40 should not depend on prompt changes.

### 2. Answer-Contract Fulfillment Identifies Inconsistent Claims

Safe for centrality, unsafe as the sole detector.

Fulfillment knows contract obligations and whether items are partial or
unfulfilled. It is the right place to answer "does this tension matter to the
contract?" It does not currently own claim extraction or contradiction
detection.

AG-40 should use fulfillment and contract family to classify centrality, not
to invent conflicts.

### 3. Evidence-Integration Checkpoint Identifies Unresolved Conflict

Unsafe as producer if it reads its own conflict fields.

The checkpoint is already a consumer and dispatcher recommendation boundary.
Making it produce conflict facts would collapse detection, centrality, and
dispatch selection into one surface.

Safe role: the checkpoint may consume `ConflictState` fields and recommend
`resolve_conflict` when central and queryable.

### 4. Source Metadata / Source-Class Disagreement Exposes Conflict

Useful as a flag, unsafe as factual conflict authority.

Metadata can show official-vs-secondary disagreement risk, stale/current
tension, low-trust contamination, or missing authority. That is not the same
as two claims being in tension.

Safe subset: metadata can raise `possible_conflict_signals` and can lower
confidence or add blockers. It should not set `conflicts_present=True` alone.

### 5. Future Targeted Retrieval Produces Resolving Queries

Unsafe for AG-40 as a dependency.

Targeted retrieval ownership is intentionally not promoted here. A future
targeted retrieval planner may produce better resolving queries, but AG-40 can
generate bounded query candidates from already-identified claims in tension.

Safe subset: query candidates are strings only, capped and provenance-tagged;
they do not execute unless AG-37B gates approve dispatch.

### 6. New Bounded Conflict-State Producer

Recommended.

This creates the smallest safe boundary: a pure/offline module that accepts
sanitized evidence and contract facts, emits `ConflictState`, and has no
provider, routing, prompt, persistence, final-answer, Scrutineer, social,
source-class recovery, weak-corpus recovery, or search-depth authority.

### 7. No Safe Source Yet / Prerequisite Boundary

Not necessary if AG-40 scopes detection tightly.

There is enough sanitized evidence and contract context to build a conservative
producer. The first implementation should be deliberately narrow and fail
closed. Broad semantic contradiction detection can wait.

## Recommended Schema

Proposed shape:

```python
@dataclass(frozen=True)
class ConflictClaim:
    claim_id: str
    normalized_claim: str
    value: str | None = None
    attribute: str | None = None
    subject: str | None = None
    source_refs: tuple[str, ...] = ()
    source_classes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConflictState:
    schema_version: str = "conflict_state_ag40_v1"
    conflicts_present: bool = False
    conflict_notes: tuple[str, ...] = ()
    claims_in_tension: tuple[ConflictClaim, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    centrality_to_contract: str = "not_central"
    resolving_query_candidates: tuple[str, ...] = ()
    resolving_query_source: str = "none"
    confidence: str = "low"
    safe_to_dispatch_resolve_conflict: bool = False
    blockers: tuple[str, ...] = ()
    ordinary_next_queries: tuple[str, ...] = ()
```

Recommended value constraints:

- `centrality_to_contract`: `central`, `supporting`, `peripheral`,
  `not_central`, `unknown`
- `resolving_query_source`: `none`, `deterministic_claim_pair`,
  `bounded_conflict_classifier`, `evidence_integration_judgment`,
  `future_targeted_retrieval`
- `confidence`: `low`, `medium`, `high`
- `blockers`: stable reason codes such as `no_claim_pair`,
  `metadata_only_signal`, `not_central_to_contract`,
  `no_resolving_query_candidates`, `ordinary_next_queries_only`,
  `final_answer_text_disallowed`, `insufficient_evidence_refs`,
  `protected_input_unavailable`

Projection into existing runtime facts:

```text
RuntimeAnswerContractFacts.conflicts_present
  = conflict_state.conflicts_present
    and conflict_state.centrality_to_contract == "central"

RuntimeAnswerContractFacts.conflict_notes
  = conflict_state.conflict_notes

RuntimeAnswerContractFacts.resolving_queries
  = conflict_state.resolving_query_candidates
    only if conflict_state.safe_to_dispatch_resolve_conflict

RuntimeAnswerContractFacts.next_queries
  = ordinary_next_queries only
```

`ordinary_next_queries` must be preserved in the state for auditability, but
must never be copied into `resolving_query_candidates`.

## Recommended Boundary

Use a hybrid boundary:

1. Deterministic evidence-state functions flag possible conflict.
2. A bounded conflict classifier or evidence-integration judgment decides
   whether the candidate is central to the answer contract and whether
   resolving query candidates are legitimate.
3. Dispatch remains owned by the existing checkpoint, conflict lifecycle, and
   controller-loop spine.

For AG-40, the implementation should start with a deterministic,
fixture-proven producer shape and optional classifier interface, not a live LLM
call. This allows tests to prove real runtime authority without changing
providers or prompts. The classifier can be dependency-injected in tests and
default to fail-closed if unavailable.

Hard boundary rules:

- Do not read final answer text.
- Do not read raw traces, raw logs, caches, DB rows, provider payloads, prompts,
  secrets, or private generated outputs.
- Do not change query generation, search depth, provider selection, routing, or
  retrieval execution.
- Do not promote targeted retrieval.
- Do not treat ordinary `next_queries` as resolving queries.
- Do not let metadata-only source-class disagreement set
  `safe_to_dispatch_resolve_conflict=True`.

## Runtime Cases

When conflict is detected but resolving queries are unavailable:

- Set `conflicts_present=True` only if a real claim pair exists.
- Set `safe_to_dispatch_resolve_conflict=False`.
- Add blocker `no_resolving_query_candidates`.
- Existing controller behavior should stop with conflict caveat rather than
  dispatch conflict retrieval.

When resolving queries exist but conflict is not central:

- Preserve queries as `resolving_query_candidates` for trace/debug only if
  they came from the conflict producer.
- Set `safe_to_dispatch_resolve_conflict=False`.
- Do not project those queries into `RuntimeAnswerContractFacts.resolving_queries`.
- Let ordinary sufficiency/source-class/weak-corpus/targeted retrieval logic
  proceed as before.

False positives:

- Same fact expressed with different wording.
- Different dates that refer to different events, versions, jurisdictions, or
  effective dates.
- Source-class gap mistaken for factual disagreement.
- Social sentiment disagreement treated as factual authority.
- Stale secondary evidence disagreeing with official current evidence where
  the official source already satisfies the contract.
- Ordinary continuation query mislabeled as conflict resolution.

Fail-closed behavior:

- Any ambiguity in claim normalization, evidence refs, centrality, or query
  provenance should set `safe_to_dispatch_resolve_conflict=False`.
- Missing evidence refs should block dispatch.
- Metadata-only signals should block dispatch.
- Low confidence should block dispatch unless a narrow deterministic rule is
  explicitly validated by fixture tests.

## Fixture Plan

AG-40 should prove production against a small offline fixture corpus before
live behavior:

1. Central current-rule date conflict:
   official page says effective date A; reputable secondary says effective
   date B for the same rule.
2. Non-central conflict:
   sources disagree on a background date, while the answer contract asks for a
   stable conceptual explanation.
3. Metadata-only source-class mismatch:
   secondary sources only, official source missing, but no contradictory claim
   pair.
4. Ordinary next-query control:
   retrieval-stop suggests an ordinary continuation query; conflict producer
   emits no resolving queries.
5. Same-date/different-context control:
   one source has announcement date, another has effective date; no conflict.
6. Stale-vs-current official control:
   older secondary conflicts with current official source, but current official
   source already satisfies the contract; no conflict-resolution dispatch.
7. Conflict without query:
   real claim tension exists but no safe query candidate can be formed; caveat
   only.
8. Query without central conflict:
   classifier emits query candidates but centrality is peripheral; no runtime
   resolving query projection.

Fixtures should use in-repo synthetic passages with `source_id`, `title`,
`url`, `text`, `source_tier`, and optional source-class labels. They should not
use provider calls or raw logs.

## Tests Needed For AG-40

Unit tests:

- `ConflictState` sanitizes and deduplicates notes, refs, claims, and query
  candidates.
- Sensitive keys and protected markers are omitted from metadata.
- Metadata-only source-class disagreement does not set dispatch-safe conflict.
- Ordinary `next_queries` remain separate and never become resolving queries.
- Confidence/centrality/blockers fail closed.
- Resolving query candidates are capped and provenance-tagged.

Adapter tests:

- ConflictState projects into `RuntimeAnswerContractFacts` only when
  `safe_to_dispatch_resolve_conflict=True`.
- Non-central conflict does not populate runtime `resolving_queries`.
- Conflict without query populates notes but blocks dispatch with
  `no_resolving_queries`.

Runtime harness tests:

- Normal offline runtime fixture surfaces `conflicts_present`,
  `conflict_notes`, and resolving candidates without monkeypatching
  `build_runtime_answer_contract_handoff`.
- AG-37B dispatches conflict resolution exactly once only for central,
  queryable conflict state.
- Terminal stops, source-class recovery, weak-corpus recovery, provider/depth
  blockers, author/post-Analyst phase blockers, and prior-attempt blockers
  still win.
- Existing AG-37B monkeypatch tests remain as plumbing tests but are no longer
  the only proof of active runtime authority.

Static guard tests:

- New producer imports no provider/model/search/persistence/prompt modules.
- New producer does not read final answer text.
- Orchestrator wiring does not alter provider role, search depth, routing,
  query generation, persistence, Analyst/Economist/Author handoffs,
  Scrutineer, social signal, source-class recovery, weak-corpus recovery, or
  final answer generation.

## Implementation Readiness

The next phase is implementation-ready if AG-40 is narrow:

- Add a minimal pure/offline conflict-state producer.
- Feed `RuntimeAnswerContractFacts` conflict fields from that producer.
- Prove normal runtime can surface conflict state without monkeypatching.
- Do not dispatch conflict resolution unless the state is central, queryable,
  confidence-gated, and free of blockers.

AG-40 should not implement broad semantic contradiction detection, live LLM
classification, targeted retrieval ownership, new prompts, or final-answer
behavior changes.

## Stop Conditions

Stop AG-40 and do not promote behavior if any of these occurs:

- The producer needs final answer text to identify conflicts.
- The producer needs raw provider payloads, raw traces, DB/cache access, raw
  logs, prompts, private generated outputs, or secrets.
- Ordinary next queries must be copied into resolving queries to make tests
  pass.
- Source-class or metadata disagreement alone is enough to dispatch conflict
  resolution.
- Query generation, providers, routing, search depth, prompts, persistence, or
  handoffs must change.
- Dispatch requires targeted retrieval ownership.
- Fixture tests cannot distinguish true claim conflict from different contexts
  or stale/background disagreement.

## Recommendation On Aggressiveness

Be conservative.

AG-40 should prefer false negatives over false positives. It should only mark
`safe_to_dispatch_resolve_conflict=True` when a bounded producer can show:

- at least two specific claims in tension,
- evidence refs for both sides,
- centrality to a must-satisfy contract item or required source class,
- legitimate resolving query candidates,
- medium or high confidence,
- no blockers.

Everything else should become caveat, ordinary missing-information state, or
source-class/weak-corpus handling through existing controllers.

## Explicit Answer: Separable From Targeted Retrieval Ownership?

Yes.

Conflict-state production is separable from targeted retrieval ownership if
AG-40 treats resolving queries as candidate facts, not as a general retrieval
planner. The existing conflict-resolution executor already has its own provider
role and dispatch plumbing. The producer only needs to say "this specific
central conflict has these bounded resolving query candidates." It must not own
continuation retrieval, provider selection, search depth, or ordinary
`next_queries`.
