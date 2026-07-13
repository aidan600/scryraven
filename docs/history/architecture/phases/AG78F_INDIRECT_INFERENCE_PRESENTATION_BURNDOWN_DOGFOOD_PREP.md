Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG78F_INDIRECT_INFERENCE_PRESENTATION_BURNDOWN_DOGFOOD_PREP).

# AG-78F — Indirect Inference Presentation Burn-Down / Dogfood Prep

**Phase date:** 2026-06-02
**Phase type:** review / burn-down / dogfood-prep.

## Scope and non-goals

AG-78F reviews the merged AG-78 indirect-inference stack end-to-end for
presentation wording, trace ergonomics, citation-laundering safety, test
coverage, and readiness for later bounded dogfood. It is documentation-only and
introduces no runtime product behavior change.

AG-78F does not change provider, model, search, query, retrieval ranking,
source-class/currentness, evaluator semantics, conflict arbitration, citation
selection, database/session/RunOutcome shape, cache behavior, Scrutineer,
remediation, Economist, follow-up, broad orchestration, live validation,
inference-opportunity detection, raw prompts, raw provider payload handling, or
runtime final-answer behavior.

## Review baseline

The review assumes the following merged AG-78 layers are authoritative:

- **AG-78A**: design posture for direct evidence, sourced-premise inference,
  caveats, source-bound/range-bound numeric posture, and AG-77 conflict
  interaction.
- **AG-78B**: inert `InferencePath` contract and evaluator-derived posture.
- **AG-78B-R1**: evaluator-derived posture and recommendation remain
  authoritative over constructor-supplied posture or recommendation attempts.
- **AG-78C**: visibility-only runtime / AnswerContract handoff under
  `indirect_inference_runtime_handoff`.
- **AG-78D**: bounded AnswerContract posture activation under
  `indirect_inference_answer_posture_activation`.
- **AG-78E**: Author-facing presentation handoff under
  `indirect_inference_author_presentation_handoff`, with direct, inferred,
  speculative/unsupported, blocked-by-conflict, and range/source-bound labels.

## Required review questions

### 1. Are the direct vs inferred labels clear enough for final-answer use?

**Verdict:** mostly ready, with one wording nuance to watch during dogfood.

The machine labels are clear enough for final-answer use because they separate
`directly_sourced` from `inferred_from_sourced_premises`, carry
`directly_sourced=false` for inferred conclusions, and require an inference
label only for supported inferred conclusions. The direct label is unlikely to
mislead because it exposes conclusion direct source IDs and uses
`direct_source_statement` attribution mode. The inferred label is also clear to
reviewers because it names both sides of the posture: the conclusion is inferred,
and the premises are sourced.

The remaining nuance is user-facing tone. `inferred from sourced premises` is
accurate, but it is architectural/legalistic. It should remain the safe default
for dogfood because it is explicit and citation-laundering-resistant. A later
Author wording phase may test friendlier variants.

### 2. Is “inferred from sourced premises” the right presentation wording?

**Verdict:** safe default for AG-78G dogfood; consider alternate wording only in
AG-78E-R1 if dogfood shows reader confusion.

Recommended wording hierarchy for future Author phases:

1. Keep **“inferred from sourced premises”** as the canonical trace/handoff
   wording.
2. Allow final-answer prose to use a shorter visible label such as
   **“inferred from cited premises”** only if the Author also preserves the
   boundary that the citation supports premises/bridge, not a directly stated
   conclusion.
3. Avoid **“source-supported inference”** as the primary label because it may
   sound like the conclusion itself is directly source-supported.
4. Avoid **“derived from sources”** for high-stakes/legal/current numeric cases
   because it can blur whether the derivation rule is externally grounded or
   model-assumed.

No immediate AG-78E-R1 wording repair is required before bounded dogfood because
the current phrase is conservative and auditable.

### 3. Do premise and bridge sources remain auditable without implying direct support?

**Verdict:** yes.

