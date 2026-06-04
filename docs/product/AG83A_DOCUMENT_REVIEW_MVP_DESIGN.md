# AG-83A Document Review MVP Design

Status: product feature design / docs-first; no runtime behavior change; no document ingestion, parsing, storage, prompt tuning, live validation, provider/model/search calls, cache reuse, UI implementation, or orchestrator work

## 1. Purpose and scope

AG-83A designs ScryRaven's first Document Review MVP as a durable product and architecture contract before implementation. It defines the intended user promise, evidence labels, document-local citation posture, claim posture, privacy boundaries, storage questions, cache relationship, export shapes, and a safe follow-on implementation slice.

This phase is design-only. It is not an implementation phase, not a parser selection phase, not a prompt-alignment phase, and not a live validation phase.

AG-83A explicitly separates Document Review MVP design from runtime behavior. It does not add parsing, upload, storage, OCR, embeddings, corpus indexing, prompt changes, provider/search calls, public web validation, cache reuse, UI components, Controller behavior, AnswerContract behavior, Author/Analyst/Economist/Scrutineer behavior, retrieval changes, or `core/pipeline_orchestrator.py` work.

The design aligns with the AG-81B answer-quality rubric, AG-81B-R1 answer-worthiness examples, AG-81A offline UX demo boundary, AG-82A cache architecture, source hierarchy invariants, conflict posture, and indirect inference posture. It does not assume ChatGPT Project Sources exist as repo files unless they are committed in this repository.

## 2. MVP product promise

The future Document Review MVP should let a user upload or provide a document and ask ScryRaven to review that document in a bounded, evidence-labeled way.

The MVP should support user requests such as:

- summarize the document;
- critique the argument or decision memo;
- extract explicit and implied claims;
- find unsupported claims or weakly supported leaps;
- identify internal contradictions, inconsistencies, gaps, risks, red flags, and review questions;
- extract action items, deadlines, responsible parties, or obligations when the document itself states them;
- suggest rewrites that preserve document-local facts and label assumptions;
- create a review artifact that can be exported.

The MVP should return answers that:

- cite document-internal evidence with anchors when available;
- distinguish what the document directly states from what the model infers;
- state when a claim is unsupported, ambiguous, contradicted, or externally unverifiable from the document alone;
- distinguish document-local answers from public-truth claims;
- avoid treating a document passage as proof of outside-world truth;
- optionally describe how future web validation or personal-corpus comparison could check the document, without performing that validation in AG-83A.

The implementation target after this design should be concrete enough for AG-83B: pasted text or Markdown first, deterministic local extraction, document-local summaries and claim tables, stable anchors, basic unsupported-claim detection, and an exportable Markdown review artifact with no provider/search calls unless a later licensed phase explicitly authorizes them.

## 3. Non-goals

AG-83A must not implement:

- parsing;
- upload flow;
- storage;
- OCR;
- embeddings;
- corpus indexing;
- public web validation;
- personal corpus or library behavior;
- prompt changes;
- live validation;
- UI components;
- cache reuse;
- provider, model, or search calls;
- `core/pipeline_orchestrator.py` work.

AG-83A also does not choose final parser libraries, add fixtures, add example uploaded documents, change offline demo fixture data, alter runtime AnswerContract shape, or change live-web citation behavior.

## 4. Supported document classes for MVP design

AG-83A designs future support for multiple document classes while recommending a smaller AG-83B implementation slice.

