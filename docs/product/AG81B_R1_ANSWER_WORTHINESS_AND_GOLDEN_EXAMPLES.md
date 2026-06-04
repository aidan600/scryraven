# AG-81B-R1 Answer-Worthiness and Golden Examples

Status: product behavior design / docs-first; extends AG-81B; no runtime behavior change; no prompt tuning; no live validation; no provider/model/search calls

## 1. Purpose and scope

AG-81B-R1 extends the AG-81B answer-quality rubric by defining what makes a ScryRaven answer worth the search time, latency, and provider cost. AG-81B already describes the stable Fast / Balanced / Deep output contract; this companion document adds search-value criteria, answer-density targets, source return-on-investment rules, golden example specs, answer-state labels, lower-tier evidence roles, and defect-classification guidance.

The central product claim is:

> A ScryRaven answer is worth search when it transforms retrieved material into a clearer, safer, more decision-useful conclusion than raw search results would provide.

This phase is a design artifact only. It does not change runtime behavior, prompts, retrieval, provider/search behavior, citations, cache behavior, UI, document-review behavior, personal-corpus behavior, Controller behavior, AnswerContract behavior, Author behavior, Analyst behavior, Economist behavior, Scrutineer behavior, or synthesis-evaluator behavior.

The examples in this document are illustrative review specs. They are not prompt outputs, not fixture outputs, not live validation results, not provider/model/search results, and not evidence of current retrieval quality.

## 2. Search Value / Answer-Worthiness Contract

A ScryRaven answer is worth the search when it adds value beyond the user's manual act of opening the top search results. It must do more than quote snippets, list links, or attach citations to plausible prose.

A search-worthy answer should:

- resolve the source hierarchy instead of merely listing sources;
- identify the highest-authority source actually used for the central claim;
- state what that source proves and what it does not prove;
- compress multiple sources into a supported conclusion;
- preserve dates, jurisdictions, units, scope, effective periods, and version boundaries where they affect the answer;
- distinguish direct evidence from inference;
- handle conflicts without prose-laundering or averaging away incompatible claims;
- give a decision boundary, next action, or clear reason to withhold judgment when useful;
- avoid implying that a lower-tier source satisfies an official/current/legal/canonical/source-bound obligation;
- make insufficiency useful by telling the user what is missing and why it matters.

Answer-worthiness differs by mode:

- **Fast:** worthiness comes from safe compression. The answer should beat opening one search result by giving the direct answer plus the one material source/limit needed to avoid overclaiming.
- **Balanced:** worthiness comes from compact synthesis. The answer should beat scanning several results by connecting the strongest evidence to a usable conclusion and naming material limits.
- **Deep:** worthiness comes from auditability and resolution. The answer should beat manual research by mapping evidence quality, conflicts, inference paths, gaps, assumptions, and decision boundaries.

## 3. Answer density by mode

| Mode | Target feel | Typical shape | Main risk | Worth-it test |
| --- | --- | --- | --- | --- |
| Fast | “I got the answer without baggage.” | One paragraph or 1–3 bullets. | Reckless compression or caveat sludge. | The answer is faster and safer than opening one search result. |
| Balanced | “I trust the answer and understand the basis.” | Short answer plus 2–5 evidence/limit bullets. | Drifting into mini-Deep or source summary. | The answer synthesizes sources into a usable conclusion. |
| Deep | “I can audit the reasoning.” | Executive answer, evidence map, analysis, conflicts/gaps, next checks. | Expensive source dump or verbosity for its own sake. | The answer resolves, maps, or safely bounds a complex evidence situation. |

Density rules:

- Fast should remove everything that does not affect the answer, source posture, or user's next step.
- Balanced should explain the basis without becoming a source-by-source report.
- Deep may be longer only when the extra structure improves auditability, not because the mode is expensive.
- All modes should preserve material insufficiency, conflict, inferred-claim, source-bound-number, currentness, jurisdiction, and document/corpus boundary posture.

