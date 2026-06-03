# AG-81B Answer Quality Rubric and Output Contract

Status: product behavior design / docs-first; no runtime behavior change; no prompt tuning; no live validation; no provider/model/search calls

## 1. Purpose and scope

AG-81B defines ScryRaven's user-facing answer-quality rubric and the stable Fast / Balanced / Deep output contract. It describes what a good answer should communicate after the runtime has already produced Controller-authorized posture, evidence, limitations, source-class obligations, conflict labels, and inference labels.

AG-81B governs presentation quality only. It is not a new runtime authority source, not a retrieval policy, not a prompt change, and not a validation result.

AG-81B is distinct from:

- **Runtime correctness:** whether the pipeline, adapters, handoffs, and persistence execute correctly.
- **Retrieval quality:** whether search/provider/retrieval acquired the best possible sources.
- **Controller authority obedience:** whether Analyst, Author, and other downstream surfaces obey Controller / AnswerContract posture.
- **Source acquisition success:** whether official, current, canonical, primary, or other required source classes were found.
- **Live validation results:** whether any live run proves a behavior in production-like conditions.

Explicit phase boundaries:

- AG-81B does **not** change runtime behavior.
- AG-81B does **not** tune prompts.
- AG-81B does **not** change Author behavior.
- AG-81B does **not** change Analyst, Economist, Scrutineer, synthesis-evaluator, Controller, or AnswerContract behavior.
- AG-81B does **not** change provider/search/retrieval, provider routing, query generation, source ranking/filtering, final evidence selection, citation generation, source ordering, cache behavior, DB/session/RunOutcome shape, package names, CLI names, or environment compatibility names.
- AG-81B defines desired presentation quality and review criteria, not a new authority source. Controller / AnswerContract posture remains authoritative wherever it governs final-answer posture.

## 2. Product answer principles

A good ScryRaven answer should satisfy these principles regardless of mode:

1. **Source-grounded, not source-laundered.** Citations should support the claims they accompany. A cited sentence must not imply stronger support than the cited source provides.
2. **Concise by default, complete when obligations require it.** Brevity is valuable, but not at the expense of central caveats, insufficiency posture, conflict posture, or inference labels.
3. **Useful uncertainty, not evasive uncertainty.** Uncertainty should tell the user what is known, what is missing, and why it matters. It should not become generic hedging.
4. **Citations support explanation; they do not replace it.** The answer should explain the reasoning or evidence basis in user-meaningful terms instead of dumping source links.
5. **Central conflicts and inferred claims remain visible.** If a conflict or inference affects the answer, it should be surfaced near the relevant claim, not buried in backend-style trace language.
6. **Weak evidence produces honest partial or insufficient posture.** If source obligations are unmet, the answer should say so and provide only the bounded information allowed by the available evidence.
7. **User intent matters, but source obligations still govern.** Format, level of detail, and examples should follow the user request where possible. Confidence, insufficiency, conflict, and inference boundaries should not be suppressed to satisfy style preferences.
8. **Different models may write differently; the output contract should remain stable.** Voice can vary, but answer order, caveat visibility, evidence boundaries, and mode expectations should remain recognizable.
9. **Structure should help the user act.** The answer should prioritize decision-ready information over raw backend trace, while still exposing source quality and limits where they affect trust.
10. **Evidence quality should be communicated without overwhelming the answer.** Mention source class, freshness, conflicts, and gaps at the level needed for the task and selected mode.

## 3. Fast / Balanced / Deep mode contract

### Fast

Fast mode promises:

- a direct, concise answer when the evidence supports one;
- minimal scaffolding;
- enough citation, limitation, conflict, or inference visibility to avoid overclaiming;
- fast refusal or insufficiency when evidence is too weak for the requested answer;
- answer-first ordering when Controller / AnswerContract posture allows an answer;
- no extra report structure unless needed to preserve source obligations.

Fast mode does **not** promise:

- reckless compression;
- hidden uncertainty;
- hidden source gaps;
- silent conflict suppression;
- unsupported numeric precision;
- full evidence mapping;
- exhaustive context.

### Balanced

Balanced mode promises:

- the default useful research brief;
- a short answer followed by compact reasoning or evidence basis;
- clear visibility for source quality, caveats, limitations, conflicts, and inferred claims;
- a practical distinction between the answer, evidence, and limits;
- enough context for trust without report-like verbosity;
- suitability for most serious user questions.

Balanced mode does **not** promise:

- exhaustive source-by-source analysis;
- long background sections by default;
- suppression of caveats for readability;
- Deep-mode audit detail.

### Deep

Deep mode promises:

- a report-like answer appropriate to complex, high-stakes, controversial, developing, multi-source, or source-quality-sensitive questions;
- an explicit evidence map or evidence-basis section;
- conflict, gap, and inference handling;
- source-quality discussion where useful;
- more visible assumptions, quantitative assumptions, and next checks;
- clear statement of what would change the answer.

Deep mode does **not** promise:

- verbosity for its own sake;
- backend trace dumping;
- speculative expansion beyond evidence;
- lower confidence merely because the answer is longer;
- live validation or new retrieval beyond what runtime actually performed.

## 4. Scenario-specific rubrics

### Ordinary factual / research answer

- **Should contain:** direct answer; compact explanation; citations for central facts; note of important limits if any.
- **Should avoid:** burying the answer; over-indexing on caveats; unsupported background claims; source dumps without synthesis.
- **Must remain visible:** any Controller-authorized insufficiency, conflict, inference label, or source-class gap that affects the answer.
- **Mode differences:** Fast gives answer plus minimal caveat; Balanced gives short answer plus evidence basis; Deep adds source map and alternative interpretations if relevant.
- **Common failure modes:** wall of citations; crisp answer with no support; irrelevant background; caveat sludge.

### Current / official / canonical answer

- **Should contain:** answer tied to the current, official, canonical, or primary source obligation; source date or effective-date relevance when central; explicit gap if only secondary/stale evidence is available.
- **Should avoid:** treating secondary commentary as official; using stale pages silently; answering from memory when current official sourcing is required.
- **Must remain visible:** missing official/current source posture; stale-source warning; jurisdiction or scope boundary.
- **Mode differences:** Fast may say the official/current source is missing and provide a limited answer; Balanced explains source class and date relevance; Deep maps official/current versus secondary evidence.
- **Common failure modes:** official-source laundering; stale-current laundering; source-class mismatch hidden behind citations.

### Legal / regulatory / government numeric answer

- **Should contain:** jurisdiction/scope; effective date or tax/regulatory year where relevant; source-bound numeric value; official/current source basis or explicit insufficiency.
- **Should avoid:** unsupported precision; mixing jurisdictions; giving advice beyond evidence; treating examples or summaries as binding law.
- **Must remain visible:** official/current/legal source obligations, missing-source posture, conflicts between official materials, and source-bound numeric uncertainty.
- **Mode differences:** Fast provides the number only when source-bound and caveated; Balanced adds applicability and caveat; Deep maps authority hierarchy, conflicts, effective dates, and next official checks.
- **Common failure modes:** invented exact figures; stale law; missing jurisdiction; secondary-source legal laundering.

### Weak evidence / insufficient corpus

- **Should contain:** clear insufficiency or partial-answer posture; what can still be said; why stronger evidence is missing or required; safe next check.
- **Should avoid:** pretending weak evidence is adequate; refusing when a bounded partial answer is allowed; generic disclaimers that do not identify the gap.
- **Must remain visible:** weak corpus, unmet source-class obligations, or unavailable provider/search/retrieval result posture.
- **Mode differences:** Fast gives brief insufficiency plus any safe partial; Balanced explains the missing evidence class; Deep itemizes gaps and what evidence would resolve them.
- **Common failure modes:** overconfident answer; total refusal despite usable partial evidence; vague uncertainty.

