# AG-83B Minimal Document-Local Review MVP Usage

Status: narrow implementation note for pasted text / Markdown only; no PDF, DOCX, OCR, public web validation, provider/model/search calls, persistent corpus/library, prompt changes, cache reuse, or orchestrator changes.

## What AG-83B adds

AG-83B adds a deterministic, session-local Document Review MVP for user-provided pasted text or Markdown. It converts the provided document into a retained `DocumentReviewContext` with normalized text, metadata, a stable document hash/ID/version, section and paragraph/excerpt anchors, document-local chunks, deterministic claim/review findings, follow-up retrieval hits, and a Markdown export artifact.

The AG-83B-R1 hardening pass clarifies that this retained context is the same-session boundary between the raw/private user document, parsed sections/anchors, Controller/model-usable document chunks, deterministic document-local findings, follow-up retrieval, and export artifacts. The document is treated as private user-provided context, not as ordinary live web evidence, not as public-truth proof, and not as persistent corpus/library material. All review labels are based only on the provided document.

## How to use it in the Streamlit UI

1. Open ScryRaven.
2. Click **Document Review** in the sidebar.
3. Paste plain text or Markdown into **Paste text or Markdown**.
4. Optionally enter a document title.
5. Click **Build local review**.
6. Review the generated session-local context, anchored chunks, claim candidates, and labels.
7. Use the follow-up box to deterministically retrieve retained document-local chunks by heading or keyword tokens; this is not model-mediated natural-language Q&A.
8. Download the Markdown export with **Download document-local review Markdown**.

The UI explicitly labels the boundary: pasted text / Markdown only, no PDF/DOCX/OCR, no public web validation, no provider/model/search calls, no persistent corpus/library, and document retention only for current session state.

## Retention and privacy boundary

The retained document context is stored only in Streamlit `st.session_state` for the current document-review session. AG-83B does not save pasted document text to JSONL, SQLite, logs, caches, full traces, a document library, or a personal corpus. `DocumentChunk` packets carry the stable document ID/hash, chunk ID, section heading, anchor IDs, preview/text, extraction confidence, `document-local-evidence`, `document-local-only`, and `private-session-document` labels so future Controller/model seams can consume them without converting them into public web evidence.

## Deterministic limits

AG-83B does not perform semantic model review. It uses local parsing and simple deterministic cues for summaries, claim candidates, unsupported-by-document labels, external-validation-required labels, source-bound numeric labels, and document-supported inference labels. Future phases can add PDF/DOCX parsing, higher-fidelity anchors, model-mediated review, source-obligation classification, personal corpus/library design, or cache instrumentation only if separately licensed.


## AG-83B-R1 retained context contract

`DocumentReviewContext` intentionally separates:

- full normalized pasted text retained for same-session follow-up;
- metadata (`title`, input format, document ID/hash/version, creation time, and privacy marker);
- parsed sections;
- paragraph/list/table anchors with normalized line references and extraction confidence;
- document-local chunks labeled as private session document context;
- deterministic review findings and labels;
- Markdown export text;
- boundary and privacy warnings.

Anchors are honest for pasted text and Markdown only. They use normalized line references rather than PDF pages, rendered page numbers, DOCX layout positions, OCR coordinates, or external parser precision. Table and list confidence is deliberately lower than paragraph confidence.

Follow-up retrieval searches only the retained `context.chunks`, returns snippets, anchors, labels, scores, and the deterministic retrieval mode, and returns no hits when no keyword/heading overlap is found. It does not call providers, models, public search, storage, caches, or a personal corpus. Full natural-language document Q&A remains a future model-mediated seam and must preserve the document-local/private-source boundary.

Markdown export includes the document ID/hash/version, privacy marker, document-local evidence/source-scope labels, boundary notice, privacy warning, review labels, anchors, unsupported/external-validation-required states, and the follow-up boundary. It does not contain public validation or persistent document-library state.

## AG-83D claim extraction and source-obligation classification

