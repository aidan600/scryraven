Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG78A_INDIRECT_EVIDENCE_INFERENCE_POSTURE_DESIGN).

# AG-78A — Controller-Owned Indirect Evidence / Inference Posture Design

Date: 2026-06-01

## Phase type

Architecture design only. AG-78A does not implement runtime inference logic, final-answer behavior, Author prompt behavior, citation behavior, provider/search/retrieval behavior, source-class semantics, or AG-78B contract code.

## Current state after AG-77D

AG-77A provides passive source-conflict representation. AG-77B adds Controller-owned conflict arbitration posture. AG-77C makes arbitration visible to Controller / AnswerContract runtime state under `source_conflict_arbitration`. AG-77D activates a bounded subset of already-arbitrated conflict posture into Controller / AnswerContract posture metadata without changing final-answer prose, Author prompts or exposure, citation behavior, prompt semantics, provider/search/query behavior, retrieval behavior, source-class/currentness detection semantics, Scrutineer/remediation, Economist/follow-up, DB/session/RunOutcome shape, cache behavior, or AG-78 indirect inference behavior.

That leaves a distinct unanswered design problem: ScryRaven can encounter questions where no source directly states target claim A, but sources do establish premises B, C, etc., and a valid bridge supports A. AG-77 governs evidence tension; it does not decide whether a non-direct conclusion may be inferred from sourced premises.

## Purpose: indirect evidence / inference posture

AG-78A defines how ScryRaven should represent and govern answers that are not direct-citation-only and not hallucinated. The intended product posture is:

- ScryRaven should answer directly when a source directly states the target claim.
- ScryRaven should use AG-77 conflict posture when credible evidence is in tension.
- ScryRaven may infer a conclusion from sourced premises when the inference bridge is valid, mode-appropriate, and honestly labeled.
- ScryRaven must not present an inferred conclusion as directly sourced unless a source directly states that conclusion.
- ScryRaven must decline, caveat, or mark unsupported conclusions when the bridge depends on missing premises, unresolved blocking conflicts, speculative assumptions, or a bridge class not licensed for the current mode.

AG-78A is a Controller-owned posture design. It is not a prompt-only instruction set. Prompt wording and final-answer presentation remain closed until a later licensed phase.

## Direct vs inferred vs speculative distinction

### Directly sourced

A target claim is directly sourced when an eligible source explicitly states the same conclusion the answer would present as claim A, with enough matching scope, entity identity, time period, jurisdiction, units, and qualifiers that no substantive reasoning bridge is required beyond citation, quotation/paraphrase, or trivial normalization.

Allowed direct-source normalizations include formatting, unit label preservation, date-format normalization, and grammar changes that do not alter meaning. A claim stops being directly sourced if the answer must combine separate premises, resolve an unstated relationship, apply a rule, compute a derived value, choose among conflicting authorities, or assume a missing fact.

### Inferred from sourced premises

A target claim is inferable from sourced premises when:

1. no eligible source directly states A;
2. sources establish the required premises B, C, etc.;
3. the premise identities, source identities, source classes, dates, scopes, units, and qualifiers are preserved;
4. a declared inference bridge connects the premises to A;
5. the bridge type is licensed for the current mode;
6. AG-77 conflict posture does not block the premise set; and
7. the resulting answer is labeled as inferred from sourced premises, not directly sourced.

The inference may be exact, range-bound, caveated, or declined depending on premise confidence, bridge strength, source class, and conflict impact.

### Speculative / unsupported

A target claim is speculative or unsupported when any required premise is absent, the bridge is model-assumed rather than externally grounded, the bridge requires domain expertise beyond the licensed mode, the source class is insufficient for the obligation, premise conflicts are unresolved and material, or the answer would need to hide assumptions from the user. Speculative claims must not be upgraded to inferred claims merely because the model can imagine a plausible path.

## Three answer-path families

### 1. Direct evidence answer path

Use this path when a source directly states A. The answer may cite A directly, subject to existing citation and Author behavior. AG-78 inference posture should record that no inference bridge was required or should remain absent.

Examples:

