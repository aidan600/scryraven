# AG-83B Minimal Document-Local Review MVP Usage

Status: narrow implementation note for pasted text / Markdown only; no PDF, DOCX, OCR, public web validation, provider/model/search calls, persistent corpus/library, prompt changes, cache reuse, or orchestrator changes.

## What AG-83B adds

AG-83B adds a deterministic, session-local Document Review MVP for user-provided pasted text or Markdown. It converts the provided document into a retained `DocumentReviewContext` with normalized text, a stable document hash/ID, section and paragraph/excerpt anchors, document-local chunks, deterministic claim/review findings, follow-up retrieval hits, and a Markdown export artifact.

The document is treated as private user-provided context, not as ordinary live web evidence and not as proof of outside-world truth. All review labels are based only on the provided document.

## How to use it in the Streamlit UI

1. Open ScryRaven.
2. Click **Document Review** in the sidebar.
3. Paste plain text or Markdown into **Paste text or Markdown**.
4. Optionally enter a document title.
5. Click **Build local review**.
6. Review the generated session-local context, anchored chunks, claim candidates, and labels.
7. Use the follow-up box to retrieve retained document-local chunks by heading, keyword, or concept.
8. Download the Markdown export with **Download document-local review Markdown**.

The UI explicitly labels the boundary: pasted text / Markdown only, no PDF/DOCX/OCR, no public web validation, no provider/model/search calls, no persistent corpus/library, and document retention only for current session state.

## Retention and privacy boundary

The retained document context is stored only in Streamlit `st.session_state` for the current document-review session. AG-83B does not save pasted document text to JSONL, SQLite, logs, caches, full traces, a document library, or a personal corpus.

## Deterministic limits

AG-83B does not perform semantic model review. It uses local parsing and simple deterministic cues for summaries, claim candidates, unsupported-by-document labels, external-validation-required labels, source-bound numeric labels, and document-supported inference labels. Future phases can add PDF/DOCX parsing, higher-fidelity anchors, model-mediated review, source-obligation classification, personal corpus/library design, or cache instrumentation only if separately licensed.