## 4. Source ROI rules

A source earns space in the answer only if it improves the user's understanding of the central claim. This is especially important in Deep mode, where more retrieval can tempt a report to become retrieval exhaust.

Source ROI rules:

- Every included source should support, contradict, bound, date, contextualize, or fail to satisfy a central claim.
- Do not include a source merely because it was retrieved.
- Evidence maps should explain why each source class mattered.
- Cite fewer sources when fewer sources answer the question well.
- A short insufficiency answer can be higher quality than a long Deep report if the required source was not found.
- A lower-tier source can be valuable only when its role is explicit.
- Multiple citations for an easy background fact are lower value than one citation that resolves the central source obligation.
- Source ordering should not imply authority beyond what Controller / AnswerContract posture allows.
- Deep mode should separate authoritative sources, conflicting sources, contextual sources, and search leads rather than blending them into one list.

Useful source roles include:

- **Support:** the source directly supports a central claim.
- **Contradict:** the source conflicts with another material source or premise.
- **Bound:** the source narrows date, jurisdiction, scope, units, version, population, or applicability.
- **Date:** the source establishes currentness, effective period, publication timing, or staleness.
- **Contextualize:** the source explains background needed to interpret stronger evidence.
- **Non-satisfaction:** the source helps show that the required source class was not found or that a lower-tier source cannot satisfy the claim.

## 5. When to stop talking

Once the answer, evidence basis, and material limits are clear, stop.

Do not add:

- generic background that does not change the conclusion;
- generic disclaimers that do not change the user's decision;
- repeated uncertainty in multiple sections;
- backend trace language, pipeline terms, or provider-search narration unless it changes the user's decision;
- padding to make Deep mode feel worth the cost;
- broad “more research is needed” language when the missing evidence class is already named;
- source summaries that do not support, contradict, bound, date, contextualize, or expose non-satisfaction.

Caveats should be material and task-specific. A useful caveat changes how the user interprets, acts on, or verifies the answer. Caveat sludge makes the answer less safe by hiding the actual decision boundary.

## 6. What would change the answer

A “what would change the answer” section is useful only when it names a concrete condition that would alter the conclusion, confidence, applicability, or allowed posture.

Useful entries name a specific:

- source;
- fact;
- date;
- jurisdiction;
- missing document;
- corpus gap;
- conflict-resolution path;
- official/current source class;
- premise that would alter an inference;
- source-bound number or unit definition;
- effective period, version, release, or policy boundary.

Noise examples include:

- “More research could change this.”
- “New information may emerge.”
- “Consult additional sources.”
- “This may not be complete.”

Those statements are acceptable only when tied to a specific missing evidence class or decision boundary, such as “An updated IRS revenue procedure for tax year 2026 would change this threshold” or “The signed lease amendment, not the email thread, would control this document-local answer.”

## 7. UI-facing answer-state labels

These labels are product-language inventory for future UI work, likely AG-81B-R3. AG-81B-R1 does not implement UI labels and does not require runtime field changes.