| Document class | Likely extraction needs | Known risks | MVP posture |
| --- | --- | --- | --- |
| PDF | Text extraction, page numbers, layout ordering, headings, tables, footnotes, document metadata, optional OCR detection. | Page fidelity may be approximate; columns can scramble reading order; tables and footnotes can detach from body text; scanned PDFs may contain no text; metadata can be missing or misleading. | Design now; likely AG-83C unless AG-83B scope remains small enough. |
| DOCX | Paragraphs, styles, headings, lists, tables, comments, footnotes/endnotes, tracked-change state when available. | Style names may be inconsistent; comments/tracked changes can be private or omitted; table structure can flatten; page numbers are not intrinsic without rendering. | Design now; implement after pasted text/Markdown unless strongly needed. |
| TXT | Lines, paragraphs, simple section separators, encoding detection. | Little metadata; weak heading detection; line wrapping can create false anchors; tables are often malformed. | Good early candidate if privacy and anchors are simple. |
| Markdown | Headings, paragraphs, lists, code blocks, tables, links, front matter. | Generated Markdown can contain malformed tables; links may look like evidence but still need posture labels; front matter may be absent or private. | Best AG-83B candidate with pasted text. |
| Pasted text | Session-local text, user-provided title/context, paragraphs, optional manual delimiters. | No file metadata; user may paste excerpts rather than whole documents; anchors depend on normalized text; privacy expectations are high. | Recommended first implementation surface. |
| HTML or email-like text | DOM structure, headings, links, quoted replies, headers, signatures, attachments, table structure. | Boilerplate, tracking URLs, nested replies, forwarded content, and headers can confuse authorship and dates. | Future candidate only. |

Cross-cutting extraction concerns:

- **Page fidelity:** PDF page numbers may be available, but DOCX/TXT/Markdown/pasted text may not have stable pages. The answer must not invent page precision.
- **Heading/section detection:** Headings should be retained as anchors when confidently extracted and marked approximate when inferred.
- **Paragraph/line anchors:** Paragraph IDs can be stable after normalization; line anchors are useful only when line wrapping is reliable.
- **Tables:** Tables need row/column anchors and should be labeled uncertain if extraction flattens or merges cells.
- **Footnotes/endnotes:** Notes should preserve backlink relationships when possible; otherwise cite note anchors separately.
- **Scanned/OCR documents:** OCR is out of scope for AG-83A and should not be claimed as supported before validation.
- **Malformed text:** Extraction should prefer honest uncertainty over precise-looking anchors.
- **Metadata loss:** File name, author, date, title, and version are helpful but not authoritative unless supplied or extracted with confidence.
- **Privacy/storage:** Uploaded documents are user-private by default; extraction artifacts must not be committed or exposed in logs, docs, raw traces, or provider payloads without explicit future policy.

## 5. Document evidence model

The future document review system should preserve these evidence types:

- **Document text:** extracted or pasted user document content.
- **Document metadata:** filename, title, author, creation/modification dates, declared source, hash, version, document class, extraction timestamp, parser version, and confidence.
- **Section/heading structure:** explicit headings or inferred section labels.
- **Page/paragraph/line anchors:** local locators that help users find the cited passage.
- **Tables:** table IDs, captions, rows, columns, cells, and extraction confidence.
- **Quoted snippets:** short previews tied to anchors, used for user locatability rather than overexposure.
- **Extracted claims:** normalized claims with posture labels, cited anchors, and source-obligation classes.
- **Model-inferred review notes:** critiques, risks, gaps, contradictions, and suggested questions derived from document premises.
- **User-provided context:** user instructions, purpose, audience, business context, jurisdiction, or reviewer preference.
- **Optional future web evidence:** public sources acquired by a later licensed web-validation phase.
- **Optional future corpus evidence:** personal library or workspace corpus materials acquired under AG-84-class boundaries.

Stable evidence labels:

| Label | Means | Must not imply |
| --- | --- | --- |
| `document-local` | The claim is grounded in text, structure, metadata, or tables from the reviewed document. | That the claim is true in the outside world. |
| `document-inferred` | The model inferred the note from document-local premises and should cite those premises. | That the document directly states the inference. |
| `user-provided context` | The user supplied context outside the document, such as goals or jurisdiction. | That the context is document evidence or public truth. |
| `public-web validated` | A future phase acquired public evidence that supports or refutes the claim under source-obligation rules. | That AG-83A performed validation, or that document evidence alone satisfied public truth. |
| `corpus-local` | A future personal corpus/library item supports the claim within the user's corpus boundary. | That the claim is generally true outside the corpus. |
| `unsupported` | The reviewed document does not support the claim, or the answer lacks adequate evidence for it. | That the claim is false in the outside world. |

The evidence model should allow multiple labels for one item only when each label is independently supported. For example, a claim can be `document-local` and `external-validation-required`; it should not become `public-web validated` until a later phase actually validates it.

