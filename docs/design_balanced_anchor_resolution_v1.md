# Balanced Anchor Resolution v1

Status: Phase 15 design contract draft. Classification: docs-only design
contract.

This note is descriptive only. It does not authorize runtime behavior changes,
prompt changes, routing changes, retrieval changes, provider changes, source
ranking/filtering changes, telemetry semantics changes, replay changes, or any
stage skip.

## Purpose

Balanced Anchor Resolution v1 defines a small pre-decomposition frame contract
for Balanced mode. It exists to make scattered anchoring assumptions explicit
before future diagnostics or tests are added.

The design direction is Balanced-first: frame first, search second, synthesize
last. Fast and Deep remain unchanged for now.

This is not a full controller. It is a compact contract for a possible future
shadow `anchor_packet` that can describe framing uncertainty before researcher
query generation.

## Non-goals

- No full QGA controller.
- No provider selection.
- No search-depth selection.
- No source-ranking or source-filtering changes.
- No active retrieve-to-anchor yet.
- No automatic clarification in production.
- No Analyst skip.
- No Economist shortcut.
- No Author-facing raw anchor dump.
- No weak-corpus behavior changes.
- No live-query benchmark.

## Conceptual Boundary

Anchor Resolution may forecast the likely answer posture. It may identify
ambiguous frames, likely source classes, temporal needs, and answerability risk.

Evidence triage and Analyst sufficiency decide answer status. Retrieval health,
source quality, and Analyst review remain responsible for determining whether an
answer is supportable, qualified, or blocked.

Author expresses the calibrated final answer only after Analyst-reviewed
synthesis. The Author must not receive raw framing material as a substitute for
reviewed analysis.

## Minimal `anchor_packet`

The v1 packet is intentionally small and diagnostic-oriented:

| Field | Meaning |
| --- | --- |
| `candidate_frames` | Short list of plausible interpretations or frames, each with a stable frame id and compact rationale. |
| `selected_frame_id` | Preferred frame when one is clear enough to guide decomposition; may be empty when multiple frames should be preserved. |
| `ambiguity_types` | Compact labels for ambiguity, such as referent, domain, metric, temporal, scope, evidence-access, or causal-mechanism ambiguity. |
| `confidence_bucket` | Coarse confidence only: low, medium, or high. |
| `temporal_frame` | Time window implied by the request, including evergreen, recent, point-in-time, rolling, or user-bounded. |
| `freshness_requirement` | Expected freshness need, such as none, low, medium, high, or official-current. |
| `source_class_expectation` | Expected source class, such as official, primary, peer-reviewed, regulatory, market/current, local corpus, or mixed. |
| `claim_or_metric_type` | Claim class, such as factual lookup, rule, comparison, metric, causal claim, forecast, estimate, or synthesis. |
| `answerability_forecast` | Coarse forecast: likely answerable, answerable with constraints, proxy-only risk, likely non-public, or unclear. |
| `decomposition_hints` | Small hints for future query decomposition, including preserve-frame, include-date, include-official-source, or avoid-proxy-only. |
| `off_domain_traps` | Nearby wrong-domain or wrong-scope interpretations that should be kept visible during decomposition. |
| `next_action` | One of the v1 enum values below. |
| `clarification_question` | Optional one-question clarification when ambiguity is high and proceeding would likely misframe the task. |

## Explicit Exclusions From v1

The v1 packet excludes:

- Entropy.
- Numeric probabilities.
- Answerability priors or posteriors.
- Clarification value estimates.
- Budget allocation.
- Provider selection.
- Search-depth selection.
- Final answer mode.

## `next_action` Enum

`proceed_single_frame`: One frame is sufficiently clear for decomposition.

`preserve_multiple_frames`: Multiple plausible frames should remain visible to
query generation and Analyst review.

`retrieve_to_anchor`: A future system may benefit from a small anchoring probe,
but this is recommendation-only for now. Do not run an active probe yet.

`ask_clarification`: A clarification may be needed when ambiguity is central and
the likely cost of a wrong frame is high.

Clarification should be scarce, not default. In v1, even `ask_clarification` is
a diagnostic recommendation unless a separately authorized behavior change
exists.

## Integration Sketch

The safest future shadow insertion point appears to be after router parsing,
fallback entity extraction, and router retry, but before researcher query
generation.