| Label | Meaning | When it should appear | Must not imply | Likely future UX use |
| --- | --- | --- | --- | --- |
| Official source found | The answer uses an official/canonical source for a claim that requires one. | Official/current/canonical obligation is satisfied for the central claim. | That every claim is official, current, or exhaustive. | Trust badge near answer/evidence basis. |
| Official source missing | Required official/canonical/current source was not found or not usable. | The answer must be partial, insufficient, or bounded because the source class is unmet. | That no useful lower-tier context exists. | Warning state with missing-source explanation. |
| Current as of [date] | The answer's currentness is anchored to a known date. | Date-sensitive answer uses evidence with a known retrieval/publication/effective date. | That the claim will remain true after that date. | Timestamp near current claims. |
| Conflict unresolved | Material sources or premises conflict and the answer cannot resolve them. | Conflict affects the central conclusion or confidence. | That all sources are equally authoritative. | Conflict banner or evidence-map marker. |
| Inferred from sources | The conclusion is derived from sourced premises rather than directly stated by a source. | Indirect inference materially supports the answer. | That the conclusion is directly quoted or source-stated. | Inline inference label near claim. |
| Document-local | The answer is limited to the provided document. | User asks what a document says or the evidence is document-internal. | That the statement is true in the outside world. | Document review scope chip. |
| Corpus-local | The answer is limited to the user's corpus/library. | Personal corpus evidence answers the question without public-world validation. | That the corpus is complete or globally true. | Corpus answer scope chip. |
| Estimate / calculated | The answer includes a calculated or estimated value. | Economist-supported or arithmetic answer depends on assumptions or source-bound inputs. | That the value is exact unless stated. | Numeric posture badge with assumptions link. |
| Weak evidence | Available evidence is lower-tier, incomplete, stale, or not source-obligation-satisfying. | The answer can provide only partial/contextual information. | That weak evidence is worthless. | Caution marker on evidence basis. |
| Partial answer | The answer resolves part, but not all, of the user intent. | Some subclaims are supported while others lack required evidence. | That the resolved part is unreliable. | Partial-result banner and follow-up prompt. |
| Source-bound number | Numeric value is tied to a named source, date, unit, or method. | A number should not be generalized beyond the source context. | That other sources or periods use the same number. | Numeric footnote or label. |
| Stale source warning | Evidence may be outdated for a current-sensitive claim. | Source date/freshness is older than the claim's currentness need. | That the claim is false. | Currentness warning and refresh CTA. |
| Lower-tier context only | Lower-tier evidence is included for context, not proof. | Community/social/secondary evidence is useful but cannot satisfy stronger obligations. | That the lower-tier source proves the central claim. | Evidence role tag. |

## 8. Lower-tier evidence value roles

Lower-tier evidence can be useful when it is labeled by role and kept within its source obligations. It cannot satisfy stronger official/current/legal/canonical/source-bound obligations.

Positive roles for lower-tier evidence:

- identify likely search terms;
- point to official documents;
- show implementation experience;
- capture sentiment or perception;
- frame hypotheses;
- provide background context;
- explain why stronger evidence may be missing;
- reveal real-world usage or failure modes that official docs do not discuss;
- help prioritize what an official or primary source should be checked for next.

Acceptable role labels:

- **Community implementation signal:** practical evidence of how users or maintainers appear to apply something; not proof of official behavior.
- **Background context:** explanatory material that helps interpret stronger evidence; not the central authority.
- **Search lead:** a clue that points toward a stronger source; not evidence that the stronger source says the same thing.
- **Sentiment/perception only:** evidence of belief, reaction, or reputation; not evidence of factual truth.
- **Hypothesis, not proof:** a plausible explanation that still needs stronger evidence before being stated as a conclusion.
- **Non-satisfying comparator:** a source that shows why the available evidence is below the required source class.

## 9. Bad expensive-answer examples

An expensive answer fails answer-worthiness when it spends search cost without transforming evidence into a safer, clearer conclusion.

Failure modes:

- paraphrases snippets without synthesis;
- lists sources but does not say what they prove;
- spends Deep-mode cost on generic background;
- uses many citations for easy facts while missing the central source obligation;
- gives a long answer when the honest answer is “the required source was not found”;
- summarizes sources one by one without resolving what they mean together;
- buries the decision boundary;
- overuses caveats to hide that no useful synthesis happened;
- presents a “report” that is just retrieval exhaust;
- cites lower-tier evidence as if it satisfied official/current/legal/canonical obligations;
- hides direct-vs-inferred posture in a footnote or caveat pile;
- repeats the same uncertainty in the executive answer, evidence section, limitations section, and conclusion;
- includes stale or jurisdiction-mismatched sources without explaining the mismatch.

Diagnostic shorthand:

- **Expensive source dump:** lots of retrieved material, little synthesis.
- **Citation camouflage:** many citations make unsupported posture look grounded.
- **Caveat sludge:** repeated generic uncertainty obscures the real limit.
- **Authority miss:** the central required source class is absent but the answer proceeds confidently.
- **Decision-boundary burial:** the user must read the whole report to discover whether they can act.

## 10. Golden example catalog

These are canonical illustrative review specs. They are not full prompt outputs, not runtime fixtures, not live validation, and not evidence of live retrieval quality.

### 10.1 Fast: simple factual answer with one citation

- **Mode:** Fast.
- **User intent:** Get a stable factual answer quickly.
- **Evidence situation:** One high-quality source directly states the answer; no material conflict.
- **Answer-worthiness goal:** Beat opening one result by giving the answer and one citation without extra background.
- **Target structure:** One sentence or one short paragraph with a citation and, if needed, a date/version phrase.
- **Must-include posture labels:** Official source found when the source obligation requires it; Current as of [date] if current-sensitive.
- **Unacceptable if:** It adds a mini-report, cites multiple redundant sources, omits the source-bound date for a current claim, or hides a material caveat.
- **Why worth the search:** The answer compresses verification into one safe, cited statement.

### 10.2 Fast: official/current missing, bounded answer

- **Mode:** Fast.
- **User intent:** Get a current official fact or rule.
- **Evidence situation:** Search finds secondary discussion but not the required official/current source.
- **Answer-worthiness goal:** Avoid false confidence and quickly say the official source was not found.
- **Target structure:** One short answer-first insufficiency statement plus one bounded context sentence if useful.
- **Must-include posture labels:** Official source missing; Weak evidence or Lower-tier context only if secondary context is included; Current as of [date] only if anchored.
- **Unacceptable if:** It treats secondary coverage as sufficient, gives a confident final answer, or pads with generic “check official sources” language.
- **Why worth the search:** The value is not the answer itself; it is preventing the user from trusting a non-authoritative result.

### 10.3 Balanced: ordinary research question

- **Mode:** Balanced.
- **User intent:** Understand a non-current topic with enough basis to trust the answer.
- **Evidence situation:** Two or three reputable sources broadly agree; no official source obligation dominates.
- **Answer-worthiness goal:** Synthesize sources into a direct conclusion and explain the basis compactly.
- **Target structure:** Short answer followed by 2–4 evidence/limit bullets.
- **Must-include posture labels:** None unless a source-bound date, inference, or weak evidence limit matters.
- **Unacceptable if:** It summarizes each source separately without saying what they mean together, or drifts into Deep-style background.
- **Why worth the search:** The user gets the combined conclusion without manually comparing multiple pages.

### 10.4 Balanced: current/government numeric answer

- **Mode:** Balanced.
- **User intent:** Get a current government number, threshold, rate, deadline, or eligibility rule.
- **Evidence situation:** An official government source gives the number with date, unit, effective period, and scope.
- **Answer-worthiness goal:** Preserve the number's authority and applicability boundaries.
- **Target structure:** Short numeric answer; evidence bullet naming official source, date/effective period, units, and scope; limit bullet if applicability varies.
- **Must-include posture labels:** Official source found; Current as of [date]; Source-bound number.
- **Unacceptable if:** It omits units/effective period, uses a secondary calculator as authority, or gives the number without jurisdiction/scope.
- **Why worth the search:** The answer packages the number with the metadata the user needs to avoid misusing it.

### 10.5 Balanced: weak evidence partial answer

- **Mode:** Balanced.
- **User intent:** Determine whether a claim is likely true when strong evidence is unavailable.
- **Evidence situation:** Lower-tier or incomplete evidence points one way, but required proof is absent.
- **Answer-worthiness goal:** Provide useful context without upgrading weak evidence into proof.
- **Target structure:** Partial answer; evidence roles; missing evidence; decision boundary.
- **Must-include posture labels:** Weak evidence; Partial answer; Lower-tier context only; Official source missing if applicable.
- **Unacceptable if:** It says “probably” without explaining source weakness, or treats community/social/secondary evidence as satisfying a stronger obligation.
- **Why worth the search:** The answer separates useful signals from proof and tells the user what would be needed to decide.