## 6. Document-local citation / anchor design

Future document-review answers should cite document evidence with the most precise honest anchor available:

- page number when available and reliable;
- section heading or inferred section label;
- paragraph anchor;
- line anchor when line positions are stable;
- table, row, and column anchor for tabular claims;
- footnote/endnote anchor when relevant;
- excerpt ID for normalized snippets;
- short quote/snippet preview to help the user locate the evidence;
- document version or hash when the review may be reused, exported, or compared;
- anchor confidence when extraction is uncertain.

Recommended anchor shape for future implementation:

```text
[document-local: doc=<document_id_or_hash>; version=<version_or_hash>; section=<heading>; page=<p?>; para=<p?>; line=<l?>; table=<t?>; row=<r?>; col=<c?>; excerpt=<e?>; confidence=<high|medium|low|approximate>]
```

When page or line anchors are unavailable, the answer should:

- use section/heading anchors;
- use paragraph or excerpt IDs;
- label anchors as approximate when generated from inferred structure;
- avoid pretending precise page, line, or table fidelity exists;
- include enough quoted preview for the user to locate the claim without dumping private text;
- make uncertainty local to the anchor rather than spreading generic caveats through the whole answer.

Citation placement should follow AG-81B: citations belong close to the claims they support, and citation clusters should not imply support for unrelated claims.

## 7. Document review task taxonomy

| Task | Expected user value | Document evidence needed | Likely answer shape | What must remain labeled | Common failure modes |
| --- | --- | --- | --- | --- | --- |
| Executive summary | Quickly understand the document's main point and implications. | Title, headings, abstract/intro/conclusion, repeated key claims. | Short summary plus key caveats or missing context. | Document-local boundary; inferred synthesis. | Overstating purpose; importing outside facts. |
| Section-by-section summary | Navigate long documents and find local content. | Heading map, paragraphs, page/section anchors. | Section bullets with anchors and local gaps. | Approximate sections; missing headings. | Treating inferred headings as original headings. |
| Claim extraction | Turn prose into reviewable claims. | Sentences, tables, footnotes, numeric values. | Claim table with posture, anchor, source obligation. | Direct vs implied vs unsupported. | Extracting opinions as facts; losing units/dates. |
| Factual consistency within the document | Find contradictions or tensions. | Multiple claims, dates, units, definitions, table values. | Contradiction list with both anchors. | Contradicted-within-document; unresolved status. | Choosing a winner without authority; missing scope differences. |
| Missing support / unsupported claim detection | Identify assertions not supported by the document. | Claims, references, surrounding premises, citations inside the document. | Unsupported-claim list with why support is missing. | Unsupported-by-document vs false. | Treating absence as disproof; demanding support for trivial context. |
| Risk review | Help user spot legal, financial, operational, reputational, technical, or delivery risk. | Claims, obligations, timelines, assumptions, disclaimers, gaps. | Risk register with severity rationale and anchors. | Inferred risk; external-validation-required. | Giving legal/financial advice as fact; unanchored alarmism. |
| Decision memo critique | Assess whether the memo supports its recommendation. | Recommendation, premises, alternatives, evidence, assumptions. | Decision critique: strengths, gaps, questions, decision blockers. | Reviewer inference vs document statement. | Substituting model preference for evidence. |
| Contract/proposal red flag review | Surface ambiguous obligations, missing terms, risks, and assumptions. | Terms, clauses, obligations, dates, amounts, exclusions. | Red flags with clause/section anchors and review questions. | Legal/current/official-source-needed when applicable. | Practicing law; missing jurisdiction; claiming enforceability. |
| Source/citation audit inside the document | Check whether cited sources or footnotes support document claims. | Document's own references, footnotes, quoted source descriptions. | Citation audit table: claim, cited support, gap. | Document-internal audit only unless public validation is licensed. | Treating cited references as actually checked online. |
| Rewrite suggestions | Improve clarity, structure, tone, or evidentiary support. | Original text, target audience, user context. | Suggested replacement text plus rationale and assumptions. | User context; inference; unsupported assertions to avoid. | Introducing new unsupported claims. |
| Action-item extraction | Identify tasks, owners, dates, obligations, dependencies. | Imperatives, commitments, dates, tables, named parties. | Action list with anchors and ambiguity flags. | Ambiguous owner/date; document-local only. | Inventing owners or deadlines. |
| Public-web or corpus comparison | Later extension for validation or comparison. | Document claim table plus future public/corpus evidence. | Validation matrix. | Future-only; external/corpus boundary. | Performing unlicensed validation; laundering sources. |