- A statute page directly says the filing deadline is a specific date.
- A company filing directly states total revenue for a fiscal year.
- An official FAQ directly states eligibility for a named program.

### 2. Conflict-arbitrated evidence answer path

Use this path when credible evidence is in tension about A or about premises that would be required for A. The AG-77 stack governs representation, arbitration, visibility, and posture activation. AG-78 must consume AG-77 posture rather than re-arbitrating conflicts.

Possible outcomes include:

- direct answer blocked because equal official/current sources conflict;
- answer caveated because a lower-tier or stale source conflicts with stronger evidence;
- numeric value range-bound because source-bound numeric premises disagree;
- background-only conflict preserved without answer impact.

### 3. Indirect inference from sourced premises answer path

Use this path when no source directly states A, but sourced premises support A through an explicit bridge. The answer must be labeled as inferred from sourced premises and should expose, at minimum in future Author-facing behavior, the premises and bridge sufficient for the user to understand why A follows.

Examples:

- Source B states a fee is $20 per unit; source C states 3 units were purchased; A is the total fee of $60 via a mathematical bridge.
- Source B defines a term; source C states an entity satisfies the defined conditions; A is a definitional classification via a definitional bridge.
- Source B states a legal rule; source C states the relevant fact pattern; A is a legal implication only if the mode and source class license that inference.

## Premise / bridge / target-claim model

AG-78B should model inference as an explicit path rather than as free text. The conceptual fields are:

### Target claim A

- stable `target_claim_id`;
- normalized claim text;
- answer obligation or user-question facet the claim satisfies;
- expected claim type such as factual, numeric, definitional, legal/statutory, eligibility, comparison, or range;
- scope qualifiers: entity, geography, jurisdiction, time period, effective date, units, and conditions;
- whether the claim is directly sourced, inferred, conflict-governed, speculative/unsupported, caveated, range-bound, or declined.

### Sourced premises B, C, etc.

Each premise should preserve:

- stable `premise_id`;
- premise text as asserted by a source;
- source identity and citation/source reference identity already used elsewhere in Controller state;
- source class such as official/current, official/stale, canonical, legal/statutory, primary data, source-bound numeric, reputable secondary, lower-tier/background, or unknown;
- source date, effective date, jurisdiction/scope, unit, and qualifier metadata where available;
- premise confidence before inference;
- AG-77 conflict posture affecting the premise;
- whether the premise is required, optional/background, assumption, or sensitivity variable.

### Inference bridge

Each bridge should preserve:

- stable `bridge_id`;
- bridge type;
- bridge description in machine-readable and human-readable form;
- required premises;
- transformation or rule shape, without executing hidden runtime reasoning in AG-78A;
- allowed modes;
- bridge strength: exact, high-confidence, domain-conditioned, assumption-dependent, speculative;
- whether the bridge is source-stated, externally normative, domain-standard, or model-assumed;
- failure modes and assumptions.

### Inference path

An inference path connects premises to a target claim and should preserve:

- ordered one-hop or multi-hop path steps;
- mode policy applied;
- premise conflict impacts;
- confidence/posture inheritance;
- final posture recommendation: may state, state with caveat, range-bound, decline, or unsupported;
- attribution posture distinguishing premise citations from conclusion labeling.

## Bridge-type taxonomy

### Mathematical

A deterministic calculation, conversion, aggregation, difference, ratio, or range computation from sourced numeric premises. The bridge is strong only when units, dates, populations, and formulas are compatible. Source-bound numeric policy applies: derived numbers must preserve premise source identities and must not pretend that a source directly stated the derived value.

### Definitional

Application of a sourced definition to sourced facts. The definition may come from an official glossary, statute, standard, canonical documentation, or source-stated definition. The bridge is strong when all necessary definition elements are sourced and scope-matched.

### Legal/statutory

Application of legal or regulatory text to sourced facts. This is high-risk and should require official/current legal sources, jurisdiction/effective-date matching, explicit caveats, and conservative mode policy. Balanced should allow only simple one-hop statutory implications from official sources. Deep may model competing legal bridges or effective-date ranges, but should still avoid legal advice posture unless separately licensed.