### Source conflict

- **Should contain:** the contested claim; conflicting sources or source classes; whether the answer can be resolved, partially answered, or must remain uncertain; user-relevant implication.
- **Should avoid:** choosing a winner without authorized resolution; hiding equal-authority disagreement; presenting one side as settled if Controller posture says conflict remains.
- **Must remain visible:** conflict label, source hierarchy relevance, current/stale distinction, jurisdiction/scope mismatch, and any source-bound numeric conflict.
- **Mode differences:** Fast notes the conflict near the answer; Balanced gives a compact conflict note; Deep provides a conflict map and next checks.
- **Common failure modes:** conflict laundering; winner-by-prose; citation list without explaining disagreement.

### Indirect inference from sourced premises

- **Should contain:** direct premises; inferred claim; bridge between premises and inference; caveat or range when premise quality limits the inference.
- **Should avoid:** citing an inferred claim as if directly stated; hiding the bridge; making speculative leaps.
- **Must remain visible:** inferred-vs-direct boundary and any premise conflict or unsupported premise.
- **Mode differences:** Fast uses a short phrase such as "This is an inference"; Balanced includes a one- or two-sentence bridge; Deep separates direct evidence, inference bridge, and confidence limits.
- **Common failure modes:** inference laundering; unsupported bridge; overstated conclusion.

### Quantitative / Economist-supported answer

- **Should contain:** source-bound inputs; assumptions; calculation or estimate summary; uncertainty range when appropriate; distinction between sourced values and derived estimates.
- **Should avoid:** false precision; hidden assumptions; mixing estimates with directly sourced numbers; numeric claims not tied to evidence.
- **Must remain visible:** source-bound numeric values, inferred/estimated values, conflicts in inputs, and weak-evidence numeric posture.
- **Mode differences:** Fast gives result plus key assumption; Balanced shows compact math and source basis; Deep provides input table, sensitivity, and what would change the estimate.
- **Common failure modes:** unsupported numeric precision; laundering estimates as facts; omitting unit/timeframe.

### Follow-up question

- **Should contain:** answer to the follow-up; relevant dependency on prior context; refreshed source obligation if the new question requires it; note when prior evidence is reused only as context.
- **Should avoid:** assuming saved context satisfies changed source obligations; ignoring new jurisdiction/date/scope; repeating the whole previous answer unnecessarily.
- **Must remain visible:** any changed obligation, reused-context boundary, and insufficiency/conflict/inference posture inherited or newly produced.
- **Mode differences:** Fast answers the delta; Balanced summarizes dependency on prior context; Deep maps old versus new evidence and obligations.
- **Common failure modes:** stale follow-up reuse; context laundering; failure to answer the actual follow-up.

### "Just answer" or concise-answer request

- **Should contain:** the shortest answer that still preserves central caveats, source-class gaps, conflict labels, or inference boundaries.
- **Should avoid:** disclaimer walls; hiding uncertainty; refusing solely because the user asked for brevity; compressing away legally or evidentially central qualifiers.
- **Must remain visible:** required confidence, insufficiency, conflict, stale-source, missing-official, and inference boundaries.
- **Mode differences:** Fast and "just answer" often align, but Fast still obeys posture; Balanced may use two bullets; Deep should only be selected if the user or task requires depth.
- **Common failure modes:** crisp but misleading answer; excessive caveat sludge; source obligations silently dropped.

### Controversial or developing topic

- **Should contain:** current state of evidence; date/freshness sensitivity; contested claims; what is settled versus disputed; source-quality note.
- **Should avoid:** false balance when evidence hierarchy is clear; premature certainty when facts are developing; using social/noisy sources as authoritative.
- **Must remain visible:** recency/freshness limits, conflicts, lower-tier evidence, and unresolved facts.
- **Mode differences:** Fast gives bounded current answer plus caveat; Balanced distinguishes settled/disputed; Deep maps source classes, timelines, and next checks.
- **Common failure modes:** overconfident early answer; burying date sensitivity; source-quality flattening.