## 8. Claim extraction and claim posture

Future claim extraction should classify both claim type and posture.

| Claim type | Labeling and citation guidance |
| --- | --- |
| Directly stated by document | Label `direct document statement`; cite the precise document anchor and snippet. |
| Implied by document | Label `document-supported inference`; cite premises, not a nonexistent direct statement. |
| Contradicted within document | Label `document-internal contradiction`; cite all conflicting anchors and do not choose a winner without a rule. |
| Unsupported by document | Label `unsupported-by-document`; explain what support is missing and avoid saying the claim is false. |
| Requires public validation | Label `external-validation-required`; cite the document claim and state that public truth was not checked. |
| Requires user/corpus validation | Label `corpus-validation-required`; cite the document claim and explain what user library or private records would be needed. |
| Numeric/source-bound claim | Label `source-bound numeric`; preserve units, date, scope, formula, assumptions, and anchor. |
| Legal/regulatory/current claim | Label `legal/current/official-source-needed`; cite the document and require official/current sources later. |
| Recommendation/opinion claim | Label `opinion/recommendation`; cite the recommendation and distinguish rationale from fact claims. |

Posture labels for review output:

- `direct document statement` — the document says it directly.
- `document-supported inference` — a reasonable inference from cited premises.
- `document-internal contradiction` — the document contains incompatible claims or scope/date/unit tensions.
- `unsupported-by-document` — the document does not provide support for the claim.
- `external-validation-required` — public truth requires public evidence not obtained in AG-83A.
- `corpus-validation-required` — user-private records or a personal corpus would be needed.
- `source-bound numeric` — the claim's number depends on source, unit, date, and scope.
- `legal/current/official-source-needed` — the claim requires official/current/legal evidence for validation.
- `opinion/recommendation` — the document or reviewer is making a judgment, not stating a verified fact.

A claim may have a document anchor and still require external validation. The anchor proves what the document says, not whether the outside world agrees.

## 9. Document-local truth vs public truth

This is the core AG-83A boundary.

ScryRaven must distinguish these statements:

- **“The document says X.”** The reviewed document directly states X, with a document-local anchor.
- **“X appears unsupported in the document.”** The document contains X or relies on X but does not provide document-local support for it.
- **“X is true in the outside world.”** Public evidence satisfies the source obligation for X. AG-83A does not produce this posture.
- **“X would require external validation.”** X may be true or false, but the document alone is insufficient for public-truth posture.
- **“The user's corpus says X.”** A future user-private corpus item supports X within a corpus-local boundary.
- **“The model infers X from document premises.”** X is a reviewer inference from cited document premises, not a direct document statement.

Anti-laundering rules:

- No document-local laundering into public truth.
- No public-truth claim without public evidence.
- No model inference presented as document-stated fact.
- No citation to a document passage as proof of outside-world truth unless the task is explicitly only document-local.
- No user-provided context laundering into document evidence.
- No corpus-local claim generalized to public truth.
- No document-internal citation audit presented as a live verification of those cited sources.
- No absence-from-document claim presented as proof of absence in the world.

Illustrative, non-runtime posture examples:

- Correct: “The document states that Project A will launch in Q4, anchored to the roadmap section. That establishes the document-local claim only.”
- Correct: “The document does not support its claim that the market is growing 20% annually; outside validation would require a current market source.”
- Correct: “This risk is an inference from the payment timeline and penalty clause sections, not a sentence the document directly states.”
- Correct: “Your corpus could later be used to check whether the vendor's pricing matches prior invoices.”
- Incorrect: “The market is growing 20% annually” with only a document-local citation.
- Incorrect: “The vendor breached the contract” when the document only states a missed milestone and no legal validation was performed.

## 10. Source-obligation classification for document claims