### Domain-standard

An inference using a widely accepted field convention, formula, taxonomy, or standard operating definition. This requires a sourced or canonical statement of the standard when the standard is not trivial. Domain-standard bridges are weaker than mathematical or source-stated bridges because applicability often depends on context.

### Source-stated relationship

A source states the relationship or rule that links premises, but does not state the final target claim. For example, a source states the conversion rule or dependency, while another source states the input value. This bridge is generally stronger than model-assumed reasoning because the relationship itself is sourced.

### Model-assumed / speculative

The model supplies the relationship, causal link, typicality assumption, or missing rule from general plausibility rather than from a source, definition, statute, math, or documented domain standard. This bridge cannot support an inferred answer posture by itself. It may only support an explicit unsupported/speculative posture or a request/need for more evidence.

## Fast / Balanced / Deep inference-depth policy

### Fast

Fast should be mostly direct evidence only. It may allow trivial transformations that do not introduce substantive new claims, such as arithmetic formatting already implied by one source, exact unit display when the unit is sourced, or direct restatement of a source-stated relationship. Fast should not perform deep component-chain inference, legal/statutory application, multi-source aggregation, competing bridge analysis, or multi-hop reasoning.

Allowed Fast bridges:

- direct evidence path;
- trivial mathematical normalization from one source-bound premise when no material assumptions are introduced;
- source-stated relationship only when the conclusion is effectively a direct restatement and clearly labeled if not direct.

### Balanced

Balanced should support controlled one-hop inference. It may infer A when B and C are sourced, the bridge is explicit and valid, all required premises are source-compatible, and the path is exposed. Balanced is the recommended initial AG-78B target.

Allowed Balanced bridges:

- mathematical one-hop calculations with compatible units/scope;
- definitional one-hop classification when all definition elements are sourced;
- source-stated relationship one-hop inference;
- simple domain-standard inference when the standard is sourced or canonical;
- narrow legal/statutory one-hop inference only from official/current legal premises with jurisdiction/effective-date match and caveat posture.

Balanced should not support multi-hop component chains, competing legal theories, speculative bridges, or unstated assumptions.

### Deep

Deep may support multi-hop inference, ranges, sensitivity analysis, competing bridges, assumptions, and alternative path comparison. Deep must be more explicit about uncertainty and alternatives. It may carry multiple candidate paths and explain why one is stronger or why the result is range-bound or declined.

Allowed Deep bridges:

- all Balanced bridge types;
- multi-hop mathematical and definitional paths;
- domain-standard paths with explicit applicability assumptions;
- legal/statutory paths with competing interpretations represented, not silently resolved;
- sensitivity/range bridges where premise values or dates vary;
- assumptions only when clearly labeled as assumptions and not upgraded to sourced premises.

Deep still cannot treat model-assumed/speculative bridges as supported inferred conclusions.

## Confidence and posture inheritance rules

Inference confidence is inherited from the weakest required premise and the bridge strength. A high-confidence bridge cannot rescue an unsupported or materially conflicted premise. A high-quality premise cannot rescue a speculative bridge.

Recommended posture combination rules:

1. If any required premise is missing, the path is unsupported.
2. If any required premise is blocked by unresolved AG-77 conflict, the path is blocked or declined.
3. If required premises are source-bound numeric values with unresolved disagreement, the path is range-bound only when the range is defensible and complete; otherwise it is declined.
4. If premises are lower-tier than the answer obligation requires, the path may provide background context but cannot satisfy authoritative posture.
5. If the bridge is exact and all required premises are strong, the inferred claim may be stated with an inference label.
6. If the bridge is domain-conditioned or legal/statutory, the inferred claim should be caveated even when stated.
7. If the bridge is model-assumed/speculative, the claim remains speculative/unsupported.

Posture labels should include at least: `directly_sourced`, `inferred_from_sourced_premises`, `conflict_arbitrated`, `caveated_inference`, `range_bound_inference`, `blocked_by_premise_conflict`, `unsupported`, and `speculative`.