AG-78E keeps premise IDs, premise source IDs, bridge IDs, bridge types, and
bridge relationship source IDs visible while keeping
`conclusion_direct_source_ids=[]` for inferred conclusions. It also sets
`source_attribution_mode=premise_or_bridge_support_only`,
`premise_bridge_sources_support_direct_conclusion=false`, and boundary text that
premise/bridge sources do not mean the inferred conclusion was directly
source-stated.

This is the correct audit posture. Reviewers can inspect which sources support
premises and relationships without laundering those sources into direct support
for the final conclusion.

### 4. Are range-bound/source-bound numeric cases presentation-safe?

**Verdict:** ready for bounded dogfood with source-bound/range-bound cases
included.

Range-bound/source-bound numeric cases are presentation-safe because they use a
separate `range_bound_or_source_bound` label and preserve unresolved scalar
posture by keeping `resolved_scalar=false` when the value remains range-bound or
source-bound. This prevents the presentation layer from collapsing a range or
source-bound packet into a falsely precise scalar.

Dogfood should include numeric query classes, but only bounded examples where
the expected decision is whether the trace/presentation packet preserves range,
source, and unresolved-scalar posture. It should not attempt to repair numeric
source-class semantics or Economist behavior.

### 5. Are speculative/unsupported and blocked-by-premise-conflict cases prevented from becoming supported inference?

**Verdict:** yes.

AG-78B/B-R1 evaluator authority prevents constructor posture/recommendation
overrides from upgrading invalid, speculative, unsupported, or conflict-blocked
paths. AG-78C serializes that evaluator-derived posture. AG-78D mirrors it into
AnswerContract posture effects. AG-78E presents speculative/unsupported and
blocked-by-premise-conflict cases as non-supported labels with
`inference_label_required=false`.

This is the right no-promotion chain. No AG-78F-R1 safety repair is indicated.

### 6. Are AG-78 trace keys and handoff layers understandable, or is there adapter/trace ergonomics debt?

**Verdict:** understandable enough for dogfood; trace ergonomics debt exists but
is not blocking.

The layer sequence is coherent:

1. `indirect_inference_contract` owns inert path semantics and evaluator posture.
2. `indirect_inference_runtime_handoff` exposes AG-78B path facts to runtime /
   AnswerContract consumers.
3. `indirect_inference_answer_posture_activation` projects bounded posture
   effects.
4. `indirect_inference_author_presentation_handoff` exposes Author-facing
   presentation facts.

The debt is verbosity and cross-layer duplication: direct/inferred/conflict /
range/lower-tier posture appears in several adjacent packets. This is acceptable
for burn-down and dogfood because the duplication is additive and auditable. It
should not be paid down before dogfood unless reviewers cannot locate a claim
through all four keys. If that happens later, the right next phase is
`AG-76D-AD — adapter debt`, not a behavior phase.

### 7. Are tests sufficient across AG-78B/C/D/E, including citation-laundering and no-promotion guards?

**Verdict:** sufficient for dogfood prep.

The AG-78 focused tests cover:

- direct vs inferred path classification and evaluator-derived posture;
- constructor override no-promotion behavior;
- runtime handoff visibility and JSON-safe serialization;
- AnswerContract posture activation;
- Author presentation labels;
- citation-laundering guard fields;
- premise and bridge source visibility;
- speculative/unsupported non-promotion;
- blocked-by-premise-conflict non-promotion;
- range/source-bound numeric unresolved posture;
- lower-tier non-satisfaction;
- protected-import and `pipeline_orchestrator.py` diff guards.

No tiny test repair is required in AG-78F. If future dogfood reveals a missing
case, prefer an AG-78F-R1 static/test repair over changing runtime output.

### 8. Is the stack ready for bounded dogfood later?

**Verdict:** yes, with strict budget and packet-only review.

The stack is ready for later bounded dogfood because the core safety surfaces are
represented and tested without runtime final-answer changes. Dogfood should be a
visibility/review exercise, not a behavior-repair exercise. It should inspect
trace and handoff packets produced by bounded runs and decide whether AG-78G can
advance toward live presentation validation or must route to a focused repair
phase.