AG-83A does not implement validation. It designs a classification future phases can use to decide which document claims would require stronger evidence if validated externally.

| Class | Triggers | Why document evidence alone is or is not sufficient | External evidence needed later | Document-review label |
| --- | --- | --- | --- | --- |
| Official/current | Claims about current product docs, policies, prices, statuses, releases, API behavior, government thresholds, or official announcements. | The document proves only that it asserts the current fact; current truth requires canonical current sources. | Official/current/canonical source with date/version. | `external-validation-required`; `official-current-source-needed`. |
| Legal/regulatory | Statutes, regulations, deadlines, eligibility, compliance, court/procedural status, enforceability, jurisdiction-sensitive claims. | User documents are not legal authority unless the task is only reviewing document text. | Primary legal/regulatory or official agency sources; jurisdiction and effective date. | `legal/current/official-source-needed`. |
| Financial/numeric | Prices, revenue, costs, rates, rankings, estimates, thresholds, market sizes, budgets, calculations. | Numbers are source-bound and can be stale, scoped, or derived. | Primary financial source, official report, audited data, calculation inputs, or current price source. | `source-bound numeric`; `external-validation-required`. |
| Medical/scientific | Health, safety, clinical efficacy, scientific causality, study findings. | Documents can summarize evidence but do not prove clinical/scientific truth without source review. | Peer-reviewed literature, official medical guidance, study protocol/results, systematic review. | `medical/scientific-validation-required`. |
| Academic | Literature claims, paper interpretations, benchmarks, empirical methods, citations to studies. | The document may report claims accurately or inaccurately; validation requires the underlying literature. | Primary papers, accepted versions, DOI/arXiv, method details, citations. | `academic-source-needed`. |
| Product/API/current technical | Current API, SDK, package, browser, model, pricing, or compatibility behavior. | Technical facts change; user docs can be stale or internal. | Official docs/changelog/release notes/current source. | `official-current-technical-source-needed`. |
| Personal/corpus-local | Claims about the user's prior files, invoices, notes, policies, emails, project history, or private library. | The document can state a private fact, but corpus truth requires the user's private records. | AG-84-style corpus evidence, workspace documents, user-approved records. | `corpus-validation-required`. |
| Internal document-local only | Claims about what this document says, its sections, internal consistency, or its own argument structure. | Document evidence is sufficient for document-local review. | None unless user asks for public validation. | `document-local`. |

The classifier should be conservative. If a document claim would materially affect a decision and depends on freshness, jurisdiction, official status, specialized evidence, numeric precision, or private records, label the source obligation rather than silently treating the document as enough.

## 11. Answer-quality alignment

AG-83A applies AG-81B and AG-81B-R1 to document review.

Document-review worthiness comes from transforming the provided document into a clearer, safer, more decision-useful review than the user would get by rereading it manually. It is worth the processing cost when ScryRaven:

- compresses long or dense document content without losing material caveats;
- maps claims to anchors;
- separates direct statements, inferences, unsupported claims, contradictions, and external-validation needs;
- identifies risks, review questions, and decision blockers;
- produces an exportable artifact that preserves evidence posture.

It is not worth the cost when it merely paraphrases every section, dumps snippets, invents external conclusions, adds caveat sludge, or performs an expensive-looking review without anchorable insights.

Mode shapes:

- **Fast document review:** one short document-local answer, 3-5 key bullets, only essential anchors, and a concise boundary such as “based only on the provided document.”
- **Balanced document review:** short answer, claim/risk/gap bullets with anchors, a compact “what the document supports / does not support / would need external validation” separation, and export-ready structure.
- **Deep document review:** executive answer, evidence map, claim table, contradiction/gap map, source-obligation classes, risk register, review questions, and export appendix when the document complexity justifies it.

Source ROI for document anchors:

- Include anchors that support central summary, claims, risks, contradictions, or action items.
- Do not dump every paragraph anchor.
- Use snippets to locate evidence, not to expose unnecessary private text.
- Prefer one precise anchor over several vague anchors.
- Surface low-confidence extraction only where it affects trust.

Stop-talking rules:

- Stop once the answer has satisfied the requested review task and visible evidence obligations.
- Do not expand a Fast review into a report unless the user asked for audit depth.
- Do not repeat generic “documents can be wrong” caveats after the document-local boundary is clear.
- State what would change the answer: public validation, corpus comparison, better extraction, full document access, missing pages, table fidelity, or user-provided purpose/jurisdiction.

Bad expensive document-review examples:

- A Deep review that summarizes every paragraph but never identifies unsupported claims.
- A claim table with no anchors.
- A risk register that cites no document premises.
- A public-truth conclusion based only on a user document.
- A source/citation audit that implies cited sources were checked online when they were not.
- A privacy-insensitive answer that quotes large chunks of a private document unnecessarily.

## 12. UX states for document review

AG-83A designs states, not UI components.

| State | User meaning | Likely future UI label/message | Must not imply | Blocks review? |
| --- | --- | --- | --- | --- |
| Document loaded | A document or pasted text is available for review. | “Document loaded.” | Parsing is perfect or public truth is validated. | No. |
| Extraction uncertain | Text/structure extraction may be incomplete or scrambled. | “Extraction confidence is limited.” | The document is unusable or claims are false. | Reduces confidence; may block precise anchors. |
| Anchors available | Page/section/paragraph/excerpt anchors can be shown. | “Anchors available.” | Anchors prove outside-world truth. | No. |
| Anchors unavailable | Review can cite only broad sections or snippets. | “Precise anchors unavailable.” | ScryRaven may invent precision. | Reduces confidence. |
| Table extraction uncertain | Table rows/columns may not be reliable. | “Table extraction uncertain; verify table values.” | All non-table text is unreliable. | Blocks table-specific conclusions if central. |
| Document too long | The document exceeds current review limits. | “Document too long for full review; choose a section or summary mode.” | ScryRaven reviewed everything. | May block full-document review. |
| Unsupported claims found | Some document claims lack internal support. | “Unsupported document claims found.” | Those claims are false publicly. | No. |
| Contradictions found | Internal tensions or conflicts were detected. | “Internal contradictions found.” | ScryRaven resolved the conflict. | No, unless the user asked for definitive decision support. |
| External validation required | Some claims need public or official evidence. | “Outside validation required for public truth.” | Validation was performed. | No for document-local review; yes for public-truth answer. |
| Review complete | Requested document-local review is done. | “Review complete.” | Exhaustive legal/public validation. | No. |
| Export ready | A shareable artifact can be generated. | “Export ready.” | Export is safe to share without privacy review. | No. |
| Privacy warning | The document may contain private or sensitive content. | “Private document: review storage/sharing settings.” | The document was sent externally. | May block provider/live validation in future phases until consent exists. |

## 13. Privacy and local-first boundaries

Documents are user-private by default.

AG-83A privacy rules:

- no committing uploaded documents;
- no raw document text in repo docs;
- no raw prompts or provider payloads;
- no full raw traces;
- no raw DB rows;
- no private logs;
- no cache contents;
- no secrets, `.env`, API keys, or uploaded private documents;
- document contents are not fixtures unless explicitly curated, sanitized, and licensed as fixture data;
- illustrative examples in this design doc are non-runtime and are not document-ingestion outputs.

Future runtime privacy expectations:

- do not send document contents to live providers without explicit user/provider-key behavior in a later licensed phase;
- prefer local-first review and local-first storage decisions;
- redact future validation packets to the minimum needed claim, anchor, snippet, and source-obligation class;
- avoid logging raw document text, raw provider payloads, prompts, full traces, DB rows, and private cache artifacts;
- provide deletion and retention controls for any persisted document, anchor map, review artifact, or cache;
- keep workspace/session boundaries explicit;
- treat exports as user-controlled artifacts that may still contain private text.

## 14. Storage and persistence design questions

AG-83A does not implement storage. It defines future options and decision criteria.

Future options:

- **Transient review only:** document state exists only for the session.
- **Local saved review artifact:** store the review output without storing the full document.
- **Local document library:** save documents and anchor maps for later review; belongs mainly to AG-84 personal corpus/library design.
- **Workspace/project document store:** save documents under a workspace boundary with local-first retention/deletion.
- **Hashed document ID/version:** identify unchanged documents without exposing contents.
- **Anchor map persistence:** persist parser/chunker/anchor results for repeat review.
- **Export-only mode:** generate a review artifact and discard document state.
- **Per-session temporary document state:** keep minimal state for follow-up within a session.
- **Deletion/retention controls:** user-visible controls for deleting documents, anchors, review artifacts, and caches.

Decision criteria:

- privacy risk;
- UX value;
- cache value;
- export value;
- implementation complexity;
- user trust.

AG-83B should decide only what is necessary for the minimal implementation slice, likely transient or export-only state for pasted text/Markdown. Persistent document libraries, personal corpus indexing, cross-session search, and document collections belong to AG-84A or later.

## 15. Cache relationship

AG-83A connects to AG-82A but does not add runtime cache reuse.

Future document-review cache candidates:

- document parsing cache;
- chunking cache;
- anchor map cache;
- document version/invalidation records;
- parser/chunker/schema version records;
- local-private document cache boundaries;
- embedding cache only as a later AG-84/corpus concern.

Future cache requirements:

- document hash/version;
- parser version;
- chunker or anchor schema version;
- workspace/session boundary;
- privacy class;
- deletion/retention policy;
- redaction and no-commit rules;
- extraction confidence;
- invalidation when document bytes, normalized text, parser version, chunker version, anchor schema, privacy scope, or retention settings change.

Document parsing and chunking are promising early cache wins because they can avoid repeated local work for unchanged local documents. But reuse must remain private/local, versioned, redacted, and deletion-aware. Public-web search caches, final-answer caches, and embedding caches remain outside AG-83A.

## 16. Export design

Future export shapes:

| Export shape | User value | Evidence/anchors to include | Privacy warnings | Share safety | Boundary preservation |
| --- | --- | --- | --- | --- | --- |
| Markdown | Simple portable review memo. | Summary, claim/risk tables, anchors, snippets. | May include private snippets. | User must review before sharing. | Easy to label document-local vs external-required. |
| PDF/HTML later | Polished artifact for stakeholders. | Same as Markdown, plus appendix and styling. | Higher accidental-sharing risk. | Review redactions before distribution. | Must keep labels visible in layout. |
| Review memo | Decision-ready narrative. | Key claims, gaps, contradictions, recommendations, anchors. | May expose sensitive strategy. | Share only with intended audience. | Separate document says / reviewer inference / external validation. |
| Claim table | Audit claims and posture. | Claim text, type, posture, anchor, source-obligation class. | Claim text may quote private content. | Useful internally; redact before external sharing. | Strong boundary preservation if labels are mandatory. |
| Risk register | Track operational/legal/financial/project risks. | Risk, severity rationale, document premise anchors, review questions. | Risks can be sensitive. | Internal by default. | Risks should be labeled inferred unless directly stated. |
| Source/anchor appendix | Make review auditable. | Anchor map, snippets, extraction confidence, document hash/version. | Contains concentrated private evidence. | Least safe to share externally. | Strong audit support if not mistaken for public proof. |
| Redaction-safe summary | Share high-level findings without raw text. | Minimal paraphrased findings and omitted/private markers. | Still may reveal document existence or conclusions. | Safer, not automatically public-safe. | Must not hide evidence limits. |

Exports should preserve document-local vs public-truth boundaries. An exported document review should not become a source for later public-truth claims unless later validation reacquires appropriate public evidence.

## 17. Minimum viable implementation slice after AG-83A

A later AG-83B should be the smallest useful implementation, not a broad document platform.

Recommended AG-83B scope:

- pasted text or Markdown first;
- deterministic local parsing only;
- document-local summary and claim extraction;
- stable section/paragraph/excerpt anchors;
- basic unsupported-claim detection;
- basic internal contradiction flagging when exact or near-explicit tensions are present;
- explicit labels for direct document statement, document-supported inference, unsupported-by-document, external-validation-required, and source-bound numeric;
- Markdown exportable review artifact;
- no public web validation;
- no persistent personal library;
- no live provider/model/search calls unless a future license explicitly authorizes them;
- no PDF/DOCX/OCR if that slows the first slice too much;
- no cache reuse beyond explicit future design;
- no broad orchestrator work.