## Interaction with AG-77 conflict posture

AG-78 must treat AG-77 as upstream authority for premise usability. It must not redefine source conflict classes, arbitration decisions, or answer-posture activation rules.

### Conflict blocks inference when

- equal official/current sources conflict on a required premise;
- official/current legal/canonical premises conflict and AG-77 marks authoritative posture insufficient;
- a source-bound numeric value is unresolved and no complete range can be formed;
- jurisdiction, scope, effective-date, or entity conflicts affect a required premise;
- the conflict affects the bridge itself, such as competing definitions or formulas.

### Conflict weakens inference when

- the conflict is lower-tier vs higher-tier and AG-77 preserves lower-tier evidence as background only;
- stale evidence conflicts with current evidence but does not defeat the current premise;
- peripheral/background conflicts do not affect required premises;
- a premise remains usable but should lower confidence or require caveat posture.

### Conflict range-bounds inference when

- all materially plausible numeric premise values are source-bound and preserved;
- the bridge can be applied separately to each value without changing assumptions;
- the resulting interval honestly represents unresolved premise variation;
- the answer labels the result as range-bound, not as a single resolved value.

## How source class / source hierarchy affects premise strength

Source class determines whether a premise can satisfy the obligation behind the target claim:

- Official/current, legal/statutory, canonical, and primary-data sources can generally support authoritative premises when scope-matched.
- Source-bound numeric premises can support calculations only if their source identity, units, scope, and date remain attached to the derived result.
- Reputable secondary sources can support background, explanatory, or non-authoritative inferences, and may support direct answers when no stronger obligation applies.
- Lower-tier/background sources cannot satisfy stronger official/current/legal/canonical obligations when AG-77 or source hierarchy says they are non-satisfying.
- Unknown or weak source classes should not support consequential inferred claims without stronger evidence.

AG-78 should preserve source hierarchy rather than flattening all premises into generic citations.

## How source-bound numeric premises should behave

Numeric premises require special handling because derived values are easy to overstate. AG-78 posture should require:

- preservation of each numeric premise's source identity;
- preservation of units, population, date/effective date, and formula context;
- explicit marking that derived values are calculated/inferred, not directly source-stated;
- no resolved scalar when AG-77 marks the underlying source-bound value unresolved;
- range-bound output when conflicting numeric premises can support a defensible interval;
- decline when numeric conflicts, unit mismatches, missing denominators, or incompatible scopes make the calculation unsafe.

## How inferred answers must be labeled

Future Author-facing behavior should distinguish:

- “Directly sourced”: the cited source states A.
- “Inferred from sourced premises”: the cited sources state B/C and ScryRaven applies a declared bridge to derive A.
- “Speculative/unsupported”: the premises or bridge are insufficient, so ScryRaven cannot state A as supported.

For inferred answers, citations should attach to premises and any sourced bridge, while the prose should not imply that a cited source directly states the final conclusion unless it does. AG-78A does not change citation formatting or final-answer wording; it defines the Controller posture that future phases should expose.

## How unsupported/speculative claims are prevented

Unsupported/speculative claims are prevented by Controller-owned gating rather than prompt-only reminders:

- required-premise completeness checks;
- source identity and source-class preservation;
- bridge type enumeration;
- mode policy checks;
- AG-77 premise conflict consumption;
- confidence/posture inheritance from weakest premise and bridge;
- explicit unsupported/speculative posture when premises or bridge fail;
- JSON-safe trace/controller state for review and fixture testing.

A model-generated rationale with no eligible bridge must not create support. A plausible inference with an untracked assumption must stay caveated or unsupported.

## Required AG-78B contract fields

AG-78B should be a minimal inert Controller-visible indirect inference contract with fixture/static tests. It should likely introduce these dataclasses/enums or equivalents:

- `IndirectInferenceState` — top-level JSON-safe state and schema version.
- `TargetClaim` — target claim A identity, text, scope, obligation, and posture.
- `SourcedPremise` — premise identity, text, source identity, source class, scope/date/unit qualifiers, confidence, and conflict posture reference.
- `InferenceBridge` — bridge identity, type, description, required premise IDs, bridge strength, allowed modes, and assumption posture.
- `InferencePath` — ordered premise/bridge/target relationship, mode applied, one-hop vs multi-hop marker, final recommendation, and confidence inheritance.
- `InferencePosture` — direct, inferred, caveated, range-bound, conflict-blocked, unsupported, speculative, or declined posture.
- `InferenceModePolicy` — Fast/Balanced/Deep depth and bridge allowances.
- `PremiseConflictImpact` — none, weakens, range-bounds, blocks, background-only, or non-satisfying-for-obligation.
- `InferenceSourceAttribution` — premise source IDs, bridge source IDs where applicable, conclusion-label posture, and direct-vs-inferred attribution.
- JSON-safe `to_controller_state()` and `to_trace_fragment()` methods with explicit protected-surface `*_behavior_changed: false` flags.

AG-78B should start with Balanced one-hop inference from sourced premises through explicit valid bridges. It should be additive and inert.

## Required AG-78B fixture/static tests

AG-78B should include fixture/static tests for:

1. direct target claim represented separately from inferred target claim;
2. Balanced one-hop mathematical inference from two sourced premises;
3. Balanced one-hop definitional inference with all definition elements sourced;
4. source-stated relationship bridge where the relationship source is preserved;
5. model-assumed/speculative bridge rejected or marked unsupported;
6. Fast mode rejects non-trivial multi-premise inference;
7. Balanced mode rejects multi-hop inference;
8. Deep mode can represent multi-hop posture without executing final-answer behavior;
9. premise conflict blocks inference when AG-77 marks required premise unresolved/blocking;
10. premise conflict weakens or backgrounds inference when AG-77 marks lower-tier/nonblocking conflict;
11. source-bound numeric conflict produces unresolved or range-bound posture, not a resolved scalar;
12. lower-tier source cannot satisfy official/current/legal/canonical obligation;
13. `to_controller_state()` and `to_trace_fragment()` are JSON-safe and preserve source identities;
14. protected-surface flags show no final-answer, Author, citation, provider/search/retrieval, DB/session/RunOutcome, cache, Scrutineer, Economist/follow-up, or orchestrator behavior change;
15. static guard that `core/pipeline_orchestrator.py` is not imported or rewritten by the contract tests.

## Closed surfaces for AG-78B

AG-78B must not change:

- final-answer prose behavior;
- Author prompts, Author exposure, or Author evidence handoff;
- citation formatting, citation selection, citation ordering, or source ordering;
- prompt text or prompt semantics;
- provider/model/search/query behavior;
- retrieval ranking/filtering;
- source-class/currentness detection semantics;
- conflict arbitration behavior;
- Scrutineer/remediation;
- Economist/follow-up behavior;
- DB/session/RunOutcome shape;
- cache implementation;
- `core/pipeline_orchestrator.py`;
- live validation;
- broad orchestrator integration.

AG-78B should not implement final-answer inference behavior. It should only add an inert contract and tests.

## Stop conditions for AG-78B

Stop AG-78B and redesign if progress requires:

- runtime final-answer behavior changes;
- Author prompt/exposure changes;
- citation behavior changes;
- provider/model/search/query changes;
- retrieval behavior changes;
- source-class/currentness semantic changes;
- conflict arbitration semantic changes;
- Scrutineer/remediation or Economist/follow-up changes;
- DB/session/RunOutcome/cache changes;
- `pipeline_orchestrator.py` changes;
- live ScryRaven/proplex/scryraven runs;
- provider/model/search calls;
- implementation of actual inference execution beyond inert contract representation;
- product decisions about how final prose should read.

## Recommended next phase

Recommended next phase: **AG-78B — Minimal Indirect Inference Contract with Fixture Tests**.

Rationale: AG-78A supports a bounded first implementation that is additive, inert, Controller-visible, and testable without runtime behavior changes. AG-78B should begin with Balanced one-hop inference representation from sourced premises through explicit valid bridges, with JSON-safe controller/trace serialization and protected-surface fixture/static tests.