AG-83D keeps the same pasted text / Markdown-only, deterministic, session-local boundary and hardens the claim layer. `ReviewFinding` now preserves the original stable label tuple while adding explicit local classification fields: `claim_type`, `source_obligation`, `evidence_role`, `validation_need`, and a modest deterministic `risk_level`. These fields are helper/output metadata for document review only; they do not alter Controller, AnswerContract, provider, search, cache, persistence, or orchestrator behavior.

The deterministic source-obligation classifier can label claims that would need stronger evidence if the user later wanted truth validation:

- `document-local-only` for claims that are only being treated as statements in the pasted document;
- `official-current-source-needed` for current/official/status/price/policy-like claims;
- `legal-current-official-source-needed` for legal, regulatory, compliance, jurisdiction, contract, tax, or effective-date claims;
- `financial-numeric-source-needed` and `source-bound-numeric` for numbers, prices, costs, rates, forecasts, estimates, budgets, and similar scoped values;
- `medical-scientific-validation-required` for medical, clinical, health, safety, efficacy, treatment, trial, patient, scientific, causal, or study claims;
- `academic-source-needed` for paper, literature, benchmark, methodology, DOI/arXiv, citation, or study claims;
- `product-api-current-technical-source-needed` for API, SDK, package, browser, model, compatibility, release-note, changelog, endpoint, or version claims;
- `corpus-validation-required` for claims that depend on internal records, customer records, uploaded documents, a private corpus, or a future document library.

These labels are not public validation. A document anchor proves only what the provided document says. Even when a local support cue such as “according to,” “table,” “appendix,” “figure,” “report,” “survey,” “study,” or “source” is present, AG-83D does not check that cited material. It only avoids the narrower `unsupported-by-document` label when a local support cue is nearby. Current, legal, numeric, scientific, academic, technical, and corpus-bound claims can still carry external/corpus validation obligations.

AG-83D also adds conservative deterministic cues for inference boundaries, recommendations/opinions, action items/obligations, date/deadline claims, risk/red-flag claims, and possible internal document tensions. Possible tensions are intentionally unresolved: the export labels them as possible document-internal tension and does not choose a winner or state that either claim is true or false.

The Markdown export and Streamlit claim-candidate display include the richer classification fields, anchors, notes, and the same document-local boundary. No PDF/HTML export, PDF/DOCX/OCR parsing, model-mediated Q&A, public-web validation, persistent document library, personal corpus, or cache reuse was added.

## AG-83C PDF/DOCX local parser note

AG-83C extends the document-review MVP with a narrow local parser seam while keeping
`DocumentReviewContext` as the canonical retained context. Pasted text and Markdown
remain supported exactly as the primary path.

Supported parser inputs:

- **Pasted text / Markdown:** normalized into deterministic lines and anchors.
- **PDF:** text-based PDF extraction only through the local `pypdf` dependency when
  installed from project requirements. PDF anchors are page-level only when the
  parser returns page-separated text.
- **DOCX:** local `.docx` package XML extraction for headings, paragraphs,
  lists-as-paragraphs, and simple flattened tables. DOCX anchors use structural
  block order only; DOCX rendered page numbers are not claimed.

Boundaries and limits:

- No OCR, scanned-PDF recovery, image extraction, rendering stack, layout
  coordinates, or table-layout fidelity is provided.
- No provider/model/search calls, prompt tuning, public web validation, live
  validation, persistent corpus/library behavior, raw document persistence, or
  runtime cache reuse is added.
- Parsed documents remain private/session-local document-review context. They are
  not public evidence and do not validate outside-world truth.
- Parser confidence is extraction confidence only. It says how cautiously to treat
  the extracted text and anchors; it is not truth confidence for document claims.
- Anchors are only as precise as parser support allows: normalized lines for
  pasted text/Markdown, PDF page anchors for text-based PDFs, and DOCX structural
  block order for DOCX.

The Streamlit page may accept an optional PDF/DOCX upload when parser support is
available. The upload path feeds the same deterministic document-local review,
claim classification, follow-up retrieval, and Markdown export as pasted text;
it does not create a document library or personal corpus.