### 10.6 Deep: conflict map

- **Mode:** Deep.
- **User intent:** Resolve or understand conflicting evidence.
- **Evidence situation:** Sources disagree on a central claim, or one source's date/scope/jurisdiction undermines apparent agreement.
- **Answer-worthiness goal:** Map the conflict instead of smoothing it over.
- **Target structure:** Executive answer; conflict table; source hierarchy; analysis of which source controls which claim; unresolved gaps; next checks.
- **Must-include posture labels:** Conflict unresolved when not resolvable; Official source found/missing as applicable; Current as of [date] if current-sensitive.
- **Unacceptable if:** It averages conflicting claims, buries the conflict, or presents all sources as equal authority.
- **Why worth the search:** The answer saves the user from mistaking disagreement for consensus.

### 10.7 Deep: indirect inference

- **Mode:** Deep.
- **User intent:** Answer a question not directly stated by any one source but derivable from sourced premises.
- **Evidence situation:** Premises are source-supported; conclusion requires a transparent inference bridge.
- **Answer-worthiness goal:** Make the inference useful without citation-laundering it as directly sourced.
- **Target structure:** Executive conclusion; premise map; inference bridge; limitations; what would change the inference.
- **Must-include posture labels:** Inferred from sources; Source-bound number or Estimate / calculated if numeric; Weak evidence if premises are lower-tier.
- **Unacceptable if:** It cites premise sources as though they directly state the conclusion, omits a premise, or hides a premise conflict.
- **Why worth the search:** The answer performs auditable reasoning the user would otherwise have to reconstruct manually.

### 10.8 Deep: quantitative/Economist-supported estimate

- **Mode:** Deep.
- **User intent:** Estimate a quantity from source-bound values, assumptions, or ranges.
- **Evidence situation:** Some inputs are directly sourced; others require assumptions or ranges.
- **Answer-worthiness goal:** Provide a decision-useful estimate with auditable assumptions and source-bound limits.
- **Target structure:** Executive estimate/range; input table; calculation/assumptions; sensitivity; source-bound limits; what would change the estimate.
- **Must-include posture labels:** Estimate / calculated; Source-bound number; Current as of [date] where relevant; Weak evidence for unsupported assumptions.
- **Unacceptable if:** It reports false precision, hides assumptions, uses stale numbers without warning, or lets lower-tier inputs satisfy source-bound obligations.
- **Why worth the search:** The answer converts scattered inputs into a bounded estimate the user can inspect.

### 10.9 Document review: “document says” vs “public truth”

- **Mode:** Balanced or Deep, depending on document complexity.
- **User intent:** Ask what an uploaded/provided document says, possibly compared with outside truth.
- **Evidence situation:** Document-local evidence may answer the document question; public truth requires separate public evidence not implemented in this phase.
- **Answer-worthiness goal:** Keep document-local claims separate from public-world claims.
- **Target structure:** Document-local answer; quoted/paraphrased document basis; explicit boundary; optional future public-check seam.
- **Must-include posture labels:** Document-local; Partial answer if public truth is requested but unavailable; Official source missing if an outside official source would be required.
- **Unacceptable if:** It treats the document as public truth, silently imports outside assumptions, or fails to say whether it is answering “the document says” or “the world says.”
- **Why worth the search:** The answer protects the user from confusing internal document content with verified external reality.

### 10.10 Personal corpus: “your corpus says” vs “the world says”