AG-83B should prove:

- document-local boundary labels are visible;
- anchors display and remain honest about precision;
- unsupported claim detection works at a basic level;
- an exportable review artifact preserves evidence posture;
- no provider/search calls occur;
- private document text is not committed or logged in unsafe artifacts.

## 18. Future extension roadmap

| Phase | Scope | Non-goals | Expected touched surfaces | Protected surfaces kept closed unless licensed | Stop conditions |
| --- | --- | --- | --- | --- | --- |
| AG-83B — Minimal document-local review implementation | Pasted text/Markdown, local parsing, anchors, summary, claim extraction, export artifact. | PDF/DOCX/OCR, public validation, corpus library, provider calls. | Narrow document-review module, tests, docs, possibly demo-only UI seam if licensed. | Prompts, providers, retrieval, live citations, Controller runtime, orchestrator broad work. | Stop if provider/search calls, persistent library, DB shape, or broad orchestrator hooks are needed. |
| AG-83C — PDF/DOCX parsing and anchor fidelity | Add parser support and fidelity tests for pages, headings, tables, notes. | Public validation, corpus indexing, legal conclusions. | Parser adapters, anchor schema tests, extraction confidence fixtures. | Prompt/provider/retrieval/cache reuse unless separately licensed. | Stop if OCR quality or rendering claims cannot be validated. |
| AG-83D — Claim extraction and source-obligation classification | Improve claim taxonomy, source-obligation labels, contradiction detection. | Live web validation. | Claim model, deterministic classifiers, evaluation fixtures. | Final web evidence selection and Author posture unless licensed. | Stop if classification requires public truth lookups. |
| AG-83E — Optional public-web validation design/implementation | Design or implement validated comparison between document claims and public evidence. | Personal corpus unless AG-84 allows it. | Web-validation seam, source-obligation acquisition, tests. | Existing provider routing/search/final evidence unless explicitly scoped. | Stop if source hierarchy, prompt, provider, or citation behavior changes exceed license. |
| AG-84A — Personal Corpus / Library Design | Define private library, storage, indexing, corpus-local truth, deletion. | Public-web validation and hosted deployment. | Product/architecture docs, storage design, corpus evidence model. | Runtime corpus indexing until implementation phase. | Stop if privacy/storage choices are unresolved. |
| AG-82B/82C document cache alignment | Instrument and eventually reuse parsing/chunk/anchor caches safely. | Answer caching or public truth cache shortcuts. | Telemetry/cache design, local-private cache tests. | Runtime reuse until AG-82C scope authorizes it. | Stop if deletion, privacy, or invalidation policy is unclear. |

## 19. Stop conditions for future implementation

Future implementation should stop if it requires:

- live provider calls not licensed;
- private document storage decisions not designed;
- public-truth validation behavior not licensed;
- prompt behavior changes not licensed;
- new retrieval/provider behavior;
- DB/session/RunOutcome shape changes not licensed;
- broad `core/pipeline_orchestrator.py` work;
- persistent document library behavior before AG-84A;
- OCR or extraction quality claims without validation;
- cache reuse without AG-82B/AG-82C scope;
- modifying live-web citation behavior or source ordering;
- using user-private documents as fixtures without sanitization and explicit license.

If future document-review implementation appears to need orchestrator hooks, document a narrow future seam and stop. Do not implement it under AG-83A.

## 20. Explicit non-goals

AG-83A keeps all closed surfaces closed:

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
- citation behavior/source ordering for live web answers;
- Author prose or final-answer posture;
- Analyst/Economist/Scrutineer/synthesis-evaluator behavior;
- Controller/AnswerContract runtime behavior;
- DB/session/RunOutcome runtime shape;
- cache behavior;
- cache keys;
- runtime cache reuse;
- document ingestion implementation;
- document storage implementation;
- personal corpus/library implementation;
- package/CLI/env compatibility rename;
- live validation;
- hosted deployment;
- broad `core/pipeline_orchestrator.py` rewrite.

This document is a design contract only. It authorizes future planning conversations and narrow follow-on phase briefs; it does not authorize runtime document-review behavior.