### Document-review style answer

- **Should contain:** boundary that the answer is based on provided document(s); direct references to document content where available; distinction between document claims and external/public truth; review posture appropriate to the task.
- **Should avoid:** treating user documents as verified public facts; importing web conclusions without sourced acquisition; exposing private document text unnecessarily.
- **Must remain visible:** document/corpus boundary, unsupported public-truth claims, missing external validation if relevant.
- **Mode differences:** Fast summarizes document-local answer; Balanced separates document says / reviewer assessment / limits; Deep provides issue map, evidence snippets, and external-check recommendations.
- **Common failure modes:** user-document laundering; privacy-insensitive quoting; unsupported external conclusions.

### Personal corpus / library style answer

- **Should contain:** corpus boundary; which library items or user-provided materials support the answer; distinction between personal corpus evidence and public evidence; missing-corpus or insufficient-corpus posture.
- **Should avoid:** generalizing private corpus claims into public truth; treating absence from the corpus as absence in the world; overexposing private material.
- **Must remain visible:** corpus boundary, source availability limits, and whether public/current evidence was or was not used.
- **Mode differences:** Fast gives corpus-local answer; Balanced gives corpus evidence basis; Deep maps corpus coverage, gaps, and possible external checks.
- **Common failure modes:** corpus laundering; unsupported public claims; ignoring corpus insufficiency.

## 5. Evidence and citation posture

Answer quality depends on preserving the evidence posture already established by runtime authority.

- **Source-class satisfaction:** The answer should identify when required source classes are satisfied or unmet if the obligation affects the conclusion. Official/current/canonical obligations cannot be satisfied by lower-tier sources unless Controller posture explicitly permits a partial answer.
- **Citation placement:** Place citations close to the claims they support. Avoid citation clusters that make it unclear which source supports which claim.
- **Source cards vs inline citations:** Inline citations support sentence-level or paragraph-level claims. Source cards can provide reviewable source metadata. Source cards do not by themselves prove every claim in the answer.
- **Unsupported claims:** Claims not supported by provided evidence should be omitted, clearly labeled as general background when allowed, or identified as unsupported if central to the user's question.
- **Inferred claims:** Inferred claims should be labeled as inferred and should cite the sourced premises, not pretend that the source directly states the conclusion.
- **Stale sources:** If freshness matters, stale sources should be labeled and should not support a current answer unless the posture permits a historical or partial answer.
- **Missing official/current sources:** If an official/current source is required but missing, the answer should state that boundary and avoid presenting lower-tier evidence as definitive.
- **Source conflicts:** Conflicts should be visible when central. The answer should describe what conflicts, why source hierarchy matters, and whether the answer can be resolved.
- **Lower-tier evidence:** Lower-tier evidence may support background or partial answers only within explicit limits. It should not be framed as equivalent to official/current/primary evidence.
- **User-provided documents vs web evidence vs model inference:** User documents support document-local or corpus-local claims. Web evidence supports public claims within source-class limits. Model inference can connect sourced premises only when labeled and bounded.
- **Source-bound numeric values:** Numeric values should cite their source, unit, timeframe, jurisdiction, and effective date when relevant. Derived numbers should show assumptions or be labeled estimates.
- **Partial answers:** When stronger obligations are unmet, ScryRaven may provide a partial answer only if the unmet obligation remains visible and the partial claim is bounded to the available evidence.

Anti-laundering rules:

- **No citation laundering:** a citation must not be attached to a claim it does not support.
- **No inference laundering:** an inferred conclusion must not be presented as directly sourced.
- **No weak-source laundering:** lower-tier, stale, anecdotal, or secondary evidence must not be presented as satisfying stronger source obligations.
- **No user-document laundering into public truth:** document-local or corpus-local claims must not be generalized as verified public facts without appropriate public evidence.
- **No unsupported numeric precision:** exact numbers, ranges, and rankings must not be invented or over-precise relative to the evidence.