- **Mode:** Balanced or Deep, depending on corpus breadth and user stakes.
- **User intent:** Ask what the user's library, notes, or saved corpus indicates.
- **Evidence situation:** Corpus evidence may be incomplete, private, stale, or non-representative; public evidence is separate.
- **Answer-worthiness goal:** Make corpus scope explicit and avoid globalizing corpus-local findings.
- **Target structure:** Corpus-local answer; evidence clusters; corpus gaps; public-world boundary; next corpus/public checks.
- **Must-include posture labels:** Corpus-local; Partial answer; Weak evidence if the corpus is thin; Lower-tier context only where applicable.
- **Unacceptable if:** It says “the answer is” when only “your corpus contains” is supported, or treats absence from the corpus as proof of absence in the world.
- **Why worth the search:** The answer turns a private evidence set into an honest bounded conclusion.

### 10.11 Developing/controversial topic

- **Mode:** Deep by default; Balanced if the user asks for a compact status update and source posture is simple.
- **User intent:** Understand a changing or disputed topic.
- **Evidence situation:** Sources differ by time, authority, access, or framing; official updates may lag or omit interpretation.
- **Answer-worthiness goal:** Preserve currentness and conflict while giving a usable status boundary.
- **Target structure:** Current status as of date; authority map; conflict/gap section; what would change the answer.
- **Must-include posture labels:** Current as of [date]; Conflict unresolved if applicable; Weak evidence or Lower-tier context only for commentary/social evidence.
- **Unacceptable if:** It states a moving claim without date, treats commentary as fact, or hides disagreement.
- **Why worth the search:** The answer reduces risk from stale or one-sided search results.

### 10.12 “Just answer” with non-removable caveat

- **Mode:** Fast or Balanced.
- **User intent:** Wants a terse answer and asks to avoid caveats.
- **Evidence situation:** A material caveat, source gap, conflict, inference, or jurisdiction/date boundary affects correctness.
- **Answer-worthiness goal:** Respect brevity while preserving the non-removable posture.
- **Target structure:** Direct answer with one embedded caveat or one short caveat bullet.
- **Must-include posture labels:** Whichever label captures the non-removable limit, such as Inferred from sources, Official source missing, Conflict unresolved, Source-bound number, or Current as of [date].
- **Unacceptable if:** It suppresses the caveat to satisfy style, or expands into a long disclaimer pile.
- **Why worth the search:** The answer stays concise without becoming unsafe.

## 11. Answer defect classification bridge

AG-81B-R1 does not repair answer defects. It helps classify them so the next phase opens the right surface. Not every bad answer should trigger prompt tuning; not every bad answer should trigger retrieval work; not every bad answer should trigger UI work.

Diagnostic taxonomy:

| Defect class | Symptom | Likely future surface | Not automatically |
| --- | --- | --- | --- |
| Presentation defect | Correct posture/evidence exists, but the answer is too verbose, poorly ordered, or hard to scan. | AG-81B-R2 prompt/output-contract alignment or AG-81B-R3 UI polish. | Retrieval failure. |
| Prompt/style defect | Author wording hides limits, repeats caveats, or misses the desired mode density despite available posture. | Prompt alignment if explicitly licensed. | Controller runtime defect. |
| Source acquisition defect | Required official/current/primary/canonical source was not retrieved. | Retrieval/provider/search/query phase if explicitly licensed. | Prompt defect. |
| Evidence selection defect | Retrieved sources include the right evidence, but final evidence or evidence map omits/misuses it. | Final evidence selection or Controller-owned handoff phase if licensed. | UI defect. |
| Controller/AnswerContract posture defect | Runtime posture fails to mark insufficiency, conflict, inference, source-bound number, or boundary state. | Controller / AnswerContract phase if explicitly licensed. | Author-only defect. |
| Citation placement defect | Citation appears near a claim it does not support or implies direct support for inferred claim. | Citation behavior/source attribution phase if licensed. | Pure prose polish. |
| UI presentation defect | Backend answer posture exists but UI display hides labels, boundaries, source roles, or currentness. | AG-81B-R3 UI presentation polish. | Retrieval or prompt failure. |
| Cache/replay defect | Cached or replayed content drops freshness, source obligation, evidence posture, or answer-worthiness. | AG-82B instrumentation or AG-82C reuse guard phase if licensed. | Live answer quality proof. |
| User-document/corpus boundary defect | Answer confuses document-local/corpus-local evidence with public truth. | AG-83A document review or AG-84A corpus/library design. | General web retrieval issue. |