At that point, the system would have parsed request metadata and fallback entity
signals, while still being early enough to influence only diagnostics and future
test assertions before any decomposition work. This document does not implement
that insertion point and does not authorize using it for live behavior.

## Phase 15b Context and Cache Discipline

Balanced Anchor Resolution should be cache-friendly if it is ever implemented in
shadow form:

- Keep stable prompt prefixes.
- Keep stable schemas.
- Put variable material later in prompts.
- Keep packets compact.
- Prefer source IDs, chunk IDs, and evidence IDs over repeated raw evidence.
- Consider an evidence registry concept so stages can reference compact IDs
  while raw evidence remains available for audit/debug.
- Context savings must not become Analyst skip.
- Raw `quantitative_packet`, raw Economist framework, and raw `economist_v1`
  JSON must not go to Author.

Raw evidence availability remains important for auditability. Compact packet
references are a context strategy, not a permission to suppress review material
or bypass safety checks.

## Safety Invariants

- Economist code execution remains prohibited.
- Economist output must not bypass Analyst.
- Economist skip-candidate and skip-eligibility fields remain diagnostic only.
- Raw `quantitative_packet`, raw Economist framework, and raw `economist_v1`
  JSON must not reach Author.
- Existing weak-corpus gate remains separate and unchanged.
- Diagnostics do not become gates.
- Every future skip, drop, or suppression would need stable telemetry and a
  stable reason.

## Synthetic Test Matrix

| Fixture class | Anchor should notice | Nearby negative control | Must not change in diagnostics-only phase |
| --- | --- | --- | --- |
| Ambiguous referent | Multiple plausible referents and need to preserve frames or ask one scarce clarification. | Clear referent with same syntax shape. | Routing, retrieval, prompts, and final answer behavior remain unchanged. |
| Wrong-domain frame | Nearby off-domain interpretation and the expected domain boundary. | Same terms in an unambiguous domain-specific request. | No source filtering or ranking change. |
| Recent mutable rule | High freshness requirement and official-current source expectation. | Evergreen definition of the same rule class. | No live recency probe or search-depth change. |
| Metric ambiguity | Metric name, unit, denominator, time basis, or geography ambiguity. | Fully specified metric request. | No query generation change. |
| Likely non-public evidence | Answerability forecast flags likely non-public or inaccessible evidence. | Public official record request. | No weak-corpus behavior change and no automatic refusal. |
| Simple evergreen negative control | Low ambiguity, low freshness, single frame. | Ambiguous variant with missing referent or scope. | No extra stage, query, or diagnostic gate required for the control. |
| Proxy-only evidence risk | Target metric may be unavailable and proxies may be tempting. | User explicitly asks for proxy or qualitative framing. | No proxy suppression, missing-target behavior change, or Analyst skip. |
| Causal claim with hidden evidence risk | Causal mechanism requires stronger evidence and may depend on unavailable data. | Descriptive correlation request. | No Economist shortcut and no final answer mode change. |
| Official/recent source-class expectation | Official or primary recent source class should be expected. | Historical background request with low freshness need. | No provider or source-class routing change. |
| Bounded comparison with constraints | Constraint set, comparison scope, and frame boundaries should be preserved. | Open-ended comparison without constraints. | No query budget allocation or ranking change. |

## Future Sequence

Intended order:

1. Docs-only contract.
2. Test-only synthetic fixtures.
3. Diagnostics-only shadow `anchor_packet`.
4. Shadow retrieve-to-anchor recommendation.
5. Offline replay / fixture evaluation.
6. Only later, scoped behavior change with Rule 0 and tests.

Each step should preserve the prior safety boundary unless a later phase
explicitly approves a narrow change with tests and stable telemetry.

## Explicit Non-authorization Checklist

This document does not authorize changes to:

- Routing.
- Retrieval.
- Provider selection.
- Search depth.
- Query generation.
- Prompts.
- Source filtering/ranking.
- Analyst.
- Economist.
- Author.
- Telemetry semantics.
- JSONL.
- SQLite.
- Replay.
- Summarizer.
- Weak-corpus behavior.

No commit, push, live query, Streamlit run, provider call, model call, search API
call, competitor call, external service call, log mutation, database mutation,
output artifact mutation, secret/env mutation, cache mutation, or Project Source
change is authorized by this note.