## 6. "Just answer" behavior

ScryRaven should respect requests for brevity by changing format, not by weakening source obligations.

A short answer is enough when:

- the evidence directly supports the answer;
- no central conflict, insufficiency, stale-source issue, or inference boundary affects the claim;
- the requested format is simple, such as a date, definition, name, or one-step factual answer.

A caveat must remain when:

- the answer relies on indirect inference;
- required official/current evidence is missing;
- sources conflict on the central claim;
- the answer is only document-local or corpus-local;
- a legal/regulatory/government numeric answer depends on jurisdiction, effective date, or source-bound values;
- evidence is weak but allows a bounded partial answer.

The system should refuse to compress away uncertainty when compression would create a materially misleading answer. For example, if two equal-authority sources conflict, the answer can be brief, but it must say that the sources conflict. If an official/current source is missing for a legal number, the answer can provide a partial value only if the missing official/current basis remains visible.

Fast mode differs from ignoring evidence quality. Fast minimizes scaffolding; it does not hide posture. A good Fast answer might be one sentence plus a citation and one caveat. It should not become a disclaimer wall: avoid generic legal/safety boilerplate, repeated uncertainty phrases, and backend terminology unless needed for user understanding.

## 7. Output structure templates

These are format contracts, not prompt text. Future implementation may adapt wording while preserving the structural promises.

### Fast template

1. **Direct answer:** one short paragraph or bullet.
2. **Minimal support:** citation or source reference where required.
3. **Required caveat only if central:** insufficiency, conflict, stale-source, inferred-vs-direct, document/corpus boundary, or numeric assumption.

Optional Fast additions:

- "Based on the available sources..."
- "This is an inference from..."
- "I do not have the required official/current source, so the bounded answer is..."

### Balanced template

1. **Short answer:** direct conclusion.
2. **Evidence basis:** two to five bullets or short paragraphs tying central claims to sources.
3. **Limits / caveats:** source gaps, conflicts, stale sources, inference labels, document/corpus boundary, or quantitative assumptions.
4. **What would change the answer:** only when useful, especially for current, legal, conflicting, weak-evidence, or developing topics.

Optional Balanced additions:

- source-quality note;
- conflict note;
- inferred-vs-direct note;
- next check.

### Deep template

1. **Executive answer:** concise conclusion and confidence/posture.
2. **Evidence map:** sources, source classes, dates, jurisdictions, and which claims each supports.
3. **Analysis:** reasoning, source hierarchy, and how evidence supports or fails to support the conclusion.
4. **Conflicts, gaps, and inferred claims:** explicit treatment where present.
5. **Quantitative assumptions / calculations:** if relevant.
6. **Limitations and what would change the answer:** missing sources, freshness checks, official confirmation, corpus expansion, or conflict resolution.
7. **Next checks:** focused, source-obligation-aware follow-up checks.

## 8. Pass/fail rubric

### Excellent answer

An excellent answer:

- answers the user's actual question early;
- preserves Controller / AnswerContract posture;
- uses citations close to supported claims;
- distinguishes direct evidence, inference, estimates, and unsupported gaps;
- surfaces central conflicts and source-class gaps;
- matches Fast / Balanced / Deep expectations;
- is concise for its mode;
- helps the user decide what to do next.

### Acceptable answer

An acceptable answer:

- gives a usable answer or appropriate insufficiency posture;
- cites central claims adequately;
- mentions material caveats, conflicts, and inference boundaries;
- may be less elegant or slightly over/under-detailed, but does not mislead;
- remains within source and mode obligations.

### Needs improvement

An answer needs improvement when it:

- buries the answer;
- overuses generic caveats;
- gives more source detail than the user can use;
- omits minor but useful source-quality context;
- has minor citation placement ambiguity;
- mismatches mode verbosity without creating a false claim.

### Unacceptable answer

An answer is unacceptable when it:

- launders citations, inferences, weak sources, stale sources, or user documents;
- gives an overconfident weak-evidence answer;
- hides a central conflict;
- silently drops required source obligations for brevity;
- invents or overstates numeric precision;
- treats user documents as verified public truth;
- refuses when a bounded partial answer is allowed;
- gives a wall of sources without a usable answer;
- gives a crisp answer that conflicts with Controller / AnswerContract posture;
- changes or ignores source-class, insufficiency, conflict, inference, or final-answer posture.

## 9. Relationship to existing Controller / AnswerContract model

Controller / AnswerContract owns source obligations, insufficiency posture, conflict posture, inference posture, and final-answer posture where those surfaces have been transferred. Analyst and Author must obey Controller-authorized posture. AG-81B does not create a parallel product authority that can override those decisions.

AG-81B should guide future Author, prompt, fixture, and UI work only when a later phase explicitly licenses those surfaces. Until then, AG-81B is review criteria and presentation-quality design. If the rubric appears to require a runtime hook, prompt change, citation change, or orchestrator change, stop and propose a future phase instead of implementing it here.

## 10. Relationship to AG-81A offline UX demo

AG-81A provides an offline fixture-backed demo shell and explicitly does not validate retrieval quality. AG-81B should guide future fixture review by defining what each fixture is trying to demonstrate:

- **Successful answer fixture:** answer-first, source-grounded, mode-appropriate, with source cards that support central claims.
- **Insufficient evidence fixture:** honest partial or insufficient posture without generic disclaimer sludge.
- **Conflict fixture:** visible contested claim, source disagreement, and unresolved/resolved posture.
- **Inferred claim fixture:** clear direct-vs-inferred boundary and source-premise support.
- **Document-review preview fixture:** document-local boundary and no user-document laundering into public truth.
- **Error/no-result fixture:** useful recovery path without implying retrieval validation.
- **Fast/Balanced/Deep comparison if later added:** same posture across modes, different presentation depth.

AG-81B does not modify AG-81A fixture data. Future fixture examples or UX screenshots should be handled by AG-81B-R1 or AG-81B-R3, not this phase.

## 11. Relationship to AG-82A cache design

Cached or replayed outputs must preserve answer-quality posture. Freshness labels, source obligations, conflict labels, inference labels, document/corpus boundaries, and quantitative assumptions must survive any future replay or reuse.

Cache-specific guidance for later phases:

- cached source lists cannot satisfy changed source obligations;
- cached final answers are high-risk for current, legal, financial, regulatory, government, and developing-topic questions;
- cached evidence may become stale even if the answer text remains fluent;
- replay should not erase missing-official/current posture or conflict/inference labels;
- cache keys and reuse decisions must account for mode, source obligations, freshness, jurisdiction/scope, corpus/document boundary, and user intent before reuse is considered.

AG-81B does not implement cache behavior, cache keys, cache instrumentation, or runtime cache reuse. AG-82B and AG-82C remain the appropriate phases for cache instrumentation and bounded reuse.

## 12. Future implementation roadmap

These are proposals only. They do not authorize implementation in AG-81B.

### AG-81B-R1 — Fixture-based answer-quality review examples

- **Scope:** add illustrative offline review examples that map existing or new fixture scenarios to this rubric.
- **Non-goals:** no prompt tuning, no live validation, no provider/model/search calls, no runtime behavior changes.
- **Expected touched surfaces:** docs, fixture review notes, possibly demo fixture metadata if explicitly licensed.
- **Protected surfaces kept closed unless explicitly licensed:** prompts, Author behavior, provider/search/retrieval, citation behavior, cache, orchestrator.
- **Stop conditions:** any need to alter live output behavior, source acquisition, prompts, or runtime posture.

