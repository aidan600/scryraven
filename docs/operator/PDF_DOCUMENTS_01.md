# PDF Documents 01

A research session can hold user-provided text PDFs. Research reads bounded
exact extracted text from those documents and can combine it with ordinary web
evidence. The document is evidence of what it states. Its provenance does not
independently verify an outside-world claim.

## Custody

`pypdf>=6.19,<7` extracts text at upload. This verification used pypdf 6.19.0.
Parsing uses an in-memory reader. There is no OCR engine, image pipeline, or
vision-model call.

Bounds, in `scryraven/documents.py`:

- 20 MiB
- 500 pages
- 2,000,000 extracted characters

The product says: "ScryRaven analyzes extracted PDF text only. Images and
scanned content are not analyzed." A page with no extracted text is counted.
That count does not claim the page contains an image. A PDF with no meaningful
extracted text is rejected. Encrypted, malformed, empty, and over-limit files
are rejected with fixed messages. Parser exceptions, paths, and PDF internals
are not shown.

Document IDs are session-local: `D1`, `D2`, and so on. The same SHA-256 in one
session returns the existing document. A different session may hold its own
copy. Filenames are display metadata. They are not filesystem paths or routes.

## Storage

The SQLite session store is schema 2. A version-1 database creates
`session_documents` and sets `PRAGMA user_version` to 2 without rewriting
session payloads. Opening a current database does not rewrite those payloads.
An unknown newer schema still fails as `incompatible_session_store`.

Each row stores the original PDF blob and the extracted pages, separate from
the completed-turn JSON. Attaching a document can update `updated_at` and does
not create a turn or advance the completed-turn revision. A blank session at
revision 0 can hold a document before the first answer. If that first question
fails, the session and the PDF remain. Deleting the session deletes its
document rows and blobs.

Selected exact views may be saved with a completed answer. Reopening checks
those views against the stored extraction.

## Research

The catalog lists document metadata only. Local Read (`target=D1`) and Find
(`scope=["D1"]`, or an unscoped Find that also sees retained web material) use
the retained text. They spend no external attempt and do not consume the Exa
Deep bootstrap. The first eligible generic Search on a turn with no retained
web acquisitions still uses Deep. A large document stays on the existing
bounded packet and exact-view limits. Exact refs look like `D1@12034:14789`.
Page numbers are the PDF page indexes from extraction, starting at 1. Page
boundaries are not crossed as one source sentence.

Web citations are unchanged. A document citation shows the filename and page
locator, not a publication URL. The original PDF for that session is
`/sessions/<session_id>/documents/<document_id>/original`.

Reading Room accepts `multipart/form-data` only on the two attach routes.
Other mutating forms stay URL-encoded, with the existing 256 KiB body bound.
Upload routes use the 20 MiB bound, the attach form token, and the existing
same-origin protection.

## Verification

Offline: 770 tests passed, `ruff check .` passed, and `git diff --check` was
clean before the live calls. Search width remains 6. Run limits remain 12
semantic attempts, 16 external attempts, 300 seconds, and 128,000 characters.
Targeted and expansion packets remain 32,000 and 48,000 characters.

Four ordinary product turns were frozen before the first call and run through
`ResearchSession` with the credential doorman. Research used `gpt-6-luna`.
Answer used `gpt-6.1-sol`. External provider attempts for the campaign: 1.
Reserve cases 5 and 6 were frozen and not run.

| Case | Result |
| --- | --- |
| Direct fact in a two-page yard report | Supported crane count 14 from `D1@0:54`, page 1. Zero external attempts. First Research packet had no document body. |
| Throughput value on page 1, qualification on page 7 | Answer kept 184 million units, fiscal year 1998, completed shipments, and the exclusion of returned units from the extracted sentences. Zero external attempts. The fixture was 455 characters, so one local Read returned every page; the 32,000-character bound is covered offline. |
| New process, same session, no re-upload | `D1` and its SHA-256 stayed. The follow-up cited the north-pier sentence on page 2. Zero external attempts. |
| PDF claim plus current web comparison | The PDF's 1948 WHO founding and WHO pages `https://www.who.int/about` and `https://www.who.int/about/history` were cited separately. One external Exa Search, with Deep, after the local document Read. |

The conservative token ceiling used for the campaign, at $15 per million input
tokens and $60 per million output tokens, was about $0.73. That figure is a
ceiling, not an invoice.

Body-free `document_navigation` counts were recorded. No Jev, Clef, embedding,
or vector index was called.
