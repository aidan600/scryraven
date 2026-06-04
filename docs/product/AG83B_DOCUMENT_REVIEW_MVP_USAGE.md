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