Review workflow:

1. Identify the user harm: wrong answer, unsupported confidence, wasted cost, hidden caveat, stale claim, bad UI affordance, or scope confusion.
2. Identify whether the required evidence existed, was selected, was handed off, was represented in posture, was cited correctly, was written clearly, and was displayed clearly.
3. Open only the smallest future phase that owns the failed layer.

## 12. Relationship to AG-81B

AG-81B remains the main answer-quality rubric and Fast / Balanced / Deep output contract. AG-81B-R1 is a review companion, not a replacement.

AG-81B-R1 adds:

- answer-worthiness and search-value criteria;
- answer-density targets by mode;
- source ROI and stop-talking rules;
- “what would change the answer” discipline;
- UI-facing answer-state label inventory;
- lower-tier evidence value roles;
- bad expensive-answer examples;
- golden example specs;
- defect classification.

Use AG-81B to ask “is the answer shaped correctly and safely?” Use AG-81B-R1 to ask “was the search cost transformed into user value?”

## 13. Relationship to AG-81A

AG-81A offline UX demo fixtures remain product-shell demos, not retrieval validation. AG-81B-R1 does not modify demo fixtures and does not add runtime example outputs.

Future fixture review may use AG-81B-R1 examples to evaluate whether offline demo scenarios communicate answer-worthiness, answer-state labels, and evidence roles clearly. Any future fixture additions should remain explicitly labeled fixture/demo-only and should not be treated as proof of live retrieval quality.

AG-81B-R1 can guide later AG-81B-R2/R3 or UX review examples, especially for answer density, state labels, and document/corpus boundaries.

## 14. Relationship to AG-82A / AG-82B

AG-82A defines cache architecture and cost-efficiency boundaries. AG-81B-R1 defines how to judge whether search cost was productively spent from the user's perspective.

Future cache instrumentation should eventually measure cost and latency, while answer-worthiness judges value. A cheap answer can still be poor if it misses source hierarchy, and an expensive Deep answer can be worthwhile if it resolves a complex conflict or safely bounds uncertainty.

AG-82B may later add redacted answer-worthiness tags or cost/value telemetry, but AG-81B-R1 does not add instrumentation. AG-82C cache reuse must preserve answer-worthiness posture and must not replay expensive but low-value answers, stale current claims, dropped insufficiency, lost conflict state, erased inference labels, or document/corpus boundary mistakes.

If future answer-worthiness instrumentation appears to require orchestrator hooks, document a future seam and stop there. AG-81B-R1 does not modify `core/pipeline_orchestrator.py`.

## 15. Future implementation roadmap

These proposals do not authorize implementation in AG-81B-R1.

### AG-81B-R2 — Prompt/output-contract alignment

- **Scope:** Align prompts or output contracts to AG-81B and AG-81B-R1 only if explicitly licensed.
- **Non-goals:** No provider/search/retrieval changes, no cache changes, no UI implementation, no live validation unless separately scoped.
- **Expected touched surfaces:** Prompt files, narrow prompt tests, output-contract docs/tests if licensed.
- **Protected surfaces kept closed unless explicitly licensed:** Controller runtime behavior, AnswerContract runtime behavior, provider/search/retrieval, final evidence selection, citation behavior/source ordering, DB/session/RunOutcome shape, cache.
- **Stop conditions:** The change requires new source obligations, query behavior, retrieval behavior, Controller posture, or broad orchestrator rewrites.

### AG-81B-R3 — UI presentation polish for answer states