### AG-81B-R2 — Prompt/output-contract alignment

- **Scope:** align Author or output prompts with this contract only if explicitly licensed by a later phase.
- **Non-goals:** no provider routing changes, retrieval changes, citation generation changes, cache changes, or live validation unless separately scoped.
- **Expected touched surfaces:** prompt files and narrow prompt tests, if licensed.
- **Protected surfaces kept closed unless explicitly licensed:** Controller runtime behavior, AnswerContract runtime behavior, provider/search/retrieval, source ordering, final evidence selection, DB/session shape.
- **Stop conditions:** prompt changes imply new source obligations, new retrieval behavior, or altered Controller posture.

### AG-81B-R3 — UI presentation polish for answer states

- **Scope:** improve UI display of insufficiency, conflict, inferred-vs-direct, source quality, document/corpus boundary, and mode labels.
- **Non-goals:** no runtime posture changes, no prompt tuning, no provider/search/retrieval changes.
- **Expected touched surfaces:** UI presentation components, docs, screenshots, fixture UX review.
- **Protected surfaces kept closed unless explicitly licensed:** pipeline orchestrator, provider/model/search, retrieval, prompts, citation generation, cache.
- **Stop conditions:** UI requires new runtime fields not already available or would reinterpret Controller posture.

### AG-83A — Document Review MVP Design alignment

- **Scope:** apply the document-review rubric to a future document-review design.
- **Non-goals:** no implementation in AG-81B, no private document ingestion changes here.
- **Expected touched surfaces:** document-review design docs, privacy/source-boundary specs, future fixtures.
- **Protected surfaces kept closed unless explicitly licensed:** runtime ingestion, storage, prompts, providers, retrieval, cache.
- **Stop conditions:** need for private document handling or public-truth validation logic.

### AG-84A — Personal Corpus / Library answer posture alignment

- **Scope:** apply the corpus/library rubric to future personal corpus answers.
- **Non-goals:** no corpus implementation in AG-81B.
- **Expected touched surfaces:** corpus design docs, library UX docs, future answer-state fixtures.
- **Protected surfaces kept closed unless explicitly licensed:** storage schema, retrieval, prompt behavior, provider/search, cache reuse.
- **Stop conditions:** need to treat corpus evidence as public truth or alter runtime evidence selection.

### AG-82B / AG-82C cache follow-ons

- **Scope:** preserve this rubric's posture fields in cache instrumentation and bounded reuse.
- **Non-goals:** no cache implementation in AG-81B.
- **Expected touched surfaces:** cache readiness docs/tests for AG-82B; bounded reuse code/tests for AG-82C if licensed.
- **Protected surfaces kept closed unless explicitly licensed:** final answers for high-risk current/legal/financial/government questions, provider/search behavior, citation generation, source ordering.
- **Stop conditions:** replay would drop freshness, source obligations, conflicts, inference labels, or document/corpus boundaries.

## 13. Explicit non-goals

AG-81B must not:

- tune prompts;
- change Author behavior;
- change Analyst behavior;
- change Economist behavior;
- change Scrutineer behavior;
- change synthesis-evaluator behavior;
- change Controller runtime behavior;
- change AnswerContract runtime behavior;
- change provider/search/retrieval behavior;
- change provider routing/depth/selection/swaps or add providers;
- change query generation/finalization/recency/official-bias/query ordering;
- change retrieval ranking/filtering;
- change final evidence selection;
- change citation generation or source ordering;
- change cache behavior;
- change cache keys or runtime cache reuse;
- change DB/session/RunOutcome runtime shape;
- implement document review;
- implement personal corpus/library;
- run live validation;
- modify `core/pipeline_orchestrator.py`;
- change package/CLI/env compatibility names;
- add runtime checks;
- add telemetry;
- add provider/model/search calls;
- add examples that look like live validation results unless clearly labeled illustrative, non-runtime, and not evidence of live retrieval quality.
