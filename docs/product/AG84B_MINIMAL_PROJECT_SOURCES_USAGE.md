# AG-84B Minimal Project Sources / Saved Source Records Usage

Status: narrow implementation note; manifest-first local project/source persistence; no retrieval integration; no prompt changes; no model, provider, search, or live-validation calls; no connectors, Project Instructions, snapshots, cache behavior, or thread report generator.

## Scope

AG-84B adds the smallest local-first Project Sources slice for ScryRaven:

- create a local Project manifest;
- list local Project manifests;
- promote an existing `DocumentReviewContext` into a Project Source;
- persist compact source manifests with explicit schema version, generator marker, privacy marker, validation posture, and retention state;
- list Project Sources for a Project;
- remove a Project Source membership edge without deleting the underlying source manifests.

This is storage metadata only. It does not make Project Sources available to retrieval, prompts, providers, model calls, public web validation, source ranking, citation ordering, Project Instructions, connectors, snapshots, saved reports, or thread reports.

## Storage root

The default manifest root is:

```text
output/project_sources/
```

The repository already ignores `output/`, so this root is local/untracked by default. Tests inject temporary directories instead of writing to the default root.

AG-84B writes only JSON manifests under these subdirectories:

```text
output/project_sources/projects/
output/project_sources/project_sources/
output/project_sources/source_records/
output/project_sources/source_revisions/
```

Raw source files are not copied by default. The manifest metadata records `raw-source-files-not-copied-by-default` to make that storage policy inspectable.

## Creating and listing Projects

Use the pure helper module:

```python
from core.project_sources import create_project, list_projects

project = create_project("Research Vault", description="Local-only source records")
projects = list_projects()
```

A Project manifest stores:

- `schema_version`;
- `project_id`;
- `name`;
- optional `description`;
- `created_at` and `updated_at` UTC timestamps;
- `privacy_class`, defaulting to `local-private`;
- ordered `project_source_ids`;
- `retention_state`, defaulting to `active`;
- manifest metadata with generator/version and local/private boundary markers.

## Saving a document review as a Project Source

Promote an existing document-review context:

```python
from core.document_review import build_document_review_context
from core.project_sources import add_project_source_from_document_review

context = build_document_review_context("# Memo\n\nThe current API price is $20.")
result = add_project_source_from_document_review(project, context)
```

The promotion writes:

- a Project manifest update containing the ProjectSource ID;
- a `ProjectSource` manifest for the Project membership edge;
- a compact `SourceRecord` manifest;
- a compact `SourceRevision` manifest.

## What is stored

A promoted document-review Project Source preserves compact metadata derived from `DocumentReviewContext`:

- document identity: `document_id`, `document_hash`, input format, document-review version, and privacy marker;
- parser metadata: parser name, parser version, parser confidence, parser notes, and context parser metadata;
- source kind and Project membership;
- evidence role, source scope, validation posture, and local/private boundary marker;
- source-obligation summary counts for finding labels, claim types, source obligations, evidence roles, validation needs, and risk levels;
- anchor IDs, section IDs/headings, normalized line references, parser-origin references, extraction confidence, source format, parser name/version, and bounded text previews;
- chunk IDs, document hash, section IDs/headings, anchor IDs, bounded chunk previews, extraction confidence, evidence label, locality label, source scope, and deterministic retrieval-mode label;
- finding IDs, labels, anchor IDs, extraction confidence, bounded note previews, claim type, source obligation, evidence role, validation need, and risk level.

## What is not stored

AG-84B does not persist raw private document text by default. It deliberately omits:

- `DocumentReviewContext.normalized_text`;
- full chunk text;
- full finding text;
- raw source files;
- provider payloads;
- raw prompts;
- JSONL trace payloads;
- SQLite/session/RunOutcome rows;
- private logs;
- caches;
- full raw traces;
- secrets or `.env` values.

Compact anchor and chunk previews may be stored because they are bounded provenance previews already derived from the document-review context. They are not a document library, corpus, retrieval index, or public validation result.

## Listing and removing Project Sources

```python
from core.project_sources import list_project_sources, remove_project_source

sources = list_project_sources(project)
project = remove_project_source(project, sources[0].project_source_id)
```

Removal is membership-edge-only in AG-84B. It updates the Project's `project_source_ids`, marks the ProjectSource edge `retention_state` as `removed-from-project`, and leaves SourceRecord/SourceRevision manifests active and in place. Source record/revision deletion, tombstoning, secure erase, managed-copy deletion, and retention UX are intentionally deferred.

## Boundaries and deferred work

AG-84B keeps these surfaces closed:

- retrieval integration and source picker behavior;
- prompts and Project Instructions;
- model/provider/search calls and live validation;
- connectors;
- snapshots;
- saved reports and thread report generator;
- cache behavior, cache keys, and runtime cache reuse;
- SQLite/session/RunOutcome shape;
- Controller/AnswerContract runtime behavior;
- broad orchestrator work.

Future phases may harden storage location policy, add deletion/tombstone UX, add report saving, add source picking/retrieval integration, instrument cache readiness, implement Project Instructions, implement connectors, or add snapshots. Those are not part of AG-84B.

## AG-84B-R1 Streamlit UI seam

AG-84B-R1 adds a minimal Streamlit surface for the existing manifest helpers. The sidebar entry **Projects / Project Sources** opens a local page where users can create Projects, list existing Projects, select a Project, and view its Project Sources. This UI is a thin wrapper over `core.project_sources`; it does not add retrieval, prompt, model, provider, search, connector, cache, Project Instructions, snapshot, saved-report, or thread-report behavior.

The Projects page displays the local/private boundary and the default manifest root (`output/project_sources/`). Project rows show name, ID, description, source count, privacy class, retention state, and created/updated timestamps.

For a selected Project, the page lists active Project Sources with title, ProjectSource ID, source kind, evidence role, validation posture, source-obligation summary, parser name/version/confidence/notes, input format, retention state, raw-text-persisted marker, privacy class, and added/updated timestamps.

The Document Review page now includes a **Save to Project** section whenever a session-local `DocumentReviewContext` exists. Users can select an existing Project or create a new Project inline, optionally adjust the Project Source title, and save the current review context as a Project Source. The save action calls `add_project_source_from_document_review` through the UI helper and preserves the AG-84B storage boundary: raw normalized document text is not persisted by default; compact manifests and bounded previews are saved locally only.

The Projects page also exposes a membership-edge-only **Remove from this Project** action. Removal updates the Project's source pointer and marks the ProjectSource edge `removed-from-project`; SourceRecord and SourceRevision manifests remain active. This is not deletion, tombstoning, secure erase, snapshot removal, or managed-copy deletion.

The UI labels these boundaries explicitly:

- storage is local/private manifest storage under `output/project_sources/`;
- raw source files are not copied by default;
- raw normalized document text is not persisted by default;
- saved Project Sources are not public validation;
- there is no retrieval integration yet and Project Sources are not automatically injected into answers;
- there are no connectors, Project Instructions, snapshots, saved reports, or thread report generator in this phase.