- **Scope:** Display answer-state labels, evidence roles, mode density, currentness, conflicts, inference posture, source-bound numbers, and document/corpus boundaries more clearly.
- **Non-goals:** No new runtime posture, no prompt tuning, no provider/search/retrieval changes, no cache reuse.
- **Expected touched surfaces:** UI components, docs, screenshots, fixture UX review if licensed.
- **Protected surfaces kept closed unless explicitly licensed:** Pipeline orchestrator, prompts, provider/model/search, retrieval, citation generation, source ordering, cache.
- **Stop conditions:** UI needs runtime fields that do not already exist or would reinterpret Controller / AnswerContract posture.

### AG-82B — Cache instrumentation with answer-worthiness tags, no reuse

- **Scope:** Add redacted candidate telemetry for cost, latency, answer-worthiness labels, and blocked-reuse reasons without runtime reuse.
- **Non-goals:** No cache hits that affect decisions, no final-answer replay, no provider/search/retrieval behavior change.
- **Expected touched surfaces:** Cache readiness docs/tests, telemetry surfaces, redaction-safe reason codes if licensed.
- **Protected surfaces kept closed unless explicitly licensed:** Runtime cache reuse, cache keys that affect decisions, provider/model/search, prompts, final evidence selection, citation behavior, DB/session/RunOutcome shape.
- **Stop conditions:** Instrumentation could satisfy runtime decisions, expose private artifacts, store raw prompts/provider payloads, or replay answer posture.

### AG-83A — Document Review MVP Design

- **Scope:** Design document-local answer posture, document evidence boundaries, and optional public-truth comparison seams aligned to AG-81B-R1 examples.
- **Non-goals:** No document ingestion/storage implementation in AG-81B-R1, no public-truth validation implementation, no personal corpus/library implementation.
- **Expected touched surfaces:** Document-review design docs, privacy/source-boundary specs, future fixture plans if licensed.
- **Protected surfaces kept closed unless explicitly licensed:** Runtime ingestion, storage, retrieval, prompts, providers, cache, DB/session/RunOutcome shape.
- **Stop conditions:** The work requires private document handling, persistent storage, public search integration, or UI implementation beyond the licensed design.

## 16. Explicit non-goals

AG-81B-R1 must not:

- tune prompts;
- change Author behavior;
- change Analyst behavior;
- change Economist behavior;
- change Scrutineer behavior;
- change Controller or AnswerContract runtime behavior;
- change provider/search/retrieval behavior;
- change provider routing/depth/selection/swaps or add providers;
- change query generation/finalization/recency/official-bias/query ordering;
- change retrieval ranking/filtering;
- change citation generation or source ordering;
- change final evidence selection;
- change cache behavior;
- change cache keys or runtime cache reuse;
- change DB/session/RunOutcome shape;
- implement UI labels;
- implement document review;
- implement personal corpus/library;
- run live validation;
- modify `core/pipeline_orchestrator.py`;
- change package/CLI/env compatibility names;
- add examples that look like live validation results unless clearly labeled illustrative, non-runtime, and not evidence of live retrieval quality.

Protected surfaces kept closed:

- prompts;
- provider/search/retrieval behavior;
- provider routing;
- provider depth;
- provider selection;
- provider swaps;
- new providers;
- query generation;
- query finalization;
- recency merge;
- official-bias insertion;
- query ordering;
- retrieval ranking/filtering;
- final evidence selection;
- citation behavior;
- source ordering;
- Author prose;
- Author final-answer posture;
- Analyst behavior;
- Economist behavior;
- Scrutineer behavior;
- synthesis-evaluator behavior;
- Controller runtime behavior;
- AnswerContract runtime behavior;
- DB/session/RunOutcome runtime shape;
- cache behavior;
- cache keys;
- runtime cache reuse;
- package/CLI/env compatibility rename;
- live validation;
- hosted deployment;
- broad `core/pipeline_orchestrator.py` rewrite.