### 9. If dogfood is recommended later, what query classes and budget should be proposed?

**Recommended next phase:** `AG-78G — Bounded Indirect-Inference Dogfood`.

AG-78G should be packet-only and should use the following bounded plan:

- **Exact query classes:**
  1. Direct-answer control where an official/current source directly states the
     target claim.
  2. One-hop mathematical or source-stated relationship inference from sourced
     premises, with no direct source-stated conclusion.
  3. Range-bound/source-bound numeric inference where premises support a range
     or source-bound value but not a resolved scalar.
  4. Speculative/model-assumed bridge negative control where the model could
     imagine a bridge but no licensed bridge or required premise exists.
  5. Premise-conflict negative control where AG-77 conflict posture should block
     supported inference.
  6. Lower-tier/non-satisfying obligation negative control where lower-tier
     premises cannot satisfy a stronger official/current/legal/canonical or
     source-bound obligation.
- **Run budget:** maximum **6 ScryRaven/proplex/scryraven runs total**, one per
  class above. If a run fails for infrastructure reasons, allow at most **1
  replacement run**, still capped at **7 total runs**.
- **Provider/model/search budget:** no more than the normal per-run configured
  budget for the selected mode; do not increase provider count, search depth,
  retrieval budget, model effort, or provider/model/search call limits for
  AG-78G. If the harness exposes explicit call counters, record actual provider,
  model, and search call counts per run in the packet.
- **Output packet path:** `output/ag78g_bounded_indirect_inference_dogfood/` with
  one redacted packet per query class and a single summary file named
  `AG78G_PACKET_SUMMARY.md`.
- **Redaction plan:** redact raw prompts, raw provider payloads, API keys,
  cookies, tokens, local absolute paths, usernames, account/session IDs, and any
  private notes. Keep normalized query class, final answer excerpt only if
  needed for label audit, source IDs/titles/domains, AG-78 trace keys,
  AnswerContract posture fields, and citation/source-attribution boundary fields.
- **Decision the run will make:** decide whether AG-78 trace/presentation packets
  preserve direct vs inferred labeling, audit premise/bridge sources without
  citation laundering, keep range/source-bound numeric posture unresolved, and
  prevent speculative/conflict/lower-tier cases from becoming supported
  inference.
- **Stop condition:** stop immediately if dogfood requires changing runtime
  output, prompts, retrieval, provider/model/search behavior, source-class /
  currentness semantics, AG-78B evaluator semantics, AG-78D activation semantics,
  AG-77 conflict arbitration, citation selection/source ordering, DB/session /
  RunOutcome shape, cache behavior, Scrutineer/remediation, Economist/follow-up,
  broad orchestration, live validation beyond the bounded plan, inference
  opportunity detection, or raw prompt/provider payload handling.

## Protected surfaces kept closed in AG-78F

AG-78F kept the following surfaces closed:

- provider/model/search/query behavior;
- retrieval ranking/filtering;
- source-class/currentness semantic changes;
- AG-78B evaluator semantic changes;
- AG-78D posture activation semantic changes;
- AG-77 conflict arbitration behavior;
- citation selection/source ordering redesign;
- DB/session/RunOutcome shape;
- cache implementation;
- Scrutineer/remediation;
- Economist/follow-up behavior;
- broad pipeline orchestration;
- live validation;
- inference-opportunity detection;
- raw prompt or raw provider payload handling;
- runtime final-answer behavior changes.

## Final readiness classification

AG-78F classifies the merged AG-78 indirect-inference presentation stack as
**ready for bounded dogfood later**. The recommended next smallest useful phase
is **AG-78G — Bounded Indirect-Inference Dogfood**.

Do not open AG-78F-R1 unless a reviewer identifies a concrete missing safety or
test guard. Do not open AG-78E-R1 unless dogfood or product review shows the
current wording confuses readers. Do not open AG-76D-AD unless trace/handoff
scaffolding, not inference presentation safety, becomes the blocker.
